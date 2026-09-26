import flet as ft
from collections.abc import Callable
from datetime import date, timedelta

from tools import db
from tools.categories import (
    CATEGORIES,
    DEFAULT_CATEGORY,
    build_category_icon,
)
from tools.layout import (
    BOTTOM_MENU_INSET,
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    SKY_BLUE,
    TODO_DONE_TEXT,
    TODO_TEXT_SIZE,
    TODO_TIME_COLOR,
    TODO_TIME_SIZE,
    TODO_TITLE_SIZE,
    build_todo_mark,
    dialog_button_style,
    page_gradient,
    text_width,
    todo_text_style,
    todo_time_label,
)
from tools.popup_select import (
    OPTION_TEXT_SIZE,
    TRIGGER_TEXT_COLOR,
    TRIGGER_TEXT_SIZE,
    build_option_row,
    build_option_selector,
    build_option_text,
    option_row,
    option_text,
)
from tools.swipe_delete import build_swipe_delete_row

# Shared surface colour of the unselected date card and the undone todo card.
UNSELECTED_CARD_BG = "#F1F5F9"
# The floating add button is a sky-blue glass tile: no border ring, and a
# translucent fill (60%) so the blur behind it shows through.
ADD_BUTTON_BG = "#99" + SKY_BLUE[1:]
# A round tile, lifted clear of the floating menu bar.
ADD_BUTTON_SIZE = 52
ADD_BUTTON_LIFT = 10
# The 日期 picker in the add-todo dialog starts at today and runs this far ahead.
# Today itself is the earliest day it offers.
DATE_RANGE_FORWARD_DAYS = 60
# The date strip is centred on today: three days before, today, three after.
DATE_STRIP_SIDE_DAYS = 3
# The day badges are circles. The picked day - today when the app opens - takes
# this blue; every other day, today included, stays on the neutral card colour.
# Clicking never repaints the weekday or the day number itself.
DATE_SELECTED_BG = "#DCEDF6"
DATE_TEXT_COLOR = "#172554"
DATE_WEEKDAY_COLOR = "#64748B"
# The seven day columns share the strip's width: every column is an expanding
# child of a `Row`, so the free space is split evenly and the strip fills the
# screen on any phone width instead of leaving a gap after the last column.
DATE_CARD_SPACING = 8
DATE_CARD_HEIGHT = 56
DATE_CARD_TOP_PADDING = 2
# Weekday and day number are stacked: the weekday is a plain grey label, the day
# number sits inside its own circular badge.
DATE_WEEKDAY_SIZE = 11
DATE_DAY_SIZE = 15
DATE_BADGE_SIZE = 34
DATE_COLUMN_SPACING = 4
PAGE_SIDE_PADDING = 24
# The dialog's 日期 panel lists every selectable day, so it is height-capped and
# scrolls like the Dropdown it replaced did (menu_height=240).
DATE_MENU_MAX_HEIGHT = 240
# The 类别 picker repeats the star pair the list pages show next to a category
# name (five red stars for 重要, three yellow for 一般, one green for 可选).
CATEGORY_STAR_SIZE = 12
CATEGORY_STAR_GAP = 6


def date_label(day: date) -> str:
    """「2026年9月24日」- option text and trigger text of the 日期 picker."""
    return f"{day.year}年{day.month}月{day.day}日"


def category_label(name: str, text: ft.Control) -> ft.Control:
    """「★★★★★ 重要」- the star pair the list pages show beside a category."""
    return ft.Row(
        tight=True,
        spacing=CATEGORY_STAR_GAP,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            build_category_icon(name, size=CATEGORY_STAR_SIZE),
            text,
        ],
    )


def category_content_width(name: str) -> float:
    """Width of「★ 重要」as a menu entry renders it."""
    return CATEGORY_STAR_SIZE + CATEGORY_STAR_GAP + text_width(
        name, OPTION_TEXT_SIZE
    )


def date_card_label(day: date, today: date) -> str:
    """「今」for today, otherwise the day of the month alone (「25」)."""
    return "今" if day == today else str(day.day)


def date_badge_bg(is_picked: bool) -> str:
    """Background of a day badge - the one rule the strip and the month share.

    The picked day takes the blue; every other day - today included - stays on
    the neutral card colour.
    """
    return DATE_SELECTED_BG if is_picked else UNSELECTED_CARD_BG


def build_date_badge(
    label: str, bgcolor: str, extra: ft.Control | None = None
) -> ft.Control:
    """The round day badge: same size, face and colours on both pages.

    The home strip passes nothing extra; the calendar hands over its todo dot,
    which is drawn under the day number inside the same circle.
    """
    number = ft.Text(
        label,
        size=DATE_DAY_SIZE,
        weight=ft.FontWeight.BOLD,
        color=DATE_TEXT_COLOR,
    )
    return ft.Container(
        width=DATE_BADGE_SIZE,
        height=DATE_BADGE_SIZE,
        shape=ft.BoxShape.CIRCLE,
        bgcolor=bgcolor,
        alignment=ft.Alignment.CENTER,
        content=(
            number
            if extra is None
            else ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=1,
                controls=[number, extra],
            )
        )
    )


def selectable_dates(anchors: list[date]) -> list[date]:
    """Days the 日期 picker offers: today is the earliest one."""
    today = date.today()
    window = {
        today + timedelta(days=offset)
        for offset in range(DATE_RANGE_FORWARD_DAYS + 1)
    }
    return sorted(day for day in window.union(anchors) if day >= today)


def group_todos_by_day(
    todos: list[db.Todo],
) -> dict[date, dict[str, list[db.Todo]]]:
    grouped: dict[date, dict[str, list[db.Todo]]] = {}
    for todo in todos:
        day = grouped.setdefault(todo.due_date, {})
        day.setdefault(todo.category, []).append(todo)
    return grouped


def build_home_page(
    page: ft.Page, set_menu_visible: Callable[[bool], None]
) -> ft.Control:
    # Today sits in the middle of the strip so both neighbours stay visible, and
    # its badge reads 「今」 instead of the day of the month.
    today = date.today()
    dates = [
        today + timedelta(days=offset)
        for offset in range(-DATE_STRIP_SIDE_DAYS, DATE_STRIP_SIDE_DAYS + 1)
    ]
    today_index = DATE_STRIP_SIDE_DAYS
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    todos_by_day = group_todos_by_day(db.list_todos(dates))
    selected_index = today_index
    date_selector = ft.Row(spacing=DATE_CARD_SPACING)
    todo_title = ft.Text(
        "",
        size=TODO_TITLE_SIZE,
        weight=ft.FontWeight.BOLD,
        color="#172554",
    )
    todo_content = ft.ListView(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.HIDDEN,
        padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
    )

    def reload_todos() -> None:
        nonlocal todos_by_day
        todos_by_day = group_todos_by_day(db.list_todos(dates))

    def todo_row(
        todo: db.Todo, completed: bool, category_color: str
    ) -> ft.Row:
        # An open todo borrows its category's colour, so the row reads as part of
        # the group above it; a completed one drops to grey with a strikethrough.
        # Its time of day sits under the text as a quiet grey line.
        lines = [
            ft.Text(
                todo.content,
                size=TODO_TEXT_SIZE,
                color=TODO_DONE_TEXT if completed else category_color,
                style=todo_text_style(completed),
            )
        ]
        if todo.due_time:
            lines.append(
                ft.Text(
                    todo_time_label(todo.due_time),
                    size=TODO_TIME_SIZE,
                    weight=ft.FontWeight.BOLD,
                    color=TODO_TIME_COLOR,
                )
            )
        return ft.Row(
            spacing=8,
            controls=[
                build_todo_mark(completed),
                ft.Column(
                    tight=True,
                    expand=True,
                    spacing=1,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    controls=lines,
                ),
            ],
        )

    def delete_todo(todo_id: int) -> None:
        db.delete_todo(todo_id)
        reload_todos()
        select_date(selected_index)

    def build_todo_item(todo: db.Todo, category_color: str) -> ft.Control:
        completed = todo.done
        todo_card = ft.Container(
            key=f"todo-{todo.id}",
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=ft.BorderRadius.all(10),
            # Both states keep the neutral card: a completed todo is marked by
            # its grey struck-through text and the green check, not by a fill.
            bgcolor=UNSELECTED_CARD_BG,
            content=todo_row(todo, completed, category_color),
        )

        def toggle_todo(_: ft.Event[ft.Container]) -> None:
            nonlocal completed
            completed = not completed
            db.set_done(todo.id, completed)
            reload_todos()
            todo_card.content = todo_row(todo, completed, category_color)
            todo_card.update()

        todo_card.on_click = toggle_todo
        return build_swipe_delete_row(
            todo_card, lambda _: delete_todo(todo.id)
        )

    def build_category_group(
        category: str, category_color: str, items: list[db.Todo]
    ) -> ft.Control:
        return ft.Column(
            tight=True,
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    spacing=6,
                    controls=[
                        build_category_icon(category, size=15),
                        ft.Text(
                            category,
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=category_color,
                        ),
                    ],
                ),
                *[
                    build_todo_item(todo, category_color) for todo in items
                ],
            ],
        )

    def build_empty_hint() -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=ft.BorderRadius.all(12),
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, "#E2E8F0"),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(
                        ft.Icons.EVENT_AVAILABLE,
                        size=20,
                        color="#94A3B8",
                    ),
                    ft.Text("今天没有待办事项哦", size=13, color="#64748B"),
                ],
            ),
        )

    def render_todos(index: int) -> None:
        selected_date = dates[index]
        day_items = todos_by_day.get(selected_date, {})
        groups = [
            build_category_group(name, color, day_items.get(name, []))
            for name, color in CATEGORIES
            if day_items.get(name)
        ]
        todo_title.value = f"{selected_date.month}月{selected_date.day}日待办"
        todo_content.controls = groups or [build_empty_hint()]

    def build_date_item(index: int) -> ft.Control:
        selected_date = dates[index]
        badge_bg = date_badge_bg(index == selected_index)
        return ft.Container(
            key=f"date-{selected_date.isoformat()}",
            expand=1,
            height=DATE_CARD_HEIGHT,
            padding=ft.Padding.only(top=DATE_CARD_TOP_PADDING),
            alignment=ft.Alignment.TOP_CENTER,
            on_click=lambda _: select_date(index),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=DATE_COLUMN_SPACING,
                controls=[
                    ft.Text(
                        weekdays[selected_date.weekday()],
                        size=DATE_WEEKDAY_SIZE,
                        color=DATE_WEEKDAY_COLOR,
                    ),
                    build_date_badge(
                        date_card_label(selected_date, today), badge_bg
                    ),
                ],
            ),
        )

    def select_date(index: int) -> None:
        nonlocal selected_index
        selected_index = index
        date_selector.controls = [
            build_date_item(date_index) for date_index in range(len(dates))
        ]
        render_todos(index)
        date_selector.update()
        todo_title.update()
        todo_content.update()

    def save_todo(
        dialog: ft.AlertDialog,
        todo_field: ft.TextField,
        selection: dict[str, str],
    ) -> None:
        item = (todo_field.value or "").strip()
        if not item:
            return
        selected_date = date.fromisoformat(selection["date"])
        # A repeating cycle also schedules the follow-ups from this start date.
        db.add_todo(
            selected_date,
            selection["category"],
            item,
            selection["cycle"],
            selection["time"],
        )
        reload_todos()
        dialog.open = False
        set_bottom_controls_visible(True)
        if selected_date in dates:
            select_date(dates.index(selected_date))
        page.update()

    def open_add_todo(_: ft.Event[ft.Container]) -> None:
        field_style = {
            "filled": False,
            "border": ft.NoInputBorder(),
            "content_padding": ft.Padding.symmetric(horizontal=0, vertical=6),
            "text_style": ft.TextStyle(size=13, color="#334155"),
            "dense": True,
            # A todo can be a word or a few lines, so the field shows two lines
            # and wraps up to five before it scrolls.
            "multiline": True,
            "min_lines": 2,
            "max_lines": 5,
        }
        # The 日期/类别 pickers are the very same option panel as the 我的 page's
        # 年/月/周 selector. A popup menu button keeps no value of its own, so the
        # picked entries live here and drive the trigger texts.
        # The 日期 panel starts at today, so opening the dialog while a past day
        # of the strip is selected falls back to today as the start date.
        start_day = max(dates[selected_index], date.today())
        # 时间 starts on the current clock, rounded down a step.
        start_hour, _, start_minute = db.default_time().partition(":")
        selection = {
            "date": start_day.isoformat(),
            "time": f"{start_hour}:{start_minute}",
            "category": DEFAULT_CATEGORY,
            "cycle": db.DEFAULT_CYCLE,
        }
        date_text = build_option_text(date_label(start_day))
        hour_text = build_option_text(start_hour)
        minute_text = build_option_text(start_minute)
        category_trigger = ft.Container(
            content=category_label(
                DEFAULT_CATEGORY, build_option_text(DEFAULT_CATEGORY)
            )
        )
        cycle_text = build_option_text(db.DEFAULT_CYCLE)

        def pick_date(key: str) -> None:
            selection["date"] = key
            date_text.value = date_label(date.fromisoformat(key))
            date_text.update()

        def pick_hour(hour: str) -> None:
            hour_text.value = hour
            selection["time"] = f"{hour}:{minute_text.value}"
            hour_text.update()

        def pick_minute(minute: str) -> None:
            minute_text.value = minute
            selection["time"] = f"{hour_text.value}:{minute}"
            minute_text.update()

        def pick_category(name: str) -> None:
            selection["category"] = name
            # Swapping the whole pair keeps the stars in step with the name.
            category_trigger.content = category_label(
                name, build_option_text(name)
            )
            category_trigger.update()

        def pick_cycle(name: str) -> None:
            selection["cycle"] = name
            cycle_text.value = name
            cycle_text.update()

        todo_field = ft.TextField(
            hint_text="请输入待办内容",
            hint_style=ft.TextStyle(size=13, color="#94A3B8"),
            on_focus=lambda _: set_bottom_controls_visible(False),
            on_blur=lambda _: set_bottom_controls_visible(True),
            **field_style,
        )
        date_selector = build_option_selector(
            date_text,
            [(day.isoformat(), date_label(day)) for day in selectable_dates(dates)],
            pick_date,
            max_menu_height=DATE_MENU_MAX_HEIGHT,
            label_builder=lambda label: option_row(option_text(label)),
            content_width=max(
                text_width(date_label(day), OPTION_TEXT_SIZE)
                for day in selectable_dates(dates)
            ),
        )
        category_selector = build_option_selector(
            category_trigger,
            [(name, name) for name, _ in CATEGORIES],
            pick_category,
            label_builder=lambda name: option_row(
                category_label(name, option_text(name))
            ),
            content_width=max(
                category_content_width(name) for name, _ in CATEGORIES
            ),
        )
        # 时间 is two panels - hours and minutes - so any minute can be picked
        # without scrolling a list of preset slots.
        hour_selector = build_option_selector(
            hour_text,
            [(value, value) for value in db.TIME_HOURS],
            pick_hour,
            max_menu_height=DATE_MENU_MAX_HEIGHT,
            content_width=text_width("00", OPTION_TEXT_SIZE),
        )
        minute_selector = build_option_selector(
            minute_text,
            [(value, value) for value in db.TIME_MINUTES],
            pick_minute,
            max_menu_height=DATE_MENU_MAX_HEIGHT,
            content_width=text_width("00", OPTION_TEXT_SIZE),
        )
        time_row = ft.Row(
            tight=True,
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                hour_selector,
                ft.Text(
                    ":",
                    size=TRIGGER_TEXT_SIZE,
                    color=TRIGGER_TEXT_COLOR,
                ),
                minute_selector,
            ],
        )
        cycle_selector = build_option_selector(
            cycle_text,
            [(name, name) for name in db.REPEAT_CYCLES],
            pick_cycle,
            content_width=max(
                text_width(name, OPTION_TEXT_SIZE) for name in db.REPEAT_CYCLES
            ),
        )
        dialog = ft.AlertDialog(
            modal=True,
            # Same 12px radius as the 我的 page's 清除 dialog (Material would
            # round it to 28px by default).
            shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
            # Pinned to the shared dialog surface so the option panels opening
            # inside it can be painted the very same colour.
            bgcolor=DIALOG_SURFACE,
            elevation=0,
            title="新增待办",
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
            on_dismiss=lambda _: set_bottom_controls_visible(True),
            content=ft.Column(
                tight=True,
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    build_option_row(date_selector),
                    build_option_row(time_row),
                    build_option_row(category_selector),
                    build_option_row(cycle_selector),
                    todo_field,
                ],
            ),
            actions=[
                ft.TextButton(
                    "取消",
                    style=dialog_button_style(),
                    on_click=lambda _: close_dialog(dialog),
                ),
                ft.TextButton(
                    "保存",
                    style=dialog_button_style(),
                    on_click=lambda _: save_todo(
                        dialog, todo_field, selection
                    ),
                ),
            ],
        )
        page.show_dialog(dialog)

    def close_dialog(dialog: ft.AlertDialog) -> None:
        dialog.open = False
        set_bottom_controls_visible(True)
        page.update()

    date_selector.controls = [
        build_date_item(index) for index in range(len(dates))
    ]
    render_todos(selected_index)

    add_button = ft.Container(
        right=24,
        # Sits 10px above the floating menu bar, whose height drives the inset.
        bottom=BOTTOM_MENU_INSET + ADD_BUTTON_LIFT,
        width=ADD_BUTTON_SIZE,
        height=ADD_BUTTON_SIZE,
        shape=ft.BoxShape.CIRCLE,
        bgcolor=ADD_BUTTON_BG,
        blur=ft.Blur(20, 20, ft.BlurTileMode.CLAMP),
        content=ft.IconButton(
            icon=ft.Icons.ADD,
            icon_color="#172554",
            icon_size=24,
            tooltip="新增待办",
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
            on_click=open_add_todo,
        ),
    )

    def set_bottom_controls_visible(visible: bool) -> None:
        set_menu_visible(visible)
        add_button.visible = visible
        add_button.update()

    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                gradient=page_gradient(),
                content=ft.Container(
                    expand=True,
                    content=ft.SafeArea(
                        expand=True,
                        content=ft.Container(
                            expand=True,
                            alignment=ft.Alignment.TOP_LEFT,
                            padding=ft.Padding.only(
                                left=PAGE_SIDE_PADDING,
                                top=PAGE_SIDE_PADDING,
                                right=PAGE_SIDE_PADDING,
                            ),
                            content=ft.Column(
                                expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                controls=[
                                    ft.Text(
                                        "待办",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color="#172554",
                                    ),
                                    date_selector,
                                    todo_title,
                                    todo_content,
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            add_button,
        ],
    )
