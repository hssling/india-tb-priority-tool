# Adapted from hssling/india-tb-acf-campaign (MIT), tools/build_submission.py (itself adapted from
# hssling/india-state-tb-score, manuscript/build_docx.py); modified: the Evaluation and Program
# Planning (Elsevier) submission set of this paper: title page, anonymised manuscript, highlights,
# figures named Figure_N, supplementary material, cover letter, declaration of interests, vitae and
# the tool's two HTML reports; refuses to write into a submitted (SUBMITTED_*) folder.
"""Build the Evaluation and Program Planning submission set into <manuscript folder>/submission/.

Run as: python -I tools/build_submission.py [--manuscript-dir DIR] [--doi 10.5281/zenodo.NNNNNNN] [--no-word]

The manuscript folder is DIR (default manuscript/; git-ignored and private); a relative DIR is taken
from the repository root. Unknown options are rejected. The build refuses to write when the folder
or its submission/ holds a SUBMITTED_* file: a submitted set is frozen, and changes after
submission go into a new folder.

Needs pandoc on PATH, python-docx, Pillow and PyMuPDF (fitz); Microsoft Word (through PowerShell
COM) for the word counts unless --no-word. Sources (in the folder): manuscript_src.md (anonymised),
title_page_src.md, highlights.md, cover_letter.md, vitae.md and exhibits/ (tables.md, figure1.pdf to
figure4.pdf, from exhibits/make_tables.py and exhibits/make_figures.py). Nothing is written outside
the folder.

Layout (manuscript/journal_rules.md; Elsevier): A4, 2.5 cm margins, Times New Roman 12 pt, double
spacing, page numbers at the foot; continuous line numbers in the anonymised manuscript. Tables are
editable, with only the top, header and bottom rules (no vertical rules, no shading) and 10 pt
single-spaced cells (8-9 pt in the landscape supplement).

  01_title_page.docx                 title page (author details; --doi fills the Zenodo DOI, otherwise the
                                     placeholder is highlighted)
  02_manuscript_anonymised.docx      anonymised text, references, Tables 1-2, figure captions
  03_highlights.docx                 3-5 bullets of at most 85 characters
  04_Figure_1.tif / 04_Figure_1.pdf  Figure 1: TIFF (LZW, 1000 dpi) rendered from the vector PDF, and the PDF
  05_Figure_2 ... 07_Figure_4        Figures 2 to 4, likewise
  08_supplementary_material.docx     Tables S1 to S12, landscape (anonymised)
  09_cover_letter.docx
  10_declaration_of_interests.docx   the declaration of competing interest from the title page
  11_vitae.docx                      the author's biography (at most 100 words)
  12_supplementary_report_state.html     the tool's State report (outputs/report_state.html)
  13_supplementary_report_district.html  the tool's district report (outputs/report_district.html)

Word's own counts of 02 go to <folder>/word_counts_word.json (tools/word_count_word.ps1); the title
page must quote them (verification/check_docx_tie.py checks it, and ties every .docx to its source).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.run import Run

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verification.check_docx_tie import SUPP_NOTE  # noqa: E402  (the supplement's one added paragraph)

DEFAULT_MS_DIR = "manuscript"
MS = ROOT / DEFAULT_MS_DIR
EX = MS / "exhibits"
OUT = MS / "submission"

FONT = "Times New Roman"
DOI_PLACEHOLDER = "10.5281/zenodo.XXXXXXX"
DOI_RE = re.compile(r"^10\.5281/zenodo\.\d+$")
TIFF_DPI = 1000  # Elsevier: bitmapped line drawings at least 1000 dpi
N_FIGURES = 4
FIG_PREFIX = ("04", "05", "06", "07")
SUPPLEMENT = "08_supplementary_material.docx"
REPORTS = {"12_supplementary_report_state.html": "outputs/report_state.html",
           "13_supplementary_report_district.html": "outputs/report_district.html"}
SUBMITTED = re.compile(r"^SUBMITTED_")
PAGEBREAK = '\n\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n'
INDENT = "\u00a0"
PANDOC_FROM = ("markdown+pipe_tables+superscript+fenced_divs+raw_attribute-smart-subscript-citations"
               "-tex_math_dollars-raw_html-auto_identifiers-implicit_figures-link_attributes")


def configure(ms_dir: Path) -> None:
    global MS, EX, OUT
    MS, EX, OUT = ms_dir, ms_dir / "exhibits", ms_dir / "submission"


def figure_names(k: int) -> tuple[str, str]:
    """Figure k (1-based) as 04_Figure_1.tif and 04_Figure_1.pdf."""
    return f"{FIG_PREFIX[k - 1]}_Figure_{k}.tif", f"{FIG_PREFIX[k - 1]}_Figure_{k}.pdf"


def submitted_markers(ms_dir: Path) -> list[Path]:
    """SUBMITTED_* files in the folder or its submission/ (a frozen, submitted set)."""
    out = []
    for d in (ms_dir, ms_dir / "submission"):
        if d.is_dir():
            out += [p for p in d.iterdir() if p.is_file() and SUBMITTED.match(p.name)]
    return out


# --------------------------------------------------------------------------------------
# Markdown preparation (the sources are never written)
# --------------------------------------------------------------------------------------
def read(rel: str) -> str:
    return (MS / rel).read_text(encoding="utf-8")


def between(text: str, start: str, end: str | None) -> str:
    i = text.index("\n" + start) + 1 if not text.startswith(start) else 0
    j = text.index("\n" + end, i) + 1 if end else len(text)
    return text[i:j]


def escape_refs(md: str) -> str:
    """Reference list entries '[n] ...' kept as literal text (each its own paragraph)."""
    return re.sub(r"(?m)^\[(\d+)\] ", r"\\[\1\\] ", md)


def table_block(md: str) -> str:
    """One '## Table N. Title' section of tables.md as pandoc Markdown: the title as a 'Table Title'
    paragraph ('Table N.' bold), the table, and the notes below as 'Table Note' paragraphs."""
    lines = md.strip("\n").splitlines()
    m = re.match(r"## (Table S?\d+\.) (.*)", lines[0])
    if not m:
        raise SystemExit(f"not a table heading: {lines[0]!r}")
    out = ['::: {custom-style="Table Title"}', f"**{m.group(1)}** {m.group(2)}", ":::", ""]
    para: list[str] = []
    for ln in lines[1:] + [""]:
        if ln.startswith("|"):
            out.append(ln)
            continue
        if ln.strip():
            para.append(ln)
            continue
        if para:
            out += ["", '::: {custom-style="Table Note"}', " ".join(para), ":::", ""]
            para = []
        elif out[-1] != "":
            out.append("")
    return "\n".join(out) + "\n"


def tables(names_from: str, names_to: str | None) -> list[str]:
    part = between(read("exhibits/tables.md"), names_from, names_to)
    return [table_block(b) for b in re.split(r"(?m)^(?=## )", part) if b.startswith("## Table ")]


def manuscript_md() -> str:
    ms = read("manuscript_src.md")
    body = between(ms, "# ", "## References")
    refs = between(ms, "## References", "## Figure captions")
    caps = between(ms, "## Figure captions", None)
    parts = [body.rstrip(), PAGEBREAK, escape_refs(refs).rstrip()]
    for t in tables("## Table 1.", "## Table S1."):
        parts += [PAGEBREAK, t]
    parts += [PAGEBREAK, caps]
    return "".join(parts)


def title_page_md(doi: str | None) -> str:
    tp = read("title_page_src.md")
    if tp.count(DOI_PLACEHOLDER) < 1:
        raise SystemExit(f"title_page_src.md must hold the DOI placeholder {DOI_PLACEHOLDER}")
    return tp.replace(DOI_PLACEHOLDER, doi) if doi else tp


def supplement_md() -> str:
    title = read("manuscript_src.md").splitlines()[0]
    if not title.startswith("# "):
        raise SystemExit("manuscript_src.md must start with its '# ' title")
    parts = ["# Supplementary material\n\n", title[2:].strip(), "\n\n", SUPP_NOTE, "\n"]
    for t in tables("## Table S1.", None):
        parts += [PAGEBREAK, t]
    return "".join(parts)


def letter_md(name: str) -> str:
    """A letter without its '# ' heading; the lines of an address block kept apart by hard breaks."""
    lines = read(name).splitlines()
    if not lines[0].startswith("# "):
        raise SystemExit(f"{name} must start with a '# ' heading")
    blocks = re.split(r"\n\s*\n", "\n".join(lines[1:]).strip())
    out = []
    for b in blocks:
        bl = b.splitlines()
        if len(bl) > 1 and not any(ln.lstrip().startswith(("-", "|")) for ln in bl):
            b = "\\\n".join(bl)
        out.append(b)
    return "\n\n".join(out) + "\n"


def declaration_md(doi: str | None) -> str:
    """The declaration of interests: the title, the author and the title page's statement of
    competing interest, word for word."""
    tp = title_page_md(doi)
    keep = []
    for key in ("**Title:**", "**Author:**", "**Declaration of competing interest:**"):
        hit = [ln for ln in tp.splitlines() if ln.startswith(key)]
        if len(hit) != 1:
            raise SystemExit(f"title_page_src.md: expected one line starting {key}")
        keep.append(hit[0])
    return "# Declaration of interests\n\n" + "\n\n".join(keep) + "\n"


# --------------------------------------------------------------------------------------
# pandoc and the reference document
# --------------------------------------------------------------------------------------
def set_font(obj, size: float | None = 12) -> None:
    obj.font.name = FONT
    if size:
        obj.font.size = Pt(size)
    rpr = obj.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]


def make_reference(path: Path) -> None:
    raw = subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                         capture_output=True, check=True).stdout
    path.write_bytes(raw)
    doc = Document(str(path))
    for name in ("Table Title", "Table Note"):
        if name not in [s.name for s in doc.styles]:
            doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH).base_style = doc.styles["Normal"]
    for st in doc.styles:
        if st.type == WD_STYLE_TYPE.PARAGRAPH:
            set_font(st, 12)
            st.font.color.rgb = None
            pf = st.paragraph_format
            pf.line_spacing = 2.0
            pf.space_before = Pt(0)
            pf.space_after = Pt(6)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.keep_together = False  # a paragraph may break across pages (no half-empty pages)
            pf.widow_control = True
            if st.name.startswith("Heading") or st.name == "Title":
                st.font.bold = True
                st.font.italic = False
                pf.keep_with_next = True
                pf.space_before = Pt(12)
        elif st.type == WD_STYLE_TYPE.CHARACTER:
            set_font(st, None)
            st.font.color.rgb = None
    doc.styles["Heading 1"].font.size = Pt(14)
    doc.styles["Heading 3"].font.italic = True
    tt = doc.styles["Table Title"]
    tt.paragraph_format.keep_with_next = True
    tt.paragraph_format.line_spacing = 1.5
    tn = doc.styles["Table Note"]
    set_font(tn, 10)
    tn.paragraph_format.line_spacing = 1.0
    tn.paragraph_format.space_before = Pt(3)
    tn.paragraph_format.space_after = Pt(3)
    doc.save(str(path))


def run_pandoc(md: str, out: Path, ref: Path, tmp: Path) -> None:
    src = tmp / (out.stem + ".md")
    src.write_text(md, encoding="utf-8")
    subprocess.run(["pandoc", str(src), "-f", PANDOC_FROM, "--reference-doc", str(ref), "-o", str(out)], check=True)


# --------------------------------------------------------------------------------------
# Post-processing with python-docx
# --------------------------------------------------------------------------------------
def page_setup(doc, landscape: bool = False, line_numbers: bool = False) -> None:
    for sec in doc.sections:
        if landscape:
            sec.orientation = WD_ORIENT.LANDSCAPE
            sec.page_width, sec.page_height = Cm(29.7), Cm(21.0)
        else:
            sec.orientation = WD_ORIENT.PORTRAIT
            sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Cm(2.5)
        sec.footer_distance = Cm(1.25)
        sp = sec._sectPr
        for e in sp.findall(qn("w:lnNumType")):
            sp.remove(e)
        if line_numbers:
            ln = OxmlElement("w:lnNumType")
            ln.set(qn("w:countBy"), "1")
            ln.set(qn("w:restart"), "continuous")
            ln.set(qn("w:distance"), "283")
            anchor = None
            for tag in ("w:pgBorders", "w:paperSrc", "w:pgMar"):
                anchor = sp.find(qn(tag))
                if anchor is not None:
                    break
            anchor.addnext(ln)
        p = sec.footer.paragraphs[0] if sec.footer.paragraphs else sec.footer.add_paragraph()
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        for kind in ("begin", "instr", "separate", "text", "end"):
            if kind == "instr":
                e = OxmlElement("w:instrText")
                e.set(qn("xml:space"), "preserve")
                e.text = " PAGE "
            elif kind == "text":
                e = OxmlElement("w:t")
                e.text = "1"
            else:
                e = OxmlElement("w:fldChar")
                e.set(qn("w:fldCharType"), kind)
            run._r.append(e)
        set_font(run, 11)


def border(tag: str, val: str = "single", sz: int = 8) -> OxmlElement:
    e = OxmlElement(f"w:{tag}")
    e.set(qn("w:val"), val)
    if val != "nil":
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "000000")
    return e


TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize",
               "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
               "tblCaption", "tblDescription"]
TCPR_ORDER = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
              "textDirection", "tcFitText", "vAlign", "hideMark"]


def reorder(parent, order: list[str]) -> None:
    kids = sorted(list(parent), key=lambda e: order.index(e.tag.split("}")[1])
                  if e.tag.split("}")[1] in order else len(order))
    for e in kids:
        parent.remove(e)
    for e in kids:
        parent.append(e)


def text_of(el) -> str:
    return "".join(x.text or "" for x in el.iter(qn("w:t")))


def col_texts(t) -> list[list[str]]:
    """The cell texts of each column; a block-label row (it will span the table) is left out."""
    cols: list[list[str]] = [[] for _ in t.columns]
    spans = set(spanning_rows(t._tbl))
    for i, tr in enumerate(t._tbl.findall(qn("w:tr"))):
        tcs = tr.findall(qn("w:tc"))
        if len(tcs) != len(cols) or i in spans:
            continue
        for j, tc in enumerate(tcs):
            cols[j].append(text_of(tc))
    return cols


PAD = 2 * 108 + 20  # the cell margins and a little slack (twips)


def col_mins(t, size: float) -> list[float]:
    """Each column's minimum width (twips): its longest word (half an em per character)."""
    char = size * 20 * 0.52
    return [(max((len(w) for s in texts for w in s.split()), default=3) + 1) * char + PAD for texts in col_texts(t)]


def fit_size(t, total: int, size: float, floor: float = 7.0) -> float:
    while sum(col_mins(t, size)) >= total and size - 0.5 >= floor:
        size -= 0.5
    return size


def col_widths(t, total: int, size: float) -> list[int]:
    char = size * 20 * 0.52
    mins, wants = col_mins(t, size), []
    for j, texts in enumerate(col_texts(t)):
        lengths = sorted(len(s.strip()) for s in texts[1:] if s.strip()) or [3]
        typical = lengths[int(0.9 * (len(lengths) - 1))]
        wants.append(max(min(typical, 150) * char + PAD, mins[j]))
    if sum(mins) >= total:
        raw = [total * m / sum(mins) for m in mins]
    elif sum(wants) <= total:
        raw = [w + (total - sum(wants)) * w / sum(wants) for w in wants]
    else:
        fixed: dict[int, float] = {}
        while True:
            free = total - sum(fixed.values())
            rest = sum(w for j, w in enumerate(wants) if j not in fixed)
            raw = [fixed.get(j, free * w / rest) for j, w in enumerate(wants)]
            low = [j for j, (x, m) in enumerate(zip(raw, mins)) if j not in fixed and x < m]
            if not low:
                break
            for j in low:
                fixed[j] = mins[j]
    widths = [int(round(x)) for x in raw]
    widths[-1] += total - sum(widths)
    return widths


def is_bold_run(r) -> bool:
    rpr = r.find(qn("w:rPr"))
    b = rpr.find(qn("w:b")) if rpr is not None else None
    return b is not None and b.get(qn("w:val")) not in ("0", "false")


def spanning_rows(tbl, first: int = 1) -> list[int]:
    """Rows (after the header) whose first cell is wholly bold and whose other cells are empty
    (tables.md writes '| **Label** | | ... |'): each becomes one cell spanning the table."""
    out = []
    for i, tr in enumerate(tbl.findall(qn("w:tr"))):
        tcs = tr.findall(qn("w:tc"))
        if i < first or len(tcs) < 2:
            continue
        texts = [text_of(tc) for tc in tcs]
        runs = [r for r in tcs[0].iter(qn("w:r")) if text_of(r).strip()]
        if texts[0].strip() and not any(x.strip() for x in texts[1:]) and runs and all(map(is_bold_run, runs)):
            out.append(i)
    return out


def set_cell_border(tc, edge: str, val: str, sz: int = 6) -> None:
    tb = tc.get_or_add_tcPr().find(qn("w:tcBorders"))
    old = tb.find(qn(f"w:{edge}"))
    new = border(edge, val, sz)
    if old is not None:
        old.addprevious(new)
        tb.remove(old)
    else:
        tb.append(new)


def merge_spanning_rows(tbl, total: int) -> None:
    rows = tbl.findall(qn("w:tr"))
    ncols = len(tbl.tblGrid.findall(qn("w:gridCol")))
    for i in spanning_rows(tbl, first=1):
        tcs = rows[i].findall(qn("w:tc"))
        for tc in tcs[1:]:
            rows[i].remove(tc)
        tcPr = tcs[0].get_or_add_tcPr()
        tcPr.find(qn("w:tcW")).set(qn("w:w"), str(total))
        for e in tcPr.findall(qn("w:gridSpan")):
            tcPr.remove(e)
        gs = OxmlElement("w:gridSpan")
        gs.set(qn("w:val"), str(ncols))
        tcPr.append(gs)
        reorder(tcPr, TCPR_ORDER)
        if i > 1:
            set_cell_border(tcs[0], "top", "single", 4)


def format_table(t, total: int, size: float, gap: float = 1) -> None:
    """Top, header and bottom rules only (a thin rule above each block label); fixed widths over the
    text block; the header row repeated on each page; single-spaced cells at `size` pt."""
    tbl = t._tbl
    pr = tbl.tblPr
    for tag in ("tblW", "tblInd", "tblLayout", "jc", "tblBorders"):
        for e in pr.findall(qn(f"w:{tag}")):
            pr.remove(e)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(total))
    tw.set(qn("w:type"), "dxa")
    pr.append(tw)
    bd = OxmlElement("w:tblBorders")
    for edge, val in (("top", "single"), ("left", "nil"), ("bottom", "single"), ("right", "nil"),
                      ("insideH", "nil"), ("insideV", "nil")):
        bd.append(border(edge, val))
    pr.append(bd)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    pr.append(lay)
    reorder(pr, TBLPR_ORDER)
    widths = col_widths(t, total, size)
    for c, w in zip(tbl.tblGrid.findall(qn("w:gridCol")), widths):
        c.set(qn("w:w"), str(w))
    rows = tbl.findall(qn("w:tr"))
    for i, tr in enumerate(rows):
        trPr = tr.get_or_add_trPr()
        for tag in ("w:cantSplit", "w:tblHeader"):
            for e in trPr.findall(qn(tag)):
                trPr.remove(e)
        trPr.append(OxmlElement("w:cantSplit"))
        if i == 0:
            trPr.append(OxmlElement("w:tblHeader"))
        for tc, w in zip(tr.findall(qn("w:tc")), widths):
            tcPr = tc.get_or_add_tcPr()
            for tag in ("w:tcW", "w:tcBorders", "w:shd"):
                for e in tcPr.findall(qn(tag)):
                    tcPr.remove(e)
            e = OxmlElement("w:tcW")
            e.set(qn("w:w"), str(w))
            e.set(qn("w:type"), "dxa")
            tcPr.append(e)
            tb = OxmlElement("w:tcBorders")
            tb.append(border("top", "single") if i == 0 else border("top", "nil"))
            tb.append(border("left", "nil"))
            tb.append(border("bottom", "single", 6) if i in (0, len(rows) - 1) else border("bottom", "nil"))
            tb.append(border("right", "nil"))
            tcPr.append(tb)
            reorder(tcPr, TCPR_ORDER)
    merge_spanning_rows(tbl, total)
    for i, row in enumerate(t.rows):
        for c in row.cells:
            for p in c.paragraphs:
                pf = p.paragraph_format
                pf.line_spacing = 1.0
                pf.space_before = Pt(gap)
                pf.space_after = Pt(gap)
                pf.keep_with_next = i == 0 or i == len(t.rows) - 1  # the last row stays with the notes
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                mark_size(p, size)
                for r in p.runs:
                    set_font(r, size)
                    if i == 0:
                        r.font.bold = True


def mark_size(p, size: float) -> None:
    """The paragraph mark at `size` pt, so that an empty cell does not set a 12 pt row height."""
    ppr = p._p.get_or_add_pPr()
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        ppr.append(rpr)
    for tag in ("w:sz", "w:szCs"):
        for e in rpr.findall(qn(tag)):
            rpr.remove(e)
        e = OxmlElement(tag)
        e.set(qn("w:val"), str(int(round(2 * size))))
        rpr.append(e)


def move_page_breaks(doc) -> None:
    """A paragraph holding only a page break is removed and the next paragraph starts a new page."""
    from docx.text.paragraph import Paragraph
    body = doc.element.body
    for p in list(body.iterchildren(qn("w:p"))):
        brs = list(p.iter(qn("w:br")))
        if not brs or any(b.get(qn("w:type")) != "page" for b in brs) or text_of(p).strip():
            continue
        nxt = p.getnext()
        if nxt is None or nxt.tag != qn("w:p"):
            continue
        Paragraph(nxt, doc._body).paragraph_format.page_break_before = True
        body.remove(p)


def highlight(doc, pattern: re.Pattern) -> None:
    for p in doc.paragraphs:
        for run in list(p.runs):
            parts = pattern.split(run.text)
            if len(parts) == 1:
                continue
            anchor = run._r
            for part in parts:
                if not part:
                    continue
                r = copy.deepcopy(run._r)
                anchor.addnext(r)
                anchor = r
                nr = Run(r, p)
                nr.text = part
                if pattern.fullmatch(part):
                    nr.font.highlight_color = WD_COLOR_INDEX.YELLOW
            run._r.getparent().remove(run._r)


APP_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           '<Company></Company><Manager></Manager></Properties>')


def scrub_app_xml(path: Path) -> None:
    tmp = path.with_suffix(".scrub")
    with zipfile.ZipFile(path) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in zi.infolist():
            data = zi.read(item.filename)
            if item.filename == "docProps/app.xml":
                data = APP_XML.encode("utf-8")
            zo.writestr(item, data)
    tmp.replace(path)


def postprocess(path: Path, *, landscape: bool = False, line_numbers: bool = False, table_pt: float = 10,
                placeholder: bool = False) -> None:
    doc = Document(str(path))
    page_setup(doc, landscape=landscape, line_numbers=line_numbers)
    move_page_breaks(doc)
    total = (16838 if landscape else 11906) - 2 * 1417
    for t in doc.tables:
        wide = not landscape and len(t.columns) >= 6
        format_table(t, total, fit_size(t, total, table_pt - 1 if wide else table_pt), gap=0 if landscape else 1)
    if placeholder:
        highlight(doc, re.compile("(" + re.escape(DOI_PLACEHOLDER) + ")"))
    cp = doc.core_properties
    for attr in ("author", "last_modified_by", "title", "comments", "keywords", "subject", "category",
                 "identifier", "content_status", "language", "version"):
        setattr(cp, attr, "")
    cp.revision = 1
    doc.save(str(path))
    scrub_app_xml(path)


# --------------------------------------------------------------------------------------
# Figures and the HTML reports
# --------------------------------------------------------------------------------------
def figures() -> list[str]:
    import fitz  # PyMuPDF
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    lines = []
    for k in range(1, N_FIGURES + 1):
        tif_name, pdf_name = figure_names(k)
        pdf = EX / f"figure{k}.pdf"
        shutil.copyfile(pdf, OUT / pdf_name)
        page = fitz.open(str(pdf))[0]
        pix = page.get_pixmap(dpi=TIFF_DPI, alpha=False, colorspace=fitz.csRGB)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        r, g, b = im.split()
        if r.tobytes() == g.tobytes() == b.tobytes():
            im = r
        tif = OUT / tif_name
        im.save(tif, format="TIFF", compression="tiff_lzw", dpi=(TIFF_DPI, TIFF_DPI))
        chk = Image.open(tif)
        w_in, h_in = page.rect.width / 72, page.rect.height / 72
        lines.append(f"{tif.name}: {chk.mode} {chk.size[0]}x{chk.size[1]} px, {chk.info.get('dpi')} dpi, "
                     f"{chk.info.get('compression')}, {w_in:.2f} x {h_in:.2f} in ({w_in * 2.54:.1f} x "
                     f"{h_in * 2.54:.1f} cm)")
    return lines


def reports() -> list[str]:
    out = []
    for dst, src in REPORTS.items():
        shutil.copyfile(ROOT / src, OUT / dst)
        out.append(f"{dst}: copy of {src} ({(OUT / dst).stat().st_size:,} bytes)")
    return out


# --------------------------------------------------------------------------------------
# Word counts (Microsoft Word, through PowerShell COM)
# --------------------------------------------------------------------------------------
def word_counts(docx: Path) -> dict:
    out = MS / "word_counts_word.json"
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(ROOT / "tools" / "word_count_word.ps1"), str(docx), str(out)], check=True)
    w = json.loads(out.read_text(encoding="utf-8-sig"))
    w["counted_by"] = ("Microsoft Word (ComputeStatistics) on 02_manuscript_anonymised.docx: abstract = Abstract "
                       "heading to the Keywords line; main text = 1. Introduction to 7. Conclusions, headings "
                       "excluded; total = every paragraph from the title to the References heading, headings "
                       "included, tables excluded")
    w["source_md5"] = hashlib.md5(read("manuscript_src.md").encode("utf-8")).hexdigest()
    out.write_text(json.dumps(w, indent=1) + "\n", encoding="utf-8", newline="\n")
    return w


def built_names() -> set[str]:
    names = {"01_title_page.docx", "02_manuscript_anonymised.docx", "03_highlights.docx", SUPPLEMENT,
             "09_cover_letter.docx", "10_declaration_of_interests.docx", "11_vitae.docx"} | set(REPORTS)
    for k in range(1, N_FIGURES + 1):
        names |= set(figure_names(k))
    return names


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    ap.add_argument("--doi", help="the Zenodo version DOI (10.5281/zenodo.NNNNNNN) for the title page")
    ap.add_argument("--no-word", action="store_true", help="skip Word's word counts")
    ap.add_argument("--manuscript-dir", default=DEFAULT_MS_DIR, help="the manuscript folder (default manuscript)")
    a = ap.parse_args(argv)  # an unknown option stops the build (argparse exits with status 2)
    if a.doi and not DOI_RE.match(a.doi):
        raise SystemExit(f"--doi must look like 10.5281/zenodo.NNNNNNN, not {a.doi!r}")
    d = Path(a.manuscript_dir)
    configure(d if d.is_absolute() else ROOT / d)
    if not MS.is_dir():
        raise SystemExit(f"{a.manuscript_dir} not present (it is private)")
    frozen = submitted_markers(MS)
    if frozen:
        raise SystemExit(f"refusing to write: {', '.join(p.name for p in frozen)} marks {MS} as submitted; "
                         f"put post-submission changes in a new folder (for example a _v2 folder)")
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ref = tmp / "reference.docx"
        make_reference(ref)
        jobs = [
            ("01_title_page.docx", title_page_md(a.doi), dict(placeholder=not a.doi)),
            ("02_manuscript_anonymised.docx", manuscript_md(), dict(line_numbers=True)),
            ("03_highlights.docx", read("highlights.md"), {}),
            (SUPPLEMENT, supplement_md(), dict(landscape=True, table_pt=8.5)),
            ("09_cover_letter.docx", letter_md("cover_letter.md"), {}),
            ("10_declaration_of_interests.docx", declaration_md(a.doi), {}),
            ("11_vitae.docx", read("vitae.md"), {}),
        ]
        for name, md, kw in jobs:
            out = OUT / name
            run_pandoc(md, out, ref, tmp)
            postprocess(out, **kw)
            print("built", name)
    for ln in figures() + reports():
        print(ln)
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name not in built_names():
            print(f"note: {f.name} is not part of this set (left from an earlier build?); remove it")
    if not a.no_word:
        w = word_counts(OUT / "02_manuscript_anonymised.docx")
        print(f"Word counts: abstract {w['abstract']}, main text {w['main_text']}, total {w['total']} "
              f"(limits 250 and 10,000)")
    print("built into", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
