import flet as ft

from pages.navigation import build_navigation


def main(page: ft.Page):
    build_navigation(page)


if __name__ == "__main__":
    ft.run(main)
