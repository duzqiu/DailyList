"""Shared layout metrics and page background of the app."""

import flet as ft

BACKGROUND_COLORS = ("#FFFFFF", "#EEF2FF")
# Solid colour behind the gradient: the native page background.
PAGE_BGCOLOR = BACKGROUND_COLORS[-1]

# A todo that has been tapped - i.e. marked done - switches to the sky blue the
# add button uses. The card stays fully opaque: it sits on top of the swipe-to-
# delete button, which a translucent fill would let show through.
# The todo's own text is plain black and stays the same in both states.
SKY_BLUE = "#B2E0F4"
TODO_DONE_BG = SKY_BLUE
# Same navy as the add button's plus, so the two tiles read as one family.
TODO_DONE_ICON = "#173A54"
TODO_TEXT = "#000000"

MENU_BAR_BOTTOM = 16
MENU_BAR_HEIGHT = 54
MENU_BAR_GAP = 8
# Material 3 dialogs default to a 28px corner radius; the app uses 12, the same
# radius as its cards and option panels, so every dialog shares this value.
DIALOG_RADIUS = 12
# Distance kept clear at the bottom of scrollable lists so their last row can rest
# just above the floating menu bar.
BOTTOM_MENU_INSET = MENU_BAR_BOTTOM + MENU_BAR_HEIGHT + MENU_BAR_GAP


def page_gradient() -> ft.LinearGradient:
    """White to indigo wash shared by the home, calendar and settings pages."""
    return ft.LinearGradient(
        colors=list(BACKGROUND_COLORS),
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
    )


def text_width(text: str, size: float) -> float:
    """Rough advance width of `text` drawn at `size`.

    CJK glyphs are full-width while digits and letters take about half, which is
    enough to reserve room for a label without asking the renderer to measure it.
    """
    return sum(size * (1.0 if ord(char) > 0x2E80 else 0.55) for char in text)
