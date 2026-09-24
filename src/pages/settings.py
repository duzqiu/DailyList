import calendar
import flet as ft
from datetime import date, timedelta

from tools import db
from tools.categories import CATEGORIES, build_category_icon
from tools.layout import BOTTOM_MENU_INSET, page_gradient

CARD_BG = "#FFFFFF"
CARD_BORDER = "#E2E8F0"
TILE_BG = "#F8FAFC"
TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
DONE_COLOR = "#16A34A"
PENDING_COLOR = "#DC2626"

DIMENSIONS = ("年", "月", "周")
STATUS_KEYS = ("all", "done", "pending")
STATUS_LABELS = {"all": "全部", "done": "已完成", "pending": "未完成"}
STATUS_COLORS = {"all": TITLE_COLOR, "done": DONE_COLOR, "pending": PENDING_COLOR}
# The 年/月/周 range selector is a `PopupMenuButton`, not a `Dropdown`: a
# Dropdown trigger is a Material TextField whose `InputDecorator` paints its own
# field box after the popup overlay, so any panel anchored on top of that field
# ended up half covered by it. Material places a popup menu strictly outside its
# anchor (`menu_position=UNDER` puts the panel's top edge on the button's bottom
# edge), so the list can neither overlap nor drift away from the button.
SELECT_OPTION_HEIGHT = 28
SELECT_BUTTON_STYLE = ft.ButtonStyle(
    # The button is only the selected 年/月/周 text plus its caret; Material's
    # default ripple/overlay painted a bright rounded rectangle around it.
    bgcolor="#00000000",
    overlay_color="#00000000",
    padding=ft.Padding.all(0),
    visual_density=ft.VisualDensity.COMPACT,
)


def build_card(
    title: str,
    controls: list[ft.Control],
    trailing: ft.Control | None = None,
) -> ft.Control:
    """White card with a title (plus optional trailing control) and content."""
    title_row: list[ft.Control] = [
        ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=TITLE_COLOR)
    ]
    if trailing is not None:
        title_row.append(trailing)
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        border_radius=ft.BorderRadius.all(12),
        bgcolor=CARD_BG,
        border=ft.Border.all(1, CARD_BORDER),
        content=ft.Column(
            tight=True,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=title_row,
                ),
                *controls,
            ],
        ),
    )


def period_span(dimension: str, today: date) -> tuple[date, date] | None:
    """Due-date range of a statistics dimension; `None` means all dates."""
    if dimension == "周":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if dimension == "月":
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.replace(day=1), today.replace(day=last_day)
    if dimension == "年":
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    return None


def summarize(rows: list[tuple[str, bool, int]]) -> dict[str, dict[str, int]]:
    """Aggregate (category, done, count) rows into per-category buckets."""
    per_category = {name: dict.fromkeys(STATUS_KEYS, 0) for name, _, _ in CATEGORIES}
    for category, done, count in rows:
        bucket = per_category.setdefault(category, dict.fromkeys(STATUS_KEYS, 0))
        status = "done" if done else "pending"
        bucket["all"] += count
        bucket[status] += count
    return per_category


def build_settings_page(page: ft.Page) -> ft.Control:
    today = date.today()
    category_names = [name for name, _, _ in CATEGORIES]
    state = {"dimension": DIMENSIONS[0]}

    numbers = {
        (name, key): ft.Text(
            "0",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=STATUS_COLORS[key],
        )
        for name in category_names
        for key in STATUS_KEYS
    }

    def category_card(name: str) -> ft.Control:
        return ft.Container(
            expand=1,
            padding=ft.Padding.symmetric(horizontal=6, vertical=6),
            border_radius=ft.BorderRadius.all(10),
            bgcolor=TILE_BG,
            border=ft.Border.all(1, CARD_BORDER),
            content=ft.Column(
                tight=True,
                spacing=3,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Row(
                        tight=True,
                        spacing=3,
                        controls=[
                            build_category_icon(name, size=8),
                            ft.Text(
                                name,
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=TITLE_COLOR,
                            ),
                        ],
                    ),
                    *[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            spacing=2,
                            controls=[
                                ft.Text(
                                    STATUS_LABELS[key],
                                    size=9,
                                    color=MUTED_COLOR,
                                ),
                                numbers[(name, key)],
                            ],
                        )
                        for key in STATUS_KEYS
                    ],
                ],
            ),
        )

    dimension_text = ft.Text(state["dimension"], size=13, color="#334155")

    def change_dimension(name: str) -> None:
        if name == state["dimension"]:
            return
        state["dimension"] = name
        # The trigger is our own Text, so the picked 年/月/周 renders right away
        # (a Dropdown only re-synced its trigger text on a full rebuild).
        dimension_text.value = name
        dimension_text.update()
        render()

    def dimension_menu() -> ft.PopupMenuButton:
        return ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(
                    content=ft.Text(name, size=12, color="#334155"),
                    height=SELECT_OPTION_HEIGHT,
                    padding=ft.Padding.symmetric(horizontal=10),
                    on_click=lambda _, name=name: change_dimension(name),
                )
                for name in DIMENSIONS
            ],
            content=ft.Container(
                # The caret hugs the value: Material otherwise reserves its 48px
                # minimum tap box for the icon and pushes the two apart.
                padding=ft.Padding.symmetric(horizontal=4, vertical=4),
                content=ft.Row(
                    tight=True,
                    spacing=2,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        dimension_text,
                        ft.Icon(ft.Icons.EXPAND_MORE, size=16, color="#94A3B8"),
                    ],
                ),
            ),
            # The panel is anchored flush under the button by Material, so it
            # never overlaps the trigger and never floats away from it.
            menu_position=ft.PopupMenuPosition.UNDER,
            style=SELECT_BUTTON_STYLE,
            bgcolor="#FFFFFF",
            elevation=0,
            shadow_color="#00000000",
            shape=ft.RoundedRectangleBorder(radius=12),
            menu_padding=ft.Padding.symmetric(vertical=2),
            # Material's popup menu defaults to a 112px minimum width, which is
            # wide enough to be pushed sideways (away from the 年/月/周 button it
            # belongs to) whenever the button sits near the right edge. 64px is
            # plenty for a 12px two-glyph entry and lets the panel drop straight
            # down from the button.
            size_constraints=ft.BoxConstraints(min_width=64),
            padding=ft.Padding.all(0),
        )

    selector_row = ft.Row(
        tight=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[dimension_menu()],
    )

    def render(update: bool = True) -> None:
        dimension = state["dimension"]
        span = period_span(dimension, today)
        rows = db.counts_in(*span) if span else db.counts_in()
        per_category = summarize(rows)
        for name in category_names:
            bucket = per_category.get(name, dict.fromkeys(STATUS_KEYS, 0))
            for key in STATUS_KEYS:
                numbers[(name, key)].value = str(bucket[key])
        if update:
            for control in numbers.values():
                control.update()

    def notify(message: str) -> None:
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, size=13, color="#FFFFFF"),
                bgcolor=TITLE_COLOR,
                duration=2000,
            )
        )

    def compact_button_style() -> ft.ButtonStyle:
        """Compact metrics shared by the 清除 action and its dialog buttons."""
        return ft.ButtonStyle(
            padding=ft.Padding.symmetric(horizontal=10, vertical=2),
            text_style=ft.TextStyle(size=12),
            visual_density=ft.VisualDensity.COMPACT,
        )

    def clear_data(_: ft.Event[ft.Control]) -> None:
        page.pop_dialog()
        removed = db.clear_todos()
        render()
        notify(f"已清除 {removed} 条待办数据")

    def confirm_clear(_: ft.Event[ft.Control]) -> None:
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                # Material 3 dialogs default to a 28px corner radius; 12 matches
                # the cards and the popup menu used across the app.
                shape=ft.RoundedRectangleBorder(radius=12),
                inset_padding=ft.Padding.symmetric(horizontal=56, vertical=24),
                title_padding=ft.Padding.only(left=16, top=12, right=16),
                content_padding=ft.Padding.only(left=16, right=16),
                actions_padding=ft.Padding.only(left=12, right=12, bottom=8),
                title=ft.Text("清除缓存", size=15, weight=ft.FontWeight.BOLD),
                content=ft.Text(
                    "将删除数据库中当前所有的待办数据，且无法恢复。",
                    size=12,
                ),
                actions=[
                    ft.OutlinedButton(
                        "取消",
                        on_click=lambda _: page.pop_dialog(),
                        style=compact_button_style(),
                    ),
                    ft.Button(
                        "确认清除",
                        on_click=clear_data,
                        style=compact_button_style(),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def settings_card() -> ft.Control:
        return build_card(
            "设置",
            [
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            tight=True,
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(
                                    "清除缓存",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                                ft.Text(
                                    "删除当前所有的待办数据",
                                    size=11,
                                    color=MUTED_COLOR,
                                ),
                            ],
                        ),
                        ft.OutlinedButton(
                            "清除",
                            on_click=confirm_clear,
                            style=compact_button_style(),
                        ),
                    ],
                ),
            ],
        )

    render(update=False)

    return ft.Container(
        expand=True,
        gradient=page_gradient(),
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=24, top=24, right=24),
                content=ft.Column(
                    expand=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text(
                            "我的",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_COLOR,
                        ),
                        ft.ListView(
                            expand=True,
                            spacing=12,
                            scroll=ft.ScrollMode.HIDDEN,
                            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
                            controls=[
                                build_card(
                                    "数据统计",
                                    [
                                        ft.Row(
                                            spacing=8,
                                            controls=[
                                                category_card(name)
                                                for name in category_names
                                            ],
                                        ),
                                    ],
                                    trailing=selector_row,
                                ),
                                settings_card(),
                            ],
                        ),
                    ],
                ),
            ),
        ),
    )
