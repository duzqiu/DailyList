from collections.abc import Callable
from datetime import date, timedelta

import flet as ft

from tools import db
from tools.categories import CATEGORIES
from tools.layout import (
    ADD_ICON_SRC,
    BOTTOM_MENU_INSET,
    CALENDAR_ICON_SRC,
    page_gradient,
)
from tools.todo_form import open_todo_form
from tools.todo_timeline import build_todo_row, sorted_todos

# 右下角那颗「+」按钮**没有底色**（`ft.Colors.TRANSPARENT`）：只留中间那枚图标，
# 落在页面渐变和列表上都不带一块托底。原来是一块天蓝毛玻璃（`#99B2E0F4` 60% 透明 +
# Blur 20），底色改成透明时连 `blur` 一起去了 —— **光有模糊没有底色并不等于「清玻璃」**：
# `Container.blur` 是按控件那块**矩形**铺的，不跟着 `shape` 裁圆，压在这块一直在滚动的
# 列表上就是一块方糊斑，比不加还脏。真要清玻璃，底色和 `clip_behavior`（裁圆）得一起加。
# A round tile, lifted clear of the floating menu bar.
ADD_BUTTON_SIZE = 52
ADD_BUTTON_LIFT = 10
# 右下角那颗圆按钮上的图标：assets 里的一张图（`src/assets/icons/add.png`）。点之前、
# 点之后都是它，不换也不转（试过「转一圈变 ×」，旋转量和图标尺寸都调不准，索性去掉）。
# `ft.IconButton.icon` 允许直接给一个控件（Flet 1.0 的类型是 `IconData | Control`），
# 所以按钮本身（圆形墨迹、tooltip、点击区）不用动，只是图标从字形换成图 —— 尺寸也
# 从 `icon_size` 挪到图自己身上。
ADD_ICON_SIZE = 24
# 空态提示（「今天没有待办事项哦」）左边那枚图：和底部菜单、倒数日卡片同一张日历图。
EMPTY_HINT_ICON_SIZE = 20
# 「+」按钮那圈**细灰边**：底色透明之后，圆形的边界就靠它交代（和卡片边、空态提示
# 那圈、倒数日卡片的边同一个灰 `#E2E8F0`；`shape=CIRCLE` 会让这圈边自己走成圆的）。
ADD_BUTTON_BORDER = "#E2E8F0"
ADD_BUTTON_BORDER_WIDTH = 1
# 顶部日期条：今天排第一个，往后连着 7 天（过去的日子不再列出来）。
DATE_STRIP_DAYS = 7
# 日期一格不带底色：选中的那天只是把日期**加粗**，选中标记交给日期底下那条黑
# 横条（见 DATE_BAR_*），所以日期怎么写都不会被一个色块框住。周几是灰的、日期是
# 深的，点哪一天都不重画这两个字，只有加粗和横条跟着走。
DATE_TEXT_COLOR = "#172554"
DATE_WEEKDAY_COLOR = "#64748B"
# The seven day columns share the strip's width: every column is an expanding
# child of a `Row`, so the free space is split evenly and the strip fills the
# screen on any phone width instead of leaving a gap after the last column.
DATE_CARD_SPACING = 8
# 主 Column 里各块之间的缝（标题 / 日期条 / 灰线 / 列表）。日期条和灰线之间那一档
# 收成 0：日期卡片顺着这条缝往下长，选中横条就落在卡片底边上、正好贴着灰线；原来
# 的 10px 挪进卡片自己的顶内边距里补回来，所以日期条的内容和灰线以下一个像素没动。
BLOCK_GAP = 10
# 卡片 = 56 的内容（周几 + 日期）+ BLOCK_GAP 那么高的一条底，横条就钉在那条底上。
DATE_CARD_HEIGHT = 56 + BLOCK_GAP
# 收掉的那点高度从这里补回来（见 DATE_DAY_BOX_HEIGHT）：日期那一行的中心还落在
# 原来的高度上，它和底下那条横条、那条灰线的相对位置一个像素没动 —— 变的只是
# 周几往下靠拢的这一点。
DATE_CARD_TOP_PADDING = 17
# 周几在上、日期在下（一律写成「09.28」这样的月.日，今天也不写「今」）；两行之间
# 那点空当 = DATE_COLUMN_SPACING + 日期盒里字上下的留白，收得很紧 —— 周几几乎贴
# 着日期。
DATE_WEEKDAY_SIZE = 11
# 日期那一行固定占这么高：整串「09.28」比单个日号长得多，字号收小、宽度也框住，
# 相邻两格的日期不会互相顶到，整条日期条的高度还跟原来一样。盒子只比 10pt 的字
# 高出一圈：早先给到 34，字上下各空出十来 px，看着就成了分家的两行。
DATE_DAY_SIZE = 10
DATE_DAY_BOX_HEIGHT = 18
DATE_COLUMN_SPACING = 1
# 选中标记：日期正下方一条黑横条，钉在日期卡片底边上（也就是贴住下面那条
# 灰间隔线）。整条日期条只画这一条，选中哪一格它就滑到那一格下面（见
# date_bar_offset）。
DATE_BAR_WIDTH = 16
DATE_BAR_HEIGHT = 3
DATE_BAR_COLOR = "#0F172A"
# 滑到新格子用的时间与曲线：慢一点（半秒），看得出来是「挪」过去的，不是「跳」过去的。
DATE_BAR_SLIDE_MS = 500
DATE_BAR_SLIDE_CURVE = ft.AnimationCurve.EASE_IN_OUT
# 下方那叠页跟着滑一格，和横条同一条时间：切一次是一整套动作（条在挪、
# 页在滑）。
DATE_PAGE_SLIDE_MS = DATE_BAR_SLIDE_MS
DATE_PAGE_SLIDE_CURVE = DATE_BAR_SLIDE_CURVE
# 在下方那块（待办列表）上左右滑，切前一天 / 后一天：横向走满这么多像素，
# 或者甩得够快，都算一次切换；两样都没到就什么都不做。
DATE_SWIPE_DISTANCE = 24.0
DATE_SWIPE_VELOCITY = 300.0
PAGE_SIDE_PADDING = 24
# 日期条的真实宽度要等布局完才量得到，横条滑动的换算（见 date_bar_offset）先按
# 手机竖屏估一个兜底；和 calendar.py / data.py 一个来路：页宽 400 减掉左右各 24。
ESTIMATED_PAGE_WIDTH = 400
DATE_STRIP_ESTIMATED_WIDTH = ESTIMATED_PAGE_WIDTH - 2 * PAGE_SIDE_PADDING
# 日期条的 key：页面上找「日期条」就认它。
DATE_STRIP_KEY = "date-strip"
# 下方那叠页的 key：页面上找「一天一页的那一叠」就认它。
PAGE_SLIDE_KEY = "date-pages"
# 选中那一天存在页面 state 里的键（见 restore_day_index）：待办页每次切页都是重
# 建的，「在看哪一天」得跟着页面名留住，不然从二级页退回来就弹回今天。
SELECTED_DAY_KEY = "selected_day"
# 日期条和下面待办列表之间那条灰线：1px，比卡片描边更淡一档的浅灰。
STRIP_DIVIDER_COLOR = "#F1F5F9"
STRIP_DIVIDER_THICKNESS = 1


def date_card_label(day: date) -> str:
    """日期条上一格怎么写：「09.28」（月.日，补零）—— 今天也写日期，不写「今」。"""
    return f"{day.month:02d}.{day.day:02d}"


def date_bar_offset(index: int, strip_width: float) -> float:
    """黑横条滑到第 `index` 格下面所需的 `offset.x`。

    `offset` 是按控件自身尺寸换算的平移（见 tools/layout.py 的 `BACK_OFFSET`：
    40px 宽 × -0.2 就是往左 8px）。横条外面那层容器铺满整条日期条，宽正好是
    `strip_width`，于是平移量 = 选中格的中线到日期条中线的距离 ÷ 日期条宽。

    每格宽 = （日期条宽 − 7 格之间那几条空隙）÷ 7，选中格中线 = `index` ×
    （格宽 + 空隙）+ 格宽 ÷ 2；正中间那格（今起第 4 天）平移量正好是 0。
    """
    if strip_width <= 0:
        return 0.0
    cell = (strip_width - DATE_CARD_SPACING * (DATE_STRIP_DAYS - 1)) / DATE_STRIP_DAYS
    center = index * (cell + DATE_CARD_SPACING) + cell / 2
    return (center - strip_width / 2) / strip_width


def group_todos_by_day(
    todos: list[db.Todo],
) -> dict[date, dict[str, list[db.Todo]]]:
    grouped: dict[date, dict[str, list[db.Todo]]] = {}
    for todo in todos:
        day = grouped.setdefault(todo.due_date, {})
        day.setdefault(todo.category, []).append(todo)
    return grouped


def restore_day_index(dates: list[date], state: dict[str, object]) -> int:
    """回到上次看的那一格：state 里存的是那一天本身（见 SELECTED_DAY_KEY）。

    存日期而不是下标 —— 下标是相对「今天」的，隔了零点之后整条日期条往后挪一天，
    同一个下标指的就是另一天了。存的这天已经不在这一周里（隔了几天才回来），
    就还是回到今天。
    """
    saved = state.get(SELECTED_DAY_KEY)
    if not isinstance(saved, str):
        return 0
    try:
        return dates.index(date.fromisoformat(saved))
    except ValueError:
        return 0


def build_home_page(
    page: ft.Page,
    set_menu_visible: Callable[[bool], None],
    state: dict[str, object],
) -> ft.Control:
    # 今天排在日期条的第一个，往后连着 DATE_STRIP_DAYS 天 —— 待办页只看今天和
    # 接下来的这几天，过去的日子不再列。
    today = date.today()
    dates = [today + timedelta(days=offset) for offset in range(DATE_STRIP_DAYS)]
    today_index = 0
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    todos_by_day = group_todos_by_day(db.list_todos(dates))
    # 进二级页（数据页）再退回来时这一页是重新 build 出来的，日期条要回到进去前
    # 看的那一格，而不是弹回今天那第一格（见 restore_day_index）。
    selected_index = restore_day_index(dates, state)
    # 日期条的真实宽度（量到之前是 0，按估的值算）。
    date_selector = ft.Row(spacing=DATE_CARD_SPACING)
    # 整条日期条只画这一条黑横条：铺满日期条的宽、钉在底边上，靠 `offset`
    # （按自身宽度换算的平移，见 date_bar_offset）滑到选中那一格下面。
    date_bar = ft.Container(
        left=0,
        right=0,
        bottom=0,
        alignment=ft.Alignment.CENTER,
        offset=ft.Offset(
            date_bar_offset(selected_index, DATE_STRIP_ESTIMATED_WIDTH), 0
        ),
        animate_offset=ft.Animation(DATE_BAR_SLIDE_MS, DATE_BAR_SLIDE_CURVE),
        content=ft.Container(
            width=DATE_BAR_WIDTH,
            height=DATE_BAR_HEIGHT,
            border_radius=ft.BorderRadius.all(DATE_BAR_HEIGHT / 2),
            bgcolor=DATE_BAR_COLOR,
        ),
    )

    # 刚被勾上的那几条的 id：交给 `build_todo_item`，让它们的对勾落定后弹一下
    # （见 tools/todo_timeline.py 的 build_todo_check）。切完成会把七页重铺一遍，
    # 换上来的是新控件、没有「上一个状态」可以插值，所以只能按「这次勾的是谁」
    # 现告诉它 —— 铺完（`reload_todos`）就清掉，别的时候重建都不再弹。
    just_done: set[int] = set()

    def reload_todos() -> None:
        nonlocal todos_by_day
        todos_by_day = group_todos_by_day(db.list_todos(dates))
        fill_pages()
        # 弹过就清：之后再重建（切日期、从二级页回来、编辑保存）不该再弹一次。
        just_done.clear()

    def delete_todo(todo_id: int) -> None:
        db.delete_todo(todo_id)
        reload_todos()
        select_date(selected_index)

    def build_todo_item(
        todo: db.Todo, first: bool = False, last: bool = False
    ) -> ft.Control:
        """一行时间轴：点一下切换完成，左滑编辑 / 删除（共用控件）。

        `first` / `last` 是这条轴的两个端点：首行不往上补点、末行不往下补点，和
        日历弹窗里那条轴一个样（两处共用 tools/todo_timeline.py）。
        """

        def toggle_todo(item: db.Todo) -> None:
            done = not item.done
            db.set_done(item.id, done)
            # 只有「刚被勾上」那一条让对勾弹一下；取消完成不弹。
            just_done.clear()
            if done:
                just_done.add(item.id)
            # reload_todos 顺带把七页都重铺、整叠更新一次。
            reload_todos()

        return build_todo_row(
            todo,
            first=first,
            last=last,
            on_click=toggle_todo,
            on_delete=lambda item: delete_todo(item.id),
            on_edit=lambda item: edit_todo(item.id),
            # 这一条刚被勾上：对勾弹一下（见 build_todo_check 的 pop）。
            popped_ids=just_done,
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
                    ft.Image(
                        src=CALENDAR_ICON_SRC,
                        width=EMPTY_HINT_ICON_SIZE,
                        height=EMPTY_HINT_ICON_SIZE,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    ft.Text("今天没有待办事项哦", size=13, color="#64748B"),
                ],
            ),
        )

    def day_rows(index: int) -> list[ft.Control]:
        """第 `index` 天要摆的那些行（那天没待办就是那条空态提示）。"""
        day_items = todos_by_day.get(dates[index], {})
        # 时间轴：没有时间的（全天）排最前，其余按时间先后（同一时间按录入顺序）。
        todos = [
            todo for name, _ in CATEGORIES for todo in day_items.get(name, [])
        ]
        todos = sorted_todos(todos)
        return [
            build_todo_item(
                todo,
                first=order == 0,
                # 最后一条下面不再补点：轴到它为止，跟日历弹窗里那条轴一致。
                last=order == len(todos) - 1,
            )
            for order, todo in enumerate(todos)
        ] or [build_empty_hint()]

    def build_day_page(index: int) -> ft.ListView:
        """一天一页：整页可以左右滑出去、新的一页滑进来（见 DATE_PAGE_SLIDE_MS）。

        页的 `offset` 是按自身宽度换算的平移，所以「离选中那页 index − 选中
        个页宽」正好把该看的那一页摆回屏幕里；平移量一改，`animate_offset`
        就把它从原来那个位置慢慢滑过去。
        """
        return ft.ListView(
            # 行之间几乎不留缝，短竖线上下相接才像一条轴。
            spacing=2,
            scroll=ft.ScrollMode.HIDDEN,
            # 上面那 BLOCK_GAP 是原来主 Column 给日期条与列表之间留的缝（现在日期条那段
            # 收成 0 了，缝归列表自己，列表内容的位置一点没动）；左右那 24px 也从整页
            # 上挪到了这里（见 build_home_page）—— 这一叠要铺满整个屏宽，页往左右滑
            # 出去时才正好滑出屏幕，边上不会剩一条邻居的影。
            padding=ft.Padding.only(
                left=PAGE_SIDE_PADDING,
                top=BLOCK_GAP,
                right=PAGE_SIDE_PADDING,
                bottom=BOTTOM_MENU_INSET,
            ),
            offset=ft.Offset(index - selected_index, 0),
            animate_offset=ft.Animation(DATE_PAGE_SLIDE_MS, DATE_PAGE_SLIDE_CURVE),
            controls=day_rows(index),
        )

    # 一天一页、一叠摆好：切日期就是整叠页滑一格，所以别的那几天也得先摆在
    # 树里 —— 不然新的一页是第一次出现，没有上一个位置可以滑过来。
    todo_pages = [build_day_page(index) for index in range(len(dates))]
    todo_stack = ft.Stack(
        key=PAGE_SLIDE_KEY,
        # 七页都被拉成和这一叠一样大：`offset` 是按控件自身尺寸换算的，页跟叠一样
        # 宽，「挪一格」才正好挪出一整屏（见 slide_pages）。
        fit=ft.StackFit.EXPAND,
        # 选中那页以外的都在栈外，全被裁掉，不会漏到日期条上去。
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        controls=todo_pages,
    )

    def fill_pages() -> None:
        """七页的内容都按当前数据重铺一遍，然后整叠更新一次。

        数据一变就得七页全铺 —— 别的日子那几页也摆在树里，只铺当前这页会留下一页旧的。
        """
        for index, page in enumerate(todo_pages):
            page.controls = day_rows(index)
        todo_stack.update()

    def slide_pages() -> None:
        """把整叠页推到选中那天：每页离它正好 i − 选中 个页宽。"""
        for index, page in enumerate(todo_pages):
            page.offset = ft.Offset(index - selected_index, 0)
        todo_stack.update()

    def build_date_item(index: int) -> ft.Control:
        """日期条的一格：周几 + 日期，选中的那天只是把日期加粗。

        选中标记（黑横条）不画在格子里 —— 整条日期条只画一条，由外面那条
        `date_bar` 滑到选中的那一格下面（见 date_bar_offset）。
        """
        selected_date = dates[index]
        picked = index == selected_index
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
                    # 日期不再有底色：格子只负责占位和居中，选中靠加粗。
                    ft.Container(
                        height=DATE_DAY_BOX_HEIGHT,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            date_card_label(selected_date),
                            size=DATE_DAY_SIZE,
                            weight=(
                                ft.FontWeight.BOLD
                                if picked
                                else ft.FontWeight.NORMAL
                            ),
                            color=DATE_TEXT_COLOR,
                            no_wrap=True,
                        ),
                    ),
                ],
            ),
        )

    def select_date(index: int) -> None:
        nonlocal selected_index
        selected_index = index
        # 记下这一天：退到二级页再回来时，日期条照它摆回去。
        state[SELECTED_DAY_KEY] = dates[index].isoformat()
        date_selector.controls = [
            build_date_item(date_index) for date_index in range(len(dates))
        ]
        # 横条滑到新格子下面，下面那叠页跟着滑一格（动效都交给 `animate_offset`）。
        place_date_bar()
        slide_pages()
        date_selector.update()

    def strip_width() -> float:
        """日期条的真实宽度；还没量到时先用估的那个兜底。"""
        return state.get("strip_width") or DATE_STRIP_ESTIMATED_WIDTH

    def place_date_bar() -> None:
        """横条摆到选中那一格下面 —— 只改 `offset`，滑动的动效由 `animate_offset` 管。"""
        date_bar.offset = ft.Offset(
            date_bar_offset(selected_index, strip_width()), 0
        )
        date_bar.update()

    def learn_strip_width(e: ft.LayoutSizeChangeEvent) -> None:
        """量一次日期条的真实宽度：横条滑动的换算要它（见 date_bar_offset）。

        宽度要等布局完才量得到，所以第一帧先按估的宽度摆；量到之后重摆一次 ——
        这一次先把动效摘掉，免得一启动就看到横条自己挪一小下。
        """
        width = e.width
        if (
            not width
            or width <= 0
            or abs(width - state.get("strip_width", 0.0)) < 1
        ):
            return
        state["strip_width"] = float(width)
        date_bar.animate_offset = None
        place_date_bar()
        date_bar.animate_offset = ft.Animation(
            DATE_BAR_SLIDE_MS, DATE_BAR_SLIDE_CURVE
        )

    def step_day(delta: int) -> None:
        """横滑一格：走到头就停住（不绕回来）。"""
        target = min(len(dates) - 1, max(0, selected_index + delta))
        if target != selected_index:
            select_date(target)

    # 这一趟横滑走了多少像素，松手时按它（或者甩的速度）决定算不算一次切换。
    swipe: dict[str, float] = {"dx": 0.0}

    def on_page_pan_start(_: ft.DragStartEvent) -> None:
        swipe["dx"] = 0.0

    def on_page_pan_update(e: ft.DragUpdateEvent) -> None:
        if e.local_delta:
            swipe["dx"] += e.local_delta.x

    def on_page_pan_end(e: ft.DragEndEvent) -> None:
        travelled = swipe["dx"]
        swipe["dx"] = 0.0
        fling = e.velocity.x if e.velocity else 0.0
        # 左滑看后一天、右滑看前一天；走够距离或者甩得够快都算一次切换。
        if travelled <= -DATE_SWIPE_DISTANCE or fling <= -DATE_SWIPE_VELOCITY:
            step_day(1)
        elif travelled >= DATE_SWIPE_DISTANCE or fling >= DATE_SWIPE_VELOCITY:
            step_day(-1)

    def on_page_pan_cancel(_: ft.Event[ft.GestureDetector]) -> None:
        swipe["dx"] = 0.0

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
    # 量一次日期条多宽：横条滑动按它换算（见 learn_strip_width）。
    date_selector.on_size_change = learn_strip_width
    # 日期条 = 那排日期格子 + 压在上面的一条黑横条（日期自己不接横滑）。
    date_strip = ft.Stack(
        key=DATE_STRIP_KEY,
        clip_behavior=ft.ClipBehavior.NONE,
        controls=[date_selector, date_bar],
    )
    # 切日期的横滑挂在**下方那块**：竖着动归列表自己滚（竖滑阈值比 pan 小，
    # 它先抢到），只有横着才轮到这层；起点落在某条待办上时，那一条自己的左滑（露出
    # 编辑 / 删除）在更里面，先进手势竞技场，所以优先。
    todo_pager = ft.GestureDetector(
        expand=True,
        content=todo_stack,
        on_pan_start=on_page_pan_start,
        on_pan_update=on_page_pan_update,
        on_pan_end=on_page_pan_end,
        on_pan_cancel=on_page_pan_cancel,
    )

    add_icon_button = ft.IconButton(
        # 就是这一张图（见 ADD_ICON_SIZE 那段注释）：这一页只剩「新增待办」一件事，
        # 不用再解释，也不换图标（换页也不转）。
        icon=ft.Image(
            src=ADD_ICON_SRC,
            width=ADD_ICON_SIZE,
            height=ADD_ICON_SIZE,
            fit=ft.BoxFit.CONTAIN,
        ),
        tooltip="新增待办",
        style=ft.ButtonStyle(shape=ft.CircleBorder()),
        # 直接开新增待办弹窗 —— 新增倒数日不在这儿了，挪到倒数日页右下角那枚「+」。
        on_click=lambda _: open_add_todo(),
    )

    add_button = ft.Container(
        right=24,
        # Sits 10px above the floating menu bar, whose height drives the inset.
        bottom=BOTTOM_MENU_INSET + ADD_BUTTON_LIFT,
        width=ADD_BUTTON_SIZE,
        height=ADD_BUTTON_SIZE,
        shape=ft.BoxShape.CIRCLE,
        # 透明底：按钮只留中间那枚图标（见文件头那段「没有底色」的注释）。
        # `shape` 留着 —— 将来要加回毛玻璃底，填上色再配 `clip_behavior` 就是圆的了。
        bgcolor=ft.Colors.TRANSPARENT,
        # 一圈细灰边：没有底色，边界只能靠这条线交代（见 ADD_BUTTON_BORDER）。
        border=ft.Border.all(ADD_BUTTON_BORDER_WIDTH, ADD_BUTTON_BORDER),
        content=add_icon_button,
    )

    def set_bottom_controls_visible(visible: bool) -> None:
        """弹窗（输入框弹键盘）时，底部菜单和这枚「+」一起退场。"""
        set_menu_visible(visible)
        add_button.visible = visible
        add_button.update()

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
                            # 左右那 24px 不再留在整页上：挪进了每一页自己（见
                            # build_day_page）。下面那一叠页因此铺满整个屏宽 —— 页往左右
                            # 滑出去时正好滑出屏幕，边上不会剩下邻居那一页的影子。
                            padding=ft.Padding.only(top=PAGE_SIDE_PADDING),
                            content=ft.Column(
                                expand=True,
                                # 块与块之间不留缝：日期条下面那条要收成 0，横条
                                # 才贴得住灰线（见 BLOCK_GAP）。
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                controls=[
                                    ft.Container(
                                        padding=ft.Padding.only(
                                            left=PAGE_SIDE_PADDING,
                                            right=PAGE_SIDE_PADDING,
                                        ),
                                        content=ft.Column(
                                            tight=True,
                                            spacing=0,
                                            horizontal_alignment=(
                                                ft.CrossAxisAlignment.STRETCH
                                            ),
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
                                                        # 右上角原来是「数据」入口，
                                                        # 已经挪到日历页的设置按钮左边
                                                        # （见 pages/calendar.py）。
                                                    ],
                                                ),
                                                date_strip,
                                                # 日期条和下面列表之间拉一条灰线（上下由
                                                # 列自己的间距隔开）。
                                                ft.Divider(
                                                    height=STRIP_DIVIDER_THICKNESS,
                                                    thickness=STRIP_DIVIDER_THICKNESS,
                                                    color=STRIP_DIVIDER_COLOR,
                                                ),
                                            ],
                                        ),
                                    ),
                                    todo_pager,
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            add_button,
        ],
    )
