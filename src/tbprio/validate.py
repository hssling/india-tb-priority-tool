"""Headline estimates, labels and leave-one-out (analysis plan §8, §10.4).

- H1 (§8.2): temporal stability. Steps S3, S4, S6; for each unit-step the pre-period mean of
  harm_averted_mean and the 2023 harm_averted_mean. Within each step the two are ranked
  separately (average ranks) and divided by (n_s + 1); rho_H1 is the Pearson correlation of
  these normalised ranks over all pooled unit x step pairs. Interval: bootstrap over units
  (each drawn unit brings all its unit-step pairs; duplicated units rank as ties), 10,000
  draws, 2.5th and 97.5th percentiles; a draw with undefined rho is discarded and counted.
- H2 (§8.3): Spearman rho between an NTPS reporting unit's 2023 S1 harm averted per 100,000
  (sum of harm / sum of population over its member units) and NTPS prevalence; Fisher-z
  interval with Fieller's variance, SE = sqrt(1.06 / (n - 3)), as in tb_state_score.
- H3 (§8.4): the share of harm averted (S2-S5, 2023) in each step's top-5 units.
- Label (§8.6): "supported" only if the main 95% interval excludes the null (both ends
  strictly on one side) and >= 80% of the grid entries agree in strict sign with the main
  estimate; otherwise "not established".

Top-5 sets break ties at the fifth place alphabetically by unit name.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import rankdata

Z = 1.96
FIELLER = 1.06
N_BOOT = 10_000
SUPPORTED = "supported"
NOT_ESTABLISHED = "not established"
AGREE_SHARE = 0.80  # applied as 5 x agree >= 4 x entries


# ---- ranks and correlations ----------------------------------------------------------

def pearson(x, y) -> float | None:
    """Pearson correlation; None when either side has no variation."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    dx, dy = x - x.mean(), y - y.mean()
    sxx, syy = float(np.sum(dx * dx)), float(np.sum(dy * dy))
    if len(x) < 2 or sxx <= 0 or syy <= 0:
        return None
    return float(np.sum(dx * dy) / math.sqrt(sxx * syy))


def spearman(x, y) -> float | None:
    """Spearman rho: the Pearson correlation of average ranks."""
    return pearson(rankdata(np.asarray(x, dtype=float), method="average"),
                   rankdata(np.asarray(y, dtype=float), method="average"))


def fisher_ci(rho: float | None, n: int) -> tuple[float | None, float | None]:
    """95% Fisher-z interval with Fieller's SE, sqrt(1.06 / (n - 3)); (None, None) if
    n <= 3 or rho is None; |rho| = 1 gives (rho, rho) (as tb_state_score)."""
    if rho is None or n <= 3:
        return None, None
    if abs(rho) >= 1.0:
        return rho, rho
    z, se = math.atanh(rho), math.sqrt(FIELLER / (n - 3))
    return math.tanh(z - Z * se), math.tanh(z + Z * se)


def top5(values: dict[str, float], k: int = 5) -> list[str]:
    """The k units with the largest value; ties at the k-th place broken alphabetically."""
    return [u for u, _ in sorted(values.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


# ---- H1 ------------------------------------------------------------------------------

def _pooled_rank_rho(idx: np.ndarray, pre: dict, post: dict) -> np.ndarray:
    """rho for each row of idx (rows of unit indices): within-step normalised ranks,
    pooled over steps. pre/post: step -> array over units (NaN = unit-step excluded)."""
    B = idx.shape[0]
    xs, ys = [], []
    for step in sorted(pre):
        P, Q = pre[step][idx], post[step][idx]
        keep = ~np.isnan(P)
        n = keep.sum(axis=1)[:, None].astype(float)
        if keep.all():
            rp = rankdata(P, method="average", axis=1)
            rq = rankdata(Q, method="average", axis=1)
        else:
            rp = rankdata(P, method="average", axis=1, nan_policy="omit")
            rq = rankdata(Q, method="average", axis=1, nan_policy="omit")
        xs.append(rp / (n + 1.0))
        ys.append(rq / (n + 1.0))
    X, Y = np.hstack(xs), np.hstack(ys)
    out = np.full(B, np.nan)
    for b in range(B):
        m = ~np.isnan(X[b])
        r = pearson(X[b][m], Y[b][m])
        if r is not None:
            out[b] = r
    return out


def _arrays(pre_vals: dict, post_vals: dict):
    """Units (alphabetical) and step -> arrays over units of included unit-steps."""
    keys = set(pre_vals) | set(post_vals)
    units = sorted({u for u, _ in keys})
    steps = sorted({s for _, s in keys})
    pre, post, excluded = {}, {}, []
    for s in steps:
        a, b = np.full(len(units), np.nan), np.full(len(units), np.nan)
        for i, u in enumerate(units):
            p, q = pre_vals.get((u, s)), post_vals.get((u, s))
            if p is None or q is None or p != p or q != q:
                if (u, s) in keys:
                    excluded.append((u, s))
                continue
            a[i], b[i] = p, q
        pre[s], post[s] = a, b
    # units with no included unit-step take no part
    used = [i for i in range(len(units)) if any(not np.isnan(pre[s][i]) for s in steps)]
    units = [units[i] for i in used]
    pre = {s: v[used] for s, v in pre.items()}
    post = {s: v[used] for s, v in post.items()}
    return units, pre, post, excluded


def h1_rho(pre_vals: dict, post_vals: dict, omit: str | None = None) -> float | None:
    """The H1 point estimate. pre_vals / post_vals: (unit, step) -> value (None or NaN
    excludes the unit-step); ``omit`` leaves out all of one unit's pairs (§8.7)."""
    if omit is not None:
        pre_vals = {k: v for k, v in pre_vals.items() if k[0] != omit}
        post_vals = {k: v for k, v in post_vals.items() if k[0] != omit}
    units, pre, post, _ = _arrays(pre_vals, post_vals)
    r = _pooled_rank_rho(np.arange(len(units))[None, :], pre, post)[0]
    return None if r != r else float(r)


def h1_stability(pre_vals: dict, post_vals: dict, rng: np.random.Generator | None = None,
                 n_boot: int = N_BOOT) -> dict:
    """H1 (§8.2): rho, the unit-bootstrap 95% interval (when rng is given), the number of
    unit-step pairs and units, the discarded draws, the excluded unit-steps and the top-5
    overlap per step (pre-period mean vs 2023)."""
    units, pre, post, excluded = _arrays(pre_vals, post_vals)
    U = len(units)
    rho = _pooled_rank_rho(np.arange(U)[None, :], pre, post)[0]
    out = {"rho": None if rho != rho else float(rho), "lo": None, "hi": None,
           "n_pairs": int(sum(int(np.sum(~np.isnan(v))) for v in pre.values())),
           "n_units": U, "n_boot": 0, "n_discarded": 0, "excluded": sorted(excluded)}
    if rng is not None:
        idx = rng.integers(0, U, size=(n_boot, U))
        draws = _pooled_rank_rho(idx, pre, post)
        ok = draws[~np.isnan(draws)]
        lo, hi = np.percentile(ok, [2.5, 97.5], method="linear")
        out.update(lo=float(lo), hi=float(hi), n_boot=n_boot,
                   n_discarded=int(n_boot - ok.size))
    overlap = {}
    for s in sorted(pre):
        keep = ~np.isnan(pre[s])
        a = {u: float(pre[s][i]) for i, u in enumerate(units) if keep[i]}
        b = {u: float(post[s][i]) for i, u in enumerate(units) if keep[i]}
        overlap[s] = len(set(top5(a)) & set(top5(b)))
    out["top5_overlap"] = overlap
    return out


# ---- H2 ------------------------------------------------------------------------------

def group_values(values: dict[str, float], denom: dict[str, float],
                 groups: dict[str, list[str]], scale: float = 1.0) -> dict[str, float]:
    """NTPS unit -> sum(values) / sum(denom) x scale over its member units (§8.3)."""
    out = {}
    for g, members in groups.items():
        if not members:
            continue
        num = sum(values[u] for u in members)
        den = sum(denom[u] for u in members)
        out[g] = num / den * scale
    return out


def h2_external(values: dict[str, float], prevalence: dict[str, float],
                omit: str | None = None) -> dict:
    """H2 (§8.3): Spearman rho between the NTPS units' values and prevalence, with the
    Fieller interval. ``omit`` leaves out one NTPS unit (§8.7)."""
    keys = sorted(k for k in values if k in prevalence and k != omit)
    rho = spearman([values[k] for k in keys], [prevalence[k] for k in keys])
    lo, hi = fisher_ci(rho, len(keys))
    return {"rho": rho, "lo": lo, "hi": hi, "n": len(keys), "units": keys}


# ---- H3 ------------------------------------------------------------------------------

def h3_concentration(harm_by_step: dict[str, dict[str, float]]) -> dict:
    """H3 (§8.4): share of harm averted in each step's top-5 units, summed over steps,
    and the share for each step."""
    top_sum = total = 0.0
    per_step = {}
    for s in sorted(harm_by_step):
        h = harm_by_step[s]
        top = sum(h[u] for u in top5(h))
        tot = sum(h.values())
        per_step[s] = {"share": top / tot if tot > 0 else None, "top5": top5(h),
                       "top": top, "total": tot}
        top_sum += top
        total += tot
    return {"share": top_sum / total if total > 0 else None, "per_step": per_step}


# ---- label ---------------------------------------------------------------------------

def sign(v: float | None, null: float = 0.0) -> int | None:
    """Strict sign of v - null: +1, -1, 0, or None when v is undefined."""
    if v is None or v != v:
        return None
    return (v > null) - (v < null)


def label(main_interval, null, grid_signs, main_sign: int | None = None) -> str:
    """§8.6. main_interval: (lo, hi) of the main estimate; grid_signs: the strict sign
    (+1, -1, 0 or None) of every grid entry, the main entry included; main_sign: the sign
    of the main estimate (by default, the side of the null the interval lies on).

    "supported" only if both ends of the interval are strictly on one side of the null
    AND >= 80% of the grid entries have the main estimate's strict sign; an entry with
    sign 0 or None does not agree."""
    lo, hi = main_interval
    if lo is None or hi is None or lo != lo or hi != hi:
        return NOT_ESTABLISHED
    if lo > null and hi > null:
        side = 1
    elif lo < null and hi < null:
        side = -1
    else:
        return NOT_ESTABLISHED
    s = side if main_sign is None else main_sign
    if s not in (1, -1):
        return NOT_ESTABLISHED
    grid = list(grid_signs)
    if not grid:
        return NOT_ESTABLISHED
    agree = sum(1 for g in grid if g == s)
    # agree / len >= 0.80, in integers: 5 agree >= 4 len
    return SUPPORTED if 5 * agree >= 4 * len(grid) else NOT_ESTABLISHED


def n_agree(grid_signs, main_sign: int | None) -> int:
    return sum(1 for g in grid_signs if main_sign in (1, -1) and g == main_sign)
