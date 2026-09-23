import calendar
from datetime import date

import flet as ft


def build_calendar_page(page: ft.Page) -> ft.Control:
    today = date.today()
    visible_month = date(today.year, today.month, 1)
    selected_day = today
    month_view = ft.Container()
    selected_content = ft.Container()
    month_title = ft.Text(
        f"{visible_month.year}年{visible_month.month}月",
        size=17,
        weight=ft.FontWeight.BOLD,
        color="#172554",
    )

    tasks_by_day = {
        1: {
            "重要": ["整理本月计划"],
            "一般": ["更新工作安排"],
            "可选": ["整理桌面文件"],
        },
        3: {
            "重要": ["完成项目进度整理"],
            "一般": ["回复重要消息"],
            "可选": ["阅读产品设计文档"],
        },
        8: {"重要": ["提交阶段成果"], "一般": ["整理会议纪要"], "可选": []},
        12: {"重要": ["提交工作报告"], "一般": [], "可选": ["备份资料"]},
        18: {
            "重要": ["安排下周任务"],
            "一般": ["备份重要资料"],
            "可选": ["整理下载目录"],
        },
        25: {"重要": ["完成学习目标"], "一般": ["复盘学习内容"], "可选": []},
    }
    category_icons = {
        "重要": (ft.Icons.PRIORITY_HIGH, "#DC2626"),
        "一般": (ft.Icons.LIST_ALT, "#2563EB"),
        "可选": (ft.Icons.LOW_PRIORITY, "#64748B"),
    }

    def build_selected_content(day: date) -> ft.Control:
        categories = tasks_by_day.get(day.day, {})
        has_tasks = any(categories.values())
        return ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Text(
                    f"{day.year}年{day.month}月{day.day}日",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color="#172554",
                ),
                ft.Text(
                    "当天暂无待办事项" if not has_tasks else "当天待办事项",
                    size=13,
                    color="#64748B",
                ),
                *[
                    ft.Column(
                        tight=True,
                        spacing=6,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(
                                        category_icons[category][0],
                                        size=16,
                                        color=category_icons[category][1],
                                    ),
                                    ft.Text(
                                        category,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=category_icons[category][1],
                                    ),
                                ],
                            ),
                            *[
                                ft.Container(
                                    padding=ft.Padding.symmetric(
                                        horizontal=12, vertical=8
                                    ),
                                    border_radius=ft.BorderRadius.all(10),
                                    bgcolor="#F1F5F9",
                                    content=ft.Text(task, size=13, color="#334155"),
                                )
                                for task in tasks
                            ],
                        ],
                    )
                    for category, tasks in categories.items()
                    if tasks
                ],
            ],
        )

    def day_cell(day_number: int) -> ft.Control:
        if day_number == 0:
            return ft.Container(expand=True, height=42)

        day = date(visible_month.year, visible_month.month, day_number)
        is_selected = day == selected_day
        has_tasks = day_number in tasks_by_day and any(
            tasks_by_day[day_number].values()
        )
        return ft.Container(
            expand=True,
            height=42,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(8),
            bgcolor="#172554" if is_selected else "#F1F5F9",
            on_click=lambda _: select_day(day),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=1,
                controls=[
                    ft.Text(
                        str(day_number),
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF" if is_selected else "#172554",
                    ),
                    ft.Container(
                        width=4,
                        height=4,
                        border_radius=ft.BorderRadius.all(2),
                        bgcolor=(
                            "#FFFFFF"
                            if is_selected and has_tasks
                            else "#2563EB"
                            if has_tasks
                            else "#00000000"
                        ),
                    ),
                ],
            ),
        )

    def build_month_view() -> ft.Control:
        month_days = calendar.monthcalendar(
            visible_month.year, visible_month.month
        )
        return ft.Column(
            tight=True,
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        ft.Text(
                            weekday,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color="#64748B",
                        )
                        for weekday in ["一", "二", "三", "四", "五", "六", "日"]
                    ],
                ),
                *[
                    ft.Row(
                        spacing=6,
                        controls=[day_cell(day) for day in week],
                    )
                    for week in month_days
                ],
            ],
        )

    def update_calendar() -> None:
        nonlocal selected_day
        if selected_day.month != visible_month.month or selected_day.year != visible_month.year:
            selected_day = visible_month
        month_view.content = build_month_view()
        selected_content.content = build_selected_content(selected_day)
        month_title.value = f"{visible_month.year}年{visible_month.month}月"
        month_title.update()
        month_view.update()
        selected_content.update()

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
        selected_content.content = build_selected_content(day)
        month_view.content = build_month_view()
        month_view.update()
        selected_content.update()

    draft_day = selected_day
    date_picker = ft.CupertinoDatePicker(
        value=selected_day,
        locale=ft.Locale("zh", "CN"),
        date_picker_mode=ft.CupertinoDatePickerMode.DATE,
        date_order=ft.CupertinoDatePickerDateOrder.YEAR_MONTH_DAY,
        minimum_year=1900,
        maximum_year=2100,
        show_day_of_week=True,
        item_extent=36,
        height=190,
    )
    date_sheet = ft.CupertinoBottomSheet(content=ft.Container())

    def date_picker_changed(e: ft.Event[ft.CupertinoDatePicker]) -> None:
        nonlocal draft_day
        selected = e.control.value
        draft_day = selected.date() if hasattr(selected, "date") else selected

    def confirm_date_picker(_: ft.Event[ft.Control]) -> None:
        nonlocal visible_month
        visible_month = date(draft_day.year, draft_day.month, 1)
        select_day(draft_day)
        update_calendar()
        date_sheet.open = False
        page.update()

    date_picker.on_change = date_picker_changed
    date_sheet.content = ft.Container(
        bgcolor="#FFFFFF",
        padding=ft.Padding.only(left=20, top=12, right=20, bottom=20),
        content=ft.Column(
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            "选择日期",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color="#172554",
                        ),
                        ft.TextButton(
                            "确定",
                            style=ft.ButtonStyle(
                                padding=ft.Padding.symmetric(horizontal=12)
                            ),
                            on_click=confirm_date_picker,
                        ),
                    ],
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12),
                    content=date_picker,
                ),
            ],
        ),
    )

    def open_date_picker(_: ft.Event[ft.Control]) -> None:
        nonlocal draft_day
        draft_day = selected_day
        date_picker.value = selected_day
        page.show_dialog(date_sheet)

    month_view.content = build_month_view()
    selected_content.content = build_selected_content(selected_day)

    return ft.Container(
        expand=True,
        bgcolor="#FFFFFF",
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=24, top=24, right=24),
                content=ft.Column(
                    expand=True,
                    spacing=16,
                    controls=[
                        ft.Text(
                            "日历",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color="#172554",
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
                        month_view,
                        selected_content,
                    ],
                ),
            ),
        ),
    )
