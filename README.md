# Where to invest against TB in India: a State and district priority tool

**Archived release:** v1.0.1, doi:[10.5281/zenodo.24411057](https://doi.org/10.5281/zenodo.24411057) (concept DOI, always the latest version: [10.5281/zenodo.24411056](https://doi.org/10.5281/zenodo.24411056)).

Code, extracted data, outputs and a pre-registered analysis plan for a tool that
helps those who run India's National TB Elimination Programme (NTEP) decide
where closing a gap in the TB care pathway would avert the most harm, at which
step of the pathway, and how sure one can be. It also flags where a unit's own
loss rate is rising. It uses only published, aggregate, official data.

It is not a league table. The official State TB Score asks how each State did
on nine process indicators. This tool asks where closing a gap would prevent
the most harm, and gives tiers, not ranks. Results describe programme data,
not the performance or effort of any State's staff. All associations reported
here are observational; none is a causal estimate.

## The questions

The analysis plan, [`docs/analysis_plan.md`](docs/analysis_plan.md), asks four
questions (its §2):

- **Q1. Priorities (data year 2023).** For each step of the care pathway, in
  which States/UTs would closing the gap to a benchmark avert the most harm,
  counted as patients lost at that step? How certain is each unit's place
  among the top five? The answer is harm averted with a 95% interval, the
  probability of being in the top five, P(top-5), and a tier.
- **Q2. Trajectory.** For each unit and step with enough years, is the gap
  widening (the registered question)? The registered flag tracks the trend in
  each unit's own loss rate, not its distance from the benchmark, so "rising
  risk" means a rising rate, which may partly reflect better recording.
- **Q3. Reliability.** Are the priorities stable over time (H1)? Are they
  associated with an independent measure of TB burden, the ICMR National TB
  Prevalence Survey (H2)? How concentrated is the harm that could be averted
  (H3)? How far do the priorities move under reasonable alternative choices?
- **Q4. District use.** Do the same functions run on district tables? This is
  shown on the national district table of the India TB Report 2019 (data year
  2018, historical) and on district notifications for Madhya Pradesh and
  Maharashtra, 2022-2024 (Lok Sabha Unstarred Question 802).

The six care-pathway steps are S1 shortfall against target (target minus
notified), S2 not tested for rifampicin resistance, S3 died (DS-TB cohort), S4
lost to follow-up (DS-TB cohort), S5 DR-TB treatment not successful and S6 HIV
status not known. Steps are never combined into one score: a death and an
unknown HIV status have no common weight.

## Registration

The plan was committed and pushed to this public repository before any
estimate was computed: commit bd3572e, pushed on 20 November 2026 at 20:38:56
UTC ([`docs/registration_event.json`](docs/registration_event.json), time from
the GitHub API). The plan is dated 21 November 2026 (India time). The text above
its §12 is frozen: `verification/check_plan_order.py` checks that it is
byte-identical at every later commit and in the working tree, and that no output
or estimation module was committed before the registration commit.

### Deviations from the registered plan (plan §12)

Each is a dated entry in §12 of the plan:

- **§12.1 (21 November 2026), a factual correction with no change to any rule
  or result.** The plan said Lakshadweep is absent from ITR 2019 Annexure
  1.4.a. It is printed there (as "Lakshwadeep") with a blank Died cell, so,
  under the registered rule, Kerala S3 2018 is formed from Kerala's row alone
  and flagged `member_missing:Lakshadweep`, as the plan expected.
- **§12.2 (21 November 2026), deviation: the S6 denominator for data year 2022.**
  The HIV-status table of ITR 2023 (Annexure 2.1) prints percentages on the
  base of Annexure 1.6 (notified by sex), not Annexure 1.2. The main S6 2022
  denominator is therefore the Annexure 1.6 sum, the basis of the numerator's
  own table. It was decided from the extraction review, before any estimate.
  The registered Annexure 1.2 basis is kept and reported as a sensitivity
  (flag `registered_basis_sensitivity_plan_12.2`, basis `s6_2022_registered`).

## Headline results

Labels follow plan §8.6: "supported" only if the main 95% interval excludes the
null **and** at least 80% of the 12 specification-grid entries agree in sign
with the main estimate; otherwise "not established". H3 and every sensitivity
are descriptive and carry no label.

| Estimate | Value (95% interval) | n | Grid entries agreeing | Label |
|---|---|---|---|---|
| **H1** temporal stability: Spearman-type correlation of each unit-step's pre-period (2018, 2019, 2021; S4: 2019, 2021) and 2023 harm averted, within-step ranks pooled over S3, S4, S6 | 0.563 (0.323 to 0.743; bootstrap over units) | 99 unit-step pairs, 33 units | 12 of 12 | **Supported** |
| **H2** external association: Spearman ρ between the 2023 S1 harm averted per 100,000 and NTPS prevalence | 0.330 (-0.146 to 0.682; Fisher-z with Fieller's variance) | 20 NTPS reporting units | 12 of 12 | **Not established** |
| H3 concentration: share of the 2023 harm averted (S2-S5 summed) in each step's top-five units | 0.587 | 4 steps | (descriptive) | none |

- The plan expected H1 to reflect unit size (plan §10.4); the size-free
  rate-gap correlation was similar (0.550, descriptive), so the stability is
  not explained by size alone. Across the H1 specification grid, H1 ranges
  from 0.484 to 0.863 (`outputs/spec_curve.csv`). The top-five sets of the
  pre-period and 2023 share 11 of 15 places (S3 4, S4 4, S6 3).
- H2 is a test of association, not of validity: the survey describes
  2019-2021, and a CTD target is a programme goal, not an estimate of disease.
  It may be circular if targets were set from burden estimates that include
  the survey. The interval includes 0, so H2 is not established. The
  association is positive per population (0.138 to 0.411) but close to 0 per
  target (0.057 to 0.095); shrinkage does not change S1, so the 12-entry grid
  holds six distinct estimates.
- Leave-one-out: H1 stays between 0.533 (without Delhi) and 0.653 (without
  Uttar Pradesh); H2 between 0.234 and 0.484.

## What the tool shows (data year 2023)

For each step, units are placed in tiers by P(top-5) under the main
specification (benchmark: the better quartile of units; empirical-Bayes
shrinkage on): "act now" P ≥ 0.80; "probable priority" 0.50 to < 0.80;
"uncertain" 0.20 to < 0.50; "lower priority" < 0.20. A unit in one of the two
lower tiers whose trend shows a rising risk (the 95% interval of its slope lies
wholly on the worsening side) is shown as "watch: rising". Units are listed
alphabetically within a tier.

| Step | Act now | Probable priority | Uncertain | Watch: rising |
|---|---|---|---|---|
| S1 shortfall against target | Bihar, Madhya Pradesh, Tamil Nadu, West Bengal | Karnataka | Chhattisgarh | none |
| S2 not tested for rifampicin resistance | Bihar, Madhya Pradesh, Maharashtra, Rajasthan, Uttar Pradesh | none | none | none |
| S3 died (2022 cohort) | Gujarat, Karnataka, Maharashtra, Tamil Nadu, West Bengal | none | none | Bihar, Chhattisgarh, Delhi, Kerala, Madhya Pradesh |
| S4 lost to follow-up (2022 cohort) | Bihar, Delhi, Madhya Pradesh, Rajasthan, Tamil Nadu | none | none | none |
| S5 DR-TB not successful (2021 cohort) | Bihar, Delhi, Madhya Pradesh, Uttar Pradesh | Tamil Nadu | Jharkhand | none |
| S6 HIV status not known | Bihar, Delhi, Madhya Pradesh, Rajasthan, Telangana | none | none | none |

All other units are "lower priority" for that step. The full table, with harm
averted, its interval, the population view (per 100,000), the rising flag and
the small-but-far-behind flag, is `outputs/state_priority.csv`; the report
`outputs/report_state.html` shows it as a priority matrix with per-unit
summaries, a plain-language legend and the caveats. Rising risk was found only
for S3 (9 units; 4 of them are already "act now"). Sensitivities (k = 3 and 8,
median and best-decile benchmarks, leave-one-out) are in
`outputs/state_priority_sensitivity.csv` and `outputs/leave_one_out.csv`;
P(top-5) with shrinkage off is in `outputs/state_harm_draws_summary.csv`
(`shrinkage` = off).

District modules (demonstrations of method, no current national district
results):

- **National, data year 2018 (historical)**, ITR 2019 Annexure 1.13, about 760
  districts: D1 not initiated on treatment and D2 public-sector treatment not
  successful, with tiers on P(top-20) and a funnel around each State's pooled
  proportion (`outputs/district_national_2018.csv`).
- **Madhya Pradesh and Maharashtra, notifications 2022 to 2024**: the change
  per district and a funnel around the State's pooled change, with
  overdispersion adjustments; no tiers. Four Madhya Pradesh and two
  Maharashtra districts lie beyond the adjusted limits. A fall in notifications
  can mean less TB or less case-finding; notifications alone cannot tell the
  two apart (`outputs/district_mp_mh.csv`, `outputs/report_district.html`).

Every output file and column is described in
[`outputs/README.md`](outputs/README.md).

## Running the tool

Install once from the repository root (Python 3.14; see
[`ENVIRONMENT.md`](ENVIRONMENT.md)):

```
python -I -m pip install -e .
```

(Offline, with numpy already installed: `python -I -m pip install --no-deps
--no-build-isolation -e .`.) Then:

```
python -I -m tbprio state --panel data/extracted/state_panel.csv --out my_results/
python -I -m tbprio district --input examples/district_example.csv --state "Synthetic State" --out my_results/
```

- `state` takes a long-format State panel (columns `unit, year, step,
  numerator, denominator, source_file, pdf_page, table_id, flag`) and writes the
  State output files and `report_state.html`. The registered-basis S6 2022
  panel and the population file are read from beside the panel when present
  (or from `--registered` and `--population`).
- `district` takes a district CSV with the required columns `district, year,
  notified` and the optional columns `state, target, population` and any
  `cascade_*`. A "Total" row is dropped with a warning, and a missing required
  column stops the run with a clear message. For each `--state` it writes the
  change between the first and last year (or `--base-year`, `--final-year`)
  with its funnel, `district_<tag>.csv`, and `report_district.html`. With
  `--national-2018 data/extracted/district_2018.csv` it also runs the
  national 2018 module. `examples/district_example.csv` is synthetic and is
  labelled as such.

The reports are single self-contained HTML files (no scripts, no external
links) that open in any browser.

## Reproducing the results

From the repository root:

```
python -I src/run_state.py
python -I src/run_validate.py
python -I -m tbprio state --panel data/extracted/state_panel.csv --out outputs/
python -I -m tbprio district --input data/extracted/district_notifications.csv --state "Madhya Pradesh" --state Maharashtra --tag mp_mh --national-2018 data/extracted/district_2018.csv --out outputs/
python -I verification/check_all.py
```

The first four commands rebuild `outputs/` from the committed extraction in
`data/extracted/` (seed 20261121, 10,000 draws per draw set; reruns are byte
for byte identical). `check_all.py` runs the tests and every check of plan
§10.3 and prints PASS, FAIL or SKIP for each:

- the registration order and the frozen plan text (`check_plan_order.py`);
- that every label of a departure from the plan in the outputs, this README and
  the data flags has a dated entry in plan §12 (`check_deviations.py`);
- the extracted tables against their printed totals
  (`check_extraction_totals.py`);
- an independent recompute with the Python standard library only
  (`check_outputs.py`): the 2023 S3 prior, posterior means, benchmark and
  P(top-5) from its own draws; H1, H2 and their grids; the labels; the trend
  and rising flags; and the headline values against their source rows;
- a byte-for-byte rerun of `outputs/` (`check_rerun.py`).

The checks were shown to fail on deliberate breaks
([`verification/MUTATIONS.md`](verification/MUTATIONS.md)).

To re-extract the tables from the source documents, fetch them first (below),
then run `python -I src/extract/itr_state.py`, `python -I
src/extract/itr2019_districts.py` and `python -I src/extract/au802.py`;
`check_extraction_totals.py` then also re-extracts them and compares byte for
byte.

## Data sources (not redistributed)

- India TB Reports 2019, 2020, 2023 and 2024 and the TB Annual Report 2022
  (Central TB Division, Ministry of Health and Family Welfare), State
  annexures for data years 2018, 2019, 2021, 2022 and 2023, and the national
  district table of ITR 2019 (Annexure 1.13). Data year 2020 is not used (ITR
  2021 has no text layer).
- The ICMR National TB Prevalence Survey in India 2019-2021, through the
  State and State-group prevalence values in `data/extracted/ntps_units.csv`.
- Lok Sabha Unstarred Question No. 802, answered 7 February 2025 (district
  notifications for Madhya Pradesh and Maharashtra, 2022-2024; data source
  Ni-kshay).

The documents are not redistributed. `data/source_manifest.csv` lists each file
with its origin, size and SHA-256 digest; `python -I tools/fetch_sources.py`
copies them into `data_raw/` from the author's sibling repositories
(`tb_state_score`, `tb_acf_campaign`) and verifies the digests; the Lok Sabha
answer is supplied by the author in `data_raw/pq/`. The values
extracted from them are in `data/extracted/`, each with its source file, PDF
page and table.

## Limitations

- **P(top-k) mostly reflects sampling noise.** With denominators of about 10^5
  patients, most P(top-5) values are close to 0 or 1 (9 of 198 State rows lie
  between 0.02 and 0.98). The tiers express little uncertainty beyond
  sampling; they do not include error in the reported figures.
- **H1 was expected to reflect unit size**; the size-free rate-gap correlation
  (0.550) is similar, so the stability is not explained by size alone.
- **H2 may be circular**, and it compares 2023 programme data with a
  2019-2021 survey over 20 reporting units, some of them State groups.
- **Cohorts lag.** S3 and S4 for data year 2023 are the 2022 treatment
  cohort, and S5 the 2021 DR-TB cohort. Definitions change between editions
  and are flagged, not harmonised; S2 and S5 have no trend.
- **Trends are short** (three to five data years) and strongly overdispersed
  (pooled φ from 42 for S3 to about 1,180 for S6), so few slopes are
  distinguishable from 0.
- **Small UTs are merged** into a neighbouring unit (Dadra and Nagar Haveli
  and Daman and Diu into Gujarat, Lakshadweep into Kerala, Ladakh into Jammu
  and Kashmir) and are not prioritised on their own.
- **The national district module is 2018 data** and is historical; districts
  have since been renamed or split. The Madhya Pradesh and Maharashtra module
  uses notifications only.
- **Shortfall against target** (S1) counts the gap to a programme target, not
  people with TB who were not found. No cost data are used, so "where effort
  buys most" means harm that closing a gap could avert, not cost per outcome.
- No value is imputed; NA cells are listed in `outputs/na_cells.csv` with the
  reason.

## Licences and citation

Code: MIT ([`LICENSE`](LICENSE)). Extracted data and outputs: CC BY 4.0
([`LICENSE-DATA`](LICENSE-DATA)). Please cite the repository as in
[`CITATION.cff`](CITATION.cff).

Author: Siddalingaiah H S (ORCID 0000-0002-4771-8285), Department of Community
Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumkur,
Karnataka, India.

Design: `docs/superpowers/specs/2026-11-21-tb-priority-tool-design.md`.
Implementation plan: `docs/superpowers/plans/2026-11-21-tb-priority-tool.md`.
What the sources print (structure only): `docs/data_inventory.md`.
