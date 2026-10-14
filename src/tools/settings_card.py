"""设置卡片的零件：`settings_section` / `setting_row` / `compact_button_style`，以及
**「账号」卡片**（`build_account_card`）。

这三块零件原本长在设置页（pages/preferences.py）里；「账号」卡片现在整块搬到「我的」页
（pages/my.py），两边都要用同一套卡片外壳 —— 所以一并搬到这儿，设置页反过来 import 它们
（一处实现，两处用；README 约定 12）。

`build_account_card` 自己只依赖 `page` 与 `open_login`，不碰设置页的任何局部状态，所以
搬过来是干净的。
"""

from collections.abc import Callable

import flet as ft

from api import member_auth, session
from api.client import ApiError
from tools.layout import UNSELECTED_CARD_BG

TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
# 报错那一行的颜色（拉取用户信息失败时用），和设置页原来的取值一致。
PENDING_COLOR = "#DC2626"
CARD_BG = UNSELECTED_CARD_BG
CARD_BORDER = "#E2E8F0"


def settings_section(title: str, rows: list[ft.Control]) -> ft.Control:
    """一档设置：卡片上方一行小标题（灰字），底下的卡片里摆这一档的各行。"""
    return ft.Column(
        tight=True,
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Text(
                title,
                size=12,
                weight=ft.FontWeight.BOLD,
                color=MUTED_COLOR,
            ),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                border_radius=ft.BorderRadius.all(12),
                bgcolor=CARD_BG,
                border=ft.Border.all(1, CARD_BORDER),
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=rows,
                ),
            ),
        ],
    )


def setting_row(
    title: str,
    subtitle: ft.Control,
    action: ft.Control | None = None,
):
    """卡片里的一行：左边「标题 + 小字说明」，右边跟一个动作控件。

    纯展示的行（当前版本）不给动作，右边就空着。
    """
    return ft.Row(
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Column(
                tight=True,
                spacing=2,
                expand=True,
                controls=[
                    ft.Text(
                        title,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=TITLE_COLOR,
                    ),
                    subtitle,
                ],
            ),
            *([action] if action is not None else []),
        ],
    )


def compact_button_style() -> ft.ButtonStyle:
    """Compact metrics of the card's own 清除 action button."""
    return ft.ButtonStyle(
        padding=ft.Padding.symmetric(horizontal=10, vertical=2),
        text_style=ft.TextStyle(size=12),
        visual_density=ft.VisualDensity.COMPACT,
    )


def build_account_card(
    page: ft.Page, open_login: Callable[[], None]
) -> ft.Control:
    """「账号」这一档：没登录给个登录入口，登录了显示当前用户。

    两种情况共用同一块 `account_body`（就是卡片里的内容），拉到数据后只换这一块
    —— 不重画整页，也不惊动别的卡片。

    用户信息来自后端 `GET /member/auth/me`（见 api/member_auth.py）；本地令牌已
    失效（401）时把令牌清掉、退回未登录形态，免得一直停在拉不到数据的样式上。

    原来长在设置页里，整块搬到「我的」页（pages/my.py）—— 卡片自己只认 `page` 和
    `open_login`（点「登录」/「管理」时进登录页），别的什么都不依赖。
    """
    avatar_size = 40
    account_body = ft.Column(
        tight=True,
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[],
    )

    def render_signed_out(message: str = "", update: bool = True) -> None:
        """未登录：一行「未登录 + 登录按钮」；`message` 用来报拉取失败的原因。"""
        account_body.controls = [
            setting_row(
                "未登录",
                ft.Text(
                    message or "登录后可查看账号信息",
                    size=11,
                    color=PENDING_COLOR if message else MUTED_COLOR,
                ),
                ft.OutlinedButton(
                    "登录",
                    on_click=lambda _: open_login(),
                    style=compact_button_style(),
                ),
            )
        ]
        if update:
            page.update()

    def render_user(user: dict) -> None:
        """已登录：头像 + 昵称 / 邮箱 / 会员号，右边一个「管理」进账号页。"""
        email = str(user.get("email") or "").strip()
        # 昵称依次退：显示名 → 昵称 → 邮箱（和后端 MemberOut 的字段一致）。
        nickname = str(
            user.get("display_name") or user.get("nickname") or email
        ).strip()
        member_no = str(user.get("member_no") or "").strip()
        lines = [
            ft.Text(
                nickname or "会员",
                size=13,
                weight=ft.FontWeight.BOLD,
                color=TITLE_COLOR,
            ),
            ft.Text(email, size=11, color=MUTED_COLOR),
        ]
        if member_no:
            lines.append(
                ft.Text(f"会员号 {member_no}", size=11, color=MUTED_COLOR)
            )
        account_body.controls = [
            ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # 头像用 Flet 内置图标，和登录页那张卡片同一个做法。
                    ft.Container(
                        width=avatar_size,
                        height=avatar_size,
                        alignment=ft.Alignment.CENTER,
                        border_radius=ft.BorderRadius.all(avatar_size / 2),
                        border=ft.Border.all(1, CARD_BORDER),
                        content=ft.Icon(
                            ft.Icons.PERSON,
                            size=avatar_size * 0.55,
                            color=MUTED_COLOR,
                        ),
                    ),
                    ft.Column(
                        tight=True, spacing=2, expand=True, controls=lines
                    ),
                    ft.OutlinedButton(
                        "管理",
                        on_click=lambda _: open_login(),
                        style=compact_button_style(),
                    ),
                ],
            )
        ]
        page.update()

    async def load_user() -> None:
        """进页面就把当前会员拉回来；401 说明令牌过期，清掉并退回未登录。"""
        try:
            user = await member_auth.me()
        except ApiError as error:
            if error.status == 401:
                session.clear()
                render_signed_out()
                return
            render_signed_out(error.message)
            return
        render_user(user)

    if session.access_token():
        # 有令牌：先摆「加载中…」，拉回来再换成用户信息。
        account_body.controls = [
            ft.Text("加载中…", size=11, color=MUTED_COLOR)
        ]
        page.run_task(load_user)
    else:
        # 建页面时这一格就定好，不用再 update 一次。
        render_signed_out(update=False)

    return settings_section("账号", [account_body])
