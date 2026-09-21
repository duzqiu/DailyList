import flet as ft


def build_settings_page() -> ft.Control:
    return ft.Container(
        expand=True,
        bgcolor="#3B0764",
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
                                ft.Icons.SETTINGS_OUTLINED,
                                size=48,
                                color="#FAF5FF",
                            ),
                            ft.Text(
                                "设置",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color="#FAF5FF",
                            ),
                            ft.Text("设置页面", color="#FAF5FF"),
                        ],
                    ),
                ),
            ),
        ),
    )
