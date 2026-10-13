"""用户中心 · 认证接口（后端前缀 `/member/auth`，全部是公开接口）。

对应后端 fastapi-admin-backend：
- `app/api/v1/endpoints/member_auth.py`  路由
- `app/schemas/member.py`                注册 / 登录 / 重置密码的入参，会员出参
- `app/schemas/email.py`                 send-code 的入参 / 出参
- `app/schemas/auth.py`                  Token

每个函数对应一个接口，**参数名与后端字段保持一致**（后端改了字段这边跟着改）。这里
只管"发什么、收什么"：界面上的校验与提示留在页面里，出错统一抛 `client.ApiError`。
"""

from . import session
from .client import get, post

# 验证码场景（后端 `EmailScene`）：注册用 register，重置密码用 reset_password。
SCENE_REGISTER = "register"
SCENE_RESET_PASSWORD = "reset_password"


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


async def me() -> dict:
    """当前登录会员（`GET /member/auth/me`，返回 `MemberOut`）。

    没登录、或令牌过期时抛 401 的 `ApiError`。
    """
    return await get("/member/auth/me", token=session.access_token())


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
