"""「编辑单个字段」那三页（简介 / 生日 / 性别）共用的零件。

从「编辑主页」点进去的这三行，现在各自开到**独立的一页**上（原来是在编辑资料页里弹弹窗，
照小红书那三张图改成整页）：

    编辑简介  pages/edit_intro.py      多行输入 + 右下角「0/160」计数
    编辑生日  pages/edit_birthday.py   一行「生日信息」+「是否公开展示」三枚开关
    编辑性别  pages/edit_gender.py     男 / 女 两行 +「展示性别标签」开关

三页长得一样：顶栏（‹ 返回 + 居中标题 + 右上「保存」）→ 白卡片 → 一行灰色小节标题 → 白卡片。
所以卡片、行、开关、红勾这些零件都在这儿做一次，三页只管往里塞内容。

**「保存」不是摆设**：内容**改过**才变红可点，点下去打后端 `PUT /member/profile`
（见 api/member_profile.py）；没改之前是浅灰、点不动 —— 照那三张图（简介页刚进去
「保存」就是灰的）。
"""

from collections.abc import Callable

import flet as ft

from widgets.layout import (
    BACK_HEIGHT,
    BACK_WIDTH,
    BOTTOM_MENU_INSET,
    build_back_button,
    safe_update,
)
from widgets.toast import build_toast

# 配色照编辑资料页那一套：浅灰底、白卡片、值近黑、说明灰。
PAGE_BG = "#F5F5F5"
CARD_BG = "#FFFFFF"
CARD_RADIUS = 10
CARD_SIDE = 12
CARD_GAP = 12
ROW_HEIGHT = 52
ROW_SIDE = 16
LABEL_SIZE = 16
LABEL_COLOR = "#1F1F1F"
PLACEHOLDER_COLOR = "#BDBDBD"
DIVIDER_COLOR = "#F0F0F0"
CHEVRON_COLOR = "#C9C9C9"
# 卡片上方那行小灰字（「是否公开展示」）。
SECTION_SIZE = 13
SECTION_COLOR = "#8C8C8C"
TITLE_SIZE = 17
TITLE_COLOR = "#1A1A1A"

# 「保存」和那几枚开关的红：和「换背景图」页、底栏那颗「+」是同一个强调红。
ACCENT_RED = "#FF2442"
SAVE_SIZE = 15
# 「保存」不可用时的灰 —— 和没填过的占位一个色系。
SAVE_IDLE_COLOR = "#C9C9C9"
CHECK_SIZE = 20


def notify(page: ft.Page, message: str) -> None:
    """一句话提示：走 widgets/toast.py，浮在屏幕正中（全项目一个做法）。"""
    page.show_dialog(build_toast(page, message))


def build_save_header(
    title: str,
    go_back: Callable[[], None],
    on_save: Callable[[], None],
) -> tuple[ft.Row, Callable[[bool], None]]:
    """顶栏：‹ 返回 + 居中 `title` + 右上「保存」。

    返回 `(顶栏, 设置「保存」可用状态的函数)`：**默认不可用**（浅灰、点了没反应），
    页面发现自己有改动时再叫 `set_enabled(True)` 把它点亮成红。

    右侧那格补的宽度和返回按钮一样（`BACK_WIDTH`），标题才会落在正中 —— 与
    `widgets/layout.py` 的 `build_subpage_header` 同一个道理。
    """
    save = ft.Text("保存", size=SAVE_SIZE, color=SAVE_IDLE_COLOR)
    # 「现在能不能点」。`on_click` 只挂一次，点不点得动跟着它走 —— 变灰的同时也点不动，
    # 光看颜色会以为还能点。
    enabled = False

    def set_enabled(value: bool) -> None:
        nonlocal enabled
        enabled = value
        save.color = ACCENT_RED if value else SAVE_IDLE_COLOR
        safe_update(save)

    def tap(_: ft.Event[ft.Container]) -> None:
        if enabled:
            on_save()

    header = ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            build_back_button(go_back),
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    title,
                    size=TITLE_SIZE,
                    weight=ft.FontWeight.BOLD,
                    color=TITLE_COLOR,
                ),
            ),
            ft.Container(
                width=BACK_WIDTH,
                height=BACK_HEIGHT,
                alignment=ft.Alignment.CENTER_RIGHT,
                ink=True,
                tooltip="保存",
                on_click=tap,
                content=save,
            ),
        ],
    )
    return header, set_enabled


def row(label: str, trailing: ft.Control | None, on_click: Callable[[], None] | None = None) -> ft.Container:
    """一行：标签在左、`trailing` 贴在右，整行可点（`on_click` 为 `None` 就不可点）。

    三页所有行都走它 —— 行高、左右内边距、标签字号才对得齐。
    """
    controls: list[ft.Control] = [
        ft.Text(label, size=LABEL_SIZE, color=LABEL_COLOR)
    ]
    if trailing is not None:
        controls.append(
            # 这一格带 `alignment`：不带的话它会把子控件拉满（开关会被抻开）。
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER_RIGHT,
                content=trailing,
            )
        )
    return ft.Container(
        height=ROW_HEIGHT,
        ink=on_click is not None,
        on_click=(lambda _: on_click()) if on_click is not None else None,
        padding=ft.Padding.symmetric(horizontal=ROW_SIDE),
        content=ft.Row(
            # ⚠️ `spacing=0`：Row 默认留 10px，值那一列会比卡片右边缘偏左一截。
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=controls,
        ),
    )


def value_row(
    label: str,
    value: str,
    hint: str,
    on_click: Callable[[], None],
) -> ft.Container:
    """「生日信息 ｜ 选择你的生日 ›」这种：右边是值（没选过就浅灰占位）+ 一个 ›。"""
    return row(
        label,
        ft.Row(
            tight=True,
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    value or hint,
                    size=LABEL_SIZE,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    color=LABEL_COLOR if value else PLACEHOLDER_COLOR,
                ),
                ft.Icon(
                    ft.Icons.CHEVRON_RIGHT, size=CHECK_SIZE, color=CHEVRON_COLOR
                ),
            ],
        ),
        on_click,
    )


def switch_row(
    label: str,
    value: bool,
    on_change: Callable[[ft.Event[ft.Switch]], None],
) -> ft.Container:
    """「展示生日标签」+ 右侧一枚开关（开时红轨道白豆，关时浅灰）。"""
    return row(
        label,
        ft.Switch(
            value=value,
            # 红色轨道 + 白豆，照那张图（和设置页那个云端开关一个写法）。
            active_color="#FFFFFF",
            active_track_color=ACCENT_RED,
            inactive_thumb_color="#FFFFFF",
            inactive_track_color="#E2E8F0",
            on_change=on_change,
        ),
    )


def choice_row(
    label: str,
    selected: bool,
    on_click: Callable[[], None],
) -> ft.Container:
    """单选行：右边一枚红勾；没选中就什么都不画（照性别那张图）。"""
    return row(
        label,
        ft.Icon(
            ft.Icons.CHECK,
            size=CHECK_SIZE,
            color=ACCENT_RED,
            visible=selected,
        ),
        on_click,
    )


def section_label(text: str) -> ft.Control:
    """卡片上方那行小灰字（「是否公开展示」）。"""
    return ft.Container(
        padding=ft.Padding.only(left=4, top=4),
        content=ft.Text(text, size=SECTION_SIZE, color=SECTION_COLOR),
    )


def card(rows: list[ft.Control]) -> ft.Control:
    """一张白卡片：几行 + 行之间一条浅灰细线（左右各缩进 `ROW_SIDE`）。"""
    controls: list[ft.Control] = []
    for index, item in enumerate(rows):
        if index:
            controls.append(
                ft.Container(
                    height=1,
                    bgcolor=DIVIDER_COLOR,
                    margin=ft.Margin.only(left=ROW_SIDE, right=ROW_SIDE),
                )
            )
        controls.append(item)
    return ft.Container(
        bgcolor=CARD_BG,
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(tight=True, spacing=0, controls=controls),
    )


def build_shell(header: ft.Control, body: ft.Control) -> ft.Control:
    """二级页的整页外壳：浅灰底 + 安全区 + 顶栏 + 可滚的内容。

    底边留 `BOTTOM_MENU_INSET`：这一层是二级页、底栏已收起，但内容滚到底时留出这段
    空白，和别的二级页一致（最后一张卡片不会紧贴屏幕下边缘）。
    """
    return ft.Container(
        expand=True,
        bgcolor=PAGE_BG,
        content=ft.SafeArea(
            expand=True,
            content=ft.Column(
                expand=True,
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Container(
                        padding=ft.Padding.only(
                            left=CARD_SIDE, right=CARD_SIDE, top=6, bottom=6
                        ),
                        content=header,
                    ),
                    ft.ListView(
                        expand=True,
                        spacing=CARD_GAP,
                        scroll=ft.ScrollMode.HIDDEN,
                        padding=ft.Padding.only(
                            left=CARD_SIDE,
                            right=CARD_SIDE,
                            top=6,
                            bottom=BOTTOM_MENU_INSET,
                        ),
                        controls=[body],
                    ),
                ],
            ),
        ),
    )
