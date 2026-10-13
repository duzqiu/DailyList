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
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# 后端基址。换环境（本地 / 测试 / 生产）只动这一行。
BASE_URL = "https://fastapi.277686.xyz/api/v1"
# 单次请求的超时（秒）：比后端自己的处理时间宽松一点，又不至于让人干等。
TIMEOUT = 15
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
