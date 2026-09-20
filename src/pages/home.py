import flet as ft


def build_home_page() -> ft.Control:
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.HOME_OUTLINED, size=48),
                    ft.Text("首页", size=28, weight=ft.FontWeight.BOLD),
                ],
            ),
        ),
    )
