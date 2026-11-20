"""Pinned values, re-read independently from the PDFs, so that a wrong column index
or a wrong row fails.

The review of Task 3 (21 Nov 2026) re-read the values below from the printed
tables, summed over the merged rows of plan §4 where the unit is merged. The
S6 2022 Annexure 1.6 values (Andhra Pradesh, Mizoram) were read by the
implementer from ITR 2023 PDF pp. 221-222.
"""
import csv
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data" / "extracted"


def _read(name: str) -> list[dict]:
    with open(EXTRACTED / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


PANEL = {(r["unit"], r["step"], int(r["year"])): r for r in _read("state_panel.csv")}
REGISTERED = {(r["unit"], r["step"], int(r["year"])): r
              for r in _read("state_panel_s6_2022_registered.csv")}
CELLS = {(r["table_key"], r["printed_unit"], r["field"]): r["value"]
         for r in _read("state_cells.csv")}

# (unit, step, year): (numerator, denominator). numerator = count lost (S2-S6) or
# notified (S1); denominator = base (S2-S6) or target (S1).
KNOWN_PANEL = {
    ("Gujarat", "S3", 2018): (6071, 135585),
    ("Kerala", "S3", 2018): (762, 23418),
    ("Bihar", "S3", 2018): (1850, 96478),
    ("Gujarat", "S6", 2018): (153687 - 120631, 153687),  # 33,056 lost
    ("Gujarat", "S3", 2019): (6465, 149647),
    ("Gujarat", "S4", 2019): (6243, 149647),
    ("Jammu and Kashmir", "S1", 2021): (11117, 14560),  # J&K + Ladakh
    ("Assam", "S4", 2021): (634, 34540),
    ("Kerala", "S6", 2021): (22044 - 20539, 22044),
    ("Jammu and Kashmir", "S3", 2022): (439, 11229),
    ("Gujarat", "S1", 2023): (145674, 141200),
    ("Gujarat", "S2", 2023): (67894 - 59126, 67894),
    ("Kerala", "S5", 2023): (235 - 185, 235),
    ("Jammu and Kashmir", "S6", 2023): (12093 - 11612, 12093),
    # Plan §12.2: S6 2022 denominator = A1.6 male + female + transgender.
    # Andhra Pradesh A1.6: 60460 + 32592 + 40; A2.1 known 92978.
    ("Andhra Pradesh", "S6", 2022): (93092 - 92978, 93092),
    # Mizoram A1.6: 1219 + 887 + 0; A2.1 known 2095.
    ("Mizoram", "S6", 2022): (2106 - 2095, 2106),
}


@pytest.mark.parametrize("key", sorted(KNOWN_PANEL))
def test_known_panel_cells(key):
    r = PANEL[key]
    assert (int(r["numerator"]), int(r["denominator"])) == KNOWN_PANEL[key]


def test_known_printed_cells():
    assert CELLS[("ITR2023_A1.6", "Andhra Pradesh", "notified_male")] == "60460"
    assert CELLS[("ITR2023_A1.6", "Andhra Pradesh", "notified_female")] == "32592"
    assert CELLS[("ITR2023_A1.6", "Andhra Pradesh", "notified_transgender")] == "40"
    assert CELLS[("ITR2023_A1.6", "India", "notified_male")] == "1472190"
    assert CELLS[("ITR2023_A1.6", "India", "notified_female")] == "948455"
    assert CELLS[("ITR2023_A1.6", "India", "notified_transgender")] == "1021"
    assert CELLS[("ITR2023_A2.1", "Andhra Pradesh", "hiv_known")] == "92978"
    assert CELLS[("ITR2019_A1.2", "Gujarat", "hiv_known")] == "119697"


def test_known_population():
    r = next(r for r in _read("state_population.csv") if r["unit"] == "Gujarat")
    assert Decimal(r["population_lakhs"]) == Decimal("733.18")
    assert int(r["population"]) == 73318000


def test_s6_2022_registered_basis_kept_as_sensitivity():
    # Andhra Pradesh on the registered A1.2 basis: known 92978 exceeds notified
    # 92187, so the cell is NA there (plan §3.3), but not on the A1.6 basis.
    assert CELLS[("ITR2023_A1.2", "Andhra Pradesh", "notified")] == "92187"
    reg = REGISTERED[("Andhra Pradesh", "S6", 2022)]
    assert reg["numerator"] == reg["denominator"] == ""
    assert "NA:loss_negative" in reg["flag"].split(";")
    assert set(REGISTERED) == {(u, "S6", 2022) for u, _, _ in REGISTERED}
    assert len(REGISTERED) == 33
