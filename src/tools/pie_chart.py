"""分类占比饼图，用 flet_charts 的官方 `PieChart` 绘制。

官方示例「PieChart with hover sections」的做法是：控件只负责画，凸出效果在
`on_event` 里改扇区半径、再 `update()` —— fl_chart 1.2 的画笔本身不再自带
悬停放大，所以悬停/点按的高亮由 `highlight_section` 完成。

扇区颜色就是待办分类的颜色（见 tools/categories.py），和折线图、图例同一套色。
"""

from collections.abc import Callable, Sequence

import flet as ft
import flet_charts as fch

from tools.layout import UNSELECTED_CARD_BG

# 扇区厚度，以及悬停时加厚到多少。
PIE_RADIUS = 38
PIE_HOVER_RADIUS = 45
# 中间的圆孔：留出写「全部 N」的位置，用卡片底色把它填掉。
PIE_CENTER_RADIUS = 26
PIE_SECTION_SPACE = 3
# 占比小到 3% 以下的扇区窄得放不下字，就不写标签了（条数仍然在图例里）。
MIN_TITLE_SHARE = 0.03
TITLE_SIZE = 10
TITLE_HOVER_SIZE = 12
TITLE_COLOR = "#FFFFFF"


def _title_style(size: float) -> ft.TextStyle:
    """扇区文字：白字压在扇区色上，悬停时大一号。"""
    return ft.TextStyle(
        size=size,
        color=TITLE_COLOR,
        weight=ft.FontWeight.BOLD,
    )


def build_category_pie_chart(
    counts: Sequence[tuple[str, int, str]],
    size: float,
    on_event: Callable[[fch.PieChartEvent], None],
) -> fch.PieChart:
    """按分类占比画一张饼图。

    `counts` 是 [(分类名, 数量, 颜色)]；数量为 0 的分类仍然占一个扇区的位置
    （fl_chart 不画 0 值扇区），这样扇区下标和分类一一对应，悬停时不用换算法。
    """
    total = sum(count for _, count, _ in counts)
    return fch.PieChart(
        width=size,
        height=size,
        sections=[_section(count, total, color) for _, count, color in counts],
        sections_space=PIE_SECTION_SPACE,
        center_space_radius=PIE_CENTER_RADIUS,
        center_space_color=UNSELECTED_CARD_BG,
        # 从正上方起画，重要的一段落在最显眼的位置。
        start_degree_offset=-90,
        on_event=on_event,
    )


def _section(value: int, total: int, color: str) -> fch.PieChartSection:
    """一个分类扇区：颜色就是分类色，扇区里只写占比，条数交给图例。"""
    share = value / total if total else 0
    return fch.PieChartSection(
        value=value,
        radius=PIE_RADIUS,
        color=color,
        title=f"{round(share * 100)}%" if share >= MIN_TITLE_SHARE else None,
        title_style=_title_style(TITLE_SIZE),
    )


def highlight_section(chart: fch.PieChart, index: int) -> None:
    """把第 `index` 个扇区凸出来（悬停/点按），其余复原。"""
    for position, section in enumerate(chart.sections):
        hovered = position == index
        section.radius = PIE_HOVER_RADIUS if hovered else PIE_RADIUS
        section.title_style = _title_style(
            TITLE_HOVER_SIZE if hovered else TITLE_SIZE
        )
