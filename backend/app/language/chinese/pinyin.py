from __future__ import annotations

"""Pinyin helpers: convert CC-CEDICT's numbered pinyin ('jin1 tian1') to tone
marks ('jīntiān'), and a fallback reading for out-of-dictionary words."""

from typing import Optional

_MARKS = {
    "a": "āáǎàa",
    "e": "ēéěèe",
    "i": "īíǐìi",
    "o": "ōóǒòo",
    "u": "ūúǔùu",
    "ü": "ǖǘǚǜü",
}


def _mark_syllable(syl: str) -> str:
    # CC-CEDICT writes ü as "u:"; some sources use "v".
    s = syl.replace("u:", "ü").replace("U:", "Ü").replace("v", "ü")
    tone = 5
    if s and s[-1] in "12345":
        tone = int(s[-1])
        s = s[:-1]
    if tone == 5 or not s:
        return s
    low = s.lower()
    # Standard placement: a and e always take the mark; in 'ou' the o does;
    # otherwise the last vowel takes it.
    for v in ("a", "e"):
        if v in low:
            i = low.index(v)
            return s[:i] + _MARKS[v][tone - 1] + s[i + 1:]
    if "ou" in low:
        i = low.index("o")
        return s[:i] + _MARKS["o"][tone - 1] + s[i + 1:]
    for i in range(len(low) - 1, -1, -1):
        if low[i] in _MARKS:
            return s[:i] + _MARKS[low[i]][tone - 1] + s[i + 1:]
    return s


def numbered_to_marks(pinyin: str, join: str = "") -> str:
    """'jin1 tian1' -> 'jīntiān'. `join` is placed between syllables."""
    if not pinyin:
        return ""
    return join.join(_mark_syllable(p) for p in pinyin.split())


_fallback = None


def fallback_reading(word: str) -> Optional[str]:
    """Tone-marked reading for a word not in the dictionary, via pypinyin.
    Returns None if pypinyin is unavailable."""
    global _fallback
    if _fallback is None:
        try:
            from pypinyin import lazy_pinyin, Style

            _fallback = (lazy_pinyin, Style)
        except Exception:
            _fallback = False
    if not _fallback:
        return None
    lazy_pinyin, Style = _fallback
    return "".join(lazy_pinyin(word, style=Style.TONE))
