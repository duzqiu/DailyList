"""「编辑资料」页（「我的」页右上角「编辑主页」进来）—— 照小红书那一页复刻。

自上而下：顶栏（‹ 返回 + 居中「编辑资料」+ 右上「预览」）→ 居中头像（右下角一枚相机角标）
→ 四张白卡片：

    ① 名字 / 小红书号 / 背景图
    ② 简介
    ③ 性别 / 生日 / 地区 / 职业 / 学校 / 原创信息
    ④ 组件管理

每行都是「标签 ｜ 值 ｜ ›」；值没填过就摆**浅灰占位**（「选择生日」这种）。卡片之间留一条
缝、行与行之间一条浅灰细线（左右各缩进一点）—— 都是照那张图量的。

点的行为：
- 名字 / 小红书号 / 简介 → 弹输入框（存本地，见 tools/my_profile.py）；
- 头像 → 选图后**复制进 App 目录**再存（同背景图那套）；
- 背景图 → 「换背景图」那一页（`open_background`，压在**这一页之上**，返回回到这儿）；
- 性别 → 三个选项的弹窗；生日 → 项目自带的日期选择器（widgets/pickers.py）；
- 地区 / 职业 / 学校 / 原创信息 / 组件管理 / 预览 → 还没做，点了给一句提示 ——
  ⚠️ 别在这儿摆死按钮，等真做的时候再把回调换掉。

⚠️ 选图器**不能在这一页新建**：Service 只有在「页面首次发给客户端之前」注册才到得了客户端
（见 widgets/services.py 开头那两条），所以用 `ensure_service` 取 `main()` 里注册好的那个。
"""

from collections.abc import Callable
from datetime import date

import flet as ft

from api import member_auth, session
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
    GENDERS,
    INTRO_HINT,
    account_id,
    account_name,
    avatar_path,
    birthday,
    gender,
    intro,
    set_avatar,
    set_birthday,
    set_gender,
    set_intro,
    set_name,
    set_xhs_id,
    store_avatar,
)
from widgets.pickers import build_date_picker
from widgets.services import ensure_service
from widgets.toast import build_toast

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
) -> ft.Control:
    """`go_back` 是左上角那个 ‹；`open_background` 是「背景图」那一行。"""

    def soon(feature: str) -> None:
        """还没做的那些：给一句人话，别点了没反应。"""
        page.show_dialog(build_toast(page, f"{feature}：暂未开放"))

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
    ) -> ft.Control:
        """一行：标签（定宽）+ 值（或浅灰占位）+ ›。

        `thumb` **不是 `None`** 就摆一个缩略图格子（「背景图」那一行是这么用的）——
        图没设过时它就是个浅灰空格子，比行里空着好看，和头像那块一个观感。
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
            value_control = ft.Text(
                # 没填过就摆占位文案，颜色浅一档。
                value or hint,
                size=VALUE_SIZE,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                color=VALUE_COLOR if value else PLACEHOLDER_COLOR,
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

    # ---------------------- 改名 / 改号 / 简介：弹输入框 ----------------------

    def edit_text(
        *,
        title: str,
        value: str,
        hint: str,
        on_save: Callable[[str], None],
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
            on_save((field.value or "").strip())
            page.pop_dialog()
            render()
            page.update()
            page.show_dialog(build_toast(page, "已保存"))

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

    # ---------------------- 性别：三个选项 ----------------------

    def pick_gender() -> None:
        current = gender()

        def choose(value: str) -> None:
            set_gender(value)
            page.pop_dialog()
            render()
            page.update()
            page.show_dialog(build_toast(page, f"性别：{value}"))

        def option(value: str) -> ft.Control:
            return ft.Container(
                height=44,
                ink=True,
                on_click=lambda _, picked=value: choose(picked),
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(value, size=15, color=VALUE_COLOR),
                        ft.Container(expand=True),
                        ft.Icon(
                            ft.Icons.CHECK,
                            size=18,
                            color=VALUE_COLOR,
                            visible=value == current,
                        ),
                    ],
                ),
            )

        dialog = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
            bgcolor=DIALOG_SURFACE,
            title=ft.Text(
                "性别", size=15, weight=ft.FontWeight.BOLD, color=TITLE_COLOR
            ),
            content=ft.Column(
                tight=True,
                spacing=0,
                width=240,
                controls=[option(value) for value in GENDERS],
            ),
            actions=[
                ft.TextButton(
                    "取消",
                    style=dialog_button_style(),
                    on_click=lambda _: page.pop_dialog(),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    # ---------------------- 生日：项目自带的日期选择器 ----------------------

    def pick_birthday() -> None:
        try:
            current = date.fromisoformat(birthday())
        except ValueError:
            current = date(2000, 1, 1)

        def chosen(day: date) -> None:
            set_birthday(day.isoformat())
            render()
            page.update()
            page.show_dialog(build_toast(page, f"生日：{birthday_text()}"))

        page.show_dialog(
            build_date_picker(
                current,
                chosen,
                first_date=date(1900, 1, 1),
                last_date=date.today(),
            )
        )

    # ---------------------- 头像：选图 → 复制进 App 目录 ----------------------

    def pick_avatar() -> None:
        # ⚠️ 取启动时注册好的那个（本页新建服务客户端收不到，见文件头）。
        picker = ensure_service(page, ft.FilePicker)

        async def pick_and_apply() -> None:
            try:
                files = await picker.pick_files(
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.IMAGE,
                )
            except Exception as error:  # noqa: BLE001
                page.show_dialog(build_toast(page, f"打不开相册：{error}"))
                return
            path = getattr(files[0], "path", "") if files else ""
            if not path:
                page.show_dialog(build_toast(page, "没有选到图片"))
                return
            set_avatar(store_avatar(path))
            render()
            page.update()
            page.show_dialog(build_toast(page, "已更换头像"))

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
        avatar_holder.content = avatar_block()
        groups.controls = [
            card(
                [
                    # 没登录 / 没同步到账号时这两行是空的 —— 给个浅灰占位，
                    # 别留两行空白（登录了就是账号里的值）。
                    row(
                        "名字",
                        account_name(account),
                        lambda: edit_text(
                            title="修改名字",
                            value=account_name(account),
                            hint="好名字是朋友记住你的第一步",
                            on_save=set_name,
                        ),
                        hint="填写名字",
                    ),
                    row(
                        "小红书号",
                        account_id(account),
                        lambda: edit_text(
                            title="修改小红书号",
                            value=account_id(account),
                            hint="数字 / 字母都可以",
                            on_save=set_xhs_id,
                        ),
                        hint="填写小红书号",
                    ),
                    # 缩略图格子（没设过背景图就是浅灰空格子，不是空白）。
                    row("背景图", "", open_background, thumb=background_path()),
                ]
            ),
            card(
                [
                    row(
                        "简介",
                        intro(),
                        lambda: edit_text(
                            title="编辑简介",
                            value=intro(),
                            hint=INTRO_HINT,
                            on_save=set_intro,
                            multiline=True,
                        ),
                        hint=INTRO_HINT,
                    )
                ]
            ),
            card(
                [
                    row(
                        "性别",
                        gender(),
                        pick_gender,
                        hint="选择性别",
                    ),
                    row(
                        "生日",
                        birthday_text(),
                        pick_birthday,
                        hint="选择生日",
                    ),
                    row("地区", "", lambda: soon("地区"), hint="选择所在的地区"),
                    row("职业", "", lambda: soon("职业"), hint="选择职业"),
                    row("学校", "", lambda: soon("学校"), hint="选择学校"),
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

    render()

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
