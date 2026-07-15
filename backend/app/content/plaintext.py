from __future__ import annotations

"""Plain text / paste ingestion — the simple alternative to file upload."""


def extract(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030", "big5"):
        try:
            return data.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace").strip()
