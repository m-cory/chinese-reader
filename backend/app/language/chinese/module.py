from __future__ import annotations

"""The concrete Chinese language module — the first (and currently only) thing
behind the language seam. Composes segmentation + dictionary + script conversion
+ pinyin into the `LanguageModule` interface the rest of the app depends on.
"""

from pathlib import Path
from typing import List, Optional

from ..base import LanguageModule, Token
from . import convert, segment as seg
from . import pinyin as pinyin_mod
from .dictionary import Dictionary, load

_DATA = Path(__file__).resolve().parents[2] / "data"


class ChineseModule(LanguageModule):
    code = "zh"

    def __init__(self, dictionary: Dictionary, user_dict: Optional[Path] = None) -> None:
        self.dict = dictionary
        self.user_dict = user_dict

    def segment(self, text: str) -> List[Token]:
        # jieba's dictionary is simplified-only and mis-segments traditional input
        # (天氣 -> 天/氣). Normalize to simplified for segmentation; each token still
        # carries both scripts from the dictionary, so traditional rendering is
        # unaffected and the canonical (traditional) key stays consistent across
        # whichever script the text arrived in.
        text = convert.to_simp(text)
        tokens: List[Token] = []
        for surface, word in seg.segment(text, self.user_dict):
            if not word:
                tokens.append(Token(surface=surface, is_word=False))
                continue
            entry = self.dict.lookup(surface)
            if entry is not None:
                tokens.append(self._word_token(surface, entry))
                continue
            # Not a headword: let CC-CEDICT arbitrate a possible over-merge before
            # falling back. 喝咖啡 -> 喝 / 咖啡; a genuine OOV name won't split.
            pieces = self.dict.split_known(surface)
            if pieces:
                for piece in pieces:
                    tokens.append(self._word_token(piece, self.dict.lookup(piece)))
            else:
                tokens.append(self._oov_token(surface))
        return tokens

    def _word_token(self, surface: str, entry) -> Token:
        return Token(
            surface=surface,
            is_word=True,
            trad=entry.trad,
            simp=entry.simp,
            pinyin=entry.pinyin,
            gloss=entry.gloss,
        )

    def _oov_token(self, surface: str) -> Token:
        # Out-of-dictionary (names, rare compounds): still show *something*. The
        # canonical key is the traditional form; pinyin falls back to pypinyin;
        # gloss is left empty for the Phase-3 correction layer.
        return Token(
            surface=surface,
            is_word=True,
            trad=convert.to_trad(surface),
            simp=convert.to_simp(surface),
            pinyin=pinyin_mod.fallback_reading(surface),
            gloss=None,
        )

    def to_script(self, text: str, script: str) -> str:
        return convert.to_script(text, script)


def build_default(extra_dicts: Optional[List[Path]] = None) -> ChineseModule:
    """Load the bundled sample plus the full CC-CEDICT if it has been fetched."""
    paths = [_DATA / "cedict_sample.u8", _DATA / "cedict.u8"]
    if extra_dicts:
        paths.extend(extra_dicts)
    dictionary = load(*paths)
    user_dict = _DATA / "userdict.txt"
    return ChineseModule(dictionary, user_dict=user_dict if user_dict.exists() else None)
