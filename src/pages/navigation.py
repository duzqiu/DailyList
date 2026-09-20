import flet as ft

from pages.calendar import build_calendar_page
from pages.home import build_home_page
from pages.settings import build_settings_page


def build_navigation(page: ft.Page) -> None:
    content = ft.Container(expand=True)
    selected_index = 0
    menu_items = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    def show_page(index: int, update: bool = True) -> None:
        nonlocal selected_index
        selected_index = index
        content.content = (
            build_home_page()
            if index == 0
            else build_calendar_page()
            if index == 1
            else build_settings_page()
        )
        build_menu_items()
        if update:
            page.update()

    def menu_item(
        index: int, icon: str, selected_icon: str, label: str, key: str
    ) -> ft.Control:
        return ft.Container(
            key=key,
            expand=True,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(16),
            ink=True,
            on_click=lambda _: show_page(index),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
                controls=[
                    ft.Icon(
                        selected_icon if selected_index == index else icon,
                        size=24,
                        color="#1F2937",
                    ),
                    ft.Text(
                        label,
                        size=12,
                        color="#1F2937",
                        weight=(
                            ft.FontWeight.BOLD
                            if selected_index == index
                            else ft.FontWeight.NORMAL
                        ),
                    ),
                ],
            ),
        )

    def build_menu_items() -> None:
        menu_items.controls = [
            menu_item(0, ft.Icons.HOME_OUTLINED, ft.Icons.HOME, "首页", "home-tab"),
            menu_item(
                1,
                ft.Icons.CALENDAR_MONTH_OUTLINED,
                ft.Icons.CALENDAR_MONTH,
                "日历",
                "calendar-tab",
            ),
            menu_item(
                2,
                ft.Icons.SETTINGS_OUTLINED,
                ft.Icons.SETTINGS,
                "设置",
                "settings-tab",
            ),
        ]

    show_page(0, update=False)

    page.add(
        ft.Stack(
            expand=True,
            controls=[
                content,
                ft.Container(
                    left=16,
                    right=16,
                    bottom=20,
                    height=64,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    border_radius=ft.BorderRadius.all(20),
                    bgcolor="#CCFFFFFF",
                    blur=ft.Blur(16, 16, ft.BlurTileMode.CLAMP),
                    border=ft.Border.all(1, "#66FFFFFF"),
                    content=menu_items,
                ),
            ],
        )
    )
