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

# Dropdown carets are Material IconButtons; their default surface/overlay colour
# painted over neighbouring content (the selected 年/月/周 and the popup below
# it). Keep icon buttons fully transparent.
ICON_BUTTON_STYLE = ft.ButtonStyle(
    bgcolor="#00000000",
    overlay_color="#00000000",
)


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
        content.content = (
            build_home_page(page, set_menu_visible, show_data)
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

    def show_data(update: bool = True) -> None:
        """待办页右上角柱状图进来的「数据」页：二级页，进来后底部菜单收起。"""
        content.content = build_data_page(
            page,
            go_back=lambda: show_page(0),
            state=page_state("data"),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_preferences(update: bool = True) -> None:
        """日历页右上角齿轮进来的设置页：二级页，进来后底部菜单收起。"""
        content.content = build_preferences_page(
            page,
            # 二级页没有底部菜单：输入框弹键盘、弹窗收起时都不要把它叫回来。
            set_menu_visible=lambda _visible: None,
            go_back=lambda: show_page(2),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

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
