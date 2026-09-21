import flet as ft


def build_calendar_page() -> ft.Control:
    return ft.Container(
        expand=True,
        bgcolor="#EAF8F0",
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
                            ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=48),
                            ft.Text("日历", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text("日历页面"),
                        ],
                    ),
                ),
            ),
        ),
    )
