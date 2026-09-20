import flet as ft

from pages.home import build_home_page
from pages.settings import build_settings_page


def build_navigation(page: ft.Page) -> None:
    content = ft.Container(expand=True)
    navigation_bar = ft.NavigationBar(
        height=72,
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
        label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
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
                key="settings-tab",
            ),
        ],
    )

    def show_page(index: int, update: bool = True) -> None:
        content.content = (
            build_home_page() if index == 0 else build_settings_page()
        )
        navigation_bar.selected_index = index
        if update:
            page.update()

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
                    bottom=12,
                    height=72,
                    border_radius=ft.BorderRadius.all(22),
                    bgcolor="#66374151",
                    blur=ft.Blur(16, 16, ft.BlurTileMode.CLAMP),
                    border=ft.Border.all(1, "#33FFFFFF"),
                    ignore_interactions=True,
                ),
                ft.Container(
                    left=16,
                    right=16,
                    bottom=12,
                    height=72,
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.all(0),
                    content=navigation_bar,
                ),
            ],
        )
    )
