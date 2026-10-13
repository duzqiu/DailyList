"""居中的 toast：一句话的提示，浮在屏幕正中，到点自己消失。

原先用的 `ft.SnackBar` 是默认那档（FIXED）—— 从屏幕**底部**升起的一条，还得等它滑
上来、再滑下去。现在改 FLOATING 档，用 `margin` 把它摆到正中：左右各留
「(屏宽 − 粒宽) / 2」把宽度钉成一粒，底部留「(屏高 − 粒高) / 2」把它顶到垂直中间。

⚠️ **别给 SnackBar 设 `width`**：Flet 文档写明 `width` 与 `margin` 不能同时用，同时给了
以 `width` 优先 —— 也就是设了 `width` 之后 `margin` 会被**整个忽略**，这一粒就掉回屏幕
底部（之前就是这么写的，所以「居中」一直没生效）。宽度改由左右留白表达即可。

用法（各页面统一走它，别再自己拼 SnackBar）：

    page.show_dialog(build_toast(page, "已复制邮箱"))
"""

from __future__ import annotations

import flet as ft

from tools.layout import SUBPAGE_TITLE_COLOR, text_width

# 提示的字与底：深靛蓝底 + 白字（和二级页标题同一个深蓝，压在浅色页面上够清楚）。
TOAST_TEXT_SIZE = 13
TOAST_TEXT_COLOR = "#FFFFFF"
TOAST_BG = SUBPAGE_TITLE_COLOR
TOAST_RADIUS = 8
TOAST_ELEVATION = 4
# 内边距与宽度：宽度按文字估（`text_width` + 两侧留白），但别宽过 `TOAST_MAX_WIDTH`
# —— 提示是一粒，不是一条横幅。
TOAST_PADDING_H = 16
TOAST_PADDING_V = 11
TOAST_WIDTH_SLACK = 2 * TOAST_PADDING_H
TOAST_MAX_WIDTH = 240
# 这块估出来的高度：算「垂直居中要多大的下边距」得用到它（Flutter 里浮动 SnackBar
# 的最小高度正是 48）。
TOAST_HEIGHT = 48
TOAST_DURATION_MS = 2000


def _toast_margin(page: ft.Page, pill_width: float) -> ft.Margin:
    """把这一粒摆到屏幕正中所需的四周留白。

    宽度也由留白表达（两侧各留「(屏宽 − 粒宽) / 2」），底部留「(屏高 − 粒高) / 2」
    把它顶到垂直中间 —— 两块合起来就是正中那一粒。

    ⚠️ 之所以不干脆用 SnackBar 的 `width`：Flet 文档写明「`width` 与 `margin` 不能同时
    使用，两者都指定时以 `width` 优先」，也就是**设了 `width` 之后 `margin` 会被整个
    忽略**，SnackBar 会掉回默认的屏幕底部（这正是「提示不在中间」的原因）。

    量不到尺寸（页面还没渲染出宽高）时对应方向留 0：宽度退化成整条、位置退化成贴底，
    总比按瞎猜的屏宽屏高算出离谱位置强。
    """
    screen_width = page.width or 0
    screen_height = page.height or 0
    side = (screen_width - pill_width) / 2 if screen_width else 0.0
    bottom = (screen_height - TOAST_HEIGHT) / 2 if screen_height else 0.0
    return ft.Margin.only(
        left=max(0.0, side),
        top=0,
        right=max(0.0, side),
        bottom=max(0.0, bottom),
    )


def build_toast(
    page: ft.Page,
    message: str,
    duration: int = TOAST_DURATION_MS,
) -> ft.SnackBar:
    """一句话的居中提示（屏幕正中那一粒）；`duration` 毫秒后自己消失。"""
    pill_width = min(
        TOAST_MAX_WIDTH,
        text_width(message, TOAST_TEXT_SIZE) + TOAST_WIDTH_SLACK,
    )
    return ft.SnackBar(
        # 提示就一行：字宽宁可裁掉尾巴，也别折行把这块撑大。
        content=ft.Text(
            message,
            size=TOAST_TEXT_SIZE,
            color=TOAST_TEXT_COLOR,
            no_wrap=True,
            text_align=ft.TextAlign.CENTER,
        ),
        # 默认那档（FIXED）是贴底的一条，只有 FLOATING 才认下面的 margin。
        behavior=ft.SnackBarBehavior.FLOATING,
        # 这里**不能**再写 width=（写了 margin 就失效，见 `_toast_margin`）。
        margin=_toast_margin(page, pill_width),
        bgcolor=TOAST_BG,
        shape=ft.RoundedRectangleBorder(radius=TOAST_RADIUS),
        padding=ft.Padding.symmetric(
            horizontal=TOAST_PADDING_H, vertical=TOAST_PADDING_V
        ),
        duration=duration,
        elevation=TOAST_ELEVATION,
    )
