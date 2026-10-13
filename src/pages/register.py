"""注册新账号页：登录页底部「注册新账号」进来的三级页。

字段是邮箱 / 邮箱验证码 / 密码 / 确认密码 —— 和忘记密码页同一套（那边是账号 / 验证码
/ 新密码 / 确认新密码）。「获取验证码」调 `POST /member/auth/send-code`
（`scene=register`），点「注册」调 `POST /member/auth/register`（见
api/member_auth.py）；密码强度（6-64 位、含字母和数字）由后端把关，报错原样提示。

验证码按钮点过之后锁一段时间（按后端返回的 `resend_after`，没给才用默认 60 秒），
期间点了不响应 —— 见 tools/auth_form.py 的 `start_code_countdown`。

卡片下面那行「已有账号？去登录」直接 `go_back()`，回到进来时的登录页；**注册成功后
也走同一条路**：先回登录页，再提示一句「注册成功，请登录」。

壳子、卡片、字段、主按钮、验证码行都来自 tools/auth_form.py（和登录页、忘记密码页
共用一套），这一页只管「有哪些字段、点了做什么」。
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


def build_register_page(
    page: ft.Page, go_back: Callable[[], None]
) -> ft.Control:
    """注册页。`go_back` 由 pages/navigation.py 给，回的是登录页那一层。"""

    def notify(message: str) -> None:
        """一句话的提示：走 tools/toast.py，浮在屏幕中间。"""
        page.show_dialog(build_toast(page, message))

    email_field = build_auth_field("请输入邮箱")
    code_field = build_auth_field("请输入邮箱验证码")
    password_field = build_auth_field("请输入密码", password=True)
    confirm_field = build_auth_field("请再次输入密码", password=True)

    async def do_send_code() -> None:
        """带请求的那半：邮箱有没有填，`on_send` 里已经同步判过了。"""
        email = (email_field.value or "").strip()
        try:
            result = await member_auth.send_code(
                email, member_auth.SCENE_REGISTER
            )
        except ApiError as error:
            # 没发成（邮箱已注册、太频繁……）：解锁，让人改完再来一次。
            release_code_button(send_button)
            notify(error.message)
            return
        # 倒计时按后端返回的重发间隔走；提示里会把调试验证码（如果后端回显了）念出来。
        start_code_countdown(page, send_button, result)
        notify(code_sent_message(result))

    def on_send(_: ft.Event[ft.Control]) -> None:
        """点「获取验证码」：本地先判空（不值得为它发一次请求），**再上锁**，最后发请求。

        上锁必须在发请求之前（见 `lock_code_button`），否则这几百毫秒里连点几下就
        会发出几次请求。
        """
        if not (email_field.value or "").strip():
            notify("请输入邮箱")
            return
        lock_code_button(send_button)
        page.run_task(do_send_code)

    # 验证码那一行（输入框 + 获取验证码）由 auth_form 给，和忘记密码页同一个长相。
    code_row, send_button = build_code_row(code_field, on_send)

    async def do_register() -> None:
        """带请求的那半：交给 `page.run_task` 跑（见 submit）。"""
        email = (email_field.value or "").strip()
        code = (code_field.value or "").strip()
        password = password_field.value or ""
        confirm = confirm_field.value or ""
        if not email:
            notify("请输入邮箱")
            return
        if not code:
            notify("请输入邮箱验证码")
            return
        if not password:
            notify("请输入密码")
            return
        if password != confirm:
            notify("两次输入的密码不一致")
            return
        try:
            await member_auth.register(email, code, password, confirm)
        except ApiError as error:
            notify(error.message)
            return
        # 注册成功：回上一层（就是登录页 —— 这一页是从它进来的），提示压在登录页上。
        go_back()
        notify("注册成功，请登录")

    def submit(_: ft.Event[ft.Control]) -> None:
        page.run_task(do_register)

    card = build_auth_card(
        [
            # 三页的标题都不带头像，统一贴在卡片左上角（见 tools/auth_form.py）。
            build_card_heading("注册"),
            build_field_box(email_field),
            code_row,
            build_field_box(password_field),
            build_field_box(confirm_field),
            build_primary_button("注册", submit),
        ]
    )

    # 只有一个链接：直接返回登录页，不另压一层。
    links = build_link_row([("已有账号？去登录", lambda _: go_back())])

    return build_auth_page(page, go_back, [card, links])
