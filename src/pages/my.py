"""「我的」页：个人主页（版式参照小红书「我」那一页）。

自上而下：**背景区**（状态栏 → 顶栏 → 头像 / 姓名 / ID → 关注 / 粉丝 / 获赞 →
「点击这里，填写简介」→ 三张小卡（个人售卖 / 浏览记录 / 群聊））→ 内容板（笔记 /
评论 / 收藏 / 赞过 + 空态）。内容板**紧贴**图片背景的下沿（`ListView(spacing=0)`）。

（原来中间还有一块「你可能感兴趣的人」，按用户要求已整块去掉。）

背景区是一个**带装饰图的容器**：图铺在内容底下，容器按内容自己撑高 —— 不写死高度，
所以既不留缝、也不会溢出去盖住下面的内容，滚动正常。这一层外面还包了一个
`GestureDetector` 吃掉竖直拖拽（在图上拉不动页面，见文件末尾），**整段不接受点击** ——
换背景图的入口只有账号卡片里那块空白（昵称 / ID 右边、与头像同高）。

范围（用户指定）：**顶部顶到状态栏，底部盖住三张小卡**。所以这一层左右不收边、也不套
`SafeArea`（套了图会从状态栏下面才开始画），状态栏那一段由它自己用 `top_inset` 让开；
图上还叠了「顶部清晰 → 底部模糊」的连续过渡（见 `_progressive_blur`）。

下拉：**手势在这一层被吃掉**（`GestureDetector`），在图上竖直拖拽页面不动 —— 也就不会
露出白底。为什么不用「页面底下再铺一张同款图」那招：用户否了（等于两张上下层图片）。

数据说明：昵称 / ID 用后端真数据（tools/settings_card.py），关注 / 粉丝 / 获赞、三张小卡、
感兴趣的人、笔记那几块**目前没有真实来源**，先按版式摆出来。
"""

from collections.abc import Callable

import flet as ft

from tools.layout import (
    BOTTOM_MENU_INSET,
    safe_update,
)
from tools.my_background import background_decoration
from tools.settings_card import build_account_card

TITLE_COLOR = "#172554"
MUTED_COLOR = "#94A3B8"
# 小红书那个红：关注胶囊、标签选中的下划线、主动作胶囊都用它。
ACCENT_RED = "#FF2442"
# 这一页的底色：和底部菜单栏一个白。
MY_BG = "#FFFFFF"
# 压在**背景图**上的文字 / 图标一律用白（用户要求）：纯白给主要文字，90% 白给次要说明，
# 40% 白给描边 / 分隔线。
ON_IMAGE_COLOR = "#FFFFFF"
ON_IMAGE_MUTED = "#E6FFFFFF"
ON_IMAGE_LINE = "#66FFFFFF"
# 浅灰面板 / 小卡底色（白底上要分得出层次）。
PANEL_BG = "#F8FAFC"
LINE_COLOR = "#E2E8F0"
# 数字统计。
STAT_NUMBER_SIZE = 17
STAT_LABEL_SIZE = 12
STAT_GAP = 18
# 「头像 / 昵称」那块与它下面「关注 / 粉丝」之间的距离：这两块是一体的，比区域内通用的
# 12px 再紧一档（用户要求缩小）。
IDENTITY_STAT_GAP = 4
INTRO_SIZE = 13
# 三张小卡：图标与标题并排一行。
QUICK_CARD_HEIGHT = 56
QUICK_CARD_RADIUS = 12
QUICK_CARD_PADDING = 10
QUICK_ICON_SIZE = 18
QUICK_TITLE_SIZE = 12
QUICK_HINT_SIZE = 10
# 「你可能感兴趣的人」。
# （PEOPLE_* 四个常量随「你可能感兴趣的人」那一块一起去掉了。）
# 内容板 + 标签页。
SHEET_PADDING = 16
# 标签条：通栏一条，自己带底色（比页面的白略深一档，才看得出是「一条」）；上下各留一点。
TAB_STRIP_BG = "#F1F5F9"
# 标签条上下各留的白：10 → 4 → **2**（用户两次要求「降低 tab 的高度」）。想更矮就往 0
# 调，那时四个标签基本贴着这一条的上下沿了。
TAB_STRIP_PADDING = 2
# 内容板**顶部两角**的圆角半径。圆角切掉的那两块小缺口要露出上面那张背景图，所以
# 「圆角顶盖」画在背景区的最底下（见 `_panel_top_cap`），背景区的下内边距也得比它大。
PANEL_TOP_RADIUS = 18
TAB_SIZE = 14
TAB_IDLE_COLOR = "#6B7280"
TAB_BAR_WIDTH = 18
TAB_BAR_HEIGHT = 2
PILL_RADIUS = 18
PILL_HEIGHT = 36
PILL_TEXT_SIZE = 13
EMPTY_HINT_SIZE = 12
# 「顶部清晰 → 底部模糊」：**一次糊到底 + 用渐变遮罩把「清晰版」盖回来**。
#
# 之前试过「切 6 条磨砂带」「切 12 条、缓入曲线」—— 用户两次都说「太明显」。原因很直白：
# `blur` 是按块生效的，块与块之间的 sigma 差在照片这种有边缘的内容上就是一道**硬分界**，
# 条数只能把台阶变浅，消不掉。所以换做法（`_progressive_blur`）：
#   ① 整块糊一次（`Container(blur=…)` 磨的是**背板**，也就是宿主容器自己那张图）；
#   ② 再叠一张同样的原图，套 `ft.ShaderMask` + 竖向渐变 —— 顶部完全不透明、往下渐透明。
# 从清晰到模糊之间是**连续**的插值，没有任何分界；而且只需要一次模糊（比十几层磨砂带
# 便宜得多）。
BLUR_STRENGTH = 26
# 清晰版那一层的竖向不透明度：顶上 34% 全实（就是原图），往下渐隐到 0（露出糊的那层）。
SHARP_FADE_COLORS = ("#FFFFFFFF", "#FFFFFFFF", "#00FFFFFF")
SHARP_FADE_STOPS = (0.0, 0.34, 1.0)
# 再压一层**连续**的淡白纱（透明 → 5% → 15% 白）：让压在模糊区的卡片 / 文字读得清。
# 它也是渐变，所以不会造成台阶。
BLUR_VEIL_COLORS = ("#00FFFFFF", "#0DFFFFFF", "#26FFFFFF")


def _progressive_blur(decoration: ft.DecorationImage) -> ft.Control:
    """「清晰 → 模糊」那一层：一次模糊 + 渐变遮罩（见上面那段说明）。

    四边定位 —— 在宿主的 `ft.Stack` 里铺满整块背景区（高度由内容层决定）。
    """
    layer = {"top": 0, "left": 0, "right": 0, "bottom": 0}
    return ft.Stack(
        **layer,
        controls=[
            # ① 整块糊一次：磨的是**宿主容器自己那张图**（背板），不是它自己的背景。
            ft.Container(
                blur=ft.Blur(
                    BLUR_STRENGTH, BLUR_STRENGTH, ft.BlurTileMode.CLAMP
                ),
                **layer,
            ),
            # ② 同一张原图，套竖向渐变遮罩：上面实、往下渐隐 —— 连续过渡，没有分界。
            ft.ShaderMask(
                # 遮罩自己四边定位（在 Stack 里铺满整块）。
                **layer,
                blend_mode=ft.BlendMode.DST_IN,
                shader=ft.LinearGradient(
                    begin=ft.Alignment.TOP_CENTER,
                    end=ft.Alignment.BOTTOM_CENTER,
                    colors=list(SHARP_FADE_COLORS),
                    stops=list(SHARP_FADE_STOPS),
                ),
                # ⚠️ 里面这张**不要再带 `top/left/…`**：那几个只在 Stack 里生效，套在
                # ShaderMask 里会被忽略。ShaderMask 给它的是紧约束，Flutter 的 Container
                # 「没子控件、没尺寸」时自己撑满 —— 尺寸就是这么来的。
                content=ft.Container(image=decoration),
            ),
        ],
    )


def _blur_veil() -> ft.Control:
    """那层连续的淡白纱（见 `BLUR_VEIL_COLORS`）：帮模糊区的文字读清楚。"""
    return ft.Container(
        top=0,
        left=0,
        right=0,
        bottom=0,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER,
            end=ft.Alignment.BOTTOM_CENTER,
            colors=list(BLUR_VEIL_COLORS),
        ),
    )


def _panel_top_cap() -> ft.Control:
    """内容板的**圆角顶盖**：与标签条同色的一条，只有上面两角是圆的。

    它贴在**背景区的最底下**（也就是那张图的最后一小段），所以圆角切掉的两块小缺口
    露出来的是**图片**（用户要的「空出的部分用上面的图片背景填充」）。内容板里那条
    标签条紧跟着它、同色相接 —— 看起来就是同一个面板的圆角顶。
    """
    return ft.Container(
        left=0,
        right=0,
        bottom=0,
        height=PANEL_TOP_RADIUS,
        bgcolor=TAB_STRIP_BG,
        border_radius=ft.BorderRadius.only(
            top_left=PANEL_TOP_RADIUS, top_right=PANEL_TOP_RADIUS
        ),
    )


def _pill(
    label: str,
    on_click: Callable[[], None] | None = None,
    *,
    primary: bool = False,
) -> ft.Control:
    """胶囊按钮：`primary` 是红实心那个（照「去发布」），否则白描边（照「更多灵感」）。"""
    return ft.Container(
        expand=True,
        height=PILL_HEIGHT,
        alignment=ft.Alignment.CENTER,
        border_radius=ft.BorderRadius.all(PILL_RADIUS),
        bgcolor=ACCENT_RED if primary else "#FFFFFF",
        border=None if primary else ft.Border.all(1, LINE_COLOR),
        ink=on_click is not None,
        on_click=(lambda _: on_click()) if on_click else None,
        content=ft.Text(
            label,
            size=PILL_TEXT_SIZE,
            weight=ft.FontWeight.BOLD if primary else ft.FontWeight.NORMAL,
            color="#FFFFFF" if primary else TITLE_COLOR,
        ),
    )


def _stat(value: str, label: str) -> ft.Control:
    """数字统计里的一格：数字 + 标签，横着排。

    这一行压在**背景图**上，所以是白字（次要的标签用 90% 白）。
    """
    return ft.Row(
        tight=True,
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text(
                value,
                size=STAT_NUMBER_SIZE,
                weight=ft.FontWeight.BOLD,
                color=ON_IMAGE_COLOR,
            ),
            ft.Text(label, size=STAT_LABEL_SIZE, color=ON_IMAGE_MUTED),
        ],
    )


def build_my_page(
    page: ft.Page,
    set_menu_visible: Callable[[bool], None],
    state: dict[str, object],
    open_settings: Callable[[], None],
    open_login: Callable[[], None],
    on_publish: Callable[[], None],
    open_background: Callable[[], None],
    open_edit_profile: Callable[[], None],
) -> ft.Control:
    """「我的」页。

    `open_settings` 是顶栏左上角那枚 ☰；`open_login` 是账号那块里点「登录」；
    `on_publish` 是内容板上那个红胶囊（目前没接功能，点了给提示）；`open_background`
    是账号卡片里那块空白（换背景图）；`open_edit_profile` 是顶栏胶囊「编辑主页」
    （进去是「编辑资料」二级页，见 pages/edit_profile.py）。

    顶栏右上角原来还有一枚「数据」（柱状图）图标，**按用户要求去掉了** —— 那一格现在只有
    「编辑主页」。
    """
    # 状态栏那一段有多高：**只让内容往下躲**，背景图不躲 —— 于是图能顶到 y=0。
    top_inset = (
        getattr(getattr(page.media, "view_padding", None), "top", 0) or 0
    )

    def quick_card(title: str, icon: str, hint: str) -> ft.Control:
        """三张小卡里的一张：图标 + 标题一行、下面一行小字。

        **透明底**（用户要求）：卡片压在背景图上，不铺自己的浅灰；文字 / 图标改白，
        只留一圈 40% 白的细描边把形状框出来。
        """
        return ft.Container(
            expand=True,
            height=QUICK_CARD_HEIGHT,
            padding=ft.Padding.all(QUICK_CARD_PADDING),
            border_radius=ft.BorderRadius.all(QUICK_CARD_RADIUS),
            bgcolor=None,
            border=ft.Border.all(1, ON_IMAGE_LINE),
            content=ft.Column(
                tight=True,
                spacing=4,
                controls=[
                    ft.Row(
                        tight=True,
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(
                                icon,
                                size=QUICK_ICON_SIZE,
                                color=ON_IMAGE_COLOR,
                            ),
                            ft.Text(
                                title,
                                size=QUICK_TITLE_SIZE,
                                weight=ft.FontWeight.BOLD,
                                color=ON_IMAGE_COLOR,
                                no_wrap=True,
                            ),
                        ],
                    ),
                    ft.Text(hint, size=QUICK_HINT_SIZE, color=ON_IMAGE_MUTED),
                ],
            ),
        )

    # （原来这儿有个 `person()` 画「你可能感兴趣的人」里的条目 —— 那一整块已按要求去掉。）

    # ---------------------- 内容板：四个标签 + 空态 ----------------------

    tab_texts = (
        ("笔记", "发布你的第一篇笔记", "可以看看你租的房子吗", "快发篇笔记来记录"),
        ("评论", "还没有评论", "说说你的看法", "在别人的笔记下留一句"),
        ("收藏", "还没有收藏", "收藏喜欢的笔记", "下次想找就方便了"),
        ("赞过", "还没有赞过", "点个赞试试", "喜欢的内容会留在这儿"),
    )
    empty_hint = ft.Text(tab_texts[0][1], size=EMPTY_HINT_SIZE, color=MUTED_COLOR)
    prompt_title = ft.Text(
        tab_texts[0][2], size=14, weight=ft.FontWeight.BOLD, color=TITLE_COLOR
    )
    prompt_hint = ft.Text(tab_texts[0][3], size=EMPTY_HINT_SIZE, color=MUTED_COLOR)
    tab_labels: list[tuple[ft.Text, ft.Container]] = []

    def select_tab(index: int) -> None:
        """切标签：选中的压深加粗 + 底下一道红杠，空态那几句跟着换。"""
        for order, (text, bar) in enumerate(tab_labels):
            selected = order == index
            text.color = TITLE_COLOR if selected else TAB_IDLE_COLOR
            text.weight = (
                ft.FontWeight.BOLD if selected else ft.FontWeight.NORMAL
            )
            bar.bgcolor = ACCENT_RED if selected else None
            safe_update(text, bar)
        empty_hint.value = tab_texts[index][1]
        prompt_title.value = tab_texts[index][2]
        prompt_hint.value = tab_texts[index][3]
        safe_update(empty_hint, prompt_title, prompt_hint)

    def tab_header(index: int, label: str) -> ft.Control:
        """标签页上的一个标签：文字 + 一条（选中才亮红的）短横杠。"""
        text = ft.Text(
            label,
            size=TAB_SIZE,
            weight=ft.FontWeight.BOLD if index == 0 else ft.FontWeight.NORMAL,
            color=TITLE_COLOR if index == 0 else TAB_IDLE_COLOR,
        )
        bar = ft.Container(
            width=TAB_BAR_WIDTH,
            height=TAB_BAR_HEIGHT,
            border_radius=ft.BorderRadius.all(TAB_BAR_HEIGHT / 2),
            bgcolor=ACCENT_RED if index == 0 else None,
        )
        tab_labels.append((text, bar))
        return ft.Container(
            ink=True,
            on_click=lambda _: select_tab(index),
            content=ft.Column(
                tight=True,
                # 文字与那道红杠之间的缝：4 → 2（跟着「降低 tab 高度」那两次一起收）。
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[text, bar],
            ),
        )

    # （原来这儿是「你可能感兴趣的人」那一块 —— 按用户要求整块去掉，内容板因此直接
    #   接着上面图片背景的下沿，见文件末尾的 ListView：`spacing=0`。）

    def tab_strip() -> ft.Control:
        """标签条：**通栏**一条，自己带底色。

        原来它跟内容一起收在内容板的 16px 内边距里；用户要求「tab 增加背景色、左右不留
        间距、与上方背景图一致」→ 单独拆出来当通栏的一条（标签文字自己仍按 16px 对齐）。
        """
        return ft.Container(
            bgcolor=TAB_STRIP_BG,
            padding=ft.Padding.symmetric(
                horizontal=SHEET_PADDING, vertical=TAB_STRIP_PADDING
            ),
            # 右侧原来还有一枚搜索图标（`Icons.SEARCH`），按用户要求去掉 —— 这一条
            # 现在只剩左边那排标签，通栏也就不用 `SPACE_BETWEEN` 了。
            content=ft.Row(
                tight=True,
                spacing=20,
                controls=[
                    tab_header(0, "笔记"),
                    tab_header(1, "评论"),
                    tab_header(2, "收藏"),
                    tab_header(3, "赞过"),
                ],
            ),
        )

    sheet = ft.Container(
        # 板块自己**不铺底色**（用户要求）：底色只留在上面那条通栏标签上。里面各块
        # 自己收 16px 边距（左右和上面的标签文字对齐）—— 于是这一块整体是通栏的。
        content=ft.Column(
            tight=True,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                tab_strip(),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SHEET_PADDING),
                    content=empty_hint,
                ),
                ft.Container(
                    # 卡片本身收在 16px 里边距里（和标签文字对齐）：通栏的是外层的标签条。
                    margin=ft.Margin.symmetric(horizontal=SHEET_PADDING),
                    padding=ft.Padding.all(12),
                    border_radius=ft.BorderRadius.all(12),
                    bgcolor="#FFFFFF",
                    border=ft.Border.all(1, LINE_COLOR),
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        controls=[
                            ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.START,
                                controls=[
                                    ft.Column(
                                        tight=True,
                                        spacing=4,
                                        expand=True,
                                        controls=[prompt_title, prompt_hint],
                                    ),
                                    ft.Container(
                                        width=56,
                                        height=56,
                                        alignment=ft.Alignment.CENTER,
                                        border_radius=ft.BorderRadius.all(8),
                                        bgcolor=PANEL_BG,
                                        content=ft.Icon(
                                            ft.Icons.IMAGE_OUTLINED,
                                            size=20,
                                            color=MUTED_COLOR,
                                        ),
                                    ),
                                ],
                            ),
                            ft.Row(
                                spacing=10,
                                controls=[
                                    _pill("更多灵感"),
                                    _pill("去发布", on_publish, primary=True),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )

    # ---------------------- 背景区（状态栏 → 三张小卡下沿）---------------------
    # 范围（用户指定）：**顶部顶到状态栏、底部盖住三张小卡**。为此：
    # - 左右**不收边** —— 外层不再铺内边距，图才能铺满屏宽；
    # - **不套 `SafeArea`** —— 套了图得从状态栏下面才开始画，顶不到 y=0；状态栏那一段
    #   改成算进它自己的上内边距（`top_inset`）；
    # - 内容到三张小卡为止（卡片也在图里，所以各段得有自己的底色才看得清）。
    #
    # 这一层只放**内容**；背景图与「清晰 → 模糊」由下面的 `background_region` 叠上去
    # （图挂在容器 `image=` 上，内容按自己撑高 —— 不写死高度，就不会溢出 / 留缝）。
    #
    # 这一层**不接 on_click**：整段背景可点的话，手指落在哪儿都算「换背景图」，太容易
    # 误触（用户反馈「区域还是很大」）。换背景图的入口收在账号卡片里那块空白上 ——
    # 见 `build_account_card(..., on_blank_tap=…)`。
    region_body = ft.Container(
        # 下边距要比圆角顶盖（`PANEL_TOP_RADIUS`）大 —— 顶盖压在图片最后那一段上，
        # 留出这 10px 是为了三张小卡不贴着顶盖。
        padding=ft.Padding.only(
            left=16,
            top=top_inset + 8,
            right=16,
            bottom=PANEL_TOP_RADIUS + 10,
        ),
        content=ft.Column(
            tight=True,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                # 顶栏：左边 ≡（打开设置页）、右边「编辑主页」（「数据」入口已去掉）。
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            ink=True,
                            tooltip="设置",
                            padding=ft.Padding.all(6),
                            on_click=lambda _: open_settings(),
                            content=ft.Icon(
                                ft.Icons.MENU, size=22, color=ON_IMAGE_COLOR
                            ),
                        ),
                        ft.Row(
                            tight=True,
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(
                                    height=28,
                                    alignment=ft.Alignment.CENTER,
                                    padding=ft.Padding.symmetric(
                                        horizontal=10
                                    ),
                                    border_radius=ft.BorderRadius.all(14),
                                    # 白描边的胶囊（压在图上）。
                                    border=ft.Border.all(1, ON_IMAGE_LINE),
                                    # 进「编辑资料」二级页（见 pages/edit_profile.py）。
                                    ink=True,
                                    tooltip="编辑资料",
                                    on_click=lambda _: open_edit_profile(),
                                    content=ft.Row(
                                        tight=True,
                                        spacing=4,
                                        vertical_alignment=(
                                            ft.CrossAxisAlignment.CENTER
                                        ),
                                        controls=[
                                            ft.Icon(
                                                ft.Icons.EDIT_OUTLINED,
                                                size=13,
                                                color=ON_IMAGE_COLOR,
                                            ),
                                            ft.Text(
                                                "编辑主页",
                                                size=12,
                                                color=ON_IMAGE_COLOR,
                                            ),
                                        ],
                                    ),
                                ),
                                # 原来「编辑主页」旁边还有一枚「数据」（柱状图）入口，
                                # 连同那一页与它的图表控件已按用户要求**整体删除**
                                # —— 这一格现在只剩「编辑主页」。
                            ],
                        ),
                    ],
                ),
                # ---- 个人信息 + 关注 / 粉丝：这两块贴紧一点 ----
                # 它们本来是一体的（头像 / 昵称，紧跟着「关注 / 粉丝 / 获赞与收藏」），
                # 外面那层 Column 通用的 12px 间距对它们太松 —— 单开一个 4px 的小列。
                ft.Column(
                    tight=True,
                    spacing=IDENTITY_STAT_GAP,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        # 背景图由整段铺上（见 background_region），这里不再单独铺一张；
                        # `on_image=True` → 卡片里的文字 / 头像框改白（压在图上看不清）；
                        # `on_blank_tap` → 昵称 / ID 右边那块空白（与头像同高）点了换背景图。
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=8),
                            content=build_account_card(
                                page,
                                open_login,
                                on_image=True,
                                on_blank_tap=open_background,
                            ),
                        ),
                        # 关注 / 粉丝 / 获赞与收藏：没有真实来源，先摆 0。
                        ft.Row(
                            spacing=STAT_GAP,
                            controls=[
                                _stat("0", "关注"),
                                _stat("0", "粉丝"),
                                _stat("0", "获赞与收藏"),
                            ],
                        ),
                    ],
                ),
                ft.Text(
                    "点击这里，填写简介",
                    size=INTRO_SIZE,
                    color=ON_IMAGE_MUTED,
                ),
                # 三张小卡：**在背景图里**（图一直铺到它们的下沿）。
                ft.Row(
                    spacing=QUICK_CARD_PADDING,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        quick_card("个人售卖", ft.Icons.STORE, "出闲置搞副业"),
                        quick_card("浏览记录", ft.Icons.HISTORY, "看过的笔记"),
                        quick_card("群聊", ft.Icons.GROUPS, "查看详情"),
                    ],
                ),
            ],
        ),
    )

    # 背景图 + 「顶部清晰 → 底部模糊」：
    # 图挂在**外层容器**的 `image=` 上（内容自己撑高，高度不用写死）；上面再叠一层磨砂带
    # —— `ft.Stack`：磨砂带在下（四边定位铺满），内容层在上（它决定整块的高度）。
    # 没设过图就什么都不叠，只有内容。
    decoration = background_decoration()
    background_region = (
        ft.Container(
            image=decoration,
            # 四层（下 → 上）：清晰→模糊 → 淡白纱 → **内容板圆角顶盖** → 内容。
            content=ft.Stack(
                controls=[
                    _progressive_blur(decoration),
                    _blur_veil(),
                    # 圆角顶盖放在这一层里：它压在图片的最后一小段上，圆角外的两块缺口
                    # 露的就是这张图。内容板（下一个列表项）里的标签条紧跟着它。
                    _panel_top_cap(),
                    region_body,
                ]
            ),
        )
        if decoration is not None
        else region_body
    )
    # ⚠️ 下拉手势**在这一层吃掉**：在图片上竖直拖拽什么都不做（页面不跟着动，也就不会
    # 露出白底）。
    #
    # 为什么只能这么做：Flet 1.0.1 没暴露滚动物理（既没有 `ScrollPhysics`，`ListView`
    # 上也没有 `physics` 字段），关不掉客户端那边的回弹 / 拉伸效果 —— 但手势能被内层
    # 抢下来：在图片这一层接住竖直拖拽，下面那个列表就不会被拖动。点按不受影响（这里
    # 没挂 on_tap），所以在下面的内容区照旧能滚。
    if decoration is not None:
        background_region = ft.GestureDetector(
            on_vertical_drag_start=lambda _: None,
            on_vertical_drag_update=lambda _: None,
            on_vertical_drag_end=lambda _: None,
            content=background_region,
        )

    return ft.Container(
        expand=True,
        bgcolor=MY_BG,
        # ⚠️ 这一层**不铺内边距、也不套 `SafeArea`**：套了背景图就顶不到状态栏、也铺不满
        # 左右。状态栏那一段由 background_region 自己用 `top_inset` 让开。
        # 里面两段都是**通栏**的（图片铺满屏宽；内容板靠那条通栏标签条到边），左右 16px
        # 各自在图 / 标签条内部让 —— 所以这层不再统一收边（原来那个 `side()` 已随之去掉）。
        content=ft.Column(
            expand=True,
            controls=[
                ft.ListView(
                    expand=True,
                    # 图片背景与内容板之间**不留缝**。
                    spacing=0,
                    scroll=ft.ScrollMode.HIDDEN,
                    padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
                    controls=[
                        background_region,
                        # 内容板：紧贴图片背景的下沿，通栏（标签条左右到边）。
                        sheet,
                    ],
                ),
            ],
        ),
    )
