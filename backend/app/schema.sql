-- Chinese Reader schema (SQLite).
-- Two users is just two rows; N users is just more rows. The heritage vs.
-- non-heritage asymmetry lives entirely in user_word_state, never in code.

CREATE TABLE IF NOT EXISTS user (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The canonical lexeme, keyed by TRADITIONAL headword (script-agnostic identity).
CREATE TABLE IF NOT EXISTS word (
    id     INTEGER PRIMARY KEY,
    trad   TEXT NOT NULL UNIQUE,
    simp   TEXT NOT NULL,
    pinyin TEXT,
    gloss  TEXT
);

-- Per-user, behavior-driven state. status: new | learning | known.
-- clean_streak = consecutive distinct sessions the word was seen WITHOUT a tap;
-- reaching PROMOTE_AFTER promotes it to known. A tap resets the streak.
CREATE TABLE IF NOT EXISTS user_word_state (
    user_id      INTEGER NOT NULL REFERENCES user(id),
    word_id      INTEGER NOT NULL REFERENCES word(id),
    status       TEXT    NOT NULL DEFAULT 'new',
    taps         INTEGER NOT NULL DEFAULT 0,
    clean_streak INTEGER NOT NULL DEFAULT 0,
    last_session TEXT,
    last_seen_at TEXT,
    promoted_at  TEXT,
    PRIMARY KEY (user_id, word_id)
);

CREATE TABLE IF NOT EXISTS document (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    source_type TEXT,
    added_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Stored segmentation. Persisting tokens (rather than re-segmenting on every open)
-- is what lets a Phase-3 correction be a stored edit on a token, not a re-run.
CREATE TABLE IF NOT EXISTS document_token (
    document_id INTEGER NOT NULL REFERENCES document(id),
    ord         INTEGER NOT NULL,
    surface     TEXT    NOT NULL,
    word_id     INTEGER REFERENCES word(id),
    is_word     INTEGER NOT NULL,
    PRIMARY KEY (document_id, ord)
);

CREATE INDEX IF NOT EXISTS idx_token_word ON document_token(word_id);
