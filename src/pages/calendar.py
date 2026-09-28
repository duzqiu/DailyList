"""日历页：月历本身就是内容，不再在下面另开一张待办列表。

日期格子没有底色，颜色全在「条目」上：当天每条待办都是一颗属于自己颜色的小圆点
（重要红 / 一般黄 / 可选绿），已完成的那颗同色淡一半，同一天的倒数日用倒数日的
天蓝色、过期的那颗用灰。选中的日期只在日期数字外面套一个统一的圆形底色，格子
本身不变色。一天有几条待办就画几个点，从左往右排，格子放不下时圆点自己换行。
"""

import calendar
import math
from collections.abc import Callable
from datetime import date

import flet as ft

from tools import db
from tools.categories import category_color
from tools.countdown_card import (
    ACCENT_COLOR as COUNTDOWN_COLOR,
    EXPIRED_CHIP_BG,
    build_countdown_card,
    countdown_expired,
    countdowns_on,
)
from tools.countdown_form import open_countdown_form
from tools.layout import (
    BOTTOM_MENU_INSET,
    # 选中日期的那圈圆形底色：和首页日期条、数据页日期选择器同一个蓝。
    DATE_SELECTED_BG,
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    TODO_TEXT_SIZE,
    TODO_TIME_SIZE,
    page_gradient,
    text_width,
)
from tools.lunar import lunar_label
from tools.pickers import build_date_picker
from tools.todo_timeline import (
    SPINE_MIN_HEIGHT,
    build_todo_timeline,
    sorted_todos,
)
from tools.todo_form import open_todo_form

TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
# 卡片之间的左右间隔（卡片平分行宽，间隔越小卡片越宽）。
DAY_CELL_SPACING = 4
# 日期数字外面的圆：只有选中的那天填色。
DAY_BADGE_SIZE = 22
DAY_NUMBER_SIZE = 12
# 日期右边那行农历：比日期小一号、灰色，只放日子（「廿三」）放得下。
LUNAR_SIZE = 7
# 格子里的待办不再写字：一个实心小圆点代替，颜色就是它自己的颜色。一天有几条就
# 画几个点，从左往右排；一格横里摆不下时点自己换到下一行，不硬凑也不省略。
DOT_SIZE = 6
DOT_GAP = 2
# 格子正文里控件之间的行距：日期和圆点几行挨紧，格子的高度才压得住。
CELL_SPACING = 1
# 格子自己的留白：左右/上下各 2 的内边距 + 各 1 的描边，横竖都占掉 6。
CELL_HORIZONTAL_CHROME = 6
CELL_VERTICAL_CHROME = 6
# 日历一行 7 天；页面左右各留 24 的边。
CALENDAR_COLUMNS = 7
PAGE_HORIZONTAL_INSETS = 48
# 宽度还没量到时先按手机竖屏估一个（和 data.py 里 trend_width 的兜底一个来路）。
ESTIMATED_PAGE_WIDTH = 400
# 高度再松两像素：行数算得刚好时，最后一行点也不会顶到描边上。
CELL_HEIGHT_SLACK = 2


def estimated_grid_width() -> float:
    """量不到宽度时的兜底：按估的页宽算一行 7 格有多宽。"""
    return ESTIMATED_PAGE_WIDTH - PAGE_HORIZONTAL_INSETS


def cell_width(row_width: float) -> float:
    """一格的宽度：整行（或整页减掉左右留白）等分 7 格。"""
    return max(
        0.0,
        (row_width - DAY_CELL_SPACING * (CALENDAR_COLUMNS - 1))
        / CALENDAR_COLUMNS,
    )


def cell_inner_width(row_width: float) -> float:
    """一格真正能摆点的净宽度：格子宽再减掉自己的留白。"""
    return max(0.0, cell_width(row_width) - CELL_HORIZONTAL_CHROME)


def dots_per_run(inner_width: float) -> int:
    """一行摆得下几个点（点之间还要留 DOT_GAP）—— 至少一个。"""
    return max(1, int((inner_width + DOT_GAP) // (DOT_SIZE + DOT_GAP)))


def dot_row_count(count: int, per_run: int) -> int:
    """这么多个点要摆几行：`Row` 按宽度自己折行，行数这里先算出来。"""
    return max(1, math.ceil(count / per_run))


def cell_height(rows: int) -> float:
    """一个日期格子的高度：日期行 + rows 行圆点（含行距）+ 上下留白。

    一个月里所有格子都用同一个高度，取当月最忙那天要的行数（见 build_month_view）：
    点少的格子空一点不要紧，点多的那天绝不会被格子切掉半截。
    """
    dots = rows * DOT_SIZE + (rows - 1) * DOT_GAP
    return (
        CELL_VERTICAL_CHROME
        + DAY_BADGE_SIZE
        + CELL_SPACING
        + dots
        + CELL_HEIGHT_SLACK
    )


def cell_min_height(row_width: float) -> float:
    """一格最矮能矮到哪：至少摆得下一行点，而且至少是个正方形（高 = 宽）。"""
    return max(cell_width(row_width), cell_height(1))


# 宽度还没量到时（按估的页宽）一格的最矮高度：正方形，比一行点的高度还高一点。
# 真高度按当月最忙那天要的行数往上长（见 build_month_view）。
DAY_CELL_HEIGHT = cell_min_height(estimated_grid_width())


# 弹窗标题和分组名比正文小一档（弹窗比卡片宽松，但内容多）。
DIALOG_TITLE_SIZE = 15
DIALOG_GROUP_SIZE = 12
# 弹窗里的分组小标题（待办 / 倒数日）：图标 + 名称，统一用正文的深色。
DIALOG_SECTION_COLOR = TITLE_COLOR
# 弹窗表面（#E4E9EF）比首页底色深，点线要跟着深一点才看得见。
DIALOG_AXIS_COLOR = "#CBD5E1"
# 当天弹窗正文的最高高度：内容比这矮时弹窗贴着内容收缩，超过就钉在这个高度上滚
# （正文的高度是量出来的 —— 见 open_day_dialog 里的 `content`）。
DIALOG_BODY_MAX_HEIGHT = 330
# 下面的估高只服务于第一帧：量高度（见 open_day_dialog 里那层探针）得等一帧，
# 所以弹窗第一帧先按估的高度把正文撑起来。估得准，开出来第一帧就是最终高度；
# 估低了，内容超过上限的那些天会先按全部内容撑高一下再收回去（点日期时看到的那
# 一闪）。所以下面每一项都往大了估：宁可先高一点、下一帧收回，也别先矮了再撑开。
# 分组小标题：图标 13 + 名称 12（section_header）。
GROUP_EST = 18
# 分组里标题和条目之间、条目之间的行距（day_groups 里的 spacing）。
GROUP_GAP = 6
# 正文里「待办」「倒数日」两组之间的间距（body 的 spacing）。
BODY_GAP = 8
# 时间轴的行距（build_todo_timeline 的 spacing），以及卡片上下各 6 的留白。
TODO_ROW_GAP = 2
TODO_CARD_PADDING = 12
# 卡片里每行文字的高度：字号 × 1.35（Flutter 的默认行高）。
TODO_LINE_EST = TODO_TEXT_SIZE * 1.35
TODO_TIME_EST = TODO_TIME_SIZE * 1.35
# 弹窗里待办文字那一列大约多宽（手机竖屏量出来的数），用来估长文字会折几行。
TODO_TEXT_SLOT = 180
# 倒数日卡片是定高的（见 tools/countdown_card.py）：上段 30 + 中段 42 + 虚线 1
# + 下段 39 + 边框 2。
COUNTDOWN_EST = 114
# 「这天没有待办事项」那块（empty_hint）：上下 10 的留白 + 20 的图标 + 边框。
EMPTY_HINT_EST = 44
# 日期格子的描边：比卡片边框 #E2E8F0 再淡一点点，只要把格子界限画出来。
CELL_BORDER = "#E2E8F0"
WEEKDAYS = ("一", "二", "三", "四", "五", "六", "日")


def lunar_short(day: date) -> str:
    """卡片右角那半截农历。

    格子只有一行位置：平常只写日子（「廿三」），碰上初一就写月份（「八月」）
    —— 一个月里出现两次「初一」这种信息量为零的写法不如报月份。
    """
    label = lunar_label(day)
    month, separator, rest = label.partition("月")
    if separator and rest in ("", "初一"):
        return f"{month}月"
    return rest or label


def estimate_day_height(day: date) -> float:
    """当天弹窗正文大概有多高（第一帧先拿它撑起来，见 open_day_dialog）。

    只按布局粗算：一条待办取「时间轴最矮身高」和「卡片留白 + 折行数」的大者，
    倒数日卡片是定高的，分组标题和间距都照实加起来。宁可多算一点 —— 估高了下一
    帧就收回去，估低了才会出现「先按全部内容撑高一下」的那一闪。
    """
    todos = db.list_range(day, day)
    countdowns = countdowns_on(day)
    if not todos and not countdowns:
        return EMPTY_HINT_EST
    groups: list[float] = []
    if todos:
        rows: list[float] = []
        for todo in todos:
            lines = max(
                1,
                math.ceil(
                    text_width(todo.content, TODO_TEXT_SIZE)
                    / TODO_TEXT_SLOT
                ),
            )
            card = TODO_CARD_PADDING + lines * TODO_LINE_EST
            if todo.due_time or todo.end_time:
                card += TODO_TIME_EST
            rows.append(max(SPINE_MIN_HEIGHT, card))
        groups.append(
            GROUP_EST
            + GROUP_GAP
            + sum(rows)
            + TODO_ROW_GAP * (len(rows) - 1)
        )
    if countdowns:
        count = len(countdowns)
        groups.append(
            GROUP_EST
            + GROUP_GAP
            + count * COUNTDOWN_EST
            + (count - 1) * GROUP_GAP
        )
    return sum(groups) + BODY_GAP * (len(groups) - 1)


def build_calendar_page(
    page: ft.Page,
    set_menu_visible: Callable[[bool], None],
    state: dict[str, object],
    open_settings: Callable[[], None],
) -> ft.Control:
    """日历页。`state` 由调用方保管（见 pages/navigation.py）：翻到哪个月、
    选中了哪一天要能跨 Tab 留住，切走再回来不会被拉回今天。控件本身照旧每次
    重建，所以上面的待办还是现从 db 读的。
    """
    today = date.today()
    saved_month = state.get("month")
    saved_day = state.get("day")
    visible_month = (
        saved_month
        if isinstance(saved_month, date)
        else date(today.year, today.month, 1)
    )
    selected_day = saved_day if isinstance(saved_day, date) else today

    def remember() -> None:
        """把当前所在的月份和选中的日期写回 `state`，供下次重建时恢复。"""
        state["month"] = visible_month
        state["day"] = selected_day

    month_view = ft.Container()
    month_title = ft.Text(
        f"{visible_month.year}年{visible_month.month}月",
        size=17,
        weight=ft.FontWeight.BOLD,
        color=TITLE_COLOR,
    )

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

    def remove_todo(todo: db.Todo, refresh: Callable[[], None]) -> None:
        db.delete_todo(todo.id)
        refresh()

    def edit_todo(todo: db.Todo, refresh: Callable[[], None]) -> None:
        open_todo_form(
            page,
            set_menu_visible=set_menu_visible,
            on_saved=lambda _: refresh(),
            default_date=todo.due_date,
            todo=todo,
        )

    def remove_countdown(item: db.Countdown, refresh: Callable[[], None]) -> None:
        db.delete_countdown(item.id)
        refresh()

    def edit_countdown(item: db.Countdown, refresh: Callable[[], None]) -> None:
        open_countdown_form(
            page,
            set_menu_visible=set_menu_visible,
            on_saved=refresh,
            item=item,
        )

    def clip_in_dialog(row: ft.Control) -> ft.Control:
        """把左滑行裁在弹窗边界内。

        左滑是靠平移卡片实现的，平移量（两个按钮 144px）比弹窗的留白大得多，
        不裁的话卡片会滑到弹窗外面、盖到页面上；这里按行自己的圆角裁一刀，
        滑出弹窗的部分直接看不见，露出来的就是那两个按钮。
        """
        return ft.Container(
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border_radius=ft.BorderRadius.all(10),
            content=row,
        )

    def section_header(name: str, icon: str, color: str) -> ft.Control:
        """弹窗里的小标题：图标 + 名称，待办和倒数日共用一套。"""
        return ft.Row(
            spacing=6,
            controls=[
                ft.Icon(icon, size=13, color=color),
                ft.Text(
                    name,
                    size=DIALOG_GROUP_SIZE,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                ),
            ],
        )

    def empty_hint() -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=ft.BorderRadius.all(12),
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, CELL_BORDER),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(
                        ft.Icons.EVENT_AVAILABLE,
                        size=20,
                        color="#94A3B8",
                    ),
                    ft.Text("这天没有待办事项", size=12, color="#64748B"),
                ],
            ),
        )

    def day_groups(
        day: date, refresh: Callable[[], None]
    ) -> list[ft.Control]:
        """弹窗内容：当天的待办用首页那套时间轴，倒数日接在下面。"""
        groups: list[ft.Control] = []
        todos = db.list_range(day, day)
        if todos:
            groups.append(
                ft.Column(
                    tight=True,
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        section_header(
                            "待办", ft.Icons.CHECKLIST, DIALOG_SECTION_COLOR
                        ),
                        build_todo_timeline(
                            todos,
                            axis_color=DIALOG_AXIS_COLOR,
                            on_delete=lambda todo: remove_todo(todo, refresh),
                            on_edit=lambda todo: edit_todo(todo, refresh),
                        ),
                    ],
                )
            )
        # 已经过期的倒数日也照常列出来：卡片整张置灰（见 countdown_card.py）。
        countdowns = countdowns_on(day)

        def countdown_card(item: db.Countdown) -> ft.Control:
            """当天这一条倒数日的卡片。

            过期的按「今天」算 —— 卡片上要写「已过期 N 天」，不能按所看的那天算成
            「就是今天」；没过期的按所看的那天算（那天就是它的日子）。灰的是哪几张
            由 tools/countdown_card.py 的 `countdown_expired` 说了算。
            """
            overdue = countdown_expired(item)
            return clip_in_dialog(
                build_countdown_card(
                    item,
                    today=None if overdue else day,
                    expired=overdue,
                    on_delete=lambda _, i=item: remove_countdown(i, refresh),
                    on_edit=lambda _, i=item: edit_countdown(i, refresh),
                )
            )

        if countdowns:
            groups.append(
                ft.Column(
                    tight=True,
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        section_header(
                            "倒数日", ft.Icons.EVENT, DIALOG_SECTION_COLOR
                        ),
                        *[countdown_card(item) for item in countdowns],
                    ],
                )
            )
        if not groups:
            groups.append(empty_hint())
        return groups

    def open_day_dialog(day: date) -> None:
        """点日期卡片：弹窗列出当天全部待办（左滑可编辑、删除）。"""
        # 正文的高度按内容来：里面那层 `content`（探针）量出来的自然高度够矮，弹窗就
        # 贴着内容收缩；超过 DIALOG_BODY_MAX_HEIGHT 才把正文钉在最高值上、打开滚动
        # （`ScrollMode.HIDDEN` = 能滚但不画滚动条，和 App 里其它滚动区一致）。日期行
        # +「×」不在这一层里：它们放在 `AlertDialog` 的 `title` 槽里（`scrollable=False`
        # 时 Material 只把 `content` 放进可伸缩的那一半），列表再长，顶上那行也不动。
        body = ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        # 量高度得等一帧，弹窗第一帧只能先按估的高度把正文撑起来：不预先定高的话，
        # 内容比上限高的那些天会先按全部内容撑高一下、下一帧才收回去 —— 点日期时
        # 看到的那一闪就是它（估高见上面的 estimate_day_height，宁可估高别估矮）。
        body.height = min(estimate_day_height(day), DIALOG_BODY_MAX_HEIGHT)
        # 高度先给了就先开滚动（不画滚动条）：万一估矮，第一帧顶多底下少露一点，
        # 内容也不会溢出到弹窗外面；量到真高度后 fit_body 再定最终高度。
        body.scroll = ft.ScrollMode.HIDDEN

        def fit_body(natural: float) -> None:
            """按量出来的自然高度定正文：够矮就贴着内容，超过上限才钉住、开滚动。"""
            over = natural > DIALOG_BODY_MAX_HEIGHT
            height = DIALOG_BODY_MAX_HEIGHT if over else None
            scroll = ft.ScrollMode.HIDDEN if over else None
            if body.height == height and body.scroll == scroll:
                return
            body.height = height
            body.scroll = scroll
            try:
                body.update()
            except RuntimeError:
                # 弹窗已经关掉：这一层不在树上了，没什么可更。
                pass

        # 量高度的探针：正文有多高由它说了算（它自己不被拉伸，量到的就是内容的自然
        # 高度）；删掉 / 改完一条它会变矮，正文跟着收回去。
        content = ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            on_size_change=lambda e: fit_body(e.height),
        )

        def refresh() -> None:
            # 删掉/改完一条，弹窗和月历一起刷新。
            content.controls = day_groups(day, refresh)
            content.update()
            update_calendar()

        content.controls = day_groups(day, refresh)
        body.controls = [content]
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                # 关掉 Material 的「标题跟着一起滚」：标题槽（日期 +「×」）
                # 留在不滚动的那一半，只有 content（`body`）滚。
                scrollable=False,
                shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
                bgcolor=DIALOG_SURFACE,
                elevation=0,
                inset_padding=ft.Padding.symmetric(horizontal=32, vertical=24),
                # 标题行和右上角的「×」都往角上靠一点。
                title_padding=ft.Padding.only(left=16, top=4, right=4, bottom=0),
                content_padding=ft.Padding.only(
                    left=16, top=8, right=16, bottom=8
                ),
                actions_padding=ft.Padding.only(left=8, right=8, bottom=8),
                action_button_padding=ft.Padding.symmetric(horizontal=8),
                # 标题右边就是关闭的「×」，底下不再放一整条 actions。
                title=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            f"{day.month}月{day.day}日 周{WEEKDAYS[day.weekday()]}",
                            size=DIALOG_TITLE_SIZE,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_COLOR,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_size=20,
                            icon_color=MUTED_COLOR,
                            tooltip="关闭",
                            on_click=lambda _: page.pop_dialog(),
                        ),
                    ],
                ),
                content=body,
            )
        )

    def faded(color: str) -> str:
        """同色淡一半（加一个 alpha 前缀）—— 完成的那条用它。"""
        return f"66{color[1:]}" if len(color) == 7 else color

    def item_dot(color: str, done: bool = False) -> ft.Container:
        """卡片里的一条：一个实心小圆点，颜色就是待办自己的颜色。

        宽高都写死（不带 content），跟图例上的圆点一个做法；完成的淡一半，颜色仍是
        那一档，扫一眼就知道是哪条打了勾。
        """
        return ft.Container(
            width=DOT_SIZE,
            height=DOT_SIZE,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=faded(color) if done else color,
        )

    def entries_of(day: date, todos: list[db.Todo]) -> list[tuple[str, bool]]:
        """当天要在格子上画的点：每条待办一个（分类色，完成的淡一半），倒数日一个。"""
        entries: list[tuple[str, bool]] = [
            (category_color(todo.category), todo.done) for todo in todos
        ]
        # 过期的倒数日也在格子里，换成同一档灰 —— 和倒数日页、当天弹窗一个样。
        entries += [
            (
                EXPIRED_CHIP_BG if countdown_expired(item) else COUNTDOWN_COLOR,
                False,
            )
            for item in countdowns_on(day)
        ]
        return entries

    def item_lines(day: date, todos: list[db.Todo]) -> list[ft.Control]:
        """当天的待办 + 倒数日：有几个画几个实心小圆点，从左往右排。"""
        entries = entries_of(day, todos)
        if not entries:
            return []
        # 点从左往右排（Row 吃满整格宽，点从左边开始）；一天有几条就画几个，格子
        # 横里放不下时圆点自己换到下一行（`wrap` 配 `run_spacing`，见 Flet 文档的
        # Row.wrap / Row.run_spacing）。要摆几行由 build_month_view 事先算好、格子
        # 高度照它定，所以折行不会被切掉。
        return [
            ft.Row(
                wrap=True,
                spacing=DOT_GAP,
                run_spacing=DOT_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[item_dot(color, done) for color, done in entries],
            )
        ]

    def day_of(number: int) -> date:
        """当月第 number 天（格子上的日期都按当前显示的月份算）。"""
        return date(visible_month.year, visible_month.month, number)


    def day_cell(
        day_number: int,
        day_todos: dict[date, list[db.Todo]],
        height: float,
    ) -> ft.Control:
        if day_number == 0:
            return ft.Container(expand=True, height=height)

        day = day_of(day_number)
        is_selected = day == selected_day
        # 卡片里的先后只看时间：全天的排最前，其余按时间早晚，同一时间按录入
        # 顺序 —— 和首页时间轴、当天弹窗共用同一套排序（tools/todo_timeline.py）。
        todos = sorted_todos(day_todos.get(day, []))
        lines = item_lines(day, todos)
        return ft.Container(
            expand=True,
            height=height,
            padding=ft.Padding.symmetric(horizontal=2, vertical=2),
            border_radius=ft.BorderRadius.all(8),
            # 浅灰描边，把每格的边界画出来（格子本身还是透明底）。
            border=ft.Border.all(1, CELL_BORDER),
            on_click=lambda _: click_day(day),
            content=ft.Column(
                tight=True,
                spacing=CELL_SPACING,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    # 日期靠左（选中的那天只有数字外面套一圈圆形底色），
                    # 右边跟一行农历，比日期小一号、灰色。
                    ft.Row(
                        spacing=2,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=DAY_BADGE_SIZE,
                                height=DAY_BADGE_SIZE,
                                shape=ft.BoxShape.CIRCLE,
                                alignment=ft.Alignment.CENTER,
                                bgcolor=(
                                    DATE_SELECTED_BG if is_selected else None
                                ),
                                content=ft.Text(
                                    str(day_number),
                                    size=DAY_NUMBER_SIZE,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                            ),
                            ft.Text(
                                lunar_short(day),
                                size=LUNAR_SIZE,
                                color=MUTED_COLOR,
                                text_align=ft.TextAlign.RIGHT,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True,
                            ),
                        ],
                    ),
                    *lines,
                ],
            ),
        )

    def learn_row_width(e: ft.LayoutSizeChangeEvent) -> None:
        """量到一周那行的真实宽度：一格能摆几个点由它说了算，行数变了就重排。

        宽度要等布局完才量得到，所以第一帧先按估的宽度排版；量到的值记在 `state`
        里，切走再回来、翻月、选日期都直接用它，只有热重载才会退回估的值。
        """
        width = e.width
        if not width or width <= 0:
            return
        known = state.get("calendar_row_width")
        if isinstance(known, (int, float)) and abs(float(known) - width) < 1:
            return
        state["calendar_row_width"] = float(width)
        try:
            month_view.content = build_month_view()
            month_view.update()
        except RuntimeError:
            # 页面已经切走：这层不在树上了，下次重建自然会用上量到的宽度。
            pass

    def build_month_view() -> ft.Control:
        month_days = calendar.monthcalendar(
            visible_month.year, visible_month.month
        )
        day_todos = month_todos()
        # 一个月里所有格子同高：先按「最忙那天要摆几行点」算内容高度，再跟
        # 「正方形底线」（高 = 宽）取大者 —— 点少的格子至少是个方的，点多的那天
        # 也不会被格子切掉半截（量到的宽度比估的准）。
        known_width = state.get("calendar_row_width")
        grid_width = (
            float(known_width)
            if isinstance(known_width, (int, float)) and known_width
            else estimated_grid_width()
        )
        per_run = dots_per_run(cell_inner_width(grid_width))
        # 每天要几个点：键是日期（month_todos 按 date 分组），别拿日号去取。
        dots_per_day = [
            len(entries_of(day_of(number), day_todos.get(day_of(number), [])))
            for week in month_days
            for number in week
            if number
        ]
        rows = max(
            dot_row_count(count, per_run) for count in dots_per_day
        )
        cell_px = max(cell_min_height(grid_width), cell_height(rows))
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
                            color=MUTED_COLOR,
                        )
                        for weekday in WEEKDAYS
                    ],
                ),
                *[
                    ft.Row(
                        # The cells share the row width, so this left-right gap
                        # sets how wide each day card gets.
                        spacing=DAY_CELL_SPACING,
                        controls=[
                            day_cell(day, day_todos, cell_px) for day in week
                        ],
                        # 第一周那行顺手量一下自己有多宽：一格能摆几个点由它说了算
                        # （见 learn_row_width），量出来跟估的不一样就重排一次。
                        on_size_change=learn_row_width if index == 0 else None,
                    )
                    for index, week in enumerate(month_days)
                ],
            ],
        )

    def update_calendar() -> None:
        nonlocal selected_day
        if (
            selected_day.month != visible_month.month
            or selected_day.year != visible_month.year
        ):
            selected_day = visible_month
        remember()
        month_view.content = build_month_view()
        month_title.value = f"{visible_month.year}年{visible_month.month}月"
        month_title.update()
        month_view.update()

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
        remember()
        month_view.content = build_month_view()
        month_view.update()

    def click_day(day: date) -> None:
        """点某天：先把它选上（日期圈变蓝），再弹出当天的待办清单。"""
        select_day(day)
        open_day_dialog(day)

    def jump_to_day(day: date) -> None:
        """Follow a date picked in the system picker: month and selection."""
        nonlocal visible_month
        visible_month = date(day.year, day.month, 1)
        select_day(day)
        update_calendar()

    date_picker = build_date_picker(selected_day, jump_to_day)

    def open_date_picker(_: ft.Event[ft.Control]) -> None:
        date_picker.value = selected_day
        page.show_dialog(date_picker)

    month_view.content = build_month_view()

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
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "日历",
                                    # Same face as the home page's
                                    # 「待办」heading.
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                                # 右上角进设置页（底部菜单已经不放「我的」入口了）。
                                ft.Container(
                                    ink=True,
                                    tooltip="设置",
                                    # 22px 的图标太难点，四周补一圈让手指够得着。
                                    padding=ft.Padding.all(6),
                                    on_click=lambda _: open_settings(),
                                    content=ft.Icon(
                                        ft.Icons.SETTINGS_OUTLINED,
                                        size=22,
                                        color=TITLE_COLOR,
                                    ),
                                ),
                            ],
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
                        # 网格万一放不下（小屏）能滚动，正常手机上不用滚。
                        ft.ListView(
                            expand=True,
                            scroll=ft.ScrollMode.HIDDEN,
                            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
                            controls=[month_view],
                        ),
                    ],
                ),
            ),
        ),
    )
