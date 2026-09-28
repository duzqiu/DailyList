"""待办时间轴：首页的待办列表和日历弹窗共用同一套行。

每行左边是时间，紧跟一条细圆点连成的轴（和时间同一行的那个点是空心圆），右边
是等级标签（分类色底 + 分类名）和待办文字。行之间只留一点缝，点线上下相接看起
来就是一条轴；最上面那行从空心圆开始，上面不再补小圆点。

轴的高度是钉在整行上的（`build_todo_row` 里那个 `top`/`bottom` 都为 0 的定位子）：
卡片被长文字撑高时轴跟着一起长，多出来的高度平分给上下那几颗点当**间距**，点本身
仍旧是一颗圆的「.」—— 轴既不会在卡片中间断开，也不会被拉成一条竖杠。

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

# 时间列 + 点线：最左边时间，紧跟一条细圆点连成的轴。时间的摆法有两档（见下面的
# TIME_ALIGN_*），两档字后面剩的空差很多，所以格子宽和轴的位置也各给一套尺寸：
#   首页：时间在 40px 的格子里**居中**（对住日期条的「周一」），字后本来就空着半格，
#         轴直接压进那段空里，空心圆就紧跟着时间；
#   弹窗：时间**靠左**（对住分组小标题的图标），字后空得更多，格子于是收到刚够最宽的
#         时间（「00:00」约 30px），轴贴着格子右边，圆两头都挨得近。
TIME_SLOT_WIDTH = 40
AXIS_INTO_SLOT_GAP = 2
TIME_SLOT_WIDTH_DIALOG = 32
# 空心圆右边离待办卡片留一点缝，卡片不会被轴贴住。
AXIS_TO_CARD_GAP = 4
# 时间在那一格（0..TIME_SLOT_WIDTH）里靠哪边摆。首页日期条头一格的「周一」和日期
# 徽标共用一条中线，所以首页的时间也摆在格子正中，正好落在「周一」底下；当天弹窗
# 里时间上方是分组小标题的图标，图标贴着最左边，时间就跟着靠左，两者的左沿对齐。
TIME_ALIGN_STRIP = ft.Alignment.CENTER
TIME_ALIGN_DIALOG = ft.Alignment.CENTER_LEFT
TIMELINE_COLOR = "#E2E8F0"
DOT_SIZE = 2
DOT_GAP = 3
# 与时间同行的那颗点画成空心圆，一行里上下各补几颗小的把轴连起来。
NODE_SIZE = 9
NODE_BORDER = 1.5
DOTS_ABOVE = 3
DOTS_BELOW = 3
# 一行时间轴的横向尺寸：时间那一格多宽、轴摆在哪（宽就是那颗空心圆的直径）、卡片左边
# 让出多少 —— 卡片是整行的定位基准，得自己把「时间 + 轴 + 右空当」那一截让出来。
AXIS_LEFT = TIME_SLOT_WIDTH - AXIS_INTO_SLOT_GAP
LEFT_GUTTER = AXIS_LEFT + NODE_SIZE + AXIS_TO_CARD_GAP
# 弹窗那档：格子收窄了，轴就贴着格子右边，卡片也跟着往前挪。
AXIS_LEFT_DIALOG = TIME_SLOT_WIDTH_DIALOG
LEFT_GUTTER_DIALOG = AXIS_LEFT_DIALOG + NODE_SIZE + AXIS_TO_CARD_GAP
# 轴的最矮高度：上下各 3 颗 2px 的点、中间那颗 9px 的空心圆，再加 6 道 3px 的缝，
# 合计 39px —— 就是「点 2px + 缝 3px」原来的样子（一行文字加留白的卡片大约 32px，
# 靠 `build_todo_row` 里那条占位把行垫到这个高度）。卡片被文字撑高时多出来的高度
# 平分给那 6 颗点当间距（见 `_timeline_dot`），点本身不跟着变长。
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


def timeline_metrics(
    time_align: ft.Alignment = TIME_ALIGN_STRIP,
) -> tuple[float, float, float]:
    """一行时间轴的横向尺寸：(时间格宽, 轴左沿, 卡片左边让出多少)。

    时间的摆法决定用哪一套 —— 首页居中、弹窗靠左，见文件开头那两档。
    """
    if time_align == TIME_ALIGN_DIALOG:
        return TIME_SLOT_WIDTH_DIALOG, AXIS_LEFT_DIALOG, LEFT_GUTTER_DIALOG
    return TIME_SLOT_WIDTH, AXIS_LEFT, LEFT_GUTTER


def sort_key(todo: db.Todo) -> tuple[bool, str, int]:
    """全天（没有时间）的排最前，其余按时间先后，同一时间按录入顺序。"""
    return (todo.due_time != "", todo.due_time, todo.id)


def sorted_todos(todos: list[db.Todo]) -> list[db.Todo]:
    return sorted(todos, key=sort_key)


def _timeline_dot(color: str) -> ft.Container:
    """轴上一格：整格拉满当间距，画出来的永远是一颗小圆点。

    一行文字时这一格就是 2px，看起来就是原来那颗点；卡片被文字撑高时格子跟着变长，
    但点本身还是 `DOT_SIZE` 见方的一颗圆点（`.`），不会被拉成一条竖杠 —— 被拉开的
    只是点与点之间的距离，轴照样从卡片顶上贯到卡片底下。
    """
    return ft.Container(
        width=DOT_SIZE,
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.Container(
            width=DOT_SIZE,
            height=DOT_SIZE,
            border_radius=ft.BorderRadius.all(DOT_SIZE / 2),
            bgcolor=color,
        ),
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


def _time_label(
    todo: db.Todo, align: ft.Alignment, slot_width: float
) -> ft.Control:
    """左边的时间「09:30」（没写时间的是「全天」），灰字、不加粗。

    和轴一样是定位子、`top`/`bottom` 都为 0，所以它垂直居中，跟着行高走；`align`
    决定它在那一格里靠哪边 —— 首页居中（对住日期条的「周一」），弹窗靠左（对住分组
    小标题的图标）；`slot_width` 是那一格的宽，见 timeline_metrics。
    """
    return ft.Container(
        left=0,
        top=0,
        bottom=0,
        width=slot_width,
        alignment=align,
        content=ft.Text(
            (
                todo_time_label(todo.due_time)
                if todo.due_time
                else ALL_DAY_LABEL
            ),
            size=TODO_TIME_SIZE,
            # 轴旁边只是一格灰色小字，不加粗 —— 加粗会和右边的正文抢眼。
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
    time_align: ft.Alignment = TIME_ALIGN_STRIP,
    on_click: Callable[[db.Todo], Any] | None = None,
    on_delete: Callable[[db.Todo], Any] | None = None,
    on_edit: Callable[[db.Todo], Any] | None = None,
) -> ft.Control:
    """时间轴的一行；`on_delete`/`on_edit` 给了就能左滑出那两个按钮。

    `axis_color` 用来让点线适应底色（首页在渐变上偏浅，弹窗里要深一些才看得见）；
    `time_align` 决定左边那格时间靠哪边摆，见 TIME_ALIGN_STRIP / TIME_ALIGN_DIALOG。
    """
    slot_width, axis_left, left_gutter = timeline_metrics(time_align)
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
                margin=ft.Margin.only(left=left_gutter), content=body
            ),
            # 轴的「最矮身高」：宽 0 的一条占位，一行文字的卡片也保持原来的点距。
            ft.Container(width=0, height=SPINE_MIN_HEIGHT),
            _time_label(todo, time_align, slot_width),
            ft.Container(
                left=axis_left,
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
    time_align: ft.Alignment = TIME_ALIGN_STRIP,
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
                time_align=time_align,
                on_click=on_click,
                on_delete=on_delete,
                on_edit=on_edit,
            )
            for index, todo in enumerate(ordered)
        ],
    )
