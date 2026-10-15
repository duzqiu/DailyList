"""用户中心 · 资料接口（后端 `/member/profile`，全部要会员令牌）。

对应后端 fastapi-admin-backend：
- `app/api/v1/endpoints/member_profile.py`  路由
- `app/schemas/member.py`                  `MemberProfileUpdate` / `MemberOut` / `AvatarUploadOut`
- `app/models/member.py`                   `MemberGender`（unknown / male / female）

资料（昵称 / 简介 / 性别 / 生日 / 地区 / 头像）**全部以后端为准**，本地不留副本：
- 读：`GET /member/profile`，登录成功后拉一次（见 pages/login.py），结果缓存一会儿；
- 改：`PUT /member/profile`，只传改了的字段（后端「未传的字段保持原值」）；
- 头像：`POST /member/profile/avatar`（multipart，字段名 `file`）—— 后端按**会员 ID**
  建目录存（`data/uploads/avatars/{会员ID}/`），返回的 `url` 直接写进资料里，
  读的时候用出参里的 `avatar_url`（可直接当图片地址用）。

App 内部性别一直是中文（「男 / 女 / 保密」），所以收发两端各做一次映射
（同 member_countdowns.py 里周期那套）。
"""

import asyncio
import os
import time
from typing import Any

from tools import image_prep

from . import member_auth, session
from .client import SITE_URL, ApiError, get, post_bytes, post_file, put

# 性别：App 的中文 ↔ 后端的 `MemberGender`。
GENDERS = ("男", "女", "保密")
GENDER_TO_API: dict[str, str] = {"男": "male", "女": "female", "保密": "unknown"}
GENDER_FROM_API: dict[str, str] = {value: key for key, value in GENDER_TO_API.items()}
# 资料里没性别（或后端加了新取值）时按「保密」显示。
DEFAULT_GENDER = "保密"

# 简介没填过时那行浅灰占位（照小红书那版）。
INTRO_HINT = "介绍一下自己"

# ---------------------- 资料缓存 ----------------------
# 「我的」页、账号卡片、编辑资料页都要读资料，没必要每进一次就打一次接口。
# 和 member_auth 那份会员缓存一个做法：**按令牌存**（换令牌自动作废）+ **有有效期**。
PROFILE_CACHE_TTL = 600
_PROFILE_CACHE: dict[str, tuple[float, dict]] = {}


def cached_profile() -> dict | None:
    """**同步**看一眼缓存里的资料；没有 / 过期就是 `None`（不打接口）。

    资料还没拉过时**退回认证层那份会员缓存**（`GET /member/auth/me` 给的也是
    `MemberOut`，字段一模一样）—— 这样刚进页面也有头像 / 昵称可用。
    """
    token = session.access_token()
    if not token:
        return None
    hit = _PROFILE_CACHE.get(token)
    if hit is not None:
        saved_at, profile = hit
        if not PROFILE_CACHE_TTL or time.monotonic() - saved_at < PROFILE_CACHE_TTL:
            return profile
    return member_auth.cached_me()


def remember(profile: dict) -> dict:
    """把资料存进缓存（只留当前令牌这一份）。"""
    token = session.access_token()
    if token:
        _PROFILE_CACHE.clear()
        _PROFILE_CACHE[token] = (time.monotonic(), profile)
        # 认证层那份会员缓存里的昵称 / 头像也过时了，丢掉让它下次重拉。
        member_auth.forget_me(token)
    return profile


def forget_profile(token: str | None = None) -> None:
    """丢掉缓存（`token` 不传就全清）：退出登录时用。"""
    if token is None:
        _PROFILE_CACHE.clear()
    else:
        _PROFILE_CACHE.pop(token, None)


def background_url(profile: dict | None = None) -> str:
    """资料的背景图地址 → **可以直接给 `ft.Image(src=)` 的绝对地址**。

    和头像同一套规则（后端按会员 ID 存 `backgrounds/{会员ID}/`）；区别是**背景没有
    默认图**：没上传过时后端给的 `background_url` 是空串，这里也就返回空串 ——
    页面按「不铺背景图」处理（见 widgets/my_background.py）。
    """
    return _absolute_media_url(profile, "background_url", "background")


def avatar_url(profile: dict | None = None) -> str:
    """资料的头像地址 → **可以直接给 `ft.Image(src=)` 的绝对地址**。

    后端给的 `avatar_url` 是 `/api/v1/static/...` 这种相对路径（没上传过时是默认头像
    `/api/v1/assets/default-avatar.svg`），要拼上站点地址才是一个完整 URL。
    """
    return _absolute_media_url(profile, "avatar_url", "avatar")


def _absolute_media_url(profile: dict | None, url_key: str, field_key: str) -> str:
    """`avatar_url` / `background_url` → 完整 URL（相对路径拼上站点根地址）。"""
    data = profile if profile is not None else cached_profile()
    if not isinstance(data, dict):
        return ""
    raw = str(data.get(url_key) or data.get(field_key) or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if not raw.startswith("/"):
        return raw
    return f"{SITE_URL}{raw}"


async def get_profile(use_cache: bool = True) -> dict:
    """我的资料（`GET /member/profile`，返回 `MemberOut`）。

    `use_cache=True`（默认）命中缓存就直接返回；要强制重拉传 `False`（改完资料、
    刚登录时就是这么用的）。
    """
    if use_cache:
        hit = cached_profile()
        if hit is not None:
            return hit
    profile = await get("/member/profile", token=session.access_token())
    if isinstance(profile, dict):
        return remember(profile)
    return {}


async def update_profile(**fields: str | None) -> dict:
    """改资料（`PUT /member/profile`），返回改后的 `MemberOut`。

    **只传要改的字段**（值为 `None` 的会被丢掉），后端对没传的字段保持原值：
    `update_profile(region="杭州")` 就只改地区。可改：
    `nickname` / `avatar` / `gender` / `birthday` / `phone` / `bio` / `region`。

    性别传中文也行（这里换成后端那套英文枚举），生日传 `YYYY-MM-DD`。
    """
    payload: dict[str, str] = {}
    gender = fields.pop("gender", None)
    if gender is not None:
        payload["gender"] = GENDER_TO_API.get(str(gender), "unknown")
    for name, value in fields.items():
        if value is None:
            continue
        payload[name] = str(value)
    profile = await put("/member/profile", payload=payload, token=session.access_token())
    if isinstance(profile, dict):
        return remember(profile)
    return {}


async def upload_avatar(picked: Any) -> dict:
    """上传头像（`POST /member/profile/avatar`，multipart 字段名 `file`）。

    `picked` 是文件选择器（`ft.FilePicker.pick_files(with_data=True)`）给回来的
    `FilePickerFile`；也接受路径字符串兜底。

    ⚠️ **优先用 `picked.bytes`（文件内容），不要去读 `picked.path`**：
    `FilePickerFile.path` 在 **Web 模式永远是 `None`**，部分原生平台也拿不到；
    只有调 `pick_files(..., with_data=True)` 才会把内容带回来（见
    `api/client.py` 的 `post_bytes`）。所以编辑资料页选图时必须带 `with_data=True`。

    后端按**会员 ID** 存：`data/uploads/avatars/{会员ID}/avatar_{会员ID}_{随机串}.{ext}`，
    同一个会员目录里只留最新这张。上传成功后**再拉一次资料并返回它**（`MemberOut`）：
    这样 `avatar_url` 立刻就是新的，页面直接重画即可（文件名带随机串，不会命中旧缓存）。
    """
    return await _upload_media(picked, "/member/profile/avatar", "avatar.jpg")


async def upload_background(picked: Any) -> dict:
    """上传背景图（`POST /member/profile/background`）—— **与头像完全同一套规则**。

    `picked` 同上（`FilePickerFile`，务必 `with_data=True`）。后端按会员 ID 存
    `data/uploads/backgrounds/{会员ID}/background_{会员ID}_{随机串}.{ext}`，
    覆盖上传只留最新这张；成功后同样返回**刷新的资料**（`background_url` 已是新地址）。
    """
    return await _upload_media(
        picked, "/member/profile/background", "background.jpg"
    )


async def _upload_media(picked: Any, endpoint: str, default_filename: str) -> dict:
    """图片上传的公共部分：压图 → 取内容 → 组 multipart → 成功后刷新资料缓存。

    **先压缩再上传**（见 tools/image_prep.py）：手机照片几 MB，不压的话又慢又容易
    撞后端的 5MB 上限/超时。压不了（动图 / 没 Pillow / 压完更大）就按原图传。
    """
    token = session.access_token()
    file_path = ""
    if isinstance(picked, str):
        file_path = picked
    else:
        file_path = str(getattr(picked, "path", "") or "")

    # 压图要解码/编码整张图（几千万像素时能到一两秒），丢到线程里做 ——
    # 直接在协程里跑会把事件循环卡住，Flet 会话看着就像「卡死 / 重启」。
    content, filename = await asyncio.to_thread(image_prep.prepare, picked)

    if content:
        result = await post_bytes(
            endpoint,
            content,
            filename=filename or default_filename,
            token=token,
        )
    elif file_path:
        # 兜底：这个平台只给了路径，没给内容。
        result = await post_file(
            endpoint,
            file_path,
            filename=filename or os.path.basename(file_path),
            token=token,
        )
    else:
        raise ApiError("没有拿到图片内容，请重新选一张")
    if isinstance(result, dict) and result.get("url"):
        # 上传接口只回地址，资料的完整样子再拉一次（顺带把 *_url 算好）。
        return await get_profile(use_cache=False)
    return result if isinstance(result, dict) else {}
