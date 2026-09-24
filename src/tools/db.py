import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "dailylist.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    due_date TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos (due_date);
"""


@dataclass(frozen=True)
class Todo:
    id: int
    due_date: date
    category: str
    content: str
    done: bool


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    connection = connect()
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def add_todo(due_date: date, category: str, content: str) -> int:
    connection = connect()
    try:
        cursor = connection.execute(
            "INSERT INTO todos (due_date, category, content, created_at)"
            " VALUES (?, ?, ?, ?)",
            (due_date.isoformat(), category, content, _now()),
        )
        connection.commit()
        return int(cursor.lastrowid)
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
            "SELECT id, due_date, category, content, done FROM todos"
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
            "SELECT id, due_date, category, content, done FROM todos"
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


def _to_todo(row: sqlite3.Row) -> Todo:
    return Todo(
        id=row["id"],
        due_date=date.fromisoformat(row["due_date"]),
        category=row["category"],
        content=row["content"],
        done=bool(row["done"]),
    )


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
