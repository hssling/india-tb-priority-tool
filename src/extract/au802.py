"""Extract the district TB notifications of Lok Sabha Unstarred Question 802 (answered
7 February 2025) for Madhya Pradesh and Maharashtra, 2022-2024 (analysis plan §9.2).

Run: python -I src/extract/au802.py

The Word file has two tables (Annexure-I/A, Madhya Pradesh; Annexure-I/B, Maharashtra),
each with two districts per row (``District | 2022 | 2023 | 2024 | | District | 2022 |
2023 | 2024``). Writes data/extracted/district_notifications.csv in the district input
schema of the tool (plan §9.3), one row per district and year:
``state, district, year, notified, source_file, table_id, flag``.

Rules:
- District names are mapped by the explicit list district_names.AU802; an unknown name
  raises KeyError naming it.
- Madhya Pradesh prints "Vidisha" twice with identical values: it is kept once with the
  flag ``duplicate_entry`` (plan §9.2). A repeated name with different values, or any
  other repeated name, is an error. The three districts created in 2023 are not printed
  and are not added.
- Every value cell must be a whole number; a blank or non-numeric cell is an error. There
  is no printed total row, so there is no printed-total check.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.extract import annex, cells, district_names  # noqa: E402

SOURCE_FILE = "data_raw/pq/AU802_LlE1Wb.docx"
OUT_CSV = ROOT / "data" / "extracted" / "district_notifications.csv"
TABLES = (  # (table index, State, table id, title as printed)
    (0, "Madhya Pradesh", "AU802 Annexure-I/A",
     "District-wise TB case notification in Madhya Pradesh for 2022-2024"),
    (1, "Maharashtra", "AU802 Annexure-I/B",
     "District-wise TB case notification in Maharashtra"),
)
YEARS = (2022, 2023, 2024)
HEADER = ["District", "2022", "2023", "2024", "", "District", "2022", "2023", "2024"]
FOOTER = "Data Source"
EXPECTED_UNITS = {"Madhya Pradesh": 52, "Maharashtra": 80}  # docs/data_inventory.md
EXPECTED_ENTRIES = {"Madhya Pradesh": 53, "Maharashtra": 80}
OUT_COLS = ["state", "district", "year", "notified", "source_file", "table_id", "flag"]


def entries(table_rows: list[list[str]], title: str) -> list[tuple[str, list[str]]]:
    """(name, [n2022, n2023, n2024]) for every printed district entry, in printed order:
    the left half of every row, then the right half (as printed: each half is one
    alphabetical run)."""
    if not table_rows or any(c.strip() != title for i, c in enumerate(table_rows[0])
                             if i != 4):
        raise ValueError(f"table title {title!r} not found")
    if [c.strip() for c in table_rows[1]] != HEADER:
        raise ValueError(f"unexpected header {table_rows[1]!r}")
    halves: tuple[list, list] = ([], [])
    for r in table_rows[2:]:
        c = [x.strip() for x in r]
        if c[0].startswith(FOOTER):
            continue
        if c[4]:
            raise ValueError(f"separator column not blank: {r!r}")
        for h, blk in enumerate((c[0:4], c[5:9])):
            if not any(blk):
                continue
            if not blk[0] or not all(blk[1:]):
                raise ValueError(f"blank cell in entry {blk!r}")
            halves[h].append((blk[0], blk[1:]))
    return halves[0] + halves[1]


def records(tables: list[list[list[str]]]) -> list[dict]:
    out: list[dict] = []
    for ti, state, table_id, title in TABLES:
        ents = entries(tables[ti], title)
        if len(ents) != EXPECTED_ENTRIES[state]:
            raise ValueError(f"{state}: {len(ents)} entries, expected "
                             f"{EXPECTED_ENTRIES[state]}")
        seen: dict[str, list[int]] = {}
        dup: set[str] = set()
        for raw, vals in ents:
            name = district_names.au802(state, raw)
            nums = [cells.parse_int(v) for v in vals]
            if name in seen:
                if seen[name] != nums or name in dup:
                    raise ValueError(f"{state}: {name!r} printed twice with values "
                                     f"{seen[name]} and {nums}")
                dup.add(name)
                continue
            seen[name] = nums
        if len(seen) != EXPECTED_UNITS[state]:
            raise ValueError(f"{state}: {len(seen)} distinct districts, expected "
                             f"{EXPECTED_UNITS[state]}")
        missing = sorted(set(district_names.AU802[state]) - set(seen))
        if missing:
            raise ValueError(f"{state}: districts in the crosswalk not printed: {missing}")
        for name in sorted(seen):
            for y, n in zip(YEARS, seen[name]):
                out.append({"state": state, "district": name, "year": y, "notified": n,
                            "source_file": SOURCE_FILE, "table_id": table_id,
                            "flag": "duplicate_entry" if name in dup else ""})
    return out


def read_docx(path: Path | None = None) -> list[list[list[str]]]:
    import docx  # python-docx; only the extraction needs it

    d = docx.Document(str(path or ROOT / SOURCE_FILE))
    return [[[c.text for c in r.cells] for r in t.rows] for t in d.tables]


def main() -> int:
    recs = records(read_docx())
    annex.write_csv(OUT_CSV, OUT_COLS, recs)
    for _, state, _, _ in TABLES:
        n = len({r["district"] for r in recs if r["state"] == state})
        dups = sorted({r["district"] for r in recs if r["state"] == state and r["flag"]})
        print(f"{state}: {n} districts; kept once and flagged duplicate_entry: {dups}")
    print(f"wrote {OUT_CSV.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
