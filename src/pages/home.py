import flet as ft
from datetime import date, timedelta


def build_home_page(page: ft.Page) -> ft.Control:
    dates = [date.today() + timedelta(days=offset) for offset in range(7)]
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    todo_items = [
        {
            "重要": ["整理今天的工作计划"],
            "一般": ["回复重要消息", "更新任务进度"],
            "可选": ["整理桌面文件"],
        },
        {
            "重要": ["完成项目进度整理"],
            "一般": ["安排明天的任务"],
            "可选": ["阅读产品设计文档"],
        },
        {
            "重要": ["确认产品发布内容"],
            "一般": ["记录新的想法", "整理会议纪要"],
            "可选": ["浏览行业资讯"],
        },
        {
            "重要": ["提交本周工作报告"],
            "一般": ["整理桌面文件", "备份重要资料"],
            "可选": ["清理下载目录"],
        },
        {
            "重要": ["完成今日学习目标"],
            "一般": ["复盘本周进度"],
            "可选": ["阅读推荐文章", "练习新技能"],
        },
        {
            "重要": ["确认周末安排"],
            "一般": ["采购日常用品"],
            "可选": ["准备周末菜单"],
        },
        {
            "重要": ["完成下周计划"],
            "一般": ["整理本周收获"],
            "可选": ["休息和放松"],
        },
    ]
    selected_index = 0
    category_icons = {
        "重要": ft.Icons.PRIORITY_HIGH,
        "一般": ft.Icons.LIST_ALT,
        "可选": ft.Icons.LOW_PRIORITY,
    }
    date_selector = ft.ListView(
        horizontal=True,
        height=48,
        spacing=8,
        padding=ft.Padding.only(right=8),
    )
    todo_content = ft.Container(expand=True)

    def build_todo_item(item: str, category: str, item_index: int) -> ft.Control:
        completed = False
        todo_card = ft.Container(
            key=f"todo-{category}-{item_index}",
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=ft.BorderRadius.all(10),
            bgcolor="#F1F5F9",
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(
                        ft.Icons.CIRCLE_OUTLINED,
                        size=16,
                        color="#94A3B8",
                    ),
                    ft.Text(item, size=13, color="#334155"),
                ],
            ),
        )

        def toggle_todo(_: ft.Event[ft.Container]) -> None:
            nonlocal completed
            completed = not completed
            todo_card.bgcolor = "#DCFCE7" if completed else "#F1F5F9"
            todo_card.content = ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE_OUTLINE
                        if completed
                        else ft.Icons.CIRCLE_OUTLINED,
                        size=16,
                        color="#16A34A" if completed else "#94A3B8",
                    ),
                    ft.Text(
                        item,
                        size=13,
                        color="#166534" if completed else "#334155",
                    ),
                ],
    )
            todo_card.update()

        todo_card.on_click = toggle_todo
        return todo_card

    def build_todo_content(index: int) -> ft.Control:
        selected_date = dates[index]
        return ft.Column(
            tight=True,
            spacing=12,
            controls=[
                ft.Text(
                    f"{selected_date.month}月{selected_date.day}日待办",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color="#172554",
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
                                        category_icons[category],
                                        size=16,
                                        color=category_color,
                                    ),
                                    ft.Text(
                                        category,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=category_color,
                                    ),
                                ],
                            ),
                            *[
                                build_todo_item(item, category, item_index)
                                for item_index, item in enumerate(items)
                            ],
                        ],
                    )
                    for category, category_color, items in [
                        ("重要", "#DC2626", todo_items[index % len(todo_items)]["重要"]),
                        ("一般", "#2563EB", todo_items[index % len(todo_items)]["一般"]),
                        ("可选", "#64748B", todo_items[index % len(todo_items)]["可选"]),
                    ]
                ],
            ],
        )

    def build_date_item(index: int) -> ft.Control:
        selected = index == selected_index
        selected_date = dates[index]
        return ft.Container(
            key=f"date-{selected_date.isoformat()}",
            width=42,
            height=42,
            padding=ft.Padding.symmetric(horizontal=4, vertical=3),
            border_radius=ft.BorderRadius.all(6),
            bgcolor="#172554" if selected else "#F1F5F9",
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=lambda _: select_date(index),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
                controls=[
                    ft.Text(
                        weekdays[selected_date.weekday()],
                        size=9,
                        color="#FFFFFF" if selected else "#64748B",
                    ),
                    ft.Text(
                        str(selected_date.day),
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF" if selected else "#172554",
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
        todo_content.content = build_todo_content(index)
        date_selector.update()
        todo_content.update()

    def save_todo(
        dialog: ft.AlertDialog,
        todo_field: ft.TextField,
        date_field: ft.Dropdown,
        category_field: ft.Dropdown,
    ) -> None:
        item = (todo_field.value or "").strip()
        if not item or date_field.value is None or category_field.value is None:
            return
        date_index = int(date_field.value)
        category = category_field.value
        todo_items[date_index][category].append(item)
        dialog.open = False
        todo_content.content = build_todo_content(selected_index)
        todo_content.update()
        page.update()

    def open_add_todo(_: ft.Event[ft.Container]) -> None:
        todo_field = ft.TextField(
            label="待办事项",
            hint_text="请输入待办内容",
            autofocus=True,
        )
        date_field = ft.Dropdown(
            label="选择日期",
            value=str(selected_index),
            options=[
                ft.DropdownOption(
                    key=str(index),
                    text=f"{item.month}月{item.day}日",
                )
                for index, item in enumerate(dates)
            ],
        )
        category_field = ft.Dropdown(
            label="选择分类",
            value="一般",
            options=[
                ft.DropdownOption(key=category, text=category)
                for category in ("重要", "一般", "可选")
            ],
        )
        dialog = ft.AlertDialog(
            modal=True,
            title="新增待办",
            content=ft.Column(
                tight=True,
                controls=[date_field, category_field, todo_field],
            ),
            actions=[
                ft.TextButton(
                    "取消",
                    on_click=lambda _: close_dialog(dialog),
                ),
                ft.TextButton(
                    "保存",
                    on_click=lambda _: save_todo(
                        dialog, todo_field, date_field, category_field
                    ),
                ),
            ],
        )
        page.show_dialog(dialog)

    def close_dialog(dialog: ft.AlertDialog) -> None:
        dialog.open = False
        page.update()

    date_selector.controls = [
        build_date_item(index) for index in range(len(dates))
    ]
    todo_content.content = build_todo_content(selected_index)

    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                bgcolor="#FFFFFF",
                content=ft.Container(
                    expand=True,
                    content=ft.SafeArea(
                        expand=True,
                        content=ft.Container(
                            expand=True,
                            alignment=ft.Alignment.TOP_LEFT,
                            padding=ft.Padding.only(left=24, top=24, right=24),
                            content=ft.Column(
                                expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                controls=[
                                    ft.Text(
                                        "待办",
                                        size=22,
                                        weight=ft.FontWeight.BOLD,
                                        color="#172554",
                                    ),
                                    date_selector,
                                    todo_content,
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            ft.Container(
                right=24,
                bottom=88,
                width=52,
                height=52,
                border_radius=ft.BorderRadius.all(26),
                blur=ft.Blur(14, 14, ft.BlurTileMode.CLAMP),
                gradient=ft.LinearGradient(
                    colors=["#CCFFFFFF", "#99FFFFFF"],
                    begin=ft.Alignment.TOP_LEFT,
                    end=ft.Alignment.BOTTOM_RIGHT,
                ),
                content=ft.IconButton(
                    icon=ft.Icons.ADD,
                    icon_color="#172554",
                    icon_size=24,
                    tooltip="新增待办",
                    on_click=open_add_todo,
                ),
            ),
        ],
    )