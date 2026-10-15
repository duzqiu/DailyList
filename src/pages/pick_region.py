"""「选择你的地区」页（编辑地区页点「地区」进来）—— 照小红书那张图。

版式：顶栏（左「取消」+ 居中「选择你的地区」）→ 小节「定位到的位置」+ 一张白卡片
（蓝色定位图标 + 定位到的「中国 上海市 浦东新区」）→ 小节「全部」+ 一张白卡片
（国家列表，**有下级的行右边带一个 ›**）。

⚠️ 顶上定位那一段**只在最外层**（国家表那层）出现：往下进了省 / 市（二三级）就不再摆它 ——
用户已经在挑具体行政区了，再顶着一条定位只是白占地方（用户要求，见 `build_content`）。

点下去：
- **定位那一行** → 直接选它（和点一个国家一样，选完就退回编辑地区页）；
- **带 › 的行**（国家 / 省）→ 往下一级：同一页里换列表，标题变成当前层级，
  左上的「取消」同时换成「‹」（回上一级）；
- **不带 › 的行** → 到底了，把这一串交回去（`on_pick`），退回编辑地区页。

定位见 tools/location.py —— ⚠️ **flet 1.x 拿不到系统定位**（没有定位 Service、也没有
执行 JS 的口子），所以这里是 IP 定位：不需要权限，给到哪一级（省 / 市 / 区）就显示哪一级。
"""

from collections.abc import Callable
from functools import partial

import flet as ft

from tools import location, regions
from widgets.field_page import (
    CARD_GAP,
    CARD_SIDE,
    CHECK_SIZE,
    CHEVRON_COLOR,
    LABEL_COLOR,
    LABEL_SIZE,
    PAGE_BG,
    PLACEHOLDER_COLOR,
    ROW_HEIGHT,
    ROW_SIDE,
    TITLE_COLOR,
    TITLE_SIZE,
    card,
    row,
    section_label,
)
from widgets.layout import (
    BACK_HEIGHT,
    BACK_ICON_SIZE,
    BACK_OFFSET,
    BOTTOM_MENU_INSET,
    SUBPAGE_TITLE_COLOR,
    safe_update,
)

TITLE = "选择你的地区"
# 左上一格「取消」/「‹」的宽度。和返回按钮一样宽（标题才落在正中），又比它宽一点，
# 「取消」两个字不至于挤在边上。
HEAD_SIDE = 48
CANCEL_SIZE = 15
# 定位那一行的小节标题。
SPOT_SECTION = "定位到的位置"
ALL_SECTION = "全部"
SPOT_COLOR = "#2E7BFA"
SPOT_LOADING = "正在定位…"
SPOT_FAILED = "定位失败，点一下重试"
SPOT_ICON_SIZE = 18
SPOT_GAP = 6


def build_pick_region_page(
    page: ft.Page,
    go_back: Callable[[], None],
    on_pick: Callable[[str], None],
) -> ft.Control:
    """`go_back` 退回编辑地区页；`on_pick` 把选中的「中国 上海市 浦东新区」交回去。

    ⚠️ 这一页是**一次性**的：选完就退回去了，所以内部状态（走到哪一级、定位结果）
    都放在闭包里，不用往外传。
    """
    # 现在走到哪一级：空 = 国家表那层，["中国"] = 省那层…
    path: list[str] = []
    # 定位到的位置（树上的一串）；还没拿到 / 拿不到就是 `None`。
    spot: tuple[str, ...] | None = _to_path(location.cached())
    spot_failed = False

    header_holder = ft.Container()
    # 内容整只挂在它下面：每次重画都换一套全新的控件（见 `refresh`）。
    content_holder = ft.Container(expand=True)

    # ---------------------- 上下级 ----------------------

    def choose(target: tuple[str, ...]) -> None:
        """选定了：交回编辑地区页并退回去。"""
        on_pick(regions.label(target))
        go_back()

    def descend(target: tuple[str, ...]) -> None:
        path.append(target[-1])
        refresh()

    def up() -> None:
        if path:
            path.pop()
            refresh()

    # ---------------------- 定位 ----------------------

    def spot_row() -> ft.Control:
        """定位那一行：拿到就显示位置（可点选），没拿到就显示进度 / 失败。"""
        if spot is not None:
            text, color = regions.label(spot), LABEL_COLOR
            # `partial` 而不是 `lambda: choose(spot)`：免得被当成 E731。
            action: Callable[[], None] | None = partial(choose, spot)
        elif spot_failed:
            text, color, action = SPOT_FAILED, PLACEHOLDER_COLOR, retry_spot
        else:
            text, color, action = SPOT_LOADING, PLACEHOLDER_COLOR, None
        return ft.Container(
            height=ROW_HEIGHT,
            ink=action is not None,
            on_click=(lambda _, action=action: action()) if action else None,
            padding=ft.Padding.symmetric(horizontal=ROW_SIDE),
            content=ft.Row(
                spacing=SPOT_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        ft.Icons.LOCATION_ON, size=SPOT_ICON_SIZE, color=SPOT_COLOR
                    ),
                    ft.Text(
                        text,
                        size=LABEL_SIZE,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        color=color,
                    ),
                ],
            ),
        )

    async def find_spot(use_cache: bool = False) -> None:
        nonlocal spot, spot_failed
        result = await location.locate(use_cache=use_cache)
        spot = _to_path(result)
        spot_failed = spot is None
        refresh()

    def retry_spot() -> None:
        """点「定位失败，点一下重试」：丢掉缓存、回到「正在定位…」再打一次。"""
        nonlocal spot, spot_failed
        spot, spot_failed = None, False
        location.forget()
        refresh()
        page.run_task(find_spot, False)

    # ---------------------- 顶栏 ----------------------

    def build_header() -> ft.Control:
        """左上一格在「取消」和「‹」之间切换：进了下级就得能回上一级。"""
        if path:
            left = ft.Container(
                width=HEAD_SIDE,
                height=BACK_HEIGHT,
                alignment=ft.Alignment.CENTER_LEFT,
                ink=True,
                tooltip="返回上一级",
                on_click=lambda _: up(),
                content=ft.Icon(
                    ft.Icons.CHEVRON_LEFT,
                    size=BACK_ICON_SIZE,
                    color=SUBPAGE_TITLE_COLOR,
                    offset=ft.Offset(BACK_OFFSET, 0),
                ),
            )
            title = path[-1]
        else:
            left = ft.Container(
                width=HEAD_SIDE,
                height=BACK_HEIGHT,
                alignment=ft.Alignment.CENTER_LEFT,
                ink=True,
                on_click=lambda _: go_back(),
                content=ft.Text("取消", size=CANCEL_SIZE, color=TITLE_COLOR),
            )
            title = TITLE
        return ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                left,
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        title,
                        size=TITLE_SIZE,
                        weight=ft.FontWeight.BOLD,
                        color=TITLE_COLOR,
                    ),
                ),
                # 和左边那格等宽的占位，标题才落在正中。
                ft.Container(width=HEAD_SIDE),
            ],
        )

    # ---------------------- 列表 ----------------------

    def region_row(name: str) -> ft.Control:
        """一个国家 / 省 / 市：有下一级就带 ›（点它往下走），没有就直接选中它。"""
        target = (*path, name)
        if regions.children(target):
            trailing = ft.Icon(
                ft.Icons.CHEVRON_RIGHT, size=CHECK_SIZE, color=CHEVRON_COLOR
            )
            # ⚠️ `target=target`：不写就全都捕获到最后一个值（闭包晚绑定）。
            return row(name, trailing, lambda target=target: descend(target))
        return row(name, None, lambda target=target: choose(target))

    def build_content() -> ft.ListView:
        """按当前层级造一屏内容（含可滚列表）。

        换级时**整只换掉**（而不是改老控件的 `controls`）：新控件的滚动位置天然是 0，
        正好是换一屏内容想要的「回到顶部」—— 换级却停在上一屏的滚动位置，
        用户会以为点错了。不然就得调 `scroll_to`，那是个协程，还得 `run_task` 去 await
        （见 widgets/wheel.py 那个坑）。

        定位那一段**只摆在最外层**（`path` 为空）：进了二三级（省 / 市）就不带了（用户要求）。
        """
        # 空元组就是「这一层不摆定位」—— 用 `*` 铺进下面那份 controls 里。
        spot_block: list[ft.Control] = (
            [section_label(SPOT_SECTION), card([spot_row()])] if not path else []
        )
        return ft.ListView(
            expand=True,
            spacing=CARD_GAP,
            scroll=ft.ScrollMode.HIDDEN,
            padding=ft.Padding.only(
                left=CARD_SIDE, right=CARD_SIDE, top=6, bottom=BOTTOM_MENU_INSET
            ),
            controls=[
                ft.Column(
                    spacing=CARD_GAP,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        *spot_block,
                        section_label(ALL_SECTION),
                        card(
                            [
                                region_row(name)
                                for name in regions.children(tuple(path))
                            ]
                        ),
                    ],
                )
            ],
        )

    def refresh() -> None:
        """按当前层级重画整页（顶栏 + 内容都换新）。"""
        header_holder.content = build_header()
        content_holder.content = build_content()
        safe_update(header_holder, content_holder)

    refresh()
    # 缓存里没有就先摆「正在定位…」，接口回来再重画（`find_spot` 自己会 refresh）。
    if spot is None:
        page.run_task(find_spot, True)

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
                        content=header_holder,
                    ),
                    content_holder,
                ],
            ),
        ),
    )


def _to_path(spot: location.Location | None) -> tuple[str, ...] | None:
    """定位结果 → 地区树上的一串；认不出来给 `None`。"""
    if spot is None:
        return None
    return regions.match_location(
        country=spot.country,
        province=spot.province,
        city=spot.city,
        district=spot.district,
    )
