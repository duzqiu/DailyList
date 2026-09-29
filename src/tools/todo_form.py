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
    date_label,
    dialog_button_style,
    track_keyboard,
)
from tools.pickers import (
    build_date_picker,
    build_time_picker,
    build_value_trigger,
    midnight,
)
from tools.popup_select import (
    MENU_HEIGHT,
    OPTION_TEXT_SIZE,
    build_option_row,
    build_option_selector,
    build_option_text,
)
from tools.segmented import build_segmented

MUTED_COLOR = "#94A3B8"
FIELD_COLOR = "#334155"
# 没填过结束时间时的默认时长：开始时间往后一个小时。
DEFAULT_DURATION_MINUTES = 60


def default_time() -> str:
    """The 时间 a fresh dialog opens on: the clock rounded down."""
    return db.default_time()


def shift_time(value: str, minutes: int) -> str:
    """「09:30」往后推 60 分钟，绕回 00:00 也不越界。"""
    hour, _, minute = value.partition(":")
    total = (int(hour) * 60 + int(minute) + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def parse_time(value: str) -> time:
    """「09:30」→ `time(9, 30)`，给时钟刻度盘当初始值。"""
    hour, _, minute = value.partition(":")
    return time(int(hour), int(minute))


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

    selection = {
        "date": start_day.isoformat(),
        "time": start_time,
        "end": end_time,
        "category": start_category,
        "cycle": start_cycle,
    }

    def range_label() -> str:
        """时间那一格的字：起止一起选，所以在同一个格里写「09:30 - 10:30」。"""
        return f"{selection['time']} - {selection['end']}"

    date_text = build_option_text(date_label(start_day))
    time_text = build_option_text(range_label())
    cycle_text = build_option_text(start_cycle)

    def apply_date(chosen: date) -> None:
        selection["date"] = chosen.isoformat()
        date_text.value = date_label(chosen)
        date_text.update()

    def refresh_time() -> None:
        """把选好的起止时间写回时间那一格。"""
        time_text.value = range_label()
        time_text.update()

    # 新增 only looks forward (today is the earliest day); editing an old row has
    # to be able to keep - or move to - a day in the past.
    date_picker = build_date_picker(
        start_day,
        apply_date,
        first_date=None if editing else midnight(date.today()),
    )
    date_selector = build_value_trigger(
        date_text, lambda _: page.show_dialog(date_picker)
    )

    def pick_time_range(_: ft.Event[ft.Control]) -> None:
        """点时间那一格：连着弹两个刻度盘，一次把开始、结束都选完。

        先弹开始时间，选完接着弹结束时间，不用回头再点第二个框。结束时间不能早于
        开始 —— 开始往后挪过了结束（或者正好压上），就把时长补回 1 小时。
        """

        def pick_end(chosen: time) -> None:
            selection["end"] = f"{chosen.hour:02d}:{chosen.minute:02d}"
            refresh_time()

        def pick_start(chosen: time) -> None:
            selection["time"] = f"{chosen.hour:02d}:{chosen.minute:02d}"
            if selection["end"] <= selection["time"]:
                selection["end"] = shift_time(
                    selection["time"], DEFAULT_DURATION_MINUTES
                )
            refresh_time()
            page.show_dialog(
                build_time_picker(
                    parse_time(selection["end"]),
                    pick_end,
                    help_text="选择结束时间",
                )
            )

        page.show_dialog(
            build_time_picker(
                parse_time(selection["time"]),
                pick_start,
                help_text="选择开始时间",
            )
        )

    # 起止时间是一个格：点一下连着把开始、结束都选了（见 pick_time_range）。
    time_selector = build_value_trigger(time_text, pick_time_range)

    def pick_category(name: str) -> None:
        """胶囊自己做单选，这里只记住选中的分类。"""
        selection["category"] = name

    def pick_cycle(name: str) -> None:
        selection["cycle"] = name
        cycle_text.value = name
        cycle_text.update()

    def focus_changed(focused: bool) -> None:
        # 弹窗挪到键盘上方这件事交给 `track_keyboard` 跟着键盘走：焦点事件比键盘
        # 动画早到一步，按它挪会先往下沉一下、键盘升起时再弹回来。
        set_menu_visible(not focused)

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
        # A todo is one short line (a word or a phrase), so this is a plain
        # single-line field: no multiline, no height it could grow into.
    )

    # 分类：三个胶囊并排，选中项填自己的分类色（红 / 黄 / 绿），字色跟着底色挑
    # 深浅（黄底配深蓝、红 / 绿底配白，由 `build_segmented` 决定）。胶囊自己做单选：
    # 点另一档就切过去，点当前这一档不会松开，永远留一个选中。
    category_row = build_segmented(
        [(name, name) for name, _ in CATEGORIES],
        start_category,
        pick_category,
        color_of=category_color,
        square=True,
    )
    cycle_selector = build_option_selector(
        cycle_text,
        [(name, name) for name in db.REPEAT_CYCLES],
        pick_cycle,
        # 周期有十档：面板钉成固定高度，多出来的在里面上下滚。
        menu_height=MENU_HEIGHT,
        content_width=max(
            len(name) * OPTION_TEXT_SIZE for name in db.REPEAT_CYCLES
        ),
    )

    def close(_: ft.Event[ft.Control] | None = None) -> None:
        unwatch_keyboard()
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
        # Same 12px radius as the 设置 page's 清除 dialog (Material would round it
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
        # 点外面 / 按返回关掉时也要把键盘跟随拆掉（保存、取消走 `close`）。
        on_dismiss=lambda _: close(),
        content=ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                build_option_row(category_row),
                todo_field,
                build_option_row(date_selector),
                # 起止时间是一个格「09:30 - 10:30」：点一下连着弹开始、结束两个
                # 刻度盘（见 pick_time_range）。
                build_option_row(time_selector),
                build_option_row(cycle_selector),
            ],
        ),
        actions=[
            ft.TextButton("取消", style=dialog_button_style(), on_click=close),
            ft.TextButton("保存", style=dialog_button_style(), on_click=save),
        ],
    )
    # 键盘一升一落都把弹窗挪到键盘上方 / 回到正中（见 track_keyboard）。
    unwatch_keyboard = track_keyboard(page, dialog)
    page.show_dialog(dialog)
