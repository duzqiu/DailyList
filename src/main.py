import flet as ft
from pathlib import Path

from pages.navigation import build_navigation
from tools import db
from widgets.services import register_app_services

# 静态资源目录（`src/assets`：图标、背景图、App 图标、开屏图）。
# `ft.run()` 在**不给**这个参数时会拿「当前工作目录」去拼默认的 `assets` —— 从项目根目录
# 起跑（`python src/main.py`）就拼到不存在的 `DailyList/assets`，图全加载不出来；而
# `flet run` 又会用它自己的 `FLET_ASSETS_DIR` 覆盖这里传的值。写成「本文件旁边的
# assets」，两条路都对。页面里引用时用**相对这个目录**的路径（路径常量见
# widgets/layout.py）。
ASSETS_DIR = str(Path(__file__).parent / "assets")


async def main(page: ft.Page):
    # 本地库现在**只装登录令牌**（api/session.py）—— 其余设置项走内存 mock
    # （tools/mock_settings.py，背景图路径也在那儿），倒数日数据全在后端。所以启动时既不
    # 用补默认值、也不用再按设备认领老数据了（见 README「待处理问题」）。
    db.init_db()
    # 入口仍留成协程：以后要读设备信息、或等服务端数据回来再装配导航时，不用改签名
    # （`ft.run` 两种入口都收）。
    #
    # 剪贴板、文件选择器这些 Service 必须在页面**首次发给客户端之前**注册好，否则
    # 客户端不认识它们（等设置页构建时再注册就晚了），调用起来会一直等然后超时。
    # 见 widgets/services.py 里的 register_app_services()。
    register_app_services(page)
    build_navigation(page)


if __name__ == "__main__":
    ft.run(main, assets_dir=ASSETS_DIR)
