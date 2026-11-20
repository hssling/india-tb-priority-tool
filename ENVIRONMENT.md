# Environment

Every script is run as `python -I <script>` from the repository root.

- Python 3.14.0
- pytest 9.0.0: the tests
- pdfplumber 0.11.8: reading the India TB Report tables (page by page, with
  `page.flush_cache()` after each page to bound memory)
- python-docx 1.2.0: reading the Lok Sabha Q802 Word file (district notifications)
- numpy 2.3.5 and scipy 1.16.3: the analysis (from Task 4)
- matplotlib 3.10.7: the figures (from Task 8)

`tools/fetch_sources.py` uses the standard library only.

The data inventory (`docs/data_inventory.md`) was also checked with PyMuPDF
1.27.2.3, used only to locate pages and to render the scanned ITR 2021 pages
for reading by eye. No analysis output depends on it.
