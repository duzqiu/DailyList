"""Line chart drawn with `flet.canvas`.

Flet 1.0 ships no chart control (charts live in a separate package), so the
trend chart is composed from canvas primitives: one stroked polyline per series
(`Points` with `PointMode.POLYGON` - "draw the entire sequence of point as one
line") plus grid lines and axis labels.
"""

import flet as ft
import flet.canvas as cv

GRID_COLOR = "#E2E8F0"
AXIS_COLOR = "#CBD5E1"
LABEL_COLOR = "#94A3B8"
LABEL_SIZE = 9
DOT_RADIUS = 2
LINE_WIDTH = 2
# Room reserved inside the canvas for the y-axis (left) and x-axis (bottom)
# labels; the right/left insets also keep the first/last x label from clipping.
PLOT_LEFT = 26
PLOT_RIGHT = 20
PLOT_TOP = 10
PLOT_BOTTOM = 20


def build_line_chart(
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    width: float,
    height: float,
) -> cv.Canvas:
    """Build a line chart; `series` is `[(name, one count per label, colour)]`."""
    plot_width = max(1.0, width - PLOT_LEFT - PLOT_RIGHT)
    plot_height = max(1.0, height - PLOT_TOP - PLOT_BOTTOM)
    counts = [count for _, values, _ in series for count in values]
    ceiling = max([1, *counts])

    def x_at(index: int) -> float:
        if len(labels) <= 1:
            return PLOT_LEFT + plot_width / 2
        return PLOT_LEFT + plot_width * index / (len(labels) - 1)

    def y_at(count: int) -> float:
        return PLOT_TOP + plot_height * (1 - count / ceiling)

    shapes: list[cv.Shape] = []
    # Y axis (vertical, on the left) and X axis (horizontal, at 0), then the
    # maximum grid line on top.
    shapes.append(
        cv.Line(
            PLOT_LEFT,
            PLOT_TOP,
            PLOT_LEFT,
            PLOT_TOP + plot_height,
            paint=ft.Paint(color=AXIS_COLOR, stroke_width=1),
        )
    )
    for count in (0, ceiling):
        y = y_at(count)
        shapes.append(
            cv.Line(
                PLOT_LEFT,
                y,
                PLOT_LEFT + plot_width,
                y,
                paint=ft.Paint(
                    color=AXIS_COLOR if count == 0 else GRID_COLOR,
                    stroke_width=1,
                ),
            )
        )
        shapes.append(
            cv.Text(
                PLOT_LEFT - 6,
                y,
                str(count),
                style=ft.TextStyle(size=LABEL_SIZE, color=LABEL_COLOR),
                alignment=ft.Alignment.CENTER_RIGHT,
            )
        )

    label_style = ft.TextStyle(size=LABEL_SIZE, color=LABEL_COLOR)
    for index in sorted({0, len(labels) // 2, len(labels) - 1}):
        if 0 <= index < len(labels):
            shapes.append(
                cv.Text(
                    x_at(index),
                    PLOT_TOP + plot_height + LABEL_SIZE,
                    labels[index],
                    style=label_style,
                    alignment=ft.Alignment.CENTER,
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
    return cv.Canvas(width=width, height=height, shapes=shapes)
