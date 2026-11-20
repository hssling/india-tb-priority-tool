"""Read the long-format State panel (analysis plan §3.3, §5, §10.2).

Columns: ``unit, year, step, numerator, denominator, source_file, pdf_page, table_id,
flag``. ``numerator`` is the count of patients lost (S2-S6) or the number notified (S1);
``denominator`` is the base of the step (S2-S6) or the target (S1).

A cell is NA when its numerator or denominator is empty or its flag carries ``NA:``, and
also (§3.3) when its denominator is 0 or, for S2-S6, when its count lost is negative or
exceeds its denominator. For S1 notified above target is a valid value; only a zero
target makes the cell NA.
"""
from __future__ import annotations

import csv
from pathlib import Path

PANEL_COLS = ["unit", "year", "step", "numerator", "denominator", "source_file", "pdf_page",
              "table_id", "flag"]
NA_COLS = ["unit", "year", "step", "numerator", "denominator", "na", "reason", "source_file",
           "pdf_page", "table_id"]


def _int(s: str) -> int | None:
    s = s.strip()
    return None if s == "" else int(s)


def _na_reasons(step: str, num: int | None, den: int | None, flag: str) -> list[str]:
    reasons = [f for f in flag.split(";") if f.startswith("NA:")]
    if num is None or den is None:
        if not reasons:
            reasons.append("NA:empty_cell")
        return reasons
    extra = []
    if den == 0:
        extra.append("NA:denominator_zero")
    elif step != "S1":
        if num < 0:
            extra.append("NA:loss_negative")
        elif num > den:
            extra.append("NA:loss_exceeds_denominator")
    return reasons + [r for r in extra if r not in reasons]


def load(path) -> list[dict]:
    """Rows of the panel as dicts; ``year`` is an int, ``numerator`` and ``denominator``
    are ints (None when empty); ``na`` (bool) and ``na_reason`` (";"-joined) are added."""
    with open(Path(path), encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in PANEL_COLS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s) {', '.join(missing)}")
        out = []
        for r in reader:
            num, den = _int(r["numerator"]), _int(r["denominator"])
            reasons = _na_reasons(r["step"], num, den, r["flag"])
            out.append({
                "unit": r["unit"], "year": int(r["year"]), "step": r["step"],
                "numerator": num, "denominator": den, "source_file": r["source_file"],
                "pdf_page": r["pdf_page"], "table_id": r["table_id"], "flag": r["flag"],
                "na": bool(reasons), "na_reason": ";".join(reasons),
            })
    seen = set()
    for r in out:
        key = (r["unit"], r["step"], r["year"])
        if key in seen:
            raise ValueError(f"{path}: duplicate cell {key}")
        seen.add(key)
    return out


def load_population(path) -> dict[str, int | None]:
    """unit -> population (persons; ITR 2024 Annexure 1.1 lakhs x 100,000, §6.7)."""
    with open(Path(path), encoding="utf-8", newline="") as f:
        return {r["unit"]: _int(r["population"]) for r in csv.DictReader(f)}


def cells(rows: list[dict], step: str, year: int) -> list[dict]:
    """The non-NA cells of a step-year, in alphabetical order of unit name (§10.1)."""
    out = [r for r in rows if r["step"] == step and r["year"] == year and not r["na"]]
    return sorted(out, key=lambda r: r["unit"])


def step_years(rows: list[dict]) -> list[tuple[str, int]]:
    """Every (step, year) present in the panel, sorted."""
    return sorted({(r["step"], r["year"]) for r in rows})


def na_cells(rows: list[dict]) -> list[dict]:
    """Every NA or flagged cell, with the reason (§3.3, §10.2): the NA reason first, then
    the cell's flag."""
    out = []
    for r in rows:
        if not (r["na"] or r["flag"]):
            continue
        parts = [p for p in r["na_reason"].split(";") if p]
        parts += [f for f in r["flag"].split(";") if f and f not in parts]
        out.append({"unit": r["unit"], "year": r["year"], "step": r["step"],
                    "numerator": r["numerator"], "denominator": r["denominator"],
                    "na": r["na"], "reason": ";".join(parts), "source_file": r["source_file"],
                    "pdf_page": r["pdf_page"], "table_id": r["table_id"]})
    return out
