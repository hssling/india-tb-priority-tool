# Adapted from hssling/india-tb-acf-campaign (MIT), verification/mutate_manuscript.py (itself adapted
# from hssling/india-state-tb-score); modified: one set of named mutations for this paper's
# Evaluation and Program Planning set (numbers, anonymisation, references, table cells, labels,
# signs, identifiers, wording, highlights, the abstract limit, the AI declaration, caveats, figures,
# reports and the file set), applied to copies inside the git-ignored manuscript folder; the
# number-token sweeps kept as --sweep.
"""Mutation test of the manuscript checks (check_manuscript_numbers and check_docx_tie).

Run as: python -I verification/mutate_manuscript.py [--manuscript-dir DIR] [--sweep]

The manuscript folder DIR (default manuscript/; git-ignored) is copied for every mutation into
DIR/_mutations/ (removed afterwards); the real files are never written. The large binary files of
submission/ (TIFF, PDF, HTML) are hard-linked into each copy, and a mutation that changes one of
them replaces the link with a new file. Each named mutation (MUTATIONS) changes one thing in the
copy, and both checks run on it: check_manuscript_numbers.problems and check_docx_tie.problems. A
mutation is caught if either reports at least one problem. The unmutated copy must pass both, or
nothing is run.

The manuscript text a mutation edits (its anchor) quotes the manuscript, so it is not kept here: it
is read from "mutation_anchors" in the private DIR/section_phrases.json. A mutation whose anchor is
missing or not found counts as NOT APPLIED and fails the run.

--sweep also bumps the last digit of every number token (a) of manuscript_src.md outside the
References, which check_manuscript_numbers must catch, and (b) of the text of
02_manuscript_anonymised.docx, tables and references included, which check_docx_tie must catch.

Prints a table of the results; exits 1 if any mutation is not applied or not caught. Prints
"SKIPPED" and exits 0 when DIR/ or DIR/submission/ is absent.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verification import check_docx_tie as tie  # noqa: E402
from verification import check_manuscript_numbers as cmn  # noqa: E402

DOC = "word/document.xml"
CORE = "docProps/core.xml"
S = "submission/"
T01, M02, H03, S08 = (S + n for n in ("01_title_page.docx", "02_manuscript_anonymised.docx", "03_highlights.docx",
                                      "08_supplementary_material.docx"))
FIG1_TIF, FIG1_PDF = (S + n for n in tie.FIGURES[1])
REPORT = S + next(iter(tie.REPORTS))
NUMBER = re.compile(r"\d+(?:,\d{3}(?!\d))*(?:\.\d+)?")
WORK = "_mutations"
LINKED = (".tif", ".pdf", ".html")


class NotApplied(Exception):
    """The mutation's anchor was not found in the copy."""


# --------------------------------------------------------------------------------------
# Editing helpers (on the copy; a file is replaced, never written through a hard link)
# --------------------------------------------------------------------------------------
def replace_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".new")
    tmp.write_bytes(data)
    path.unlink()
    tmp.replace(path)


def edit_text(path: Path, old: str, new: str) -> None:
    s = path.read_text(encoding="utf-8")
    if old not in s:
        raise NotApplied(f"{path.name}: {old!r} not found")
    replace_bytes(path, s.replace(old, new, 1).encode("utf-8"))


def rewrite_part(path: Path, part: str, fn: Callable[[str], str]) -> None:
    tmp = path.with_name(path.name + ".mut")
    with zipfile.ZipFile(path) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in zi.infolist():
            data = zi.read(item.filename)
            if item.filename == part:
                data = fn(data.decode("utf-8")).encode("utf-8")
            zo.writestr(item, data)
    path.unlink()
    tmp.replace(path)


def edit_docx(path: Path, old: str, new: str, part: str = DOC) -> None:
    def fn(xml: str) -> str:
        if old not in xml:
            raise NotApplied(f"{path.name}:{part}: {old!r} not found")
        return xml.replace(old, new, 1)
    rewrite_part(path, part, fn)


def set_creator(path: Path, name: str) -> None:
    def fn(xml: str) -> str:
        tag = f"<dc:creator>{name}</dc:creator>"
        out, n = re.subn(r"<dc:creator\s*/>|<dc:creator>[^<]*</dc:creator>", tag, xml, count=1)
        if n == 0:
            out, n = re.subn(r"</cp:coreProperties>", tag + "</cp:coreProperties>", xml, count=1)
        if n == 0:
            raise NotApplied(f"{path.name}: no coreProperties element")
        return out
    rewrite_part(path, CORE, fn)


def bump(tok: str) -> str:
    return tok[:-1] + str((int(tok[-1]) + 1) % 10)


def bumped(s: str) -> str:
    m = NUMBER.search(s)
    if not m:
        raise NotApplied(f"no number in anchor {s!r}")
    return s[:m.start()] + bump(m.group()) + s[m.end():]


def flipped(s: str) -> str:
    m = NUMBER.search(s)
    if not m:
        raise NotApplied(f"no number in anchor {s!r}")
    if m.start() > 0 and s[m.start() - 1] == cmn.MINUS:
        return s[:m.start() - 1] + s[m.start():]
    return s[:m.start()] + cmn.MINUS + s[m.start():]


def anchor(d: Path, mid: str):
    try:
        a = cmn.load_phrase_file(d).get("mutation_anchors", {}).get(mid)
    except (OSError, ValueError) as e:
        raise NotApplied(f"{cmn.PHRASES}: {e}") from None
    if not a:
        raise NotApplied(f"no anchor for mutation {mid} in {cmn.PHRASES}")
    return a


def change(edit, rel: str, mid: str, how: Callable[[str], str]) -> Callable[[Path], None]:
    def fn(d: Path) -> None:
        a = anchor(d, mid)
        edit(d / rel, a, how(a))
    return fn


def insert(edit, rel: str, mid: str, extra: Callable[[Path], str], before: bool = False) -> Callable[[Path], None]:
    def fn(d: Path) -> None:
        a, x = anchor(d, mid), extra(d)
        edit(d / rel, a, x + a if before else a + x)
    return fn


def swap(edit, rel: str, mid: str) -> Callable[[Path], None]:
    """The anchor is a pair [old, new]."""
    def fn(d: Path) -> None:
        a = anchor(d, mid)
        if not (isinstance(a, list) and len(a) == 2):
            raise NotApplied(f"anchor of {mid} must be a pair [old, new]")
        edit(d / rel, a[0], a[1])
    return fn


def renumber_refs(d: Path) -> None:
    """02 References: the entry numbers [2] and [3] exchanged."""
    def fn(xml: str) -> str:
        for a, b in (("[2] ", "[@@] "), ("[3] ", "[2] "), ("[@@] ", "[3] ")):
            i = xml.find(">" + a, xml.find(">References<"))
            if i < 0:
                raise NotApplied(f"02: reference entry {a!r} not found")
            xml = xml[:i + 1] + b + xml[i + 1 + len(a):]
        return xml
    rewrite_part(d / M02, DOC, fn)


def author_name() -> str:
    return "Siddalingaiah H S"


def email(d: Path) -> str:
    hits = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", (d / cmn.TITLE_PAGE).read_text(encoding="utf-8"))
    if not hits:
        raise NotApplied("no e-mail on the title page")
    return hits[0]


def repo_url() -> str:
    head = cmn.plan_text(ROOT).split("\n---", 1)[0]
    return re.search(r"\*\*Repository:\*\* (\S+)", head).group(1)


def low_dpi_tiff(d: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        raise NotApplied("Pillow not installed") from None
    p = d / FIG1_TIF
    p.unlink()
    Image.new("L", (100, 100), 255).save(p, format="TIFF", dpi=(300, 300))


def other_figure(d: Path) -> None:
    replace_bytes(d / FIG1_PDF, (d / "exhibits" / "figure2.pdf").read_bytes())


def edit_report(d: Path) -> None:
    p = d / REPORT
    data = p.read_bytes()
    i = data.find(b"</body>")
    if i < 0:
        raise NotApplied("report has no </body>")
    replace_bytes(p, data[:i] + b"<!-- x -->" + data[i:])


def edit_figure_data(d: Path) -> None:
    p = d / "exhibits" / "figure1_data.csv"
    s = p.read_text(encoding="utf-8")
    if ",act now," not in s:
        raise NotApplied("figure1_data.csv has no act-now row")
    replace_bytes(p, s.replace(",act now,", ",lower priority,", 1).encode("utf-8"))


def extra_file(d: Path) -> None:
    (d / S / "14_notes.txt").write_text("x", encoding="utf-8")


def drop_file(d: Path) -> None:
    (d / S / "11_vitae.docx").unlink()


# --------------------------------------------------------------------------------------
# The named mutations: (id, kind, what is changed, function of the copied folder)
# --------------------------------------------------------------------------------------
Mutation = tuple[str, str, str, Callable[[Path], None]]
MS = cmn.MS_NAME
MUTATIONS: list[Mutation] = [
    ("1a", "number, docx only", "02 Results: the H1 value changed in its last digit", change(edit_docx, M02, "1a", bumped)),
    ("1b", "number, docx only", "01 title page: Word's abstract count increased by 1", change(edit_docx, T01, "1b", bumped)),
    ("1c", "number, docx only", "08 Table S2: a harm-averted cell changed in its last digit", change(edit_docx, S08, "1c", bumped)),
    ("2a", "number, markdown only", "manuscript_src.md Results: the H2 value changed in its last digit", change(edit_text, MS, "2a", bumped)),
    ("2b", "number, markdown only", "manuscript_src.md Abstract: the count of rising units increased by 1", change(edit_text, MS, "2b", bumped)),
    ("2c", "number, markdown only", "highlights.md: the count of rising units increased by 1", change(edit_text, cmn.HIGHLIGHTS, "2c", bumped)),
    ("2d", "number, markdown only", "manuscript_src.md Methods: the registration time changed", change(edit_text, MS, "2d", bumped)),
    ("3a", "author name, anonymised docx", "02 Discussion: the author's name inserted",
     insert(edit_docx, M02, "3a", lambda d: f" ({author_name()})")),
    ("3b", "author name, anonymised docx", "02 document properties: author (dc:creator) set to the name",
     lambda d: set_creator(d / M02, author_name())),
    ("3c", "author e-mail, anonymised docx", "08 note under Table S1: the author's e-mail inserted",
     insert(edit_docx, S08, "3c", lambda d: email(d) + " ", before=True)),
    ("3d", "repository URL, anonymised docx", "02 Methods: the placeholder replaced by the repository URL",
     lambda d: edit_docx(d / M02, cmn.PLACEHOLDER, repo_url())),
    ("3e", "author name, anonymised docx", "03 highlights: the author's name inserted",
     insert(edit_docx, H03, "3e", lambda d: f" ({author_name()})")),
    ("3f", "institution, markdown", "manuscript_src.md Methods: the institution inserted",
     insert(edit_text, MS, "3f", lambda d: " (Shridevi Institute of Medical Sciences and Research Hospital)")),
    ("3g", "author name, anonymised docx", "08 document properties: author (dc:creator) set to the name",
     lambda d: set_creator(d / S08, author_name())),
    ("4a", "reference number, markdown", "manuscript_src.md Methods: a citation number increased by 1", change(edit_text, MS, "4a", bumped)),
    ("4b", "reference number, docx only", "02 Methods: the same citation number increased by 1", change(edit_docx, M02, "4a", bumped)),
    ("4c", "reference number, docx only", "02 References: entries [2] and [3] renumbered [3] and [2]", renumber_refs),
    ("4d", "reference order, markdown", "manuscript_src.md Introduction: two first citations exchanged", swap(edit_text, MS, "4d")),
    ("5a", "table cell, docx only", "02 Table 1: the top-five overlap cell changed", change(edit_docx, M02, "5a", bumped)),
    ("5b", "table cell, markdown only", "tables.md Table 2: a unit moved between tiers", swap(edit_text, "exhibits/tables.md", "5b")),
    ("5c", "table cell, docx only", "08 Table S10: a district's harm averted changed", change(edit_docx, S08, "5c", bumped)),
    ("5d", "figure data, exhibits", "figure1_data.csv: an act-now cell set to lower priority", edit_figure_data),
    ("6a", "label, markdown", "manuscript_src.md Results: H1 'supported' -> 'not established'", swap(edit_text, MS, "6a")),
    ("6b", "label, docx only", "02 Abstract: H2 'not established' -> 'supported'", swap(edit_docx, M02, "6b")),
    ("6c", "label, markdown", "manuscript_src.md Results: H2 called 'validated'", swap(edit_text, MS, "6c")),
    ("7a", "sign, markdown", "manuscript_src.md Results: the lower limit of H2 made positive", change(edit_text, MS, "7a", flipped)),
    ("7b", "sign, docx only", "08 Table S12: Chhatarpur's change made positive", change(edit_docx, S08, "7b", flipped)),
    ("8a", "internal identifier, markdown", "manuscript_src.md Methods: '(Task 8)' inserted",
     insert(edit_text, MS, "8a", lambda d: " (Task 8)")),
    ("8b", "internal identifier, docx only", "08 note under Table S1: 'ITR2024' inserted",
     insert(edit_docx, S08, "3c", lambda d: "ITR2024 ", before=True)),
    ("8c", "wording, markdown", "manuscript_src.md Lessons learned: 'missed cases' for the shortfall", swap(edit_text, MS, "8c")),
    ("8d", "wording, markdown", "manuscript_src.md Discussion: a causal claim inserted",
     insert(edit_text, MS, "8d", lambda d: " The programme caused these gaps.")),
    ("8e", "wording, docx only", "02 Results: ranking language inserted",
     insert(edit_docx, M02, "8e", lambda d: " Bihar ranked first.")),
    ("8f", "spelling, markdown", "manuscript_src.md Discussion: 'programme' written 'program'", swap(edit_text, MS, "8f")),
    ("9a", "highlight length, markdown", "highlights.md: a bullet made longer than 85 characters",
     insert(edit_text, cmn.HIGHLIGHTS, "9a", lambda d: " in every State and Union Territory")),
    ("9b", "highlight length, docx only", "03: a bullet made longer than 85 characters",
     insert(edit_docx, H03, "9a", lambda d: " in every State and Union Territory")),
    ("9c", "abstract limit, markdown", "manuscript_src.md Abstract: twelve words added",
     insert(edit_text, MS, "9c", lambda d: " This sentence adds exactly twelve more words to the abstract for this test.")),
    ("10a", "AI declaration, title page", "title_page_src.md: the AI declaration changed", swap(edit_text, cmn.TITLE_PAGE, "10a")),
    ("10b", "caveat, markdown", "manuscript_src.md Methods: the notification caveat removed", swap(edit_text, MS, "10b")),
    ("10c", "caveat, markdown", "manuscript_src.md Figure captions: '(historical)' removed", swap(edit_text, MS, "10c")),
    ("11a", "figure, PDF", "04_Figure_1.pdf replaced by Figure 2", other_figure),
    ("11b", "figure, TIFF", "04_Figure_1.tif replaced by a 300 dpi image", low_dpi_tiff),
    ("12a", "report", "12 State report: one comment added", edit_report),
    ("13a", "file set", "an extra file in submission/", extra_file),
    ("13b", "file set", "11_vitae.docx removed", drop_file),
]


# --------------------------------------------------------------------------------------
# Running the checks on a copy
# --------------------------------------------------------------------------------------
def copy_manuscript(src: Path, dst: Path) -> Path:
    """A copy of the folder, without the render output, the PNG previews and the mutation work
    folder; the large binary files of submission/ are hard-linked."""
    def ignore(d: str, names: list[str]) -> set[str]:
        return {n for n in names if n in ("_render", "__pycache__", WORK) or n.endswith(".png")}

    def copy_fn(s: str, t: str) -> None:
        if s.endswith(LINKED) and "submission" in Path(s).parts:
            try:
                os.link(s, t)
                return
            except OSError:
                pass
        shutil.copy2(s, t)
    shutil.copytree(src, dst, ignore=ignore, copy_function=copy_fn)
    return dst


def cmn_problems(ms_dir: Path) -> list[str]:
    if not (ms_dir / cmn.PHRASES).exists():
        return [f"PHRASES: {cmn.PHRASES} missing"]
    return cmn.problems(ROOT, ms_dir)


def tie_problems(ms_dir: Path) -> list[str]:
    return tie.problems(ms_dir, ROOT)


def run_named(src: Path, mutations: list[Mutation] | None = None) -> list[dict]:
    mutations = MUTATIONS if mutations is None else mutations
    checks = {"check_manuscript_numbers": cmn_problems, "check_docx_tie": tie_problems}
    rows = []
    work = src / WORK
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    try:
        base = copy_manuscript(src, work / "base")
        for name, fn in checks.items():
            found = fn(base)
            if found:
                raise SystemExit(f"the unmutated copy fails {name}; fix that first:\n" + "\n".join(found[:5]))
        shutil.rmtree(base, ignore_errors=True)
        for mid, kind, what, fn in mutations:
            d = copy_manuscript(src, work / f"m{mid}")
            row = {"id": mid, "kind": kind, "what": what, "applied": True, "by": [], "first": ""}
            try:
                fn(d)
            except NotApplied as e:
                row.update(applied=False, first=str(e))
                rows.append(row)
                shutil.rmtree(d, ignore_errors=True)
                continue
            for name, check in checks.items():
                found = check(d)
                if found:
                    row["by"].append(name)
                    row["first"] = row["first"] or found[0].splitlines()[0]
            rows.append(row)
            shutil.rmtree(d, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return rows


# --------------------------------------------------------------------------------------
# Sweeps over every number token
# --------------------------------------------------------------------------------------
def md_token_spans(text: str) -> list[tuple[int, int]]:
    spans, pos, in_refs = [], 0, False
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            in_refs = line.strip() == "## References"
        elif not in_refs:
            spans += [(pos + m.start(), pos + m.end()) for m in NUMBER.finditer(line)]
        pos += len(line)
    return spans


def sweep_md(ms: Path) -> tuple[int, int, list[str]]:
    text = (ms / cmn.MS_NAME).read_text(encoding="utf-8")
    gold, required = cmn.load_gold(ms), cmn.section_phrases(ms)
    hl = (ms / cmn.HIGHLIGHTS).read_text(encoding="utf-8")
    caught, escaped = 0, []
    spans = md_token_spans(text)
    for a, b in spans:
        mutated = text[:a] + bump(text[a:b]) + text[b:]
        if cmn.problems(ROOT, ms, mutated, gold, required, hl, exhibits=False):
            caught += 1
        else:
            escaped.append(f"...{text[max(0, a - 30):b + 10]}...".replace("\n", " "))
    return caught, len(spans), escaped


def sweep_docx(path: Path, want: list[str]) -> tuple[int, int, list[str]]:
    with zipfile.ZipFile(path) as z:
        xml = z.read(DOC).decode("utf-8")
    spans = []
    for m in re.finditer(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml):
        spans += [(m.start(1) + t.start(), m.start(1) + t.end()) for t in NUMBER.finditer(m.group(1))]
    caught, escaped = 0, []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / path.name
        for a, b in spans:
            shutil.copyfile(path, tmp)
            rewrite_part(tmp, DOC, lambda _x, a=a, b=b: xml[:a] + bump(xml[a:b]) + xml[b:])
            if tie.compare(path.name, tie.docx_units(tmp), want):
                caught += 1
            else:
                escaped.append(xml[max(0, a - 40):b + 10])
    return caught, len(spans), escaped


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ms, rest = cmn.manuscript_dir(root, argv)
    unknown = [a for a in rest if a != "--sweep"]
    if unknown:
        print(f"FAIL: unknown arguments {unknown}")
        return 1
    name = cmn.rel(ms, root)
    if not ms.is_dir() or not (ms / "submission").is_dir():
        print(f"SKIPPED: {name}/ or {name}/submission/ not present (kept private, not in this repository)")
        return 0
    rows = run_named(ms)
    bad = 0
    print("| # | Kind | Mutation | Caught by | First problem reported |")
    print("|---|------|----------|-----------|------------------------|")
    for r in rows:
        res = "NOT APPLIED" if not r["applied"] else (" and ".join(r["by"]) if r["by"] else "NOT CAUGHT")
        bad += res in ("NOT APPLIED", "NOT CAUGHT")
        print(f"| {r['id']} | {r['kind']} | {r['what']} | {res} | {r['first'].replace('|', '/')[:110]} |")
    print(f"named mutations: {len(rows) - bad} of {len(rows)} caught")
    if "--sweep" in rest:
        c, t, e = sweep_md(ms)
        print(f"sweep, manuscript_src.md number tokens (check_manuscript_numbers): caught {c} of {t}")
        for x in e:
            print("  UNCAUGHT", x)
        p = ms / M02
        c2, t2, e2 = sweep_docx(p, tie.expected(ms, p.name))
        print(f"sweep, {p.name} number tokens (check_docx_tie): caught {c2} of {t2}")
        for x in e2:
            print("  UNCAUGHT", x)
        bad += len(e) + len(e2)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
