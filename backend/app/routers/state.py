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


@router.get("/coverage")
def coverage(
    user: str,
    document_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    user_id = db.ensure_user(conn, user)
    return coverage_mod.coverage(conn, user_id, document_id)
