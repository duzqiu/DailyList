import flet as ft
from pathlib import Path

from api import member_profile, session
from api.client import ApiError
from pages.navigation import build_navigation
from widgets.services import ensure_service, register_app_services

# 静态资源目录（`src/assets`：图标、背景图、App 图标、开屏图）。
# `ft.run()` 在**不给**这个参数时会拿「当前工作目录」去拼默认的 `assets` —— 从项目根目录
# 起跑（`python src/main.py`）就拼到不存在的 `DailyList/assets`，图全加载不出来；而
# `flet run` 又会用它自己的 `FLET_ASSETS_DIR` 覆盖这里传的值。写成「本文件旁边的
# assets」，两条路都对。页面里引用时用**相对这个目录**的路径（路径常量见
# widgets/layout.py）。
ASSETS_DIR = str(Path(__file__).parent / "assets")


async def main(page: ft.Page):
    # 剪贴板、文件选择器、客户端存储（`SharedPreferences`）这些 Service 必须在页面**首次发给
    # 客户端之前**注册好，否则客户端不认识它们（等设置页构建时再注册就晚了），调用起来会
    # 一直等然后超时。见 widgets/services.py 里的 register_app_services()。
    register_app_services(page)
    # 登录令牌存在**客户端存储**里（见 api/session.py）：启动时读一次填进内存镜像，之后各
    # 页面同步读它。读不到 / 超时就当没登录 —— 这一步不能把首帧拖住，所以入口是协程
    # （`ft.run` 两种入口都收）。
    await session.restore(page, ensure_service(page, ft.SharedPreferences))
    # 已登录就把资料先拉回来（昵称 / 头像 / **背景图** / 简介…）：「我的」页整块
    # 背景区的配色与结构都取决于**有没有背景图**，必须进页面前就知道，否则会先按
    # 「没图」摆一遍再闪成有图。拉不到也不拦着进 App（页面自己还会再试一次）。
    if session.access_token():
        try:
            await member_profile.get_profile(use_cache=False)
        except ApiError:
            pass
    build_navigation(page)


if __name__ == "__main__":
    ft.run(main, assets_dir=ASSETS_DIR)
