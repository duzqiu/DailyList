"""The 新增/编辑倒数日 dialog used by the 倒数日 page.

弹窗里不摆颜色：卡片底色由 tools/countdown_store.py 按倒数日的 **id** 稳定取一档浅色
（后端没有颜色字段）。保存走的是后端接口（`/member/countdowns`，见
api/member_countdowns.py），所以要登录 —— 没登录时点「保存」会给一句提示、弹窗不关。

周期只提供后端支持的那几档（`SUPPORTED_CYCLES`）：后端 `CountdownCycle` 目前只有
once / daily / weekly / monthly / yearly，App 另外那 5 档（三天 / 工作日 / 非工作日 /
三月 / 六月）还没有对应取值，选了也存不进去。
"""

from collections.abc import Callable
from datetime import date

import flet as ft

from api.client import ApiError
from api.member_countdowns import DEFAULT_CYCLE, SUPPORTED_CYCLES
from tools import countdown_store
from tools.layout import (
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    date_label,
    dialog_button_style,
    track_keyboard,
)
from tools.pickers import build_date_picker, build_value_trigger
from tools.popup_select import (
    MENU_HEIGHT,
    build_option_row,
    build_option_selector,
    build_option_text,
)
from tools.toast import build_toast

TITLE_COLOR = "#172554"
MUTED_COLOR = "#94A3B8"


def open_countdown_form(
    page: ft.Page,
    *,
    set_menu_visible: Callable[[bool], None],
    on_saved: Callable[[], None],
    item: countdown_store.Countdown | None = None,
) -> None:
    """Show the 新增/编辑倒数日 dialog. `item` present means editing."""
    editing = item is not None
    today = date.today()
    start_day = item.due_date if editing else today
    draft = {"date": start_day}
    cycle_text = build_option_text(
        item.cycle if editing else DEFAULT_CYCLE
    )

    date_text = build_option_text(date_label(start_day))

    def apply_date(chosen: date) -> None:
        draft["date"] = chosen
        date_text.value = date_label(chosen)
        date_text.update()

    # 日期 uses the shared system picker with no lower bound: a countdown
    # anchor may sit in the past (a birthday, an anniversary).
    sheet = build_date_picker(start_day, apply_date)

    def open_date_picker(_: ft.Event[ft.Control]) -> None:
        page.show_dialog(sheet)

    date_trigger = build_value_trigger(date_text, open_date_picker)

    def set_cycle(name: str) -> None:
        cycle_text.value = name
        cycle_text.update()

    cycle_selector = build_option_selector(
        cycle_text,
        # 只列后端 `CountdownCycle` 认得的这几档（App 内部另几档见 db.REPEAT_CYCLES）。
        [(name, name) for name in SUPPORTED_CYCLES],
        set_cycle,
        # 面板钉成固定高度：档位再多也不用改这里，多出来的在里面上下滚。
        menu_height=MENU_HEIGHT,
        content_width=90,
    )

    def focus_changed(focused: bool) -> None:
        # 弹窗跟着键盘走由 `track_keyboard` 管（焦点事件比键盘动画早一步，按它挪
        # 会先沉一下再弹回来）。
        set_menu_visible(not focused)

    content_field = ft.TextField(
        value=item.content if editing else "",
        hint_text="请输入倒数日事项",
        hint_style=ft.TextStyle(size=13, color=MUTED_COLOR),
        # Typing opens the keyboard, so the floating menu bar steps out of the
        # way and the dialog parks just above the keyboard.
        on_focus=lambda _: focus_changed(True),
        on_blur=lambda _: focus_changed(False),
        filled=False,
        border=ft.NoInputBorder(),
        content_padding=ft.Padding.symmetric(horizontal=0, vertical=6),
        text_style=ft.TextStyle(size=13, color="#334155"),
        dense=True,
        # 事项就是一行字，输入框也保持单行 —— 不设 `multiline`，它就没有会长高的
        # 余地。
    )

    def close_dialog(_: ft.Event[ft.Control] | None = None) -> None:
        unwatch_keyboard()
        dialog.open = False
        set_menu_visible(True)
        page.update()

    def notify(message: str) -> None:
        """一句话提示：走 tools/toast.py，浮在屏幕正中（弹窗开着也看得见）。"""
        page.show_dialog(build_toast(page, message))

    async def do_save(text: str) -> None:
        """带请求的那半：走倒数日仓库（内部调 `/member/countdowns`）。"""
        try:
            if editing and item is not None:
                await countdown_store.update(
                    item.id, draft["date"], text, cycle_text.value
                )
            else:
                await countdown_store.create(
                    draft["date"], text, cycle_text.value
                )
        except ApiError as error:
            # 没存成（令牌失效、网络异常、后端校验…）：弹窗留着，人改完再存一次。
            notify(error.message)
            return
        close_dialog()
        on_saved()

    def save(_: ft.Event[ft.Control]) -> None:
        """「保存」：先判空与登录态，请求丢给 `page.run_task`（别卡住事件循环）。"""
        text = (content_field.value or "").strip()
        if not text:
            return
        if not countdown_store.logged_in():
            notify("请先登录后再保存倒数日")
            return
        page.run_task(do_save, text)

    dialog = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
        bgcolor=DIALOG_SURFACE,
        elevation=0,
        title="编辑倒数日" if editing else "新增倒数日",
        title_text_style=ft.TextStyle(
            size=16,
            weight=ft.FontWeight.BOLD,
            color=TITLE_COLOR,
        ),
        inset_padding=ft.Padding.symmetric(horizontal=48, vertical=24),
        title_padding=ft.Padding.only(left=16, top=12, right=16, bottom=0),
        content_padding=ft.Padding.only(left=16, top=8, right=16, bottom=8),
        actions_padding=ft.Padding.only(left=8, right=8, bottom=8),
        action_button_padding=ft.Padding.symmetric(horizontal=8),
        # 点外面 / 按返回关掉时也走 `close_dialog`，键盘跟随在那里拆。
        on_dismiss=lambda _: close_dialog(),
        content=ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                content_field,
                build_option_row(date_trigger),
                build_option_row(cycle_selector),
            ],
        ),
        actions=[
            ft.TextButton(
                "取消",
                style=dialog_button_style(),
                on_click=close_dialog,
            ),
            ft.TextButton(
                "保存",
                style=dialog_button_style(),
                on_click=save,
            ),
        ],
    )
    # 键盘一升一落都把弹窗挪到键盘上方 / 回到正中（见 track_keyboard）。
    unwatch_keyboard = track_keyboard(page, dialog)
    page.show_dialog(dialog)
