import flet as ft

from pages.navigation import build_navigation
from tools import db
from tools.services import register_app_services


def main(page: ft.Page):
    db.init_db()
    # 剪贴板、文件选择器这些 Service 必须在页面**首次发给客户端之前**注册好，否则
    # 客户端不认识它们（等设置页构建时再注册就晚了），调用起来会一直等然后超时。
    # 见 tools/services.py 里的 register_app_services()。
    register_app_services(page)
    build_navigation(page)


if __name__ == "__main__":
    ft.run(main)
