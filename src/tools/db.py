"""本地 SQLite：现在**只装登录令牌**，启动时顺手把没人再读的老东西清掉。

怎么变成这样的：倒数日整体搬到了后端（api/member_countdowns.py + tools/countdown_store.py），
其余设置项（云端开关、通知、联系方式、「我的」页资料与背景图）改走内存 mock
（tools/mock_settings.py）—— 于是这张库里只剩下 `member_access_token` /
`member_refresh_token` 两行（api/session.py 读写）。

所以这里只留四件事：库文件位置（`DB_PATH`）、建表（`init_db`）、读写一项设置
（`get_setting` / `set_setting`）。周期计算搬去了 tools/cycles.py，按设备隔离与倒数日的读写
随数据一起删掉了 —— `init_db` 会把老库里残留的 `countdowns` 表和过期的设置项一并清掉
（见 `LEGACY_TABLES` / `KEPT_SETTINGS`）。
"""

import os
import sqlite3
from pathlib import Path

# Where the SQLite file lives. A packaged app runs from inside a read-only
# bundle, so prefer the writable data directory Flet hands the app
# (`FLET_APP_STORAGE_DATA`); running from source keeps the project-root file.
_DATA_DIR = os.environ.get("FLET_APP_STORAGE_DATA")
DB_PATH = (
    Path(_DATA_DIR) / "dailylist.db"
    if _DATA_DIR
    else Path(__file__).resolve().parents[2] / "dailylist.db"
)

# 建表：只剩 `settings` 一张（name / value 两列）。
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# 老版本建过、现在已经没人在读的表：启动时删掉，别让废弃数据留在库里。
# - `todos`：待办那一版的表；
# - `countdowns`：倒数日还在本地时那张（含它的 owner 列与索引），数据源早换成后端了。
LEGACY_TABLES = ("todos", "countdowns")

# `settings` 里**该留**的键：只有登录令牌。其余一律删 —— 那些设置项现在走内存 mock
# （tools/mock_settings.py），留在库里只是占地方，还容易让人以为它们还在起作用。
# ⚠️ 键名与 api/session.py 里的 ACCESS_KEY / REFRESH_KEY 对应；以后若把某个设置项改回
# 落库，记得把它的键加到这里，否则下次启动就被清掉了。
KEPT_SETTINGS = (
    "member_access_token",
    "member_refresh_token",
)


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """建表 + 清掉没人再读的老东西（见 `LEGACY_TABLES` / `KEPT_SETTINGS`）。

    每次启动都跑，重复执行无副作用（建表是 `IF NOT EXISTS`、删表是 `DROP ... IF EXISTS`、
    设置项是一条 DELETE）。
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect()
    try:
        connection.executescript(SCHEMA)
        _purge_stale(connection)
        connection.commit()
    finally:
        connection.close()


def _purge_stale(connection: sqlite3.Connection) -> None:
    """清掉废弃的表与过期的设置项（表名 / 键名都是模块里的常量，不来自外部输入）。"""
    for table in LEGACY_TABLES:
        connection.execute(f"DROP TABLE IF EXISTS {table}")
    placeholders = ", ".join("?" for _ in KEPT_SETTINGS)
    connection.execute(
        f"DELETE FROM settings WHERE name NOT IN ({placeholders})", KEPT_SETTINGS
    )


def get_setting(name: str, default: str = "") -> str:
    """One stored setting, or `default` when it was never saved."""
    connection = connect()
    try:
        row = connection.execute(
            "SELECT value FROM settings WHERE name = ?", (name,)
        ).fetchone()
    finally:
        connection.close()
    return row["value"] if row else default


def set_setting(name: str, value: str) -> None:
    """Store a setting, replacing any previous value of the same name."""
    connection = connect()
    try:
        connection.execute(
            "INSERT INTO settings (name, value) VALUES (?, ?)"
            " ON CONFLICT(name) DO UPDATE SET value = excluded.value",
            (name, value),
        )
        connection.commit()
    finally:
        connection.close()
