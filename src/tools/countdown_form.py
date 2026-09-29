"""The 新增/编辑倒数日 dialog, shared by the 倒数日 and 日历 pages.

弹窗里不摆颜色：新增时从 `CARD_COLORS` 那套浅色里**随机**取一个当卡片底色，编辑时
沿用这条倒数日原来的颜色（见 `open_countdown_form`）。
"""

import random
from collections.abc import Callable
from datetime import date

import flet as ft

from tools import db
from tools.layout import (
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    date_label,
    dialog_button_style,
    track_keyboard,
)
from tools.pickers import build_date_picker, build_value_trigger
from tools.popup_select import (
    MENU_HEIGHT,
    build_option_row,
    build_option_selector,
    build_option_text,
)

TITLE_COLOR = "#172554"
MUTED_COLOR = "#94A3B8"
# The card's own background is picked when the countdown is added; every choice
# is a pale tint so the card's dark ink stays readable on it.
CARD_COLORS = (
    ("冰浅蓝", "#E0F2FE"),
    ("浅天蓝", "#BAE6FD"),
    ("莫兰迪灰蓝", "#D1DCE8"),
    ("青调浅灰蓝", "#C9D7E0"),
    ("柔和浅紫", "#DDD6FE"),
    ("奶薄荷浅绿", "#ECFDF5"),
    ("柔和浅青绿", "#D1FAE5"),
    ("莫兰迪浅绿", "#E6F4EA"),
    ("极浅灰粉", "#FDF2F8"),
    ("莫兰迪裸粉", "#F4E7E9"),
    ("奶油杏", "#FFF7ED"),
    ("莫兰迪奶咖", "#F5EBE0"),
    ("页面底色灰", "#F8FAFC"),
    ("边框浅灰", "#E2E8F0"),
)
def open_countdown_form(
    page: ft.Page,
    *,
    set_menu_visible: Callable[[bool], None],
    on_saved: Callable[[], None],
    item: db.Countdown | None = None,
) -> None:
    """Show the 新增/编辑倒数日 dialog. `item` present means editing."""
    editing = item is not None
    today = date.today()
    start_day = item.due_date if editing else today
    # 新增的倒数日不让用户挑颜色：从原来那套浅色里**随机**取一个当卡片底色；编辑时
    # 沿用这条倒数日原来的颜色，不动。
    start_color = item.bgcolor if editing else random.choice(CARD_COLORS)[1]
    draft = {"date": start_day, "bgcolor": start_color}
    cycle_text = build_option_text(
        item.cycle if editing else db.DEFAULT_CYCLE
    )

    date_text = build_option_text(date_label(start_day))

    def apply_date(chosen: date) -> None:
        draft["date"] = chosen
        date_text.value = date_label(chosen)
        date_text.update()

    # 日期 uses the shared system picker with no lower bound: a countdown
    # anchor may sit in the past (a birthday, an anniversary).
    sheet = build_date_picker(start_day, apply_date)

    def open_date_picker(_: ft.Event[ft.Control]) -> None:
        page.show_dialog(sheet)

    date_trigger = build_value_trigger(date_text, open_date_picker)

    def set_cycle(name: str) -> None:
        cycle_text.value = name
        cycle_text.update()

    cycle_selector = build_option_selector(
        cycle_text,
        [(name, name) for name in db.REPEAT_CYCLES],
        set_cycle,
        # 周期有十档：面板钉成固定高度，多出来的在里面上下滚。
        menu_height=MENU_HEIGHT,
        content_width=90,
    )

    def focus_changed(focused: bool) -> None:
        # 弹窗跟着键盘走由 `track_keyboard` 管（焦点事件比键盘动画早一步，按它挪
        # 会先沉一下再弹回来）。
        set_menu_visible(not focused)

    content_field = ft.TextField(
        value=item.content if editing else "",
        hint_text="请输入倒数日事项",
        hint_style=ft.TextStyle(size=13, color=MUTED_COLOR),
        # Typing opens the keyboard, so the floating menu bar steps out of the
        # way and the dialog parks just above the keyboard, exactly as it does in
        # the 新增待办 dialog.
        on_focus=lambda _: focus_changed(True),
        on_blur=lambda _: focus_changed(False),
        filled=False,
        border=ft.NoInputBorder(),
        content_padding=ft.Padding.symmetric(horizontal=0, vertical=6),
        text_style=ft.TextStyle(size=13, color="#334155"),
        dense=True,
        # 事项就是一行字，输入框也保持单行 —— 不设 `multiline`，它就没有会长高的
        # 余地（和 新增待办 的输入框一个做法）。
    )

    def close_dialog(_: ft.Event[ft.Control] | None = None) -> None:
        unwatch_keyboard()
        dialog.open = False
        set_menu_visible(True)
        page.update()

    def save(_: ft.Event[ft.Control]) -> None:
        text = (content_field.value or "").strip()
        if not text:
            return
        if editing and item is not None:
            db.update_countdown(
                item.id,
                draft["date"],
                text,
                cycle_text.value,
                draft["bgcolor"],
            )
        else:
            db.add_countdown(
                draft["date"], text, cycle_text.value, draft["bgcolor"]
            )
        close_dialog()
        on_saved()

    dialog = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
        bgcolor=DIALOG_SURFACE,
        elevation=0,
        title="编辑倒数日" if editing else "新增倒数日",
        title_text_style=ft.TextStyle(
            size=16,
            weight=ft.FontWeight.BOLD,
            color=TITLE_COLOR,
        ),
        inset_padding=ft.Padding.symmetric(horizontal=48, vertical=24),
        title_padding=ft.Padding.only(left=16, top=12, right=16, bottom=0),
        content_padding=ft.Padding.only(left=16, top=8, right=16, bottom=8),
        actions_padding=ft.Padding.only(left=8, right=8, bottom=8),
        action_button_padding=ft.Padding.symmetric(horizontal=8),
        # 点外面 / 按返回关掉时也走 `close_dialog`，键盘跟随在那里拆。
        on_dismiss=lambda _: close_dialog(),
        content=ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                content_field,
                build_option_row(date_trigger),
                build_option_row(cycle_selector),
            ],
        ),
        actions=[
            ft.TextButton(
                "取消",
                style=dialog_button_style(),
                on_click=close_dialog,
            ),
            ft.TextButton(
                "保存",
                style=dialog_button_style(),
                on_click=save,
            ),
        ],
    )
    # 键盘一升一落都把弹窗挪到键盘上方 / 回到正中（见 track_keyboard）。
    unwatch_keyboard = track_keyboard(page, dialog)
    page.show_dialog(dialog)
