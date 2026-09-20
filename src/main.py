import flet as ft

from pages.home import build_home_page


def main(page: ft.Page):
    build_home_page(page)


if __name__ == "__main__":
    ft.run(main)
