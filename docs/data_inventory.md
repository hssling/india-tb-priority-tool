# Data inventory (structure only, no estimates)

Task 1, 21 Nov 2026. This file records what the sources print: annexure
numbers, pages, column headers, units covered and the printed total row. No
rate, ratio, sum or difference has been computed. Every number below is copied
from a printed total row.

## Conventions

- **Edition → data year:** ITR 2019 → 2018; ITR 2020 → 2019; ITR 2021 → 2020;
  TB Annual Report 2022 (`TBAnnaulReport2022.pdf`, cited as TBAR 2022) → 2021;
  ITR 2023 → 2022; ITR 2024 → 2023. The DS-TB and DR-TB outcome tables report
  earlier cohorts. Each cohort is named below.
- **Pages:** "PDF p." is the 1-based page of the file in
  `data/source_manifest.csv`. "printed" is the page number printed on that page.
  TBAR 2022 is laid out as two-page spreads, so one PDF page carries two printed
  pages.
- **Headers:** headers are given verbatim. Cell line breaks are shown as spaces,
  and column groups as `Group (sub, sub, sub)`. `|` separates columns. Print
  errors are kept and marked [sic].
- **Units:** "36 rows" means one row per State/UT as printed. The composition
  changes between editions:
  - **ITR 2019 and ITR 2020:** Dadra & Nagar Haveli and Daman & Diu are
    separate rows. Jammu & Kashmir has no separate Ladakh row.
  - **ITR 2021 onwards:** one merged row, "Dadra and Nagar Haveli and Daman and
    Diu", plus a separate Ladakh row.
  - Unit names were found by a text match on each table's pages, excluding
    footnotes. ITR 2021 has no text layer, so its rows were counted by eye (see
    below).
- **How the pages were read:**
  - pdfplumber 0.11.8, page by page with `page.flush_cache()`. Rotated tables
    were rebuilt from the characters, as in `tb_state_score/src/extract/pdftext.py`.
  - PyMuPDF 1.27.2.3 to locate pages and to cross-read total rows.
  - Where pdfplumber merged rotated cells, the PyMuPDF reading is given. One
    case: in the ITR 2019 Annexure 1.10 total row, pdfplumber dropped
    "618279 (29%)".
- **ITR 2021 is a scan.** All 352 pages are images with no text layer (as found
  in tb_state_score). Its tables below were read by eye from pages rendered
  at 90–110 dpi. No values were machine-read, and none should be until Task 2
  decides how 2020 is transcribed. PDF page = printed page + 22.

## Summary: steps S1–S6 by data year

| Step | 2018 (ITR 2019) | 2019 (ITR 2020) | 2020 (ITR 2021, scan) | 2021 (TBAR 2022) | 2022 (ITR 2023) | 2023 (ITR 2024) |
|---|---|---|---|---|---|---|
| S1 target + notified | **no target printed** | **no target printed** | yes, A1.2 | yes, A1.2 | yes, A1.2 | yes, A1.2 |
| S2 notified, RR-tested | yes, A1.10 | yes, A4.1 | yes, A4.2 | yes, A4.7 | yes†, A4.7 | yes†, A4.7 |
| S3 died (DS-TB cohort) | yes‡, A1.4.a (2017 cohort) | yes, A3.3 (2018) | yes, A3.3 (2019) | yes, A3.3 (2020) | yes, A3.3 (2021) | yes, A3.3 (2022) |
| S4 LTFU (DS-TB cohort) | public only‡, A1.4.a | yes, A3.3 | yes, A3.3 | yes, A3.3 | yes, A3.3 | yes, A3.3 |
| S5 DR-TB cohort, success | yes§, A1.12 | yes§, A4.8 (and A4.6) | yes§, A4.5 (and A4.9) | yes§, A4.13 | yes§, A4.13 | yes§, A4.13 |
| S6 notified, HIV status known | yes, A1.2 | yes, A2.1 | yes, A2.1 | yes, A2.1 | yes, A2.1 | yes, A2.1 |

**State targets are printed for data years 2020, 2021, 2022 and 2023 only**
(ITR 2021, TBAR 2022, ITR 2023, ITR 2024). In ITR 2019 and ITR 2020:
- no annexure has a target column;
- the word "target" appears only in partner and score text: ITR 2019 PDF pp.
  128 and 148, and ITR 2020 PDF pp. 146 and 152 (the last is a dashboard
  example with dummy values).

S1 therefore has 3 non-2020 years with targets (2021, 2022 and 2023).

**All six steps are printed for 2023.** S6 is printed for all 6 years, which
meets the "≥4 years" rule.

† **Definition change in S2.**
- **2018–2021:** RR testing is reported for all notified patients. The headers
  are "UDST Tested" and "Tested for Rifampicin Resistance^".
- **2022–2023:** it is reported only for bacteriologically confirmed patients:
  "…with valid rapid DRT result for at least Rifampicin (RS/RR)". The
  notified-patient denominator is not on the same footing across the two
  periods. This is a definitional flag for Task 2. It is not harmonised here.

‡ **ITR 2019 A1.4.a prints public and private sectors separately, with no
total columns.**
- Public: Died and Lost to follow up.
- Private: "Died" and "Others", with no LTFU column.
- No Lakshadweep row (35 rows).

§ **The DR-TB outcome cohorts differ by edition.**
- 2018: 3Q15–2Q16, Cat IV.
- 2019: 3Q16–2Q17 conventional regimen, and 2018 shorter regimen.
- 2020: whole 2017 cohort ("The data published in 2020 report was upto 2Q17").
  This overlaps the 2019 edition's cohort.
- 2021: the 2019 cohort, all regimens, excluding XDR and H-mono/poly.
- 2022: the 2020 cohort. Regimen-changed records are excluded from the
  denominator.
- 2023: the 2021 cohort, excluding pre-XDR and XDR.
- Small UTs are missing or merged in several years: see each edition.

**Population** (for the population view) is printed in each edition's
Annexure 1.1:
- ITR 2019: persons (PDF p. 167).
- ITR 2020: lakhs (PDF p. 203).
- ITR 2021: lakhs (PDF p. 209, scan).
- TBAR 2022: "Population 2021 (in lakhs)" (PDF p. 88).
- ITR 2023: "Population - 2022 (in lakhs)" (PDF p. 211).
- ITR 2024: "Population - 2023 (in lakhs)" (PDF pp. 185–186).

---

## ITR 2019 (data 2018): `data_raw/india_tb_report/India-TB-Report-2019.pdf`

Annexure contents: PDF pp. 165–166. The contents page numbers run 2 lower than
the printed pages. PDF page = printed page + 22.

**A1.1 "Presumptive TB Cases examined & TB patients notified 2018" (S1 notified only; population)**
- PDF pp. 167–168 (printed 145–146). 36 rows.
- Header: State | Population | Presumptive TB Cases examination (Number examined, Rate*) | TB patients notified$ (Public, Private, Total) | Annualised TB case notification rate (Public, Private, Total) | Paediatric TB patients notified$ | TB patients notified$ – Gender (Male, Female, Trans- gender) | TB patients notified$ – Type of disease# (New, Previ- ously …) | TB patients initiated on treatment (Public, Private, Total, Pulmo- nary @, Extrapulmo- nary@)
- No target column.
- Total row: `India | 1340092226 | 1,21,61,676 | 908 | 1613504 | 542390 | 2155894 | 120 | 40 | 160 | 133059 | 1372752 | 781466 | 1676 | 1876586 | 241460 | 1465502 | 447019 | 1912521 | 1527267 | 385254`
- Footnote: "$ TB notified cases based on diagnosing PHI."

**A1.2 "TB Comorbidities" (S6)**
- PDF pp. 169–170 (printed 147–148). 36 rows.
- Header: Total TB patients Notified (notified cases based on current PHI) | Total TB patients with known HIV status (%)# | HIV positive patients among tested* (%) | TB-HIV co- infected patients initiated on ART* | … on CPT* | (then DM and tobacco columns)
- Total row: `India | 2155894 | 1438912 (67%) | 49047 (3.4%) | 44080 | 45653 | …`

**A1.4.a "Treatment outcome of TB patients notified in 2017 (Both Public and Private sector)" (S3, S4; 2017 cohort)**
- PDF pp. 172–173 (printed 150–151). 35 rows (no Lakshadweep).
- Header:
  - State
  - Public Sector (TB patients Notified* | Microbiologically Confirmed TB Patients Notified | Cured | Cure rate $ (%) | Treatment Success | Success rate# (%) | Died | Death Rate (%) | Failure | Failure Rate (%) | Lost to follow up | % Lost to follow up (%) | Regimen Change | % Regimen Change | Not evaluated)
  - Private Sector (TB patients Notified* | Treatment Success | Success rate (%) | Died | Death Rate (%) | Others | Not evaluated)
- Total row: `India | 1364562 | 874241 | 550772 | 63 | 1079167 | 79 | 54184 | 4.0 | 13022 | 1.0 | 58222 | 4.3 | 13059 | 1.0 | 146908 | 391708 | 135400 | 35 | 2093 | 1 | 27986 | 226229`
- Footnote: "* notified cases based on current PHI-2017".

**A1.10 "PMDT – Case Finding" (S2)**
- PDF pp. 182–183 (printed 160–161). 36 rows.
- Header: State | No. of DR-TB Centres (Nodal + District) established | Total presumptive DR TB tested | Total TB patients Notified* | UDST Tested (%) | No. of MDR/ RR patient diagnosed$ | Total put on treatment# | No. of patient initiated on Shorter MDR-TB regimen | No. of H mono/ poly notified | No. of H mono/ poly patient initiated on treatment# | No. of patient eligible for DST guided treatment regimen
- Total row (PyMuPDF): `Grand Total | 643 | 1047441 | 2155894 | 618279 (29%) | 58347 | 46569 | 16488 | 8809 | 6454 | 11209`
- Footnotes: "* TB patients notified based on current PHI."; "UDST data - Source of data is Nikshay".

**A1.12 "PMDT – Treatment Outcome of MDR/ RR TB patients" (S5; Cat IV, 3Q15–2Q16)**
- PDF pp. 186–187 (printed 164–165). 33 rows: no DNH, D&D or Lakshadweep, and
  no Ladakh row.
- Header: State | No. of MDR/ RR-TB patients initiated on Cat IV during 3Q15 to 2Q16 (c) | Out of c, No. reported as Cured | Out of c, No. reported as Treatment Completed | Out of c, Success Rate | Out of c, No. (%) who died | Out of c, No. (%) who lost to follow up | Out of c, No. (%) who failed treatment | Out of c, No. (%) who were declared with outcome like Switch to XDR regimen, stopped due to ADR, Transferred out etc.,
- No success count is printed; only cured, completed and the rate.
- Total row: `India | 30183 | 9004 | 5191 | 47% | 5934 | 20% | 5761 | 19% | 595 | 2% | 3698 | 12%`
- Footnote: "* Data from Daman-Diu & Dadra Nagar Haveli is included in Gujarat: Lakshadweep is included in Kerala for 6/12 months interim and treatment outcome report."

## ITR 2020 (data 2019): `data_raw/india_tb_report/ITR2020.pdf`

Annexure contents: PDF pp. 201–202. PDF page = printed page + 24. All tables
have 36 rows unless noted.

**A1.2 "TB Cases & Paediatric cases notification" (S1 notified only)**
- PDF p. 204 (printed 180).
- Header: State | TB patients notified (Public, Private, Total) | TB case notification rate (Public, Private, Total) | Paediatric TB patients notified (Public, Private, Total)
- No target column.
- Total row: `India | 1725920 | 678895 | 2404815 | 127 | 50 | 177 | 87869 | 63417 | 151286`
- Footnote: "TB Patients Notification is based on notification by diagnosing PHI."

**A1.4 "Patient Transfer Status"**
- PDF p. 206 (printed 182).
- Header: State | Patients notified | Transfer Out | Transfer In | Net TB Patients Notified (Total, Public, Private)
- Total row: `India | 2404815 | 55264 | 55264 | 2404815 | 1777168 | 627647`

**A2.1 "TB – HIV" (S6)**
- PDF p. 211 (printed 187).
- Header: State | TB patients with known HIV status (%) (Public, Private, Total) | TB-HIV co-infected patients (Diagnosed, Put on ART*, Put on CPT*)
- Total row: `India | 1588742 (89%) | 347191 (55%) | 1935933 (81%) | 46741 (2%) | 44027 (94%) | 45021 (96%)`

**A3.3 "Treatment outcome of TB patients notified in 2018 (Total)" (S3, S4; 2018 cohort)**
- PDF pp. 224–225 (printed 200–201).
- Header: State | TB patients Notified | Micro Conf TB | Cure Rate | Success Rate | Death Rate | Treatment Failure Rate | % Lost to follow up | % Reg- imen Change | % Not* evaluated
- Total row: `India | 2049517 | 961203 | 643221 (67%) | 1665016 (81%) | 73382 (4%) | 13644 (1%) | 81042 (4%) | 16616 (1%) | 199817 (10%)`
- Footnote: "*Not evaluated - (includes Pre-treatment loss of follow up)".

**A4.1 "Case Finding – UDST testing & MDR patients management" (S2)**
- PDF pp. 234–235 (printed 210–211).
- Header: State | DR-TB Centres | TB Patients notified (Public, Private, Total) | UDST Tested (Public, Private, Total) | MDR/RR patient diagnosed (Public, Pri- vate, Total) | MDR/ RR put on treatment (%) | MDR/ RR put on Shorter MDR Regi- men | MDR/RR put on All Oral Regi- men
- Total row: `India | 703 | 1777168 | 627647 | 2404815 | 1208318 (68%) | 174782 (28%) | 1383100 (58%) | 59945 | 6310 | 66255 | 56569 (85%) | 40397 (71%) | 1738 (3%)`

**A4.8 "Treatment Outcome of MDR/ RR – TB patients put on Conventional MDR TB regimen during the period 3Q16 to 2Q17" (S5)**
- PDF pp. 248–249 (printed 224–225). 33 rows: no DNH, D&D or Lakshadweep.
- Header: State | MDR/RR-TB patients put on Conventional MDR TB regimen | Cure Rate (%) | Success Rate (%) | Death Rate (%) | Failure (%) | Loss to follow up (%) | Pts who were declared with outcome like Switch to XDR regimen, stopped due to ADR, Transferred out etc., (%)
- Total row: `India | 34621 | 9494 (27%) | 16668 (48%) | 6406 (19%) | 693 (2%) | 6430 (19%) | 4424 (13%)`
- Footnote: "Data from Daman-Diu & Dadra Nagar Haveli is included in Gujarat: Lakshadweep is included in Kerala for treatment outcome report."

**A4.6 "Treatment Outcome of MDR/ RR TB Patients initiated on Shorter regimen during 2018" (S5, second regimen)**
- PDF pp. 244–245 (printed 220–221).
- Header: State | Registered | Cure Rate (%) | Success Rate (%) | Death Rate (%) | Failure (%) | Loss to follow up (%) | Regimen Change (%) | Not Evaluated (%)
- Total row: `India | 16311 | 6444 (40%) | 9728 (60%) | 1793 (11%) | 395 (2%) | 2157 (13%) | 1957 (12%) | 286 (2%)`

## ITR 2021 (data 2020): `data_raw/india_tb_report/ITR2021.pdf` (scan, read by eye)

Annexure contents: PDF pp. 207–208. PDF page = printed page + 22.

**A1.2 "TB Case Notification rate and achievement against target cases" (S1)**
- PDF pp. 211–213 (printed 189–191).
- 36 rows counted by eye (15 + 15 + 6), with the merged DNH and DD row and a Ladakh row.
- Header: State | Target TB patients expected to be notified (Public, Private, Total) | TB patients notified (Public, Private, Total) | TB case notification rate (Public, Private, Total) | Achievement in TB Case Notification against target cases (Public, Private, Total)
- Total row: `India | 1923120 | 1075910 | 2999030 | 1249088 (69%) | 556582 (31%) | 1805670 | 91 | 40 | 131 | 1249088 (65%) | 556582 (52%) | 1805670 (60%)`
- Footnotes: "TB Patients Notification is based on notification by diagnosing PHI."; "Data Source: Nikshay – Data extracted as on 12th February 2021".

**A1.4 "Patient Transfer Status & Treatment Initiation Status"**
- PDF pp. 217–218 (printed 195–196).
- Header: State | TB Patients notified | Trans- ferred Out | Trans- ferred In | Net TB Patients Notified (Public, Private, Total) | Net TB Patients initiated on treatment (Public, Private, Total)
- Total row: `India | 1805670 | 35986 | 35986 | 1325765 | 479905 | 1805670 | 1247584 (94%) | 463339 (97%) | 1710923 (95%)`

**A2.1 "TB – HIV" (S6)**
- PDF pp. 227–228 (printed 205–206).
- Header: State | TB patients with known HIV status (%) (Public, Private, Total) | TB-HIV co-infected patients (Diagnosed, Put on ART*, Put on CPT*)
- Total row: `India | 1250438 (94%) | 407864 (85%) | 1658302 (92%) | 33884 | 31490 (93%) | 32027 (95%)`

**A3.3 "Treatment outcome of TB patients notified in 2019 (Total)" (S3, S4; 2019 cohort)**
- PDF pp. 254–256 (printed 232–234).
- Header: State | TB patients Notified | Micro Conf TB | Cure Rate | Success Rate | Death Rate | % Lost to follow up | Treatment Failure Rate | % Regimen Change | % Not evaluated
- Total row: `India | 2328338 | 1097843 | 672000 (61%) | 1905920 (82%) | 89823 (3.9%) | 81306 (3.5%) | 13781 (0.6%) | 27169 (1.2%) | 210339 (9.0%)`

**A4.2 "Case Finding – UDST testing & MDR patients management" (S2)**
- PDF pp. 286–288 (printed 264–266).
- Header: State | UDST Tested (Public, Private, Total) | MDR/RR patient diagnosed (Public, Private, Total) | MDR/ RR put on treatment (%) | MDR/ RR put on Shorter MDR Regimen | MDR/RR put on All Oral Regimen
- No notified column in this table.
- Total row: `India | 985660 (74%) | 230783 (48%) | 1216443 (67%) | 43618 | 6061 | 49679 | 42505 (86%) | 30605 (72%) | 8434 (20%)`
- Footnote: "Data Source: UDST – Nikshay: Case Finding on diagnosis and treatment initiation – State Submitted Data".

**A4.5 "Treatment Outcome of MDR/ RR TB Patients initiated on treatment during 2017" (S5)**
- PDF pp. 293–294 (printed 271–272).
- Header: State | Registered | Cure Rate | Success Rate | Death Rate | Loss to follow up (%) | Failure (%) | Regimen Change (%) | Not Evaluated (%)
- Total row: `India | 36043 | 9860 (27%) | 17699 (49%) | 6422 (18%) | 6697 (19%) | 776 (2%) | 2635 (7%) | 1814 (5%)`
- Footnotes: "Not evaluated includes transfer out and People still on treatment…"; "The data published in 2020 report was upto 2Q17. The current report includes the total 2017 cohort data."; "Data Source: – State Submitted Data".

**A4.9 "Treatment Outcome of MDR TB patients initiated on conventional regimen as well as MDR TB patients with additional resistance initiated on any regimen during 2018" (S5, alternative)**
- PDF pp. 301–302 (printed 279–280).
- Header: State | Registered | Cure Rate | Success Rate | Death Rate | Loss to follow up (%) | Failure (%) | Regimen Change (%) | Not Evaluated (%)
- Total row: `India | 31939 | 7218 (23%) | 16478 (52%) | 4823 (15%) | 4748 (15%) | 524 (2%) | 3140 (10%) | 2226 (7%)`

Rows were counted only for A1.2. The other ITR 2021 tables were read on their
last page only, for the header and the total row.

## TB Annual Report 2022 (data 2021): `data_raw/india_tb_report/TBAnnaulReport2022.pdf`

Annexure contents: PDF pp. 86–87. Each PDF page is a spread of two printed
pages. All tables have 36 rows unless noted.

**A1.2 "TB Case Notification" (S1)**
- PDF p. 89 (printed 153–154).
- Header: State/UT | Target TB patients expected to be notified (Public, Private, Total) | TB patients notified (Achievement against target %) (Public, Private, Total) | TB case notification rate (Public, Private, Total)
- Total row: `INDIA | 1952750 | 1041580 | 2994330 | 1446701 (74%) | 689129 (66%) | 2135830 (71%) | 104 | 49 | 153`
- Footnote: "TB Patients Notification is based on notification by diagnosing PHI."

**A1.4 "Patient Transfer Status & Treatment Initiation Status"**
- PDF p. 91 (printed 157). The same spread holds A1.5, the paediatric table.
- Header: State | Patients Notified | Transfer Out | Transfer In | Net TB Patients Notified | Net TB Patients Initiated on Treatment
- Total row: `INDIA | 2135830 | 55224 | 55224 | 2135830 | 2030509 (95%)`

**A2.1 "TB - HIV" (S6)**
- PDF p. 94 (printed 163).
- Header: State | TB patients with known HIV status (%) (Public, Private, Total) | TB-HIV co-infected patients (Diagnosed, Put on ART*, Put on CPT*)
- Total row: `INDIA | 1509432 (96%) | 511862 (92%) | 2021294 (95%) | 34877 | 32577 (93%) | 33085 (95%)`

**A3.3 "Treatment outcome of TB patients notified in 2020 (Total)" (S3, S4; 2020 cohort)**
- PDF p. 102 (printed 179–180).
- Header: State | TB patients Notified | Bacteriologically Confirmed | Cure Rate | Success Rate | Death Rate | % Lost to follow up | Treatment Failure Rate | % Regimen Change | % Not evaluated
- Total row: `INDIA | 1751437 | 784781 | 484079 (62%) | 1451867 (83%) | 76002 (4.3%) | 51138 (2.9%) | 9202 (0.5%) | 26669 (1.5%) | 43841 (2.5%)`

**A4.7 "MDR/RR TB DIAGNOSED IN 2021" (S2)**
- PDF p. 122 (printed 219–220).
- Header: State | Tested for Rifampicin Resistance^ (Public, Private, Total) | MDR/RR patient diagnosed (2021)# (Public Sector, Private Sector, Total) | MDR/ RR Initiated on treatment (%)# | MDR/ RR initiated on Shorter MDR-TB (Inj containing) regimen | MDR/ RR initiated on Shorter MDR/RR-TB (oral) regimen | Total No. of MDR/RR patients put on longer oral M/XDR-TB regimen
- No notified column in this table.
- Total row: `India | 952948 (60.4%) | 220189 (39.4%) | 1173137 (54.9%) | 41981 | 6251 | 48232 | 43380 (90%) | 25235 (58%) | 1939 (4%) | 14156 (33%)`
- The "^" footnote text was not found in the page's text layer.

**A4.13 "Treatment Outcome of MDR/ RR TB patients with/ without additional resistance - 2019 cohort (excluding XDR-TB and H-mono/poly DR-TB)" (S5)**
- PDF p. 128 (printed 231–232). 34 rows: no Ladakh or Lakshadweep.
- Header: State | No. of MDR/RR-TB patients initiated on treatment during 2019 (includes all regimen) (c) | Cure Rate | Success Rate | Death Rate | Failure (%) | Loss to follow up (%) | Regimen hanged (%) [sic] | Not evaluated (%) | Still on treatment (%)
- Total row: `India | 60873 | 16212 (27%) | 34535 (57%) | 7988 (13%) | 1208 (2%) | 8028 (13%) | 8041 (13%) | 289 (0%) | 784 (1%)`
- Also printed: A4.10 "shorter MDR-TB regimen (Inj containing) during 2020" (PDF p. 125; 34 rows) and A4.12 "longer oral M/XDR-TB regimen during 2019" (PDF p. 127; only States with patients).

## ITR 2023 (data 2022): `data_raw/india_tb_report/ITR2023.pdf`

Annexure contents: PDF pp. 207–209. PDF page = printed page + 30. All tables
have 36 rows unless noted.

**A1.2 "TB CASE NOTIFICATION" (S1)**
- PDF pp. 213–214 (printed 183–184).
- Header: State/UT | Target TB patients expected to be notified (Public, Private, Total) | TB patients notified, n (% achievement against target) (Public, Private, Total) | TB case notification rate (per 1,00,000) (Public, Private, Total)
- Total row: `India | 1828260 | 951740 | 2780000 | 1688427 (92.4) | 733694 (77.1) | 2422121 (87.1) | 120 | 52.1 | 172.1`

**A1.6 "Gender disaggregated data on total TB notifications, Paediatric TB notification and treatment initiation"**
- PDF pp. 221–222 (printed 191–192).
- The edition has no patient-transfer (net notified) annexure.
- Header: State | TB Cases Notified (Male, Female, Trans Gender) | Paediatric TB Cases Notified, n (% of total notified) (Male, Female, Trans Gender) | Total TB Cases initiated on treatment, n (% of total notified) (Male, Female, Trans Gender)
- Total row: `India | 1472190 | 948455 | 1021 | 67150 (4.6) | 68470 (7.2) | 57 (5.6) | 1402503 (95.3) | 909348 (95.9) | 964 (94.4)`

**A2.1 "SCREENING FOR HIV IN NOTIFIED TB" (S6)**
- PDF p. 225 (printed 195).
- Header: State | TB patients with known HIV status, n (%) (Public, Private, Total)
- Total row: `India | 1794785 (96.8) | 531460 (93.6) | 2326245 (96.1)`

**A3.3 "TREATMENT OUTCOME OF TB PATIENTS NOTIFIED IN 2021 (TOTAL)" (S3, S4; 2021 cohort)**
- PDF pp. 251–252 (printed 221–222).
- Header: State | TB patients Notified | Cure Rate, n (%) | Success Rate, n (%) | Death Rate, n (%) | Lost to follow up, n (%) | Treatment Failure Rate, n (%) | Regimen Change, n (%) | Not evaluated, n (%)
- Total row: `India | 2082444 | 579038 (27.8) | 1779602 (85.5) | 88060 (4.2) | 54127 (2.6) | 11308 (0.5) | 30147 (1.4) | 21155 (1)`

**A4.7 "PMDT CASE FINDING IN 2022 - I" (S2†)**
- PDF pp. 281–282 (printed 251–252).
- Header: State/UT | Bacteriologically confirmed among notified TB patients, n (%) (Private sector, Public sector, Total TB) | Bacteriologically confirmed TB patients with valid rapid DRT result for at least Rifampicin (RS/RR), n (%) (Private sector, Public sector, Total TB) | Rifampicin resistant TB patients diagnosed (MDR/RR-TB), n (%) (Private sector, Public sector, Total TB, Pediatric MDR/ RR-TB patients (<15 years)) | Rifampicin resistance TB patients with a DST result available for at least fluoroquinolone, n (%) (Private sector, Public sector, Total TB)
- Note the column order: Private before Public.
- Total row, total columns only: bacteriologically confirmed `1232149 (51)`; with valid rapid DRT result `938217 (76)`; MDR/RR-TB `63801 (7)`.
- Footnote: "*Patients as per current facility".

**A4.13 "TREATMENT OUTCOME OF MDR/RR-TB PATIENTS INITIATED ON TREATMENT IN 2020" (S5)**
- PDF pp. 293–294 (printed 263–264). 35 rows (no Lakshadweep).
- Header: State/UT | Total MDR/ RR-TB initiated | Cured | Treatment success | Died | Lost to follow up | Treatment failure | Not evaluated
- Total row: `INDIA | 41922 | 12373 (30) | 28452 (68) | 5628 (13) | 4506 (11) | 834 (2) | 2502 (6)`
- Footnote: records with "treatment regimen changed" are excluded from the denominator.

## ITR 2024 (data 2023): `data_raw/india_tb_report/ITR2024.pdf`

Annexure contents: PDF pp. 182–183. PDF page = printed page + 31. All tables
have 36 rows unless noted.

**A1.2 "TB case notification" (S1)**
- PDF pp. 187–188 (printed 156–157).
- Header: States/UTs | Target of TB patients expected to be notified (Public, Private, Total) | TB patients notified, n(% of achievement against target) (Public, Private, Total) | TB case notification rate (per lakh population) (Public, Private, Total)
- Total row: `INDIA | 1825705 | 937127 | 2762832 | 1707878 (93.5) | 844379 (90.1) | 2552257 (92.4) | 119.7 | 59.2 | 178.8`
- Footnote: "TB patient's notification is based on notification by diagnosing PHI."

**A1.4 "Patient transfer status and treatment initiation status"**
- PDF pp. 191–192 (printed 160–161).
- Header: States/UTs | Patients notified (Based on diagnosing PHI); public–private disaggregated (Public, Private, Total) | Net TB patients* notified (Based on current PHI); public–private disaggregated (Public, Private, Total) | Patients initiated on treatment, n(% out of total TB) (Public, Private, Total)
- Total row: `INDIA | 1707878 (66.9) | 844379 (33.1) | 2552257 | 1889689 (74) | 662568 (26) | 2552257 | 1799399 (95.2) | 638550 (96.4) | 2437949 (95.5)`

**A2.1 "TB patients with known HIV status" (S6)**
- PDF p. 199 (printed 168).
- Header: States/UTs | TB patients with known HIV status, n (%) (Public, Private, Total)
- Total row: `INDIA | 1804178 (95%) | 615913 (93%) | 2420091 (95%)`

**A3.3 "Treatment outcome of TB patients notified in 2022 (total)" (S3, S4; 2022 cohort)**
- PDF pp. 222–223 (printed 191–192).
- Header: States/UTs | TB patients notified | Cure rate, n(%) | Success rate, n(%) | Death rate, n(%) | Lost to follow up, n(%) | Treatment failure rate, n(%) | Regimen change, n(%) | Not evaluated, n(%)
- Total row: `INDIA | 2360036 | 681021 (28.9) | 2066386 (87.6) | 85231 (3.6) | 48604 (2.1) | 11691 (0.5) | 32937 (1.4) | 9221 (0.4)`
- Footnote: "Note: Numerator is outcomes in DSTB patients initiated on treatment, and Denominator is total notified DSTB cases by current facility."

**A4.7 "PMDT case finding in 2023 - I" (S2†)**
- PDF pp. 260–262 (printed 229–231).
- Header: States/UTs | Total TB cases notified (2023) (Public sector, Private sector, Total) | No. of bacteriological confirmed TB cases among notified (…) | No. of bacteriologically confirmed TB cases with valid rapid DRT result for at least rifampicin (RS/RR) (…) | No. of rifampicin resistant TB cases diagnosed (MDR/RR-TB) (…)
- Total row: `INDIA | 1853274 | 656262 | 2509536 | 1062870 (57%) | 182063 (28%) | 1244933 (50%) | 881425 (83%) | 142499 (78%) | 1023924 (82%) | 59486 | 4443 | 63929`
- Footnote: "*Based on case concept, no. of cases based on current facility in Ni-kshay".
- This table's printed notified total differs from A1.2's printed total, which is
  on a diagnosing-PHI basis. Both are printed values. Which one is the S2
  denominator is a Task 2 decision.

**A4.13 "Treatment outcome of MDR/RR-TB cases initiated on treatment in 2021 (excluding Pre-XDR-TB and XDR-TB)" (S5)**
- PDF pp. 273–274 (printed 242–243). 36 rows. The Lakshadweep row prints "#N/A" in every cell.
- Header: States/UTs | Total MDR/RR-TB initiated on treatment | Cured | Treatment success | Died | Lost to follow-up | Treatment failure | Not evaluated
- Total row: `INDIA | 33555 | 10348 (31%) | 24793 (74%) | 4086 (12%) | 2892 (9%) | 1346 (4%) | 438 (1%)`

---

## District level

### What the India TB Reports print at district level (page scans)

**ITR 2019 DOES print a national district table.** This finding differs from the
earlier controller scan.
- **Table:** Annexure 1.13 "District Wise Indicators", PDF pp. 188–220
  (printed 166–198; the contents list it at p. 164).
- **Data:** each row is State | District, for data year 2018.
- **Header:** State | District | Total TB patients Notified$ | TB patients notified from Public sector | TB patients notified from Private sector | Paediatric TB patients notified | New TB patients notified | Previously treated TB patients notified | PMDT cases noti- fied* | TB patients initiated on treat- ment-To- tal | TB patients initiated on treat- ment - Public Sector | TB patients initiated on treat- ment - Private Sector | Treatment success rate of TB noti- fied patients (Public sector) 2017 (N&%) | Treatment success rate of TB notified patients (Private sector) 2017 (N&%)
- **Rows:** about 761 district rows (machine count of rows with ≥9 numeric
  cells; to be verified at extraction).
  - Madhya Pradesh: 51 districts, including Agar Malwa … Vidisha. Niwari is
    absent.
  - Maharashtra: 79 rows, including municipal corporations and the Mumbai
    wards. The first-line name "Nanded" occurs twice: probably Nanded and the
    wrapped "Nanded Waghala MC".
  - No State subtotal rows were found.
- **Total row:** `India | 2155894 | 1613504 | 542390 | 133059 | 1876586 | 241460 | 37848 | 1912521 | 1465502 | 447019 | 1079167 (79%) | 135400 (35%)`
- **Footnotes:**
  - "$ - TB notified cases based on diagnosing PHI includes new TB, PT TB & PMDT Patients"
  - "*- PMDT cases initiated on treatment as per Nikshay"
  - "Blank boxes in the treatment outcome column of the Private sector indicates NO private sector notified patients in the district during the year 2017."
- **Use:** this is a second district source, and gives a 2018 point for the
  Madhya Pradesh and Maharashtra districts in AU802. Several district names
  changed between 2018 and 2024 (e.g. Hoshangabad, Ahmednagar, Aurangabad,
  Osmanabad), so a crosswalk is needed.
- The ITR 2019 State tables at PDF pp. 178–183 (A1.7 ACF, A1.8–A1.10) are
  State-level only. This is consistent with the controller's scan of that
  range.

**ITR 2020: no district data table.**
- The annexure list (PDF pp. 201–202) has no district table.
- A text search of all 292 pages for "district-wise", "district level" and
  "district indicators" finds only:
  - narrative text;
  - A10.6 "District level - Programme Staffing Status in 2019" (PDF p. 279),
    which has State rows;
  - a dummy-value district dashboard example (PDF p. 152).

**ITR 2021 (scan): no district data table in the annexure contents** (PDF pp.
207–208).
- Only A10.6a/b "District level - Programme Staffing Status in 2020".
- Chapter 7 (PDF p. 88) ranks top districts only (tb_state_score finding).
- The scan has no text layer, so it could not be text-searched.

**TBAR 2022, ITR 2023, ITR 2024: no district data tables.** The annexure lists
and a text search show only "District level – program staffing status"
(A8.6).

### Lok Sabha Unstarred Question 802, 7 Feb 2025: `data_raw/pq/AU802_LlE1Wb.docx`

- SHA-256 `673f79000b8c6da71fea01ad57ff0e3437e8eb9236166a2fe041e2bba3fe7405`,
  54,910 bytes.
- **Question:** "RISING OF CASES OF TUBERCULOSIS". Part (b) asks for "the number
  of TB cases reported in the States of Madhya Pradesh and Maharashtra during
  last three years, year-wise and district-wise".
- **Tables:** 2 Word tables, each 9 columns: two districts per row, separated
  by a blank column. Header row: `District | 2022 | 2023 | 2024 | | District | 2022 | 2023 | 2024`.
- **Table 1, Annexure-I/A:** "District-wise TB case notification in Madhya
  Pradesh for 2022-2024"; 40 rows.
  - 53 district entries, 52 distinct names: **"Vidisha" appears twice with
    identical values.**
  - The 52 names are the pre-2023 districts: Agar Malwa … Vidisha, with
    Hoshangabad and Niwari. The three districts created in 2023 (Maihar,
    Mauganj, Pandhurna) are not listed.
  - Paragraph after the table: "Data Source: Ni-kshay".
- **Table 2, Annexure-I/B:** "District-wise TB case notification in
  Maharashtra"; 43 rows.
  - 80 district entries, 80 distinct names: 24 "Mumbai_…" wards and 22
    "… Municipal Corporation" units.
  - Last row: "Data Source: Ni-kshay Portal / Under National TB Elimination
    Programme for operational purposes 80 districts have been created in
    Maharashtra and report in Ni-kshay portal".
- No total row in either table. No blank or non-numeric value cells.
- **Units per State:** Madhya Pradesh 52 distinct (53 entries); Maharashtra 80.

### Excluded: `data_raw/pq/AU1891_qm5WaQ.docx`

- Lok Sabha Unstarred Q. 1891 (Karnataka), 2 Aug 2024.
- SHA-256 `a109f02f6b0465e61ccf7ef63d412265418194fe630460b056998714aea972bc`.
- **UNUSABLE:** it has the annexure heading but no table. It is recorded in the
  manifest and not used.

## Not inventoried here

`data_raw/icmr_ntps/NTPS_2019_21_report.pdf` is copied and digest-verified. Its
State and State-group estimates were extracted in tb_state_score (19–20 units)
and are reviewed in Task 3.
