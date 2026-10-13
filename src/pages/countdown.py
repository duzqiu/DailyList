"""倒数日 page: 底部菜单第二格。

数据源是**后端**（`/member/countdowns`，按登录会员隔离）：进页面拉一次，缓存在
tools/countdown_store.py 里，页面（以及日历页那几处）同步读缓存 —— 所以「拉数据」是
异步的，而渲染仍是同步的、一行都不用改成 async。

未登录时这一页只显示一句「登录后可同步倒数日」（登录入口在设置页的「账号」卡片里），
右下角那枚「+」照常在，点了会提示先登录。

Every entry keeps the anchor date plus an optional 周期 (the same choices a
repeating 待办 uses). A repeating anchor walks forward to its next occurrence, so
a birthday written down years ago still counts down to the coming one, while 不循环
counts down to the fixed day - or shows how long ago it passed.
"""

from collections.abc import Callable
from datetime import date

import flet as ft

from api.client import ApiError
from tools import countdown_store
from tools.countdown_card import (
    MUTED_COLOR,
    TITLE_COLOR,
    build_countdown_card,
    countdown_days,
    expired_countdowns,
    visible_countdowns,
)
from tools.countdown_form import open_countdown_form
from tools.layout import (
    ADD_ICON_SRC,
    BOTTOM_MENU_INSET,
    page_gradient,
    safe_update,
)
from tools.toast import build_toast

PAGE_SIDE_PADDING = 24
# 双列卡片：两张之间的缝，以及再窄也要保住的卡片宽度。
COUNTDOWN_GAP = 10
COUNTDOWN_MIN_WIDTH = 140

# 右下角那枚「+」：和待办页那一枚同一个尺寸、位置与长相（见 pages/home.py）。
# 「+」在这里是**直接**开新增倒数日的弹窗（待办页那边还要先选「新增待办 / 倒数日」，
# 因为那儿有两种东西要加；这一页只有倒数日，不用再问一次）。
ADD_BUTTON_SIZE = 52
ADD_BUTTON_LIFT = 10
ADD_BUTTON_BORDER = "#E2E8F0"
ADD_BUTTON_BORDER_WIDTH = 1
ADD_ICON_SIZE = 22

# 列表最底下那个「已过期 N」开关：弱化成一行浅灰小字 —— 没有边框也没有底色，
# 圆角只用来给水波纹定型。key 留给校验用。
EXPIRED_TOGGLE_KEY = "expired-toggle"
EXPIRED_TOGGLE_TEXT_SIZE = 12
EXPIRED_TOGGLE_ICON_SIZE = 16
EXPIRED_TOGGLE_COLOR = "#94A3B8"
EXPIRED_TOGGLE_RADIUS = 8

# 未登录 / 空态那两句提示共用的外框色。
HINT_BG = "#F8FAFC"
HINT_BORDER = "#E2E8F0"
HINT_TEXT_COLOR = "#64748B"
SIGNED_OUT_HINT = "登录后可同步倒数日"
SIGNED_OUT_WHERE = "入口：设置 → 账号"
NEED_LOGIN_TOAST = "请先登录后再新增倒数日"


def build_countdown_page(
    page: ft.Page, set_menu_visible: Callable[[bool], None]
) -> ft.Control:
    today = date.today()
    items = ft.ListView(
        expand=True,
        spacing=COUNTDOWN_GAP,
        scroll=ft.ScrollMode.HIDDEN,
        padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
    )

    # 底部「已过期的倒数日」现在是开是关：刷新（增删改、重新渲染）时保持不变，
    # 只有点它才翻。
    expired_open = False

    def notify(message: str) -> None:
        """一句话的提示：走 tools/toast.py，浮在屏幕正中。"""
        page.show_dialog(build_toast(page, message))

    def card_width() -> float:
        """卡片宽度跟着屏幕走：页面左右各 24px，中间留一道缝，正好两列。"""
        page_width = getattr(page, "width", None) or 360
        return max(
            COUNTDOWN_MIN_WIDTH,
            (page_width - PAGE_SIDE_PADDING * 2 - COUNTDOWN_GAP) / 2,
        )

    def entry(
        item: countdown_store.Countdown, expired: bool = False
    ) -> ft.Control:
        return build_countdown_card(
            item,
            today=today,
            expired=expired,
            on_delete=lambda _: remove(item.id),
            on_edit=lambda _: edit(item),
        )

    def card_grid(
        rows: list[countdown_store.Countdown],
        expired: bool = False,
        wide_first: bool = True,
    ) -> list[ft.Control]:
        """两列排；`wide_first` 时第一张单独通栏（倒数日页上面那一段）。

        过期那一段传 `wide_first=False` —— 全部双列，谁也不被单独放大。
        """
        controls: list[ft.Control] = []
        rest = rows
        if wide_first and rows:
            controls.append(entry(rows[0], expired))
            rest = rows[1:]
        if rest:
            controls.append(
                ft.Row(
                    wrap=True,
                    spacing=COUNTDOWN_GAP,
                    run_spacing=COUNTDOWN_GAP,
                    controls=[
                        ft.Container(
                            width=card_width(),
                            content=entry(item, expired),
                        )
                        for item in rest
                    ],
                )
            )
        return controls

    def hint(
        icon: str, title: str, subtitle: str = ""
    ) -> ft.Control:
        """一块浅色小提示（空态与未登录态共用，只有文案和图标不同）。"""
        lines = [
            ft.Text(title, size=13, color=HINT_TEXT_COLOR),
        ]
        if subtitle:
            lines.append(ft.Text(subtitle, size=11, color=HINT_TEXT_COLOR))
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=ft.BorderRadius.all(12),
            bgcolor=HINT_BG,
            border=ft.Border.all(1, HINT_BORDER),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=20, color=MUTED_COLOR),
                    ft.Column(tight=True, spacing=2, controls=lines),
                ],
            ),
        )

    def empty_hint() -> ft.Control:
        return hint(ft.Icons.HOURGLASS_EMPTY, "还没有倒数日哦")

    def signed_out_hint() -> ft.Control:
        """未登录：整页就这一句 —— 数据在后端，登录了才有得可看。"""
        return hint(
            ft.Icons.LOCK_OUTLINE, SIGNED_OUT_HINT, SIGNED_OUT_WHERE
        )

    def expired_toggle(count: int) -> ft.Control:
        """列表最底下那个开关：点开展示已过期的卡片，再点收回去。"""
        return ft.Container(
            key=EXPIRED_TOGGLE_KEY,
            # 没有边框、没有底色：过期卡片是次要信息，这里只留一行浅灰小字。
            border_radius=ft.BorderRadius.all(EXPIRED_TOGGLE_RADIUS),
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            ink=True,
            on_click=lambda _: set_expired_open(not expired_open),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
                controls=[
                    ft.Text(
                        f"已过期 {count}",
                        size=EXPIRED_TOGGLE_TEXT_SIZE,
                        color=EXPIRED_TOGGLE_COLOR,
                    ),
                    ft.Icon(
                        (
                            ft.Icons.EXPAND_LESS
                            if expired_open
                            else ft.Icons.EXPAND_MORE
                        ),
                        size=EXPIRED_TOGGLE_ICON_SIZE,
                        color=EXPIRED_TOGGLE_COLOR,
                    ),
                ],
            ),
        )

    def set_expired_open(open_it: bool) -> None:
        """展开 / 收起过期的那些：重画整列，箭头方向也跟着翻。"""
        nonlocal expired_open
        if open_it == expired_open:
            return
        expired_open = open_it
        refresh()

    def render() -> None:
        """按缓存重画整列（同步）：未登录 → 提示；否则就是那两段卡片。"""
        if not countdown_store.logged_in():
            items.controls = [signed_out_hint()]
            return
        all_items = countdown_store.items()
        # 到期的按天数排；过期的那些被 `visible_countdowns` 筛掉了（见
        # tools/countdown_card.py），收在底部那个开关里，最近过期的排最前。
        rows = sorted(
            visible_countdowns(all_items, today),
            key=lambda item: countdown_days(item, today),
        )
        expired = sorted(
            expired_countdowns(all_items, today),
            key=lambda item: countdown_days(item, today),
            reverse=True,
        )
        if not rows and not expired:
            items.controls = [empty_hint()]
            return
        # 最近的那个单独放最上面，占满一整行；其余的按两列排（窄屏自动落成一张）。
        controls: list[ft.Control] = card_grid(rows) if rows else []
        if expired:
            controls.append(expired_toggle(len(expired)))
            if expired_open:
                controls.extend(
                    card_grid(expired, expired=True, wide_first=False)
                )
        items.controls = controls

    async def do_remove(countdown_id: int) -> None:
        """左滑删除：真删在后端，删完重画（失败就提示，列表不动）。"""
        try:
            await countdown_store.remove(countdown_id)
        except ApiError as error:
            notify(error.message)
            return
        refresh()

    def remove(countdown_id: int) -> None:
        page.run_task(do_remove, countdown_id)

    def open_form(item: countdown_store.Countdown | None = None) -> None:
        """新增 / 编辑弹窗；没登录先提示（保存时还会再拦一次）。"""
        if not countdown_store.logged_in():
            notify(NEED_LOGIN_TOAST)
            return
        open_countdown_form(
            page,
            # 输入框弹键盘时收起底部菜单（和待办弹窗用的是同一套回调）。
            set_menu_visible=set_bottom_controls_visible,
            on_saved=refresh,
            item=item,
        )

    def refresh() -> None:
        """重画整列并刷到界面。

        走 `safe_update`：这个函数既被同步的点击调，也被**异步任务**调（拉数据、左滑
        删除、弹窗保存后的回调）—— 后者回来时这一页可能已经被换掉了，硬 `update()` 会
        抛「ListView Control must be added to the page first」。
        """
        render()
        safe_update(items)

    def edit(item: countdown_store.Countdown) -> None:
        open_form(item)

    async def load() -> None:
        """进页面拉一次后端数据；拉完重画（失败只提示，页面照旧是空态）。

        刷新统一走 `refresh()`（内部 `safe_update`）：这一页每次切过来都是**重建**
        的，网络回来时它可能已经被换掉了，直接 `items.update()` 会抛
        「ListView Control must be added to the page first」。
        """
        try:
            await countdown_store.reload()
        except ApiError as error:
            notify(error.message)
        refresh()

    def go_add(_: ft.Event[ft.Control]) -> None:
        open_form()

    add_button = ft.Container(
        right=PAGE_SIDE_PADDING,
        # 和待办页那枚一样：坐在浮动菜单条上面 10px（菜单条高度就是那个 inset）。
        bottom=BOTTOM_MENU_INSET + ADD_BUTTON_LIFT,
        width=ADD_BUTTON_SIZE,
        height=ADD_BUTTON_SIZE,
        shape=ft.BoxShape.CIRCLE,
        # 透明底 + 一圈细灰边：和待办页那枚同一个做法（没有底色，边界靠这圈线）。
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.Border.all(ADD_BUTTON_BORDER_WIDTH, ADD_BUTTON_BORDER),
        content=ft.IconButton(
            icon=ft.Image(
                src=ADD_ICON_SRC,
                width=ADD_ICON_SIZE,
                height=ADD_ICON_SIZE,
                fit=ft.BoxFit.CONTAIN,
            ),
            tooltip="新增倒数日",
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
            on_click=go_add,
        ),
    )

    def set_bottom_controls_visible(visible: bool) -> None:
        """弹窗（输入框弹键盘）时，底部菜单和这枚「+」一起退场。"""
        set_menu_visible(visible)
        add_button.visible = visible
        # 弹窗保存后的回调也会走到这儿（那时这一页可能已经被换掉了，见 refresh）。
        safe_update(add_button)

    render()
    # 进页面就拉一次：这一页每次切过来都是重建的，所以等于每次进来都刷新一遍。
    page.run_task(load)

    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                gradient=page_gradient(),
                content=ft.SafeArea(
                    expand=True,
                    content=ft.Container(
                        expand=True,
                        padding=ft.Padding.only(
                            left=PAGE_SIDE_PADDING,
                            top=PAGE_SIDE_PADDING,
                            right=PAGE_SIDE_PADDING,
                            bottom=PAGE_SIDE_PADDING,
                        ),
                        content=ft.Column(
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
                                ft.Text(
                                    "倒数日",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                                ft.Container(
                                    expand=True,
                                    margin=ft.Margin.only(top=12),
                                    content=items,
                                ),
                            ],
                        ),
                    ),
                ),
            ),
            add_button,
        ],
    )
