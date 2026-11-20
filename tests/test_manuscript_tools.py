"""Tests of the manuscript tooling: exhibits, the submission build's guards and the manuscript checks.

None of these tests needs the private manuscript folder; they use outputs/ and temporary folders.
"""
import csv
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exhibits import formats, make_figures, make_tables  # noqa: E402
from verification import check_docx_tie as tie  # noqa: E402
from verification import check_manuscript_numbers as cmn  # noqa: E402
from verification import mutate_manuscript as mut  # noqa: E402


# ---- formats -------------------------------------------------------------------------------
def test_formats():
    assert formats.num(-0.1456, 3) == "−0.146"
    assert formats.count(52951.5) == "52,952"
    assert formats.harm("52951.5", "52109.3", "53797.1") == "52,952 (52,109 to 53,797)"
    assert formats.prob(1.0) == "1" and formats.prob(0.0) == "0"
    assert formats.prob(0.9996) == ">0.999" and formats.prob(0.998) == "0.998"
    assert formats.prob(0.772) == "0.77"
    assert formats.pct(0.58749) == "58.7%"
    assert formats.and_list(["A", "B", "C"]) == "A, B and C"


# ---- tables ---------------------------------------------------------------------------------
def test_tables_are_in_citation_order_and_csv_equals_markdown():
    tables = make_tables.build(ROOT)
    labels = [t.label for t in tables]
    assert labels == ["Table 1", "Table 2"] + [f"Table S{k}" for k in range(1, 13)]
    md = make_tables.render_md(tables)
    for t in tables:
        rows = list(csv.reader(io.StringIO(make_tables.csv_bytes(t).decode("utf-8"))))
        assert rows[0] == t.header and len(rows) == len(t.rows) + 1
    assert md.count("\n## Table ") == len(tables)


def test_table1_labels_are_the_outputs_labels():
    t1 = make_tables.build(ROOT)[0]
    with open(ROOT / "outputs" / "headline.csv", newline="", encoding="utf-8") as f:
        hl = {r["estimate"]: r["label"] for r in csv.DictReader(f)}
    row = {r[0]: r[-1] for r in t1.rows}
    assert row["H1"] == hl["H1"] and row["H2"] == hl["H2"]


def test_table2_lists_every_unit_once_per_step():
    t2 = make_tables.build(ROOT)[1]
    for r in t2.rows:
        named = [x for c in r[1:5] if c != make_tables.DASH for x in c.split(", ")]
        assert len(named) + int(r[5]) == 33


def test_figure_data_come_from_outputs():
    rows = make_figures.fig1_data(ROOT)
    assert len(rows) == 198
    assert {r["letter"] for r in rows} <= {"A", "P", "U", "W", ""}
    assert len(make_figures.fig2_data(ROOT)) == 6 * make_figures.TOP_N
    assert make_figures.data_csv(rows) == make_figures.data_csv(make_figures.fig1_data(ROOT))


# ---- the build's guards ----------------------------------------------------------------------
def test_build_refuses_a_submitted_folder(tmp_path):
    bs = pytest.importorskip("tools.build_submission")
    (tmp_path / "submission").mkdir()
    (tmp_path / "submission" / "SUBMITTED_2026-11-21.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        bs.main(["--manuscript-dir", str(tmp_path), "--no-word"])
    assert "refusing to write" in str(e.value)
    (tmp_path / "submission" / "SUBMITTED_2026-11-21.txt").unlink()
    (tmp_path / "SUBMITTED_2026-11-22.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        bs.main(["--manuscript-dir", str(tmp_path), "--no-word"])
    assert "refusing to write" in str(e.value)


def test_build_rejects_unknown_options(tmp_path):
    bs = pytest.importorskip("tools.build_submission")
    with pytest.raises(SystemExit) as e:
        bs.main(["--manuscript-dir", str(tmp_path), "--frobnicate"])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        bs.main(["--manuscript-dir", str(tmp_path), "--do", "10.5281/zenodo.1"])  # no abbreviations
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        bs.main(["--manuscript-dir", str(tmp_path), "--doi", "10.1000/x"])
    assert "--doi must look like" in str(e.value)


# ---- the checks skip, fail and reject as documented -----------------------------------------
def test_checks_skip_without_the_private_folder(tmp_path, capsys):
    absent = ["--manuscript-dir", str(tmp_path / "none")]
    assert cmn.main(ROOT, absent) == 0
    assert tie.main(ROOT, absent) == 0
    assert mut.main(absent, ROOT) == 0
    out = capsys.readouterr().out
    assert out.count("SKIPPED") == 3


def test_number_check_fails_without_its_phrases(tmp_path, capsys):
    (tmp_path / "manuscript_src.md").write_text("# T\n", encoding="utf-8")
    assert cmn.main(ROOT, ["--manuscript-dir", str(tmp_path)]) == 1
    assert "section_phrases.json is missing" in capsys.readouterr().out
    assert cmn.main(ROOT, ["--manuscript-dir", str(tmp_path), "--bogus"]) == 1


def test_references_in_order_of_first_citation():
    ok = "Text [1] and [2,3].\n\n## References\n\n[1] a. https://doi.org/x\n\n[2] b. https://doi.org/y\n\n[3] c. https://doi.org/z\n"
    assert cmn.reference_problems(ok) == []
    bad = ok.replace("Text [1] and [2,3]", "Text [2] and [1,3]")
    assert any("first citation" in p for p in cmn.reference_problems(bad))
    never = ok.replace(" and [2,3]", "")
    assert any("never cited" in p for p in cmn.reference_problems(never))


def test_highlight_and_abstract_limits():
    text = "# T\n\n## Abstract\n\n" + "word " * 251 + "\n\n**Keywords:** A; B\n\n## 1. Introduction\n\nx\n"
    hl = "# Highlights\n\n- " + "x" * 86 + "\n- short\n"
    found = cmn.length_problems(text, hl)
    assert any("abstract 251 words" in p for p in found)
    assert any("HIGHLIGHTS: 2 bullets" in p for p in found)
    assert any("86 characters" in p for p in found)


def test_wording_rules():
    found = cmn.wording_problems("x.md", "The missed cases were ranked first; the program caused it.", ROOT, None,
                                 anonymised=False)
    kinds = " ".join(found)
    assert "missed cases" in kinds and "ranking" in kinds and "causal" in kinds and "program" in kinds
    assert cmn.wording_problems("x.md", "Evaluation and Program Planning", ROOT, None, anonymised=False) == []
    marks = cmn.author_markers(ROOT)
    assert any("Siddalingaiah" in m for m in marks) and "0000-0002-4771-8285" in marks


def test_docx_tie_units_normalise_both_sides():
    md = "# Title\n\n**Bold** text\nwrapped.\n\n- a bullet\n\n[1] A reference.\n\n| a | b |\n|---|---|\n| **L** | |\n"
    assert tie.md_units(md) == ["Title", "Bold text wrapped.", "a bullet", "[1] A reference.", "a | b", "L"]
    assert tie.norm("10.5281/zenodo.XXXXXXX") == tie.norm("10.5281/zenodo.123")
