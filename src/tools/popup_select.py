"""Option selector shared by the 我的 pickers and the add-todo dialog.

The 年/月/周 selector and the dialog's 日期/类别 pickers must look and behave the
same, so they are built here once instead of being styled twice.

Material anchors a popup menu strictly outside its button (`menu_position=UNDER`
puts the panel's top edge on the button's bottom edge), so the panel can neither
overlap nor drift away from its trigger. A `Dropdown` trigger is a Material
TextField whose `InputDecorator` paints its own field box after the popup
overlay, which left any panel anchored on top of that field half covered by it.
"""

from collections.abc import Callable

import flet as ft

from tools.layout import text_width

OPTION_HEIGHT = 28
OPTION_PADDING = ft.Padding.symmetric(horizontal=10)
OPTION_TEXT_SIZE = 12
OPTION_TEXT_COLOR = "#334155"
TRIGGER_TEXT_SIZE = 13
TRIGGER_TEXT_COLOR = "#334155"
MENU_BG = "#FFFFFF"
MENU_BORDER = "#E2E8F0"
MENU_BORDER_WIDTH = 1
MENU_RADIUS = 10
CARET_COLOR = "#94A3B8"
# Material's popup menu defaults to a 112px minimum width, which is wide enough
# to be pushed sideways (away from the button it belongs to) whenever the button
# sits near the right edge. The panel is anchored to the button's right edge, so
# a tight 44px lets the entries land right under the caret instead of leaving a
# wide empty strip after the text.
MENU_MIN_WIDTH = 44
# Slack kept between the longest entry and the panel edge, so a glyph can never
# touch - or be shaved by - the panel's rounded border.
MENU_LABEL_SLACK = 6
SELECTOR_STYLE = ft.ButtonStyle(
    # The button is only the selected value plus its caret; Material's default
    # ripple/overlay painted a bright rounded rectangle around it.
    bgcolor="#00000000",
    overlay_color="#00000000",
    padding=ft.Padding.all(0),
    visual_density=ft.VisualDensity.COMPACT,
)


def build_option_text(value: str) -> ft.Text:
    """Trigger label of a selector - the same face on every page."""
    return ft.Text(value, size=TRIGGER_TEXT_SIZE, color=TRIGGER_TEXT_COLOR)


def option_text(label: str) -> ft.Text:
    """Menu-entry label - the same face in every option panel."""
    return ft.Text(label, size=OPTION_TEXT_SIZE, color=OPTION_TEXT_COLOR)


def option_row(
    content: ft.Control,
    align: ft.MainAxisAlignment = ft.MainAxisAlignment.START,
) -> ft.Row:
    """Option row that fills the panel so `content` rests on `align`."""
    return ft.Row(
        alignment=align,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[content],
    )


def panel_width(content_width: float) -> float:
    """Panel width that just fits an entry `content_width` wide."""
    return (
        content_width
        + OPTION_PADDING.left
        + OPTION_PADDING.right
        + MENU_BORDER_WIDTH * 2
        + MENU_LABEL_SLACK
    )


def menu_min_width(options: list[tuple[str, str]]) -> float:
    """Panel floor that fits the longest entry.

    Material sizes a popup menu to its entries, but the floor from
    `size_constraints` is what decides the panel width on Android, and a 44px
    floor shaved the 类别 labels and pushed the 日期 ones (2026年10月4日) well past
    the white panel. Measuring the labels keeps both inside it.
    """
    widest = max(
        (text_width(label, OPTION_TEXT_SIZE) for _, label in options), default=0.0
    )
    return max(
        MENU_MIN_WIDTH,
        panel_width(widest),
    )


def build_option_selector(
    text: ft.Control,
    options: list[tuple[str, str]],
    on_pick: Callable[[str], None],
    max_menu_height: float | None = None,
    label_builder: Callable[[str], ft.Control] | None = None,
    content_width: float | None = None,
) -> ft.PopupMenuButton:
    """Value-plus-caret trigger that opens an inset-bordered white panel.

    `options` is `[(key, label)]`; `on_pick` gets the key of the chosen entry,
    while `text` - owned by the caller - shows the current value.
    `max_menu_height` caps a long list (the dialog's dates) so the panel scrolls
    instead of growing past the screen.
    `label_builder` renders an option's own content (e.g. the category stars plus
    its name) instead of the plain label text.
    `content_width` pins the panel to the width one entry needs, so a short list
    does not end up with a wide empty strip.
    """
    menu_constraints = {"min_width": menu_min_width(options)}
    if content_width is not None:
        menu_constraints["min_width"] = panel_width(content_width)
        menu_constraints["max_width"] = panel_width(content_width)
    if max_menu_height is not None:
        menu_constraints["max_height"] = max_menu_height
    return ft.PopupMenuButton(
        items=[
            ft.PopupMenuItem(
                content=(
                    label_builder(label)
                    if label_builder is not None
                    else option_text(label)
                ),
                height=OPTION_HEIGHT,
                padding=OPTION_PADDING,
                on_click=lambda _, key=key: on_pick(key),
            )
            for key, label in options
        ],
        content=ft.Container(
            # The caret sits just after the value: Material otherwise reserves
            # its 48px minimum tap box for the icon and pushes the two apart,
            # while 2px left the caret touching the last CJK glyph.
            padding=ft.Padding.symmetric(horizontal=4, vertical=4),
            content=ft.Row(
                tight=True,
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    text,
                    ft.Icon(
                        ft.Icons.EXPAND_MORE,
                        size=16,
                        color=CARET_COLOR,
                        # A large Android font scale grows text; the caret keeps
                        # its size so it cannot grow into the value next to it.
                        apply_text_scaling=False,
                    ),
                ],
            ),
        ),
        # The panel is anchored flush under the button by Material, so it never
        # overlaps the trigger and never floats away from it.
        menu_position=ft.PopupMenuPosition.UNDER,
        style=SELECTOR_STYLE,
        bgcolor=MENU_BG,
        elevation=0,
        shadow_color="#00000000",
        # The panel is white, exactly like the card or dialog it opens over, so a
        # 1px inset border - rather than a Material shadow - is what makes the
        # option list read as a panel on top of the content.
        shape=ft.RoundedRectangleBorder(
            radius=MENU_RADIUS, side=ft.BorderSide(width=1, color=MENU_BORDER)
        ),
        menu_padding=ft.Padding.symmetric(vertical=2),
        size_constraints=ft.BoxConstraints(**menu_constraints),
        padding=ft.Padding.all(0),
    )


def build_option_row(selector: ft.Control) -> ft.Row:
    """Left-aligned row so a trigger hugs its text instead of stretching."""
    return ft.Row(
        tight=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[selector],
    )
