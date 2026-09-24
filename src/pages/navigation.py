import flet as ft

from pages.calendar import build_calendar_page
from pages.home import build_home_page
from pages.settings import build_settings_page
from tools.layout import MENU_BAR_BOTTOM, MENU_BAR_HEIGHT


def build_navigation(page: ft.Page) -> None:
    page.padding = 0
    page.spacing = 0
    content = ft.Container(expand=True)
    page_backgrounds = ["#FFFFFF", "#FFFFFF", "#3B0764"]
    selected_index = 0
    menu_items = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    menu_bottom = MENU_BAR_BOTTOM
    menu_bar = ft.Container(
        left=32,
        right=32,
        bottom=menu_bottom,
        height=MENU_BAR_HEIGHT,
        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
        border_radius=ft.BorderRadius.all(18),
        blur=ft.Blur(16, 16, ft.BlurTileMode.CLAMP),
        gradient=ft.LinearGradient(
            colors=["#66FFFFFF", "#40FFFFFF", "#66FFFFFF"],
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
        ),
        content=menu_items,
    )

    def set_menu_visible(visible: bool) -> None:
        menu_bar.visible = visible
        menu_bar.update()

    def keep_menu_off_keyboard(_: ft.Event[ft.Page]) -> None:
        menu_bar.bottom = menu_bottom - getattr(
            page.media.view_insets, "bottom", 0
        )
        menu_bar.update()

    def show_page(index: int, update: bool = True) -> None:
        nonlocal selected_index
        selected_index = index
        content.content = (
            build_home_page(page, set_menu_visible)
            if index == 0
            else             build_calendar_page(page)
            if index == 1
            else build_settings_page()
        )
        page.bgcolor = page_backgrounds[index]
        menu_bar.visible = True
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
                menu_bar,
            ],
        )
    )

    page.on_media_change = keep_menu_off_keyboard
