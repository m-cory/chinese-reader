# Chinese Reader

A self-hosted reading-and-recognition tool for Chinese. Read real texts; tap any
word to reveal pinyin + gloss on demand; word knowledge is inferred from behavior
(a tap means "not yet"), not from grading. Built for two learners over one shared
library, and architected so more users — and eventually more languages — slot in
without a redesign.

This is the **M1 core loop**: the reading surface + the data spine behind it. See
the product roadmap for the full plan and the [decisions log](docs/DECISIONS.md)
for why things are the way they are.

> Status: MVP backend + a live reading client. Reading runs entirely on local,
> free components (jieba + CC-CEDICT + OpenCC) — **no API calls in the core loop.**

## What works today

- **`POST /api/segment`** — turn any Chinese text into tappable tokens with pinyin
  and gloss. Simplified *and* traditional input; each token carries both scripts.
- **Behavior-driven word state** — tap = "not yet"; words you stop tapping across
  distinct sessions passively promote to *known*; long-press overrides.
- **Per-user coverage** and **"next text" routing** toward ~90–95% known.
- **Ingestion** — paste, `.txt`, or `.epub` (stdlib-only EPUB extraction).
- **A reading client** at `/` — the M0 surface, now wired to live segmentation.

## Quickstart (development)

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # POSIX: .venv/bin/python
.venv/Scripts/python -m pytest                            # 13 tests

# optional: bake in the full dictionary (CC-BY-SA, ~120k entries)
.venv/Scripts/python scripts/fetch_cedict.py

# run it
.venv/Scripts/python -m uvicorn app.main:app --app-dir . --port 8099
# open http://localhost:8099/
```

Without `fetch_cedict.py` the app runs on a small bundled sample
(`app/data/cedict_sample.u8`) — enough for the demo passage and the tests.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/segment` | Segment text → tokens (stateless) |
| POST | `/api/documents` | Ingest pasted text into the library |
| POST | `/api/documents/upload` | Ingest an uploaded `.txt` / `.epub` |
| GET | `/api/documents` | List library |
| GET | `/api/documents/{id}/read?user=` | Stored tokens + this user's word status |
| POST | `/api/tap` | Record a tap (→ learning) |
| POST | `/api/exposures` | Batch "seen this session" (drives promotion) |
| POST | `/api/override` | Manual status set |
| GET | `/api/coverage?user=&document_id=` | Coverage for a document |
| GET | `/api/next?user=` | Documents ranked by coverage fit |

## Layout

```
backend/app/
  language/            the language seam (base.py) + the one concrete module
    chinese/           segment (jieba) · dictionary (CC-CEDICT) · convert (OpenCC) · pinyin
  content/             the content seam: plaintext + epub ingestion
  core/                state.py (behavior model) · coverage.py (routing)
  routers/             read · library · state
  db.py schema.sql     SQLite, explicit SQL, no ORM
web/index.html         the reading client
deploy/                Dockerfile + compose stanza for nas-stack
docs/                  ARCHITECTURE.md · DECISIONS.md
```

## Deploy (NAS)

On the NAS: `git pull` this repo, `docker build -f deploy/Dockerfile -t
chinese-reader:0.1.0 .` (the build fetches the full dictionary itself), then bring
it up from `nas-stack/services/chinese-reader/`. Runs as `PUID:PGID`, SQLite +
uploads under `${DATA_ROOT}/chinese-reader`, on host port 3008. See
[deploy/compose.yaml](deploy/compose.yaml).

## Licensing of bundled data

- **CC-CEDICT** — CC-BY-SA 4.0 (fetched, not vendored; sample subset is vendored)
- **jieba** — MIT · **OpenCC / opencc-python** — Apache-2.0 · **pypinyin** — MIT
