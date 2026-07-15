from __future__ import annotations

"""Process-wide singletons and the per-request DB dependency.

The language module (dictionary + jieba) is built once and shared read-only; a
fresh SQLite connection is opened per request (SQLite objects aren't meant to
cross threads, and FastAPI runs sync endpoints in a threadpool).
"""

from typing import Iterator

from . import db
from .language.base import LanguageModule
from .language.chinese import build_default

_module: LanguageModule = None  # type: ignore[assignment]


def language() -> LanguageModule:
    global _module
    if _module is None:
        _module = build_default()
    return _module


def get_conn() -> Iterator["db.sqlite3.Connection"]:
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()
