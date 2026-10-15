"""「编辑生日」页（编辑资料页点「生日」进来）—— 照小红书那张图。

版式：顶栏（‹ + 居中「编辑生日」+ 右上「保存」）→ 一张白卡片（一行「生日信息」，
右边是选中的那天 / 浅灰占位「选择你的生日」+ ›）→ 一行小灰字「是否公开展示」→
两张白卡片（「展示生日标签」开关；「展示年龄 / 展示星座」**二选一**）。

点「生日信息」**从底下滑出一块滚轮面板**（`ft.BottomSheet`，见 widgets/wheel.py），
不是居中弹窗：三列「年 / 月 / 日」，正中那行高亮，滑停自动吸到整行上。

（原来用的是 `ft.DatePicker` 系统弹窗选择器。项目里那个 Cupertino 原生滚轮早先试过、
**滚动之后值回不来**，所以那会儿退回了系统选择器；这次要「底部滑动」，就自己用
`ft.ListView` 搭了滚轮 —— 除了滑动，**点一行也能选中**，值不会丢。）

选完不立刻保存：点右上「保存」才 `PUT /member/profile {birthday}`（`YYYY-MM-DD`，
见 api/member_profile.py）；后端会挡掉「晚于今天」和「早于 1900 年」，滚轮只列到这两个边界。
"""

import calendar
from collections.abc import Callable
from datetime import date

import flet as ft

from api import member_profile
from api.client import ApiError
from tools import mock_settings
from tools.my_profile import birthday
from widgets.field_page import (
    CARD_GAP,
    build_save_header,
    build_shell,
    card,
    choice_row,
    notify,
    section_label,
    switch_row,
    value_row,
)
from widgets.layout import date_label, safe_update
from widgets.wheel import Wheel, build_picker_sheet

TITLE = "编辑生日"
BIRTHDAY_HINT = "选择你的生日"
# 滚轮的边界：和后端的校验一致（不晚于今天、不早于 1900 年）。
FIRST_YEAR = 1900
# 没选过生日时滚轮停在 2000-01-01（不是今天）—— 一进来就是今天的日期太像「已经选好了」。
DEFAULT_DAY = date(2000, 1, 1)


def _year_labels() -> list[str]:
    return [f"{year}年" for year in range(FIRST_YEAR, date.today().year + 1)]


def _month_labels() -> list[str]:
    return [f"{month}月" for month in range(1, 13)]


def _day_labels(year: int, month: int) -> list[str]:
    """「日」那一列：按这个年月实际有多少天给（2 月会短一截）。"""
    days = calendar.monthrange(year, month)[1]
    return [f"{day}日" for day in range(1, days + 1)]


def build_edit_birthday_page(
    page: ft.Page, go_back: Callable[[], None]
) -> ft.Control:
    """`go_back` 是左上角那个 ‹（保存成功后也走它退回编辑资料页）。"""
    original = birthday()
    # 这一页上选中的那天，`YYYY-MM-DD`；没选过就是空串（那一行摆浅灰占位）。
    picked = original

    body = ft.Column(
        spacing=CARD_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[],
    )

    def picked_date() -> date:
        """当前选中的那天；没选过（或值坏了）就给滚轮的起点。"""
        try:
            return date.fromisoformat(picked) if picked else DEFAULT_DAY
        except ValueError:
            return DEFAULT_DAY

    def picked_text() -> str:
        """「2001年5月20日」；没选过就是空串（让那一行走占位）。"""
        return date_label(picked_date()) if picked else ""

    def open_picker() -> None:
        """点「生日信息」那一行：**从底下滑出**滚轮面板（不是弹窗）。"""
        start = picked_date()
        # ⚠️ 三个回调都读闭包里的三个滚轮 —— 它们在这几行之后才赋值，但回调只在用户
        # 滚动 / 点选时才跑，那时三个都已经在了。
        def sync_days() -> None:
            """年月一变，「日」那一列要跟着变长变短（原来那天超了月末就压到月末）。"""
            labels = _day_labels(
                FIRST_YEAR + year_wheel.index, month_wheel.index + 1
            )
            day_wheel.set_values(labels, min(day_wheel.index, len(labels) - 1))

        year_wheel = Wheel(
            page,
            _year_labels(),
            start.year - FIRST_YEAR,
            lambda _index: sync_days(),
        )
        month_wheel = Wheel(
            page, _month_labels(), start.month - 1, lambda _index: sync_days()
        )
        day_wheel = Wheel(page, _day_labels(start.year, start.month), start.day - 1)

        def close() -> None:
            page.pop_dialog()

        def cancel() -> None:
            close()

        def confirm() -> None:
            """面板上的「保存」：把滚轮停下的三格拼成日期，写回这一页（还没提交后端）。"""
            nonlocal picked
            picked = date(
                FIRST_YEAR + year_wheel.index,
                month_wheel.index + 1,
                day_wheel.index + 1,
            ).isoformat()
            close()
            refresh()

        page.show_dialog(
            build_picker_sheet(
                # 面板标题固定是「选择你的生日」（照那张图），不显示当前选中的日期。
                BIRTHDAY_HINT,
                [year_wheel, month_wheel, day_wheel],
                on_cancel=cancel,
                on_confirm=confirm,
            )
        )
        # 控件落到界面上才滚得动：等它铺开再把选中行摆到正中。
        for wheel in (year_wheel, month_wheel, day_wheel):
            wheel.center_when_ready()

    def toggle_show_birthday(event: ft.Event[ft.Switch]) -> None:
        """「展示生日标签」：只写内存 —— 后端没有这个字段（见 tools/mock_settings.py）。"""
        mock_settings.set_setting(
            mock_settings.SHOW_BIRTHDAY_SETTING,
            mock_settings.SWITCH_ON if event.control.value else mock_settings.SWITCH_OFF,
        )

    def choose_display(mode: str) -> None:
        """「展示年龄 / 展示星座」二选一（那张图里只有一项带勾）——同样只写内存。"""
        mock_settings.set_setting(mock_settings.BIRTHDAY_DISPLAY_SETTING, mode)
        refresh()

    def show_birthday_switch() -> ft.Control:
        return switch_row(
            "展示生日标签",
            mock_settings.get_setting(
                mock_settings.SHOW_BIRTHDAY_SETTING, mock_settings.SWITCH_ON
            )
            == mock_settings.SWITCH_ON,
            toggle_show_birthday,
        )

    def refresh() -> None:
        """按当前选择重画四块内容，并决定「保存」能不能点（日期没改就点不动）。"""
        set_save_enabled(bool(picked) and picked != original)
        display = mock_settings.get_setting(
            mock_settings.BIRTHDAY_DISPLAY_SETTING, mock_settings.BIRTHDAY_AGE
        )
        body.controls = [
            card([value_row("生日信息", picked_text(), BIRTHDAY_HINT, open_picker)]),
            section_label("是否公开展示"),
            card([show_birthday_switch()]),
            card(
                [
                    choice_row(
                        "展示年龄",
                        display == mock_settings.BIRTHDAY_AGE,
                        lambda: choose_display(mock_settings.BIRTHDAY_AGE),
                    ),
                    choice_row(
                        "展示星座",
                        display == mock_settings.BIRTHDAY_ZODIAC,
                        lambda: choose_display(mock_settings.BIRTHDAY_ZODIAC),
                    ),
                ]
            ),
        ]
        safe_update(body)

    async def on_save() -> None:
        try:
            await member_profile.update_profile(birthday=picked)
        except ApiError as error:
            notify(page, error.message)
            return
        go_back()
        notify(page, f"生日：{picked_text()}")

    header, set_save_enabled = build_save_header(
        TITLE, go_back, lambda: page.run_task(on_save)
    )
    refresh()
    return build_shell(header, body)
