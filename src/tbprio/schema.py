"""The district input schema of the tool (analysis plan §9.3).

Required columns: ``district, year, notified``. Optional: ``state``, ``target``,
``population`` and any ``cascade_*`` column; and the provenance columns ``flag``,
``source_file``, ``table_id``, ``pdf_page``. Column names are matched after trimming spaces
and ignoring case. Any other column is dropped with a warning.

- A row whose district is "Total" (or "Grand Total", "State Total", "All", "All
  districts"; any case) is dropped with a warning: it is a total, not a district. A
  district named like its State (Chandigarh) is kept.
- A missing required column is an error that names it.
- ``year`` must be a whole number; ``notified`` and the optional count columns must be
  whole numbers >= 0 (blank is allowed for the optional columns only).
- The same (state, district, year) twice is an error.
- Blank lines and lines starting with "#" (comments, such as the label of a synthetic
  example) are skipped by ``read_csv``.
"""
from __future__ import annotations

import csv
import io
import re
import warnings
from pathlib import Path

REQUIRED = ("district", "year", "notified")
OPTIONAL = ("state", "target", "population")
CASCADE_PREFIX = "cascade_"
PROVENANCE = ("flag", "source_file", "table_id", "pdf_page")
TOTAL_NAMES = frozenset({"total", "grand total", "state total", "all", "all districts"})


class SchemaError(ValueError):
    """The input does not follow the district schema; the message says what to fix."""


class SchemaWarning(UserWarning):
    pass


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def _count(v: str, col: str, where: str, required: bool) -> int | None:
    s = (v or "").strip().replace(",", "")
    if s == "":
        if required:
            raise SchemaError(f"{where}: {col} is blank")
        return None
    if not re.fullmatch(r"\d+(\.0+)?", s):
        raise SchemaError(f"{where}: {col} = {v!r} is not a whole number >= 0")
    return int(float(s)) if "." in s else int(s)


def validate_district(rows: list[dict]) -> list[dict]:
    """Validated rows: ``district`` and ``state`` (str; state "" when absent), ``year``
    and ``notified`` (int), the optional count columns (int or None), the provenance
    columns (str). Raises SchemaError; warns (SchemaWarning) on dropped rows or columns."""
    rows = list(rows)
    if not rows:
        raise SchemaError("the input has no rows")
    cols = list(rows[0].keys())
    for r in rows[1:]:
        if list(r.keys()) != cols:
            raise SchemaError("rows have different columns")
    by_key: dict[str, str] = {}
    for c in cols:
        if c is None:
            raise SchemaError("a row has more cells than the header")
        k = _key(c)
        if k in by_key:
            raise SchemaError(f"column {c!r} appears twice")
        by_key[k] = c
    missing = [c for c in REQUIRED if c not in by_key]
    if missing:
        raise SchemaError(
            f"missing required column(s): {', '.join(missing)}. The district input needs "
            f"the columns {', '.join(REQUIRED)}; optional: {', '.join(OPTIONAL)}, "
            f"{CASCADE_PREFIX}* (found: {', '.join(repr(c) for c in cols)})")
    counts = [k for k in by_key if k in ("target", "population")
              or k.startswith(CASCADE_PREFIX)]
    keep = set(REQUIRED) | {"state"} | set(counts) | {k for k in by_key if k in PROVENANCE}
    dropped = [by_key[k] for k in by_key if k not in keep]
    if dropped:
        warnings.warn(f"column(s) not in the district schema, ignored: "
                      f"{', '.join(dropped)}", SchemaWarning, stacklevel=2)

    out: list[dict] = []
    seen = set()
    for i, r in enumerate(rows, start=2):  # line 1 is the header
        get = {k: (r[by_key[k]] or "") for k in by_key}
        district = re.sub(r"\s+", " ", get["district"]).strip()
        state = re.sub(r"\s+", " ", get.get("state", "")).strip()
        where = f"row {i} ({district or 'no district'})"
        if not district:
            raise SchemaError(f"{where}: district is blank")
        if _key(district) in TOTAL_NAMES:
            warnings.warn(f"{where}: a total row, dropped", SchemaWarning, stacklevel=2)
            continue
        year_s = get["year"].strip()
        if not re.fullmatch(r"\d{4}", year_s):
            raise SchemaError(f"{where}: year = {get['year']!r} is not a four-digit year")
        rec = {"state": state, "district": district, "year": int(year_s),
               "notified": _count(get["notified"], "notified", where, True)}
        for k in counts:
            rec[k] = _count(get[k], k, where, False)
        for k in PROVENANCE:
            if k in by_key:
                rec[k] = get[k].strip()
        key = (state.casefold(), district.casefold(), rec["year"])
        if key in seen:
            raise SchemaError(f"{where}: {state + ' | ' if state else ''}{district} "
                              f"{rec['year']} appears twice")
        seen.add(key)
        out.append(rec)
    if not out:
        raise SchemaError("no district rows left after dropping total rows")
    return out


def read_csv(path) -> list[dict]:
    """The rows of a district CSV, skipping blank lines and "#" comment lines, validated."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise SchemaError(f"{path}: no header line")
    reader = csv.DictReader(io.StringIO("\n".join(lines) + "\n"))
    return validate_district(list(reader))
