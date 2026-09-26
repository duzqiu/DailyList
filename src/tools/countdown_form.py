"""The 新增/编辑倒数日 dialog, shared by the 倒数日 and 日历 pages.

It carries the card-background palette as well, so the colour a card is painted
with and the colour the picker offers can never drift apart.
"""

from collections.abc import Callable
from datetime import date

import flet as ft

from tools import db
from tools.layout import (
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    anchor_dialog_above_keyboard,
    date_label,
    dialog_button_style,
    text_width,
)
from tools.pickers import build_date_picker, build_value_trigger
from tools.popup_select import (
    OPTION_TEXT_SIZE,
    build_option_row,
    build_option_selector,
    build_option_text,
    option_row,
    option_text,
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
CARD_COLOR_HEX = {name: value for name, value in CARD_COLORS}
# The 背景色 panel is sized to its longest name instead of a guessed width, so a
# name can never be clipped by the panel's right edge.
SWATCH_SIZE = 12
SWATCH_GAP = 6


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
    start_color = item.bgcolor if editing else CARD_COLORS[0][1]
    start_color_name = next(
        (name for name, value in CARD_COLORS if value == start_color),
        CARD_COLORS[0][0],
    )
    draft = {"date": start_day, "bgcolor": start_color}
    cycle_text = build_option_text(
        item.cycle if editing else db.DEFAULT_CYCLE
    )
    color_text = build_option_text(start_color_name)

    def swatch(value: str) -> ft.Control:
        return ft.Container(
            width=SWATCH_SIZE,
            height=SWATCH_SIZE,
            border_radius=ft.BorderRadius.all(3),
            bgcolor=value,
            # A hairline keeps the palest swatch visible on the white panel.
            border=ft.Border.all(1, "#E2E8F0"),
        )

    def color_face(name: str, text: ft.Control) -> ft.Control:
        """Swatch plus name - the same pair in the trigger and the panel."""
        return ft.Row(
            tight=True,
            spacing=SWATCH_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[swatch(CARD_COLOR_HEX[name]), text],
        )

    color_width = max(
        SWATCH_SIZE + SWATCH_GAP + text_width(name, OPTION_TEXT_SIZE)
        for name, _ in CARD_COLORS
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
        content_width=90,
    )

    def set_color(name: str) -> None:
        draft["bgcolor"] = CARD_COLOR_HEX[name]
        color_text.value = name
        color_trigger.content = color_face(name, color_text)
        color_trigger.update()

    color_trigger = ft.Container(
        content=color_face(start_color_name, color_text)
    )
    color_selector = build_option_selector(
        color_trigger,
        [(name, name) for name, _ in CARD_COLORS],
        set_color,
        label_builder=lambda name: option_row(
            color_face(name, option_text(name))
        ),
        content_width=color_width,
    )
    def focus_changed(focused: bool) -> None:
        set_menu_visible(not focused)
        anchor_dialog_above_keyboard(dialog, focused)

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
        multiline=True,
        min_lines=2,
        max_lines=5,
    )

    def close_dialog(_: ft.Event[ft.Control] | None = None) -> None:
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
        on_dismiss=lambda _: close_dialog(),
        content=ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                build_option_row(date_trigger),
                build_option_row(cycle_selector),
                build_option_row(color_selector),
                content_field,
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
    page.show_dialog(dialog)
