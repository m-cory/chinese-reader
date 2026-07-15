from __future__ import annotations

"""CC-CEDICT loader + lookup.

CC-CEDICT lines look like:  繁體 简体 [pin1 yin1] /gloss one/gloss two/
We index every entry by BOTH its traditional and simplified headword, so a lookup
of a surface string (whichever script the text is in) resolves in one hop, with no
network call. This is what keeps tap-to-gloss instant and the core loop API-free.

The full dictionary (~120k entries, CC-BY-SA) is fetched at setup time — see
scripts/fetch_cedict.py — and is NOT committed. A small sample ships in
backend/app/data/cedict_sample.u8 so tests and the demo run without the download.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from . import pinyin as pinyin_mod

_LINE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]*)\]\s+/(.*)/\s*$")


@dataclass
class Entry:
    trad: str
    simp: str
    pinyin: str          # tone-marked, e.g. "jīntiān"
    glosses: List[str]

    @property
    def gloss(self) -> str:
        """A compact gloss for the popover — first two senses, '; '-joined."""
        return "; ".join(self.glosses[:2])


class Dictionary:
    def __init__(self) -> None:
        self._by_key: Dict[str, Entry] = {}

    def __len__(self) -> int:
        return len(self._by_key)

    def add_line(self, line: str) -> bool:
        line = line.strip()
        if not line or line.startswith("#"):
            return False
        m = _LINE.match(line)
        if not m:
            return False
        trad, simp, py, defs = m.groups()
        glosses = [g for g in defs.split("/") if g]
        entry = Entry(
            trad=trad,
            simp=simp,
            pinyin=pinyin_mod.numbered_to_marks(py),
            glosses=glosses,
        )
        # A headword can appear more than once (different readings). Keep the first
        # seen as primary; that is the "most likely reading" baseline of Phase 1.
        self._by_key.setdefault(trad, entry)
        self._by_key.setdefault(simp, entry)
        return True

    def load_file(self, path: Path) -> "Dictionary":
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                self.add_line(line)
        return self

    def lookup(self, surface: str) -> Optional[Entry]:
        return self._by_key.get(surface)

    def split_known(self, surface: str, max_len: int = 8) -> Optional[List[str]]:
        """If `surface` is not itself a headword but splits cleanly (greedy
        longest-match) into two or more headwords, return those pieces; else None.

        This lets CC-CEDICT arbitrate jieba's over-merges (喝咖啡 -> 喝 / 咖啡)
        without butchering genuine out-of-dictionary names, which won't split
        cleanly and are therefore left untouched.
        """
        if surface in self._by_key:
            return None
        pieces: List[str] = []
        i, n = 0, len(surface)
        while i < n:
            hit = None
            for j in range(min(n, i + max_len), i, -1):
                if surface[i:j] in self._by_key:
                    hit = surface[i:j]
                    break
            if hit is None:
                return None  # a character with no known word -> don't split at all
            pieces.append(hit)
            i += len(hit)
        return pieces if len(pieces) > 1 else None


def load(*paths: Path) -> Dictionary:
    d = Dictionary()
    for p in paths:
        p = Path(p)
        if p.exists():
            d.load_file(p)
    return d
