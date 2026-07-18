from __future__ import annotations

"""Progress endpoint: counts, HSK matching, frequency bands."""

import pytest
from fastapi.testclient import TestClient

from app.language.chinese import benchmarks
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_hsk_lists_load():
    words = benchmarks.hsk_words()
    assert set(words) == {1, 2, 3, 4, 5, 6}
    assert len(words[1]) == 150
    assert "我" in words[1] and "爱" in words[1]
    assert sum(len(v) for v in words.values()) > 4900


def test_frequency_tables():
    top = benchmarks.top_words(500)
    assert len(top) == 500 and "的" in top
    chars = benchmarks.top_chars(500)
    assert len(chars) == 500 and all(len(c) == 1 for c in chars)


def test_progress_empty_user(client):
    r = client.get("/api/progress", params={"user": "prog-fresh"})
    assert r.status_code == 200
    p = r.json()
    assert p["words"] == {"known": 0, "learning": 0, "promoted_7d": 0}
    assert p["chars"]["known"] == 0
    assert p["hsk_estimate"] == 0
    assert [h["level"] for h in p["hsk"]] == [1, 2, 3, 4, 5, 6]
    assert all(h["known"] == 0 for h in p["hsk"])


def test_progress_counts_known_words(client):
    user = "prog-counts"
    r = client.post("/api/documents", json={"title": "p", "text": "我爱你。今天天气很好。"})
    doc_id = r.json()["id"]
    tokens = client.get(f"/api/documents/{doc_id}/read", params={"user": user}).json()["tokens"]
    by_surface = {t["surface"]: t for t in tokens if t["word_id"] is not None}

    # 我 and 爱 are HSK-1 words; mark them known, and one word learning
    for w in ("我", "爱"):
        client.post("/api/override", json={"user": user, "word_id": by_surface[w]["word_id"], "status": "known"})
    client.post("/api/tap", json={"user": user, "word_id": by_surface["今天"]["word_id"]})

    p = client.get("/api/progress", params={"user": user}).json()
    assert p["words"]["known"] == 2
    assert p["words"]["learning"] == 1
    assert p["words"]["promoted_7d"] == 2          # overrides stamp promoted_at
    assert p["chars"]["known"] == 2                # 我, 爱

    hsk1 = next(h for h in p["hsk"] if h["level"] == 1)
    assert hsk1["known"] == 2 and hsk1["total"] == 150

    band500 = next(b for b in p["freq_words"] if b["band"] == 500)
    assert band500["known"] >= 1                   # 我 is deep inside the top 500
    cband = next(b for b in p["freq_chars"] if b["band"] == 500)
    assert cband["known"] >= 1
