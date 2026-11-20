"""Independent recompute of the registered State results, with the standard library only
(analysis plan §10.3). Nothing of src/ is imported, and neither numpy nor scipy: the
formulas below are written out again from the plan.

Run as: python -I verification/check_outputs.py [--root DIR]

Inputs: data/extracted/state_panel.csv, state_population.csv and ntps_units.csv, and the
committed outputs/ files. Tolerances: |dP| <= 0.02 for P(top-5) from this file's own
draws (§10.3); 1e-9 relative for deterministic values (1e-7 for the trend's matrix
inverse); exact equality where a value is copied from another output row.

(a) Data year 2023, step S3, main specification (benchmark p75, shrinkage on): the
    method-of-moments Beta prior (§6.1) against prior_alpha and prior_beta of
    state_harm_draws_summary.csv; every unit's posterior-mean rate and the benchmark (25th
    percentile of posterior means, linear interpolation, §6.2) against state_priority.csv;
    and P(top-5) of every unit (§6.4) from 10,000 draws per unit taken with
    random.Random(20261121).betavariate (units in alphabetical order), within 0.02. The
    plan names the units at each tier boundary; every unit of the step is checked, which
    includes them (the five "act now" units and the units ranked next). Each unit's mean
    harm averted is also compared, within 5 Monte Carlo standard errors of the
    difference plus 0.01 patient.
(b) H1 (§8.2): every entry of the H1 grid (§8.5) from the harm_averted_mean values of
    state_harm_draws_summary.csv: pre-period mean, within-step average ranks divided by
    (n_s + 1), pooled Pearson correlation; the value and n (unit-step pairs) of each entry
    against spec_curve.csv. Also the rate-gap rho (§10.4), the top-5 overlaps and the H1
    leave-one-out values (§8.7).
(c) H2 (§8.3): every entry of the H2 grid from the S1 2023 harm_averted_mean values, the
    ITR 2024 population, the S1 targets and the NTPS units (members mapped to the
    coarsened units of §4; State groups summed); Spearman rho with average ranks; the main
    entry's Fisher-z interval with Fieller's variance 1.06/(n - 3). Also the signed
    shortfall row, the H2 leave-one-out values and H3 (§8.4) with its per-step shares.
(d) The labels (§8.6) from spec_curve.csv: the sign agreement of every entry, n_grid,
    n_agree and the label of H1 and H2 in headline.csv (the H1 interval is the bootstrap
    interval printed in headline.csv; the H2 interval is the one recomputed in (c)).
(e) The trend (§7.2): the weighted least squares fit of every unit of S1, S3, S4 and S6
    on the main basis, the pooled phi_s, the slope, its SE and 95% CI and the rising flag
    (§6.5), against state_trend.csv; S3 Bihar and phi_S3 are printed. The rising flag and
    tier of every row of state_priority.csv follow from these and P(top-5) (§6.4-§6.5).
(f) Headline values equal their source rows: headline.csv H1 and H2 against the main row
    of spec_curve.csv; every row of state_priority.csv and state_priority_sensitivity.csv
    against the matching row of state_harm_draws_summary.csv; per_100k against the
    population.

NOT re-derived here: the H1 bootstrap interval (it is reproduced by the seeded rerun of
outputs/ in check_all), the sensitivity trend models, leave-one-out tiers and the district
modules.

Exit 1 on any failed comparison.
"""
import argparse
import csv
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261121
N_DRAWS = 10_000
K = 5
TOL_P = 0.02
REL = 1e-9
REL_TREND = 1e-7
YEAR = 2023
BENCHMARKS = {"p75": 25.0, "median": 50.0, "p90": 10.0}        # loss steps (§6.2)
ACHIEVEMENT_Q = {"p75": 75.0, "median": 50.0, "p90": 90.0}     # S1
H1_STEPS = ("S3", "S4", "S6")
H1_WINDOWS = {"2018;2019;2021": {"S3": (2018, 2019, 2021), "S4": (2019, 2021),
                                 "S6": (2018, 2019, 2021)},
              "2019;2021": {"S3": (2019, 2021), "S4": (2019, 2021), "S6": (2019, 2021)}}
H1_MAIN = ("p75", "on", "2018;2019;2021")
H2_MAIN = ("p75", "on", "per population")
H3_STEPS = ("S2", "S3", "S4", "S5")
TREND_YEARS = {"S1": (2021, 2022, 2023), "S3": (2018, 2019, 2021, 2022, 2023),
               "S4": (2019, 2021, 2022, 2023), "S6": (2018, 2019, 2021, 2022, 2023)}
NO_TREND = {"S2": "not estimable (definition change)", "S5": "no trend"}
# Plan §4: printed rows merged into a coarsened unit (2023 rows: DNH&DD is one row).
MERGED = {"Dadra and Nagar Haveli and Daman and Diu": "Gujarat", "Lakshadweep": "Kerala",
          "Ladakh": "Jammu and Kashmir"}
Z = 1.96
FIELLER = 1.06


# ------------------------------------------------------------------ input

def read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def flt(s: str):
    return None if s is None or s.strip() == "" else float(s)


def boolean(s: str) -> bool:
    if s not in ("True", "False"):
        raise ValueError(f"not a boolean: {s!r}")
    return s == "True"


def load_panel(root: Path) -> dict:
    """(unit, step, year) -> (x, n) for the non-NA cells of state_panel.csv (§3.3)."""
    out = {}
    for r in read(root / "data" / "extracted" / "state_panel.csv"):
        num, den = r["numerator"].strip(), r["denominator"].strip()
        if num == "" or den == "" or any(f.startswith("NA:") for f in r["flag"].split(";")):
            continue
        x, n = int(num), int(den)
        if n == 0 or (r["step"] != "S1" and (x < 0 or x > n)):
            continue
        out[(r["unit"], r["step"], int(r["year"]))] = (x, n)
    return out


def cells(panel: dict, step: str, year: int) -> list[tuple[str, int, int]]:
    return sorted((u, x, n) for (u, s, y), (x, n) in panel.items() if s == step and y == year)


# ------------------------------------------------------------------ arithmetic

def close(a, b, rel=REL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=rel, abs_tol=rel * 1e-3)


def percentile(values, q: float) -> float:
    """Linear interpolation between order statistics (numpy's "linear" method)."""
    s = sorted(values)
    h = (len(s) - 1) * q / 100.0
    lo = math.floor(h)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (h - lo)


def mom_beta(xn: list[tuple[int, int]]) -> tuple[float, float]:
    """Plan §6.1, beta-binomial method of moments."""
    U = len(xn)
    m = sum(x for x, _ in xn) / sum(n for _, n in xn)
    s2 = sum((x / n - m) ** 2 for x, n in xn) / (U - 1)
    tau2 = s2 - m * (1 - m) * sum(1 / n for _, n in xn) / U
    S = 1e6 if tau2 <= 0 else min(max(m * (1 - m) / tau2 - 1, 1.0), 1e6)
    return m * S, (1 - m) * S


def avg_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def pearson(a: list[float], b: list[float]):
    n = len(a)
    if n < 2:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    if saa <= 0 or sbb <= 0:
        return None
    return sab / math.sqrt(saa * sbb)


def spearman(a, b):
    return pearson(avg_ranks(a), avg_ranks(b))


def fieller(rho, n):
    if rho is None or n <= 3:
        return None, None
    if abs(rho) >= 1:
        return rho, rho
    z, se = math.atanh(rho), math.sqrt(FIELLER / (n - 3))
    return math.tanh(z - Z * se), math.tanh(z + Z * se)


def top5(values: dict) -> list[str]:
    return [u for u, _ in sorted(values.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]


def sign(v):
    if v is None or v != v:
        return None
    return (v > 0) - (v < 0)


def label(lo, hi, signs, main_sign) -> str:
    if lo is None or hi is None:
        return "not established"
    if not ((lo > 0 and hi > 0) or (lo < 0 and hi < 0)):
        return "not established"
    agree = sum(1 for s in signs if main_sign in (1, -1) and s == main_sign)
    return "supported" if 5 * agree >= 4 * len(signs) else "not established"


def tier(p: float, rising: bool) -> str:
    if p >= 0.80:
        return "act now"
    if p >= 0.50:
        return "probable priority"
    if rising:
        return "watch: rising"
    return "uncertain" if p >= 0.20 else "lower priority"


def inverse(a: list[list[float]]) -> list[list[float]]:
    """Gauss-Jordan inverse with partial pivoting."""
    n = len(a)
    m = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        piv = m[c][c]
        m[c] = [v / piv for v in m[c]]
        for r in range(n):
            if r != c and m[r][c] != 0.0:
                f = m[r][c]
                m[r] = [v - f * w for v, w in zip(m[r], m[c])]
    return [row[n:] for row in m]


# ------------------------------------------------------------------ (a) S3 2023

def p_top(draws: dict[str, list[float]], k: int) -> dict[str, float]:
    """Plan §6.4: top-k score per draw, zero harm scores 0, ties at the k-th place share."""
    units = list(draws)
    score = dict.fromkeys(units, 0.0)
    n_draws = len(next(iter(draws.values())))
    for d in range(n_draws):
        h = {u: draws[u][d] for u in units}
        if len(units) <= k:
            for u in units:
                score[u] += 1.0 if h[u] > 0 else 0.0
            continue
        vk = sorted(h.values(), reverse=True)[k - 1]
        gt = [u for u in units if h[u] > vk]
        eq = [u for u in units if h[u] == vk and h[u] > 0]
        for u in gt:
            score[u] += 1.0
        if eq:
            share = (k - len(gt)) / len(eq)
            for u in eq:
                score[u] += share
    return {u: score[u] / n_draws for u in units}


def check_s3(panel, summary, prio, bad, ok):
    step = "S3"
    cs = cells(panel, step, YEAR)
    alpha, beta = mom_beta([(x, n) for _, x, n in cs])
    s_rows = {r["unit"]: r for r in summary
              if (r["basis"], r["step"], r["year"], r["benchmark"], r["shrinkage"])
              == ("main", step, str(YEAR), "p75", "on")}
    p_rows = {r["unit"]: r for r in prio if r["step"] == step}
    if sorted(s_rows) != [u for u, _, _ in cs] or sorted(p_rows) != [u for u, _, _ in cs]:
        bad.append(f"(a) S3 {YEAR}: the units of the outputs differ from the panel's "
                   f"non-NA cells")
        return
    any_row = s_rows[cs[0][0]]
    for name, mine, printed in (("prior alpha", alpha, flt(any_row["prior_alpha"])),
                                ("prior beta", beta, flt(any_row["prior_beta"]))):
        if not close(mine, printed):
            bad.append(f"(a) S3 {YEAR} {name}: printed {printed!r} but recomputed {mine!r}")
    post = {u: (alpha + x) / (alpha + beta + n) for u, x, n in cs}
    bench = percentile(post.values(), BENCHMARKS["p75"])
    for u, x, n in cs:
        for col, mine in (("rate", post[u]), ("rate_bench", bench)):
            if not close(mine, flt(p_rows[u][col])):
                bad.append(f"(a) S3 {YEAR} {u} {col}: printed {p_rows[u][col]} but "
                           f"recomputed {mine!r}")
    rng = random.Random(SEED)
    draws = {}
    for u, x, n in cs:  # alphabetical
        a, b = alpha + x, beta + n - x
        draws[u] = [max(0.0, n * (rng.betavariate(a, b) - bench)) for _ in range(N_DRAWS)]
    p = p_top(draws, K)
    worst = 0.0
    for u, _, _ in cs:
        printed = flt(p_rows[u]["p_top5"])
        worst = max(worst, abs(p[u] - printed))
        if abs(p[u] - printed) > TOL_P:
            bad.append(f"(a) S3 {YEAR} {u} P(top-5): printed {printed} but standard-library "
                       f"draws give {p[u]:.4f} (|d| > {TOL_P})")
        h = draws[u]
        mean = sum(h) / N_DRAWS
        sd = math.sqrt(sum((v - mean) ** 2 for v in h) / (N_DRAWS - 1))
        # 5 Monte Carlo SEs of a difference of two means, plus 0.01 patient for units
        # whose harm is almost always 0 (a rare positive draw dominates their mean)
        tol = 5 * math.sqrt(2) * sd / math.sqrt(N_DRAWS) + 0.01
        if abs(mean - flt(p_rows[u]["harm_averted_mean"])) > tol:
            bad.append(f"(a) S3 {YEAR} {u} harm_averted_mean: printed "
                       f"{p_rows[u]['harm_averted_mean']} but standard-library draws give "
                       f"{mean:.4f} (tolerance {tol:.4f})")
    order = sorted(cs, key=lambda c: -flt(p_rows[c[0]]["harm_averted_mean"]))
    boundary = [u for u, _, _ in order[K - 1:K + 1]]
    ok.append(f"(a) S3 {YEAR}: prior alpha {alpha:.6g}, beta {beta:.6g}; benchmark "
              f"{bench:.6f}; {len(cs)} posterior means; P(top-5) of {len(cs)} units within "
              f"{TOL_P} (largest |d| {worst:.4f}; boundary units {', '.join(boundary)})")


# ------------------------------------------------------------------ (b) H1

def summary_index(summary) -> dict:
    """(step, year, benchmark, shrinkage) -> unit -> row (main basis)."""
    out: dict = {}
    for r in summary:
        if r["basis"] == "main":
            out.setdefault((r["step"], int(r["year"]), r["benchmark"], r["shrinkage"]),
                           {})[r["unit"]] = r
    return out


def h1_values(idx, benchmark, shrinkage, window, column="harm_averted_mean"):
    pre, post = {}, {}
    for step in H1_STEPS:
        years = H1_WINDOWS[window][step] + (YEAR,)
        per_year = [{u: flt(r[column]) for u, r in idx[(step, y, benchmark, shrinkage)].items()}
                    for y in years]
        for u in sorted(set().union(*per_year)):
            vals = [d.get(u) for d in per_year]
            if any(v is None for v in vals):
                continue
            pre[(u, step)] = sum(vals[:-1]) / len(vals[:-1])
            post[(u, step)] = vals[-1]
    return pre, post


def h1_rho(pre, post, omit=None):
    xs, ys = [], []
    for step in H1_STEPS:
        keys = sorted(k for k in pre if k[1] == step and k[0] != omit)
        if not keys:
            continue
        n = len(keys)
        xs += [r / (n + 1) for r in avg_ranks([pre[k] for k in keys])]
        ys += [r / (n + 1) for r in avg_ranks([post[k] for k in keys])]
    return pearson(xs, ys), len(xs)


def check_h1(idx, spec, headline, loo, bad, ok):
    rows = [r for r in spec if r["estimate"] == "H1"]
    seen = set()
    for r in rows:
        key = (r["benchmark"], r["shrinkage"], r["year_window"])
        seen.add(key)
        rho, n = h1_rho(*h1_values(idx, *key))
        if not close(rho, flt(r["value"])) or str(n) != r["n"]:
            bad.append(f"(b) spec_curve H1 {key}: printed {r['value']} (n {r['n']}) but "
                       f"recomputed {rho!r} (n {n})")
        if boolean(r["main"]) != (key == H1_MAIN):
            bad.append(f"(b) spec_curve H1 {key}: main is {r['main']}")
    expected = {(b, s, w) for b in BENCHMARKS for s in ("on", "off") for w in H1_WINDOWS}
    if seen != expected or len(rows) != 12:
        bad.append(f"(b) spec_curve H1: {len(rows)} entries; expected the 12 of plan 8.5")
    pre, post = h1_values(idx, *H1_MAIN)
    rho, n = h1_rho(pre, post)
    gap_rho, _ = h1_rho(*h1_values(idx, *H1_MAIN, column="gap"))
    hl = {r["estimate"]: r for r in headline}
    checks = [("H1", rho), ("H1 rate-gap rho (descriptive)", gap_rho)]
    total = 0
    for step in H1_STEPS:
        a = {u: v for (u, s), v in pre.items() if s == step}
        b = {u: post[(u, s)] for (u, s) in pre if s == step}
        ov = len(set(top5(a)) & set(top5(b)))
        total += ov
        checks.append((f"H1 top-5 overlap {step}", float(ov)))
    checks.append(("H1 top-5 overlap", float(total)))
    for name, mine in checks:
        if name not in hl or not close(mine, flt(hl[name]["value"])):
            bad.append(f"(b) headline {name}: printed "
                       f"{hl[name]['value'] if name in hl else 'missing'} but recomputed "
                       f"{mine!r}")
    if "H1" in hl and hl["H1"]["n"] != str(n):
        bad.append(f"(b) headline H1 n: printed {hl['H1']['n']} but recomputed {n}")
    loo_rows = [r for r in loo if r["analysis"] == "H1"]
    units = sorted({u for u, _ in pre})
    if [r["omitted"] for r in loo_rows] != units:
        bad.append("(b) leave_one_out H1: the omitted units differ from the H1 units")
    else:
        for r in loo_rows:
            mine, _ = h1_rho(pre, post, omit=r["omitted"])
            if not close(mine, flt(r["value"])):
                bad.append(f"(b) leave_one_out H1 omitting {r['omitted']}: printed "
                           f"{r['value']} but recomputed {mine!r}")
    ok.append(f"(b) H1 = {rho:.6f} over {n} unit-step pairs; 12 grid entries, rate-gap rho "
              f"{gap_rho:.6f}, top-5 overlap {total}/15 and {len(loo_rows)} leave-one-out "
              f"values recomputed")


# ------------------------------------------------------------------ (c) H2 and H3

def ntps_groups(root: Path) -> tuple[dict, dict]:
    groups, prevalence = {}, {}
    for r in read(root / "data" / "extracted" / "ntps_units.csv"):
        members = sorted({MERGED.get(m, m) for m in r["member_states"].split(";")})
        groups[r["unit"]] = members
        prevalence[r["unit"]] = float(r["prevalence"])
    return groups, prevalence


def group_values(values, denom, groups, scale):
    return {g: sum(values[u] for u in ms) / sum(denom[u] for u in ms) * scale
            for g, ms in groups.items() if ms}


def h2_rho(values, prevalence, omit=None):
    keys = sorted(k for k in values if k in prevalence and k != omit)
    return spearman([values[k] for k in keys], [prevalence[k] for k in keys]), len(keys), keys


def check_h2_h3(root, panel, idx, spec, headline, loo, bad, ok):
    groups, prevalence = ntps_groups(root)
    pop = {r["unit"]: int(r["population"]) for r in
           read(root / "data" / "extracted" / "state_population.csv") if r["population"]}
    s1 = cells(panel, "S1", YEAR)
    target = {u: n for u, _, n in s1}
    hl = {r["estimate"]: r for r in headline}

    def values(benchmark, shrinkage, denominator):
        harm = {u: flt(r["harm_averted_mean"])
                for u, r in idx[("S1", YEAR, benchmark, shrinkage)].items()}
        if denominator == "per population":
            return group_values(harm, pop, groups, 100000.0)
        return group_values(harm, target, groups, 1.0)

    rows = [r for r in spec if r["estimate"] == "H2"]
    for r in rows:
        key = (r["benchmark"], r["shrinkage"], r["denominator"])
        rho, n, _ = h2_rho(values(*key), prevalence)
        if not close(rho, flt(r["value"])) or str(n) != r["n"]:
            bad.append(f"(c) spec_curve H2 {key}: printed {r['value']} (n {r['n']}) but "
                       f"recomputed {rho!r} (n {n})")
        if boolean(r["main"]) != (key == H2_MAIN):
            bad.append(f"(c) spec_curve H2 {key}: main is {r['main']}")
    if len(rows) != 12:
        bad.append(f"(c) spec_curve H2: {len(rows)} entries; expected 12")
    main_vals = values(*H2_MAIN)
    rho, n, keys = h2_rho(main_vals, prevalence)
    lo, hi = fieller(rho, n)
    signed = {u: float(t - y) for u, y, t in s1}
    srho, sn, _ = h2_rho(group_values(signed, pop, groups, 100000.0), prevalence)
    slo, shi = fieller(srho, sn)
    for name, triple in (("H2", (rho, lo, hi)),
                         ("H2 signed shortfall per 100,000 (descriptive)", (srho, slo, shi))):
        if name not in hl:
            bad.append(f"(c) headline {name}: missing")
            continue
        for col, mine in zip(("value", "lo", "hi"), triple):
            if not close(mine, flt(hl[name][col])):
                bad.append(f"(c) headline {name} {col}: printed {hl[name][col]} but "
                           f"recomputed {mine!r}")
    if "H2" in hl and hl["H2"]["n"] != str(n):
        bad.append(f"(c) headline H2 n: printed {hl['H2']['n']} but recomputed {n}")
    loo_rows = [r for r in loo if r["analysis"] == "H2"]
    if [r["omitted"] for r in loo_rows] != keys:
        bad.append("(c) leave_one_out H2: the omitted units differ from the NTPS units")
    else:
        for r in loo_rows:
            mine, _, _ = h2_rho(main_vals, prevalence, omit=r["omitted"])
            if not close(mine, flt(r["value"])):
                bad.append(f"(c) leave_one_out H2 omitting {r['omitted']}: printed "
                           f"{r['value']} but recomputed {mine!r}")
    # H3 (§8.4)
    top_sum = total = 0.0
    for s in H3_STEPS:
        h = {u: flt(r["harm_averted_mean"]) for u, r in idx[(s, YEAR, "p75", "on")].items()}
        t5 = top5(h)
        top, tot = sum(h[u] for u in t5), sum(h.values())
        top_sum, total = top_sum + top, total + tot
        name = f"H3 share {s}"
        if (name not in hl or not close(top / tot, flt(hl[name]["value"]))
                or hl[name]["note"] != "top 5: " + ", ".join(t5)
                or hl[name]["n"] != str(len(h))):
            bad.append(f"(c) headline {name}: printed "
                       f"{hl[name]['value'] if name in hl else 'missing'} but recomputed "
                       f"{top / tot!r} (top 5: {', '.join(t5)})")
    if "H3" not in hl or not close(top_sum / total, flt(hl["H3"]["value"])):
        bad.append(f"(c) headline H3: printed {hl['H3']['value'] if 'H3' in hl else 'missing'}"
                   f" but recomputed {top_sum / total!r}")
    ok.append(f"(c) H2 = {rho:.6f} [{lo:.6f}, {hi:.6f}] over {n} NTPS units; 12 grid "
              f"entries, the signed shortfall row, {len(loo_rows)} leave-one-out values and "
              f"H3 = {top_sum / total:.6f} recomputed")
    return {"H2": (lo, hi)}


# ------------------------------------------------------------------ (d) labels

def check_labels(spec, headline, h2_interval, bad, ok):
    hl = {r["estimate"]: r for r in headline}
    out = []
    for est in ("H1", "H2"):
        rows = [r for r in spec if r["estimate"] == est]
        mains = [r for r in rows if boolean(r["main"])]
        if len(mains) != 1 or est not in hl:
            bad.append(f"(d) {est}: {len(mains)} main entries in spec_curve.csv")
            continue
        main_sign = sign(flt(mains[0]["value"]))
        signs = [sign(flt(r["value"])) for r in rows]
        for r, s in zip(rows, signs):
            agrees = main_sign in (1, -1) and s == main_sign
            if boolean(r["agrees"]) != agrees:
                bad.append(f"(d) spec_curve {est} {r['benchmark']} {r['shrinkage']} "
                           f"{r['year_window'] or r['denominator']}: agrees printed "
                           f"{r['agrees']} but the sign rule gives {agrees}")
        n_agree = sum(1 for s in signs if main_sign in (1, -1) and s == main_sign)
        lo, hi = ((flt(hl[est]["lo"]), flt(hl[est]["hi"])) if est == "H1"
                  else h2_interval)
        lab = label(lo, hi, signs, main_sign)
        for col, mine in (("n_grid", str(len(rows))), ("n_agree", str(n_agree)),
                          ("label", lab)):
            if hl[est][col] != mine:
                bad.append(f"(d) headline {est} {col}: printed {hl[est][col]!r} but plan 8.6 "
                           f"gives {mine!r} ({n_agree}/{len(rows)} entries agree; interval "
                           f"[{lo}, {hi}])")
        out.append(f"{est} {lab} ({n_agree}/{len(rows)})")
    ok.append("(d) labels: " + "; ".join(out))


# ------------------------------------------------------------------ (e) trend

def fit(years, xs, ns, achievement, indicator):
    rows = []
    for t, x, n in zip(years, xs, ns):
        if achievement:
            L, V = math.log((x + 0.5) / n), 1 / (x + 0.5)
        else:
            L = math.log((x + 0.5) / (n - x + 0.5))
            V = 1 / (x + 0.5) + 1 / (n - x + 0.5)
        X = [1.0, float(t - YEAR)] + ([1.0 if t == 2021 else 0.0] if indicator else [])
        rows.append((X, L, 1 / V))
    p = len(rows[0][0])
    xtwx = [[sum(w * X[i] * X[j] for X, _, w in rows) for j in range(p)] for i in range(p)]
    xtwl = [sum(w * X[i] * L for X, L, w in rows) for i in range(p)]
    inv = inverse(xtwx)
    b = [sum(inv[i][j] * xtwl[j] for j in range(p)) for i in range(p)]
    chi2 = sum(w * (L - sum(bi * xi for bi, xi in zip(b, X))) ** 2 for X, L, w in rows)
    return b[1], inv[1][1], chi2, len(rows) - p


def trends(panel: dict, step: str, units: list[str]) -> tuple[dict, float]:
    achievement = step == "S1"
    fits, status = {}, {}
    for u in units:
        ys = [y for y in TREND_YEARS[step] if (u, step, y) in panel]
        xs = [panel[(u, step, y)][0] for y in ys]
        ns = [panel[(u, step, y)][1] for y in ys]
        indicator = (not achievement) and 2021 in ys and any(y < 2021 for y in ys)
        other = sum(1 for y in ys if y != 2021) if indicator else len(ys)
        if len(ys) < 3 or other < 3:
            status[u] = "not estimable (fewer than 3 years)"
            continue
        fits[u] = fit(ys, xs, ns, achievement, indicator) + (ys,)
        status[u] = "estimated"
    chi2 = sum(f[2] for f in fits.values() if f[3] > 0)
    df = sum(f[3] for f in fits.values() if f[3] > 0)
    phi = 1.0 if df == 0 else max(1.0, chi2 / df)
    out = {}
    for u in units:
        if u not in fits:
            out[u] = {"status": status[u], "rising": False}
            continue
        slope, v, _, _, ys = fits[u]
        se = math.sqrt(phi * v)
        lo, hi = slope - Z * se, slope + Z * se
        out[u] = {"status": "estimated", "slope": slope, "se": se, "lo": lo, "hi": hi,
                  "years": ";".join(map(str, ys)),
                  "rising": hi < 0 if achievement else lo > 0}
    return out, phi


def check_trend(panel, trend_rows, prio, sens, bad, ok):
    main = {(r["unit"], r["step"]): r for r in trend_rows if r["basis"] == "main"}
    units = sorted({u for u, _ in main})
    rising = {}
    phis = {}
    for step in ("S1", "S2", "S3", "S4", "S5", "S6"):
        if step in NO_TREND:
            for u in units:
                r = main.get((u, step))
                if r is None or r["trend_status"] != NO_TREND[step] or boolean(r["rising"]):
                    bad.append(f"(e) state_trend {u} {step}: expected "
                               f"{NO_TREND[step]!r} and rising False")
                rising[(u, step)] = False
            continue
        res, phi = trends(panel, step, units)
        phis[step] = phi
        for u in units:
            r, m = main.get((u, step)), res[u]
            rising[(u, step)] = m["rising"]
            if r is None:
                bad.append(f"(e) state_trend {u} {step}: missing")
                continue
            if r["trend_status"] != m["status"] or boolean(r["rising"]) != m["rising"]:
                bad.append(f"(e) state_trend {u} {step}: printed {r['trend_status']!r}, "
                           f"rising {r['rising']}, but recomputed {m['status']!r}, rising "
                           f"{m['rising']}")
                continue
            if m["status"] != "estimated":
                continue
            if r["years"] != m["years"]:
                bad.append(f"(e) state_trend {u} {step} years: printed {r['years']} but "
                           f"recomputed {m['years']}")
            for col in ("slope", "se", "lo", "hi"):
                if not close(m[col], flt(r[col]), REL_TREND):
                    bad.append(f"(e) state_trend {u} {step} {col}: printed {r[col]} but "
                               f"recomputed {m[col]!r}")
            if not close(phi, flt(r["phi"]), REL_TREND):
                bad.append(f"(e) state_trend {u} {step} phi: printed {r['phi']} but "
                           f"recomputed {phi!r}")
    for r in prio:
        key = (r["unit"], r["step"])
        if boolean(r["rising"]) != rising.get(key):
            bad.append(f"(e) state_priority {r['unit']} {r['step']} rising: printed "
                       f"{r['rising']} but the trend gives {rising.get(key)}")
        t = tier(flt(r["p_top5"]), rising.get(key, False))
        if r["tier"] != t:
            bad.append(f"(e) state_priority {r['unit']} {r['step']} tier: printed "
                       f"{r['tier']!r} but plan 6.4-6.5 give {t!r}")
    for r in sens:
        key = (r["unit"], r["step"])
        if boolean(r["rising"]) != rising.get(key):
            bad.append(f"(e) state_priority_sensitivity {r['unit']} {r['step']} "
                       f"{r['analysis']} rising: printed {r['rising']}")
        t = tier(flt(r["p_topk"]), rising.get(key, False))
        if r["tier"] != t or boolean(r["tier_changed"]) != (t != r["tier_main"]):
            bad.append(f"(e) state_priority_sensitivity {r['unit']} {r['step']} "
                       f"{r['analysis']} tier: printed {r['tier']!r} but the rule gives "
                       f"{t!r}")
    bihar = main.get(("Bihar", "S3"))
    res, _ = trends(panel, "S3", ["Bihar"])
    ok.append(f"(e) trend: every unit of S1, S3, S4, S6 refitted; S3 Bihar slope "
              f"{flt(bihar['slope']):.6f} [{flt(bihar['lo']):.6f}, {flt(bihar['hi']):.6f}], "
              f"rising {bihar['rising']}; phi_S3 {phis['S3']:.4f}; "
              f"{sum(rising.values())} rising flags; tiers of {len(prio)} priority rows and "
              f"{len(sens)} sensitivity rows follow plan 6.4-6.5")


# ------------------------------------------------------------------ (f) source rows

PRIO_FROM_SUMMARY = ("harm_averted_mean", "lo", "hi", "p_top5", "small_far_behind", "rate",
                     "rate_bench")
SENS = {"k3": ("p75", "p_top3"), "k8": ("p75", "p_top8"), "benchmark_median": ("median",
        "p_top5"), "benchmark_p90": ("p90", "p_top5")}


def check_sources(root, idx, spec, headline, prio, sens, bad, ok):
    hl = {r["estimate"]: r for r in headline}
    for est in ("H1", "H2"):
        mains = [r for r in spec if r["estimate"] == est and r["main"] == "True"]
        if len(mains) != 1 or est not in hl:
            bad.append(f"(f) headline {est}: no single main row in spec_curve.csv")
            continue
        for col in ("value", "n"):
            if hl[est][col] != mains[0][col]:
                bad.append(f"(f) headline {est} {col}: printed {hl[est][col]} but the main "
                           f"row of spec_curve.csv has {mains[0][col]}")
    pop = {r["unit"]: int(r["population"]) for r in
           read(root / "data" / "extracted" / "state_population.csv") if r["population"]}
    tier_main = {}
    for r in prio:
        src = idx.get((r["step"], int(r["year"]), "p75", "on"), {}).get(r["unit"])
        tier_main[(r["unit"], r["step"])] = r["tier"]
        if src is None:
            bad.append(f"(f) state_priority {r['unit']} {r['step']}: no summary row")
            continue
        for col in PRIO_FROM_SUMMARY:
            if r[col] != src[col]:
                bad.append(f"(f) state_priority {r['unit']} {r['step']} {col}: printed "
                           f"{r[col]} but state_harm_draws_summary.csv has {src[col]}")
        mine = (flt(src["harm_averted_mean"]) / pop[r["unit"]] * 100000
                if pop.get(r["unit"]) else None)
        if not close(mine, flt(r["per_100k"])):
            bad.append(f"(f) state_priority {r['unit']} {r['step']} per_100k: printed "
                       f"{r['per_100k']} but recomputed {mine!r}")
    for r in sens:
        bench, col = SENS[r["analysis"]]
        src = idx.get((r["step"], int(r["year"]), bench, "on"), {}).get(r["unit"])
        if src is None or r["p_topk"] != src[col] or r["benchmark"] != bench:
            bad.append(f"(f) state_priority_sensitivity {r['unit']} {r['step']} "
                       f"{r['analysis']}: p_topk {r['p_topk']} does not match the summary")
        elif r["harm_averted_mean"] != src["harm_averted_mean"]:
            bad.append(f"(f) state_priority_sensitivity {r['unit']} {r['step']} "
                       f"{r['analysis']}: harm_averted_mean does not match the summary")
        if r["tier_main"] != tier_main.get((r["unit"], r["step"])):
            bad.append(f"(f) state_priority_sensitivity {r['unit']} {r['step']} "
                       f"{r['analysis']}: tier_main {r['tier_main']!r} differs from "
                       f"state_priority.csv")
    ok.append(f"(f) headline H1 and H2 equal the main rows of spec_curve.csv; {len(prio)} "
              f"priority rows and {len(sens)} sensitivity rows equal their summary rows")


# ------------------------------------------------------------------ main

def problems(root: Path = ROOT) -> tuple[list[str], list[str]]:
    out_dir = root / "outputs"
    panel = load_panel(root)
    summary = read(out_dir / "state_harm_draws_summary.csv")
    prio = read(out_dir / "state_priority.csv")
    sens = read(out_dir / "state_priority_sensitivity.csv")
    spec = read(out_dir / "spec_curve.csv")
    headline = read(out_dir / "headline.csv")
    loo = read(out_dir / "leave_one_out.csv")
    trend_rows = read(out_dir / "state_trend.csv")
    idx = summary_index(summary)
    bad: list[str] = []
    ok: list[str] = []
    check_s3(panel, summary, prio, bad, ok)
    check_h1(idx, spec, headline, loo, bad, ok)
    h2 = check_h2_h3(root, panel, idx, spec, headline, loo, bad, ok)
    check_labels(spec, headline, h2["H2"], bad, ok)
    check_trend(panel, trend_rows, prio, sens, bad, ok)
    check_sources(root, idx, spec, headline, prio, sens, bad, ok)
    return bad, ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT), help="repository root (default: this one)")
    a = ap.parse_args(argv)
    try:
        bad, ok = problems(Path(a.root))
    except Exception as e:  # noqa: BLE001  any error is a failed check
        bad, ok = [f"{type(e).__name__}: {e}"], []
    for line in ok:
        print(f"ok {line}")
    for b in bad:
        print(f"FAIL: {b}")
    if bad:
        return 1
    print("OK: the standard-library recompute agrees with outputs/ ((a)-(f))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
