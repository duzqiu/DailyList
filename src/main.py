import flet as ft

from pages.navigation import build_navigation
from tools import db


def main(page: ft.Page):
    db.init_db()
    build_navigation(page)


if __name__ == "__main__":
    ft.run(main)
