"""SQLite 数据层：建表 / 迁移、按设备隔离，以及倒数日与设置的读写。

待办（todos）那一版已经整体删掉了：`init_db` 会把老库里遗留的 `todos` 表删掉
（见 LEGACY_TABLES），代码里不再有任何待办相关的表、字段与读写。
"""

import calendar
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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

# 倒数日带一列 `owner`：**这份数据属于哪台设备**（值就是设备主键，见 `data_owner`）。
# 读写一律带 `owner = 当前设备` —— 换台设备就是另一份清单。settings 不带 owner：
# 通知渠道这些是**这台设备**的配置，本来就只有一份。
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS countdowns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    due_date TEXT NOT NULL,
    cycle TEXT NOT NULL DEFAULT '不循环',
    content TEXT NOT NULL,
    bgcolor TEXT NOT NULL DEFAULT '#F1F5F9',
    owner TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

# 待办那版建过一张 `todos` 表（连同它的索引），代码里已经没有待办了 —— 启动时把
# 它们删掉，别让没人在读的数据留在库里。`DROP TABLE` 会连它自己的索引一起带走。
LEGACY_TABLES = ("todos",)

# 带上 owner 的索引**不能写在 SCHEMA 里**：老库的 `countdowns` 还没有这一列，
# `executescript` 会在建索引那句上直接报 `no such column: owner`。等
# `_add_missing_columns` 把列补齐之后再建。
OWNER_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_countdowns_owner ON countdowns (owner)",
)

# 当前设备的主键 —— 启动时由 main.py 问一次设备信息填进来（见 tools/device.py）。
# 空串是合法的：Android / Web 上拿不到设备标识，那时所有数据都落在 `owner = ''` 那一堆
# 里，等于"默认那一份"，照样能用（只有一个用户，也就不存在隔离问题）。
_owner = {"value": ""}

# "老数据已经认领过了"的标记：见 set_data_owner —— 认领只能做一次。
_ADOPTED_SETTING = "owner_adopted"

# 倒数日的循环周期: the value stored in `countdowns.cycle`. 后端只认其中 5 档，
# 收发两端的映射见 api/member_countdowns.py；`next_occurrence` 拿这个元组判断
# 一条倒数日是不是循环的。
DEFAULT_CYCLE = "不循环"
# 两个「跳着来」的周期：工作日只落在周一..周五，非工作日只落在周六 / 周日。
# 它们不是「隔几天一次」，所以由 `_keeps_weekday` 处理。
WORKDAY_CYCLE = "工作日"
WEEKEND_CYCLE = "非工作日"
SKIP_CYCLES = (WORKDAY_CYCLE, WEEKEND_CYCLE)
REPEAT_CYCLES = (
    DEFAULT_CYCLE,
    "每天",
    "三天",
    "一周",
    WORKDAY_CYCLE,
    WEEKEND_CYCLE,
    "一月",
    "三月",
    "六月",
    "一年",
)

# Columns added after the countdowns table shipped. `init_db` adds any that a
# database is still missing, so an existing dailylist.db keeps up with SCHEMA
# without a separate migration step.
ADDED_COLUMNS = (
    ("countdowns", "bgcolor", "TEXT NOT NULL DEFAULT '#F1F5F9'"),
    ("countdowns", "owner", "TEXT NOT NULL DEFAULT ''"),
)

_MONTH_STEPS = {"一月": 1, "三月": 3, "六月": 6, "一年": 12}
_DAY_STEPS = {"每天": 1, "三天": 3, "一周": 7}


def next_occurrence(start: date, cycle: str, on_or_after: date) -> date:
    """First date of `start`'s cycle series that is not before `on_or_after`.

    不循环 keeps its single date (even a past one), while 每天/一周/每年… walk
    forward from the anchor so a birthday stays a birthday every year. The step
    count is estimated first, then nudged, so an anchor decades old still
    resolves in a couple of iterations.
    """
    if cycle not in REPEAT_CYCLES or cycle == DEFAULT_CYCLE:
        return start
    if cycle in SKIP_CYCLES:
        # 工作日 / 非工作日：从这天起往后找第一个属于该周期的日子。
        day = max(start, on_or_after)
        while not _keeps_weekday(cycle, day):
            day += timedelta(days=1)
        return day
    if start >= on_or_after:
        return start
    day_step = _DAY_STEPS.get(cycle)
    if day_step:
        steps = (on_or_after - start).days // day_step
    else:
        months = _MONTH_STEPS.get(cycle, 1)
        steps = (
            (on_or_after.year - start.year) * 12
            + on_or_after.month
            - start.month
        ) // months
    steps = max(0, steps - 1)
    while _shift(start, cycle, steps) < on_or_after:
        steps += 1
    return _shift(start, cycle, steps)


def _keeps_weekday(cycle: str, day: date) -> bool:
    """工作日 keeps 周一..周五, 非工作日 keeps 周六 / 周日."""
    return day.weekday() < 5 if cycle == WORKDAY_CYCLE else day.weekday() >= 5


def _shift(start: date, repeat_cycle: str, steps: int) -> date:
    """The day `steps` cycles after `start`.

    Month steps count from `start` rather than from the previous occurrence, so
    a countdown on the 31st stays on the 31st (clamping only in short months)
    instead of drifting to the 28th for good.
    """
    day_step = _DAY_STEPS.get(repeat_cycle)
    if day_step:
        return start + timedelta(days=day_step * steps)
    months = _MONTH_STEPS.get(repeat_cycle, 0)
    if months == 0:
        return start
    month_index = start.month - 1 + months * steps
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


@dataclass(frozen=True)
class Countdown:
    """一个倒数日: the anchor date, the repeat cycle and what it counts down to.

    页面上真正读的是 tools/countdown_store.py 里那个同名字段结构的 dataclass
    （数据来自后端）；这一个描述的是库里那一行。
    """

    id: int
    due_date: date
    cycle: str
    content: str
    # The card's own background, picked when the countdown is added.
    bgcolor: str = "#F1F5F9"


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect()
    try:
        connection.executescript(SCHEMA)
        _drop_legacy_tables(connection)
        _add_missing_columns(connection)
        _create_owner_indexes(connection)
        connection.commit()
    finally:
        connection.close()


def data_owner() -> str:
    """这份数据属于哪台设备：本机的倒数日都按它隔开。"""
    return _owner["value"]


def set_data_owner(key: str) -> int:
    """记下当前设备的键，返回**认领了几行老数据**。

    加 `owner` 这一版之前存下来的行，`owner` 是空串 —— 第一次用这个版本打开库时把它们
    认过来（不认领的话，升级之后那些倒数日一条都看不见）。

    **认领只做一次**，靠 `owner_adopted` 这个标记把门。空串除了表示"还没迁移的老数据"，
    还兼着 Android / Web 那份数据的键（那两个平台拿不到设备标识，见 tools/device.py）：
    不把门的话，Android 上攒了一堆数据、下次换台电脑打开，那批数据就被认领走了 ——
    它可不是"没人要的老数据"，它是有主的。所以**第一次调用的"这一版"启动就算迁移过**
    （哪怕那次没拿到设备键，标记照打）—— 老数据留在空串下，Android 自己反而看得见。
    """
    _owner["value"] = key
    if get_setting(_ADOPTED_SETTING, ""):
        return 0
    connection = connect()
    try:
        adopted = 0
        if key:
            cursor = connection.execute(
                "UPDATE countdowns SET owner = ? WHERE owner = ''", (key,)
            )
            adopted += max(0, int(cursor.rowcount))
        connection.execute(
            "INSERT INTO settings (name, value) VALUES (?, '1')"
            " ON CONFLICT(name) DO UPDATE SET value = '1'",
            (_ADOPTED_SETTING,),
        )
        connection.commit()
        return adopted
    finally:
        connection.close()


def _drop_legacy_tables(connection: sqlite3.Connection) -> None:
    """删掉上一版留下的表（见 LEGACY_TABLES）。老库里没有就是空转。"""
    for table in LEGACY_TABLES:
        connection.execute(f"DROP TABLE IF EXISTS {table}")


def _create_owner_indexes(connection: sqlite3.Connection) -> None:
    """补建 owner 上的索引 —— 得等列补齐之后才建（见 OWNER_INDEXES）。"""
    for statement in OWNER_INDEXES:
        connection.execute(statement)


def clear_countdowns() -> int:
    """Delete every 倒数日 row **of this device**, returning how many went."""
    connection = connect()
    try:
        cursor = connection.execute(
            "DELETE FROM countdowns WHERE owner = ?", (data_owner(),)
        )
        connection.commit()
        return int(cursor.rowcount)
    finally:
        connection.close()


def replace_data(
    countdowns: list[dict],
    settings: dict[str, str] | None = None,
) -> tuple[int, int]:
    """导入用：清空倒数日，再把这批记录写进去。

    三个要点：
    - 记录是**原样**写的：`cycle` 直接存、不做任何推算。导入的每一行本来就是结果行，
      展开一次就不再是原来那条。
    - `settings` 是逐条覆盖、**不清空**：那张表里还放着通知渠道之类的配置，导入文件
      里没有的键不该被抹掉。
    - 全程一个连接、一个事务：几千行逐条写要开几千次连接，而且中途出错会留下半截
      数据；这里要么全进、要么全不进。

    返回 `(写了几个倒数日, 覆盖了几个设置)`。

    **只动本机的那些行**：导入是"把这批记录换进我这台设备的清单"，别人那边的数据一条
    都不能碰。
    """
    created_at = _now()
    owner = data_owner()
    connection = connect()
    try:
        connection.execute("DELETE FROM countdowns WHERE owner = ?", (owner,))
        for item in countdowns:
            connection.execute(
                "INSERT INTO countdowns (due_date, cycle, content, bgcolor,"
                " owner, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item["due_date"],
                    item.get("cycle", DEFAULT_CYCLE),
                    item["content"],
                    item.get("bgcolor", "#F1F5F9"),
                    owner,
                    created_at,
                ),
            )
        written_settings = 0
        for name, value in (settings or {}).items():
            connection.execute(
                "INSERT INTO settings (name, value) VALUES (?, ?)"
                " ON CONFLICT(name) DO UPDATE SET value = excluded.value",
                (name, value),
            )
            written_settings += 1
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return len(countdowns), written_settings


def add_countdown(
    due_date: date,
    content: str,
    cycle: str = DEFAULT_CYCLE,
    bgcolor: str = "#F1F5F9",
) -> int:
    """Add a 倒数日 row and return its id."""
    connection = connect()
    try:
        cursor = connection.execute(
            "INSERT INTO countdowns (due_date, cycle, content, bgcolor,"
            " owner, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                due_date.isoformat(),
                cycle,
                content,
                bgcolor,
                data_owner(),
                _now(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def list_countdowns() -> list[Countdown]:
    """本机的倒数日, oldest anchor first; the page sorts by the countdown."""
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, due_date, cycle, content, bgcolor FROM countdowns"
            " WHERE owner = ? ORDER BY id",
            (data_owner(),),
        ).fetchall()
    finally:
        connection.close()
    return [
        Countdown(
            id=row["id"],
            due_date=date.fromisoformat(row["due_date"]),
            cycle=row["cycle"],
            content=row["content"],
            bgcolor=row["bgcolor"],
        )
        for row in rows
    ]


def delete_countdown(countdown_id: int) -> None:
    connection = connect()
    try:
        connection.execute(
            "DELETE FROM countdowns WHERE id = ? AND owner = ?",
            (countdown_id, data_owner()),
        )
        connection.commit()
    finally:
        connection.close()


def get_countdown(countdown_id: int) -> Countdown | None:
    connection = connect()
    try:
        row = connection.execute(
            "SELECT id, due_date, cycle, content, bgcolor FROM countdowns"
            " WHERE id = ? AND owner = ?",
            (countdown_id, data_owner()),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return Countdown(
        id=row["id"],
        due_date=date.fromisoformat(row["due_date"]),
        cycle=row["cycle"],
        content=row["content"],
        bgcolor=row["bgcolor"],
    )


def update_countdown(
    countdown_id: int,
    due_date: date,
    content: str,
    cycle: str = DEFAULT_CYCLE,
    bgcolor: str = "#F1F5F9",
) -> None:
    """Edit a 倒数日. Its 周期 is a rule on this one row, so nothing else follows."""
    connection = connect()
    try:
        connection.execute(
            "UPDATE countdowns SET due_date = ?, content = ?, cycle = ?,"
            " bgcolor = ? WHERE id = ? AND owner = ?",
            (
                due_date.isoformat(),
                content,
                cycle,
                bgcolor,
                countdown_id,
                data_owner(),
            ),
        )
        connection.commit()
    finally:
        connection.close()


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


def list_settings() -> dict[str, str]:
    """settings 表里的全部键值 —— 导出数据用。"""
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT name, value FROM settings ORDER BY name"
        ).fetchall()
    finally:
        connection.close()
    return {row["name"]: row["value"] for row in rows}


def _add_missing_columns(connection: sqlite3.Connection) -> None:
    """Bring an already-created countdowns table up to SCHEMA, column by column."""
    for table, column, definition in ADDED_COLUMNS:
        existing = {
            row["name"] for row in connection.execute(f"PRAGMA table_info({table})")
        }
        if column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
