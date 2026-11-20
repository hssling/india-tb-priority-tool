"""Tests of the trend (src/tbprio/trend.py), the headline estimates and labels
(src/tbprio/validate.py) and src/run_validate.py, against the registered analysis plan
§6.5, §7, §8 and §10.

The Fieller fixture (tests/fixtures/tb_state_score_q3_2023_*.csv) is copied from
../tb_state_score (hssling/india-state-tb-score, HEAD 7e5f211; files last changed at
14901eb): outputs/q3_2023_units.csv (rule R2, role primary: unit, unit_score, dropped,
prevalence) and outputs/q3_2023_summary.csv (rule R2, analysis "9.1 primary": rho, lo, hi,
n), values as printed.
"""
import csv
import math
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import rankdata

from src import run_state, run_validate
from src.tbprio import harm, panel, trend, validate

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _row(unit, step, year, num, den, flag=""):
    return {"unit": unit, "year": year, "step": step, "numerator": num, "denominator": den,
            "source_file": "synthetic", "pdf_page": "1", "table_id": "T", "flag": flag,
            "na": num is None, "na_reason": "NA:empty_cell" if num is None else ""}


# ---- label (plan §8.6) ---------------------------------------------------------------

def test_label_rule():
    ten = [1] * 10 + [-1, 0]
    nine = [1] * 9 + [-1, None, 0]
    assert validate.label((0.1, 0.5), 0.0, ten, 1) == "supported"
    assert validate.label((0.1, 0.5), 0.0, nine, 1) == "not established"
    assert validate.n_agree(ten, 1) == 10 and validate.n_agree(nine, 1) == 9
    # The interval must exclude the null strictly.
    assert validate.label((0.0, 0.5), 0.0, [1] * 12, 1) == "not established"
    assert validate.label((-0.1, 0.5), 0.0, [1] * 12, 1) == "not established"
    assert validate.label((None, None), 0.0, [1] * 12, 1) == "not established"
    # Negative side; the main sign defaults to the interval's side.
    assert validate.label((-0.6, -0.2), 0.0, [-1] * 10 + [1, 1]) == "supported"
    assert validate.label((-0.6, -0.2), 0.0, [-1] * 9 + [1, 1, 1]) == "not established"
    # 0 and undefined entries never agree.
    assert validate.label((0.1, 0.5), 0.0, [1] * 9 + [0, 0, None], 1) == "not established"
    assert validate.sign(0.0) == 0 and validate.sign(None) is None
    assert validate.sign(float("nan")) is None and validate.sign(-0.2) == -1


# ---- trend (plan §7) -----------------------------------------------------------------

def test_trend_requires_three_years():
    with pytest.raises(trend.NotEstimable):
        trend.slope([2022, 2023], [100, 90], [1000, 1000])
    # With the 2021 indicator fitted, 3 years other than 2021 are needed.
    with pytest.raises(trend.NotEstimable):
        trend.slope([2019, 2021, 2023], [100, 90, 80], [1000, 1000, 1000])
    with pytest.raises(trend.NotEstimable):
        trend.slope([2019, 2021, 2023], [1, 2, 3], [100, 100, 100], indicator=True)
    # Three non-2021 years with 2021: estimable (S4 years).
    s, lo, hi = trend.slope([2019, 2021, 2022, 2023], [100, 50, 90, 80], [1000] * 4)
    assert lo < s < hi
    # S1: 3 years, no indicator.
    s, lo, hi = trend.slope([2021, 2022, 2023], [900, 950, 990], [1000] * 3, achievement=True)
    assert lo < s < hi

    rows = [_row("A", "S3", y, 50 + y - 2018, 1000) for y in (2018, 2019, 2021, 2022, 2023)]
    rows += [_row("B", "S3", y, 40, 1000) for y in (2021, 2022, 2023)]
    rows += [_row("C", "S3", y, 40, 1000) for y in (2022, 2023)]
    rows += [_row("B", "S3", 2018, None, None)]
    res, _ = trend.step_trends(rows, "S3", ["A", "B", "C", "D"])
    st = {r["unit"]: r for r in res}
    assert st["A"]["trend_status"] == "estimated" and st["A"]["indicator"] is True
    # B: 2021-2023 only (no year before 2021, so no indicator): 3 years, estimable.
    assert st["B"]["trend_status"] == "estimated" and st["B"]["indicator"] is False
    for u in ("C", "D"):
        assert st[u]["trend_status"] == "not estimable (fewer than 3 years)"
        assert st[u]["rising"] is False and st[u]["slope"] is None
    res, _ = trend.step_trends(rows, "S2", ["A"])
    assert res[0]["trend_status"] == "not estimable (definition change)"
    assert res[0]["rising"] is False
    res, _ = trend.step_trends(rows, "S5", ["A"])
    assert res[0]["trend_status"] == "no trend" and res[0]["rising"] is False


def test_trend_wls_and_phi():
    years = [2018, 2019, 2021, 2022, 2023]
    x = np.array([40, 46, 30, 55, 61])
    n = np.array([1000, 1010, 900, 1020, 1030])
    f = trend.fit(years, x, n)
    L = np.log((x + 0.5) / (n - x + 0.5))
    V = 1 / (x + 0.5) + 1 / (n - x + 0.5)
    t = np.array(years, dtype=float)
    X = np.column_stack([np.ones(5), t - 2023, (t == 2021).astype(float)])
    W = np.diag(1 / V)
    inv = np.linalg.inv(X.T @ W @ X)
    beta = inv @ X.T @ W @ L
    assert f.indicator and f.df == 2
    assert f.slope == pytest.approx(beta[1], rel=1e-10)
    assert f.var_unscaled == pytest.approx(inv[1, 1], rel=1e-10)
    r = L - X @ beta
    assert f.chi2 == pytest.approx(float(r @ W @ r), rel=1e-10)
    # phi_s pools chi2 and df over units; 0-df fits contribute nothing; floor 1.
    f2 = trend.fit([2021, 2022, 2023], [900, 950, 990], [1000] * 3, achievement=True,
                   indicator=True, min_years=False)
    assert f2.df == 0
    big = trend.Fit((), False, 0.0, 1.0, 30.0, 3)
    assert trend.pooled_phi([f, f2, big]) == pytest.approx(max(1, (f.chi2 + 30) / 5))
    assert trend.pooled_phi([f2]) == 1.0
    # S1: log achievement, variance 1/(y + 1/2); worsening is a negative slope.
    y, e = np.array([1000, 900, 800]), np.array([1000, 1000, 1000])
    s, lo, hi = trend.slope([2021, 2022, 2023], y, e, achievement=True, phi=2.0)
    L = np.log((y + 0.5) / e)
    w = y + 0.5
    tt = np.array([-2.0, -1.0, 0.0])
    X = np.column_stack([np.ones(3), tt])
    inv = np.linalg.inv((X.T * w) @ X)
    b = inv @ ((X.T * w) @ L)
    assert s == pytest.approx(b[1]) and hi == pytest.approx(b[1] + 1.96 * math.sqrt(2 * inv[1, 1]))
    assert trend.worsening("S1", lo, hi) == (hi < 0)
    assert trend.worsening("S1", -0.3, -0.1) and not trend.worsening("S1", -0.3, 0.1)
    assert trend.worsening("S3", 0.01, 0.2) and not trend.worsening("S3", -0.01, 0.2)
    # The S1 sensitivity (with the indicator) is the 2022-2023 slope.
    f2 = trend.fit([2021, 2022, 2023], y, e, achievement=True, indicator=True,
                   min_years=False)
    assert f2.slope == pytest.approx(math.log(800.5 / 900.5))


# ---- H1 (plan §8.2) ------------------------------------------------------------------

def _h1_brute(pre, post, units_drawn):
    """Brute-force H1 rho for one list of drawn units (duplicates allowed)."""
    xs, ys = [], []
    for s in sorted({s for _, s in pre}):
        p = [pre[(u, s)] for u in units_drawn if pre.get((u, s)) is not None]
        q = [post[(u, s)] for u in units_drawn if pre.get((u, s)) is not None]
        n = len(p)
        xs += list(rankdata(p) / (n + 1))
        ys += list(rankdata(q) / (n + 1))
    return float(np.corrcoef(xs, ys)[0, 1])


def test_h1_within_step_ranks_and_bootstrap():
    rng = np.random.default_rng(3)
    units = [f"U{i:02d}" for i in range(12)]
    pre, post = {}, {}
    for s, scale in (("S3", 1.0), ("S4", 100.0), ("S6", 1e4)):
        for u in units:
            v = float(rng.gamma(2.0, scale))
            pre[(u, s)] = v
            post[(u, s)] = v * float(rng.uniform(0.5, 1.5))
    pre[("U03", "S4")] = None  # excluded unit-step
    rho = validate.h1_rho(pre, post)
    assert rho == pytest.approx(_h1_brute(pre, post, units), rel=1e-12)
    # Ranks are within step: scaling one step does not change rho.
    pre2 = {k: (None if v is None else (v * 1e6 if k[1] == "S3" else v)) for k, v in pre.items()}
    post2 = {k: (v * 1e6 if k[1] == "S3" else v) for k, v in post.items()}
    assert validate.h1_rho(pre2, post2) == pytest.approx(rho, rel=1e-12)

    res = validate.h1_stability(pre, post, rng=np.random.default_rng(harm.SEED), n_boot=200)
    assert res["n_pairs"] == 35 and res["n_units"] == 12
    assert res["excluded"] == [("U03", "S4")]
    idx = np.random.default_rng(harm.SEED).integers(0, 12, size=(200, 12))
    brute = [_h1_brute(pre, post, [units[i] for i in row]) for row in idx]
    lo, hi = np.percentile(brute, [2.5, 97.5], method="linear")
    assert res["lo"] == pytest.approx(lo, rel=1e-10)
    assert res["hi"] == pytest.approx(hi, rel=1e-10)
    assert res["n_discarded"] == 0
    # Leave-one-out drops all of a unit's pairs.
    assert validate.h1_rho(pre, post, omit="U05") == pytest.approx(
        _h1_brute(pre, post, [u for u in units if u != "U05"]), rel=1e-12)


def test_top5_overlap_ties_alphabetical():
    assert validate.top5({"B": 1, "A": 1, "C": 2, "D": 3, "E": 4, "F": 5}) == \
        ["F", "E", "D", "C", "A"]
    pre = {(u, "S3"): v for u, v in zip("ABCDEFG", [7, 6, 5, 4, 3, 2, 1])}
    post = {(u, "S3"): v for u, v in zip("ABCDEFG", [1, 2, 3, 4, 5, 6, 7])}
    assert validate.h1_stability(pre, post)["top5_overlap"] == {"S3": 3}


# ---- H2 (plan §8.3) ------------------------------------------------------------------

def test_fieller_matches_tb_state_score():
    with open(FIXTURES / "tb_state_score_q3_2023_units.csv", encoding="utf-8") as f:
        units = [r for r in csv.DictReader(f) if r["dropped"] == "0"]
    with open(FIXTURES / "tb_state_score_q3_2023_summary.csv", encoding="utf-8") as f:
        want = next(csv.DictReader(f))
    score = {r["unit"]: float(r["unit_score"]) for r in units}
    prev = {r["unit"]: float(r["prevalence"]) for r in units}
    res = validate.h2_external(score, prev)
    assert res["n"] == int(want["n"]) == 19
    assert res["rho"] == pytest.approx(float(want["rho"]), abs=1e-12)
    assert res["lo"] == pytest.approx(float(want["lo"]), abs=1e-12)
    assert res["hi"] == pytest.approx(float(want["hi"]), abs=1e-12)
    assert validate.fisher_ci(0.5, 3) == (None, None)


def test_h2_groups_population_weighted():
    harm_mean = {"A": 300.0, "B": 100.0, "C": 50.0}
    pop = {"A": 3_000_000, "B": 1_000_000, "C": 500_000}
    g = validate.group_values(harm_mean, pop, {"G": ["A", "B"], "H": ["C"]}, 100000.0)
    # Sum of harm / sum of population = the population-weighted mean of per-100k values.
    per = {u: harm_mean[u] / pop[u] * 1e5 for u in pop}
    assert g["G"] == pytest.approx((per["A"] * 3 + per["B"] * 1) / 4)
    assert g["H"] == pytest.approx(10.0)

    groups, not_covered, notes = run_validate.ntps_groups(run_validate.load_ntps())
    assert len(groups) == 20 and all(groups.values())
    assert not_covered == ["Andaman and Nicobar Islands"]
    assert groups["Gujarat"] == ["Gujarat"]
    assert groups["Himachal Pradesh, Uttarakhand, Jammu & Kashmir"] == [
        "Himachal Pradesh", "Jammu and Kashmir", "Uttarakhand"]
    assert groups["Punjab"] == ["Chandigarh", "Punjab"]
    assert sum(len(v) for v in groups.values()) == 32
    assert any("Lakshadweep" in s for s in notes) and any("Ladakh" in s for s in notes)


def test_h3_concentration():
    h = {"S2": {u: float(v) for u, v in zip("ABCDEFG", [10, 9, 8, 7, 6, 5, 5])},
         "S3": {u: 1.0 for u in "ABCDEF"}}
    res = validate.h3_concentration(h)
    assert res["per_step"]["S2"]["share"] == pytest.approx(40 / 50)
    assert res["per_step"]["S3"]["top5"] == list("ABCDE")
    assert res["share"] == pytest.approx((40 + 5) / (50 + 6))


# ---- outputs (plan §10) --------------------------------------------------------------

def test_no_pending_trend_status():
    with open(OUTPUTS / "state_priority.csv", encoding="utf-8", newline="") as f:
        prio = list(csv.DictReader(f))
    assert prio and not any(r["trend_status"] == "pending" for r in prio)
    assert {r["trend_status"] for r in prio} <= {
        "estimated", "not estimable (definition change)", "no trend",
        "not estimable (fewer than 3 years)"}
    with open(OUTPUTS / "state_trend.csv", encoding="utf-8", newline="") as f:
        tr = list(csv.DictReader(f))
    assert not any(r["trend_status"] == "pending" for r in tr)
    main = {(r["unit"], r["step"]): r for r in tr if r["basis"] == "main"}
    for r in prio:
        t = main[(r["unit"], r["step"])]
        assert r["rising"] == t["rising"] and r["trend_status"] == t["trend_status"]
        if r["rising"] == "True" and float(r["p_top5"]) < 0.5:
            assert r["tier"] == "watch: rising"
        if r["tier"] == "watch: rising":
            assert r["rising"] == "True" and float(r["p_top5"]) < 0.5
    for r in tr:
        if r["rising"] == "True":
            worse = float(r["hi"]) < 0 if r["step"] == "S1" else float(r["lo"]) > 0
            assert worse
    assert {r["step"] for r in tr if r["basis"] == "s6_2022_registered"} == {"S6"}


def test_run_validate_outputs_byte_identical(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_validate.main(a)
    run_validate.main(b)
    names = sorted(p.name for p in a.iterdir())
    assert names == sorted(run_validate.OUTPUT_FILES)
    for name in names:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name
        assert b"\r\n" not in (a / name).read_bytes()
        assert (OUTPUTS / name).read_bytes() == (a / name).read_bytes(), name
    with open(a / "headline.csv", encoding="utf-8", newline="") as f:
        rows = {r["estimate"]: r for r in csv.DictReader(f)}
    assert list(next(iter(rows.values())))[:9] == ["estimate", "value", "lo", "hi", "null",
                                                   "n", "n_grid", "n_agree", "label"]
    for est in ("H1", "H2"):
        r = rows[est]
        assert r["n_grid"] == "12" and r["label"] in ("supported", "not established")
        lo, hi, v = float(r["lo"]), float(r["hi"]), float(r["value"])
        expect = ("supported" if ((lo > 0 and hi > 0) or (lo < 0 and hi < 0))
                  and int(r["n_agree"]) >= 10 else "not established")
        assert r["label"] == expect
        assert -1 <= v <= 1
    assert rows["H3"]["label"] == "" and rows["H3"]["lo"] == ""
    with open(a / "spec_curve.csv", encoding="utf-8", newline="") as f:
        spec = list(csv.DictReader(f))
    for est in ("H1", "H2"):
        entries = [r for r in spec if r["estimate"] == est]
        assert len(entries) == 12 and sum(r["main"] == "True" for r in entries) == 1
        main = next(r for r in entries if r["main"] == "True")
        assert main["value"] == rows[est]["value"]
        assert sum(r["agrees"] == "True" for r in entries) == int(rows[est]["n_agree"])
