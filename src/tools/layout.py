"""Shared layout metrics and page background of the app."""

import flet as ft

BACKGROUND_COLORS = ("#FFFFFF", "#EEF2FF")
# Solid colour behind the gradient: the native page background.
PAGE_BGCOLOR = BACKGROUND_COLORS[-1]

# An open todo takes the colour of its category (see tools/categories.py) and
# keeps the same neutral card as a completed one - no fill either way. Only the
# done state changes the text: grey, struck through, behind a green check.
SKY_BLUE = "#B2E0F4"
# A completed todo greys out and is struck through, the way a paper list reads
# once an item is ticked off.
TODO_DONE_TEXT = "#94A3B8"
TODO_DONE_STRIKE_THICKNESS = 1.5
# A todo row is the state marker plus the text, and both share one size so the
# circle never looks bigger or smaller than the line it belongs to.
TODO_TEXT_SIZE = 15
# The marker in front of a todo: an empty ring while the todo is open, a green
# filled circle with a white check once it is done.
TODO_MARK_SIZE = 15
TODO_MARK_COLOR = "#94A3B8"
TODO_MARK_BORDER_WIDTH = 1.5
TODO_MARK_DONE_BG = "#22C55E"
TODO_MARK_DONE_CHECK = "#FFFFFF"
# The「9月26日待办」heading above the list stays a quiet caption next to the
# rows, so it sits a step below the todo text itself.
TODO_TITLE_SIZE = 14
# A todo's time of day is a quiet second line under its text.
TODO_TIME_SIZE = 11
TODO_TIME_COLOR = "#94A3B8"

MENU_BAR_BOTTOM = 16
MENU_BAR_HEIGHT = 46
MENU_BAR_GAP = 8
# Icon and label of one bottom-menu entry, sized to sit inside the shorter bar.
MENU_ICON_SIZE = 20
MENU_LABEL_SIZE = 10
# Material 3 dialogs default to a 28px corner radius; the app uses 12, the same
# radius as its cards and option panels, so every dialog shares this value.
DIALOG_RADIUS = 12
# Material's dialog surface (surfaceContainerHigh). Every dialog is painted this
# colour, and an option panel opened *inside* a dialog borrows it too, so the
# dropdown reads as part of the dialog instead of a white card floating on it.
DIALOG_SURFACE = "#E4E9EF"
# Distance kept clear at the bottom of scrollable lists so their last row can rest
# just above the floating menu bar.
BOTTOM_MENU_INSET = MENU_BAR_BOTTOM + MENU_BAR_HEIGHT + MENU_BAR_GAP


def dialog_button_style() -> ft.ButtonStyle:
    """Plain dialog action button: no ripple, no hover fill, no elevation."""
    return ft.ButtonStyle(
        bgcolor="#00000000",
        overlay_color="#00000000",
        shadow_color="#00000000",
        elevation=0,
    )


def page_gradient() -> ft.LinearGradient:
    """White to indigo wash shared by the home, calendar and settings pages."""
    return ft.LinearGradient(
        colors=list(BACKGROUND_COLORS),
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
    )


def build_todo_mark(done: bool) -> ft.Control:
    """The circle drawn in front of a todo, in either of its two states.

    The diameter is kept at `TODO_MARK_SIZE` (the todo font size) so the circle
    and the text line up instead of one outgrowing the other.
    """
    if done:
        return ft.Container(
            width=TODO_MARK_SIZE,
            height=TODO_MARK_SIZE,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=TODO_MARK_DONE_BG,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(
                ft.Icons.CHECK,
                size=TODO_MARK_SIZE * 0.72,
                color=TODO_MARK_DONE_CHECK,
            ),
        )
    return ft.Container(
        width=TODO_MARK_SIZE,
        height=TODO_MARK_SIZE,
        shape=ft.BoxShape.CIRCLE,
        border=ft.Border.all(TODO_MARK_BORDER_WIDTH, TODO_MARK_COLOR),
    )


def todo_text_style(done: bool) -> ft.TextStyle | None:
    """Grey strikethrough for a completed todo; `None` keeps the default face."""
    if not done:
        return None
    return ft.TextStyle(
        decoration=ft.TextDecoration.LINE_THROUGH,
        decoration_color=TODO_DONE_TEXT,
        decoration_thickness=TODO_DONE_STRIKE_THICKNESS,
    )


def todo_time_label(due_time: str) -> str:
    """「09:30」- how a todo's time of day is printed, here and in the picker."""
    return due_time


def text_width(text: str, size: float) -> float:
    """Rough advance width of `text` drawn at `size`.

    CJK glyphs are full-width while digits and letters take about half, which is
    enough to reserve room for a label without asking the renderer to measure it.
    """
    return sum(size * (1.0 if ord(char) > 0x2E80 else 0.55) for char in text)
