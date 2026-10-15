"""「换背景图」那一页（从「我的」页点背景区的空白处进来）。

版式：左上角 **✕** 关掉 → 中间摆**当前背景图** → 下面一条**长条按钮「更换背景图」**。
点它走 `ft.FilePicker.pick_files`（手机上是系统相册 / 文件选图器，桌面是文件对话框），
选中的图**上传到后端**（`POST /member/profile/background`，与头像同一套规则：按会员 ID
分目录存），随后叫一次 `on_saved` —— 由调用方（pages/navigation.py）去重画「我的」页，
那段背景就换成新图了。

⚠️ 不再复制进 App 目录（原来那套本地存法已去掉）：换设备登录背景图也还在。
"""

from collections.abc import Callable

import flet as ft

from api import member_profile, session
from api.client import ApiError
from widgets.layout import BOTTOM_MENU_INSET
from widgets.services import ensure_service
from widgets.toast import build_toast
from widgets.my_background import background_path

TITLE_COLOR = "#172554"
MUTED_COLOR = "#94A3B8"
PAGE_BG = "#FFFFFF"
ACCENT_RED = "#FF2442"
PREVIEW_RADIUS = 14
BUTTON_HEIGHT = 48


def build_background_page(
    page: ft.Page,
    go_back: Callable[[], None],
    on_saved: Callable[[], None],
) -> ft.Control:
    """换背景图那一页。

    `go_back` 是左上角那个 ✕；`on_saved` 在选好图之后叫一次（让「我的」页重画）。
    """
    preview = ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        border_radius=ft.BorderRadius.all(PREVIEW_RADIUS),
        # 不描边：用户要求「选中的图片不要有外围边框线示意」—— 预览就是图片本身，
        # 外面那圈线会像「选中框」，去掉。
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Container(),
    )

    def render() -> None:
        """中间那块：有图就摆图（均匀拉伸铺满），没有就一句提示。"""
        path = background_path()
        preview.content = (
            ft.Image(src=path, fit=ft.BoxFit.FILL, expand=True)
            if path
            else ft.Text("还没有背景图", size=13, color=MUTED_COLOR)
        )

    def notify(message: str) -> None:
        """一句话提示：走 widgets/toast.py，浮在屏幕正中。"""
        page.show_dialog(build_toast(page, message))

    # ⚠️ 选图器**不能在这一页里新建**：Service 只有在「页面首次发给客户端之前」注册才到
    # 得了客户端（见 widgets/services.py 开头那两条踩坑记录 —— 注册表自己的 `parent` 恒为
    # `None`，后来的注册推送不出去，只能随首个页面一起发出）。这一页是二级页，页面早就发
    # 过了：此刻新建 / 注册的 FilePicker 客户端永远收不到，调它只会干等 10 秒后抛
    #     TimeoutException: Timeout waiting for invoke method listener for FilePicker(xxx)
    # 那个「客户端不认识的控件」还会在界面上渲染成一片红（Unknown control）。
    # 所以取 `main()` 里已经注册好的那一个（`register_app_services`）—— 和设置页的
    # 导出 / 导入用的是同一个（preferences.py 里同一个写法）。
    # 不挂 `on_result`：新版 Flet 的 `pick_files` 是**把结果 return 回来**的；两条路都挂
    # 会互相覆盖（这个选图器设置页也在用）。
    picker = ensure_service(page, ft.FilePicker)

    async def pick_and_apply() -> None:
        """打开系统相册选一张，回来直接换上。

        ⚠️ 关键：新版 Flet 的 `pick_files` 是**把结果 return 回来**的（`on_result` 是旧写法，
        有些版本不再触发）—— 之前「选完毫无反应」就是因为只挂了 `on_result`、没人接返回值。
        所以这里只走返回值这一条路。
        """
        try:
            # ⚠️ `with_data=True` 与头像同理：`FilePickerFile.path` 在 Web 模式永远是
            # None、部分原生平台也拿不到，只有这个开关会把**文件内容**放进 `bytes`。
            picked_files = await picker.pick_files(
                allow_multiple=False,
                # `file_type=IMAGE`：手机上就是**系统相册 / 图库**（不是老的「文件」选择器）。
                file_type=ft.FilePickerFileType.IMAGE,
                with_data=True,
            )
        except Exception as error:  # noqa: BLE001
            # 选图器没起来 / 等超时：给一句人话，别把堆栈直接糊在控制台上。
            notify(f"打不开相册：{error}")
            return
        picked = picked_files[0] if picked_files else None
        if picked is None:
            notify("没有选到图片")
            return
        notify("正在上传背景图…")
        try:
            # 上传到后端（POST /member/profile/background），成功后资料缓存已刷新。
            await member_profile.upload_background(picked)
        except ApiError as error:
            notify(error.message)
            return
        render()
        page.update()
        on_saved()
        notify("已更换背景图")

    def pick(_: ft.Event[ft.Control]) -> None:
        """「更换背景图」：先给一句提示（确认按钮接上了），再进相册选图。

        没登录就不给选 —— 背景图是存在**会员**名下的，没登录无处可存。
        """
        if not session.access_token():
            notify("请先登录再设置背景图")
            return
        notify("正在打开相册…")
        page.run_task(pick_and_apply)

    render()

    return ft.Container(
        expand=True,
        bgcolor=PAGE_BG,
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=16, top=16, right=16),
                content=ft.Column(
                    expand=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        # 顶栏：左上角只有一个 ✕（关掉这一页）。原来旁边还有「背景图」
                        # 这个标题，用户要去掉 —— 这一页干什么一目了然，标题是多余的。
                        ft.Row(
                            tight=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(
                                    ink=True,
                                    tooltip="返回",
                                    padding=ft.Padding.all(6),
                                    on_click=lambda _: go_back(),
                                    content=ft.Icon(
                                        ft.Icons.CLOSE,
                                        size=22,
                                        color=TITLE_COLOR,
                                    ),
                                ),
                            ],
                        ),
                        preview,
                        # 底下那条长条按钮：点了就去选图。
                        ft.Container(
                            height=BUTTON_HEIGHT,
                            alignment=ft.Alignment.CENTER,
                            border_radius=ft.BorderRadius.all(
                                BUTTON_HEIGHT / 2
                            ),
                            bgcolor=ACCENT_RED,
                            ink=True,
                            on_click=pick,
                            content=ft.Text(
                                "更换背景图",
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color="#FFFFFF",
                            ),
                        ),
                        ft.Container(height=BOTTOM_MENU_INSET / 2),
                    ],
                ),
            ),
        ),
    )
