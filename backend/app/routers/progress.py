from __future__ import annotations

"""Progress read: one endpoint, everything derived at read time."""

import sqlite3

from fastapi import APIRouter, Depends

from .. import db
from ..core import progress as progress_mod
from ..runtime import get_conn

router = APIRouter()


@router.get("/progress")
def progress(user: str, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    user_id = db.ensure_user(conn, user)
    return {"user": user, **progress_mod.progress(conn, user_id)}
