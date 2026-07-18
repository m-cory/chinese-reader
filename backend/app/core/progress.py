from __future__ import annotations

"""Per-user progress: absolute counts plus the same known-set measured against
external yardsticks (HSK levels, corpus frequency bands).

Everything is derived from user_word_state at read time — no counters to keep in
sync, so it can never drift from the behavior data. Benchmarks match on the
SIMPLIFIED form: the word store's canonical key is traditional, but every word row
carries simp, and the HSK/frequency lists are simplified.

Note: the yardsticks are Chinese-specific (imported from the zh language module).
If a second language ever lands, this is the file that grows a seam — not before.
"""

import sqlite3
from typing import Dict, List, Set

from ..language.chinese import benchmarks


def _band_stats(known: Set[str], ordered: List[str], bands) -> List[dict]:
    out = []
    for band in bands:
        ref = ordered[:band]
        n = sum(1 for w in ref if w in known)
        out.append({"band": band, "known": n, "total": len(ref),
                    "pct": round(n / len(ref), 4) if ref else 0.0})
    return out


def progress(conn: sqlite3.Connection, user_id: int) -> dict:
    rows = conn.execute(
        """SELECT w.simp, s.status,
                  (s.status = 'known' AND s.promoted_at >= datetime('now', '-7 days'))
                      AS fresh
             FROM user_word_state s
             JOIN word w ON w.id = s.word_id
            WHERE s.user_id = ? AND s.status != 'new'""",
        (user_id,),
    ).fetchall()

    known: Set[str] = {r["simp"] for r in rows if r["status"] == "known"}
    learning: Set[str] = {r["simp"] for r in rows if r["status"] == "learning"}
    promoted_7d = sum(1 for r in rows if r["fresh"])

    known_chars: Set[str] = set()
    for w in known:
        known_chars |= benchmarks.han_chars(w)

    hsk: List[dict] = []
    cum_known = cum_total = 0
    estimate = 0
    for lvl, ref in benchmarks.hsk_words().items():
        n = len(known & ref)
        hsk.append({"level": lvl, "known": n, "total": len(ref),
                    "pct": round(n / len(ref), 4) if ref else 0.0})
        cum_known += n
        cum_total += len(ref)
        # "at" a level once you know >=80% of everything up to and including it
        if cum_total and cum_known / cum_total >= 0.8:
            estimate = lvl

    return {
        "words": {"known": len(known), "learning": len(learning), "promoted_7d": promoted_7d},
        "chars": {"known": len(known_chars)},
        "hsk": hsk,
        "hsk_estimate": estimate,
        "freq_words": _band_stats(known, benchmarks.top_words(max(benchmarks.WORD_BANDS)),
                                  benchmarks.WORD_BANDS),
        "freq_chars": _band_stats(known_chars, benchmarks.top_chars(max(benchmarks.CHAR_BANDS)),
                                  benchmarks.CHAR_BANDS),
    }
