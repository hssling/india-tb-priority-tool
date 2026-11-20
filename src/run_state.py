"""State priorities: harm averted, P(top-k), tiers and flags (analysis plan §6, §10).

Run: python -I src/run_state.py

Reads data/extracted/state_panel.csv, state_panel_s6_2022_registered.csv (the plan §12.2
sensitivity) and state_population.csv, and writes to outputs/:

- state_priority.csv: data year 2023, main specification (benchmark p75, shrinkage on,
  k = 5), one row per unit and step S1-S6 with a non-NA cell: ``unit, step, year,
  harm_averted_mean, lo, hi, per_100k, p_top5, tier, rising, small_far_behind, rate,
  rate_bench`` (§10.2), then ``trend_status`` (the source of the rising flag, §6.5) and
  ``flag`` (the cell's flag, which names the cohort, §3.2). ``rate`` and ``rate_bench``
  are posterior-mean rates (loss rate for S2-S6, achievement for S1).
- state_priority_sensitivity.csv: data year 2023, P(top-k) and tiers under k = 3 and
  k = 8 (benchmark p75), and under the median and best-decile (p90) benchmarks (k = 5),
  all with shrinkage on, beside the main tier (§6.4, §10.2).
- state_harm_draws_summary.csv: the summary of the draws for each unit, step, year and
  specification (benchmark p75 / median / p90 x shrinkage on / off), on the main panel;
  and for S6 2022 also on the registered A1.2 basis (``basis`` =
  ``s6_2022_registered``, §12.2).
- na_cells.csv: every NA or flagged cell of both panel files, with the reason (§3.3,
  §10.2).

Each draw set (step, year, specification, basis) starts from a new
numpy.random.default_rng(20261121) (§10.1). Reruns give byte-identical files.

- state_trend.csv: the trend of every unit and step (§7, §10.2): the main model's slope, SE,
  95% CI, phi_s, years used and rising flag, with the sensitivity model's slope, CI and
  flag (§7.3); S6 also on the registered S6 2022 basis (``basis`` = ``s6_2022_registered``,
  §12.2). Tiers use the main model on the main basis only.

The trend is computed first, and the rising flag (§6.5) is read from it before any tier.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.tbprio import harm, panel, priority, trend  # noqa: E402

EXTRACTED = ROOT / "data" / "extracted"
PANEL_CSV = EXTRACTED / "state_panel.csv"
REGISTERED_CSV = EXTRACTED / "state_panel_s6_2022_registered.csv"
POP_CSV = EXTRACTED / "state_population.csv"
OUTPUTS = ROOT / "outputs"

PRIORITY_YEAR = 2023
MAIN_BENCHMARK = "p75"
KS = (3, priority.K_MAIN, 8)
SPECS = [(b, s) for b in harm.BENCHMARKS for s in (True, False)]
SENSITIVITIES = (  # (analysis, benchmark, k); shrinkage on
    ("k3", "p75", 3),
    ("k8", "p75", 8),
    ("benchmark_median", "median", priority.K_MAIN),
    ("benchmark_p90", "p90", priority.K_MAIN),
)
REGISTERED_BASIS = "s6_2022_registered"

PRIORITY_COLS = ["unit", "step", "year", "harm_averted_mean", "lo", "hi", "per_100k",
                 "p_top5", "tier", "rising", "small_far_behind", "rate", "rate_bench",
                 "trend_status", "flag"]
SENSITIVITY_COLS = ["unit", "step", "year", "analysis", "benchmark", "shrinkage", "k",
                    "harm_averted_mean", "p_topk", "tier", "tier_main", "tier_changed",
                    "rising"]
SUMMARY_COLS = ["basis", "step", "year", "benchmark", "shrinkage", "unit", "n_units",
                "numerator", "denominator", "rate_observed", "rate", "rate_bench", "gap",
                "prior_alpha", "prior_beta", "harm_averted_mean", "lo", "hi", "p_top3",
                "p_top5", "p_top8", "small_far_behind", "no_harm", "flag"]
NA_OUT_COLS = ["panel"] + panel.NA_COLS
TREND_COLS = ["basis", "unit", "step", "trend_status", "years", "n_years", "indicator",
              "slope", "se", "lo", "hi", "chi2", "df", "phi", "rising", "sens_model",
              "sens_status", "sens_slope", "sens_lo", "sens_hi", "sens_rising",
              "rising_differs"]
OUTPUT_FILES = ("state_trend.csv", "state_priority.csv", "state_priority_sensitivity.csv",
                "state_harm_draws_summary.csv", "na_cells.csv")
STEPS = ("S1", "S2", "S3", "S4", "S5", "S6")


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "True" if v else "False"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        v = float(v)
        return "" if v != v else repr(v)
    return str(v)


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow([fmt(r[h]) for h in header])


def trends(rows: list[dict], registered: list[dict] | None = None) -> list[dict]:
    """The trend rows of every unit and step (§7), main basis; and S6 on the registered
    S6 2022 basis when ``registered`` (the panel with that basis swapped in) is given."""
    units = sorted({r["unit"] for r in rows})
    out = []
    for step in STEPS:
        res, _ = trend.step_trends(rows, step, units)
        out += [{"basis": "main", **r} for r in res]
    if registered is not None:
        res, _ = trend.step_trends(registered, "S6", units)
        out += [{"basis": REGISTERED_BASIS, **r} for r in res]
    return out


def rising_flags(trend_rows: list[dict]) -> dict[tuple[str, str], tuple[bool, str]]:
    """(unit, step) -> (rising, trend_status) from the main model on the main basis
    (§6.5, §7.2)."""
    return {(r["unit"], r["step"]): (bool(r["rising"]), r["trend_status"])
            for r in trend_rows if r["basis"] == "main"}


def analyse(rows: list[dict], step: str, year: int, benchmark: str,
            shrinkage: bool) -> dict:
    """One draw set: harm averted, P(top-k) for k in KS and the flags, per unit."""
    rng = np.random.default_rng(harm.SEED)  # reset per analysis (§10.1)
    est = harm.estimate(rows, step, year, benchmark, shrinkage, rng)
    p = {k: priority.p_topk(est.draws, k) for k in KS}
    summ = {u: harm.summary(est.draws[u]) for u in est.units}
    gaps = {u: est.gap(u) for u in est.units}
    fl = priority.flags(gaps, {u: summ[u][0] for u in est.units})
    return {"est": est, "p": p, "summary": summ, "gaps": gaps, "flags": fl}


def summary_rows(basis: str, rows: list[dict], res: dict) -> list[dict]:
    est = res["est"]
    flag = {r["unit"]: r["flag"] for r in panel.cells(rows, est.step, est.year)}
    out = []
    for u in est.units:
        mean, lo, hi = res["summary"][u]
        out.append({
            "basis": basis, "step": est.step, "year": est.year, "benchmark": est.benchmark,
            "shrinkage": "on" if est.shrinkage else "off", "unit": u,
            "n_units": len(est.units), "numerator": est.x[u], "denominator": est.n[u],
            "rate_observed": est.x[u] / est.n[u], "rate": est.post_mean[u],
            "rate_bench": est.rate_bench, "gap": res["gaps"][u], "prior_alpha": est.alpha,
            "prior_beta": est.beta, "harm_averted_mean": mean, "lo": lo, "hi": hi,
            "p_top3": res["p"][3][u], "p_top5": res["p"][5][u], "p_top8": res["p"][8][u],
            "small_far_behind": res["flags"][u]["small_far_behind"],
            "no_harm": est.no_harm, "flag": flag[u],
        })
    return out


def main(out_dir: Path = OUTPUTS) -> int:
    out_dir = Path(out_dir)
    rows = panel.load(PANEL_CSV)
    registered = panel.load(REGISTERED_CSV)
    population = panel.load_population(POP_CSV)
    reg_keys = {(r["step"], r["year"]) for r in registered}
    rows_registered = [r for r in rows if (r["step"], r["year"]) not in reg_keys] + registered

    trend_rows = trends(rows, rows_registered)  # first: the rising flag precedes tiers
    rising = rising_flags(trend_rows)

    results: dict[tuple, dict] = {}
    summary: list[dict] = []
    for step, year in panel.step_years(rows):
        for benchmark, shrinkage in SPECS:
            res = analyse(rows, step, year, benchmark, shrinkage)
            results[(step, year, benchmark, shrinkage)] = res
            summary += summary_rows("main", rows, res)
    for step, year in sorted(reg_keys):
        for benchmark, shrinkage in SPECS:
            res = analyse(rows_registered, step, year, benchmark, shrinkage)
            summary += summary_rows(REGISTERED_BASIS, rows_registered, res)

    prio: list[dict] = []
    sens: list[dict] = []
    for step in sorted({s for s, y in panel.step_years(rows) if y == PRIORITY_YEAR}):
        main_res = results[(step, PRIORITY_YEAR, MAIN_BENCHMARK, True)]
        est = main_res["est"]
        flag = {r["unit"]: r["flag"] for r in panel.cells(rows, step, PRIORITY_YEAR)}
        tier_main = {}
        for u in est.units:
            is_rising, status = rising[(u, step)]
            mean, lo, hi = main_res["summary"][u]
            p5 = main_res["p"][priority.K_MAIN][u]
            tier_main[u] = priority.tier(p5, is_rising)
            pop = population.get(u)
            prio.append({
                "unit": u, "step": step, "year": PRIORITY_YEAR, "harm_averted_mean": mean,
                "lo": lo, "hi": hi,
                "per_100k": None if not pop else mean / pop * 100000,
                "p_top5": p5, "tier": tier_main[u], "rising": is_rising,
                "small_far_behind": main_res["flags"][u]["small_far_behind"],
                "rate": est.post_mean[u], "rate_bench": est.rate_bench,
                "trend_status": status, "flag": flag[u],
            })
        for analysis, benchmark, k in SENSITIVITIES:
            res = results[(step, PRIORITY_YEAR, benchmark, True)]
            for u in res["est"].units:
                is_rising = rising[(u, step)][0]
                p = res["p"][k][u]
                t = priority.tier(p, is_rising)
                sens.append({
                    "unit": u, "step": step, "year": PRIORITY_YEAR, "analysis": analysis,
                    "benchmark": benchmark, "shrinkage": "on", "k": k,
                    "harm_averted_mean": res["summary"][u][0], "p_topk": p, "tier": t,
                    "tier_main": tier_main[u], "tier_changed": t != tier_main[u],
                    "rising": is_rising,
                })

    na = [{"panel": PANEL_CSV.stem, **r} for r in panel.na_cells(rows)]
    na += [{"panel": REGISTERED_CSV.stem, **r} for r in panel.na_cells(registered)]

    write_csv(out_dir / "state_trend.csv", TREND_COLS, trend_rows)
    write_csv(out_dir / "state_priority.csv", PRIORITY_COLS, prio)
    write_csv(out_dir / "state_priority_sensitivity.csv", SENSITIVITY_COLS, sens)
    write_csv(out_dir / "state_harm_draws_summary.csv", SUMMARY_COLS, summary)
    write_csv(out_dir / "na_cells.csv", NA_OUT_COLS, na)
    no_harm = sorted({(r["basis"], r["step"], r["year"]) for r in summary if r["no_harm"]})
    for b, s, y in no_harm:
        print(f"no harm to avert (m = 0): {b} {s} {y}")
    for basis in ("main", REGISTERED_BASIS):
        for step in STEPS:
            tr = [r for r in trend_rows if r["basis"] == basis and r["step"] == step]
            if not tr or tr[0]["phi"] is None or tr[0]["phi"] != tr[0]["phi"]:
                continue
            print(f"trend {basis} {step}: phi = {tr[0]['phi']:.4f}; rising "
                  f"{sum(r['rising'] for r in tr)}; sensitivity rising "
                  f"{sum(r['sens_rising'] for r in tr)}; flag differs "
                  f"{sum(r['rising_differs'] for r in tr)}")
    for name in OUTPUT_FILES:
        print(f"wrote {(out_dir / name).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
