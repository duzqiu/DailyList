"""「编辑性别」页（编辑资料页点「性别」进来）—— 照小红书那张图。

版式：顶栏（‹ + 居中「编辑性别」+ 右上「保存」）→ 一张白卡片里两行（「男」/「女」，
选中的那行右边一枚红勾）→ 一行小灰字「是否公开展示」→ 一张白卡片（「展示性别标签」开关）。

选中**不立刻保存**：改完点右上「保存」才打后端 `PUT /member/profile {gender}`
（见 api/member_profile.py，中文在这里换成后端的 male / female）—— 和那张图一致，
勾选只是改了这一页上的选择；保存成功后 `go_back()` 退回编辑资料页，那一层会重画。

⚠️ 选项**只有「男」「女」**（照那张图）。领域里还有个「保密」（`my_profile.GENDERS`），
这一页没摆 —— 需要的话在 `GENDER_OPTIONS` 里加一项即可。
"""

from collections.abc import Callable

import flet as ft

from api import member_profile
from api.client import ApiError
from tools import mock_settings
from tools.my_profile import gender
from widgets.field_page import (
    CARD_GAP,
    build_save_header,
    build_shell,
    card,
    choice_row,
    notify,
    section_label,
    switch_row,
)
from widgets.layout import safe_update

GENDER_OPTIONS = ("男", "女")

TITLE = "编辑性别"


def build_edit_gender_page(
    page: ft.Page, go_back: Callable[[], None]
) -> ft.Control:
    """`go_back` 是左上角那个 ‹（保存成功后也走它退回编辑资料页）。"""
    original = gender()
    # 这一页上的临时选择；原来没选过就是空串 —— 两行都不亮勾，选中哪行才亮哪行。
    selected = original

    body = ft.Column(
        spacing=CARD_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[],
    )

    def pick(option: str) -> None:
        nonlocal selected
        selected = option
        refresh()

    def toggle_show_gender(event: ft.Event[ft.Switch]) -> None:
        """「展示性别标签」：只写内存 —— 后端没有这个字段（见 tools/mock_settings.py）。"""
        mock_settings.set_setting(
            mock_settings.SHOW_GENDER_SETTING,
            mock_settings.SWITCH_ON if event.control.value else mock_settings.SWITCH_OFF,
        )

    def show_gender_switch() -> ft.Control:
        return switch_row(
            "展示性别标签",
            mock_settings.get_setting(
                mock_settings.SHOW_GENDER_SETTING, mock_settings.SWITCH_OFF
            )
            == mock_settings.SWITCH_ON,
            toggle_show_gender,
        )

    def refresh() -> None:
        """按当前选择重画两张卡片，并决定「保存」能不能点（没改就点不动）。"""
        set_save_enabled(bool(selected) and selected != original)
        body.controls = [
            card(
                [
                    choice_row(
                        option,
                        option == selected,
                        # ⚠️ `option=option`：不写就全都捕获到最后一个值（闭包晚绑定）。
                        lambda option=option: pick(option),
                    )
                    for option in GENDER_OPTIONS
                ]
            ),
            section_label("是否公开展示"),
            card([show_gender_switch()]),
        ]
        safe_update(body)

    async def on_save() -> None:
        try:
            # 性别传中文，api 层换成后端的 male / female。
            await member_profile.update_profile(gender=selected)
        except ApiError as error:
            notify(page, error.message)
            return
        go_back()
        notify(page, f"性别：{selected}")

    header, set_save_enabled = build_save_header(
        TITLE, go_back, lambda: page.run_task(on_save)
    )
    refresh()
    return build_shell(header, body)
