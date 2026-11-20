# Pre-registered analysis plan: where to invest against TB in India, a State and district priority tool

**Date of this plan:** 21 November 2026
**Author:** Siddalingaiah H S, MD, Professor, Department of Community Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumkur 572106, Karnataka, India. ORCID 0000-0002-4771-8285. Single author.
**Repository:** https://github.com/hssling/india-tb-priority-tool
**Status:** registered before any estimate was computed. The registration point (the commit SHA and the UTC time of the public push, taken from the GitHub API) is recorded in `docs/registration_event.json`. `verification/check_plan_order.py` checks that the text above §12 is byte-identical at every later commit, and that no output and no estimation module was committed before the registration commit.
**Design:** `docs/superpowers/specs/2026-11-21-tb-priority-tool-design.md` (approved 21 November 2026). **Implementation plan:** `docs/superpowers/plans/2026-11-21-tb-priority-tool.md`, sections "Fixed analysis values" and "Controller rulings after Task 1". **Data inventory (structure only):** `docs/data_inventory.md`. Where any of these and this plan differ, this plan governs.

**Conventions in this plan.**
- A paragraph marked **Fixed (verbatim)** copies the implementation plan's "Fixed analysis values" or "Global Constraints" word for word.
- A paragraph marked **Ruling (verbatim)** copies the implementation plan's "Controller rulings after Task 1" (21 November 2026) word for word. Where a ruling and a fixed value differ, the ruling governs.
- A paragraph marked **Operational detail** fixes how a value is applied. These details were settled when this plan was written, before any estimate.
- "Edition" is the report; "data year" is the year its State tables describe (§3.2). "Unit" is a State or UT after coarsening (§4).

---

## 1. Background and scope

### 1.1 Purpose

The tool is meant for those who run India's National TB Elimination Programme (NTEP): the Central TB Division (CTD) and the State TB Cells. It asks: where would closing a gap in the TB care pathway avert the most harm, at which step of the pathway, and how sure can we be? It also asks where the gap is widening.

It is not a league table. The official State TB Score asks how each State did on nine process indicators. This tool asks where closing a gap would prevent the most harm, and where the risk is rising. It does not reconstruct or re-rank the State TB Score, which the author's related study (JPH-26-1883) audits.

### 1.2 Scope

- Published, aggregate, official data only (§3).
- The main unit is the State or UT after coarsening (§4). The main priority year is data year 2023.
- Harm is counted in natural units: patients lost at a step of the care pathway (§5). Steps are not combined into one score.
- Two district modules are demonstrations of method (§9): a national district module for data year 2018, and a notification funnel for Madhya Pradesh and Maharashtra, 2022–2024.
- Out of scope: causal estimates of the effect of any intervention; cost-effectiveness (no cost data are used; "where an extra unit of effort buys most" means harm that closing a gap could avert, not cost per outcome); current district results for the whole country; replacing the State TB Score.

### 1.3 Wording

**Fixed (verbatim).** Wording: "shortfall against target", never "missed cases" for the target-based measure. No causal language. Tiers, never ranks, in headline text.

**Operational detail.** Results describe programme data, not the performance or effort of any State's staff. No State is described as failing or to blame.

---

## 2. Questions

- **Q1. Priorities (data year 2023).** For each care-pathway step S1–S6 (§5), in which units would closing the gap to a benchmark avert the most harm, counted as patients lost at that step? How certain is each unit's place among the top k? The answer is given as harm averted with a 95% interval, the probability of being in the top k, and a tier (§6).
- **Q2. Trajectory.** For each unit and step with enough years (§7), is the gap widening? A widening gap is flagged as rising risk, and it can move a unit into "watch: rising" (§6.5).
- **Q3. Reliability.** Are the priorities stable over time (H1)? Are they associated with an independent measure of TB burden (H2)? How concentrated is the harm that could be averted (H3)? How far do the priorities move under reasonable alternative choices: the specification grids, k, the benchmark and leave-one-out (§8)?
- **Q4. District use.** Do the same functions run on district tables? This is shown on (a) the national district table of the India TB Report 2019 (data year 2018) and (b) district notifications for Madhya Pradesh and Maharashtra, 2022–2024, from Lok Sabha Unstarred Question 802 (§9).

---

## 3. Data sources and data years

### 3.1 Files

All files were copied from the author's sibling repositories or supplied by the author, and are verified by SHA-256 against `data/source_manifest.csv`. They are kept in `data_raw/`, which is not committed and not redistributed.

| File (`data_raw/…`) | Edition or document | Data year | SHA-256 | Use |
|---|---|---|---|---|
| `india_tb_report/India-TB-Report-2019.pdf` | India TB Report (ITR) 2019 | 2018 | `87e546751372ba157cb9eba1620173d54aad0fb99abc1b99f4302e9a2005c03b` | S3, S6 (State); national district module (§9.1) |
| `india_tb_report/ITR2020.pdf` | ITR 2020 | 2019 | `63b9408015dae510858e0eef2711e809d398bfe3149dd21c94390b258c007e7e` | S3, S4, S6 |
| `india_tb_report/ITR2021.pdf` | ITR 2021 (scan, no text layer) | 2020 | `692267fd532e01289a23c7b6551245ac94a1e5d6894060d2612c4337e6c410c3` | Not used (data year 2020 dropped, §3.2) |
| `india_tb_report/TBAnnaulReport2022.pdf` | TB Annual Report 2022 (TBAR 2022) | 2021 | `dc9ff4a88a28eb87232770d0956fe92b2b266b15e5794f879a7335b7c083418b` | S1, S3, S4, S6 |
| `india_tb_report/ITR2023.pdf` | ITR 2023 | 2022 | `0817ac3a1e7a03273438073d4e685f88aa93507ad115ec5c6588edfddc8f0b7b` | S1, S3, S4, S6 |
| `india_tb_report/ITR2024.pdf` | ITR 2024 | 2023 | `e37f9f406153b5e9a19726538c3f4d09dc4c470281c34fe511adaa56a0e22765` | S1–S6; population |
| `icmr_ntps/NTPS_2019_21_report.pdf` | ICMR National TB Prevalence Survey 2019–21 (NTPS) | 2019–21 | `884ffdd205d3b69569b06b3058ea77c490d44b1f2af6c3622f99282d60f04f83` | H2 (§8.3), through `data/extracted/ntps_units.csv`, copied from tb_state_score with its provenance |
| `pq/AU802_LlE1Wb.docx` | Lok Sabha Unstarred Question 802, answered 7 February 2025 | 2022–2024 | `673f79000b8c6da71fea01ad57ff0e3437e8eb9236166a2fe041e2bba3fe7405` | MP/MH district module (§9.2) |
| `pq/AU1891_qm5WaQ.docx` | Lok Sabha Unstarred Question 1891 (Karnataka), answered 2 August 2024 | — | `a109f02f6b0465e61ccf7ef63d412265418194fe630460b056998714aea972bc` | Not used: annexure heading but no table |

No other source is used. A new source is added only with the author's approval, and its addition is logged in §12.

### 3.2 Data years

**Fixed (verbatim).**
- **Data years:** 2018, 2019, 2020, 2021, 2022 and 2023, from ITR 2019, ITR 2020, ITR 2021, the TB Annual Report 2022, ITR 2023 and ITR 2024.
- **Main priority year:** 2023.
- **Main trend and stability analyses:** exclude 2020; 2021 is kept with a year indicator. Sensitivity: all years.

**Ruling (verbatim).** **Data year 2020 is dropped entirely.** ITR 2021 has no text layer. Main-analysis data years: 2018, 2019, 2021, 2022 and 2023. The "including 2020" sensitivity is replaced, for H1, by the year-window axis {pre-period 2018, 2019, 2021} vs {2019, 2021}.

**Operational detail.**
- The data years used are 2018, 2019, 2021, 2022 and 2023. No value is taken from ITR 2021.
- "Sensitivity: all years" is applied to the trend as the same model fitted without the 2021 indicator (§7.3). There is no 2020 value to add.
- Edition to data year: ITR 2019 → 2018; ITR 2020 → 2019; TBAR 2022 → 2021; ITR 2023 → 2022; ITR 2024 → 2023.
- The DS-TB and DR-TB outcome tables report earlier treatment cohorts. A cohort is labelled by the data year of the edition that prints it. For example, S3 and S4 for data year 2023 are the 2022 notification cohort in ITR 2024 Annexure 3.3. The cohort is named in each output row's flag.

### 3.3 Data rules

**Fixed (verbatim).** No imputation. NA cells are listed in `outputs/na_cells.csv`. Every extracted value carries source_file, pdf_page and table_id. Every table is checked against its printed total where one exists.

**Operational detail.**
- The check against a printed total compares the sum of the printed State/UT rows (before coarsening) with the printed India row, column by column. A difference is recorded in the extraction check with its size. It is not corrected, and the State values are used as printed.
- Definitional changes between editions are recorded as flags. They are not harmonised.
- A cell is NA for that step-year when its loss count is negative, when the count exceeds its denominator (for example, HIV status known above notified), or when its denominator is 0. It is listed in `outputs/na_cells.csv` with the reason.
- Where a cell prints both a count and a percentage, the count is used and the percentage is not, except for D2 (§9.1).

---

## 4. Units and coarsening

**Fixed (verbatim).** **State units:** the States/UTs as printed, with the coarsening used in tb_acf_campaign §9.4 (merged units summed) applied identically every year.

**Ruling (verbatim).** **Unit coarsening.** Units are coarsened to the 2018 structure in every year: DNH&DD merged into Gujarat, Lakshadweep into Kerala, Ladakh into J&K. Small UTs are not separately prioritised; this is a stated limitation.

**Operational detail.**
- In every data year, the following printed rows are added to the named unit:
  - Dadra and Nagar Haveli, and Daman and Diu (two rows in ITR 2019 and ITR 2020), or "Dadra and Nagar Haveli and Daman and Diu" (one row from TBAR 2022 onwards) → **Gujarat**;
  - Lakshadweep → **Kerala**;
  - Ladakh (a separate row from TBAR 2022 onwards) → **Jammu and Kashmir**.
- This gives 33 units in every data year: the 36 printed rows less the three rows merged.
- Merging sums counts (loss count, denominator, target, notified, population) over the member rows before any rate is formed.
- Each edition's printed unit names are mapped by an explicit crosswalk (`src/extract/crosswalk.py`). A name that is not in the crosswalk stops extraction with an error that names it.
- A member row that is absent from a table, or that prints NA, adds nothing. Examples are Lakshadweep in ITR 2019 Annexure 1.4.a and in ITR 2024 Annexure 4.13. The merged unit's value is the sum of its printed members and carries the flag `member_missing`, and the cell is listed in `outputs/na_cells.csv`. Some tables state that a member's data are included in another unit (the footnotes to ITR 2019 Annexure 1.12 and ITR 2020 Annexure 4.8); there, the flag records that footnote. A unit whose members are all NA is NA for that step-year.
- No unit outside the 33 is prioritised. Small UTs are reported only within the unit they are merged into; this is stated as a limitation.

---

## 5. Care-pathway steps and source tables

### 5.1 Steps

**Fixed (verbatim).** **Steps.** A step is used only if Task 1 finds it printed for 2023. The harm is the count of patients lost at that step.

| Step | Name | Harm counted | Rate | Notes |
|---|---|---|---|---|
| S1 | `shortfall` | target − notified (the CTD notification target) | achievement a = notified/target | Years with printed targets only |
| S2 | `not_rr_tested` | notified − tested for rifampicin resistance | | |
| S3 | `died` | deaths in the DS-TB outcome cohort | | |
| S4 | `ltfu` | lost to follow-up in the DS-TB cohort | | |
| S5 | `drtb_not_success` | DR-TB cohort − successful | | |
| S6 | `hiv_unknown` | notified − HIV status known | | Only if printed for ≥4 years |

**Ruling (verbatim).**
- **S1** uses 2021–2023 only, the years with printed targets. Its trend uses those 3 years.
- **S2** changes definition in 2022 (bacteriologically confirmed patients only). S2 is used for the 2023 priorities only; trend "not estimable (definition change)"; excluded from H1.
- **S3** for 2018 = public + private deaths.
- **S4** for 2018 is public only and is excluded. The S4 pre-period is 2019 and 2021.
- **S5** DR-TB cohorts are not comparable across editions. S5 is used for the 2023 priorities only; no trend; excluded from H1.
- **S6** has all years.

**Finding of the data inventory.** All six steps are printed for data year 2023, so no step is dropped. S6 is printed for every data year (five years once 2020 is dropped), which meets the "≥4 years" rule. State targets are printed only for data years 2020–2023, so S1 has data years 2021, 2022 and 2023.

For steps S2–S6, the loss rate of unit u is r_u = x_u / n_u, where x_u is the harm count (patients lost) and n_u the denominator. For S1, the rate is the achievement a_u = notified_u / target_u.

### 5.2 Source table for each step and data year

Column headers are quoted as printed (see `docs/data_inventory.md`). "Total" means the Total sub-column of a Public/Private/Total group. PDF pages are 1-based pages of the files in §3.1. "—" means not used.

**S1 `shortfall`** (denominator = target; count = notified; harm = target − notified):
- 2018 (ITR 2019) and 2019 (ITR 2020): — (no target printed).
- 2021: TBAR 2022 Annexure 1.2 "TB Case Notification", PDF p. 89. Target: "Target TB patients expected to be notified", Total. Notified: "TB patients notified (Achievement against target %)", Total, count part.
- 2022: ITR 2023 Annexure 1.2 "TB CASE NOTIFICATION", PDF pp. 213–214. Target: "Target TB patients expected to be notified", Total. Notified: "TB patients notified, n (% achievement against target)", Total, count part.
- 2023: ITR 2024 Annexure 1.2 "TB case notification", PDF pp. 187–188. Target: "Target of TB patients expected to be notified", Total. Notified: "TB patients notified, n(% of achievement against target)", Total, count part.

**S2 `not_rr_tested`** (2023 only):
- 2023: ITR 2024 Annexure 4.7 "PMDT case finding in 2023 - I", PDF pp. 260–262. Denominator n: "No. of bacteriological confirmed TB cases among notified", Total, count part. Tested: "No. of bacteriologically confirmed TB cases with valid rapid DRT result for at least rifampicin (RS/RR)", Total, count part. Harm x = n − tested. This bacteriologically confirmed denominator departs from the "notified" of the fixed step table, by the controller's ruling on S2 (§5.1).
- Not used (definition change; ruling above): ITR 2019 Annexure 1.10 (2018), ITR 2020 Annexure 4.1 (2019), TBAR 2022 Annexure 4.7 (2021), ITR 2023 Annexure 4.7 (2022).

**S3 `died`** (n = cohort notified; x = died):
- 2018: ITR 2019 Annexure 1.4.a "Treatment outcome of TB patients notified in 2017 (Both Public and Private sector)", PDF pp. 172–173 (2017 cohort). n = Public Sector "TB patients Notified*" + Private Sector "TB patients Notified*". x = Public Sector "Died" + Private Sector "Died". Flag: `public_plus_private`.
- 2019: ITR 2020 Annexure 3.3, PDF pp. 224–225 (2018 cohort). n = "TB patients Notified"; x = "Death Rate", count part.
- 2021: TBAR 2022 Annexure 3.3, PDF p. 102 (2020 cohort). n = "TB patients Notified"; x = "Death Rate", count part.
- 2022: ITR 2023 Annexure 3.3, PDF pp. 251–252 (2021 cohort). n = "TB patients Notified"; x = "Death Rate, n (%)", count part.
- 2023: ITR 2024 Annexure 3.3, PDF pp. 222–223 (2022 cohort). n = "TB patients notified"; x = "Death rate, n(%)", count part. Flag: the table's note that the numerator is outcomes in patients initiated on treatment and the denominator is notified DS-TB cases by current facility.

**S4 `ltfu`** (n = cohort notified; x = lost to follow-up):
- 2018: — (ITR 2019 Annexure 1.4.a prints lost to follow-up for the public sector only; excluded by ruling).
- 2019: ITR 2020 Annexure 3.3, as for S3; x = "% Lost to follow up", count part.
- 2021: TBAR 2022 Annexure 3.3, as for S3; x = "% Lost to follow up", count part.
- 2022: ITR 2023 Annexure 3.3, as for S3; x = "Lost to follow up, n (%)", count part.
- 2023: ITR 2024 Annexure 3.3, as for S3; x = "Lost to follow up, n(%)", count part; same flag as S3.

**S5 `drtb_not_success`** (2023 only):
- 2023: ITR 2024 Annexure 4.13 "Treatment outcome of MDR/RR-TB cases initiated on treatment in 2021 (excluding Pre-XDR-TB and XDR-TB)", PDF pp. 273–274 (2021 cohort). n = "Total MDR/RR-TB initiated on treatment"; x = n − "Treatment success", count part. The Lakshadweep row prints "#N/A" and is handled as in §4.
- Not used (cohorts not comparable; ruling above): ITR 2019 Annexure 1.12, ITR 2020 Annexures 4.8 and 4.6, TBAR 2022 Annexure 4.13, ITR 2023 Annexure 4.13.

**S6 `hiv_unknown`** (n = notified; x = n − HIV status known):
- 2018: ITR 2019 Annexure 1.2 "TB Comorbidities", PDF pp. 169–170. n = "Total TB patients Notified (notified cases based on current PHI)"; known = "Total TB patients with known HIV status (%)#", count part.
- 2019: ITR 2020 Annexure 2.1 "TB – HIV", PDF p. 211; known = "TB patients with known HIV status (%)", Total, count part. n = ITR 2020 Annexure 1.4 "Patient Transfer Status", PDF p. 206, "Net TB Patients Notified", Total.
- 2021: TBAR 2022 Annexure 2.1 "TB - HIV", PDF p. 94; known = "TB patients with known HIV status (%)", Total, count part. n = TBAR 2022 Annexure 1.4, PDF p. 91, "Net TB Patients Notified".
- 2022: ITR 2023 Annexure 2.1 "SCREENING FOR HIV IN NOTIFIED TB", PDF p. 225; known = "TB patients with known HIV status, n (%)", Total, count part. n = ITR 2023 Annexure 1.2, PDF pp. 213–214, "TB patients notified, n (% achievement against target)", Total, count part. Flag: `denominator_diagnosing_PHI` (this edition has no patient-transfer annexure).
- 2023: ITR 2024 Annexure 2.1 "TB patients with known HIV status", PDF p. 199; known = "TB patients with known HIV status, n (%)", Total, count part. n = ITR 2024 Annexure 1.4, PDF pp. 191–192, "Net TB patients* notified (Based on current PHI)", Total.

Reason for the S6 denominator: the net (current-PHI) notified count is used where an edition prints it, as in the ITR 2019 table, which prints its own current-PHI denominator. The flag records the one year where it is not printed.

**Population** (for the population view, §6.7, and H2, §8.3): ITR 2024 Annexure 1.1, "Population - 2023 (in lakhs)", PDF pp. 185–186, multiplied by 100,000. Other editions' population columns are not used.

**NTPS prevalence** (H2): the State and State-group reporting units in `data/extracted/ntps_units.csv`, copied from tb_state_score with its provenance. The measure is the one tb_state_score used: microbiologically confirmed pulmonary TB per 100,000 population aged 15 years and over.

### 5.3 Steps used in each analysis

| Step | 2023 priorities (§6) | Trend and rising flag (§7) | H1 (§8.2) |
|---|---|---|---|
| S1 | yes | 2021–2023 | no |
| S2 | yes | not estimable (definition change) | no |
| S3 | yes | 2018, 2019, 2021, 2022, 2023 | yes (pre-period 2018, 2019, 2021) |
| S4 | yes | 2019, 2021, 2022, 2023 | yes (pre-period 2019, 2021) |
| S5 | yes | no trend | no |
| S6 | yes | 2018, 2019, 2021, 2022, 2023 | yes (pre-period 2018, 2019, 2021) |

---

## 6. Harm averted, priorities and tiers

All quantities in this section are computed per step and data year, over the units with a non-NA cell for that step-year. A unit with NA for a step is excluded from that step only and listed in `outputs/na_cells.csv`; P(top-k) is computed over the remaining units. The main priority year is 2023. The same quantities are computed for the other data years of S1, S3, S4 and S6, for H1 and for the trend outputs.

### 6.1 Shrinkage

**Fixed (verbatim).**
- Binomial steps (S2–S6): beta-binomial empirical Bayes, by method of moments per step-year. Posterior draws come from Beta(α + x, β + n − x).
- S1: gamma-Poisson on notified with exposure = target.

**Operational detail: method of moments (beta-binomial).** Over the U units of a step-year, with p̂_u = x_u / n_u:
- m = Σx_u / Σn_u (the pooled rate);
- s² = (1 / (U − 1)) Σ (p̂_u − m)² (unweighted);
- τ² = s² − m(1 − m) · (1 / U) Σ (1 / n_u);
- S = m(1 − m) / τ² − 1, bounded to the interval [1, 10⁶] (S = 10⁶ when τ² ≤ 0);
- α = m · S, β = (1 − m) · S.
- If m = 0 (no patient lost in any unit), the step-year has no harm to avert: every unit's harm averted is 0, and the step-year is reported as such.

**Operational detail: method of moments (gamma-Poisson, S1).** Notified y_u ~ Poisson(e_u · a_u), with exposure e_u = target_u and a_u ~ Gamma(α, β) (shape α, rate β). With â_u = y_u / e_u:
- m = Σy_u / Σe_u;
- s² = (1 / (U − 1)) Σ (â_u − m)²;
- v = s² − m · (1 / U) Σ (1 / e_u);
- α = m² / v, bounded to [1, 10⁶] (α = 10⁶ when v ≤ 0); β = α / m.
- Posterior draws of a_u come from Gamma(α + y_u, rate β + e_u).

**Operational detail: shrinkage "off"** (an axis of the specification grids, §8.5). The empirical-Bayes prior is replaced by the Jeffreys prior: α = β = ½ for S2–S6, and α = ½, β = 0 for S1. These values replace α and β in every formula of this plan, including the posterior draws and the posterior means used for benchmarks. Draws therefore come from Beta(½ + x, ½ + n − x) for S2–S6, and from Gamma(½ + y, rate e) for S1. Everything else is unchanged.

**Posterior mean rates:** (α + x_u) / (α + β + n_u) for S2–S6; (α + y_u) / (β + e_u) for S1. With shrinkage off these are (½ + x_u) / (1 + n_u) and (½ + y_u) / e_u.

### 6.2 Benchmark

**Fixed (verbatim).** **Benchmark** (per step-year, on posterior-mean rates across units)
- Main: the 75th percentile of performance, i.e. the 25th percentile of loss rates (the better quartile). Sensitivities: the median; the best decile.

**Operational detail.**
- Percentiles are taken with `numpy.percentile(..., method="linear")` over the posterior-mean rates of the units in the step-year.
- Loss steps (S2–S6): main r_bench = 25th percentile of loss rates; median = 50th; best decile = 10th.
- S1 (achievement, where higher is better): main a_bench = 75th percentile of achievement; median = 50th; best decile = 90th.
- In the specification grids (§8.5) these are named p75, median and p90 (the 75th, 50th and 90th percentiles of performance).
- The benchmark is computed once per step-year and specification, from the posterior means. It is not redrawn per draw.

### 6.3 Harm averted

**Fixed (verbatim).**
- **Harm averted** (unit u, step s) = max(0, n_u·(r_u − r_bench)). For S1 it is max(0, a_bench·target_u − notified_u).
- Computed per draw, with 10,000 draws.

**Operational detail.**
- In draw d, r_u is replaced by its posterior draw r_u⁽ᵈ⁾: harm averted⁽ᵈ⁾ = max(0, n_u · (r_u⁽ᵈ⁾ − r_bench)).
- For S1, notified_u is replaced by a_u⁽ᵈ⁾ · target_u: harm averted⁽ᵈ⁾ = max(0, target_u · (a_bench − a_u⁽ᵈ⁾)). With the observed achievement in place of the draw, this equals the fixed formula.
- Each unit's harm averted is summarised by the mean of its 10,000 draws (`harm_averted_mean`) and by the 2.5th and 97.5th percentiles (`lo`, `hi`; numpy linear method).
- Harm averted is never negative: where the expression is below 0, harm averted is 0 per draw. Because the floor is applied per draw, `harm_averted_mean` can exceed 0 for a unit whose posterior-mean rate is at or better than the benchmark.

### 6.4 Priority and tiers

**Fixed (verbatim).**
- k = 5 (main); sensitivities k = 3 and k = 8.
- P(top-k) is computed within each step, from draws.
- Tiers: "act now" P ≥ 0.80; "probable priority" 0.50 ≤ P < 0.80; "uncertain" 0.20 ≤ P < 0.50; "lower priority" P < 0.20.

**Operational detail.**
- In each draw, the units of the step-year are ordered by harm averted⁽ᵈ⁾, and the k largest each score 1. A unit whose harm averted is 0 in a draw scores 0 in that draw. If units with harm averted above 0 are tied at the k-th place, the places left are shared equally among those tied units; units with zero harm get no share of tied top-k places. P(top-k) is the mean score over the 10,000 draws.
- Tiers are set on P(top-5) from the main specification (benchmark p75, shrinkage on) for data year 2023, separately for each step S1–S6. No combined score across steps is formed.
- Tiers under k = 3 and k = 8, and under the median and best-decile benchmarks, are reported as sensitivities. Headline tiers use k = 5 and the p75 benchmark.

### 6.5 Rising-risk flag and "watch: rising"

**Fixed (verbatim).** **Rising-risk flag:** the trend slope's 95% CI lies wholly on the worsening side. A unit in "uncertain" or "lower priority" with the rising flag is relabelled "watch: rising".

**Operational detail.**
- The slope and its CI come from the main trend model (§7). The worsening side is a positive slope of logit(loss rate) for S3, S4 and S6, and a negative slope of log achievement for S1.
- Where the trend is not estimable (S2; S5; a unit-step with too few years), the rising flag is false and the reason is recorded.
- "Watch: rising" replaces "uncertain" or "lower priority" only. It never changes "act now" or "probable priority".

### 6.6 Small but far behind

**Fixed (verbatim).** **Small but far behind:** the unit's rate gap (r_u − r_bench) is in the worst quartile across units AND its harm averted is below the median. Reported as a flag; never changes the tier.

**Operational detail.**
- The rate gap uses posterior-mean rates: r_u − r_bench for S2–S6, and a_bench − a_u for S1.
- "Worst quartile" means a gap at or above the 75th percentile of the gaps of the units in the step-year. "Below the median" means `harm_averted_mean` strictly below the median of `harm_averted_mean` over the same units. Percentiles use the numpy linear method.

### 6.7 Population view

**Fixed (verbatim).** **Population view:** harm averted per 100,000 population, using the ITR-printed population. Shown alongside; never used for tiers.

**Operational detail.** For data year 2023, `per_100k` = harm_averted_mean ÷ (population in lakhs × 100,000) × 100,000, with the ITR 2024 Annexure 1.1 population of the coarsened unit (§4).

### 6.8 Cross-step profile

For each unit, the step with its largest relative gap is reported: (r_u − r_bench) / r_bench for S2–S6, and (a_bench − a_u) / a_bench for S1, using posterior means for data year 2023. If the benchmark is 0, the relative gap is NA. The profile is descriptive. It does not combine steps and does not affect tiers.

---

## 7. Trend

### 7.1 Fixed values and rulings

**Fixed (verbatim).**
- Per unit and step: weighted least squares of logit(rate) on year (log achievement for S1), with weights from the binomial (Poisson) variance of the transformed rate.
- Slope 95% CI: normal, from the WLS variance.
- Main analysis requires ≥3 non-2020 years; otherwise "trend not estimable".

**Ruling (verbatim).** **S1** uses 2021–2023 only, the years with printed targets. Its trend uses those 3 years. **S2** … trend "not estimable (definition change)". **S5** … no trend. (The full rulings are in §5.1.)

### 7.2 Main model

**Operational detail.**
- Observed (not shrunken) counts are used.
- Loss steps S3, S4 and S6: the transformed rate is the empirical logit L_t = log((x_t + ½) / (n_t − x_t + ½)), with variance V_t = 1/(x_t + ½) + 1/(n_t − x_t + ½).
- S1: the transformed rate is L_t = log((y_t + ½) / e_t), with variance V_t = 1/(y_t + ½), where y_t is notified and e_t the target.
- Model: L_t = β₀ + β₁ (t − 2023) + γ · [t = 2021], with weights w_t = 1 / V_t. The term γ is the 2021 year indicator of the fixed values.
- The slope is β₁. Var(β₁) = φ_s · [(XᵀWX)⁻¹]₁₁, where φ_s = max(1, Σ Pearson χ² ÷ Σ residual df), pooled over all units of step s in the main model (units with 0 residual df contribute nothing to either sum). The 95% CI is β₁ ± 1.96 × SE, with SE = √Var(β₁).
- A unit-step needs at least 3 data years with non-NA cells. With 2020 dropped, every year counts as a non-2020 year. Otherwise the result is "trend not estimable".
- The 2021 indicator is fitted only where the unit-step has at least one year before 2021 (S3, S4, S6). For S1, which has no year before 2021, the indicator cannot be separated from the slope. The S1 main model is therefore L_t = β₀ + β₁(t − 2023) over 2021–2023, and its sensitivity is the model with the indicator (the 2022–2023 slope). Where the indicator is fitted, a unit-step needs at least 3 non-NA years other than 2021.
- Years used: S1 2021–2023; S3 and S6 2018, 2019, 2021, 2022, 2023; S4 2019, 2021, 2022, 2023. S2: "not estimable (definition change)". S5: no trend.

### 7.3 Sensitivity

"Sensitivity: all years" (§3.2) is the same model without the 2021 indicator, over the same data years, for S3, S4 and S6. For S1 the sensitivity is the model with the indicator (§7.2). The number of units whose rising flag differs from the main model is reported. Tiers and "watch: rising" use the main model only.

---

## 8. Headline estimates, specification grids and labels

### 8.1 Fixed values and rulings

**Fixed (verbatim).** **Headline estimates and their nulls**

| | Estimate | Null | Interval |
|---|---|---|---|
| H1 | Temporal stability: Spearman ρ between each unit's mean harm averted over the pre-period (2018, 2019, 2021) and its 2023 harm averted, pooled over steps S2–S5, unit × step | 0 | Bootstrap over units, 10,000 draws |
| H2 | External association: Spearman ρ between State 2023 S1 shortfall per 100,000 population and NTPS prevalence (19–20 units; State groups population-weighted as in tb_state_score) | 0 | Fieller interval, as in tb_state_score |

Also reported for H1: top-5 overlap.

- **H3 (descriptive, no label):** the share of total harm averted (summed over steps S2–S5) in the top-5 units.

**Ruling (verbatim).** **H1** pools S3, S4 and S6 only. (Also, from §5.1: S2 and S5 are excluded from H1, and the S4 pre-period is 2019 and 2021.)

### 8.2 H1: temporal stability

**Operational detail.**
- **Steps and years.** Steps S3, S4 and S6. Pre-period: 2018, 2019 and 2021 for S3 and S6; 2019 and 2021 for S4. Comparison year: 2023.
- **Values.** For each unit-step and year, `harm_averted_mean` (§6.3), computed with that year's own shrinkage prior and benchmark. The pre-period value is the arithmetic mean over the pre-period years.
- **Inclusion.** A unit-step enters H1 only if it has a non-NA value for every year of its pre-period and for 2023. Excluded unit-steps are listed.
- **Ranking.** Harm averted is not comparable across steps: a death and an unknown HIV status have no common weight (design §4.0). Ranks are therefore formed **within each step**. Within each step, the pre-period values and the 2023 values are ranked separately, with average ranks (ties share the mean rank). Each rank is divided by (n_s + 1), where n_s is the number of unit-steps of step s in H1.
- **Estimate.** ρ_H1 is the Pearson correlation of these within-step normalised ranks over all pooled unit × step pairs.
- **Interval.** Bootstrap over units, with 10,000 draws.
  - In each draw, units are resampled with replacement (as many as there are units in H1), and each drawn unit brings all its unit-step pairs.
  - Within-step ranks are recomputed in each draw, with duplicated units ranked as ties.
  - The 95% interval is the 2.5th and 97.5th percentiles of the draws (numpy linear method).
  - A draw in which ρ is undefined (no variation in ranks) is discarded, and the number discarded is reported.
- **Null:** ρ = 0.
- **Top-5 overlap** (descriptive). For each step, the count of units in both the top 5 by pre-period mean and the top 5 by 2023 `harm_averted_mean`. It is reported for each step and summed over the three steps (out of 15). Ties at the fifth place are broken alphabetically by unit name, and this is stated.
- **Main specification:** benchmark p75, shrinkage on, year window {2018, 2019, 2021} (S4: {2019, 2021}).

### 8.3 H2: external association

**Operational detail.**
- **Quantity.** For each NTPS reporting unit: the data-year-2023 S1 harm averted (§6.3; `harm_averted_mean`) per 100,000 population. This is the shortfall against the benchmark achievement applied to the target, so the grid's benchmark and shrinkage axes (§8.5) change it. Under the main specification it is the posterior mean of max(0, a_bench·target_u − a_u⁽ᵈ⁾·target_u).
- **State groups.** An NTPS unit made of several States takes Σ harm averted ÷ Σ population × 100,000 over its member units. This is the population-weighted mean of the members' per-100,000 values, as tb_state_score weighted by population. Population is the ITR 2024 Annexure 1.1 population (§5.2).
- **Coarsened units and NTPS units.** Each NTPS unit's member States are mapped to the 33 units of §4. If a coarsened unit's members fall in different NTPS units, the coarsened unit is assigned to the NTPS unit that holds its most populous member. States that the survey does not cover are excluded and listed.
- **Estimate.** Spearman ρ between this quantity and NTPS prevalence, over the NTPS reporting units (19–20 units; n is stated with the estimate). Ties take average ranks; ρ is the Pearson correlation of the ranks.
- **Interval** (as in tb_state_score): Fisher-z 95% confidence interval with Fieller's variance for Spearman's ρ: z = atanh(ρ), SE = √(1.06 ÷ (n − 3)), interval tanh(z ± 1.96 × SE). If n ≤ 3, no interval is given.
- This replaces the raw shortfall because the benchmark and shrinkage axes of the fixed H2 grid have no meaning for it. The signed (target − notified) per 100,000 is reported alongside as a descriptive, unlabelled sensitivity.
- **Null:** ρ = 0. No direction is assumed: the label (§8.6) uses only the interval and the grid's sign agreement.
- **"Per target"** (a grid axis): Σ harm averted ÷ Σ target over the member units, in place of population.
- **Main specification:** benchmark p75, shrinkage on, per population.
- This is a test of association, not of validity. The survey's prevalence (2019–21) and the 2023 shortfall describe different years, and a CTD target is a programme goal, not an estimate of disease.

### 8.4 H3: concentration (descriptive, no label)

**Operational detail.**
- For each step S2–S5 in data year 2023, the top-5 units are the five with the largest `harm_averted_mean` (ties at the fifth place broken alphabetically).
- H3 = (Σ over steps S2–S5 of the harm averted in that step's top-5 units) ÷ (Σ over steps S2–S5 of the harm averted in all units), under the main specification.
- The share for each step is reported alongside. The steps count different kinds of patient lost. The summed share is a count of patients and puts no weight on any step.
- H3 has no null, no interval and no label.

### 8.5 Specification grids

**Fixed (verbatim).** **Specification grids**
- H1: benchmark {p75, median, p90} × shrinkage {on, off} × year window {excluding 2020, including 2020} = 12 entries.
- H2: benchmark {p75, median, p90} × shrinkage {on, off} × denominator {per population, per target} = 12 entries.

**Ruling (verbatim).** The "including 2020" sensitivity is replaced, for H1, by the year-window axis {pre-period 2018, 2019, 2021} vs {2019, 2021}.

**Operational detail.**
- H1 grid: benchmark {p75, median, p90} × shrinkage {on, off} × year window {pre-period 2018, 2019, 2021; pre-period 2019, 2021} = 12 entries. The S4 pre-period is 2019 and 2021 under both windows. The bootstrap interval is computed for the main entry only.
- H2 grid: benchmark {p75, median, p90} × shrinkage {on, off} × denominator {per population, per target} = 12 entries.
- Each grid includes the main specification as one of its 12 entries. Every entry is written to `outputs/spec_curve.csv`.

### 8.6 Label rule

**Fixed (verbatim).** Labels: "supported" only if the main 95% interval excludes the null AND ≥80% of specification-grid entries agree in sign with the main estimate; otherwise "not established".

**Operational detail.**
- The label applies to H1 and H2 only. H3, the leave-one-out results and all sensitivities carry no label.
- "Excludes the null": both ends of the interval are strictly above 0, or both strictly below 0.
- "Agree in sign": an entry agrees if its ρ has the same strict sign as the main estimate. An entry with ρ = 0, or with ρ undefined, does not agree. The main entry counts as one of the 12. With 12 entries, "supported" needs at least 10 entries agreeing (10/12 ≥ 0.80; 9/12 = 0.75 is not enough).
- Labels are set by this rule and reported as computed.

### 8.7 Leave-one-out (descriptive, no label)

**Operational detail.**
- **H1 and H2.** The main-specification point estimate is recomputed with each unit left out in turn: for H1, all of that unit's unit-step pairs; for H2, each NTPS reporting unit. The minimum and maximum ρ are reported, with the unit whose omission gives each.
- **2023 tiers.** Each unit is removed in turn. For each step, the shrinkage prior, benchmark, P(top-5) and tiers of the remaining units are then recomputed (main specification). The number of (unit, step) tier changes among the remaining units is reported, with the omitted unit that causes the most changes.
- Results go to `outputs/leave_one_out.csv`.

---

## 9. District modules

### 9.1 National district module, data year 2018 (ITR 2019 Annexure 1.13)

**Ruling (verbatim).** **National district module, data year 2018 (ITR 2019 Annexure 1.13, about 760 districts).**
- Steps:
  - D1 "not initiated on treatment" = total notified − total initiated;
  - D2 "public-sector treatment not successful" = the 2017 public cohort (success N ÷ success %) − success N. Rounding from % is flagged.
- The same within-step harm, shrinkage, P(top-k) and tiers as the States, with k = 20.
- A State-relative funnel per district.
- Labelled as 2018 data (historical).

**Operational detail.**
- **Source.** ITR 2019 Annexure 1.13 "District Wise Indicators", PDF pp. 188–220. The units are the district rows as printed (State | District); the row count is verified at extraction. Districts are not coarsened and not linked to later district names.
- **D1.** n = "Total TB patients Notified$"; initiated = "TB patients initiated on treatment-Total"; x = n − initiated. A district where the number initiated exceeds the number notified is NA for D1 and is listed with that reason.
- **D2.** The column is "Treatment success rate of TB notified patients (Public sector) 2017 (N&%)", with success count N and printed percentage p.
  - Cohort n = round(N ÷ (p / 100)), rounding half up; x = n − N.
  - Every D2 value carries the flag `rounded_from_percent` and the cohort range implied by the rounding of p. With h = half of the last printed digit of p (h = 0.5 when p is printed as a whole number), the range runs from N ÷ ((p + h)/100) to N ÷ ((p − h)/100), and its lower bound is clipped at N.
  - p = 100 gives x = 0.
  - p = 0, or a blank cell, gives NA.
  - The private-sector column is not used.
- **Estimation.** For each of D1 and D2, across all districts in the country:
  - beta-binomial shrinkage (§6.1);
  - the p75 benchmark, i.e. the 25th percentile of loss rates (§6.2);
  - harm averted per draw (§6.3);
  - P(top-20), and tiers with the thresholds of §6.4;
  - the small-but-far-behind flag (§6.6).

  There is one data year, so there is no trend, no rising flag and no "watch: rising". There is no district population, so there is no population view.
- **State-relative funnel.** For each district d in State S, the State's pooled proportion is p_S = Σx ÷ Σn over its districts, and z_d = (p̂_d − p_S) ÷ √(p_S (1 − p_S) / n_d).
  - **Multiplicative adjustment** (Spiegelhalter, Stat Med 2005;24:1185). The signed z_d are set to their 10th and 90th percentiles (numpy linear) where they lie outside them, and φ = the mean of the squared winsorised z_d. φ is estimated once from all districts in the country, because many States have too few districts for their own estimate. States with one district are excluded from φ, from D and from G. If φ > 1, the limits are widened by √φ.
  - **Additive adjustment (reported separately).** A DerSimonian–Laird between-district variance τ² is estimated with State-specific centres:
    - w_d = n_d ÷ (p_S (1 − p_S));
    - Q = Σ w_d (p̂_d − p_S)²;
    - τ² = max(0, (Q − (D − G)) ÷ (Σw_d − Σ_S [Σ_{d∈S} w_d² ÷ Σ_{d∈S} w_d])), where D is the number of districts and G the number of States with at least two districts.

    The adjusted z is (p̂_d − p_S) ÷ √(p_S (1 − p_S) / n_d + τ²).
  - **Limits.** Limits are drawn at 95% (z = 1.96) and 99.8% (z = 3.09). A district is flagged "above State limits" or "below State limits" when it lies outside the 99.8% limits under the multiplicative adjustment. Its position under the additive adjustment is reported alongside.
  - A State with a single district has no funnel; it is listed.
- **Output:** `outputs/district_national_2018.csv`, labelled as 2018 data (historical).

### 9.2 Madhya Pradesh and Maharashtra, notifications 2022–2024 (Lok Sabha Q802)

**Fixed (verbatim).** **District (Madhya Pradesh, Maharashtra; 2022–2024 notifications only)**
- Change 2022→2024 per district, with Poisson SE √(n22 + n24).
- Funnel around the State's pooled change: multiplicative overdispersion φ from 10%-winsorised z (Spiegelhalter 2005) and additive DerSimonian–Laird τ².
- Flags: "fell beyond adjusted limits" and "rose beyond adjusted limits".
- No tiers at district level. The paper states that a notification fall can mean less TB or less case-finding.

**Ruling (verbatim).** **MP/MH district trend (AU802, 2022–2024).** Kept as in the plan. There is no 2018→2022 linkage, because districts were renamed or split. The Vidisha duplicate is kept once and flagged.

**Operational detail.**
- **Units.**
  - Madhya Pradesh: 52 distinct districts, from 53 printed entries. "Vidisha" appears twice with identical values; it is kept once with the flag `duplicate_entry`. The three districts created in 2023 are not printed and are not added.
  - Maharashtra: the 80 NTEP districts as printed, including municipal corporations and Mumbai wards.
- **Change.** For district d: Δ_d = n24 − n22, with Poisson SE √(n22 + n24). The State's pooled change is R − 1, where R = N24 ÷ N22, the ratio of the State totals summed over its printed districts.
- **Funnel statistic.** z_d = (Δ_d − n22 (R − 1)) ÷ √(n22 + n24). Dividing the numerator and the denominator by n22 puts the funnel on the scale of relative change: y_d = Δ_d ÷ n22, with SE s_d = √(n22 + n24) ÷ n22, around R − 1.
- **Overdispersion,** estimated within each State:
  - multiplicative: the signed z_d are set to their 10th and 90th percentiles (numpy linear) where they lie outside them, and φ = the mean of the squared winsorised z_d; if φ > 1, the limits widen by √φ;
  - additive: w_d = 1 / s_d², Q = Σ w_d (y_d − (R − 1))², τ² = max(0, (Q − (D − 1)) ÷ (Σw_d − Σw_d² ÷ Σw_d)), and the adjusted z = (y_d − (R − 1)) ÷ √(s_d² + τ²).
- **Flags.** "Fell beyond adjusted limits" or "rose beyond adjusted limits": outside the 99.8% limits (z = 3.09) under the multiplicative adjustment. The 95% limits and the additive adjustment are reported alongside.
- A district with n22 = 0 is NA and listed. The 2023 column is shown descriptively and is not tested.
- **No tiers** at district level. The report and the paper state that a fall in notifications can mean less TB or less case-finding, and that notifications alone cannot tell the two apart.
- **Output:** `outputs/district_mp_mh.csv`.

### 9.3 District input schema

The tool's district command takes a CSV with the required columns `district, year, notified`, and the optional columns `target, population` and any `cascade_*`. With notifications only, it gives the change and funnel of §9.2. The schema accepts optional columns, drops a "Total" row with a warning, and fails with a clear message when a required column is missing. A synthetic example file is clearly labelled as synthetic.

---

## 10. Computation, reproducibility and outputs

### 10.1 Computation

**Fixed (verbatim).** Python 3.14, always `python -I`; LF line endings; seed 20261121; numpy `default_rng(seed)`, reset per analysis; 10,000 draws.

**Operational detail.**
- Python 3.14 with numpy 2.3.5 and scipy 1.16.3.
- "Reset per analysis" means a new `numpy.random.default_rng(20261121)` at the start of each of the following:
  - each draw set for a step, year and specification (§6);
  - the H1 bootstrap (§8.2);
  - each leave-one-out refit (§8.7);
  - each district step (§9.1).
- Within a draw set, units are processed in alphabetical order of unit name, and each unit's 10,000 draws are taken in one call.
- Every percentile uses `numpy.percentile(..., method="linear")`.
- Reruns with the same inputs must give byte-identical outputs. This is checked.

### 10.2 Outputs

- `data/extracted/state_panel.csv`: columns `unit, year, step, numerator, denominator, source_file, pdf_page, table_id, flag`.
- `outputs/state_priority.csv`: columns `unit, step, year, harm_averted_mean, lo, hi, per_100k, p_top5, tier, rising, small_far_behind, rate, rate_bench`.
- `outputs/state_priority_sensitivity.csv`: P(top-k) and tiers under k = 3 and k = 8, and under the median and best-decile benchmarks.
- `outputs/state_harm_draws_summary.csv`: the summary of the draws for each unit, step, year and specification.
- `outputs/na_cells.csv`: every NA or flagged cell, with the reason.
- `outputs/state_trend.csv`: the slope, its CI, the years used and the rising flag, with the sensitivity model's slope and flag.
- `outputs/headline.csv`: columns `estimate, value, lo, hi, null, n, n_grid, n_agree, label`, for H1, H2 and H3 (H3 without interval or label).
- `outputs/spec_curve.csv`: every grid entry of H1 and H2.
- `outputs/leave_one_out.csv`.
- `outputs/district_national_2018.csv` and `outputs/district_mp_mh.csv`.
- `outputs/report_state.html` and `outputs/report_district.html`: self-contained reports, with a priority-matrix heat-map, funnel plots, per-unit summaries, a plain-language legend and the caveats.

### 10.3 Verification

- `verification/check_plan_order.py` checks the registration order and the frozen text above §12.
- An independent standard-library recompute covers:
  - P(top-5) for the units at each tier boundary of the 2023 S3 step, from its own standard-library draws (not numpy's), agreeing within |Δ| ≤ 0.02;
  - the H1 and H2 point estimates;
  - the labels, from `outputs/spec_curve.csv`.
- Further checks:
  - the extracted tables against their printed totals;
  - a byte-for-byte rerun of `outputs/`;
  - mutation tests showing that each check fails when its target is altered.
- Every deviation from this plan is dated and explained in §12. Any analysis not in this plan is labelled exploratory.

### 10.4 Known limitations stated in advance

- With denominators of about 10⁵ patients, P(top-k) mostly reflects binomial noise, so it will be close to 0 or 1. The tiers therefore express little uncertainty beyond sampling.
- H1 is largely driven by unit size: large units have large harm averted in every year. The Spearman ρ of rate gaps (r_u − r_bench, or a_bench − a_u for S1) between the pre-period and 2023 is therefore reported alongside H1 as a descriptive measure, without a label.
- H2 may be circular if CTD targets were set from burden estimates that include NTPS.

---

## 11. What had been seen before registration

This section lists everything seen before this plan was registered. No estimate of any kind had been computed in this repository: no rate, ratio, harm averted, benchmark, shrinkage prior, P(top-k), tier, trend, correlation or funnel position, for any unit, step or year.

1. **The India TB Report tables (Task 1 inventory, 21 November 2026).** Every table listed in `docs/data_inventory.md` was opened, in all six editions from ITR 2019 to ITR 2024. Its annexure number, pages, column headers, the units it covers and its printed India total row were recorded.
   - The printed India total rows were transcribed into the inventory, including the national percentages printed in them (for example, HIV status known and UDST tested, as printed). Nothing was calculated from them.
   - State rows were located by a text match on unit names, and rows were counted. Their values were on the pages read and may have been visible. No State value was recorded or used.
   - ITR 2021 is a scan. Its tables were viewed as page images at 90–110 dpi, for the header and the total row only.
   - The controller's rulings after Task 1 were made from this structural record: which tables exist, their definitions and cohorts, and the unit composition. They cover dropping 2020, the coarsening, which steps enter the trends and H1, and the national district module. They were not made from State values.
2. **State descriptive values in the companion repositories.** The author's two related studies used some of the same source tables. Their extracted values, analyses and manuscripts were seen by the author.
   - **tb_state_score** (hssling/india-state-tb-score; the State TB Score study, JPH-26-1883).
     - It extracted State values from ITR 2023 and ITR 2024 for score years 2022 and 2023. These include notifications against targets; UDST testing; HIV status known; treatment success and its cohorts; deaths and loss to follow-up for the 2022 cohort (ITR 2024 Annexure 3.3); DR-TB treatment outcomes; a population derived from Annexure 1.2; and the NTPS State and State-group prevalence values (`ntps_units.csv`, which this study reuses). These are State-level descriptive values of some inputs to S1–S6 for data years 2022 and 2023.
     - Its results, which the author has seen, include State score reconstructions, rank robustness, Spearman correlations between the State TB Score and NTPS prevalence, and overdispersion-adjusted funnels of change in score.
     - tb_state_score computed and the author saw each State's notified ÷ target and HIV-known proportion for 2022 and 2023 and their changes; these determine the S1 rate and, under the indicator model, the S1 slope. The source tables also print the step rates themselves as percentages.
     - That study did not correlate notified ÷ target with NTPS prevalence (its plan §9.3 excluded it). It did not compute harm averted, a benchmark gap or P(top-k).
   - **tb_acf_campaign** (hssling/india-tb-acf-campaign; the ACF campaign study, submitted to Public Health).
     - It extracted State notification tables from ITR 2020, ITR 2023 and ITR 2024 (Annexure 1.2, including the printed targets of the 2023 and 2024 editions), and State and district figures from parliamentary answers.
     - It also extracted the State active case-finding (ACF) tables of ITR 2019 (Annexure 1.7 "Active Case Finding", data year 2018) and TBAR 2022 (Annexure 6 "Active Case Finding", data year 2021), and of ITR 2020, ITR 2023 and ITR 2024 (Annexure 6).
     - It analysed active case-finding yield and notification change. Its State notification values for data years 2022 and 2023 were seen.
   - No value from either repository was used in writing this plan. The steps, benchmark, k, thresholds and grids were fixed in the design and implementation plan from the questions, not from these values.
3. **The AU802 district counts as printed.** Task 1 read both tables of Lok Sabha Unstarred Question 802 in full. It recorded the district names and the number of entries, found the duplicate "Vidisha" entry with identical values, and found no blank or non-numeric value cell. The district notification counts for 2022, 2023 and 2024 were therefore displayed as printed. No change, ratio, pooled change, z-score or funnel position was computed.
4. **The structure of ITR 2019 Annexure 1.13.** The header, the footnotes and the printed India total row were recorded. District rows were counted by machine (about 761 rows with at least nine numeric cells). The Madhya Pradesh (51) and Maharashtra (79) district names were listed. The district values were on the pages read and may have been visible. None was recorded, and nothing was computed from them.
5. **Nothing else.** No NTPS value was re-read for this study. No output of this repository existed before the registration commit.

---

## 12. Deviations (dated)

**12.1 (21 November 2026), a factual correction with no change to any rule or result.** §4 and the data inventory state that Lakshadweep is absent from ITR 2019 Annexure 1.4.a (the 2017 treatment-outcome cohort, used for S3 in data year 2018). Extraction found it printed, as "Lakshwadeep", with public-sector cells, private notified 0 and the other private cells blank. Its Died cell is blank, so under the registered rule a member row with a blank needed cell adds nothing to its merged unit: Kerala S3 2018 is formed from Kerala's row alone and flagged `member_missing:Lakshadweep`, exactly as the plan expected. Only the stated reason differs (printed with a blank cell, not absent). The crosswalk accepts the misspelling "Lakshwadeep" for that table only.

**12.2 (21 November 2026), a deviation decided before any estimate was computed: the S6 denominator for data year 2022.** §5 registered ITR 2023 Annexure 1.2 (notified, diagnosing-PHI basis) as the S6 2022 denominator. Review of the extraction found that ITR 2023 Annexure 2.1, which supplies the S6 numerator (HIV status known), prints percentages whose implied denominators match ITR 2023 Annexure 1.6 (notified by sex: male + female + transgender), not Annexure 1.2. Examples: Andhra Pradesh 93,071 implied vs 93,092 (A1.6) vs 92,187 (A1.2); Mizoram ~2,106 vs 2,106 vs 2,085. Mixing the two bases makes five units' "known" exceed "notified" (NA under the registered rule) and distorts others (for example Uttar Pradesh: 1,219 lost on the registered basis vs about 14,223 on the A1.6 basis). Deviation: the main S6 2022 denominator is the A1.6 sum (male + female + transgender), the basis of the numerator's own table. The registered A1.2 basis is kept and reported as a sensitivity (the S6 2022 cells, and every S6 result that uses 2022, are given on both bases). Reason: numerator and denominator must share a basis. Timing: decided on 21 November 2026 from the extraction review, before src/tbprio/ existed and before any rate, harm, priority, trend or correlation was computed.
