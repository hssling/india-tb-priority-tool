# Adapted from hssling/india-state-tb-score (MIT), verification/check_extraction_totals.py
# (commit df8907d): the same "State sum = printed national row" check, SKIPPED when the
# source PDFs are absent. Changes: it reads this repository's State panel extraction
# (src/extract/itr_state.py); a difference is allowed only where it is recorded with its
# size in itr_state.RECORDED_GAPS (analysis plan §3.3); the committed CSVs are checked
# without the PDFs, and rebuilt from the PDFs byte for byte when they are present.
"""Check the State panel extraction against the printed India rows, writing nothing.

Run as: python -I verification/check_extraction_totals.py

1. data/extracted/state_cells.csv (committed): for every table and extracted
   column, the sum of the 36 printed State/UT rows equals the printed India row,
   except the differences recorded with their size in itr_state.RECORDED_GAPS,
   which must be present exactly as recorded.
2. data/extracted/state_panel.csv and state_population.csv (committed) equal
   the panel and population rebuilt from state_cells.csv.
3. If the source PDFs are in data_raw/: the tables are extracted again, check 1
   is repeated on the fresh extraction, and the three CSVs rebuilt from it are
   byte-identical to the committed files. If any PDF is absent this step is
   reported as SKIPPED (run tools/fetch_sources.py) and does not fail.

Exit 1 on any failed check.
"""
import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.extract import annex, crosswalk, itr_state  # noqa: E402

SKIP = "SKIPPED: source PDFs not present (run python -I tools/fetch_sources.py)"


def cell_total_problems(rows: list[dict]) -> list[str]:
    """Check 1 on the rows of state_cells.csv."""
    groups: dict[tuple[str, str], dict[str, str]] = {}
    for r in rows:
        groups.setdefault((r["table_key"], r["field"]), {})[r["printed_unit"]] = r["value"]
    checks = []
    for (key, fld), vals in groups.items():
        spec = itr_state.SPECS[key]
        conv = itr_state.Decimal if spec.field(fld).decimal else int
        expected = set(crosswalk.PRINTED[spec.year]) | {crosswalk.NATIONAL}
        if set(vals) != expected:
            return [f"{key} {fld}: printed rows {sorted(set(vals) ^ expected)} missing or extra"]
        if vals[crosswalk.NATIONAL] == "":
            return [f"{key} {fld}: the India row is blank"]
        states = [None if vals[u] == "" else conv(vals[u]) for u in crosswalk.PRINTED[spec.year]]
        s, nat, blanks = annex.total_gaps(states, conv(vals[crosswalk.NATIONAL]))
        checks.append({"table_key": key, "field": fld, "state_sum": s, "printed": nat,
                       "difference": s - nat, "blank_cells": blanks})
    missing = [k for k in itr_state.SPECS
               if not any(c["table_key"] == k for c in checks)]
    out = [f"table {k} has no rows in state_cells.csv" for k in missing]
    return out + itr_state.unrecorded_gaps(checks)


def _read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _written(rows: list[dict], cols: list[str]) -> bytes:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.csv"
        annex.write_csv(p, cols, rows)
        return p.read_bytes()


def rebuild_problems() -> list[str]:
    """Check 2: panel and population rebuilt from the committed cells."""
    t = itr_state.tables_from_cells(itr_state.CELLS_CSV)
    b = {"panel": itr_state.panel_rows(t), "population": itr_state.population_rows(t)}
    out = []
    for name, cols, path in (("panel", itr_state.PANEL_COLS, itr_state.PANEL_CSV),
                             ("population", itr_state.POP_COLS, itr_state.POP_CSV)):
        if _written(b[name], cols) != path.read_bytes():
            out.append(f"{path.name} differs from its rebuild from state_cells.csv")
    return out


def pdf_problems() -> list[str]:
    """Check 3: extract again from the PDFs and compare byte for byte."""
    tables = itr_state.read_all()
    out = itr_state.unrecorded_gaps(itr_state.total_checks(tables))
    with tempfile.TemporaryDirectory() as d:
        paths = itr_state.write_all(tables, Path(d))
        for name, committed in (("cells", itr_state.CELLS_CSV), ("panel", itr_state.PANEL_CSV),
                                ("population", itr_state.POP_CSV)):
            if paths[name].read_bytes() != committed.read_bytes():
                out.append(f"{committed.name} differs from a fresh extraction from the PDFs")
    return out


def main() -> int:
    failed = 0
    for label, fn in (("printed totals (state_cells.csv)",
                       lambda: cell_total_problems(_read(itr_state.CELLS_CSV))),
                      ("panel and population rebuilt from state_cells.csv", rebuild_problems)):
        try:
            bad = fn()
        except Exception as e:  # noqa: BLE001  any error is a failed check
            bad = [f"{type(e).__name__}: {e}"]
        for b in bad:
            print(f"FAIL: {b}")
        failed += bool(bad)
        if not bad:
            print(f"OK: {label}")
    for (k, f), (s, n) in itr_state.RECORDED_GAPS.items():
        print(f"RECORDED GAP: {k} {f}: State sum {s}, printed India {n}, difference {s - n}")
    pdfs = sorted({s.source_file for s in itr_state.SPECS.values()})
    absent = [p for p in pdfs if not (ROOT / p).exists()]
    if absent:
        print(f"{SKIP}; not re-extracted: {', '.join(absent)}")
    else:
        try:
            bad = pdf_problems()
        except Exception as e:  # noqa: BLE001
            bad = [f"{type(e).__name__}: {e}"]
        for b in bad:
            print(f"FAIL: {b}")
        failed += bool(bad)
        if not bad:
            print(f"OK: {len(itr_state.SPECS)} tables re-extracted from the PDFs; printed "
                  f"totals as recorded; the committed CSVs are reproduced byte for byte")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
