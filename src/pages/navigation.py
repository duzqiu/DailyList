from collections.abc import Callable

import flet as ft

from pages.background import build_background_page
from pages.messages import build_messages_page
from pages.my import build_my_page
# 占位页要页面渐变 + 底栏那一段留白。
from widgets.layout import safe_update
from widgets.toast import build_toast
from pages.countdown import build_countdown_page
from pages.edit_birthday import build_edit_birthday_page
from pages.edit_gender import build_edit_gender_page
from pages.edit_intro import build_edit_intro_page
from pages.edit_name import build_edit_name_page
from pages.edit_profile import build_edit_profile_page
from pages.forgot_password import build_forgot_password_page
from pages.feed import build_feed_page
from pages.login import build_login_page
from pages.preferences import build_preferences_page
from pages.register import build_register_page
from widgets.layout import (
    MENU_BAR_BOTTOM,
    MENU_BAR_HEIGHT,
    MENU_LABEL_SIZE,
    PAGE_BGCOLOR,
)
from widgets.swipe_back import build_swipe_back

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

# 一级页（底栏那几格）切换的过渡：用 flet 自带的 **`ft.AnimatedSwitcher`** —— 服务端只要
# 换一次 `content`，**客户端**自己就会让旧页淡出、新页淡入（真正的交叉淡入淡出），不用在
# 服务端排「先淡出、再换、再淡入」那两拍。
#
# ⚠️ 别再拿 `animate_opacity` / `animate_offset`（隐式动画）做这件事：真机上走了两轮，
# 这两种写法都**看不到任何过渡**（客户端里那两处分支是有的，实测不生效），而
# `AnimatedSwitcher` 是客户端驱动的，稳。
# ⚠️ 二级 / 三级页也不用这套：它们是压在 `page.views` 上的真 View，走上面的
# `PAGE_TRANSITION`（系统那档横向推拉），自己再画一层反而会叠。
PAGE_SWITCH_MS = 220
# 每一页一个**不同的 key**：AnimatedSwitcher 靠 key 判断「这是不是另一个控件」——
# key 相同只当普通刷新（不播动画），正好对上「同一格重复点 = 刷新」那条。
PAGE_KEYS: dict[int, str] = {
    0: "tab-feed",
    1: "tab-countdown",
    3: "tab-messages",
    4: "tab-my",
}


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
    # 一级页的容器：**AnimatedSwitcher 负责过渡** —— 换 `content` 时旧页淡出、新页淡入。
    # 初始给一个空占位：真身在第一帧之前就换上（见文件末尾的 `show_page(0, update=False)`，
    # 那一步发生在 `page.add()` 之前），所以首屏不会先闪一下再切。
    holder = ft.AnimatedSwitcher(
        content=ft.Container(),
        duration=PAGE_SWITCH_MS,
        reverse_duration=PAGE_SWITCH_MS,
        transition=ft.AnimatedSwitcherTransition.FADE,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
        expand=True,
    )
    selected_index = 0

    # 各页的「选择状态」，按页面名保管。切页时页面控件是重建的（数据要现从库里
    # 读），但「选了哪一档」这类选择不该跟着回到默认值：切走再切回来还停在原处，
    # 只有热重载重新跑 main() 才回到初始值。
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

        第 0 层是一级页的外壳（`holder` + 底部菜单），由 `show_page` 直接画在
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
    # 底栏那 4 个文字项的引用：(index, Text)。项只建一次、之后只改它们的状态 ——
    # 挂着 `animate_scale` 才插得出「选中放大」那段动画（见 `refresh_menu_items`）。
    menu_label_texts: list[tuple[int, ft.Text]] = []

    # 底栏配色：白底、**不描边**；项只有文字，中间那颗红「+」是小红书最显眼的一笔。
    MENU_BAR_BG = "#FFFFFF"
    MENU_LABEL_IDLE = "#9CA3AF"
    MENU_LABEL_SELECTED = "#111827"
    # 选中的那一项**放大**：字号不变、靠 `scale` + 动画（切页时它是「弹大」的，
    # 不是直接蹦成大字 —— 所以项只建一次、之后改它，见 `refresh_menu_items`）。
    # 幅度收过一档：1.18 太跳，1.08 只是「比旁边大一点点」。
    MENU_LABEL_ZOOM = 1.08
    MENU_LABEL_ZOOM_MS = 160
    MENU_PLUS_BG = "#FF2442"
    # 那颗「+」是**扁的**：宽比高长，圆角比「高的一半」小一档 —— 是一枚圆角扁块，
    # 不是完整的椭圆。
    MENU_PLUS_WIDTH = 56
    MENU_PLUS_HEIGHT = 34
    MENU_PLUS_RADIUS = 10
    # 底栏某一格右上角那枚未读徽标的底色（「消息」那格是 99+）。
    MENU_BADGE_BG = "#FF2442"
    # 底栏内**底边**留的白：内容因此整体上移一点；这段空白用的就是底栏自己的白底，
    # 和菜单一个颜色，不会在下面露出一条别的颜色的边。
    MENU_BAR_BOTTOM_SPACE = 20

    menu_bottom = MENU_BAR_BOTTOM
    # 底栏参照小红书那一版：**通栏平底、贴着屏幕底**（不再是浮在中间的一枚圆角毛玻璃
    # 丸，顶上也不描那条细灰线）。项本身只有文字，中间那颗红「+」见 `menu_plus`。
    menu_bar = ft.Container(
        left=0,
        right=0,
        bottom=menu_bottom,
        height=MENU_BAR_HEIGHT,
        padding=ft.Padding.only(
            left=6, right=6, top=2, bottom=MENU_BAR_BOTTOM_SPACE
        ),
        bgcolor=MENU_BAR_BG,
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
        # 先把目标页建出来（建的时候不碰界面），换上去的时机交给下面的过渡。
        control = (
            # 一级页 0：发现流（原来这一格是「待办」页，那一页已按用户要求删掉，
            # 见 pages/feed.py）。
            build_feed_page(page)
            if index == 0
            else             build_countdown_page(page, set_menu_visible)
            if index == 1
            else build_messages_page(page)
            if index == 3
            else build_my_page(
                page,
                set_menu_visible,
                page_state("my"),
                # 设置页照旧是**压在之上的一层**（`show_preferences`，二级页、收起底栏）；
                # 入口只剩「我的」页左上角那枚 ≡（右上角那枚齿轮已去掉）。
                show_preferences,
                # ⚠️ 原来的「数据」入口（顶栏那枚柱状图图标）连同数据页**已按用户要求整体删掉**
                # （只服务它的图表控件也没了），所以这儿不再传 `show_data`。
                # 「账号」卡片里点「登录」/「管理」→ 登录页压在**这个 Tab 之上**（第 1
                # 层），返回回到这个 Tab。
                show_login_from_settings,
                # 内容板上那个红色胶囊「去发布」：和底栏那颗「+」走同一个回调 ——
                # 两处目前都没接功能，点了给一句提示（见 `notify_unavailable`）。
                notify_unavailable,
                # 背景区里点空白处 → 换背景图那一页。
                show_background,
                # 顶栏那枚胶囊「编辑主页」→「编辑资料」页（复刻小红书那一版）。
                show_edit_profile,
            )
        )
        # 每页一个固定的 key：**AnimatedSwitcher 靠它认出「换的是另一个控件」才播过渡**；
        # 同一格再来（从二级页退回来 / 重复点）key 不变 → 只当普通刷新，不白播一次。
        control.key = PAGE_KEYS.get(index, f"tab-{index}")
        holder.content = control
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = True
        build_menu_items()
        if update:
            page.update()

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
                # 「账号」卡片里点「登录」/「管理」→ 登录页压在设置页之上（第 2 层）。
                open_login=show_login_from_settings,
            ),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_background(update: bool = True) -> None:
        """「我的」页背景区点空白处进来：**换背景图**那一页（二级页，收起底栏）。

        左上角的 ✕ / 返回回到进来时那个 Tab；选好图后那一页会叫 `on_saved`，这里顺手把
        「我的」重画一遍（`show_page` 会把上面这层也撤掉），新背景就铺上了。
        """
        origin = selected_index
        nav_stack.append(lambda: show_page(origin))
        show_layer(
            1,
            "/background",
            lambda: build_background_page(
                page,
                go_back=go_back,
                on_saved=lambda: show_page(origin),
            ),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def render_edit_profile(update: bool = True) -> None:
        """只重画「编辑资料」页那**一层**，不动页面栈（同上）。"""
        show_layer(
            1,
            "/edit-profile",
            lambda: build_edit_profile_page(
                page,
                go_back=go_back,
                # 「背景图」那一行 → 换背景图页压在**这一页之上**（第 2 层）。
                open_background=show_background_from_editor,
                # 「名字 / 简介 / 生日 / 性别」四行 → 各自一整页，同样压在这一页之上（第 2 层）。
                open_name=show_name_from_editor,
                open_intro=show_intro_from_editor,
                open_birthday=show_birthday_from_editor,
                open_gender=show_gender_from_editor,
            ),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_edit_profile(update: bool = True) -> None:
        """「我的」页顶栏「编辑主页」进来：**编辑资料**页（二级页，收起底栏）。

        返回回到进来时那个 Tab；改完资料退回去时「我的」页会重画一遍（名字 / 头像跟着变
        —— 资料读的是后端 `GET /member/profile`，见 tools/my_profile.py）。
        """
        origin = selected_index
        nav_stack.append(lambda: show_page(origin))
        render_edit_profile(update)

    def show_background_from_editor(update: bool = True) -> None:
        """编辑资料页里点「背景图」→ 换背景图页（第 2 层）。

        和「我的」页直接进不一样：这一层**压在编辑资料页之上**，所以父层动作是
        `render_edit_profile`（退回编辑资料页、缩略图跟着换成新图），不是 `show_page`。
        """
        nav_stack.append(lambda: render_edit_profile())
        show_layer(
            2,
            "/background",
            lambda: build_background_page(
                page,
                go_back=go_back,
                # 选完图直接退回编辑资料页（`go_back` 弹掉这一层 + 重画编辑资料页）。
                on_saved=go_back,
            ),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_field_page(
        route: str, build: Callable[[], ft.Control], update: bool = True
    ) -> None:
        """编辑资料页里点「简介 / 生日 / 性别」→ 各自那一页（第 2 层）。

        和「换背景图」从编辑资料页进来那条是同一个套路：压在编辑资料页**之上**，
        所以父层动作是 `render_edit_profile` —— 在那一页保存成功后 `go_back`，弹掉这
        一层的同时把编辑资料页重画一遍，行上的值（简介 / 生日 / 性别）就跟着变了。
        """
        nav_stack.append(lambda: render_edit_profile())
        show_layer(2, route, build)
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_name_from_editor(update: bool = True) -> None:
        """编辑资料页点「名字」→ 编辑名字页（第 2 层）。"""
        show_field_page(
            "/edit-name",
            lambda: build_edit_name_page(page, go_back=go_back),
            update,
        )

    def show_intro_from_editor(update: bool = True) -> None:
        """编辑资料页点「简介」→ 编辑简介页（第 2 层）。"""
        show_field_page(
            "/edit-intro",
            lambda: build_edit_intro_page(page, go_back=go_back),
            update,
        )

    def show_birthday_from_editor(update: bool = True) -> None:
        """编辑资料页点「生日」→ 编辑生日页（第 2 层）。"""
        show_field_page(
            "/edit-birthday",
            lambda: build_edit_birthday_page(page, go_back=go_back),
            update,
        )

    def show_gender_from_editor(update: bool = True) -> None:
        """编辑资料页点「性别」→ 编辑性别页（第 2 层）。"""
        show_field_page(
            "/edit-gender",
            lambda: build_edit_gender_page(page, go_back=go_back),
            update,
        )

    def show_preferences(update: bool = True) -> None:
        """「我的」页左上角那枚 ☰ 进来的设置页：二级页，进来后底部菜单收起。"""
        origin = selected_index
        nav_stack.append(lambda: show_page(origin))
        render_preferences(update)

    def render_login(depth: int = 1, update: bool = True) -> None:
        """只重画「登录」页那**一层**，不动页面栈（同上）。

        `depth` 是它压在 `page.views` 的第几层：从「我的」页进来是第 1 层（默认），
        从**设置页**进来时压在设置页之上，是第 2 层（见 `show_login_from_settings`）。
        注册页 / 忘记密码页跟着再深一层，返回才能逐层退回去。
        """
        show_layer(
            depth,
            "/login",
            lambda: build_login_page(
                page,
                go_back=go_back,
                # 卡片底下那两个链接：各自再往下压一层，见下面的
                # show_register / show_forgot。
                open_register=lambda: show_register(depth + 1),
                open_forgot=lambda: show_forgot(depth + 1),
                # 登录成功 → 首页（一级页第 0 个 Tab）：`show_page` 会把上面压的层
                # 全撤掉，所以跳过去之后就是干净的一级页。
                open_home=lambda: show_page(0),
                # 退出登录 / 令牌失效 → 重画本层，使它回到未登录形态。
                reload_login=lambda: render_login(depth),
            ),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_login_from_settings(update: bool = True) -> None:
        """「我的」页「账号」卡片里点「登录」/「管理」：登录页压在**这个 Tab 之上**（第 1 层）。

        回一层回的是进来时那个一级页（`show_page(origin)`）—— 在那儿登录完退回来，整页
        重画，账号卡片也就跟着刷成「已登录」。

        （名字里的 settings 是历史：这张卡片原来长在设置页里，现在搬到「我的」页。从设置页
        进去登录要压第 2 层，那条路已随卡片一起撤掉。）
        """
        origin = selected_index
        nav_stack.append(lambda: show_page(origin))
        render_login(1, update)

    def render_register(depth: int = 2, update: bool = True) -> None:
        """只重画「注册」页那一层（默认**第 2 层**），不动页面栈（同上）。"""
        show_layer(
            depth,
            "/register",
            lambda: build_register_page(page, go_back=go_back),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_register(depth: int = 2, update: bool = True) -> None:
        """登录页「注册新账号」进来的三级页。

        回一层回的是**登录页那一层**、不是一级页：所以这里压的是 `render_login(depth-1)`
        （只重画登录页那一层）。登录页自己压的那层「回上一页」还留在栈里 —— 从这一页连按
        两次返回，才会回到进来时的地方（「我的」页那个 Tab / 设置页）。
        """
        nav_stack.append(lambda: render_login(depth - 1))
        render_register(depth, update)

    def render_forgot(depth: int = 2, update: bool = True) -> None:
        """只重画「忘记密码」页那一层（默认**第 2 层**），不动页面栈（同上）。"""
        show_layer(
            depth,
            "/forgot",
            lambda: build_forgot_password_page(page, go_back=go_back),
        )
        page.bgcolor = PAGE_BGCOLOR
        menu_bar.visible = False
        if update:
            page.update()

    def show_forgot(depth: int = 2, update: bool = True) -> None:
        """登录页「忘记密码」进来的三级页（同上，回一层回登录页）。"""
        nav_stack.append(lambda: render_login(depth - 1))
        render_forgot(depth, update)

    def menu_item(index: int, label: str, badge: str = "") -> ft.Control:
        """底栏一项：**只有文字**（照小红书那排），选中的放大 + 加粗 + 颜色压深。

        文字控件留一份引用（`menu_label_texts`）：选中态是**改它**、不是重建 —— 挂着
        `animate_scale` 才有得插值，切页时那一项是「弹大」的。

        `badge` 给了就在那两个字右上角挂一枚红徽标（「消息」那一格是 99+）。
        """
        selected = selected_index == index
        text = ft.Text(
            label,
            size=MENU_LABEL_SIZE,
            color=MENU_LABEL_SELECTED if selected else MENU_LABEL_IDLE,
            weight=ft.FontWeight.BOLD if selected else ft.FontWeight.NORMAL,
            # 放大对齐中心：字只变大、不挪位。
            scale=ft.Scale(
                MENU_LABEL_ZOOM if selected else 1,
                alignment=ft.Alignment.CENTER,
            ),
            animate_scale=ft.Animation(
                MENU_LABEL_ZOOM_MS, ft.AnimationCurve.EASE_OUT
            ),
            badge=(
                ft.Badge(
                    label=badge,
                    bgcolor=MENU_BADGE_BG,
                    text_color="#FFFFFF",
                    text_style=ft.TextStyle(size=10),
                    padding=ft.Padding.symmetric(horizontal=5, vertical=0),
                )
                if badge
                else None
            ),
        )
        menu_label_texts.append((index, text))
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=lambda _: show_page(index),
            content=text,
        )

    def notify_unavailable() -> None:
        """底栏那颗「+」和「我的」页那个红胶囊：两处目前都没接功能，点了给一句提示。

        「新增待办」整块已经删掉，这两个按钮先留着小红书那一笔红色视觉 —— 底栏
        那颗「+」和我的页的胶囊都走这一个回调。新增倒数日不在这儿，它在倒数日页
        右下角自己那枚「+」上。
        """
        page.show_dialog(build_toast(page, "该功能暂未开放"))

    def menu_plus() -> ft.Control:
        """中间那颗「+」（小红书最显眼的一笔）：**扁椭圆**的红按钮 + 白加号。

        照旧摆在底栏正中，但暂时没接功能（见 `notify_unavailable`）。
        """
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=ft.Container(
                width=MENU_PLUS_WIDTH,
                height=MENU_PLUS_HEIGHT,
                alignment=ft.Alignment.CENTER,
                # 圆角比「高的一半」小一档：是一枚圆角扁块，不是完整椭圆。
                border_radius=ft.BorderRadius.all(MENU_PLUS_RADIUS),
                bgcolor=MENU_PLUS_BG,
                ink=True,
                on_click=lambda _: notify_unavailable(),
                content=ft.Icon(ft.Icons.ADD, size=22, color="#FFFFFF"),
            ),
        )

    def refresh_menu_items() -> None:
        """切页后把选中态刷到那 4 个文字上（放大 / 加粗 / 压深换人）。

        改的是原来那几个 `ft.Text`：它们带着 `animate_scale`，所以「放大」是动画出来的。
        """
        for index, text in menu_label_texts:
            selected = selected_index == index
            text.color = MENU_LABEL_SELECTED if selected else MENU_LABEL_IDLE
            text.weight = (
                ft.FontWeight.BOLD if selected else ft.FontWeight.NORMAL
            )
            text.scale = ft.Scale(
                MENU_LABEL_ZOOM if selected else 1,
                alignment=ft.Alignment.CENTER,
            )
        # 底栏这时候可能还没挂到页面上（第一次是 `build_navigation` 里先 build 的），
        # 挂上了才刷得动 —— 走 safe_update 免得抛。
        safe_update(menu_items)

    def build_menu_items() -> None:
        """建 / 刷底栏那五格：**只建一次**，之后都走 `refresh_menu_items` 改选中态。"""
        if menu_items.controls:
            refresh_menu_items()
            return
        menu_items.controls = [
            # 第 1 格原来是「待办」，页面换成发现流之后改叫「首页」（和那一页对得上）。
            menu_item(0, "首页"),
            menu_item(1, "倒数日"),
            menu_plus(),
            # 「消息」：页面上有 9 条未读，底栏这一格跟着挂个「99+」（照截图那排）。
            menu_item(3, "消息", badge="99+"),
            menu_item(4, "我的"),
        ]

    show_page(0, update=False)

    page.add(
        ft.Stack(
            expand=True,
            controls=[
                holder,
                menu_bar,
            ],
        )
    )

    page.on_media_change = keep_menu_off_keyboard
    # 真机的「返回」接到页面上：返回键 / 边缘返回手势弹的是一层 View，而不是
    # 把 Activity 结束掉（见 `on_view_pop`）。
    page.on_view_pop = on_view_pop
