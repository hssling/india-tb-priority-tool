"""Empirical-Bayes priors by the method of moments (analysis plan §6.1).

beta_binomial: S2-S6, loss count x out of n. gamma_poisson: S1, notified y with
exposure e = target. Shrinkage "off" uses the Jeffreys prior (JEFFREYS_BINOMIAL,
JEFFREYS_POISSON) in place of these.
"""
from __future__ import annotations

import numpy as np

BOUND_LO = 1.0
BOUND_HI = 1e6
JEFFREYS_BINOMIAL = (0.5, 0.5)
JEFFREYS_POISSON = (0.5, 0.0)


def beta_binomial(x: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """(alpha, beta) of the Beta prior of the loss rate over the U units of a step-year.

    m = sum x / sum n; s2 = unweighted variance of x/n (divisor U - 1);
    tau2 = s2 - m(1 - m) mean(1/n); S = m(1 - m)/tau2 - 1 bounded to [1, 1e6]
    (1e6 when tau2 <= 0); alpha = m S, beta = (1 - m) S.

    m = 0 (no patient lost) has no prior: the caller reports the step-year as having no
    harm to avert (§6.1), and this raises. m = 1 has no proper prior either and raises.
    """
    x = np.asarray(x, dtype=float)
    n = np.asarray(n, dtype=float)
    U = len(x)
    if U < 2:
        raise ValueError("beta_binomial needs at least 2 units")
    m = x.sum() / n.sum()
    if not 0.0 < m < 1.0:
        raise ValueError(f"beta_binomial: pooled rate m = {m} (needs 0 < m < 1)")
    p = x / n
    s2 = float(np.sum((p - m) ** 2) / (U - 1))
    tau2 = s2 - m * (1.0 - m) * float(np.mean(1.0 / n))
    if tau2 <= 0:
        S = BOUND_HI
    else:
        S = min(max(m * (1.0 - m) / tau2 - 1.0, BOUND_LO), BOUND_HI)
    return float(m * S), float((1.0 - m) * S)


def gamma_poisson(y, e) -> tuple[float, float]:
    """(alpha, beta) (shape, rate) of the Gamma prior of achievement a = y/e (S1).

    m = sum y / sum e; s2 = unweighted variance of y/e (divisor U - 1);
    v = s2 - m mean(1/e); alpha = m^2/v bounded to [1, 1e6] (1e6 when v <= 0);
    beta = alpha/m.
    """
    y = np.asarray(y, dtype=float)
    e = np.asarray(e, dtype=float)
    U = len(y)
    if U < 2:
        raise ValueError("gamma_poisson needs at least 2 units")
    m = y.sum() / e.sum()
    if not m > 0:
        raise ValueError(f"gamma_poisson: pooled achievement m = {m} (needs m > 0)")
    a = y / e
    s2 = float(np.sum((a - m) ** 2) / (U - 1))
    v = s2 - m * float(np.mean(1.0 / e))
    if v <= 0:
        alpha = BOUND_HI
    else:
        alpha = min(max(m * m / v, BOUND_LO), BOUND_HI)
    return float(alpha), float(alpha / m)
