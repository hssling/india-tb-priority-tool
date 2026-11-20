"""P(top-k), tiers and the small-but-far-behind flag (analysis plan §6.4-§6.6)."""
from __future__ import annotations

import numpy as np

K_MAIN = 5
K_SENSITIVITY = (3, 8)


def p_topk(draws: dict, k: int) -> dict[str, float]:
    """P(top-k) of each unit: the mean over draws of its top-k score.

    In each draw the units are ordered by harm averted and the k largest score 1. A unit
    whose harm averted is 0 in a draw scores 0 in that draw. Units above 0 tied at the
    k-th place share the places left equally; units with zero harm get no share.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    units = list(draws)
    if not units:
        return {}
    H = np.vstack([np.asarray(draws[u], dtype=float) for u in units])
    pos = H > 0
    U = H.shape[0]
    if U <= k:
        score = pos.astype(float)
    else:
        vk = np.sort(H, axis=0)[U - k, :]   # the k-th largest value in each draw
        gt = H > vk                          # strictly above the k-th place (hence > 0)
        eq = (H == vk) & pos                 # tied at the k-th place and above 0
        n_gt = gt.sum(axis=0)
        n_eq = eq.sum(axis=0)
        share = np.divide(k - n_gt, n_eq, out=np.zeros(H.shape[1]), where=n_eq > 0)
        score = gt.astype(float) + eq * share
    p = score.mean(axis=1)
    return {u: float(p[i]) for i, u in enumerate(units)}


def tier(p: float, rising: bool) -> str:
    """Tier from P(top-k) (§6.4) and the rising flag (§6.5).

    "act now" P >= 0.80; "probable priority" 0.50 <= P < 0.80; "uncertain"
    0.20 <= P < 0.50; "lower priority" P < 0.20. With the rising flag, "uncertain" and
    "lower priority" become "watch: rising"; the two upper tiers never change.
    """
    if p >= 0.80:
        return "act now"
    if p >= 0.50:
        return "probable priority"
    if rising:
        return "watch: rising"
    return "uncertain" if p >= 0.20 else "lower priority"


def flags(gaps: dict, harm_mean: dict) -> dict[str, dict]:
    """unit -> {"small_far_behind": bool} (§6.6).

    gaps: the rate gap on posterior means (r_u - r_bench, or a_bench - a_u for S1);
    harm_mean: harm_averted_mean. A unit is flagged when its gap is at or above the 75th
    percentile of the gaps AND its harm_averted_mean is strictly below the median of
    harm_averted_mean, over the same units (numpy linear percentiles). The flag never
    changes the tier.
    """
    units = list(gaps)
    if set(units) != set(harm_mean):
        raise ValueError("gaps and harm_mean must cover the same units")
    g = np.array([gaps[u] for u in units], dtype=float)
    h = np.array([harm_mean[u] for u in units], dtype=float)
    g75 = np.percentile(g, 75, method="linear")
    h50 = np.percentile(h, 50, method="linear")
    return {u: {"small_far_behind": bool(g[i] >= g75 and h[i] < h50)}
            for i, u in enumerate(units)}
