"""「编辑资料」页（「我的」页右上角「编辑主页」进来）—— 照小红书那一页复刻。

自上而下：顶栏（‹ 返回 + 居中「编辑资料」+ 右上「预览」）→ 居中头像（右下角一枚相机角标）
→ 四张白卡片：

    ① 名字 / 小红书号 / 背景图
    ② 简介
    ③ 性别 / 生日 / 地区 / 原创信息
    ④ 组件管理

每行都是「标签 ｜ 值 ｜ ›」；值没填过就摆**浅灰占位**（「选择生日」这种）。卡片之间留一条
缝、行与行之间一条浅灰细线（左右各缩进一点）—— 都是照那张图量的。

点的行为：
- 名字 → **独立的一整页**（`open_name`，见 pages/edit_name.py；带字符计数和
  那张图的规则说明），压在**这一页之上**，返回回到这儿；
- 地区 → 弹输入框，**直接调后端** `PUT /member/profile`
  （见 api/member_profile.py；本地不存副本）；
- 头像 → 选图后**上传**到后端 `POST /member/profile/avatar`，后端按会员 ID 存
  （`data/uploads/avatars/{会员ID}/`）；显示用的是后端给的 `avatar_url`，
  **不再复制进 App 目录**（原来那种本地存法已去掉）；
- 背景图 → 「换背景图」那一页（`open_background`，压在**这一页之上**，返回回到这儿）；
- 简介 / 性别 / 生日 → 各自**独立的一整页**（`open_intro` / `open_gender` /
  `open_birthday`；同样压在这一页之上）—— 照小红书那三张图，改成整页而不是弹窗，
  见 pages/edit_intro.py、pages/edit_gender.py、pages/edit_birthday.py；
- 小红书号 = 会员号，后端**不支持改**，这一行只读（点了给一句说明）；
- 职业 / 学校：**按需求删掉了**（后端也没有这两个字段）；
- 原创信息 / 组件管理 / 预览 → 还没做，点了给一句提示。

⚠️ 选图器**不能在这一页新建**：Service 只有在「页面首次发给客户端之前」注册才到得了客户端
（见 widgets/services.py 开头那两条），所以用 `ensure_service` 取 `main()` 里注册好的那个。
"""

import logging
from collections.abc import Callable, Coroutine
from datetime import date
from typing import Any

import flet as ft

from api import member_auth, member_profile, session
from api.client import ApiError
from tools import image_prep
from widgets.layout import (
    BACK_WIDTH,
    BOTTOM_MENU_INSET,
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    build_back_button,
    dialog_button_style,
    track_keyboard,
)
from widgets.my_background import background_path
from tools.my_profile import (
    INTRO_HINT,
    account_id,
    account_name,
    avatar_path,
    birthday,
    gender,
    intro,
    region,
)
from widgets.services import ensure_service
from widgets.toast import build_toast

logger = logging.getLogger(__name__)

# 这一页的配色照那张图：浅灰底、白卡片、标签灰、值近黑、没填过的值更浅一档。
PAGE_BG = "#F5F5F5"
CARD_BG = "#FFFFFF"
CARD_RADIUS = 10
CARD_SIDE = 12
CARD_GAP = 10
ROW_HEIGHT = 52
ROW_SIDE = 16
LABEL_WIDTH = 104
LABEL_SIZE = 16
VALUE_SIZE = 16
LABEL_COLOR = "#666666"
VALUE_COLOR = "#1F1F1F"
PLACEHOLDER_COLOR = "#BDBDBD"
# 「简介」那一行**填过之后**用的灰（用户要求：简介也用灰字）。
# 比近黑的 `VALUE_COLOR` 弱、又比占位的 `PLACEHOLDER_COLOR` 深一档 ——
# 一眼能看出「填了」和「没填」，但那行字不会比别的字段更抢眼。
INTRO_VALUE_COLOR = "#9A9A9A"
CHEVRON_COLOR = "#C9C9C9"
DIVIDER_COLOR = "#F0F0F0"
TITLE_COLOR = "#1A1A1A"
TITLE_SIZE = 17
PREVIEW_SIZE = 15

AVATAR_SIZE = 88
AVATAR_BG = "#E9E9E9"
AVATAR_ICON_COLOR = "#9A9A9A"
BADGE_SIZE = 28
BADGE_BG = "#111111"
BADGE_ICON_SIZE = 15
THUMB_SIZE = 40
THUMB_RADIUS = 6

# 「原创信息」「组件管理」这两行的值（照那张图）—— 现在都还是固定的占位文案。
ORIGINAL_INFO = "暂未完成原创认证"
COMPONENT_INFO = "访客可见 群聊 等1个组件"


def build_edit_profile_page(
    page: ft.Page,
    go_back: Callable[[], None],
    open_background: Callable[[], None],
    open_name: Callable[[], None],
    open_intro: Callable[[], None],
    open_birthday: Callable[[], None],
    open_gender: Callable[[], None],
) -> ft.Control:
    """`go_back` 是左上角那个 ‹；后面几个回调各自对应一行，点开就压一页新的上来：

    `open_background` 换背景图页、`open_name` 编辑名字页、`open_intro` 编辑简介页、
    `open_gender` 编辑性别页、`open_birthday` 编辑生日页（都由 pages/navigation.py
    决定压在哪一层）。
    """

    def soon(feature: str) -> None:
        """还没做的那些：给一句人话，别点了没反应。"""
        page.show_dialog(build_toast(page, f"{feature}：暂未开放"))

    def notify(message: str) -> None:
        """一句话提示：走 widgets/toast.py，浮在屏幕正中。"""
        page.show_dialog(build_toast(page, message))

    async def save_profile(**fields: str | None) -> dict | None:
        """把改动交给后端（`PUT /member/profile`）。

        成功返回改后的资料（已经写进 api 层缓存）；失败把后端那句话弹出来并返回
        `None` —— 调用方据此决定要不要重画页面。
        """
        try:
            return await member_profile.update_profile(**fields)
        except ApiError as error:
            notify(error.message)
            return None

    def birthday_text() -> str:
        """生日这一行显示成「2001年5月20日」，没选过就给空（那行摆占位）。"""
        try:
            day = date.fromisoformat(birthday())
        except ValueError:
            return ""
        return f"{day.year}年{day.month}月{day.day}日"

    # ---------------------- 一行 ----------------------

    def row(
        label: str,
        value: str,
        on_click: Callable[[], None],
        *,
        hint: str = "",
        thumb: str | None = None,
        value_gray: bool = False,
    ) -> ft.Control:
        """一行：标签（定宽）+ 值（或浅灰占位）+ ›。

        `thumb` **不是 `None`** 就摆一个缩略图格子（「背景图」那一行是这么用的）——
        图没设过时它就是个浅灰空格子，比行里空着好看，和头像那块一个观感。

        `value_gray=True` 让**填过的值也用灰**（默认只有「没填过的占位」才是浅灰）——
        「简介」那一行用它（用户要求：简介比其它字段次要，用近黑太抢眼）。
        """
        if thumb is not None:
            value_control: ft.Control = ft.Container(
                width=THUMB_SIZE,
                height=THUMB_SIZE,
                border_radius=ft.BorderRadius.all(THUMB_RADIUS),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                bgcolor=AVATAR_BG,
                content=(
                    ft.Image(src=thumb, fit=ft.BoxFit.COVER, expand=True)
                    if thumb
                    else None
                ),
            )
        else:
            # 三种取色：没填过 → 浅灰占位；填了但这一行要弱化（`value_gray`）→ 中灰；
            # 其余 → 近黑（这一页的常态）。
            if not value:
                value_color = PLACEHOLDER_COLOR
            elif value_gray:
                value_color = INTRO_VALUE_COLOR
            else:
                value_color = VALUE_COLOR
            value_control = ft.Text(
                value or hint,
                size=VALUE_SIZE,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                color=value_color,
            )
        return ft.Container(
            height=ROW_HEIGHT,
            ink=True,
            on_click=lambda _: on_click(),
            padding=ft.Padding.symmetric(horizontal=ROW_SIDE),
            content=ft.Row(
                # ⚠️ `spacing=0`：Row 默认留 10px 间距，值列会比那张图偏右一截。
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=LABEL_WIDTH,
                        content=ft.Text(
                            label, size=LABEL_SIZE, color=LABEL_COLOR
                        ),
                    ),
                    # ⚠️ 这一格带 `alignment`：不带的话它会**把自己的子控件拉满**，
                    # 40x40 的缩略图会被抻成一条长条（踩过）。
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment.CENTER_LEFT,
                        content=value_control,
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        size=20,
                        color=CHEVRON_COLOR,
                    ),
                ],
            ),
        )

    def card(rows: list[ft.Control]) -> ft.Control:
        """一张白卡：几行 + 行之间一条浅灰细线（左右各缩进 `ROW_SIDE`）。"""
        controls: list[ft.Control] = []
        for index, item in enumerate(rows):
            if index:
                controls.append(
                    ft.Container(
                        height=1,
                        bgcolor=DIVIDER_COLOR,
                        margin=ft.Margin.only(
                            left=ROW_SIDE, right=ROW_SIDE
                        ),
                    )
                )
            controls.append(item)
        return ft.Container(
            bgcolor=CARD_BG,
            border_radius=ft.BorderRadius.all(CARD_RADIUS),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Column(tight=True, spacing=0, controls=controls),
        )

    # ---------------------- 头像（右下角一枚相机角标）---------------------

    def avatar_block() -> ft.Control:
        path = avatar_path()
        circle = ft.Container(
            width=AVATAR_SIZE,
            height=AVATAR_SIZE,
            border_radius=ft.BorderRadius.all(AVATAR_SIZE / 2),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=AVATAR_BG,
            alignment=ft.Alignment.CENTER,
            content=(
                ft.Image(src=path, fit=ft.BoxFit.COVER, expand=True)
                if path
                else ft.Icon(
                    ft.Icons.PERSON,
                    size=AVATAR_SIZE * 0.5,
                    color=AVATAR_ICON_COLOR,
                )
            ),
        )
        badge = ft.Container(
            width=BADGE_SIZE,
            height=BADGE_SIZE,
            border_radius=ft.BorderRadius.all(BADGE_SIZE / 2),
            bgcolor=BADGE_BG,
            # 一圈白描边：角标压在头像边上，没有这圈会糊在一起。
            border=ft.Border.all(2, CARD_BG),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(
                ft.Icons.PHOTO_CAMERA,
                size=BADGE_ICON_SIZE,
                color="#FFFFFF",
            ),
        )
        return ft.Container(
            alignment=ft.Alignment.CENTER,
            ink=True,
            tooltip="更换头像",
            on_click=lambda _: pick_avatar(),
            padding=ft.Padding.only(bottom=CARD_GAP),
            content=ft.Stack(
                width=AVATAR_SIZE,
                height=AVATAR_SIZE,
                controls=[
                    circle,
                    # 稍微压出头像一点（照那张图）。
                    ft.Container(right=-2, bottom=-2, content=badge),
                ],
            ),
        )

    # ---------------------- 地区：弹输入框 ----------------------

    def edit_text(
        *,
        title: str,
        value: str,
        hint: str,
        on_save: Callable[[str], Coroutine[Any, Any, None]],
        multiline: bool = False,
    ) -> None:
        field = ft.TextField(
            value=value,
            hint_text=hint,
            autofocus=True,
            multiline=multiline,
            min_lines=3 if multiline else 1,
            max_lines=5 if multiline else 1,
            border=ft.NoInputBorder(),
            dense=True,
            text_size=15,
            content_padding=ft.Padding.symmetric(horizontal=0, vertical=8),
        )

        def save(_: ft.Event[ft.TextButton]) -> None:
            # 保存要打接口：`on_save` 是协程函数，交给 run_task 跑，别卡住 UI；
            # 提示由它自己弹（成功 / 失败各一句），这里只管把弹窗收掉。
            page.pop_dialog()
            page.run_task(on_save, (field.value or "").strip())

        dialog = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
            bgcolor=DIALOG_SURFACE,
            title=ft.Text(
                title,
                size=15,
                weight=ft.FontWeight.BOLD,
                color=TITLE_COLOR,
            ),
            content=ft.Container(width=280, content=field),
            actions=[
                ft.TextButton(
                    "取消",
                    style=dialog_button_style(),
                    on_click=lambda _: page.pop_dialog(),
                ),
                ft.TextButton("保存", style=dialog_button_style(), on_click=save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        # 输入框弹键盘时把弹窗顶上去（项目里所有带输入框的弹窗都这么干）。
        track_keyboard(page, dialog)
        page.show_dialog(dialog)

    # ---------------------- 头像：选图 → 上传到后端 ----------------------

    def pick_avatar() -> None:
        """换头像：选一张图 → `POST /member/profile/avatar`。

        后端按**会员 ID** 存（`data/uploads/avatars/{会员ID}/`，一个会员一个目录，
        覆盖时旧的会被清掉），**不再往 App 目录里复制**（原来的本地存法已去掉）。
        上传成功后重新拉一次资料（拿到新的 `avatar_url`）再重画 —— 文件名带随机串，
        不会显示到缓存里的旧图。
        """
        # ⚠️ 取启动时注册好的那个（本页新建服务客户端收不到，见文件头）。
        picker = ensure_service(page, ft.FilePicker)

        async def pick_and_apply() -> None:
            try:
                # ⚠️ `with_data=True` 是关键：这样 `FilePickerFile.bytes` 才会带上
                # **文件内容**。只拿 `path` 是不够的 —— Web 模式下它永远是 None、
                # 部分原生平台也给不出来，按路径读就会「读不到选中的图片」。
                # `compression_quality` 则是给 **iOS** 用的：iPhone 相机默认拍 HEIC，
                # 带上它选图器会直接给一份 JPEG（顺带压小），后端也兜了一层转码。
                files = await picker.pick_files(
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.IMAGE,
                    with_data=True,
                    compression_quality=image_prep.PICKER_QUALITY,
                )
            except Exception as error:  # noqa: BLE001
                notify(f"打不开相册：{error}")
                return
            picked = files[0] if files else None
            if picked is None:
                notify("没有选到图片")
                return
            notify("正在上传头像…")
            try:
                # 传**选择器给的那个对象**：它带着文件内容（with_data=True）与原始
                # 文件名（后端靠后缀判断图片格式）。api 层优先用内容上传，
                # 只有内容缺失时才回退到按路径读（见 api/member_profile.py）。
                await member_profile.upload_avatar(picked)
            except ApiError as error:
                notify(error.message)
                return
            except Exception as error:  # noqa: BLE001
                # 兜住一切意外：任务里抛异常会让整个 App 崩掉，这里至少要留住界面
                # 并给一句人话（选图 / 压缩 / 上传任何一步出问题都算）。
                logger.exception("上传头像失败")
                notify(f"上传失败：{error}")
                return
            render()
            page.update()
            notify("已更换头像")

        page.run_task(pick_and_apply)

    # ---------------------- 装配 ----------------------

    avatar_holder = ft.Container()
    groups = ft.Column(
        spacing=CARD_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[],
    )

    def render() -> None:
        """按当前资料重建头像块与四张卡片（改完任何一项都叫它一次）。"""
        account = (
            member_auth.cached_me() if session.access_token() else None
        )

        async def save_region(value: str) -> None:
            if await save_profile(region=value) is None:
                return
            render()
            page.update()
            notify("已保存")

        avatar_holder.content = avatar_block()
        groups.controls = [
            card(
                [
                    # 没登录 / 没同步到账号时这两行是空的 —— 给个浅灰占位，
                    # 别留两行空白（登录了就是账号里的值）。
                    row(
                        "名字",
                        account_name(account),
                        open_name,
                        hint="填写名字",
                    ),
                    # 会员号是注册时生成的、后端不给改 —— 这一行只读，点了说明一下。
                    row(
                        "小红书号",
                        account_id(account),
                        lambda: notify("小红书号就是会员号，由系统生成，暂不支持修改"),
                        hint="登录后自动生成",
                    ),
                    # 缩略图格子（没设过背景图就是浅灰空格子，不是空白）。
                    row("背景图", "", open_background, thumb=background_path()),
                ]
            ),
            card(
                [
                    # 「简介」单独一张卡，点开是一整页（`open_intro`）。
                    # 「简介」填过之后也用灰字（用户要求），见 `INTRO_VALUE_COLOR`。
                    row(
                        "简介",
                        intro(),
                        open_intro,
                        hint=INTRO_HINT,
                        value_gray=True,
                    )
                ]
            ),
            card(
                [
                    row(
                        "性别",
                        gender(),
                        open_gender,
                        hint="选择性别",
                    ),
                    row(
                        "生日",
                        birthday_text(),
                        open_birthday,
                        hint="选择生日",
                    ),
                    row(
                        "地区",
                        region(),
                        lambda: edit_text(
                            title="填写地区",
                            value=region(),
                            hint="例如：杭州",
                            on_save=save_region,
                        ),
                        hint="选择所在的地区",
                    ),
                    row("原创信息", ORIGINAL_INFO, lambda: soon("原创认证")),
                ]
            ),
            card(
                [row("组件管理", COMPONENT_INFO, lambda: soon("组件管理"))]
            ),
        ]

    def top_bar() -> ft.Control:
        """顶栏：‹ 返回 + 居中「编辑资料」+ 右上「预览」（和返回键等宽，标题才在正中）。"""
        return ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                build_back_button(go_back),
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "编辑资料",
                        size=TITLE_SIZE,
                        weight=ft.FontWeight.BOLD,
                        color=TITLE_COLOR,
                    ),
                ),
                ft.Container(
                    width=BACK_WIDTH,
                    alignment=ft.Alignment.CENTER_RIGHT,
                    ink=True,
                    tooltip="预览",
                    on_click=lambda _: page.show_dialog(
                        build_toast(page, "预览：访客看到的就是「我的」页")
                    ),
                    content=ft.Text(
                        "预览", size=PREVIEW_SIZE, color=TITLE_COLOR
                    ),
                ),
            ],
        )

    async def load_profile() -> None:
        """进页面先把资料拉回来（缓存里有就不打接口）。

        没登录就什么都不做 —— 这一页照样能开（值都是空的、摆占位），只是改不动。
        """
        if not session.access_token():
            return
        try:
            await member_profile.get_profile()
        except ApiError as error:
            notify(error.message)
            return
        render()
        page.update()

    render()
    # 资料还没拉过（比如刚启动、令牌是恢复出来的）就补一次，拉到后重画。
    if session.access_token() and member_profile.cached_profile() is None:
        page.run_task(load_profile)

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
                        content=top_bar(),
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
                        controls=[avatar_holder, groups],
                    ),
                ],
            ),
        ),
    )
