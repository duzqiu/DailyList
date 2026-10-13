"""登录 / 注册 / 忘记密码这三页共用的表单骨架。

三页除了「有哪些字段、按钮点了做什么」，其余是同一套：渐变底 + `SafeArea` + 左右 24
的内边距、顶栏「‹ 返回」+ 居中标题、卡片、等高的输入框、整宽的主按钮、卡片下面那行
小字链接；表单整体**偏上**摆，而且位置是固定的 —— 键盘升起、视口被压矮时它不会跟着
往上挤（见 `FORM_TOP_RATIO`）。

**没有底色**：卡片和输入框都是透明的，范围由一圈浅灰细边示意（`CARD_BORDER`）——
底色去掉后整页只剩白到靛蓝的渐变，边界全靠这两圈线。输入框另钉了统一高度
（`FIELD_HEIGHT`），外层小框和里面的输入框同高，文字因此落在格子的正中间。

抽到这儿是因为 README 约定 12（能共享的都放 tools/，别重复造控件）—— 三页将来一起
调样式时只有这一处要动；页面自己只管字段和动作。

配色全部取自 tools/layout.py 已经给出的那几档，这里不新起颜色：边线是设置页卡片边框
那一档浅灰，主按钮的底色就是首页日期条 / 日历格子那档「选中」的蓝，字色是全 App 的
深蓝（这个底色够浅，按 `readable_ink` 的判断本来就该配深字）。
"""

import asyncio
from collections.abc import Callable

import flet as ft

from tools.layout import (
    DATE_SELECTED_BG,
    SUBPAGE_TITLE_COLOR,
    build_subpage_header,
    page_gradient,
)

# 唯一的线色：卡片外围那一圈、以及每个输入框那一圈，都用它 —— 没有底色之后，
# 「范围」只能靠这道浅灰细边说清楚。
CARD_BORDER = "#E2E8F0"
TITLE_COLOR = SUBPAGE_TITLE_COLOR
MUTED_COLOR = "#64748B"
FIELD_COLOR = "#334155"
HINT_COLOR = "#94A3B8"
PAGE_SIDE_PADDING = 24
# 卡片顶上那枚头像（只有登录页用）：原图再缩到圆的 0.6，四周留一圈才像头像。
AVATAR_SIZE = 56
AVATAR_ICON_RATIO = 0.6
TITLE_SIZE = 15
SUBTITLE_SIZE = 11
FIELD_TEXT_SIZE = 13
# 所有输入框都是这个高度：外层小框和里面的输入框同高（见 build_field_box），
# 一列字段等高，文字也落在格子正中。
FIELD_HEIGHT = 40
FIELD_RADIUS = 8
FIELD_SIDE_PADDING = 12
# 密码框右边那枚「显示 / 隐藏」自带内边距，右侧只留这么一点，让它贴到框的后端。
FIELD_TRAILING_INSET = 4
BUTTON_HEIGHT = 42
BUTTON_TEXT_SIZE = 14
# 卡片里图片与文字之间、字段与按钮之间的统一间距。
CARD_SPACING = 12
CARD_PADDING_X = 16
CARD_PADDING_Y = 14
CARD_RADIUS = 12
# 表单区离顶栏的距离：按**窗口高度**的比例取（`page.height` 在页面构建时就有了），
# 不是按「剩余可用高度」分配。键盘升起时视口会被压矮，用后者算出来的位置会跟着往上
# 跑 —— 那就是「弹键盘整页往上挤」。这里定成固定像素，构建完就不再变。
# 比例给得比较小（约等于从顶部 13% 处起），表单整体落在中上偏上的位置。
FORM_TOP_RATIO = 0.13
FORM_TOP_MIN = 96.0
# 「获取验证码」那枚小按钮的三种文案：初始 → 倒计时中（`{n}` 是剩余秒数）→ 可重发。
CODE_SEND_LABEL = "获取验证码"
CODE_RESEND_LABEL = "重新发送"
# 刻意和「获取验证码」差不多长（都是 5-6 个字），倒计时开始 / 结束时按钮不会跳宽。
CODE_COUNTDOWN_LABEL = "{n}s 后重发"
# 点一次锁多少秒：期间点了不响应，归零后恢复（见 start_code_countdown）。
CODE_COUNTDOWN_SECONDS = 60


def build_auth_field(hint: str, password: bool = False) -> ft.TextField:
    """一个表单字段：和新增待办、通知地址同一个写法（无边框、单行、13pt）。

    密码那格用 `password=True`，右边的「显示 / 隐藏」交给 `can_reveal_password`
    —— Material 自己那枚眼睛，不用另画一个。

    高度直接钉在输入框上（和设置页通知地址那一格一个做法），并显式要求**文字垂直
    居中**：Flet 的 `text_vertical_align` 默认是 `None`（等同顶部对齐），只钉高度、
    不写这一项的话文字仍然贴在上边 —— 这是真的踩过一次。
    """
    return ft.TextField(
        hint_text=hint,
        hint_style=ft.TextStyle(size=FIELD_TEXT_SIZE, color=HINT_COLOR),
        password=password,
        can_reveal_password=password,
        # 这几页都是单行字段：不给它长高的余地（`multiline` 默认就是 False，
        # 写出来是防以后被改成 True）。
        multiline=False,
        height=FIELD_HEIGHT,
        text_vertical_align=ft.VerticalAlignment.CENTER,
        filled=False,
        border=ft.NoInputBorder(),
        content_padding=ft.Padding.symmetric(horizontal=0, vertical=6),
        text_style=ft.TextStyle(size=FIELD_TEXT_SIZE, color=FIELD_COLOR),
        dense=True,
    )


def build_field_box(field: ft.TextField) -> ft.Control:
    """把无边框的输入框套进一圈浅灰细边里，高度统一取 `FIELD_HEIGHT`。

    没有底色（背景色去掉了），范围靠这圈线示意。密码框右边那枚「显示 / 隐藏」是控件
    自带的 suffix，右侧内边距收窄到 `FIELD_TRAILING_INSET`，让它贴住框的后端；
    其余字段左右一样宽，文字看着才对称。
    """
    trailing = bool(getattr(field, "password", False)) or bool(
        getattr(field, "can_reveal_password", False)
    )
    return ft.Container(
        height=FIELD_HEIGHT,
        padding=ft.Padding.only(
            left=FIELD_SIDE_PADDING,
            right=FIELD_TRAILING_INSET if trailing else FIELD_SIDE_PADDING,
        ),
        border_radius=ft.BorderRadius.all(FIELD_RADIUS),
        border=ft.Border.all(1, CARD_BORDER),
        content=field,
    )


def build_code_row(
    field: ft.TextField,
    on_send: Callable[[ft.Event[ft.Control]], None],
) -> tuple[ft.Control, ft.Control]:
    """验证码那一行：输入框占满剩余宽度，右边跟上「获取验证码」。

    返回 `(整行, 那枚按钮)` —— 按钮要留个引用，倒计时由 `start_code_countdown` 跑。
    注册页（邮箱验证码）和忘记密码页都用这一行，样式与行为保持一致。

    这枚按钮是 `Container` 画的（不是 Button），没有真的「不可点」状态：倒计时期间
    拿 `button.data` 当锁，点了直接不理 —— 文案里已经在报剩余秒数，看得出来。
    """

    def guarded(event: ft.Event[ft.Control]) -> None:
        if button.data:
            return
        on_send(event)

    button = build_link(CODE_SEND_LABEL, guarded)
    button.data = False  # False = 没在倒计时，可以点
    row = ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(expand=True, content=build_field_box(field)),
            button,
        ],
    )
    return row, button


def _set_code_label(button: ft.Control, label: str, color: str) -> bool:
    """给按钮换文案 / 换字色并推给客户端；控件已经不在树上时返回 False。

    倒计时期间把字调浅一档（`HINT_COLOR`），和「可以点」那档灰分开。控件被卸下之后
    `update()` 会抛 RuntimeError —— 页面还在时不会，用户退回上一页才会，这时当成
    「页面没了」收手就行（和 tools/layout.py 的 anchor_dialog_above_keyboard
    一个处理）。
    """
    button.content.value = label
    button.content.color = color
    try:
        button.update()
    except RuntimeError:
        return False
    return True


async def _countdown_code(button: ft.Control) -> None:
    """倒计时本体：写下剩余秒数 → 睡一秒 → 减一，归零后恢复成「重新发送」。"""
    for remaining in range(CODE_COUNTDOWN_SECONDS, 0, -1):
        if not _set_code_label(
            button, CODE_COUNTDOWN_LABEL.format(n=remaining), HINT_COLOR
        ):
            button.data = False
            return
        await asyncio.sleep(1)
    _set_code_label(button, CODE_RESEND_LABEL, MUTED_COLOR)
    button.data = False


def start_code_countdown(page: ft.Page, button: ft.Control) -> None:
    """点过「获取验证码」之后：按钮锁 60 秒、每秒把剩余秒数写上去，归零才恢复可点。

    锁记在 `button.data` 上（点击时由 `build_code_row` 里那层守卫读它）。倒计时用
    `page.run_task` + `asyncio.sleep(1)` 跑 —— Flet 里跑后台循环的标准做法（设置页
    的「检查新版本」也是这么发的），不会卡住 UI。
    """
    button.data = True
    page.run_task(_countdown_code, button)


def build_primary_button(
    label: str, on_click: Callable[[ft.Event[ft.Control]], None]
) -> ft.Control:
    """整宽的主按钮（登录 / 注册 / 重置密码）。

    全 App 都平（菜单、弹窗按钮都不留阴影和涟漪），主按钮也照办：`elevation=0`、
    阴影和 overlay 全透明。
    """
    return ft.FilledButton(
        label,
        height=BUTTON_HEIGHT,
        style=ft.ButtonStyle(
            bgcolor=DATE_SELECTED_BG,
            color=TITLE_COLOR,
            elevation=0,
            shadow_color="#00000000",
            overlay_color="#00000000",
            shape=ft.RoundedRectangleBorder(radius=FIELD_RADIUS),
            text_style=ft.TextStyle(
                size=BUTTON_TEXT_SIZE, weight=ft.FontWeight.BOLD
            ),
        ),
        on_click=on_click,
    )


def build_card_heading(
    title: str, hint: str | None = None, icon_src: str | None = None
) -> ft.Control:
    """卡片顶部的标题区：标题 + 可选的一行小字说明 + 可选一张圆头像。

    `icon_src` 给的是相对 assets 的路径（见 tools/layout.py 里那几张 *_ICON_SRC）；
    只有登录页带头像，注册和忘记密码只留标题。
    """
    lines = [
        ft.Text(
            title,
            size=TITLE_SIZE,
            weight=ft.FontWeight.BOLD,
            color=TITLE_COLOR,
        )
    ]
    if hint:
        lines.append(ft.Text(hint, size=SUBTITLE_SIZE, color=MUTED_COLOR))
    heading = ft.Column(
        tight=True,
        spacing=2,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=lines,
    )
    if icon_src is None:
        return heading
    return ft.Column(
        tight=True,
        spacing=CARD_SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            # 头像也不填底色，只有一圈细边（和卡片、输入框同一个做法）。
            ft.Container(
                width=AVATAR_SIZE,
                height=AVATAR_SIZE,
                alignment=ft.Alignment.CENTER,
                border_radius=ft.BorderRadius.all(AVATAR_SIZE / 2),
                border=ft.Border.all(1, CARD_BORDER),
                content=ft.Image(
                    src=icon_src,
                    width=AVATAR_SIZE * AVATAR_ICON_RATIO,
                    height=AVATAR_SIZE * AVATAR_ICON_RATIO,
                    fit=ft.BoxFit.CONTAIN,
                ),
            ),
            heading,
        ],
    )


def build_auth_card(controls: list[ft.Control]) -> ft.Control:
    """装这些字段的那张卡片：只有一圈浅灰细边 + 12 圆角，没有底色。

    字段与按钮之间不再插分隔线：卡片里第一个元素（标题 / 头像）和第一个输入框之间
    那道横线已经去掉了，留白由 `CARD_SPACING` 负责。
    """
    return ft.Container(
        padding=ft.Padding.symmetric(
            horizontal=CARD_PADDING_X, vertical=CARD_PADDING_Y
        ),
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        border=ft.Border.all(1, CARD_BORDER),
        content=ft.Column(
            tight=True,
            spacing=CARD_SPACING,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=controls,
        ),
    )


def build_link(
    label: str, on_click: Callable[[ft.Event[ft.Control]], None]
) -> ft.Control:
    """卡片下面那行小字按钮（点了就走，样式跟正文区分开）。"""
    return ft.Container(
        ink=True,
        border_radius=ft.BorderRadius.all(6),
        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
        on_click=on_click,
        content=ft.Text(label, size=SUBTITLE_SIZE, color=MUTED_COLOR),
    )


def build_link_row(
    items: list[tuple[str, Callable[[ft.Event[ft.Control]], None]]],
) -> ft.Control:
    """卡片下面那行小字链接：`[(文案, 回调), ...]`，之间自动插一个中点分隔。"""
    controls: list[ft.Control] = []
    for index, (label, on_click) in enumerate(items):
        if index:
            controls.append(ft.Text("·", size=SUBTITLE_SIZE, color=HINT_COLOR))
        controls.append(build_link(label, on_click))
    return ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=controls)


def build_auth_page(
    page: ft.Page,
    title: str,
    go_back: Callable[[], None],
    controls: list[ft.Control],
) -> ft.Control:
    """三页共用的页面壳：渐变底 + SafeArea + 左右 24 的边距。

    版式用 `Stack` 摆两块，都横跨整行：顶栏钉在顶上（`top=0`），表单从 `form_top`
    往下摆 —— `form_top` 是**按窗口高度算出的固定像素**（见 `FORM_TOP_RATIO`），
    不是弹性留白。这样键盘升起、视口被压矮时，表单的绝对位置一点不变，也就不会
    「整页往上挤」；Stack 默认裁掉超出部分，所以真要放不下也只是下半截被裁掉，
    不会挤出布局报错。

    需要 `page` 只是为了取 `page.height`（构建这一页时键盘还没升起，拿到的是整屏
    高度）。
    """
    form_top = max(FORM_TOP_MIN, (page.height or 0) * FORM_TOP_RATIO)
    return ft.Container(
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
                ),
                content=ft.Stack(
                    expand=True,
                    controls=[
                        ft.Container(
                            left=0,
                            right=0,
                            top=0,
                            content=build_subpage_header(title, go_back),
                        ),
                        # `tight=True`：这一块只有内容那么高，`top` 才是它的上边距，
                        # 不会自己长到整屏。
                        ft.Container(
                            left=0,
                            right=0,
                            top=form_top,
                            content=ft.Column(
                                tight=True,
                                spacing=CARD_SPACING,
                                horizontal_alignment=(
                                    ft.CrossAxisAlignment.STRETCH
                                ),
                                controls=controls,
                            ),
                        ),
                    ],
                ),
            ),
        ),
    )
