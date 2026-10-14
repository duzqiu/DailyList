"""「首页」页：发现流 / 关注（照小红书首页复刻，**没有接口** —— 数据就是下面那几张静态表）。

版式：
- **顶栏**：三个一级 tab（关注 / 发现 / 上海）**居中**，左右两头分别是「菜单」和「搜索」。
- 选中**关注** → 关注列表（「关注的人」+「可能感兴趣的人」两段，每行「用户 + 关注 + ✕」）。
- 选中**发现 / 上海** → 二级标签排 + 双列瀑布流卡片。两者**同一套数据**，区别只有一个：
  **上海那排最前面多一个「全城 ▾」**（它不是 tab、是个位置选择器，点了只给提示）；
  发现没有它。
- **每个二级 tab 各有各的数据**（`NOTES_BY_CHIP`）。

几条实现上的取舍：
- Flet 没有 masonry/瀑布流控件：用「两个 `Column` 并排 + 一个 `ListView` 装着这一行」凑 ——
  整行一起滚，看着就是瀑布流；哪张进哪列按**估算高度**贪心分配（`_split_columns`）。
- 没有真图可用：图片位用**渐变色块**顶上（高度各不相同，正是瀑布流的错落感）。
- 关注页的「关注 / ✕」只在本地生效（一个 `set` 记着状态），退出页面就还原 —— 没有接口。

接接口时把 `TOP_TABS` / `CHIP_TABS` / `NOTES_BY_CHIP` / `FOLLOWING` / `SUGGESTED` 换成
后端返回的即可，版式不用动。
"""

from dataclasses import dataclass

import flet as ft

from tools.layout import BOTTOM_MENU_INSET, safe_update
from tools.toast import build_toast

# ---------------------------- 配色（照截图取）----------------------------
PAGE_BG = "#FFFFFF"
TITLE_COLOR = "#1F2937"
MUTED_COLOR = "#94A3B8"
CHIP_IDLE = "#6B7280"
LINK_COLOR = "#3B82F6"  # 话题标签那种蓝
RED = "#FF2442"
HIGHLIGHT_BG = "#FEF3A3"  # 正文里的「荧光笔」底色
CHIP_BG = "#F1F5F9"
LIKE_COLOR = "#94A3B8"
CARD_RADIUS = 10
CARD_GAP = 10
# 顶栏。
TOP_TAB_SIZE = 16
TOP_TAB_UNDERLINE_W = 26
TOP_TAB_GAP = 22
CHIP_SIZE = 14
CHIP_UNDERLINE_W = 18
TAB_BAR_H = 2.5
# 卡片。
NOTE_TITLE_SIZE = 14
NOTE_META_SIZE = 12
NOTE_TAG_SIZE = 12
FOOTER_SIZE = 11
FOOTER_AVATAR = 20
# 关注列表。
USER_AVATAR = 44
USER_NAME_SIZE = 14
USER_HINT_SIZE = 12
FOLLOW_BTN_W = 62
FOLLOW_BTN_H = 28
# 在内容区左右滑一下切二级 tab：走满这么多像素、或者甩得够快，都算一次切换
# （左右滑切二级 tab 与竖着列表的滚动不冲突，见 `on_swipe_*` 那几个回调）。
SWIPE_DISTANCE = 24.0
SWIPE_VELOCITY = 300.0
# 切 tab 时**由客户端做交叉淡入淡出**（`ft.AnimatedSwitcher`，见 `body`）。之前是自己算
# 起始 offset + `animate_offset` 滑过来（隐式动画），真机上一点效果都看不到 —— 那条路别
# 再走回去了。
SWITCH_MS = 220


@dataclass(frozen=True)
class Note:
    """瀑布流里的一张卡。

    `media` 是图片位的高度（0 = 没有图片、纯文字卡）；`media_color` 是那块渐变的起色。
    `title_lines` 只用于**估算高度**好分配列，别的地方不用。
    """

    title: str
    media: int = 0
    media_color: str = "#CBD5E1"
    highlight: str = ""  # 正文里那一段高亮（纯文字卡用）
    tags: str = ""  # 蓝色话题标签，一行
    place: str = ""  # 定位小胶囊
    distance: str = ""
    meta: str = ""  # 标题下面那行小字（「明天 周四 19:30」那种）
    author: str = "还在"
    likes: int = 0
    title_lines: int = 1


@dataclass(frozen=True)
class User:
    """关注列表里的一行。"""

    name: str
    hint: str
    avatar_bg: str = "#F1F5F9"
    avatar_fg: str = "#475569"


# ---------------------------- 静态数据 ----------------------------
# 三个一级 tab。「关注」那一页是用户列表，另外两个是发现流（见文件头的说明）。
TOP_TABS: tuple[str, ...] = ("关注", "发现", "上海")
TOP_TAB_SELECTED = 2
# 「全城」不是 tab：它是位置选择器（带 ▾），只在「上海」那一页出现，点了给个提示。
LOCATION_LABEL = "全城"
# 二级 tab（发现 / 上海 共用这一排）。
CHIP_TABS: tuple[str, ...] = ("推荐", "活动", "美食", "新热打卡", "周末出逃")
CHIP_SELECTED = 0

NOTES_BY_CHIP: dict[str, tuple[Note, ...]] = {
    "推荐": (
        Note(
            title="张江集贤天地银联食堂可以混进去吃饭嘛？可以用手机支付嘛还是必须得刷"
            "他们饭卡之类的？🤔",
            highlight="张江集贤天地银联食堂可以混进去吃饭嘛？",
            tags="#食堂 #干饭人食堂 #张江 #集贤天地 #银联 #创芯…",
            place="长鑫存储技术有限公司",
            distance="794m",
            author="还在",
            likes=10,
            title_lines=5,
        ),
        Note(
            title="上海已迎来 Citywalk 最佳赏味期",
            media=210,
            media_color="#7DD3FC",
            author="泽拉图图",
            likes=1323,
        ),
        Note(
            title="魔都新地标 | 我很少用震撼来形容一个地方",
            media=330,
            media_color="#FDBA74",
            author="魔都小分队",
            likes=866,
            title_lines=2,
        ),
        Note(
            title="10.15 零基础英文创意游戏",
            media=190,
            media_color="#C4B5FD",
            meta="明天 周四 19:30",
            place="长宁区",
            author="大鱼营造",
            likes=64,
            title_lines=1,
        ),
        Note(
            title="工作日中午的滨江，人少景好还免费",
            media=260,
            media_color="#86EFAC",
            author="周末去哪儿",
            likes=278,
            title_lines=2,
        ),
        Note(
            title="一个人吃饭也可以很认真 | 15 家小馆子清单",
            media=230,
            media_color="#FCA5A5",
            author="干饭笔记",
            likes=531,
            title_lines=2,
        ),
    ),
    "活动": (
        Note(
            title="本周末｜梧桐区手作市集，带娃友好",
            media=220,
            media_color="#FCD34D",
            meta="周六 周日 10:00 - 18:00",
            place="徐汇区 · 永康路",
            author="市集情报",
            likes=186,
        ),
        Note(
            title="免费展｜城市与记忆：老照片里的上海",
            media=180,
            media_color="#A5B4FC",
            meta="展至 11.20",
            place="静安区 · 明当代美术馆",
            author="看展搭子",
            likes=274,
            title_lines=2,
        ),
        Note(
            title="夜跑召集｜滨江 5 公里，配速随意",
            media=200,
            media_color="#6EE7B7",
            meta="周三 20:00 集合",
            place="杨浦区 · 杨浦滨江",
            author="夜跑小组",
            likes=95,
        ),
        Note(
            title="露天电影｜今晚《海上钢琴师》",
            media=240,
            media_color="#FCA5A5",
            meta="今晚 19:30 免费",
            place="虹口区 · 北外滩",
            author="露天放映",
            likes=312,
            title_lines=2,
        ),
    ),
    "美食": (
        Note(
            title="愚园路这家面包店，可颂脆到掉渣",
            media=230,
            media_color="#FDE68A",
            place="长宁区 · 愚园路",
            distance="1.2km",
            author="面包脑袋",
            likes=728,
        ),
        Note(
            title="人均 40 的本帮菜，本地人从小吃到大",
            media=260,
            media_color="#FDBA74",
            place="黄浦区 · 老西门",
            tags="#本帮菜 #上海味道 #苍蝇馆子",
            author="干饭笔记",
            likes=1204,
            title_lines=2,
        ),
        Note(
            title="深夜 12 点还开着的面馆清单（8 家）",
            media=210,
            media_color="#FCA5A5",
            tags="#深夜食堂 #面馆 #夜宵",
            author="夜宵地图",
            likes=642,
            title_lines=2,
        ),
    ),
    "新热打卡": (
        Note(
            title="武康大楼的三角梅开了，取景位在这",
            media=300,
            media_color="#F9A8D4",
            place="徐汇区 · 武康路",
            author="citywalk 笔记",
            likes=2310,
        ),
        Note(
            title="新开的书店 + 咖啡，坐一下午不想走",
            media=220,
            media_color="#C4B5FD",
            place="静安区 · 陕西北路",
            author="逛店日记",
            likes=486,
            title_lines=2,
        ),
        Note(
            title="外滩这个机位，第一次拍也不用修图",
            media=250,
            media_color="#93C5FD",
            place="黄浦区 · 外滩源",
            author="拍照小能手",
            likes=1533,
            title_lines=2,
        ),
    ),
    "周末出逃": (
        Note(
            title="离上海 1 小时｜淀山湖边露营看日落",
            media=280,
            media_color="#6EE7B7",
            meta="自驾约 1h",
            place="青浦区 · 淀山湖",
            author="周末去哪儿",
            likes=918,
        ),
        Note(
            title="苏州一日往返｜园林 + 面馆 + 书店",
            media=240,
            media_color="#FDE68A",
            meta="高铁 25 分钟",
            author="出逃计划",
            likes=677,
            title_lines=2,
        ),
        Note(
            title="崇明岛看候鸟，带望远镜别带零食",
            media=210,
            media_color="#A7F3D0",
            meta="往返约 3h",
            place="崇明区 · 东滩",
            author="自然观察",
            likes=402,
            title_lines=2,
        ),
    ),
}

# 关注页两段。
FOLLOWING: tuple[User, ...] = (
    User("泽拉图图", "常看 citywalk · 互相关注", "#E0F2FE", "#0369A1"),
    User("干饭笔记", "同城美食 · 三天前互动", "#FEF3C7", "#B45309"),
    User("大鱼营造", "关注的活动主办方", "#EDE9FE", "#6D28D9"),
)
SUGGESTED: tuple[User, ...] = (
    User("魔都小分队", "你常看的人", "#FFE4E9", "#BE123C"),
    User("周末去哪儿", "近期互动较多", "#DCFCE7", "#15803D"),
    User("市集情报", "同城同好", "#DBEAFE", "#1D4ED8"),
    User("夜宵地图", "美食 · 新账号", "#FCE7F3", "#BE185D"),
)


def _split_columns(notes: tuple[Note, ...]) -> tuple[list[Note], list[Note]]:
    """把卡片按**估算高度**贪心分到两列：每张都投给当前较矮的那一列。

    估算 = 图片高度 + 标题行数×18 + 标签/定位/小字那些加一点 + 底部那行 26。
    够粗糙，但足以让两列长短不齐得别太明显。
    """
    heights = [0.0, 0.0]
    columns: list[list[Note]] = [[], []]
    for note in notes:
        estimate = (
            note.media
            + note.title_lines * 18
            + (20 if note.tags else 0)
            + (22 if note.place else 0)
            + (18 if note.meta else 0)
            + (16 if note.highlight else 0)
            + 26
        )
        target = 0 if heights[0] <= heights[1] else 1
        columns[target].append(note)
        heights[target] += estimate
    return columns[0], columns[1]


def build_feed_page(page: ft.Page) -> ft.Control:
    """「首页」页。切 tab / 点关注都只在本地生效，其余点击给 toast。"""

    # 当前选中的一级 tab、二级 tab（下标）；关注页里「已关注 / 已隐藏」两份本地状态。
    state = {"top": TOP_TAB_SELECTED, "chip": CHIP_SELECTED}
    followed: set[str] = set()
    hidden: set[str] = set()

    def notify(text: str) -> None:
        page.show_dialog(build_toast(page, text))

    # ---------------------- 顶栏（三个 tab 居中）---------------------

    def top_tab(index: int) -> ft.Control:
        """顶栏一个 tab：文字 +（选中才亮的）红下划线。"""
        chosen = index == state["top"]
        label = ft.Text(
            TOP_TABS[index],
            size=TOP_TAB_SIZE,
            weight=ft.FontWeight.BOLD if chosen else ft.FontWeight.NORMAL,
            color=TITLE_COLOR if chosen else MUTED_COLOR,
        )
        bar = ft.Container(
            width=TOP_TAB_UNDERLINE_W,
            height=TAB_BAR_H,
            border_radius=ft.BorderRadius.all(TAB_BAR_H / 2),
            bgcolor=RED if chosen else None,
        )
        return ft.Container(
            ink=True,
            on_click=lambda _: select_top(index),
            content=ft.Column(
                tight=True,
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[label, bar],
            ),
        )

    top_tabs_row = ft.Row(
        tight=True,
        spacing=TOP_TAB_GAP,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    def fill_top_tabs() -> None:
        top_tabs_row.controls = [top_tab(i) for i in range(len(TOP_TABS))]

    def top_bar() -> ft.Control:
        """三个 tab **居中**，两头各一枚图标 —— 用 `Stack` 叠（一行里塞不出对称空位）。"""
        return ft.Stack(
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[top_tabs_row],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            ink=True,
                            tooltip="菜单",
                            padding=ft.Padding.all(6),
                            on_click=lambda _: notify("菜单暂未开放"),
                            content=ft.Icon(
                                ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                                size=24,
                                color=TITLE_COLOR,
                            ),
                        ),
                        ft.Container(
                            ink=True,
                            tooltip="搜索",
                            padding=ft.Padding.all(6),
                            on_click=lambda _: notify("搜索暂未开放"),
                            content=ft.Icon(
                                ft.Icons.SEARCH, size=22, color=TITLE_COLOR
                            ),
                        ),
                    ],
                ),
            ]
        )

    def select_top(index: int) -> None:
        state["top"] = index
        fill_top_tabs()
        # 换 key → 客户端播一次交叉淡入淡出（见 render_body）。
        render_body()
        safe_update(top_tabs_row, chip_bar, body)

    # ---------------------- 二级标签排（发现 / 上海）---------------------

    def location_selector() -> ft.Control:
        """「全城 ▾」：**不是 tab** —— 位置选择器，点了只给提示（用户要求）。"""
        return ft.Container(
            ink=True,
            on_click=lambda _: notify(f"{LOCATION_LABEL}：选择城市暂未开放"),
            content=ft.Row(
                tight=True,
                spacing=2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        LOCATION_LABEL,
                        size=CHIP_SIZE,
                        color=CHIP_IDLE,
                    ),
                    ft.Icon(
                        ft.Icons.KEYBOARD_ARROW_DOWN,
                        size=16,
                        color=MUTED_COLOR,
                    ),
                ],
            ),
        )

    def chip(index: int) -> ft.Control:
        chosen = index == state["chip"]
        label = ft.Text(
            CHIP_TABS[index],
            size=CHIP_SIZE,
            weight=ft.FontWeight.BOLD if chosen else ft.FontWeight.NORMAL,
            color=TITLE_COLOR if chosen else CHIP_IDLE,
        )
        bar = ft.Container(
            width=CHIP_UNDERLINE_W,
            height=TAB_BAR_H,
            border_radius=ft.BorderRadius.all(TAB_BAR_H / 2),
            bgcolor=RED if chosen else None,
        )
        return ft.Container(
            ink=True,
            on_click=lambda _: select_chip(index),
            content=ft.Column(
                tight=True,
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[label, bar],
            ),
        )

    chip_row = ft.Row(
        spacing=18,
        scroll=ft.ScrollMode.HIDDEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    def fill_chips() -> None:
        # 「上海」那一页最前面多一个「全城」，发现没有（其余完全一样）。
        head = [location_selector()] if TOP_TABS[state["top"]] == "上海" else []
        chip_row.controls = [
            *head,
            *[chip(i) for i in range(len(CHIP_TABS))],
        ]

    def select_chip(index: int) -> None:
        """换二级 tab（点标签、左右滑都走这条）。"""
        state["chip"] = index
        fill_chips()
        render_body()
        # 标签排现在在 `chip_bar` 里（body 之外），两块都要刷。
        safe_update(chip_bar, body)

    def step_chip(delta: int) -> None:
        """左右滑一格。到头了就不动（不弹提示，免得滑一下就吵一句）。"""
        target = state["chip"] + delta
        if not 0 <= target < len(CHIP_TABS):
            return
        select_chip(target)

    # 这一趟横滑走了多少像素，松手时按它（或者甩的速度）决定算不算一次切换。
    swipe: dict[str, float] = {"dx": 0.0}

    def on_swipe_start(_: ft.DragStartEvent) -> None:
        swipe["dx"] = 0.0

    def on_swipe_update(e: ft.DragUpdateEvent) -> None:
        if e.local_delta:
            swipe["dx"] += e.local_delta.x

    def on_swipe_end(e: ft.DragEndEvent) -> None:
        travelled = swipe["dx"]
        swipe["dx"] = 0.0
        fling = e.velocity.x if e.velocity else 0.0
        # 左滑看下一个二级 tab、右滑看上一个。
        if travelled <= -SWIPE_DISTANCE or fling <= -SWIPE_VELOCITY:
            step_chip(1)
        elif travelled >= SWIPE_DISTANCE or fling >= SWIPE_VELOCITY:
            step_chip(-1)

    def on_swipe_cancel(_: ft.Event[ft.GestureDetector]) -> None:
        swipe["dx"] = 0.0

    # ---------------------- 关注页 ----------------------

    def follow_button(user: User) -> ft.Control:
        """「关注 / 已关注」按钮：点一下就地切换（只存本地）。"""
        chosen = user.name in followed
        return ft.Container(
            width=FOLLOW_BTN_W,
            height=FOLLOW_BTN_H,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(FOLLOW_BTN_H / 2),
            bgcolor=None if chosen else RED,
            border=ft.Border.all(1, RED),
            ink=True,
            on_click=lambda _: toggle_follow(user),
            content=ft.Text(
                "已关注" if chosen else "关注",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=RED if chosen else "#FFFFFF",
            ),
        )

    def toggle_follow(user: User) -> None:
        if user.name in followed:
            followed.discard(user.name)
        else:
            followed.add(user.name)
        render_body()
        safe_update(body)

    def dismiss_user(user: User) -> None:
        """右边那个 ✕：把这一行从列表里去掉（本地）。"""
        hidden.add(user.name)
        render_body()
        safe_update(body)

    def user_row(user: User) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=USER_AVATAR,
                        height=USER_AVATAR,
                        alignment=ft.Alignment.CENTER,
                        border_radius=ft.BorderRadius.all(USER_AVATAR / 2),
                        bgcolor=user.avatar_bg,
                        content=ft.Text(
                            user.name[0],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=user.avatar_fg,
                        ),
                    ),
                    ft.Column(
                        tight=True,
                        spacing=3,
                        expand=True,
                        controls=[
                            ft.Text(
                                user.name,
                                size=USER_NAME_SIZE,
                                weight=ft.FontWeight.BOLD,
                                color=TITLE_COLOR,
                            ),
                            ft.Text(
                                user.hint,
                                size=USER_HINT_SIZE,
                                color=MUTED_COLOR,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                    follow_button(user),
                    ft.Container(
                        ink=True,
                        tooltip="不感兴趣",
                        padding=ft.Padding.all(4),
                        on_click=lambda _: dismiss_user(user),
                        content=ft.Icon(
                            ft.Icons.CLOSE, size=16, color=MUTED_COLOR
                        ),
                    ),
                ],
            ),
        )

    def follow_section(title: str, users: tuple[User, ...]) -> ft.Control:
        rows = [user_row(u) for u in users if u.name not in hidden]
        return ft.Column(
            tight=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=16, right=16, top=14, bottom=6),
                    content=ft.Text(
                        title,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color="#64748B",
                    ),
                ),
                *rows,
                *(
                    [
                        ft.Container(
                            padding=ft.Padding.only(left=16, top=6),
                            content=ft.Text(
                                "暂无更多",
                                size=12,
                                color=MUTED_COLOR,
                            ),
                        )
                    ]
                    if not rows
                    else []
                ),
            ],
        )

    def follow_view() -> ft.Control:
        return ft.ListView(
            expand=True,
            spacing=0,
            scroll=ft.ScrollMode.HIDDEN,
            padding=ft.Padding.only(bottom=BOTTOM_MENU_INSET),
            controls=[
                follow_section("关注的人", FOLLOWING),
                follow_section("可能感兴趣的人", SUGGESTED),
            ],
        )

    # ---------------------- 瀑布流 ----------------------

    def media_block(note: Note) -> ft.Control:
        """图片位：一段渐变（没有真图，用色块顶上，高度各不一样）。"""
        return ft.Container(
            height=note.media,
            border_radius=ft.BorderRadius.all(CARD_RADIUS),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[note.media_color, "#F8FAFC"],
            ),
        )

    def footer(note: Note) -> ft.Control:
        """卡片底部那行：头像 + 昵称 +（右边）赞。"""
        return ft.Row(
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=FOOTER_AVATAR,
                    height=FOOTER_AVATAR,
                    alignment=ft.Alignment.CENTER,
                    border_radius=ft.BorderRadius.all(FOOTER_AVATAR / 2),
                    bgcolor=CHIP_BG,
                    content=ft.Icon(
                        ft.Icons.PERSON, size=12, color=MUTED_COLOR
                    ),
                ),
                ft.Text(note.author, size=FOOTER_SIZE, color=MUTED_COLOR),
                ft.Container(expand=True),
                ft.Icon(ft.Icons.FAVORITE_BORDER, size=14, color=LIKE_COLOR),
                ft.Text(str(note.likes), size=FOOTER_SIZE, color=LIKE_COLOR),
            ],
        )

    def place_chip(note: Note) -> ft.Control:
        """定位小胶囊：📍 + 地点 +（可选）距离。"""
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            border_radius=ft.BorderRadius.all(20),
            bgcolor=CHIP_BG,
            content=ft.Row(
                tight=True,
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.LOCATION_ON, size=12, color=MUTED_COLOR),
                    ft.Text(note.place, size=NOTE_META_SIZE, color="#64748B"),
                    *(
                        [
                            ft.Container(width=1, height=10, bgcolor="#CBD5E1"),
                            ft.Text(
                                note.distance,
                                size=NOTE_META_SIZE,
                                color=MUTED_COLOR,
                            ),
                        ]
                        if note.distance
                        else []
                    ),
                ],
            ),
        )

    def note_card(note: Note) -> ft.Control:
        body: list[ft.Control] = []
        if note.media:
            body.append(media_block(note))
        if note.highlight:
            # 正文里那段「荧光笔」：高亮底 + 深一点的字。
            body.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                    bgcolor=HIGHLIGHT_BG,
                    border_radius=ft.BorderRadius.all(4),
                    content=ft.Text(
                        note.highlight,
                        size=NOTE_TITLE_SIZE,
                        weight=ft.FontWeight.BOLD,
                        color="#1F2937",
                    ),
                )
            )
        body.append(
            ft.Text(
                note.title,
                size=NOTE_TITLE_SIZE,
                weight=ft.FontWeight.BOLD,
                color=TITLE_COLOR,
                max_lines=note.title_lines,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )
        if note.tags:
            body.append(
                ft.Text(
                    note.tags,
                    size=NOTE_TAG_SIZE,
                    color=LINK_COLOR,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
        if note.meta:
            body.append(
                ft.Text(note.meta, size=NOTE_META_SIZE, color=MUTED_COLOR)
            )
        tail: list[ft.Control] = []
        if note.place:
            tail.append(place_chip(note))
        tail.append(footer(note))
        return ft.Container(
            ink=True,
            padding=ft.Padding.only(bottom=6),
            on_click=lambda _: notify(f"打开笔记：{note.title[:12]}…"),
            content=ft.Column(
                tight=True,
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    *body,
                    ft.Column(tight=True, spacing=8, controls=tail),
                ],
            ),
        )

    def waterfall() -> ft.Control:
        """两列并排 —— 整行一起滚，看着就是瀑布流（Flet 没有 masonry）。"""
        notes = NOTES_BY_CHIP[CHIP_TABS[state["chip"]]]
        left, right = _split_columns(notes)

        def column(items: list[Note]) -> ft.Control:
            return ft.Column(
                expand=True,
                spacing=CARD_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[note_card(note) for note in items],
            )

        return ft.ListView(
            expand=True,
            spacing=0,
            scroll=ft.ScrollMode.HIDDEN,
            padding=ft.Padding.only(left=12, right=12, bottom=BOTTOM_MENU_INSET),
            controls=[
                ft.Row(
                    spacing=CARD_GAP,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[column(left), column(right)],
                )
            ],
        )

    # ---------------------- 主体：按一级 tab 换 ----------------------

    # 主体：一级 / 二级 tab 换内容的地方。用 **`ft.AnimatedSwitcher`** —— 换 `content` 时
    # **客户端**自己让旧内容淡出、新内容淡入（交叉淡入淡出）。⚠️ 别再退回「自己算偏移 +
    # `animate_offset`」那一套：真机上一点效果都看不到。
    # 初始给空占位，真身在 `page.add()` 之前就换上（见文件末尾的 `render_body()`），
    # 所以首屏不会先闪一下。
    body = ft.AnimatedSwitcher(
        content=ft.Container(),
        duration=SWITCH_MS,
        reverse_duration=SWITCH_MS,
        transition=ft.AnimatedSwitcherTransition.FADE,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
        expand=True,
    )

    # 二级标签排**单独占一层**，不放进 `body` 里：切二级 tab 时它不该跟着一起动
    # （它是「切换器」本身），只有内容换 —— 和真机上的观感一致。只有「发现 / 上海」显示它。
    chip_bar = ft.Container(
        padding=ft.Padding.only(left=12, right=12, top=6, bottom=8),
        content=chip_row,
    )

    def render_body() -> None:
        """按当前的「一级 tab + 二级 tab」重建内容；**换 key** 客户端才播一次过渡。

        key 用「一级 + 二级」拼：只有真换了 tab 才变 —— 在同一个 tab 上刷新数据（点收藏、
        划掉一张卡、切一级 tab 再回来）不播动画，正好对上这两种不同场景。
        """
        if TOP_TABS[state["top"]] == "关注":
            # 关注页没有二级标签排。
            chip_bar.visible = False
            view: ft.Control = follow_view()
            key = "feed-follow"
        else:
            fill_chips()
            chip_bar.visible = True
            # 卡片区域包一层手势：在这一块上左右滑 = 切二级 tab（横滑自己判定，
            # 竖着的列表滚动照旧 —— 横滑只判横着走的那一截）。
            view = ft.GestureDetector(
                expand=True,
                on_pan_start=on_swipe_start,
                on_pan_update=on_swipe_update,
                on_pan_end=on_swipe_end,
                on_pan_cancel=on_swipe_cancel,
                content=waterfall(),
            )
            key = f"feed-{state['top']}-{state['chip']}"
        view.key = key
        body.content = view

    fill_top_tabs()
    render_body()

    return ft.Container(
        expand=True,
        bgcolor=PAGE_BG,
        content=ft.SafeArea(
            expand=True,
            content=ft.Column(
                expand=True,
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Container(
                        padding=ft.Padding.only(
                            left=12, right=12, top=6, bottom=8
                        ),
                        content=top_bar(),
                    ),
                    chip_bar,
                    body,
                ],
            ),
        ),
    )
