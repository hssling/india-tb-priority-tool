# Outputs

Every file here is written by the analysis from the committed extraction in
`data/extracted/` and is reproduced byte for byte by a rerun
(`python -I verification/check_rerun.py`; commands in the main README). Section
numbers (§) refer to the registered analysis plan, `docs/analysis_plan.md`.
Numbers are written in full precision (Python `repr`); an empty cell means not
applicable or not estimable. Booleans are `True`/`False`. Licence: CC BY 4.0.

Conventions:

- **Unit**: a State or UT after coarsening (§4; 33 units). **Step**: S1 shortfall
  against target, S2 not tested for rifampicin resistance, S3 died (DS-TB
  cohort), S4 lost to follow-up (DS-TB cohort), S5 DR-TB treatment not
  successful, S6 HIV status not known (§5). **Year**: the data year (§3.2).
- **Rate**: the loss rate x/n for S2-S6; for S1 the achievement, notified ÷
  target (higher is better). `rate` columns are posterior means (§6.1) unless
  named `rate_observed`.
- **Specification**: `benchmark` p75 (main; the better quartile of units), median
  or p90 (best decile), and `shrinkage` on (empirical Bayes, main) or off
  (Jeffreys prior) (§6.1-§6.2, §8.5).
- **Harm averted** (patients): the mean of 10,000 posterior draws of
  max(0, n (r - r_bench)), or max(0, target (a_bench - a)) for S1; `lo` and
  `hi` are the 2.5th and 97.5th percentiles of the draws (§6.3).
- **Tiers** (§6.4-§6.5): "act now" P(top-k) ≥ 0.80; "probable priority" 0.50 to
  < 0.80; "uncertain" 0.20 to < 0.50; "lower priority" < 0.20; "watch: rising"
  replaces the last two when the rising flag is set.

## state_priority.csv

Data year 2023, main specification (benchmark p75, shrinkage on, k = 5): one row
per unit and step with a non-NA cell (198 rows).

| Column | Meaning |
|---|---|
| `unit`, `step`, `year` | unit, step, data year (2023) |
| `harm_averted_mean`, `lo`, `hi` | harm averted and its 95% interval (patients) |
| `per_100k` | harm_averted_mean per 100,000 population (ITR 2024 Annexure 1.1 population; §6.7); shown alongside, never used for tiers |
| `p_top5` | P(top-5) within the step (§6.4) |
| `tier` | the tier from p_top5 and `rising` |
| `rising` | rising-risk flag: the main trend slope's 95% interval lies wholly on the worsening side (§6.5) |
| `small_far_behind` | rate gap in the worst quartile and harm averted below the median (§6.6); never changes the tier |
| `rate`, `rate_bench` | the unit's posterior-mean rate and the benchmark rate |
| `trend_status` | added beyond §10.2: the status of the main trend model that gives `rising` ("estimated"; "not estimable (definition change)" for S2; "no trend" for S5) |
| `flag` | added beyond §10.2: the cell's flags from the extraction, which name the cohort (for example `cohort_2022`), merged members (`merged:...`), missing members and table notes |

## state_priority_sensitivity.csv

Data year 2023, shrinkage on: P(top-k) and tiers under k = 3 and k = 8
(benchmark p75), and under the median and best-decile (p90) benchmarks (k = 5)
(§6.4). Columns: `unit, step, year`; `analysis` (`k3`, `k8`,
`benchmark_median`, `benchmark_p90`); `benchmark`; `shrinkage` (on); `k`;
`harm_averted_mean` under that benchmark; `p_topk`; `tier` under this
sensitivity; `tier_main` (the tier in state_priority.csv); `tier_changed`;
`rising` (the main-model flag, the same in every analysis).

## state_harm_draws_summary.csv

The summary of every draw set: each unit, step, data year and specification
(3 benchmarks × shrinkage on/off). One new `numpy.random.default_rng(20261121)`
per draw set (§10.1).

| Column | Meaning |
|---|---|
| `basis` | `main`, or `s6_2022_registered` for S6 2022 on the registered Annexure 1.2 denominator (sensitivity kept under the plan §12.2 deviation) |
| `step`, `year`, `benchmark`, `shrinkage`, `unit` | the draw set and unit |
| `n_units` | units with a non-NA cell in the step-year |
| `numerator`, `denominator` | count lost (S2-S6) or notified (S1); denominator, or target for S1 |
| `rate_observed` | numerator ÷ denominator |
| `rate`, `rate_bench` | posterior-mean rate and benchmark |
| `gap` | rate gap on posterior means: rate - rate_bench (S2-S6), rate_bench - rate (S1) |
| `prior_alpha`, `prior_beta` | the prior: method of moments (shrinkage on) or Jeffreys (off) (§6.1) |
| `harm_averted_mean`, `lo`, `hi` | harm averted (patients) |
| `p_top3`, `p_top5`, `p_top8` | P(top-k) for k = 3, 5, 8 |
| `small_far_behind` | §6.6 flag |
| `no_harm` | True when no patient is lost in any unit of the step-year (§6.1) |
| `flag` | the cell's extraction flags |

## state_trend.csv

The trend of every unit and step (§7), on the main basis and, for S6, also on
the registered S6 2022 basis (`basis` = `s6_2022_registered`). Tiers use the
main model on the main basis only.

| Column | Meaning |
|---|---|
| `basis`, `unit`, `step` | as above |
| `trend_status` | "estimated", "not estimable (fewer than 3 years)", "not estimable (definition change)" (S2) or "no trend" (S5) |
| `years`, `n_years` | the non-NA data years used |
| `indicator` | whether the 2021 year indicator was fitted (§7.2) |
| `slope`, `se`, `lo`, `hi` | slope per year of logit(loss rate) (S3, S4, S6) or log achievement (S1), weighted least squares; SE scaled by φ_s; 95% interval |
| `chi2`, `df` | the unit's Pearson χ² and residual degrees of freedom |
| `phi` | φ_s = max(1, Σχ² ÷ Σdf) pooled over the step's units |
| `rising` | the 95% interval lies wholly on the worsening side (lo > 0; hi < 0 for S1) |
| `sens_model`, `sens_status`, `sens_slope`, `sens_lo`, `sens_hi`, `sens_rising` | the sensitivity model (§7.3): without the 2021 indicator (S3, S4, S6) or with it (S1) |
| `rising_differs` | the sensitivity flag differs from the main flag |

## na_cells.csv

Every NA or flagged cell of `data/extracted/state_panel.csv` and of
`state_panel_s6_2022_registered.csv` (§3.3). Columns: `panel` (which file),
`unit, year, step, numerator, denominator`; `na` (True when the cell is not
used); `reason` (the NA reason first, for example `NA:loss_negative`, then the
cell's flags; `denominator_A1.6_sex_sum_plan_12.2` marks the main S6 2022
denominator of plan §12.2); `source_file, pdf_page, table_id`.

## headline.csv

| Column | Meaning |
|---|---|
| `estimate` | H1, H2, H3, then the descriptive rows below |
| `value`, `lo`, `hi` | the estimate and its 95% interval (H1: bootstrap over units, 10,000 draws; H2: Fisher-z with Fieller's variance 1.06/(n - 3)) |
| `null` | 0 for H1 and H2; empty for descriptive rows |
| `n` | H1: unit-step pairs; H2: NTPS reporting units; H3: steps; descriptive rows: as stated in `note` |
| `n_grid`, `n_agree` | grid entries, and those agreeing in strict sign with the main estimate (§8.6) |
| `label` | "supported" or "not established" (§8.6); empty for H3 and descriptive rows |
| `note` | added beyond §10.2: how the row was computed, units excluded or not covered, and for H3 shares the top-five units |

Rows: `H1`, `H2`, `H3` (§8.2-§8.4); then the descriptive rows, which carry no
null and no label: `H1 top-5 overlap S3`, `S4`, `S6` and their sum (out of 15,
ties at the fifth place broken alphabetically); `H1 rate-gap rho (descriptive)`
(§10.4); `H2 signed shortfall per 100,000 (descriptive)` (target - notified,
with its Fieller interval; §8.3); `H3 share S2` to `S5` (the share for each
step, with its top five in `note`).

## spec_curve.csv

Every entry of the H1 and H2 specification grids (§8.5), 12 each, the main entry
included. Columns: `estimate`; `benchmark`; `shrinkage`; `year_window` (H1: the
pre-period, `2018;2019;2021` or `2019;2021`; S4 is 2019, 2021 in both);
`denominator` (H2: per population or per target); `value` (ρ); `n` (the entry's
own count: unit-step pairs for H1, NTPS units for H2); `main`; `agrees` (strict
sign agreement with the main estimate).

## leave_one_out.csv

§8.7, descriptive. Columns: `analysis` (`H1`, `H2` or `tiers`); `omitted` (the
unit, or NTPS reporting unit for H2, left out); `step` (for `tiers`: the step,
or `all`); `value` (ρ without that unit, H1 and H2); `n_tier_changes` and
`changes` (for `tiers`: the 2023 tier changes among the remaining units after
refitting the prior, benchmark and P(top-5), as "unit: old -> new"); `extreme`
(`min`/`max` ρ, or `most_changes`).

## district_national_2018.csv

National district module, data year 2018 (historical), ITR 2019 Annexure 1.13
(§9.1). One row per district and step: D1 not initiated on treatment, D2
public-sector treatment not successful (2017 cohort).

| Column | Meaning |
|---|---|
| `data_label` | "2018 data (historical)" |
| `state`, `district`, `step`, `step_name`, `year` | as printed; districts are not coarsened or linked to later names |
| `numerator`, `denominator` | patients lost and the base (D2: cohort rebuilt from the printed count and percentage) |
| `rate_observed`, `rate`, `rate_bench`, `gap` | as for the States, across all districts in the country |
| `harm_averted_mean`, `lo`, `hi`, `p_top20`, `tier`, `small_far_behind` | as for the States, with k = 20 |
| `state_rate` | the State's pooled proportion |
| `z`, `phi`, `limit_998`, `funnel_flag`, `position_95` | State-relative funnel: z, the multiplicative φ (from all districts), the 99.8% limit widened by √φ, the flag ("above State limits", "below State limits", "within State limits", or "no funnel" for a State with one district) and the position against the 95% limit |
| `tau2`, `z_additive`, `additive_position_998`, `additive_position_95` | the additive DerSimonian-Laird adjustment, reported alongside |
| `cohort_lo`, `cohort_hi` | D2: the cohort range implied by the rounding of the printed percentage |
| `na`, `flag` | NA status and flags (for example `rounded_from_percent`) |
| `source_file`, `pdf_page`, `table_id` | provenance |

## district_mp_mh.csv

Madhya Pradesh and Maharashtra, notifications 2022-2024, Lok Sabha Unstarred
Question 802 (§9.2). One row per district; no tiers. A fall in notifications can
mean less TB or less case-finding.

| Column | Meaning |
|---|---|
| `state`, `district` | as printed (the duplicate Vidisha entry kept once) |
| `n_2022`, `n_2023`, `n_2024` | notifications; 2023 is shown, not tested |
| `base_year`, `final_year` | 2022 and 2024 |
| `change`, `rel_change`, `se_rel` | n_2024 - n_2022; change ÷ n_2022; its Poisson SE on that scale |
| `state_ratio`, `state_change` | R = the State's 2024 total ÷ 2022 total, and R - 1 |
| `z`, `phi`, `limit_998`, `flag`, `position_95` | the funnel around the State's pooled change: z, the multiplicative φ (10%-winsorised), the widened 99.8% limit, the flag ("fell beyond adjusted limits", "rose beyond adjusted limits", "within adjusted limits") and the position against the 95% limit |
| `tau2`, `z_additive`, `additive_position_998`, `additive_position_95` | the additive DerSimonian-Laird adjustment, reported alongside |
| `na` | `NA:base_zero` when n_2022 = 0 |
| `entry_flag` | for example `duplicate_entry` |
| `source_file`, `table_id` | provenance |

## report_state.html and report_district.html

Self-contained HTML reports (§10.2; no scripts, no external links), written by
the tool's `state` and `district` commands. `report_state.html`: a plain-language
legend, the priority matrix (a heat-map of tiers by unit and step), the largest
harm averted at each step, a summary for each State/UT and the caveats.
`report_district.html`: the legend, the funnel plot of the change in
notifications for each State, the national 2018 module (its priority matrix and
State-relative funnels) and the caveats. They carry no date, so reruns are
byte-identical.
