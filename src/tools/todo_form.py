"""The 新增/编辑待办 dialog, shared by the home and calendar pages.

Adding and editing are the same form: editing just opens it pre-filled with an
existing row. Saving a repeating todo rebuilds its whole series (see
`db.update_todo`), so one edit keeps every occurrence of the cycle in step.
"""

from collections.abc import Callable
from datetime import date, time

import flet as ft

from tools import db
from tools.categories import (
    CATEGORIES,
    DEFAULT_CATEGORY,
    build_category_label,
    category_label_width,
)
from tools.layout import (
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    date_label,
    dialog_button_style,
)
from tools.pickers import (
    build_date_picker,
    build_time_picker,
    build_value_trigger,
    midnight,
)
from tools.popup_select import (
    OPTION_TEXT_SIZE,
    build_option_row,
    build_option_selector,
    build_option_text,
    option_row,
    option_text,
)

MUTED_COLOR = "#94A3B8"
FIELD_COLOR = "#334155"


def default_time() -> str:
    """The 时间 a fresh dialog opens on: the clock rounded down."""
    return db.default_time()


def open_todo_form(
    page: ft.Page,
    *,
    set_menu_visible: Callable[[bool], None],
    on_saved: Callable[[date], None],
    default_date: date,
    todo: db.Todo | None = None,
) -> None:
    """Show the add/edit dialog. `todo` present means editing that row."""
    editing = todo is not None
    start_day = todo.due_date if editing else default_date
    start_time = todo.due_time if editing and todo.due_time else default_time()
    start_category = todo.category if editing else DEFAULT_CATEGORY
    start_cycle = todo.repeat_cycle if editing else db.DEFAULT_CYCLE
    start_hour, _, start_minute = start_time.partition(":")

    selection = {
        "date": start_day.isoformat(),
        "time": f"{start_hour}:{start_minute}",
        "category": start_category,
        "cycle": start_cycle,
    }
    date_text = build_option_text(date_label(start_day))
    time_text = build_option_text(selection["time"])
    cycle_text = build_option_text(start_cycle)
    category_trigger = ft.Container(
        content=build_category_label(
            start_category, build_option_text(start_category)
        )
    )

    def apply_date(chosen: date) -> None:
        selection["date"] = chosen.isoformat()
        date_text.value = date_label(chosen)
        date_text.update()

    def apply_time(chosen: time) -> None:
        selection["time"] = f"{chosen.hour:02d}:{chosen.minute:02d}"
        time_text.value = selection["time"]
        time_text.update()

    # 新增 only looks forward (today is the earliest day); editing an old row has
    # to be able to keep - or move to - a day in the past.
    date_picker = build_date_picker(
        start_day,
        apply_date,
        first_date=None if editing else midnight(date.today()),
    )
    time_picker = build_time_picker(
        time(int(start_hour), int(start_minute)), apply_time
    )
    date_selector = build_value_trigger(
        date_text, lambda _: page.show_dialog(date_picker)
    )
    time_selector = build_value_trigger(
        time_text, lambda _: page.show_dialog(time_picker)
    )

    def pick_category(name: str) -> None:
        selection["category"] = name
        # Swapping the whole pair keeps the stars in step with the name.
        category_trigger.content = build_category_label(
            name, build_option_text(name)
        )
        category_trigger.update()

    def pick_cycle(name: str) -> None:
        selection["cycle"] = name
        cycle_text.value = name
        cycle_text.update()

    todo_field = ft.TextField(
        value=todo.content if editing else "",
        hint_text="请输入待办内容",
        hint_style=ft.TextStyle(size=13, color=MUTED_COLOR),
        on_focus=lambda _: set_menu_visible(False),
        on_blur=lambda _: set_menu_visible(True),
        filled=False,
        border=ft.NoInputBorder(),
        content_padding=ft.Padding.symmetric(horizontal=0, vertical=6),
        text_style=ft.TextStyle(size=13, color=FIELD_COLOR),
        dense=True,
        # A todo can be a word or a few lines, so the field shows two lines and
        # wraps up to five before it scrolls.
        multiline=True,
        min_lines=2,
        max_lines=5,
    )

    category_selector = build_option_selector(
        category_trigger,
        [(name, name) for name, _ in CATEGORIES],
        pick_category,
        label_builder=lambda name: option_row(
            build_category_label(name, option_text(name))
        ),
        content_width=max(
            category_label_width(name) for name, _ in CATEGORIES
        ),
    )
    cycle_selector = build_option_selector(
        cycle_text,
        [(name, name) for name in db.REPEAT_CYCLES],
        pick_cycle,
        content_width=max(
            len(name) * OPTION_TEXT_SIZE for name in db.REPEAT_CYCLES
        ),
    )

    def close(_: ft.Event[ft.Control] | None = None) -> None:
        dialog.open = False
        set_menu_visible(True)
        page.update()

    def save(_: ft.Event[ft.Control]) -> None:
        content = (todo_field.value or "").strip()
        if not content:
            return
        chosen_day = date.fromisoformat(selection["date"])
        if editing and todo is not None:
            db.update_todo(
                todo.id,
                chosen_day,
                selection["category"],
                content,
                selection["cycle"],
                selection["time"],
            )
        else:
            db.add_todo(
                chosen_day,
                selection["category"],
                content,
                selection["cycle"],
                selection["time"],
            )
        close()
        on_saved(chosen_day)

    dialog = ft.AlertDialog(
        modal=True,
        # Same 12px radius as the 我的 page's 清除 dialog (Material would round it
        # to 28px by default).
        shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
        # Pinned to the shared dialog surface so the option panels opening inside
        # it can be painted the very same colour.
        bgcolor=DIALOG_SURFACE,
        elevation=0,
        title="编辑待办" if editing else "新增待办",
        title_text_style=ft.TextStyle(
            size=16,
            weight=ft.FontWeight.BOLD,
            color="#172554",
        ),
        inset_padding=ft.Padding.symmetric(horizontal=48, vertical=24),
        title_padding=ft.Padding.only(left=16, top=12, right=16, bottom=0),
        content_padding=ft.Padding.only(left=16, top=8, right=16, bottom=8),
        actions_padding=ft.Padding.only(left=8, right=8, bottom=8),
        action_button_padding=ft.Padding.symmetric(horizontal=8),
        on_dismiss=lambda _: set_menu_visible(True),
        content=ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                build_option_row(date_selector),
                build_option_row(time_selector),
                build_option_row(category_selector),
                build_option_row(cycle_selector),
                todo_field,
            ],
        ),
        actions=[
            ft.TextButton("取消", style=dialog_button_style(), on_click=close),
            ft.TextButton("保存", style=dialog_button_style(), on_click=save),
        ],
    )
    page.show_dialog(dialog)
