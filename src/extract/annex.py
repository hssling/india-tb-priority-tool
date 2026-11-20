"""Cell tokens, the printed-total comparison and the CSV writer.

Adapted from hssling/india-state-tb-score (MIT), src/extract/annex.py at
commit df8907d. Kept from that module:

- the ``Cell`` record (count as printed, percentage as printed, raw text);
- the token rules: a count (``_NUM``), a parenthesised percentage (``_PCT``,
  with or without "%", or "(NA)"), and the blank markers (``BLANKS``);
- the printed-total comparison of ``national_mismatches``/``check_national``
  (State sum of an extracted column against the printed national row, blank
  cells left out), here as ``total_gaps`` returning every difference with its
  size instead of raising;
- ``write_csv`` (UTF-8, LF line endings).

Changed: ``_PCT`` also accepts the empty "(%)" that TBAR 2022 Annexure 2.1
prints; a bare percentage such as "50%" (ITR 2024 Annexure 1.1) is a value
token of its own; ``tokens`` splits a word such as "3728(100%)" into its count
and its percentage. Dropped: the line-based row assembly, the List of
Annexures page location and the score-specific writers; the rows are rebuilt
from character positions in grid.py and the pages are fixed by the analysis
plan (§5.2).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import NamedTuple


class Cell(NamedTuple):
    n: str | None  # the count as printed; None for a blank cell
    pct: str | None
    raw: str


_PCT = re.compile(r"^\(\s*(?:-?\d+(?:\.\d+)?\s*%?|NA|%)\s*\)$")
_NUM = re.compile(r"^\*?\d[\d,]*(?:\.\d+)?\*?$")
_BARE_PCT = re.compile(r"^\d+(?:\.\d+)?%$")
_TOKEN = re.compile(r"\(\s*(?:-?\d+(?:\.\d+)?\s*%?|NA|%)\s*\)|[^\s(]+|\(\S*")
BLANKS = frozenset({"NA", "-", "–", "#N/A", "#DIV/0!"})


def tokens(text: str) -> list[tuple[int, int, str]]:
    """(start, end, token) for every token of `text`."""
    return [(m.start(), m.end(), m.group(0)) for m in _TOKEN.finditer(text)]


def kind(tok: str) -> str | None:
    """'pct', 'count' (a count or a bare percentage), 'blank', or None (text)."""
    if _PCT.match(tok):
        return "pct"
    if _NUM.match(tok) or _BARE_PCT.match(tok):
        return "count"
    if tok in BLANKS:
        return "blank"
    return None


def total_gaps(state_values: list[int | None], national: int) -> tuple[int, int, int]:
    """(State sum, printed national, number of blank State cells); the sum leaves
    blank cells out, as check_national did."""
    vals = [v for v in state_values if v is not None]
    return sum(vals), national, len(state_values) - len(vals)


# ---- writing -----------------------------------------------------------------

def _fmt(v) -> str:
    return "" if v is None else str(v)


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow([_fmt(r[h]) for h in header])
