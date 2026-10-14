"""导入数据：把 `tools/data_export.py` 导出的那份 JSON 读回来。

**设置**逐条写进内存 mock（tools/mock_settings.py）；**倒数日**那段暂时不落地 —— 页面读的是
后端（api/member_countdowns.py），写哪儿都不会显示出来，所以如实报 0 而不是假装写进去了
（见 README「待处理问题」）。

文件里认不出来的行直接跳过，最后把「进了多少、跳了几条」报给调用方。

早先的导出文件里还带一个 `todos` 数组（待办那版留下的），现在直接忽略 —— 老备份
照样能导，只是待办不再进库。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from tools import cycles, data_export, mock_settings


class ImportFailed(Exception):
    """文件根本不能用。

    消息是**给用户看的一句话**（页面直接拿去弹提示），所以要短、要说人话。
    """


@dataclass
class ImportResult:
    """导入结果：各类写进去多少条，以及跳过了几行。"""

    countdowns: int = 0
    settings: int = 0
    skipped: int = 0

    def summary(self) -> str:
        """一句话说清导入了什么（提示条只有一行）。"""
        if not self.settings:
            return "文件里没有可导入的数据"
        return f"已导入 {self.settings} 项设置（倒数日暂未落地）"


def _iso_date(value: Any) -> str | None:
    """把 `YYYY-MM-DD` 验成库里存的那种字符串；认不出来就 `None`。"""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


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
                "cycle": str(item.get("cycle") or cycles.DEFAULT_CYCLE),
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

    这一步会**先清空**倒数日，所以文件必须验明正身：只有 `format` 对得上、
    而且解析出了数据的文件才放行 —— 不然随手选个别的 JSON 就把库清空了。
    """
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ImportFailed("这个文件不是 JSON") from error

    if not isinstance(data, dict) or data.get("format") != data_export.EXPORT_FORMAT:
        raise ImportFailed("不是「每日清单」导出的文件")

    countdowns, skipped_countdowns = _countdowns_from(data.get("countdowns"))
    settings = _settings_from(data.get("settings"))
    # 两边都没解析出东西就别当导入成功了（老备份里只有 countdowns 也算数，见模块说明）。
    if not countdowns and not settings:
        raise ImportFailed("文件里没有可导入的数据")

    written_settings = 0
    for name, value in settings.items():
        mock_settings.set_setting(name, value)
        written_settings += 1
    # 倒数日那段**暂时不落地**：页面读的是后端，写哪儿都显示不出来 —— 如实报 0。
    return ImportResult(
        countdowns=0,
        settings=written_settings,
        skipped=skipped_countdowns,
    )
