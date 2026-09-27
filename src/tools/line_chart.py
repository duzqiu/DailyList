"""待办趋势折线图，用 flet_charts 的官方多系列 LineChart 绘制。

Flet 1.0 把图表控件拆到了独立的 ``flet-charts`` 包：`LineChart` 可以在同一张图里挂多条
`LineChartData`（多系列），自带网格、轴刻度和触摸提示 —— 点按某个点就会弹出该点所属
系列的数值，所以「周/月/年」切换和「点击查看数据」都由控件本身负责。

y 轴没有单独的「轴线」开关，fl_chart 只有整块图的一圈 border，所以这里给它只留左边
一条：它正好落在 y 轴刻度右边，和 y=0 的横向网格线拼成一个 L 形坐标轴。浮框里不写
分类名，改用该系列颜色的圆点，和图表下方的图例是同一套颜色；圆点与文字同色是因为
fl_chart 的 `text_spans` 在 flet-charts 1.0.1 里是按值传给 Dart 的，Dart 侧却按控件
解析，一用就在描边阶段抛异常、整个浮框画不出来，所以浮框只能整行一个颜色。
"""

from collections.abc import Sequence

import flet as ft
import flet_charts as fch

GRID_COLOR = "#E2E8F0"
GRID_WIDTH = 1
# The y axis line: fl_chart draws `LineChart.border` around the plot area, so a
# left-only border is exactly a vertical axis standing next to the y labels. It
# meets the y=0 grid line, which closes the corner the way a chart frame reads.
Y_AXIS_WIDTH = 1
# `ChartAxis.label_size` is the *slot width* each label may occupy, and the font
# itself comes from the control passed as the label - fl_chart would otherwise
# draw its own 14pt text, far too big for this card.
AXIS_LABEL_SIZE = 9
AXIS_LABEL_COLOR = "#64748B"
X_LABEL_SLOT = 34
Y_LABEL_SLOT = 18
LINE_WIDTH = 2.5
POINT_RADIUS = 2.5
SELECTED_POINT_RADIUS = 5
# Dots are drawn on every point up to this many points; a 28-31 day month would
# otherwise turn into a dotted stripe.
POINT_LIMIT = 14
TOOLTIP_BG = "#F5FFFFFF"
TOOLTIP_TEXT_SIZE = 11
# The tooltip names a series by colour instead of by text: one filled round dot
# in the series' own colour, the same dot the legend under the chart uses. The
# line is painted in that colour too - `text_spans` (which would let the dot and
# the numbers differ) aborts the tooltip paint in flet-charts 1.0.1, see the
# module docstring.
TOOLTIP_DOT = "●"
MAX_Y_LABELS = 5
# Round steps the y axis is allowed to count in, so the ticks read 0/25/50/75/100
# rather than 0/19/38/57/76/95 when a month holds 90-odd todos.
NICE_STEPS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000)


def axis_ceiling(values: Sequence[int]) -> tuple[int, int]:
    """(顶部刻度, 刻度间隔)：最多 `MAX_Y_LABELS` 个标签，顶格落在数据上方。"""
    top = max(1, max(values, default=0))
    for step in NICE_STEPS:
        if top <= step * (MAX_Y_LABELS - 1):
            break
    else:
        # Past the last round step just use the smallest step that still fits.
        step = -(-top // (MAX_Y_LABELS - 1))
    return step * ((top + step - 1) // step), step


def label_indices(count: int, step: int | None) -> list[int]:
    """要标注的横轴位置：给了 step 就每 step 个标一次，否则首/中/尾。"""
    if count <= 1:
        return [0]
    if not step:
        return sorted({0, count // 2, count - 1})
    indices = list(range(0, count, step))
    if indices[-1] != count - 1:
        indices[-1] = count - 1
    return indices


def build_interactive_line_chart(
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    width: float,
    height: float,
    x_label_step: int | None = None,
) -> ft.Control:
    """多系列折线图。

    `labels`  每个点的横轴文字（1月…12月 / 9/21…9/27）
    `series`  [(名称, 数值列表, 颜色)]，每个元素画一条线
    """
    ceiling, y_step = axis_ceiling(
        [value for _, values, _ in series for value in values]
    )
    x_max = max(1, len(labels) - 1)
    return fch.LineChart(
        width=width,
        height=height,
        min_x=0,
        max_x=x_max,
        min_y=0,
        max_y=ceiling,
        # 触摸提示：点/长按某个点会弹出它的数值
        interactive=True,
        tooltip=fch.LineChartTooltip(
            bgcolor=TOOLTIP_BG,
            border_radius=ft.BorderRadius.all(8),
            border_side=ft.BorderSide(GRID_WIDTH, GRID_COLOR),
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            # The card would otherwise clip a tooltip that opens above the plot.
            fit_inside_horizontally=True,
            fit_inside_vertically=True,
        ),
        horizontal_grid_lines=fch.ChartGridLines(
            interval=y_step, color=GRID_COLOR, width=GRID_WIDTH
        ),
        border=ft.Border(
            left=ft.BorderSide(Y_AXIS_WIDTH, GRID_COLOR),
        ),
        left_axis=fch.ChartAxis(
            show_labels=True,
            labels=[
                fch.ChartAxisLabel(
                    value=value,
                    label=ft.Text(
                        str(value),
                        size=AXIS_LABEL_SIZE,
                        color=AXIS_LABEL_COLOR,
                    ),
                )
                for value in range(0, ceiling + 1, y_step)
            ],
            label_size=Y_LABEL_SLOT,
            # 固定刻度间隔，标签才会正好落在 fl_chart 取的刻度值上。
            label_spacing=y_step,
        ),
        bottom_axis=fch.ChartAxis(
            show_labels=True,
            labels=[
                fch.ChartAxisLabel(
                    value=index,
                    label=ft.Text(
                        labels[index],
                        size=AXIS_LABEL_SIZE,
                        color=AXIS_LABEL_COLOR,
                        no_wrap=True,
                    ),
                )
                for index in label_indices(len(labels), x_label_step)
                if index < len(labels)
            ],
            label_size=X_LABEL_SLOT,
        ),
        data_series=[
            fch.LineChartData(
                points=[
                    fch.LineChartDataPoint(
                        x=index,
                        y=value,
                        show_tooltip=True,
                        tooltip=fch.LineChartDataPointTooltip(
                            # The dot carries the category, so the line reads
                            # 「● 9/26 · 1」instead of naming the category.
                            text=f"{TOOLTIP_DOT} {labels[index]} · {value}",
                            text_style=ft.TextStyle(
                                size=TOOLTIP_TEXT_SIZE,
                                color=color,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ),
                    )
                    for index, value in enumerate(values)
                ],
                color=color,
                stroke_width=LINE_WIDTH,
                curved=True,
                # A curve through few points otherwise dips under the zero line.
                prevent_curve_over_shooting=True,
                point=(
                    fch.ChartCirclePoint(radius=POINT_RADIUS)
                    if len(values) <= POINT_LIMIT
                    else None
                ),
                selected_point=fch.ChartCirclePoint(
                    radius=SELECTED_POINT_RADIUS, stroke_width=2
                ),
            )
            for _name, values, color in series
        ],
    )
