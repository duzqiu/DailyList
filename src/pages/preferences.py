"""设置页：日历页右上角齿轮进来的二级页。

三档设置卡片，每档一张：**通知设置**（通知渠道）、**数据设置**（导出 JSON、云端
数据）、**通用设置**（当前版本、联系方式、清除缓存）—— 档名是卡片上的小标题，
条目都摆在自己那张卡片里
（见 settings_section）。顶栏用 tools/layout.py 的 build_subpage_header：左边是
「‹ 返回」，标题「设置」落在页面正中（左边返回按钮有多宽，右边就留多宽的空位撑
着）。
"""

import asyncio
import logging
from collections.abc import Callable

import flet as ft

from tools import data_export, data_import, db, notifications, version_check
from tools.layout import (
    BOTTOM_MENU_INSET,
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    SKY_BLUE,
    UNSELECTED_CARD_BG,
    anchor_dialog_above_keyboard,
    build_subpage_header,
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
from tools.services import ensure_service
from tools.toast import build_toast

logger = logging.getLogger(__name__)

CARD_BG = UNSELECTED_CARD_BG
CARD_BORDER = "#E2E8F0"
TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
PENDING_COLOR = "#DC2626"
PAGE_SIDE_PADDING = 24
# 检查新版本时，右边那枚版本号先换成这句，回来再换回版本号。
CHECKING_LABEL = "检查中…"
# 联系方式（摆在「通用设置」那张卡片里，点一下把值复制到剪贴板）。
CONTACTS = (
    ("邮箱", "duzqiu@outlook.com"),
    ("微信", "test001"),
)


def build_preferences_page(
    page: ft.Page,
    set_menu_visible: Callable[[bool], None],
    go_back: Callable[[], None],
) -> ft.Control:
    def notify(message: str) -> None:
        """一句话的提示：走 `tools/toast.py`，浮在**屏幕中间**（不再是底部那条）。"""
        page.show_dialog(build_toast(page, message))

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

    # 复制和导出各要一个 Service（剪贴板、文件选择器）。它们不能像控件那样随手挂到
    # 页面上 —— 必须**真注册**（见 tools/services.py）：`page.services.append()` 只
    # 往清单里塞个对象、不推给客户端，客户端不认识它，之后调它的方法就是干等，10 秒
    # 后抛 TimeoutException。
    clipboard = ensure_service(page, ft.Clipboard)
    export_picker = ensure_service(page, ft.FilePicker)

    async def copy_contact(label: str, value: str) -> None:
        """点一下联系方式：把值复制到剪贴板，再吱一声复制的是哪一条。"""
        try:
            await clipboard.set(value)
        except Exception:
            # 复制失败也得应一声，别让人点了没反应；栈打进日志方便查。
            logger.exception("复制联系方式失败")
            notify("复制失败")
            return
        notify(f"已复制{label}")

    async def export_data() -> None:
        """导出数据：把库里的东西拍成一份 JSON，交给系统去存。

        桌面端弹「另存为」；手机和 Web 上 `save_file` 表现为导出 / 下载 —— 这几种
        平台上 `src_bytes` 必须给（不给会直接抛 `ValueError`），内容在内存里就先
        备好了。用户取消返回 `None`，存下了才有值（手机返回的路径不可用，只拿它
        判存没存）。
        """
        name = data_export.export_file_name()
        try:
            saved = await export_picker.save_file(
                dialog_title="导出为 JSON 文件",
                file_name=name,
                # Flet 的 `file_type` 只有 any / media / image / video / audio /
                # custom 这几档，没有「文本档」—— 要限定后缀就得走 CUSTOM +
                # allowed_extensions。它只管对话框筛不筛，不校验内容。
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=[data_export.EXPORT_FORMAT],
                src_bytes=data_export.export_bytes(),
            )
        except Exception:
            logger.exception("导出数据失败")
            notify("导出失败")
            return
        if saved:
            notify("已导出 JSON 数据")

    def confirm_import(_: ft.Event[ft.Control]) -> None:
        """导入前的二次确认 —— 它会把现在的待办与倒数日整表换掉，不能点错就进去。"""
        page.show_dialog(
            ft.CupertinoAlertDialog(
                modal=True,
                title=ft.Text(
                    "导入数据",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=TITLE_COLOR,
                ),
                content=ft.Container(
                    padding=ft.Padding.only(top=6),
                    content=ft.Text(
                        "会用 JSON 文件里的内容替换现在的待办与倒数日，且无法撤销。",
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
                            "选择文件",
                            size=14,
                            color=PENDING_COLOR,
                            weight=ft.FontWeight.BOLD,
                        ),
                        destructive=True,
                        on_click=pick_import_file,
                    ),
                ],
            )
        )

    def pick_import_file(_: ft.Event[ft.Control]) -> None:
        """关掉确认框再去挑文件（挑文件是异步的，交给 `run_task`）。"""
        page.pop_dialog()
        page.run_task(import_data)

    async def import_data() -> None:
        """挑一个 JSON 文件导进库；结果用一句提示说清楚。"""
        files = await export_picker.pick_files(
            dialog_title="选择要导入的 JSON 文件",
            # 和导出同理：Flet 的 `file_type` 没有「文本档」这一档，限定后缀得走
            # CUSTOM + allowed_extensions。
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=[data_export.EXPORT_FORMAT],
            # 让 Flet 把内容一并读进来：手机上返回的路径不可用，只有 bytes 靠得住。
            with_data=True,
        )
        if not files:
            return
        chosen = files[0]
        raw = chosen.bytes
        if not raw and chosen.path:
            # 有的平台 `with_data` 只回路径，桌面端就自己补读一次。
            try:
                with open(chosen.path, "rb") as handle:
                    raw = handle.read()
            except OSError:
                logger.exception("读取导入文件失败")
        if not raw:
            notify("读不到文件内容")
            return

        try:
            result = data_import.import_bytes(raw)
        except data_import.ImportFailed as failure:
            # 这一步的消息本来就是写给用户看的（「不是 JSON」之类），直接弹。
            notify(str(failure))
            return
        except Exception:
            logger.exception("导入数据失败")
            notify("导入失败")
            return
        notify(result.summary())

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

    def settings_section(
        title: str, rows: list[ft.Control]
    ) -> ft.Control:
        """一档设置：卡片上方一行小标题（灰字），底下的卡片里摆这一档的各行。"""
        return ft.Column(
            tight=True,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(
                    title,
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=MUTED_COLOR,
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                    border_radius=ft.BorderRadius.all(12),
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        controls=rows,
                    ),
                ),
            ],
        )

    def setting_row(
        title: str,
        subtitle: ft.Control,
        action: ft.Control | None = None,
    ):
        """卡片里的一行：左边「标题 + 小字说明」，右边跟一个动作控件。

        纯展示的行（当前版本）不给动作，右边就空着。
        """
        return ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    tight=True,
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(
                            title,
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_COLOR,
                        ),
                        subtitle,
                    ],
                ),
                *([action] if action is not None else []),
            ],
        )

    def notify_row() -> ft.Control:
        """通知设置那一行：通知渠道 —— 点开弹窗改渠道和推送地址。"""
        return ft.Container(
            border_radius=ft.BorderRadius.all(8),
            on_click=open_notify_settings,
            content=setting_row(
                "通知渠道",
                notify_summary,
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color="#94A3B8"),
            ),
        )

    def export_row() -> ft.Control:
        """数据设置那一行：导出数据（JSON）。

        小字里就写明是 JSON 文件 —— 点之前用户就知道会拿到个什么样的文件。
        """
        return setting_row(
            "导出数据",
            ft.Text(
                "导出为 JSON 文件",
                size=11,
                color=MUTED_COLOR,
                no_wrap=True,
            ),
            ft.OutlinedButton(
                "导出",
                # async 处理器交给 `run_task` 跑（和首页「+」面板那两条入口一个
                # 路子），别直接挂在 on_click 上。
                on_click=lambda _: page.run_task(export_data),
                style=compact_button_style(),
            ),
        )

    def import_row() -> ft.Control:
        """数据设置那一行：导入数据（从导出的 JSON 恢复）。

        小字里就写明**会覆盖** —— 这一行按下去是要整表换掉的，得先说清楚。
        """
        return setting_row(
            "导入数据",
            ft.Text(
                "从 JSON 恢复，会覆盖现有数据",
                size=11,
                color=MUTED_COLOR,
                no_wrap=True,
            ),
            ft.OutlinedButton(
                "导入",
                on_click=confirm_import,
                style=compact_button_style(),
            ),
        )

    def cloud_row() -> ft.Control:
        """数据设置那一行：云端数据（开关先只做样子，不落库、不发请求）。"""
        return setting_row(
            "云端数据",
            ft.Text(
                "把待办数据同步到云端", size=11, color=MUTED_COLOR
            ),
            cloud_switch,
        )

    def check_version_row() -> ft.Control:
        """通用设置那一行：检查新版本 —— 右边写着当前版本号，点它去仓库问一次。

        查询走网络，别堵事件循环：`latest_version()` 自己就是个阻塞的标准库调用，
        所以扔给 `asyncio.to_thread` 跑。
        """
        version_text = ft.Text(
            version_check.APP_VERSION,
            size=11,
            color=MUTED_COLOR,
            no_wrap=True,
        )

        async def check_version() -> None:
            """问一次仓库上的最新版本，结果用一句 toast 说清楚。"""
            # 请求期间把版本号换成「检查中…」，回来再换回去 —— 网络慢时点了也不至
            # 于毫无动静。
            version_text.value = CHECKING_LABEL
            version_text.update()
            latest = None
            try:
                latest = await asyncio.to_thread(version_check.latest_version)
            except Exception:
                logger.exception("检查新版本失败")
            version_text.value = version_check.APP_VERSION
            version_text.update()

            # `latest_version()` 的三种返回对应三句不同的话，别混着说。
            if latest is None:
                notify("检查失败，请稍后重试")
            elif not latest:
                notify("还没有已发布的版本")
            elif version_check.is_newer(latest):
                notify(f"发现新版本 {latest}")
            else:
                notify("已是最新版本")

        return ft.Container(
            border_radius=ft.BorderRadius.all(8),
            on_click=lambda _: page.run_task(check_version),
            content=setting_row(
                "检查新版本",
                ft.Text(
                    "点这里看有没有新版本",
                    size=11,
                    color=MUTED_COLOR,
                    no_wrap=True,
                ),
                version_text,
            ),
        )

    def contact_row(label: str, value: str) -> ft.Control:
        """通用设置里的联系方式行：点一下把值复制走。

        右边那枚复制图标既是「可以点」的提示，也把这行和上面几行区分开。
        """
        return ft.Container(
            border_radius=ft.BorderRadius.all(8),
            on_click=lambda _: page.run_task(copy_contact, label, value),
            content=setting_row(
                label,
                ft.Text(value, size=11, color=MUTED_COLOR, no_wrap=True),
                ft.Icon(ft.Icons.COPY, size=16, color="#94A3B8"),
            ),
        )

    def clear_row() -> ft.Control:
        """通用设置那一行：清除缓存。"""
        return setting_row(
            "清除缓存",
            ft.Text(
                "删除当前所有的待办数据", size=11, color=MUTED_COLOR
            ),
            ft.OutlinedButton(
                "清除",
                on_click=confirm_clear,
                style=compact_button_style(),
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
                        build_subpage_header("设置", go_back),
                        ft.ListView(
                            expand=True,
                            spacing=12,
                            scroll=ft.ScrollMode.HIDDEN,
                            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
                            controls=[
                                # 三档设置，各一张卡片，条目摆在自己那张里。
                                settings_section(
                                    "通知设置", [notify_row()]
                                ),
                                settings_section(
                                    "数据设置",
                                    [export_row(), import_row(), cloud_row()],
                                ),
                                settings_section(
                                    "通用设置",
                                    [
                                        check_version_row(),
                                        *(
                                            contact_row(label, value)
                                            for label, value in CONTACTS
                                        ),
                                        clear_row(),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        ),
    )
