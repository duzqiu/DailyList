"""Option selector shared by the 数据 pickers and the add-todo dialog.

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
# Every entry paints its own background, so a panel that borrows the dialog's
# surface still reads as a list of options instead of a flat block of text.
OPTION_BG = "#FFFFFF"
OPTION_RADIUS = 6
OPTION_VERTICAL_MARGIN = 1
# Side gap between an entry's own background and the panel edge.
OPTION_HORIZONTAL_MARGIN = 2
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
# 长列表（周期 10 项、卡片颜色 14 项）的面板钉在这个高度上：面板不再跟着项数长，
# 多出来的项在里面上下滚。按「一行占 OPTION_HEIGHT + 上下各一点外边距」算摆几行，
# 再加面板自己上下各 2 的内边距。
MENU_VISIBLE_ROWS = 6
MENU_HEIGHT = (
    MENU_VISIBLE_ROWS * (OPTION_HEIGHT + 2 * OPTION_VERTICAL_MARGIN) + 4
)
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
    menu_height: float | None = None,
    label_builder: Callable[[str], ft.Control] | None = None,
    content_width: float | None = None,
    bgcolor: str = MENU_BG,
    option_bgcolor: str = OPTION_BG,
) -> ft.PopupMenuButton:
    """Value-plus-caret trigger that opens an inset-bordered white panel.

    `options` is `[(key, label)]`; `on_pick` gets the key of the chosen entry,
    while `text` - owned by the caller - shows the current value.
    `menu_height` 把面板钉成一个固定高度（长列表用，见 `MENU_HEIGHT`）：面板不再
    跟着项数长，超出这一截的项在面板里上下滚。
    `label_builder` renders an option's own content (e.g. the category stars plus
    its name) instead of the plain label text.
    `content_width` pins the panel to the width one entry needs, so a short list
    does not end up with a wide empty strip.
    `bgcolor` repaints the panel itself - a selector inside a dialog passes the
    dialog's own surface so the panel matches what it opens over.
    `option_bgcolor` paints the individual entries sitting on that panel.
    """
    menu_constraints = {"min_width": menu_min_width(options)}
    if content_width is not None:
        menu_constraints["min_width"] = panel_width(content_width)
        menu_constraints["max_width"] = panel_width(content_width)
    if menu_height is not None:
        # 钉死成固定高度（Material 的菜单会在这个高度里自己滚起来），短列表也不会
        # 缩回去 —— 周期、颜色那两排开出来的面板一样大。
        menu_constraints["min_height"] = menu_height
        menu_constraints["max_height"] = menu_height
    # Material lays an entry's content out at its natural width, so an entry's
    # own background is pinned to the panel width instead (minus its own side
    # gaps) and every row is painted edge to edge.
    row_width = (
        panel_width(content_width)
        if content_width is not None
        else menu_min_width(options)
    ) - 2 * OPTION_HORIZONTAL_MARGIN
    # 展开时箭头朝上、收起时朝下：光看箭头就知道这一格现在是开着的还是合上的。
    caret = ft.Icon(
        ft.Icons.EXPAND_MORE,
        size=16,
        color=CARET_COLOR,
        # A large Android font scale grows text; the caret keeps its size so it
        # cannot grow into the value next to it.
        apply_text_scaling=False,
    )

    def set_expanded(expanded: bool) -> None:
        caret.icon = (
            ft.Icons.EXPAND_LESS if expanded else ft.Icons.EXPAND_MORE
        )
        try:
            caret.update()
        except RuntimeError:
            # 面板是在弹窗里开的：这一层可能已经跟着弹窗一起没了。
            pass

    def pick(key: str) -> None:
        set_expanded(False)
        on_pick(key)

    return ft.PopupMenuButton(
        items=[
            ft.PopupMenuItem(
                content=ft.Container(
                    width=row_width,
                    bgcolor=option_bgcolor,
                    border_radius=ft.BorderRadius.all(OPTION_RADIUS),
                    margin=ft.Margin.symmetric(
                        horizontal=OPTION_HORIZONTAL_MARGIN,
                        vertical=OPTION_VERTICAL_MARGIN,
                    ),
                    # The entry's own padding lives inside its background, so
                    # the colour reaches the panel edge on both sides.
                    padding=OPTION_PADDING,
                    alignment=ft.Alignment.CENTER_LEFT,
                    content=(
                        label_builder(label)
                        if label_builder is not None
                        else option_text(label)
                    ),
                ),
                height=OPTION_HEIGHT,
                padding=ft.Padding.all(0),
                on_click=lambda _, key=key: pick(key),
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
                controls=[text, caret],
            ),
        ),
        # The panel is anchored flush under the button by Material, so it never
        # overlaps the trigger and never floats away from it.
        menu_position=ft.PopupMenuPosition.UNDER,
        # 面板一开一合都把箭头掰到对应的方向（见 set_expanded）：开着朝上、
        # 点外面关掉（on_cancel）或选了一项（pick）都掰回朝下。
        on_open=lambda *_: set_expanded(True),
        on_cancel=lambda *_: set_expanded(False),
        on_select=lambda *_: set_expanded(False),
        style=SELECTOR_STYLE,
        bgcolor=bgcolor,
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
        # Material 的弹出菜单默认 `ClipBehavior.NONE`：面板不裁自己的内容，钉了固定
        # 高度之后，上下滑动时滚出视野的那几项会从圆角边框外面露出去。按面板的圆
        # 角裁（`ANTI_ALIAS`）就贴着边框收住，和 MENU_RADIUS 一个形状。
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
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
