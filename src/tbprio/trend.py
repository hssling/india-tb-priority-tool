"""Trend of each unit-step and the rising-risk flag (analysis plan §6.5, §7).

Main model (§7.2), on observed (not shrunken) counts:
- S3, S4, S6: the empirical logit L_t = log((x_t + 1/2) / (n_t - x_t + 1/2)), with variance
  V_t = 1/(x_t + 1/2) + 1/(n_t - x_t + 1/2);
- S1: L_t = log((y_t + 1/2) / e_t), with variance V_t = 1/(y_t + 1/2) (y notified, e target).
Weighted least squares L_t = b0 + b1 (t - 2023) + g [t = 2021], weights w_t = 1/V_t. The 2021
indicator is fitted only where the unit-step has a year before 2021 (so never for S1 in the
main model). Var(b1) = phi_s [(X'WX)^-1]_11, with phi_s = max(1, sum Pearson chi2 / sum
residual df) pooled over the units of step s in the main model; 95% CI b1 +/- 1.96 SE.

A unit-step needs at least 3 non-NA years, and at least 3 non-NA years other than 2021 where
the indicator is fitted; otherwise "not estimable (fewer than 3 years)". S2: "not estimable
(definition change)"; S5: "no trend".

Sensitivity (§7.3): S3, S4, S6 without the 2021 indicator over the same years; S1 with the
indicator (the 2022-2023 slope). The minimum-years rule is that of the main analysis
(fixed value: "Main analysis requires >=3 non-2020 years"); a sensitivity fit needs only an
identifiable slope. The sensitivity uses the step's main-model phi_s (§7.2: "pooled over all
units of step s in the main model").

Rising (§6.5): the main 95% CI lies wholly on the worsening side: lo > 0 for S3, S4, S6
(a rising loss rate); hi < 0 for S1 (falling achievement).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import panel

Z = 1.96
REF_YEAR = 2023
INDICATOR_YEAR = 2021
MIN_YEARS = 3
ACHIEVEMENT_STEPS = ("S1",)
TREND_YEARS = {
    "S1": (2021, 2022, 2023),
    "S3": (2018, 2019, 2021, 2022, 2023),
    "S4": (2019, 2021, 2022, 2023),
    "S6": (2018, 2019, 2021, 2022, 2023),
}
NO_TREND = {
    "S2": "not estimable (definition change)",
    "S5": "no trend",
}
ESTIMATED = "estimated"
TOO_FEW = "not estimable (fewer than 3 years)"


class NotEstimable(ValueError):
    """The unit-step has too few years for the model."""


@dataclass
class Fit:
    years: tuple[int, ...]
    indicator: bool
    slope: float
    var_unscaled: float   # [(X'WX)^-1]_11
    chi2: float           # Pearson chi2 = sum w (L - fitted)^2
    df: int               # residual degrees of freedom


def transform(x, n, achievement: bool) -> tuple[np.ndarray, np.ndarray]:
    """(L, V): the transformed rate and its variance (§7.2)."""
    x = np.asarray(x, dtype=float)
    n = np.asarray(n, dtype=float)
    if achievement:
        return np.log((x + 0.5) / n), 1.0 / (x + 0.5)
    return np.log((x + 0.5) / (n - x + 0.5)), 1.0 / (x + 0.5) + 1.0 / (n - x + 0.5)


def default_indicator(years) -> bool:
    """The 2021 indicator is fitted where the unit-step has 2021 and a year before it."""
    years = list(years)
    return INDICATOR_YEAR in years and any(t < INDICATOR_YEAR for t in years)


def fit(years, x, n, *, achievement: bool = False, indicator: bool | None = None,
        min_years: bool = True) -> Fit:
    """Weighted least squares of the transformed rate on (year - 2023) [+ the 2021
    indicator]. Raises NotEstimable when the unit-step has too few years: with
    ``min_years`` (the main analysis) fewer than 3 years, or fewer than 3 years other
    than 2021 where the indicator is fitted; without it, an unidentifiable slope."""
    years = [int(t) for t in years]
    if len(set(years)) != len(years):
        raise ValueError(f"duplicate years {years}")
    order = np.argsort(years)
    t = np.array(years, dtype=float)[order]
    x = np.asarray(x, dtype=float)[order]
    n = np.asarray(n, dtype=float)[order]
    if indicator is None:
        indicator = default_indicator(years)
    if indicator and INDICATOR_YEAR not in years:
        indicator = False  # nothing to separate: the column would be all zero
    other = int(np.sum(t != INDICATOR_YEAR)) if indicator else len(t)
    if min_years:
        if len(t) < MIN_YEARS or other < MIN_YEARS:
            raise NotEstimable(TOO_FEW)
    elif other < 2:
        raise NotEstimable("slope not identifiable")
    L, V = transform(x, n, achievement)
    w = 1.0 / V
    cols = [np.ones_like(t), t - REF_YEAR]
    if indicator:
        cols.append((t == INDICATOR_YEAR).astype(float))
    X = np.column_stack(cols)
    XtW = X.T * w
    inv = np.linalg.inv(XtW @ X)
    beta = inv @ (XtW @ L)
    resid = L - X @ beta
    return Fit(tuple(int(v) for v in t), bool(indicator), float(beta[1]), float(inv[1, 1]),
               float(np.sum(w * resid ** 2)), int(len(t) - X.shape[1]))


def pooled_phi(fits) -> float:
    """phi_s = max(1, sum chi2 / sum residual df); fits with 0 df contribute nothing."""
    chi2 = sum(f.chi2 for f in fits if f.df > 0)
    df = sum(f.df for f in fits if f.df > 0)
    return 1.0 if df == 0 else max(1.0, chi2 / df)


def interval(f: Fit, phi: float) -> tuple[float, float, float]:
    """(se, lo, hi) of the slope with residual scaling phi."""
    se = float(np.sqrt(phi * f.var_unscaled))
    return se, f.slope - Z * se, f.slope + Z * se


def slope(years, x, n, *, achievement: bool = False, indicator: bool | None = None,
          phi: float = 1.0) -> tuple[float, float, float]:
    """(slope, lo, hi) of one unit-step under the main-analysis rules (§7.2), with the
    step's pooled phi passed in (1 by default). Raises NotEstimable with < 3 years."""
    f = fit(years, x, n, achievement=achievement, indicator=indicator)
    _, lo, hi = interval(f, phi)
    return f.slope, lo, hi


def worsening(step: str, lo: float, hi: float) -> bool:
    """The 95% CI lies wholly on the worsening side (§6.5)."""
    return hi < 0 if step in ACHIEVEMENT_STEPS else lo > 0


def _unit_series(rows, step):
    """unit -> (years, x, n) over the step's trend years, non-NA cells only."""
    out: dict[str, tuple[list, list, list]] = {}
    for year in TREND_YEARS[step]:
        for c in panel.cells(rows, step, year):
            ys, xs, ns = out.setdefault(c["unit"], ([], [], []))
            ys.append(year)
            xs.append(c["numerator"])
            ns.append(c["denominator"])
    return out


def step_trends(rows: list[dict], step: str, units: list[str]) -> tuple[list[dict], float]:
    """The main and sensitivity trend of every unit of a step, and the step's phi_s.

    ``units``: every unit to report (those with no estimable trend get the reason)."""
    if step in NO_TREND:
        return [_row(u, step, NO_TREND[step]) for u in units], float("nan")
    achievement = step in ACHIEVEMENT_STEPS
    series = _unit_series(rows, step)
    main: dict[str, Fit] = {}
    status: dict[str, str] = {}
    for u in units:
        if u not in series:
            status[u] = TOO_FEW
            continue
        ys, xs, ns = series[u]
        try:
            main[u] = fit(ys, xs, ns, achievement=achievement,
                          indicator=None if not achievement else False)
            status[u] = ESTIMATED
        except NotEstimable as e:
            status[u] = str(e)
    phi = pooled_phi(main.values())
    out = []
    for u in units:
        r = _row(u, step, status[u])
        r["phi"] = phi
        if u in series:
            r["years"] = ";".join(str(t) for t in series[u][0])
            r["n_years"] = len(series[u][0])
        if u in main:
            f = main[u]
            se, lo, hi = interval(f, phi)
            r.update(indicator=f.indicator, slope=f.slope, se=se, lo=lo, hi=hi,
                     chi2=f.chi2, df=f.df, rising=worsening(step, lo, hi))
        if u in series:
            ys, xs, ns = series[u]
            sens_indicator = achievement  # S1: with the indicator; others: without
            r["sens_model"] = ("with 2021 indicator (2022-2023 slope)" if achievement
                               else "without 2021 indicator")
            try:
                fs = fit(ys, xs, ns, achievement=achievement, indicator=sens_indicator,
                         min_years=False)
                _, slo, shi = interval(fs, phi)
                r.update(sens_status=ESTIMATED, sens_slope=fs.slope, sens_lo=slo,
                         sens_hi=shi, sens_rising=worsening(step, slo, shi))
            except NotEstimable as e:
                r["sens_status"] = f"not estimable ({e})"
        r["rising_differs"] = r["rising"] != r["sens_rising"]
        out.append(r)
    return out, phi


def _row(unit: str, step: str, status: str) -> dict:
    return {"unit": unit, "step": step, "trend_status": status, "years": "", "n_years": 0,
            "indicator": None, "slope": None, "se": None, "lo": None, "hi": None,
            "chi2": None, "df": None, "phi": None, "rising": False, "sens_model": "",
            "sens_status": "", "sens_slope": None, "sens_lo": None, "sens_hi": None,
            "sens_rising": False, "rising_differs": False}
