"""Rotation-aware text access to the CTD India TB Report PDFs.

Copied from hssling/india-state-tb-score (MIT), src/extract/pdftext.py at
commit df8907d. Kept: _is_rotated, _row_text, _rotated_lines and page_lines,
unchanged. Added: ``page_chars``, which reads one page's characters and calls
``page.flush_cache()`` so that pdfplumber's memory stays bounded (ENVIRONMENT.md).

pdfplumber may be imported only under src/extract/.

CTD's annexures are landscape tables set on portrait pages by rotating the
text 90 degrees counter-clockwise. On those pages pdfplumber's upright
extract_text() returns character-reversed fragments ("noitacifiton"), so the
lines are rebuilt here from the characters: each table row is a run of chars
sharing a baseline x, read in order of decreasing `top`.
"""
from __future__ import annotations

from pathlib import Path

import pdfplumber

_ROW_TOL = 2.0  # max baseline (x) distance, in points, within one rotated row


def _is_rotated(chars: list[dict]) -> bool:
    chars = [c for c in chars if c["text"].strip()]
    if not chars:
        return False
    return sum(1 for c in chars if not c["upright"]) > len(chars) / 2


def _row_text(chars: list[dict]) -> str:
    """Join one rotated row's chars (reading bottom to top) into text."""
    chars = sorted(chars, key=lambda c: -c["top"])
    out: list[str] = []
    prev = None
    for c in chars:
        if c["text"] == " ":
            if out and out[-1] != " ":
                out.append(" ")
            prev = c
            continue
        if prev is not None and out and out[-1] != " ":
            # gap between end of previous char (its top) and start of this one
            # (its bottom, in reading direction)
            gap = prev["top"] - c["bottom"]
            if gap > 0.2 * (c["bottom"] - c["top"]):
                out.append(" ")
        out.append(c["text"])
        prev = c
    return "".join(out).strip()


def _rotated_lines(chars: list[dict]) -> list[str]:
    chars = [c for c in chars if not c["upright"]]
    # baseline x of rotated text is the matrix translation e.
    chars.sort(key=lambda c: c["matrix"][4])
    rows: list[list[dict]] = []
    for c in chars:
        if rows and abs(c["matrix"][4] - rows[-1][-1]["matrix"][4]) <= _ROW_TOL:
            rows[-1].append(c)
        else:
            rows.append([c])
    return [t for t in (_row_text(r) for r in rows) if t]


def page_lines(pdf_path: Path, page: int) -> list[str]:
    """Text lines of 1-based `page`, reading forwards, one per table row."""
    with pdfplumber.open(pdf_path) as pdf:
        pg = pdf.pages[page - 1]
        if _is_rotated(pg.chars):
            return _rotated_lines(pg.chars)
        text = pg.extract_text() or ""
    return text.splitlines()


_KEYS = ("text", "upright", "x0", "x1", "top", "bottom", "size", "matrix")


def page_chars(pdf: pdfplumber.PDF, page: int) -> tuple[list[dict], float, float]:
    """(characters, page width, page height) of 1-based `page`.

    Only the character fields used by the table reader are kept, and the
    page's cache is flushed before returning.
    """
    pg = pdf.pages[page - 1]
    chars = [{k: c[k] for k in _KEYS} for c in pg.chars]
    w, h = float(pg.width), float(pg.height)
    pg.flush_cache()
    pg.close()
    return chars, w, h
