# Mutation record

<!-- Adapted from hssling/india-tb-acf-campaign (MIT), verification/MUTATIONS.md; modified: this repository's checks and mutations -->

Each check was shown to fail on a deliberate break (analysis plan §10.3). All breaks
were made in a scratch clone (`git clone <repo> <scratch>/mut`), never in this
repository or its history; the clone was restored (`git checkout -- .` and
`git reset --hard` to the cloned commit) between runs. Run on 21 November 2026
against commit c2625a1. The clone has no `data_raw/`, so the parts of
check_extraction_totals that re-extract from the source documents print SKIPPED there;
none of the other checks reads `data_raw/`.

| # | Check | Break | Result |
|---|-------|-------|--------|
| 1 | check_outputs | headline value: `headline.csv` H1 value 0.5629... to 0.5729... | caught (FAIL, exit 1) |
| 2 | check_plan_order | `docs/analysis_plan.md` §6.4 "k = 5 (main)" to "k = 6 (main)", above §12; first uncommitted, then committed | caught both times (FAIL, exit 1) |
| 3 | check_outputs | label flipped: `headline.csv` H2 "not established" to "supported" | caught (FAIL, exit 1) |
| 4 | check_outputs | one rising flag: `state_priority.csv` Bihar S3 `rising` True to False (tier left "watch: rising") | caught (FAIL, exit 1) |
| 5 | check_outputs, check_extraction_totals | one extracted cell: `state_panel.csv` Bihar S3 2023 numerator + 1 | caught by both (FAIL, exit 1) |
| 6 | check_extraction_totals | one extracted cell: `state_cells.csv` first Bihar value (ITR 2019 A1.2 notified) + 1 | caught (FAIL, exit 1) |
| 7 | check_outputs (a) | P(top-5) of Kerala S3 set to 0.05 in both `state_priority.csv` and the summary, so the source-row tie holds | caught by the standard-library draws alone (FAIL, exit 1) |
| 8 | check_deviations | " (post hoc)" appended to the H1 row of `headline.csv` | caught (FAIL, exit 1) |
| 9 | check_deviations | a README line "A further deviation was made in data year 2021." | caught (FAIL, exit 1) |
| 10 | check_rerun | one byte edited in `report_state.html` | caught (FAIL, exit 1) |
| 11 | check_all | mutation 1, whole suite | FAIL: pytest, check_outputs, check_rerun (exit 1) |

## 1. Headline value

```
sed -i 's/^H1,0\.5629141158270872,/H1,0.5729141158270872,/' outputs/headline.csv
python -I verification/check_outputs.py
```

```
FAIL: (b) headline H1: printed 0.5729141158270872 but recomputed 0.5629141158270872
FAIL: (f) headline H1 value: printed 0.5729141158270872 but the main row of spec_curve.csv has 0.5629141158270872
exit 1
```

## 2. Plan edited above §12

```
sed -i 's/^- k = 5 (main); sensitivities k = 3 and k = 8\./- k = 6 (main); sensitivities k = 3 and k = 8./' docs/analysis_plan.md
python -I verification/check_plan_order.py
git commit -am "mutation: edit above section 12"
python -I verification/check_plan_order.py
```

```
FAIL: the working-tree docs/analysis_plan.md above section 12 differs from its content at the registration commit bd3572e (an uncommitted edit)
exit 1
FAIL: commit a09f557: docs/analysis_plan.md above section 12 differs from its content at the registration commit bd3572e
exit 1
```

The uncommitted case is caught since this task added assertion 6 (the working tree) to
check_plan_order; before it, only committed edits were caught.

## 3. Label flipped

```
sed -i 's/^\(H2,.*\),not established,/\1,supported,/' outputs/headline.csv
python -I verification/check_outputs.py
```

```
FAIL: (d) headline H2 label: printed 'supported' but plan 8.6 gives 'not established' (12/12 entries agree; interval [-0.14561559756087536, 0.6816492596075885])
exit 1
```

The H2 interval is recomputed (Fieller), so editing the interval and the label together
in `headline.csv` is also caught (`test_coherent_interval_and_label_edit_fails`).

## 4. One rising flag

```
sed -i 's/^\(Bihar,S3,2023,.*,watch: rising,\)True,/\1False,/' outputs/state_priority.csv
python -I verification/check_outputs.py
```

```
FAIL: (e) state_priority Bihar S3 rising: printed False but the trend gives True
exit 1
```

## 5. Extracted panel cell

```
# Bihar,2023,S3: numerator + 1
python -I verification/check_outputs.py
python -I verification/check_extraction_totals.py
```

```
FAIL: (a) S3 2023 prior alpha: printed 3.7415123541650726 but recomputed 3.7416771310542702
FAIL: (a) S3 2023 prior beta: printed 99.86050862733605 but recomputed 99.8636909192648
FAIL: (a) S3 2023 Bihar rate: printed 0.03159606338443174 but recomputed 0.03160218494777351
... (every S3 posterior mean and the benchmark; the S3 trend of every unit and phi_S3)
FAIL: (e) state_trend Bihar S3 slope: printed 0.10309708039865298 but recomputed 0.1031276388495131
exit 1

OK: printed totals (state_cells.csv)
FAIL: state_panel.csv differs from its rebuild from state_cells.csv
exit 1
```

## 6. Extracted table cell

```
# data/extracted/state_cells.csv, first Bihar row (ITR 2019 A1.2 notified): value 106313 to 106314
python -I verification/check_extraction_totals.py
```

```
FAIL: ITR2019_A1.2 notified: State sum 2155895 vs printed 2155894 (difference 1) is not recorded
FAIL: state_panel.csv differs from its rebuild from state_cells.csv
exit 1
```

## 7. P(top-5) edited consistently in two files

```
# Kerala S3 2023: p_top5 0.0 to 0.05 in state_priority.csv and in the matching
# state_harm_draws_summary.csv row (main, p75, on); the tier stays "watch: rising"
python -I verification/check_outputs.py
```

```
FAIL: (a) S3 2023 Kerala P(top-5): printed 0.05 but standard-library draws give 0.0000 (|d| > 0.02)
exit 1
```

Only the independent draws own this failure: the source-row tie (f) and the tier rule (e)
still hold.

## 8. Unlogged post hoc label

```
sed -i '2s/$/ (post hoc)/' outputs/headline.csv
python -I verification/check_deviations.py
```

```
FAIL: outputs/headline.csv line 2: labelled 'post hoc' but names no dated plan 12 entry that carries that label
exit 1
```

## 9. Unlogged deviation in the README

```
printf 'A further deviation was made in data year 2021.\n' >> README.md
python -I verification/check_deviations.py
```

```
FAIL: README.md line 272: labelled 'deviation' but names no dated plan 12 entry that carries that label
exit 1
```

## 10. Report byte edited

```
sed -i 's/Priority matrix/Priority  matrix/' outputs/report_state.html
python -I verification/check_rerun.py
```

```
FAIL: outputs/report_state.html differs from the rerun (tbprio state)
exit 1
```

Since this run the message names the rerun folder as is: `(tbprio_state)`.

## 11. Whole suite with mutation 1

```
python -I verification/check_all.py
```

```
[FAIL] pytest -q
    FAILED tests/test_validate.py::test_run_validate_outputs_byte_identical - Ass...
    FAILED tests/test_verification.py::test_check_outputs_passes_on_the_committed_outputs
    FAILED tests/test_verification.py::test_p_top5_edited_in_both_files_fails_the_independent_draws
    3 failed, 123 passed, 2 skipped in 139.03s (0:02:19)
[PASS] check_plan_order: OK: ...
[PASS] check_deviations: OK: ...
[FAIL] check_outputs
    FAIL: (b) headline H1: printed 0.5729141158270872 but recomputed 0.5629141158270872
    FAIL: (f) headline H1 value: printed 0.5729141158270872 but the main row of spec_curve.csv has 0.5629141158270872
[FAIL] check_rerun (byte-for-byte rerun of outputs/)
    FAIL: outputs/headline.csv differs from the rerun (run validate)
[SKIP] check_manuscript_numbers: SKIPPED: manuscript/manuscript.md does not exist
[SKIP] check_docx_tie: SKIPPED: manuscript/manuscript.md does not exist

3/6 checks passed (2 skipped)
exit 1
```

(The check_extraction_totals line, PASS with its PDF parts skipped in the clone, is
omitted above.)

## Fixed in the tests

The same breaks, on temporary copies of `outputs/`, `data/extracted/`, the plan and the
README (or a temporary clone for the plan), are fixed in `tests/test_verification.py`, which
runs in the pytest step of check_all:

- check_outputs: `test_mutated_headline_value_fails`,
  `test_mutated_descriptive_headline_row_fails`, `test_flipped_label_fails`,
  `test_coherent_interval_and_label_edit_fails`, `test_spec_curve_entry_sign_flip_fails`,
  `test_altered_rising_flag_in_priority_fails`, `test_altered_rising_flag_in_trend_fails`,
  `test_tier_inconsistent_with_p_and_rising_fails`,
  `test_changed_extracted_panel_cell_fails`,
  `test_p_top5_edited_in_both_files_fails_the_independent_draws`,
  `test_check_outputs_main_exits_1_on_a_mutation`; and
  `test_check_outputs_is_standard_library_only` (no numpy, scipy or src is imported or
  loaded);
- check_extraction_totals: `test_changed_extracted_cell_fails_the_printed_totals`;
- check_plan_order: `test_edit_above_section12_fails_in_a_clone` (uncommitted and
  committed), and `tests/test_plan_order.py::test_uncommitted_edit_above_section12_is_flagged`;
- check_deviations: `test_unlogged_labels_fail` (post hoc; exploratory naming an entry
  that is not exploratory; a missing entry; deviation with no entry; deviation naming
  §12.1, which is not a deviation; and two lines that pass),
  `test_unlogged_label_in_readme_and_data_flags_fail`, `test_undated_section12_entry_fails`,
  `test_post_hoc_line_covered_by_a_dated_post_hoc_entry_passes`;
- check_rerun: `test_rerun_compares_every_output_byte_for_byte` (a changed, a missing and
  an extra file, with the rerun replaced by a stub);
- check_all: `test_check_all_skips_the_manuscript_steps_without_a_manuscript`.

## Not exercised

- (Superseded, 21 November 2026: the manuscript checks now exist; see the next section.)
- check_outputs does not re-derive the H1 bootstrap interval, the sensitivity trend
  models, the leave-one-out tiers or the district modules; an edit there alone is caught
  by check_rerun (and the byte-identity tests), as mutation 10 shows for a report.

## Manuscript checks (Task 8, 21 November 2026)

`check_manuscript_numbers` and `check_docx_tie` run on the private, git-ignored manuscript
folder (`manuscript/`); check_all runs both and reports SKIP only where
`manuscript/manuscript_src.md` is absent (a fresh clone). Their mutation harness is
`verification/mutate_manuscript.py`: each named mutation is applied to a copy of the folder
inside the folder's own `_mutations/` work area (removed afterwards), and both checks run
on the copy. The anchors the mutations edit quote the manuscript, so they are kept with it
(in its `section_phrases.json`), not here.

- 44 named mutations, all caught: numbers changed in the .docx only (01, 02, 08) and in
  the Markdown only (text, highlights, the registration time); the author's name, e-mail,
  institution or the repository URL put into an anonymised file (text and document
  properties of 02, 03 and 08); citation and reference-list numbers changed or reordered; table
  cells edited in the .docx and in `tables.md`; a figure-data cell edited; the H1/H2 labels
  changed or overstated; signs flipped; internal identifiers, "missed cases", causal and
  ranking language and an American spelling inserted; a highlight made longer than 85
  characters; the abstract pushed over 250 words; the AI declaration changed on the title
  page; a caveat removed; a figure PDF swapped, a TIFF at 300 dpi, a report edited; an
  extra and a missing file in `submission/`.
- `--sweep`: every number token of `manuscript_src.md` outside the References (506 tokens,
  last digit bumped) is caught by check_manuscript_numbers, and every number token in the
  text of `02_manuscript_anonymised.docx`, tables and references included (951 tokens), by
  check_docx_tie.
- Unit tests: `tests/test_manuscript_tools.py` (the build refuses a folder holding a
  `SUBMITTED_*` file and rejects unknown options; the checks skip without the folder and fail
  without their phrases; reference order, highlight and abstract limits, wording rules).
