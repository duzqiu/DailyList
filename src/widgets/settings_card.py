"""设置卡片的零件：`settings_section` / `setting_row` / `compact_button_style`，以及
**「我的」页那张账号卡片**（`build_account_card`）。

这三块零件原本长在设置页（pages/preferences.py）里；「账号」卡片现在挂在「我的」页
（pages/my.py），两边都要用同一套卡片外壳 —— 所以一并搬到这儿，设置页反过来 import 它们
（一处实现、两处用；见 README 开发约定 2）。

`build_account_card` 自己只依赖 `page` 与 `open_login`，不碰设置页的任何局部状态。

⚠️ 这张卡片是**只读**的：只显示「我是谁」（左侧头像，右侧「昵称：…」+「ID：…」）。
退出登录不在它里面（原来那个「管理」按钮进登录页）—— 那个动作现在归设置页的「通用设置」
（见 pages/preferences.py 的 `logout_row`）。
"""

from collections.abc import Callable

import flet as ft

from api import member_auth, session
from api.client import ApiError
from tools import my_profile
from widgets.layout import UNSELECTED_CARD_BG

TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
# 报错那一行的颜色（拉取用户信息失败时用），和设置页原来的取值一致。
PENDING_COLOR = "#DC2626"
CARD_BG = UNSELECTED_CARD_BG
CARD_BORDER = "#E2E8F0"
# 卡片压在**背景图**上时（「我的」页，`on_image=True`）的配色：文字 / 图标改白 ——
# 纯白给主要文字，90% 白给次要说明，40% 白给描边。
ON_IMAGE_COLOR = "#FFFFFF"
ON_IMAGE_MUTED = "#E6FFFFFF"
# ID 那一行再淡一档（浅灰）：压在图上时和上面那行昵称拉开层次。
ON_IMAGE_DIM = "#B3FFFFFF"
ON_IMAGE_LINE = "#66FFFFFF"
# 骨架（拉用户信息时先摆的占位块）：图上用**半透明白**，白底上用浅灰。
ON_IMAGE_SKELETON = "#3DFFFFFF"
SKELETON_COLOR = "#E8EDF3"
# 未登录那行「未登录」的字号：和登录后那行昵称同档（16），切换时不会忽然矮一截。
SIGNED_OUT_SIZE = 16


def settings_section(
    title: str,
    rows: list[ft.Control],
    bgcolor: str | None = CARD_BG,
    show_border: bool = True,
    padding: ft.Padding | None = None,
) -> ft.Control:
    """`padding` 不给就是卡片惯用的 16 / 14 内边距；「我的」页账号那块把它去掉 ——
    它上面没有卡片框，多一圈内边距会让头像比下面几块（统计 / 简介 / 小卡）右移一截。"""
    """一档设置：卡片上方一行小标题（灰字，可省），底下的卡片里摆这一档的各行。

    `title` 给空串就**不要那行小标题**，只留卡片本身（「我的」页的账号卡片就是这么用的：
    它自己已经够清楚了，再压一行「账号」反而多余）。

    `bgcolor=None` 就是**透明底**：卡片自己不铺色，露出来的是页面的渐变（边框还留着，
    方框的样子还在）。「我的」页那张个人信息卡片就是用它：原来那层灰底压在渐变上显得闷。
    """
    return ft.Column(
        tight=True,
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            *(
                [
                    ft.Text(
                        title,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=MUTED_COLOR,
                    )
                ]
                if title
                else []
            ),
            ft.Container(
                padding=(
                    padding
                    if padding is not None
                    else ft.Padding.symmetric(horizontal=16, vertical=14)
                ),
                border_radius=ft.BorderRadius.all(12),
                bgcolor=bgcolor,
                border=(
                    ft.Border.all(1, CARD_BORDER) if show_border else None
                ),
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=rows,
                ),
            ),
        ],
    )


def setting_row(
    title: str,
    subtitle: ft.Control,
    action: ft.Control | None = None,
):
    """卡片里的一行：左边「标题 + 小字说明」，右边跟一个动作控件。

    纯展示的行（当前版本）不给动作，右边就空着。

    （原来还有个 `on_image` 参数给「我的」页未登录那一行用 —— 那一行改成整块可点的
    大字之后就不需要了，参数一并撤掉。）
    """
    return ft.Row(
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Column(
                tight=True,
                spacing=2,
                expand=True,
                controls=[
                    ft.Text(
                        title,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=TITLE_COLOR,
                    ),
                    subtitle,
                ],
            ),
            *([action] if action is not None else []),
        ],
    )


def compact_button_style() -> ft.ButtonStyle:
    """Compact metrics of the card's own 清除 action button."""
    return ft.ButtonStyle(
        padding=ft.Padding.symmetric(horizontal=10, vertical=2),
        text_style=ft.TextStyle(size=12),
        visual_density=ft.VisualDensity.COMPACT,
    )


def build_account_card(
    page: ft.Page,
    open_login: Callable[[], None],
    on_image: bool = False,
    on_blank_tap: Callable[[], None] | None = None,
) -> ft.Control:
    """「我的」页那张账号卡片：没登录给个登录入口，登录了显示**头像 + 昵称 + ID**。

    `on_image=True` 表示这张卡片压在**背景图**上 → 文字 / 图标 / 头像框改白
    （见上面的 `ON_IMAGE_*`）；默认 `False` 是深色字，给白底场景用。

    `on_blank_tap` 给了就在昵称 / ID 右边留一块**与头像同高的空白**当点击区（点了换
    背景图）。原来「我的」页是整段背景都能点，用户说区域太大、容易误触，就收成这一块。

    两种情况共用同一块 `account_body`（就是卡片里的内容），拉到数据后只换这一块
    —— 不重画整页，也不惊动别的东西。

    已登录的形态是按需求收过的：**不收邮箱**、**没有「管理」按钮**，左侧只有头像，右侧
    两行「昵称：…」/「ID：…」（会员号）。退出登录在设置页（见 preferences.logout_row）。

    **缓存优先**：`api/member_auth.py` 里存着当前会员（按令牌存、10 分钟有效），命中
    就直接摆真数据 —— 切 Tab / 退回这一页都不会再打一次接口。没命中才摆**骨架**
    （见 `skeleton()`，形状和真实那一行对得上，数据回来就地替换、位置不跳）并去拉。

    用户信息来自后端 `GET /member/auth/me`（见 api/member_auth.py）；本地令牌已
    失效（401）时把令牌清掉、退回未登录形态，免得一直停在拉不到数据的样式上。

    卡片上**没有小标题**（`settings_section("", …)`）：这张卡片本身就写着是谁。
    """
    # 头像是个人主页那一块的主体（照小红书那版：圆头像压在最上面，比行高一大截）。
    avatar_size = 72
    account_body = ft.Column(
        tight=True,
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[],
    )

    def skeleton() -> ft.Control:
        """拉用户信息时先摆的**骨架**：一个圆 + 两条短条 + 右边那块空白。

        形状和真实那一行**对得上**（同样的圆头像、同样的间距、同样的右空白），所以数据
        回来换成真内容时位置不会跳。颜色：图上用半透明白、白底用浅灰（见上面的常量）。
        """
        block = ON_IMAGE_SKELETON if on_image else SKELETON_COLOR

        def bar(width: int, height: int) -> ft.Control:
            return ft.Container(
                width=width,
                height=height,
                border_radius=ft.BorderRadius.all(height / 2),
                bgcolor=block,
            )

        return ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                # 圆头像的占位。
                ft.Container(
                    width=avatar_size,
                    height=avatar_size,
                    border_radius=ft.BorderRadius.all(avatar_size / 2),
                    bgcolor=block,
                ),
                # 昵称 / ID 两条的占位（高矮对应 16 / 11 那两个字号）。
                ft.Column(
                    tight=True,
                    spacing=8,
                    controls=[bar(120, 16), bar(80, 11)],
                ),
                # 和真实那一行一样：右边那块空白单独留着（点了换背景图，见 `on_blank_tap`）。
                ft.Container(
                    expand=True,
                    height=avatar_size,
                    tooltip="更换背景图" if on_blank_tap else None,
                    on_click=(
                        (lambda _: on_blank_tap())
                        if on_blank_tap is not None
                        else None
                    ),
                ),
            ],
        )

    def render_signed_out(message: str = "", update: bool = True) -> None:
        """未登录：「未登录」四个字**放大**（和登录后的昵称同档），下面一行小字说明。

        **整块可点** → 进登录页（用户要求）；右边那个「登录」按钮因此去掉了 ——
        一行字自己就是入口，不用再并一个按钮。`message` 用来报拉取失败的原因。
        """
        account_body.controls = [
            ft.Container(
                ink=True,
                tooltip="去登录",
                on_click=lambda _: open_login(),
                content=ft.Column(
                    tight=True,
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Text(
                            "未登录",
                            # 放大：13 → 16，和登录后那行昵称同一档（切换时不显得矮一截）。
                            size=SIGNED_OUT_SIZE,
                            weight=ft.FontWeight.BOLD,
                            color=ON_IMAGE_COLOR if on_image else TITLE_COLOR,
                        ),
                        ft.Text(
                            message or "点击登录后可查看账号信息",
                            size=11,
                            color=(
                                PENDING_COLOR
                                if message
                                else (
                                    ON_IMAGE_MUTED
                                    if on_image
                                    else MUTED_COLOR
                                )
                            ),
                        ),
                    ],
                ),
            )
        ]
        if update:
            page.update()

    def render_user(user: dict, update: bool = True) -> None:
        """已登录：左头像、右「昵称：…」「ID：…」—— 不给邮箱，也不给「管理」。

        `update=False` 给**建页面时**用（缓存里已经有数据那一路）：那一格在建的时候
        就定好了，不用再刷一次。
        """
        # 名字 / 小红书号：**编辑资料页改过的（本地）优先**，没改过才用账号里的
        # （显示名 → 昵称 → 邮箱；都没有就写「会员」）。见 tools/my_profile.py。
        nickname = my_profile.account_name(user)
        member_no = my_profile.account_id(user)
        # 头像是本地换过的那张（没换过是空串 → 摆图标）。
        local_avatar = my_profile.avatar_path()
        lines = [
            ft.Text(
                # 只写名字，不带「昵称：」那个字段名 —— 名字自己就是这一块的标题
                # （照小红书那版）。
                nickname or "会员",
                size=16,
                weight=ft.FontWeight.BOLD,
                color=ON_IMAGE_COLOR if on_image else TITLE_COLOR,
            )
        ]
        if member_no:
            lines.append(
                ft.Text(
                    f"ID：{member_no}",
                    size=11,
                    # 压在图上时用更淡的一档白（浅灰），和上面那行昵称分开层次。
                    color=ON_IMAGE_DIM if on_image else MUTED_COLOR,
                )
            )
        account_body.controls = [
            ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # 头像：编辑资料页换过就用那张（本地存的路径），没换过还是内置图标
                    # —— 和登录页那张卡片同一个做法。
                    ft.Container(
                        width=avatar_size,
                        height=avatar_size,
                        alignment=ft.Alignment.CENTER,
                        border_radius=ft.BorderRadius.all(avatar_size / 2),
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        border=ft.Border.all(
                            1, ON_IMAGE_LINE if on_image else CARD_BORDER
                        ),
                        content=(
                            ft.Image(
                                src=local_avatar,
                                fit=ft.BoxFit.COVER,
                                expand=True,
                            )
                            if local_avatar
                            else ft.Icon(
                                ft.Icons.PERSON,
                                size=avatar_size * 0.55,
                                color=(
                                    ON_IMAGE_COLOR if on_image else MUTED_COLOR
                                ),
                            )
                        ),
                    ),
                    # 文字列**不再 expand**：右边的空白要单独留出来当点击区。
                    ft.Column(tight=True, spacing=2, controls=lines),
                    # 换背景图的点击区：昵称 / ID 右边那块空白，**高度 = 头像**
                    # （`CrossAxisAlignment.CENTER` 下空容器不给高度就是 0，所以写死）。
                    ft.Container(
                        expand=True,
                        height=avatar_size,
                        tooltip="更换背景图" if on_blank_tap else None,
                        on_click=(
                            (lambda _: on_blank_tap())
                            if on_blank_tap is not None
                            else None
                        ),
                    ),
                ],
            )
        ]
        if update:
            page.update()

    async def load_user() -> None:
        """进页面就把当前会员拉回来；401 说明令牌过期，清掉并退回未登录。"""
        try:
            user = await member_auth.me()
        except ApiError as error:
            if error.status == 401:
                session.clear()
                render_signed_out()
                return
            render_signed_out(error.message)
            return
        render_user(user)

    # 缓存里已经有会员信息 → **不打接口、不闪骨架**，直接摆真数据（用户要求：
    # 不要每次进这一页都请求接口）。缓存在 api/member_auth.py，按令牌存、有有效期。
    cached = member_auth.cached_me() if session.access_token() else None
    if cached is not None:
        render_user(cached, update=False)
    elif session.access_token():
        # 没缓存（或过期 / 刚换过令牌）：先摆**骨架**（形状和真实那一行一致），
        # 拉回来再换成用户信息；拉回来的结果会进缓存，下次进页面就走上面那一路了。
        account_body.controls = [skeleton()]
        page.run_task(load_user)
    else:
        # 建页面时这一格就定好，不用再 update 一次。
        render_signed_out(update=False)

    # 不铺色、不描边、也**不留左右内边距**：这一块就是白底上的一行头像 + 名字。
    # 留 16px 的话头像会比下面几块（统计 / 简介 / 小卡）右移一截，左边缘对不齐。
    return settings_section(
        "",
        [account_body],
        bgcolor=None,
        show_border=False,
        padding=ft.Padding.symmetric(vertical=14),
    )
