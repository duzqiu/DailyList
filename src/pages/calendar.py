"""日历页：月历本身就是内容，不再在下面另开一张待办列表。

日期格子没有底色，颜色全在「条目」上：当天每条待办都是一小块自己的颜色
（分类色的浅底 + 分类色文字，重要红 / 一般黄 / 可选绿），已完成的那条沿用
全局约定变灰并加删除线，同一天的倒数日用倒数日的天蓝色。选中的日期只在日期
数字外面套一个统一的圆形底色，格子本身不变色。一天最多列 5 条，多出来的
折成「+N」。
"""

import calendar
from collections.abc import Callable
from datetime import date

import flet as ft

from tools import db
from tools.categories import category_color
from tools.countdown_card import (
    ACCENT_COLOR as COUNTDOWN_COLOR,
    build_countdown_card,
    countdowns_on,
    visible_countdowns,
)
from tools.countdown_form import open_countdown_form
from tools.layout import (
    BOTTOM_MENU_INSET,
    # 选中日期的那圈圆形底色：和首页日期条、我的页日期选择器同一个蓝。
    DATE_SELECTED_BG,
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    page_gradient,
    readable_ink,
)
from tools.lunar import lunar_label
from tools.pickers import build_date_picker
from tools.todo_timeline import build_todo_timeline, sorted_todos
from tools.todo_form import open_todo_form

TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
# 每格的高度：一行日期 + 最多 4 条待办（条目本身带底色）。
DAY_CELL_HEIGHT = 96
# 卡片之间的左右间隔（卡片平分行宽，间隔越小卡片越宽）。
DAY_CELL_SPACING = 4
# 日期数字外面的圆：只有选中的那天填色。
DAY_BADGE_SIZE = 22
DAY_NUMBER_SIZE = 12
# 日期右边那行农历：比日期小一号、灰色，只放日子（「廿三」）放得下。
LUNAR_SIZE = 7
ITEM_SIZE = 9
# 弹窗标题和分组名比正文小一档（弹窗比卡片宽松，但内容多）。
DIALOG_TITLE_SIZE = 15
DIALOG_GROUP_SIZE = 12
# 弹窗里的分组小标题（待办 / 倒数日）：图标 + 名称，统一用正文的深色。
DIALOG_SECTION_COLOR = TITLE_COLOR
# 弹窗表面（#E4E9EF）比首页底色深，点线要跟着深一点才看得见。
DIALOG_AXIS_COLOR = "#CBD5E1"
# 日期格子的描边：比卡片边框 #E2E8F0 再淡一点点，只要把格子界限画出来。
CELL_BORDER = "#E2E8F0"
MAX_ITEMS = 4
WEEKDAYS = ("一", "二", "三", "四", "五", "六", "日")


def lunar_short(day: date) -> str:
    """卡片右角那半截农历。

    格子只有一行位置：平常只写日子（「廿三」），碰上初一就写月份（「八月」）
    —— 一个月里出现两次「初一」这种信息量为零的写法不如报月份。
    """
    label = lunar_label(day)
    month, separator, rest = label.partition("月")
    if separator and rest in ("", "初一"):
        return f"{month}月"
    return rest or label


def build_calendar_page(
    page: ft.Page,
    set_menu_visible: Callable[[bool], None],
    state: dict[str, object],
) -> ft.Control:
    """日历页。`state` 由调用方保管（见 pages/navigation.py）：翻到哪个月、
    选中了哪一天要能跨 Tab 留住，切走再回来不会被拉回今天。控件本身照旧每次
    重建，所以上面的待办还是现从 db 读的。
    """
    today = date.today()
    saved_month = state.get("month")
    saved_day = state.get("day")
    visible_month = (
        saved_month
        if isinstance(saved_month, date)
        else date(today.year, today.month, 1)
    )
    selected_day = saved_day if isinstance(saved_day, date) else today

    def remember() -> None:
        """把当前所在的月份和选中的日期写回 `state`，供下次重建时恢复。"""
        state["month"] = visible_month
        state["day"] = selected_day

    month_view = ft.Container()
    month_title = ft.Text(
        f"{visible_month.year}年{visible_month.month}月",
        size=17,
        weight=ft.FontWeight.BOLD,
        color=TITLE_COLOR,
    )

    def month_todos() -> dict[date, list[db.Todo]]:
        last_day = calendar.monthrange(
            visible_month.year, visible_month.month
        )[1]
        grouped: dict[date, list[db.Todo]] = {}
        for todo in db.list_range(
            visible_month,
            date(visible_month.year, visible_month.month, last_day),
        ):
            grouped.setdefault(todo.due_date, []).append(todo)
        return grouped

    def remove_todo(todo: db.Todo, refresh: Callable[[], None]) -> None:
        db.delete_todo(todo.id)
        refresh()

    def edit_todo(todo: db.Todo, refresh: Callable[[], None]) -> None:
        open_todo_form(
            page,
            set_menu_visible=set_menu_visible,
            on_saved=lambda _: refresh(),
            default_date=todo.due_date,
            todo=todo,
        )

    def remove_countdown(item: db.Countdown, refresh: Callable[[], None]) -> None:
        db.delete_countdown(item.id)
        refresh()

    def edit_countdown(item: db.Countdown, refresh: Callable[[], None]) -> None:
        open_countdown_form(
            page,
            set_menu_visible=set_menu_visible,
            on_saved=refresh,
            item=item,
        )

    def clip_in_dialog(row: ft.Control) -> ft.Control:
        """把左滑行裁在弹窗边界内。

        左滑是靠平移卡片实现的，平移量（两个按钮 144px）比弹窗的留白大得多，
        不裁的话卡片会滑到弹窗外面、盖到页面上；这里按行自己的圆角裁一刀，
        滑出弹窗的部分直接看不见，露出来的就是那两个按钮。
        """
        return ft.Container(
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border_radius=ft.BorderRadius.all(10),
            content=row,
        )

    def section_header(name: str, icon: str, color: str) -> ft.Control:
        """弹窗里的小标题：图标 + 名称，待办和倒数日共用一套。"""
        return ft.Row(
            spacing=6,
            controls=[
                ft.Icon(icon, size=13, color=color),
                ft.Text(
                    name,
                    size=DIALOG_GROUP_SIZE,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                ),
            ],
        )

    def empty_hint() -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=ft.BorderRadius.all(12),
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, CELL_BORDER),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(
                        ft.Icons.EVENT_AVAILABLE,
                        size=20,
                        color="#94A3B8",
                    ),
                    ft.Text("这天没有待办事项", size=12, color="#64748B"),
                ],
            ),
        )

    def day_groups(
        day: date, refresh: Callable[[], None]
    ) -> list[ft.Control]:
        """弹窗内容：当天的待办用首页那套时间轴，倒数日接在下面。"""
        groups: list[ft.Control] = []
        todos = db.list_range(day, day)
        if todos:
            groups.append(
                ft.Column(
                    tight=True,
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        section_header(
                            "待办", ft.Icons.CHECKLIST, DIALOG_SECTION_COLOR
                        ),
                        build_todo_timeline(
                            todos,
                            axis_color=DIALOG_AXIS_COLOR,
                            on_delete=lambda todo: remove_todo(todo, refresh),
                            on_edit=lambda todo: edit_todo(todo, refresh),
                        ),
                    ],
                )
            )
        countdowns = visible_countdowns(countdowns_on(day))
        if countdowns:
            groups.append(
                ft.Column(
                    tight=True,
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        section_header(
                            "倒数日", ft.Icons.EVENT, DIALOG_SECTION_COLOR
                        ),
                        *[
                            clip_in_dialog(
                                build_countdown_card(
                                    item,
                                    today=day,
                                    on_delete=lambda _, i=item: remove_countdown(
                                        i, refresh
                                    ),
                                    on_edit=lambda _, i=item: edit_countdown(
                                        i, refresh
                                    ),
                                )
                            )
                            for item in countdowns
                        ],
                    ],
                )
            )
        if not groups:
            groups.append(empty_hint())
        return groups

    def open_day_dialog(day: date) -> None:
        """点日期卡片：弹窗列出当天全部待办（左滑可编辑、删除）。"""
        body = ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        def refresh() -> None:
            # 删掉/改完一条，弹窗和月历一起刷新。
            body.controls = day_groups(day, refresh)
            body.update()
            update_calendar()

        body.controls = day_groups(day, refresh)
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                # 一天里条目多时整个弹窗内容可滚。
                scrollable=True,
                shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
                bgcolor=DIALOG_SURFACE,
                elevation=0,
                inset_padding=ft.Padding.symmetric(horizontal=32, vertical=24),
                # 标题行和右上角的「×」都往角上靠一点。
                title_padding=ft.Padding.only(left=16, top=4, right=4, bottom=0),
                content_padding=ft.Padding.only(
                    left=16, top=8, right=16, bottom=8
                ),
                actions_padding=ft.Padding.only(left=8, right=8, bottom=8),
                action_button_padding=ft.Padding.symmetric(horizontal=8),
                # 标题右边就是关闭的「×」，底下不再放一整条 actions。
                title=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            f"{day.month}月{day.day}日 周{WEEKDAYS[day.weekday()]}",
                            size=DIALOG_TITLE_SIZE,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_COLOR,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_size=20,
                            icon_color=MUTED_COLOR,
                            tooltip="关闭",
                            on_click=lambda _: page.pop_dialog(),
                        ),
                    ],
                ),
                content=body,
            )
        )

    def item_line(text: str, color: str, done: bool = False) -> ft.Control:
        """卡片里的一条：底色就是待办对应的颜色，字色跟着底色选深浅。"""
        ink = readable_ink(color)
        return ft.Container(
            bgcolor=color,
            border_radius=ft.BorderRadius.all(4),
            padding=ft.Padding.symmetric(horizontal=3, vertical=1),
            content=ft.Text(
                text,
                size=ITEM_SIZE,
                color=ink,
                # 完成的画删除线；线跟着字色走，压在深底色上也看得见。
                style=(
                    ft.TextStyle(
                        decoration=ft.TextDecoration.LINE_THROUGH,
                        decoration_thickness=1.5,
                        decoration_color=ink,
                    )
                    if done
                    else None
                ),
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        )

    def item_lines(day: date, todos: list[db.Todo]) -> list[ft.Control]:
        """当天的待办 + 倒数日，按分类上色，最多 MAX_ITEMS 行。"""
        entries: list[tuple[str, str, bool]] = [
            # 完成的待办底色照旧用分类色，靠删除线表示已完成。
            (todo.content, category_color(todo.category), todo.done)
            for todo in todos
        ]
        entries += [
            (item.content, COUNTDOWN_COLOR, False)
            for item in visible_countdowns(countdowns_on(day))
        ]
        if not entries:
            return []
        if len(entries) > MAX_ITEMS:
            # 多出来的不硬挤：少列一条，末尾用「+N」交代。
            shown = entries[: MAX_ITEMS - 1]
            lines = [item_line(*entry) for entry in shown]
            lines.append(item_line(f"+{len(entries) - len(shown)}", MUTED_COLOR))
            return lines
        return [item_line(*entry) for entry in entries]

    def day_cell(
        day_number: int, day_todos: dict[date, list[db.Todo]]
    ) -> ft.Control:
        if day_number == 0:
            return ft.Container(expand=True, height=DAY_CELL_HEIGHT)

        day = date(visible_month.year, visible_month.month, day_number)
        is_selected = day == selected_day
        # 卡片里的先后只看时间：全天的排最前，其余按时间早晚，同一时间按录入
        # 顺序 —— 和首页时间轴、当天弹窗共用同一套排序（tools/todo_timeline.py）。
        todos = sorted_todos(day_todos.get(day, []))
        lines = item_lines(day, todos)
        return ft.Container(
            expand=True,
            height=DAY_CELL_HEIGHT,
            padding=ft.Padding.symmetric(horizontal=2, vertical=2),
            border_radius=ft.BorderRadius.all(8),
            # 浅灰描边，把每格的边界画出来（格子本身还是透明底）。
            border=ft.Border.all(1, CELL_BORDER),
            on_click=lambda _: click_day(day),
            content=ft.Column(
                tight=True,
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    # 日期靠左（选中的那天只有数字外面套一圈圆形底色），
                    # 右边跟一行农历，比日期小一号、灰色。
                    ft.Row(
                        spacing=2,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=DAY_BADGE_SIZE,
                                height=DAY_BADGE_SIZE,
                                shape=ft.BoxShape.CIRCLE,
                                alignment=ft.Alignment.CENTER,
                                bgcolor=(
                                    DATE_SELECTED_BG if is_selected else None
                                ),
                                content=ft.Text(
                                    str(day_number),
                                    size=DAY_NUMBER_SIZE,
                                    weight=ft.FontWeight.BOLD,
                                    color=TITLE_COLOR,
                                ),
                            ),
                            ft.Text(
                                lunar_short(day),
                                size=LUNAR_SIZE,
                                color=MUTED_COLOR,
                                text_align=ft.TextAlign.RIGHT,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True,
                            ),
                        ],
                    ),
                    *lines,
                ],
            ),
        )

    def build_month_view() -> ft.Control:
        month_days = calendar.monthcalendar(
            visible_month.year, visible_month.month
        )
        day_todos = month_todos()
        return ft.Column(
            tight=True,
            # Row-to-row (and header-to-first-row) gap between the day cards.
            spacing=5,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        ft.Text(
                            weekday,
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=MUTED_COLOR,
                        )
                        for weekday in WEEKDAYS
                    ],
                ),
                *[
                    ft.Row(
                        # The cells share the row width, so this left-right gap
                        # sets how wide each day card gets.
                        spacing=DAY_CELL_SPACING,
                        controls=[day_cell(day, day_todos) for day in week],
                    )
                    for week in month_days
                ],
            ],
        )

    def update_calendar() -> None:
        nonlocal selected_day
        if (
            selected_day.month != visible_month.month
            or selected_day.year != visible_month.year
        ):
            selected_day = visible_month
        remember()
        month_view.content = build_month_view()
        month_title.value = f"{visible_month.year}年{visible_month.month}月"
        month_title.update()
        month_view.update()

    def change_month(offset: int) -> None:
        nonlocal visible_month
        month_index = visible_month.month - 1 + offset
        visible_month = date(
            visible_month.year + month_index // 12,
            month_index % 12 + 1,
            1,
        )
        update_calendar()

    def select_day(day: date) -> None:
        nonlocal selected_day
        selected_day = day
        remember()
        month_view.content = build_month_view()
        month_view.update()

    def click_day(day: date) -> None:
        """点某天：先把它选上（日期圈变蓝），再弹出当天的待办清单。"""
        select_day(day)
        open_day_dialog(day)

    def jump_to_day(day: date) -> None:
        """Follow a date picked in the system picker: month and selection."""
        nonlocal visible_month
        visible_month = date(day.year, day.month, 1)
        select_day(day)
        update_calendar()

    date_picker = build_date_picker(selected_day, jump_to_day)

    def open_date_picker(_: ft.Event[ft.Control]) -> None:
        date_picker.value = selected_day
        page.show_dialog(date_picker)

    month_view.content = build_month_view()

    return ft.Container(
        expand=True,
        gradient=page_gradient(),
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=24, top=24, right=24),
                content=ft.Column(
                    expand=True,
                    # 4px base gap so the month selector sits closer to the grid;
                    # other sections add 12px margins to keep their previous gaps.
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text(
                            "日历",
                            # Same face as the home page's「待办」heading.
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_COLOR,
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            # The month selector sits right under the「日历」
                            # heading: only the column's own gap is left between
                            # them (the icon buttons keep their tap padding).
                            margin=ft.Margin.only(top=0),
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.CHEVRON_LEFT,
                                    tooltip="上个月",
                                    on_click=lambda _: change_month(-1),
                                ),
                                ft.Container(
                                    ink=True,
                                    on_click=open_date_picker,
                                    content=month_title,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CHEVRON_RIGHT,
                                    tooltip="下个月",
                                    on_click=lambda _: change_month(1),
                                ),
                            ],
                        ),
                        # 网格万一放不下（小屏）能滚动，正常手机上不用滚。
                        ft.ListView(
                            expand=True,
                            scroll=ft.ScrollMode.HIDDEN,
                            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
                            controls=[month_view],
                        ),
                    ],
                ),
            ),
        ),
    )
