"""The system date and time pickers the 待办 and 倒数日 dialogs share.

Both are Flet's own controls - the Material date dialog and the time dial - and
both are point-only: the date picker cannot switch to typing a date and the time
picker cannot switch to typing a time.

Two details worth keeping in mind:

* The value arrives through `on_change` when the user confirms (`ft.DatePicker`
  documents exactly that). The Cupertino wheel was tried before and dropped -
  scrolling it never reached `on_change`, so a picked day stayed lost.
* Flet hands a picked local midnight back as UTC (2026-10-15 00:00 +08 arrives
  as 2026-10-14 16:00Z), hence `local_day`.
"""

from collections.abc import Callable
from datetime import date, datetime, time

import flet as ft

from tools.popup_select import CARET_COLOR



def build_value_trigger(
    text: ft.Control, on_click: Callable[[ft.Event[ft.Control]], None]
) -> ft.Container:
    """The value-plus-caret trigger that opens a picker - one face for both."""
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=4, vertical=4),
        border_radius=ft.BorderRadius.all(6),
        on_click=on_click,
        content=ft.Row(
            tight=True,
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                text,
                ft.Icon(
                    ft.Icons.EXPAND_MORE,
                    size=16,
                    color=CARET_COLOR,
                    # A large Android font scale grows text; the caret keeps its
                    # size so it cannot grow into the value next to it.
                    apply_text_scaling=False,
                ),
            ],
        ),
    )


def local_day(value: date | datetime) -> date:
    """The local calendar day of a value a picker handed back."""
    if isinstance(value, datetime):
        return value.astimezone().date()
    return value


def midnight(day: date) -> datetime:
    """`day` as the datetime `first_date`/`last_date` expect."""
    return datetime.combine(day, time.min)


def build_date_picker(
    value: date,
    on_confirm: Callable[[date], None],
    first_date: datetime | None = None,
    last_date: datetime | None = None,
) -> ft.DatePicker:
    """Flet's system date picker. 点选 only - the typing mode is not offered.

    `first_date`/`last_date` clamp the range the way each dialog needs: 新增待办
    keeps past days out, 倒数日 allows them because a birthday usually starts
    years ago.
    """
    picker = ft.DatePicker(
        value=value,
        locale=ft.Locale("zh", "CN"),
        first_date=first_date,
        last_date=last_date,
        date_picker_mode=ft.DatePickerMode.DAY,
        # Calendar only: no mode button, so a date can only be tapped in.
        entry_mode=ft.DatePickerEntryMode.CALENDAR_ONLY,
        help_text="选择日期",
        cancel_text="取消",
        confirm_text="确定",
        field_label_text="日期",
        field_hint_text="年/月/日",
    )

    def confirm(e: ft.Event[ft.DatePicker]) -> None:
        picker.open = False
        on_confirm(local_day(e.control.value))
        if e.page:
            e.page.update()

    picker.on_change = confirm
    return picker


def build_time_picker(
    value: time, on_confirm: Callable[[time], None]
) -> ft.TimePicker:
    """Flet's system time picker. 点选 only - the dial, no typed input."""
    picker = ft.TimePicker(
        value=value,
        # 24-hour dial so the picked value matches the "HH:MM" the app prints.
        hour_format=ft.TimePickerHourFormat.H24,
        # Dial only: the mode button that switches to typing a time is hidden.
        entry_mode=ft.TimePickerEntryMode.DIAL_ONLY,
        help_text="选择时间",
        cancel_text="取消",
        confirm_text="确定",
    )

    def confirm(e: ft.Event[ft.TimePicker]) -> None:
        picker.open = False
        on_confirm(e.control.value)
        if e.page:
            e.page.update()

    picker.on_change = confirm
    return picker
