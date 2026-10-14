"""登录 / 注册 / 忘记密码这三页共用的表单骨架。

三页除了「有哪些字段、按钮点了做什么」，其余是同一套：渐变底 + `SafeArea` + 左右 24
的内边距、顶栏「‹ 返回」+ 居中标题、卡片、等高的输入框、整宽的主按钮、卡片下面那行
小字链接；表单整体**偏上**摆，而且位置是固定的 —— 键盘升起、视口被压矮时它不会跟着
往上挤（见 `FORM_TOP_RATIO`）。

**背景**：整页铺一张柔和的蓝调图（`AUTH_BACKGROUND_SRC`，在 `src/assets/images/` 下），
上面再压一层很淡的白纱（`WASH_GRADIENT`）把照片的对比度压下去 —— 卡片与输入框上的字才稳。

**毛玻璃**：卡片是**一块玻璃**—— 半透明白底 + 背后模糊（`GLASS_*`）+ 一圈更亮的细边，
圆角靠 `clip_behavior` 裁，否则模糊是按矩形铺的、四角会漏出方糊斑。输入框是压在玻璃上的
**第二层**（更透一点，`FIELD_GLASS_BG`），前面带一枚对应的小图标（邮箱 / 密码 / 验证码，见
`FIELD_ICONS`）。玻璃「有东西可糊」才看得出磨砂感 —— 现在糊的就是那张背景图。

输入框钉了统一高度（`FIELD_HEIGHT`），外层小框和里面的输入框同高，内容压在格子中线上。

抽到这儿是因为一份实现、三页共用，别重复造控件（见 README 开发约定 2）—— 三页将来
一起调样式时只有这一处要动；页面自己只管字段和动作。

配色全部取自 tools/layout.py 已经给出的那几档，这里不新起颜色：边线是设置页卡片边框
那一档浅灰，主按钮的底色就是那档「选中」的蓝（`DATE_SELECTED_BG`），字色是全 App 的
深蓝（这个底色够浅，按 `readable_ink` 的判断本来就该配深字）。
"""

import asyncio
from collections.abc import Callable

import flet as ft

from tools.layout import (
    AUTH_BACKGROUND_SRC,
    DATE_SELECTED_BG,
    PAGE_BGCOLOR,
    SUBPAGE_TITLE_COLOR,
    build_subpage_header,
)

# ============================ 毛玻璃 ============================
# 和底部菜单栏、折线图浮框、设置页卡片同一套做法：半透明底 + `ft.Blur`。
# 两点必须一起给，少一个都不是玻璃：
# ① **底色要有，而且必须半透明** —— `blur` 糊的是背后那层，全透明（或不填色）等于没糊；
# ② **`clip_behavior`** —— `blur` 按控件那块**矩形**铺、不跟圆角裁，圆角卡片不裁就会在
#    四角漏出一块方糊斑（真机上翻过这个车）。
# 底下两位是 alpha（00 = 全透、FF = 不透明）：卡片给 `#78`（≈47% 的白，**放得更透**才能
# 看出它糊的是背后那张背景图），`blur` 跟着**往大调** —— 这两样是一对：越透就得糊得越
# 狠，只把底色变透而模糊不变，底下的图案会直接穿上来，卡片上的字是清楚了、磨砂感却没了。
GLASS_BG = "#78FFFFFF"
GLASS_BORDER = "#99FFFFFF"
GLASS_BLUR = ft.Blur(32, 32, ft.BlurTileMode.CLAMP)
# 输入框那层比卡片再透一点：卡片是「一块玻璃」，字段是「玻璃上又压一层」，靠深浅分层。
# `#66` ≈ 40%，跟着卡片一起往下调，**仍是更透的那一层**（两者的深浅关系别反过来）。
FIELD_GLASS_BG = "#66FFFFFF"
# 字段前方那枚图标：尺寸、与文字之间的距离，以及「带图标时」的左内边距。
# 带图标后左内边距要收窄一点，让「图标 + 文字」整体看着仍然居中。
FIELD_ICON_SIZE = 16
FIELD_ICON_GAP = 8
FIELD_LEADING_INSET = 10
# 字段文案 → 图标：按关键字匹配（各页 build_auth_field 的 hint 见下）。
# ⚠️ 顺序有意义：「请输入邮箱验证码」同时含「邮箱」和「验证码」，验证码那格该配盾牌，
# 所以 `SHIELD` 这一类要排在「邮箱」前面。
FIELD_ICONS = (
    ("验证码", ft.Icons.SHIELD_OUTLINED),
    ("邮箱", ft.Icons.MAIL_OUTLINE),
    ("密码", ft.Icons.LOCK_OUTLINE),
)
# 压在那张背景图上的白纱（`#AARRGGBB`）：**很淡**，只够把照片的对比度收一收、让字稳下来。
# 头一版两端 85% / 中间 55% 白，压得太狠 —— 整页看着就是一片白，图等于白铺。现在
# 顶 60% / 中间 15% / 底 70%（底部那件小字链接需要一点底，所以比顶部更实一点）。
WASH_GRADIENT = ft.LinearGradient(
    colors=["#99FFFFFF", "#26FFFFFF", "#B3FFFFFF"],
    begin=ft.Alignment.TOP_LEFT,
    end=ft.Alignment.BOTTOM_RIGHT,
)

# 唯一的线色：卡片外围那一圈、以及每个输入框那一圈，都用它 —— 有玻璃底之后，
# 「范围」由它和更亮的那圈玻璃边一起说清楚。
CARD_BORDER = "#E2E8F0"
TITLE_COLOR = SUBPAGE_TITLE_COLOR
MUTED_COLOR = "#64748B"
FIELD_COLOR = "#334155"
HINT_COLOR = "#94A3B8"
PAGE_SIDE_PADDING = 24
# 卡片标题：摆在卡片**左上角**，字号比正文大出一截（15 → 22）—— 它是这一页要说
# 的头一件事，不该和下面 13pt 的字段挤在同一档。
TITLE_SIZE = 22
SUBTITLE_SIZE = 11
FIELD_TEXT_SIZE = 13
# 所有输入框都是这个高度：外层小框和里面的输入框同高（见 build_field_box），
# 一列字段等高，文字也落在格子正中。
FIELD_HEIGHT = 40
FIELD_RADIUS = 8
FIELD_SIDE_PADDING = 12
# 输入框内容（输入文字 + 提示文字）的上下内边距：**上大下小**。
#
# 格子前面那枚图标是 `build_field_box` 用 `CrossAxisAlignment.CENTER` 摆的，严格居中；
# 而文字那行是**顶部对齐**内容的 —— 13pt 的字，行盒比字形本身高，视觉重心天生偏上一点，
# 所以对称的上下内边距（11/11）会让文字看着比图标高出一截。这里上面多给 3、下面少给 3，
# 把它压到与图标同一条中线上。
# 想再挪：只改这两个数 —— **保持相加 22**（内容盒高度就与原来一致，行不会被压扁），
# 那么「上 − 下」每多 2，文字就往下 1px：13/9 = 往下 2px，14/8 = 往下 3px，12/10 = 往下 1px。
# 现在是 13/9（头一版给 14/8，偏下了一点）；`fit_parent_size` 保证可点区域仍是整格。
FIELD_TEXT_INSET_TOP = 13
FIELD_TEXT_INSET_BOTTOM = 9
# 密码框右边那枚「显示 / 隐藏」自带内边距，容器这侧不再另留（0）—— 那枚眼睛才会
# 贴到框的后端。想让整体再往左一点，把这个数往上调即可。
FIELD_TRAILING_INSET = 0
BUTTON_HEIGHT = 42
BUTTON_TEXT_SIZE = 14
# 卡片内元素的统一间距（字段之间、字段与主按钮之间、卡片之间）：比原先宽一档
# （12 → 14），字段挨得太挤时看不出一格是一格。
CARD_SPACING = 14
# 标题**额外**多出的那一截下间距：加在 `CARD_SPACING` 之上，所以标题到下面第一个
# 输入框是 `CARD_SPACING + HEADING_BOTTOM_GAP`（26）。字号放大到 22 之后，标题跟
# 字段用同一个间距会把两件事糊成一团，留出这一截才看得出它是块标题。
HEADING_BOTTOM_GAP = 12
# 字段下面那行小提示（登录页的「忘记密码？」）与字段之间的距离：**与 `CARD_SPACING`
# 同档** —— 上面挨着密码框、下面是主按钮，两处留白相等时这枚链接才在它们之间的空档
# 里**上下居中**。原先给 2（紧贴右下角）时明显偏上，看着像挂在密码框上的一行尾巴。
FIELD_HINT_GAP = CARD_SPACING
CARD_PADDING_X = 16
CARD_PADDING_Y = 14
CARD_RADIUS = 12
# 链接（卡片下面那行小字按钮）左右各留一点，点起来更好按；登录页的「忘记密码？」
# 要跟密码框右边缘对齐，所以那一行传 0。
LINK_SIDE_PADDING = 6
# 表单区离顶栏的距离：按**窗口高度**的比例取（`page.height` 在页面构建时就有了），
# 不是按「剩余可用高度」分配。键盘升起时视口会被压矮，用后者算出来的位置会跟着往上
# 跑 —— 那就是「弹键盘整页往上挤」。这里定成固定像素，构建完就不再变。
# 比例给得比较小（约等于从顶部 13% 处起），表单整体落在中上偏上的位置。
FORM_TOP_RATIO = 0.13
FORM_TOP_MIN = 96.0
# 「不跟表单走」那件（登录页的「还没有账号？去注册」）的位置：**从内容区的顶边往下量**
# （`top`），而不是从底边往上量（`bottom`）。
#
# ⚠️ 别改成 `bottom`：那一行原本拿来做参照的是「按整屏高排版的那一屏」（见
# `build_auth_page`），而它的底边伸在**可见区之外** —— 顶部状态栏、24 的内边距已经把
# 真正看得见的那块往里缩了一截，iOS 底部那条小横条再吃掉一点。于是用 `bottom` 时这个
# 距离必须大于被吃掉的那一截才看得见：给 0.12H（iPhone 上约 101px）时它正好卡在可见
# 边界上、看着偏低，收到 0.08H（约 67px）就整行被裁掉 —— 一个字都不剩。从顶边往下量
# 没有这个坑：顶边是稳的，量出来的位置和设备底部那一圈 inset 无关。
# 0.74 ≈ 落在页面的下 1/4；表单占到大约 `0.13H + 260px`，小屏上也不会跟它撞上。
FOOTER_TOP_RATIO = 0.74
# 量不到屏高（`page.height` 为 0）时的兜底：这一档是从顶边往下量，给小一点没关系。
FOOTER_TOP_MIN = 300.0
# 「获取验证码」那枚小按钮的三种文案：初始 → 倒计时中（`{n}` 是剩余秒数）→ 可重发。
CODE_SEND_LABEL = "获取验证码"
CODE_RESEND_LABEL = "重新发送"
# 刻意和「获取验证码」差不多长（都是 5-6 个字），倒计时开始 / 结束时按钮不会跳宽。
CODE_COUNTDOWN_LABEL = "{n}s 后重发"
# 倒计时的默认秒数：send-code 的返回里带了 `resend_after` 就用后端的，没带才用它。
CODE_COUNTDOWN_SECONDS = 60
# 「获取验证码」那枚按钮的形态：底取主按钮同一档蓝（`DATE_SELECTED_BG`），字用深蓝，
# 和左边输入框**同高**并排 —— 它是个「能点的动作」，不该像其它小字链接那样只剩一行灰字。
CODE_BUTTON_BG = DATE_SELECTED_BG
CODE_BUTTON_TEXT = TITLE_COLOR
CODE_BUTTON_HEIGHT = FIELD_HEIGHT
# 字比其它小字链接（11pt）大一档，和输入框里的 13pt 同档 —— 它跟输入框**同高并排**，
# 字号也一致才像一对。倒计时期间只换字色、不换字号。
CODE_BUTTON_TEXT_SIZE = 13
CODE_BUTTON_SIDE_PADDING = 12
# 与左边输入框之间的距离：给了底色之后不能贴在一起，会糊成一块。
CODE_BUTTON_GAP = 8
# 这枚按钮只有**两种配色**（互切的过渡是 `CODE_BUTTON_ANIMATION`）：
#   ① 可以点（默认）    蓝底深蓝字 —— **按下去的那一段也用这副配色**
#   ② 冷却中·倒计时      灰底浅字，一眼看出这会儿点不了
# 按下 / 请求在飞这段时间**只缩一点点**（`CODE_BUTTON_PRESSED_SCALE`）、不换配色：颜色变了
# 容易被误读成「已经发出去了」，而它表达的其实是「手指按住了」。文案在这段也「故意一个
# 字都不改」（理由见 `lock_code_button`），所以这段唯一的反馈就是那一下缩放。
CODE_BUTTON_PRESSED_SCALE = 0.96
CODE_BUTTON_COOLDOWN_BG = CARD_BORDER
CODE_BUTTON_COOLDOWN_TEXT = MUTED_COLOR
CODE_BUTTON_ANIMATION = ft.Animation(120, ft.AnimationCurve.EASE_OUT)


def icon_for(hint: str) -> str | None:
    """按字段文案认一枚图标（见 `FIELD_ICONS`）；认不出来返回 `None`（那就不放图标）。"""
    for keyword, icon in FIELD_ICONS:
        if keyword in hint:
            return icon
    return None


def build_auth_field(
    hint: str, password: bool = False, icon: str | None = None
) -> ft.TextField:
    """一个表单字段：和设置页「推送地址」同一个写法（无边框、单行、13pt）。

    密码那格用 `password=True`，右边的「显示 / 隐藏」交给 `can_reveal_password`
    —— Material 自己那枚眼睛，不用另画一个。

    `icon` 是**框前面**那枚小图标（`ft.Icons.*`）：不传就按 `hint` 自己认（邮箱 /
    密码 / 验证码），认不出来就不放。它不挂在 `ft.TextField` 自带的 `prefix_icon` 上
    —— 那个在各平台尺寸不一致，这儿的框是手画的，图标由 `build_field_box` 摆进去，
    位置与间距才可控。认出来的结果记在 `field.data` 上（Flet 控件的自由字段）。

    高度直接钉在输入框上（和设置页通知地址那一格一个做法），并显式要求**文字垂直
    居中**：Flet 的 `text_vertical_align` 默认是 `None`（等同顶部对齐），只钉高度、
    不写这一项的话文字仍然贴在上边 —— 这是真的踩过一次。
    """
    field = ft.TextField(
        hint_text=hint,
        hint_style=ft.TextStyle(size=FIELD_TEXT_SIZE, color=HINT_COLOR),
        password=password,
        can_reveal_password=password,
        # 这几页都是单行字段：不给它长高的余地（`multiline` 默认就是 False，
        # 写出来是防以后被改成 True）。
        multiline=False,
        height=FIELD_HEIGHT,
        text_vertical_align=ft.VerticalAlignment.CENTER,
        # 可编辑区填满这一格的高度：不然内容只占中间一条，点框的上下边缘会点不中
        # 输入框（点上去没反应）。填满后整格都是可点区，文字仍按 `text_vertical_align`
        # 摆在正中。
        fit_parent_size=True,
        filled=False,
        border=ft.NoInputBorder(),
        # 上下内边距见 FIELD_TEXT_INSET_TOP / _BOTTOM：这个框是顶部对齐内容的，靠它把
        # 那一行压到与前面那枚图标同一条中线上（上大下小 → 文字往下挪一点）。
        content_padding=ft.Padding.only(
            left=0,
            right=0,
            top=FIELD_TEXT_INSET_TOP,
            bottom=FIELD_TEXT_INSET_BOTTOM,
        ),
        text_style=ft.TextStyle(size=FIELD_TEXT_SIZE, color=FIELD_COLOR),
        dense=True,
    )
    field.data = icon if icon is not None else icon_for(hint)
    return field


def build_field_box(field: ft.TextField) -> ft.Control:
    """把无边框的输入框套进一格「第二层玻璃」里，高度统一取 `FIELD_HEIGHT`。

    带图标时（`build_auth_field` 认出来的）摆成「图标 + 输入框」一行：那枚图标是灰的、
    不接点击；输入框 `expand=True` 吃掉剩下的宽度，所以**有没有图标，右边缘都一样齐**，
    密码框那枚「显示 / 隐藏」也不会被挤动。

    密码框右边那枚「显示 / 隐藏」是控件自带的 suffix，右侧内边距收窄到
    `FIELD_TRAILING_INSET`，让它贴住框的后端；其余字段左右一样宽，文字看着才对称。
    """
    icon = getattr(field, "data", None)
    if icon:
        field.expand = True
        content: ft.Control = ft.Row(
            spacing=FIELD_ICON_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=FIELD_ICON_SIZE, color=MUTED_COLOR),
                field,
            ],
        )
    else:
        content = field
    trailing = bool(getattr(field, "password", False)) or bool(
        getattr(field, "can_reveal_password", False)
    )
    return ft.Container(
        height=FIELD_HEIGHT,
        # 带图标时左侧收窄：那枚图标自己占掉一点，「图标 + 文字」才看着居中。
        padding=ft.Padding.only(
            left=FIELD_LEADING_INSET if icon else FIELD_SIDE_PADDING,
            right=FIELD_TRAILING_INSET if trailing else FIELD_SIDE_PADDING,
        ),
        border_radius=ft.BorderRadius.all(FIELD_RADIUS),
        # 第二层玻璃：比卡片更透一点，再压一圈浅灰细边示意范围。
        bgcolor=FIELD_GLASS_BG,
        border=ft.Border.all(1, CARD_BORDER),
        # 和卡片同理：不裁的话 blur 会按矩形铺出来。
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=content,
    )


def build_code_row(
    field: ft.TextField,
    on_send: Callable[[ft.Event[ft.Control]], None],
) -> tuple[ft.Control, ft.Control]:
    """验证码那一行：输入框占满剩余宽度，右边跟上「获取验证码」。

    返回 `(整行, 那枚按钮)` —— 按钮要留个引用，倒计时由 `start_code_countdown` 跑。
    注册页（邮箱验证码）和忘记密码页都用这一行，样式与行为保持一致。

    这枚按钮是 `Container` 画的（不是 Button），没有真的「不可点」状态：拿了
    `button.data` 当锁（上锁见 `lock_code_button`），锁着的时候点了直接不理 ——
    配色只有两套（可以点 / 冷却中，见 `CODE_BUTTON_*` 常量），按时序由
    `lock_code_button` / `release_code_button` / `start_code_countdown` 切换，灰的那套
    只在倒计时期间出现；按下到响应回来那一段只把按钮缩一点点（`CODE_BUTTON_PRESSED_SCALE`）、
    配色不动。文案也**故意不动**，等响应回来才跟着一起变。
    """

    def guarded(event: ft.Event[ft.Control]) -> None:
        if button.data:
            return
        on_send(event)

    button = ft.Container(
        height=CODE_BUTTON_HEIGHT,
        alignment=ft.Alignment.CENTER,
        border_radius=ft.BorderRadius.all(FIELD_RADIUS),
        # 有底色：它是个「能点的动作」，不像其它小字链接那样只剩一行灰字。
        bgcolor=CODE_BUTTON_BG,
        padding=ft.Padding.symmetric(horizontal=CODE_BUTTON_SIDE_PADDING),
        ink=True,
        on_click=guarded,
        # 「按下去」那一下是缩一点点：给了 `animate_scale` 才有缓动，硬切看着像闪。
        # 样子怎么切（配色 + 缩放）统一交给 `_paint_code_button`。
        scale=1.0,
        animate_scale=CODE_BUTTON_ANIMATION,
        # 文案与字色都要能就地改（倒计时每秒换一次），所以留在 `button.content` 上
        # —— `_set_code_label` 直接写它的 `value` / `color`。
        content=ft.Text(
            CODE_SEND_LABEL, size=CODE_BUTTON_TEXT_SIZE, color=CODE_BUTTON_TEXT
        ),
    )
    button.data = False  # False = 没在倒计时，可以点
    row = ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        # 有底色之后不能和输入框贴在一起，会糊成一块。
        spacing=CODE_BUTTON_GAP,
        controls=[
            ft.Container(expand=True, content=build_field_box(field)),
            button,
        ],
    )
    return row, button


def _paint_code_button(
    button: ft.Control, *, bgcolor: str, color: str, scale: float
) -> None:
    """给按钮换底色 / 字色 / 缩放 —— 三样一起改，它们是同一个「样子」的三面。

    分开改要多推几次界面，还可能中间那一瞬三者错位（底色已经灰了、字还是深蓝）。控件
    不在树上时 `update()` 抛 RuntimeError —— 页面还在时不会，用户退回
    上一页才会，这时当作「页面没了」收手就行（和 tools/layout.py 的
    anchor_dialog_above_keyboard 一个处理）。
    """
    button.bgcolor = bgcolor
    button.scale = scale
    button.content.color = color
    try:
        button.update()
    except RuntimeError:
        pass


def _set_code_label(button: ft.Control, label: str, color: str) -> bool:
    """给按钮换文案 / 换字色并推给客户端；控件已经不在树上时返回 False。

    冷却期的字色由调用方给（`CODE_BUTTON_COOLDOWN_TEXT`）—— 那时候按钮整体是灰的，
    和「可以点」那档深蓝分开。控件被卸下之后
    `update()` 会抛 RuntimeError —— 页面还在时不会，用户退回上一页才会，这时当成
    「页面没了」收手就行（和 tools/layout.py 的 anchor_dialog_above_keyboard
    一个处理）。
    """
    button.content.value = label
    button.content.color = color
    try:
        button.update()
    except RuntimeError:
        return False
    return True


async def _countdown_code(button: ft.Control, seconds: int) -> None:
    """倒计时本体：写下剩余秒数 → 睡一秒 → 减一，归零后恢复成「重新发送」。

    倒计时期间整枚按钮是灰的（见 `start_code_countdown`），字色跟着浅一档 —— 这么浅的
    灰压在蓝底上几乎看不见（对比度不到 2:1），压在灰底上才读得清。
    """
    for remaining in range(seconds, 0, -1):
        if not _set_code_label(
            button,
            CODE_COUNTDOWN_LABEL.format(n=remaining),
            CODE_BUTTON_COOLDOWN_TEXT,
        ):
            button.data = False
            return
        await asyncio.sleep(1)
    # 归零 → 弹回「可以点」那副样子（文案 + 底色 + 缩放一起换）。
    _paint_code_button(
        button, bgcolor=CODE_BUTTON_BG, color=CODE_BUTTON_TEXT, scale=1.0
    )
    _set_code_label(button, CODE_RESEND_LABEL, CODE_BUTTON_TEXT)
    button.data = False


def lock_code_button(button: ft.Control) -> None:
    """点下「获取验证码」的**那一刻**先上锁 —— 必须在请求发出之前，但**只置锁、不动文案**。

    send-code 要走网络，等响应回来才上锁的话，这几百毫秒里连点几下就会发出几次请求
    （每点一次都得等一次响应，看着像没点上）。

    所以上锁只写 `button.data`，文案**留给响应回来之后**再定：发成了由
    `start_code_countdown` 改成「Ns 后重发」，没发成由 `release_code_button` 写回
    「获取验证码」。请求还在路上就把字改掉的话，一旦后端报错还得再改回来 —— 文案先跳
    一下、再跳回去，看着像闪屏，而且给人「已经发出去了」的错觉。

    文案不动不代表没反馈：紧接着那句 `_paint_code_button` 让按钮缩一点点，像被手指按住
    —— **只动缩放，配色不动**（一直是「可以点」那副蓝）：这会儿还没发成，换深色会被读成
    「已经发出去了」。响应回来才决定下一步的样子。
    """
    button.data = True
    _paint_code_button(
        button,
        bgcolor=CODE_BUTTON_BG,
        color=CODE_BUTTON_TEXT,
        scale=CODE_BUTTON_PRESSED_SCALE,
    )


def release_code_button(button: ft.Control) -> None:
    """没发成（本地校验没过 / 后端报错）时解锁：按钮弹回「可以点」那副样子，能再试一次。"""
    button.data = False
    _paint_code_button(
        button,
        bgcolor=CODE_BUTTON_BG,
        color=CODE_BUTTON_TEXT,
        scale=1.0,
    )
    _set_code_label(button, CODE_SEND_LABEL, CODE_BUTTON_TEXT)


def start_code_countdown(
    page: ft.Page, button: ft.Control, result: dict | None = None
) -> None:
    """点过「获取验证码」之后：按钮锁一段、每秒把剩余秒数写上去，归零才恢复可点。

    `result` 是 send-code 的返回：带了 `resend_after`（后端要求的下次可发间隔）就按
    它倒计时，没带才用默认的 `CODE_COUNTDOWN_SECONDS` —— 两边规矩一致，不会出现
    "界面说能点了、后端还在冷却"。

    锁记在 `button.data` 上（点击时由 `build_code_row` 里那层守卫读它）。倒计时用
    `page.run_task` + `asyncio.sleep(1)` 跑 —— Flet 里跑后台循环的标准做法（设置页
    的「检查新版本」也是这么发的），不会卡住 UI。
    """
    seconds = CODE_COUNTDOWN_SECONDS
    if isinstance(result, dict):
        raw = result.get("resend_after")
        if isinstance(raw, int) and raw > 0:
            seconds = raw
    button.data = True
    # 发成功了 → 从「被按住」换成「冷却中」：灰底浅字，倒计时期间一直是这副样子，
    # 归零才 `_countdown_code` 把它弹回「可以点」。
    _paint_code_button(
        button,
        bgcolor=CODE_BUTTON_COOLDOWN_BG,
        color=CODE_BUTTON_COOLDOWN_TEXT,
        scale=1.0,
    )
    page.run_task(_countdown_code, button, seconds)


def code_sent_message(result: dict | None) -> str:
    """把 send-code 的返回翻成一句提示。

    - 返回里带 `debug_code`（后端开了 `EMAIL_CODE_DEBUG_RETURN`）：直接念出来，联调
      时不用去翻服务端日志；
    - `sent=false`：后端没配 SMTP，信没真发出去 —— 说清楚，免得人一直等邮件；
    - 其余：正常提示去查收。
    """
    data = result if isinstance(result, dict) else {}
    code = data.get("debug_code")
    if code:
        return f"验证码已发送（调试验证码：{code}）"
    if data.get("sent") is False:
        return "验证码已生成，但后端未配置邮件，请查看服务端日志"
    return "验证码已发送，请查收邮箱"


def build_primary_button(
    label: str, on_click: Callable[[ft.Event[ft.Control]], None]
) -> ft.Control:
    """整宽的主按钮（登录 / 注册 / 重置密码）。

    全 App 都平（菜单、弹窗按钮都不留阴影和涟漪），主按钮也照办：`elevation=0`、
    阴影和 overlay 全透明。
    """
    return ft.FilledButton(
        label,
        height=BUTTON_HEIGHT,
        style=ft.ButtonStyle(
            bgcolor=DATE_SELECTED_BG,
            color=TITLE_COLOR,
            elevation=0,
            shadow_color="#00000000",
            overlay_color="#00000000",
            shape=ft.RoundedRectangleBorder(radius=FIELD_RADIUS),
            text_style=ft.TextStyle(
                size=BUTTON_TEXT_SIZE, weight=ft.FontWeight.BOLD
            ),
        ),
        on_click=on_click,
    )


def build_card_heading(title: str, hint: str | None = None) -> ft.Control:
    """卡片顶部的标题区：标题 + 可选的一行小字说明，**贴在卡片左上角**。

    三页都不再摆头像：原来登录页顶上那枚 `ft.Icons.PERSON` 圆头像已经去掉，标题自己
    说明这一页是干什么的就够了。
    """
    lines = [
        ft.Text(
            title,
            size=TITLE_SIZE,
            weight=ft.FontWeight.BOLD,
            color=TITLE_COLOR,
            text_align=ft.TextAlign.START,
        )
    ]
    if hint:
        lines.append(
            ft.Text(
                hint,
                size=SUBTITLE_SIZE,
                color=MUTED_COLOR,
                text_align=ft.TextAlign.START,
            )
        )
    return ft.Container(
        # 标题与下面第一个输入框拉开一截：`HEADING_BOTTOM_GAP` 是**额外**加的，卡片
        # 自己的 `CARD_SPACING` 照旧排在它下面，两者相加才是标题到输入框的距离。
        padding=ft.Padding.only(bottom=HEADING_BOTTOM_GAP),
        content=ft.Column(
            tight=True,
            spacing=2,
            # 靠左摆：标题是这一页的第一句话，贴着卡片左上角比居中更明朗，也和下面
            # 左对齐的字段同一条起笔线。
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=lines,
        ),
    )


def build_auth_card(controls: list[ft.Control]) -> ft.Control:
    """装这些字段的那张卡片：**一块毛玻璃**。

    半透明白底 + 背后模糊 + 一圈更亮的细边；圆角要 `clip_behavior` 一起裁 —— `blur`
    是按控件那块矩形铺的，不裁的话四角会漏出方糊斑。背后那两团淡色块由
    `build_auth_page` 垫在下面：没有它们，玻璃底下就是一片平渐变，磨砂感看不出来。

    留着这个 `Container` 的另一件事是给内容定宽度（左右 `CARD_PADDING_X`）与上下留白
    （`CARD_PADDING_Y`）；字段与按钮之间不插分隔线，留白由 `CARD_SPACING` 负责。
    """
    return ft.Container(
        padding=ft.Padding.symmetric(
            horizontal=CARD_PADDING_X, vertical=CARD_PADDING_Y
        ),
        border_radius=ft.BorderRadius.all(CARD_RADIUS),
        bgcolor=GLASS_BG,
        blur=GLASS_BLUR,
        border=ft.Border.all(1, GLASS_BORDER),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            tight=True,
            spacing=CARD_SPACING,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=controls,
        ),
    )


def build_link(
    label: str,
    on_click: Callable[[ft.Event[ft.Control]], None],
    side_padding: int = LINK_SIDE_PADDING,
) -> ft.Control:
    """一行里的小字按钮（点了就走，样式跟正文区分开）。

    `side_padding` 是它的左右内边距：默认 `LINK_SIDE_PADDING`（点起来更好按）；
    传 0 时文字边缘就与所在那一行的边缘齐平 —— 登录页的「忘记密码？」要跟密码框的
    右边缘对齐，走的正是这条。
    """
    return ft.Container(
        ink=True,
        border_radius=ft.BorderRadius.all(6),
        padding=ft.Padding.symmetric(horizontal=side_padding, vertical=2),
        on_click=on_click,
        content=ft.Text(
            label,
            size=SUBTITLE_SIZE,
            # 加粗：这几枚是「换一页」的入口（去注册 / 去登录 / 忘记密码），和正文同号
            # 的细字会被当成说明文字，看不出它们能点。
            weight=ft.FontWeight.BOLD,
            color=MUTED_COLOR,
        ),
    )


def build_link_row(
    items: list[tuple[str, Callable[[ft.Event[ft.Control]], None]]],
    alignment: ft.MainAxisAlignment = ft.MainAxisAlignment.CENTER,
    side_padding: int = LINK_SIDE_PADDING,
) -> ft.Control:
    """一行小字链接：`[(文案, 回调), ...]`，之间自动插一个中点分隔。

    默认整行居中（注册页 / 忘记密码页卡片下面那行、登录页 footer 那件都用它）；
    登录页的「忘记密码？」要贴到密码框外的右下角并与密码框右边缘对齐，所以留了
    `alignment`（传 `ft.MainAxisAlignment.END`）与 `side_padding`（传 0）。
    """
    controls: list[ft.Control] = []
    for index, (label, on_click) in enumerate(items):
        if index:
            controls.append(ft.Text("·", size=SUBTITLE_SIZE, color=HINT_COLOR))
        controls.append(build_link(label, on_click, side_padding))
    return ft.Row(alignment=alignment, controls=controls)


def build_auth_page(
    page: ft.Page,
    go_back: Callable[[], None],
    controls: list[ft.Control],
    footer: ft.Control | None = None,
) -> ft.Control:
    """三页共用的页面壳：整页背景图 + 一层白纱 + SafeArea + 左右 24 的边距。

    **顶栏只留返回按钮**：标题不摆在这儿了 —— 它已经在卡片上，而且三页的卡片标题与页面
    一一对应（登录 / 注册 / 重置密码），顶栏再来一行是重复。给
    `build_subpage_header` 传 `None` 就是这条形态。

    版式用 `Stack` 摆两块，都横跨整行：顶栏钉在顶上（`top=0`），表单从 `form_top`
    往下摆 —— `form_top` 是**按窗口高度算出的固定像素**（见 `FORM_TOP_RATIO`），
    不是弹性留白。这样键盘升起、视口被压矮时，表单的绝对位置一点不变，也就不会
    「整页往上挤」；Stack 默认裁掉超出部分，所以真要放不下也只是下半截被裁掉，
    不会挤出布局报错。

    `footer` 是**不跟表单走**的那一件（登录页的「还没有账号？去注册」）：单独钉在从顶边
    往下 `FOOTER_TOP_RATIO` 处（为什么不用「离底边多远」见那两个常量的注释），左右横跨
    整行、内容自己居中。它是一个**绝对像素的 `top`**，所以键盘弹起也不会被顶上去（超出
    视口的部分由 Stack 裁掉，松键盘即回原位）。

    需要 `page` 只是为了取 `page.height`（构建这一页时键盘还没升起，拿到的是整屏
    高度）。
    """
    height = page.height or 0
    form_top = max(FORM_TOP_MIN, height * FORM_TOP_RATIO)
    layers: list[ft.Control] = [
        ft.Container(
            left=0,
            right=0,
            top=0,
            content=build_subpage_header(None, go_back),
        ),
        # `tight=True`：这一块只有内容那么高，`top` 才是它的上边距，
        # 不会自己长到整屏。
        ft.Container(
            left=0,
            right=0,
            top=form_top,
            content=ft.Column(
                tight=True,
                spacing=CARD_SPACING,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=controls,
            ),
        ),
    ]
    if footer is not None:
        # ⚠️ 必须放在**最底下**（插到列表开头）：这一层铺满整屏，一旦压在表单上面就会把
        # 整张卡片盖住 —— 输入框点不中、卡片里的链接也点不动（真机上翻过这个车）。
        # 压在下面时：footer 那一带只有它，照样点得到；卡片那一带由上面的表单层接管。
        layers.insert(
            0,
            # 位置给的是**绝对像素的 `top`**（取值见 `FOOTER_TOP_RATIO`）：Stack 里的
            # `top` 从顶边往下数是固定的，键盘弹起、视口被压矮时它不会跟着往上跑 ——
            # 和表单那块同一个办法，所以外面不必再裹一层「钉成整屏高」的容器。
            ft.Container(
                left=0,
                right=0,
                top=max(FOOTER_TOP_MIN, height * FOOTER_TOP_RATIO),
                # 容器横跨整行，内容自己居中（footer 那一行只有内容那么宽）。
                alignment=ft.Alignment.CENTER,
                content=footer,
            )
        )
    return ft.Container(
        # 底色垫在最底下：图片还没加载出来、或 `COVER` 裁剩的边角，露出来的是这层很浅的
        # 靛蓝（`PAGE_BGCOLOR`），不会闪白。
        expand=True,
        bgcolor=PAGE_BGCOLOR,
        content=ft.Stack(
            expand=True,
            controls=[
                # ① 背景图：铺满**整个页面**，而且在 `SafeArea` **外面** —— 手机状态栏
                #    那一条也是这张图。头一版把它放进了 SafeArea（图在里、安全区在外），
                #    顶部那一条露的是底色，看着就像没铺满。
                ft.Container(
                    expand=True,
                    image=ft.DecorationImage(
                        src=AUTH_BACKGROUND_SRC, fit=ft.BoxFit.COVER
                    ),
                ),
                # ② 白纱：把照片压淡一档，卡片与输入框上的字才稳（见 WASH_GRADIENT）。
                ft.Container(expand=True, gradient=WASH_GRADIENT),
                # ③ 内容：**只有这一层进 SafeArea**（避开状态栏 / 刘海），左右 24 的边距，
                #    里面还是原来那两件：顶栏 + 表单（以及登录页的 footer）。
                ft.Container(
                    expand=True,
                    content=ft.SafeArea(
                        expand=True,
                        content=ft.Container(
                            expand=True,
                            padding=ft.Padding.only(
                                left=PAGE_SIDE_PADDING,
                                top=PAGE_SIDE_PADDING,
                                right=PAGE_SIDE_PADDING,
                            ),
                            content=ft.Stack(expand=True, controls=layers),
                        ),
                    ),
                ),
            ],
        ),
    )
