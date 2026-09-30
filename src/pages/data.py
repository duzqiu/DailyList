"""「数据」页：从待办页右上角的柱状图图标进来，底部菜单收起。

数据统计 / 分类占比 / 待办趋势三张卡都在这一个二级页上，顶栏是「返回 + 居中标题」
（和设置页共用 tools/layout.py 的 build_subpage_header）。卡里的 年/月/周 由调用方
保管，退出去再进来还是原来那一档。

数据统计那张卡里不是几张数字小卡，而是**一枚半圆进度环**（tools/half_ring.py）：
圆心写着完成率，环下面一行是各分类的条数；进页面时环从 0 滑到该周期的完成率。
"""

import asyncio
import calendar
from bisect import bisect_right
from collections.abc import Callable
import flet as ft
import flet_charts as fch
from datetime import date, timedelta

from tools import db
from tools.categories import CATEGORIES
from tools.layout import (
    BOTTOM_MENU_INSET,
    UNSELECTED_CARD_BG,
    build_subpage_header,
    page_gradient,
)
from tools.half_ring import build_half_ring
from tools.line_chart import build_interactive_line_chart
from tools.pie_chart import build_category_pie_chart, highlight_section
from tools.segmented import build_segmented

# Every surface on this page is the same grey the 待办 cards use, so a card here
# and a todo card read as the same material.
CARD_BG = UNSELECTED_CARD_BG
CARD_BORDER = "#E2E8F0"
TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
DONE_COLOR = "#16A34A"
PENDING_COLOR = "#DC2626"

DIMENSIONS = ("年", "月", "周")
# 数据统计 and 待办趋势 both open on 周; the picker still offers 年/月/周.
DEFAULT_DIMENSION = "周"
# 三张卡各有一份 年/月/周 选择，key 也是保管它们的那份 state 的键名
# （见 build_data_page 的 `state` 参数）。
DIMENSION_STATE_KEYS = ("dimension", "trend", "pie")
# 年 and 周 plot one point per month/day and stay few enough to name every point
# on the x axis; 月's 28-31 points keep the sparse first/middle/last labels.
NAMED_AXIS_DIMENSIONS = ("年", "周")
STATUS_KEYS = ("all", "done", "pending")
# 完成率低于一半就换成红的那一档（中间那个数字用它）。
RATE_THRESHOLD = 50
# 卡片的内边距（`build_card` 用、环的尺寸也从它推）与卡片标题：这一页三张卡的标题
# 都是**小一号的灰字** —— 它只是「这张卡在讲什么」的标签，不和卡里的内容抢眼。
CARD_PADDING_H = 16
CARD_PADDING_V = 14
CARD_TITLE_SIZE = 11
CARD_TITLE_COLOR = MUTED_COLOR
CARD_TITLE_GAP = 10
# 一行两张的**小长方卡**（数据统计 / 分类占比）：宽度**平分**页面给卡片的宽度（两张
# 加中间那道缝正好铺满一行，窗口一变就跟着变），高度都**跟着内容走**（不留空白）；
# 比别的卡更紧凑 —— 内边距更小、和标题的间隙更小、年/月/周 用紧凑款胶囊。
# 下限 142：「标题 数据统计（11pt 44px）+ 间隙 6 + 紧凑款胶囊（64px）= 114」再加左右
# 内边距 24 是 138，留 4px 余量 —— 再窄那一行就放不下了（那时两张卡会折成两行）。
STATS_CARD_GAP = 12
STATS_CARD_MIN_WIDTH = 142
STATS_CARD_TITLE_GAP = 6
STATS_CARD_PADDING_H = 12
STATS_CARD_PADDING_V = 8
# 环再大也就这么宽（卡内宽）；宽屏上卡片本身很宽，环别跟着无限拉长 —— 它的字和圆点
# 是定号的，拉太长就只剩一空壳了。饼跟着取它的一半（两张卡因此仍然同高）。
RING_MAX_WIDTH = 260
# 页面内容两侧的边距（外层容器的 padding 也用它）。
PAGE_SIDE_PADDING = 24
# 小卡里的环：画布边长 = 卡内宽（见 stats_card_width），环厚与环里的字号跟着收。
RING_THICKNESS = 8
RATE_TEXT_SIZE = 18
RATE_CAPTION_SIZE = 8
# 小卡里的饼：右边一列图例（「● 重要 3」一行一个分类，8pt：点 6 + 缝 4 + 名字/数字），
# 饼的直径见 build_data_page。
LEGEND_DOT_SIZE = 6
LEGEND_TEXT_SIZE = 8
LEGEND_TEXT_GAP = 4
LEGEND_ROW_GAP = 8
# 图例那一列的宽度估计（点 6 + 缝 4 + 「重要 3」约 23，这里往宽里写一点留余量）——
# 只用来算饼最多能占多宽：窄屏上饼就是卡在这儿，而不是卡在 `PIE_GROW` 上。
LEGEND_WIDTH = 36
PIE_GAP = 6
# 饼比环那边高多少：环那边的高度是天生的（半圆只有宽的一半），饼不该跟着那么小。
# 窄屏上饼顶到的是**宽度**那条线（卡内宽 − 图例 − 缝），这个倍数只在宽屏（卡片很宽、
# 环又收在 `RING_MAX_WIDTH`）时兜底。多出来的高度在两张卡里**平分**：图上那一行都取
# 饼那么高，环按自己天生的高度居中 —— 两张卡还是同高。
PIE_GROW = 1.4
# 饼图圆孔里那个总数。圆孔小（跟着饼缩），只放得下一行字 —— 所以没有「全部」那行小字，
# 数字自己就说明是总数（各分类的条数在图例里）。
TOTAL_TEXT_SIZE = 11
# 进场那一下：圆点从最左边（0%）走到完成率那格，缓出走（越到后面越慢）。
RING_ANIM_MS = 700
RING_ANIM_STEPS = 24
# 年/月/周 是卡片标题行里的横向胶囊开关（tools/segmented.py），不再是下拉触发器：
# 三档直接摊在标题行里，点一下就切。


def build_card(
    title: str,
    controls: list[ft.Control],
    trailing: ft.Control | None = None,
    width: float | None = None,
    title_size: float = CARD_TITLE_SIZE,
    title_color: str = CARD_TITLE_COLOR,
    bgcolor: str | None = CARD_BG,
) -> ft.Control:
    """White card with a title (plus optional trailing control) and content.

    `width` 给了就是那张**小长方卡**（见 `stats_card_width`）：宽度定死、不再通栏
    （右上角那个 `trailing` 还在标题行里，所以它得放得下「标题 + 开关」），**高度
    不写、跟着内容走** —— 半圆下面就不会多出一块空白；内边距、标题间隙也跟着换
    小一号的那套。

    `bgcolor=None` 就是透明底：卡片自己不铺色，露出来的是页面的渐变（数据统计那张
    卡用它），边框还留着，方框的样子还在。
    """
    small = width is not None
    title_row: list[ft.Control] = [
        ft.Text(
            title,
            size=title_size,
            weight=ft.FontWeight.BOLD,
            color=title_color,
        )
    ]
    if trailing is not None:
        title_row.append(trailing)
    return ft.Container(
        width=width,
        padding=ft.Padding.symmetric(
            horizontal=(
                STATS_CARD_PADDING_H if small else CARD_PADDING_H
            ),
            vertical=STATS_CARD_PADDING_V if small else CARD_PADDING_V,
        ),
        border_radius=ft.BorderRadius.all(12),
        bgcolor=bgcolor,
        border=ft.Border.all(1, CARD_BORDER),
        content=ft.Column(
            tight=True,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    spacing=(
                        STATS_CARD_TITLE_GAP if small else CARD_TITLE_GAP
                    ),
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


# 折线画布的高度：回到原来那一档 —— 三条线要看得清，图本身不能压太扁。
TREND_HEIGHT = 150
# 画布和图例之间那道缝：**贴住**（0）。画布的底边本来就留着 X 轴标签那一截，图例
# 紧接在下面看着仍是一条，卡也因此矮下来。
TREND_GAP = 0
# 饼图自己画在正方形画布上（边长见上面那两条常量推算），圆孔里放「全部 N」。
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


def card_area_width(page: ft.Page) -> float:
    """卡片真正能用的宽度：页面宽减去两侧的边距。

    和 `trend_width` 的区别在**上限**：那个是给折线画布用的（宽过 560 就不再加宽，
    免得一条线拉成横贯屏幕），卡片这边要的是「窗口一变就跟着变」，所以不设上限。
    """
    page_width = getattr(page, "width", None) or TREND_FALLBACK_PAGE_WIDTH
    return float(max(TREND_MIN_WIDTH, page_width - 2 * PAGE_SIDE_PADDING))


def stats_card_width(page: ft.Page) -> float:
    """一行两张小卡时，一张的宽度：卡片能用的宽度减掉中间那道缝再**平分**。

    算出来的小数**往下取整**：两张加起来必须稳稳放得下一行 —— 141.5 那种小数两边
    一进位（283 + 12 = 295 顶到边），真机上四舍五入差一点就折行了。
    """
    available = card_area_width(page)
    return float(
        max(STATS_CARD_MIN_WIDTH, int((available - STATS_CARD_GAP) / 2))
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


def build_data_page(
    page: ft.Page,
    go_back: Callable[[], None],
    state: dict[str, object],
) -> ft.Control:
    """「数据」页。`state` 由调用方保管（见 pages/navigation.py）：三张卡各自的
    年/月/周 要能留住，退出去再进来还是原来那一档。
    """
    today = date.today()
    # 数据统计、分类占比和待办趋势各自留一份 年/月/周 选择：首次进来按默认值
    # 落一份，之后就沿用调用方存下的那一份。
    for key in DIMENSION_STATE_KEYS:
        state.setdefault(key, DEFAULT_DIMENSION)

    # 上面两张小卡的尺寸：宽度平分页面（见 stats_card_width）；卡内宽就是环的画布边长
    # （宽屏上收在 `RING_MAX_WIDTH`）。
    card_width = stats_card_width(page)
    inner_width = card_width - 2 * STATS_CARD_PADDING_H
    ring_width = min(inner_width, RING_MAX_WIDTH)
    # 饼比环那边（半圆天生只占宽的一半）大一圈，只要右边还给图例留得下位置：
    # 取「卡内宽 − 图例 − 缝」和「环高 × PIE_GROW」里的小者。
    pie_size = min(
        inner_width - LEGEND_WIDTH - PIE_GAP,
        ring_width / 2 * PIE_GROW,
    )
    # 图上那一行的共同高度 = 饼的直径；环在自己的行里居中，两张卡因此还是同高。
    figure_height = pie_size

    # 数据统计那张卡：**一枚**半圆环（tools/half_ring.py），画的是**全部待办**在这一档
    # 的完成率。环里只写「完成率大字 + 完成率」两个字段。
    rate_text = ft.Text(
        "—", size=RATE_TEXT_SIZE, weight=ft.FontWeight.BOLD, color=TITLE_COLOR
    )
    ring = build_half_ring(
        ft.Column(
            tight=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                rate_text,
                ft.Text("完成率", size=RATE_CAPTION_SIZE, color=MUTED_COLOR),
            ],
        ),
        size=ring_width,
        thickness=RING_THICKNESS,
    )
    # 这一档要走的完成率：`render()` 每次算出来，动画只负责把圆点从当前那格挪过去。
    # `fraction` 为 None 表示这一档一条待办都没有（圆点停在起点、数字写「—」）。
    gauge: dict[str, object] = {"fraction": None, "color": MUTED_COLOR}

    # 进场动画只跑一次：第一帧量到尺寸就把标记立起来，之后转屏 / 缩放不再重放。
    started = {"done": False}
    # 动画的编号：连点两下 年/月/周 时，前一次跑到一半就自己退出 —— 免得两条动画
    # 同时往圆点上写位置、抖起来。
    sweep_token = {"n": 0}

    def paint(fraction: float) -> None:
        """把圆点挪到 `fraction`（0..1），中间那个数字跟着一起涨。"""
        ring.set_value(fraction)
        rate_text.value = (
            f"{round(fraction * 100)}%" if gauge["fraction"] is not None else "—"
        )
        ring.control.update()

    async def sweep() -> None:
        """把圆点从**现在停着的那一格**挪到 `gauge` 那一档。

        进页面那一下是从最左边起（`HalfRing.value` 的初值就是 0），切 年/月/周 时是从
        上一档接着走 —— 两种情况都只认「现在停在哪」这一个起点。缓出走：越到后面越慢。
        """
        sweep_token["n"] += 1
        token = sweep_token["n"]
        target = gauge["fraction"]
        if target is None:
            # 这一档一条待办都没有：圆点留在起点、中间写「—」，没什么可滑的。
            paint(0.0)
            return
        start = ring.value
        for step in range(1, RING_ANIM_STEPS + 1):
            if token != sweep_token["n"]:
                return
            eased = 1 - (1 - step / RING_ANIM_STEPS) ** 3
            paint(start + (target - start) * eased)
            await asyncio.sleep(RING_ANIM_MS / 1000 / RING_ANIM_STEPS)

    def start_sweep(_: ft.LayoutSizeChangeEvent) -> None:
        """第一帧布局完才开始滑 —— 那会儿控件已经在页面上，`update()` 才发得出去。"""
        if started["done"]:
            return
        started["done"] = True
        page.run_task(sweep)

    # `on_size_change` 是布局之后才回的，正好当「这一页已经上树」的信号（和日历页
    # 量格子宽、待办对勾弹出来是同一个用法）。
    ring.control.on_size_change = start_sweep

    def change_dimension(name: str) -> None:
        if name == state["dimension"]:
            return
        state["dimension"] = name
        render()
        # 换了一档：环从当前那个比例滑到新的完成率。
        page.run_task(sweep)

    selector_row = build_segmented(
        [(name, name) for name in DIMENSIONS],
        state["dimension"],
        change_dimension,
        # 小卡里和标题并排放在一行，得用紧凑那款（待办趋势那张照旧）。
        compact=True,
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
        [(name, name) for name in DIMENSIONS],
        state["trend"],
        change_trend,
        # 和上面两张卡一样用紧凑款：标题行矮一截（30 → 22），整张卡也跟着矮。
        compact=True,
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
        [(name, name) for name in DIMENSIONS],
        state["pie"],
        change_pie,
        # 和「数据统计」一样是一张小卡，胶囊也用紧凑那款。
        compact=True,
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
        """小卡里的内容：饼图 + 右边一列图例（点 + 分类名 + 条数）。

        饼的直径是算好的（`pie_size`，扣掉了图例那一列的宽度），图例竖着摆在右边 ——
        小卡里横着摆不下三行。图例字号比别处小一号，和卡里其它字配套。
        """
        counts = pie_counts(state["pie"])
        total = sum(count for _, count, _ in counts)
        if not total:
            pie_state["chart"] = None
            pie_state["section"] = -1
            return ft.Container(
                height=pie_size,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    "本期没有待办", size=LEGEND_TEXT_SIZE, color=MUTED_COLOR
                ),
            )
        chart = build_category_pie_chart(counts, pie_size, on_pie_event)
        pie_state["chart"] = chart
        pie_state["section"] = -1
        return ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=PIE_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Stack(
                    width=pie_size,
                    height=pie_size,
                    alignment=ft.Alignment.CENTER,
                    controls=[
                        chart,
                        # 圆孔里写总数，外面一圈就是各分类的占比。孔小，只放数字。
                        ft.Text(
                            str(total),
                            size=TOTAL_TEXT_SIZE,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_COLOR,
                        ),
                    ],
                ),
                # 图例在饼图右侧：一行一个分类，圆点颜色就是扇区颜色。
                ft.Column(
                    tight=True,
                    spacing=LEGEND_ROW_GAP,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Row(
                            tight=True,
                            spacing=LEGEND_TEXT_GAP,
                            controls=[
                                ft.Container(
                                    width=LEGEND_DOT_SIZE,
                                    height=LEGEND_DOT_SIZE,
                                    border_radius=ft.BorderRadius.all(
                                        LEGEND_DOT_SIZE / 2
                                    ),
                                    bgcolor=color,
                                ),
                                ft.Text(
                                    f"{name} {count}",
                                    size=LEGEND_TEXT_SIZE,
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
            spacing=TREND_GAP,
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
        """把这一档的数据算出来摆好：圆点要走到的那一格、两张图。

        圆点和中间那个数字**不在这里画** —— 它们由 `sweep` 一步步挪过去（见上）。
        """
        dimension = state["dimension"]
        span = period_span(dimension, today)
        rows = db.counts_in(*span) if span else db.counts_in()
        per_category = summarize(rows)
        # 全部待办一起算：所有分类的条数与完成数各自相加。
        total = sum(bucket["all"] for bucket in per_category.values())
        done = sum(bucket["done"] for bucket in per_category.values())
        if total:
            gauge["fraction"] = done / total
            gauge["color"] = (
                DONE_COLOR
                if gauge["fraction"] * 100 >= RATE_THRESHOLD
                else PENDING_COLOR
            )
        else:
            # 这一档一条待办都没有：不给红绿断言，数字走灰的。
            gauge["fraction"] = None
            gauge["color"] = MUTED_COLOR
        rate_text.color = gauge["color"]
        chart_holder.content = trend_chart()
        pie_holder.content = pie_chart()
        if update:
            for control in [rate_text, pie_holder, chart_holder]:
                control.update()

    render(update=False)

    return ft.Container(
        expand=True,
        gradient=page_gradient(),
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(
                    left=PAGE_SIDE_PADDING,
                    top=PAGE_SIDE_PADDING,
                    right=PAGE_SIDE_PADDING,
                ),
                content=ft.Column(
                    expand=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        # 返回按钮在左、标题居中，和设置页同一个顶栏。
                        build_subpage_header("数据", go_back),
                        ft.ListView(
                            expand=True,
                            spacing=12,
                            scroll=ft.ScrollMode.HIDDEN,
                            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
                            controls=[
                                # 数据统计 + 分类占比：两张**同款小卡并排**（都不通栏，
                                # 宽度对半分）——套一层 Row 才摆得住：ListView 会把自己的
                                # 子项拉满整行宽，小卡得有个「不拉伸」的盒子。窄屏摆不下
                                # 就折行，两张高度本来也不一样（一个半圆、一个整圆），
                                # 所以顶对齐、各长各的。
                                ft.Row(
                                    wrap=True,
                                    spacing=STATS_CARD_GAP,
                                    run_spacing=STATS_CARD_GAP,
                                    alignment=ft.MainAxisAlignment.START,
                                    vertical_alignment=(
                                        ft.CrossAxisAlignment.START
                                    ),
                                    controls=[
                                        build_card(
                                            "数据统计",
                                            # 一枚半圆环：刻度弧 + 一个圆点指着完成率。
                                            # 这一行给的是**图上那一行的共同高度**
                                            # （`figure_height` = 饼的直径），半圆在它
                                            # 里面居中、不写 `expand` —— 卡片高度跟着
                                            # 内容走，不会在环下面多出一块。
                                            [
                                                ft.Row(
                                                    height=figure_height,
                                                    alignment=(
                                                        ft.MainAxisAlignment
                                                        .CENTER
                                                    ),
                                                    vertical_alignment=(
                                                        ft.CrossAxisAlignment
                                                        .CENTER
                                                    ),
                                                    controls=[ring.control],
                                                )
                                            ],
                                            trailing=selector_row,
                                            width=card_width,
                                            # 透明底：卡片自己不铺色，环浮在页面渐变上
                                            # （只留那圈边框）。
                                            bgcolor=None,
                                        ),
                                        # 分类占比照数据统计那套来：同宽、透明底、
                                        # 紧凑款胶囊，高度也跟内容走。
                                        build_card(
                                            "分类占比",
                                            [pie_holder],
                                            trailing=pie_selector_row,
                                            width=card_width,
                                            bgcolor=None,
                                        ),
                                    ],
                                ),
                                build_card(
                                    "待办趋势",
                                    [chart_holder],
                                    # 透明底：折线图自己不带底色（网格线和坐标轴都是画上
                                    # 去的浅灰），卡片一透明它就浮在页面渐变上 —— 和上
                                    # 面两张小卡一个材质，只留那圈边框。
                                    bgcolor=None,
                                    trailing=trend_selector_row,
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        ),
    )
