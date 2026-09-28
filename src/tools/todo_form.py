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
    category_color,
)
from tools.layout import (
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    anchor_dialog_above_keyboard,
    date_label,
    dialog_button_style,
    readable_ink,
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
)

MUTED_COLOR = "#94A3B8"
FIELD_COLOR = "#334155"
# 没填过结束时间时的默认时长：开始时间往后一个小时。
DEFAULT_DURATION_MINUTES = 60
# 三个分类勾选框之间的间距。
CATEGORY_CHECK_GAP = 14


def default_time() -> str:
    """The 时间 a fresh dialog opens on: the clock rounded down."""
    return db.default_time()


def shift_time(value: str, minutes: int) -> str:
    """「09:30」往后推 60 分钟，绕回 00:00 也不越界。"""
    hour, _, minute = value.partition(":")
    total = (int(hour) * 60 + int(minute) + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


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
    # 结束时间没存过就默认「开始 + 1 小时」，两个框任何时候都有值。
    end_time = (
        todo.end_time
        if editing and todo.end_time
        else shift_time(start_time, DEFAULT_DURATION_MINUTES)
    )
    start_category = todo.category if editing else DEFAULT_CATEGORY
    start_cycle = todo.repeat_cycle if editing else db.DEFAULT_CYCLE
    start_hour, _, start_minute = start_time.partition(":")
    end_hour, _, end_minute = end_time.partition(":")

    selection = {
        "date": start_day.isoformat(),
        "time": f"{start_hour}:{start_minute}",
        "end": f"{end_hour}:{end_minute}",
        "category": start_category,
        "cycle": start_cycle,
    }
    date_text = build_option_text(date_label(start_day))
    time_text = build_option_text(selection["time"])
    end_text = build_option_text(selection["end"])
    cycle_text = build_option_text(start_cycle)

    def apply_date(chosen: date) -> None:
        selection["date"] = chosen.isoformat()
        date_text.value = date_label(chosen)
        date_text.update()

    def apply_time(chosen: time) -> None:
        selection["time"] = f"{chosen.hour:02d}:{chosen.minute:02d}"
        time_text.value = selection["time"]
        time_text.update()

    def apply_end(chosen: time) -> None:
        selection["end"] = f"{chosen.hour:02d}:{chosen.minute:02d}"
        end_text.value = selection["end"]
        end_text.update()

    # 新增 only looks forward (today is the earliest day); editing an old row has
    # to be able to keep - or move to - a day in the past.
    date_picker = build_date_picker(
        start_day,
        apply_date,
        first_date=None if editing else midnight(date.today()),
    )
    time_picker = build_time_picker(
        time(int(start_hour), int(start_minute)),
        apply_time,
        help_text="选择开始时间",
    )
    end_picker = build_time_picker(
        time(int(end_hour), int(end_minute)),
        apply_end,
        help_text="选择结束时间",
    )
    date_selector = build_value_trigger(
        date_text, lambda _: page.show_dialog(date_picker)
    )
    time_selector = build_value_trigger(
        time_text, lambda _: page.show_dialog(time_picker)
    )
    end_selector = build_value_trigger(
        end_text, lambda _: page.show_dialog(end_picker)
    )

    def pick_category(name: str, checked: bool) -> None:
        """勾选框做成单选：勾上另一个就松开前一个，而且永远留一个勾着。"""
        if not checked and selection["category"] == name:
            # 想把当前这项取消 → 把这一勾弹回去，不留「一个都没选」的状态。
            category_checks[name].value = True
            category_checks[name].update()
            return
        if checked:
            selection["category"] = name
        for other, box in category_checks.items():
            box.value = other == selection["category"]
            box.update()

    def pick_cycle(name: str) -> None:
        selection["cycle"] = name
        cycle_text.value = name
        cycle_text.update()

    def focus_changed(focused: bool) -> None:
        set_menu_visible(not focused)
        anchor_dialog_above_keyboard(dialog, focused)

    todo_field = ft.TextField(
        value=todo.content if editing else "",
        hint_text="请输入待办内容",
        hint_style=ft.TextStyle(size=13, color=MUTED_COLOR),
        on_focus=lambda _: focus_changed(True),
        on_blur=lambda _: focus_changed(False),
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

    # 分类：三个勾选框并排，勾上另一个自动取消前一个（单选）。勾是分类自己的
    # 颜色，勾里的对号用 `readable_ink` 选深浅，黄底配深蓝、红 / 绿底配白。
    category_checks = {
        name: ft.Checkbox(
            label=name,
            value=name == start_category,
            active_color=color,
            check_color=readable_ink(color),
            label_style=ft.TextStyle(size=OPTION_TEXT_SIZE, color=FIELD_COLOR),
            visual_density=ft.VisualDensity.COMPACT,
            splash_radius=12,
            on_change=lambda event, name=name: pick_category(
                name, bool(event.control.value)
            ),
        )
        for name, color in CATEGORIES
    }
    category_row = ft.Row(
        tight=True,
        spacing=CATEGORY_CHECK_GAP,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=list(category_checks.values()),
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
                selection["end"],
            )
        else:
            db.add_todo(
                chosen_day,
                selection["category"],
                content,
                selection["cycle"],
                selection["time"],
                selection["end"],
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
                # 起止时间并成一行：开始 ~ 结束，两个都是系统的时钟刻度盘。
                build_option_row(
                    ft.Row(
                        tight=True,
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            time_selector,
                            ft.Container(
                                padding=ft.Padding.symmetric(
                                    horizontal=2, vertical=4
                                ),
                                content=ft.Text(
                                    "~", size=12, color=MUTED_COLOR
                                ),
                            ),
                            end_selector,
                        ],
                    )
                ),
                build_option_row(category_row),
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
