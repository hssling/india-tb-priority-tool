# Environment

Every script is run as `python -I <script>` from the repository root, with LF line
endings (`.gitattributes`). The outputs in `outputs/` were produced, and
`python -I verification/check_all.py` was run, with:

- Windows 11 Pro (64-bit)
- Python 3.14.0
- numpy 2.3.5: the analysis (`numpy.random.default_rng(20261121)`, percentiles with
  `method="linear"`); the tool's only dependency (`pyproject.toml`)
- scipy 1.16.3: average ranks for H1 and H2 (`scipy.stats.rankdata`) in
  `src/tbprio/validate.py`
- pytest 9.0.0: the tests
- pdfplumber 0.11.8: reading the India TB Report tables (page by page, with
  `page.flush_cache()` after each page to bound memory); needed only to
  re-extract from the source PDFs
- python-docx 1.2.0: reading the Lok Sabha Q802 Word file (district
  notifications); needed only to re-extract it
- setuptools 80.9.0 and pip 25.2: the editable install of the tool
  (`python -I -m pip install -e .`, which makes `python -I -m tbprio` work)
- matplotlib 3.10.7: optional, for the manuscript figures; not used by the tool or
  the outputs

The independent recompute `verification/check_outputs.py`, the deviations check and
`tools/fetch_sources.py` use the standard library only. The HTML reports are
written as plain text with inline SVG; they need no plotting library.

Reruns with the same inputs give byte-identical outputs on this environment
(`verification/check_rerun.py`). Another platform or library version could change
the last digits of the random draws; `check_outputs.py` then still recomputes the
deterministic values and P(top-5) within its stated tolerances.

The data inventory (`docs/data_inventory.md`) was also checked with PyMuPDF
1.27.2.3, used only to locate pages and to render the scanned ITR 2021 pages
for reading by eye. No analysis output depends on it.
