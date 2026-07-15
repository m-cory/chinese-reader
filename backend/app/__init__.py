"""Chinese Reader backend — a reading-and-recognition tool.

Package layout mirrors the three generic seams from the roadmap:
  language/  — everything language-specific, behind a thin interface (Chinese is the one concrete module)
  content/   — ingestion, format-driven (plain text, EPUB)
  core/      — per-user word state + coverage (the user seam lives in the data model)
"""
