"""Tests of the core estimation (src/tbprio/: panel, shrink, harm, priority) and of
src/run_state.py, against the registered analysis plan §6 and §10."""
import csv
import math
from pathlib import Path

import numpy as np
import pytest

from src import run_state
from src.tbprio import harm, panel, priority, shrink

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


def _row(unit, step, year, num, den, flag=""):
    return {"unit": unit, "year": year, "step": step, "numerator": num, "denominator": den,
            "source_file": "synthetic", "pdf_page": "1", "table_id": "T", "flag": flag}


def _write_panel(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(panel.PANEL_COLS)
        for r in rows:
            w.writerow(["" if r[c] is None else r[c] for c in panel.PANEL_COLS])


def _loaded(tmp_path: Path, rows: list[dict]) -> list[dict]:
    p = tmp_path / "panel.csv"
    _write_panel(p, rows)
    return panel.load(p)


# ---- shrinkage (plan §6.1) -----------------------------------------------------------

def test_beta_binomial_method_of_moments():
    x = np.array([5, 30, 12, 0, 50])
    n = np.array([100, 200, 150, 80, 300])
    p = x / n
    m = x.sum() / n.sum()
    s2 = sum((pi - m) ** 2 for pi in p) / (len(p) - 1)
    tau2 = s2 - m * (1 - m) * np.mean(1 / n)
    S = min(max(m * (1 - m) / tau2 - 1, 1.0), 1e6)
    a, b = shrink.beta_binomial(x, n)
    assert a == pytest.approx(m * S, rel=1e-12)
    assert b == pytest.approx((1 - m) * S, rel=1e-12)
    # No between-unit variance beyond binomial: S = 10^6.
    a, b = shrink.beta_binomial(np.array([10, 10, 10]), np.array([1000, 1000, 1000]))
    assert a + b == pytest.approx(1e6)


def test_gamma_poisson_method_of_moments():
    y = np.array([90, 120, 60, 200])
    e = np.array([100, 100, 100, 180])
    a_hat = y / e
    m = y.sum() / e.sum()
    s2 = sum((ai - m) ** 2 for ai in a_hat) / (len(y) - 1)
    v = s2 - m * np.mean(1 / e)
    alpha = min(max(m * m / v, 1.0), 1e6)
    a, b = shrink.gamma_poisson(y, e)
    assert a == pytest.approx(alpha, rel=1e-12)
    assert b == pytest.approx(alpha / m, rel=1e-12)
    a, b = shrink.gamma_poisson(np.array([100, 100]), np.array([100, 100]))
    assert a == 1e6 and b == pytest.approx(1e6)


# ---- harm averted (plan §6.3) --------------------------------------------------------

def test_harm_averted_floor_zero_and_zero_counts(tmp_path):
    loss = [_row(f"U{i:02d}", "S3", 2023, x, 1000) for i, x in
            enumerate([0, 5, 10, 20, 40, 60, 80, 100])]
    s1 = [_row(f"U{i:02d}", "S1", 2023, y, 1000) for i, y in
          enumerate([700, 800, 900, 950, 1000, 1500, 600, 850])]
    zero = [_row(f"U{i:02d}", "S4", 2023, 0, 500 + i) for i in range(6)]
    rows = _loaded(tmp_path, loss + s1 + zero)

    # A unit with 0 patients lost still gets a finite, proper posterior.
    a, b = shrink.beta_binomial(np.array([r["numerator"] for r in rows if r["step"] == "S3"]),
                                np.array([r["denominator"] for r in rows if r["step"] == "S3"]))
    assert math.isfinite(a) and math.isfinite(b) and a > 0 and b > 0

    for shrinkage in (True, False):
        est = harm.estimate(rows, "S3", 2023, "p75", shrinkage, np.random.default_rng(1))
        for u, h in est.draws.items():
            assert h.shape == (harm.N_DRAWS,)
            assert np.all(np.isfinite(h)) and np.all(h >= 0)
            r = est.rate_draws[u]
            # The floor is applied per draw: below the benchmark, harm is exactly 0.
            assert np.all(h[r <= est.rate_bench] == 0)
            np.testing.assert_allclose(h[r > est.rate_bench],
                                       1000 * (r[r > est.rate_bench] - est.rate_bench))
        assert est.draws["U00"].mean() < 1.0
        assert 0 < est.post_mean["U00"] < 0.01

        # S1: notified far above target gives zero harm in every draw.
        est1 = harm.estimate(rows, "S1", 2023, "p75", shrinkage, np.random.default_rng(1))
        assert all(np.all(h >= 0) for h in est1.draws.values())
        assert np.all(est1.draws["U05"] == 0)
        a = est1.rate_draws["U06"]
        np.testing.assert_allclose(est1.draws["U06"], np.maximum(0, 1000 * (est1.rate_bench - a)))

        # A step-year with no patient lost: every unit's harm averted is 0 (§6.1).
        est0 = harm.estimate(rows, "S4", 2023, "p75", shrinkage, np.random.default_rng(1))
        assert est0.no_harm
        assert set(est0.draws) == {f"U{i:02d}" for i in range(6)}
        assert all(np.all(h == 0) for h in est0.draws.values())
        p = priority.p_topk(est0.draws, 5)
        assert all(v == 0 for v in p.values())


def test_benchmark_percentiles_on_posterior_means(tmp_path):
    rows = _loaded(tmp_path, [_row(f"U{i}", "S6", 2022, 10 * i + 3, 1000) for i in range(9)]
                   + [_row(f"U{i}", "S1", 2022, 800 + 25 * i, 1000) for i in range(9)])
    for bench, q_loss, q_ach in (("p75", 25, 75), ("median", 50, 50), ("p90", 10, 90)):
        est = harm.estimate(rows, "S6", 2022, bench, True, np.random.default_rng(0))
        pm = np.array([est.post_mean[u] for u in est.units])
        assert est.rate_bench == np.percentile(pm, q_loss, method="linear")
        est = harm.estimate(rows, "S1", 2022, bench, True, np.random.default_rng(0))
        pm = np.array([est.post_mean[u] for u in est.units])
        assert est.rate_bench == np.percentile(pm, q_ach, method="linear")
    # Shrinkage off: Jeffreys prior, posterior mean (1/2 + x) / (1 + n) and (1/2 + y) / e.
    est = harm.estimate(rows, "S6", 2022, "p75", False, np.random.default_rng(0))
    assert est.post_mean["U2"] == pytest.approx((0.5 + 23) / 1001)
    est = harm.estimate(rows, "S1", 2022, "p75", False, np.random.default_rng(0))
    assert est.post_mean["U2"] == pytest.approx((0.5 + 850) / 1000)


def test_draws_reset_per_analysis_and_alphabetical(tmp_path):
    rows = _loaded(tmp_path, [_row(u, "S3", 2023, x, 2000) for u, x in
                              (("Zeta", 40), ("Alpha", 10), ("Mu", 25))])
    d = harm.draws(rows, "S3", 2023, "p75", True, np.random.default_rng(harm.SEED))
    assert list(d) == ["Alpha", "Mu", "Zeta"]
    est = harm.estimate(rows, "S3", 2023, "p75", True, np.random.default_rng(harm.SEED))
    rng = np.random.default_rng(harm.SEED)
    for u in ("Alpha", "Mu", "Zeta"):
        x = {"Alpha": 10, "Mu": 25, "Zeta": 40}[u]
        expect = rng.beta(est.alpha + x, est.beta + 2000 - x, size=harm.N_DRAWS)
        np.testing.assert_array_equal(est.rate_draws[u], expect)


# ---- missing cells (plan §6, §3.3) ---------------------------------------------------

def test_missing_step_excludes_unit_only_from_that_step(tmp_path):
    units = [f"Unit {c}" for c in "ABCDEFGH"]
    rows = []
    for i, u in enumerate(units):
        if u == "Unit A":
            rows.append(_row(u, "S3", 2023, None, None, "cohort_2022;NA:loss_negative"))
        else:
            rows.append(_row(u, "S3", 2023, 20 + 7 * i, 1000 + 100 * i))
        rows.append(_row(u, "S4", 2023, 30 + 5 * i, 1200 + 50 * i))
    loaded = _loaded(tmp_path, rows)

    s3 = harm.draws(loaded, "S3", 2023, "p75", True, np.random.default_rng(harm.SEED))
    s4 = harm.draws(loaded, "S4", 2023, "p75", True, np.random.default_rng(harm.SEED))
    assert "Unit A" not in s3 and set(s3) == set(units[1:])
    assert set(s4) == set(units)
    p3 = priority.p_topk(s3, 5)
    assert set(p3) == set(units[1:])
    assert sum(p3.values()) <= 5 + 1e-9

    na = panel.na_cells(loaded)
    assert [(r["unit"], r["step"], r["year"]) for r in na if r["na"]] == [("Unit A", "S3", 2023)]
    assert "NA:loss_negative" in next(r for r in na if r["na"])["reason"]

    # A cell that breaks a §3.3 rule is NA even if the extraction left it filled.
    p = tmp_path / "bad.csv"
    _write_panel(p, [_row("X", "S6", 2023, 12, 10), _row("Y", "S6", 2023, 3, 0),
                     _row("Z", "S1", 2023, 120, 100)])
    bad = {r["unit"]: r for r in panel.load(p)}
    assert bad["X"]["na"] and "loss_exceeds_denominator" in bad["X"]["na_reason"]
    assert bad["Y"]["na"] and "denominator_zero" in bad["Y"]["na_reason"]
    assert not bad["Z"]["na"]  # S1: notified above target is a valid value


# ---- priority and tiers (plan §6.4-§6.6) ---------------------------------------------

def test_small_unit_cannot_dominate_tiers(tmp_path):
    rows = [_row(f"Large {i:02d}", "S5", 2023, 3000 + 400 * i, 100000) for i in range(12)]
    rows.append(_row("Small UT", "S5", 2023, 45, 50))  # n < 100, loss rate 0.9
    loaded = _loaded(tmp_path, rows)
    est = harm.estimate(loaded, "S5", 2023, "p75", True, np.random.default_rng(harm.SEED))
    assert est.post_mean["Small UT"] == max(est.post_mean.values())  # worst rate of all
    p = priority.p_topk(est.draws, 5)
    assert p["Small UT"] < 0.2
    assert priority.tier(p["Small UT"], False) == "lower priority"
    assert priority.tier(p["Small UT"], False) != "act now"
    gaps = {u: est.post_mean[u] - est.rate_bench for u in est.units}
    means = {u: float(h.mean()) for u, h in est.draws.items()}
    assert priority.flags(gaps, means)["Small UT"]["small_far_behind"] is True


def test_p_topk_zero_harm_scores_zero():
    # Draw 0: only A > 0 (B, C, D tied at 0 for the 2nd place get nothing).
    # Draw 1: A first; B and C tied above 0 at the 2nd place share 1 place.
    # Draw 2: no unit above 0.
    d = {"A": np.array([5.0, 9.0, 0.0]), "B": np.array([0.0, 4.0, 0.0]),
         "C": np.array([0.0, 4.0, 0.0]), "D": np.array([0.0, 1.0, 0.0])}
    p = priority.p_topk(d, 2)
    assert p["A"] == pytest.approx(2 / 3)
    assert p["B"] == pytest.approx(0.5 / 3) and p["C"] == pytest.approx(0.5 / 3)
    assert p["D"] == 0.0
    # Three tied above 0 at places 1-3 with k = 2: each gets 2/3.
    p = priority.p_topk({"A": np.array([3.0]), "B": np.array([3.0]), "C": np.array([3.0]),
                         "D": np.array([0.0])}, 2)
    assert [p[u] for u in "ABCD"] == pytest.approx([2 / 3, 2 / 3, 2 / 3, 0.0])
    # Fewer units than k.
    assert priority.p_topk({"A": np.array([1.0, 0.0])}, 5) == {"A": 0.5}
    # Every draw has >= k units above 0: P(top-k) sums to k.
    rng = np.random.default_rng(7)
    draws = {f"U{i}": rng.gamma(2.0, 10.0 * (i + 1), size=10000) for i in range(15)}
    for k in (3, 5, 8):
        assert abs(sum(priority.p_topk(draws, k).values()) - k) <= 1e-9
    # With many exact zeros but still >= k positive units in each draw.
    draws = {f"U{i}": np.where(rng.random(10000) < 0.5, 0.0, rng.random(10000) + 1)
             for i in range(10)}
    draws.update({f"V{i}": rng.random(10000) + 0.1 for i in range(5)})
    p = priority.p_topk(draws, 5)
    assert abs(sum(p.values()) - 5) <= 1e-9
    for u, h in draws.items():
        assert p[u] <= float(np.mean(h > 0)) + 1e-12


def test_tier_thresholds():
    assert priority.tier(0.80, False) == "act now"
    assert priority.tier(1.0, True) == "act now"
    assert priority.tier(0.7999, False) == "probable priority"
    assert priority.tier(0.50, True) == "probable priority"
    assert priority.tier(0.4999, False) == "uncertain"
    assert priority.tier(0.20, False) == "uncertain"
    assert priority.tier(0.19, False) == "lower priority"
    assert priority.tier(0.19, True) == "watch: rising"
    assert priority.tier(0.30, True) == "watch: rising"
    assert priority.tier(0.0, True) == "watch: rising"


def test_small_far_behind_rule():
    gaps = {"A": 0.30, "B": 0.10, "C": 0.05, "D": 0.0, "E": -0.02}
    means = {"A": 1.0, "B": 500.0, "C": 300.0, "D": 50.0, "E": 0.0}
    f = priority.flags(gaps, means)
    # 75th percentile of gaps = 0.10 (linear); median of means = 50.
    assert f["A"]["small_far_behind"] is True
    assert f["B"]["small_far_behind"] is False  # worst quartile, but harm above median
    assert not any(f[u]["small_far_behind"] for u in "CDE")


# ---- run script (plan §10) -----------------------------------------------------------

def test_run_state_outputs_byte_identical(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_state.main(a)
    run_state.main(b)
    names = sorted(p.name for p in a.iterdir())
    assert names == sorted(run_state.OUTPUT_FILES)
    for name in names:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name
        assert b"\r\n" not in (a / name).read_bytes()
        # The committed outputs are the current ones.
        assert (OUTPUTS / name).read_bytes() == (a / name).read_bytes(), name
    with open(a / "state_priority.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0])[:13] == ["unit", "step", "year", "harm_averted_mean", "lo", "hi",
                                  "per_100k", "p_top5", "tier", "rising", "small_far_behind",
                                  "rate", "rate_bench"]
    assert {r["year"] for r in rows} == {"2023"}
    assert {r["step"] for r in rows} == {"S1", "S2", "S3", "S4", "S5", "S6"}
    for step in ("S1", "S2", "S3", "S4", "S5", "S6"):
        assert sum(float(r["p_top5"]) for r in rows if r["step"] == step) <= 5 + 1e-9
