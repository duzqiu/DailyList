import flet as ft
from collections.abc import Callable
from datetime import date, timedelta

from tools import db
from tools.categories import CATEGORIES, build_category_icon
from tools.layout import (
    BOTTOM_MENU_INSET,
    DATE_SELECTED_BG,
    SKY_BLUE,
    TODO_DONE_TEXT,
    TODO_TEXT_SIZE,
    TODO_TIME_COLOR,
    TODO_TIME_SIZE,
    TODO_TITLE_SIZE,
    UNSELECTED_CARD_BG,
    build_todo_mark,
    page_gradient,
    todo_text_style,
    todo_time_label,
)
from tools.swipe_delete import build_swipe_delete_row
from tools.todo_form import open_todo_form

# The floating add button is a sky-blue glass tile: no border ring, and a
# translucent fill (60%) so the blur behind it shows through.
ADD_BUTTON_BG = "#99" + SKY_BLUE[1:]
# A round tile, lifted clear of the floating menu bar.
ADD_BUTTON_SIZE = 52
ADD_BUTTON_LIFT = 10
# The date strip is centred on today: three days before, today, three after.
DATE_STRIP_SIDE_DAYS = 3
# The day badges are circles. The picked day - today when the app opens - takes
# DATE_SELECTED_BG (shared with the 日历 grid and the dialog calendars, see
# tools/layout.py); every other day, today included, stays on the neutral card
# colour. Clicking never repaints the weekday or the day number itself.
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
            todo_card,
            lambda _: delete_todo(todo.id),
            lambda _: edit_todo(todo.id),
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

    def refresh_after_save(saved_day: date) -> None:
        """Re-read the list and follow a todo that landed on the shown week."""
        reload_todos()
        if saved_day in dates:
            select_date(dates.index(saved_day))
        page.update()

    def open_add_todo(_: ft.Event[ft.Container]) -> None:
        open_todo_form(
            page,
            set_menu_visible=set_bottom_controls_visible,
            on_saved=refresh_after_save,
            default_date=max(dates[selected_index], date.today()),
        )

    def edit_todo(todo_id: int) -> None:
        todo = db.get_todo(todo_id)
        if todo is None:
            return
        open_todo_form(
            page,
            set_menu_visible=set_bottom_controls_visible,
            on_saved=refresh_after_save,
            default_date=todo.due_date,
            todo=todo,
        )

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
