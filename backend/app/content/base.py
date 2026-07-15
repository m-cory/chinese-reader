from __future__ import annotations

"""The content seam: ingestion is format-driven, so a new source slots in without
touching the reader. EPUB is preferred (clean text layer, no OCR); text-layer PDF
would extract directly; scanned material would fall to OCR (a deliberate last
resort, not built here). Today: plain text and EPUB.
"""

from pathlib import Path

from . import plaintext, epub

SUPPORTED = {".txt", ".text", ".epub"}


def ingest(filename: str, data: bytes) -> str:
    """Extract clean reading text from an uploaded file's bytes."""
    ext = Path(filename).suffix.lower()
    if ext == ".epub":
        return epub.extract(data)
    if ext in (".txt", ".text", ""):
        return plaintext.extract(data)
    raise ValueError(f"unsupported format {ext!r}; supported: {sorted(SUPPORTED)}")
