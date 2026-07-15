from __future__ import annotations

"""Word segmentation via jieba.

jieba is not a perfect segmenter — no Chinese segmenter is; even native speakers
agree only ~90% of the time. That's fine: the roadmap's win is not a perfect
segmenter but a frictionless *shared correction* affordance (Phase 3). Here we
just produce a reasonable default tokenization and preserve every character
(including punctuation) so the reader can render the text verbatim.
"""

import re
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

_HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

_jieba = None


def _engine(user_dict: Optional[Path] = None):
    global _jieba
    if _jieba is None:
        import jieba

        jieba.initialize()
        if user_dict and Path(user_dict).exists():
            jieba.load_userdict(str(user_dict))
        _jieba = jieba
    return _jieba


def is_word(surface: str) -> bool:
    """A token is a (tappable) word if it contains at least one Han character."""
    return bool(_HAN.search(surface))


def segment(text: str, user_dict: Optional[Path] = None) -> List[Tuple[str, bool]]:
    """Return [(surface, is_word), ...] in reading order, nothing dropped.

    HMM=False on purpose: jieba's HMM new-word discovery invents OOV merges we
    don't want in a reader. Note this alone is not enough — jieba's *built-in*
    dictionary also ships junk collocations (喝咖啡, 今天天气 at frequency 3) that
    fuse known words. Those are broken back apart downstream by CC-CEDICT-guided
    resplitting (see ChineseModule.segment / Dictionary.split_known), which is the
    concrete answer to the "segmentation fuses known words" complaint the roadmap
    cites against LingQ.
    """
    jieba = _engine(user_dict)
    out: List[Tuple[str, bool]] = []
    for tok in jieba.cut(text, HMM=False):
        if tok == "":
            continue
        out.append((tok, is_word(tok)))
    return out
