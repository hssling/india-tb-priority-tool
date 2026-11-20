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
The computation is src/tbprio/state.py, shared with the tool's ``state`` command.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.tbprio import panel  # noqa: E402
from src.tbprio.state import (  # noqa: E402,F401  (names used by run_validate and tests)
    COLS, KS, MAIN_BENCHMARK, NA_OUT_COLS, OUTPUT_FILES, PRIORITY_COLS, PRIORITY_YEAR,
    REGISTERED_BASIS, SENSITIVITIES, SENSITIVITY_COLS, SPECS, STEPS, SUMMARY_COLS,
    TREND_COLS, analyse, fmt, messages, rising_flags, run, summary_rows, trends, write,
    write_csv,
)

EXTRACTED = ROOT / "data" / "extracted"
PANEL_CSV = EXTRACTED / "state_panel.csv"
REGISTERED_CSV = EXTRACTED / "state_panel_s6_2022_registered.csv"
POP_CSV = EXTRACTED / "state_population.csv"
OUTPUTS = ROOT / "outputs"


def main(out_dir: Path = OUTPUTS) -> int:
    tables = run(panel.load(PANEL_CSV), panel.load(REGISTERED_CSV),
                 panel.load_population(POP_CSV), PANEL_CSV.stem, REGISTERED_CSV.stem)
    paths = write(tables, Path(out_dir))
    for m in messages(tables):
        print(m)
    for p in paths:
        print(f"wrote {p.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
