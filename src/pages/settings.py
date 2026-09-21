import flet as ft


def build_settings_page() -> ft.Control:
    return ft.Container(
        expand=True,
        bgcolor="#F4ECFF",
        content=ft.Container(
            expand=True,
            content=ft.SafeArea(
                expand=True,
                content=ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=48),
                            ft.Text("设置", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text("设置页面"),
                        ],
                    ),
                ),
            ),
        ),
    )
