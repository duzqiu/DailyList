"""Todo categories: colours and star icons shared by the pages."""

import flet as ft

STAR_SIZE = 13
STAR_SPACING = 1
DEFAULT_COLOR = "#64748B"

CATEGORIES = (
    ("重要", "#DC2626", 5),
    ("一般", "#EAB308", 3),
    ("可选", "#16A34A", 1),
)
CATEGORY_COLORS = {name: color for name, color, _ in CATEGORIES}
CATEGORY_STARS = {name: stars for name, _, stars in CATEGORIES}
DEFAULT_CATEGORY = "一般"


def category_color(name: str) -> str:
    """Colour of a category, falling back to slate for unknown names."""
    return CATEGORY_COLORS.get(name, DEFAULT_COLOR)


def build_category_icon(name: str, size: float = STAR_SIZE) -> ft.Control:
    """Star rating: five red stars for 重要, three yellow, one green."""
    stars = CATEGORY_STARS.get(name)
    if stars is None:
        return ft.Icon(ft.Icons.LABEL_OUTLINE, size=size, color=DEFAULT_COLOR)
    color = category_color(name)
    return ft.Row(
        tight=True,
        spacing=STAR_SPACING,
        controls=[ft.Icon(ft.Icons.STAR, size=size, color=color) for _ in range(stars)],
    )
