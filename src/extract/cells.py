"""Cell parsers. Blanks, dashes and NA are errors: callers decide their meaning.

Copied from hssling/india-state-tb-score (MIT), src/extract/cells.py at commit
df8907d. Kept unchanged: parse_int, parse_count, parse_n_pct. Added:
parse_decimal, for the population column printed in lakhs with two decimals.
"""
from __future__ import annotations

import re
from decimal import Decimal

_INT = re.compile(r"^\*?(\d+(?:,\d+)*)\*?$")
_COUNT = re.compile(r"^\*?(\d+(?:,\d+)*)(?:\.(\d+))?\*?$")
_N_PCT = re.compile(r"^\s*(\S+?)\s*\(\s*(\d+(?:\.\d+)?)\s*%\s*\)\s*$")
_DEC = re.compile(r"^(\d+)\.(\d+)$")


def parse_int(s: str) -> int:
    """'1,23,456' / '1,234,567' / '*89' -> int; ValueError for anything else."""
    m = _INT.match(s.strip())
    if not m:
        raise ValueError(f"not an integer cell: {s!r}")
    return int(m.group(1).replace(",", ""))


def parse_count(s: str) -> int:
    """Like parse_int, but also accepts integral floats: '63.0' -> 63.

    CTD prints some count columns from a spreadsheet as '4607.0'. A
    non-integral value ('63.5') is not a count and raises ValueError.
    """
    m = _COUNT.match(s.strip())
    if not m or (m.group(2) is not None and int(m.group(2)) != 0):
        raise ValueError(f"not a count cell: {s!r}")
    return int(m.group(1).replace(",", ""))


def parse_n_pct(s: str) -> tuple[int, float]:
    """'62795 (99%)' -> (62795, 99.0)."""
    m = _N_PCT.match(s)
    if not m:
        raise ValueError(f"not an 'n (pct%)' cell: {s!r}")
    return parse_int(m.group(1)), float(m.group(2))


def parse_decimal(s: str) -> Decimal:
    """'532.49' -> Decimal('532.49'); a plain decimal number only (no commas)."""
    m = _DEC.match(s.strip())
    if not m:
        raise ValueError(f"not a decimal cell: {s!r}")
    return Decimal(s.strip())
