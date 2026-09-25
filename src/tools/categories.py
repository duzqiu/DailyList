"""Todo categories: colours and the star that marks them."""

import flet as ft

STAR_SIZE = 13
DEFAULT_COLOR = "#64748B"

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


def build_category_icon(name: str, size: float = STAR_SIZE) -> ft.Control:
    """The category's star: red for 重要, yellow for 一般, green for 可选."""
    if name not in CATEGORY_COLORS:
        return ft.Icon(ft.Icons.LABEL_OUTLINE, size=size, color=DEFAULT_COLOR)
    return ft.Icon(ft.Icons.STAR, size=size, color=category_color(name))
