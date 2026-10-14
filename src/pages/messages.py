"""「消息」页：互动消息（照小红书那一页画的，**没有接口** —— 数据就是下面那两张静态表）。

版式自上而下：
    顶栏（「消息」居中 + 右边搜索 / ＋）
    → 三枚快捷入口（赞和收藏 / 新增关注 / 评论和@）
    → 消息列表（圆角方头像 + 标题（可带小标签 / 认证勾）+ 一句摘要 + 右侧「时间 / 未读徽标」）
    → 底部浮着一条通知提示条（喇叭 + 「开启」+ ✕，点 ✕ 收起）

数据写死在 `SHORTCUTS` / `MESSAGES`：等接了接口，把这两张表换成后端返回的即可，版式不用动
—— 所以这个文件不 import `db` / `api`。头像没有图可用，用「底色 + 一个字 / 一个图标」顶上。
"""

from dataclasses import dataclass
from collections.abc import Callable

import flet as ft

from tools.layout import BOTTOM_MENU_INSET, safe_update
from tools.toast import build_toast

# ---------------------------- 配色（照截图取）----------------------------
PAGE_BG = "#FFFFFF"
TITLE_COLOR = "#1F2937"
MUTED_COLOR = "#94A3B8"
TIME_COLOR = "#9CA3AF"
DIVIDER_COLOR = "#F1F5F9"
RED = "#FF2442"
# 未读徽标：红底白字的小药丸；`DOT_SIZE` 是「只有一个小点」那种（照「活动消息」）。
BADGE_BG = RED
BADGE_HEIGHT = 18
DOT_SIZE = 8
# 快捷入口的小方块。
SHORTCUT_SIZE = 54
SHORTCUT_RADIUS = 16
SHORTCUT_ICON_SIZE = 26
SHORTCUT_LABEL_SIZE = 13
SHORTCUT_LABEL_GAP = 8
# 列表行。
AVATAR_SIZE = 48
AVATAR_RADIUS = 14
ROW_TITLE_SIZE = 15
ROW_HINT_SIZE = 13
ROW_TIME_SIZE = 12
ROW_PADDING_H = 16
ROW_PADDING_V = 12
AVATAR_GAP = 12
# 顶栏那两个图标。
HEADER_ICON_SIZE = 22


@dataclass(frozen=True)
class Shortcut:
    """顶栏下面那三枚快捷入口之一。"""

    label: str
    icon: str
    icon_color: str
    bg: str


@dataclass(frozen=True)
class Message:
    """消息列表里的一行。

    `unread` 给了数字就画红徽标；`dot=True` 画一个小红点（照「活动消息」那一行，
    它没有数字、只有一个点）；两者都不给就什么也不画。
    """

    title: str
    subtitle: str
    time: str
    unread: int | None = None
    dot: bool = False
    # 标题后面那个小标签（「点点 ai」的 ai）。
    tag: str = ""
    # 标题后面那个蓝色认证勾。
    verified: bool = False
    # 头像：默认用标题第一个字 + `avatar_bg`；给了 `avatar_icon` 就画图标。
    avatar_bg: str = "#E2E8F0"
    avatar_fg: str = "#475569"
    avatar_icon: str = ""


SHORTCUTS: tuple[Shortcut, ...] = (
    Shortcut("赞和收藏", ft.Icons.FAVORITE, "#F43F5E", "#FFE4E9"),
    Shortcut("新增关注", ft.Icons.PERSON, "#3B82F6", "#E4EDFF"),
    Shortcut("评论和@", ft.Icons.CHAT_BUBBLE, "#10B981", "#DEF7EC"),
)

MESSAGES: tuple[Message, ...] = (
    Message(
        "大流量自助",
        '"俗人"加入了群聊',
        "13:36",
        unread=1,
        avatar_bg="#FDE9D9",
        avatar_fg="#C2410C",
    ),
    Message(
        "福利29缘185G",
        "该群聊禁言已被解除",
        "昨天",
        unread=30,
        avatar_bg="#E0F2FE",
        avatar_fg="#0369A1",
    ),
    Message(
        "自选套餐19/29r圆180-350G",
        '"四月"加入了群聊',
        "昨天",
        unread=58,
        avatar_bg="#FEF3C7",
        avatar_fg="#B45309",
    ),
    Message(
        "流量卡分享群",
        '"QwYKo әe"加入了群聊',
        "星期一",
        unread=67,
        avatar_bg="#EDE9FE",
        avatar_fg="#6D28D9",
    ),
    Message(
        "点点",
        "想找便宜的云服务器，不能只看价格，关…",
        "10-06",
        tag="ai",
        avatar_bg="#DCFCE7",
        avatar_fg="#15803D",
    ),
    Message(
        "活动消息",
        "户外包挂限量发放中，发笔记免费领！",
        "09-24",
        dot=True,
        avatar_bg="#DBEAFE",
        avatar_icon=ft.Icons.CAMPAIGN,
    ),
    Message(
        "小嘟流量卡-恩趣",
        "1.电信 39元 180G+200分钟",
        "09-23",
        unread=1,
        verified=True,
        avatar_bg="#FFE4E6",
        avatar_fg="#BE123C",
    ),
    Message(
        "流量卡批发",
        "广申39元60G全国通用流量+首月免月租",
        "09-23",
        avatar_bg="#E0E7FF",
        avatar_fg="#4338CA",
    ),
    Message(
        "官方助手",
        "欢迎回来，看看今天有什么新消息",
        "09-20",
        avatar_bg="#F1F5F9",
        avatar_fg="#475569",
        avatar_icon=ft.Icons.NOTIFICATIONS,
    ),
)


def build_messages_page(page: ft.Page) -> ft.Control:
    """「消息」页。点哪儿都只是给个 toast —— 这一版只画版式，不接任何接口。"""

    def notify(text: str) -> None:
        page.show_dialog(build_toast(page, text))

    def icon_button(icon: str, tooltip: str, on_click: Callable[[], None]):
        """顶栏右侧那种小图标按钮：四周补一圈内边距，手指才够得着。"""
        return ft.Container(
            ink=True,
            tooltip=tooltip,
            padding=ft.Padding.all(6),
            on_click=lambda _: on_click(),
            content=ft.Icon(icon, size=HEADER_ICON_SIZE, color=TITLE_COLOR),
        )

    def header() -> ft.Control:
        """「消息」居中、搜索 / ＋ 在右 —— 用 Stack 才真的居中（一行里塞不下对称的空位）。"""
        return ft.Stack(
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            "消息",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=TITLE_COLOR,
                        )
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        icon_button(
                            ft.Icons.SEARCH, "搜索", lambda: notify("搜索暂未开放")
                        ),
                        icon_button(
                            ft.Icons.ADD, "发起聊天", lambda: notify("发起聊天暂未开放")
                        ),
                    ],
                ),
            ],
        )

    def shortcut(item: Shortcut) -> ft.Control:
        """一枚快捷入口：圆角色块 + 里的图标，下面一行字。"""
        return ft.Container(
            ink=True,
            on_click=lambda _: notify(f"{item.label}：暂未开放"),
            content=ft.Column(
                tight=True,
                spacing=SHORTCUT_LABEL_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=SHORTCUT_SIZE,
                        height=SHORTCUT_SIZE,
                        alignment=ft.Alignment.CENTER,
                        border_radius=ft.BorderRadius.all(SHORTCUT_RADIUS),
                        bgcolor=item.bg,
                        content=ft.Icon(
                            item.icon,
                            size=SHORTCUT_ICON_SIZE,
                            color=item.icon_color,
                        ),
                    ),
                    ft.Text(
                        item.label, size=SHORTCUT_LABEL_SIZE, color=TITLE_COLOR
                    ),
                ],
            ),
        )

    def shortcuts() -> ft.Control:
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            controls=[shortcut(item) for item in SHORTCUTS],
        )

    def unread_badge(item: Message) -> ft.Control:
        """右侧那枚未读标记：数字药丸 / 小红点。"""
        if item.unread is not None:
            return ft.Container(
                height=BADGE_HEIGHT,
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.symmetric(horizontal=6),
                border_radius=ft.BorderRadius.all(BADGE_HEIGHT / 2),
                bgcolor=BADGE_BG,
                content=ft.Text(
                    str(item.unread),
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color="#FFFFFF",
                ),
            )
        if item.dot:
            return ft.Container(
                width=DOT_SIZE,
                height=DOT_SIZE,
                margin=ft.Margin.only(right=(BADGE_HEIGHT - DOT_SIZE) / 2),
                border_radius=ft.BorderRadius.all(DOT_SIZE / 2),
                bgcolor=BADGE_BG,
            )
        # 没有未读：留一块同高的空位，右侧两行才对得齐（不然时间会往下掉）。
        return ft.Container(height=BADGE_HEIGHT)

    def avatar(item: Message) -> ft.Control:
        """头像：现在是「底色 + 一个字 / 一个图标」顶上（没有真图可用）。"""
        return ft.Container(
            width=AVATAR_SIZE,
            height=AVATAR_SIZE,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(AVATAR_RADIUS),
            bgcolor=item.avatar_bg,
            content=(
                ft.Icon(item.avatar_icon, size=22, color=item.avatar_fg)
                if item.avatar_icon
                else ft.Text(
                    item.title[0],
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=item.avatar_fg,
                )
            ),
        )

    def title_row(item: Message) -> ft.Control:
        """标题那一行：标题 +（可选的）小标签 / 认证勾。"""
        return ft.Row(
            tight=True,
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    item.title,
                    size=ROW_TITLE_SIZE,
                    weight=ft.FontWeight.BOLD,
                    color=TITLE_COLOR,
                    no_wrap=True,
                ),
                *(
                    [
                        ft.Container(
                            padding=ft.Padding.symmetric(
                                horizontal=5, vertical=1
                            ),
                            border_radius=ft.BorderRadius.all(4),
                            bgcolor="#F1F5F9",
                            content=ft.Text(
                                item.tag, size=10, color=MUTED_COLOR
                            ),
                        )
                    ]
                    if item.tag
                    else []
                ),
                *(
                    [
                        ft.Icon(
                            ft.Icons.VERIFIED, size=14, color="#3B82F6"
                        )
                    ]
                    if item.verified
                    else []
                ),
            ],
        )

    def message_row(item: Message) -> ft.Control:
        """一行消息：左头像、中间「标题 / 摘要」、右边「时间 / 未读」。"""
        return ft.Container(
            ink=True,
            padding=ft.Padding.symmetric(
                horizontal=ROW_PADDING_H, vertical=ROW_PADDING_V
            ),
            on_click=lambda _: notify(f"打开会话：{item.title}"),
            content=ft.Row(
                spacing=AVATAR_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    avatar(item),
                    ft.Column(
                        tight=True,
                        spacing=4,
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            title_row(item),
                            ft.Text(
                                item.subtitle,
                                size=ROW_HINT_SIZE,
                                color=MUTED_COLOR,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                    ft.Column(
                        tight=True,
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        controls=[
                            ft.Text(
                                item.time, size=ROW_TIME_SIZE, color=TIME_COLOR
                            ),
                            unread_badge(item),
                        ],
                    ),
                ],
            ),
        )

    def message_list() -> ft.Control:
        return ft.ListView(
            expand=True,
            spacing=0,
            scroll=ft.ScrollMode.HIDDEN,
            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
            controls=[message_row(item) for item in MESSAGES],
        )

    def notice_bar() -> ft.Control:
        """底部那条通知提示：点了 ✕ 就收起（连通那条一起 —— 它在 Stack 里浮着）。"""
        bar = ft.Container(
            left=12,
            right=12,
            bottom=BOTTOM_MENU_INSET + 6,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=ft.BorderRadius.all(14),
            bgcolor="#FFFFFF",
            border=ft.Border.all(1, DIVIDER_COLOR),
            shadow=ft.BoxShadow(
                blur_radius=18,
                color="#14000000",
                offset=ft.Offset(0, 4),
            ),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=26,
                        height=26,
                        alignment=ft.Alignment.CENTER,
                        border_radius=ft.BorderRadius.all(13),
                        bgcolor="#FEF9C3",
                        content=ft.Icon(
                            ft.Icons.NOTIFICATIONS,
                            size=15,
                            color="#CA8A04",
                        ),
                    ),
                    ft.Text(
                        "打开通知，不再错过互动消息",
                        size=13,
                        color=TITLE_COLOR,
                        expand=True,
                    ),
                    ft.Container(
                        ink=True,
                        on_click=lambda _: notify("通知权限暂未接入"),
                        content=ft.Text(
                            "开启",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=RED,
                        ),
                    ),
                    ft.Container(
                        ink=True,
                        tooltip="关闭提示",
                        padding=ft.Padding.all(2),
                        on_click=lambda _: dismiss(),
                        content=ft.Icon(
                            ft.Icons.CLOSE, size=16, color=MUTED_COLOR
                        ),
                    ),
                ],
            ),
        )

        def dismiss() -> None:
            bar.visible = False
            # 走 safe_update：没挂在页面上（比如这一页已经被换掉）时不硬刷。
            safe_update(bar)

        return bar

    return ft.Container(
        expand=True,
        bgcolor=PAGE_BG,
        content=ft.SafeArea(
            expand=True,
            content=ft.Stack(
                expand=True,
                controls=[
                    ft.Container(
                        expand=True,
                        padding=ft.Padding.only(top=8),
                        content=ft.Column(
                            expand=True,
                            spacing=16,
                            horizontal_alignment=(
                                ft.CrossAxisAlignment.STRETCH
                            ),
                            controls=[
                                header(),
                                shortcuts(),
                                message_list(),
                            ],
                        ),
                    ),
                    notice_bar(),
                ],
            ),
        ),
    )
