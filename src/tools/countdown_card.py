"""The 倒数日 card, shared by the 倒数日 page and the 日历 day dialog.

一张卡片分上中下三段：上段是图标 + 倒数日事项，底色就是这张卡自己选的颜色；
中段是放大后的天数，「天后」贴在数字右上角；一条「--」虚线把中段和下段隔开，
下段写倒数日的日期 · 农历 · 周几。天数徽标按剩余天数分三档上色，用的就是类别三色，
天数越近越像「重要」那一档：七天及以上绿、三到六天黄、不到三天（含已过）红；不循环
的那种过了到期日第二天就整张收起。
"""

from collections.abc import Callable
from datetime import date
from typing import Any

import flet as ft

from tools import db
from tools.categories import category_color
from tools.layout import date_label, readable_ink
from tools.lunar import lunar_label

TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
# 没挑背景色时上段用的灰，以及卡片中下段的白底和描边。
CARD_BG = "#F1F5F9"
CARD_BODY_BG = "#FFFFFF"
CARD_BORDER = "#E2E8F0"
ACCENT_COLOR = "#0EA5E9"
CARD_RADIUS = 12
ICON_SIZE = 18
HEADER_PADDING = ft.Padding.symmetric(horizontal=8, vertical=6)
MID_PADDING = ft.Padding.only(left=8, right=8, top=6, bottom=2)
SUB_PADDING = ft.Padding.only(left=8, right=8, top=4, bottom=8)
TITLE_SIZE = 12
DAYS_SIZE = 26
SUFFIX_SIZE = 10
SUB_SIZE = 9
# 天数用黑字，状态色挪到「天后」那块底色上。
DAYS_COLOR = "#111827"
SUFFIX_TOP_PAD = 4
SUFFIX_PADDING = ft.Padding.symmetric(horizontal=4, vertical=1)
SUFFIX_RADIUS = 4
# 「--」分隔线：细密短横线，卡片宽度变了也跟着重排。
DASH_COUNT = 16
DASH_GAP = 2
# 天数徽标的三档状态色直接借待办类别的三色：红 = 重要、黄 = 一般、绿 = 可选，天数
# 越近越像「重要」。三张卡都取同一份色值（tools/categories.py），别再手写十六进制。
URGENT_COLOR = category_color("重要")
SOON_COLOR = category_color("一般")
FUTURE_COLOR = category_color("可选")
SOON_DAYS = 3
FUTURE_DAYS = 7
# 不循环的倒数日过期后还挂几天：到期当天算第 0 天，到期后第二天（+2）起不再展示。
EXPIRED_HIDE_AFTER_DAYS = 2
# 周一..周日, indexed by `date.weekday()`.
WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def countdown_days(item: db.Countdown, today: date | None = None) -> int:
    """Days left until the next occurrence; negative once a fixed day passed."""
    return (
        db.next_occurrence(item.due_date, item.cycle, today or date.today())
        - (today or date.today())
    ).days


def countdown_color(days: int) -> str:
    """七天及以上绿、三到六天黄、不到三天（含已过）红。"""
    if days < SOON_DAYS:
        return URGENT_COLOR
    if days < FUTURE_DAYS:
        return SOON_COLOR
    return FUTURE_COLOR


def countdown_visible(item: db.Countdown, today: date | None = None) -> bool:
    """不循环的倒数日过了到期日第二天就不再展示；循环的永远等下一次。"""
    if item.cycle in db.REPEAT_CYCLES and item.cycle != db.DEFAULT_CYCLE:
        return True
    return ((today or date.today()) - item.due_date).days < EXPIRED_HIDE_AFTER_DAYS


def visible_countdowns(
    items: list[db.Countdown], today: date | None = None
) -> list[db.Countdown]:
    """筛掉已经过期的倒数日；页面列表和日历都先用它过一遍。"""
    today = today or date.today()
    return [item for item in items if countdown_visible(item, today)]


def countdown_date_lunar(item: db.Countdown) -> str:
    """「2026年10月1日 · 八月廿一」- anchor date with its lunar day."""
    return " · ".join(
        part
        for part in (
            date_label(item.due_date),
            lunar_label(item.due_date),
        )
        if part
    )


def countdown_weekday(item: db.Countdown) -> str:
    """「-周四-」- the weekday sits above the date, boxed in dashes."""
    return f"-{WEEKDAYS[item.due_date.weekday()]}-"


def days_block(days: int, color: str) -> ft.Control:
    """中段居中：天数放大用黑字，「天后」带状态色的底贴在数字右上角。"""
    badge = ft.Container(
        padding=SUFFIX_PADDING,
        border_radius=ft.BorderRadius.all(SUFFIX_RADIUS),
        bgcolor=color,
        content=ft.Text(
            "天后" if days >= 0 else "天前",
            size=SUFFIX_SIZE,
            color=readable_ink(color),
        ),
    )
    if days == 0:
        return ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    padding=SUFFIX_PADDING,
                    border_radius=ft.BorderRadius.all(SUFFIX_RADIUS),
                    bgcolor=color,
                    content=ft.Text(
                        "就是今天",
                        size=SUFFIX_SIZE + 1,
                        color=readable_ink(color),
                    ),
                )
            ],
        )
    return ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=2,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Text(
                str(abs(days)),
                size=DAYS_SIZE,
                weight=ft.FontWeight.BOLD,
                color=DAYS_COLOR,
            ),
            ft.Container(
                padding=ft.Padding.only(top=SUFFIX_TOP_PAD),
                content=badge,
            ),
        ],
    )


def dashed_rule() -> ft.Control:
    """「--」：几段等宽短线排开，卡片宽窄变化都能铺满。"""
    return ft.Row(
        spacing=DASH_GAP,
        controls=[
            ft.Container(height=1, expand=True, bgcolor=CARD_BORDER)
            for _ in range(DASH_COUNT)
        ],
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
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        border=ft.Border.all(1, CARD_BORDER),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor=CARD_BODY_BG,
        content=ft.Column(
            tight=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                # 上：图标 + 倒数日事项，底色用这张卡自己的背景色
                ft.Container(
                    padding=HEADER_PADDING,
                    bgcolor=item.bgcolor or CARD_BG,
                    content=ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(
                                ft.Icons.EVENT,
                                size=ICON_SIZE,
                                color=ACCENT_COLOR,
                            ),
                            ft.Text(
                                item.content,
                                size=TITLE_SIZE,
                                color=TITLE_COLOR,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True,
                            ),
                        ],
                    ),
                ),
                # 中：天数 + 右上角的「天后」
                ft.Container(
                    padding=MID_PADDING,
                    content=days_block(days, countdown_color(days)),
                ),
                # 「--」
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=8),
                    content=dashed_rule(),
                ),
                # 下：周几一行、日期 · 农历一行，都居中
                ft.Container(
                    padding=SUB_PADDING,
                    content=ft.Column(
                        tight=True,
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        controls=[
                            ft.Text(
                                countdown_weekday(item),
                                size=SUB_SIZE,
                                color=MUTED_COLOR,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                countdown_date_lunar(item),
                                size=SUB_SIZE,
                                color=MUTED_COLOR,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )
    if on_delete is None and on_edit is None:
        return card
    from tools.swipe_delete import build_swipe_delete_row

    # 左滑会平移卡片，这里按卡片圆角裁一刀：网格里卡片不会盖到隔壁那张。
    return ft.Container(
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        content=build_swipe_delete_row(
            card,
            on_delete or (lambda _: None),
            on_edit,
        ),
    )


def countdowns_on(day: date, items: list[db.Countdown] | None = None) -> list[db.Countdown]:
    """The 倒数日 whose next occurrence lands on `day` - one row per day."""
    return [
        item
        for item in (items if items is not None else db.list_countdowns())
        if db.next_occurrence(item.due_date, item.cycle, day) == day
    ]
