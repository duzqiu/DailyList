import calendar
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "dailylist.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    due_date TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    repeat_cycle TEXT NOT NULL DEFAULT '不循环',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos (due_date);

CREATE TABLE IF NOT EXISTS settings (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# 待办的循环周期: the value stored in `todos.repeat_cycle`.
DEFAULT_CYCLE = "不循环"
REPEAT_CYCLES = (DEFAULT_CYCLE, "三天", "一周", "一月", "三月", "六月", "一年")
# A repeating todo is materialised one cycle at a time up to this far ahead, so
# the home and calendar windows always have their rows without a background job.
REPEAT_HORIZON_DAYS = 365

# Columns added after the todos table shipped. `init_db` adds any that a database
# is still missing, so an existing dailylist.db keeps up with SCHEMA without a
# separate migration step.
ADDED_COLUMNS = (
    ("todos", "repeat_cycle", "TEXT NOT NULL DEFAULT '不循环'"),
)

_MONTH_STEPS = {"一月": 1, "三月": 3, "六月": 6, "一年": 12}


def occurrence_dates(
    start: date, repeat_cycle: str, horizon_days: int = REPEAT_HORIZON_DAYS
) -> list[date]:
    """Every 待办 date of a repeating todo: `start`, then one row per cycle.

    `不循环` is a single date. Longer steps stop at the last occurrence that still
    falls within `horizon_days` of the start.
    """
    if repeat_cycle == DEFAULT_CYCLE or repeat_cycle not in REPEAT_CYCLES:
        return [start]
    last = start + timedelta(days=horizon_days)
    dates = [start]
    steps = 0
    while True:
        steps += 1
        current = _shift(start, repeat_cycle, steps)
        if current > last:
            return dates
        dates.append(current)


def _shift(start: date, repeat_cycle: str, steps: int) -> date:
    """The day `steps` cycles after `start`.

    Month steps count from `start` rather than from the previous occurrence, so a
    todo on the 31st stays on the 31st (clamping only in short months) instead of
    drifting to the 28th for good.
    """
    if repeat_cycle == "三天":
        return start + timedelta(days=3 * steps)
    if repeat_cycle == "一周":
        return start + timedelta(days=7 * steps)
    months = _MONTH_STEPS.get(repeat_cycle, 0)
    if months == 0:
        return start
    month_index = start.month - 1 + months * steps
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


@dataclass(frozen=True)
class Todo:
    id: int
    due_date: date
    category: str
    content: str
    done: bool
    repeat_cycle: str


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    connection = connect()
    try:
        connection.executescript(SCHEMA)
        _add_missing_columns(connection)
        connection.commit()
    finally:
        connection.close()


def add_todo(
    due_date: date,
    category: str,
    content: str,
    repeat_cycle: str = DEFAULT_CYCLE,
) -> int:
    """Add a todo and return the id of its first row.

    A repeating `repeat_cycle` also schedules the follow-ups: one row per cycle
    from `due_date` up to `REPEAT_HORIZON_DAYS` ahead, each carrying the same
    cycle so the series stays recognisable.
    """
    created_at = _now()
    connection = connect()
    try:
        first_id = 0
        for day in occurrence_dates(due_date, repeat_cycle):
            cursor = connection.execute(
                "INSERT INTO todos (due_date, category, content, repeat_cycle,"
                " created_at) VALUES (?, ?, ?, ?, ?)",
                (day.isoformat(), category, content, repeat_cycle, created_at),
            )
            if not first_id:
                first_id = int(cursor.lastrowid)
        connection.commit()
        return first_id
    finally:
        connection.close()


def set_done(todo_id: int, done: bool) -> None:
    connection = connect()
    try:
        connection.execute(
            "UPDATE todos SET done = ? WHERE id = ?",
            (1 if done else 0, todo_id),
        )
        connection.commit()
    finally:
        connection.close()


def delete_todo(todo_id: int) -> None:
    connection = connect()
    try:
        connection.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        connection.commit()
    finally:
        connection.close()


def clear_todos() -> int:
    """Delete every todo row, returning how many rows were removed."""
    connection = connect()
    try:
        cursor = connection.execute("DELETE FROM todos")
        connection.commit()
        return int(cursor.rowcount)
    finally:
        connection.close()


def list_todos(days: Iterable[date]) -> list[Todo]:
    due_dates = [day.isoformat() for day in days]
    if not due_dates:
        return []
    placeholders = ", ".join("?" for _ in due_dates)
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, due_date, category, content, done, repeat_cycle FROM todos"
            f" WHERE due_date IN ({placeholders})"
            " ORDER BY due_date, id",
            due_dates,
        ).fetchall()
    finally:
        connection.close()
    return [_to_todo(row) for row in rows]


def list_range(start: date, end: date) -> list[Todo]:
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, due_date, category, content, done, repeat_cycle FROM todos"
            " WHERE due_date BETWEEN ? AND ?"
            " ORDER BY due_date, id",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    finally:
        connection.close()
    return [_to_todo(row) for row in rows]


def counts_in(
    start: date | None = None, end: date | None = None
) -> list[tuple[str, bool, int]]:
    """(category, done, count) rows, optionally limited to a due-date range."""
    query = "SELECT category, done, COUNT(*) AS count FROM todos"
    parameters: list[str] = []
    if start is not None and end is not None:
        query += " WHERE due_date BETWEEN ? AND ?"
        parameters = [start.isoformat(), end.isoformat()]
    query += " GROUP BY category, done"
    connection = connect()
    try:
        rows = connection.execute(query, parameters).fetchall()
    finally:
        connection.close()
    return [
        (row["category"], bool(row["done"]), int(row["count"])) for row in rows
    ]


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


def _to_todo(row: sqlite3.Row) -> Todo:
    return Todo(
        id=row["id"],
        due_date=date.fromisoformat(row["due_date"]),
        category=row["category"],
        content=row["content"],
        done=bool(row["done"]),
        repeat_cycle=row["repeat_cycle"],
    )


def _add_missing_columns(connection: sqlite3.Connection) -> None:
    """Bring an already-created todos table up to SCHEMA, column by column."""
    for table, column, definition in ADDED_COLUMNS:
        existing = {
            row["name"] for row in connection.execute(f"PRAGMA table_info({table})")
        }
        if column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
