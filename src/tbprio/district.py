"""The district modules (analysis plan §9).

National module, data year 2018 (§9.1), from ITR 2019 Annexure 1.13
(data/extracted/district_2018.csv):
- D1 "not initiated on treatment": n = total notified, x = n - total initiated. A district
  where the number initiated exceeds the number notified is NA.
- D2 "public-sector treatment not successful": with success count N and printed percentage
  p of the 2017 public cohort, n = round(N / (p/100)) (half up) and x = n - N. Every D2 value
  carries ``rounded_from_percent`` and the cohort range implied by the rounding of p: with h
  half of the last printed digit of p, N/((p + h)/100) (clipped below at N) to
  N/((p - h)/100). p = 100 gives x = 0; p = 0 or a blank cell is NA.
- Per step, across all districts: beta-binomial shrinkage, the p75 benchmark, harm averted
  per draw, P(top-20) and tiers, and the small-but-far-behind flag, with the State
  functions (shrink, harm, priority) and a new default_rng(20261121) per step. No trend, no
  rising flag, no population view.
- State-relative funnel: z_d = (p_d - p_S) / sqrt(p_S (1 - p_S) / n_d) around the State's
  pooled proportion. Multiplicative phi = the mean of the squared z_d winsorised at their
  10th and 90th percentiles, from all districts of States with at least two districts;
  limits widen by sqrt(phi) when phi > 1. Additive DerSimonian-Laird tau^2 with State
  centres. Flags at the 99.8% limits (z = 3.09) under the multiplicative adjustment.

Madhya Pradesh and Maharashtra, notifications 2022-2024 (§9.2), and any district input of
the tool's ``district`` command (§9.3):
- Change d = n_final - n_base with Poisson SE sqrt(n_base + n_final); the State's pooled
  change R - 1, R = N_final / N_base summed over its districts.
- z_d = (d - n_base (R - 1)) / sqrt(n_base + n_final); on the relative scale y_d = d / n_base
  with SE s_d = sqrt(n_base + n_final) / n_base around R - 1.
- Multiplicative phi from the 10%-winsorised z_d within the State; additive tau^2 =
  max(0, (Q - (D - 1)) / (sum w - sum w^2 / sum w)), w = 1/s_d^2.
- Flags "fell beyond adjusted limits" / "rose beyond adjusted limits": outside the 99.8%
  limits under the multiplicative adjustment. No tiers. A district with n_base = 0 is NA.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

import numpy as np

from . import harm, priority

SEED = harm.SEED
YEAR_2018 = 2018
K_DISTRICT = 20
BENCHMARK = "p75"
Z95 = 1.96
Z998 = 3.09
WINSOR = (10.0, 90.0)
LABEL_2018 = "2018 data (historical)"
STEPS_2018 = {"D1": "not initiated on treatment",
              "D2": "public-sector treatment not successful (2017 cohort)"}

FELL = "fell beyond adjusted limits"
ROSE = "rose beyond adjusted limits"
WITHIN_CHANGE = "within adjusted limits"
ABOVE = "above State limits"
BELOW = "below State limits"
WITHIN_STATE = "within State limits"
NO_FUNNEL = "no funnel"


# ---- shared ------------------------------------------------------------------------

def winsorised_phi(z) -> float:
    """phi = mean of the squared z, each set to the 10th / 90th percentile (numpy linear)
    where it lies outside them (Spiegelhalter, Stat Med 2005;24:1185)."""
    z = np.asarray(z, dtype=float)
    if z.size == 0:
        return float("nan")
    lo, hi = np.percentile(z, WINSOR, method="linear")
    return float(np.mean(np.clip(z, lo, hi) ** 2))


def widen(phi: float) -> float:
    """The factor applied to the limits: sqrt(phi) if phi > 1, else 1."""
    return math.sqrt(phi) if phi == phi and phi > 1 else 1.0


def position(z: float, limit: float, low: str, high: str, within: str) -> str:
    if z != z:
        return ""
    if z > limit:
        return high
    if z < -limit:
        return low
    return within


# ---- §9.1 national module, data year 2018 -------------------------------------------

def unit_name(state: str, district: str) -> str:
    """The unit of a district row: "State | District", as printed (§9.1)."""
    return f"{state} | {district}"


def d2_cohort(n_success: int, pct: str) -> tuple[int, float, float]:
    """(cohort n, range low, range high) from success N and printed percentage p (§9.1).

    n = round(N / (p/100)), half up; the range is N/((p + h)/100) to N/((p - h)/100), h half
    of the last printed digit of p, its low end clipped at N."""
    p = Decimal(pct)
    if p <= 0:
        raise ValueError(f"percentage {pct!r} must be above 0")
    N = Decimal(n_success)
    n = int((N / (p / 100)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    exp = -p.as_tuple().exponent if p.as_tuple().exponent < 0 else 0
    h = Decimal("0.5") * (Decimal(10) ** -exp)
    lo = max(N / ((p + h) / 100), N)
    hi = N / ((p - h) / 100) if p - h > 0 else Decimal("Infinity")
    return n, float(lo), float(hi)


def national_cells(recs: list[dict]) -> list[dict]:
    """Panel-like cells of D1 and D2 (unit, year, step, numerator, denominator, na,
    na_reason, flag), with state, district, provenance and the D2 cohort range."""
    out = []
    for r in recs:
        base = {"unit": unit_name(r["state"], r["district"]), "state": r["state"],
                "district": r["district"], "year": YEAR_2018,
                "source_file": r["source_file"], "pdf_page": r["pdf_page"],
                "table_id": r["table_id"], "cohort_lo": None, "cohort_hi": None}
        # D1
        n, init = r["notified"], r["initiated"]
        reasons = []
        if n == 0:
            reasons.append("NA:denominator_zero")
        elif init > n:
            reasons.append("NA:initiated_exceeds_notified")
        out.append({**base, "step": "D1", "numerator": None if reasons else n - init,
                    "denominator": None if reasons else n, "na": bool(reasons),
                    "na_reason": ";".join(reasons), "flag": ";".join(reasons)})
        # D2
        N, p = r["success_public_n"], r["success_public_pct"]
        flags = ["rounded_from_percent", "cohort_2017_public"]
        cell = {**base, "step": "D2", "numerator": None, "denominator": None}
        if N is None or p is None:
            reasons = ["NA:blank_cell"]
        elif Decimal(p) == 0:
            reasons = ["NA:percent_zero"]
        else:
            nn, lo, hi = d2_cohort(N, p)
            reasons = []
            if nn == 0:
                reasons = ["NA:denominator_zero"]
            elif nn - N < 0:
                reasons = ["NA:loss_negative"]
            else:
                cell.update(numerator=nn - N, denominator=nn, cohort_lo=lo, cohort_hi=hi)
        out.append({**cell, "na": bool(reasons), "na_reason": ";".join(reasons),
                    "flag": ";".join(reasons + ([] if reasons else flags))})
    return out


def state_funnel(cells: list[dict]) -> dict:
    """The State-relative funnel of one step (§9.1) over its non-NA cells.

    Returns {"units": unit -> {state_rate, z, z_additive, funnel_flag, position_95,
    additive_position_998, additive_position_95}, "phi", "tau2", "D", "G",
    "no_funnel": {state: reason}}."""
    by_state: dict[str, list[dict]] = {}
    for c in cells:
        by_state.setdefault(c["state"], []).append(c)
    no_funnel: dict[str, str] = {}
    pS: dict[str, float] = {}
    for s, cs in sorted(by_state.items()):
        if len(cs) < 2:
            no_funnel[s] = "one district with a value"
            continue
        x = sum(c["numerator"] for c in cs)
        n = sum(c["denominator"] for c in cs)
        p = x / n
        if not 0 < p < 1:
            no_funnel[s] = f"State pooled proportion {p:g} (no binomial variance)"
            continue
        pS[s] = p
    inc = [c for c in cells if c["state"] in pS]
    z = {}
    for c in inc:
        p = pS[c["state"]]
        ph = c["numerator"] / c["denominator"]
        z[c["unit"]] = (ph - p) / math.sqrt(p * (1 - p) / c["denominator"])
    phi = winsorised_phi([z[c["unit"]] for c in inc])
    D, G = len(inc), len(pS)
    w = {c["unit"]: c["denominator"] / (pS[c["state"]] * (1 - pS[c["state"]])) for c in inc}
    Q = sum(w[c["unit"]] * (c["numerator"] / c["denominator"] - pS[c["state"]]) ** 2
            for c in inc)
    sw = sum(w.values())
    within = sum(sum(w[c["unit"]] ** 2 for c in inc if c["state"] == s)
                 / sum(w[c["unit"]] for c in inc if c["state"] == s) for s in pS)
    tau2 = max(0.0, (Q - (D - G)) / (sw - within)) if D > G else 0.0
    f = widen(phi)
    units = {}
    for c in inc:
        u, p = c["unit"], pS[c["state"]]
        ph = c["numerator"] / c["denominator"]
        za = (ph - p) / math.sqrt(p * (1 - p) / c["denominator"] + tau2)
        units[u] = {
            "state_rate": p, "z": z[u], "z_additive": za,
            "funnel_flag": position(z[u], Z998 * f, BELOW, ABOVE, WITHIN_STATE),
            "position_95": position(z[u], Z95 * f, BELOW, ABOVE, WITHIN_STATE),
            "additive_position_998": position(za, Z998, BELOW, ABOVE, WITHIN_STATE),
            "additive_position_95": position(za, Z95, BELOW, ABOVE, WITHIN_STATE),
        }
    return {"units": units, "phi": phi, "tau2": tau2, "D": D, "G": G, "Q": Q,
            "no_funnel": no_funnel, "limit_998": Z998 * f, "limit_95": Z95 * f}


NATIONAL_COLS = ["data_label", "state", "district", "step", "step_name", "year", "numerator",
                 "denominator", "rate_observed", "rate", "rate_bench", "gap",
                 "harm_averted_mean", "lo", "hi", "p_top20", "tier", "small_far_behind",
                 "state_rate", "z", "phi", "limit_998", "funnel_flag", "position_95",
                 "tau2", "z_additive", "additive_position_998", "additive_position_95",
                 "cohort_lo", "cohort_hi", "na", "flag", "source_file", "pdf_page",
                 "table_id"]


def national(recs: list[dict], n_draws: int = harm.N_DRAWS) -> tuple[list[dict], dict]:
    """§9.1 on the rows of district_2018.csv: output rows (NATIONAL_COLS) and, per step,
    a summary (units, benchmark, prior, phi, tau2, D, G, States without a funnel, NA)."""
    cells = national_cells(recs)
    out: list[dict] = []
    info: dict[str, dict] = {}
    for step in STEPS_2018:
        sc = [c for c in cells if c["step"] == step]
        ok = [c for c in sc if not c["na"]]
        rng = np.random.default_rng(SEED)  # reset per district step (§10.1)
        est = harm.estimate(sc, step, YEAR_2018, BENCHMARK, True, rng, n_draws)
        p20 = priority.p_topk(est.draws, K_DISTRICT)
        summ = {u: harm.summary(est.draws[u]) for u in est.units}
        gaps = {u: est.gap(u) for u in est.units}
        fl = priority.flags(gaps, {u: summ[u][0] for u in est.units})
        fun = state_funnel(ok)
        info[step] = {"units": len(est.units), "na": len(sc) - len(ok),
                      "rate_bench": est.rate_bench, "alpha": est.alpha, "beta": est.beta,
                      "phi": fun["phi"], "tau2": fun["tau2"], "D": fun["D"], "G": fun["G"],
                      "no_funnel": fun["no_funnel"], "limit_998": fun["limit_998"],
                      "limit_95": fun["limit_95"]}
        for c in sorted(sc, key=lambda c: c["unit"]):
            u = c["unit"]
            row = {k: None for k in NATIONAL_COLS}
            row.update({"data_label": LABEL_2018, "state": c["state"],
                        "district": c["district"], "step": step,
                        "step_name": STEPS_2018[step], "year": YEAR_2018,
                        "numerator": c["numerator"], "denominator": c["denominator"],
                        "na": c["na"], "flag": c["flag"], "source_file": c["source_file"],
                        "pdf_page": c["pdf_page"], "table_id": c["table_id"],
                        "cohort_lo": c["cohort_lo"], "cohort_hi": c["cohort_hi"]})
            if not c["na"]:
                mean, lo, hi = summ[u]
                row.update({
                    "rate_observed": c["numerator"] / c["denominator"],
                    "rate": est.post_mean[u], "rate_bench": est.rate_bench,
                    "gap": gaps[u], "harm_averted_mean": mean, "lo": lo, "hi": hi,
                    "p_top20": p20[u], "tier": priority.tier(p20[u], False),
                    "small_far_behind": fl[u]["small_far_behind"],
                    "phi": fun["phi"], "tau2": fun["tau2"]})
                f = fun["units"].get(u)
                if f is None:
                    row["funnel_flag"] = (f"{NO_FUNNEL}: "
                                          f"{fun['no_funnel'].get(c['state'], '')}")
                else:
                    row.update(f)
                    row["limit_998"] = fun["limit_998"]
            out.append(row)
    return out, info


# ---- §9.2 / §9.3 change funnel -------------------------------------------------------

def change_funnel(units: list[tuple[str, int, int]]) -> dict:
    """The change funnel of one State (§9.2). ``units``: (district, n_base, n_final).

    Returns {"R", "change", "phi", "tau2", "D", "limit_998", "limit_95", "units": district
    -> {...}, "na": [districts with n_base = 0]}."""
    Nb = sum(b for _, b, _ in units)
    Nf = sum(f for _, _, f in units)
    if Nb == 0:
        raise ValueError("the State's baseline total is 0: no pooled change")
    R = Nf / Nb
    ok = [(d, b, f) for d, b, f in units if b > 0]
    na = sorted(d for d, b, _ in units if b == 0)
    z, y, s = {}, {}, {}
    for d, b, f in ok:
        z[d] = ((f - b) - b * (R - 1)) / math.sqrt(b + f)
        y[d] = (f - b) / b
        s[d] = math.sqrt(b + f) / b
    phi = winsorised_phi(list(z.values())) if len(ok) >= 2 else float("nan")
    w = {d: 1 / s[d] ** 2 for d in s}
    D = len(ok)
    if D >= 2:
        Q = sum(w[d] * (y[d] - (R - 1)) ** 2 for d in w)
        sw = sum(w.values())
        tau2 = max(0.0, (Q - (D - 1)) / (sw - sum(v * v for v in w.values()) / sw))
    else:
        Q, tau2 = float("nan"), float("nan")
    f_ = widen(phi)
    out = {}
    for d, b, f in ok:
        za = ((y[d] - (R - 1)) / math.sqrt(s[d] ** 2 + tau2)) if tau2 == tau2 else float("nan")
        lim = Z998 * f_ if phi == phi else float("nan")
        out[d] = {
            "change": f - b, "rel_change": y[d], "se_rel": s[d], "z": z[d],
            "z_additive": za,
            "flag": position(z[d], lim, FELL, ROSE, WITHIN_CHANGE) if lim == lim else "",
            "position_95": (position(z[d], Z95 * f_, FELL, ROSE, WITHIN_CHANGE)
                            if phi == phi else ""),
            "additive_position_998": position(za, Z998, FELL, ROSE, WITHIN_CHANGE),
            "additive_position_95": position(za, Z95, FELL, ROSE, WITHIN_CHANGE),
        }
    return {"R": R, "change": R - 1, "phi": phi, "tau2": tau2, "Q": Q, "D": D,
            "limit_998": Z998 * f_, "limit_95": Z95 * f_, "units": out, "na": na,
            "N_base": Nb, "N_final": Nf}


def change_cols(years: list[int]) -> list[str]:
    return (["state", "district"] + [f"n_{y}" for y in years]
            + ["base_year", "final_year", "change", "rel_change", "se_rel", "state_ratio",
               "state_change", "z", "phi", "limit_998", "flag", "position_95", "tau2",
               "z_additive", "additive_position_998", "additive_position_95", "na",
               "entry_flag", "source_file", "table_id"])


def notifications(rows: list[dict], states: list[str], base_year: int | None = None,
                  final_year: int | None = None) -> tuple[list[dict], dict, list[int]]:
    """§9.2 on validated district rows (schema.validate_district). ``states``: the States
    to analyse, each separately; rows whose ``state`` is blank take the single State
    named. Returns (output rows, per-State summary, years)."""
    if not states:
        raise ValueError("name at least one State")
    years = sorted({r["year"] for r in rows})
    b = base_year if base_year is not None else years[0]
    f = final_year if final_year is not None else years[-1]
    if b >= f:
        raise ValueError(f"the base year {b} must precede the final year {f}")
    blank = any(not r["state"] for r in rows)
    if blank and len(states) != 1:
        raise ValueError("the input has no state column: name exactly one State")
    out: list[dict] = []
    info: dict[str, dict] = {}
    for st in states:
        sr = [r for r in rows if (r["state"] or st).casefold() == st.casefold()]
        if not sr:
            raise ValueError(f"no rows for State {st!r} in the input "
                             f"(States: {sorted({r['state'] for r in rows})})")
        st = sr[0]["state"] or st  # the input's spelling
        if st in info:
            raise ValueError(f"State {st!r} named twice")
        by: dict[str, dict[int, dict]] = {}
        for r in sr:
            by.setdefault(r["district"], {})[r["year"]] = r
        missing = sorted(d for d, ys in by.items() if b not in ys or f not in ys)
        if missing:
            raise ValueError(f"{st}: no {b} or {f} value for {missing}")
        units = [(d, by[d][b]["notified"], by[d][f]["notified"]) for d in sorted(by)]
        fun = change_funnel(units)
        info[st] = {k: fun[k] for k in ("R", "change", "phi", "tau2", "Q", "D", "limit_998",
                                        "limit_95", "na", "N_base", "N_final")}
        info[st]["districts"] = len(by)
        for d in sorted(by):
            ys = by[d]
            any_row = ys[f]
            row = {"state": st, "district": d, "base_year": b, "final_year": f,
                   "state_ratio": fun["R"], "state_change": fun["R"] - 1,
                   "entry_flag": ";".join(sorted({ys[y].get("flag", "") for y in ys} - {""})),
                   "source_file": any_row.get("source_file", ""),
                   "table_id": any_row.get("table_id", "")}
            for y in years:
                row[f"n_{y}"] = ys[y]["notified"] if y in ys else None
            u = fun["units"].get(d)
            if u is None:
                row.update({k: None for k in ("change", "rel_change", "se_rel", "z", "phi",
                                              "limit_998", "flag", "position_95", "tau2",
                                              "z_additive", "additive_position_998",
                                              "additive_position_95")})
                row["na"] = "NA:base_zero"
            else:
                row.update(u)
                row.update({"phi": fun["phi"], "tau2": fun["tau2"],
                            "limit_998": fun["limit_998"], "na": ""})
            out.append(row)
    return out, info, years


def cells_by_step(rows: list[dict]) -> dict[str, list[dict]]:
    """National output rows grouped by step (for the report)."""
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["step"], []).append(r)
    return out

