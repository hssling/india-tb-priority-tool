"""Extract the State panel (steps S1-S6) and the 2023 population (analysis plan §3-§5).

Run: python -I src/extract/itr_state.py

Reads the annexure tables named in plan §5.2 from the India TB Reports in
data_raw/ (ITR 2019, ITR 2020, TBAR 2022, ITR 2023, ITR 2024; ITR 2021 is not
used, §3.2) and writes:

- data/extracted/state_cells.csv: every extracted printed cell, one row per
  printed row (36 State/UT rows and the India row) and column, before
  coarsening, with its page;
- data/extracted/state_panel.csv: one row per coarsened unit (33), data year
  and step: ``unit, year, step, numerator, denominator, source_file, pdf_page,
  table_id, flag``. ``numerator`` is the count lost at the step (S2-S6) or the
  number notified (S1); ``denominator`` is the base of the step (S2-S6) or the
  target (S1). Where a step's count lost is printed as "base minus kept" (S2,
  S5, S6), it is formed here from the two printed counts; nothing else is
  computed (no rate, harm or estimate). The S6 2022 denominator is the ITR 2023
  Annexure 1.6 notified count by sex (male + female + transgender), by the
  plan §12.2 deviation;
- data/extracted/state_panel_s6_2022_registered.csv: the S6 2022 rows on the
  registered basis (ITR 2023 Annexure 1.2, plan §5.2), kept as a sensitivity
  (plan §12.2); same columns as state_panel.csv;
- data/extracted/state_population.csv: the ITR 2024 Annexure 1.1 population of
  each coarsened unit, in lakhs as printed (summed over merged rows) and
  multiplied by 100,000 (§5.2).

Rules (plan §3.3, §4):
- Every table is compared with its printed India row, column by column, for
  the extracted columns (sum of the 36 printed State/UT rows, blank cells left
  out). A difference is recorded with its size (RECORDED_GAPS) and not
  corrected; the State values are used as printed.
- Printed rows are mapped by src/extract/crosswalk.py and merged rows are
  summed into their unit before the count lost is formed. A member row that
  is absent, or whose needed cells are blank, adds nothing; the unit carries
  ``member_missing:<row>``. A unit whose members are all missing is NA.
- A cell is NA (numerator and denominator left empty, flag ``NA:<reason>``)
  when its count lost is negative, exceeds its denominator, or its denominator
  is 0. For S1 only a zero target makes the cell NA (notified above target is
  a valid value).

``pdf_page`` lists the pages of the printed rows read for the unit (all its
member rows, ascending, ";"-joined); ``table_id`` lists the tables used, the
table of the count lost (S3, S4), of the count kept (S2, S5, S6) or of the
notified count (S1) first, then the table of the denominator.

Printed rows are found by name (crosswalk) and cells are placed by their
position on the page (grid.py); the pages are those fixed in plan §5.2, and
each is checked for the table's title (first page) and a header line.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.extract import annex, cells, crosswalk  # noqa: E402

EXTRACTED = ROOT / "data" / "extracted"
CELLS_CSV = EXTRACTED / "state_cells.csv"
PANEL_CSV = EXTRACTED / "state_panel.csv"
POP_CSV = EXTRACTED / "state_population.csv"
S6_2022_REGISTERED_CSV = EXTRACTED / "state_panel_s6_2022_registered.csv"

CELL_COLS = ["edition", "year", "table_key", "table_id", "pdf_page", "printed_name",
             "printed_unit", "unit", "field", "column_header", "cell_printed", "value"]
PANEL_COLS = ["unit", "year", "step", "numerator", "denominator", "source_file", "pdf_page",
              "table_id", "flag"]
POP_COLS = ["unit", "year", "population_lakhs", "population", "source_file", "pdf_page",
            "table_id", "flag"]

FILES = {
    "ITR 2019": "data_raw/india_tb_report/India-TB-Report-2019.pdf",
    "ITR 2020": "data_raw/india_tb_report/ITR2020.pdf",
    "TBAR 2022": "data_raw/india_tb_report/TBAnnaulReport2022.pdf",
    "ITR 2023": "data_raw/india_tb_report/ITR2023.pdf",
    "ITR 2024": "data_raw/india_tb_report/ITR2024.pdf",
}
YEAR_OF = {"ITR 2019": 2018, "ITR 2020": 2019, "TBAR 2022": 2021, "ITR 2023": 2022,
           "ITR 2024": 2023}

STEPS = ("S1", "S2", "S3", "S4", "S5", "S6")


@dataclass(frozen=True)
class Field:
    name: str
    index: int  # 0-based value cell after the name
    header: str  # verbatim column header (plan §5.2)
    decimal: bool = False


@dataclass(frozen=True)
class TableSpec:
    key: str
    edition: str
    table_id: str
    pages: tuple[int, ...]
    ncells: int  # value cells per row
    fields: tuple[Field, ...]
    title: str | None  # text on the first page (None: the title is not in the text layer)
    header: str  # text on every page
    region: tuple[float, float] | None = None  # part of the page width (TBAR 2022 spreads)

    @property
    def year(self) -> int:
        return YEAR_OF[self.edition]

    @property
    def source_file(self) -> str:
        return FILES[self.edition]

    def field(self, name: str) -> Field:
        return next(f for f in self.fields if f.name == name)


F = Field
SPECS: dict[str, TableSpec] = {s.key: s for s in (
    # ---- ITR 2019 (data year 2018)
    TableSpec("ITR2019_A1.2", "ITR 2019", "Annexure 1.2", (169, 170), 11, (
        F("notified", 0, "Total TB patients Notified (notified cases based on current PHI)"),
        F("hiv_known", 1, "Total TB patients with known HIV status (%)#: count part"),
    ), "1.2 TB Comorbidities", "HIV positive"),
    TableSpec("ITR2019_A1.4.a", "ITR 2019", "Annexure 1.4.a", (172, 173), 22, (
        F("public_notified", 0, "Public Sector: TB patients Notified*"),
        F("public_died", 6, "Public Sector: Died"),
        F("private_notified", 15, "Private Sector: TB patients Notified*"),
        F("private_died", 18, "Private Sector: Died"),
    ), "1.4.a Treatment outcome of TB patients notified in", "Public Sector"),
    # ---- ITR 2020 (data year 2019)
    TableSpec("ITR2020_A1.4", "ITR 2020", "Annexure 1.4", (206,), 6, (
        F("net_notified", 3, "Net TB Patients Notified: Total"),
    ), "1.4 Patient Transfer Status", "Net TB Patients Notified"),
    TableSpec("ITR2020_A2.1", "ITR 2020", "Annexure 2.1", (211,), 6, (
        F("hiv_known", 2, "TB patients with known HIV status (%): Total, count part"),
    ), "2.1 TB – HIV", "TB patients with known HIV status (%)"),
    TableSpec("ITR2020_A3.3", "ITR 2020", "Annexure 3.3", (224, 225), 9, (
        F("cohort_notified", 0, "TB patients Notified"),
        F("died", 4, "Death Rate: count part"),
        F("ltfu", 6, "% Lost to follow up: count part"),
    ), "3.3 Treatment outcome of TB patients notified in 2018 (Total)", "Death Rate"),
    # ---- TB Annual Report 2022 (data year 2021); two printed pages per PDF page
    TableSpec("TBAR2022_A1.2", "TBAR 2022", "Annexure 1.2", (89,), 9, (
        F("target", 2, "Target TB patients expected to be notified: Total"),
        F("notified", 5, "TB patients notified (Achievement against target %): Total, count part"),
    ), "1.2 TB Case Notification", "Target TB patients expected to be notified"),
    TableSpec("TBAR2022_A1.4", "TBAR 2022", "Annexure 1.4", (91,), 5, (
        F("net_notified", 3, "Net TB Patients Notified"),
    ), "1.4 Patient Transfer Status & Treatment Initiation Status", "Net TB",
        region=(0.0, 0.5)),
    TableSpec("TBAR2022_A2.1", "TBAR 2022", "Annexure 2.1", (94,), 6, (
        F("hiv_known", 2, "TB patients with known HIV status (%): Total, count part"),
    ), "2.1 TB – HIV", "TB patients with known HIV status (%)", region=(0.0, 0.5)),
    TableSpec("TBAR2022_A3.3", "TBAR 2022", "Annexure 3.3", (102,), 9, (
        F("cohort_notified", 0, "TB patients Notified"),
        F("died", 4, "Death Rate: count part"),
        F("ltfu", 5, "% Lost to follow up: count part"),
    ), "3.3 Treatment outcome of TB patients notified in 2020 (Total)", "Death Rate"),
    # ---- ITR 2023 (data year 2022)
    TableSpec("ITR2023_A1.2", "ITR 2023", "Annexure 1.2", (213, 214), 9, (
        F("target", 2, "Target TB patients expected to be notified: Total"),
        F("notified", 5, "TB patients notified, n (% achievement against target): Total, "
                         "count part"),
    ), None, "Target TB patients expected"),
    TableSpec("ITR2023_A1.6", "ITR 2023", "Annexure 1.6", (221, 222), 9, (
        F("notified_male", 0, "TB Cases Notified: Male"),
        F("notified_female", 1, "TB Cases Notified: Female"),
        F("notified_transgender", 2, "TB Cases Notified: Trans Gender"),
    ), "1.6 GENDER DISAGGREGATED DATA ON TOTAL TB NOTIFICATION", "TB Cases Notified"),
    TableSpec("ITR2023_A2.1", "ITR 2023", "Annexure 2.1", (225,), 3, (
        F("hiv_known", 2, "TB patients with known HIV status, n (%): Total, count part"),
    ), "2.1 SCREENING FOR HIV IN NOTIFIED TB", "TB patients with known HIV status, n (%)"),
    TableSpec("ITR2023_A3.3", "ITR 2023", "Annexure 3.3", (251, 252), 8, (
        F("cohort_notified", 0, "TB patients Notified"),
        F("died", 3, "Death Rate, n (%): count part"),
        F("ltfu", 4, "Lost to follow up, n (%): count part"),
    ), "3.3 TREATMENT OUTCOME OF TB PATIENTS", "Death"),
    # ---- ITR 2024 (data year 2023)
    TableSpec("ITR2024_A1.1", "ITR 2024", "Annexure 1.1", (185, 186), 10, (
        F("population_lakhs", 0, "Population - 2023 (in lakhs)", decimal=True),
    ), "1.1. Presumptive TB cases examination", "Population -"),
    TableSpec("ITR2024_A1.2", "ITR 2024", "Annexure 1.2", (187, 188), 9, (
        F("target", 2, "Target of TB patients expected to be notified: Total"),
        F("notified", 5, "TB patients notified, n(% of achievement against target): Total, "
                         "count part"),
    ), "1.2. TB case notification", "Target of TB patients expected"),
    TableSpec("ITR2024_A1.4", "ITR 2024", "Annexure 1.4", (191, 192), 9, (
        F("net_notified", 5, "Net TB patients* notified (Based on current PHI): Total"),
    ), "1.4. Patient transfer status and treatment initiation status",
        "Net TB patients* notified"),
    TableSpec("ITR2024_A2.1", "ITR 2024", "Annexure 2.1", (199,), 3, (
        F("hiv_known", 2, "TB patients with known HIV status, n (%): Total, count part"),
    ), "2.1. TB patients with known HIV status", "TB patients with known HIV status, n (%)"),
    TableSpec("ITR2024_A3.3", "ITR 2024", "Annexure 3.3", (222, 223), 8, (
        F("cohort_notified", 0, "TB patients notified"),
        F("died", 3, "Death rate, n(%): count part"),
        F("ltfu", 4, "Lost to follow up, n(%): count part"),
    ), "3.3. Treatment outcome of TB patients notified in 2022 (total)", "Death rate"),
    TableSpec("ITR2024_A4.7", "ITR 2024", "Annexure 4.7", (260, 261, 262), 12, (
        F("bact_confirmed", 5, "No. of bacteriological confirmed TB cases among notified: "
                               "Total, count part"),
        F("rr_tested", 8, "No. of bacteriologically confirmed TB cases with valid rapid DRT "
                          "result for at least rifampicin (RS/RR): Total, count part"),
    ), "4.7. PMDT case finding in 2023 - I", "valid rapid DRT result"),
    TableSpec("ITR2024_A4.13", "ITR 2024", "Annexure 4.13", (273, 274), 7, (
        F("cohort_initiated", 0, "Total MDR/RR-TB initiated on treatment"),
        F("success", 2, "Treatment success: count part"),
    ), "4.13. Treatment outcome of MDR/RR-TB cases initiated on treatment in 2021",
        "Treatment"),
)}


# ---- steps (plan §5.2) ------------------------------------------------------------

@dataclass(frozen=True)
class Recipe:
    """How one step-year is built. `base` is summed; `lost` is the printed count
    lost (S3, S4) or None; `kept` is subtracted from `base` (S2, S5, S6); for S1
    `base` is the target and `kept` the notified count (numerator = notified)."""
    step: str
    year: int
    base: tuple[tuple[str, str], ...]
    lost: tuple[tuple[str, str], ...] | None
    kept: tuple[tuple[str, str], ...] | None
    flags: tuple[str, ...] = ()


_NOTE_2023 = "note_numerator_initiated_denominator_notified_current_facility"
RECIPES: tuple[Recipe, ...] = (
    Recipe("S1", 2021, (("TBAR2022_A1.2", "target"),), None, (("TBAR2022_A1.2", "notified"),)),
    Recipe("S1", 2022, (("ITR2023_A1.2", "target"),), None, (("ITR2023_A1.2", "notified"),)),
    Recipe("S1", 2023, (("ITR2024_A1.2", "target"),), None, (("ITR2024_A1.2", "notified"),)),
    Recipe("S2", 2023, (("ITR2024_A4.7", "bact_confirmed"),), None,
           (("ITR2024_A4.7", "rr_tested"),), ("denominator_bacteriologically_confirmed",)),
    Recipe("S3", 2018, (("ITR2019_A1.4.a", "public_notified"),
                        ("ITR2019_A1.4.a", "private_notified")),
           (("ITR2019_A1.4.a", "public_died"), ("ITR2019_A1.4.a", "private_died")), None,
           ("cohort_2017", "public_plus_private")),
    Recipe("S3", 2019, (("ITR2020_A3.3", "cohort_notified"),), (("ITR2020_A3.3", "died"),),
           None, ("cohort_2018",)),
    Recipe("S3", 2021, (("TBAR2022_A3.3", "cohort_notified"),), (("TBAR2022_A3.3", "died"),),
           None, ("cohort_2020",)),
    Recipe("S3", 2022, (("ITR2023_A3.3", "cohort_notified"),), (("ITR2023_A3.3", "died"),),
           None, ("cohort_2021",)),
    Recipe("S3", 2023, (("ITR2024_A3.3", "cohort_notified"),), (("ITR2024_A3.3", "died"),),
           None, ("cohort_2022", _NOTE_2023)),
    Recipe("S4", 2019, (("ITR2020_A3.3", "cohort_notified"),), (("ITR2020_A3.3", "ltfu"),),
           None, ("cohort_2018",)),
    Recipe("S4", 2021, (("TBAR2022_A3.3", "cohort_notified"),), (("TBAR2022_A3.3", "ltfu"),),
           None, ("cohort_2020",)),
    Recipe("S4", 2022, (("ITR2023_A3.3", "cohort_notified"),), (("ITR2023_A3.3", "ltfu"),),
           None, ("cohort_2021",)),
    Recipe("S4", 2023, (("ITR2024_A3.3", "cohort_notified"),), (("ITR2024_A3.3", "ltfu"),),
           None, ("cohort_2022", _NOTE_2023)),
    Recipe("S5", 2023, (("ITR2024_A4.13", "cohort_initiated"),), None,
           (("ITR2024_A4.13", "success"),), ("cohort_2021",)),
    Recipe("S6", 2018, (("ITR2019_A1.2", "notified"),), None, (("ITR2019_A1.2", "hiv_known"),)),
    Recipe("S6", 2019, (("ITR2020_A1.4", "net_notified"),), None,
           (("ITR2020_A2.1", "hiv_known"),)),
    Recipe("S6", 2021, (("TBAR2022_A1.4", "net_notified"),), None,
           (("TBAR2022_A2.1", "hiv_known"),)),
    # Plan §12.2 (deviation, 21 Nov 2026): the denominator is the A1.6 notified
    # count by sex (male + female + transgender), the basis of A2.1's own
    # percentages. The registered A1.2 basis is SENSITIVITY_RECIPES below.
    Recipe("S6", 2022, (("ITR2023_A1.6", "notified_male"), ("ITR2023_A1.6", "notified_female"),
                        ("ITR2023_A1.6", "notified_transgender")), None,
           (("ITR2023_A2.1", "hiv_known"),), ("denominator_A1.6_sex_sum_plan_12.2",)),
    Recipe("S6", 2023, (("ITR2024_A1.4", "net_notified"),), None,
           (("ITR2024_A2.1", "hiv_known"),)),
)

# The registered S6 2022 denominator (plan §5.2: ITR 2023 A1.2, diagnosing PHI),
# kept as a sensitivity (plan §12.2); written to state_panel_s6_2022_registered.csv.
SENSITIVITY_RECIPES: tuple[Recipe, ...] = (
    Recipe("S6", 2022, (("ITR2023_A1.2", "notified"),), None, (("ITR2023_A2.1", "hiv_known"),),
           ("denominator_diagnosing_PHI", "registered_basis_sensitivity_plan_12.2")),
)

# Printed-total differences found at extraction (plan §3.3): (table key, field)
# -> (sum of the 36 printed State/UT rows, printed India value). They are
# recorded, not corrected; any other difference fails the check.
RECORDED_GAPS: dict[tuple[str, str], tuple[int | Decimal, int | Decimal]] = {
    # The 36 State/UT cells sum to 2071 fewer than the India row prints; every
    # cell was also read by eye from the rotated text lines (21 Nov 2026).
    ("ITR2019_A1.2", "hiv_known"): (1436841, 1438912),
    # Population in lakhs printed to two decimals: the rows sum to 0.01 lakh
    # (1,000 persons) less than the India row (rounding).
    ("ITR2024_A1.1", "population_lakhs"): (Decimal("14271.23"), Decimal("14271.24")),
}


# ---- extraction -------------------------------------------------------------------

@dataclass
class Table:
    spec: TableSpec
    cells: dict[str, list[annex.Cell | None]]  # printed unit (and "India") -> cells
    pages: dict[str, int]  # printed unit (and "India") -> PDF page
    raw_names: dict[str, str]
    values: dict[str, dict[str, int | Decimal | None]]  # printed unit -> field -> value


def _page_text(lines) -> str:
    return "".join("".join(t.text for t in ln.tokens) for ln in lines).casefold()


def _squash(s: str) -> str:
    return "".join(s.split()).casefold()


def _value(cell: annex.Cell | None, f: Field, where: str) -> int | Decimal | None:
    if cell is None or cell.n is None:
        return None
    try:
        return cells.parse_decimal(cell.n) if f.decimal else cells.parse_int(cell.n)
    except ValueError as e:
        raise ValueError(f"{where}: {e}") from None


def read_table(spec: TableSpec, pdf_path: Path | None = None) -> Table:
    import pdfplumber  # only the extraction needs it

    from src.extract import grid, pdftext

    path = pdf_path or ROOT / spec.source_file
    rows: dict[str, list[annex.Cell | None]] = {}
    pages: dict[str, int] = {}
    raw: dict[str, str] = {}
    with pdfplumber.open(path) as pdf:
        for i, p in enumerate(spec.pages):
            chars, w, h = pdftext.page_chars(pdf, p)
            text = _page_text(grid.lines_of(chars, w, h, spec.region))
            if i == 0 and spec.title is not None and _squash(spec.title) not in text:
                raise ValueError(f"{spec.key}: title {spec.title!r} not on PDF p. {p}")
            if _squash(spec.header) not in text:
                raise ValueError(f"{spec.key}: header {spec.header!r} not on PDF p. {p}")
            try:
                pr = grid.read_page(chars, w, h, spec.year, spec.ncells, spec.region)
            except ValueError as e:
                raise ValueError(f"{spec.key} PDF p. {p}: {e}") from None
            found = list(pr.rows.items())
            if pr.national is not None:
                found.append((crosswalk.NATIONAL, pr.national))
            for name, cs in found:
                if name in rows:
                    raise ValueError(f"{spec.key}: {name} printed on two pages")
                rows[name], pages[name], raw[name] = cs, p, pr.raw_names[name]
    if crosswalk.NATIONAL not in rows:
        raise ValueError(f"{spec.key}: no India row")
    missing = [u for u in crosswalk.PRINTED[spec.year] if u not in rows]
    if missing:
        raise ValueError(f"{spec.key}: printed rows not found: {missing}")
    values: dict[str, dict[str, int | Decimal | None]] = {}
    for name, cs in rows.items():
        values[name] = {f.name: _value(cs[f.index], f, f"{spec.key} {name} {f.name}")
                        for f in spec.fields}
    nat = values[crosswalk.NATIONAL]
    blank_nat = [k for k, v in nat.items() if v is None]
    if blank_nat:
        raise ValueError(f"{spec.key}: India row blank in {blank_nat}")
    return Table(spec, rows, pages, raw, values)


@lru_cache(maxsize=None)
def read_all() -> dict[str, Table]:
    return {k: read_table(s) for k, s in SPECS.items()}


def tables_from_cells(path: Path = CELLS_CSV) -> dict[str, Table]:
    """The extracted values and pages, read back from state_cells.csv (no PDF
    needed). The printed cells themselves are not kept (``cells`` is empty)."""
    import csv

    out: dict[str, Table] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            spec = SPECS[r["table_key"]]
            t = out.setdefault(spec.key, Table(spec, {}, {}, {}, {}))
            u, fld = r["printed_unit"], spec.field(r["field"])
            v = r["value"]
            val = None if v == "" else (Decimal(v) if fld.decimal else int(v))
            t.values.setdefault(u, {})[fld.name] = val
            t.pages[u] = int(r["pdf_page"])
            t.raw_names[u] = r["printed_name"]
    return out


def total_checks(tables: dict[str, Table]) -> list[dict]:
    """One row per table and extracted column: State sum, printed India value,
    the difference (sum - printed) and the number of blank State cells."""
    out = []
    for key, t in tables.items():
        for f in t.spec.fields:
            states = [t.values[u][f.name] for u in crosswalk.PRINTED[t.spec.year]]
            s, nat, blanks = annex.total_gaps(states, t.values[crosswalk.NATIONAL][f.name])
            out.append({"table_key": key, "field": f.name, "state_sum": s, "printed": nat,
                        "difference": s - nat, "blank_cells": blanks})
    return out


def unrecorded_gaps(checks: list[dict]) -> list[str]:
    """Differences that are not in RECORDED_GAPS, and recorded gaps that changed."""
    bad = []
    seen = set()
    for c in checks:
        k = (c["table_key"], c["field"])
        if c["difference"] != 0:
            seen.add(k)
            if RECORDED_GAPS.get(k) != (c["state_sum"], c["printed"]):
                bad.append(f"{k[0]} {k[1]}: State sum {c['state_sum']} vs printed "
                           f"{c['printed']} (difference {c['difference']}) is not recorded")
        elif k in RECORDED_GAPS:
            bad.append(f"{k[0]} {k[1]}: recorded gap {RECORDED_GAPS[k]} no longer present")
    for k in RECORDED_GAPS:
        if k not in seen and k not in {(c["table_key"], c["field"]) for c in checks}:
            bad.append(f"recorded gap for unknown column {k}")
    return bad


# ---- outputs -----------------------------------------------------------------------

def cell_rows(tables: dict[str, Table]) -> list[dict]:
    out = []
    for key, t in tables.items():
        order = list(crosswalk.PRINTED[t.spec.year]) + [crosswalk.NATIONAL]
        for u in order:
            for f in t.spec.fields:
                c = t.cells[u][f.index]
                out.append({
                    "edition": t.spec.edition, "year": t.spec.year, "table_key": key,
                    "table_id": t.spec.table_id, "pdf_page": t.pages[u],
                    "printed_name": t.raw_names[u], "printed_unit": u,
                    "unit": "" if u == crosswalk.NATIONAL else crosswalk.coarsen(u),
                    "field": f.name, "column_header": f.header,
                    "cell_printed": "" if c is None else c.raw,
                    "value": t.values[u][f.name],
                })
    return out


def _sum(tables: dict[str, Table], refs, member: str) -> int | None:
    vals = [tables[k].values[member][f] for k, f in refs]
    if any(v is None for v in vals):
        return None
    return sum(vals)  # type: ignore[arg-type]


def panel_rows(tables: dict[str, Table],
               recipes: tuple[Recipe, ...] = RECIPES) -> list[dict]:
    out = []
    for r in recipes:
        roles = [("base", r.base)] + [(n, x) for n, x in (("lost", r.lost), ("kept", r.kept))
                                      if x is not None]
        num_refs = r.lost if r.lost is not None else r.kept
        ordered_tables: list[str] = []
        for refs in (num_refs, r.base):
            for k, _ in refs:  # type: ignore[union-attr]
                if tables[k].spec.table_id not in ordered_tables:
                    ordered_tables.append(tables[k].spec.table_id)
        files = {tables[k].spec.source_file for _, refs in roles for k, _ in refs}
        if len(files) != 1:
            raise ValueError(f"{r.step} {r.year}: inputs from several files {sorted(files)}")
        (source_file,) = files
        for unit in crosswalk.UNITS:
            mem = crosswalk.members(unit, r.year)
            sums = {name: 0 for name, _ in roles}
            used, missing, pages = [], [], set()
            for m in mem:
                vals = {name: _sum(tables, refs, m) for name, refs in roles}
                for _, refs in roles:
                    pages.update(tables[k].pages[m] for k, _ in refs)
                if any(v is None for v in vals.values()):
                    missing.append(m)
                    continue
                used.append(m)
                for name, v in vals.items():
                    sums[name] += v  # type: ignore[operator]
            flags = list(r.flags)
            if len(mem) > 1:
                flags.append("merged:" + "+".join(mem))
            flags += [f"member_missing:{m}" for m in missing]
            num = den = None
            if not used:
                flags.append("NA:all_members_missing")
            else:
                den = sums["base"]
                if r.step == "S1":
                    num = sums["kept"]
                    if den == 0:
                        flags.append("NA:denominator_zero")
                else:
                    num = sums["lost"] if r.lost is not None else den - sums["kept"]
                    if den == 0:
                        flags.append("NA:denominator_zero")
                    elif num < 0:
                        flags.append("NA:loss_negative")
                    elif num > den:
                        flags.append("NA:loss_exceeds_denominator")
                if any(f.startswith("NA:") for f in flags):
                    num = den = None
            out.append({
                "unit": unit, "year": r.year, "step": r.step, "numerator": num,
                "denominator": den, "source_file": source_file, "pdf_page": ";".join(str(p) for p in sorted(pages)),
                "table_id": ";".join(ordered_tables), "flag": ";".join(flags),
            })
    out.sort(key=lambda d: (STEPS.index(d["step"]), d["year"], d["unit"]))
    return out


def population_rows(tables: dict[str, Table]) -> list[dict]:
    t = tables["ITR2024_A1.1"]
    out = []
    for unit in crosswalk.UNITS:
        mem = crosswalk.members(unit, t.spec.year)
        vals = {m: t.values[m]["population_lakhs"] for m in mem}
        used = [m for m in mem if vals[m] is not None]
        flags = []
        if len(mem) > 1:
            flags.append("merged:" + "+".join(mem))
        flags += [f"member_missing:{m}" for m in mem if vals[m] is None]
        lakhs = sum((vals[m] for m in used), Decimal(0)) if used else None
        if lakhs is None:
            flags.append("NA:all_members_missing")
        pop = None if lakhs is None else lakhs * 100000
        if pop is not None:
            if pop != pop.to_integral_value():
                raise ValueError(f"{unit}: population {pop} is not whole")
            pop = int(pop)
        out.append({
            "unit": unit, "year": t.spec.year, "population_lakhs": lakhs, "population": pop,
            "source_file": t.spec.source_file,
            "pdf_page": ";".join(str(p) for p in sorted({t.pages[m] for m in mem})),
            "table_id": t.spec.table_id, "flag": ";".join(flags),
        })
    return out


def build(tables: dict[str, Table]) -> dict[str, list[dict]]:
    return {"cells": cell_rows(tables), "panel": panel_rows(tables),
            "s6_2022_registered": panel_rows(tables, SENSITIVITY_RECIPES),
            "population": population_rows(tables)}


def write_all(tables: dict[str, Table], out_dir: Path = EXTRACTED) -> dict[str, Path]:
    b = build(tables)
    paths = {"cells": out_dir / CELLS_CSV.name, "panel": out_dir / PANEL_CSV.name,
             "population": out_dir / POP_CSV.name,
             "s6_2022_registered": out_dir / S6_2022_REGISTERED_CSV.name}
    annex.write_csv(paths["cells"], CELL_COLS, b["cells"])
    annex.write_csv(paths["panel"], PANEL_COLS, b["panel"])
    annex.write_csv(paths["population"], POP_COLS, b["population"])
    annex.write_csv(paths["s6_2022_registered"], PANEL_COLS, b["s6_2022_registered"])
    return paths


def main() -> int:
    tables = read_all()
    checks = total_checks(tables)
    for c in checks:
        mark = "ok" if c["difference"] == 0 else "GAP"
        print(f"{mark}: {c['table_key']} {c['field']}: State sum {c['state_sum']}, "
              f"printed {c['printed']}, blanks {c['blank_cells']}")
    bad = unrecorded_gaps(checks)
    for b in bad:
        print(f"FAIL: {b}")
    if bad:
        return 1
    for name, p in write_all(tables).items():
        print(f"wrote {p.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
