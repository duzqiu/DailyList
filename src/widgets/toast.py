"""居中的 toast：一句话的提示，浮在屏幕正中，到点自己消失。

宽度跟着**提示语的长度**走：短句是一小粒；长句宽到屏宽的边界就不再长，多出来的字**折到
下一行**（这一粒的高度跟着往上长）—— 不会因为一格装不下而把尾巴裁掉。

原先用的 `ft.SnackBar` 是默认那档（FIXED）—— 从屏幕**底部**升起的一条，还得等它滑
上来、再滑下去。现在改 FLOATING 档，用 `margin` 把它摆到正中：左右各留
「(屏宽 − 粒宽) / 2」把宽度钉成一粒，底部留「(屏高 − 粒高) / 2」把它顶到垂直中间。

⚠️ **别给 SnackBar 设 `width`**：Flet 文档写明 `width` 与 `margin` 不能同时用，同时给了
以 `width` 优先 —— 也就是设了 `width` 之后 `margin` 会被**整个忽略**，这一粒就掉回屏幕
底部（之前就是这么写的，所以「居中」一直没生效）。宽度改由左右留白表达即可。

⚠️ **已知局限（键盘）**：SnackBar 会被 Flutter 抬到键盘之上。`page.media.view_insets.bottom`
在这套环境里实测恒为 0、`page.height` 也不变、连铺满可用区域的探针都量不到变化，所以
「按键盘高度补偿下边距」这条路走不通（试过：补偿量算出来是 0）。**键盘没弹时它是正中的**
—— 这是目前确定的、能稳定显示的那一版；键盘弹起时的位置问题留给以后（例如改成页面内
自绘的层，但那一版曾把整页点击挡掉，要另想办法）。

用法（各页面统一走它，别再自己拼 SnackBar）：

    page.show_dialog(build_toast(page, "已复制邮箱"))
"""

from __future__ import annotations

from math import ceil

import flet as ft

from widgets.layout import SUBPAGE_TITLE_COLOR, text_width

# 提示的字与底：深靛蓝底 + 白字（和二级页标题同一个深蓝，压在浅色页面上够清楚）。
TOAST_TEXT_SIZE = 13
TOAST_TEXT_COLOR = "#FFFFFF"
TOAST_BG = SUBPAGE_TITLE_COLOR
TOAST_RADIUS = 8
TOAST_ELEVATION = 4
TOAST_PADDING_H = 16
TOAST_PADDING_V = 11
TOAST_WIDTH_SLACK = 2 * TOAST_PADDING_H
# 宽度**跟着提示语走**：`text_width` 估出字宽 + 两侧留白，短句就是一小粒；一格装不下才
# 折行把字显示全 —— 原先宽度钉死在 240 又锁了单行（`no_wrap`），句子稍长尾巴就被裁掉，
# 看着像话没说完。
# 上限按屏宽给：两边留出 `TOAST_SIDE_MARGIN` 就不会顶到屏幕边上；量不到屏宽时退回
# `TOAST_MAX_WIDTH`。
TOAST_SIDE_MARGIN = 24
TOAST_MAX_WIDTH = 300
# 再窄也不能比这窄：屏宽量得离谱时（宽度还没出来就先给了一个很小的数）别把这一粒
# 压成一条竖线，至少放得下三四个字。
TOAST_MIN_PILL_WIDTH = 120
# `text_width` 是粗估（中文按整宽、西文按 0.55 估），给它一点富余，免得差一点点就折行、
# 或者实际折出来的行数比算的多一行。
TOAST_WIDTH_ESTIMATE_SLACK = 1.06
# 一行的高度（13pt 字那一行行盒）：折行之后这一粒有多高要靠它算，垂直居中要用到。
TOAST_LINE_HEIGHT = 18
# 单行那一粒的高度：Flutter 里浮动 SnackBar 的最小高度正是 48，算出来比它矮时按它。
TOAST_HEIGHT_MIN = 48
TOAST_DURATION_MS = 2000


def _toast_metrics(page: ft.Page, message: str) -> tuple[float, float]:
    """这一粒该多大：`(宽度, 高度)`。

    宽度跟着提示语走 —— 短句一小粒，长句宽到上限就不再长，**超出一行的部分折到下一行**
    （所以高度跟着行数往上长）。居中和换算左右留白都得用这两个数，所以算一次给两边。
    """
    screen_width = page.width or 0
    max_width = (
        min(TOAST_MAX_WIDTH, screen_width - 2 * TOAST_SIDE_MARGIN)
        if screen_width
        else TOAST_MAX_WIDTH
    )
    max_width = max(max_width, TOAST_MIN_PILL_WIDTH)
    # 字宽（带点富余）：比它能容字的那一段窄就一行，宽了就折。
    ink = text_width(message, TOAST_TEXT_SIZE) * TOAST_WIDTH_ESTIMATE_SLACK
    line_width = max(max_width - TOAST_WIDTH_SLACK, 1.0)
    width = min(ink + TOAST_WIDTH_SLACK, max_width)
    lines = max(1, ceil(ink / line_width))
    height = max(
        TOAST_HEIGHT_MIN, lines * TOAST_LINE_HEIGHT + 2 * TOAST_PADDING_V
    )
    return width, height


def _toast_margin(
    page: ft.Page, pill_width: float, pill_height: float
) -> ft.Margin:
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
    bottom = (screen_height - pill_height) / 2 if screen_height else 0.0
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
    pill_width, pill_height = _toast_metrics(page, message)
    return ft.SnackBar(
        # **不锁一行**：比一格宽的句子要折行才看得全 —— 原先 `no_wrap=True`，长一点的
        # 提示语尾巴就被裁掉了。短句本来就放得进一行，照旧是一小粒。
        content=ft.Text(
            message,
            size=TOAST_TEXT_SIZE,
            color=TOAST_TEXT_COLOR,
            text_align=ft.TextAlign.CENTER,
        ),
        # 默认那档（FIXED）是贴底的一条，只有 FLOATING 才认下面的 margin。
        behavior=ft.SnackBarBehavior.FLOATING,
        # 这里**不能**再写 width=（写了 margin 就失效，见 `_toast_margin`）。
        margin=_toast_margin(page, pill_width, pill_height),
        bgcolor=TOAST_BG,
        shape=ft.RoundedRectangleBorder(radius=TOAST_RADIUS),
        padding=ft.Padding.symmetric(
            horizontal=TOAST_PADDING_H, vertical=TOAST_PADDING_V
        ),
        duration=duration,
        elevation=TOAST_ELEVATION,
    )
