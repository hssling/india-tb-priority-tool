# TB Priority Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pre-registered, reproducible State and district TB priority tool for India, and a submission-ready manuscript. The tool ranks where closing a care-pathway gap would avert the most harm, with uncertainty, tiers and trajectory.

**Architecture:**
- A Python package `tbprio` (standard library plus numpy/scipy) under `src/tbprio/`. It does extraction-agnostic analysis on a long-format panel (unit, year, step, numerator, denominator).
- Extraction scripts under `src/extract/` build that panel from the India TB Reports (State) and Lok Sabha Q802 (district).
- The analysis plan `docs/analysis_plan.md` is pushed to a new public repo before any estimate.
- Outputs go to `outputs/`. The checks in `verification/` recompute headline values independently.
- The manuscript is local under `manuscript/`.

**Tech Stack:**
- Python 3.14 (`python -I`), numpy 2.3.5, scipy 1.16.3, pdfplumber (extraction), python-docx (district file), pytest, matplotlib (figures).
- pandoc + Microsoft Word for the submission build, as in the sibling repos.

**Spec:** `docs/superpowers/specs/2026-11-21-tb-priority-tool-design.md`. Read §4.0 first: it holds the decisions settled after the builder check.

## Global Constraints
- Python 3.14, always `python -I`; LF line endings; seed 20261121; numpy `default_rng(seed)`, reset per analysis; 10,000 draws.
- No imputation. NA cells are listed in `outputs/na_cells.csv`. Every extracted value carries source_file, pdf_page and table_id. Every table is checked against its printed total where one exists.
- No estimate (harm, rate, priority, trend, correlation) is computed or printed before the registration commit is pushed (Task 2 gate). Inventory (which tables and columns exist) is allowed before it.
- `data_raw/` and `manuscript/` are git-ignored and never committed. Source PDFs come from the sibling repos' `data_raw` copies, verified by SHA-256 into `data/source_manifest.csv`. No new downloads without asking the author; never bypass a CAPTCHA.
- Wording: "shortfall against target", never "missed cases" for the target-based measure. No causal language. Tiers, never ranks, in headline text.
- Labels: "supported" only if the main 95% interval excludes the null AND ≥80% of specification-grid entries agree in sign with the main estimate; otherwise "not established".
- Commits end with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
- Single author: Siddalingaiah H S, ORCID 0000-0002-4771-8285, Department of Community Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumkur 572106, Karnataka, India; contact hssling@yahoo.com.

## Fixed analysis values (Task 2 copies these into the registered plan verbatim)

**Units and years**
- **State units:** the States/UTs as printed, with the coarsening used in tb_acf_campaign §9.4 (merged units summed) applied identically every year.
- **Data years:** 2018, 2019, 2020, 2021, 2022 and 2023, from ITR 2019, ITR 2020, ITR 2021, the TB Annual Report 2022, ITR 2023 and ITR 2024.
- **Main priority year:** 2023.
- **Main trend and stability analyses:** exclude 2020; 2021 is kept with a year indicator. Sensitivity: all years.

**Steps.** A step is used only if Task 1 finds it printed for 2023. The harm is the count of patients lost at that step.

| Step | Name | Harm counted | Rate | Notes |
|---|---|---|---|---|
| S1 | `shortfall` | target − notified (the CTD notification target) | achievement a = notified/target | Years with printed targets only |
| S2 | `not_rr_tested` | notified − tested for rifampicin resistance | | |
| S3 | `died` | deaths in the DS-TB outcome cohort | | |
| S4 | `ltfu` | lost to follow-up in the DS-TB cohort | | |
| S5 | `drtb_not_success` | DR-TB cohort − successful | | |
| S6 | `hiv_unknown` | notified − HIV status known | | Only if printed for ≥4 years |

**Shrinkage**
- Binomial steps (S2–S6): beta-binomial empirical Bayes, by method of moments per step-year. Posterior draws come from Beta(α + x, β + n − x).
- S1: gamma-Poisson on notified with exposure = target.

**Benchmark** (per step-year, on posterior-mean rates across units)
- Main: the 75th percentile of performance, i.e. the 25th percentile of loss rates (the better quartile). Sensitivities: the median; the best decile.
- **Harm averted** (unit u, step s) = max(0, n_u·(r_u − r_bench)). For S1 it is max(0, a_bench·target_u − notified_u).
- Computed per draw, with 10,000 draws.

**Priority and tiers**
- k = 5 (main); sensitivities k = 3 and k = 8.
- P(top-k) is computed within each step, from draws.
- Tiers: "act now" P ≥ 0.80; "probable priority" 0.50 ≤ P < 0.80; "uncertain" 0.20 ≤ P < 0.50; "lower priority" P < 0.20.
- **Rising-risk flag:** the trend slope's 95% CI lies wholly on the worsening side. A unit in "uncertain" or "lower priority" with the rising flag is relabelled "watch: rising".
- **Small but far behind:** the unit's rate gap (r_u − r_bench) is in the worst quartile across units AND its harm averted is below the median. Reported as a flag; never changes the tier.
- **Population view:** harm averted per 100,000 population, using the ITR-printed population. Shown alongside; never used for tiers.

**Trend**
- Per unit and step: weighted least squares of logit(rate) on year (log achievement for S1), with weights from the binomial (Poisson) variance of the transformed rate.
- Slope 95% CI: normal, from the WLS variance.
- Main analysis requires ≥3 non-2020 years; otherwise "trend not estimable".

**Headline estimates and their nulls**

| | Estimate | Null | Interval |
|---|---|---|---|
| H1 | Temporal stability: Spearman ρ between each unit's mean harm averted over the pre-period (2018, 2019, 2021) and its 2023 harm averted, pooled over steps S2–S5, unit × step | 0 | Bootstrap over units, 10,000 draws |
| H2 | External association: Spearman ρ between State 2023 S1 shortfall per 100,000 population and NTPS prevalence (19–20 units; State groups population-weighted as in tb_state_score) | 0 | Fieller interval, as in tb_state_score |

Also reported for H1: top-5 overlap.

- **H3 (descriptive, no label):** the share of total harm averted (summed over steps S2–S5) in the top-5 units.

**Specification grids**
- H1: benchmark {p75, median, p90} × shrinkage {on, off} × year window {excluding 2020, including 2020} = 12 entries.
- H2: benchmark {p75, median, p90} × shrinkage {on, off} × denominator {per population, per target} = 12 entries.

**District (Madhya Pradesh, Maharashtra; 2022–2024 notifications only)**
- Change 2022→2024 per district, with Poisson SE √(n22 + n24).
- Funnel around the State's pooled change: multiplicative overdispersion φ from 10%-winsorised z (Spiegelhalter 2005) and additive DerSimonian–Laird τ².
- Flags: "fell beyond adjusted limits" and "rose beyond adjusted limits".
- No tiers at district level. The paper states that a notification fall can mean less TB or less case-finding.

**Controller rulings after Task 1 (21 Nov 2026; fixed before registration; Task 2 copies them into the analysis plan)**
- **Data year 2020 is dropped entirely.** ITR 2021 has no text layer. Main-analysis data years: 2018, 2019, 2021, 2022 and 2023. The "including 2020" sensitivity is replaced, for H1, by the year-window axis {pre-period 2018, 2019, 2021} vs {2019, 2021}.
- **Unit coarsening.** Units are coarsened to the 2018 structure in every year: DNH&DD merged into Gujarat, Lakshadweep into Kerala, Ladakh into J&K. Small UTs are not separately prioritised; this is a stated limitation.
- **S1** uses 2021–2023 only, the years with printed targets. Its trend uses those 3 years.
- **S2** changes definition in 2022 (bacteriologically confirmed patients only). S2 is used for the 2023 priorities only; trend "not estimable (definition change)"; excluded from H1.
- **S3** for 2018 = public + private deaths.
- **S4** for 2018 is public only and is excluded. The S4 pre-period is 2019 and 2021.
- **S5** DR-TB cohorts are not comparable across editions. S5 is used for the 2023 priorities only; no trend; excluded from H1.
- **S6** has all years.
- **H1** pools S3, S4 and S6 only.
- **National district module, data year 2018 (ITR 2019 Annexure 1.13, about 760 districts).**
  - Steps:
    - D1 "not initiated on treatment" = total notified − total initiated;
    - D2 "public-sector treatment not successful" = the 2017 public cohort (success N ÷ success %) − success N. Rounding from % is flagged.
  - The same within-step harm, shrinkage, P(top-k) and tiers as the States, with k = 20.
  - A State-relative funnel per district.
  - Labelled as 2018 data (historical).
- **MP/MH district trend (AU802, 2022–2024).** Kept as in the plan. There is no 2018→2022 linkage, because districts were renamed or split. The Vidisha duplicate is kept once and flagged.

## Review Focus
1. **Missing step data.** A unit has NA for a step in 2023 (e.g. no DR-TB cohort for a small UT). Expected: the unit is excluded from that step only, listed in `na_cells.csv`, and P(top-k) is computed over the remaining units. Pinned in Task 4: `test_missing_step_excludes_unit_only_from_that_step`.
2. **Above-target or zero-loss units.** notified > target, or x = 0 deaths. Expected: harm averted is 0 (never negative), and shrinkage still gives a finite posterior. Pinned in Task 4: `test_harm_averted_floor_zero_and_zero_counts`.
3. **Merged or renamed units across editions** (e.g. Dadra and Nagar Haveli + Daman and Diu; J&K/Ladakh). Expected: one unit name per year via an explicit crosswalk; an unmapped name raises an error naming it. Pinned in Task 3: `test_unmapped_unit_name_raises`.
4. **A district CSV with a different layout** (extra columns, different column order, a total row). Expected: schema validation accepts optional columns, drops a "Total" row with a warning, and fails clearly on a missing required column. Pinned in Task 6: `test_district_schema_variants`.
5. **Small units dominating rates.** Expected: absolute harm drives tiers, so a UT with n < 100 cannot reach "act now" from a high rate alone. Pinned in Task 4: `test_small_unit_cannot_dominate_tiers`.

---

### Task 1: Scaffold, source manifest and data inventory (no estimates)

**Files:**
- Create: `README.md` (stub), `LICENSE` (MIT), `LICENSE-DATA` (CC BY 4.0), `ENVIRONMENT.md`, `data/source_manifest.csv`, `docs/data_inventory.md`, `tools/fetch_sources.py` (copies the named PDFs from the sibling repos' `data_raw` into `data_raw/` and verifies SHA-256), `src/__init__.py`, `tests/test_manifest.py`.

**Interfaces:**
- Produces: `data/source_manifest.csv` with columns `path, origin, bytes, sha256`.
- Produces: `docs/data_inventory.md`. For each edition (2019–2024) and each step S1–S6, it records the annexure number, page, column header verbatim, units covered and the printed-total row. It records which years print State targets. It records what ITR 2019/ITR 2020 print at district level (from a page scan; see the controller note in the brief).
- Covers AU802 too: the table count and the unit count per State.

- [ ] Step 1: Write `tests/test_manifest.py::test_manifest_digests_match`, asserting that every manifest row's file exists in `data_raw/` with a matching sha256.
- [ ] Step 2: Implement `tools/fetch_sources.py` and run it. It copies from `../tb_state_score/data_raw/india_tb_report/`, `../tb_acf_campaign/data_raw/official/` (ITR 2019, TB Annual Report 2022), `../tb_state_score/data_raw/icmr_ntps/` and the author-supplied `data_raw/pq/AU802_LlE1Wb.docx`.
- [ ] Step 3: Write `docs/data_inventory.md` by reading the PDFs (pdfplumber, page by page, with `flush_cache()` to bound memory). Record structure only: headers, pages and coverage. Compute no rate, ratio or sum beyond reading a printed total.
- [ ] Step 4: Run `python -I -m pytest -q`. Expected: PASS.
- [ ] Step 5: Commit.

### Task 2: Analysis plan and registration (HARD GATE)

**Files:**
- Create: `docs/analysis_plan.md`, `docs/registration_event.json`, `verification/check_plan_order.py`, `tests/test_plan_order.py`.

**Interfaces:**
- Produces: the plan text with §1–§11 frozen and §12 "Deviations (dated)".
- Produces: `check_plan_order.main() -> int`, which asserts four things:
  - the registration commit is an ancestor of HEAD;
  - no commit before it touches `outputs/` or `src/tbprio/{harm,shrink,priority,trend}.py`;
  - the plan text above §12 is byte-identical at every later commit;
  - `docs/registration_event.json` exists.

- [ ] Step 1: Write the plan. It states:
  - the questions;
  - the units and years;
  - steps S1–S6 as found in Task 1 (a step not printed for 2023 is dropped, with the reason);
  - every value in "Fixed analysis values" above, verbatim;
  - the headline estimates H1–H3 with their nulls, grids and the label rule;
  - the district module;
  - what had been seen: the ITR tables, the companion repos' State descriptive values, and the AU802 district counts as printed;
  - that no estimate had been computed.
- [ ] Step 2: Write `tests/test_plan_order.py` covering a synthetic repo where an output commit precedes registration (expect FAIL) and a plan edit above §12 (expect FAIL).
- [ ] Step 3: Implement `check_plan_order.py`, reusing `../tb_acf_campaign/verification/check_plan_order.py` logic.
- [ ] Step 4: Commit the plan. **The controller** creates the public repo `hssling/india-tb-priority-tool`, pushes, and records `pushed_at` from the GitHub API in `docs/registration_event.json`, then commits that file. The implementer does not push.

### Task 3: State panel extraction

**Files:**
- Create: `src/extract/itr_state.py`, `src/extract/crosswalk.py`, `data/extracted/state_panel.csv`, `data/extracted/state_population.csv`, `data/extracted/ntps_units.csv` (copied from `../tb_state_score/data/extracted/ntps_units.csv` with its provenance), `verification/check_extraction_totals.py`, `tests/test_extract_state.py`.

**Interfaces:**
- Produces: `state_panel.csv` with columns `unit, year, step, numerator, denominator, source_file, pdf_page, table_id, flag`. `numerator` is the count lost (or notified, for S1); `denominator` is the base (or target, for S1).
- Produces: `crosswalk.unit_name(raw: str, year: int) -> str`, which raises `KeyError` naming the raw string.

- [ ] Step 1: Write the tests:
  - `test_unmapped_unit_name_raises`;
  - `test_state_rows_sum_to_printed_india_row`, which tolerates a recorded gap, as for ITR 2023;
  - `test_every_value_has_page`.
- [ ] Step 2: Implement the extractors. Reuse `../tb_state_score/src/extract/` helpers (`pdftext.py`, `annex.py`, `cells.py`) by copying them with attribution in the module docstring.
- [ ] Step 3: Implement `check_extraction_totals.main() -> int`.
- [ ] Step 4: Run pytest and the check. Expected: PASS. Commit.

### Task 4: Core estimation (harm, shrinkage, priority, tiers)

**Files:**
- Create: `src/tbprio/__init__.py`, `src/tbprio/panel.py`, `src/tbprio/shrink.py`, `src/tbprio/harm.py`, `src/tbprio/priority.py`, `src/run_state.py`, `outputs/state_priority.csv`, `outputs/state_harm_draws_summary.csv`, `outputs/na_cells.csv`, `tests/test_core.py`.

**Interfaces:**
- `panel.load(path) -> list[dict]`
- `shrink.beta_binomial(x: np.ndarray, n: np.ndarray) -> tuple[float, float]`, returning (α, β).
- `shrink.gamma_poisson(y, e) -> tuple[float, float]`
- `harm.draws(rows, step, year, benchmark: str, shrinkage: bool, rng) -> dict[str, np.ndarray]`, mapping each unit to a vector of harm-averted draws of length 10,000.
- `priority.p_topk(draws: dict, k: int) -> dict[str, float]`
- `priority.tier(p: float, rising: bool) -> str`
- `priority.flags(...) -> dict`, covering "small but far behind".
- `outputs/state_priority.csv` columns: `unit, step, year, harm_averted_mean, lo, hi, per_100k, p_top5, tier, rising, small_far_behind, rate, rate_bench`.

- [ ] Step 1: Write the tests:
  - `test_harm_averted_floor_zero_and_zero_counts`;
  - `test_missing_step_excludes_unit_only_from_that_step`;
  - `test_small_unit_cannot_dominate_tiers`;
  - `test_p_topk_sums_to_k_over_units` (the sum of P(top-k) over units equals k, within 1e-9, when all units have draws);
  - `test_tier_thresholds` (0.80 gives "act now"; 0.7999 gives "probable priority"; 0.19 with rising=True gives "watch: rising").
- [ ] Step 2: Implement, with no hard-coded unit names.
- [ ] Step 3: Implement `src/run_state.py`. It writes the outputs deterministically: same seed, byte-identical reruns.
- [ ] Step 4: Run pytest. Commit.

### Task 5: Trajectory, stability, external association, robustness

**Files:**
- Create: `src/tbprio/trend.py`, `src/tbprio/validate.py`, `src/run_validate.py`, `outputs/state_trend.csv`, `outputs/headline.csv`, `outputs/spec_curve.csv`, `outputs/leave_one_out.csv`, `tests/test_validate.py`.

**Interfaces:**
- `trend.slope(years, x, n) -> tuple[float, float, float]`, returning (slope, lo, hi).
- `validate.h1_stability(...) -> dict`
- `validate.h2_external(...) -> dict`
- `validate.label(main_interval, null, grid_signs) -> str`
- `outputs/headline.csv` columns: `estimate, value, lo, hi, null, n, n_grid, n_agree, label`.
- Task 4 reads `rising` from `state_trend.csv`. Task 5 regenerates `state_priority.csv` after trends exist: `run_state.py` calls trend first.

- [ ] Step 1: Write the tests:
  - `test_label_rule` (an interval excluding the null with 10 of 12 agreeing gives "supported"; 9 of 12 gives "not established");
  - `test_trend_requires_three_years`;
  - `test_fieller_matches_tb_state_score` (on a fixture copied from that repo).
- [ ] Step 2: Implement.
- [ ] Step 3: Implement the run script.
- [ ] Step 4: Run pytest and the full run. Commit.

### Task 6: District module and CLI tool with HTML report

**Files:**
- Create: `src/extract/au802.py`, `data/extracted/district_notifications.csv`, `src/tbprio/district.py`, `src/tbprio/schema.py`, `src/tbprio/report.py`, `src/tbprio/__main__.py`, `examples/district_example.csv` (synthetic, clearly labelled), `outputs/district_mp_mh.csv`, `outputs/report_state.html`, `outputs/report_district.html`, `tests/test_district.py`, `tests/test_cli.py`.

**Interfaces:**
- CLI: `python -I -m tbprio state --panel data/extracted/state_panel.csv --out outputs/`
- CLI: `python -I -m tbprio district --input <csv> --state <name> --out <dir>`
- `schema.validate_district(rows) -> list[dict]`. The required columns are `district, year, notified`. The optional ones are `target, population` and any `cascade_*`.
- The report is self-contained HTML: inline SVG, no external scripts. It contains a priority-matrix heat-map, funnel plots, per-unit summaries, a plain-language legend and the caveats.

- [ ] Step 1: Write the tests:
  - `test_district_schema_variants`;
  - `test_au802_units_per_state` (MP 55, MH 80; verify the counts in Task 1's inventory and use those exact numbers);
  - `test_district_flags_on_synthetic_overdispersed_data`;
  - `test_cli_writes_report`.
- [ ] Step 2: Implement.
- [ ] Step 3: Run the CLI on both demonstration States. Open the HTML and check it renders. Commit.

### Task 7: Verification suite

**Files:**
- Create: `verification/check_outputs.py` (independent standard-library recompute of: P(top-5) for each tier boundary unit, using its own simple simulation with the same seed for the 2023 S3 step; H1 and H2 point estimates; labels from `spec_curve.csv`), `verification/check_deviations.py`, `verification/check_all.py`, `verification/MUTATIONS.md`, `tests/test_verification.py`.

**Interfaces:**
- `check_all.py` runs pytest, then:
  - `check_plan_order`;
  - `check_deviations`;
  - `check_extraction_totals`;
  - `check_outputs`;
  - a byte-for-byte rerun of `outputs/`;
  - `check_manuscript_numbers` and `check_docx_tie`, both SKIP when `manuscript/` is absent.

  It prints PASS/FAIL/SKIP per step.

- [ ] Step 1: Write the mutation tests: change a headline value in `outputs/headline.csv`; edit the plan above §12; flip a label. Each must make `check_all` FAIL.
- [ ] Step 2: Implement.
- [ ] Step 3: Run `python -I verification/check_all.py`. Expected: all PASS, manuscript steps SKIP.
- [ ] Step 4: Update README (questions, headline table with labels, reproduction commands, tool usage) and ENVIRONMENT.md.
- [ ] Step 5: Commit. The controller pushes.

### Task 8: Manuscript (local), exhibits and submission build

**Files:**
- Create: `exhibits/make_tables.py`, `exhibits/make_figures.py`, and `tools/build_submission.py` plus `tools/render_check.ps1` and `tools/word_count_word.ps1` (adapted from `../tb_acf_campaign/tools/`). Also `verification/check_manuscript_numbers.py`, `verification/check_docx_tie.py` and `verification/mutate_manuscript.py`, adapted from the same repo.
- Create locally: `manuscript/` (manuscript_src.md, title page, cover letter, checklist, journal_rules.md, exhibits, submission/).

**Interfaces:**
- The journal and its rules come from `manuscript/journal_rules.md`, which the controller writes from the journal's own guidelines before dispatch.
- The checks follow the ACF repo's `--manuscript-dir` pattern.
- `build_submission.py` refuses to write into a folder holding a `SUBMITTED_*` file, and rejects unknown options.

- [ ] Step 1: Exhibits:
  - Figure 1: the priority matrix (unit × step) heat-map of P(top-5), with tier markers.
  - Figure 2: harm averted with intervals for the top units per step, with the per-population view as a second panel.
  - Figure 3: trajectories with rising flags.
  - Figure 4: the district funnel for MP and MH.
  - Table I or 1 (per the journal): headline estimates with labels.

  Everything else goes in the supplement. Every cell is traced to `outputs/`.
- [ ] Step 2: Prose, framed as programme guidance. Methods disclose the registration, what had been seen and all deviations. Results report labels as fixed. Discussion: where to invest, by step; who acts (CTD, State TB Cells); limits (target ≠ disease; notifications only at district level; ecological). Include the AI disclosure sentence used in the companion papers. References are Crossref-verified, in first-citation order, with the dataset reference to the Zenodo/GitHub release.
- [ ] Step 3: Cover letter. Related manuscripts are JPH-26-1883 (State TB Score) and the Public Health ACF paper (number pending), each with a one-line note on how it differs, plus the other TB manuscripts as in the JPH letter.
- [ ] Step 4: Build. Run render QA on every page, then Word counts, the number check, the docx tie and the mutation harness. Expected: all PASS within the journal limits.
- [ ] Step 5: Commit only tooling and tests.

### Task 9: Final review, release, hand-over (controller)
- [ ] Whole-branch review on the most capable model. One fix wave. A scoped re-review.
- [ ] Push. Set the CITATION.cff version 1.0.0 and date. Tag v1.0.0 and create the GitHub release. Zenodo mints a DOI only if the author has switched the repo on in Zenodo; if not, record that the author must switch it on and re-release.
- [ ] Rebuild the title page with the DOI, if minted. Rerun check_all.
- [ ] Update memory. Give the author the "Rulings I made" list.
