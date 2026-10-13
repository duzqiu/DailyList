"""用户中心 · 倒数日接口（后端前缀 `/member/countdowns`，全部要会员令牌）。

对应后端 fastapi-admin-backend：
- `app/api/v1/endpoints/member_countdowns.py`  路由
- `app/schemas/countdown.py`                   `CountdownSelfCreate` / `CountdownSelfUpdate` /
                                              `CountdownOut`
- `app/models/countdown.py`                    `CountdownCycle`（周期枚举）

五个接口都是「按当前登录会员隔离」的：归属由后端从令牌里取，这边**不传** member_id。

只有「发什么、收什么」：出错统一抛 `client.ApiError`，界面提示留在页面里。周期那一栏
在 App 内部一直用中文（见 tools/db.py 的 `REPEAT_CYCLES`），所以收发两端各做一次映射
（`CYCLE_TO_API` / `CYCLE_FROM_API`）。
"""

from dataclasses import dataclass
from datetime import date

from . import session
from .client import delete, get, post, put

# 周期映射：App 的中文 ↔ 后端的 `CountdownCycle`。
#
# ⚠️ 后端目前只有这 5 档（once / daily / weekly / monthly / yearly），而 App 的
# `db.REPEAT_CYCLES` 有 10 档 —— 「三天 / 工作日 / 非工作日 / 三月 / 六月」这 5 档
# 后端还没有对应取值，所以**倒数日的表单只提供这 5 档**（见 `SUPPORTED_CYCLES`）。
# 要让那 5 档也能用：后端给 `CountdownCycle` 补枚举值 + 中文标签，重新部署后在这里
# 补两行映射、把 `SUPPORTED_CYCLES` 换成 `db.REPEAT_CYCLES` 即可。
CYCLE_TO_API: dict[str, str] = {
    "不循环": "once",
    "每天": "daily",
    "一周": "weekly",
    "一月": "monthly",
    "一年": "yearly",
}
CYCLE_FROM_API: dict[str, str] = {value: key for key, value in CYCLE_TO_API.items()}
# 倒数日表单能选的周期（顺序就是下拉里的顺序）。
SUPPORTED_CYCLES: tuple[str, ...] = tuple(CYCLE_TO_API)
# 认不出来的周期（后端加了新档而这边还没跟上）就按「不循环」显示，别让它把页面带崩。
DEFAULT_CYCLE = "不循环"


@dataclass
class Countdown:
    """一条倒数日（后端那条记录的本地样子）。

    字段名和 tools/db.py 的 `Countdown` 保持一致（`due_date` / `cycle` / `content`），
    卡片与导出那几处代码因此不用改：**颜色不在里面** —— 后端没有这个字段，由
    tools/countdown_store.py 按 id 稳定推一个浅色。
    """

    id: int
    due_date: date
    cycle: str
    content: str
    active: bool = True
    created_at: str = ""


def _parse_date(raw: object) -> date:
    """后端给的是 `YYYY-MM-DD`；拿不到就退回今天（宁可显示错一天，也别崩）。"""
    if isinstance(raw, str) and raw:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            pass
    return date.today()


def to_item(payload: dict) -> Countdown:
    """把 `CountdownOut` 翻成本地的 `Countdown`。"""
    raw_cycle = payload.get("cycle")
    return Countdown(
        id=int(payload.get("id") or 0),
        due_date=_parse_date(payload.get("target_date")),
        cycle=CYCLE_FROM_API.get(str(raw_cycle), DEFAULT_CYCLE),
        content=str(payload.get("title") or ""),
        active=bool(payload.get("is_active", True)),
        created_at=str(payload.get("created_at") or ""),
    )


async def list_mine() -> list[Countdown]:
    """我的倒数日列表（`GET /member/countdowns`）。

    后端是分页信封（`PageResult`：`{items, total, ...}`），这里一次要一页足够大的
    —— 倒数日这种量级（几十条）没必要翻页；真到上千条再谈分页。
    """
    result = await get(
        "/member/countdowns",
        token=session.access_token(),
    )
    payload = result if isinstance(result, dict) else {}
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return []
    return [to_item(item) for item in raw_items if isinstance(item, dict)]


async def create(
    due_date: date, content: str, cycle: str = DEFAULT_CYCLE
) -> dict:
    """新增（`POST /member/countdowns`）：归属由后端按令牌决定。"""
    return await post(
        "/member/countdowns",
        payload={
            "title": content,
            "cycle": CYCLE_TO_API.get(cycle, "once"),
            "target_date": due_date.isoformat(),
            "is_active": True,
            # 备注留给后端的管理界面用，App 这边不填。
            "remark": "",
        },
        token=session.access_token(),
    )


async def update(
    countdown_id: int,
    due_date: date,
    content: str,
    cycle: str = DEFAULT_CYCLE,
) -> dict:
    """修改（`PUT /member/countdowns/{id}`）；动别人的会 403。"""
    return await put(
        f"/member/countdowns/{countdown_id}",
        payload={
            "title": content,
            "cycle": CYCLE_TO_API.get(cycle, "once"),
            "target_date": due_date.isoformat(),
            "is_active": True,
        },
        token=session.access_token(),
    )


async def delete_mine(countdown_id: int) -> dict:
    """删除（`DELETE /member/countdowns/{id}`）。"""
    return await delete(
        f"/member/countdowns/{countdown_id}",
        token=session.access_token(),
    )
