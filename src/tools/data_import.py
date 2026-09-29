"""导入数据：把 `tools/data_export.py` 导出的那份 JSON 读回库里。

导出文件里的待办是**已经铺开**的全部行（循环待办在新增时就按周期铺满一年了，见
`db.occurrence_dates`），所以写回去也是原样写、**不能再按周期展开一次** —— 这件事由
`db.replace_data()` 保证，别改成 `db.add_todo()`。

语义是「恢复备份」：待办与倒数日整表替换，设置逐条覆盖。文件里认不出来的行直接跳过，
最后把「进了多少、跳了几条」报给调用方。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from tools import data_export, db


class ImportFailed(Exception):
    """文件根本不能用。

    消息是**给用户看的一句话**（页面直接拿去弹提示），所以要短、要说人话。
    """


@dataclass
class ImportResult:
    """导入结果：各类写进去多少条，以及跳过了几行。"""

    todos: int = 0
    countdowns: int = 0
    settings: int = 0
    skipped: int = 0

    def summary(self) -> str:
        """一句话说清导入了什么（提示条只有一行，所以只报待办和倒数日）。"""
        parts: list[str] = []
        if self.todos:
            parts.append(f"{self.todos} 条待办")
        if self.countdowns:
            parts.append(f"{self.countdowns} 个倒数日")
        if not parts:
            return "文件里没有可导入的数据"
        return "已导入 " + "、".join(parts)


def _iso_date(value: Any) -> str | None:
    """把 `YYYY-MM-DD` 验成库里存的那种字符串；认不出来就 `None`。"""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _todos_from(data: Any) -> tuple[list[dict], int]:
    """挑出能用的待办行；返回 (记录, 跳过了几条)。"""
    rows: list[dict] = []
    skipped = 0
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            skipped += 1
            continue
        due_date = _iso_date(item.get("due_date"))
        category = item.get("category")
        content = item.get("content")
        # 日期、分类、内容这三样缺一不可（其余字段都能给默认值）。
        if (
            due_date is None
            or not isinstance(category, str)
            or not isinstance(content, str)
        ):
            skipped += 1
            continue
        rows.append(
            {
                "due_date": due_date,
                "due_time": str(item.get("due_time") or ""),
                "end_time": str(item.get("end_time") or ""),
                "category": category,
                "content": content,
                "done": bool(item.get("done")),
                "repeat_cycle": str(
                    item.get("repeat_cycle") or db.DEFAULT_CYCLE
                ),
            }
        )
    return rows, skipped


def _countdowns_from(data: Any) -> tuple[list[dict], int]:
    """挑出能用的倒数日行；返回 (记录, 跳过了几条)。"""
    rows: list[dict] = []
    skipped = 0
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            skipped += 1
            continue
        due_date = _iso_date(item.get("due_date"))
        content = item.get("content")
        if due_date is None or not isinstance(content, str):
            skipped += 1
            continue
        rows.append(
            {
                "due_date": due_date,
                "cycle": str(item.get("cycle") or db.DEFAULT_CYCLE),
                "content": content,
                "bgcolor": str(item.get("bgcolor") or "#F1F5F9"),
            }
        )
    return rows, skipped


def _settings_from(data: Any) -> dict[str, str]:
    """挑出能用的设置项（值是字符串的才要）。"""
    if not isinstance(data, dict):
        return {}
    return {
        str(name): str(value)
        for name, value in data.items()
        if isinstance(value, (str, int, float, bool))
    }


def import_bytes(raw: bytes) -> ImportResult:
    """把导出的 JSON（字节）导回库里；文件不能用就抛 `ImportFailed`。

    这一步会**先清空**待办与倒数日，所以文件必须验明正身：只有 `format` 对得上、
    而且解析出了数据的文件才放行 —— 不然随手选个别的 JSON 就把库清空了。
    """
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ImportFailed("这个文件不是 JSON") from error

    if not isinstance(data, dict) or data.get("format") != data_export.EXPORT_FORMAT:
        raise ImportFailed("不是「每日清单」导出的文件")

    todos, skipped_todos = _todos_from(data.get("todos"))
    countdowns, skipped_countdowns = _countdowns_from(data.get("countdowns"))
    # 一条都没解析出来就别动库了 —— 清空之后写不进去，等于白丢数据。
    if not todos and not countdowns:
        raise ImportFailed("文件里没有可导入的数据")

    written_todos, written_countdowns, written_settings = db.replace_data(
        todos, countdowns, _settings_from(data.get("settings"))
    )
    return ImportResult(
        todos=written_todos,
        countdowns=written_countdowns,
        settings=written_settings,
        skipped=skipped_todos + skipped_countdowns,
    )
