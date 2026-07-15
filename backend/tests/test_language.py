from __future__ import annotations

from app.language.chinese import build_default
from app.language.chinese import convert
from app.language.chinese.pinyin import numbered_to_marks


def test_tone_marks():
    assert numbered_to_marks("jin1 tian1") == "jīntiān"
    assert numbered_to_marks("ni3 hao3") == "nǐhǎo"
    assert numbered_to_marks("lu:3") == "lǚ"          # ü handling
    assert numbered_to_marks("de5") == "de"           # neutral tone, no mark


def test_script_conversion_roundtrip():
    assert convert.to_trad("天气") == "天氣"
    assert convert.to_simp("天氣") == "天气"
    assert convert.to_trad("阳光温暖") == "陽光溫暖"


def test_segment_and_gloss():
    zh = build_default()
    tokens = zh.segment("我今天很好。")
    words = [t for t in tokens if t.is_word]
    surfaces = [t.surface for t in words]
    assert "今天" in surfaces
    jt = next(t for t in words if t.surface == "今天")
    assert jt.pinyin == "jīntiān"
    assert "today" in jt.gloss
    # trailing period is a non-word token, never tappable
    assert any((not t.is_word) and t.surface == "。" for t in tokens)


def test_dictionary_resplits_jieba_overmerges():
    """jieba's built-in dict fuses 喝咖啡 / 今天天气; CC-CEDICT arbitration must
    break them back into glossed words."""
    zh = build_default()
    surfaces = [t.surface for t in zh.segment("我喜欢喝咖啡") if t.is_word]
    assert "咖啡" in surfaces and "喝" in surfaces
    assert "喝咖啡" not in surfaces
    kafei = next(t for t in zh.segment("我喜欢喝咖啡") if t.surface == "咖啡")
    assert "coffee" in kafei.gloss


def test_traditional_is_canonical_key():
    """A simplified and its traditional form resolve to the SAME canonical trad —
    this is what gives one script-agnostic known-set."""
    zh = build_default()
    simp = next(t for t in zh.segment("天气") if t.is_word)
    trad = next(t for t in zh.segment("天氣") if t.is_word)
    assert simp.trad == trad.trad == "天氣"
