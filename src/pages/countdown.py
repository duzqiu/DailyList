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
    visible_countdowns,
)
from tools.countdown_form import open_countdown_form
from tools.layout import BOTTOM_MENU_INSET, page_gradient

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
                        "还没有倒数日，去待办页点右下角 + 添加",
                        size=13,
                        color="#64748B",
                    ),
                ],
            ),
        )

    def render() -> None:
        # 已经过期的不循环倒数日不再出现在列表里（tools/countdown_card.py）。
        rows = sorted(
            visible_countdowns(db.list_countdowns(), today),
            key=lambda item: countdown_days(item, today),
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
            # 输入框弹键盘时收起底部菜单（和待办弹窗用的是同一套回调）。
            set_menu_visible=set_menu_visible,
            on_saved=refresh,
            item=item,
        )

    def refresh() -> None:
        render()
        items.update()

    def edit(item: db.Countdown) -> None:
        open_form(item)

    render()

    # 倒数日页不再有自己的「+」：新增入口统一在待办页右下角那个按钮上（那里可以
    # 选「新增待办 / 新增倒数日」），所以这一页只剩一张列表。
    return ft.Container(
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
    )
