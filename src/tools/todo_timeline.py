"""待办时间轴：首页的待办列表和日历弹窗共用同一套行。

每行左边是时间，紧跟一条细圆点连成的轴（和时间同一行的那个点是空心圆），右边
是等级标签（分类色底 + 分类名）和待办文字。行之间只留一点缝，点线上下相接看起
来就是一条轴；最上面那行从空心圆开始，上面不再补小圆点。

左滑只带走右边的待办（露出编辑 / 删除），时间和点线留在原地，而且待办裁在自己
那一格里，不会滑到轴上去。
"""

from collections.abc import Callable
from typing import Any

import flet as ft

from tools import db
from tools.categories import category_color
from tools.layout import (
    TODO_DONE_TEXT,
    TODO_TEXT_SIZE,
    TODO_TIME_COLOR,
    TODO_TIME_SIZE,
    UNSELECTED_CARD_BG,
    build_todo_mark,
    readable_ink,
    todo_text_style,
    todo_time_label,
    todo_time_range,
)
from tools.swipe_delete import build_swipe_delete_row

# 时间列 + 点线：最左边时间，紧跟一条细圆点连成的轴。
TIME_SLOT_WIDTH = 40
TIME_TO_DOT_GAP = 6
TIMELINE_COLOR = "#E2E8F0"
DOT_SIZE = 2
DOT_GAP = 3
# 与时间同行的那颗点画成空心圆，一行里上下各补几颗小的把轴连起来。
NODE_SIZE = 9
NODE_BORDER = 1.5
DOTS_ABOVE = 3
DOTS_BELOW = 3
# 轴到待办之间的空当，以及待办前面那枚等级标签。
DOT_TO_TEXT_GAP = 10
CATEGORY_TAG_SIZE = 9
CATEGORY_TAG_PADDING = ft.Padding.symmetric(horizontal=4, vertical=1)
CATEGORY_TAG_RADIUS = 4
CATEGORY_TAG_GAP = 6
ALL_DAY_LABEL = "全天"
# 每条待办自己的一块底色（等级标签也在这一块里）。纯白在首页渐变上太亮、在日历
# 弹窗的灰底上又太跳，统一用全局那张「未选中的卡片」灰：和数据页卡片、分类 tile
# 是同一档（tools/layout.py 的 UNSELECTED_CARD_BG）。
CARD_BG = UNSELECTED_CARD_BG
CARD_RADIUS = 8


def sort_key(todo: db.Todo) -> tuple[bool, str, int]:
    """全天（没有时间）的排最前，其余按时间先后，同一时间按录入顺序。"""
    return (todo.due_time != "", todo.due_time, todo.id)


def sorted_todos(todos: list[db.Todo]) -> list[db.Todo]:
    return sorted(todos, key=sort_key)


def _timeline_dot(color: str) -> ft.Control:
    return ft.Container(
        width=DOT_SIZE,
        height=DOT_SIZE,
        border_radius=ft.BorderRadius.all(DOT_SIZE / 2),
        bgcolor=color,
    )


def _timeline_node(color: str) -> ft.Control:
    """和时间同一行的那个点：空心圆。"""
    return ft.Container(
        width=NODE_SIZE,
        height=NODE_SIZE,
        shape=ft.BoxShape.CIRCLE,
        border=ft.Border.all(NODE_BORDER, color),
    )


def _time_column(
    todo: db.Todo, first: bool, last: bool, axis_color: str
) -> ft.Control:
    """左边不跟着滑动的一块：时间 + 细圆点连成的轴。

    第一行不往上补点、最后一行不往下补点，但仍然留出同样高的一段空位，
    空心圆才和别行一样高。
    """
    dot_step = DOT_SIZE + DOT_GAP
    return ft.Row(
        spacing=TIME_TO_DOT_GAP,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=TIME_SLOT_WIDTH,
                alignment=ft.Alignment.CENTER_RIGHT,
                content=ft.Text(
                    (
                        todo_time_label(todo.due_time)
                        if todo.due_time
                        else ALL_DAY_LABEL
                    ),
                    size=TODO_TIME_SIZE,
                    weight=ft.FontWeight.BOLD,
                    color=TODO_TIME_COLOR,
                ),
            ),
            ft.Column(
                tight=True,
                spacing=DOT_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    *(
                        [
                            ft.Container(
                                width=DOT_SIZE,
                                height=DOTS_ABOVE * dot_step - DOT_GAP,
                            )
                        ]
                        if first
                        else [_timeline_dot(axis_color) for _ in range(DOTS_ABOVE)]
                    ),
                    _timeline_node(axis_color),
                    *(
                        [
                            ft.Container(
                                width=DOT_SIZE,
                                height=DOTS_BELOW * dot_step - DOT_GAP,
                            )
                        ]
                        if last
                        else [_timeline_dot(axis_color) for _ in range(DOTS_BELOW)]
                    ),
                ],
            ),
        ],
    )


def _card_content(todo: db.Todo, color: str) -> ft.Control:
    """待办那一行：等级标签 + 正文，正文上方是灰字起止时间，完成的末尾补绿勾。

    时间只写进卡片；左边那条时间轴照旧只报开始时间。
    """
    time_range = todo_time_range(todo.due_time, todo.end_time)
    body = ft.Column(
        tight=True,
        spacing=0,
        expand=True,
        controls=[
            *(
                [
                    ft.Text(
                        time_range,
                        size=TODO_TIME_SIZE,
                        color=TODO_TIME_COLOR,
                    )
                ]
                if time_range
                else []
            ),
            ft.Text(
                todo.content,
                size=TODO_TEXT_SIZE,
                # 开着的待办用分类色，完成的变灰加删除线。
                color=TODO_DONE_TEXT if todo.done else color,
                style=todo_text_style(todo.done),
            ),
        ],
    )
    return ft.Row(
        spacing=CATEGORY_TAG_GAP,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                padding=CATEGORY_TAG_PADDING,
                border_radius=ft.BorderRadius.all(CATEGORY_TAG_RADIUS),
                bgcolor=color,
                content=ft.Text(
                    todo.category,
                    size=CATEGORY_TAG_SIZE,
                    color=readable_ink(color),
                ),
            ),
            body,
            # 完成的在卡片最后收一枚绿勾，和 layout 里那枚完成态图标是同一枚。
            *([build_todo_mark(todo.done)] if todo.done else []),
        ],
    )


def build_todo_row(
    todo: db.Todo,
    *,
    first: bool = False,
    last: bool = False,
    axis_color: str = TIMELINE_COLOR,
    on_click: Callable[[db.Todo], Any] | None = None,
    on_delete: Callable[[db.Todo], Any] | None = None,
    on_edit: Callable[[db.Todo], Any] | None = None,
) -> ft.Control:
    """时间轴的一行；`on_delete`/`on_edit` 给了就能左滑出那两个按钮。

    `axis_color` 用来让点线适应底色（首页在渐变上偏浅，弹窗里要深一些才看得见）。
    """
    color = category_color(todo.category)
    card = ft.Container(
        key=f"todo-{todo.id}",
        # 待办自己一块白底（标签也在里面），左边留出轴到文字的空当。
        bgcolor=CARD_BG,
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        padding=ft.Padding.only(
            left=DOT_TO_TEXT_GAP, right=12, top=6, bottom=6
        ),
        content=_card_content(todo, color),
    )
    if on_click is not None:
        card.on_click = lambda _: on_click(todo)
    if on_delete is None and on_edit is None:
        return ft.Row(
            spacing=0,
            controls=[
                _time_column(todo, first, last, axis_color),
                ft.Container(expand=True, content=card),
            ],
        )
    return ft.Row(
        spacing=0,
        controls=[
            _time_column(todo, first, last, axis_color),
            ft.Container(
                expand=True,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=build_swipe_delete_row(
                    card,
                    lambda _: on_delete(todo),
                    (lambda _: on_edit(todo)) if on_edit is not None else None,
                ),
            ),
        ],
    )


def build_todo_timeline(
    todos: list[db.Todo],
    *,
    axis_color: str = TIMELINE_COLOR,
    on_click: Callable[[db.Todo], Any] | None = None,
    on_delete: Callable[[db.Todo], Any] | None = None,
    on_edit: Callable[[db.Todo], Any] | None = None,
) -> ft.Control:
    """一整列时间轴：自己会按「全天 → 时间」排好序。"""
    ordered = sorted_todos(todos)
    return ft.Column(
        tight=True,
        spacing=2,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            build_todo_row(
                todo,
                first=index == 0,
                last=index == len(ordered) - 1,
                axis_color=axis_color,
                on_click=on_click,
                on_delete=on_delete,
                on_edit=on_edit,
            )
            for index, todo in enumerate(ordered)
        ],
    )
