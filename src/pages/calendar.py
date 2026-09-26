import calendar
from collections.abc import Callable
from datetime import date

import flet as ft

from tools import db
from tools.categories import CATEGORY_COLORS, build_category_icon, category_color
from tools.countdown_card import (
    ACCENT_COLOR as COUNTDOWN_COLOR,
    build_countdown_card,
    countdowns_on,
)
from tools.countdown_form import open_countdown_form
# The month grid draws the very same day badge as the home date strip: same
# circle, same face, same colours for today, the picked day and the rest.
from pages.home import build_date_badge, date_badge_bg
from tools.pickers import build_date_picker
from tools.layout import (
    BOTTOM_MENU_INSET,
    TODO_DONE_TEXT,
    TODO_TEXT_SIZE,
    TODO_TIME_COLOR,
    TODO_TIME_SIZE,
    build_todo_mark,
    page_gradient,
    todo_text_style,
    todo_time_label,
)
from tools.swipe_delete import build_swipe_delete_row
from tools.todo_form import open_todo_form

DONE_COLOR = "#16A34A"
PENDING_COLOR = "#EAB308"
OVERDUE_COLOR = "#DC2626"
NO_DOT = "#00000000"
# Only days that are already behind us wear their state on the badge: green when
# every todo of that day is done, light yellow while something is still open.
# Today and the days ahead keep the plain badge (neutral, or the selection blue
# for the picked one), so the colours read as "how did that day end up".
PENDING_DAY_BG = "#FEF08A"
DONE_DAY_BG = "#4ADE80"
# Compact month grid. The cell is one row tall and the day itself is the same
# round badge the home strip draws, so the two pages match to the pixel.
DAY_CELL_HEIGHT = 36
# Left-right gap between two day cells (the cells share the row width).
DAY_CELL_SPACING = 6


def build_calendar_page(
    page: ft.Page, set_menu_visible: Callable[[bool], None]
) -> ft.Control:
    today = date.today()
    visible_month = date(today.year, today.month, 1)
    selected_day = today
    month_view = ft.Container()
    selected_content = ft.Container()
    selected_scroll = ft.ListView(
        expand=True,
        scroll=ft.ScrollMode.HIDDEN,
        margin=ft.Margin.only(top=12),
        padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
        controls=[selected_content],
    )
    month_title = ft.Text(
        f"{visible_month.year}年{visible_month.month}月",
        size=17,
        weight=ft.FontWeight.BOLD,
        color="#172554",
    )

    def delete_todo(todo_id: int) -> None:
        db.delete_todo(todo_id)
        update_calendar()

    def remove_countdown(countdown_id: int) -> None:
        db.delete_countdown(countdown_id)
        update_calendar()

    def edit_countdown(item: db.Countdown) -> None:
        open_countdown_form(
            page,
            set_menu_visible=set_menu_visible,
            on_saved=update_calendar,
            item=item,
        )

    def edit_todo(todo_id: int) -> None:
        todo = db.get_todo(todo_id)
        if todo is None:
            return
        open_todo_form(
            page,
            set_menu_visible=set_menu_visible,
            on_saved=lambda _: update_calendar(),
            default_date=todo.due_date,
            todo=todo,
        )

    def todo_card(todo: db.Todo) -> ft.Control:
        lines = [
            ft.Text(
                todo.content,
                size=TODO_TEXT_SIZE,
                # Open todos wear their category's colour; done ones grey out and
                # get the strikethrough.
                color=(
                    TODO_DONE_TEXT
                    if todo.done
                    else category_color(todo.category)
                ),
                style=todo_text_style(todo.done),
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
        card = ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=ft.BorderRadius.all(10),
            # Completed rows keep the neutral card too; the grey struck-through
            # text and the green check carry the done state.
            bgcolor="#F1F5F9",
            content=ft.Row(
                spacing=8,
                controls=[
                    build_todo_mark(todo.done),
                    ft.Column(
                        tight=True,
                        expand=True,
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                        controls=lines,
                    ),
                ],
            ),
        )
        return build_swipe_delete_row(
            card,
            lambda _: delete_todo(todo.id),
            lambda _: edit_todo(todo.id),
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
                    ft.Text(
                        "今天没有待办事项哦", size=13, color="#64748B"
                    ),
                ],
            ),
        )

    def build_selected_content(day: date) -> ft.Control:
        grouped: dict[str, list[db.Todo]] = {}
        for todo in db.list_range(day, day):
            grouped.setdefault(todo.category, []).append(todo)
        names = [name for name in CATEGORY_COLORS if grouped.get(name)]
        names += [name for name in grouped if name not in CATEGORY_COLORS]
        groups: list[ft.Control] = []
        for name in names:
            color = category_color(name)
            groups.append(
                ft.Column(
                    tight=True,
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Row(
                            spacing=6,
                            controls=[
                                build_category_icon(name, size=15),
                                ft.Text(
                                    name,
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=color,
                                ),
                            ],
                        ),
                        *[todo_card(todo) for todo in grouped[name]],
                    ],
                )
            )
        countdowns = countdowns_on(day)
        # The "nothing here" hint only shows for a day that is truly empty - a day
        # that only carries a 倒数日 already has something to show.
        if not names and not countdowns:
            groups.append(build_empty_hint())
        if countdowns:
            groups.append(
                ft.Column(
                    tight=True,
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Icon(
                                    ft.Icons.EVENT,
                                    size=15,
                                    color=COUNTDOWN_COLOR,
                                ),
                                ft.Text(
                                    "倒数日",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=COUNTDOWN_COLOR,
                                ),
                            ],
                        ),
                        *[
                            build_countdown_card(
                                item,
                                today=day,
                                on_delete=lambda _, i=item: remove_countdown(i.id),
                                on_edit=lambda _, i=item: edit_countdown(i),
                            )
                            for item in countdowns
                        ],
                    ],
                )
            )
        return ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[*groups],
        )

    def day_dot_color(day: date, todos: list[db.Todo]) -> str:
        if not todos:
            return NO_DOT
        if all(todo.done for todo in todos):
            return DONE_COLOR
        return OVERDUE_COLOR if day < today else PENDING_COLOR

    def month_todos() -> dict[date, list[db.Todo]]:
        last_day = calendar.monthrange(
            visible_month.year, visible_month.month
        )[1]
        grouped: dict[date, list[db.Todo]] = {}
        for todo in db.list_range(
            visible_month,
            date(visible_month.year, visible_month.month, last_day),
        ):
            grouped.setdefault(todo.due_date, []).append(todo)
        return grouped

    def day_cell(
        day_number: int, day_todos: dict[date, list[db.Todo]]
    ) -> ft.Control:
        if day_number == 0:
            return ft.Container(expand=True, height=DAY_CELL_HEIGHT)

        day = date(visible_month.year, visible_month.month, day_number)
        is_selected = day == selected_day
        todos = day_todos.get(day, [])
        dot_color = day_dot_color(day, todos)
        if is_selected:
            badge_bg = date_badge_bg(True)
        elif day < today and todos:
            badge_bg = (
                DONE_DAY_BG
                if all(todo.done for todo in todos)
                else PENDING_DAY_BG
            )
        else:
            badge_bg = date_badge_bg(False)
        return ft.Container(
            expand=True,
            height=DAY_CELL_HEIGHT,
            alignment=ft.Alignment.CENTER,
            on_click=lambda _: select_day(day),
            content=build_date_badge(
                str(day_number),
                badge_bg,
                extra=(
                    ft.Container(
                        width=3,
                        height=3,
                        border_radius=ft.BorderRadius.all(2),
                        bgcolor=dot_color,
                        border=(
                            ft.Border.all(1, "#FFFFFF")
                            if is_selected and dot_color != NO_DOT
                            else None
                        ),
                    )
                    if dot_color != NO_DOT
                    else None
                ),
            ),
        )

    def build_month_view() -> ft.Control:
        month_days = calendar.monthcalendar(
            visible_month.year, visible_month.month
        )
        day_todos = month_todos()
        return ft.Column(
            tight=True,
            # Row-to-row (and header-to-first-row) gap between the day cards.
            spacing=5,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        ft.Text(
                            weekday,
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color="#64748B",
                        )
                        for weekday in ["一", "二", "三", "四", "五", "六", "日"]
                    ],
                ),
                *[
                    ft.Row(
                        # The cells share the row width, so this left-right gap
                        # sets how wide each day cell gets.
                        spacing=DAY_CELL_SPACING,
                        controls=[day_cell(day, day_todos) for day in week],
                    )
                    for week in month_days
                ],
            ],
        )

    def update_calendar() -> None:
        nonlocal selected_day
        if selected_day.month != visible_month.month or selected_day.year != visible_month.year:
            selected_day = visible_month
        month_view.content = build_month_view()
        selected_content.content = build_selected_content(selected_day)
        month_title.value = f"{visible_month.year}年{visible_month.month}月"
        month_title.update()
        month_view.update()
        selected_content.update()

    def change_month(offset: int) -> None:
        nonlocal visible_month
        month_index = visible_month.month - 1 + offset
        visible_month = date(
            visible_month.year + month_index // 12,
            month_index % 12 + 1,
            1,
        )
        update_calendar()

    def select_day(day: date) -> None:
        nonlocal selected_day
        selected_day = day
        selected_content.content = build_selected_content(day)
        month_view.content = build_month_view()
        month_view.update()
        selected_content.update()

    def jump_to_day(day: date) -> None:
        """Follow a date picked in the system picker: month, selection, list."""
        nonlocal visible_month
        visible_month = date(day.year, day.month, 1)
        select_day(day)
        update_calendar()

    date_picker = build_date_picker(selected_day, jump_to_day)

    def open_date_picker(_: ft.Event[ft.Control]) -> None:
        date_picker.value = selected_day
        page.show_dialog(date_picker)

    month_view.content = build_month_view()
    selected_content.content = build_selected_content(selected_day)

    return ft.Container(
        expand=True,
        gradient=page_gradient(),
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=24, top=24, right=24),
                content=ft.Column(
                    expand=True,
                    # 4px base gap so the month selector sits closer to the grid;
                    # other sections add 12px margins to keep their previous gaps.
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text(
                            "日历",
                            # Same face as the home page's「待办」heading.
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color="#172554",
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            # The month selector sits right under the「日历」
                            # heading: only the column's own gap is left between
                            # them (the icon buttons keep their tap padding).
                            margin=ft.Margin.only(top=0),
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.CHEVRON_LEFT,
                                    tooltip="上个月",
                                    on_click=lambda _: change_month(-1),
                                ),
                                ft.Container(
                                    ink=True,
                                    on_click=open_date_picker,
                                    content=month_title,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CHEVRON_RIGHT,
                                    tooltip="下个月",
                                    on_click=lambda _: change_month(1),
                                ),
                            ],
                        ),
                        month_view,
                        selected_scroll,
                    ],
                ),
            ),
        ),
    )
