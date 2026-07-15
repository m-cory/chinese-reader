from __future__ import annotations

"""Simplified <-> traditional conversion (OpenCC).

Traditional is our canonical key, so `to_trad` is the important direction. It is
also the *safer* direction: traditional -> simplified is deterministic, while the
reverse (simplified -> traditional) has genuine one-to-many cases (发 -> 髮/發)
that OpenCC resolves by best-guess and that the Phase-3 correction layer will own.
"""

from functools import lru_cache
from typing import Optional

_t2s = None
_s2t = None


def _converters():
    global _t2s, _s2t
    if _t2s is None:
        try:
            from opencc import OpenCC

            _t2s = OpenCC("t2s")
            _s2t = OpenCC("s2t")
        except Exception:
            _t2s = False
            _s2t = False
    return _t2s, _s2t


@lru_cache(maxsize=100_000)
def to_simp(text: str) -> str:
    t2s, _ = _converters()
    return t2s.convert(text) if t2s else text


@lru_cache(maxsize=100_000)
def to_trad(text: str) -> str:
    _, s2t = _converters()
    return s2t.convert(text) if s2t else text


def to_script(text: str, script: str) -> str:
    if script == "simp":
        return to_simp(text)
    if script == "trad":
        return to_trad(text)
    return text
