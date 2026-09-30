"""The 倒数日 card, shared by the 倒数日 page and the 日历 day dialog.

一张卡片分上中下三段：上段是图标 + 倒数日事项，底色就是这张卡自己选的颜色；
中段是放大后的天数，「天后」贴在数字右上角；中段高度钉死成「有数字那一行」的高度，
到期当天改成一块「就是今天」，所以卡片张张等高。一排定大的细小圆点把中段和下段隔开，
下段写倒数日的日期 · 农历 · 周几。天数徽标按剩余天数分三档上色，用的就是类别三色，
天数越近越像「重要」那一档：七天及以上绿、三到六天黄、不到三天（含已过）红；不循环
的那种一过到期日就整张收起。

收起来的那些没有消失：倒数日页把它们收进列表底部的开关里，展开时用 `expired=True` 再
渲染同一张卡；日历页也照常在当天格子里把它们列出来 —— 而且只要所看的那天在今天
之前，这一次的倒数日就照 `expired=True` 显示（循环的那条也算：`countdown_expired`
只判不循环的那条，循环的按设计永远等下一次）。`expired=True` 的卡片整张置灰 ——
上段丢掉自选色、中下段丢掉白底，图标和「天前」那块小底也不留状态色，只有天数本身
照旧，下段的日期那行换成「已过期 N 天」。
"""

from collections.abc import Callable
from datetime import date
from typing import Any

import flet as ft

from tools import db
from tools.categories import category_color
from tools.layout import CALENDAR_ICON_SRC, date_label, readable_ink
from tools.lunar import lunar_label

TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
# 没挑背景色时上段用的灰，以及卡片中下段的白底和描边。
CARD_BG = "#F1F5F9"
CARD_BODY_BG = "#FFFFFF"
# 过期卡片整张置灰：上段不再用这张卡自选的颜色，中下段也不再是白底，两段各降一档
# 灰（上段比中下段深，三段的分界还看得出来）；图标、「天前」那块小底、以及日历页
# 当天格里那条小标签，统统用下面这档灰，不留一点状态色。
#
# 上段这档灰还必须比日历弹窗的底色（`layout.DIALOG_SURFACE` = #E4E9EF）深出一截：
# 早先用的 #E2E8F0 和它只差一两个色阶，过期卡片一放进弹窗，上段就跟弹窗底色融成
# 一片，看着像是根本没画背景（倒数日页是白底渐变，所以那里看得出来、这儿看不出）。
EXPIRED_HEADER_BG = "#D5DBE4"
EXPIRED_BODY_BG = "#F1F5F9"
EXPIRED_ICON_COLOR = "#94A3B8"
EXPIRED_CHIP_BG = "#CBD5E1"
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
# 中下两段之间那排分隔：一排**定大、定距**的细小圆点。早先是拉长的短横线（卡片一
# 宽线就跟着被拉长），后来改成按宽度摊开间距 —— 通栏卡片上的点被摊得稀稀拉拉。现
# 在点的大小和**点距都写死**：卡片宽就多摆几个、窄就少摆几个，所以通栏和双列看着
# 是同一条点线，密度也一样。点距现在只有 2（点 2 + 空 2，中心距 4），密到快连成线
# —— 再密就把 `DOT_GAP` 减到 1，或者把 `DOT_SIZE` 也收小一号。
DOT_SIZE = 2
DOT_GAP = 2
DOT_COLOR = CARD_BORDER
# 还没量到宽度时先按双列那档估一排点（双列卡片约 149 宽，减掉左右各 8 的内边距）。
DOT_ROW_ESTIMATE = 133
# 再窄也留这么几个，免得算出 0 或 1 个看着不像一条线。
DOT_MIN_COUNT = 4
# 天数徽标的三档状态色直接借待办类别的三色：红 = 重要、黄 = 一般、绿 = 可选，天数
# 越近越像「重要」。三张卡都取同一份色值（tools/categories.py），别再手写十六进制。
URGENT_COLOR = category_color("重要")
SOON_COLOR = category_color("一般")
FUTURE_COLOR = category_color("可选")
SOON_DAYS = 3
FUTURE_DAYS = 7
# 不循环的倒数日过期后还挂几天：到期当天算第 0 天、还留在正列表里，第二天起收进底部开关。
EXPIRED_HIDE_AFTER_DAYS = 1
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
    """不循环的倒数日一过到期日就收进「已过期」；循环的永远等下一次。"""
    if item.cycle in db.REPEAT_CYCLES and item.cycle != db.DEFAULT_CYCLE:
        return True
    return ((today or date.today()) - item.due_date).days < EXPIRED_HIDE_AFTER_DAYS


def visible_countdowns(
    items: list[db.Countdown], today: date | None = None
) -> list[db.Countdown]:
    """筛掉已经过期的倒数日；页面列表和日历都先用它过一遍。"""
    today = today or date.today()
    return [item for item in items if countdown_visible(item, today)]


def countdown_expired(item: db.Countdown, today: date | None = None) -> bool:
    """这张卡是不是已经过期了（不循环的那种过了到期日就算）。"""
    return not countdown_visible(item, today)


def expired_countdowns(
    items: list[db.Countdown], today: date | None = None
) -> list[db.Countdown]:
    """`visible_countdowns` 筛掉的那一半：倒数日页底部「已过期的倒数日」用它们。"""
    today = today or date.today()
    return [item for item in items if countdown_expired(item, today)]


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


def countdown_expired_label(item: db.Countdown, today: date | None = None) -> str:
    """「已过期 3 天」- 过期卡片下段的日期那一行。"""
    return f"已过期 {-countdown_days(item, today)} 天"


def countdown_weekday(item: db.Countdown) -> str:
    """「-周四-」- the weekday sits above the date, boxed in dashes."""
    return f"-{WEEKDAYS[item.due_date.weekday()]}-"


def _suffix_badge(days: int, color: str) -> ft.Control:
    """「天后 / 天前」：状态色的小底块，贴在数字右上角。"""
    return ft.Container(
        padding=SUFFIX_PADDING,
        border_radius=ft.BorderRadius.all(SUFFIX_RADIUS),
        bgcolor=color,
        content=ft.Text(
            "天后" if days >= 0 else "天前",
            size=SUFFIX_SIZE,
            color=readable_ink(color),
        ),
    )


def _today_badge(color: str) -> ft.Control:
    """到期当天不写 0，改成这块「就是今天」。"""
    return ft.Container(
        padding=SUFFIX_PADDING,
        border_radius=ft.BorderRadius.all(SUFFIX_RADIUS),
        bgcolor=color,
        content=ft.Text(
            "就是今天",
            size=SUFFIX_SIZE + 1,
            color=readable_ink(color),
        ),
    )


def _days_line_spacer() -> ft.Control:
    """一个空格：只占「有数字那一行」的高度，本身什么都不画。

    和数字同字号、同字重，行高也就一样，所以「就是今天」那张卡的中段和别的卡一样高。
    """
    return ft.Text(" ", size=DAYS_SIZE, weight=ft.FontWeight.BOLD, color=DAYS_COLOR)


def days_block(days: int, color: str) -> ft.Control:
    """中段居中：天数放大用黑字，「天后」带状态色的底贴在数字右上角。

    `days == 0` 不写 0，只放一块「就是今天」，底下垫一行空格（`_days_line_spacer`）——
    中段因此和有数字时一样高，每张倒数日卡片也就一样高。
    """
    if days == 0:
        return ft.Stack(
            alignment=ft.Alignment.CENTER,
            controls=[_days_line_spacer(), _today_badge(color)],
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
                content=_suffix_badge(days, color),
            ),
        ],
    )


def dot_count(width: float) -> int:
    """这么宽能摆几个点：点距是定死的，所以就是宽度除以「一个点 + 一个点距」。"""
    return max(
        DOT_MIN_COUNT, int((width + DOT_GAP) // (DOT_SIZE + DOT_GAP))
    )


def _dots(count: int) -> list[ft.Control]:
    return [
        ft.Container(
            width=DOT_SIZE,
            height=DOT_SIZE,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=DOT_COLOR,
        )
        for _ in range(count)
    ]


def dotted_rule() -> ft.Control:
    """一排小圆点：点定大、点距定死，卡片多宽就摆几个（见 `dot_count`）。"""
    row = ft.Row(
        spacing=DOT_GAP,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=_dots(dot_count(DOT_ROW_ESTIMATE)),
    )

    def fit(e: ft.LayoutSizeChangeEvent) -> None:
        """量到这一排多宽，按定死的点距算该摆几个点，不一样就重摆一次。"""
        count = dot_count(e.width)
        if count == len(row.controls):
            return
        row.controls = _dots(count)
        try:
            row.update()
        except RuntimeError:
            # 卡片已经被摘下树（翻页 / 关弹窗）：没什么可更。
            pass

    # `alignment` 让这层撑满可用宽 —— 量到的才是「能摆几个点」的那个宽度（不然量
    # 到的只是这排点自己的宽，点数就永远算不出来了）。
    return ft.Container(
        alignment=ft.Alignment.CENTER,
        on_size_change=fit,
        content=row,
    )


def build_countdown_card(
    item: db.Countdown,
    *,
    today: date | None = None,
    expired: bool = False,
    days: int | None = None,
    on_delete: Callable[[ft.Event[ft.Container]], Any] | None = None,
    on_edit: Callable[[ft.Event[ft.Container]], Any] | None = None,
) -> ft.Control:
    """One 倒数日 card; wrapped in the swipe row when callbacks are given.

    `expired=True`（倒数日页底部展开的那些、日历页当天格里的过期项）只动外观：
    整张卡片连同图标、「天前」那块小底一并置灰，下段的日期换成「已过期 N 天」，
    卡片本身还是同一张。

    `days` 是「这张卡片讲的那一天」相对今天的天数：正数还有几天、负数已经过了几天、
    0 就是今天。给了就用它，不给则卡片按这条倒数日自己推。**中段和下段共用这一个
    数**，所以过期卡片中段写的天数和下段「已过期 N 天」永远是同一个数、同一个状态。
    日历里必须给：那儿一张卡讲的是「所看的那天」，而循环倒数日的 `next_occurrence`
    只会往前找下一次，推不出这一天已经过去了（会推到还在未来的下一次去）。
    """
    # 中段和下段共用这一个数，两处永远同步。
    shown_days = days if days is not None else countdown_days(item, today)
    # 下段那行「已过期 N 天」：天数直接取中段那个数（负的就是已经过了几天）。
    expired_text = (
        f"已过期 {-shown_days} 天"
        if shown_days < 0
        else countdown_expired_label(item, today)
    )
    # 过期卡片整张置灰：上段丢掉自选色，中下段丢掉白底，图标和「天前」那块小底
    # 也跟着灰下去。
    header_bg = EXPIRED_HEADER_BG if expired else (item.bgcolor or CARD_BG)
    body_bg = EXPIRED_BODY_BG if expired else CARD_BODY_BG
    badge_bg = EXPIRED_CHIP_BG if expired else countdown_color(shown_days)
    # 上段那枚图（`CALENDAR_ICON_SRC`，和底部菜单、空态提示同一张）：平时就摆它本来的
    # 样子；**过期的卡片压成 `EXPIRED_ICON_COLOR` 那档灰** —— `SRC_IN` 只留图的形状、
    # 颜色换成给定的这档，于是它和整张灰卡是一套（不然一张灰卡上顶着一枚彩色图很跳）。
    icon = ft.Image(
        src=CALENDAR_ICON_SRC,
        width=ICON_SIZE,
        height=ICON_SIZE,
        fit=ft.BoxFit.CONTAIN,
        color=EXPIRED_ICON_COLOR if expired else None,
        color_blend_mode=ft.BlendMode.SRC_IN if expired else None,
    )
    card = ft.Container(
        key=f"countdown-{item.id}",
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        border=ft.Border.all(1, CARD_BORDER),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor=body_bg,
        content=ft.Column(
            tight=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                # 上：图标 + 倒数日事项，一般用这张卡自己的背景色（过期卡片用灰）
                ft.Container(
                    padding=HEADER_PADDING,
                    bgcolor=header_bg,
                    content=ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            icon,
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
                # 中：天数 + 右上角的「天后 / 天前」（过期的和下面的「已过期 N 天」
                # 是同一个数）
                ft.Container(
                    padding=MID_PADDING,
                    content=days_block(shown_days, badge_bg),
                ),
                # 中 / 下之间那一排小圆点
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=8),
                    content=dotted_rule(),
                ),
                # 下：周几一行、日期 · 农历一行，都居中；过期卡片把日期那行换成
                # 「已过期 N 天」，字色照旧是灰色。
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
                                expired_text
                                if expired
                                else countdown_date_lunar(item),
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
