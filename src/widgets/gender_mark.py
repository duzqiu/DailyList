"""昵称后面那枚**彩色性别符号**：♂ 蓝、♀ 粉，其余（保密 / 没填）不画。

一处实现、两处用 —— 「我的」页账号卡片（widgets/settings_card.py）与登录页的「当前用户」
卡片（pages/login.py）都显示昵称，符号的取值与配色别各写一份（见 README 开发约定 2）。

**为什么用 `ft.TextSpan` 而不是并排放一个 `ft.Icon`**：符号是**长在昵称这一行文字里**的，
用 span 走的是文本排版，基线、字号、行高都自动跟昵称对齐；换成 `ft.Row` + `ft.Icon` 就得
手动凑垂直居中和字号，昵称一长、字号一改就容易歪。

**颜色为什么不跟随 `on_image`**：「我的」页那张卡片压在背景图上时昵称会变白，但符号
**故意保持彩色** —— 它要的就是这点颜色，压在图上也认得出来（见 `build_account_card`
的 `on_image` 参数）。
"""

import flet as ft

# 中文取值与 api/member_profile.GENDERS（「男 / 女 / 保密」）一致。
MALE = "男"
FEMALE = "女"

# 性别 → (符号, 颜色)。**只列要显示的这两个**：保密 / 没填 / 后端将来加了新取值，
# 一律查不到 → 不画符号（`name_spans` 只返回昵称本身）。
MARKS: dict[str, tuple[str, str]] = {
    MALE: ("♂", "#2F80ED"),  # 蓝
    FEMALE: ("♀", "#FF4D8F"),  # 粉
}


def name_spans(
    name: str,
    gender: str = "",
    *,
    size: int = 16,
    weight: ft.FontWeight = ft.FontWeight.BOLD,
) -> list[ft.TextSpan]:
    """把「昵称 + 性别符号」拼成 `ft.Text(spans=...)` 用的片段。

    `gender` 传**中文**（「男」/「女」，见 `tools/my_profile.py` 的 `account_gender`）；
    传别的（「保密」、空串、未知值）就只返回昵称本身，不画符号。

    昵称自己的颜色由调用方的 `ft.Text(color=...)` 决定（压在背景图上时是白色），
    符号始终是彩色。`size` / `weight` 要和外面那个 `ft.Text` 保持一致。
    """
    spans = [ft.TextSpan(name)]
    mark = MARKS.get(gender)
    if mark is None:
        return spans
    symbol, color = mark
    # 符号前留一点空隙；字号 / 粗细**显式写上**，不依赖 span 从父 `Text` 继承
    # （继承行为在部分 Flet 版本上不一致，符号会忽然缩水一档）。
    spans.append(
        ft.TextSpan(
            f"  {symbol}",
            style=ft.TextStyle(size=size, weight=weight, color=color),
        )
    )
    return spans


__all__ = ["FEMALE", "MALE", "MARKS", "name_spans"]
