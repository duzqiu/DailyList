import flet as ft
from datetime import date, timedelta


def build_home_page() -> ft.Control:
    dates = [date.today() + timedelta(days=offset) for offset in range(14)]
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
    date_selector = ft.ListView(
        horizontal=True,
        height=48,
        spacing=6,
        padding=ft.Padding.only(right=6),
    )
    todo_content = ft.Container(expand=True)

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
                            ft.Text(
                                category,
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=category_color,
                            ),
                            *[
                                ft.Container(
                                    padding=ft.Padding.symmetric(
                                        horizontal=12, vertical=8
                                    ),
                                    border_radius=ft.BorderRadius.all(10),
                                    bgcolor="#F1F5F9",
                                    content=ft.Text(
                                        item, size=13, color="#334155"
                                    ),
                                )
                                for item in items
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
            width=48,
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

    date_selector.controls = [
        build_date_item(index) for index in range(len(dates))
    ]
    todo_content.content = build_todo_content(selected_index)

    return ft.Container(
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
    )
