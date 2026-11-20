"""Headline estimates H1-H3, specification grids, labels and leave-one-out (analysis plan
§8, §10.2, §10.4).

Run: python -I src/run_validate.py

Reads data/extracted/state_panel.csv, state_population.csv and ntps_units.csv, recomputes
the draw sets it needs exactly as src/run_state.py does (a new
numpy.random.default_rng(20261121) per draw set, §10.1), and writes to outputs/:

- headline.csv: ``estimate, value, lo, hi, null, n, n_grid, n_agree, label`` (§10.2), then
  ``note``. Rows H1, H2 and H3 (H3 without interval or label), then the descriptive rows,
  which carry no null and no label: the H1 top-5 overlap (per step and summed, out of 15),
  the rate-gap rho beside H1 (§10.4), the signed shortfall per 100,000 beside H2 (§8.3) and
  the H3 share of each step.
- spec_curve.csv: every entry of the H1 and H2 grids (§8.5), the main entry included.
- leave_one_out.csv: H1 and H2 with each unit left out (point estimates), and the 2023 tiers
  refitted with each unit removed (§8.7); ``extreme`` marks the minimum and maximum rho and
  the omitted unit that changes the most tiers.

Fixed choices (§8): H1 pools S3, S4 and S6 over the pre-period {2018, 2019, 2021} ({2019,
2021} for S4) against 2023; the bootstrap draws all 10,000 resamples of units in one call,
``rng.integers(0, U, size=(10000, U))`` over the units in alphabetical order, from a new
default_rng(20261121). H2 uses the data-year-2023 S1 harm averted. The rising flag of the
tiers comes from the main trend model (src/run_state.py, §6.5); leave-one-out refits the
shrinkage prior, benchmark, P(top-5) and tiers (§8.7), not the trend.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src import run_state  # noqa: E402
from src.extract import crosswalk  # noqa: E402
from src.tbprio import harm, panel, priority, validate  # noqa: E402

EXTRACTED = ROOT / "data" / "extracted"
NTPS_CSV = EXTRACTED / "ntps_units.csv"
OUTPUTS = ROOT / "outputs"

YEAR = run_state.PRIORITY_YEAR
H1_STEPS = ("S3", "S4", "S6")
H1_WINDOWS = {  # name -> step -> pre-period (§8.2, §8.5); S4 is {2019, 2021} in both
    "2018;2019;2021": {"S3": (2018, 2019, 2021), "S4": (2019, 2021), "S6": (2018, 2019, 2021)},
    "2019;2021": {"S3": (2019, 2021), "S4": (2019, 2021), "S6": (2019, 2021)},
}
H1_MAIN = ("p75", True, "2018;2019;2021")
H2_DENOMINATORS = ("per population", "per target")
H2_MAIN = ("p75", True, "per population")
H3_STEPS = ("S2", "S3", "S4", "S5")
NULL = 0.0

HEADLINE_COLS = ["estimate", "value", "lo", "hi", "null", "n", "n_grid", "n_agree", "label",
                 "note"]
SPEC_COLS = ["estimate", "benchmark", "shrinkage", "year_window", "denominator", "value",
             "n", "main", "agrees"]
LOO_COLS = ["analysis", "omitted", "step", "value", "n_tier_changes", "changes", "extreme"]
OUTPUT_FILES = ("headline.csv", "spec_curve.csv", "leave_one_out.csv")


def onoff(shrinkage: bool) -> str:
    return "on" if shrinkage else "off"


def load_ntps(path=NTPS_CSV) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return [{"unit": r["unit"], "members": r["member_states"].split(";"),
                 "prevalence": float(r["prevalence"])} for r in csv.DictReader(f)]


def ntps_groups(ntps: list[dict]) -> tuple[dict[str, list[str]], list[str], list[str]]:
    """(NTPS unit -> its coarsened units, coarsened units not covered, notes) (§8.3).

    Each NTPS member State is mapped to its coarsened unit (§4). A coarsened unit whose
    members fall in different NTPS units would go to the one holding its most populous
    member; member populations are not extracted, so that case stops with an error (it
    does not arise: every coarsened unit's covered members lie in one NTPS unit)."""
    merged = {m: u for m, u in crosswalk.MERGED_INTO.items()
              if m not in (crosswalk.DNH, crosswalk.DD)}  # 2023 rows: DNH&DD is one row
    home: dict[str, set[str]] = {}
    listed = set()
    for g in ntps:
        for m in g["members"]:
            u = merged.get(m, m)
            if u not in crosswalk.UNITS:
                raise ValueError(f"NTPS unit {g['unit']!r}: member {m!r} is not a unit")
            home.setdefault(u, set()).add(g["unit"])
            listed.add(m)
    groups: dict[str, list[str]] = {g["unit"]: [] for g in ntps}
    for u in crosswalk.UNITS:
        gs = home.get(u, set())
        if len(gs) > 1:
            raise ValueError(f"{u}: members in NTPS units {sorted(gs)}; the most populous "
                             "member decides (§8.3), but member populations are not extracted")
        if gs:
            groups[next(iter(gs))].append(u)
    not_covered = [u for u in crosswalk.UNITS if u not in home]
    notes = [f"{m} (member of {u}) not covered by the survey" for m, u in sorted(merged.items())
             if m not in listed and u in home]
    return {g: sorted(us) for g, us in groups.items()}, not_covered, notes


def compute(rows: list[dict]) -> dict:
    """The draw sets used here, keyed (step, year, benchmark, shrinkage)."""
    need = set()
    for step in H1_STEPS:
        years = sorted({y for w in H1_WINDOWS.values() for y in w[step]} | {YEAR})
        for year in years:
            for spec in run_state.SPECS:
                need.add((step, year) + spec)
    for spec in run_state.SPECS:
        need.add(("S1", YEAR) + spec)
    for step in run_state.STEPS:
        need.add((step, YEAR, "p75", True))
    return {k: run_state.analyse(rows, *k) for k in sorted(need)}


def mean_harm(res: dict) -> dict[str, float]:
    return {u: v[0] for u, v in res["summary"].items()}


def h1_values(results: dict, benchmark: str, shrinkage: bool, window: str,
              value: str = "harm") -> tuple[dict, dict]:
    """(pre, post): (unit, step) -> pre-period mean and 2023 value; None where a year of
    the pre-period or 2023 is NA for the unit-step (§8.2, inclusion)."""
    pre, post = {}, {}
    for step in H1_STEPS:
        years = H1_WINDOWS[window][step]
        per_year = []
        for y in years + (YEAR,):
            res = results[(step, y, benchmark, shrinkage)]
            per_year.append(mean_harm(res) if value == "harm" else dict(res["gaps"]))
        units = sorted(set().union(*per_year))
        for u in units:
            vals = [d.get(u) for d in per_year]
            if any(v is None for v in vals):
                pre[(u, step)] = post[(u, step)] = None
                continue
            pre[(u, step)] = float(np.mean(vals[:-1]))
            post[(u, step)] = vals[-1]
    return pre, post


def h2_values(results: dict, rows: list[dict], population: dict, groups: dict,
              benchmark: str, shrinkage: bool, denominator: str) -> dict[str, float]:
    harm_mean = mean_harm(results[("S1", YEAR, benchmark, shrinkage)])
    if denominator == "per population":
        return validate.group_values(harm_mean, population, groups, 100000.0)
    target = {c["unit"]: c["denominator"] for c in panel.cells(rows, "S1", YEAR)}
    return validate.group_values(harm_mean, target, groups, 1.0)


def main_tiers(results: dict, rising: dict) -> dict[tuple[str, str], str]:
    out = {}
    for step in run_state.STEPS:
        res = results[(step, YEAR, "p75", True)]
        for u, p in res["p"][priority.K_MAIN].items():
            out[(u, step)] = priority.tier(p, rising[(u, step)][0])
    return out


def loo_tiers(rows: list[dict], rising: dict, tiers: dict) -> list[dict]:
    """Each unit removed in turn; per step, the prior, benchmark, P(top-5) and tiers of
    the remaining units are refitted (main specification), a new rng per refit."""
    units = sorted({r["unit"] for r in rows})
    out = []
    for omit in units:
        kept = [r for r in rows if r["unit"] != omit]
        total, all_changes = 0, []
        for step in run_state.STEPS:
            rng = np.random.default_rng(harm.SEED)  # reset per refit (§10.1)
            est = harm.estimate(kept, step, YEAR, "p75", True, rng)
            p = priority.p_topk(est.draws, priority.K_MAIN)
            changes = []
            for u in est.units:
                t = priority.tier(p[u], rising[(u, step)][0])
                if t != tiers[(u, step)]:
                    changes.append(f"{u}: {tiers[(u, step)]} -> {t}")
            total += len(changes)
            all_changes += [f"{step} {c}" for c in changes]
            out.append({"analysis": "tiers", "omitted": omit, "step": step, "value": None,
                        "n_tier_changes": len(changes), "changes": "; ".join(changes),
                        "extreme": ""})
        out.append({"analysis": "tiers", "omitted": omit, "step": "all", "value": None,
                    "n_tier_changes": total, "changes": "; ".join(all_changes),
                    "extreme": ""})
    totals = [r for r in out if r["step"] == "all"]
    most = max(r["n_tier_changes"] for r in totals)
    for r in totals:
        if r["n_tier_changes"] == most:
            r["extreme"] = "most_changes"
    return out


def mark_extremes(rows: list[dict]) -> None:
    vals = [r["value"] for r in rows if r["value"] is not None]
    lo, hi = min(vals), max(vals)
    for r in rows:
        if r["value"] == lo:
            r["extreme"] = "min"
        elif r["value"] == hi:
            r["extreme"] = "max"


def fmt_n(v) -> str:
    return run_state.fmt(v)


def main(out_dir: Path = OUTPUTS) -> int:
    out_dir = Path(out_dir)
    rows = panel.load(run_state.PANEL_CSV)
    registered = panel.load(run_state.REGISTERED_CSV)
    population = {u: p for u, p in panel.load_population(run_state.POP_CSV).items()}
    reg_keys = {(r["step"], r["year"]) for r in registered}
    rows_registered = [r for r in rows if (r["step"], r["year"]) not in reg_keys] + registered
    ntps = load_ntps()
    prevalence = {g["unit"]: g["prevalence"] for g in ntps}
    groups, not_covered, ntps_notes = ntps_groups(ntps)

    results = compute(rows)
    rising = run_state.rising_flags(run_state.trends(rows, rows_registered))
    tiers = main_tiers(results, rising)

    headline: list[dict] = []
    spec: list[dict] = []

    # ---- H1 (§8.2) ----
    pre, post = h1_values(results, *H1_MAIN)
    h1 = validate.h1_stability(pre, post, rng=np.random.default_rng(harm.SEED))
    h1_main_sign = validate.sign(h1["rho"])
    h1_grid = []
    for benchmark in harm.BENCHMARKS:
        for shrinkage in (True, False):
            for window in H1_WINDOWS:
                key = (benchmark, shrinkage, window)
                rho = (h1["rho"] if key == H1_MAIN
                       else validate.h1_rho(*h1_values(results, *key)))
                h1_grid.append(validate.sign(rho))
                spec.append({"estimate": "H1", "benchmark": benchmark,
                             "shrinkage": onoff(shrinkage), "year_window": window,
                             "denominator": "", "value": rho, "n": h1["n_pairs"],
                             "main": key == H1_MAIN,
                             "agrees": validate.sign(rho) == h1_main_sign
                             and h1_main_sign in (1, -1)})
    excluded = ", ".join(f"{u} {s}" for u, s in h1["excluded"]) or "none"
    headline.append({
        "estimate": "H1", "value": h1["rho"], "lo": h1["lo"], "hi": h1["hi"], "null": NULL,
        "n": h1["n_pairs"], "n_grid": len(h1_grid),
        "n_agree": validate.n_agree(h1_grid, h1_main_sign),
        "label": validate.label((h1["lo"], h1["hi"]), NULL, h1_grid, h1_main_sign),
        "note": (f"Pearson of within-step normalised ranks, unit x step pairs of S3, S4, "
                 f"S6 ({h1['n_units']} units); pre-period 2018, 2019, 2021 (S4: 2019, 2021) "
                 f"vs 2023; bootstrap over units, {h1['n_boot']} draws, "
                 f"{h1['n_discarded']} discarded; excluded unit-steps: {excluded}"),
    })

    # ---- H2 (§8.3) ----
    h2_grid = []
    h2_main = None
    for benchmark in harm.BENCHMARKS:
        for shrinkage in (True, False):
            for denominator in H2_DENOMINATORS:
                key = (benchmark, shrinkage, denominator)
                vals = h2_values(results, rows, population, groups, *key)
                r = validate.h2_external(vals, prevalence)
                if key == H2_MAIN:
                    h2_main, h2_main_vals = r, vals
                spec.append({"estimate": "H2", "benchmark": benchmark,
                             "shrinkage": onoff(shrinkage), "year_window": "",
                             "denominator": denominator, "value": r["rho"], "n": r["n"],
                             "main": key == H2_MAIN, "agrees": None})
                h2_grid.append(validate.sign(r["rho"]))
    h2_main_sign = validate.sign(h2_main["rho"])
    for e in spec:
        if e["estimate"] == "H2":
            e["agrees"] = validate.sign(e["value"]) == h2_main_sign and h2_main_sign in (1, -1)
    nc = ", ".join(not_covered) or "none"
    headline.append({
        "estimate": "H2", "value": h2_main["rho"], "lo": h2_main["lo"], "hi": h2_main["hi"],
        "null": NULL, "n": h2_main["n"], "n_grid": len(h2_grid),
        "n_agree": validate.n_agree(h2_grid, h2_main_sign),
        "label": validate.label((h2_main["lo"], h2_main["hi"]), NULL, h2_grid, h2_main_sign),
        "note": (f"Spearman rho, 2023 S1 harm averted per 100,000 (sum over members) vs NTPS "
                 f"prevalence, over NTPS reporting units; Fisher-z interval with Fieller's "
                 f"variance 1.06/(n-3); excluded (not covered): {nc}; "
                 + "; ".join(ntps_notes)),
    })

    # ---- H3 (§8.4) ----
    h3 = validate.h3_concentration(
        {s: mean_harm(results[(s, YEAR, "p75", True)]) for s in H3_STEPS})
    headline.append({
        "estimate": "H3", "value": h3["share"], "lo": None, "hi": None, "null": None,
        "n": len(H3_STEPS), "n_grid": None, "n_agree": None, "label": "",
        "note": ("share of harm averted (2023, S2-S5 summed, main specification) in each "
                 "step's top-5 units; n = steps; descriptive, no label"),
    })

    # ---- descriptive rows (no null, no label) ----
    for s in H1_STEPS:
        headline.append({"estimate": f"H1 top-5 overlap {s}", "value": h1["top5_overlap"][s],
                         "lo": None, "hi": None, "null": None, "n": 5, "n_grid": None,
                         "n_agree": None, "label": "",
                         "note": "descriptive; ties at the fifth place broken alphabetically"})
    headline.append({"estimate": "H1 top-5 overlap", "value": sum(h1["top5_overlap"].values()),
                     "lo": None, "hi": None, "null": None, "n": 5 * len(H1_STEPS),
                     "n_grid": None, "n_agree": None, "label": "",
                     "note": "descriptive; summed over S3, S4, S6"})
    gap_rho = validate.h1_rho(*h1_values(results, *H1_MAIN, value="gap"))
    headline.append({"estimate": "H1 rate-gap rho (descriptive)", "value": gap_rho,
                     "lo": None, "hi": None, "null": None, "n": h1["n_pairs"],
                     "n_grid": None, "n_agree": None, "label": "",
                     "note": ("rate gap r_u - r_bench on posterior means (§10.4), same "
                              "within-step rank construction as H1; no interval, no label")})
    s1 = panel.cells(rows, "S1", YEAR)
    signed = {c["unit"]: float(c["denominator"] - c["numerator"]) for c in s1}
    signed_vals = validate.group_values(signed, population, groups, 100000.0)
    sh = validate.h2_external(signed_vals, prevalence)
    headline.append({"estimate": "H2 signed shortfall per 100,000 (descriptive)",
                     "value": sh["rho"], "lo": sh["lo"], "hi": sh["hi"], "null": None,
                     "n": sh["n"], "n_grid": None, "n_agree": None, "label": "",
                     "note": ("(target - notified) summed over members per 100,000 vs NTPS "
                              "prevalence; Fieller interval; descriptive, no label")})
    for s in H3_STEPS:
        ps = h3["per_step"][s]
        headline.append({"estimate": f"H3 share {s}", "value": ps["share"], "lo": None,
                         "hi": None, "null": None, "n": len(mean_harm(
                             results[(s, YEAR, "p75", True)])),
                         "n_grid": None, "n_agree": None, "label": "",
                         "note": "top 5: " + ", ".join(ps["top5"])})

    # ---- leave-one-out (§8.7) ----
    loo_h1 = [{"analysis": "H1", "omitted": u, "step": "", "n_tier_changes": None,
               "changes": "", "extreme": "", "value": validate.h1_rho(pre, post, omit=u)}
              for u in sorted({u for u, _ in pre})]
    mark_extremes(loo_h1)
    loo_h2 = [{"analysis": "H2", "omitted": g, "step": "", "n_tier_changes": None,
               "changes": "", "extreme": "",
               "value": validate.h2_external(h2_main_vals, prevalence, omit=g)["rho"]}
              for g in h2_main["units"]]
    mark_extremes(loo_h2)
    loo = loo_h1 + loo_h2 + loo_tiers(rows, rising, tiers)

    run_state.write_csv(out_dir / "headline.csv", HEADLINE_COLS, headline)
    run_state.write_csv(out_dir / "spec_curve.csv", SPEC_COLS, spec)
    run_state.write_csv(out_dir / "leave_one_out.csv", LOO_COLS, loo)
    for r in headline:
        print(f"{r['estimate']}: {fmt_n(r['value'])} [{fmt_n(r['lo'])}, {fmt_n(r['hi'])}] "
              f"n={fmt_n(r['n'])} agree={fmt_n(r['n_agree'])}/{fmt_n(r['n_grid'])} "
              f"{r['label']}")
    for r in loo:
        if r["extreme"]:
            print(f"leave-one-out {r['analysis']} {r['extreme']}: {r['omitted']} "
                  f"{fmt_n(r['value'])} {fmt_n(r['n_tier_changes'])}")
    for name in OUTPUT_FILES:
        print(f"wrote {(out_dir / name).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
