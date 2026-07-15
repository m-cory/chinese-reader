from __future__ import annotations

"""Behavior-driven word state — the "no grading ritual" model.

  - A TAP means "not yet": the word becomes (at least) `learning` and its no-tap
    streak resets. Tapping is the only explicit signal the reader ever gives.
  - EXPOSURE without a tap, across enough *distinct sessions*, passively promotes
    a word to `known`. We count distinct sessions (not raw repeats) on purpose:
    seeing the same word five times in one sitting is one signal, not five, and
    that guards against promoting a word the reader merely skimmed past.
  - A long-press OVERRIDE sets status directly, for when behavior misleads.
"""

import sqlite3
from typing import Iterable, Optional

from .. import config
from ..language.base import Token

STATUSES = ("new", "learning", "known")


def get_or_create_word(conn: sqlite3.Connection, token: Token) -> Optional[int]:
    """Upsert a word by its canonical (traditional) key. Returns word_id, or
    None for non-word tokens."""
    if not token.is_word or not token.trad:
        return None
    row = conn.execute("SELECT id FROM word WHERE trad = ?", (token.trad,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO word (trad, simp, pinyin, gloss) VALUES (?, ?, ?, ?)",
        (token.trad, token.simp or token.trad, token.pinyin, token.gloss),
    )
    return cur.lastrowid


def _state_row(conn: sqlite3.Connection, user_id: int, word_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM user_word_state WHERE user_id = ? AND word_id = ?",
        (user_id, word_id),
    ).fetchone()
    if row:
        return row
    conn.execute(
        "INSERT INTO user_word_state (user_id, word_id) VALUES (?, ?)",
        (user_id, word_id),
    )
    return conn.execute(
        "SELECT * FROM user_word_state WHERE user_id = ? AND word_id = ?",
        (user_id, word_id),
    ).fetchone()


def record_tap(conn: sqlite3.Connection, user_id: int, word_id: int) -> str:
    """A tap = 'not yet'. Move to at least `learning`, reset the no-tap streak."""
    _state_row(conn, user_id, word_id)
    conn.execute(
        """UPDATE user_word_state
              SET status = 'learning',
                  taps = taps + 1,
                  clean_streak = 0,
                  promoted_at = NULL,
                  last_seen_at = datetime('now')
            WHERE user_id = ? AND word_id = ?""",
        (user_id, word_id),
    )
    conn.commit()
    return "learning"


def record_exposures(
    conn: sqlite3.Connection,
    user_id: int,
    word_ids: Iterable[int],
    session: str,
    promote_after: Optional[int] = None,
) -> int:
    """Register that these words were on screen this session (no tap). Returns the
    number of words that promoted to `known` as a result."""
    threshold = promote_after if promote_after is not None else config.PROMOTE_AFTER
    promoted = 0
    for word_id in word_ids:
        row = _state_row(conn, user_id, word_id)
        if row["status"] == "known":
            continue
        # Only a *new* session advances the streak.
        if row["last_session"] == session:
            continue
        streak = row["clean_streak"] + 1
        if streak >= threshold:
            conn.execute(
                """UPDATE user_word_state
                      SET status = 'known', clean_streak = ?, last_session = ?,
                          promoted_at = datetime('now'), last_seen_at = datetime('now')
                    WHERE user_id = ? AND word_id = ?""",
                (streak, session, user_id, word_id),
            )
            promoted += 1
        else:
            conn.execute(
                """UPDATE user_word_state
                      SET clean_streak = ?, last_session = ?, last_seen_at = datetime('now')
                    WHERE user_id = ? AND word_id = ?""",
                (streak, session, user_id, word_id),
            )
    conn.commit()
    return promoted


def override(conn: sqlite3.Connection, user_id: int, word_id: int, status: str) -> str:
    """Manual escape hatch (long-press). status must be one of STATUSES."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
    _state_row(conn, user_id, word_id)
    conn.execute(
        """UPDATE user_word_state
              SET status = ?, clean_streak = 0,
                  promoted_at = CASE WHEN ? = 'known' THEN datetime('now') ELSE NULL END,
                  last_seen_at = datetime('now')
            WHERE user_id = ? AND word_id = ?""",
        (status, status, user_id, word_id),
    )
    conn.commit()
    return status


def status_map(conn: sqlite3.Connection, user_id: int) -> dict:
    """word_id -> status for this user (unseen words are implicitly 'new')."""
    rows = conn.execute(
        "SELECT word_id, status FROM user_word_state WHERE user_id = ?", (user_id,)
    ).fetchall()
    return {r["word_id"]: r["status"] for r in rows}
