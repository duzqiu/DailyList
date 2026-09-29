from collections.abc import Callable

import flet as ft

from pages.calendar import build_calendar_page
from pages.countdown import build_countdown_page
from pages.data import build_data_page
from pages.home import build_home_page
from pages.preferences import build_preferences_page
from tools.layout import (
    MENU_BAR_BOTTOM,
    MENU_BAR_HEIGHT,
    MENU_ICON_SIZE,
    MENU_LABEL_SIZE,
    PAGE_BGCOLOR,
)
from tools.swipe_back import build_swipe_back

# Dropdown carets are Material IconButtons; their default surface/overlay colour
# painted over neighbouring content (the selected 年/月/周 and the popup below
# it). Keep icon buttons fully transparent.
ICON_BUTTON_STYLE = ft.ButtonStyle(
    bgcolor="#00000000",
    overlay_color="#00000000",
)

# 页面进 / 退场动画。Android 那档默认是 `FADE_UPWARDS`：新页淡入并往上移，旧页
# 还留在原地一起淡 —— 两页同时在屏上叠着，这套自己画渐变底的自定义页面就会被
# 看穿，像上一个页面留下的残影（桌面默认的 `ZOOM` 同样要淡）。换成 `CUPERTINO`
# 是纯横向推拉：新旧两页各自整块不透明地滑进滑出，前后不会叠在一起，配边缘返回
# 手势也是这一档最顺。想干脆不要动画，把它换成 `ft.PageTransitionTheme.NONE`。
PAGE_TRANSITION = ft.PageTransitionTheme.CUPERTINO


def build_navigation(page: ft.Page) -> None:
    page.padding = 0
    page.spacing = 0
    # Every colour in this app is a light-mode one (white cards, #172554 text,
    # white-to-indigo wash), so the Material surfaces it does not paint itself -
    # dialogs, menus, snackbars - must stay light too. With the default
    # ThemeMode.SYSTEM a phone in dark mode rendered those surfaces dark and the
    # hard-coded light text on them was barely readable.
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        icon_button_theme=ft.IconButtonTheme(style=ICON_BUTTON_STYLE),
        # 进 / 退场动画见上面的 PAGE_TRANSITION：默认那档会让两页叠出残影。
        page_transitions=ft.PageTransitionsTheme(
            android=PAGE_TRANSITION,
            ios=PAGE_TRANSITION,
            linux=PAGE_TRANSITION,
            macos=PAGE_TRANSITION,
            windows=PAGE_TRANSITION,
        ),
        # Nothing in the app should flash a grey rectangle when tapped: the
        # menu entries and the dialog's triggers and buttons stay flat, so the
        # only thing that changes on a tap is the selected value.
        splash_color="#00000000",
        highlight_color="#00000000",
        hover_color="#00000000",
        focus_color="#00000000",
    )
    content = ft.Container(expand=True)
    selected_index = 0
    # 各页的「选择状态」，按页面名保管。切页时页面控件是重建的（待办数据要现从
    # db 读），但「在看哪个月 / 选了哪一档」这类选择不该跟着回到默认值：切走再
    # 切回来还停在原处，只有热重载重新跑 main() 才回到初始值。
    state_store: dict[str, dict[str, object]] = {}

    def page_state(name: str) -> dict[str, object]:
        return state_store.setdefault(name, {})

    # 页面栈：每往下进一层就压一个「回上一层」的动作。二级 / 三级页的「‹ 返回」
    # 和左滑都走同一个 `go_back`（取栈顶执行），所以从三级页退回二级页时回到的是
    # 二级页自己，再退才是一级页 —— 层数多深都成立。一级页是根，回到它就把栈清空。
    nav_stack: list[Callable[[], None]] = []

    def go_back() -> None:
        """回上一层：顶栏「‹ 返回」、左滑、真机的返回都调它。

        二级 / 三级页各是一层压进 `page.views` 的真 View（见 `show_layer`），所以
        这里要先把顶上那一层弹掉，再让父层把自己重画一遍。
        """
        if not nav_stack:
            return
        parent = nav_stack.pop()
        if len(page.views) > 1:
            page.views.pop()
        parent()

    def on_view_pop(_: ft.ViewPopEvent) -> None:
        """真机的返回落到这儿：Android 的返回键 / 边缘返回手势、iOS 的边缘返回。

        客户端是把它接到 `page.views` 上的。早先整个 App 只有 `views[0]` 一层，
        系统返回没有可弹的层，客户端只能把 Activity 结束掉 —— 看上去就是「一滑就
        回到 Flet 首页」。现在二级 / 三级页都是真 View，返回就有层可弹了。

        一级页（根）上没有 `nav_stack`，`go_back()` 直接返回：在首页按返回仍然是
        退出 App，这是系统的正常行为。
        """
        go_back()

    def show_layer(
        depth: int, route: str, build: Callable[[], ft.Control]
    ) -> None:
        """把 `build()` 画成第 `depth` 层，二级起每层一个真 `ft.View`。

        第 0 层是一级页的外壳（`content` + 底部菜单），由 `show_page` 直接画在
        `page.add()` 建出来的根 View 里。这一层已经存在就重画它（从更深的层退回来
        时走这条），不存在才压一层新的 —— **压出来的必须是真 View**，客户端的
        「返回」和边缘返回手势才有层可弹、才不回把整个 App 结束掉。
        """
        control = build_swipe_back(build(), go_back)
        views = page.views
        if len(views) > depth:
            view = views[depth]
            view.route = route
            view.controls = [control]
        else:
            views.append(
                ft.View(
                    route=route,
                    # View 默认带内边距 / 间距，这一页自己已经把渐变、SafeArea 和
                    # 内边距都画好了，别再叠一层。
                    padding=0,
                    spacing=0,
                    bgcolor=PAGE_BGCOLOR,
                    controls=[control],
                )
            )

    menu_items = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    menu_bottom = MENU_BAR_BOTTOM
    menu_bar = ft.Container(
        left=32,
        right=32,
        bottom=menu_bottom,
        height=MENU_BAR_HEIGHT,
        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
        border_radius=ft.BorderRadius.all(18),
        blur=ft.Blur(16, 16, ft.BlurTileMode.CLAMP),
        gradient=ft.LinearGradient(
            colors=["#66FFFFFF", "#40FFFFFF", "#66FFFFFF"],
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
        ),
        content=menu_items,
    )

    def set_menu_visible(visible: bool) -> None:
        menu_bar.visible = visible
        menu_bar.update()

    def keep_menu_off_keyboard(_: ft.Event[ft.Page]) -> None:
        menu_bar.bottom = menu_bottom - getattr(
            page.media.view_insets, "bottom", 0
        )
        menu_bar.update()

    def show_page(index: int, update: bool = True) -> None:
        nonlocal selected_index
        selected_index = index
        # 一级页是根：回到它就把上面压的层全撤掉，也再没有「上一页」了。
        nav_stack.clear()
        del page.views[1:]
        content.content = (
            build_home_page(
                page, set_menu_visible, show_data, page_state("home")
            )
            if index == 0
            else             build_countdown_page(page, set_menu_visible)
            if index == 1
            else build_calendar_page(
                page,
                set_menu_visible,
                page_state("calendar"),
                show_preferences,
            )
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = True
        build_menu_items()
        if update:
            page.update()

    def render_data(update: bool = True) -> None:
        """只重画「数据」页那**一层**，不动页面栈 —— 从三级页退回二级页回的就是它。"""
        show_layer(
            1,
            "/data",
            lambda: build_data_page(
                page, go_back=go_back, state=page_state("data")
            ),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_data(update: bool = True) -> None:
        """待办页右上角柱状图进来的「数据」页：二级页，进来后底部菜单收起。"""
        # 记下是从哪一个一级页进来的：退回来时回的也是它（写死 0 的话，从别的页
        # 进来就会被摁回待办页）。
        origin = selected_index
        nav_stack.append(lambda: show_page(origin))
        render_data(update)

    def render_preferences(update: bool = True) -> None:
        """只重画设置页那**一层**，不动页面栈（同上）。"""
        show_layer(
            1,
            "/settings",
            lambda: build_preferences_page(
                page,
                # 二级页没有底部菜单：输入框弹键盘、弹窗收起时都不要把它叫回来。
                set_menu_visible=lambda _visible: None,
                go_back=go_back,
            ),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_preferences(update: bool = True) -> None:
        """日历页右上角齿轮进来的设置页：二级页，进来后底部菜单收起。"""
        origin = selected_index
        nav_stack.append(lambda: show_page(origin))
        render_preferences(update)

    def menu_item(
        index: int, icon: str, selected_icon: str, label: str, key: str
    ) -> ft.Control:
        return ft.Container(
            key=key,
            expand=True,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(16),
            ink=True,
            on_click=lambda _: show_page(index),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
                controls=[
                    ft.Icon(
                        selected_icon if selected_index == index else icon,
                        size=MENU_ICON_SIZE,
                        color="#1F2937",
                    ),
                    ft.Text(
                        label,
                        size=MENU_LABEL_SIZE,
                        color="#1F2937",
                        weight=(
                            ft.FontWeight.BOLD
                            if selected_index == index
                            else ft.FontWeight.NORMAL
                        ),
                    ),
                ],
            ),
        )

    def build_menu_items() -> None:
        menu_items.controls = [
            menu_item(0, ft.Icons.HOME_OUTLINED, ft.Icons.HOME, "待办", "home-tab"),
            menu_item(
                1,
                ft.Icons.HOURGLASS_EMPTY,
                ft.Icons.HOURGLASS_BOTTOM,
                "倒数日",
                "countdown-tab",
            ),
            menu_item(
                2,
                ft.Icons.CALENDAR_MONTH_OUTLINED,
                ft.Icons.CALENDAR_MONTH,
                "日历",
                "calendar-tab",
            ),
        ]

    show_page(0, update=False)

    page.add(
        ft.Stack(
            expand=True,
            controls=[
                content,
                menu_bar,
            ],
        )
    )

    page.on_media_change = keep_menu_off_keyboard
    # 真机的「返回」接到页面上：返回键 / 边缘返回手势弹的是一层 View，而不是
    # 把 Activity 结束掉（见 `on_view_pop`）。
    page.on_view_pop = on_view_pop
