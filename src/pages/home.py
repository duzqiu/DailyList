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
    SKY_BLUE,
    TODO_DONE_BG,
    TODO_DONE_ICON,
    TODO_TEXT,
    page_gradient,
    text_width,
)
from tools.popup_select import (
    OPTION_TEXT_SIZE,
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
# translucent fill (60%) so the blur behind it shows through. Kept independent
# of TODO_DONE_BG, which is the colour of a completed todo card.
ADD_BUTTON_BG = "#99" + SKY_BLUE[1:]
DATE_RANGE_BACK_DAYS = 7
DATE_RANGE_FORWARD_DAYS = 60
# The seven day cards share the strip's width: every card is an expanding child
# of a `Row`, so the free space is split evenly and the strip fills the screen
# on any phone width instead of leaving a gap after the last 42px card.
DATE_CARD_SPACING = 8
DATE_CARD_HEIGHT = 42
DATE_CARD_SIDE_PADDING = 4
# The date line carries the month. Below this card width 「9月25日」 no longer
# fits between the card's paddings and the label shortens to 「9.25」.
DATE_DAY_SIZE = 13
PAGE_SIDE_PADDING = 24
DATE_FALLBACK_PAGE_WIDTH = 390
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


def date_card_width(page: ft.Page) -> float:
    """Width one of the seven date cards gets on the current window."""
    page_width = getattr(page, "width", None) or DATE_FALLBACK_PAGE_WIDTH
    return (
        page_width - 2 * PAGE_SIDE_PADDING - 6 * DATE_CARD_SPACING
    ) / 7


def date_card_label(day: date, card_width: float) -> str:
    """「9月25日」, shortened to「9.25」when the card is too narrow for it."""
    full = f"{day.month}月{day.day}日"
    if text_width(full, DATE_DAY_SIZE) <= card_width - 2 * DATE_CARD_SIDE_PADDING:
        return full
    return f"{day.month}.{day.day}"


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
    # The seven cards share the window width, which decides whether their date
    # line can spell out 「9月25日」 or has to shorten to 「9.25」.
    date_width = date_card_width(page)
    date_selector = ft.Row(spacing=DATE_CARD_SPACING)
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
                    color=TODO_DONE_ICON if completed else "#94A3B8",
                ),
                ft.Text(
                    item,
                    size=13,
                    expand=True,
                    color=TODO_TEXT,
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
            bgcolor=TODO_DONE_BG if completed else UNSELECTED_CARD_BG,
            content=todo_row(todo.content, completed),
        )

        def toggle_todo(_: ft.Event[ft.Container]) -> None:
            nonlocal completed
            completed = not completed
            db.set_done(todo.id, completed)
            reload_todos()
            todo_card.bgcolor = TODO_DONE_BG if completed else UNSELECTED_CARD_BG
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
            for name, color in CATEGORIES
            if day_items.get(name)
        ]
        todo_title.value = f"{selected_date.month}月{selected_date.day}日待办"
        todo_content.controls = groups or [build_empty_hint()]

    def build_date_item(index: int) -> ft.Control:
        selected = index == selected_index
        selected_date = dates[index]
        return ft.Container(
            key=f"date-{selected_date.isoformat()}",
            expand=1,
            height=DATE_CARD_HEIGHT,
            padding=ft.Padding.symmetric(
                horizontal=DATE_CARD_SIDE_PADDING, vertical=3
            ),
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
                        date_card_label(selected_date, date_width),
                        size=DATE_DAY_SIZE,
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
        selection: dict[str, str],
    ) -> None:
        item = (todo_field.value or "").strip()
        if not item:
            return
        selected_date = date.fromisoformat(selection["date"])
        # A repeating cycle also schedules the follow-ups from this start date.
        db.add_todo(
            selected_date, selection["category"], item, selection["cycle"]
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
        selection = {
            "date": dates[selected_index].isoformat(),
            "category": DEFAULT_CATEGORY,
            "cycle": db.DEFAULT_CYCLE,
        }
        date_text = build_option_text(date_label(dates[selected_index]))
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
                    build_option_row(category_selector),
                    build_option_row(cycle_selector),
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
        bottom=88,
        width=52,
        height=52,
        border_radius=ft.BorderRadius.all(16),
        bgcolor=ADD_BUTTON_BG,
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
