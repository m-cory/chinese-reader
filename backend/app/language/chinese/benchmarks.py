from __future__ import annotations

"""External yardsticks for progress: HSK 2.0 word lists and corpus frequency
ranks. Chinese-specific by nature, so it lives with the rest of the zh module.

Two data sources, chosen to add ~zero weight:
  - HSK 2.0 levels 1-6, vendored as slim TSVs in app/data/hsk/ (~100 KB total;
    per-level *exclusive* lists, simplified + traditional per line).
  - Frequency ranks derived from jieba's bundled dictionary — jieba is already a
    core dependency, so "frequency list" costs no new data file. Its counts are
    corpus word frequencies; good enough to rank the top few thousand.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set, Tuple

_DATA = Path(__file__).resolve().parents[2] / "data"
_HSK_DIR = _DATA / "hsk"
_HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

HSK_LEVELS = (1, 2, 3, 4, 5, 6)
WORD_BANDS = (500, 1000, 2000, 5000)
CHAR_BANDS = (500, 1500, 3000)


@lru_cache(maxsize=1)
def hsk_words() -> Dict[int, Set[str]]:
    """level -> simplified headwords exclusive to that level."""
    out: Dict[int, Set[str]] = {}
    for lvl in HSK_LEVELS:
        words: Set[str] = set()
        path = _HSK_DIR / f"hsk{lvl}.tsv"
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line and not line.startswith("#"):
                    words.add(line.split("\t", 1)[0])
        out[lvl] = words
    return out


def _jieba_dict_path() -> Path:
    import jieba

    return Path(jieba.__file__).resolve().parent / "dict.txt"


@lru_cache(maxsize=1)
def _frequency_tables() -> Tuple[List[str], List[str]]:
    """(top words by descending corpus frequency, top single Han chars likewise),
    sliced to the largest band reported. Loaded once, lazily (~1s)."""
    entries: List[Tuple[int, str]] = []
    with open(_jieba_dict_path(), encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and _HAN.search(parts[0]):
                try:
                    entries.append((int(parts[1]), parts[0]))
                except ValueError:
                    continue
    entries.sort(reverse=True)
    words: List[str] = []
    chars: List[str] = []
    for _freq, w in entries:
        if len(words) < max(WORD_BANDS):
            words.append(w)
        if len(w) == 1 and len(chars) < max(CHAR_BANDS):
            chars.append(w)
        if len(words) >= max(WORD_BANDS) and len(chars) >= max(CHAR_BANDS):
            break
    return words, chars


def top_words(n: int) -> List[str]:
    return _frequency_tables()[0][:n]


def top_chars(n: int) -> List[str]:
    return _frequency_tables()[1][:n]


def han_chars(text: str) -> Set[str]:
    return {c for c in text if _HAN.match(c)}
