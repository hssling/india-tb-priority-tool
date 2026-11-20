# Where to invest against TB in India: a State and district priority tool. Design

Date: 21 November 2026. Idea B from the author's research list ("an alternative state ranking tool"), reshaped by the author's answers on 21 November 2026.

## 1. Intent

**Author's words.** The tool should guide "where to invest, where to focus and sort of risk prioritisation, also anything that is essential for programmatic decision making". It serves "both" levels: the national programme choosing between States, and a State programme choosing between its districts. The approach is option C (below).

**Purpose.** The tool helps those who run India's National TB Elimination Programme (NTEP) decide where extra effort would prevent the most TB harm, at which step of the care pathway, and how sure we can be. The Central TB Division (CTD) and State TB Cells are the users.

**Not a league table.** The official State TB Score asks "how did each State do on nine process indicators?". This tool asks a different question: "where would closing a gap prevent the most harm, and where is the risk rising?".

**Relation to the author's other work.** The State TB Score paper (JPH-26-1883, under review) audits whether the official score can be rebuilt and ranked reliably. This study does not reconstruct or re-rank that score. It has its own question, outputs and method. It may share extraction code and some source tables, and it will disclose JPH-26-1883 (and the Public Health ACF paper) as related manuscripts.

## 2. Goals, non-goals, anti-goals

**Goals**
- Priorities in natural units of harm: missed cases, deaths, people lost to follow-up, people not tested for drug resistance, and drug-resistant patients not successfully treated. Each comes with an uncertainty interval and is broken down by step of the care pathway.
- A priority matrix (State × care-pathway step) that says where an extra unit of effort buys most, with tiers ("act now", "probable priority", "uncertain", "lower priority") rather than ranks.
- Trajectory: whether each gap is closing or widening across data years 2018–2023, so that rising risk is flagged.
- A reusable open tool that a State officer can run on their own district export, demonstrated on one or two States.
- Tests of the tool's reliability: stability across years, robustness to reasonable choices, and association with the independent prevalence survey.
- Full reproducibility from public sources; pre-registration before any estimate.

**Non-goals**
- Causal estimates of the effect of any intervention.
- A cost-effectiveness analysis: no cost data are used. "Where an extra unit of effort buys most" means harm that could be averted by closing a gap, not cost per outcome.
- Producing national district results for all ~700 districts.
- Replacing the State TB Score.

**Anti-goals (failure even if it runs)**
- Rankings without uncertainty.
- Rates that make small States or UTs dominate the priorities.
- Causal or blaming language about States.
- Priorities that flip under a reasonable alternative choice without the paper saying so.
- A district module that only works on one State's file layout.
- Overlap with JPH-26-1883 large enough to look like redundant publication.

## 3. Data

**State level.** All sources are public India TB Report (ITR) editions, held locally with SHA-256 digests:
- ITR 2019 (data 2018);
- ITR 2020 (2019);
- ITR 2021 (2020);
- TB Annual Report 2022 (2021);
- ITR 2023 (2022);
- ITR 2024 (2023).

State annexures expected per edition (the builder inventories exactly what each edition prints):
- the notification target/expected cases;
- notifications, public and private;
- presumptive examination;
- testing for rifampicin resistance (UDST);
- HIV status known;
- treatment outcomes: success, died, lost to follow-up;
- DR-TB notifications and outcomes;
- TPT, where printed.

The National TB Prevalence Survey 2019–21 (NTPS; state or state-group prevalence with CIs; 19–20 units) serves as an independent yardstick and as an alternative source of expected cases.

Existing extractions can be reused or adapted after review: tb_state_score data/extracted (ITR 2023/2024 indicators, outcomes, DR-TB, population, NTPS) and tb_acf_campaign (ITR 2019–2024 ACF and notification tables).

**District level (demonstration).** Settled 21 Nov 2026.
- Ni-kshay does not allow downloads (author, 21 Nov), and the parliament library is unreachable from this machine. The district source is the author-supplied Word copy of **Lok Sabha Unstarred Question 802 (7 February 2025)**, at data_raw/pq/AU802_LlE1Wb.docx (SHA-256 recorded at extraction). Its source is the Ni-kshay portal.
- It gives district-wise TB notifications for 2022, 2023 and 2024 for **Madhya Pradesh** (about 55 districts) and **Maharashtra** (the 80 NTEP districts, including municipal corporations). These ~135 units are the demonstration.
- Karnataka (Lok Sabha Q1891, 2 Aug 2024) is NOT usable: the author's copy has the annexure heading but no table. It is added only if a readable copy turns up.
- If the India TB Reports print national district tables for any year (being checked: ITR 2019 has a "State and district-wise performance" section), the builder adds them as a second district source and records what was found.
- No district targets or cascade fields are available. The district module's minimum input is therefore notifications by district and year, with an optional expected/target column and optional cascade columns. On notifications only, it reports trend, change beyond noise, and a funnel position relative to the State.
- District population is NOT downloaded without the author's approval. Without it, the module does not compute per-population rates for districts.

**Data rules**
- No imputation. NA is listed.
- Every value is traced to its page and table.
- Table totals are checked against printed totals.
- Definitional changes between editions are recorded as flags, not silently harmonised.

## 4. Method

### 4.0 Settled after the builder check (21 Nov 2026)
- **Main measure: author's answer.** Both views, absolute first. Tiers are set on absolute harm averted, because that is what a fixed budget buys. Every unit also gets its gap per population (or per notified patient) and a flag "small but far behind" (rate gap in the worst quartile, absolute harm below the median), so poor performers are not hidden behind large States.
- **Within-step priorities: my call.** There is no defensible common weight between a missed case, a death and an untested patient, so P(top-k) and tiers are computed within each step. Each unit gets a cross-step profile showing its largest relative gap. No single combined score.
- **"Shortfall against target", not "missed cases": my call.** A CTD target is a programme goal, not an estimate of disease, so the measure is named accordingly. It is computed only for years whose edition prints State targets; the builder inventories which years these are before registration. Its trend and out-of-time analyses use only those years. Steps with a full 2018–2023 series carry the trajectory and stability analyses.
- **NTPS is the independent yardstick only: my call.** NTPS is NOT used to build expected cases. That conversion needs prevalence-to-incidence, child and extrapulmonary assumptions, and it would make the external test circular. The external test uses the target-based shortfall and states its limits (19–20 units; prevalence in 2019–21).
- **COVID: my call.** The main trend and stability analyses exclude data year 2020. 2021 is kept, with a year indicator. A sensitivity analysis includes all years.

### 4.1 Harm measures (per unit-year, absolute numbers)
- **Shortfall against target** = CTD target − notified, for years with printed targets. Negative values (notified above target) are kept.
- **Not tested for rifampicin resistance** = notified − UDST-tested.
- **Deaths during treatment and loss to follow-up**, from the outcome cohorts.
- **DR-TB harm:** missed RR-TB (expected RR-TB, if printed, minus detected) and DR-TB patients not successfully treated.
- Further steps (HIV status, TPT) only if a printed series exists across years.

### 4.2 Uncertainty
- Each proportion and count has a sampling or Poisson model. Small units are stabilised by empirical-Bayes shrinkage of rates towards the national value, as in the companion ACF study. Absolute harm is the shrunken rate × the denominator.
- Posterior simulation (10,000 draws, fixed seed) gives, for each unit, intervals for harm and the probability of being among the top-k priorities.

### 4.3 Gap closable: "where an extra unit of effort buys most"
- For each unit and step: harm averted if the unit reached a benchmark for that step. The benchmark is the 75th percentile of units, or the national target where one exists.
- Sensitivities: the median benchmark; the best decile.
- The priority matrix is (unit × step) ranked by expected harm averted, with intervals and tiers:
  - **act now:** P(top-k) ≥ 0.8;
  - **probable:** 0.5–0.8;
  - **uncertain:** 0.2–0.5;
  - **lower:** < 0.2.
- k and the thresholds are fixed in the plan.

### 4.4 Risk and trajectory
- Per unit and step, the trend of each gap over the available years, with uncertainty: a random-slope or weighted log-linear model.
- A "rising risk" flag when the slope interval lies above zero.
- The decision tier combines harm averted, certainty and trajectory, using a rule fixed in advance.

### 4.5 Reliability and validity
- **Temporal stability:** do priorities from 2018–2021 data predict the units with the largest gaps in 2022–2023 (out-of-time check)?
- **Robustness:** a specification curve over the expected-case source, the benchmark, the shrinkage choice and the year window.
- **External:** association of missed-case burden with NTPS prevalence (19–20 units). Labelled as a test of association, not validation.

### 4.6 District module
- The same functions run on a district table:
  - minimum fields: district, year, notified;
  - optional fields: target/expected, population, cascade fields.
- The module degrades gracefully:
  - with notifications only, it gives the trend, change beyond noise (Poisson, with the overdispersion-adjusted funnel used in the companion State TB Score work) and the districts whose notifications fell most;
  - with a target, it adds shortfall;
  - each cascade field adds a step.
- Demonstrated on Madhya Pradesh and Maharashtra, 2022–2024, from Lok Sabha Q802.
- The paper states plainly that a fall in notifications may mean less TB or less case-finding, and that notifications alone cannot tell the two apart.

### 4.7 Label rule
Results carry labels ("supported" / "not established"), fixed before computation, as in the companion papers.

## 5. The tool
- A Python package (standard library + numpy/scipy) with a CLI:

  ```
  tbprio state --data <dir>
  tbprio district --input <csv>
  ```

- Outputs:
  - CSV tables: harm, priority matrix, tiers, trends;
  - a self-contained HTML report with a priority matrix heat-map, funnel-type plots and a one-page summary per unit.
- An input schema with validation and clear error messages, so another State's export works.
- An example dataset.

## 6. Registration, reproducibility, honesty
- New public repository. An analysis plan is pushed before any estimate (registration event recorded, as in the companion repos), with dated deviations after.
- The plan states what had been seen: the ITR tables and State-level descriptive values from the companion studies.
- Verification:
  - an independent recompute of headline values;
  - plan-order checks;
  - number checks of the manuscript against outputs;
  - mutation-tested checks.
- Zenodo DOI at release.
- Manuscript local; never committed.

## 7. Paper and journal
- **Paper:** "where to invest" framed as programme guidance. The State results are the main application; the district module is shown as a method with a worked example. AI use is disclosed.
- **Journal:** hybrid or APC-free, chosen and verified against the journal's own guidelines at the manuscript stage. Leading candidates:
  - International Journal of Health Planning and Management (Wiley, hybrid);
  - Health Policy OPEN is excluded (APC);
  - IJTLD and IJTB are only possible once their current submissions resolve.

## 8. Constraints
- Python 3.14 with `python -I`, LF line endings; numpy/scipy allowed.
- No downloads without asking (state the file, source and size). Never bypass a CAPTCHA.
- No personal data to external services.
- Single author. Hybrid/APC-free journal.
- Pre-registration before computing.

## 9. Approaches considered
- **A. National district tool:** the author downloads ~700 districts. The most complete, but it stalls on manual collection, and per-district cascade fields are uncertain.
- **B. State tool + district notifications from parliamentary answers:** easy but partial (some States, notifications only).
- **C. Chosen by the author:** a full State tool, plus a reusable district module demonstrated on one or two States. Both levels, feasible, and usable by programmes.

## 10. Left to the builder
- The exact table inventory and column mappings per edition.
- Module layout.
- The HTML report styling (within accessibility rules).
- The trend-model implementation detail within §4.4.
- Test design.
- The choice among equivalent shrinkage estimators, documented in the plan before registration.
