"""The 倒数日 card, shared by the 倒数日 page and the 日历 day list.

One card shows what it counts down to, the anchor date with its lunar day and
weekday, and how far off the next occurrence is - red once a fixed day slipped
by, yellow within three days, green for anything further out.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

import flet as ft

from tools import db
from tools.layout import date_label
from tools.lunar import lunar_label

TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
CARD_BG = "#F1F5F9"
ACCENT_COLOR = "#0EA5E9"
ICON_SIZE = 20
CARD_RADIUS = 10
CARD_PADDING = ft.Padding.symmetric(horizontal=12, vertical=8)
MUTED_SIZE = 11
TITLE_SIZE = 15
DAYS_SIZE = 13
# Countdown colours, each a darker tone of its hue so it cannot blend into any of
# the pale card backgrounds the palette offers.
PAST_COLOR = "#B91C1C"
SOON_COLOR = "#A16207"
FUTURE_COLOR = "#15803D"
SOON_DAYS = 3
# 周一..周日, indexed by `date.weekday()`.
WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def countdown_days(item: db.Countdown, today: date | None = None) -> int:
    """Days left until the next occurrence; negative once a fixed day passed."""
    return (
        db.next_occurrence(item.due_date, item.cycle, today or date.today())
        - (today or date.today())
    ).days


def countdown_label(days: int) -> str:
    if days == 0:
        return "就是今天"
    if days > 0:
        return f"还有 {days} 天"
    return f"已过 {-days} 天"


def countdown_color(days: int) -> str:
    """Red once a fixed day passed, yellow within three days, green otherwise."""
    if days < 0:
        return PAST_COLOR
    if days <= SOON_DAYS:
        return SOON_COLOR
    return FUTURE_COLOR


def countdown_subtitle(item: db.Countdown) -> str:
    """「2026年10月1日 · 八月廿一 · 周四」- anchor date, lunar day, weekday."""
    return " · ".join(
        part
        for part in (
            date_label(item.due_date),
            lunar_label(item.due_date),
            WEEKDAYS[item.due_date.weekday()],
        )
        if part
    )


def build_countdown_card(
    item: db.Countdown,
    *,
    today: date | None = None,
    on_delete: Callable[[ft.Event[ft.Container]], Any] | None = None,
    on_edit: Callable[[ft.Event[ft.Container]], Any] | None = None,
) -> ft.Control:
    """One 倒数日 card; wrapped in the swipe row when callbacks are given."""
    days = countdown_days(item, today)
    card = ft.Container(
        key=f"countdown-{item.id}",
        padding=CARD_PADDING,
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        bgcolor=item.bgcolor or CARD_BG,
        content=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.EVENT, size=ICON_SIZE, color=ACCENT_COLOR),
                ft.Column(
                    tight=True,
                    expand=True,
                    spacing=1,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Text(item.content, size=TITLE_SIZE, color=TITLE_COLOR),
                        ft.Text(
                            countdown_subtitle(item),
                            size=MUTED_SIZE,
                            color=MUTED_COLOR,
                        ),
                    ],
                ),
                ft.Text(
                    countdown_label(days),
                    size=DAYS_SIZE,
                    weight=ft.FontWeight.BOLD,
                    color=countdown_color(days),
                ),
            ],
        ),
    )
    if on_delete is None and on_edit is None:
        return card
    from tools.swipe_delete import build_swipe_delete_row

    return build_swipe_delete_row(
        card,
        on_delete or (lambda _: None),
        on_edit,
    )


def countdowns_on(day: date, items: list[db.Countdown] | None = None) -> list[db.Countdown]:
    """The 倒数日 whose next occurrence lands on `day` - one row per day."""
    return [
        item
        for item in (items if items is not None else db.list_countdowns())
        if db.next_occurrence(item.due_date, item.cycle, day) == day
    ]
