"""待办时间轴：首页的待办列表和日历弹窗共用同一套行。

每行左边是时间，紧跟一条细圆点连成的轴（和时间同一行的那个点是空心圆），右边
是等级标签（分类色底 + 分类名）和待办文字。行之间只留一点缝，点线上下相接看起
来就是一条轴；最上面那行从空心圆开始，上面不再补小圆点。

轴的高度是钉在整行上的（`build_todo_row` 里那个 `top`/`bottom` 都为 0 的定位子）：
卡片被长文字撑高时轴跟着一起长，多出来的高度平分给上下那几颗点、各自拉长成一
小段竖线，所以轴不会在卡片中间断开。

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
# 轴在这一行里的横向位置（时间那一格的右边、宽就是那颗空心圆的直径），以及卡片
# 左边要空出的位置 —— 卡片是整行的定位基准，得自己把「时间 + 轴」那一截让出来。
AXIS_LEFT = TIME_SLOT_WIDTH + TIME_TO_DOT_GAP
LEFT_GUTTER = AXIS_LEFT + NODE_SIZE
# 轴的最矮高度：上下各 3 颗 2px 的点、中间那颗 9px 的空心圆，再加 6 道 3px 的缝，
# 合计 39px —— 就是「点 2px + 缝 3px」原来的样子（一行文字加留白的卡片大约 32px，
# 靠 `build_todo_row` 里那条占位把行垫到这个高度）。卡片被文字撑高时多出来的高度
# 平分给那 6 颗点（见 `_timeline_dot`），轴始终首尾相接。
SPINE_MIN_HEIGHT = (
    (DOTS_ABOVE + DOTS_BELOW) * DOT_SIZE
    + NODE_SIZE
    + (DOTS_ABOVE + DOTS_BELOW) * DOT_GAP
)
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
    """轴上一小段点线，高度交给轴去拉伸（`expand`）。

    一行文字时它就是那颗 2px 的小圆点；卡片被文字撑高时这一段跟着变长，轴上下仍旧
    相接，不会在卡片中间断开。
    """
    return ft.Container(
        width=DOT_SIZE,
        expand=True,
        border_radius=ft.BorderRadius.all(DOT_SIZE / 2),
        bgcolor=color,
    )


def _timeline_spacer() -> ft.Control:
    """首行上方 / 末行下方那段看不见的占位，占掉和别行的点一样高的位置。

    也是 `expand` 的，空心圆才一直停在行的中间。"""
    return ft.Container(width=DOT_SIZE, expand=True)


def _timeline_node(color: str) -> ft.Control:
    """和时间同一行的那个点：空心圆。"""
    return ft.Container(
        width=NODE_SIZE,
        height=NODE_SIZE,
        shape=ft.BoxShape.CIRCLE,
        border=ft.Border.all(NODE_BORDER, color),
    )


def _timeline_axis(first: bool, last: bool, axis_color: str) -> ft.Column:
    """细圆点连成的轴：高度由外面那行给（定位子，`top`/`bottom` 都为 0）。

    首行不往上补点、末行不往下补点，但仍然占掉同样的一段高度，空心圆才和别行一样
    高、停在行的中间。
    """
    above = (
        [_timeline_spacer() for _ in range(DOTS_ABOVE)]
        if first
        else [_timeline_dot(axis_color) for _ in range(DOTS_ABOVE)]
    )
    below = (
        [_timeline_spacer() for _ in range(DOTS_BELOW)]
        if last
        else [_timeline_dot(axis_color) for _ in range(DOTS_BELOW)]
    )
    # 不写死高度：轴上每一段都是 `expand` 的，卡片撑高多少，它们就平摊多少。
    return ft.Column(
        spacing=DOT_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[*above, _timeline_node(axis_color), *below],
    )


def _time_label(todo: db.Todo) -> ft.Control:
    """左边的时间「09:30」（没写时间的是「全天」）。

    和轴一样是定位子、`top`/`bottom` 都为 0，所以它垂直居中，跟着行高走。
    """
    return ft.Container(
        left=0,
        top=0,
        bottom=0,
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
    body = (
        card
        if on_delete is None and on_edit is None
        else ft.Container(
            # 左滑只带走右边的待办，时间和点线留在原地，所以待办裁在自己那一格里，
            # 不会滑到轴上去（见 tools/swipe_delete.py）。
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=build_swipe_delete_row(
                card,
                lambda _: on_delete(todo),
                (lambda _: on_edit(todo)) if on_edit is not None else None,
            ),
        )
    )
    # 整行是一个 `Stack`：卡片（左滑时就是整条能滑的行）是唯一的**非定位**子控件，
    # 这一行多高、多宽都由它说了算；时间和轴是定位子、`top`/`bottom` 都是 0，高度
    # 于是跟着卡片走 —— 卡片被长文字撑高，轴就跟着一起长，不会在中间断开。
    return ft.Stack(
        alignment=ft.Alignment.CENTER,
        controls=[
            ft.Container(
                margin=ft.Margin.only(left=LEFT_GUTTER), content=body
            ),
            # 轴的「最矮身高」：宽 0 的一条占位，一行文字的卡片也保持原来的点距。
            ft.Container(width=0, height=SPINE_MIN_HEIGHT),
            _time_label(todo),
            ft.Container(
                left=AXIS_LEFT,
                top=0,
                bottom=0,
                content=_timeline_axis(first, last, axis_color),
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
