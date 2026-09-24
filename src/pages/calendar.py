import calendar
from datetime import date

import flet as ft

from tools import db
from tools.swipe_delete import build_swipe_delete_row

CATEGORY_ICONS = {
    "重要": (ft.Icons.PRIORITY_HIGH, "#DC2626"),
    "一般": (ft.Icons.LIST_ALT, "#2563EB"),
    "可选": (ft.Icons.LOW_PRIORITY, "#64748B"),
}
DEFAULT_CATEGORY_STYLE = (ft.Icons.LIST_ALT, "#64748B")
DONE_COLOR = "#16A34A"
PENDING_COLOR = "#EAB308"
OVERDUE_COLOR = "#DC2626"
NO_DOT = "#00000000"


def build_calendar_page(page: ft.Page) -> ft.Control:
    today = date.today()
    visible_month = date(today.year, today.month, 1)
    selected_day = today
    month_view = ft.Container()
    selected_content = ft.Container()
    month_title = ft.Text(
        f"{visible_month.year}年{visible_month.month}月",
        size=17,
        weight=ft.FontWeight.BOLD,
        color="#172554",
    )

    def category_style(name: str) -> tuple[str, str]:
        return CATEGORY_ICONS.get(name, DEFAULT_CATEGORY_STYLE)

    def delete_todo(todo_id: int) -> None:
        db.delete_todo(todo_id)
        update_calendar()

    def todo_card(todo: db.Todo) -> ft.Control:
        card = ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=ft.BorderRadius.all(10),
            bgcolor="#DCFCE7" if todo.done else "#F1F5F9",
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE_OUTLINE
                        if todo.done
                        else ft.Icons.CIRCLE_OUTLINED,
                        size=16,
                        color=DONE_COLOR if todo.done else "#94A3B8",
                    ),
                    ft.Text(
                        todo.content,
                        size=13,
                        color="#166534" if todo.done else "#334155",
                    ),
                ],
            ),
        )
        return build_swipe_delete_row(card, lambda _: delete_todo(todo.id))

    def build_selected_content(day: date) -> ft.Control:
        grouped: dict[str, list[db.Todo]] = {}
        for todo in db.list_range(day, day):
            grouped.setdefault(todo.category, []).append(todo)
        names = [name for name in CATEGORY_ICONS if grouped.get(name)]
        names += [name for name in grouped if name not in CATEGORY_ICONS]
        groups: list[ft.Control] = []
        for name in names:
            icon, color = category_style(name)
            groups.append(
                ft.Column(
                    tight=True,
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Icon(icon, size=16, color=color),
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
        return ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(
                    f"{day.year}年{day.month}月{day.day}日",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color="#172554",
                ),
                ft.Text(
                    "当天暂无待办事项" if not grouped else "当天待办事项",
                    size=13,
                    color="#64748B",
                ),
                *groups,
            ],
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
            return ft.Container(expand=True, height=42)

        day = date(visible_month.year, visible_month.month, day_number)
        is_selected = day == selected_day
        dot_color = day_dot_color(day, day_todos.get(day, []))
        return ft.Container(
            expand=True,
            height=42,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(8),
            bgcolor="#172554" if is_selected else "#F1F5F9",
            on_click=lambda _: select_day(day),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=1,
                controls=[
                    ft.Text(
                        str(day_number),
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF" if is_selected else "#172554",
                    ),
                    ft.Container(
                        width=5,
                        height=5,
                        border_radius=ft.BorderRadius.all(3),
                        bgcolor=dot_color,
                        border=(
                            ft.Border.all(1, "#FFFFFF")
                            if is_selected and dot_color != NO_DOT
                            else None
                        ),
                    ),
                ],
            ),
        )

    def build_month_view() -> ft.Control:
        month_days = calendar.monthcalendar(
            visible_month.year, visible_month.month
        )
        day_todos = month_todos()
        return ft.Column(
            tight=True,
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        ft.Text(
                            weekday,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color="#64748B",
                        )
                        for weekday in ["一", "二", "三", "四", "五", "六", "日"]
                    ],
                ),
                *[
                    ft.Row(
                        spacing=6,
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

    draft_day = selected_day
    date_picker = ft.CupertinoDatePicker(
        value=selected_day,
        locale=ft.Locale("zh", "CN"),
        date_picker_mode=ft.CupertinoDatePickerMode.DATE,
        date_order=ft.CupertinoDatePickerDateOrder.YEAR_MONTH_DAY,
        minimum_year=1900,
        maximum_year=2100,
        show_day_of_week=True,
        item_extent=36,
        height=190,
    )
    date_sheet = ft.CupertinoBottomSheet(content=ft.Container())

    def date_picker_changed(e: ft.Event[ft.CupertinoDatePicker]) -> None:
        nonlocal draft_day
        selected = e.control.value
        draft_day = selected.date() if hasattr(selected, "date") else selected

    def confirm_date_picker(_: ft.Event[ft.Control]) -> None:
        nonlocal visible_month
        visible_month = date(draft_day.year, draft_day.month, 1)
        select_day(draft_day)
        update_calendar()
        date_sheet.open = False
        page.update()

    date_picker.on_change = date_picker_changed
    date_sheet.content = ft.Container(
        bgcolor="#FFFFFF",
        padding=ft.Padding.only(left=20, top=12, right=20, bottom=20),
        content=ft.Column(
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            "选择日期",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color="#172554",
                        ),
                        ft.TextButton(
                            "确定",
                            style=ft.ButtonStyle(
                                padding=ft.Padding.symmetric(horizontal=12)
                            ),
                            on_click=confirm_date_picker,
                        ),
                    ],
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12),
                    content=date_picker,
                ),
            ],
        ),
    )

    def open_date_picker(_: ft.Event[ft.Control]) -> None:
        nonlocal draft_day
        draft_day = selected_day
        date_picker.value = selected_day
        page.show_dialog(date_sheet)

    month_view.content = build_month_view()
    selected_content.content = build_selected_content(selected_day)

    return ft.Container(
        expand=True,
        bgcolor="#FFFFFF",
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=24, top=24, right=24),
                content=ft.Column(
                    expand=True,
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text(
                            "日历",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color="#172554",
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
                        selected_content,
                    ],
                ),
            ),
        ),
    )
