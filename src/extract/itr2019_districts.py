"""Extract ITR 2019 Annexure 1.13 "District Wise Indicators" (data year 2018; analysis plan
§9.1).

Run: python -I src/extract/itr2019_districts.py

Reads PDF pp. 188-220 of the India TB Report 2019 and writes
data/extracted/district_2018.csv: one row per printed district row (State | District),
with the printed counts of the 12 value columns, the printed percentages of the two
treatment-success columns, and ``source_file, pdf_page, table_id``. Nothing is computed
here (no difference, rate or cohort): D1 and D2 are formed in src/tbprio/district.py.

Rules:
- Rows are rebuilt from character positions (grid.lines_of). The State, District and value
  regions of each page are fixed by the header words "State", "District" and "Total". A
  line with at least MIN_ANCHOR_COUNTS counts in the value region is a row; every other
  line of the table body (a wrapped name fragment, or a count or percentage stacked above
  or below its row) is placed in the nearest row, which must be clearly nearer than any
  other. A count followed by a percentage is one cell; a percentage stacked below a count
  is joined to it (grid._cells).
- Columns are placed by position: on each page the rows that print all 12 cells give the
  column centres; a row with a blank cell (a private-sector treatment-success cell left
  blank: "NO private sector notified patients in the district during the year 2017") has
  each of its cells placed in the nearest column.
- The State name is mapped by the State crosswalk (crosswalk.printed_unit, data year 2018,
  not coarsened); the District name by the explicit list district_names.ITR2019, keyed by
  the State. An unknown string raises KeyError naming it.
- The printed India row is checked column by column against the sum of the district rows
  (blank cells left out). A difference is recorded with its size in RECORDED_GAPS (plan
  §3.3) and is not corrected; any other difference fails.
"""
from __future__ import annotations

import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.extract import annex, cells, crosswalk, district_names  # noqa: E402

SOURCE_FILE = "data_raw/india_tb_report/India-TB-Report-2019.pdf"
TABLE_ID = "Annexure 1.13"
TITLE = "1.13 District Wise Indicators"
PAGES = tuple(range(188, 221))
YEAR = 2018
OUT_CSV = ROOT / "data" / "extracted" / "district_2018.csv"

# The 12 value columns, in printed order (docs/data_inventory.md, verbatim headers).
COLUMNS: tuple[tuple[str, str], ...] = (
    ("notified", "Total TB patients Notified$"),
    ("notified_public", "TB patients notified from Public sector"),
    ("notified_private", "TB patients notified from Private sector"),
    ("paediatric", "Paediatric TB patients notified"),
    ("new", "New TB patients notified"),
    ("previously_treated", "Previously treated TB patients notified"),
    ("pmdt", "PMDT cases notified*"),
    ("initiated", "TB patients initiated on treatment-Total"),
    ("initiated_public", "TB patients initiated on treatment - Public Sector"),
    ("initiated_private", "TB patients initiated on treatment - Private Sector"),
    ("success_public", "Treatment success rate of TB notified patients (Public sector) 2017 "
                       "(N&%)"),
    ("success_private", "Treatment success rate of TB notified patients (Private sector) "
                        "2017 (N&%)"),
)
NCELLS = len(COLUMNS)
PCT_COLUMNS = ("success_public", "success_private")

# The printed India row (docs/data_inventory.md): counts, and the two N of "N (%)".
PRINTED_INDIA: dict[str, int] = {
    "notified": 2155894, "notified_public": 1613504, "notified_private": 542390,
    "paediatric": 133059, "new": 1876586, "previously_treated": 241460, "pmdt": 37848,
    "initiated": 1912521, "initiated_public": 1465502, "initiated_private": 447019,
    "success_public": 1079167, "success_private": 135400,
}

# Printed-total differences found at extraction (plan §3.3): column -> (sum of the
# district rows, printed India value). Recorded, not corrected.
RECORDED_GAPS: dict[str, tuple[int, int]] = {
    # The India row prints 2 more notified (public sector, new) and 2 more initiated
    # (public sector) patients than its district rows sum to; every district row satisfies
    # notified = public + private = new + previously treated + PMDT and initiated = public
    # + private, so the gap is in the printed table (21 Nov 2026).
    "notified": (2155892, 2155894),
    "notified_public": (1613502, 1613504),
    "new": (1876584, 1876586),
    "initiated": (1912519, 1912521),
    "initiated_public": (1465500, 1465502),
    # The district rows sum to 27 fewer public-sector treatment successes (2017 cohort)
    # than the India row prints; 754 of the 761 cells were cross-read from the text lines
    # (pdftext.page_lines) and the 7 stacked cells by eye (21 Nov 2026).
    "success_public": (1079140, 1079167),
}

OUT_COLS = (["state", "district", "printed_state", "printed_district", "row"]
            + [c for c, _ in COLUMNS[:10]]
            + ["success_public_n", "success_public_pct", "success_private_n",
               "success_private_pct", "source_file", "pdf_page", "table_id", "flag"])

MIN_ANCHOR_COUNTS = 8
MAX_ROW_DIST = 0.75  # x row pitch: a three-line name spreads 0.7 pitch
NEAR_RATIO = 0.7
STACK_DV = 1.0  # x row pitch


@dataclass
class DistrictRow:
    printed_state: str
    printed_district: str
    page: int
    cells: list[annex.Cell | None]


def _region(t, sd: float, dv: float) -> str:
    if t.u1 <= sd:
        return "S"
    if t.u0 >= dv:
        return "V"
    if t.u0 >= sd and t.u1 <= dv:
        return "D"
    raise ValueError(f"token {t.text!r} at u {t.u0:.1f}-{t.u1:.1f} straddles a column "
                     f"boundary ({sd:.1f}, {dv:.1f})")


def read_page(chars: list[dict], width: float, height: float, page: int
              ) -> tuple[list[DistrictRow], list[annex.Cell | None] | None]:
    """The district rows and the India row (if printed) of one page."""
    from src.extract import grid

    lines = grid.lines_of(chars, width, height)
    hdr = [ln for ln in lines
           if any(t.text == "State" for t in ln.tokens)
           and any(t.text == "District" for t in ln.tokens)]
    if len(hdr) != 1:
        raise ValueError(f"PDF p. {page}: {len(hdr)} header lines with 'State' and 'District'")
    h = hdr[0]
    st = next(t for t in h.tokens if t.text == "State")
    di = next(t for t in h.tokens if t.text == "District")
    tot = [t for ln in lines for t in ln.tokens
           if t.text == "Total" and t.u0 > di.u1 and abs(ln.v - h.v) < 30]
    if len(tot) != 1:
        raise ValueError(f"PDF p. {page}: header word 'Total' not found once")
    dv = tot[0].u0 - 3.0
    nah = [ln.v for ln in lines if any(t.text == "(N&%)" for t in ln.tokens)]
    if not nah:
        raise ValueError(f"PDF p. {page}: header '(N&%)' not found")
    body_start = max(v for v in nah if v < h.v + 60)

    body = [ln for ln in lines if ln.v > body_start]
    # The District column is left-aligned: its left edge is the most common start of a
    # word between the "State" and "District" header words.
    starts = [round(t.u0) for ln in body for t in ln.tokens if st.u1 + 5 < t.u0 < di.u0]
    if not starts:
        raise ValueError(f"PDF p. {page}: no District column")
    sd = statistics.mode(starts) - 1.5
    regions = []
    for ln in body:
        try:
            regions.append([_region(t, sd, dv) for t in ln.tokens])
        except ValueError:
            regions.append(None)  # resolved below: only footnotes may straddle
    anchors = [i for i, ln in enumerate(body) if regions[i] is not None and
               sum(1 for t, r in zip(ln.tokens, regions[i])
                   if r == "V" and annex.kind(t.text) == "count") >= MIN_ANCHOR_COUNTS]
    if not anchors:
        raise ValueError(f"PDF p. {page}: no table row")
    av = [body[i].v for i in anchors]
    pitch = statistics.median(b - a for a, b in zip(av, av[1:])) if len(av) > 1 else 15.0
    maxd = MAX_ROW_DIST * pitch

    # A line that crosses a column boundary is a footnote: it must lie below the last row.
    for i, ln in enumerate(body):
        if regions[i] is None and ln.v < av[-1]:
            raise ValueError(f"PDF p. {page}: line straddles a column inside the table: "
                             f"{ln.text!r}")
    inside = [i for i, ln in enumerate(body)
              if regions[i] is not None and av[0] - pitch < ln.v < av[-1] + pitch]

    # Values: a count or percentage stacked on a line of its own belongs to the nearest
    # row, which must be clearly nearer than any other.
    owner: dict[int, int] = {i: j for j, i in enumerate(anchors)}  # value line -> row
    for i in inside:
        if i in owner or "V" not in regions[i]:
            continue
        d = sorted((abs(body[i].v - v), j) for j, v in enumerate(av))
        if d[0][0] > maxd or (len(d) > 1 and d[0][0] > NEAR_RATIO * d[1][0]):
            raise ValueError(f"PDF p. {page}: values {body[i].text!r} cannot be placed in "
                             f"a row")
        owner[i] = d[0][1]

    # Names: a wrapped name is set vertically centred on its row, so in each name column
    # a row has as many fragment lines below its value line as above it. Walking down the
    # page, the fragments between two rows go first to the row above (as many as it has
    # above it) and the rest to the row below.
    name_owner: dict[tuple[int, str], int] = {}
    for col in ("S", "D"):
        for j, i in enumerate(anchors):
            name_owner[(i, col)] = j
        frag = [i for i in inside if i not in owner and col in regions[i]]
        frag += [i for i in owner if i not in anchors and col in regions[i]]
        frag.sort(key=lambda i: body[i].v)
        above = [i for i in frag if body[i].v < av[0]]
        for i in above:
            name_owner[(i, col)] = 0
        k = len(above)
        for j in range(len(anchors)):
            hi = av[j + 1] if j + 1 < len(anchors) else av[j] + pitch
            gap = [i for i in frag if av[j] < body[i].v < hi]
            if len(gap) < k:
                if j + 1 < len(anchors):
                    raise ValueError(f"PDF p. {page}: the name of row {j + 1} is not "
                                     f"centred on its values (column {col})")
                raise ValueError(f"PDF p. {page}: the name of the last row is not centred "
                                 f"on its values (column {col})")
            for i in gap[:k]:
                name_owner[(i, col)] = j
            for i in gap[k:]:
                if j + 1 >= len(anchors):
                    raise ValueError(f"PDF p. {page}: name fragment after the last row: "
                                     f"{body[i].text!r}")
                name_owner[(i, col)] = j + 1
            k = len(gap) - k
        for i in frag:
            j = name_owner[(i, col)]
            if abs(body[i].v - av[j]) > pitch:
                raise ValueError(f"PDF p. {page}: name fragment {body[i].text!r} lies more "
                                 f"than a row pitch from its row")

    # value cells, with stacked percentages joined to their counts
    vlines = []
    for i, ln in enumerate(body):
        vl = grid.Line(ln.v, ln.tokens)
        vl.values = ([t for t, r in zip(ln.tokens, regions[i]) if r == "V"]
                     if i in owner else [])
        vlines.append(vl)
    pcs = grid._cells(vlines, STACK_DV * pitch)
    per_row: list[list] = [[] for _ in anchors]
    for c in pcs:
        rows_of = {owner[c.line]} | ({owner[c.pct_line]} if c.pct_line is not None else set())
        if len(rows_of) != 1:
            raise ValueError(f"PDF p. {page}: cell {c.cell().raw!r} spans two rows")
        per_row[rows_of.pop()].append(c)

    names: list[tuple[str, str]] = []
    for j in range(len(anchors)):
        parts = []
        for col in ("S", "D"):
            own = sorted((i for (i, c), r in name_owner.items() if c == col and r == j),
                         key=lambda i: body[i].v)
            parts.append(" ".join(t.text for i in own
                                  for t, r in zip(body[i].tokens, regions[i]) if r == col))
        names.append((parts[0], parts[1]))

    for j, cs in enumerate(per_row):
        cs.sort(key=lambda c: c.uc)
        if len(cs) > NCELLS:
            raise ValueError(f"PDF p. {page}: row {names[j]}: {len(cs)} cells: "
                             f"{[c.cell().raw for c in cs]}")
    full = [cs for cs in per_row if len(cs) == NCELLS]
    if not full:
        raise ValueError(f"PDF p. {page}: no row prints all {NCELLS} cells")
    centre = [statistics.median(cs[k].uc for cs in full) for k in range(NCELLS)]

    def nearest(u: float) -> int:
        return min(range(NCELLS), key=lambda k: abs(u - centre[k]))

    rows: list[DistrictRow] = []
    national = None
    for (sname, dname), cs in zip(names, per_row):
        placed: list[annex.Cell | None] = [None] * NCELLS
        for k0, c in enumerate(cs):
            k = k0 if len(cs) == NCELLS else nearest(c.uc)
            if nearest(c.uc) != k:
                raise ValueError(f"PDF p. {page}: {sname} | {dname}: cell {c.cell().raw!r} "
                                 f"lies nearer column {nearest(c.uc) + 1} than {k + 1}")
            if placed[k] is not None:
                raise ValueError(f"PDF p. {page}: {sname} | {dname}: two cells in column "
                                 f"{k + 1}")
            placed[k] = c.cell()
        if crosswalk.is_national(sname) and not dname:
            if national is not None:
                raise ValueError(f"PDF p. {page}: two India rows")
            national = placed
            continue
        if not sname or not dname:
            raise ValueError(f"PDF p. {page}: row without a State or District name: "
                             f"{sname!r} | {dname!r}")
        rows.append(DistrictRow(sname, dname, page, placed))
    return rows, national


def read_pdf(pdf_path: Path | None = None
             ) -> tuple[list[DistrictRow], list[annex.Cell | None]]:
    import pdfplumber

    from src.extract import grid, pdftext

    path = pdf_path or ROOT / SOURCE_FILE
    rows: list[DistrictRow] = []
    national = None
    with pdfplumber.open(path) as pdf:
        for p in PAGES:
            chars, w, h = pdftext.page_chars(pdf, p)
            if p == PAGES[0]:
                text = "".join("".join(t.text for t in ln.tokens)
                               for ln in grid.lines_of(chars, w, h)).casefold()
                if "".join(TITLE.split()).casefold() not in text:
                    raise ValueError(f"title {TITLE!r} not on PDF p. {p}")
            r, nat = read_page(chars, w, h, p)
            rows += r
            if nat is not None:
                if national is not None:
                    raise ValueError("two India rows")
                national = nat
    if national is None:
        raise ValueError("no India row")
    return rows, national


def _pct(c: annex.Cell, where: str) -> str:
    """'(95%)' -> '95'; '(0.2%)' -> '0.2' (the percentage as printed)."""
    s = (c.pct or "").strip()
    if not (s.startswith("(") and s.endswith("%)")):
        raise ValueError(f"{where}: not a percentage {c.pct!r} (cell {c.raw!r})")
    v = s[1:-2].strip()
    float(v)
    return v


def records(rows: list[DistrictRow]) -> list[dict]:
    """One output row per printed district row, in printed order; names mapped by the
    crosswalks (KeyError naming an unknown string)."""
    out = []
    seen = set()
    for i, r in enumerate(rows, start=1):
        state = crosswalk.printed_unit(r.printed_state, YEAR)
        district = district_names.itr2019(state, r.printed_district)
        if (state, district) in seen:
            raise ValueError(f"district printed twice: {state} | {district}")
        seen.add((state, district))
        where = f"PDF p. {r.page} {state} | {district}"
        rec: dict = {"state": state, "district": district, "printed_state": r.printed_state,
                     "printed_district": r.printed_district, "row": i,
                     "source_file": SOURCE_FILE, "pdf_page": r.page, "table_id": TABLE_ID}
        flags = []
        for k, (name, _) in enumerate(COLUMNS):
            c = r.cells[k]
            if name in PCT_COLUMNS:
                if c is None or c.n is None:
                    rec[f"{name}_n"] = rec[f"{name}_pct"] = None
                    flags.append(f"{name}_blank")
                    continue
                try:
                    rec[f"{name}_n"] = cells.parse_int(c.n)
                except ValueError as e:
                    raise ValueError(f"{where} {name}: {e}") from None
                rec[f"{name}_pct"] = _pct(c, f"{where} {name}")
                continue
            if c is None or c.n is None:
                raise ValueError(f"{where}: blank {name} cell")
            if c.pct is not None:
                raise ValueError(f"{where}: {name} has a percentage {c.raw!r}")
            try:
                rec[name] = cells.parse_int(c.n)
            except ValueError as e:
                raise ValueError(f"{where} {name}: {e}") from None
        rec["flag"] = ";".join(flags)
        out.append(rec)
    expected = district_names.itr2019_count()
    if len(out) != expected:
        listed = {(s, d) for s, ds in district_names.ITR2019.items() for d in ds}
        missing = sorted(listed - seen)
        raise ValueError(f"{len(out)} district rows, the crosswalk lists {expected}; "
                         f"not printed: {missing}")
    return out


def national_values(national: list[annex.Cell | None]) -> dict[str, int]:
    out = {}
    for k, (name, _) in enumerate(COLUMNS):
        c = national[k]
        if c is None or c.n is None:
            raise ValueError(f"India row: blank {name}")
        out[name] = cells.parse_int(c.n)
    return out


def total_checks(recs: list[dict]) -> list[dict]:
    """Per column: sum of the district rows (blank cells left out), printed India value,
    the difference and the number of blank cells."""
    out = []
    for name, _ in COLUMNS:
        key = f"{name}_n" if name in PCT_COLUMNS else name
        s, nat, blanks = annex.total_gaps([r[key] for r in recs], PRINTED_INDIA[name])
        out.append({"column": name, "district_sum": s, "printed": nat, "difference": s - nat,
                    "blank_cells": blanks})
    return out


def unrecorded_gaps(checks: list[dict]) -> list[str]:
    bad = []
    for c in checks:
        k = c["column"]
        if c["difference"] != 0:
            if RECORDED_GAPS.get(k) != (c["district_sum"], c["printed"]):
                bad.append(f"A1.13 {k}: district sum {c['district_sum']} vs printed India "
                           f"{c['printed']} (difference {c['difference']}) is not recorded")
        elif k in RECORDED_GAPS:
            bad.append(f"A1.13 {k}: recorded gap {RECORDED_GAPS[k]} no longer present")
    return bad


def read_csv(path: Path = OUT_CSV) -> list[dict]:
    """district_2018.csv read back, with the count columns as ints (None when blank)."""
    import csv

    ints = [c for c, _ in COLUMNS[:10]] + ["success_public_n", "success_private_n", "row",
                                           "pdf_page"]
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            d = dict(r)
            for k in ints:
                d[k] = None if d[k] == "" else int(d[k])
            for k in ("success_public_pct", "success_private_pct"):
                d[k] = None if d[k] == "" else d[k]
            out.append(d)
    return out


def write(recs: list[dict], path: Path = OUT_CSV) -> Path:
    annex.write_csv(path, OUT_COLS, recs)
    return path


def main() -> int:
    rows, national = read_pdf()
    recs = records(rows)
    nat = national_values(national)
    if nat != PRINTED_INDIA:
        print(f"FAIL: the India row read from the PDF {nat} differs from the printed row "
              f"recorded in the inventory {PRINTED_INDIA}")
        return 1
    checks = total_checks(recs)
    for c in checks:
        mark = "ok" if c["difference"] == 0 else "GAP"
        print(f"{mark}: A1.13 {c['column']}: district sum {c['district_sum']}, printed India "
              f"{c['printed']}, blanks {c['blank_cells']}")
    bad = unrecorded_gaps(checks)
    for b in bad:
        print(f"FAIL: {b}")
    if bad:
        return 1
    states = sorted({r["state"] for r in recs})
    print(f"{len(recs)} district rows in {len(states)} States/UTs")
    print(f"wrote {write(recs).relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
