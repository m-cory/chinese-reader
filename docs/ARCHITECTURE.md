# Architecture

The whole extensibility story rides on **three generic seams**. They are built
clean; only the one concrete case runs behind each. Everything in the middle is
deliberately concrete until the concrete case works.

## The three seams

### 1. User seam — the data model
There is no per-user code. Everything a user "knows" is rows in
`user_word_state` keyed by `(user_id, word_id)`. N users is just more rows. The
heritage vs. non-heritage asymmetry the project is validating against is entirely
emergent from each user's data — never an `if heritage:` branch. Coverage routing
is where this pays off: the same document scores differently per user, all from
state.

### 2. Language seam — `language/base.py`
A thin interface (`segment`, `to_script`, a `code`). Chinese is the only concrete
module today, in `language/chinese/`. **The interface is intentionally minimal**
because it is being designed from a single example; a genuine second language
(especially non-CJK) should reshape it rather than be forced into Chinese's
assumptions. Retrofitting a real second module is cheap precisely because nothing
outside the seam reaches into Chinese internals.

### 3. Content seam — `content/base.py`
Ingestion is format-driven: `ingest(filename, bytes) -> str` dispatches by
extension. EPUB (stdlib zip + tag strip) and plain text today; a text-layer PDF
or an OCR path slots in here without touching the reader.

## Segmentation pipeline (the part that needed the most care)

Raw text → tokens is a three-step pipeline, each step fixing a real failure of the
one before (see [DECISIONS.md](DECISIONS.md) for the evidence):

1. **Normalize to simplified.** jieba's dictionary is simplified-only and
   mis-segments traditional input (天氣 → 天/氣). We convert to simplified for
   jieba's benefit; tokens still carry both scripts from CC-CEDICT, so traditional
   rendering and the canonical key are unaffected.
2. **jieba, `HMM=False`.** HMM's new-word discovery invents OOV merges; off is the
   right default for a reader.
3. **CC-CEDICT-guided resplit.** jieba's *built-in* dictionary still ships junk
   collocations (喝咖啡, 今天天气 at frequency 3) that fuse known words. If a token
   isn't a headword but splits cleanly into headwords, we prefer the split. A
   genuine OOV name won't split cleanly and is left intact. This is the concrete
   answer to LingQ's "segmentation fuses known words" complaint — and it will only
   get better with the full dictionary loaded.

The residue that all three steps still get wrong is what the Phase-3 **shared
correction layer** is for. The win was never a perfect segmenter.

## Canonical key = traditional headword

A word's identity is its **traditional** form. Traditional → simplified is
deterministic; the reverse is one-to-many (发 → 髮/發). Keying `word.trad` (UNIQUE)
means a tap on 请 and a tap on 請 resolve to the same lexeme — one script-agnostic
known-set, for free. Rendering either script is a client-side toggle over the
`trad`/`simp` fields every token carries.

## Word state — behavior, not grading

`core/state.py`:
- **tap** → status becomes `learning`, `clean_streak` resets. The only explicit
  signal the reader ever gives.
- **exposure** without a tap, across `CR_PROMOTE_AFTER` *distinct sessions*,
  promotes `learning`/`new` → `known`. Distinct sessions, not raw repeats: five
  looks in one sitting is one signal.
- **override** (long-press) sets status directly.

`core/coverage.py`: coverage = known word-tokens / total word-tokens for a user;
`rank_next` orders documents by distance from the target band.

## Data flow

```
paste / upload ──ingest──► text
text ──ChineseModule.segment──► tokens (surface, trad, simp, pinyin, gloss, is_word)
store: document + document_token(+word_id)   word: upsert by trad
read: document_token ⋈ word, overlaid with user_word_state.status
signals: /tap /exposures /override ──► user_word_state ──► coverage
```

## Why SQLite + explicit SQL, no ORM

Two users. The schema fits on one screen. Explicit SQL keeps the whole system
inside your head — which, with an LLM writing much of the code, is the constraint
that actually matters (an ORM you didn't write is one more thing to hold). Swap to
Postgres later only if the library and search genuinely outgrow SQLite.
