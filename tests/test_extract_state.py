"""Tests of the State panel extraction (src/extract/itr_state.py, crosswalk.py, grid.py)
and of its committed outputs in data/extracted/."""
import csv
import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from src.extract import crosswalk, grid, itr_state
from verification import check_extraction_totals

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data" / "extracted"
MANIFEST = ROOT / "data" / "source_manifest.csv"

STEP_YEARS = {
    "S1": (2021, 2022, 2023),
    "S2": (2023,),
    "S3": (2018, 2019, 2021, 2022, 2023),
    "S4": (2019, 2021, 2022, 2023),
    "S5": (2023,),
    "S6": (2018, 2019, 2021, 2022, 2023),
}


def _read(name: str) -> list[dict]:
    with open(EXTRACTED / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---- crosswalk -----------------------------------------------------------------------

def test_unmapped_unit_name_raises():
    with pytest.raises(KeyError, match="Atlantis"):
        crosswalk.unit_name("Atlantis", 2023)
    # Names that exist in other years only are not mapped silently.
    with pytest.raises(KeyError, match="Ladakh"):
        crosswalk.unit_name("Ladakh", 2018)
    with pytest.raises(KeyError, match="Daman & Diu"):
        crosswalk.unit_name("Daman & Diu", 2023)
    with pytest.raises(KeyError, match="Dadra and Nagar Haveli and Daman and Diu"):
        crosswalk.unit_name("Dadra and Nagar Haveli and Daman and Diu", 2019)
    with pytest.raises(KeyError, match="India"):
        crosswalk.unit_name("India", 2023)
    with pytest.raises(KeyError, match="2020"):
        crosswalk.unit_name("Assam", 2020)


def test_crosswalk_coarsening():
    assert crosswalk.unit_name("Dadra & Nagar Haveli", 2018) == "Gujarat"
    assert crosswalk.unit_name("Daman & Diu", 2019) == "Gujarat"
    assert crosswalk.unit_name("Dadra And Nagar Haveli And Daman And Diu", 2022) == "Gujarat"
    assert crosswalk.unit_name("Lakshwadeep", 2018) == "Kerala"
    assert crosswalk.unit_name("Ladakh", 2023) == "Jammu and Kashmir"
    assert crosswalk.unit_name("Jammu & Kashmir", 2021) == "Jammu and Kashmir"
    for y in crosswalk.YEARS:
        assert len(crosswalk.PRINTED[y]) == 36
        assert sorted({crosswalk.coarsen(p) for p in crosswalk.PRINTED[y]}) == \
            sorted(crosswalk.UNITS)
    assert crosswalk.members("Gujarat", 2018) == ("Gujarat", "Dadra and Nagar Haveli",
                                                  "Daman and Diu")
    assert crosswalk.members("Jammu and Kashmir", 2019) == ("Jammu and Kashmir",)
    assert crosswalk.members("Jammu and Kashmir", 2023) == ("Jammu and Kashmir", "Ladakh")


# ---- the page reader on a synthetic page ------------------------------------------------

H = 300.0


def _word(text: str, x: float, y: float, size: float = 8.0) -> list[dict]:
    w = 0.5 * size
    return [{"text": ch, "upright": True, "x0": x + i * w, "x1": x + (i + 1) * w,
             "top": y - size, "bottom": y, "size": size,
             "matrix": (1, 0, 0, 1, x + i * w, H - y)} for i, ch in enumerate(text)]


def _line(y: float, *words: tuple[str, float]) -> list[dict]:
    return [c for t, x in words for c in _word(t, x, y)]


def test_grid_reads_wrapped_names_stacked_cells_and_blanks():
    chars = (
        _line(100, ("State", 20), ("Public", 100), ("Private", 150), ("Total", 200))
        + _line(120, ("Andhra", 20), ("Pradesh", 48), ("10", 100), ("(50%)", 112),
                ("20", 150), ("30", 200))
        # Assam: the middle cell's count is printed above the name, its percentage below.
        + _line(150, ("45", 150))
        + _line(155, ("Assam", 20), ("7", 100), ("(7%)", 108), ("52", 200))
        + _line(160, ("(90%)", 146))
        # Bihar: the middle cell is blank (nothing printed).
        + _line(170, ("Bihar", 20), ("4", 100), ("9", 200))
        # A name wrapped around its values.
        + _line(185, ("Dadra", 20), ("and", 44), ("Nagar", 60), ("Haveli", 84))
        + _line(190, ("1", 100), ("2", 150), ("3", 200))
        + _line(195, ("and", 20), ("Daman", 36), ("and", 60), ("Diu", 76))
        + _line(210, ("India", 20), ("22", 100), ("67", 150), ("94", 200))
        + _line(240, ("*", 20), ("note", 28))
        + _line(260, ("7", 140))
    )
    pr = grid.read_page(chars, 300.0, H, 2023, 3)
    raw = {u: [None if c is None else c.raw for c in cs] for u, cs in pr.rows.items()}
    assert raw == {
        "Andhra Pradesh": ["10 (50%)", "20", "30"],
        "Assam": ["7 (7%)", "45 (90%)", "52"],
        "Bihar": ["4", None, "9"],
        "Dadra and Nagar Haveli and Daman and Diu": ["1", "2", "3"],
    }
    assert [c.raw for c in pr.national] == ["22", "67", "94"]
    assert pr.raw_names["Assam"] == "Assam"


def test_grid_rejects_an_unknown_row_inside_the_table():
    chars = (
        _line(120, ("Assam", 20), ("1", 100), ("2", 150))
        + _line(130, ("Atlantis", 20), ("3", 100), ("4", 150))
        + _line(140, ("Bihar", 20), ("5", 100), ("6", 150))
    )
    with pytest.raises(ValueError, match="Atlantis"):
        grid.read_page(chars, 300.0, H, 2023, 2)


# ---- committed outputs ------------------------------------------------------------------

def test_state_rows_sum_to_printed_india_row():
    rows = _read("state_cells.csv")
    assert check_extraction_totals.cell_total_problems(rows) == []
    # The recorded gaps are the only differences, and they are still there.
    assert set(itr_state.RECORDED_GAPS) == {("ITR2019_A1.2", "hiv_known"),
                                            ("ITR2024_A1.1", "population_lakhs")}
    # A changed State cell is caught.
    bad = [dict(r) for r in rows]
    i = next(i for i, r in enumerate(bad) if r["table_key"] == "ITR2024_A3.3"
             and r["field"] == "died" and r["printed_unit"] == "Assam")
    bad[i]["value"] = str(int(bad[i]["value"]) + 1)
    assert any("ITR2024_A3.3 died" in p for p in check_extraction_totals.cell_total_problems(bad))
    # A recorded gap that disappears is caught too.
    bad = [dict(r) for r in rows]
    i = next(i for i, r in enumerate(bad) if r["table_key"] == "ITR2019_A1.2"
             and r["field"] == "hiv_known" and r["printed_unit"] == "India")
    bad[i]["value"] = "1436841"
    assert any("no longer present" in p
               for p in check_extraction_totals.cell_total_problems(bad))


def test_every_value_has_page():
    sources = set()
    with open(MANIFEST, encoding="utf-8", newline="") as f:
        sources = {r["path"] for r in csv.DictReader(f)}
    spec_pages = {s.table_id + "|" + s.source_file: set(s.pages)
                  for s in itr_state.SPECS.values()}
    for r in _read("state_cells.csv"):
        spec = itr_state.SPECS[r["table_key"]]
        assert r["table_id"] == spec.table_id
        assert int(r["pdf_page"]) in spec.pages, r
        assert r["printed_name"] and r["printed_unit"], r
    for name in ("state_panel.csv", "state_population.csv"):
        for r in _read(name):
            assert r["source_file"] in sources, r
            assert r["pdf_page"] and r["table_id"], r
            pages = {int(p) for p in r["pdf_page"].split(";")}
            allowed = set().union(*(spec_pages[t + "|" + r["source_file"]]
                                    for t in r["table_id"].split(";")))
            assert pages <= allowed, r


def test_panel_shape_and_values():
    rows = _read("state_panel.csv")
    assert list(rows[0]) == itr_state.PANEL_COLS
    want = {(s, y) for s, ys in STEP_YEARS.items() for y in ys}
    got: dict[tuple[str, int], list[str]] = {}
    for r in rows:
        got.setdefault((r["step"], int(r["year"])), []).append(r["unit"])
    assert set(got) == want
    for units in got.values():
        assert sorted(units) == sorted(crosswalk.UNITS)
    assert len(rows) == 33 * len(want)
    for r in rows:
        flags = r["flag"].split(";") if r["flag"] else []
        if any(f.startswith("NA:") for f in flags):
            assert r["numerator"] == r["denominator"] == "", r
            continue
        x, n = int(r["numerator"]), int(r["denominator"])
        assert n > 0, r
        if r["step"] != "S1":
            assert 0 <= x <= n, r
        members = crosswalk.members(r["unit"], int(r["year"]))
        if len(members) > 1:
            assert "merged:" + "+".join(members) in flags, r


def test_panel_flags_follow_the_plan():
    rows = {(r["unit"], r["step"], int(r["year"])): r for r in _read("state_panel.csv")}
    flags = {k: set(r["flag"].split(";")) for k, r in rows.items()}
    assert all("public_plus_private" in flags[(u, "S3", 2018)] for u in crosswalk.UNITS)
    assert all("denominator_diagnosing_PHI" in flags[(u, "S6", 2022)] for u in crosswalk.UNITS)
    assert all("cohort_2022" in flags[(u, "S3", 2023)] for u in crosswalk.UNITS)
    # Lakshadweep prints "#N/A" in ITR 2024 Annexure 4.13 and no private-sector
    # deaths in ITR 2019 Annexure 1.4.a: it adds nothing to Kerala there.
    assert "member_missing:Lakshadweep" in flags[("Kerala", "S5", 2023)]
    assert "member_missing:Lakshadweep" in flags[("Kerala", "S3", 2018)]
    missing = {k for k, f in flags.items() if any(x.startswith("member_missing") for x in f)}
    assert missing == {("Kerala", "S5", 2023), ("Kerala", "S3", 2018)}


def test_panel_and_population_rebuild_from_cells():
    assert check_extraction_totals.rebuild_problems() == []


def test_population():
    rows = _read("state_population.csv")
    assert sorted(r["unit"] for r in rows) == sorted(crosswalk.UNITS)
    for r in rows:
        assert Decimal(r["population_lakhs"]) * 100000 == int(r["population"])
    guj = next(r for r in rows if r["unit"] == "Gujarat")
    assert guj["flag"] == "merged:Gujarat+Dadra and Nagar Haveli and Daman and Diu"


def test_ntps_units_copy_matches_its_provenance():
    rec = _read("copied_files.csv")
    assert [r["path"] for r in rec] == ["data/extracted/ntps_units.csv"]
    data = (ROOT / rec[0]["path"]).read_bytes()
    assert len(data) == int(rec[0]["bytes"])
    assert hashlib.sha256(data).hexdigest() == rec[0]["sha256"]
    sibling = ROOT.parent / "tb_state_score" / "data" / "extracted" / "ntps_units.csv"
    if sibling.exists():
        assert sibling.read_bytes() == data


@pytest.mark.skipif(not (ROOT / itr_state.SPECS["ITR2024_A2.1"].source_file).exists(),
                    reason="data_raw/ is not distributed; run python -I tools/fetch_sources.py")
def test_fresh_extraction_of_one_table_matches_committed_cells():
    t = itr_state.read_table(itr_state.SPECS["ITR2024_A2.1"])
    committed = [r for r in _read("state_cells.csv") if r["table_key"] == "ITR2024_A2.1"]
    fresh = itr_state.cell_rows({"ITR2024_A2.1": t})
    assert [{k: str(v) if v is not None else "" for k, v in r.items()} for r in fresh] == \
        committed
