"""Tests of the district modules (analysis plan §9) and their extraction."""
import csv
import math
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from src.extract import au802, district_names, itr2019_districts
from src.tbprio import district, schema

ROOT = Path(__file__).resolve().parents[1]
NOTIF_CSV = ROOT / "data" / "extracted" / "district_notifications.csv"
EXAMPLE = ROOT / "examples" / "district_example.csv"
NATIONAL_OUT = ROOT / "outputs" / "district_national_2018.csv"
MPMH_OUT = ROOT / "outputs" / "district_mp_mh.csv"


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---- schema (§9.3) --------------------------------------------------------------------

def test_district_schema_variants():
    # different column order, header case and spacing, an extra column, an optional
    # cascade column, and a total row
    rows = [
        {" Year ": "2022", "Notified": "1,200", "DISTRICT": "Alpha", "extra": "x",
         "cascade_initiated": "1100", "target": ""},
        {" Year ": "2024", "Notified": "1300", "DISTRICT": "Alpha", "extra": "y",
         "cascade_initiated": "1250", "target": "1500"},
        {" Year ": "2022", "Notified": "2400", "DISTRICT": "Total", "extra": "",
         "cascade_initiated": "", "target": ""},
    ]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = schema.validate_district(rows)
    msgs = [str(w.message) for w in caught]
    assert any("extra" in m for m in msgs)
    assert any("total row" in m for m in msgs)
    assert [r["district"] for r in out] == ["Alpha", "Alpha"]
    assert out[0] == {"state": "", "district": "Alpha", "year": 2022, "notified": 1200,
                      "target": None, "cascade_initiated": 1100}
    assert out[1]["target"] == 1500

    # missing required column: a clear error naming it
    with pytest.raises(schema.SchemaError, match="missing required column.*notified"):
        schema.validate_district([{"district": "A", "year": "2022", "count": "3"}])
    with pytest.raises(schema.SchemaError, match="year"):
        schema.validate_district([{"district": "A", "notified": "3"}])
    # bad values
    with pytest.raises(schema.SchemaError, match="not a whole number"):
        schema.validate_district([{"district": "A", "year": "2022", "notified": "-3"}])
    with pytest.raises(schema.SchemaError, match="four-digit year"):
        schema.validate_district([{"district": "A", "year": "22", "notified": "3"}])
    with pytest.raises(schema.SchemaError, match="appears twice"):
        schema.validate_district([{"district": "A", "year": "2022", "notified": "3"},
                                  {"district": "A", "year": "2022", "notified": "4"}])
    # a district named like its State is not a total row
    out = schema.validate_district([{"state": "Chandigarh", "district": "Chandigarh",
                                     "year": "2022", "notified": "9"}])
    assert len(out) == 1


def test_example_file_is_synthetic_and_valid():
    text = EXAMPLE.read_text(encoding="utf-8")
    assert text.startswith("# SYNTHETIC EXAMPLE - NOT REAL DATA")
    assert "\r" not in text
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = schema.read_csv(EXAMPLE)
    assert sum("total row" in str(w.message) for w in caught) == 3
    assert {r["state"] for r in rows} == {"Synthetic State"}
    assert all(r["district"].startswith("Synthetic District") for r in rows)
    assert {"target", "population", "cascade_initiated"} <= set(rows[0])


# ---- AU802 (§9.2) ---------------------------------------------------------------------

def test_au802_units_per_state():
    # docs/data_inventory.md: Madhya Pradesh 52 distinct districts (53 entries, "Vidisha"
    # twice), Maharashtra 80
    rows = _read(NOTIF_CSV)
    units = Counter()
    for st, d in {(r["state"], r["district"]) for r in rows}:
        units[st] += 1
    assert units == {"Madhya Pradesh": 52, "Maharashtra": 80}
    years = Counter((r["state"], r["district"]) for r in rows)
    assert set(years.values()) == {3}
    flagged = {(r["state"], r["district"]) for r in rows if r["flag"]}
    assert flagged == {("Madhya Pradesh", "Vidisha")}
    assert {r["flag"] for r in rows if r["district"] == "Vidisha"} == {"duplicate_entry"}
    assert len(district_names.AU802["Madhya Pradesh"]) == 52
    assert len(district_names.AU802["Maharashtra"]) == 80
    # the file passes the tool's own schema
    assert len(schema.read_csv(NOTIF_CSV)) == 3 * 132
    if (ROOT / au802.SOURCE_FILE).exists():
        assert au802.records(au802.read_docx()) == [
            {**r, "year": int(r["year"]), "notified": int(r["notified"])} for r in rows]


def _table(entries, title):
    head = [title] * 4 + [""] + [title] * 4
    rows = [head, au802.HEADER]
    half = (len(entries) + 1) // 2
    left, right = entries[:half], entries[half:]
    for i in range(half):
        a = left[i]
        b = right[i] if i < len(right) else ("", "", "", "")
        rows.append([*a, "", *b])
    return rows


def test_au802_duplicates_and_unknown_names():
    mp = [(d, "10", "11", "12") for d in district_names.AU802["Madhya Pradesh"]]
    mh = [(d, "20", "21", "22") for d in district_names.AU802["Maharashtra"]]
    t_mh = _table(mh, au802.TABLES[1][3])
    ok = au802.records([_table(mp + [("Vidisha", "10", "11", "12")], au802.TABLES[0][3]),
                        t_mh])
    assert len(ok) == 3 * 132
    with pytest.raises(ValueError, match="printed twice"):
        au802.records([_table(mp + [("Vidisha", "10", "11", "13")], au802.TABLES[0][3]),
                       t_mh])
    bad = mp[:-1] + [("Nowhere", "1", "2", "3"), ("Vidisha", "10", "11", "12")]
    with pytest.raises(KeyError, match="Nowhere"):
        au802.records([_table(bad, au802.TABLES[0][3]), t_mh])


# ---- ITR 2019 Annexure 1.13 (§9.1) -----------------------------------------------------

def test_itr2019_districts_extraction():
    recs = itr2019_districts.read_csv()
    assert len(recs) == district_names.itr2019_count() == 761
    by = Counter(r["state"] for r in recs)
    assert by["Madhya Pradesh"] == 51 and by["Maharashtra"] == 79
    names = {(r["state"], r["district"]) for r in recs}
    assert ("Maharashtra", "Nanded") in names
    assert ("Maharashtra", "Nanded Waghela MC") in names
    assert all(r["pdf_page"] in itr2019_districts.PAGES for r in recs)
    assert {r["table_id"] for r in recs} == {"Annexure 1.13"}
    # printed India row: equal, or a recorded difference of the recorded size
    checks = itr2019_districts.total_checks(recs)
    assert itr2019_districts.unrecorded_gaps(checks) == []
    assert {c["column"] for c in checks if c["difference"]} == set(
        itr2019_districts.RECORDED_GAPS)
    # row identities hold in every district row
    for r in recs:
        assert r["notified"] == r["notified_public"] + r["notified_private"]
        assert r["notified"] == r["new"] + r["previously_treated"] + r["pmdt"]
        assert r["initiated"] == r["initiated_public"] + r["initiated_private"]


def test_itr2019_district_crosswalk_names_unknown_strings():
    assert district_names.itr2019("Maharashtra", "Nanded") == "Nanded"
    assert district_names.itr2019("Karnataka", "Chamara- janagar") == "Chamarajanagar"
    with pytest.raises(KeyError, match="Atlantis"):
        district_names.itr2019("Karnataka", "Atlantis")
    with pytest.raises(KeyError, match="Neverland"):
        district_names.itr2019("Neverland", "Atlantis")
    with pytest.raises(KeyError, match="Bijapur"):  # a Karnataka name in the wrong State
        district_names.itr2019("Kerala", "Bijapur")


def test_d2_cohort_rounding():
    n, lo, hi = district.d2_cohort(238, "95")
    assert n == 251  # 238 / 0.95 = 250.53 -> 251
    assert lo == pytest.approx(238 / 0.955) and hi == pytest.approx(238 / 0.945)
    n, lo, hi = district.d2_cohort(1, "0.2")  # h = 0.05
    assert n == 500 and lo == pytest.approx(1 / 0.0025) and hi == pytest.approx(1 / 0.0015)
    n, lo, hi = district.d2_cohort(48, "100")
    assert n == 48 and lo == 48.0 and hi == pytest.approx(48 / 0.995)
    n, _, _ = district.d2_cohort(5, "40")  # 12.5 rounds half up
    assert n == 13
    rec = {"state": "S", "district": "d", "notified": 10, "initiated": 12,
           "success_public_n": 0, "success_public_pct": "0", "source_file": "f",
           "pdf_page": 1, "table_id": "t"}
    cells = district.national_cells([rec])
    assert cells[0]["na"] and cells[0]["flag"] == "NA:initiated_exceeds_notified"
    assert cells[1]["na"] and cells[1]["flag"] == "NA:percent_zero"


def test_state_funnel_formulas():
    # two States of three districts and one single-district State
    spec = [("A", 1000, 100), ("A", 2000, 150), ("A", 500, 80),
            ("B", 800, 40), ("B", 1600, 120), ("B", 400, 30), ("C", 300, 30)]
    cells = [{"unit": f"{s} | d{i}", "state": s, "numerator": x, "denominator": n}
             for i, (s, n, x) in enumerate(spec)]
    f = district.state_funnel(cells)
    assert f["no_funnel"] == {"C": "one district with a value"}
    assert f["D"] == 6 and f["G"] == 2
    pS = {"A": 330 / 3500, "B": 190 / 2800}
    z = []
    for c in cells[:6]:
        p = pS[c["state"]]
        z.append((c["numerator"] / c["denominator"] - p)
                 / math.sqrt(p * (1 - p) / c["denominator"]))
    zw = np.clip(z, *np.percentile(z, [10, 90], method="linear"))
    assert f["phi"] == pytest.approx(float(np.mean(zw ** 2)))
    w = [c["denominator"] / (pS[c["state"]] * (1 - pS[c["state"]])) for c in cells[:6]]
    Q = sum(wi * (c["numerator"] / c["denominator"] - pS[c["state"]]) ** 2
            for wi, c in zip(w, cells[:6]))
    within = sum(sum(x * x for x in w[k:k + 3]) / sum(w[k:k + 3]) for k in (0, 3))
    tau2 = max(0.0, (Q - 4) / (sum(w) - within))
    assert f["tau2"] == pytest.approx(tau2)
    u = f["units"]["A | d0"]
    assert u["z"] == pytest.approx(z[0])
    assert u["z_additive"] == pytest.approx(
        (0.1 - pS["A"]) / math.sqrt(pS["A"] * (1 - pS["A"]) / 1000 + tau2))


def test_district_flags_on_synthetic_overdispersed_data():
    rng = np.random.default_rng(7)
    units = []
    for i in range(40):
        b = int(rng.integers(1000, 8000))
        eps = rng.normal(0, 0.08)  # extra-Poisson variation between districts
        units.append((f"d{i:02d}", b, int(rng.poisson(b * (1.0 + eps)))))
    units.append(("fell", 5000, 2000))
    units.append(("rose", 4000, 7000))
    units.append(("zero", 0, 15))
    f = district.change_funnel(units)
    assert f["na"] == ["zero"]
    R = sum(u[2] for u in units) / sum(u[1] for u in units)
    assert f["R"] == pytest.approx(R)
    z = {d: ((n24 - n22) - n22 * (R - 1)) / math.sqrt(n22 + n24)
         for d, n22, n24 in units if n22 > 0}
    zs = np.array(list(z.values()))
    zw = np.clip(zs, *np.percentile(zs, [10, 90], method="linear"))
    assert f["phi"] == pytest.approx(float(np.mean(zw ** 2)))
    assert f["phi"] > 1  # overdispersed
    assert f["units"]["fell"]["flag"] == district.FELL
    assert f["units"]["rose"]["flag"] == district.ROSE
    flagged = {d for d, u in f["units"].items() if u["flag"] != district.WITHIN_CHANGE}
    unadjusted = {d for d, v in z.items() if abs(v) > district.Z998}
    assert flagged == {d for d, v in z.items()
                       if abs(v) > district.Z998 * math.sqrt(f["phi"])}
    assert flagged < unadjusted  # the adjustment widens the limits
    # additive tau2 by its formula
    y = {d: (n24 - n22) / n22 for d, n22, n24 in units if n22 > 0}
    s = {d: math.sqrt(n22 + n24) / n22 for d, n22, n24 in units if n22 > 0}
    w = {d: 1 / s[d] ** 2 for d in s}
    Q = sum(w[d] * (y[d] - (R - 1)) ** 2 for d in w)
    sw = sum(w.values())
    tau2 = max(0.0, (Q - (len(w) - 1)) / (sw - sum(v * v for v in w.values()) / sw))
    assert f["tau2"] == pytest.approx(tau2) and tau2 > 0
    assert f["units"]["fell"]["z_additive"] == pytest.approx(
        (y["fell"] - (R - 1)) / math.sqrt(s["fell"] ** 2 + tau2))
    # no tiers in the change funnel
    assert not any("tier" in u for u in f["units"].values())


def test_notifications_on_au802():
    rows = schema.read_csv(NOTIF_CSV)
    out, info, years = district.notifications(rows, ["madhya pradesh", "Maharashtra"])
    assert list(info) == ["Madhya Pradesh", "Maharashtra"]  # the input's spelling
    assert years == [2022, 2023, 2024]
    assert info["Madhya Pradesh"]["districts"] == 52
    assert info["Maharashtra"]["districts"] == 80
    mp = [r for r in out if r["state"] == "Madhya Pradesh"]
    assert info["Madhya Pradesh"]["N_base"] == sum(r["n_2022"] for r in mp)
    assert {r["entry_flag"] for r in mp if r["district"] == "Vidisha"} == {"duplicate_entry"}
    with pytest.raises(ValueError, match="no rows for State"):
        district.notifications(rows, ["Kerala"])


def test_national_module_output():
    rows = _read(NATIONAL_OUT)
    assert {r["data_label"] for r in rows} == {district.LABEL_2018}
    for step in ("D1", "D2"):
        rs = [r for r in rows if r["step"] == step]
        assert len(rs) == 761
        ok = [r for r in rs if r["na"] == "False"]
        p = [float(r["p_top20"]) for r in ok]
        assert sum(p) == pytest.approx(20, abs=1e-6)  # 20 places per draw
        assert {r["tier"] for r in ok} <= {"act now", "probable priority", "uncertain",
                                           "lower priority"}
        assert {r["funnel_flag"] for r in ok} <= {
            "above State limits", "below State limits", "within State limits",
            "no funnel: one district with a value"}
    d2 = [r for r in rows if r["step"] == "D2" and r["na"] == "False"]
    assert all("rounded_from_percent" in r["flag"] for r in d2)
    for r in d2:  # the range runs from at least N (the success count) upwards
        success = int(r["denominator"]) - int(r["numerator"])
        assert success <= float(r["cohort_lo"]) <= float(r["cohort_hi"])
    mpmh = _read(MPMH_OUT)
    assert Counter(r["state"] for r in mpmh) == {"Madhya Pradesh": 52, "Maharashtra": 80}
    assert {r["flag"] for r in mpmh} <= {district.FELL, district.ROSE,
                                         district.WITHIN_CHANGE}
