import flet as ft
from collections.abc import Callable
from datetime import date, timedelta

from tools import db
from tools.categories import CATEGORIES, DEFAULT_CATEGORY, build_category_icon
from tools.layout import BOTTOM_MENU_INSET, page_gradient
from tools.swipe_delete import build_swipe_delete_row

# Shared surface colour: unselected date card, undone todo card and the add button.
UNSELECTED_CARD_BG = "#F1F5F9"
DATE_RANGE_BACK_DAYS = 7
DATE_RANGE_FORWARD_DAYS = 60
DATE_FIELD_WIDTH = 190
DATE_CARET_WIDTH = 32
DATE_CARET_ALIGN = ft.Alignment(1, 0)
DATE_CARET = ft.Container(
    width=DATE_CARET_WIDTH,
    alignment=DATE_CARET_ALIGN,
    content=ft.Icon(ft.Icons.EXPAND_MORE, size=18, color="#94A3B8"),
)
DATE_CARET_OPEN = ft.Container(
    width=DATE_CARET_WIDTH,
    alignment=DATE_CARET_ALIGN,
    content=ft.Icon(ft.Icons.EXPAND_LESS, size=18, color="#94A3B8"),
)
OPTION_STYLE = ft.ButtonStyle(padding=ft.Padding.only(left=10, right=4))


def selectable_dates(anchors: list[date]) -> list[date]:
    today = date.today()
    window = {
        today + timedelta(days=offset)
        for offset in range(-DATE_RANGE_BACK_DAYS, DATE_RANGE_FORWARD_DAYS + 1)
    }
    return sorted(window.union(anchors))


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
    dates = [date.today() + timedelta(days=offset) for offset in range(7)]
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    todos_by_day = group_todos_by_day(db.list_todos(dates))
    selected_index = 0
    date_selector = ft.ListView(
        horizontal=True,
        height=48,
        spacing=8,
        padding=ft.Padding.only(right=8),
    )
    todo_title = ft.Text(
        "",
        size=16,
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

    def todo_row(item: str, completed: bool) -> ft.Row:
        return ft.Row(
            spacing=8,
            controls=[
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE_OUTLINE
                    if completed
                    else ft.Icons.CIRCLE_OUTLINED,
                    size=16,
                    color="#16A34A" if completed else "#94A3B8",
                ),
                ft.Text(
                    item,
                    size=13,
                    expand=True,
                    color="#166534" if completed else "#334155",
                ),
            ],
        )

    def delete_todo(todo_id: int) -> None:
        db.delete_todo(todo_id)
        reload_todos()
        select_date(selected_index)

    def build_todo_item(todo: db.Todo) -> ft.Control:
        completed = todo.done
        todo_card = ft.Container(
            key=f"todo-{todo.id}",
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=ft.BorderRadius.all(10),
            bgcolor="#DCFCE7" if completed else UNSELECTED_CARD_BG,
            content=todo_row(todo.content, completed),
        )

        def toggle_todo(_: ft.Event[ft.Container]) -> None:
            nonlocal completed
            completed = not completed
            db.set_done(todo.id, completed)
            reload_todos()
            todo_card.bgcolor = "#DCFCE7" if completed else UNSELECTED_CARD_BG
            todo_card.content = todo_row(todo.content, completed)
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
                    build_todo_item(todo) for todo in items
                ],
            ],
        )

    def build_empty_hint() -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=18),
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
            for name, color, _ in CATEGORIES
            if day_items.get(name)
        ]
        todo_title.value = f"{selected_date.month}月{selected_date.day}日待办"
        todo_content.controls = groups or [build_empty_hint()]

    def build_date_item(index: int) -> ft.Control:
        selected = index == selected_index
        selected_date = dates[index]
        return ft.Container(
            key=f"date-{selected_date.isoformat()}",
            width=42,
            height=42,
            padding=ft.Padding.symmetric(horizontal=4, vertical=3),
            border_radius=ft.BorderRadius.all(6),
            bgcolor="#172554" if selected else UNSELECTED_CARD_BG,
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=lambda _: select_date(index),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
                controls=[
                    ft.Text(
                        weekdays[selected_date.weekday()],
                        size=9,
                        color="#FFFFFF" if selected else "#64748B",
                    ),
                    ft.Text(
                        str(selected_date.day),
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF" if selected else "#172554",
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
        date_field: ft.Dropdown,
        category_field: ft.Dropdown,
    ) -> None:
        item = (todo_field.value or "").strip()
        if not item or date_field.value is None or category_field.value is None:
            return
        selected_date = date.fromisoformat(str(date_field.value))
        db.add_todo(selected_date, category_field.value, item)
        reload_todos()
        dialog.open = False
        set_bottom_controls_visible(True)
        if selected_date in dates:
            select_date(dates.index(selected_date))
        page.update()

    def open_add_todo(_: ft.Event[ft.Container]) -> None:
        flat_style = {
            "filled": False,
            "border": ft.NoInputBorder(),
            "content_padding": ft.Padding.symmetric(horizontal=0, vertical=6),
            "text_style": ft.TextStyle(size=13, color="#334155"),
            "dense": True,
            "height": 40,
        }
        select_style = {
            **flat_style,
            "trailing_icon": ft.Icon(
                ft.Icons.EXPAND_MORE,
                size=18,
                color="#94A3B8",
            ),
            "selected_trailing_icon": ft.Icon(
                ft.Icons.EXPAND_LESS,
                size=18,
                color="#94A3B8",
            ),
            "menu_style": ft.MenuStyle(
                bgcolor="#FFFFFF",
                elevation=2,
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=6),
                side=ft.BorderSide(0),
            ),
        }
        date_select_style = {
            **select_style,
            "trailing_icon": DATE_CARET,
            "selected_trailing_icon": DATE_CARET_OPEN,
        }
        todo_field = ft.TextField(
            hint_text="请输入待办内容",
            hint_style=ft.TextStyle(size=13, color="#94A3B8"),
            on_focus=lambda _: set_bottom_controls_visible(False),
            on_blur=lambda _: set_bottom_controls_visible(True),
            **flat_style,
        )
        date_field = ft.Dropdown(
            width=DATE_FIELD_WIDTH,
            value=dates[selected_index].isoformat(),
            options=[
                ft.DropdownOption(
                    key=item.isoformat(),
                    text=f"{item.year}年{item.month}月{item.day}日",
                    style=OPTION_STYLE,
                )
                for item in selectable_dates(dates)
            ],
            menu_height=240,
            **date_select_style,
        )
        category_field = ft.Dropdown(
            width=88,
            value=DEFAULT_CATEGORY,
            options=[
                ft.DropdownOption(key=name, text=name, style=OPTION_STYLE)
                for name, _, _ in CATEGORIES
            ],
            menu_height=160,
            **select_style,
        )
        dialog = ft.AlertDialog(
            modal=True,
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
                    ft.Row(controls=[date_field]),
                    ft.Row(controls=[category_field]),
                    todo_field,
                ],
            ),
            actions=[
                ft.TextButton(
                    "取消",
                    on_click=lambda _: close_dialog(dialog),
                ),
                ft.TextButton(
                    "保存",
                    on_click=lambda _: save_todo(
                        dialog, todo_field, date_field, category_field
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
        bottom=88,
        width=52,
        height=52,
        border_radius=ft.BorderRadius.all(16),
        bgcolor=UNSELECTED_CARD_BG,
        border=ft.Border.all(1, "#80FFFFFF"),
        blur=ft.Blur(20, 20, ft.BlurTileMode.CLAMP),
        content=ft.IconButton(
            icon=ft.Icons.ADD,
            icon_color="#172554",
            icon_size=24,
            tooltip="新增待办",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=16)
            ),
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
                            padding=ft.Padding.only(left=24, top=24, right=24),
                            content=ft.Column(
                                expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                controls=[
                                    ft.Text(
                                        "待办",
                                        size=22,
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
