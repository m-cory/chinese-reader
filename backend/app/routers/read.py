from __future__ import annotations

"""The reading surface's data: stateless segmentation, and per-user document reads."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import db
from ..core import state as state_mod
from ..runtime import get_conn, language

router = APIRouter()


class SegmentIn(BaseModel):
    text: str


@router.post("/segment")
def segment(body: SegmentIn) -> dict:
    """Segment raw text into tappable tokens with pinyin + gloss. Stateless — no
    user, no persistence. This is what the M0 reader renders."""
    tokens = language().segment(body.text)
    return {"tokens": [t.to_dict() for t in tokens]}


@router.get("/documents/{document_id}/read")
def read_document(
    document_id: int,
    user: str,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Return a stored document's tokens overlaid with this user's word status."""
    doc = conn.execute("SELECT * FROM document WHERE id = ?", (document_id,)).fetchone()
    if not doc:
        raise HTTPException(404, f"no document {document_id}")
    user_id = db.ensure_user(conn, user)
    statuses = state_mod.status_map(conn, user_id)

    rows = conn.execute(
        """SELECT dt.ord, dt.surface, dt.is_word, dt.word_id,
                  w.trad, w.simp, w.pinyin, w.gloss
             FROM document_token dt
             LEFT JOIN word w ON w.id = dt.word_id
            WHERE dt.document_id = ?
            ORDER BY dt.ord""",
        (document_id,),
    ).fetchall()

    tokens: List[dict] = []
    for r in rows:
        tokens.append(
            {
                "surface": r["surface"],
                "is_word": bool(r["is_word"]),
                "word_id": r["word_id"],
                "trad": r["trad"],
                "simp": r["simp"],
                "pinyin": r["pinyin"],
                "gloss": r["gloss"],
                "status": statuses.get(r["word_id"], "new") if r["word_id"] else None,
            }
        )
    return {"id": doc["id"], "title": doc["title"], "tokens": tokens}
