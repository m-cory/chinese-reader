from __future__ import annotations

"""The content library: ingest a document (paste or file upload), list, and route
the next text by per-user coverage."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .. import content, db
from ..core import coverage as coverage_mod
from ..core import state as state_mod
from ..runtime import get_conn, language

router = APIRouter()


def _store_document(conn: sqlite3.Connection, title: str, text: str, source: str) -> dict:
    tokens = language().segment(text)
    cur = conn.execute(
        "INSERT INTO document (title, source_type) VALUES (?, ?)", (title, source)
    )
    doc_id = cur.lastrowid
    n_words = 0
    for ord_, tok in enumerate(tokens):
        word_id = state_mod.get_or_create_word(conn, tok)
        if word_id:
            n_words += 1
        conn.execute(
            "INSERT INTO document_token (document_id, ord, surface, word_id, is_word) "
            "VALUES (?, ?, ?, ?, ?)",
            (doc_id, ord_, tok.surface, word_id, 1 if tok.is_word else 0),
        )
    conn.commit()
    return {"id": doc_id, "title": title, "tokens": len(tokens), "words": n_words}


class DocIn(BaseModel):
    title: str
    text: str


@router.post("/documents")
def add_document(body: DocIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    return _store_document(conn, body.title.strip() or "Untitled", body.text, "paste")


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    raw = await file.read()
    try:
        text = content.ingest(file.filename or "", raw)
    except ValueError as e:
        raise HTTPException(415, str(e))
    if not text.strip():
        raise HTTPException(422, "no readable text extracted from file")
    return _store_document(conn, title or (file.filename or "Untitled"), text, "upload")


@router.get("/documents")
def list_documents(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    rows = conn.execute(
        """SELECT d.id, d.title, d.source_type, d.added_at,
                  COALESCE(SUM(dt.is_word), 0) AS words
             FROM document d
             LEFT JOIN document_token dt ON dt.document_id = d.id
            GROUP BY d.id ORDER BY d.id DESC""",
    ).fetchall()
    return {"documents": [dict(r) for r in rows]}


@router.get("/next")
def next_text(
    user: str,
    target: Optional[float] = None,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    user_id = db.ensure_user(conn, user)
    return {"ranked": coverage_mod.rank_next(conn, user_id, target)}
