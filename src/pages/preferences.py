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

from tools import (
    contacts,
    data_export,
    data_import,
    db,
    notifications,
    version_check,
)
from tools.app_settings import CLOUD_OFF, CLOUD_ON, CLOUD_SETTING
from tools.layout import (
    BOTTOM_MENU_INSET,
    DIALOG_RADIUS,
    DIALOG_SURFACE,
    SKY_BLUE,
    UNSELECTED_CARD_BG,
    build_subpage_header,
    dialog_button_style,
    page_gradient,
    text_width,
    track_keyboard,
)
from tools.popup_select import (
    MENU_HEIGHT,
    OPTION_TEXT_SIZE,
    build_option_row,
    build_option_selector,
    build_option_text,
    option_text,
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
# 通知渠道下拉里那枚图标：尺寸 16、名字前留 8 的空当；颜色比正文浅一档，让它站在辅助
# 的位置上，别和渠道名抢眼。宽度会一起算进面板宽度（见 open_notify_settings）。
CHANNEL_ICON_SIZE = 16
CHANNEL_ICON_GAP = 8
CHANNEL_ICON_COLOR = "#475569"
# 通知地址那一格的高度：输入框和「平时显示的那行文字」共用，点开时高度不跳。
URL_FIELD_HEIGHT = 40
# 云端数据的两种状态：一行小字说明 + 开关时的一句提示。文案放一起，免得两边对不上。
# （开关存哪个键、值是什么，见 tools/app_settings.py。）
CLOUD_ON_LABEL = "本地数据会同步到云端"
CLOUD_OFF_LABEL = "数据只保存在本机"
CLOUD_ON_TOAST = "已开启云端同步"
CLOUD_OFF_TOAST = "已关闭云端同步"


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

    cloud_switch = ft.Switch(
        # 状态存在 `settings` 里（键见 tools/app_settings.py）：关掉之后再进来还是
        # 关着。表里没有这个键时按 `CLOUD_OFF` 算 —— 默认**关着**，云端同步是后加
        # 的能力，不该在用户还没表态时替他打开。
        value=db.get_setting(CLOUD_SETTING, CLOUD_OFF) == CLOUD_ON,
        active_color="#FFFFFF",
        active_track_color=SKY_BLUE,
        inactive_thumb_color="#FFFFFF",
        inactive_track_color="#E2E8F0",
    )

    cloud_summary = ft.Text(
        "",
        size=11,
        color=MUTED_COLOR,
        # 和通知渠道那行一个道理：这里只放一句话，放不下就省略，别折行把卡片顶高。
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    def refresh_cloud_summary() -> None:
        """小字说明跟着开关走：关着说「只存本机」，开着才提「同步云端」。"""
        cloud_summary.value = (
            CLOUD_ON_LABEL if cloud_switch.value else CLOUD_OFF_LABEL
        )

    def toggle_cloud(_: ft.Event[ft.Switch]) -> None:
        """云端数据开关：先只做样子，不落库、不发请求。

        但**开、关都要说一声** —— 这个开关管的是「数据出不出本机」，值得让用户知道
        自己刚做了什么（小字说明同时跟着换）。
        """
        db.set_setting(
            CLOUD_SETTING, CLOUD_ON if cloud_switch.value else CLOUD_OFF
        )
        refresh_cloud_summary()
        cloud_summary.update()
        notify(CLOUD_ON_TOAST if cloud_switch.value else CLOUD_OFF_TOAST)

    # 处理函数等开关和说明都摆好之后再挂上去：`ft.Switch(on_change=...)` 是**构建时**
    # 求值（不像函数体那样延迟解析），写在前面会直接 `UnboundLocalError`。
    cloud_switch.on_change = toggle_cloud

    notify_summary = ft.Text(
        "",
        size=11,
        color=MUTED_COLOR,
        # 通知地址可以很长（钉钉那种带一串 access_token 的尤其）：这一行**绝不折行**
        # —— 一折就把上面「通知渠道」那行顶下去、卡片跟着变高，而且断在半截的地址
        # 也没法看。放不下就省略号收尾。
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

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

    def channel_icon(name: str, size: int = CHANNEL_ICON_SIZE) -> ft.Icon:
        """渠道图标控件。图标不跟着系统字号缩放 —— 放大了会把面板挤出去。"""
        return ft.Icon(
            notifications.channel_icon(name),
            size=size,
            color=CHANNEL_ICON_COLOR,
            apply_text_scaling=False,
        )

    def channel_label(name: str) -> ft.Control:
        """下拉里的一项：图标 + 渠道名。"""
        return ft.Row(
            tight=True,
            spacing=CHANNEL_ICON_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[channel_icon(name), option_text(name)],
        )

    def open_notify_settings(_: ft.Event[ft.Container]) -> None:
        """通知渠道 dialog: the channel picker plus its delivery address."""
        selected = db.get_setting(
            notifications.CHANNEL_SETTING, notifications.DEFAULT_CHANNEL
        )
        channel_text = build_option_text(selected)
        # 触发按钮上也挂一枚图标，选完渠道它跟着换。
        trigger_icon = channel_icon(selected)
        selection = {"channel": selected}

        def pick_channel(name: str) -> None:
            selection["channel"] = name
            channel_text.value = name
            trigger_icon.icon = notifications.channel_icon(name)
            channel_text.update()
            trigger_icon.update()

        channel_selector = build_option_selector(
            # 触发按钮就是「图标 + 渠道名」，和面板里的项同一个样子。
            ft.Row(
                tight=True,
                spacing=CHANNEL_ICON_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[trigger_icon, channel_text],
            ),
            [(name, name) for name in notifications.CHANNELS],
            pick_channel,
            # 九个渠道一屏摆不下：面板钉成固定高度，多出来的在里面上下滚。
            menu_height=MENU_HEIGHT,
            # 面板宽度得把图标也一起算进去 —— 否则行宽按纯文字钉死，图标会把名字挤出
            # 面板（行宽是按 `content_width` 定死的，不会自己撑开）。
            content_width=(
                max(
                    text_width(name, OPTION_TEXT_SIZE)
                    for name in notifications.CHANNELS
                )
                + CHANNEL_ICON_SIZE
                + CHANNEL_ICON_GAP
            ),
            label_builder=channel_label,
        )

        def url_focus_changed(focused: bool) -> None:
            """键盘弹起时把底部菜单栏收走。

            **只干这一件** —— 挪弹窗那件事交给下面的 `track_keyboard`：焦点事件比
            键盘动画早到一步，照焦点挪的话弹窗会先往屏幕底下一沉（键盘还没起来），
            等键盘真升上来再弹回去，看上去就是「先下拉、再弹起」。
            """
            set_menu_visible(not focused)

        url_field = ft.TextField(
            value=db.get_setting(notifications.URL_SETTING, ""),
            hint_text="粘贴通知地址",
            hint_style=ft.TextStyle(size=13, color="#94A3B8"),
            # 地址很长，这一格必须是**单行**：长地址在格子里横向滚，别折成两行
            # （`multiline` 默认就是 False，这里写出来是防止以后被改成 True）。
            multiline=False,
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
            height=URL_FIELD_HEIGHT,
        )

        # 地址平时是一行**省略号收尾的文字**，点一下才换成上面那格输入框。
        # Flet 的 `TextField` 没有 `overflow`：长链接塞进去只会被硬裁（右边直接切
        # 掉，连省略号都不给），而省略号只有 `ft.Text` 上才有。所以「看」和「改」
        # 分成两层 —— 默认这层专门用来看，点一下才换成能输入的。
        url_value = db.get_setting(notifications.URL_SETTING, "")
        url_display = ft.Container(
            height=URL_FIELD_HEIGHT,
            alignment=ft.Alignment.CENTER_LEFT,
            content=ft.Text(
                url_value or "粘贴通知地址",
                size=13,
                color="#334155" if url_value else "#94A3B8",
                no_wrap=True,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        )

        url_slot = ft.Container()

        async def focus_url() -> None:
            """再显式要一次焦点。

            `focus()` 是**方法**（async），不是布尔字段 —— 写成 `url_field.focus =
            True` 只会把方法覆盖掉，客户端那边一点动静都没有（这正是「点了输入框
            光标不出来」的原因）。
            """
            try:
                await url_field.focus()
            except Exception:
                logger.debug("通知地址格没能自动聚焦", exc_info=True)

        def start_editing(_: ft.Event[ft.Container]) -> None:
            """从「看」切到「改」：换上输入框，并把光标送进去。

            两头都要：`autofocus` 管控件**挂上去那一帧**，`focus_url` 等它挂稳之后
            再要一次 —— 万一这一帧客户端漏了，光标也还是落得进去。
            """
            url_slot.content = url_field
            url_slot.on_click = None
            url_field.autofocus = True
            page.update()
            page.run_task(focus_url)

        url_slot.content = url_display
        url_slot.on_click = start_editing

        def dismiss(_: ft.Event[ft.Control]) -> None:
            """关掉这个弹窗：先拆掉键盘跟随，再走页面那套关闭流程。"""
            unwatch_keyboard()
            close_notify_settings()

        def save_notify(_: ft.Event[ft.Control]) -> None:
            db.set_setting(notifications.CHANNEL_SETTING, selection["channel"])
            db.set_setting(
                notifications.URL_SETTING, (url_field.value or "").strip()
            )
            unwatch_keyboard()
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
                    url_slot,
                ],
            ),
            [
                ft.TextButton(
                    "取消",
                    style=dialog_button_style(),
                    on_click=dismiss,
                ),
                ft.TextButton(
                    "保存",
                    style=dialog_button_style(),
                    on_click=save_notify,
                ),
            ],
        )
        # 键盘一升一落都把弹窗挪到键盘上方 / 回到正中（见 track_keyboard）。
        # 挂在 media 事件上而不是焦点上 —— 和新增待办、新增倒数日那两个弹窗一个做法。
        unwatch_keyboard = track_keyboard(page, dialog)
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
        """数据设置那一行：云端数据（开关先只做样子，不落库、不发请求）。

        小字不是死文案 —— 它跟着开关在「只存本机」和「同步到云端」之间换（见
        `refresh_cloud_summary`）。
        """
        return setting_row("云端数据", cloud_summary, cloud_switch)

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
    refresh_cloud_summary()

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
                                            for label, value in contacts.items()
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
