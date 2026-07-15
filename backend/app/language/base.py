from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class Token:
    """One unit of segmented text.

    `surface` is the substring as it appeared. For word tokens we also carry both
    scripts (`trad`/`simp`) plus `pinyin`/`gloss`, so the reader can toggle
    simplified <-> traditional on the client with no re-segmentation. Punctuation
    and whitespace are tokens too, with `is_word=False` (never tappable).

    The canonical identity of a word is its **traditional** form (`trad`):
    traditional -> simplified is deterministic, the reverse is one-to-many, so
    keying state on `trad` gives a single script-agnostic known-set for free.
    """

    surface: str
    is_word: bool
    trad: Optional[str] = None
    simp: Optional[str] = None
    pinyin: Optional[str] = None
    gloss: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class LanguageModule:
    """The language seam.

    Deliberately thin. Exactly one concrete module (Chinese) lives behind it today.
    Do NOT grow this interface speculatively from a single example — a genuine
    second language (especially a non-CJK one) should reshape this, not be forced
    to squeeze into Chinese's assumptions about segmentation and script variants.

    A concrete module is a plain object exposing `code`, `segment`, and `to_script`.
    """

    code: str = "und"

    def segment(self, text: str) -> List[Token]:
        raise NotImplementedError

    def to_script(self, text: str, script: str) -> str:
        """Convert running text to `script` ('simp' | 'trad'). No-op if unsupported."""
        return text
