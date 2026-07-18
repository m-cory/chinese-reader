from __future__ import annotations

"""API tests for library management (rename/delete) and the per-user words list."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _add(client, title="t", text="我今天很好。"):
    r = client.post("/api/documents", json={"title": title, "text": text})
    assert r.status_code == 200
    return r.json()["id"]


def test_rename_document(client):
    doc_id = _add(client, title="old")
    r = client.patch(f"/api/documents/{doc_id}", json={"title": "  new name  "})
    assert r.status_code == 200 and r.json()["title"] == "new name"
    docs = client.get("/api/documents").json()["documents"]
    assert next(d for d in docs if d["id"] == doc_id)["title"] == "new name"


def test_rename_rejects_empty_and_missing(client):
    doc_id = _add(client)
    assert client.patch(f"/api/documents/{doc_id}", json={"title": "   "}).status_code == 400
    assert client.patch("/api/documents/999999", json={"title": "x"}).status_code == 404


def test_delete_document_removes_tokens_but_keeps_word_state(client):
    doc_id = _add(client)
    tokens = client.get(f"/api/documents/{doc_id}/read", params={"user": "alex"}).json()["tokens"]
    wid = next(t["word_id"] for t in tokens if t["surface"] == "今天")
    client.post("/api/tap", json={"user": "alex", "word_id": wid})

    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert client.get(f"/api/documents/{doc_id}/read", params={"user": "alex"}).status_code == 404
    assert all(d["id"] != doc_id for d in client.get("/api/documents").json()["documents"])
    # word knowledge survives the text
    words = client.get("/api/words", params={"user": "alex", "status": "learning"}).json()["words"]
    assert any(w["word_id"] == wid for w in words)


def test_delete_missing_404(client):
    assert client.delete("/api/documents/999999").status_code == 404


def test_words_filters_by_status(client):
    doc_id = _add(client)
    tokens = client.get(f"/api/documents/{doc_id}/read", params={"user": "mei"}).json()["tokens"]
    ids = [t["word_id"] for t in tokens if t["word_id"] is not None]
    learn_id, known_id = ids[0], ids[1]
    client.post("/api/tap", json={"user": "mei", "word_id": learn_id})
    client.post("/api/override", json={"user": "mei", "word_id": known_id, "status": "known"})

    learning = client.get("/api/words", params={"user": "mei", "status": "learning"}).json()["words"]
    assert [w["word_id"] for w in learning] == [learn_id]
    assert learning[0]["taps"] == 1 and learning[0]["pinyin"]

    known = client.get("/api/words", params={"user": "mei", "status": "known"}).json()["words"]
    assert [w["word_id"] for w in known] == [known_id]

    assert client.get("/api/words", params={"user": "mei", "status": "bogus"}).status_code == 400
