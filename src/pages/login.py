"""登录页 / 账号页：日历页右上角那枚 person 图标进来的二级页。

**未登录**（本地没有令牌）时是登录表单：字段是邮箱 / 密码，点「登录」调后端
`POST /member/auth/login`（见 api/member_auth.py）；令牌由 api/session.py 存到本地，
登录成功后**直接跳到首页**（`open_home`，由 pages/navigation.py 给）。

**已登录**（本地有令牌）时这一页换成「当前用户」卡片：进来先调 `GET /member/auth/me`
把昵称 / 邮箱 / 会员号显示出来，卡片下面是「退出登录」（调 `POST /member/auth/logout`；
后端是无状态 JWT，真正生效的是 api/session.py 把本地令牌清掉）。令牌已失效（401）时
自动清掉本地令牌并退回未登录形态（`reload_login` 重画本层）。

两个链接的位置：**「忘记密码？」贴着密码框外的右下角**（卡片里、密码框下面那一行，右对齐，
与密码框的间距用 `FIELD_HINT_GAP` 收到 2），**「还没有账号？去注册」钉在页面左右居中偏下**
（不跟表单走 —— 见 tools/auth_form.py 的 `footer`）。
它们进的都是**三级页**（压进 page.views 的第 2 层，见 pages/register.py 与
pages/forgot_password.py）；从那儿返回回到的是这一页 —— 注册成功、重置密码成功也是回
这一层（各页自己调 `go_back()`）。

壳子、卡片、字段、主按钮、底部链接都来自 tools/auth_form.py（和注册页、忘记密码页
共用一套），这一页只负责「有哪些字段、点了做什么」。
"""

from collections.abc import Callable

import flet as ft

from api import member_auth, session
from api.client import ApiError
from tools.auth_form import (
    FIELD_HINT_GAP,
    FIELD_TEXT_SIZE,
    HINT_COLOR,
    MUTED_COLOR,
    SUBTITLE_SIZE,
    TITLE_COLOR,
    build_auth_card,
    build_auth_field,
    build_auth_page,
    build_card_heading,
    build_field_box,
    build_link_row,
    build_primary_button,
)
from tools.toast import build_toast


def build_login_page(
    page: ft.Page,
    go_back: Callable[[], None],
    open_register: Callable[[], None],
    open_forgot: Callable[[], None],
    open_home: Callable[[], None],
    reload_login: Callable[[], None],
) -> ft.Control:
    """登录页。

    `go_back` / `open_register` / `open_forgot` / `open_home` / `reload_login` 都由
    pages/navigation.py 给：「‹ 返回」、整页左滑、真机返回键共用 `go_back`；两个链接
    分别进注册页、忘记密码页；登录成功走 `open_home` 跳回首页；退出登录（或令牌
    失效）走 `reload_login` 重画本层，使它回到未登录形态。
    """
    if session.access_token():
        return _build_signed_in(page, go_back, open_home, reload_login)
    return _build_sign_in_form(page, go_back, open_register, open_forgot, open_home)


def _notify(page: ft.Page, message: str) -> None:
    """一句话的提示：走 tools/toast.py，浮在**屏幕正中**。"""
    page.show_dialog(build_toast(page, message))


# ------------------------------ 未登录：登录表单 ------------------------------


def _build_sign_in_form(
    page: ft.Page,
    go_back: Callable[[], None],
    open_register: Callable[[], None],
    open_forgot: Callable[[], None],
    open_home: Callable[[], None],
) -> ft.Control:
    # 字段对象要留着读值（`build_auth_field` 给控件本体，`build_field_box` 只是把它
    # 套进那圈细边里，两者分开是为了这一层还能拿到 TextField）。
    email_field = build_auth_field("请输入邮箱")
    password_field = build_auth_field("请输入密码", password=True)

    async def do_login() -> None:
        """带请求的那半：交给 `page.run_task` 跑，别卡住 UI（见 submit）。"""
        email = (email_field.value or "").strip()
        password = password_field.value or ""
        if not email:
            _notify(page, "请输入邮箱")
            return
        if not password:
            _notify(page, "请输入密码")
            return
        try:
            # 令牌由 api 层存好（见 api/session.py），这一页不用管。
            await member_auth.login(email, password)
        except ApiError as error:
            # 后端的话（「邮箱或密码错误」之类）可以直接给用户看。
            _notify(page, error.message)
            return
        # 登录成功：先跳回首页，再把提示压在它上面 —— 提示是页面级弹层，换页不受影响。
        open_home()
        _notify(page, "登录成功")

    def submit(_: ft.Event[ft.Control]) -> None:
        """按钮回调是同步的：请求丢给 `page.run_task`，避免阻塞事件循环。"""
        page.run_task(do_login)

    card = build_auth_card(
        [
            build_card_heading("登录"),
            build_field_box(email_field),
            # 密码框与「忘记密码？」是一对：这一小块自己把间距收到 `FIELD_HINT_GAP`，
            # 不用卡片统一的 `CARD_SPACING` —— 那一行要贴着密码框的**右下角**。
            ft.Column(
                tight=True,
                spacing=FIELD_HINT_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    build_field_box(password_field),
                    build_link_row(
                        [("忘记密码？", lambda _: open_forgot())],
                        alignment=ft.MainAxisAlignment.END,
                        # 去掉链接自带的左右内边距，文字右边缘就跟密码框的右边缘齐平。
                        side_padding=0,
                    ),
                ],
            ),
            build_primary_button("登录", submit),
        ]
    )

    # 「还没有账号？去注册」不跟表单走：交给页面壳的 footer，钉在页面左右居中偏下的位置。
    footer = build_link_row([("还没有账号？去注册", lambda _: open_register())])

    return build_auth_page(page, go_back, [card], footer=footer)


# ------------------------------ 已登录：当前用户 ------------------------------


def _build_signed_in(
    page: ft.Page,
    go_back: Callable[[], None],
    open_home: Callable[[], None],
    reload_login: Callable[[], None],
) -> ft.Control:
    """已登录时的形态：当前用户信息 + 退出登录。

    三行字先摆「加载中…」，进页面立刻异步拉 `GET /member/auth/me` 再填上。令牌失效
    时清本地令牌并 `reload_login()` 退回登录表单，免得卡在一个请求不到数据的卡片上。
    """
    name_text = ft.Text(
        "加载中…",
        size=FIELD_TEXT_SIZE,
        color=TITLE_COLOR,
        text_align=ft.TextAlign.CENTER,
    )
    email_text = ft.Text(
        "", size=SUBTITLE_SIZE, color=MUTED_COLOR, text_align=ft.TextAlign.CENTER
    )
    member_text = ft.Text(
        "", size=SUBTITLE_SIZE, color=HINT_COLOR, text_align=ft.TextAlign.CENTER
    )

    def show(user: dict) -> None:
        """把 `MemberOut` 填进这三行字（后端字段见 schemas/member.py）。"""
        email = str(user.get("email") or "").strip()
        # 昵称依次退：显示名 → 昵称 → 邮箱；后端给的都是空串时至少还有个「会员」。
        nickname = str(
            user.get("display_name") or user.get("nickname") or email
        ).strip()
        member_no = str(user.get("member_no") or "").strip()
        name_text.value = nickname or "会员"
        email_text.value = email
        member_text.value = f"会员号 {member_no}" if member_no else ""
        page.update()

    async def load_user() -> None:
        """拉当前会员；401 说明本地令牌已失效，直接退回登录表单。"""
        try:
            user = await member_auth.me()
        except ApiError as error:
            if error.status == 401:
                session.clear()
                reload_login()
                return
            name_text.value = "加载失败"
            email_text.value = error.message
            member_text.value = ""
            page.update()
            return
        show(user)

    async def do_logout() -> None:
        """退出登录：后端只是应一声，本地令牌由 `member_auth.logout` 清掉。"""
        try:
            await member_auth.logout()
        except ApiError as error:
            # `logout` 在 finally 里清令牌，所以这里只是把后端的抱怨说一声，照样回登录表单。
            _notify(page, error.message)
            reload_login()
            return
        # 先重画（回到未登录形态），再把提示压在上面。
        reload_login()
        _notify(page, "已退出登录")

    def on_logout(_: ft.Event[ft.Control]) -> None:
        page.run_task(do_logout)

    def on_reload(_: ft.Event[ft.Control]) -> None:
        page.run_task(load_user)

    card = build_auth_card(
        [
            build_card_heading("已登录"),
            name_text,
            email_text,
            member_text,
            build_primary_button("退出登录", on_logout),
        ]
    )

    links = build_link_row(
        [
            ("重新加载", on_reload),
            ("去首页", lambda _: open_home()),
        ]
    )

    # 进页面就把会员信息拉回来（异步，先显示「加载中…」）。
    page.run_task(load_user)

    return build_auth_page(page, go_back, [card, links])
