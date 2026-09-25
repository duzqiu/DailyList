"""Line chart drawn with `flet.canvas`.

Flet 1.0 ships no chart control (charts live in a separate package), so the
trend chart is composed from canvas primitives: one stroked polyline per series
(`Points` with `PointMode.POLYGON` - "draw the entire sequence of point as one
line") plus grid lines and axis labels.
"""

import math
from collections.abc import Callable

import flet as ft
import flet.canvas as cv

from tools.layout import text_width

GRID_COLOR = "#E2E8F0"
AXIS_COLOR = "#CBD5E1"
LABEL_COLOR = "#94A3B8"
LABEL_SIZE = 9
# The 年 view names all twelve months, so each label gets half the horizontal
# room a 月/周 label has; the smaller face keeps neighbouring months apart.
DENSE_LABEL_SIZE = 8
DOT_RADIUS = 2
LINE_WIDTH = 2
# Room reserved inside the canvas for the y-axis (left) and x-axis (bottom)
# labels; the right/left insets also keep the first/last x label from clipping.
PLOT_LEFT = 26
PLOT_RIGHT = 20
PLOT_TOP = 10
PLOT_BOTTOM = 20
LABEL_GAP = 2
# An axis labelled 0/2/4/6/8 reads better than one tick per todo, so the scale
# aims for at most this many intervals and rounds the top up to a 1/2/5/10...
# step that keeps every tick a whole number.
MAX_Y_INTERVALS = 4
NICE_STEPS = (
    1, 2, 5, 10, 20, 25, 50,
    100, 200, 250, 500,
    1_000, 2_000, 2_500, 5_000,
    10_000, 20_000, 25_000, 50_000,
    100_000, 200_000, 250_000, 500_000,
    1_000_000,
)
# Tap-to-inspect: the tapped point keeps a guide line and a tooltip listing that
# day's (or month's) numbers per category.
GUIDE_COLOR = "#CBD5E1"
TIP_BG = "#FFFFFF"
TIP_BORDER = "#CBD5E1"
TIP_TITLE_COLOR = "#172554"
TIP_TEXT_COLOR = "#334155"
TIP_FONT_SIZE = 9
TIP_PAD = 6
TIP_ROW_GAP = 4
TIP_DOT_RADIUS = 2.5
TIP_DOT_GAP = 5
TIP_OFFSET = 8
TIP_MARGIN = 2


def y_ticks(ceiling: int) -> tuple[list[int], int]:
    """Y-axis tick values from 0 up, plus the rounded top of the axis."""
    for candidate in NICE_STEPS:
        step = candidate
        if ceiling <= candidate * MAX_Y_INTERVALS:
            break
    else:
        # More todos than the listed steps cover: keep scaling the largest one.
        while ceiling > step * MAX_Y_INTERVALS:
            step *= 10
    top = max(step, math.ceil(ceiling / step) * step)
    return list(range(0, top + 1, step)), top


def x_label_indices(count: int, step: int | None) -> list[int]:
    """Indices of the points that get an x-axis label.

    `None` keeps the sparse axis (first, middle and last point); `1` names every
    point, which is what the 年 view needs so no month goes unnamed.
    """
    if count <= 0:
        return []
    if step is None:
        return sorted({0, count // 2, count - 1})
    return list(range(0, count, max(1, step)))


def chart_metrics(
    series: list[tuple[str, list[int], str]], width: float
) -> tuple[list[int], int, float, float]:
    """Y ticks, axis top, left inset and plot width.

    Drawing and tap hit-testing both go through this, so a tap lands on the
    point the user actually sees. A multi-digit tick label widens the left inset
    instead of losing the gap between itself and the axis.
    """
    counts = [count for _, values, _ in series for count in values]
    ticks, ceiling = y_ticks(max([1, *counts]))
    left = max(
        PLOT_LEFT,
        max(text_width(str(value), LABEL_SIZE) for value in ticks) + LABEL_GAP + 4,
    )
    return ticks, ceiling, left, max(1.0, width - left - PLOT_RIGHT)


def selection_shapes(
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    index: int,
    x_at: Callable[[int], float],
    y_at: Callable[[int], float],
    width: float,
    height: float,
) -> list[cv.Shape]:
    """Enlarged dots on the tapped point plus its numbers tooltip."""
    anchor_x = x_at(index)
    rows = [(name, values[index], color) for name, values, color in series]
    dot_width = TIP_DOT_RADIUS * 2 + TIP_DOT_GAP
    row_width = max(
        (text_width(f"{name} {value}", TIP_FONT_SIZE) for name, value, _ in rows),
        default=0.0,
    )
    row_height = TIP_FONT_SIZE + TIP_ROW_GAP
    box_width = max(text_width(labels[index], TIP_FONT_SIZE), dot_width + row_width)
    box_width += TIP_PAD * 2
    box_height = TIP_PAD * 2 + row_height * (len(rows) + 1)
    # Sits above the tapped point, flipping below it when it would leave the top
    # of the canvas, and always stays inside the canvas horizontally.
    point_ys = [y_at(values[index]) for _, values, _ in series]
    box_x = min(
        max(anchor_x - box_width / 2, TIP_MARGIN), width - box_width - TIP_MARGIN
    )
    box_y = min(point_ys) - TIP_OFFSET - box_height
    if box_y < TIP_MARGIN:
        box_y = max(point_ys) + TIP_OFFSET
    box_y = min(max(box_y, TIP_MARGIN), height - box_height - TIP_MARGIN)

    shapes: list[cv.Shape] = []
    for _, values, color in series:
        y = y_at(values[index])
        shapes.append(
            cv.Circle(
                anchor_x,
                y,
                DOT_RADIUS + 2,
                paint=ft.Paint(color=TIP_BG, style=ft.PaintingStyle.FILL),
            )
        )
        shapes.append(
            cv.Circle(
                anchor_x,
                y,
                DOT_RADIUS + 1,
                paint=ft.Paint(color=color, style=ft.PaintingStyle.FILL),
            )
        )
    # The 1px border is a filled rect behind the white one - canvas rects only
    # take a fill paint.
    shapes.append(
        cv.Rect(
            box_x,
            box_y,
            box_width,
            box_height,
            border_radius=6,
            paint=ft.Paint(color=TIP_BORDER),
        )
    )
    shapes.append(
        cv.Rect(
            box_x + 1,
            box_y + 1,
            box_width - 2,
            box_height - 2,
            border_radius=5,
            paint=ft.Paint(color=TIP_BG),
        )
    )
    title_y = box_y + TIP_PAD + row_height / 2
    shapes.append(
        cv.Text(
            box_x + TIP_PAD,
            title_y,
            labels[index],
            style=ft.TextStyle(
                size=TIP_FONT_SIZE,
                weight=ft.FontWeight.BOLD,
                color=TIP_TITLE_COLOR,
            ),
            alignment=ft.Alignment.CENTER_LEFT,
        )
    )
    for row_index, (name, value, color) in enumerate(rows):
        row_y = title_y + row_height * (row_index + 1)
        shapes.append(
            cv.Circle(
                box_x + TIP_PAD + TIP_DOT_RADIUS,
                row_y,
                TIP_DOT_RADIUS,
                paint=ft.Paint(color=color, style=ft.PaintingStyle.FILL),
            )
        )
        shapes.append(
            cv.Text(
                box_x + TIP_PAD + dot_width,
                row_y,
                f"{name} {value}",
                style=ft.TextStyle(size=TIP_FONT_SIZE, color=TIP_TEXT_COLOR),
                alignment=ft.Alignment.CENTER_LEFT,
            )
        )
    return shapes


def build_line_chart(
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    width: float,
    height: float,
    x_label_step: int | None = None,
    selected: int | None = None,
) -> cv.Canvas:
    """Build a line chart; `series` is `[(name, one count per label, colour)]`.

    `x_label_step` is the spacing between x-axis labels: `None` keeps the sparse
    axis (first, middle and last point), `1` names every point.

    `selected` marks one point as inspected: it gets a guide line, enlarged dots
    and a tooltip with that point's numbers per series.
    """
    ticks, ceiling, plot_left, plot_width = chart_metrics(series, width)
    label_size = (
        DENSE_LABEL_SIZE if x_label_step == 1 and len(labels) > 8 else LABEL_SIZE
    )
    plot_height = max(1.0, height - PLOT_TOP - PLOT_BOTTOM)

    def x_at(index: int) -> float:
        if len(labels) <= 1:
            return plot_left + plot_width / 2
        return plot_left + plot_width * index / (len(labels) - 1)

    def y_at(count: int) -> float:
        return PLOT_TOP + plot_height * (1 - count / ceiling)

    shapes: list[cv.Shape] = []
    # Y axis (vertical, on the left) plus one labelled grid line per tick; the
    # zero line doubles as the x axis and stays darker than the other ticks.
    shapes.append(
        cv.Line(
            plot_left,
            PLOT_TOP,
            plot_left,
            PLOT_TOP + plot_height,
            paint=ft.Paint(color=AXIS_COLOR, stroke_width=1),
        )
    )
    for count in ticks:
        y = y_at(count)
        shapes.append(
            cv.Line(
                plot_left,
                y,
                plot_left + plot_width,
                y,
                paint=ft.Paint(
                    color=AXIS_COLOR if count == 0 else GRID_COLOR,
                    stroke_width=1,
                ),
            )
        )
        shapes.append(
            cv.Text(
                plot_left - 6,
                y,
                str(count),
                style=ft.TextStyle(size=LABEL_SIZE, color=LABEL_COLOR),
                alignment=ft.Alignment.CENTER_RIGHT,
            )
        )

    label_style = ft.TextStyle(size=label_size, color=LABEL_COLOR)
    for index in x_label_indices(len(labels), x_label_step):
        if 0 <= index < len(labels):
            shapes.append(
                cv.Text(
                    x_at(index),
                    PLOT_TOP + plot_height + label_size,
                    labels[index],
                    style=label_style,
                    alignment=ft.Alignment.CENTER,
                )
            )

    # The guide line belongs under the data, the tooltip on top of it.
    if selected is not None and 0 <= selected < len(labels):
        shapes.append(
            cv.Line(
                x_at(selected),
                PLOT_TOP,
                x_at(selected),
                PLOT_TOP + plot_height,
                paint=ft.Paint(color=GUIDE_COLOR, stroke_width=1),
            )
        )

    for _, values, color in series:
        points = [ft.Offset(x_at(i), y_at(c)) for i, c in enumerate(values)]
        if len(points) > 1:
            shapes.append(
                cv.Points(
                    points,
                    point_mode=cv.PointMode.POLYGON,
                    paint=ft.Paint(
                        color=color,
                        stroke_width=LINE_WIDTH,
                        stroke_cap=ft.StrokeCap.ROUND,
                        stroke_join=ft.StrokeJoin.ROUND,
                    ),
                )
            )
        shapes.extend(
            cv.Circle(
                point.x,
                point.y,
                DOT_RADIUS,
                paint=ft.Paint(color=color, style=ft.PaintingStyle.FILL),
            )
            for point in points
        )
    if selected is not None and 0 <= selected < len(labels):
        shapes.extend(
            selection_shapes(
                labels, series, selected, x_at, y_at, width, height
            )
        )
    return cv.Canvas(width=width, height=height, shapes=shapes)


def build_interactive_line_chart(
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    width: float,
    height: float,
    x_label_step: int | None = None,
) -> ft.Control:
    """Line chart that reveals a point's numbers when it is tapped.

    Tapping a column pins that point's tooltip; tapping the same point again
    dismisses it. The chart owns this selection, so a caller only rebuilds it
    when the data or the range changes.
    """
    holder = ft.Container()
    state: dict[str, int | None] = {"selected": None}

    def render() -> None:
        holder.content = build_line_chart(
            labels, series, width, height, x_label_step, state["selected"]
        )

    def nearest_index(x: float) -> int:
        """Index of the point under a canvas-local x, using the drawn geometry."""
        _, _, plot_left, plot_width = chart_metrics(series, width)
        if len(labels) <= 1:
            return 0
        slot = plot_width / (len(labels) - 1)
        index = round((x - plot_left) / slot)
        return min(max(index, 0), len(labels) - 1)

    def on_tap(e: ft.TapEvent[ft.GestureDetector]) -> None:
        index = nearest_index(e.local_position.x if e.local_position else 0.0)
        state["selected"] = None if state["selected"] == index else index
        render()
        holder.update()

    render()
    return ft.GestureDetector(content=holder, on_tap_down=on_tap)
