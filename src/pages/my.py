"""「我的」页：账号信息 + 右上角两枚入口（数据 / 设置）。

这一页原来是「日历」页。月历部分整块搬去了数据页（接在待办趋势图下方，见
tools/month_calendar.py），腾出来的位置放**账号** —— 它原来长在设置页的「账号」卡片里
（见 tools/settings_card.py 的 `build_account_card`），现在整块挪到这儿，底部 Tab 也
跟着从「日历」改名「我的」。

右上角那两枚入口保持原样：**数据、设置**。数据页现在是「图 + 月历」，从这儿进；设置页
照旧管通知 / 数据 / 通用三档（「账号」已经从它里面拿走了）。
"""

from collections.abc import Callable

import flet as ft

from tools.layout import (
    BOTTOM_MENU_INSET,
    DATA_ICON_SRC,
    SETTINGS_ICON_SRC,
    page_gradient,
)
from tools.settings_card import build_account_card

TITLE_COLOR = "#172554"
DATA_ICON_SIZE = 22
SETTINGS_ICON_SIZE = 22
TOPBAR_ICON_GAP = 0


def _topbar_icon(
    src: str, size: float, tooltip: str, on_click: Callable[[], None]
) -> ft.Control:
    """顶栏右上角那种小图标入口：图标小、四周补一圈内边距，手指才够得着。"""
    return ft.Container(
        ink=True,
        tooltip=tooltip,
        padding=ft.Padding.all(6),
        on_click=lambda _: on_click(),
        content=ft.Image(
            src=src,
            width=size,
            height=size,
            fit=ft.BoxFit.CONTAIN,
        ),
    )


def build_my_page(
    page: ft.Page,
    set_menu_visible: Callable[[bool], None],
    state: dict[str, object],
    open_settings: Callable[[], None],
    open_data: Callable[[], None],
    open_login: Callable[[], None],
) -> ft.Control:
    """「我的」页。

    `state` 由调用方保管（见 pages/navigation.py），签名与别的 Tab 保持一致 —— 这一页
    眼下没有需要跨 Tab 记住的东西，留着是给以后（比如记住展开的哪一档）。

    `open_settings` / `open_data` 进二级页；`open_login` 是「账号」卡片里点「登录」/
    「管理」时进登录页（由 navigation 给的一层，返回回到这个 Tab）。
    """
    return ft.Container(
        expand=True,
        gradient=page_gradient(),
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=24, top=24, right=24),
                content=ft.Column(
                    expand=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "我的",
                                    # 和「待办」「日历」那几个页头同一副字面。
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                                ft.Row(
                                    tight=True,
                                    spacing=TOPBAR_ICON_GAP,
                                    controls=[
                                        _topbar_icon(
                                            DATA_ICON_SRC,
                                            DATA_ICON_SIZE,
                                            "数据",
                                            open_data,
                                        ),
                                        _topbar_icon(
                                            SETTINGS_ICON_SRC,
                                            SETTINGS_ICON_SIZE,
                                            "设置",
                                            open_settings,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.ListView(
                            expand=True,
                            spacing=12,
                            scroll=ft.ScrollMode.HIDDEN,
                            padding=ft.Padding.only(
                                bottom=BOTTOM_MENU_INSET
                            ),
                            controls=[build_account_card(page, open_login)],
                        ),
                    ],
                ),
            ),
        ),
    )
