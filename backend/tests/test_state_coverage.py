from __future__ import annotations

import pathlib
import tempfile

from app import db
from app.core import coverage as coverage_mod
from app.core import state as state_mod
from app.language.base import Token


def _fresh_db():
    p = pathlib.Path(tempfile.mkdtemp(prefix="cr-sc-")) / "t.db"
    conn = db.connect(p)
    db.init_db(conn)
    return conn


def _word(trad, simp=None):
    return Token(surface=simp or trad, is_word=True, trad=trad, simp=simp or trad,
                 pinyin="x", gloss="x")


def test_tap_sets_learning_and_resets_streak():
    conn = _fresh_db()
    uid = db.ensure_user(conn, "alex")
    wid = state_mod.get_or_create_word(conn, _word("今天", "今天"))
    # accumulate a no-tap streak, then a tap wipes it
    state_mod.record_exposures(conn, uid, [wid], session="s1")
    state_mod.record_exposures(conn, uid, [wid], session="s2")
    state_mod.record_tap(conn, uid, wid)
    row = conn.execute(
        "SELECT status, taps, clean_streak FROM user_word_state WHERE user_id=? AND word_id=?",
        (uid, wid),
    ).fetchone()
    assert row["status"] == "learning"
    assert row["taps"] == 1
    assert row["clean_streak"] == 0


def test_passive_promotion_needs_distinct_sessions():
    conn = _fresh_db()
    uid = db.ensure_user(conn, "alex")
    wid = state_mod.get_or_create_word(conn, _word("咖啡", "咖啡"))
    # Repeating the SAME session many times is one signal, not many: the streak
    # advances to 1 and stays there.
    for _ in range(5):
        state_mod.record_exposures(conn, uid, [wid], session="s1", promote_after=3)
    assert state_mod.status_map(conn, uid).get(wid) != "known"
    row = conn.execute(
        "SELECT clean_streak FROM user_word_state WHERE user_id=? AND word_id=?", (uid, wid)
    ).fetchone()
    assert row["clean_streak"] == 1

    # Two more DISTINCT sessions reaches the threshold of 3 and promotes.
    assert state_mod.record_exposures(conn, uid, [wid], session="s2", promote_after=3) == 0
    assert state_mod.record_exposures(conn, uid, [wid], session="s3", promote_after=3) == 1
    assert state_mod.status_map(conn, uid).get(wid) == "known"


def test_override():
    conn = _fresh_db()
    uid = db.ensure_user(conn, "mei")
    wid = state_mod.get_or_create_word(conn, _word("生活", "生活"))
    state_mod.override(conn, uid, wid, "known")
    assert state_mod.status_map(conn, uid).get(wid) == "known"


def test_coverage_and_routing():
    conn = _fresh_db()
    uid = db.ensure_user(conn, "alex")
    # a 4-word document
    words = ["今天", "咖啡", "生活", "美好"]
    wids = [state_mod.get_or_create_word(conn, _word(w)) for w in words]
    cur = conn.execute("INSERT INTO document (title) VALUES ('doc')")
    doc_id = cur.lastrowid
    for i, wid in enumerate(wids):
        conn.execute(
            "INSERT INTO document_token (document_id, ord, surface, word_id, is_word) VALUES (?,?,?,?,1)",
            (doc_id, i, words[i], wid),
        )
    conn.commit()

    cov = coverage_mod.coverage(conn, uid, doc_id)
    assert cov == {"document_id": doc_id, "known": 0, "total": 4, "pct": 0.0}

    state_mod.override(conn, uid, wids[0], "known")
    state_mod.override(conn, uid, wids[1], "known")
    cov = coverage_mod.coverage(conn, uid, doc_id)
    assert cov["known"] == 2 and cov["pct"] == 0.5

    ranked = coverage_mod.rank_next(conn, uid)
    assert ranked[0]["document_id"] == doc_id
