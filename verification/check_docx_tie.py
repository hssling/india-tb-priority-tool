# Adapted from hssling/india-tb-acf-campaign (MIT), verification/check_docx_tie.py (itself adapted
# from hssling/india-state-tb-score); modified: the Evaluation and Program Planning submission set of
# this paper (title page, anonymised manuscript, highlights, Figure_N files, supplement, cover letter,
# declaration, vitae, HTML reports); highlight lengths, abstract and whole-text limits from Word's
# counts; the figures equal the exhibits and are at least 1000 dpi; the reports equal outputs/.
"""Tie the submission files to their Markdown sources and check the journal's limits.

Run as: python -I verification/check_docx_tie.py [--manuscript-dir DIR]

The manuscript folder is DIR (default manuscript/; git-ignored). The files in <folder>/submission/
(built by tools/build_submission.py) are what the journal receives; the Markdown files in <folder>/
are what check_manuscript_numbers.py verifies. Reading the .docx files needs only zipfile and
ElementTree (the TIFF check uses Pillow when it is installed).

1. Text tie. Each .docx's units (paragraphs outside tables; table rows as their cells joined by
   " | ") equal, in order, the units of its Markdown source(s): headings, paragraphs, list items,
   table rows and reference entries, normalised the same way on both sides (emphasis markers and
   escapes removed, superscripts written ^...^, whitespace collapsed, the Zenodo DOI read as one
   token). A changed number, sign, cell, reference number or inserted word on either side is a
   difference. Every file of the set is present and no other file is in submission/ (except a
   SUBMITTED_* record and the _render folder).
2. Anonymisation. No author marker (check_manuscript_numbers.author_markers: name, ORCID,
   institution, postcode, repository and account, companion repositories, the title page's
   e-mail) occurs anywhere in 02, 03 or 08 (every XML part, document properties included), in
   the figure files or in the HTML reports; 02 holds the placeholder for the repository.
3. Internal identifiers and wording (check_manuscript_numbers.BANNED) do not occur in 02 (before
   the References), 03 or 08.
4. Highlights: 3 to 5 bullets in 03, each at most 85 characters including spaces.
5. Word's counts. <folder>/word_counts_word.json (Word's ComputeStatistics on 02, written by the
   build) belongs to the current manuscript_src.md; the abstract is at most 250 words and the whole
   text at most 10,000 words; the title page quotes the three counts.
6. Figures: each NN_Figure_k.pdf equals exhibits/figurek.pdf byte for byte, and each TIFF is at
   least 1000 dpi and at most 7480 pixels wide (Elsevier full-page width). Reports: 12 and 13 equal
   outputs/report_state.html and outputs/report_district.html byte for byte.

Prints "SKIPPED" and exits 0 when <folder>/ or <folder>/submission/ is absent. Exit 1 on any problem.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verification import check_manuscript_numbers as cmn  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOI = re.compile(r"10\.5281/zenodo\.(?:\d+|X{3,})")
LIMITS = {"abstract": 250, "total": 10000}
HIGHLIGHT_CHARS = 85
MIN_DPI, MAX_PX = 1000, 7480
MS = "manuscript_src.md"
TP = "title_page_src.md"
# The one paragraph the build adds to the supplement (tools/build_submission.py imports it from here).
SUPP_NOTE = ("Tables S1 to S12 are cited in the manuscript in this order. The tool's two HTML reports "
             "(supplementary files 12 and 13) show the State priority matrix and the district funnels; they "
             "open in any web browser and need no connection.")

FIGURES = {k: (f"{p}_Figure_{k}.tif", f"{p}_Figure_{k}.pdf") for k, p in zip(range(1, 5), ("04", "05", "06", "07"))}
REPORTS = {"12_supplementary_report_state.html": "outputs/report_state.html",
           "13_supplementary_report_district.html": "outputs/report_district.html"}
SPEC: dict[str, list[tuple]] = {
    "01_title_page.docx": [("md", TP, None, None)],
    "02_manuscript_anonymised.docx": [
        ("md", MS, None, "## Figure captions"),
        ("md", "exhibits/tables.md", "## Table 1.", "## Table S1."),
        ("md", MS, "## Figure captions", None),
    ],
    "03_highlights.docx": [("md", "highlights.md", None, None)],
    "08_supplementary_material.docx": [
        ("builder", "Supplementary material"),
        ("first", MS, "# "),
        ("builder", SUPP_NOTE),
        ("md", "exhibits/tables.md", "## Table S1.", None),
    ],
    "09_cover_letter.docx": [("md", "cover_letter.md", "# Cover letter", None, "drop-first")],
    "10_declaration_of_interests.docx": [
        ("builder", "Declaration of interests"),
        ("first", TP, "**Title:**"),
        ("first", TP, "**Author:**"),
        ("first", TP, "**Declaration of competing interest:**"),
    ],
    "11_vitae.docx": [("md", "vitae.md", None, None)],
}
ANONYMISED = ("02_manuscript_anonymised.docx", "03_highlights.docx", "08_supplementary_material.docx")
SUBMITTED = re.compile(r"SUBMITTED_.*")


def all_files() -> set[str]:
    return set(SPEC) | {f for pair in FIGURES.values() for f in pair} | set(REPORTS)


# --------------------------------------------------------------------------------------
# Normalisation (the same for both sides)
# --------------------------------------------------------------------------------------
def norm(s: str) -> str:
    s = s.replace("**", "").replace("*", "")
    s = re.sub(r"\\(?=[^\w\s])", "", s)
    s = s.replace("^^", "")
    s = s.replace("\u00a0", " ")
    s = DOI.sub("10.5281/zenodo.<DOI>", s)
    return re.sub(r"\s+", " ", s).strip()


def md_slice(text: str, start: str | None, end: str | None) -> str:
    lines = text.splitlines()
    i = 0 if start is None else next(k for k, ln in enumerate(lines) if ln.startswith(start))
    j = len(lines) if end is None else next(k for k, ln in enumerate(lines) if k > i and ln.startswith(end))
    return "\n".join(lines[i:j])


def row_unit(cells) -> str:
    cells = list(cells)
    while len(cells) > 1 and not cells[-1]:
        cells.pop()
    return " | ".join(cells)


def md_units(text: str) -> list[str]:
    """Headings, paragraphs, list items and table rows of a Markdown text, normalised."""
    units: list[str] = []
    para: list[str] = []

    def flush() -> None:
        if para:
            units.append(norm(" ".join(para)))
            para.clear()

    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            flush()
        elif s.startswith("#"):
            flush()
            units.append(norm(s.lstrip("#")))
        elif s.startswith("|"):
            flush()
            body = s[1:-1] if s.endswith("|") else s[1:]
            cells = body.split("|")
            if all(re.fullmatch(r"\s*:?-{3,}:?\s*", c) for c in cells):
                continue
            units.append(row_unit(norm(c) for c in cells))
        elif re.match(r"[-*+] ", s):
            flush()
            para.append(s[2:])
        elif re.match(r"\[\d+\] ", s):
            flush()
            para.append(s)
        else:
            para.append(s)
    flush()
    return [u for u in units if u]


# --------------------------------------------------------------------------------------
# .docx units
# --------------------------------------------------------------------------------------
def para_text(p: ET.Element) -> str:
    parts = []
    for r in p.iter(f"{W}r"):
        va = r.find(f"{W}rPr/{W}vertAlign")
        sup = va is not None and va.get(f"{W}val") == "superscript"
        txt = "".join((t.text or "") if t.tag == f"{W}t" else " " for t in r if t.tag in (f"{W}t", f"{W}tab", f"{W}br"))
        parts.append(f"^{txt}^" if sup and txt.strip() else txt)
    return "".join(parts)


def docx_units(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        body = ET.fromstring(z.read("word/document.xml")).find(f"{W}body")
    units: list[str] = []
    for el in body:
        if el.tag == f"{W}p":
            u = norm(para_text(el))
            if u:
                units.append(u)
        elif el.tag == f"{W}tbl":
            for tr in el.iter(f"{W}tr"):
                cells = [" ".join(para_text(p) for p in tc.iter(f"{W}p")) for tc in tr.findall(f"{W}tc")]
                units.append(row_unit(norm(c) for c in cells))
    return units


def docx_all_text(path: Path) -> str:
    out = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith((".xml", ".rels")):
                raw = z.read(name).decode("utf-8", errors="replace")
                out += [re.sub(r"<[^>]+>", "", raw), raw]
    return "\n".join(out)


# --------------------------------------------------------------------------------------
# Expected units
# --------------------------------------------------------------------------------------
def expected(ms_dir: Path, name: str) -> list[str]:
    out: list[str] = []
    for part in SPEC[name]:
        if part[0] == "builder":
            out.append(norm(part[1]))
        elif part[0] == "first":
            text = (ms_dir / part[1]).read_text(encoding="utf-8")
            if part[2] == "# ":
                hits = [norm(text.splitlines()[0].lstrip("#"))]
            else:
                hits = [u for u in md_units(text) if u.startswith(norm(part[2]))]
            if len(hits) != 1:
                raise ValueError(f"{part[1]}: {len(hits)} units start with {part[2]!r}")
            out.append(hits[0])
        else:
            text = (ms_dir / part[1]).read_text(encoding="utf-8")
            units = md_units(md_slice(text, part[2], part[3]))
            if len(part) > 4 and part[4] == "drop-first":
                units = units[1:]
            out += units
    return out


def compare(name: str, got: list[str], want: list[str], limit: int = 6) -> list[str]:
    if got == want:
        return []
    out = []
    sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        md = " // ".join(want[i1:i2])[:300] or "(nothing)"
        dx = " // ".join(got[j1:j2])[:300] or "(nothing)"
        out.append(f"TIE {name}: {tag} at markdown unit {i1 + 1}, docx unit {j1 + 1}:\n    markdown: {md}\n    docx:     {dx}")
        if len(out) >= limit:
            out.append(f"TIE {name}: further differences not listed")
            break
    return out


# --------------------------------------------------------------------------------------
# Anonymisation, wording, highlights, word counts, figures and reports
# --------------------------------------------------------------------------------------
def markers(ms_dir: Path, root: Path) -> list[str]:
    return [m for m in cmn.author_markers(root, ms_dir) if len(m) >= 5]


def anonymisation_problems(name: str, haystack: str, marks: list[str]) -> list[str]:
    low = haystack.lower()
    return [f"ANONYMISATION in {name}: contains {m!r}" for m in marks if m.lower() in low]


def wording_problems(name: str, units: list[str]) -> list[str]:
    text = "\n".join(units)
    if name.startswith("02_"):
        text = text.split("\nReferences\n", 1)[0]
    out = []
    for pat, what in cmn.BANNED + cmn.WORDING:
        for m in re.finditer(pat, text, re.I if (pat, what) in cmn.WORDING else 0):
            out.append(f"WORDING in {name}: {what}: {m.group()!r}")
    return out


def highlight_problems(units: list[str]) -> list[str]:
    bullets = [u for u in units if u != "Highlights"]
    out = []
    if not 3 <= len(bullets) <= 5:
        out.append(f"HIGHLIGHTS: 03 has {len(bullets)} bullets (3 to 5 required)")
    for b in bullets:
        if len(b) > HIGHLIGHT_CHARS:
            out.append(f"HIGHLIGHTS: {len(b)} characters (limit {HIGHLIGHT_CHARS}): {b!r}")
    return out


def word_count_problems(ms_dir: Path, title_units: list[str], abstract_units: list[str]) -> list[str]:
    p = ms_dir / "word_counts_word.json"
    if not p.exists():
        return ["WORDS: word_counts_word.json missing (build with Word: python -I tools/build_submission.py)"]
    w = json.loads(p.read_text(encoding="utf-8"))
    out = []
    md5 = hashlib.md5((ms_dir / MS).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    if w.get("source_md5") != md5:
        out.append("WORDS: word_counts_word.json is stale (manuscript_src.md changed): rebuild")
    for k, lim in LIMITS.items():
        if w[k] > lim:
            out.append(f"WORDS: Word counts {w[k]} words in the {k}, over the limit of {lim}")
    own = sum(len(u.split()) for u in abstract_units)
    if own > LIMITS["abstract"]:
        out.append(f"WORDS: the abstract of 02 has {own} words, over the limit of {LIMITS['abstract']}")
    flat = " ".join(title_units)
    for want in (f"abstract {w['abstract']:,} words", f"main text (Introduction to Conclusions) {w['main_text']:,} words",
                 f"whole text (title to the AI declaration; references, tables and figure captions excluded) "
                 f"{w['total']:,} words"):
        if want not in flat:
            out.append(f"WORDS: the title page does not quote Word's count {want!r}")
    return out


def abstract_of(units: list[str]) -> list[str]:
    try:
        i = units.index("Abstract")
    except ValueError:
        return ["(no Abstract heading)"] * 999
    out = []
    for u in units[i + 1:]:
        if u.startswith("Keywords:"):
            break
        out.append(u)
    return out


def figure_problems(ms_dir: Path) -> list[str]:
    sub, ex = ms_dir / "submission", ms_dir / "exhibits"
    out = []
    for k, (tif, pdf) in FIGURES.items():
        src = ex / f"figure{k}.pdf"
        if (sub / pdf).exists() and src.exists() and (sub / pdf).read_bytes() != src.read_bytes():
            out.append(f"FIGURES: {pdf} differs from exhibits/figure{k}.pdf (rebuild)")
        if (sub / tif).exists():
            try:
                from PIL import Image
            except ImportError:
                continue
            Image.MAX_IMAGE_PIXELS = None
            with Image.open(sub / tif) as im:
                dpi = im.info.get("dpi", (0, 0))
                if min(float(dpi[0]), float(dpi[1])) < MIN_DPI:
                    out.append(f"FIGURES: {tif} is {dpi} dpi, below {MIN_DPI}")
                if im.size[0] > MAX_PX:
                    out.append(f"FIGURES: {tif} is {im.size[0]} pixels wide, more than {MAX_PX}")
    return out


def report_problems(sub: Path, root: Path) -> list[str]:
    return [f"REPORTS: {dst} differs from {src}" for dst, src in REPORTS.items()
            if (sub / dst).exists() and (sub / dst).read_bytes() != (root / src).read_bytes()]


# Optional uploads the submission system accepts beside the set (not required by the journal's
# guide): a graphical abstract.
OPTIONAL_FILES = {"14_graphical_abstract.tif", "14_graphical_abstract.pdf"}


def problems(ms_dir: Path | None = None, root: Path = ROOT) -> list[str]:
    ms_dir = ms_dir or root / cmn.DEFAULT_MS_DIR
    sub = ms_dir / "submission"
    out: list[str] = []
    marks = markers(ms_dir, root)
    units_of: dict[str, list[str]] = {}
    out += [f"EXTRA: {p.name} is not part of the submission set" for p in sorted(sub.iterdir())
            if p.is_file() and p.name not in all_files() and p.name not in OPTIONAL_FILES
            and not SUBMITTED.fullmatch(p.name)]
    for name in SPEC:
        path = sub / name
        if not path.exists():
            out.append(f"MISSING: {name}")
            continue
        got = docx_units(path)
        units_of[name] = got
        out += compare(name, got, expected(ms_dir, name))
        if name in ANONYMISED:
            out += anonymisation_problems(name, docx_all_text(path), marks)
            out += wording_problems(name, got)
    for name in [f for pair in FIGURES.values() for f in pair] + list(REPORTS):
        path = sub / name
        if not path.exists():
            out.append(f"MISSING: {name}")
            continue
        out += anonymisation_problems(name, path.read_bytes().decode("latin-1"), marks)
    if "02_manuscript_anonymised.docx" in units_of and not any(
            cmn.PLACEHOLDER in u for u in units_of["02_manuscript_anonymised.docx"]):
        out.append(f"ANONYMISATION: 02 lacks the placeholder {cmn.PLACEHOLDER!r}")
    if "03_highlights.docx" in units_of:
        out += highlight_problems(units_of["03_highlights.docx"])
    if "01_title_page.docx" in units_of and "02_manuscript_anonymised.docx" in units_of:
        out += word_count_problems(ms_dir, units_of["01_title_page.docx"],
                                   abstract_of(units_of["02_manuscript_anonymised.docx"]))
    out += figure_problems(ms_dir)
    out += report_problems(sub, root)
    return out


def notes(ms_dir: Path) -> list[str]:
    p = ms_dir / "submission" / "01_title_page.docx"
    if p.exists() and "zenodo.XXXXXXX" in docx_all_text(p):
        return ["note: the title page still holds the Zenodo DOI placeholder (rebuild with --doi at release)"]
    return []


def main(root: Path = ROOT, argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ms_dir, rest = cmn.manuscript_dir(root, argv)
    if rest:
        print(f"FAIL: unknown arguments {rest}")
        return 1
    name = cmn.rel(ms_dir, root)
    if not ms_dir.is_dir() or not (ms_dir / "submission").is_dir():
        print(f"SKIPPED: {name}/ or {name}/submission/ not present (kept private, not in this repository)")
        return 0
    found = problems(ms_dir, root)
    for ln in found:
        print(ln)
    for ln in notes(ms_dir):
        print(ln)
    n_units = sum(len(docx_units(ms_dir / "submission" / n)) for n in SPEC if (ms_dir / "submission" / n).exists())
    print(f"docx tie: {len(all_files())} files; {len(SPEC)} .docx, {n_units} paragraphs and table rows tied to the "
          f"Markdown; anonymisation of 02, 03, 08, the figures and the reports; highlights, abstract and word limits; "
          f"figures and reports byte-equal to their sources; {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
