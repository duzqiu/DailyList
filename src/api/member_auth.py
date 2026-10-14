"""用户中心 · 认证接口（后端前缀 `/member/auth`，全部是公开接口）。

对应后端 fastapi-admin-backend：
- `app/api/v1/endpoints/member_auth.py`  路由
- `app/schemas/member.py`                注册 / 登录 / 重置密码的入参，会员出参
- `app/schemas/email.py`                 send-code 的入参 / 出参
- `app/schemas/auth.py`                  Token

每个函数对应一个接口，**参数名与后端字段保持一致**（后端改了字段这边跟着改）。这里
只管"发什么、收什么"：界面上的校验与提示留在页面里，出错统一抛 `client.ApiError`。
"""

import time

from . import session
from .client import get, post

# 验证码场景（后端 `EmailScene`）：注册用 register，重置密码用 reset_password。
SCENE_REGISTER = "register"
SCENE_RESET_PASSWORD = "reset_password"

# ---------------------- 当前会员的缓存 ----------------------
# 「我的」页、登录页都会拿一次当前会员；原来每进一次页面就打一次接口（还要闪一下骨架）。
# 这里存一份：
# - **按令牌存**：登录 / 退出 / 刷新令牌都会换掉令牌，键跟着变，天然就作废了，不用手动清；
# - 有**有效期**（`ME_CACHE_TTL` 秒）：过期后下次进入会重新拉一遍，数据不会永远停在老样子。
#   想让它一直有效就调大，想每次进页面都重拉就设 0（等于关掉缓存）。
ME_CACHE_TTL = 600
# 只留**当前令牌**这一份（换过令牌的老条目会被顺手清掉，不会无限攒）。
_ME_CACHE: dict[str, tuple[float, dict]] = {}


async def send_code(email: str, scene: str = SCENE_REGISTER) -> dict:
    """发送邮箱验证码（`POST /member/auth/send-code`）。

    出参 `{email, scene, sent, expires_in, resend_after, debug_code}`：
    `sent=False` 表示后端没配 SMTP（没真发）；`resend_after` 是再过多少秒才能重发；
    `debug_code` 只在后端开了 `EMAIL_CODE_DEBUG_RETURN` 时回显验证码（联调用）。
    """
    return await post(
        "/member/auth/send-code", payload={"email": email, "scene": scene}
    )


async def register(
    email: str, code: str, password: str, confirm_password: str
) -> dict:
    """邮箱验证码注册（`POST /member/auth/register`），返回新会员。

    密码规则由后端把关（6-64 位、需同时含字母和数字），不符合会抛 `ApiError`；
    注册成功后邮箱即视为已验证，昵称与头像由后端给默认值。
    """
    return await post(
        "/member/auth/register",
        payload={
            "email": email,
            "code": code,
            "password": password,
            "confirm_password": confirm_password,
        },
    )


async def login(email: str, password: str) -> dict:
    """邮箱密码登录（`POST /member/auth/login`），返回令牌 `Token`。

    成功后**顺手把令牌存到本地**（见 `session`）—— 页面不用自己管这件事。令牌是
    `scope=member` 的，只能访问用户中心接口。
    """
    token = await post(
        "/member/auth/login", payload={"email": email, "password": password}
    )
    session.save(token)
    return token


async def refresh() -> dict:
    """用本地的 refresh_token 换一套新令牌（`POST /member/auth/refresh`）。"""
    token = await post(
        "/member/auth/refresh",
        payload={"refresh_token": session.refresh_token()},
    )
    session.save(token)
    return token


async def reset_password(
    email: str, code: str, new_password: str, confirm_password: str
) -> dict:
    """忘记密码（`POST /member/auth/reset-password`），返回 `{message, detail}`。

    密码规则同样由后端把关；验证码要用 `scene=reset_password` 那次发出的。
    """
    return await post(
        "/member/auth/reset-password",
        payload={
            "email": email,
            "code": code,
            "new_password": new_password,
            "confirm_password": confirm_password,
        },
    )


def cached_me() -> dict | None:
    """**同步**看一眼缓存里的会员信息；没有 / 过期就是 `None`（不打接口）。

    构建页面时用它：命中就**直接摆真数据**，连骨架都不用闪（见 widgets/settings_card.py）。
    """
    token = session.access_token()
    if not token:
        return None
    hit = _ME_CACHE.get(token)
    if hit is None:
        return None
    saved_at, user = hit
    if ME_CACHE_TTL and time.monotonic() - saved_at >= ME_CACHE_TTL:
        return None
    return user


def forget_me(token: str | None = None) -> None:
    """把缓存丢掉（`token` 不传就全清）。退出登录时清一下，免得留着没用的条目。"""
    if token is None:
        _ME_CACHE.clear()
    else:
        _ME_CACHE.pop(token, None)


async def me(use_cache: bool = True) -> dict:
    """当前登录会员（`GET /member/auth/me`，返回 `MemberOut`）。

    没登录、或令牌过期时抛 401 的 `ApiError`。

    `use_cache=True`（默认）先看缓存：同一个令牌、且没过期就直接返回，**不再打接口**；
    拉回来的结果也会存进缓存。要强制重拉传 `use_cache=False`。
    """
    token = session.access_token()
    if use_cache:
        hit = cached_me()
        if hit is not None:
            return hit
    user = await get("/member/auth/me", token=token)
    if token:
        # 只留这一份（见 `_ME_CACHE` 的说明）。
        _ME_CACHE.clear()
        _ME_CACHE[token] = (time.monotonic(), user)
    return user


async def logout() -> dict:
    """退出登录（`POST /member/auth/logout`）。

    后端是无状态 JWT，它那边只是应一声；真正要紧的是把本地令牌清掉，所以放在
    `finally` 里 —— 就算请求失败，本地也算退出了。
    """
    token = session.access_token()
    try:
        return await post("/member/auth/logout", token=token)
    finally:
        session.clear()
        # 退出后这条令牌作废了，缓存的会员信息也一并丢掉。
        forget_me(token)
