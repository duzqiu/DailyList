import calendar
from bisect import bisect_right
from collections.abc import Callable
import flet as ft
from datetime import date, timedelta

from tools import db, notifications
from tools.categories import (
    CATEGORIES,
    build_category_icon,
    category_color,
)
from tools.layout import (
    BOTTOM_MENU_INSET,
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    UNSELECTED_CARD_BG,
    anchor_dialog_above_keyboard,
    dialog_button_style,
    page_gradient,
    text_width,
)
from tools.line_chart import build_interactive_line_chart
from tools.popup_select import (
    OPTION_TEXT_SIZE,
    build_option_row,
    build_option_selector,
    build_option_text,
)

# Every surface on this page is the same grey the 待办 cards use, so a card here
# and a todo card read as the same material.
CARD_BG = UNSELECTED_CARD_BG
CARD_BORDER = "#E2E8F0"
TILE_BG = UNSELECTED_CARD_BG
# A tile's header is a pale tint of the category's own colour (see
# tools/categories.py) with the same dark ink on all three, so the levels differ
# only by hue. The text is 11pt like the rest of the tile.
CATEGORY_HEADERS = {
    "重要": "#D4DCE1",
    "一般": "#D4DCE1",
    "可选": "#D4DCE1",
}
HEADER_TEXT_SIZE = 11
TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
DONE_COLOR = "#16A34A"
PENDING_COLOR = "#DC2626"
# 三张卡的标题文字用同一个深色（只有底色按等级区分）。
HEADER_TEXT_COLOR = TITLE_COLOR

DIMENSIONS = ("年", "月", "周")
# 数据统计 and 待办趋势 both open on 周; the picker still offers 年/月/周.
DEFAULT_DIMENSION = "周"
# 年 and 周 plot one point per month/day and stay few enough to name every point
# on the x axis; 月's 28-31 points keep the sparse first/middle/last labels.
NAMED_AXIS_DIMENSIONS = ("年", "周")
STATUS_KEYS = ("all", "done", "pending")
STATUS_LABELS = {"all": "全部", "done": "已完成", "pending": "未完成"}
STATUS_COLORS = {"all": TITLE_COLOR, "done": DONE_COLOR, "pending": PENDING_COLOR}
# A 数据统计 tile is a header in the category's colour over a grey data block.
# Every row carries a dot: 全部/已完成/未完成 keep the green one, 完成率 flips to
# red below half - and its percentage follows the dot.
DOT_SIZE = 5
RATE_THRESHOLD = 50
# The 年/月/周 range selector is a `PopupMenuButton`, not a `Dropdown`: a
# Dropdown trigger paints over an anchored panel - see tools/popup_select.py,
# which the add-todo dialog's 日期/类别 pickers share with these two.


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


TREND_HEIGHT = 150
# The chart canvas is given an explicit size, so it needs the width of the card
# content area: page padding (24px per side) plus the card's own 16px padding.
TREND_PAGE_INSETS = 80
TREND_FALLBACK_PAGE_WIDTH = 360
TREND_MIN_WIDTH = 240
TREND_MAX_WIDTH = 560


def trend_width(page: ft.Page) -> float:
    """Canvas width that fits inside the card on the current window."""
    page_width = getattr(page, "width", None) or TREND_FALLBACK_PAGE_WIDTH
    return float(
        max(TREND_MIN_WIDTH, min(TREND_MAX_WIDTH, page_width - TREND_PAGE_INSETS))
    )


def chart_buckets(dimension: str, today: date) -> list[tuple[str, date, date]]:
    """Trend-chart buckets as (x label, first due-date, last due-date).

    周/月 are plotted per day and 年 per month, so the X axis stays readable.
    """
    if dimension == "周":
        start = today - timedelta(days=today.weekday())
        days = [start + timedelta(days=offset) for offset in range(7)]
        return [(f"{day.month}/{day.day}", day, day) for day in days]
    if dimension == "月":
        last_day = calendar.monthrange(today.year, today.month)[1]
        days = [today.replace(day=day) for day in range(1, last_day + 1)]
        return [(f"{day.month}/{day.day}", day, day) for day in days]
    return [
        (
            f"{month}月",
            date(today.year, month, 1),
            date(today.year, month, calendar.monthrange(today.year, month)[1]),
        )
        for month in range(1, 13)
    ]


def trend_series(
    buckets: list[tuple[str, date, date]],
) -> list[tuple[str, list[int], str]]:
    """Per-category todo counts for every bucket, ready for the line chart."""
    starts = [first for _, first, _ in buckets]
    counts = {name: [0] * len(buckets) for name, _ in CATEGORIES}
    for todo in db.list_range(starts[0], buckets[-1][2]):
        if todo.category not in counts:
            continue
        index = bisect_right(starts, todo.due_date) - 1
        if index >= 0 and todo.due_date <= buckets[index][2]:
            counts[todo.category][index] += 1
    return [(name, counts[name], color) for name, color in CATEGORIES]


def summarize(rows: list[tuple[str, bool, int]]) -> dict[str, dict[str, int]]:
    """Aggregate (category, done, count) rows into per-category buckets."""
    per_category = {name: dict.fromkeys(STATUS_KEYS, 0) for name, _ in CATEGORIES}
    for category, done, count in rows:
        bucket = per_category.setdefault(category, dict.fromkeys(STATUS_KEYS, 0))
        status = "done" if done else "pending"
        bucket["all"] += count
        bucket[status] += count
    return per_category


def build_settings_page(
    page: ft.Page, set_menu_visible: Callable[[bool], None]
) -> ft.Control:
    today = date.today()
    category_names = [name for name, _ in CATEGORIES]
    # The statistics card and the trend chart keep their own 年/月/周 selection.
    state = {"dimension": DEFAULT_DIMENSION, "trend": DEFAULT_DIMENSION}

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
    # 完成率 is derived, so it keeps its own control per category.
    rates = {
        name: ft.Text(
            "—",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=TITLE_COLOR,
        )
        for name in category_names
    }
    # The 完成率 dot, the only one whose colour changes with the data.
    rate_dots = {
        name: ft.Container(
            width=DOT_SIZE,
            height=DOT_SIZE,
            border_radius=ft.BorderRadius.all(DOT_SIZE / 2),
            bgcolor=DONE_COLOR,
        )
        for name in category_names
    }

    def category_card(name: str) -> ft.Control:
        header_bg = CATEGORY_HEADERS.get(name, TILE_BG)

        def dot(color: str) -> ft.Control:
            return ft.Container(
                width=DOT_SIZE,
                height=DOT_SIZE,
                border_radius=ft.BorderRadius.all(DOT_SIZE / 2),
                bgcolor=color,
            )

        def row(
            label: str, marker: ft.Control, value: ft.Control
        ) -> ft.Control:
            return ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=2,
                controls=[
                    ft.Row(
                        tight=True,
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            marker,
                            ft.Text(label, size=9, color=MUTED_COLOR),
                        ],
                    ),
                    value,
                ],
            )

        return ft.Container(
            expand=1,
            border_radius=ft.BorderRadius.all(10),
            border=ft.Border.all(1, CARD_BORDER),
            # Keeps the header's grade inside the tile's rounded corners.
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=TILE_BG,
            content=ft.Column(
                tight=True,
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    # 头部：等级标题，底色是该分类颜色的浅色档
                    ft.Container(
                        padding=ft.Padding.symmetric(
                            horizontal=8, vertical=5
                        ),
                        bgcolor=header_bg,
                        content=ft.Row(
                            # 星标和文字在卡片里左右居中
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                build_category_icon(
                                    name,
                                    size=HEADER_TEXT_SIZE,
                                    color=category_color(name),
                                ),
                                ft.Text(
                                    name,
                                    size=HEADER_TEXT_SIZE,
                                    weight=ft.FontWeight.BOLD,
                                    color=HEADER_TEXT_COLOR,
                                ),
                            ],
                        ),
                    ),
                    # 数据：灰底，每行前面一个小圆点
                    ft.Container(
                        padding=ft.Padding.symmetric(
                            horizontal=8, vertical=6
                        ),
                        bgcolor=TILE_BG,
                        content=ft.Column(
                            tight=True,
                            spacing=3,
                            horizontal_alignment=(
                                ft.CrossAxisAlignment.STRETCH
                            ),
                            controls=[
                                *[
                                    row(
                                        STATUS_LABELS[key],
                                        dot(
                                            PENDING_COLOR
                                            if key == "pending"
                                            else DONE_COLOR
                                        ),
                                        numbers[(name, key)],
                                    )
                                    for key in STATUS_KEYS
                                ],
                                row("完成率", rate_dots[name], rates[name]),
                            ],
                        ),
                    ),
                ],
            ),
        )

    dimension_text = build_option_text(state["dimension"])

    def change_dimension(name: str) -> None:
        if name == state["dimension"]:
            return
        state["dimension"] = name
        # The trigger is our own Text, so the picked 年/月/周 renders right away
        # (a Dropdown only re-synced its trigger text on a full rebuild).
        dimension_text.value = name
        dimension_text.update()
        render()

    selector_row = build_option_row(
        build_option_selector(
            dimension_text,
            [(name, name) for name in DIMENSIONS],
            change_dimension,
        )
    )

    chart_holder = ft.Container()
    trend_text = build_option_text(state["trend"])

    def change_trend(name: str) -> None:
        """Re-render the chart; it has its own 年/月/周 switch."""
        if name == state["trend"]:
            return
        state["trend"] = name
        trend_text.value = name
        trend_text.update()
        chart_holder.content = trend_chart()
        chart_holder.update()

    trend_selector_row = build_option_row(
        build_option_selector(
            trend_text,
            [(name, name) for name in DIMENSIONS],
            change_trend,
        )
    )

    def trend_chart() -> ft.Control:
        buckets = chart_buckets(state["trend"], today)
        return ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                build_interactive_line_chart(
                    [label for label, _, _ in buckets],
                    trend_series(buckets),
                    trend_width(page),
                    TREND_HEIGHT,
                    x_label_step=(
                        1 if state["trend"] in NAMED_AXIS_DIMENSIONS else None
                    ),
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                    controls=[
                        ft.Row(
                            tight=True,
                            spacing=4,
                            controls=[
                                ft.Container(
                                    width=8,
                                    height=8,
                                    border_radius=ft.BorderRadius.all(4),
                                    bgcolor=color,
                                ),
                                ft.Text(name, size=11, color=MUTED_COLOR),
                            ],
                        )
                        for name, color in CATEGORIES
                    ],
                ),
            ],
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
            total = bucket["all"]
            if total:
                rate = round(bucket["done"] / total * 100)
                rate_color = (
                    DONE_COLOR if rate >= RATE_THRESHOLD else PENDING_COLOR
                )
                rates[name].value = f"{rate}%"
            else:
                # Nothing to rate yet: a quiet grey instead of a red/green claim.
                rate_color = MUTED_COLOR
                rates[name].value = "—"
            rates[name].color = rate_color
            rate_dots[name].bgcolor = rate_color
        chart_holder.content = trend_chart()
        if update:
            for control in [
                *numbers.values(),
                *rates.values(),
                *rate_dots.values(),
                chart_holder,
            ]:
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
        """Compact metrics of the card's own 清除 action button."""
        return ft.ButtonStyle(
            padding=ft.Padding.symmetric(horizontal=10, vertical=2),
            text_style=ft.TextStyle(size=12),
            visual_density=ft.VisualDensity.COMPACT,
        )

    def settings_dialog(
        title: str, content: ft.Control, actions: list[ft.Control]
    ) -> ft.AlertDialog:
        """Dialog chrome shared by the 清除缓存 and 通知渠道 dialogs.

        Both must look like the add-todo dialog: 12px radius, the same paddings
        and the same plain text buttons.
        """
        return ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
            # Same surface as the add-todo dialog, so the option panels opening
            # inside a settings dialog can be painted the same colour too.
            bgcolor=DIALOG_SURFACE,
            elevation=0,
            inset_padding=ft.Padding.symmetric(horizontal=48, vertical=24),
            title_padding=ft.Padding.only(left=16, top=12, right=16, bottom=0),
            content_padding=ft.Padding.only(left=16, top=8, right=16, bottom=8),
            actions_padding=ft.Padding.only(left=8, right=8, bottom=8),
            action_button_padding=ft.Padding.symmetric(horizontal=8),
            title=ft.Text(
                title,
                size=16,
                weight=ft.FontWeight.BOLD,
                color=TITLE_COLOR,
            ),
            content=content,
            actions=actions,
        )

    def clear_data(_: ft.Event[ft.Control]) -> None:
        page.pop_dialog()
        removed = db.clear_todos()
        render()
        notify(f"已清除 {removed} 条待办数据")

    def confirm_clear(_: ft.Event[ft.Control]) -> None:
        page.show_dialog(
            settings_dialog(
                "清除缓存",
                ft.Text(
                    "将删除数据库中当前所有的待办数据，且无法恢复。",
                    size=12,
                ),
                [
                    ft.TextButton(
                        "取消",
                        style=dialog_button_style(),
                        on_click=lambda _: page.pop_dialog(),
                    ),
                    ft.TextButton(
                        "确认清除",
                        style=dialog_button_style(),
                        on_click=clear_data,
                    ),
                ],
            )
        )

    notify_summary = ft.Text("", size=11, color=MUTED_COLOR)

    def refresh_notify_summary() -> None:
        notify_summary.value = notifications.summary(
            db.get_setting(
                notifications.CHANNEL_SETTING, notifications.DEFAULT_CHANNEL
            ),
            db.get_setting(notifications.URL_SETTING, ""),
        )

    def open_notify_settings(_: ft.Event[ft.Container]) -> None:
        """通知渠道 dialog: the channel picker plus its delivery address."""
        channel_text = build_option_text(
            db.get_setting(
                notifications.CHANNEL_SETTING, notifications.DEFAULT_CHANNEL
            )
        )
        selection = {"channel": channel_text.value}

        def pick_channel(name: str) -> None:
            selection["channel"] = name
            channel_text.value = name
            channel_text.update()

        channel_selector = build_option_selector(
            channel_text,
            [(name, name) for name in notifications.CHANNELS],
            pick_channel,
            content_width=max(
                text_width(name, OPTION_TEXT_SIZE)
                for name in notifications.CHANNELS
            ),
        )
        def url_focus_changed(focused: bool) -> None:
            set_menu_visible(not focused)
            anchor_dialog_above_keyboard(dialog, focused)

        url_field = ft.TextField(
            value=db.get_setting(notifications.URL_SETTING, ""),
            hint_text="粘贴通知地址",
            hint_style=ft.TextStyle(size=13, color="#94A3B8"),
            # Same as the 待办内容 field: the keyboard would cover the floating
            # menu bar, so the bar steps out of the way and the dialog parks just
            # above the keyboard while typing.
            on_focus=lambda _: url_focus_changed(True),
            on_blur=lambda _: url_focus_changed(False),
            filled=False,
            border=ft.NoInputBorder(),
            content_padding=ft.Padding.symmetric(horizontal=0, vertical=6),
            text_style=ft.TextStyle(size=13, color="#334155"),
            dense=True,
            height=40,
        )

        def save_notify(_: ft.Event[ft.Control]) -> None:
            db.set_setting(notifications.CHANNEL_SETTING, selection["channel"])
            db.set_setting(
                notifications.URL_SETTING, (url_field.value or "").strip()
            )
            dialog.open = False
            set_menu_visible(True)
            refresh_notify_summary()
            notify_summary.update()
            page.update()
            notify("通知渠道已保存")

        dialog = settings_dialog(
            "通知渠道",
            ft.Column(
                tight=True,
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    build_option_row(channel_selector),
                    url_field,
                ],
            ),
            [
                ft.TextButton(
                    "取消",
                    style=dialog_button_style(),
                    on_click=lambda _: close_notify_settings(),
                ),
                ft.TextButton(
                    "保存",
                    style=dialog_button_style(),
                    on_click=save_notify,
                ),
            ],
        )
        page.show_dialog(dialog)

    def close_notify_settings() -> None:
        """Dismiss the 通知渠道 dialog and bring the menu bar back."""
        page.pop_dialog()
        set_menu_visible(True)

    def settings_card() -> ft.Control:
        return build_card(
            "设置",
            [
                ft.Container(
                    border_radius=ft.BorderRadius.all(8),
                    on_click=open_notify_settings,
                    content=ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                tight=True,
                                spacing=2,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        "通知渠道",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=TITLE_COLOR,
                                    ),
                                    notify_summary,
                                ],
                            ),
                            ft.Icon(
                                ft.Icons.CHEVRON_RIGHT,
                                size=20,
                                color="#94A3B8",
                            ),
                        ],
                    ),
                ),
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
    refresh_notify_summary()

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
                            # Same face as the home page's「待办」heading.
                            size=18,
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
                                build_card(
                                    "待办趋势",
                                    [chart_holder],
                                    trailing=trend_selector_row,
                                ),
                                settings_card(),
                            ],
                        ),
                    ],
                ),
            ),
        ),
    )
