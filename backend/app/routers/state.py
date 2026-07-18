from __future__ import annotations

"""Word-state signals from the reader: tap (=not yet), batch exposures (drives
passive promotion), and long-press override. Plus a coverage read."""

import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import db
from ..core import coverage as coverage_mod
from ..core import state as state_mod
from ..runtime import get_conn

router = APIRouter()


class TapIn(BaseModel):
    user: str
    word_id: int


class ExposuresIn(BaseModel):
    user: str
    session: str
    word_ids: List[int]


class OverrideIn(BaseModel):
    user: str
    word_id: int
    status: str


@router.post("/tap")
def tap(body: TapIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    user_id = db.ensure_user(conn, body.user)
    status = state_mod.record_tap(conn, user_id, body.word_id)
    return {"word_id": body.word_id, "status": status}


@router.post("/exposures")
def exposures(body: ExposuresIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    user_id = db.ensure_user(conn, body.user)
    promoted = state_mod.record_exposures(conn, user_id, body.word_ids, body.session)
    return {"seen": len(body.word_ids), "promoted_to_known": promoted}


@router.post("/override")
def override(body: OverrideIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    user_id = db.ensure_user(conn, body.user)
    try:
        status = state_mod.override(conn, user_id, body.word_id, body.status)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"word_id": body.word_id, "status": status}


@router.get("/words")
def words(
    user: str,
    status: str = "learning",
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """This user's tracked words in one status bucket — feeds the vocab panel
    and the Anki export."""
    if status not in state_mod.STATUSES:
        raise HTTPException(400, f"status must be one of {state_mod.STATUSES}, got {status!r}")
    user_id = db.ensure_user(conn, user)
    rows = conn.execute(
        """SELECT w.id AS word_id, w.trad, w.simp, w.pinyin, w.gloss,
                  s.status, s.taps, s.last_seen_at
             FROM user_word_state s
             JOIN word w ON w.id = s.word_id
            WHERE s.user_id = ? AND s.status = ?
            ORDER BY s.last_seen_at DESC, w.id DESC""",
        (user_id, status),
    ).fetchall()
    return {"status": status, "words": [dict(r) for r in rows]}


@router.get("/coverage")
def coverage(
    user: str,
    document_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    user_id = db.ensure_user(conn, user)
    return coverage_mod.coverage(conn, user_id, document_id)
