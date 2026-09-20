import flet as ft


def build_home_page() -> ft.Control:
    counter = ft.Text("0", size=50, data=0)

    def increment_click(e: ft.Event[ft.FloatingActionButton]):
        counter.data += 1
        counter.value = str(counter.data)

    return ft.Stack(
        expand=True,
        controls=[
            ft.SafeArea(
                expand=True,
                content=ft.Container(
                    content=counter,
                    alignment=ft.Alignment.CENTER,
                ),
            ),
            ft.FloatingActionButton(
                icon=ft.Icons.ADD,
                key="increment",
                on_click=increment_click,
                right=24,
                bottom=104,
            ),
        ],
    )
