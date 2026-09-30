"""待办趋势折线图：官方 `LineChart` 画线，浮框由本文件用 Flet 控件自己画。

Flet 1.0 把图表控件拆到了独立的 ``flet-charts`` 包：`LineChart` 能在同一张图里挂多条
`LineChartData`（多系列），自带网格、轴刻度和 y 轴线。

浮框（点按提示）没有用它自带的那个：fl_chart 的浮框是「一个系列一行」，每行只有一种
颜色（`text_spans` 在 flet-charts 1.0.1 里到不了 Dart 侧），画不出「灰色日期 + 彩色
圆点 + 黑色数值」。所以整张图**关掉自带触摸**（`interactive=False`）—— 自带那套触摸还会
画一条竖直的指示线、把点到的那颗点放大，这两样都不要；手势改由外面那层
`ft.GestureDetector` 自己接（点按 / 横向拖动 / 悬停），浮框是我们挂在同一个 `ft.Stack`
上的 `ft.Container`，位置按下标自己算（`spot_pixel` / `tip_placement`）。

**线上的圆点也自己画**（`build_dots`）：关掉自带触摸之后，控件那颗点整个不出现了
（`interactive=False` 时它不画），所以每条线的每个点都由我们摆一颗圆点 ——
**没点的时候是实心圆**（填满分类色，`DOT_DIAMETER`），**点住那一格时换成空心、放大**
（`ACTIVE_DOT_DIAMETER` + 一圈 `ACTIVE_DOT_STROKE_WIDTH` 同色线），两种样子都在
`style_dot` 里换。点与点之间连的仍是折线本身（**实线**，`LINE_WIDTH`）；**点住那一列**
另有一条**浅灰细虚线**（`build_guide` / `GUIDE_*`）把这一列的几个圆点串起来，从最上面
那颗的下沿连到最下面那颗的上沿 —— 它只是「这一列是同一天」的引导线，不是折线。点多过
`POINT_LIMIT` 的维度（一个月 28-31 天）不画点：一条线上三十来个圆点会连成一条链子。

手势（见 `build_interactive_line_chart` 里的几个回调）：

- **点一下**：浮框停在最近的那个点上，之后再点同一点才收起来；
- **横向拖动**：沿着曲线看别的点，浮框一路跟过去（用横向拖动而不是 pan，顺手把竖直
  方向的滚动留给页面 —— pan 会和外面 `ListView` 的滚动抢手势）；
- **悬停**（桌面鼠标）：跟着鼠标走，移开就收 —— **但点住的那一点不会被悬停带走**。

浮框是毛玻璃：半透明灰白底（`#CCF1F5F9`，`#AARRGGBB`）+ `blur=ft.Blur(12, 12, ft.BlurTileMode.CLAMP)`，
与「+」按钮、底部菜单栏同一套写法。
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
# 折线本身：**实线**，点与点之间就靠它连（虚线不用在这里 —— 见下面的 GUIDE_*）。
LINE_WIDTH = 2.5
# 线上的圆点**自己画**（见文件开头）：关掉自带触摸之后，控件那颗点不再出现
# （`interactive=False` 时不画）。平时是**实心圆** —— 填满自己的分类色（一眼看出这条线
# 是哪个等级，也压得住底下的网格线）；**点住的那一颗换成空心、放大到
# `ACTIVE_DOT_DIAMETER`、圈线 `ACTIVE_DOT_STROKE_WIDTH`**，圈里空着、露出来的是页面
# 渐变 —— 和浮框一起指明「现在看的是哪一格」。两种样子都在 `style_dot` 里换。
DOT_DIAMETER = 8
ACTIVE_DOT_DIAMETER = 11
ACTIVE_DOT_STROKE_WIDTH = 2
# 点住那一列：把这一列的几个圆点用一条**浅灰细虚线**串起来（只是「这一列是同一天」
# 的引导线，不是折线本身），从最上面那颗的下沿连到最下面那颗的上沿，不穿过圆点。
# Flet 没有虚线边框，所以按「一段实线 + 一段空」拼出来（见 build_guide）。
GUIDE_COLOR = "#94A3B8"
GUIDE_WIDTH = 1
GUIDE_DASH = 3
GUIDE_GAP = 3
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


def event_index(event, count: int, width: float) -> int:
    """手势事件命中的数据点下标：按事件里的横坐标取**最近**的那个点。

    和 `spot_pixel` 是同一套换算反过来用（画布左边留给 y 刻度，右边到底是一个点），
    所以手指点在两点之间也能落到最近的那一点上，不需要非点中图上的圆点。
    """
    position = getattr(event, "local_position", None)
    if position is None:
        return -1
    plot_width = max(1.0, width - Y_LABEL_SLOT)
    ratio = (position.x - Y_LABEL_SLOT) / plot_width
    return max(0, min(count - 1, round(ratio * (count - 1))))


def build_interactive_line_chart(
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    width: float,
    height: float,
    x_label_step: int | None = None,
) -> ft.Control:
    """多系列折线图，带一个跟着点按 / 悬停走的自绘浮框。

    `labels`  每个点的横轴文字（1月…12月 / 9/21…9/27）
    `series`  [(名称, 数值列表, 颜色)]，每个元素画一条线
    """
    ceiling, y_step = axis_ceiling(
        [value for _, values, _ in series for value in values]
    )
    x_max = max(1, len(labels) - 1)
    # index = 浮框现在画在哪个点上（-1 = 收着）；pinned = 点住的那一点（-1 = 没点住）；
    # dragged = 这一次手势里横拖过（拖动之后的抬手不算「点选」，别再把它取消掉）；
    # active = 手指/鼠标还按在图上（这期间指针移出图表不算「离开」）。
    shown = {"index": -1, "pinned": -1, "dragged": False, "active": False}
    tip = ft.Container(
        visible=False,
        bgcolor=TIP_BG,
        blur=TIP_BLUR,
        border=ft.Border.all(GRID_WIDTH, TIP_BORDER),
        border_radius=ft.BorderRadius.all(TIP_RADIUS),
        padding=ft.Padding.all(TIP_PAD),
    )
    # 自己画的圆点：{(第几条线, 第几个点): 那颗点}。
    dots: dict[tuple[int, int], ft.Container] = {}
    # 点住那一列的浅灰细虚线（见 GUIDE_*）。它是一根定位的柱子，里面按「一段实线 +
    # 一段空」码一串小方块 —— Flet 没有虚线边框。
    guide = ft.Container(visible=False, width=GUIDE_WIDTH)

    def build_guide(index: int) -> None:
        """把这一列几个圆点之间的虚线摆好（`index < 0` 收起来）。

        只在**最上面那颗的下沿**和**最下面那颗的上沿**之间连 —— 两头都让开圆点，
        圆点是空心的，线穿进去就成了「圆里一道线」，不好看。
        """
        if index < 0:
            guide.visible = False
            return
        centers: list[float] = []
        for _name, values, _color in series:
            if index >= len(values):
                continue
            _x, y = spot_pixel(
                index, len(labels), values[index], ceiling, width, height
            )
            centers.append(y)
        if len(centers) < 2:
            guide.visible = False
            return
        top = min(centers) + ACTIVE_DOT_DIAMETER / 2
        bottom = max(centers) - ACTIVE_DOT_DIAMETER / 2
        span = bottom - top
        if span <= GUIDE_DASH:
            # 几个点挤在一格里（都没待办时都在 0 线上）：没地方画虚线，不画。
            guide.visible = False
            return
        x, _y = spot_pixel(
            index, len(labels), series[0][1][index], ceiling, width, height
        )
        guide.left = x - GUIDE_WIDTH / 2
        guide.top = top
        guide.height = span
        guide.content = ft.Column(
            tight=True,
            spacing=GUIDE_GAP,
            controls=[
                ft.Container(
                    width=GUIDE_WIDTH, height=GUIDE_DASH, bgcolor=GUIDE_COLOR
                )
                for _ in range(max(1, int(span // (GUIDE_DASH + GUIDE_GAP))))
            ],
        )
        guide.visible = True

    def style_dot(dot: ft.Container, color: str, active: bool) -> None:
        """把一颗点改写成 `active` 那一档的样子（以自己中心重摆，位置不跳）。

        平时：`DOT_DIAMETER` 的**实心圆**（填满分类色）；点住的那颗：放大到
        `ACTIVE_DOT_DIAMETER`、**空心**（不填底，只画一圈同色的线）。
        """
        diameter = ACTIVE_DOT_DIAMETER if active else DOT_DIAMETER
        center_x = dot.left + dot.width / 2
        center_y = dot.top + dot.height / 2
        dot.width = dot.height = diameter
        dot.border_radius = ft.BorderRadius.all(diameter / 2)
        if active:
            dot.bgcolor = None
            dot.border = ft.Border.all(ACTIVE_DOT_STROKE_WIDTH, color)
        else:
            dot.bgcolor = color
            dot.border = None
        dot.left = center_x - diameter / 2
        dot.top = center_y - diameter / 2

    def highlight_dots(index: int) -> None:
        """把 `index` 那一列的点改成空心放大（其余回到实心）—— 一眼看出浮框指着哪一格。"""
        changed: list[ft.Container] = []
        for (series_index, point_index), dot in dots.items():
            active = point_index == index
            wanted_size = ACTIVE_DOT_DIAMETER if active else DOT_DIAMETER
            # 大小和「实 / 空」两样都得对：收起来时实心、点住时空心。
            if dot.width == wanted_size and (dot.bgcolor is None) == active:
                continue
            style_dot(dot, series[series_index][2], active)
            changed.append(dot)
        for dot in changed:
            dot.update()

    def build_dots() -> list[ft.Control]:
        """每条线上的圆点（见文件开头：控件自己那颗不画了）。

        点多过 `POINT_LIMIT` 的那一档不画 —— 一条线上三十来个点会连成虚线。
        """
        made: list[ft.Control] = []
        for series_index, (_name, values, color) in enumerate(series):
            if len(values) > POINT_LIMIT:
                continue
            for index, value in enumerate(values):
                x, y = spot_pixel(
                    index, len(labels), value, ceiling, width, height
                )
                dot = ft.Container(
                    left=x - DOT_DIAMETER / 2,
                    top=y - DOT_DIAMETER / 2,
                    width=DOT_DIAMETER,
                    height=DOT_DIAMETER,
                    border_radius=ft.BorderRadius.all(DOT_DIAMETER / 2),
                    # 实心：填满自己的分类色（点住时才换成空心，见 style_dot）。
                    bgcolor=color,
                )
                dots[(series_index, index)] = dot
                made.append(dot)
        return made

    def show_tip(index: int) -> None:
        """摆好浮框：换一个点才重画，同一个点重复悬停不做事。"""
        if index == shown["index"]:
            return
        shown["index"] = index
        highlight_dots(index)
        build_guide(index)
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
        # 虚线是另一个控件，得自己推一下（和浮框同一处、同一个前提：页面已在屏上）。
        guide.update()

    def on_tap_down(event) -> None:
        """按下去：先落到最近的那一点上（还没「点住」，等抬手那一下再定）。"""
        shown["active"] = True
        shown["dragged"] = False
        index = event_index(event, len(labels), width)
        if index >= 0:
            show_tip(index)

    def on_tap_up(event) -> None:
        """抬手：点在别处就**点住**那个点，点在同一点上就收起来。

        触屏抬手不会再收到任何 `pointerExit`（自带触摸关掉了、手势是我们自己接的），
        所以不会出现「浮框刚出来又被收走」的那一闪。
        """
        shown["active"] = False
        if shown["dragged"]:
            # 横拖之后抬的手：保持停在最后那一点上。
            shown["dragged"] = False
            return
        index = event_index(event, len(labels), width)
        if index < 0 or index == shown["pinned"]:
            shown["pinned"] = -1
            show_tip(-1)
            return
        shown["pinned"] = index
        show_tip(index)

    def on_drag_start(event) -> None:
        """横向拖动的第一下：浮框挪过去并点住 —— 后面每挪一步都跟着走。"""
        shown["active"] = True
        shown["dragged"] = True
        follow(event)

    def on_drag_update(event) -> None:
        follow(event)

    def follow(event) -> None:
        index = event_index(event, len(labels), width)
        if index >= 0:
            shown["pinned"] = index
            show_tip(index)

    def on_release(event) -> None:
        """横拖结束 / 手势取消：松手，浮框留在最后那一点上（没点住才收）。"""
        shown["active"] = False
        if shown["pinned"] < 0:
            show_tip(-1)

    def on_hover(event) -> None:
        """桌面鼠标悬停：跟着走 —— 但**点住的那一点不会被悬停带走**。"""
        if shown["pinned"] >= 0:
            return
        index = event_index(event, len(labels), width)
        if index >= 0:
            show_tip(index)

    def on_exit(event) -> None:
        """鼠标移出图表：没点住的收起来（点住的留着）。"""
        if shown["pinned"] < 0 and not shown["active"]:
            show_tip(-1)

    gestures = ft.GestureDetector(
        # 横向拖动而不是 pan：竖直方向留给页面滚（pan 会和外面 ListView 抢手势）。
        on_tap_down=on_tap_down,
        on_tap_up=on_tap_up,
        on_tap_cancel=on_release,
        on_horizontal_drag_start=on_drag_start,
        on_horizontal_drag_update=on_drag_update,
        on_horizontal_drag_end=on_release,
        on_horizontal_drag_cancel=on_release,
        on_hover=on_hover,
        on_exit=on_exit,
        content=fch.LineChart(
            width=width,
            height=height,
            min_x=0,
            max_x=x_max,
            min_y=0,
            max_y=ceiling,
            # **关掉自带触摸**：它那套还会画一条竖直指示线、把点到的那颗点放大 ——
            # 两样都不要；手势和浮框由外面这层手势控件 + 自绘容器负责（见文件开头）。
            interactive=False,
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
                        fch.LineChartDataPoint(x=index, y=value)
                        for index, value in enumerate(values)
                    ],
                    color=color,
                    stroke_width=LINE_WIDTH,
                    curved=True,
                    # A curve through few points otherwise dips under the zero line.
                    prevent_curve_over_shooting=True,
                    # 线上的点**不由控件画**：它那颗点在 `interactive=False` 时不出现，
                    # 这里自己摆（见 build_dots）。
                )
                for _name, values, color in series
            ],
        ),
    )

    return ft.Stack(
        width=width,
        height=height,
        # 浮框可以开到画布外一点点，这一层别裁它。
        clip_behavior=ft.ClipBehavior.NONE,
        # 图 → 那一列的引导虚线 → 我们摆的圆点 → 浮框
        # （虚线垫在点下面，点压在线上，浮框压在最上面）。
        controls=[gestures, guide, *build_dots(), tip],
    )
