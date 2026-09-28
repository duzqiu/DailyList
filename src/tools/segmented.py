"""横向分段开关：年 / 月 / 周 的胶囊，和新增待办分类那款方一点的。

「数据」页三张卡（数据统计、分类占比、待办趋势）各有一个 年/月/周 开关。它原来用的是
`popup_select` 的下拉触发器：先点按钮，再在弹出的白色面板里选一项。胶囊把三档直接摊在
卡片的标题行里，点一下就切完，也没有要弹出的面板。

选中项用和首页日期卡片一样的「选中蓝」（`DATE_SELECTED_BG`），其余两档只是卡片上的灰色
文字，所以一眼能看出当前是哪一档。选中态由控件自己维护，调用方不必像下拉触发器那样另外
准备一个 `Text` 来显示当前值。

新增待办弹窗的三个分类也用它：那里传 `color_of`，选中项就填自己的分类色（红 / 黄 / 绿），
而不是统一的「选中蓝」；字色由 `readable_ink` 跟着底色挑深浅。分类那排用方一点的
那款（`square=True`）：圆角收小、两档之间立一条竖线，一眼就和 年/月/周 的胶囊区分开。
"""

from collections.abc import Callable

import flet as ft

from tools.layout import DATE_SELECTED_BG, readable_ink

# 单个选项的高度。整条胶囊 = 这个高度 + 内边距 + 边框，30px 出头，和卡片标题
# （15pt 粗体）同高，不会把标题行撑起来。
SEGMENT_TILE_HEIGHT = 24
# 胶囊四周的内边距：选中项四周露出的那条白边。
SEGMENT_PAD = 2
# 两个选项之间的缝隙，避免选中项的圆角贴到隔壁。
SEGMENT_GAP = 2
SEGMENT_BORDER_WIDTH = 1
# 胶囊是圆的：半径取整条高度的一半；选中项同理。
SEGMENT_RADIUS = (
    SEGMENT_TILE_HEIGHT + 2 * SEGMENT_PAD + 2 * SEGMENT_BORDER_WIDTH
) / 2
SEGMENT_TILE_RADIUS = SEGMENT_TILE_HEIGHT / 2
# 方的那一款（新增待办的分类）：圆角收小、两档之间立一条竖线把选项分开。里外两级
# 圆角照旧同心 —— 外圈减掉内边距和边框，就是选项自己的圆角（选中项也用它）。
SEGMENT_SQUARE_RADIUS = 8
SEGMENT_SQUARE_TILE_RADIUS = (
    SEGMENT_SQUARE_RADIUS - SEGMENT_PAD - SEGMENT_BORDER_WIDTH
)
# 两档之间那条竖线：细、短、浅灰，两边各留一个 `SEGMENT_GAP` 的空。
SEGMENT_DIVIDER_WIDTH = 1
SEGMENT_DIVIDER_HEIGHT = 14
SEGMENT_DIVIDER_COLOR = "#E2E8F0"
# 一档只有一个汉字，左右各 10px 就有胶囊的手感了。
SEGMENT_TILE_PAD = ft.Padding.symmetric(horizontal=10)
SEGMENT_TEXT_SIZE = 12
# 胶囊底：从纯白降一档的浅灰白。比「待办」卡片的 #F1F5F9 再亮一格（不然摆在卡片上
# 的 年/月/周 胶囊会糊进卡面），但也不是刺眼的白。
SEGMENT_BG = "#F8FAFC"
SEGMENT_BORDER = "#E2E8F0"
SEGMENT_ACTIVE_BG = DATE_SELECTED_BG
# 未选中项自己不画底色，露出来的就是胶囊那层浅灰白。
SEGMENT_TILE_BG = "#00000000"
SEGMENT_TEXT_COLOR = "#64748B"
SEGMENT_ACTIVE_TEXT_COLOR = "#172554"


def build_segmented(
    options: list[tuple[str, str]],
    value: str,
    on_pick: Callable[[str], None],
    color_of: Callable[[str], str] | None = None,
    square: bool = False,
) -> ft.Container:
    """横向胶囊开关：`options` 是 `[(key, 标签)]`，`value` 是当前选中项的 key。

    点击先把胶囊切过去再回调 `on_pick`，所以切换是立刻可见的；把选中态画在这里，
    调用方就只需要关心数据本身。点当前这一档什么也不做，选中项永远留一个。

    `color_of` 给某一档单独指定选中底色（弹窗里的分类用它填红 / 黄 / 绿）；不传就
    统一用「选中蓝」。

    `square=True` 换方一点的那一款：圆角从「半个高度」收小到 `SEGMENT_SQUARE_RADIUS`
    （选中项同一套圆角），并在两档之间立一条竖线。
    """
    radius = SEGMENT_SQUARE_RADIUS if square else SEGMENT_RADIUS
    tile_radius = (
        SEGMENT_SQUARE_TILE_RADIUS if square else SEGMENT_TILE_RADIUS
    )
    labels: dict[str, ft.Text] = {}
    tiles: dict[str, ft.Container] = {}
    current = {"key": value}

    def active_bg(key: str) -> str:
        """选中项的底色：默认「选中蓝」，也可以一项一色。"""
        return SEGMENT_ACTIVE_BG if color_of is None else color_of(key)

    def paint(active: str) -> None:
        for key, tile in tiles.items():
            chosen = key == active
            bg = active_bg(key)
            tile.bgcolor = bg if chosen else SEGMENT_TILE_BG
            ink = (
                SEGMENT_ACTIVE_TEXT_COLOR
                if color_of is None
                else readable_ink(bg)
            )
            labels[key].color = ink if chosen else SEGMENT_TEXT_COLOR
            labels[key].weight = (
                ft.FontWeight.BOLD if chosen else ft.FontWeight.NORMAL
            )

    def select(key: str) -> None:
        # 点当前这一档什么也不做，免得白刷一遍。
        if key == current["key"]:
            return
        current["key"] = key
        paint(key)
        for tile in tiles.values():
            tile.update()
        on_pick(key)

    for key, label in options:
        labels[key] = ft.Text(label, size=SEGMENT_TEXT_SIZE)
        tiles[key] = ft.Container(
            height=SEGMENT_TILE_HEIGHT,
            border_radius=ft.BorderRadius.all(tile_radius),
            padding=SEGMENT_TILE_PAD,
            alignment=ft.Alignment.CENTER,
            # 水波纹要跟着圆角走，所以用 Container 自带的 ink 而不是 IconButton。
            ink=True,
            content=labels[key],
            on_click=lambda _, key=key: select(key),
        )

    def divider() -> ft.Container:
        """两档之间那条竖线（只有方款才画）。"""
        return ft.Container(
            width=SEGMENT_DIVIDER_WIDTH,
            height=SEGMENT_DIVIDER_HEIGHT,
            bgcolor=SEGMENT_DIVIDER_COLOR,
        )

    rows: list[ft.Control] = []
    for index, tile in enumerate(tiles.values()):
        if index and square:
            rows.append(divider())
        rows.append(tile)
    paint(value)
    return ft.Container(
        bgcolor=SEGMENT_BG,
        border=ft.Border.all(SEGMENT_BORDER_WIDTH, SEGMENT_BORDER),
        border_radius=ft.BorderRadius.all(radius),
        padding=ft.Padding.all(SEGMENT_PAD),
        content=ft.Row(
            tight=True,
            spacing=SEGMENT_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=rows,
        ),
    )