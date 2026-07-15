from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # The context manager runs the lifespan handler, which creates the tables.
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_segment_endpoint(client):
    r = client.post("/api/segment", json={"text": "我今天很好"})
    assert r.status_code == 200
    tokens = r.json()["tokens"]
    jt = next(t for t in tokens if t["surface"] == "今天")
    assert jt["is_word"] and jt["pinyin"] == "jīntiān" and "today" in jt["gloss"]


def test_document_tap_coverage_loop(client):
    # ingest a document
    r = client.post("/api/documents", json={"title": "morning", "text": "我今天很好。"})
    assert r.status_code == 200
    doc_id = r.json()["id"]

    # read it back with a user overlay; everything starts 'new'
    r = client.get(f"/api/documents/{doc_id}/read", params={"user": "alex"})
    tokens = r.json()["tokens"]
    jt = next(t for t in tokens if t["surface"] == "今天")
    assert jt["status"] == "new"

    # tap marks it learning
    r = client.post("/api/tap", json={"user": "alex", "word_id": jt["word_id"]})
    assert r.json()["status"] == "learning"

    # override to known lifts coverage
    client.post("/api/override", json={"user": "alex", "word_id": jt["word_id"], "status": "known"})
    r = client.get("/api/coverage", params={"user": "alex", "document_id": doc_id})
    assert r.json()["known"] >= 1


def test_epub_upload(client):
    # build a minimal EPUB in-memory and upload it
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container><rootfiles>'
            '<rootfile full-path="content.opf"/></rootfiles></container>',
        )
        z.writestr(
            "content.opf",
            '<package><manifest><item id="c1" href="c1.xhtml"/></manifest>'
            '<spine><itemref idref="c1"/></spine></package>',
        )
        z.writestr("c1.xhtml", "<html><body><p>我今天很好。</p></body></html>")
    buf.seek(0)
    r = client.post(
        "/api/documents/upload",
        files={"file": ("book.epub", buf.read(), "application/epub+zip")},
    )
    assert r.status_code == 200
    assert r.json()["words"] >= 2
