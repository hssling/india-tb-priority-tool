"""State priorities: harm averted, P(top-k), tiers and flags (analysis plan §6, §7, §10).

Used by src/run_state.py and by the tool's ``state`` command (``python -I -m tbprio
state``). ``run`` computes, from the long-format State panel:

- the trend of every unit and step (§7), first, so that the rising flag (§6.5) is read from
  it before any tier; S6 also on the registered S6 2022 basis (§12.2) when that panel is
  given;
- for every step-year and specification (benchmark p75 / median / p90 x shrinkage on /
  off), one draw set from a new numpy.random.default_rng(20261121) (§10.1): harm averted,
  P(top-k) for k = 3, 5, 8, and the small-but-far-behind flag;
- the data-year 2023 priorities under the main specification (benchmark p75, shrinkage on,
  k = 5) with tiers, and their sensitivities (k = 3, k = 8; median and best-decile
  benchmarks).

``write`` writes state_trend.csv, state_priority.csv, state_priority_sensitivity.csv,
state_harm_draws_summary.csv and na_cells.csv (columns below). Reruns give byte-identical
files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import harm, panel, priority, trend
from .table import fmt, write_csv  # noqa: F401  (re-exported for the scripts)

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
STEP_NAMES = {
    "S1": "shortfall against target", "S2": "not tested for rifampicin resistance",
    "S3": "died (DS-TB cohort)", "S4": "lost to follow-up (DS-TB cohort)",
    "S5": "DR-TB treatment not successful", "S6": "HIV status not known",
}


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


def run(rows: list[dict], registered: list[dict] | None = None,
        population: dict[str, int | None] | None = None,
        panel_name: str = "state_panel",
        registered_name: str = "state_panel_s6_2022_registered") -> dict[str, list[dict]]:
    """Every State output table, keyed by output file name (without ".csv")."""
    population = population or {}
    if registered is not None:
        reg_keys = {(r["step"], r["year"]) for r in registered}
        rows_registered = ([r for r in rows if (r["step"], r["year"]) not in reg_keys]
                           + registered)
    else:
        reg_keys, rows_registered = set(), None

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

    na = [{"panel": panel_name, **r} for r in panel.na_cells(rows)]
    if registered is not None:
        na += [{"panel": registered_name, **r} for r in panel.na_cells(registered)]
    return {"state_trend": trend_rows, "state_priority": prio,
            "state_priority_sensitivity": sens, "state_harm_draws_summary": summary,
            "na_cells": na}


COLS = {"state_trend": TREND_COLS, "state_priority": PRIORITY_COLS,
        "state_priority_sensitivity": SENSITIVITY_COLS,
        "state_harm_draws_summary": SUMMARY_COLS, "na_cells": NA_OUT_COLS}


def write(tables: dict[str, list[dict]], out_dir: Path) -> list[Path]:
    """Write the five State output files (OUTPUT_FILES) to ``out_dir``."""
    out_dir = Path(out_dir)
    paths = []
    for name in OUTPUT_FILES:
        key = name[:-4]
        write_csv(out_dir / name, COLS[key], tables[key])
        paths.append(out_dir / name)
    return paths


def messages(tables: dict[str, list[dict]]) -> list[str]:
    """The run's console summary: step-years with no harm to avert, and trend phi_s."""
    out = []
    summary, trend_rows = tables["state_harm_draws_summary"], tables["state_trend"]
    no_harm = sorted({(r["basis"], r["step"], r["year"]) for r in summary if r["no_harm"]})
    for b, s, y in no_harm:
        out.append(f"no harm to avert (m = 0): {b} {s} {y}")
    for basis in ("main", REGISTERED_BASIS):
        for step in STEPS:
            tr = [r for r in trend_rows if r["basis"] == basis and r["step"] == step]
            if not tr or tr[0]["phi"] is None or tr[0]["phi"] != tr[0]["phi"]:
                continue
            out.append(f"trend {basis} {step}: phi = {tr[0]['phi']:.4f}; rising "
                       f"{sum(r['rising'] for r in tr)}; sensitivity rising "
                       f"{sum(r['sens_rising'] for r in tr)}; flag differs "
                       f"{sum(r['rising_differs'] for r in tr)}")
    return out
