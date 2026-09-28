"""待办趋势折线图：官方 `LineChart` 画线，浮框由本文件用 Flet 控件自己画。

Flet 1.0 把图表控件拆到了独立的 ``flet-charts`` 包：`LineChart` 能在同一张图里挂多条
`LineChartData`（多系列），自带网格、轴刻度、悬停高亮和 y 轴线 —— 「周/月/年」切换、
点按放大都交给控件。

浮框（悬停提示）没有用它自带的那个：fl_chart 的浮框是「一个系列一行」，每行只有一种
颜色（`text_spans` 在 flet-charts 1.0.1 里到不了 Dart 侧），画不出「灰色日期 + 彩色
圆点 + 黑色数值」。所以自带浮框只留个透明的壳（位置还算它算的），内容换成这里自绘的
`ft.Container`，挂在图表的 `ft.Stack` 上，由 `on_event` 的悬停事件摆位置、换内容。

浮框特意贴在锚点左右（`TIP_OFFSET` 比 fl_chart 10px 的命中半径大）：它只按 x 距离判断
命中，光标永远碰不到浮框，也就不会出现「浮框盖住光标 → 图表 pointerExit → 浮框消失 →
又冒出来」的抖动。
"""

import flet as ft
import flet_charts as fch

from tools.layout import text_width

GRID_COLOR = "#E2E8F0"
GRID_WIDTH = 1
# The y axis line: fl_chart draws `LineChart.border` around the plot area, so a
# left-only border is exactly a vertical axis standing next to the y labels. It
# meets the y=0 grid line, which closes the corner the way a chart frame reads.
Y_AXIS_WIDTH = 1
# `ChartAxis.label_size` is the *slot width* each label may occupy, and the font
# itself comes from the control passed as the label - fl_chart would otherwise
# draw its own 14pt text, far too big for this card. The two slots are also the
# plot's left/bottom inset, which is what places the tooltip.
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
MAX_Y_LABELS = 5
# Round steps the y axis is allowed to count in, so the ticks read 0/25/50/75/100
# rather than 0/19/38/57/76/95 when a month holds 90-odd todos.
NICE_STEPS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000)

# 自绘浮框：毛玻璃底 + 日期单独一行灰字，下面每个系列一行「对应颜色的圆点 + 黑色数值」。
# 底色是半透明的灰白，再叠一层 blur：容器下方的图表先被模糊，再透过半透明底色显出来，
# 就是毛玻璃。颜色写作 `#AARRGGBB`，前两位是透明度 —— 和右下角「+」按钮、
# 底部菜单栏是同一套做法（见 pages/home.py、pages/navigation.py）。
TIP_BG = "#CCF1F5F9"
TIP_BLUR = ft.Blur(12, 12, ft.BlurTileMode.CLAMP)
TIP_BORDER = "#B3E2E8F0"
TIP_RADIUS = 8
TIP_PAD = 6
TIP_GAP = 5
TIP_SIZE = 11
TIP_DATE_COLOR = "#94A3B8"
TIP_VALUE_COLOR = "#000000"
TIP_DOT_SIZE = 7
# 浮框与锚点的水平距离：fl_chart 的 touchSpotThreshold 是 10px（只比 x），比它大
# 一点，光标才不会落到浮框上。
TIP_OFFSET = 14
TIP_MARGIN = 2
# 控件自带浮框的底色：全透明，等于只借它的高亮，不显示它自己的文字。
TIP_CLEAR = "#00FFFFFF"
# 这几种事件表示指针已经离开数据点，浮框要收起来。
TIP_HIDE_EVENTS = ("pointerExit", "tapCancel", "panCancel", "longPressEnd")


def axis_ceiling(values: list[int]) -> tuple[int, int]:
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


def spot_pixel(
    index: int,
    count: int,
    value: float,
    ceiling: int,
    width: float,
    height: float,
) -> tuple[float, float]:
    """数据点在图表控件里的像素位置。

    画布左边和下边留给轴刻度（`ChartAxis.label_size`），上边和右边没有轴所以不占
    位 —— fl_chart 的 `getPixelX`/`getPixelY` 正是按这块绘图区换算浮框位置的。
    """
    plot_width = max(1.0, width - Y_LABEL_SLOT)
    plot_height = max(1.0, height - X_LABEL_SLOT)
    x = Y_LABEL_SLOT + index / max(1, count - 1) * plot_width
    if not ceiling:
        return x, plot_height
    return x, plot_height - value / ceiling * plot_height


def anchor_pixel(
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    index: int,
    ceiling: int,
    width: float,
    height: float,
) -> tuple[float, float]:
    """浮框锚点：横坐标是这个数据点的位置，纵坐标取最高的一条线。"""
    anchor_x, _ = spot_pixel(index, len(labels), 0, ceiling, width, height)
    top_y = height
    for _name, values, _color in series:
        top_y = min(
            top_y,
            spot_pixel(index, len(labels), values[index], ceiling, width, height)[1],
        )
    return anchor_x, top_y


def tip_box_size(
    labels: list[str], series: list[tuple[str, list[int], str]], index: int
) -> tuple[float, float]:
    """浮框的估算尺寸：决定它贴左边还是右边、竖直方向怎么摆。"""
    rows = [
        text_width(str(values[index]), TIP_SIZE) + TIP_DOT_SIZE + TIP_GAP
        for _name, values, _color in series
    ]
    width = max([text_width(labels[index], TIP_SIZE), *rows])
    height = (TIP_SIZE + TIP_GAP) * (len(series) + 1)
    return width + TIP_PAD * 2, height + TIP_PAD * 2


def tip_content(
    labels: list[str], series: list[tuple[str, list[int], str]], index: int
) -> ft.Column:
    """浮框内容：日期一行灰字，下面每个系列「彩色圆点 + 黑色数值」。"""
    return ft.Column(
        tight=True,
        spacing=TIP_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Text(labels[index], size=TIP_SIZE, color=TIP_DATE_COLOR),
            *[
                ft.Row(
                    tight=True,
                    spacing=TIP_GAP,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=TIP_DOT_SIZE,
                            height=TIP_DOT_SIZE,
                            bgcolor=color,
                            border_radius=ft.BorderRadius.all(TIP_DOT_SIZE / 2),
                        ),
                        ft.Text(
                            str(values[index]),
                            size=TIP_SIZE,
                            weight=ft.FontWeight.BOLD,
                            color=TIP_VALUE_COLOR,
                        ),
                    ],
                )
                for _name, values, color in series
            ],
        ],
    )


def tip_placement(
    anchor_x: float,
    anchor_y: float,
    box: tuple[float, float],
    width: float,
    height: float,
) -> tuple[float | None, float | None, float]:
    """浮框的位置：横向贴锚点的一侧，纵向以最高那条线的点为中点。

    右边放得下就贴右边，放不下且左边够宽就贴左边。`TIP_OFFSET` 保证浮框整块落在
    光标的命中范围（锚点左右各 10px）之外，所以不会被光标碰到。
    """
    box_width, box_height = box
    if (
        anchor_x + TIP_OFFSET + box_width <= width - TIP_MARGIN
        or anchor_x - TIP_OFFSET - box_width < TIP_MARGIN
    ):
        left, right = anchor_x + TIP_OFFSET, None
    else:
        left, right = None, width - anchor_x + TIP_OFFSET
    top = min(
        max(anchor_y - box_height / 2, TIP_MARGIN),
        max(TIP_MARGIN, height - box_height - TIP_MARGIN),
    )
    return left, right, top


def event_index(event, count: int) -> int:
    """悬停事件命中的数据点下标；离开数据点或点在空白处时返回 -1。"""
    if getattr(event.type, "value", event.type) in TIP_HIDE_EVENTS:
        return -1
    spots = getattr(event, "spots", None) or []
    index = spots[0].spot_index if spots else -1
    return index if isinstance(index, int) and 0 <= index < count else -1


def build_interactive_line_chart(
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    width: float,
    height: float,
    x_label_step: int | None = None,
) -> ft.Control:
    """多系列折线图，带一个跟着悬停点走的自绘浮框。

    `labels`  每个点的横轴文字（1月…12月 / 9/21…9/27）
    `series`  [(名称, 数值列表, 颜色)]，每个元素画一条线
    """
    ceiling, y_step = axis_ceiling(
        [value for _, values, _ in series for value in values]
    )
    x_max = max(1, len(labels) - 1)
    shown = {"index": -1}
    tip = ft.Container(
        visible=False,
        bgcolor=TIP_BG,
        blur=TIP_BLUR,
        border=ft.Border.all(GRID_WIDTH, TIP_BORDER),
        border_radius=ft.BorderRadius.all(TIP_RADIUS),
        padding=ft.Padding.all(TIP_PAD),
    )

    def show_tip(index: int) -> None:
        """摆好浮框：换一个点才重画，同一个点重复悬停不做事。"""
        if index == shown["index"]:
            return
        shown["index"] = index
        if index < 0:
            tip.visible = False
        else:
            tip.content = tip_content(labels, series, index)
            anchor_x, anchor_y = anchor_pixel(
                labels, series, index, ceiling, width, height
            )
            tip.left, tip.right, tip.top = tip_placement(
                anchor_x,
                anchor_y,
                tip_box_size(labels, series, index),
                width,
                height,
            )
            tip.visible = True
        tip.update()

    def on_chart_event(event) -> None:
        show_tip(event_index(event, len(labels)))

    return ft.Stack(
        width=width,
        height=height,
        clip_behavior=ft.ClipBehavior.NONE,
        controls=[
            fch.LineChart(
                width=width,
                height=height,
                min_x=0,
                max_x=x_max,
                min_y=0,
                max_y=ceiling,
                # 触摸提示：点/长按某个点会弹出它的数值
                interactive=True,
                on_event=on_chart_event,
                # The card would otherwise clip a tooltip that opens above the plot.
                tooltip=fch.LineChartTooltip(
                    bgcolor=TIP_CLEAR,
                    padding=ft.Padding.all(0),
                    border_side=ft.BorderSide.none(),
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
                                # 自带浮框的文字留空：内容由上面那个 `tip` 画。
                                tooltip=fch.LineChartDataPointTooltip(text=""),
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
            ),
            tip,
        ],
    )
