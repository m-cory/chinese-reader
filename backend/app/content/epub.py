from __future__ import annotations

"""EPUB ingestion using only the standard library (an EPUB is a ZIP of XHTML).

We read the OPF spine to recover reading order, then strip tags from each XHTML
document. No lxml/ebooklib dependency — fewer moving parts, and the text layer in
a well-made EPUB is clean enough that a tag-stripper is sufficient.
"""

import io
import re
import zipfile
from html.parser import HTMLParser
from typing import List

_CONTAINER = "META-INF/container.xml"
_SKIP_TAGS = {"script", "style", "head"}


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in ("p", "br", "div", "h1", "h2", "h3", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _strip(xhtml: str) -> str:
    p = _Text()
    p.feed(xhtml)
    text = "".join(p.parts)
    return re.sub(r"\n{3,}", "\n\n", text)


def _spine_order(zf: zipfile.ZipFile) -> List[str]:
    try:
        container = zf.read(_CONTAINER).decode("utf-8", "replace")
        opf_path = re.search(r'full-path="([^"]+)"', container).group(1)
        opf = zf.read(opf_path).decode("utf-8", "replace")
        base = opf_path.rsplit("/", 1)[0] if "/" in opf_path else ""
        # id -> href, parsing each <item> tag's attributes independently of order
        manifest = {}
        for item in re.findall(r"<item\b[^>]*>", opf):
            mid = re.search(r'id="([^"]+)"', item)
            href = re.search(r'href="([^"]+)"', item)
            if mid and href:
                manifest[mid.group(1)] = href.group(1)
        order = re.findall(r'<itemref[^>]*idref="([^"]+)"', opf)
        hrefs = []
        for idref in order:
            href = manifest.get(idref)
            if href:
                hrefs.append(f"{base}/{href}" if base else href)
        return hrefs
    except Exception:
        return []


def extract(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        hrefs = _spine_order(zf)
        if not hrefs:
            hrefs = sorted(n for n in zf.namelist() if n.lower().endswith((".xhtml", ".html", ".htm")))
        chunks = []
        for href in hrefs:
            try:
                chunks.append(_strip(zf.read(href).decode("utf-8", "replace")))
            except KeyError:
                continue
    return re.sub(r"\n{3,}", "\n\n", "\n\n".join(chunks)).strip()
