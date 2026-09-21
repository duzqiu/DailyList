import flet as ft


def build_home_page() -> ft.Control:
    return ft.Container(
        expand=True,
        bgcolor="#172554",
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
                            ft.Icon(
                                ft.Icons.HOME_OUTLINED,
                                size=48,
                                color="#F8FAFC",
                            ),
                            ft.Text(
                                "首页",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color="#F8FAFC",
                            ),
                        ],
                    ),
                ),
            ),
        ),
    )
