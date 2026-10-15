"""「写想法」页（发布面板里点「写文字」进来）—— 照小红书那张图复刻。

版式（自上而下）：
- **顶栏**：左边一枚 ✕（关掉这一页），右边一枚「下一步」胶囊 —— 没打字时是**浅红那档**
  （点不动），打了字才变成本项目那个强调红（`#FF2442`）；
- **主卡片**：一整张白色圆角大卡，**后面垫着差不多大的另一张纸、斜着抽出来的** ——
  它的**左上角**从主卡上边探出来、**右下角**从主卡下边探出来（照那张图，见
  `thought_card`）；卡片里面自上而下是一枚浅灰引号（`ft.Icons.FORMAT_QUOTE`，Material
  这个图标本身就是一对引号）、一行大字「写想法」、再下面是**输入区**：没写东西时显示浅灰
  占位「说点什么或提个问题...」，光标是项目那个红（`cursor_color`）；
- **底卡片**：「写长文」一行（图标格子 + 标题 + 小字「支持万字，全屏阅读体验」+ ›）。

底下整页是一层**浅绿 → 浅灰**的渐变（照那张图：上半偏薄荷绿、下半偏灰白）。

键盘（用户要求 —— 这一页和别的页不一样）：
- 进来**不自动弹键盘**（没有 `autofocus`），要写再点输入区；
- 键盘升起时底下那张「写长文」卡**不往上挤**。两点保证：
  1. 那张卡是**从页面顶边量**的绝对位置（`_card_top`），不是贴屏幕底 —— 页面被键盘压短
     时贴底的绝对定位会跟着往上跑，从顶边量则不受影响，卡片照旧停在屏幕上原地；
  2. 它一被点中（`on_focus`）就把主卡下面给它留的那段空当收掉，键盘弹起后主卡直接铺到
     键盘上沿，不会在键盘上方留一条 132px 的空白。
  ⚠️ **别改回靠 `page.media.view_insets.bottom` 算**：那个值在真机上量出来是 0（键盘高度
  拿不到，等于没补偿），试过一版就是因此失效的。

⚠️ 这一页目前**没接后端**：写的内容、以及「下一步」「写长文」都还没有去处，点了只给一句
提示（和发布面板里那两项一个做法）。要接的时候把 `submit` 换成真请求即可，版式不用动。
"""

from collections.abc import Callable

import flet as ft

from widgets.layout import safe_update
from widgets.toast import build_toast

# 那一层浅绿 → 浅灰的整页渐变（左上偏绿、右下偏灰白）。
BG_TOP = "#E9F6EF"
BG_BOTTOM = "#F1F2F1"
# 卡片与内容。
CARD_BG = "#FFFFFF"
SIDE_PADDING = 16
PAGE_TOP_PADDING = 8
CARD_RADIUS = 24
CARD_PADDING = 24
# 主卡和底下「写长文」卡之间那段间距：要给主卡后面那张斜纸的右下角留出探头的余地
# （`SHEET_ANGLE` 歪过去之后它往下探十来像素）。
CARD_GAP = 40
# 主卡那层浅阴影：让它和底下那张「折叠」的小卡分得出上下。
CARD_SHADOW = ft.BoxShadow(
    blur_radius=18, color="#1A0F172A", offset=ft.Offset(0, 6)
)
# 顶栏：✕ 与「下一步」胶囊。顶栏到主卡之间要留出折角那一小截的位置。
HEADER_GAP = 30
CLOSE_SIZE = 24
CLOSE_COLOR = "#1F1F1F"
TITLE_COLOR = "#1F1F1F"
NEXT_LABEL = "下一步"
NEXT_SIZE = 14
NEXT_HEIGHT = 34
NEXT_SIDE_PADDING = 18
# 「下一步」没打字时的那档浅红（图上就是这个状态：点不动），打字后才变成强调红。
ACCENT_RED = "#FF2442"
NEXT_IDLE_BG = "#F8B4AE"
# 主卡：引号 + 「写想法」+ 输入区。
QUOTE_SIZE = 40
QUOTE_COLOR = "#E3E6EA"
HEADING = "写想法"
HEADING_SIZE = 22
HEADING_TOP_GAP = 22
PLACEHOLDER = "说点什么或提个问题..."
INPUT_SIZE = 18
PLACEHOLDER_COLOR = "#B9BDC4"
INPUT_GAP = 8
# 主卡后面那张纸：和主卡**一样高**、左右各收 `SHEET_INSET`，再顺时针歪 `SHEET_ANGLE`
# 弧度 —— 歪过之后它的**左上角**从主卡上边探出来、**右下角**从主卡下边探出来，另外两个角
# 歪回主卡底下看不见（用户要的就是「一张图片倾斜出来的」这个效果：两张纸各露一个角）。
#
# ⚠️ 角度是**正的**（顺时针）才有左上 / 右下这一对探头；负角度会翻成右上 / 左下（上一版
# 方向就是反的）。左右各收 `SHEET_INSET` 是为了把右上 / 左下那两个角**收进卡片里**：
# 横着探多少 ≈ (卡片高 / 2) × sin(角度)，卡片越高这个数越大 —— 所以 `SHEET_INSET` 至少要
# 比它大（现在 32 对 ~29 就是按这条卡的，卡片高了 / 角度调大了都得跟着往上调）。
#
# 两个数都跟角度**同向**，所以别指望「角度大 + 探头贴角」：
#   探头大小 ≈ (卡片宽/2 − `SHEET_INSET`) × sin(角度) − (卡片高/2) × (1 − cos(角度))
#   探头离角多远 ≈ `SHEET_INSET` + (卡片高/2) × sin(角度)
# 角度一调大，探头就往卡片中间跑（用户反馈过两轮：先嫌小、后嫌 0.22 太大 + 不贴角）。
# 现在 0.11（约 6.3°）：360×529 的卡片上探头 ≈15px，左上那截从卡片左边进来 ≈60px。
# 还想更贴角就得换玩法：`SHEET_INSET` 再收小会让右上 / 左下两个角也露出来，或者把纸改得
# 比主卡宽（左右各露一条侧边）。
SHEET_INSET = 32
SHEET_ANGLE = 0.11
SHEET_BG = "#F4F7F5"
SHEET_SHADOW = ft.BoxShadow(
    blur_radius=16, color="#140F172A", offset=ft.Offset(0, 4)
)
# 底卡片：「写长文」。
LONG_RADIUS = 16
LONG_PADDING = 12
LONG_ICON_TILE = 40
LONG_ICON_RADIUS = 10
TILE_BG = "#F2F3F5"
LONG_ICON_SIZE = 20
LONG_TITLE = "写长文"
LONG_TITLE_SIZE = 16
LONG_HINT = "支持万字，全屏阅读体验"
LONG_HINT_SIZE = 12
HINT_COLOR = "#9CA3AF"
CHEVRON_COLOR = "#C9C9C9"
# 「写长文」那张卡离屏幕底边多远（比原来往上挪了一截：用户要求）；它自己那点高度；以及
# **主卡下面要给它留出的空当**（离底边那段 + 卡片高度 + 一道间距）。
BOTTOM_OFFSET = 56
LONG_CARD_HEIGHT = LONG_PADDING * 2 + LONG_ICON_TILE
BOTTOM_RESERVE = BOTTOM_OFFSET + LONG_CARD_HEIGHT + CARD_GAP


def _card_top(page: ft.Page) -> float | None:
    """「写长文」卡离**页面顶边**多远（按屏高算出来的绝对位置）；量不到屏高给 `None`。

    ⚠️ 为什么不用 `bottom=` 贴屏幕底：键盘升起时页面会被压短，贴着底边的绝对定位会跟着往上
    跑 —— 卡片就被挤到主卡下面去了（用户反馈）。从**顶边**量就没这个问题：页面压短不影响
    这个绝对位置，卡片照旧停在屏幕上原地（被键盘盖住）。

    屏高的坐标：`page.height` 是整个窗口高，`view_padding` 是系统栏那两段，我们的 Stack
    正好从**顶部状态栏下面**开始，所以要减掉 `top`；底边那段则决定了「贴底」到底在哪。
    量不到（页面还没渲染出尺寸）时返回 `None`：调用方退回 `bottom=` 那种贴底摆法，至少
    位置是对的。
    """
    height = page.height or 0
    if not height:
        return None
    padding = getattr(page.media, "view_padding", None)
    top = getattr(padding, "top", 0) or 0
    bottom = getattr(padding, "bottom", 0) or 0
    return height - bottom - BOTTOM_OFFSET - LONG_CARD_HEIGHT - top


def build_write_thought_page(
    page: ft.Page,
    go_back: Callable[[], None],
) -> ft.Control:
    """`go_back` 是左上角那个 ✕（发布面板里进来时，退回去的是当时那个 Tab）。"""

    def notify(message: str) -> None:
        """一句话提示：走 widgets/toast.py，浮在屏幕正中（全项目一个做法）。"""
        page.show_dialog(build_toast(page, message))

    def submit(_: ft.Event[ft.Container]) -> None:
        """「下一步」：目前没接后端，先给一句提示（要接就换成真请求）。"""
        notify("「下一步」暂未开放")

    thought = ft.TextField(
        hint_text=PLACEHOLDER,
        hint_style=ft.TextStyle(size=INPUT_SIZE, color=PLACEHOLDER_COLOR),
        # 多行：这张卡片剩下的地方都是写东西的地方。
        multiline=True,
        # ⚠️ **不要 autofocus**（用户要求）：一进这一页就弹键盘太吵 —— 想写再点这一格。
        # 光标仍然是项目那个红（`cursor_color`）。
        cursor_color=ACCENT_RED,
        cursor_width=3,
        cursor_radius=2,
        filled=False,
        border=ft.NoInputBorder(),
        content_padding=0,
        text_style=ft.TextStyle(size=INPUT_SIZE, color=TITLE_COLOR),
        expand=True,
        on_change=lambda _: refresh_next(),
    )

    next_button = ft.Container(
        height=NEXT_HEIGHT,
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(horizontal=NEXT_SIDE_PADDING),
        border_radius=ft.BorderRadius.all(NEXT_HEIGHT / 2),
        # 初始状态照那张图：还没打字 → 浅红、点不动（见 `refresh_next`）。
        bgcolor=NEXT_IDLE_BG,
        content=ft.Text(
            NEXT_LABEL,
            size=NEXT_SIZE,
            weight=ft.FontWeight.BOLD,
            color="#FFFFFF",
        ),
    )

    def refresh_next() -> None:
        """有内容「下一步」才亮；空着是浅红那档、也点不动。"""
        written = bool((thought.value or "").strip())
        next_button.bgcolor = ACCENT_RED if written else NEXT_IDLE_BG
        next_button.on_click = submit if written else None
        safe_update(next_button)

    def header() -> ft.Control:
        """顶栏：✕ 在左、「下一步」胶囊在右。"""
        return ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    ink=True,
                    tooltip="关闭",
                    padding=ft.Padding.all(6),
                    on_click=lambda _: go_back(),
                    content=ft.Icon(
                        ft.Icons.CLOSE, size=CLOSE_SIZE, color=CLOSE_COLOR
                    ),
                ),
                ft.Container(expand=True),
                next_button,
            ],
        )

    def thought_card() -> ft.Control:
        """主卡 + 它后面那张**斜着抽出来的纸**（左上角 / 右下角各探出一截）。

        ⚠️ 两点容易做错：
        1. 这层 `Stack` 必须 `clip_behavior=NONE`（默认会把探出去的两个角裁掉）；
        2. 纸要摆在主卡**前面**（先画）才会被主卡压住中间那大半截，只留对角两个角。
        """
        return ft.Stack(
            expand=True,
            clip_behavior=ft.ClipBehavior.NONE,
            controls=[
                ft.Container(
                    # 四个边都标上 = 撑满这一格（再各自收 `SHEET_INSET`），于是它和主卡
                    # 一样高；歪过去之后左上角往上探、右下角往下探。
                    left=SHEET_INSET,
                    right=SHEET_INSET,
                    top=0,
                    bottom=0,
                    bgcolor=SHEET_BG,
                    border_radius=ft.BorderRadius.all(CARD_RADIUS),
                    rotate=ft.Rotate(angle=SHEET_ANGLE),
                    shadow=SHEET_SHADOW,
                ),
                ft.Container(
                    expand=True,
                    border_radius=ft.BorderRadius.all(CARD_RADIUS),
                    bgcolor=CARD_BG,
                    shadow=CARD_SHADOW,
                    padding=ft.Padding.all(CARD_PADDING),
                    # ⚠️ 里面的 Column 要 `expand=True`（不是 `tight=True`）：输入框带着
                    # `expand=True` 吃掉卡片剩下的高度，得有个**有界**的父高度给它（卡片
                    # 撑满那一格，所以这里有界）。
                    content=ft.Column(
                        expand=True,
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        controls=[
                            # ⚠️ 套一层 Row：外面这列是 `STRETCH`，图标直接摆进去会被拉成
                            # 满宽（引号就跑到卡片中间去了）。套上 Row 才是自己那么大、靠左。
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.FORMAT_QUOTE,
                                        size=QUOTE_SIZE,
                                        color=QUOTE_COLOR,
                                    )
                                ]
                            ),
                            ft.Container(height=HEADING_TOP_GAP),
                            ft.Text(
                                HEADING,
                                size=HEADING_SIZE,
                                weight=ft.FontWeight.BOLD,
                                color=TITLE_COLOR,
                            ),
                            ft.Container(height=INPUT_GAP),
                            thought,
                        ],
                    ),
                ),
            ],
        )

    def long_form_card() -> ft.Container:
        """底卡「写长文」：图标格子 + 标题 / 小字 + ›（目前没接功能，点了给提示）。

        返回的就是那张卡本身 —— 调用方给它标上 `left` / `right` 和纵向位置（绝对定位，
        见 `_card_top`）。
        """
        return ft.Container(
            border_radius=ft.BorderRadius.all(LONG_RADIUS),
            bgcolor=CARD_BG,
            shadow=CARD_SHADOW,
            ink=True,
            padding=ft.Padding.all(LONG_PADDING),
            on_click=lambda _: notify("「写长文」暂未开放"),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=LONG_ICON_TILE,
                        height=LONG_ICON_TILE,
                        alignment=ft.Alignment.CENTER,
                        border_radius=ft.BorderRadius.all(LONG_ICON_RADIUS),
                        bgcolor=TILE_BG,
                        content=ft.Icon(
                            ft.Icons.EDIT_NOTE,
                            size=LONG_ICON_SIZE,
                            color=TITLE_COLOR,
                        ),
                    ),
                    ft.Column(
                        tight=True,
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(
                                LONG_TITLE,
                                size=LONG_TITLE_SIZE,
                                weight=ft.FontWeight.BOLD,
                                color=TITLE_COLOR,
                            ),
                            ft.Text(
                                LONG_HINT, size=LONG_HINT_SIZE, color=HINT_COLOR
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT, size=20, color=CHEVRON_COLOR
                    ),
                ],
            ),
        )

    def set_reserve(reserved: bool) -> None:
        """主卡下面留给「写长文」的那段空当：收掉 / 放回。

        点进输入框（键盘要起来了）就收掉 —— 底下那张卡已经被键盘盖住，主卡没必要再让出
        位置，直接铺到键盘上沿；失焦（键盘落下）再放回来，卡片才不会被主卡压住。
        """
        body.padding = ft.Padding.only(
            left=SIDE_PADDING,
            right=SIDE_PADDING,
            top=PAGE_TOP_PADDING,
            bottom=BOTTOM_RESERVE if reserved else 0,
        )
        safe_update(body)

    refresh_next()
    # 先建控件、再挂处理函数（和页里那两枚开关一个写法）。
    thought.on_focus = lambda _: set_reserve(False)
    thought.on_blur = lambda _: set_reserve(True)

    # 上面一整块（顶栏 + 主卡）：主卡用 `expand` 吃掉键盘带来的收缩，于是它始终贴着键盘
    # 上沿；底下一段 `BOTTOM_RESERVE` 是给「写长文」卡留的位置（点进输入框就收掉，见
    # `set_reserve`）。
    body = ft.Container(
        padding=ft.Padding.only(
            left=SIDE_PADDING,
            right=SIDE_PADDING,
            top=PAGE_TOP_PADDING,
            bottom=BOTTOM_RESERVE,
        ),
        content=ft.Column(
            expand=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                header(),
                ft.Container(height=HEADER_GAP),
                thought_card(),
            ],
        ),
    )
    # 底卡**绝对定位**在屏幕上「离底边 56」的位置（不是跟在主卡后面 —— 跟在后面的话，
    # 键盘一起来它就贴到主卡上去了）。纵向用**离顶边**算出来的绝对位置（`_card_top`），
    # 这样页面被键盘压短也不会把它带着往上跑。
    bottom_card = long_form_card()
    bottom_card.left = SIDE_PADDING
    bottom_card.right = SIDE_PADDING
    card_top = _card_top(page)
    if card_top is None:
        # 量不到屏高（还没渲染出来）：退回贴底摆法，位置对但会被键盘带着走。
        bottom_card.bottom = BOTTOM_OFFSET
    else:
        bottom_card.top = card_top

    return ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            colors=[BG_TOP, BG_BOTTOM],
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
        ),
        content=ft.SafeArea(
            expand=True,
            content=ft.Stack(
                # ⚠️ 不裁：底卡是**按屏幕绝对位置**摆的，键盘把这一层压短之后它会落在这一层
                # 的框外面 —— 裁掉的话它就直接消失了。
                clip_behavior=ft.ClipBehavior.NONE,
                expand=True,
                controls=[
                    body,
                    bottom_card,
                ],
            ),
        ),
    )
