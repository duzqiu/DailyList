"""Todo categories: colours and the star that marks them."""

import flet as ft

from tools.layout import text_width

STAR_SIZE = 13
DEFAULT_COLOR = "#64748B"
# The dialog's 类别 picker draws the star pair smaller than the list headers do.
PICKER_STAR_SIZE = 12
PICKER_STAR_GAP = 6
PICKER_TEXT_SIZE = 12

# One star marks a category, in the category's own colour.
CATEGORIES = (
    ("重要", "#DC2626"),
    ("一般", "#EAB308"),
    ("可选", "#16A34A"),
)
CATEGORY_COLORS = {name: color for name, color in CATEGORIES}
DEFAULT_CATEGORY = "一般"


def category_color(name: str) -> str:
    """Colour of a category, falling back to slate for unknown names."""
    return CATEGORY_COLORS.get(name, DEFAULT_COLOR)


def build_category_icon(
    name: str, size: float = STAR_SIZE, color: str | None = None
) -> ft.Control:
    """The category's star: red for 重要, yellow for 一般, green for 可选.

    `color` overrides the star's own colour - the 数据统计 headers paint the star
    in the ink that reads on the category's solid background.
    """
    if name not in CATEGORY_COLORS:
        return ft.Icon(
            ft.Icons.LABEL_OUTLINE, size=size, color=color or DEFAULT_COLOR
        )
    return ft.Icon(ft.Icons.STAR, size=size, color=color or category_color(name))


def build_category_label(name: str, text: ft.Control) -> ft.Control:
    """「★ 重要」- the star pair the list pages and the 类别 picker show."""
    return ft.Row(
        tight=True,
        spacing=PICKER_STAR_GAP,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            build_category_icon(name, size=PICKER_STAR_SIZE),
            text,
        ],
    )


def category_label_width(name: str) -> float:
    """Width of「★ 重要」as a menu entry renders it."""
    return PICKER_STAR_SIZE + PICKER_STAR_GAP + text_width(
        name, PICKER_TEXT_SIZE
    )
