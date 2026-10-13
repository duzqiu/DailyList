"""注册新账号页：登录页底部「注册新账号」进来的三级页。

字段是邮箱 / 邮箱验证码（右边一枚「获取验证码」）/ 密码 / 确认密码 —— 和忘记密码页
同一套（那边是账号 / 验证码 / 新密码 / 确认新密码），两页看起来是一回事。点「注册」
只做「非空 + 邮箱含 @ + 两次密码一致」的校验，通过就 toast 一句 —— 没有写库、没有发
邮件，所以这一页同样**没有任何 db 调用**；「获取验证码」也只是把按钮文案换成
「重新发送」+ 提示一句，让人看出点过了。

卡片下面那行「已有账号？去登录」直接 `go_back()`，回到进来时的登录页（返回走的是
和别的页同一套 `nav_stack + page.views`，所以顶栏「‹ 返回」、整页左滑、真机返回键
三处行为一致）。

壳子、卡片、字段、主按钮、验证码行都来自 tools/auth_form.py（和登录页、忘记密码页
共用一套），这一页只管「有哪些字段、点了做什么」。
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

    def email_filled() -> bool:
        """邮箱这一格填了、而且像个邮箱（只判有没有 @，别的规则等接了真的再说）。"""
        return "@" in (email_field.value or "")

    def send_code(_: ft.Event[ft.Control]) -> None:
        """收到邮箱后发验证码：校验邮箱 → 换按钮文案 → 提示一句（不真的发）。"""
        if not email_filled():
            notify("请先输入正确的邮箱")
            return
        mark_code_sent(send_button)
        notify("邮箱验证码已发送（演示）")

    # 验证码那一行（输入框 + 获取验证码）由 auth_form 给，和忘记密码页同一个长相。
    code_row, send_button = build_code_row(code_field, send_code)

    def submit(_: ft.Event[ft.Control]) -> None:
        """只校验非空、邮箱格式和两次密码一致，不落库、不发请求。"""
        if not email_filled():
            notify("请先输入正确的邮箱")
            return
        if not (code_field.value or "").strip():
            notify("请输入邮箱验证码")
            return
        if not (password_field.value or "").strip():
            notify("请输入密码")
            return
        if (password_field.value or "") != (confirm_field.value or ""):
            notify("两次输入的密码不一致")
            return
        notify("注册成功（演示）")

    card = build_auth_card(
        [
            # 注册页不带头像：头像那张图是「我的」入口的标识，留给登录页。
            build_card_heading("创建账号"),
            build_field_box(email_field),
            code_row,
            build_field_box(password_field),
            build_field_box(confirm_field),
            build_primary_button("注册", submit),
        ]
    )

    # 只有一个链接：直接返回登录页，不另压一层。
    links = build_link_row([("已有账号？去登录", lambda _: go_back())])

    return build_auth_page(page, "注册", go_back, [card, links])
