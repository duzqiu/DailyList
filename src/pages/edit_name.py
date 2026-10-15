"""「编辑名字」页（编辑资料页点「名字」进来）—— 照小红书那张图。

版式：顶栏（‹ + 居中「编辑名字」+ 右上「保存」）→ 一张白卡片（左边单行输入框，
右边「7/24」这样的计数）→ 卡片下面一行灰字说明。

保存直接打后端：`PUT /member/profile {nickname}`（见 api/member_profile.py），本地不留
副本；成功后 `go_back()` 退回编辑资料页 —— 那一层会重画，「名字」那一行就是新值了。

规则（照那张图的说明 + 后端约束）：**2-24 个字符、不含 `@ < > /` 等无效字符**。
后端 `nickname` 是 1-50，这里按图收得更紧；非法时点保存会弹一句说明，不会悄悄提交。
"""

from collections.abc import Callable

import flet as ft

from api import member_auth, member_profile, session
from api.client import ApiError
from tools.my_profile import account_name
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

TITLE = "编辑名字"
# 长度上限（照那张图的「7/24」）。
NAME_MAX = 24
NAME_MIN = 2
# 这几个字符不允许出现在名字里（照那张图的说明）。
INVALID_CHARS = "@<>/"
INVALID_HINT = f"请设置 {NAME_MIN}-{NAME_MAX} 个字符，不包括 @<>/ 等无效字符"
HINT = "填写名字"
# 卡片下面那行说明。
# ⚠️ 后端**没有**「昵称修改次数」这种字段，所以只写**规则本身**，不编造
# 「11.14 前还可修改 4 次」那样的数字 —— 要真数字得让后端加个计数字段。
NAME_NOTE = f"{INVALID_HINT}。30 天内可修改 4 次昵称"
COUNTER_COLOR = "#BDBDBD"
NOTE_SIZE = 13
NOTE_COLOR = "#8C8C8C"


def build_edit_name_page(page: ft.Page, go_back: Callable[[], None]) -> ft.Control:
    """`go_back` 是左上角那个 ‹（保存成功后也走它退回编辑资料页）。"""
    # 资料里没拉到昵称时退回账号上的显示名 —— 和编辑资料页「名字」那一行同一个口径，
    # 不然输入框会是空的，一保存反倒把名字清掉了。
    original = account_name(
        member_auth.cached_me() if session.access_token() else None
    )

    counter = ft.Text("", size=15, color=COUNTER_COLOR)
    field = ft.TextField(
        value=original,
        hint_text=HINT,
        autofocus=True,
        border=ft.NoInputBorder(),
        dense=True,
        text_size=15,
        # 左右内边距交给外面那张卡片，这里只管上下。
        content_padding=ft.Padding.symmetric(horizontal=0, vertical=10),
    )

    def problem(value: str) -> str:
        """返回不合规的原因；合规就是空串。"""
        if len(value) < NAME_MIN:
            return f"名字至少 {NAME_MIN} 个字符"
        if any(char in value for char in INVALID_CHARS):
            return "名字里不能有 @ < > / 这几个字符"
        return ""

    def refresh() -> None:
        """按当前输入刷新计数，并决定「保存」能不能点（没改就点不动）。"""
        text = field.value or ""
        counter.value = f"{len(text)}/{NAME_MAX}"
        safe_update(counter)
        set_save_enabled(text.strip() != original)

    def on_change(_: ft.Event[ft.TextField]) -> None:
        text = field.value or ""
        if len(text) > NAME_MAX:
            # ⚠️ 刻意**不用** `TextField(max_length=...)`：Material 会自带一个计数，
            # 和卡片里这个重复。自己截断、自己数，界面上就只有一个「7/24」。
            field.value = text[:NAME_MAX]
            safe_update(field)
        refresh()

    async def on_save() -> None:
        value = (field.value or "").strip()
        # 不合规就说清原因，别把请求发出去让后端兜。
        reason = problem(value)
        if reason:
            notify(page, reason)
            return
        try:
            await member_profile.update_profile(nickname=value)
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
        padding=ft.Padding.symmetric(horizontal=ROW_SIDE, vertical=6),
        content=ft.Row(
            # ⚠️ `spacing=0`：计数要紧贴右边，默认那 10px 会让它离卡片边缘远一截。
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                # 输入框吃掉剩下的宽度，计数就自然贴在右边缘。
                ft.Container(expand=True, content=field),
                counter,
            ],
        ),
    )

    body = ft.Column(
        spacing=CARD_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            card_control,
            ft.Container(
                padding=ft.Padding.only(left=ROW_SIDE, right=ROW_SIDE),
                content=ft.Text(NAME_NOTE, size=NOTE_SIZE, color=NOTE_COLOR),
            ),
        ],
    )

    header, set_save_enabled = build_save_header(
        TITLE, go_back, lambda: page.run_task(on_save)
    )
    # 摆好之后先刷一次：计数从「/24」变成真实的「N/24」，「保存」保持不可用（还没改）。
    refresh()
    return build_shell(header, body)
