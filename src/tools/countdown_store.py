"""倒数日的内存仓库：唯一数据源是后端（`/member/countdowns`），这里给页面一个**同步**读法。

为什么要有这一层：日历页有 5 处在**同步构建**时读倒数日（当月弹窗里的卡片、日期格子里
的圆点、弹窗第一帧的估高），它们没法 `await`。所以拉回来的列表缓存在这里，页面同步读
`items()`；真正的增删改都落到后端，写完 `reload()` 一次再刷新界面。

未登录时缓存为空、也不发请求（页面自己显示「登录后可用」）。

颜色：后端没有颜色字段，这里按 `id` 从 `CARD_COLORS` 里稳定取一个浅色 —— 卡片长相和
原来一样（都是一档浅色），而且同一条倒数日每次进页面都是同一个颜色。
"""

import random
from dataclasses import dataclass
from datetime import date

from api import member_countdowns, session
from api.client import ApiError

# 卡片底色可选的那几档浅色（原来是「新增时随机取一个」）。每档都是浅色调，卡片上的
# 深色文字因此在任何一种上都读得清。
CARD_COLORS = (
    ("冰浅蓝", "#E0F2FE"),
    ("浅天蓝", "#BAE6FD"),
    ("莫兰迪灰蓝", "#D1DCE8"),
    ("青调浅灰蓝", "#C9D7E0"),
    ("柔和浅紫", "#DDD6FE"),
    ("奶薄荷浅绿", "#ECFDF5"),
    ("柔和浅青绿", "#D1FAE5"),
    ("莫兰迪浅绿", "#E6F4EA"),
    ("极浅灰粉", "#FDF2F8"),
    ("莫兰迪裸粉", "#F4E7E9"),
    ("奶油杏", "#FFF7ED"),
    ("莫兰迪奶咖", "#F5EBE0"),
    ("页面底色灰", "#F8FAFC"),
    ("边框浅灰", "#E2E8F0"),
)
DEFAULT_BGCOLOR = CARD_COLORS[0][1]


@dataclass
class Countdown:
    """一条倒数日。

    字段与 tools/db.py 的 `Countdown` 一致（`due_date` / `cycle` / `content` /
    `bgcolor`），所以卡片、左滑、导出那些地方一行都不用改 —— 换的只是数据从哪来。
    """

    id: int
    due_date: date
    cycle: str
    content: str
    bgcolor: str = DEFAULT_BGCOLOR


_cache: list[Countdown] = []


def color_for(countdown_id: int) -> str:
    """按 id 稳定取一档浅色：同一条永远同一个色，不同条之间又错开。"""
    if not CARD_COLORS:
        return DEFAULT_BGCOLOR
    return CARD_COLORS[countdown_id % len(CARD_COLORS)][1]


def items() -> list[Countdown]:
    """当前缓存里的倒数日（同步，随时可读；没拉过就是空列表）。"""
    return list(_cache)


def logged_in() -> bool:
    """本地有没有会员令牌：没有就别发请求，页面直接显示「登录后可用」。"""
    return bool(session.access_token())


def clear() -> None:
    """清空缓存（退出登录、或拉取失败时用）。"""
    _cache.clear()


async def reload() -> None:
    """从后端重新拉一次我的倒数日，填进缓存。

    未登录：清空缓存直接返回（不发请求）。令牌失效（401）：清掉本地令牌 + 清缓存，
    调用方随后重画即可看到「未登录」形态。其它错误原样抛 `ApiError`，由页面提示。
    """
    if not logged_in():
        clear()
        return
    try:
        fetched = await member_countdowns.list_mine()
    except ApiError as error:
        if error.status == 401:
            session.clear()
            clear()
        raise
    _cache[:] = [
        Countdown(
            id=item.id,
            due_date=item.due_date,
            cycle=item.cycle,
            content=item.content,
            bgcolor=color_for(item.id),
        )
        for item in fetched
        # 后端有「是否有效」这一档（管理界面用），App 里没有这个概念：只显示有效的。
        if item.active
    ]


async def create(due_date: date, content: str, cycle: str) -> None:
    """新增一条并刷新缓存（颜色跟着后端给的 id 走）。"""
    await member_countdowns.create(due_date, content, cycle)
    await reload()


async def update(
    countdown_id: int, due_date: date, content: str, cycle: str
) -> None:
    """改一条并刷新缓存。"""
    await member_countdowns.update(countdown_id, due_date, content, cycle)
    await reload()


async def remove(countdown_id: int) -> None:
    """删一条并刷新缓存。"""
    await member_countdowns.delete_mine(countdown_id)
    await reload()


def pick_color() -> str:
    """新增时用的兜底色（正常情况下颜色由 `color_for(id)` 决定）。"""
    return random.choice(CARD_COLORS)[1]
