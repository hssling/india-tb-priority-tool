# Adapted from hssling/india-tb-acf-campaign (MIT), verification/check_manuscript_numbers.py,
# "Number formats"; modified: the formats of this paper, shared by exhibits/make_tables.py,
# exhibits/make_figures.py and verification/check_manuscript_numbers.py.
"""Number formats of the manuscript and its exhibits: the only place they are fixed.

Every number printed in the tables, the figure labels and the text goes through one of these
functions, so the number check (verification/check_manuscript_numbers.py) and the exhibits
always agree on how a value from outputs/ is written.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

MINUS = "−"  # a negative number is written with the minus sign U+2212
TO = " to "        # every interval: "0.323 to 0.743"
MONTHS = ("January February March April May June July August September October November "
          "December").split()

STEP_NAMES = {
    "S1": "shortfall against target",
    "S2": "not tested for rifampicin resistance",
    "S3": "died (DS-TB cohort)",
    "S4": "lost to follow-up (DS-TB cohort)",
    "S5": "DR-TB treatment not successful",
    "S6": "HIV status not known",
}
STEPS = list(STEP_NAMES)
TIERS = ["act now", "probable priority", "uncertain", "watch: rising", "lower priority"]
TIER_LETTER = {"act now": "A", "probable priority": "P", "uncertain": "U",
               "watch: rising": "W", "lower priority": "L"}


def num(x: float | str, dp: int) -> str:
    """x with dp decimals; a negative value with the minus sign."""
    s = f"{float(x):.{dp}f}"
    return MINUS + s[1:] if s.startswith("-") else s


def count(x: float | str) -> str:
    """A whole number with thousands separators ("52,952"); x is rounded half to even."""
    v = round(float(x))
    s = f"{v:,}"
    return MINUS + s[1:] if s.startswith("-") else s


def rng(lo: str, hi: str) -> str:
    return f"{lo}{TO}{hi}"


def pct(x: float | str, dp: int = 1) -> str:
    """A share as a percentage: 0.5875 -> "58.7%"."""
    return num(100 * float(x), dp) + "%"


def prob(x: float | str) -> str:
    """A probability such as P(top-5): two decimals, but 1 and 0 written in full only when exact
    ("1.00" for a value that rounds to 1 but is not 1 would hide a draw outside the top five)."""
    v = float(x)
    if v == 1.0:
        return "1"
    if v == 0.0:
        return "0"
    s = num(v, 2)
    if s == "1.00":
        return num(v, 3) if num(v, 3) != "1.000" else ">0.999"
    if s == "0.00":
        return num(v, 3) if num(v, 3) != "0.000" else "<0.001"
    return s


def rho(x: float | str) -> str:
    """A correlation: three decimals."""
    return num(x, 3)


def harm(mean: str, lo: str, hi: str) -> str:
    """Harm averted with its interval, in patients: "52,952 (52,109 to 53,797)"."""
    return f"{count(mean)} ({rng(count(lo), count(hi))})"


def day(iso: str) -> str:
    """'2026-11-20' -> '20 November 2026'."""
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def and_list(items: list[str]) -> str:
    """'A, B and C' (no item: 'none')."""
    if not items:
        return "none"
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def read_csv(root: Path, rel: str) -> list[dict]:
    with open(root / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def one(rows: list[dict], what: str, **kv) -> dict:
    hits = [r for r in rows if all(r[k] == v for k, v in kv.items())]
    if len(hits) != 1:
        raise ValueError(f"{what}: {len(hits)} rows match {kv}")
    return hits[0]
