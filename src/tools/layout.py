"""Shared layout metrics and page background of the app."""

import flet as ft

BACKGROUND_COLORS = ("#FFFFFF", "#EEF2FF")
# Solid colour behind the gradient: the native page background.
PAGE_BGCOLOR = BACKGROUND_COLORS[-1]

MENU_BAR_BOTTOM = 16
MENU_BAR_HEIGHT = 54
MENU_BAR_GAP = 8
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
