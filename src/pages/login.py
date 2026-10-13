"""登录页：日历页右上角那枚 person 图标进来的二级页。

字段是用户名 / 密码，点「登录」只做非空校验，通过就 toast 一句 —— 还没有接鉴权
（没有接口、没有本地账号表，也没有登录态保存），所以这一页里**没有任何 db 调用**。
底部「忘记密码 / 注册新账号」两个链接进的是**三级页**（压进 page.views 的第 2 层，
见 pages/register.py 与 pages/forgot_password.py）；从那儿返回回到的是这一页。

壳子、卡片、字段、主按钮、底部链接都来自 tools/auth_form.py（和注册页、忘记密码页
共用一套，见那份文件的说明），这一页只负责「有哪些字段、点了做什么」。
"""

from collections.abc import Callable

import flet as ft

from tools.auth_form import (
    build_auth_card,
    build_auth_field,
    build_auth_page,
    build_card_heading,
    build_field_box,
    build_link_row,
    build_primary_button,
)
from tools.layout import PERSON_ICON_SRC
from tools.toast import build_toast


def build_login_page(
    page: ft.Page,
    go_back: Callable[[], None],
    open_register: Callable[[], None],
    open_forgot: Callable[[], None],
) -> ft.Control:
    """登录页。

    `go_back` / `open_register` / `open_forgot` 都由 pages/navigation.py 给：
    「‹ 返回」、整页左滑、真机返回键共用 `go_back`；两个链接分别进注册页、忘记密码页。
    """

    def notify(message: str) -> None:
        """一句话的提示：走 tools/toast.py，浮在**屏幕中间**（和设置页的提示同一个做法）。"""
        page.show_dialog(build_toast(page, message))

    # 字段对象要留着读值（`build_auth_field` 给控件本体，`build_field_box` 只是把它
    # 套进那圈细边里，两者分开是为了这一层还能拿到 TextField）。
    username_field = build_auth_field("请输入用户名")
    password_field = build_auth_field("请输入密码", password=True)

    def submit(_: ft.Event[ft.Control]) -> None:
        """只校验非空。既不查库也不发请求，「登录成功」同样只是一句提示。"""
        if not (username_field.value or "").strip():
            notify("请输入用户名")
            return
        if not (password_field.value or "").strip():
            notify("请输入密码")
            return
        # 故意不 `go_back()`：还没接鉴权，退回去反而看不清刚才那句提示。
        notify("登录成功（演示）")

    card = build_auth_card(
        [
            # 只有登录页这张卡片带头像（就是右上角入口那同一张图）。
            build_card_heading("欢迎回来", icon_src=PERSON_ICON_SRC),
            build_field_box(username_field),
            build_field_box(password_field),
            build_primary_button("登录", submit),
        ]
    )

    links = build_link_row(
        [
            ("忘记密码", lambda _: open_forgot()),
            ("注册新账号", lambda _: open_register()),
        ]
    )

    return build_auth_page(page, "登录", go_back, [card, links])
