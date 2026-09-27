"""设置页：「我的」右上角齿轮进来的二级页。

从「我的」搬过来的两项：通知渠道、清除缓存。页面顶部左边是「‹ 返回」，标题
「设置」落在页面正中（左边返回按钮有多宽，右边就留多宽的空位撑着）。
"""

from collections.abc import Callable

import flet as ft

from tools import db, notifications
from tools.layout import (
    BOTTOM_MENU_INSET,
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    SKY_BLUE,
    UNSELECTED_CARD_BG,
    anchor_dialog_above_keyboard,
    dialog_button_style,
    page_gradient,
    text_width,
)
from tools.popup_select import (
    OPTION_TEXT_SIZE,
    build_option_row,
    build_option_selector,
    build_option_text,
)

CARD_BG = UNSELECTED_CARD_BG
CARD_BORDER = "#E2E8F0"
TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
PENDING_COLOR = "#DC2626"
PAGE_SIDE_PADDING = 24
# 返回按钮占的宽度，右边照抄一份空位，标题才是真正的居中。
BACK_WIDTH = 40
# 点击范围高一点，手指好按；图标本身 22px。
BACK_HEIGHT = 34
BACK_ICON_SIZE = 22
# Material 的箭头图标左右各留了约 8px 空白，直接摆上去会比下面的卡片缩进一截。
# `offset` 是按自身尺寸换算的平移（40px 宽 × -0.2 = 往左 8px），把这段空白抵掉，
# 箭头的笔画就落在内容左边缘上，和下方卡片的左边框对齐。
BACK_OFFSET = -0.2
TITLE_SIZE = 18


def build_preferences_page(
    page: ft.Page,
    set_menu_visible: Callable[[bool], None],
    go_back: Callable[[], None],
) -> ft.Control:
    def notify(message: str) -> None:
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, size=13, color="#FFFFFF"),
                bgcolor=TITLE_COLOR,
                duration=2000,
            )
        )

    def compact_button_style() -> ft.ButtonStyle:
        """Compact metrics of the card's own 清除 action button."""
        return ft.ButtonStyle(
            padding=ft.Padding.symmetric(horizontal=10, vertical=2),
            text_style=ft.TextStyle(size=12),
            visual_density=ft.VisualDensity.COMPACT,
        )

    def settings_dialog(
        title: str, content: ft.Control, actions: list[ft.Control]
    ) -> ft.AlertDialog:
        """Dialog chrome shared by the 清除缓存 and 通知渠道 dialogs."""
        return ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
            # Same surface as the add-todo dialog, so the option panels opening
            # inside a settings dialog can be painted the same colour too.
            bgcolor=DIALOG_SURFACE,
            elevation=0,
            inset_padding=ft.Padding.symmetric(horizontal=48, vertical=24),
            title_padding=ft.Padding.only(left=16, top=12, right=16, bottom=0),
            content_padding=ft.Padding.only(left=16, top=8, right=16, bottom=8),
            actions_padding=ft.Padding.only(left=8, right=8, bottom=8),
            action_button_padding=ft.Padding.symmetric(horizontal=8),
            title=ft.Text(
                title,
                size=16,
                weight=ft.FontWeight.BOLD,
                color=TITLE_COLOR,
            ),
            content=content,
            actions=actions,
        )

    def clear_data(_: ft.Event[ft.Control]) -> None:
        page.pop_dialog()
        removed = db.clear_todos()
        notify(f"已清除 {removed} 条待办数据")

    def confirm_clear(_: ft.Event[ft.Control]) -> None:
        # iOS-style dialog, the one Cupertino control Flet offers: the whole
        # dialog scrolls as one card with the actions stacked under the text.
        page.show_dialog(
            ft.CupertinoAlertDialog(
                modal=True,
                title=ft.Text(
                    "清除缓存",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=TITLE_COLOR,
                ),
                content=ft.Container(
                    padding=ft.Padding.only(top=6),
                    content=ft.Text(
                        "将删除数据库中当前所有的待办数据，且无法恢复。",
                        size=13,
                        color=TITLE_COLOR,
                    ),
                ),
                actions=[
                    ft.CupertinoDialogAction(
                        content=ft.Text("取消", size=14),
                        on_click=lambda _: page.pop_dialog(),
                    ),
                    ft.CupertinoDialogAction(
                        content=ft.Text(
                            "确认清除",
                            size=14,
                            color=PENDING_COLOR,
                            weight=ft.FontWeight.BOLD,
                        ),
                        destructive=True,
                        on_click=clear_data,
                    ),
                ],
            )
        )

    def toggle_cloud(_: ft.Event[ft.Switch]) -> None:
        """云端数据开关：先只做样子，不落库、不发请求。"""

    cloud_switch = ft.Switch(
        value=False,
        active_color="#FFFFFF",
        active_track_color=SKY_BLUE,
        inactive_thumb_color="#FFFFFF",
        inactive_track_color="#E2E8F0",
        on_change=toggle_cloud,
    )

    notify_summary = ft.Text("", size=11, color=MUTED_COLOR)

    def refresh_notify_summary() -> None:
        notify_summary.value = notifications.summary(
            db.get_setting(
                notifications.CHANNEL_SETTING, notifications.DEFAULT_CHANNEL
            ),
            db.get_setting(notifications.URL_SETTING, ""),
        )

    def close_notify_settings() -> None:
        """Dismiss the 通知渠道 dialog and bring the menu bar back."""
        page.pop_dialog()
        set_menu_visible(True)

    def open_notify_settings(_: ft.Event[ft.Container]) -> None:
        """通知渠道 dialog: the channel picker plus its delivery address."""
        channel_text = build_option_text(
            db.get_setting(
                notifications.CHANNEL_SETTING, notifications.DEFAULT_CHANNEL
            )
        )
        selection = {"channel": channel_text.value}

        def pick_channel(name: str) -> None:
            selection["channel"] = name
            channel_text.value = name
            channel_text.update()

        channel_selector = build_option_selector(
            channel_text,
            [(name, name) for name in notifications.CHANNELS],
            pick_channel,
            content_width=max(
                text_width(name, OPTION_TEXT_SIZE)
                for name in notifications.CHANNELS
            ),
        )

        def url_focus_changed(focused: bool) -> None:
            set_menu_visible(not focused)
            anchor_dialog_above_keyboard(dialog, focused)

        url_field = ft.TextField(
            value=db.get_setting(notifications.URL_SETTING, ""),
            hint_text="粘贴通知地址",
            hint_style=ft.TextStyle(size=13, color="#94A3B8"),
            # Same as the 待办内容 field: the keyboard would cover the floating
            # menu bar, so the bar steps out of the way and the dialog parks just
            # above the keyboard while typing.
            on_focus=lambda _: url_focus_changed(True),
            on_blur=lambda _: url_focus_changed(False),
            filled=False,
            border=ft.NoInputBorder(),
            content_padding=ft.Padding.symmetric(horizontal=0, vertical=6),
            text_style=ft.TextStyle(size=13, color="#334155"),
            dense=True,
            height=40,
        )

        def save_notify(_: ft.Event[ft.Control]) -> None:
            db.set_setting(notifications.CHANNEL_SETTING, selection["channel"])
            db.set_setting(
                notifications.URL_SETTING, (url_field.value or "").strip()
            )
            dialog.open = False
            set_menu_visible(True)
            refresh_notify_summary()
            notify_summary.update()
            page.update()
            notify("通知渠道已保存")

        dialog = settings_dialog(
            "通知渠道",
            ft.Column(
                tight=True,
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    build_option_row(channel_selector),
                    url_field,
                ],
            ),
            [
                ft.TextButton(
                    "取消",
                    style=dialog_button_style(),
                    on_click=lambda _: close_notify_settings(),
                ),
                ft.TextButton(
                    "保存",
                    style=dialog_button_style(),
                    on_click=save_notify,
                ),
            ],
        )
        page.show_dialog(dialog)

    def settings_card() -> ft.Control:
        """一个卡片里的两行：通知渠道、清除缓存（标题已经在页面顶部）。"""
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            border_radius=ft.BorderRadius.all(12),
            bgcolor=CARD_BG,
            border=ft.Border.all(1, CARD_BORDER),
            content=ft.Column(
                tight=True,
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Container(
                        border_radius=ft.BorderRadius.all(8),
                        on_click=open_notify_settings,
                        content=ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Column(
                                    tight=True,
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(
                                            "通知渠道",
                                            size=13,
                                            weight=ft.FontWeight.BOLD,
                                            color=TITLE_COLOR,
                                        ),
                                        notify_summary,
                                    ],
                                ),
                                ft.Icon(
                                    ft.Icons.CHEVRON_RIGHT,
                                    size=20,
                                    color="#94A3B8",
                                ),
                            ],
                        ),
                    ),
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                tight=True,
                                spacing=2,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        "清除缓存",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=TITLE_COLOR,
                                    ),
                                    ft.Text(
                                        "删除当前所有的待办数据",
                                        size=11,
                                        color=MUTED_COLOR,
                                    ),
                                ],
                            ),
                            ft.OutlinedButton(
                                "清除",
                                on_click=confirm_clear,
                                style=compact_button_style(),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                tight=True,
                                spacing=2,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        "云端数据",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=TITLE_COLOR,
                                    ),
                                    ft.Text(
                                        "把待办数据同步到云端",
                                        size=11,
                                        color=MUTED_COLOR,
                                    ),
                                ],
                            ),
                            cloud_switch,
                        ],
                    ),
                ],
            ),
        )

    def back_button() -> ft.Control:
        return ft.Container(
            width=BACK_WIDTH,
            height=BACK_HEIGHT,
            alignment=ft.Alignment.CENTER_LEFT,
            offset=ft.Offset(BACK_OFFSET, 0),
            ink=True,
            tooltip="返回",
            on_click=lambda _: go_back(),
            content=ft.Icon(
                ft.Icons.CHEVRON_LEFT,
                size=BACK_ICON_SIZE,
                color=TITLE_COLOR,
            ),
        )

    refresh_notify_summary()

    return ft.Container(
        expand=True,
        gradient=page_gradient(),
        content=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(
                    left=PAGE_SIDE_PADDING,
                    top=PAGE_SIDE_PADDING,
                    right=PAGE_SIDE_PADDING,
                ),
                content=ft.Column(
                    expand=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                back_button(),
                                ft.Container(
                                    expand=True,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Text(
                                        "设置",
                                        size=TITLE_SIZE,
                                        weight=ft.FontWeight.BOLD,
                                        color=TITLE_COLOR,
                                    ),
                                ),
                                # 和返回按钮等宽的占位，标题才落在正中。
                                ft.Container(width=BACK_WIDTH),
                            ],
                        ),
                        ft.ListView(
                            expand=True,
                            spacing=12,
                            scroll=ft.ScrollMode.HIDDEN,
                            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
                            controls=[settings_card()],
                        ),
                    ],
                ),
            ),
        ),
    )
