from __future__ import annotations

"""Thin SQLite access. Deliberately no ORM — the schema is small enough to hold
in your head, and explicit SQL keeps it that way (see docs/DECISIONS.md)."""

import sqlite3
from pathlib import Path
from typing import Optional

from . import config

_SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI may create a yield-dependency connection on
    # one thread and use it on a threadpool worker. Each request still gets its own
    # connection and never shares it concurrently, so this is safe here.
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    conn.commit()


def ensure_user(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM user WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO user (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid
