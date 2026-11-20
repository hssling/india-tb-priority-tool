"""Benchmark and harm-averted draws for one step-year and specification (analysis plan
§6.1-§6.3, §10.1).

For S2-S6 the rate is the loss rate r = x/n; for S1 it is the achievement a = notified /
target. In draw d:
- S2-S6: harm averted = max(0, n_u (r_u(d) - r_bench)), r_u(d) ~ Beta(alpha + x, beta + n - x);
- S1: harm averted = max(0, target_u (a_bench - a_u(d))), a_u(d) ~ Gamma(alpha + y, rate
  beta + e).
The benchmark is a percentile (numpy linear) of the posterior-mean rates, computed once per
step-year and specification: p75 / median / p90 of performance, i.e. the 25th / 50th / 10th
percentile of loss rates and the 75th / 50th / 90th percentile of achievement.

Units are processed in alphabetical order of unit name and each unit's draws are taken in
one call. The caller passes a fresh numpy.random.default_rng(SEED) for each draw set.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import panel, shrink

SEED = 20261121
N_DRAWS = 10_000
BENCHMARKS = ("p75", "median", "p90")
LOSS_PERCENTILE = {"p75": 25.0, "median": 50.0, "p90": 10.0}
ACHIEVEMENT_PERCENTILE = {"p75": 75.0, "median": 50.0, "p90": 90.0}
ACHIEVEMENT_STEPS = ("S1",)


@dataclass
class StepYear:
    """The estimates of one step-year under one specification."""
    step: str
    year: int
    benchmark: str
    shrinkage: bool
    units: list[str]
    x: dict[str, int]          # count lost (S2-S6) or notified (S1)
    n: dict[str, int]          # denominator (S2-S6) or target (S1)
    alpha: float
    beta: float
    post_mean: dict[str, float]
    rate_bench: float
    no_harm: bool              # m = 0: no patient lost in any unit (§6.1)
    rate_draws: dict[str, np.ndarray] = field(repr=False)
    draws: dict[str, np.ndarray] = field(repr=False)

    def gap(self, unit: str) -> float:
        """Rate gap on posterior means (§6.6): r_u - r_bench, or a_bench - a_u for S1."""
        if self.step in ACHIEVEMENT_STEPS:
            return self.rate_bench - self.post_mean[unit]
        return self.post_mean[unit] - self.rate_bench


def estimate(rows: list[dict], step: str, year: int, benchmark: str, shrinkage: bool,
             rng: np.random.Generator, n_draws: int = N_DRAWS) -> StepYear:
    if benchmark not in BENCHMARKS:
        raise ValueError(f"unknown benchmark {benchmark!r}; expected one of {BENCHMARKS}")
    cells = panel.cells(rows, step, year)
    if not cells:
        raise ValueError(f"no non-NA cell for {step} {year}")
    units = [c["unit"] for c in cells]
    x = {c["unit"]: c["numerator"] for c in cells}
    n = {c["unit"]: c["denominator"] for c in cells}
    xs = np.array([x[u] for u in units], dtype=float)
    ns = np.array([n[u] for u in units], dtype=float)
    achievement = step in ACHIEVEMENT_STEPS

    if not achievement and xs.sum() == 0:
        # m = 0: the step-year has no harm to avert; every unit's harm averted is 0.
        return StepYear(step, year, benchmark, shrinkage, units, x, n, float("nan"),
                        float("nan"), {u: 0.0 for u in units}, 0.0, True,
                        {u: np.zeros(n_draws) for u in units},
                        {u: np.zeros(n_draws) for u in units})

    if achievement:
        a, b = shrink.gamma_poisson(xs, ns) if shrinkage else shrink.JEFFREYS_POISSON
        post_mean = {u: (a + x[u]) / (b + n[u]) for u in units}
        q = ACHIEVEMENT_PERCENTILE[benchmark]
    else:
        a, b = shrink.beta_binomial(xs, ns) if shrinkage else shrink.JEFFREYS_BINOMIAL
        post_mean = {u: (a + x[u]) / (a + b + n[u]) for u in units}
        q = LOSS_PERCENTILE[benchmark]
    bench = float(np.percentile(np.array([post_mean[u] for u in units]), q, method="linear"))

    rate_draws: dict[str, np.ndarray] = {}
    draws: dict[str, np.ndarray] = {}
    for u in units:  # alphabetical: panel.cells sorts by unit name
        if achievement:
            r = rng.gamma(a + x[u], 1.0 / (b + n[u]), size=n_draws)
            h = np.maximum(0.0, n[u] * (bench - r))
        else:
            r = rng.beta(a + x[u], b + n[u] - x[u], size=n_draws)
            h = np.maximum(0.0, n[u] * (r - bench))
        rate_draws[u] = r
        draws[u] = h
    return StepYear(step, year, benchmark, shrinkage, units, x, n, float(a), float(b),
                    {u: float(v) for u, v in post_mean.items()}, bench, False, rate_draws,
                    draws)


def draws(rows: list[dict], step: str, year: int, benchmark: str, shrinkage: bool,
          rng: np.random.Generator) -> dict[str, np.ndarray]:
    """unit -> its 10,000 harm-averted draws (§6.3), in alphabetical order of unit."""
    return estimate(rows, step, year, benchmark, shrinkage, rng).draws


def summary(h: np.ndarray) -> tuple[float, float, float]:
    """(harm_averted_mean, lo, hi): the mean and the 2.5th and 97.5th percentiles."""
    lo, hi = np.percentile(h, [2.5, 97.5], method="linear")
    return float(h.mean()), float(lo), float(hi)
