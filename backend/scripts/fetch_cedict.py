#!/usr/bin/env python3
"""Fetch the full CC-CEDICT into backend/app/data/cedict.u8.

CC-CEDICT is CC-BY-SA 4.0 (attribution + share-alike) — fine for a self-hosted
personal tool. It is intentionally NOT vendored in the repo (large, and share-
alike); this script pulls it on demand. The app runs on the bundled sample until
you do this; afterwards ChineseModule loads both.

Usage:
    python backend/scripts/fetch_cedict.py
"""

import gzip
import io
import sys
import urllib.request
from pathlib import Path

URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
DEST = Path(__file__).resolve().parents[1] / "app" / "data" / "cedict.u8"


def main() -> int:
    print(f"Downloading {URL}", file=sys.stderr)
    try:
        with urllib.request.urlopen(URL, timeout=60) as resp:
            blob = resp.read()
    except Exception as e:  # noqa: BLE001
        print(f"Download failed: {e}", file=sys.stderr)
        return 1
    text = gzip.GzipFile(fileobj=io.BytesIO(blob)).read()
    DEST.write_bytes(text)
    n = sum(1 for line in text.splitlines() if line and not line.startswith(b"#"))
    print(f"Wrote {DEST} ({n} entries)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
