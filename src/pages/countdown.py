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
    expired_countdowns,
    visible_countdowns,
)
from tools.countdown_form import open_countdown_form
from tools.layout import BOTTOM_MENU_INSET, page_gradient

PAGE_SIDE_PADDING = 24
# 双列卡片：两张之间的缝，以及再窄也要保住的卡片宽度。
COUNTDOWN_GAP = 10
COUNTDOWN_MIN_WIDTH = 140

# 列表最底下那个「已过期 N」开关：弱化成一行浅灰小字 —— 没有边框也没有底色，
# 圆角只用来给水波纹定型。key 留给校验用。
EXPIRED_TOGGLE_KEY = "expired-toggle"
EXPIRED_TOGGLE_TEXT_SIZE = 12
EXPIRED_TOGGLE_ICON_SIZE = 16
EXPIRED_TOGGLE_COLOR = "#94A3B8"
EXPIRED_TOGGLE_RADIUS = 8


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

    # 底部「已过期的倒数日」现在是开是关：刷新（增删改、重新渲染）时保持不变，
    # 只有点它才翻。
    expired_open = False

    def card_width() -> float:
        """卡片宽度跟着屏幕走：页面左右各 24px，中间留一道缝，正好两列。"""
        page_width = getattr(page, "width", None) or 360
        return max(
            COUNTDOWN_MIN_WIDTH,
            (page_width - PAGE_SIDE_PADDING * 2 - COUNTDOWN_GAP) / 2,
        )

    def entry(item: db.Countdown, expired: bool = False) -> ft.Control:
        return build_countdown_card(
            item,
            today=today,
            expired=expired,
            on_delete=lambda _: remove(item.id),
            on_edit=lambda _: edit(item),
        )

    def card_grid(
        rows: list[db.Countdown],
        expired: bool = False,
        wide_first: bool = True,
    ) -> list[ft.Control]:
        """两列排；`wide_first` 时第一张单独通栏（倒数日页上面那一段）。

        过期那一段传 `wide_first=False` —— 全部双列，谁也不被单独放大。
        """
        controls: list[ft.Control] = []
        rest = rows
        if wide_first and rows:
            controls.append(entry(rows[0], expired))
            rest = rows[1:]
        if rest:
            controls.append(
                ft.Row(
                    wrap=True,
                    spacing=COUNTDOWN_GAP,
                    run_spacing=COUNTDOWN_GAP,
                    controls=[
                        ft.Container(
                            width=card_width(),
                            content=entry(item, expired),
                        )
                        for item in rest
                    ],
                )
            )
        return controls

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
                        "还没有倒数日哦",
                        size=13,
                        color="#64748B",
                    ),
                ],
            ),
        )

    def expired_toggle(count: int) -> ft.Control:
        """列表最底下那个开关：点开展示已过期的卡片，再点收回去。"""
        return ft.Container(
            key=EXPIRED_TOGGLE_KEY,
            # 没有边框、没有底色：过期卡片是次要信息，这里只留一行浅灰小字。
            border_radius=ft.BorderRadius.all(EXPIRED_TOGGLE_RADIUS),
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            ink=True,
            on_click=lambda _: set_expired_open(not expired_open),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
                controls=[
                    ft.Text(
                        f"已过期 {count}",
                        size=EXPIRED_TOGGLE_TEXT_SIZE,
                        color=EXPIRED_TOGGLE_COLOR,
                    ),
                    ft.Icon(
                        (
                            ft.Icons.EXPAND_LESS
                            if expired_open
                            else ft.Icons.EXPAND_MORE
                        ),
                        size=EXPIRED_TOGGLE_ICON_SIZE,
                        color=EXPIRED_TOGGLE_COLOR,
                    ),
                ],
            ),
        )

    def set_expired_open(open_it: bool) -> None:
        """展开 / 收起过期的那些：重画整列，箭头方向也跟着翻。"""
        nonlocal expired_open
        if open_it == expired_open:
            return
        expired_open = open_it
        render()
        items.update()

    def render() -> None:
        all_items = db.list_countdowns()
        # 到期的按天数排；过期的那些被 `visible_countdowns` 筛掉了（见
        # tools/countdown_card.py），收在底部那个开关里，最近过期的排最前。
        rows = sorted(
            visible_countdowns(all_items, today),
            key=lambda item: countdown_days(item, today),
        )
        expired = sorted(
            expired_countdowns(all_items, today),
            key=lambda item: countdown_days(item, today),
            reverse=True,
        )
        if not rows and not expired:
            items.controls = [empty_hint()]
            return
        # 最近的那个单独放最上面，占满一整行；其余的按两列排（窄屏自动落成一张）。
        controls: list[ft.Control] = card_grid(rows) if rows else []
        if expired:
            controls.append(expired_toggle(len(expired)))
            if expired_open:
                controls.extend(
                    card_grid(expired, expired=True, wide_first=False)
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
