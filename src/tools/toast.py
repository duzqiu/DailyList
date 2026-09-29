"""居中的 toast：一句话的提示，浮在屏幕中间，到点自己消失。

原先用的 `ft.SnackBar` 是默认那档（FIXED）—— 从屏幕**底部**升起的一条，还得等它滑
上来、再滑下去。现在改 FLOATING 档，靠一段底部留白把它顶到屏幕正中：留白按「(屏高
− 这块的高) / 2」算，宽度按文字估出来（封顶 `TOAST_MAX_WIDTH`），看着就是屏幕中间
浮起的一粒提示。

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
# 这块估出来的高度：算「垂直居中要多少底部留白」得用到它（Flutter 里浮动 SnackBar
# 的最小高度正是 48）。
TOAST_HEIGHT = 48
TOAST_DURATION_MS = 2000


def _center_bottom(page: ft.Page) -> float:
    """垂直居中要的底部留白 = (屏高 − 这块的高) / 2。

    量不到屏高（页面还没渲染出尺寸）时返回 0：那时它会落回底部，总比按一个瞎猜的
    屏高算出离谱的位置强。
    """
    screen = page.height or 0
    return max(0.0, (screen - TOAST_HEIGHT) / 2)


def build_toast(
    page: ft.Page,
    message: str,
    duration: int = TOAST_DURATION_MS,
) -> ft.SnackBar:
    """一句话的居中提示；`duration` 毫秒后自己消失。"""
    return ft.SnackBar(
        # 提示就一行：字宽宁可裁掉尾巴，也别折行把这块撑大。
        content=ft.Text(
            message,
            size=TOAST_TEXT_SIZE,
            color=TOAST_TEXT_COLOR,
            no_wrap=True,
            text_align=ft.TextAlign.CENTER,
        ),
        # 默认那档（FIXED）是贴底的一条，只有 FLOATING 才认下面那个 margin。
        behavior=ft.SnackBarBehavior.FLOATING,
        width=min(
            TOAST_MAX_WIDTH,
            text_width(message, TOAST_TEXT_SIZE) + TOAST_WIDTH_SLACK,
        ),
        margin=ft.Margin.only(bottom=_center_bottom(page)),
        bgcolor=TOAST_BG,
        shape=ft.RoundedRectangleBorder(radius=TOAST_RADIUS),
        padding=ft.Padding.symmetric(
            horizontal=TOAST_PADDING_H, vertical=TOAST_PADDING_V
        ),
        duration=duration,
        elevation=TOAST_ELEVATION,
    )
