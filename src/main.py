import flet as ft
from pathlib import Path

from pages.navigation import build_navigation
from tools import app_settings, db
from tools.services import register_app_services

# 静态资源目录（`src/assets`：设置入口那张图、App 图标、开屏图）。
# `ft.run()` 在**不给**这个参数时会拿「当前工作目录」去拼默认的 `assets` —— 从项目根目录
# 起跑（`python src/main.py`）就拼到不存在的 `DailyList/assets`，图全加载不出来；而
# `flet run` 又会用它自己的 `FLET_ASSETS_DIR` 覆盖这里传的值。写成「本文件旁边的
# assets」，两条路都对。页面里引用时用**相对这个目录**的路径（见 pages/calendar.py 的
# SETTINGS_ICON_SRC）。
ASSETS_DIR = str(Path(__file__).parent / "assets")


def main(page: ft.Page):
    db.init_db()
    # 设置项（通知渠道 / 云端开关 / 联系方式）的默认值：表里还没有的先补上，见
    # tools/app_settings.py —— 那份清单就是「settings 表里该有哪些行」的准头。
    app_settings.ensure_defaults()
    # 剪贴板、文件选择器这些 Service 必须在页面**首次发给客户端之前**注册好，否则
    # 客户端不认识它们（等设置页构建时再注册就晚了），调用起来会一直等然后超时。
    # 见 tools/services.py 里的 register_app_services()。
    register_app_services(page)
    build_navigation(page)


if __name__ == "__main__":
    ft.run(main, assets_dir=ASSETS_DIR)
