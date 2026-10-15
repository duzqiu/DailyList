"""请求底座：基址、发一次请求、把后端的错误体翻成异常。

后端所有接口都挂在 `/api/v1` 下（见 fastapi-admin-backend 的
`app/core/config.py` 的 `API_V1_PREFIX`）；**成功**时直接返回模型本身，**出错**时
统一是 `{"code", "message", "data"}`（见后端 `app/core/exceptions.py`）。

**地址不写 127.0.0.1**：那是"跑代码的这台机器"，手机上（或另一台电脑上）跑起来
它指向的是设备自己，连不上任何东西。这里直接写部署好的域名，换环境只改这一处。

HTTP 用标准库 `urllib`（和 tools/version_check.py 检查新版本一个做法）：不引第三方
依赖 —— 这套 App 的依赖只有 flet / flet-charts，为了几个请求再挂一个 requests 不划算。
"""

import asyncio
import json
import logging
import mimetypes
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname

logger = logging.getLogger(__name__)

# 后端基址。两种改法，**本地调试推荐第一种**（不用改代码）：
#   1. 启动前设环境变量：`DAILYLIST_API_BASE=http://<本机IP>:8000/api/v1`
#      PowerShell 写法：`$env:DAILYLIST_API_BASE = "http://192.168.18.110:8000/api/v1"`
#   2. 直接改下面 `LOCAL_BASE_URL` 这一行。
#
# ⚠️ 本地调试三个易踩的点：
#   - **必须带端口号**：后端跑在 **8000**（后端 `app/core/config.py` 的 `PORT`，
#     `python run.py` 启动时也是它）。只写 `http://192.168.x.x/api/v1` 会去连 80
#     端口 —— 那就是 `[WinError 10061] 由于目标计算机积极拒绝，无法连接`。
#   - **IP 用局域网那个**（`ipconfig` 里与手机 / 模拟器同网段的），别写 127.0.0.1：
#     在手机或另一台机器上跑时，127.0.0.1 指的是**设备自己**。
#   - 后端要监听 0.0.0.0（默认就是），且**防火墙放行 8000 入站**，否则别的设备连不上。
LOCAL_BASE_URL = "http://192.168.18.110:8000/api/v1"
# 线上（已部署的域名，前面挂着 Cloudflare）。
REMOTE_BASE_URL = "https://fastapi.277686.xyz/api/v1"
BASE_URL = (os.environ.get("DAILYLIST_API_BASE") or "").strip() or LOCAL_BASE_URL
# 站点根地址（基址去掉 `/api/v1` 那一段）。后端返回的**静态资源 / 头像地址**是
# `/api/v1/static/...`、`/api/v1/assets/...` 这种相对路径（见后端
# `app/core/config.py` 的 `upload_url_prefix` 与 `DEFAULT_AVATAR`），
# 直接塞给 `ft.Image(src=)` 解析不出域名，要先拼上这个前缀。
SITE_URL = BASE_URL.removesuffix("/api/v1")
# 单次请求的超时（秒）：比后端自己的处理时间宽松一点，又不至于让人干等。
TIMEOUT = 15
# 上传图片的超时（秒）：比普通请求宽松得多。手机照片本来就有几 MB，选完图之后
# 客户端还要先把图传给 Python 这一侧、再往服务器传，走 WiFi 十几秒很常见 ——
# 用 `TIMEOUT`（15s）会让「图大一点就报错」，看着像接口坏了。
UPLOAD_TIMEOUT = 120
# 认证头的前缀：后端用的是 JWT，`Authorization: Bearer <token>`。
TOKEN_TYPE = "Bearer"
# 默认请求头。**User-Agent 必须是浏览器样子的**：域名前面挂着 Cloudflare，它按浏览器
# 指纹过滤（Error 1010: Access denied），urllib 默认的 `Python-urllib/3.x` 会被直接
# 403 —— 实测同一接口换浏览器 UA 就是 200。那个 403 是 Cloudflare 回的 JSON
# （`{"title": "Error 1010: Access denied", ...}`），不是后端的 `{code,message,data}`，
# 所以光看 App 只会得到一句兜底提示（见 `_error_from` 现在会把 title/detail 说出来）。
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
# 给用户看的错误文案最长的长度：后端自己的文案都很短，这条是防 Cloudflare / nginx
# 那种一整段英文说明把 toast 撑爆。
MAX_MESSAGE = 80
# 没有错误体（或错误体翻不出来）时按状态码给的兜底文案。
STATUS_MESSAGES = {
    400: "请求参数有误",
    401: "登录状态已失效，请重新登录",
    403: "没有权限访问",
    404: "接口不存在",
    422: "提交的内容不符合要求",
    429: "操作太频繁，请稍后再试",
    500: "服务器开小差了，请稍后再试",
    502: "服务器暂时不可用，请稍后再试",
    503: "服务维护中，请稍后再试",
}


class ApiError(Exception):
    """后端明确回过来的错误（4xx / 5xx）：`message` 就是给用户看的那句话。"""

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        # 后端的业务码（见 `_payload`），排查问题时有用。
        self.code = code
        # HTTP 状态码。
        self.status = status
        self.message = message


class NetworkError(ApiError):
    """连不上 / 超时 / 回的不是 JSON —— 一律翻成一句人话，不把底层细节抛给用户。"""


def _decode(raw: bytes) -> object:
    """把响应体解成 Python 对象；空的或不是 JSON 时返回 None。"""
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("响应不是 JSON: %r", raw[:200])
        return None


def _error_from(error: urllib.error.HTTPError) -> ApiError:
    """把 HTTPError 翻成 ApiError。

    消息按这个顺序找：后端信封的 `message`（422 时是「参数校验失败: email ...」，也是
    直接可展示的）→ 中间层给的 `title` / `detail`（Cloudflare 拦截页是
    `{"title": "Error 1010: Access denied", "detail": ...}`，nginx 是 `{"detail": ...}`
    —— 都不是后端回的，但把原因说出来远比一句「没有权限访问」有用）→ 按状态码兜底。
    """
    status = error.code
    code = None
    message = ""
    try:
        payload = _decode(error.read())
    except Exception:  # noqa: BLE001  读响应体失败不该盖掉真正的错误
        payload = None
    if isinstance(payload, dict):
        raw_code = payload.get("code")
        code = raw_code if isinstance(raw_code, int) else None
        for key in ("message", "title", "detail"):
            raw = payload.get(key)
            if isinstance(raw, str) and raw.strip():
                message = raw.strip()
                break
    if not message:
        message = STATUS_MESSAGES.get(status, f"请求失败（{status}）")
    if len(message) > MAX_MESSAGE:
        message = message[: MAX_MESSAGE - 1] + "…"
    logger.warning("接口返回 %s: %s", status, message)
    return ApiError(message, code=code, status=status)


def _request_sync(
    method: str,
    path: str,
    payload: dict | None,
    token: str | None,
) -> Any:
    """同步发一次请求（跑在工作线程里，见 `request`）。"""
    url = f"{BASE_URL}{path}"
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    # 浏览器样子的 User-Agent 等默认头（见 DEFAULT_HEADERS：少了它会被 Cloudflare 403）。
    for name, value in DEFAULT_HEADERS.items():
        request.add_header(name, value)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"{TOKEN_TYPE} {token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return _decode(response.read())
    except urllib.error.HTTPError as error:
        # HTTPError 要在 URLError 之前接：它俩是父子关系（HTTPError ⊂ URLError）。
        raise _error_from(error) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        logger.warning("%s %s 连接失败: %s", method, path, error)
        raise NetworkError("网络异常，请检查网络后重试") from error


async def request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    token: str | None = None,
) -> Any:
    """异步发一次请求。

    真正的网络调用丢进线程（`asyncio.to_thread`）—— Flet 的事件处理跑在事件循环上，
    在里面直接阻塞会把整个 UI 冻住（设置页「检查新版本」也是这么处理的）。

    `path` 是相对 `BASE_URL` 的路径，如 `/member/auth/login`。
    """
    return await asyncio.to_thread(_request_sync, method, path, payload, token)


async def get(path: str, *, token: str | None = None) -> Any:
    return await request("GET", path, token=token)


async def post(
    path: str, *, payload: dict | None = None, token: str | None = None
) -> Any:
    return await request("POST", path, payload=payload, token=token)


async def put(
    path: str, *, payload: dict | None = None, token: str | None = None
) -> Any:
    return await request("PUT", path, payload=payload, token=token)


async def delete(path: str, *, token: str | None = None) -> Any:
    """DELETE 用不上请求体：后端的删除接口都是只带路径。"""
    return await request("DELETE", path, token=token)


# ---------------------- 上传文件（multipart/form-data） ----------------------
# 只有「上传头像」用得上（`POST /member/profile/avatar`）：那个接口收的是
# `multipart/form-data`，字段名叫 `file`。urllib 没有现成的 multipart，按 RFC 7578
# 手写一个最简单的「只有一个文件字段」的请求体即可 —— 为这一处再引个依赖不划算。
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def resolve_local_path(path: str) -> Path | None:
    """把文件选择器给的 `path` 变成一个**真能读的本地路径**；认不出来返回 `None`。

    ⚠️ 各平台给的形态不一样，直接 `Path(path).read_bytes()` 会不时报「读不到选中的图片」：
    - 桌面 / 移动端：多半是**绝对本地路径**；
    - Web / 部分移动端：Flet 会先把文件传到服务端，给的常是**相对路径**、只有文件名、
      或 `file://` 开头的 URI —— 拿它直接读文件系统必然失败。

    所以这里按「原样 → 去 file:// → 相对 Flet 上传目录 / 当前目录（含 uploads 子目录）」
    逐个试，第一个真实存在的就是它。
    """
    raw = (path or "").strip()
    if not raw:
        return None

    candidates: list[Path] = [Path(raw)]
    if raw.lower().startswith("file://"):
        try:
            candidates.append(Path(url2pathname(urlparse(raw).path)))
        except ValueError:  # pragma: no cover - 畸形 URI
            pass
    if not Path(raw).is_file():
        roots = [
            os.environ.get("FLET_APP_STORAGE_DATA") or "",
            os.environ.get("FLET_APP_STORAGE_TEMP") or "",
            os.getcwd(),
        ]
        name = Path(raw).name
        for root in roots:
            if not root:
                continue
            candidates.append(Path(root) / raw)
            candidates.append(Path(root) / name)
            candidates.append(Path(root) / "uploads" / name)

    for item in candidates:
        try:
            if item.is_file():
                return item
        except OSError:  # pragma: no cover - 非法路径字符等
            continue
    logger.warning("选中的文件读不到: %r（试过 %s）", raw, [str(c) for c in candidates])
    return None


def _multipart_body(field: str, filename: str, content: bytes) -> tuple[bytes, str]:
    """拼出单文件 multipart 请求体，并返回（请求体, Content-Type）。"""
    boundary = f"----dailylist{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    # ⚠️ 换行必须是 CRLF（`\r\n`）：HTTP 的 multipart 就这么规定的，写 `\n` 后端解不出边界。
    body = bytearray()
    body += f"--{boundary}\r\n".encode("utf-8")
    body += (
        f'Content-Disposition: form-data; name="{field}"; '
        f'filename="{filename}"\r\n'
    ).encode("utf-8")
    body += f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
    body += content
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def _post_bytes_sync(
    path: str,
    filename: str,
    content: bytes,
    field: str,
    token: str | None,
) -> Any:
    """同步把**已经在内存里的**文件内容上传（跑在工作线程里，见 `post_bytes`）。"""
    if not content:
        raise ApiError("选中的文件是空的")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ApiError(f"图片不能超过 {MAX_UPLOAD_BYTES // 1024 // 1024} MB")

    body, content_type = _multipart_body(field, filename or "upload", content)
    request = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, method="POST"
    )
    for name, value in DEFAULT_HEADERS.items():
        request.add_header(name, value)
    request.add_header("Content-Type", content_type)
    if token:
        request.add_header("Authorization", f"{TOKEN_TYPE} {token}")
    try:
        with urllib.request.urlopen(request, timeout=UPLOAD_TIMEOUT) as response:
            return _decode(response.read())
    except urllib.error.HTTPError as error:
        raise _error_from(error) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        logger.warning("POST %s 上传失败: %s", path, error)
        raise NetworkError("图片上传超时或网络中断，请重试") from error


async def post_bytes(
    path: str,
    content: bytes,
    *,
    filename: str = "upload",
    field: str = "file",
    token: str | None = None,
) -> Any:
    """上传**内存里的文件内容**（`multipart/form-data`），字段默认叫 `file`。

    ⚠️ 这是上传的**首选**：Flet 的文件选择器在 `with_data=True` 时会直接把文件内容
    带回来（`FilePickerFile.bytes`），**不碰文件系统** —— 而 `path` 在 Web 模式下永远
    是 `None`、部分原生平台也拿不到（见 `resolve_local_path` 上面那段说明），
    直接按路径读就会「读不到选中的图片」。

    `filename` 要带后缀：后端靠它判断图片格式。
    """
    return await asyncio.to_thread(
        _post_bytes_sync, path, filename, content, field, token
    )


async def post_file(
    path: str,
    file_path: str,
    *,
    filename: str = "",
    field: str = "file",
    token: str | None = None,
) -> Any:
    """上传一个**磁盘上的文件**（`multipart/form-data`）。

    只在拿不到文件内容（比如某个平台不给 `bytes`）时才走这一条：`file_path` 会被
    `resolve_local_path` 兜底找一遍，找不到就抛「读不到选中的图片」。
    `filename` 不传就用原文件名 —— 后端靠它的后缀判断图片格式，所以别传空。
    """
    target = resolve_local_path(file_path)
    if target is None:
        raise NetworkError("读不到选中的图片，请重新选一张")
    try:
        content = target.read_bytes()
    except OSError as error:
        logger.warning("读不到要上传的文件 %s: %s", target, error)
        raise NetworkError("读不到选中的图片，请重新选一张") from error
    return await post_bytes(
        path,
        content,
        filename=filename or target.name,
        field=field,
        token=token,
    )
