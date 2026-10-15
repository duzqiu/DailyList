"""底栏那颗「+」弹出来的**发布面板**（照小红书那张图）。

版式：一张白面板从底下滑上来，三个**居中**的入口 ——「从相册选择」/「相机」/「写文字」，
「相机」那行底下多一行小字「拍摄与直播」；每条入口之间一条浅浅的分隔线；再往下是一条浅灰
粗带，最后才是「取消」。上面两个角是圆的（下面贴着屏幕底边），弹出来时后面那层页面压暗。

⚠️ 为什么用 `ft.BottomSheet`：它在 flet 1.x 里也是 `DialogControl`，`page.show_dialog`
直接收 ——「从底下滑上来 + 点外面 / 下拉能关 + 后面压暗」都是客户端自带的（和
widgets/wheel.py 那个选生日的面板同一个做法），不用自己搭一层遮罩。

**面板自己什么都不做**：点哪一项都是先把面板收掉，再把名字交回给调用方（`on_choose`）——
去哪儿、提示什么由调用方决定（见 pages/navigation.py 的 `choose_publish`：目前只有
「写文字」有去处，进的是「写想法」页）。
"""

from collections.abc import Callable

import flet as ft

# 面板：白底、只圆上面两个角（下面贴着屏幕底边），弹出来时后面压暗一档。
SHEET_RADIUS = 16
SHEET_BG = "#FFFFFF"
BARRIER_COLOR = "#33000000"
# 一条入口：普通行那么高，带小字那行（「相机」）高一些；文字居中、近黑。
ROW_HEIGHT = 58
ROW_TALL_HEIGHT = 76
ITEM_SIZE = 16
ITEM_COLOR = "#1F1F1F"
# 小字（「拍摄与直播」）：比正文小两档、浅灰，和上面那行大字隔一点点。
HINT_SIZE = 11
HINT_COLOR = "#9CA3AF"
HINT_GAP = 2
CAMERA_HINT = "拍摄与直播"
# 三个入口的名字。面板把选中的**名字**交回调用方（见 `on_choose`），所以这几个字同时也是
# 调用方认的那几个 key（「写文字」已经被接到「写想法」页了，见 pages/navigation.py 的
# `choose_publish`）—— 以后加 / 改入口，两边一起改。
ALBUM_LABEL = "从相册选择"
CAMERA_LABEL = "相机"
WRITE_LABEL = "写文字"
# 入口之间那条浅灰分隔线（画在各条的**下边**）。
LINE_COLOR = "#F0F0F0"
LINE_WIDTH = 1
# 「取消」上面那条浅灰粗带（照那张图：把「取消」和上面的入口分开）。
BAND_COLOR = "#F5F5F5"
BAND_HEIGHT = 8
CANCEL_LABEL = "取消"
CANCEL_HEIGHT = 58
CANCEL_SIZE = 16
CANCEL_COLOR = "#1F1F1F"
# 面板最下面留的白：让开系统那条「小横条」/ 虚拟导航键。量不到屏内边距时退回这个值 ——
# 那点白是面板自己的底色，多留一点也比让「取消」贴着屏幕边强。
BOTTOM_MIN_INSET = 12


def build_publish_sheet(
    page: ft.Page,
    on_choose: Callable[[str], None],
) -> ft.BottomSheet:
    """发布面板。`on_choose` 收到被选中的那项名字（「从相册选择」/「相机」/「写文字」）。

    面板自己只负责**收摊**：点任一项都是先 `pop_dialog()` 再交名字（和「取消」一样干脆），
    免得提示浮出来的时候面板还挂在上面挡着 —— 提示那句话由调用方给。
    """

    def pick(name: str) -> None:
        """选了一项：先收掉面板，再把名字交回调用方。"""
        page.pop_dialog()
        on_choose(name)

    def entry(label: str, height: int, hint: str = "") -> ft.Control:
        """一条入口：居中一行大字（+ 可选的一行小字），下边一条浅灰线。"""
        return ft.Container(
            height=height,
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=lambda _: pick(label),
            border=ft.Border.only(
                bottom=ft.BorderSide(LINE_WIDTH, LINE_COLOR)
            ),
            content=ft.Column(
                tight=True,
                spacing=HINT_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(label, size=ITEM_SIZE, color=ITEM_COLOR),
                    *(
                        [ft.Text(hint, size=HINT_SIZE, color=HINT_COLOR)]
                        if hint
                        else []
                    ),
                ],
            ),
        )

    return ft.BottomSheet(
        # 那张图上没有顶部那条小横杠。
        show_drag_handle=False,
        dismissible=True,
        draggable=True,
        barrier_color=BARRIER_COLOR,
        bgcolor=SHEET_BG,
        # 只圆上面两个角：下面贴着屏幕底边。
        shape=ft.RoundedRectangleBorder(
            radius=ft.BorderRadius.only(
                top_left=SHEET_RADIUS, top_right=SHEET_RADIUS
            )
        ),
        content=ft.Column(
            tight=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                entry(ALBUM_LABEL, ROW_HEIGHT),
                entry(CAMERA_LABEL, ROW_TALL_HEIGHT, hint=CAMERA_HINT),
                entry(WRITE_LABEL, ROW_HEIGHT),
                ft.Container(height=BAND_HEIGHT, bgcolor=BAND_COLOR),
                ft.Container(
                    height=CANCEL_HEIGHT,
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    #「取消」什么也不交回：收掉面板就完了。
                    on_click=lambda _: page.pop_dialog(),
                    content=ft.Text(
                        CANCEL_LABEL, size=CANCEL_SIZE, color=CANCEL_COLOR
                    ),
                ),
                ft.Container(height=_bottom_inset(page)),
            ],
        ),
    )


def _bottom_inset(page: ft.Page) -> int:
    """面板最下面让开多少：系统那条小横条 / 虚拟导航键的高度（见 `BOTTOM_MIN_INSET`）。

    ⚠️ 和「我的」页量状态栏那一段是同一个路子（`page.media.view_padding`）：拿不到就给 0，
    这里再和最小值取大 —— 不会算出个负数把面板压短。
    """
    padding = getattr(page.media, "view_padding", None)
    bottom = getattr(padding, "bottom", 0) or 0
    return max(BOTTOM_MIN_INSET, int(bottom))
