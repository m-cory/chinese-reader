from __future__ import annotations

"""Runtime configuration, all overridable by environment variable so the same
image runs locally and on the NAS (data path is a bind mount there)."""

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
REPO_DIR = BACKEND_DIR.parent

# Where the SQLite DB and uploaded texts live. On the NAS this is a
# ${DATA_ROOT}/chinese-reader bind mount owned by PUID:PGID.
DATA_DIR = Path(os.environ.get("CR_DATA_DIR", BACKEND_DIR / "var"))
DB_PATH = Path(os.environ.get("CR_DB_PATH", DATA_DIR / "reader.db"))

# Static reader client (served same-origin so the browser needs no CORS).
WEB_DIR = Path(os.environ.get("CR_WEB_DIR", REPO_DIR / "web"))

# How many distinct no-tap sessions before a word passively promotes to "known".
PROMOTE_AFTER = int(os.environ.get("CR_PROMOTE_AFTER", "3"))

# Coverage target for "next text" routing — slightly above comfort.
COVERAGE_TARGET = float(os.environ.get("CR_COVERAGE_TARGET", "0.92"))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
