"""「编辑地区」页（编辑资料页点「地区」进来）—— 照小红书那张图。

版式：顶栏（‹ + 居中「编辑地区」+ 右上「保存」）→ 一张白卡片（一行「地区」，右边是选中的
地区 / 浅灰占位「选择所在的地区」+ ›）→ 一行小灰字「是否公开展示」→ 一张白卡片
（「展示地区标签」开关）。

点「地区」那一行**不是弹输入框了**：跳到**另一整页**「选择你的地区」
（pages/pick_region.py，压在这一页之上，第 3 层）—— 上面一行是定位到的位置，下面是
「全部」国家列表，逐级往下选（国家 → 省 → 市 → 区）。选完退回这一页，这一行就是新值。

选完**不立刻保存**：点右上「保存」才打后端 `PUT /member/profile {region}`
（见 api/member_profile.py）。「展示地区标签」只写内存 —— 后端没有这个字段
（见 tools/mock_settings.py），和性别 / 生日那两页同一个做法。
"""

from collections.abc import Callable

import flet as ft

from api import member_profile
from api.client import ApiError
from tools import mock_settings
from tools.my_profile import region
from widgets.field_page import (
    CARD_GAP,
    build_save_header,
    build_shell,
    card,
    notify,
    section_label,
    switch_row,
    value_row,
)
from widgets.layout import safe_update

TITLE = "编辑地区"
# 没选过地区时那一行的浅灰占位（照那张图）。
REGION_HINT = "选择所在的地区"
# 卡片上方那行小灰字。
SECTION = "是否公开展示"


def build_edit_region_page(
    page: ft.Page,
    go_back: Callable[[], None],
    open_picker: Callable[[], None],
    picked: str | None = None,
) -> ft.Control:
    """`go_back` 是左上角那个 ‹（保存成功后也走它退回编辑资料页）。

    `picked` 是「选择你的地区」页刚选回来的值（`None` = 还没去选过，用资料里那份）。
    选择页压在这一页之上，选完由 navigation 传回来 —— 这一页是重新构建的，
    所以这个值只能从外面递进来（见 pages/navigation.py）。
    """
    original = region()
    # 这一页上的临时选择；没改过就等于原来的值（「保存」也就点不动）。
    selected = picked if picked is not None else original

    body = ft.Column(
        spacing=CARD_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[],
    )

    def toggle_show_region(event: ft.Event[ft.Switch]) -> None:
        """「展示地区标签」：只写内存 —— 后端没有这个字段（见 tools/mock_settings.py）。"""
        mock_settings.set_setting(
            mock_settings.SHOW_REGION_SETTING,
            mock_settings.SWITCH_ON if event.control.value else mock_settings.SWITCH_OFF,
        )

    def refresh() -> None:
        """重画两张卡片，并决定「保存」能不能点（没改就点不动）。"""
        set_save_enabled(selected != original)
        body.controls = [
            card([value_row("地区", selected, REGION_HINT, open_picker)]),
            section_label(SECTION),
            card(
                [
                    switch_row(
                        "展示地区标签",
                        mock_settings.get_setting(
                            mock_settings.SHOW_REGION_SETTING,
                            mock_settings.SWITCH_ON,
                        )
                        == mock_settings.SWITCH_ON,
                        toggle_show_region,
                    )
                ]
            ),
        ]
        safe_update(body)

    async def on_save() -> None:
        try:
            await member_profile.update_profile(region=selected)
        except ApiError as error:
            notify(page, error.message)
            return
        go_back()
        notify(page, f"地区：{selected}")

    header, set_save_enabled = build_save_header(
        TITLE, go_back, lambda: page.run_task(on_save)
    )
    refresh()
    return build_shell(header, body)
