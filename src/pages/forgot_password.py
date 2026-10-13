"""忘记密码页：登录页底部「忘记密码」进来的三级页。

字段是账号 / 验证码 / 新密码 / 确认新密码，点「重置密码」只做「非空 + 两次新密码一致」
的校验，通过就 toast 一句 —— 没有发验证码、没有写库，所以这一页同样**没有任何 db
调用**。「获取验证码」也只是把按钮文案换成「重新发送」+ 提示一句，让人看出点过了。

卡片下面那行「想起来了？返回登录」直接 `go_back()`，回到进来时的登录页。

壳子、卡片、字段、主按钮、验证码行都来自 tools/auth_form.py（和登录页、注册页共用
一套），这一页只管「有哪些字段、点了做什么」。
"""

from collections.abc import Callable

import flet as ft

from tools.auth_form import (
    build_auth_card,
    build_auth_field,
    build_auth_page,
    build_card_heading,
    build_code_row,
    build_field_box,
    build_link_row,
    build_primary_button,
    mark_code_sent,
)
from tools.toast import build_toast


def build_forgot_password_page(
    page: ft.Page, go_back: Callable[[], None]
) -> ft.Control:
    """忘记密码页。`go_back` 由 pages/navigation.py 给，回的是登录页那一层。"""

    def notify(message: str) -> None:
        """一句话的提示：走 tools/toast.py，浮在屏幕中间。"""
        page.show_dialog(build_toast(page, message))

    account_field = build_auth_field("请输入用户名或邮箱")
    code_field = build_auth_field("请输入验证码")
    password_field = build_auth_field("请输入新密码", password=True)
    confirm_field = build_auth_field("请再次输入新密码", password=True)

    def send_code(_: ft.Event[ft.Control]) -> None:
        """收到账号后发验证码：校验账号 → 换按钮文案 → 提示一句（不真的发）。"""
        if not (account_field.value or "").strip():
            notify("请先输入用户名或邮箱")
            return
        mark_code_sent(send_button)
        notify("验证码已发送（演示）")

    # 验证码那一行（输入框 + 获取验证码）由 auth_form 给，和注册页同一个长相。
    code_row, send_button = build_code_row(code_field, send_code)

    def submit(_: ft.Event[ft.Control]) -> None:
        """只校验非空和两次新密码一致，不落库、不发请求。"""
        if not (account_field.value or "").strip():
            notify("请输入用户名或邮箱")
            return
        if not (code_field.value or "").strip():
            notify("请输入验证码")
            return
        if not (password_field.value or "").strip():
            notify("请输入新密码")
            return
        if (password_field.value or "") != (confirm_field.value or ""):
            notify("两次输入的密码不一致")
            return
        notify("密码已重置（演示）")

    card = build_auth_card(
        [
            build_card_heading("重置密码"),
            build_field_box(account_field),
            code_row,
            build_field_box(password_field),
            build_field_box(confirm_field),
            build_primary_button("重置密码", submit),
        ]
    )

    # 只有一个链接：直接返回登录页，不另压一层。
    links = build_link_row([("想起来了？返回登录", lambda _: go_back())])

    return build_auth_page(page, "忘记密码", go_back, [card, links])
