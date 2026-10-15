"""底部「滑动样式」的滚轮（编辑生日页选日期用）。

**为什么自己搭、不用 `ft.CupertinoPicker`**：项目早先试过那个原生滚轮，**滚动之后
`on_change` 根本不回来**，选中的日期就这么丢了（见 widgets/pickers.py 开头那段 ——
那之后一直退回系统弹窗选择器）。这一次要的是「底部滑动」，所以自己用 `ft.ListView` 算：

- 每行等高（`item_extent`），`pixels / ROW_HEIGHT` 四舍五入就是当前停在第几行；
- 滚动时高亮实时跟着走（正中那行变大变黑，两边依次变淡），和滚轮一个观感；
- **滚停之后**（`SNAP_DELAY` 内没再收到滚动事件）把这一列吸到整行上，不会停在半格；
- **点一行**也能选中并居中 —— 万一某个平台收不到滚动事件，这条路仍然选得出值，
  绝不会出现「选了却没生效」。

所以它比现成控件啰嗦，换的是**选中的值不会丢**。

⚠️ **打开时怎么落到进来时那个值上**：flet 1.x 的 `ScrollableControl.scroll_to` 是
**协程**，必须 await 才发得出去 —— 写成同步调用不报错、客户端什么也收不到，滚轮就
永远停在第 0 行（「生日点开默认选在 1900 年 1 月 1 日」就是这个，见 `_scroll_to`）。

⚠️ 面板自己不用 `page.show_dialog`（那是弹窗）。这里的 `Wheel` 只是零件，
底部面板由调用方用 `ft.BottomSheet` 弹出（见 pages/edit_birthday.py）。
"""

import asyncio
from collections.abc import Callable

import flet as ft

from widgets.layout import is_attached, safe_update

# 一行的基准高度。文字字号会在这个高度里变化，但行高不变 —— `pixels / ROW_HEIGHT`
# 才能直接当行号用（行高一变，「停在第几行」就不好算了）。
ROW_HEIGHT = 34
# 视口里露出几行（中间那行是选中的，上下各留两行）。
VISIBLE_ROWS = 5
VIEW_HEIGHT = ROW_HEIGHT * VISIBLE_ROWS

CENTER_SIZE = 20
NEAR_SIZE = 17
FAR_SIZE = 15
CENTER_COLOR = "#111111"
NEAR_COLOR = "#8C8C8C"
FAR_COLOR = "#C4C4C4"

# 滚停判定：这么久没再收到滚动事件就当停了，把这一列吸到整行上。
SNAP_DELAY = 0.12
SNAP_MS = 140
# 弹出来时把选中行摆到正中：控件要等落到界面上才滚得动，所以隔一小会儿**试几次**
# 兜底 —— 面板滑上来要两百多毫秒，只试一次不一定赶得上；已经在位子上时再滚一次
# 没有副作用，用户一上手滚动就停手。
CENTER_DELAY = 0.08
CENTER_TRIES = 5


SHEET_RADIUS = 16
SHEET_BG = "#FFFFFF"
HEADER_HEIGHT = 48
HEADER_SIZE = 16
TITLE_COLOR = "#111111"
CANCEL_COLOR = "#8C8C8C"
# 「保存」用底栏那颗「+」同一个强调红（widgets/field_page.py 的 ACCENT_RED）。
CONFIRM_COLOR = "#FF2442"
# 正中那一行的浅色高亮带（照那张图：选中行底下有一条浅灰圆角）。
BAND_COLOR = "#F1F5F9"
BAND_RADIUS = 8
# 面板弹出时把后面的页面压暗（BottomSheet 自带的遮罩色）。
BARRIER_COLOR = "#33000000"


def build_picker_sheet(
    title: str,
    wheels: list["Wheel"],
    on_cancel: Callable[[], None],
    on_confirm: Callable[[], None],
) -> ft.BottomSheet:
    """底部滑出来的选择面板：上面一行「取消 ｜ 标题 ｜ 保存」，下面并排几列滚轮。

    用 `ft.BottomSheet`（flet 1.x 里它也是 `DialogControl`，`page.show_dialog` 直接收），
    所以它是**从底下滑上来的面板**、不是居中的弹窗：后面的页面压暗，点外面 / 下拉能关。
    """
    band = ft.Container(
        left=0,
        right=0,
        top=(VIEW_HEIGHT - ROW_HEIGHT) / 2,
        height=ROW_HEIGHT,
        bgcolor=BAND_COLOR,
        border_radius=ft.BorderRadius.all(BAND_RADIUS),
    )
    columns = ft.Row(
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(expand=True, content=wheel.view) for wheel in wheels
        ],
    )
    return ft.BottomSheet(
        # 那三张图里都没有顶部那条小横杠。
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
        content=ft.Container(
            padding=ft.Padding.only(left=12, right=12, bottom=8),
            content=ft.Column(
                tight=True,
                spacing=0,
                controls=[
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=64,
                                height=HEADER_HEIGHT,
                                alignment=ft.Alignment.CENTER_LEFT,
                                ink=True,
                                on_click=lambda _: on_cancel(),
                                content=ft.Text(
                                    "取消", size=HEADER_SIZE, color=CANCEL_COLOR
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(
                                    title,
                                    size=HEADER_SIZE,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                            ),
                            ft.Container(
                                width=64,
                                height=HEADER_HEIGHT,
                                alignment=ft.Alignment.CENTER_RIGHT,
                                ink=True,
                                on_click=lambda _: on_confirm(),
                                content=ft.Text(
                                    "保存", size=HEADER_SIZE, color=CONFIRM_COLOR
                                ),
                            ),
                        ],
                    ),
                    ft.Stack(
                        height=VIEW_HEIGHT,
                        # 高亮带摆在**列表下面**（后画会盖住字，也会挡掉点击）。
                        controls=[band, columns],
                    ),
                ],
            ),
        ),
    )


class Wheel:
    """一列滚轮。`values` 是这一列的显示文案（「2026年」/「10月」/「15日」）。

    `on_change(index)` 在选中行**变了**之后叫一次（滚动、点选都算），用来联动别的列
    （年月一变，「日」那一列的长度要跟着变）。

    用法：`Wheel(page, values, index).view` 摆进面板；确认时读 `.index`。
    """

    def __init__(
        self,
        page: ft.Page,
        values: list[str],
        index: int,
        on_change: Callable[[int], None] | None = None,
    ) -> None:
        self._page = page
        self._values = list(values)
        self._index = self._clamp(index)
        self._on_change = on_change
        self._labels: list[ft.Text] = []
        # 滚停任务的「期号」：期号一变，早先排的那个就作废（用户又滚了）。
        self._token = 0
        # 用户碰过没有（碰过了就别再替他归位，也别把「刚铺开」那条杂音当成他滚的）。
        self._touched = False
        self.view = ft.ListView(
            height=VIEW_HEIGHT,
            # 每行等高：行号 = pixels / ROW_HEIGHT，直接四舍五入。
            item_extent=ROW_HEIGHT,
            spacing=0,
            scroll=ft.ScrollMode.HIDDEN,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            # 上下各留两行：第一行 / 最后一行也能滚到正中间。
            padding=ft.Padding.symmetric(
                vertical=ROW_HEIGHT * (VISIBLE_ROWS - 1) // 2
            ),
            on_scroll=self._on_scroll,
            controls=[],
        )
        self._build()

    # ---------------------- 对外 ----------------------

    @property
    def index(self) -> int:
        """现在停在（选中）第几行。"""
        return self._index

    def select(self, index: int) -> None:
        """点某一行：选中它，并把它挪到正中间。"""
        index = self._clamp(index)
        changed = index != self._index
        self._index = index
        self._paint()
        if changed and self._on_change is not None:
            self._on_change(index)
        # 用户自己动的：撤掉还没落地的滚停任务，直接归位。
        self._token += 1
        self._snap()

    def set_values(self, values: list[str], index: int) -> None:
        """换一列选项（「日」会因为年月不同而变长变短），尽量停在原来的位置。"""
        values = list(values)
        if values == self._values:
            if self._clamp(index) != self._index:
                self.select(index)
            return
        self._values = values
        self._index = self._clamp(index)
        self._build()

    def center(self) -> None:
        """把选中行摆到正中间（面板刚出来时调；没动画，也不会打扰已经动手的用户）。"""
        if self._touched or not is_attached(self.view):
            return
        self._scroll_to(self._index * ROW_HEIGHT, duration=0)

    def center_when_ready(self) -> None:
        """等控件落到界面上再归位（自己排一个任务试几次，见 `CENTER_TRIES`）。

        控件刚建出来时还不在页面上，`scroll_to` 发不出去（见 `_scroll_to`），所以不能
        当场就滚 —— 隔一小会儿试，试几次兜底。
        """

        async def attempt() -> None:
            for _ in range(CENTER_TRIES):
                await asyncio.sleep(CENTER_DELAY)
                if self._touched:
                    return
                self.center()

        self._page.run_task(attempt)

    # ---------------------- 内部 ----------------------

    def _clamp(self, index: int) -> int:
        return max(0, min(int(index), len(self._values) - 1))

    def _build(self) -> None:
        self._labels = [
            ft.Text(
                "",
                size=CENTER_SIZE,
                weight=ft.FontWeight.BOLD,
                color=CENTER_COLOR,
                no_wrap=True,
            )
            for _ in self._values
        ]
        self.view.controls = [
            ft.Container(
                height=ROW_HEIGHT,
                alignment=ft.Alignment.CENTER,
                # 点一行也能选中 —— 滚动事件万一收不到，值仍然选得出来。
                on_click=lambda _, position=position: self.select(position),
                content=self._labels[position],
            )
            for position in range(len(self._values))
        ]
        self._paint()

    def _paint(self) -> None:
        """按「离正中多远」给每行上样式：正中一行最大最深，越远越小越淡。"""
        for position, value in enumerate(self._values):
            distance = abs(position - self._index)
            if distance == 0:
                size, weight, color = (
                    CENTER_SIZE,
                    ft.FontWeight.BOLD,
                    CENTER_COLOR,
                )
            elif distance == 1:
                size, weight, color = (
                    NEAR_SIZE,
                    ft.FontWeight.NORMAL,
                    NEAR_COLOR,
                )
            else:
                size, weight, color = (
                    FAR_SIZE,
                    ft.FontWeight.NORMAL,
                    FAR_COLOR,
                )
            label = self._labels[position]
            label.value = value
            label.size = size
            label.weight = weight
            label.color = color
        safe_update(*self._labels)

    def _on_scroll(self, event: ft.OnScrollEvent) -> None:
        self._touched = True
        pixels = event.pixels or 0
        index = self._clamp(round(pixels / ROW_HEIGHT))
        if index != self._index:
            self._index = index
            self._paint()
            if self._on_change is not None:
                self._on_change(index)
        self._schedule_snap(pixels)

    def _schedule_snap(self, pixels: float) -> None:
        """滚停之后把这一列吸到整行上（已经在整行上就不用排了）。"""
        if abs(pixels - self._index * ROW_HEIGHT) < 1:
            return
        self._token += 1
        token = self._token

        async def settle() -> None:
            await asyncio.sleep(SNAP_DELAY)
            # 期间又滚了（期号变了）：这一轮作废，交给后一轮。
            if token == self._token:
                self._snap()

        self._page.run_task(settle)

    def _snap(self) -> None:
        self._scroll_to(self._index * ROW_HEIGHT, duration=SNAP_MS)

    def _scroll_to(self, offset: float, duration: int) -> None:
        if not is_attached(self.view):
            return  # 面板已经关掉了：没什么可滚

        # ⚠️ flet 1.x 里 `ScrollableControl.scroll_to` 是 **async** 的（见
        # flet/controls/scrollable_control.py）。写成同步调用只会造出一个没人 await 的
        # 协程对象：服务端不报错、客户端什么都收不到，滚轮于是永远停在第 0 行 ——
        # 「生日点开默认 1900 年 1 月 1 日」的真凶就是这一句。交给 run_task 去 await。
        async def run() -> None:
            try:
                await self.view.scroll_to(offset=offset, duration=duration)
            except Exception:  # noqa: BLE001
                # 还没布局出可滚区域之类：归位失败不值得把界面炸掉，下次滚动会再试。
                pass

        self._page.run_task(run)
