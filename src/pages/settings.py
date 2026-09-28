import calendar
from bisect import bisect_right
from collections.abc import Callable
import flet as ft
import flet_charts as fch
from datetime import date, timedelta

from tools import db
from tools.categories import (
    CATEGORIES,
    build_category_icon,
    category_color,
)
from tools.layout import (
    BOTTOM_MENU_INSET,
    UNSELECTED_CARD_BG,
    page_gradient,
)
from tools.line_chart import build_interactive_line_chart
from tools.pie_chart import build_category_pie_chart, highlight_section
from tools.segmented import build_segmented

# Every surface on this page is the same grey the 待办 cards use, so a card here
# and a todo card read as the same material.
CARD_BG = UNSELECTED_CARD_BG
CARD_BORDER = "#E2E8F0"
TILE_BG = UNSELECTED_CARD_BG
# A tile's header is a pale tint of the category's own colour (see
# tools/categories.py) with the same dark ink on all three, so the levels differ
# only by hue. The text is 11pt like the rest of the tile.
CATEGORY_HEADERS = {
    "重要": "#D4DCE1",
    "一般": "#D4DCE1",
    "可选": "#D4DCE1",
}
HEADER_TEXT_SIZE = 11
TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
DONE_COLOR = "#16A34A"
PENDING_COLOR = "#DC2626"
# 三张卡的标题文字用同一个深色（只有底色按等级区分）。
HEADER_TEXT_COLOR = TITLE_COLOR

DIMENSIONS = ("年", "月", "周")
# 数据统计 and 待办趋势 both open on 周; the picker still offers 年/月/周.
DEFAULT_DIMENSION = "周"
# 三张卡各有一份 年/月/周 选择，key 也是保管它们的那份 state 的键名
# （见 build_settings_page 的 `state` 参数）。
DIMENSION_STATE_KEYS = ("dimension", "trend", "pie")
# 年 and 周 plot one point per month/day and stay few enough to name every point
# on the x axis; 月's 28-31 points keep the sparse first/middle/last labels.
NAMED_AXIS_DIMENSIONS = ("年", "周")
STATUS_KEYS = ("all", "done", "pending")
STATUS_LABELS = {"all": "全部", "done": "已完成", "pending": "未完成"}
STATUS_COLORS = {"all": TITLE_COLOR, "done": DONE_COLOR, "pending": PENDING_COLOR}
# A 数据统计 tile is a header in the category's colour over a grey data block.
# Every row carries a dot: 全部/已完成/未完成 keep the green one, 完成率 flips to
# red below half - and its percentage follows the dot.
DOT_SIZE = 5
RATE_THRESHOLD = 50
# 年/月/周 是卡片标题行里的横向胶囊开关（tools/segmented.py），不再是下拉触发器：
# 三档直接摊在标题行里，点一下就切。


def build_card(
    title: str,
    controls: list[ft.Control],
    trailing: ft.Control | None = None,
) -> ft.Control:
    """White card with a title (plus optional trailing control) and content."""
    title_row: list[ft.Control] = [
        ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=TITLE_COLOR)
    ]
    if trailing is not None:
        title_row.append(trailing)
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        border_radius=ft.BorderRadius.all(12),
        bgcolor=CARD_BG,
        border=ft.Border.all(1, CARD_BORDER),
        content=ft.Column(
            tight=True,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=title_row,
                ),
                *controls,
            ],
        ),
    )


def period_span(dimension: str, today: date) -> tuple[date, date] | None:
    """Due-date range of a statistics dimension; `None` means all dates."""
    if dimension == "周":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if dimension == "月":
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.replace(day=1), today.replace(day=last_day)
    if dimension == "年":
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    return None


TREND_HEIGHT = 150
# 饼图自己画在正方形画布上，圆孔里放「全部 N」；画布边长要给悬停时变粗的那段
# 留出余量（外半径 26+45=71，画布 152 的一半是 76）。
PIE_SIZE = 152
# The chart canvas is given an explicit size, so it needs the width of the card
# content area: page padding (24px per side) plus the card's own 16px padding.
TREND_PAGE_INSETS = 80
TREND_FALLBACK_PAGE_WIDTH = 360
TREND_MIN_WIDTH = 240
TREND_MAX_WIDTH = 560


def trend_width(page: ft.Page) -> float:
    """Canvas width that fits inside the card on the current window."""
    page_width = getattr(page, "width", None) or TREND_FALLBACK_PAGE_WIDTH
    return float(
        max(TREND_MIN_WIDTH, min(TREND_MAX_WIDTH, page_width - TREND_PAGE_INSETS))
    )


def chart_buckets(dimension: str, today: date) -> list[tuple[str, date, date]]:
    """Trend-chart buckets as (x label, first due-date, last due-date).

    周/月 are plotted per day and 年 per month, so the X axis stays readable.
    """
    if dimension == "周":
        start = today - timedelta(days=today.weekday())
        days = [start + timedelta(days=offset) for offset in range(7)]
        return [(f"{day.month}/{day.day}", day, day) for day in days]
    if dimension == "月":
        last_day = calendar.monthrange(today.year, today.month)[1]
        days = [today.replace(day=day) for day in range(1, last_day + 1)]
        return [(f"{day.month}/{day.day}", day, day) for day in days]
    return [
        (
            f"{month}月",
            date(today.year, month, 1),
            date(today.year, month, calendar.monthrange(today.year, month)[1]),
        )
        for month in range(1, 13)
    ]


def trend_series(
    buckets: list[tuple[str, date, date]],
) -> list[tuple[str, list[int], str]]:
    """Per-category todo counts for every bucket, ready for the line chart."""
    starts = [first for _, first, _ in buckets]
    counts = {name: [0] * len(buckets) for name, _ in CATEGORIES}
    for todo in db.list_range(starts[0], buckets[-1][2]):
        if todo.category not in counts:
            continue
        index = bisect_right(starts, todo.due_date) - 1
        if index >= 0 and todo.due_date <= buckets[index][2]:
            counts[todo.category][index] += 1
    return [(name, counts[name], color) for name, color in CATEGORIES]


def summarize(rows: list[tuple[str, bool, int]]) -> dict[str, dict[str, int]]:
    """Aggregate (category, done, count) rows into per-category buckets."""
    per_category = {name: dict.fromkeys(STATUS_KEYS, 0) for name, _ in CATEGORIES}
    for category, done, count in rows:
        bucket = per_category.setdefault(category, dict.fromkeys(STATUS_KEYS, 0))
        status = "done" if done else "pending"
        bucket["all"] += count
        bucket[status] += count
    return per_category


def build_settings_page(
    page: ft.Page,
    open_preferences: Callable[[], None],
    state: dict[str, object],
) -> ft.Control:
    """「我的」页。`state` 由调用方保管（见 pages/navigation.py）：三张卡各自的
    年/月/周 要能跨 Tab 留住，切走再回来还是原来那一档。
    """
    today = date.today()
    category_names = [name for name, _ in CATEGORIES]
    # 数据统计、分类占比和待办趋势各自留一份 年/月/周 选择：首次进来按默认值
    # 落一份，之后就沿用调用方存下的那一份。
    for key in DIMENSION_STATE_KEYS:
        state.setdefault(key, DEFAULT_DIMENSION)

    numbers = {
        (name, key): ft.Text(
            "0",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=STATUS_COLORS[key],
        )
        for name in category_names
        for key in STATUS_KEYS
    }
    # 完成率 is derived, so it keeps its own control per category.
    rates = {
        name: ft.Text(
            "—",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=TITLE_COLOR,
        )
        for name in category_names
    }
    # The 完成率 dot, the only one whose colour changes with the data.
    rate_dots = {
        name: ft.Container(
            width=DOT_SIZE,
            height=DOT_SIZE,
            border_radius=ft.BorderRadius.all(DOT_SIZE / 2),
            bgcolor=DONE_COLOR,
        )
        for name in category_names
    }

    def category_card(name: str) -> ft.Control:
        header_bg = CATEGORY_HEADERS.get(name, TILE_BG)

        def dot(color: str) -> ft.Control:
            return ft.Container(
                width=DOT_SIZE,
                height=DOT_SIZE,
                border_radius=ft.BorderRadius.all(DOT_SIZE / 2),
                bgcolor=color,
            )

        def row(
            label: str, marker: ft.Control, value: ft.Control
        ) -> ft.Control:
            return ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=2,
                controls=[
                    ft.Row(
                        tight=True,
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            marker,
                            ft.Text(label, size=9, color=MUTED_COLOR),
                        ],
                    ),
                    value,
                ],
            )

        return ft.Container(
            expand=1,
            border_radius=ft.BorderRadius.all(10),
            border=ft.Border.all(1, CARD_BORDER),
            # Keeps the header's grade inside the tile's rounded corners.
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=TILE_BG,
            content=ft.Column(
                tight=True,
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    # 头部：等级标题，底色是该分类颜色的浅色档
                    ft.Container(
                        padding=ft.Padding.symmetric(
                            horizontal=8, vertical=5
                        ),
                        bgcolor=header_bg,
                        content=ft.Row(
                            # 星标和文字在卡片里左右居中
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                build_category_icon(
                                    name,
                                    size=HEADER_TEXT_SIZE,
                                    color=category_color(name),
                                ),
                                ft.Text(
                                    name,
                                    size=HEADER_TEXT_SIZE,
                                    weight=ft.FontWeight.BOLD,
                                    color=HEADER_TEXT_COLOR,
                                ),
                            ],
                        ),
                    ),
                    # 数据：灰底，每行前面一个小圆点
                    ft.Container(
                        padding=ft.Padding.symmetric(
                            horizontal=8, vertical=6
                        ),
                        bgcolor=TILE_BG,
                        content=ft.Column(
                            tight=True,
                            spacing=3,
                            horizontal_alignment=(
                                ft.CrossAxisAlignment.STRETCH
                            ),
                            controls=[
                                *[
                                    row(
                                        STATUS_LABELS[key],
                                        dot(
                                            PENDING_COLOR
                                            if key == "pending"
                                            else DONE_COLOR
                                        ),
                                        numbers[(name, key)],
                                    )
                                    for key in STATUS_KEYS
                                ],
                                row("完成率", rate_dots[name], rates[name]),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def change_dimension(name: str) -> None:
        if name == state["dimension"]:
            return
        state["dimension"] = name
        render()

    selector_row = build_segmented(
        [(name, name) for name in DIMENSIONS], state["dimension"], change_dimension
    )

    chart_holder = ft.Container()

    def change_trend(name: str) -> None:
        """Re-render the chart; it has its own 年/月/周 switch."""
        if name == state["trend"]:
            return
        state["trend"] = name
        chart_holder.content = trend_chart()
        chart_holder.update()

    trend_selector_row = build_segmented(
        [(name, name) for name in DIMENSIONS], state["trend"], change_trend
    )

    pie_holder = ft.Container()
    # 凸出效果是在 on_event 里就地改扇区，所以要把当前这张图和悬停下标记住。
    pie_state: dict[str, object] = {"chart": None, "section": -1}

    def change_pie(name: str) -> None:
        """饼图也有自己的年/月/周切换。"""
        if name == state["pie"]:
            return
        state["pie"] = name
        pie_holder.content = pie_chart()
        pie_holder.update()

    pie_selector_row = build_segmented(
        [(name, name) for name in DIMENSIONS], state["pie"], change_pie
    )

    def pie_counts(dimension: str) -> list[tuple[str, int, str]]:
        """该周期里每个分类的待办条数，颜色用分类自己的颜色。"""
        span = period_span(dimension, today)
        rows = db.counts_in(*span) if span else db.counts_in()
        per_category = summarize(rows)
        return [
            (name, per_category.get(name, {}).get("all", 0), color)
            for name, color in CATEGORIES
        ]

    def on_pie_event(event: fch.PieChartEvent) -> None:
        """悬停/点按某个扇区时把它凸出来，离开就复原。"""
        chart = pie_state["chart"]
        if chart is None:
            return
        index = -1 if event.section_index is None else event.section_index
        if index == pie_state["section"]:
            return
        pie_state["section"] = index
        highlight_section(chart, index)
        chart.update()

    def pie_chart() -> ft.Control:
        counts = pie_counts(state["pie"])
        total = sum(count for _, count, _ in counts)
        if not total:
            pie_state["chart"] = None
            pie_state["section"] = -1
            return ft.Container(
                width=PIE_SIZE,
                height=PIE_SIZE,
                alignment=ft.Alignment.CENTER,
                content=ft.Text("本期没有待办", size=12, color=MUTED_COLOR),
            )
        chart = build_category_pie_chart(counts, PIE_SIZE, on_pie_event)
        pie_state["chart"] = chart
        pie_state["section"] = -1
        return ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Stack(
                    width=PIE_SIZE,
                    height=PIE_SIZE,
                    alignment=ft.Alignment.CENTER,
                    controls=[
                        chart,
                        # 圆孔里写总数，外面一圈就是各分类的占比。
                        ft.Column(
                            tight=True,
                            spacing=0,
                            horizontal_alignment=(
                                ft.CrossAxisAlignment.CENTER
                            ),
                            controls=[
                                ft.Text(
                                    str(total),
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                                ft.Text("全部", size=9, color=MUTED_COLOR),
                            ],
                        ),
                    ],
                ),
                # 图例挪到饼图右侧：一行一个分类，圆点颜色就是扇区颜色。
                ft.Column(
                    tight=True,
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Row(
                            tight=True,
                            spacing=6,
                            controls=[
                                ft.Container(
                                    width=8,
                                    height=8,
                                    border_radius=ft.BorderRadius.all(4),
                                    bgcolor=color,
                                ),
                                ft.Text(
                                    f"{name} {count}",
                                    size=11,
                                    color=MUTED_COLOR,
                                ),
                            ],
                        )
                        for name, count, color in counts
                    ],
                ),
            ],
        )

    def trend_chart() -> ft.Control:
        buckets = chart_buckets(state["trend"], today)
        return ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                build_interactive_line_chart(
                    [label for label, _, _ in buckets],
                    trend_series(buckets),
                    trend_width(page),
                    TREND_HEIGHT,
                    x_label_step=(
                        1 if state["trend"] in NAMED_AXIS_DIMENSIONS else None
                    ),
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                    controls=[
                        ft.Row(
                            tight=True,
                            spacing=4,
                            controls=[
                                ft.Container(
                                    width=8,
                                    height=8,
                                    border_radius=ft.BorderRadius.all(4),
                                    bgcolor=color,
                                ),
                                ft.Text(name, size=11, color=MUTED_COLOR),
                            ],
                        )
                        for name, color in CATEGORIES
                    ],
                ),
            ],
        )

    def render(update: bool = True) -> None:
        dimension = state["dimension"]
        span = period_span(dimension, today)
        rows = db.counts_in(*span) if span else db.counts_in()
        per_category = summarize(rows)
        for name in category_names:
            bucket = per_category.get(name, dict.fromkeys(STATUS_KEYS, 0))
            for key in STATUS_KEYS:
                numbers[(name, key)].value = str(bucket[key])
            total = bucket["all"]
            if total:
                rate = round(bucket["done"] / total * 100)
                rate_color = (
                    DONE_COLOR if rate >= RATE_THRESHOLD else PENDING_COLOR
                )
                rates[name].value = f"{rate}%"
            else:
                # Nothing to rate yet: a quiet grey instead of a red/green claim.
                rate_color = MUTED_COLOR
                rates[name].value = "—"
            rates[name].color = rate_color
            rate_dots[name].bgcolor = rate_color
        chart_holder.content = trend_chart()
        pie_holder.content = pie_chart()
        if update:
            for control in [
                *numbers.values(),
                *rates.values(),
                *rate_dots.values(),
                pie_holder,
                chart_holder,
            ]:
                control.update()

    render(update=False)

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
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "我的",
                                    # Same face as the home page's「待办」heading.
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                                # 右上角的设置入口，点开的是二级页「设置」。
                                ft.Container(
                                    ink=True,
                                    tooltip="设置",
                                    # 22px 的图标太难点，四周补一圈让手指够得着。
                                    padding=ft.Padding.all(6),
                                    on_click=lambda _: open_preferences(),
                                    content=ft.Icon(
                                        ft.Icons.SETTINGS_OUTLINED,
                                        size=22,
                                        color=TITLE_COLOR,
                                    ),
                                ),
                            ],
                        ),
                        ft.ListView(
                            expand=True,
                            spacing=12,
                            scroll=ft.ScrollMode.HIDDEN,
                            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
                            controls=[
                                build_card(
                                    "数据统计",
                                    [
                                        ft.Row(
                                            spacing=8,
                                            controls=[
                                                category_card(name)
                                                for name in category_names
                                            ],
                                        ),
                                    ],
                                    trailing=selector_row,
                                ),
                                build_card(
                                    "分类占比",
                                    [pie_holder],
                                    trailing=pie_selector_row,
                                ),
                                build_card(
                                    "待办趋势",
                                    [chart_holder],
                                    trailing=trend_selector_row,
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        ),
    )
