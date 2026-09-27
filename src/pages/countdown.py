"""倒数日 page: the countdown list the home page's 待办 row opens.

Every entry keeps the anchor date plus an optional 周期 (the same choices a
repeating 待办 uses). A repeating anchor walks forward to its next occurrence, so
a birthday written down years ago still counts down to the coming one, while 不循环
counts down to the fixed day - or shows how long ago it passed.
"""

from collections.abc import Callable
from datetime import date

import flet as ft

from tools import db
from tools.countdown_card import (
    MUTED_COLOR,
    TITLE_COLOR,
    build_countdown_card,
    countdown_days,
)
from tools.countdown_form import open_countdown_form
from tools.layout import BOTTOM_MENU_INSET, SKY_BLUE, page_gradient

# Same floating tile as the home page's 新增待办 button, and the same dialogs.
ADD_BUTTON_BG = "#99" + SKY_BLUE[1:]
ADD_BUTTON_SIZE = 52
ADD_BUTTON_LIFT = 10
PAGE_SIDE_PADDING = 24
# 双列卡片：两张之间的缝，以及再窄也要保住的卡片宽度。
COUNTDOWN_GAP = 10
COUNTDOWN_MIN_WIDTH = 140


def build_countdown_page(
    page: ft.Page, set_menu_visible: Callable[[bool], None]
) -> ft.Control:
    today = date.today()
    items = ft.ListView(
        expand=True,
        spacing=COUNTDOWN_GAP,
        scroll=ft.ScrollMode.HIDDEN,
        padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
    )

    def card_width() -> float:
        """卡片宽度跟着屏幕走：页面左右各 24px，中间留一道缝，正好两列。"""
        page_width = getattr(page, "width", None) or 360
        return max(
            COUNTDOWN_MIN_WIDTH,
            (page_width - PAGE_SIDE_PADDING * 2 - COUNTDOWN_GAP) / 2,
        )

    def entry(item: db.Countdown) -> ft.Control:
        return build_countdown_card(
            item,
            today=today,
            on_delete=lambda _: remove(item.id),
            on_edit=lambda _: edit(item),
        )

    def empty_hint() -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=ft.BorderRadius.all(12),
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, "#E2E8F0"),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(
                        ft.Icons.HOURGLASS_EMPTY,
                        size=20,
                        color=MUTED_COLOR,
                    ),
                    ft.Text(
                        "还没有倒数日，点右下角 + 添加",
                        size=13,
                        color="#64748B",
                    ),
                ],
            ),
        )

    def render() -> None:
        rows = sorted(
            db.list_countdowns(), key=lambda item: countdown_days(item, today)
        )
        if not rows:
            items.controls = [empty_hint()]
            return
        # 最近的那个单独放最上面，占满一整行；其余的按两列排（窄屏自动落成一张）。
        controls: list[ft.Control] = [entry(rows[0])]
        if rows[1:]:
            controls.append(
                ft.Row(
                    wrap=True,
                    spacing=COUNTDOWN_GAP,
                    run_spacing=COUNTDOWN_GAP,
                    controls=[
                        ft.Container(width=card_width(), content=entry(item))
                        for item in rows[1:]
                    ],
                )
            )
        items.controls = controls

    def remove(countdown_id: int) -> None:
        db.delete_countdown(countdown_id)
        render()
        items.update()

    def open_form(item: db.Countdown | None = None) -> None:
        open_countdown_form(
            page,
            # Same callback the 待办 dialog gets: hiding the menu takes the
            # floating + tile with it while the keyboard is up.
            set_menu_visible=set_bottom_controls_visible,
            on_saved=refresh,
            item=item,
        )

    def refresh() -> None:
        render()
        items.update()

    def open_add(_: ft.Event[ft.Container]) -> None:
        open_form()

    def edit(item: db.Countdown) -> None:
        open_form(item)

    add_button = ft.Container(
        right=24,
        bottom=BOTTOM_MENU_INSET + ADD_BUTTON_LIFT,
        width=ADD_BUTTON_SIZE,
        height=ADD_BUTTON_SIZE,
        shape=ft.BoxShape.CIRCLE,
        bgcolor=ADD_BUTTON_BG,
        blur=ft.Blur(20, 20, ft.BlurTileMode.CLAMP),
        content=ft.IconButton(
            icon=ft.Icons.ADD,
            icon_color=TITLE_COLOR,
            icon_size=24,
            tooltip="添加倒数日",
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
            on_click=open_add,
        ),
    )

    def set_bottom_controls_visible(visible: bool) -> None:
        set_menu_visible(visible)
        add_button.visible = visible
        add_button.update()

    render()

    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                gradient=page_gradient(),
                content=ft.SafeArea(
                    expand=True,
                    content=ft.Container(
                        expand=True,
                        padding=ft.Padding.only(
                            left=PAGE_SIDE_PADDING,
                            top=PAGE_SIDE_PADDING,
                            right=PAGE_SIDE_PADDING,
                            bottom=PAGE_SIDE_PADDING,
                        ),
                        content=ft.Column(
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
                                ft.Text(
                                    "倒数日",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                                ft.Container(
                                    expand=True,
                                    margin=ft.Margin.only(top=12),
                                    content=items,
                                ),
                            ],
                        ),
                    ),
                ),
            ),
            add_button,
        ],
    )
