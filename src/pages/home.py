from collections.abc import Callable
from datetime import date, timedelta

import flet as ft

from tools import db
from tools.categories import CATEGORIES
from tools.countdown_form import open_countdown_form
from tools.layout import (
    BOTTOM_MENU_INSET,
    DATE_SELECTED_BG,
    SKY_BLUE,
    UNSELECTED_CARD_BG,
    page_gradient,
    text_width,
)
from tools.todo_form import open_todo_form
from tools.todo_timeline import build_todo_row, sorted_todos

# The floating add button is a sky-blue glass tile: no border ring, and a
# translucent fill (60%) so the blur behind it shows through.
ADD_BUTTON_BG = "#99" + SKY_BLUE[1:]
# A round tile, lifted clear of the floating menu bar.
ADD_BUTTON_SIZE = 52
ADD_BUTTON_LIFT = 10
# 「+」不直接开新增待办：先弹一块毛玻璃小面板，里面是「新增待办 / 新增倒数日」
# 两条入口，选完才开对应的弹窗。面板右下角对齐按钮、缩放原点也放在那一角
# （`CHOOSE_ANCHOR`），看起来就是从这个按钮里长出来的。
CHOOSE_PANEL_GAP = 10
CHOOSE_PANEL_RADIUS = 16
# 奶白毛玻璃：半透明白 + Blur 20，和「+」按钮同一套做法；多一条亮边，面板压在
# 列表上时才看得出边界。
CHOOSE_PANEL_BG = "#B3FFFFFF"
CHOOSE_PANEL_BORDER = "#99FFFFFF"
CHOOSE_PANEL_PADDING = ft.Padding.symmetric(horizontal=6, vertical=6)
CHOOSE_OPTION_HEIGHT = 34
CHOOSE_OPTION_RADIUS = 10
CHOOSE_OPTION_PADDING = ft.Padding.symmetric(horizontal=10)
CHOOSE_OPTION_GAP = 2
CHOOSE_ICON_SIZE = 18
CHOOSE_ICON_GAP = 8
CHOOSE_TEXT_SIZE = 13
CHOOSE_TEXT_COLOR = "#172554"
# 面板宽度按最长的一条入口量出来，免得「新增倒数日」贴着面板右边缘。
CHOOSE_LABELS = ("新增待办", "新增倒数日")
CHOOSE_PANEL_WIDTH = (
    CHOOSE_PANEL_PADDING.left
    + CHOOSE_OPTION_PADDING.left
    + CHOOSE_ICON_SIZE
    + CHOOSE_ICON_GAP
    + max(text_width(label, CHOOSE_TEXT_SIZE) for label in CHOOSE_LABELS)
    + CHOOSE_OPTION_PADDING.right
    + CHOOSE_PANEL_PADDING.right
)
# 展开 / 收起：缩放（从按钮那一角）+ 淡入淡出，收起就是回到这个起点。
CHOOSE_GROW_MS = 200
CHOOSE_FADE_MS = 160
CHOOSE_START_SCALE = 0
CHOOSE_ANCHOR = ft.Alignment.BOTTOM_RIGHT
# 顶部日期条：今天排第一个，往后连着 7 天（过去的日子不再列出来）。
DATE_STRIP_DAYS = 7
# The day badges stay round: a single glyph (「今」) keeps the plain circle while
# a whole date (「09.28」) widens it into a short pill. The picked day - today
# when the app opens - takes DATE_SELECTED_BG (shared with the 日历 grid and the
# dialog calendars, see tools/layout.py); every other day, today included, stays
# on the neutral card colour. Clicking never repaints the weekday or the date.
DATE_TEXT_COLOR = "#172554"
DATE_WEEKDAY_COLOR = "#64748B"
# The seven day columns share the strip's width: every column is an expanding
# child of a `Row`, so the free space is split evenly and the strip fills the
# screen on any phone width instead of leaving a gap after the last column.
DATE_CARD_SPACING = 8
DATE_CARD_HEIGHT = 56
DATE_CARD_TOP_PADDING = 2
# Weekday and date are stacked: the weekday is a plain grey label, the date
# (「今」today, 「09.28」otherwise) sits inside its own round badge.
DATE_WEEKDAY_SIZE = 11
DATE_DAY_SIZE = 12
DATE_BADGE_SIZE = 34
# 徽标左右各留一点空隙，「09.28」才不会顶到胶囊边。「今」只有一个字，宽度取
# 不满，徽标就还是一个正圆。
DATE_BADGE_PAD_X = 3
DATE_COLUMN_SPACING = 4
PAGE_SIDE_PADDING = 24
# 日期条和下面待办列表之间那条灰线：1px，比卡片描边更淡一档的浅灰。
STRIP_DIVIDER_COLOR = "#F1F5F9"
STRIP_DIVIDER_THICKNESS = 1


def date_card_label(day: date, today: date) -> str:
    """「今」for today, otherwise the date as 「09.28」 (month.day, padded)."""
    return "今" if day == today else f"{day.month:02d}.{day.day:02d}"


def date_badge_width(label: str) -> float:
    """Width of a day badge: a circle for one glyph, a short pill for a date.

    Every column of the strip gets the same room, so 「09.28」 is measured
    instead of guessed: `text_width` is the project's own estimate, and a
    single glyph such as 「今」 still comes out at DATE_BADGE_SIZE - a circle.
    """
    text = text_width(label, DATE_DAY_SIZE) + DATE_BADGE_PAD_X * 2
    return max(DATE_BADGE_SIZE, text)


def date_badge_bg(is_picked: bool) -> str:
    """Background of a day badge - the one rule the strip and the month share.

    The picked day takes the blue; every other day - today included - stays on
    the neutral card colour.
    """
    return DATE_SELECTED_BG if is_picked else UNSELECTED_CARD_BG


def build_date_badge(
    label: str, bgcolor: str, extra: ft.Control | None = None
) -> ft.Control:
    """The round day badge: same height, colours and face on both pages.

    The home strip passes nothing extra; a caller may hand over an `extra`
    control, which is drawn under the date inside the same badge.
    """
    number = ft.Text(
        label,
        size=DATE_DAY_SIZE,
        weight=ft.FontWeight.BOLD,
        color=DATE_TEXT_COLOR,
        # 宽度已经按 `date_badge_width` 算好，日期再折成两行就难看了。
        no_wrap=True,
    )
    return ft.Container(
        width=date_badge_width(label),
        height=DATE_BADGE_SIZE,
        # 半径取半个高度：宽度撑开是胶囊，只剩一个「今」时还是正圆。
        border_radius=ft.BorderRadius.all(DATE_BADGE_SIZE / 2),
        bgcolor=bgcolor,
        alignment=ft.Alignment.CENTER,
        content=(
            number
            if extra is None
            else ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=1,
                controls=[number, extra],
            )
        )
    )


def group_todos_by_day(
    todos: list[db.Todo],
) -> dict[date, dict[str, list[db.Todo]]]:
    grouped: dict[date, dict[str, list[db.Todo]]] = {}
    for todo in todos:
        day = grouped.setdefault(todo.due_date, {})
        day.setdefault(todo.category, []).append(todo)
    return grouped


def build_home_page(
    page: ft.Page,
    set_menu_visible: Callable[[bool], None],
    open_data: Callable[[], None],
) -> ft.Control:
    # 今天排在日期条的第一个（徽标写「今」），往后连着 DATE_STRIP_DAYS 天 ——
    # 待办页只看今天和接下来的这几天，过去的日子不再列。
    today = date.today()
    dates = [today + timedelta(days=offset) for offset in range(DATE_STRIP_DAYS)]
    today_index = 0
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    todos_by_day = group_todos_by_day(db.list_todos(dates))
    selected_index = today_index
    date_selector = ft.Row(spacing=DATE_CARD_SPACING)
    todo_content = ft.ListView(
        expand=True,
        # 行之间几乎不留缝，短竖线上下相接才像一条轴。
        spacing=2,
        scroll=ft.ScrollMode.HIDDEN,
        padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
    )

    def reload_todos() -> None:
        nonlocal todos_by_day
        todos_by_day = group_todos_by_day(db.list_todos(dates))

    def delete_todo(todo_id: int) -> None:
        db.delete_todo(todo_id)
        reload_todos()
        select_date(selected_index)

    def build_todo_item(todo: db.Todo, first: bool = False) -> ft.Control:
        """一行时间轴：点一下切换完成，左滑编辑 / 删除（共用控件）。"""

        def toggle_todo(item: db.Todo) -> None:
            db.set_done(item.id, not item.done)
            reload_todos()
            render_todos(selected_index)
            todo_content.update()

        return build_todo_row(
            todo,
            first=first,
            on_click=toggle_todo,
            on_delete=lambda item: delete_todo(item.id),
            on_edit=lambda item: edit_todo(item.id),
        )

    def build_empty_hint() -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=ft.BorderRadius.all(12),
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, "#E2E8F0"),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(
                        ft.Icons.EVENT_AVAILABLE,
                        size=20,
                        color="#94A3B8",
                    ),
                    ft.Text("今天没有待办事项哦", size=13, color="#64748B"),
                ],
            ),
        )

    def render_todos(index: int) -> None:
        selected_date = dates[index]
        day_items = todos_by_day.get(selected_date, {})
        # 时间轴：没有时间的（全天）排最前，其余按时间先后（同一时间按录入顺序）。
        todos = [
            todo for name, _ in CATEGORIES for todo in day_items.get(name, [])
        ]
        todos = sorted_todos(todos)
        todo_content.controls = [
            build_todo_item(todo, first=index == 0)
            for index, todo in enumerate(todos)
        ] or [build_empty_hint()]

    def build_date_item(index: int) -> ft.Control:
        selected_date = dates[index]
        badge_bg = date_badge_bg(index == selected_index)
        return ft.Container(
            key=f"date-{selected_date.isoformat()}",
            expand=1,
            height=DATE_CARD_HEIGHT,
            padding=ft.Padding.only(top=DATE_CARD_TOP_PADDING),
            alignment=ft.Alignment.TOP_CENTER,
            on_click=lambda _: select_date(index),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=DATE_COLUMN_SPACING,
                controls=[
                    ft.Text(
                        weekdays[selected_date.weekday()],
                        size=DATE_WEEKDAY_SIZE,
                        color=DATE_WEEKDAY_COLOR,
                    ),
                    build_date_badge(
                        date_card_label(selected_date, today), badge_bg
                    ),
                ],
            ),
        )

    def select_date(index: int) -> None:
        nonlocal selected_index
        selected_index = index
        date_selector.controls = [
            build_date_item(date_index) for date_index in range(len(dates))
        ]
        render_todos(index)
        date_selector.update()
        todo_content.update()

    def refresh_after_save(saved_day: date) -> None:
        """Re-read the list and follow a todo that landed on the shown week."""
        reload_todos()
        if saved_day in dates:
            select_date(dates.index(saved_day))
        page.update()

    def open_add_todo() -> None:
        open_todo_form(
            page,
            set_menu_visible=set_bottom_controls_visible,
            on_saved=refresh_after_save,
            default_date=max(dates[selected_index], date.today()),
        )

    def open_add_countdown() -> None:
        """「+」面板的第二条：新增倒数日。

        倒数日不在待办页上展示，所以存完不用重排列表。
        """
        open_countdown_form(
            page,
            set_menu_visible=set_bottom_controls_visible,
            on_saved=lambda: None,
        )

    def edit_todo(todo_id: int) -> None:
        todo = db.get_todo(todo_id)
        if todo is None:
            return
        open_todo_form(
            page,
            set_menu_visible=set_bottom_controls_visible,
            on_saved=refresh_after_save,
            default_date=todo.due_date,
            todo=todo,
        )

    date_selector.controls = [
        build_date_item(index) for index in range(len(dates))
    ]
    render_todos(selected_index)

    add_button = ft.Container(
        right=24,
        # Sits 10px above the floating menu bar, whose height drives the inset.
        bottom=BOTTOM_MENU_INSET + ADD_BUTTON_LIFT,
        width=ADD_BUTTON_SIZE,
        height=ADD_BUTTON_SIZE,
        shape=ft.BoxShape.CIRCLE,
        bgcolor=ADD_BUTTON_BG,
        blur=ft.Blur(20, 20, ft.BlurTileMode.CLAMP),
        content=ft.IconButton(
            # 就是一个「+」：新增入口本身不用再解释，面板里那两条才分工。
            icon=ft.Icons.ADD,
            icon_color="#172554",
            icon_size=24,
            tooltip="新增待办 / 倒数日",
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
            # 点一下弹小面板，再点一下收回去。
            on_click=lambda _: set_choose_open(not choose_open),
        ),
    )

    choose_open = False
    # 面板开着时铺满页面的遮罩：点空白处收面板。1/255 的不透明度是为了让这块空白
    # 也吃得到点击 —— 完全透明（或不填色）的 Container 收不到。
    scrim = ft.Container(
        expand=True,
        bgcolor="#01000000",
        visible=False,
        on_click=lambda _: set_choose_open(False),
    )

    def choose_option(
        label: str, icon: str, open_form: Callable[[], None]
    ) -> ft.Container:
        """面板上的一条入口：图标 + 文案，点一下先收面板再开弹窗。"""
        return ft.Container(
            height=CHOOSE_OPTION_HEIGHT,
            border_radius=ft.BorderRadius.all(CHOOSE_OPTION_RADIUS),
            padding=CHOOSE_OPTION_PADDING,
            ink=True,
            on_click=lambda _: start_add(open_form),
            content=ft.Row(
                tight=True,
                spacing=CHOOSE_ICON_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon, size=CHOOSE_ICON_SIZE, color=CHOOSE_TEXT_COLOR
                    ),
                    ft.Text(
                        label, size=CHOOSE_TEXT_SIZE, color=CHOOSE_TEXT_COLOR
                    ),
                ],
            ),
        )

    def start_add(open_form: Callable[[], None]) -> None:
        """选好一条：先收面板，紧接着开对应的新增弹窗。"""
        set_choose_open(False)
        open_form()

    choose_panel = ft.Container(
        right=24,
        # 面板落在按钮正上方，中间留 `CHOOSE_PANEL_GAP` 的缝。
        bottom=(
            BOTTOM_MENU_INSET
            + ADD_BUTTON_LIFT
            + ADD_BUTTON_SIZE
            + CHOOSE_PANEL_GAP
        ),
        width=CHOOSE_PANEL_WIDTH,
        padding=CHOOSE_PANEL_PADDING,
        border_radius=ft.BorderRadius.all(CHOOSE_PANEL_RADIUS),
        bgcolor=CHOOSE_PANEL_BG,
        blur=ft.Blur(20, 20, ft.BlurTileMode.CLAMP),
        border=ft.Border.all(1, CHOOSE_PANEL_BORDER),
        # 收起状态是「缩到按钮那一角 + 全透明」：控件一直留在树上，缩放和淡入才有
        # 起点可插值（就是「从按钮里长出来」的动效）；缩到 0 之后既看不见也不吃
        # 点击，所以不必再用 `visible` 开关它。
        scale=ft.Scale(CHOOSE_START_SCALE, alignment=CHOOSE_ANCHOR),
        opacity=0,
        animate_scale=ft.Animation(
            CHOOSE_GROW_MS, ft.AnimationCurve.EASE_OUT_CUBIC
        ),
        animate_opacity=ft.Animation(CHOOSE_FADE_MS, ft.AnimationCurve.EASE_OUT),
        content=ft.Column(
            tight=True,
            spacing=CHOOSE_OPTION_GAP,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                choose_option("新增待办", ft.Icons.EDIT_NOTE, open_add_todo),
                choose_option(
                    "新增倒数日",
                    ft.Icons.HOURGLASS_BOTTOM,
                    open_add_countdown,
                ),
            ],
        ),
    )

    def set_choose_open(open_panel: bool) -> None:
        """开 / 收「+」面板：缩放配淡入淡出，缩放的落点是按钮那一角。"""
        nonlocal choose_open
        if open_panel == choose_open:
            return
        choose_open = open_panel
        scrim.visible = open_panel
        choose_panel.scale = ft.Scale(
            1 if open_panel else CHOOSE_START_SCALE, alignment=CHOOSE_ANCHOR
        )
        choose_panel.opacity = 1 if open_panel else 0
        page.update()

    def set_bottom_controls_visible(visible: bool) -> None:
        set_menu_visible(visible)
        add_button.visible = visible
        add_button.update()
        # 弹窗（输入框弹键盘）时，「+」上的小面板也跟着退场。
        set_choose_open(False)

    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                gradient=page_gradient(),
                content=ft.Container(
                    expand=True,
                    content=ft.SafeArea(
                        expand=True,
                        content=ft.Container(
                            expand=True,
                            alignment=ft.Alignment.TOP_LEFT,
                            padding=ft.Padding.only(
                                left=PAGE_SIDE_PADDING,
                                top=PAGE_SIDE_PADDING,
                                right=PAGE_SIDE_PADDING,
                            ),
                            content=ft.Column(
                                expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                controls=[
                                    ft.Row(
                                        alignment=(
                                            ft.MainAxisAlignment.SPACE_BETWEEN
                                        ),
                                        vertical_alignment=(
                                            ft.CrossAxisAlignment.CENTER
                                        ),
                                        controls=[
                                            ft.Text(
                                                "待办",
                                                size=18,
                                                weight=ft.FontWeight.BOLD,
                                                color="#172554",
                                            ),
                                            # 右上角进「数据」页：数据统计 / 分类占比 /
                                            # 待办趋势都在那一页上。
                                            ft.Container(
                                                ink=True,
                                                tooltip="数据",
                                                # 22px 的图标太难点，四周补一圈让
                                                # 手指够得着。
                                                padding=ft.Padding.all(6),
                                                on_click=lambda _: open_data(),
                                                content=ft.Icon(
                                                    ft.Icons.BAR_CHART,
                                                    size=22,
                                                    color="#172554",
                                                ),
                                            ),
                                        ],
                                    ),
                                    date_selector,
                                    # 日期条和下面列表之间拉一条灰线（上下由
                                    # 列自己的间距隔开）。
                                    ft.Divider(
                                        height=STRIP_DIVIDER_THICKNESS,
                                        thickness=STRIP_DIVIDER_THICKNESS,
                                        color=STRIP_DIVIDER_COLOR,
                                    ),
                                    todo_content,
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            # 遮罩压在按钮底下、面板底下：点空白处收面板，但不挡「+」自己。
            scrim,
            add_button,
            choose_panel,
        ],
    )
