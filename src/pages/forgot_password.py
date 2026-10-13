"""忘记密码页：登录页底部「忘记密码」进来的三级页。

字段是邮箱 / 验证码 / 新密码 / 确认新密码。「获取验证码」调
`POST /member/auth/send-code`（`scene=reset_password`，后端要求该邮箱已注册），
点「重置密码」调 `POST /member/auth/reset-password`（见 api/member_auth.py）；
密码强度（6-64 位、含字母和数字）由后端把关，报错原样提示。

验证码按钮点过之后锁一段时间（按后端返回的 `resend_after`，没给才用默认 60 秒），
期间点了不响应 —— 见 tools/auth_form.py 的 `start_code_countdown`。

卡片下面那行「想起来了？返回登录」直接 `go_back()`，回到进来时的登录页；**重置成功后
也走同一条路**：先回登录页，提示沿用后端回的那句话（「密码重置成功，请使用新密码登录」）。

壳子、卡片、字段、主按钮、验证码行都来自 tools/auth_form.py（和登录页、注册页共用
一套），这一页只管「有哪些字段、点了做什么」。
"""

from collections.abc import Callable

import flet as ft

from api import member_auth
from api.client import ApiError
from tools.auth_form import (
    build_auth_card,
    build_auth_field,
    build_auth_page,
    build_card_heading,
    build_code_row,
    build_field_box,
    build_link_row,
    build_primary_button,
    code_sent_message,
    lock_code_button,
    release_code_button,
    start_code_countdown,
)
from tools.toast import build_toast


def build_forgot_password_page(
    page: ft.Page, go_back: Callable[[], None]
) -> ft.Control:
    """忘记密码页。`go_back` 由 pages/navigation.py 给，回的是登录页那一层。"""

    def notify(message: str) -> None:
        """一句话的提示：走 tools/toast.py，浮在屏幕中间。"""
        page.show_dialog(build_toast(page, message))

    email_field = build_auth_field("请输入邮箱")
    code_field = build_auth_field("请输入验证码")
    password_field = build_auth_field("请输入新密码", password=True)
    confirm_field = build_auth_field("请再次输入新密码", password=True)

    async def do_send_code() -> None:
        """带请求的那半：邮箱有没有填，`on_send` 里已经同步判过了。"""
        email = (email_field.value or "").strip()
        try:
            result = await member_auth.send_code(
                email, member_auth.SCENE_RESET_PASSWORD
            )
        except ApiError as error:
            # 没发成（邮箱未注册、太频繁……）：解锁，让人改完再来一次。
            release_code_button(send_button)
            notify(error.message)
            return
        start_code_countdown(page, send_button, result)
        notify(code_sent_message(result))

    def on_send(_: ft.Event[ft.Control]) -> None:
        """点「获取验证码」：本地先判空，**再上锁**，最后发请求（同上锁的道理见
        `lock_code_button`）。"""
        if not (email_field.value or "").strip():
            notify("请输入邮箱")
            return
        lock_code_button(send_button)
        page.run_task(do_send_code)

    # 验证码那一行（输入框 + 获取验证码）由 auth_form 给，和注册页同一个长相。
    code_row, send_button = build_code_row(code_field, on_send)

    async def do_reset() -> None:
        """带请求的那半：交给 `page.run_task` 跑（见 submit）。"""
        email = (email_field.value or "").strip()
        code = (code_field.value or "").strip()
        password = password_field.value or ""
        confirm = confirm_field.value or ""
        if not email:
            notify("请输入邮箱")
            return
        if not code:
            notify("请输入验证码")
            return
        if not password:
            notify("请输入新密码")
            return
        if password != confirm:
            notify("两次输入的密码不一致")
            return
        try:
            result = await member_auth.reset_password(
                email, code, password, confirm
            )
        except ApiError as error:
            notify(error.message)
            return
        # 后端会回一句「密码重置成功，请使用新密码登录」（MessageResponse）。
        message = result.get("message") if isinstance(result, dict) else None
        # 重置成功：回上一层（登录页），让人用新密码登录；提示压在登录页上。
        go_back()
        notify(message or "密码重置成功，请使用新密码登录")

    def submit(_: ft.Event[ft.Control]) -> None:
        page.run_task(do_reset)

    card = build_auth_card(
        [
            build_card_heading("重置密码"),
            build_field_box(email_field),
            code_row,
            build_field_box(password_field),
            build_field_box(confirm_field),
            build_primary_button("重置密码", submit),
        ]
    )

    # 只有一个链接：直接返回登录页，不另压一层。
    links = build_link_row([("想起来了？返回登录", lambda _: go_back())])

    return build_auth_page(page, "忘记密码", go_back, [card, links])
