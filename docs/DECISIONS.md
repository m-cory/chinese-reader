# Decisions

Short, dated rationale for choices that aren't obvious from the code. Some were
locked in planning; several were forced or confirmed by testing during the M1
build and are marked accordingly.

## Locked in planning

- **Reader-surface first, backend second.** The reading surface *is* the product
  and is the weak axis for this team; the backend is the comfortable one. Build
  order fights the temptation to polish the spine while the reader lags.
- **Core loop is API-free.** Segmentation + gloss run on local, free components
  (jieba, CC-CEDICT, OpenCC). An LLM gloss/correction pass is a later, optional
  layer; the MVP depends on none of it.
- **Canonical key = traditional headword.** Deterministic trad→simp vs. ambiguous
  simp→trad ⇒ one script-agnostic known-set. See ARCHITECTURE.md.
- **Behavior over grading.** Tap = "not yet"; passive promotion by distinct-session
  exposure; long-press override.
- **Thin language seam.** Designing a language interface from one example over-fits;
  keep it minimal and let language #2 reshape it.
- **SQLite + explicit SQL, no ORM.** Small schema, two users; keep it in-head.

## Forced or confirmed by testing (2026-07-14)

- **`HMM=False` for jieba.** HMM new-word discovery invents OOV merges. Necessary
  but *not sufficient* — see next.
- **CC-CEDICT-guided resplit.** *Evidence:* with the sample dict, `我喜欢喝咖啡`
  segmented to `喝咖啡` (one glossless token) and `今天天气非常好` to `今天天气`,
  because jieba's built-in dict lists those collocations at frequency 3. Toggling
  HMM changed nothing. Fix: if a non-headword splits cleanly into headwords, prefer
  the split. Now both resolve to glossed `喝`/`咖啡`, `今天`/`天气`.
- **Normalize to simplified before segmenting.** *Evidence:* a test asserting a
  simplified and traditional form share one canonical key failed — jieba split the
  traditional `天氣` into `天`/`氣` (its dict is simplified-only). Fix: convert input
  to simplified for jieba; tokens still carry both scripts, so display is unaffected.
- **`check_same_thread=False` on the SQLite connection.** FastAPI may open a
  yield-dependency connection on one thread and use it on a threadpool worker.
  Each request still gets its own connection and never shares it concurrently.
- **`TestClient` as a context manager.** Modern Starlette only runs the lifespan
  (which creates the tables) when the client is entered as a context manager;
  tests use a fixture that does so.
- **Lifespan handler over `@app.on_event`.** The latter is deprecated in the
  installed FastAPI.

## Stateful client (2026-07-15)

- **The reader reads from the library, not `/segment`.** The stateless
  `/segment` endpoint carries no `word_id`, so nothing could persist. The client
  now stores every text as a document and reads it back via
  `/documents/{id}/read?user=`, so each token has a stable `word_id` and this
  user's `status`. Pasting a text adds it to the library rather than being a
  throwaway.
- **One page load = one reading session.** The exposure model promotes across
  *distinct sessions*; the client mints a session id per load. Untapped words are
  banked (`/exposures`) on tab-hide via `navigator.sendBeacon` and on an explicit
  "Done" button. Re-banking within a load is idempotent (the server skips a word
  whose `last_session` already matches).
- **Only `learning` is visibly marked.** `known` and `new` render as plain text —
  we never pre-highlight "unknown" because, by design, we don't know what the
  reader doesn't know until they tap. Help (the accent underline) appears on tap
  and fades when a word promotes to `known`. Progress lives in the status bar
  (coverage %, learning count), not in decorating the prose.
- **A tap marks every occurrence** of that word on screen, and counts are by
  unique `word_id`, not token — the reader acts on a lexeme, not a position.

## Deferred (with the seam already in place)

- Second **language** module — the seam exists; do not design its shape until a
  real second language is on the table.
- **LLM gloss + shared correction layer** (Phase 3) — owns the residue the
  segmentation pipeline still gets wrong, and the ambiguous simp→trad conversions.
- **SRS safety net** (Phase 4), **web import / generated content** (Phase 5).
- **React client.** The current client is intentionally vanilla (no Node
  dependency) and is enough to validate the reading feel. Port to React only after
  the surface is validated and Node is available.

## Open

- `CR_PROMOTE_AFTER` (default 3) and `CR_COVERAGE_TARGET` (default 0.92) are
  guesses; tune from real reading.
- Passive promotion still can't distinguish "knew it" from "skimmed past it"
  perfectly. Distinct-session counting is the current guard; revisit if promotion
  feels too eager.
- EPUB extraction is a tag-stripper; messy EPUBs may need a real parser later.
