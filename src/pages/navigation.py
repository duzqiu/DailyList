import flet as ft

from pages.home import build_home_page
from pages.settings import build_settings_page


def build_navigation(page: ft.Page) -> None:
    content = ft.Container(expand=True)
    navigation_bar = ft.NavigationBar(
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME,
                label="首页",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="设置",
            ),
        ],
    )

    def show_page(index: int, update: bool = True) -> None:
        content.content = (
            build_home_page() if index == 0 else build_settings_page()
        )
        navigation_bar.selected_index = index
        if update:
            content.update()
            navigation_bar.update()

    def navigation_changed(e: ft.Event[ft.NavigationBar]) -> None:
        if e.control.selected_index is not None:
            show_page(e.control.selected_index)

    navigation_bar.on_change = navigation_changed
    show_page(0, update=False)

    page.add(
        ft.Stack(
            expand=True,
            controls=[
                content,
                ft.Container(
                    left=16,
                    right=16,
                    bottom=16,
                    height=80,
                    border_radius=ft.BorderRadius.all(28),
                    bgcolor="#661F2937",
                    blur=ft.Blur(20, 20, ft.BlurTileMode.CLAMP),
                    border=ft.Border.all(1, "#33FFFFFF"),
                ),
                ft.Container(
                    left=16,
                    right=16,
                    bottom=16,
                    height=80,
                    content=navigation_bar,
                ),
            ],
        )
    )
