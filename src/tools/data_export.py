"""导出数据：把库里的待办 / 倒数日 / 设置拍成一份 JSON。

选 JSON 是因为它和 SQLite 结构最贴 —— 一张表一个数组，字段名和列名一一对上，将来
要「导入回填」不用再拍平一层。写文件时 `ensure_ascii=False`，中文在文件里仍是原文，
用户拿去看也认得出。

Flet 那边只管把一串字节交出去（`FilePicker.save_file` 的 `src_bytes`）：桌面弹的是
「另存为」，手机和 Web 上表现为导出 / 下载 —— 格式是这里定的，Flet 不挑。
"""

import json
from datetime import datetime

from tools import db

# 文件里写明的格式标记：以后要加 CSV、或改结构，靠这两个字段分辨是什么、哪一版。
EXPORT_FORMAT = "json"
EXPORT_VERSION = 1
APP_NAME = "每日清单"


def export_file_name(now: datetime | None = None) -> str:
    """导出文件名：每日清单-2026-09-29.json（同一天导出两次就是同名覆盖）。"""
    return f"{APP_NAME}-{(now or datetime.now()):%Y-%m-%d}.{EXPORT_FORMAT}"


def build_payload(now: datetime | None = None) -> dict:
    """库里的全部数据拍成一个可 JSON 序列化的 dict。

    三张表各一数组，`settings` 是键值对（它本来就是 name/value 两列）。
    """
    moment = now or datetime.now()
    return {
        "app": APP_NAME,
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "exported_at": moment.isoformat(timespec="seconds"),
        "todos": [
            {
                "id": todo.id,
                "due_date": todo.due_date.isoformat(),
                "due_time": todo.due_time,
                "end_time": todo.end_time,
                "category": todo.category,
                "content": todo.content,
                "done": todo.done,
                "repeat_cycle": todo.repeat_cycle,
            }
            for todo in db.list_all_todos()
        ],
        "countdowns": [
            {
                "id": item.id,
                "due_date": item.due_date.isoformat(),
                "cycle": item.cycle,
                "content": item.content,
                "bgcolor": item.bgcolor,
            }
            for item in db.list_countdowns()
        ],
        "settings": db.list_settings(),
    }


def export_bytes(now: datetime | None = None) -> bytes:
    """序列化成 UTF-8 的 JSON 字节，交给 `save_file(src_bytes=...)`。

    `indent=2` 是为了导出的文件能直接打开看；`ensure_ascii=False` 让中文保持中文
    （否则整份文件会变成 `\\uXXXX` 的转义，人没法读）。
    """
    return json.dumps(
        build_payload(now), ensure_ascii=False, indent=2
    ).encode("utf-8")
