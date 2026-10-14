"""导出数据：把倒数日与设置拍成一份 JSON。

两边的来源不一样：**倒数日**取自后端那份缓存（tools/countdown_store.py），**设置**取自
内存里的 mock 数据（tools/mock_settings.py，见 README「待处理问题」）—— 导出即所见。

选 JSON 是因为结构直白 —— 一块数据一个数组，字段名和原来的列名一一对上，将来要「导入
回填」不用再拍平一层。写文件时 `ensure_ascii=False`，中文在文件里仍是原文，用户拿去看
也认得出。

Flet 那边只管把一串字节交出去（`FilePicker.save_file` 的 `src_bytes`）：桌面弹的是
「另存为」，手机和 Web 上表现为导出 / 下载 —— 格式是这里定的，Flet 不挑。
"""

import json
from datetime import datetime

from tools import countdown_store, mock_settings

# 文件里写明的格式标记：以后要加 CSV、或改结构，靠这两个字段分辨是什么、哪一版。
EXPORT_FORMAT = "json"
EXPORT_VERSION = 1
APP_NAME = "每日清单"


def export_file_name(now: datetime | None = None) -> str:
    """导出文件名：每日清单-2026-09-29.json（同一天导出两次就是同名覆盖）。"""
    return f"{APP_NAME}-{(now or datetime.now()):%Y-%m-%d}.{EXPORT_FORMAT}"


def build_payload(now: datetime | None = None) -> dict:
    """当前全部数据拍成一个可 JSON 序列化的 dict。

    两块各一个字段：`countdowns` 来自后端缓存，`settings` 是内存 mock 里那份键值对。
    """
    moment = now or datetime.now()
    return {
        "app": APP_NAME,
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "exported_at": moment.isoformat(timespec="seconds"),
        "countdowns": [
            {
                "id": item.id,
                "due_date": item.due_date.isoformat(),
                "cycle": item.cycle,
                "content": item.content,
                "bgcolor": item.bgcolor,
            }
            for item in countdown_store.items()
        ],
        "settings": mock_settings.list_settings(),
    }


def export_bytes(now: datetime | None = None) -> bytes:
    """序列化成 UTF-8 的 JSON 字节，交给 `save_file(src_bytes=...)`。

    `indent=2` 是为了导出的文件能直接打开看；`ensure_ascii=False` 让中文保持中文
    （否则整份文件会变成 `\\uXXXX` 的转义，人没法读）。
    """
    return json.dumps(
        build_payload(now), ensure_ascii=False, indent=2
    ).encode("utf-8")
