"""设置页：「我的」页左上角那枚 ☰ 进来的二级页。

两档卡片，每档一张：**通知设置**（通知提醒总开关、通知渠道）、**通用设置**（当前版本、
联系方式、清除缓存、退出登录）—— 档名是卡片上的小标题，条目都摆在自己那张卡片里
（见 settings_section）。原来那张「账号」卡片已经搬去「我的」页（pages/my.py），两页共用
widgets/settings_card.py 里的同一套零件。

每张卡片都是**透明底**（用户要求）：`settings_section(..., bgcolor=None)` —— 卡片自己不铺色，
露出来的是页面那层渐变，边框照旧留着（方框的样子还在）。

**「数据设置」那一档整块去掉了**（导出 / 导入 JSON、云端开关 —— 用户要求）：页面里那几条
处理函数（导出 / 导入 / 云端开关）连同对 `tools/data_export.py`、`tools/data_import.py`、
`mock_settings` 里那个云端键的调用一起删了（那两个工具模块还留在 `tools/`，只是暂时没人用；
要恢复这一档，照原来那版接回来即可）。

**「通知渠道」那一行不再弹窗**：原来点开是个弹窗（挑渠道 + 填推送地址），现在点一下只给一句
提示（用户要求，功能先不做）。渠道 / 地址照旧从 `tools/notifications.py` 读，那行小字
（`notify_summary`）还是显示当前配的是什么。

顶栏用 widgets/layout.py 的 build_subpage_header：左边是「‹ 返回」，标题「设置」落在页面
正中（左边返回按钮有多宽，右边就留多宽的空位撑着）。
"""

import asyncio
import logging
from collections.abc import Callable

import flet as ft

from api import member_auth, session
from api.client import ApiError
from tools import (
    contacts,
    countdown_store,
    mock_settings,
    notifications,
    version_check,
)
from widgets.layout import (
    BOTTOM_MENU_INSET,
    SKY_BLUE,
    build_subpage_header,
    page_gradient,
)
from widgets.layout import safe_update
from widgets.services import ensure_service
# 「账号」卡片搬去「我的」页了（pages/my.py），它和设置页共用这几个卡片零件 —— 实现
# 收在 widgets/settings_card.py 一处，两边都从这儿取（`settings_section` / `setting_row` /
# `compact_button_style` 的本地定义已删掉，避免两份会各自漂移）。
from widgets.settings_card import (
    compact_button_style,
    setting_row,
    settings_section,
)
from widgets.toast import build_toast

logger = logging.getLogger(__name__)

# 卡片底色：**透明**（用户要求）—— 每张卡片都走 `settings_section(..., bgcolor=None)`：
# 卡片自己不铺色，露出来的就是页面那层渐变，边框还留着（方框的样子还在）。原来那两枚
# `CARD_BG` / `CARD_BORDER` 常量（白卡片 + 深一档的描边）没人用了，一并删掉。
TITLE_COLOR = "#172554"
MUTED_COLOR = "#64748B"
PENDING_COLOR = "#DC2626"
PAGE_SIDE_PADDING = 24
# 检查新版本时，右边那枚版本号先换成这句，回来再换回版本号。
CHECKING_LABEL = "检查中…"
# 「通知渠道」那一行点一下给的那句话：渠道 / 地址那个弹窗先不做了（用户要求），
# 但这一行照旧可点、照旧显示当前配的渠道（见 notify_row）。
NOTIFY_CHANNEL_TOAST = "通知渠道：设置暂未开放"
# 通知提醒总开关那两行小字（跟着开关换：关着的时候说清「填了也不发」，别让人只看见
# 一串地址以为提醒是活的）+ 拨动时的一句提示。文案放一起，免得两边对不上。
# （开关存哪个键、值是什么，见 tools/notifications.py。）
NOTIFY_ON_LABEL = "有新提醒时按下面的渠道推送"
NOTIFY_OFF_LABEL = "关着的时候不推送提醒"
NOTIFY_ON_TOAST = "已开启通知提醒"
NOTIFY_OFF_TOAST = "已关闭通知提醒"
# 页面最下方那行署名。App 名和 pyproject.toml 的 `product` 是一对，版本跟着
# tools/version_check.py 的 `APP_VERSION` 走（不在版本里重复一遍），版权年份发版时改。
APP_NAME = "每日资讯"
APP_COPYRIGHT = "© 2026 duzqiu"


def build_preferences_page(
    page: ft.Page,
    go_back: Callable[[], None],
    open_login: Callable[[], None],
) -> ft.Control:
    """设置页。

    `open_login` 由 pages/navigation.py 给：「账号」那张卡片里点「登录」/「管理」时
    调用它 —— 登录页压在设置页之上，返回回到这一页。

    原来还有一个 `set_menu_visible` 入参（给「通知渠道」那个弹窗和通知地址输入框用的：
    收弹窗 / 弹键盘时把底部菜单栏叫回来）。那个弹窗没了之后它就没人用了，一并去掉。
    """
    def notify(message: str) -> None:
        """一句话的提示：走 `widgets/toast.py`，浮在**屏幕中间**（不再是底部那条）。"""
        page.show_dialog(build_toast(page, message))

    def clear_data(_: ft.Event[ft.Control]) -> None:
        page.pop_dialog()
        # 「清除缓存」= 把本地这份**内存缓存**倒空（倒数日列表来自后端，下次进那一页会重新拉）。
        # 原先清的是本地 SQLite 的 countdowns 表，而那一页早就不读那张表了 —— 清了跟没清一样，
        # 提示里还在报「已清除 N 个」（见 README「待处理问题」）。
        countdown_store.clear()
        notify("已清除本地缓存")

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
                        "将清空本地缓存（倒数日列表下次进页面会重新拉）。",
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

    # 复制联系方式要一个 Service（剪贴板）。它不能像控件那样随手挂到页面上 —— 必须
    # **真注册**（见 widgets/services.py）：`page.services.append()` 只往清单里塞个对象、
    # 不推给客户端，客户端不认识它，之后调它的方法就是干等，10 秒后抛 TimeoutException。
    # （导出 / 导入原来那个文件选择器服务，随「数据设置」那张卡片一起去掉了。）
    clipboard = ensure_service(page, ft.Clipboard)

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
            mock_settings.get_setting(
                notifications.CHANNEL_SETTING, notifications.DEFAULT_CHANNEL
            ),
            mock_settings.get_setting(notifications.URL_SETTING, ""),
        )

    # 「通知提醒」总开关：它管「发不发」，所以摆在**卡片里自己一行**（原来那个「通知
    # 渠道」弹窗管的是「怎么发」—— 往哪个渠道、地址是什么）。拨一下只写内存、不落库
    # （设置项都在 tools/mock_settings.py 那张内存表里），当次运行内一直是这档。
    notify_switch = ft.Switch(
        value=(
            mock_settings.get_setting(
                notifications.ENABLED_SETTING, notifications.ENABLED_OFF
            )
            == notifications.ENABLED_ON
        ),
        active_color="#FFFFFF",
        active_track_color=SKY_BLUE,
        inactive_thumb_color="#FFFFFF",
        inactive_track_color="#E2E8F0",
    )

    notify_state_summary = ft.Text(
        "",
        size=11,
        color=MUTED_COLOR,
        # 和上面那行一个道理：只放一句话，放不下就省略，别折行把卡片顶高。
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    def refresh_notify_state() -> None:
        """那行小字跟着开关走（关着时说清「填了也不发」）。"""
        notify_state_summary.value = (
            NOTIFY_ON_LABEL if notify_switch.value else NOTIFY_OFF_LABEL
        )

    def toggle_notify_enabled(_: ft.Event[ft.Switch]) -> None:
        """拨一下：立刻写进内存、换掉自己那行小字，并弹一句提示。

        **不动「通知渠道」那行**：它的摘要只说渠道和地址配没配好，和总开关是两码事
        （联动的话，关掉提醒会让这一行看不出地址到底填了没有）。
        """
        mock_settings.set_setting(
            notifications.ENABLED_SETTING,
            notifications.ENABLED_ON
            if notify_switch.value
            else notifications.ENABLED_OFF,
        )
        refresh_notify_state()
        notify_state_summary.update()
        notify(
            NOTIFY_ON_TOAST if notify_switch.value else NOTIFY_OFF_TOAST
        )

    # 先建控件、再挂处理函数 —— `ft.Switch(on_change=...)` 是**构建时**求值，
    # 写在处理函数之前会直接 `UnboundLocalError`。
    notify_switch.on_change = toggle_notify_enabled

    def notify_enabled_row() -> ft.Control:
        """通知设置卡片里的第一行：通知提醒总开关。

        拨一下写内存（见 `toggle_notify_enabled`），不跟「通知渠道」那一行绑在一起。
        """
        return setting_row("通知提醒", notify_state_summary, notify_switch)

    def notify_row() -> ft.Control:
        """通知设置那一行：通知渠道 —— 点一下**只给一句提示**（用户要求）。

        原来是点开一个弹窗（挑渠道 + 填推送地址）。弹窗撤了、渠道也暂时不做，所以这一行
        只把当前配的渠道 / 地址（`notify_summary`）摆着看，点一下提示「暂未开放」——
        处理函数留在 `tools/notifications.py`，之后要做直接照原来那版弹窗接回来。
        """
        return ft.Container(
            border_radius=ft.BorderRadius.all(8),
            on_click=lambda _: notify(NOTIFY_CHANNEL_TOAST),
            content=setting_row(
                "通知渠道",
                notify_summary,
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color="#94A3B8"),
            ),
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
        """通用设置那一行：清除缓存（见 clear_data）。"""
        return setting_row(
            "清除缓存",
            ft.Text("清空本地缓存", size=11, color=MUTED_COLOR),
            ft.OutlinedButton(
                "清除",
                on_click=confirm_clear,
                style=compact_button_style(),
            ),
        )

    def logout_row() -> ft.Control:
        """通用设置最后一行：**退出登录**（只在登录状态下摆出来）。

        这个动作原来在登录页的已登录形态里（pages/login.py 的 `do_logout`）—— 现在挂到
        「清除缓存」下面：设置页才是「配置」的地方，「要不要退出」归它管。

        令牌由 `member_auth.logout` 清掉（后端是无状态 JWT，只是应一声，见 api/session.py）；
        清完把这一行收掉（已经是未登录了）。没登录时这一行不出现：那时候没有「退出」可点。
        （原先这里还顺手重画了「云端数据」那一行的小字 —— 那张卡片已经整块去掉，不用了。）
        """
        if not session.access_token():
            return ft.Container(visible=False)

        async def do_logout() -> None:
            try:
                await member_auth.logout()
            except ApiError as error:
                # `logout` 在 finally 里清令牌，所以这里只把后端的抱怨说一声，照样算退出。
                notify(error.message)
            row.visible = False
            # 走 safe_update：退出是**异步**做完的（等后端应一声），回来时这一页可能
            # 已经被换掉了（切走就重建），硬 update 会抛「must be added to the page
            # first」—— 和倒数日页那处同一个道理。
            safe_update(row)
            notify("已退出登录")

        def on_logout(_: ft.Event[ft.Control]) -> None:
            page.run_task(do_logout)

        row = ft.Container(
            content=setting_row(
                "退出登录",
                ft.Text(
                    "清掉本机保存的登录凭证", size=11, color=MUTED_COLOR
                ),
                ft.OutlinedButton(
                    "退出",
                    on_click=on_logout,
                    style=compact_button_style(),
                ),
            )
        )
        return row

    def app_info() -> ft.Control:
        """页面最下方那行署名：App 名 + 版本 + 版权，居中一行灰字。

        它就是「最后一张卡片下面」的一小块，跟着内容一起滚 —— 所以直接塞在 ListView
        末尾，不占固定高度。字色比卡片里的说明还浅一档，它是落款，不该抢内容；宽度
        拉满靠 `text_align` 居中（ListView 的子项本来就是满宽的）。
        """
        return ft.Text(
            f"{APP_NAME} {version_check.APP_VERSION} · {APP_COPYRIGHT}",
            size=11,
            color="#94A3B8",
            no_wrap=True,
            text_align=ft.TextAlign.CENTER,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    refresh_notify_state()
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
                                # 两档设置，各一张卡片，条目摆在自己那张里。
                                # （「账号」原来摆在这上头 —— 已整块搬到「我的」页，
                                # 见 pages/my.py；「数据设置」那一档按用户要求去掉了。）
                                # `bgcolor=None`：卡片**不铺色**（透明），露出来的是页面那层
                                # 渐变 ——「我的」页那张个人信息卡片也是这个做法。
                                settings_section(
                                    "通知设置",
                                    [notify_enabled_row(), notify_row()],
                                    bgcolor=None,
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
                                        # 退出登录紧挨在「清除缓存」下面（只登录时出现）。
                                        logout_row(),
                                    ],
                                    bgcolor=None,
                                ),
                                # 落款：两张卡片下面的一小块署名（跟着内容滚）。
                                app_info(),
                            ],
                        ),
                    ],
                ),
            ),
        ),
    )
