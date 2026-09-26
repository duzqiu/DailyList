import calendar
import os
import sqlite3
from collections.abc import Iterable
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

SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    due_date TEXT NOT NULL,
    due_time TEXT NOT NULL DEFAULT '',
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

CREATE TABLE IF NOT EXISTS countdowns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    due_date TEXT NOT NULL,
    cycle TEXT NOT NULL DEFAULT '不循环',
    content TEXT NOT NULL,
    bgcolor TEXT NOT NULL DEFAULT '#F1F5F9',
    created_at TEXT NOT NULL
);
"""

# 待办的循环周期: the value stored in `todos.repeat_cycle`.
DEFAULT_CYCLE = "不循环"
REPEAT_CYCLES = (
    DEFAULT_CYCLE,
    "每天",
    "三天",
    "一周",
    "一月",
    "三月",
    "六月",
    "一年",
)
# A repeating todo is materialised one cycle at a time up to this far ahead, so
# the home and calendar windows always have their rows without a background job.
REPEAT_HORIZON_DAYS = 365
# Safety net for denser cycles: 每天 needs 366 rows for the whole horizon.
MAX_OCCURRENCES = 400

# Columns added after the todos table shipped. `init_db` adds any that a database
# is still missing, so an existing dailylist.db keeps up with SCHEMA without a
# separate migration step.
ADDED_COLUMNS = (
    ("todos", "repeat_cycle", "TEXT NOT NULL DEFAULT '不循环'"),
    ("todos", "due_time", "TEXT NOT NULL DEFAULT ''"),
    ("countdowns", "bgcolor", "TEXT NOT NULL DEFAULT '#F1F5F9'"),
)

# The dialog opens on the current clock, rounded down to this many minutes so the
# default reads as a round number.
DEFAULT_TIME_STEP_MINUTES = 5

_MONTH_STEPS = {"一月": 1, "三月": 3, "六月": 6, "一年": 12}
_DAY_STEPS = {"每天": 1, "三天": 3, "一周": 7}


def next_occurrence(start: date, cycle: str, on_or_after: date) -> date:
    """First date of `start`'s cycle series that is not before `on_or_after`.

    倒数日 reuse the todo cycles: 不循环 keeps its single date (even a past one),
    while 每天/一周/每年… walk forward from the anchor so a birthday stays a
    birthday every year. The step count is estimated first, then nudged, so an
    anchor decades old still resolves in a couple of iterations.
    """
    if cycle not in REPEAT_CYCLES or cycle == DEFAULT_CYCLE:
        return start
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


def default_time(now: datetime | None = None) -> str:
    """The 时间 the add-todo dialog starts on: the clock rounded down a step."""
    moment = now or datetime.now()
    minute = moment.minute - moment.minute % DEFAULT_TIME_STEP_MINUTES
    return f"{moment.hour:02d}:{minute:02d}"


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
        if current > last or len(dates) >= MAX_OCCURRENCES:
            return dates
        dates.append(current)


def _shift(start: date, repeat_cycle: str, steps: int) -> date:
    """The day `steps` cycles after `start`.

    Month steps count from `start` rather than from the previous occurrence, so a
    todo on the 31st stays on the 31st (clamping only in short months) instead of
    drifting to the 28th for good.
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
class Todo:
    id: int
    due_date: date
    category: str
    content: str
    done: bool
    repeat_cycle: str
    # "HH:MM" for todos that carry a time of day; empty for rows created before
    # the 时间 field existed.
    due_time: str = ""


@dataclass(frozen=True)
class Countdown:
    """一个倒数日: the anchor date, the repeat cycle and what it counts down to."""

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
        _add_missing_columns(connection)
        connection.commit()
    finally:
        connection.close()


def add_todo(
    due_date: date,
    category: str,
    content: str,
    repeat_cycle: str = DEFAULT_CYCLE,
    due_time: str = "",
) -> int:
    """Add a todo and return the id of its first row.

    A repeating `repeat_cycle` also schedules the follow-ups: one row per cycle
    from `due_date` up to `REPEAT_HORIZON_DAYS` ahead, each carrying the same
    cycle and time of day, so the series stays recognisable.
    """
    created_at = _now()
    connection = connect()
    try:
        first_id = 0
        for day in occurrence_dates(due_date, repeat_cycle):
            cursor = connection.execute(
                "INSERT INTO todos (due_date, due_time, category, content,"
                " repeat_cycle, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    day.isoformat(),
                    due_time,
                    category,
                    content,
                    repeat_cycle,
                    created_at,
                ),
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


def get_todo(todo_id: int) -> Todo | None:
    connection = connect()
    try:
        row = connection.execute(
            "SELECT id, due_date, due_time, category, content, done,"
            " repeat_cycle FROM todos WHERE id = ?",
            (todo_id,),
        ).fetchone()
    finally:
        connection.close()
    return _to_todo(row) if row else None


def todo_series(todo_id: int) -> list[Todo]:
    """Every row of the repeating series `todo_id` belongs to, oldest first.

    A repeating 待办 materialises one row per occurrence; the rows of one series
    were inserted in the same call, so they share `created_at`, `repeat_cycle`
    and content. A 不循环 todo is a series of one.
    """
    todo = get_todo(todo_id)
    if todo is None:
        return []
    connection = connect()
    try:
        row = connection.execute(
            "SELECT created_at FROM todos WHERE id = ?", (todo_id,)
        ).fetchone()
        if todo.repeat_cycle == DEFAULT_CYCLE:
            return [todo]
        rows = connection.execute(
            "SELECT id, due_date, due_time, category, content, done,"
            " repeat_cycle FROM todos WHERE created_at = ? AND repeat_cycle = ?"
            " AND content = ? ORDER BY due_date, id",
            (row["created_at"], todo.repeat_cycle, todo.content),
        ).fetchall()
    finally:
        connection.close()
    return [_to_todo(r) for r in rows]


def update_todo(
    todo_id: int,
    due_date: date,
    category: str,
    content: str,
    repeat_cycle: str = DEFAULT_CYCLE,
    due_time: str = "",
) -> int:
    """Edit one 待办, keeping its whole cycle in step. Returns rows written.

    The edited row may be any occurrence of a repeating series, so the series is
    rebuilt from its own anchor shifted by however far the edited day moved -
    editing the 5th of a daily series to the 6th moves the whole series by one
    day. Occurrences that were already done stay done (matched by their place in
    the series, so a shift keeps the ticks), and a 不循环 todo simply becomes its
    single edited row.
    """
    todo = get_todo(todo_id)
    if todo is None:
        return 0
    series = todo_series(todo_id) or [todo]
    done_places = {index for index, item in enumerate(series) if item.done}
    anchor = min(item.due_date for item in series)
    start = due_date - (todo.due_date - anchor)
    ids = [item.id for item in series]
    created_at = _now()
    connection = connect()
    try:
        placeholders = ", ".join("?" for _ in ids)
        connection.execute(f"DELETE FROM todos WHERE id IN ({placeholders})", ids)
        written = 0
        for place, day in enumerate(occurrence_dates(start, repeat_cycle)):
            connection.execute(
                "INSERT INTO todos (due_date, due_time, category, content, done,"
                " repeat_cycle, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    day.isoformat(),
                    due_time,
                    category,
                    content,
                    1 if place in done_places else 0,
                    repeat_cycle,
                    created_at,
                ),
            )
            written += 1
        connection.commit()
        return written
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
            " created_at) VALUES (?, ?, ?, ?, ?)",
            (due_date.isoformat(), cycle, content, bgcolor, _now()),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def list_countdowns() -> list[Countdown]:
    """Every 倒数日, oldest anchor first; the page sorts by the countdown."""
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, due_date, cycle, content, bgcolor FROM countdowns"
            " ORDER BY id"
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
            "DELETE FROM countdowns WHERE id = ?", (countdown_id,)
        )
        connection.commit()
    finally:
        connection.close()


def get_countdown(countdown_id: int) -> Countdown | None:
    connection = connect()
    try:
        row = connection.execute(
            "SELECT id, due_date, cycle, content, bgcolor FROM countdowns"
            " WHERE id = ?",
            (countdown_id,),
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
            " bgcolor = ? WHERE id = ?",
            (due_date.isoformat(), content, cycle, bgcolor, countdown_id),
        )
        connection.commit()
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
            "SELECT id, due_date, due_time, category, content, done, repeat_cycle"
            " FROM todos"
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
            "SELECT id, due_date, due_time, category, content, done, repeat_cycle"
            " FROM todos"
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
        due_time=row["due_time"],
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
