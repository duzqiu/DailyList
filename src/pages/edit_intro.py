"""「编辑简介」页（编辑资料页点「简介」进来）—— 照小红书那张图。

版式：顶栏（‹ + 居中「编辑简介」+ 右上「保存」）→ 一张白卡片（多行输入 + 右下角
「0/160」计数）→ 卡片下面一行灰字说明。

保存直接打后端：`PUT /member/profile {bio}`（见 api/member_profile.py），本地不留副本；
成功后 `go_back()` 退回编辑资料页 —— 那一层会重画，「简介」那一行就是新值了。
"""

from collections.abc import Callable

import flet as ft

from api import member_profile
from api.client import ApiError
from tools.my_profile import INTRO_HINT, intro
from widgets.field_page import (
    CARD_BG,
    CARD_GAP,
    CARD_RADIUS,
    ROW_SIDE,
    build_save_header,
    build_shell,
    notify,
)
from widgets.layout import safe_update

TITLE = "编辑简介"
# 简介长度上限（照那张图的「0/160」）。后端 `bio` 的上限是 255，这里收得更紧。
INTRO_MAX = 160
FIELD_MIN_LINES = 5
FIELD_MAX_LINES = 8
COUNTER_SIZE = 13
COUNTER_COLOR = "#BDBDBD"
NOTE_SIZE = 13
NOTE_COLOR = "#8C8C8C"
# 卡片下面那行说明。
# ⚠️ 后端**没有**「简介修改次数」这种字段（`MemberProfileUpdate` 只有昵称 / 头像 /
# 背景 / 性别 / 生日 / 电话 / 简介 / 地区），所以这里只写**规则本身**，不编造
# 「10.22 前还可修改 8 次」那样的数字 —— 要真数字得让后端加个计数字段。
INTRO_NOTE = "7 天内可修改 10 次简介"


def build_edit_intro_page(page: ft.Page, go_back: Callable[[], None]) -> ft.Control:
    """`go_back` 是左上角那个 ‹（保存成功后也走它退回编辑资料页）。"""
    original = intro()

    counter = ft.Text("", size=COUNTER_SIZE, color=COUNTER_COLOR)
    field = ft.TextField(
        value=original,
        hint_text=INTRO_HINT,
        multiline=True,
        min_lines=FIELD_MIN_LINES,
        max_lines=FIELD_MAX_LINES,
        autofocus=True,
        border=ft.NoInputBorder(),
        dense=True,
        text_size=15,
        # 左右内边距交给外面那张卡片，这里只管上下。
        content_padding=ft.Padding.symmetric(horizontal=0, vertical=8),
    )

    def refresh() -> None:
        """按当前输入刷新计数，并决定「保存」能不能点（没改就点不动）。"""
        text = field.value or ""
        counter.value = f"{len(text)}/{INTRO_MAX}"
        safe_update(counter)
        set_save_enabled(text.strip() != original)

    def on_change(_: ft.Event[ft.TextField]) -> None:
        text = field.value or ""
        if len(text) > INTRO_MAX:
            # ⚠️ 刻意**不用** `TextField(max_length=...)`：Material 会自带一个计数，
            # 和卡片里这个重复。自己截断、自己数，界面上就只有一个「0/160」。
            field.value = text[:INTRO_MAX]
            safe_update(field)
        refresh()

    async def on_save() -> None:
        try:
            await member_profile.update_profile(bio=(field.value or "").strip())
        except ApiError as error:
            notify(page, error.message)
            return
        go_back()
        notify(page, "已保存")

    # 先建控件、再挂 `on_change`（构建时就求值的写法要求处理函数已经定义好）。
    field.on_change = on_change

    card_control = ft.Container(
        bgcolor=CARD_BG,
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        padding=ft.Padding.all(ROW_SIDE),
        content=ft.Column(
            tight=True,
            spacing=0,
            controls=[
                field,
                # 计数贴在卡片右下角（照那张图）。
                ft.Row(alignment=ft.MainAxisAlignment.END, controls=[counter]),
            ],
        ),
    )

    body = ft.Column(
        spacing=CARD_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            card_control,
            ft.Container(
                padding=ft.Padding.only(left=4, right=4),
                content=ft.Text(INTRO_NOTE, size=NOTE_SIZE, color=NOTE_COLOR),
            ),
        ],
    )

    header, set_save_enabled = build_save_header(
        TITLE, go_back, lambda: page.run_task(on_save)
    )
    # 摆好之后先刷一次：计数从「/160」变成真实的「N/160」，「保存」保持不可用（还没改）。
    refresh()
    return build_shell(header, body)
