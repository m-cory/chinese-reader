from __future__ import annotations

"""Coverage = the fraction of a document's word-tokens the user already knows.
This is the engine that (a) routes "next text" and (b) later turns any natural
web text into a graded text, per user — the same essay scores differently for
each reader, all emergent from user_word_state, never hard-coded.
"""

import sqlite3
from typing import List, Optional

from .. import config
from . import state as state_mod


def coverage(conn: sqlite3.Connection, user_id: int, document_id: int) -> dict:
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM document_token WHERE document_id = ? AND is_word = 1",
        (document_id,),
    ).fetchone()["n"]
    if total == 0:
        return {"document_id": document_id, "known": 0, "total": 0, "pct": 0.0}

    statuses = state_mod.status_map(conn, user_id)
    rows = conn.execute(
        "SELECT word_id FROM document_token WHERE document_id = ? AND is_word = 1",
        (document_id,),
    ).fetchall()
    known = sum(1 for r in rows if statuses.get(r["word_id"]) == "known")
    return {
        "document_id": document_id,
        "known": known,
        "total": total,
        "pct": round(known / total, 4),
    }


def rank_next(
    conn: sqlite3.Connection,
    user_id: int,
    target: Optional[float] = None,
) -> List[dict]:
    """Rank documents by how close their coverage sits to the target band —
    slightly above comfort, ~90-95% known. Closest first."""
    tgt = target if target is not None else config.COVERAGE_TARGET
    docs = conn.execute("SELECT id, title FROM document ORDER BY id").fetchall()
    scored = []
    for d in docs:
        cov = coverage(conn, user_id, d["id"])
        scored.append(
            {
                "document_id": d["id"],
                "title": d["title"],
                "pct": cov["pct"],
                "known": cov["known"],
                "total": cov["total"],
                "distance": round(abs(cov["pct"] - tgt), 4),
            }
        )
    scored.sort(key=lambda s: s["distance"])
    return scored
