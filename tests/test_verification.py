"""Mutation tests of the verification suite (analysis plan §10.3; verification/MUTATIONS.md).

Each test breaks one thing in a temporary copy of the repository (never in the repository
itself) and shows that the check that owns it fails: a headline value, a label, a rising
flag, an extracted cell, P(top-5), the plan above §12 (in a temporary clone), an unlogged
post hoc or deviation label, and a file of outputs/ that a rerun does not reproduce.
"""
import ast
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.extract import itr_state
from verification import (check_all, check_deviations, check_extraction_totals,
                          check_outputs, check_plan_order, check_rerun)

ROOT = Path(__file__).resolve().parents[1]


# ---- helpers -------------------------------------------------------------------------

@pytest.fixture(scope="module")
def committed_problems():
    return check_outputs.problems(ROOT)


@pytest.fixture
def root(tmp_path):
    """A copy of what the content checks read: outputs/, data/extracted/, the plan and the
    README."""
    r = tmp_path / "repo"
    shutil.copytree(ROOT / "outputs", r / "outputs")
    shutil.copytree(ROOT / "data" / "extracted", r / "data" / "extracted")
    (r / "docs").mkdir()
    shutil.copy2(ROOT / "docs" / "analysis_plan.md", r / "docs" / "analysis_plan.md")
    shutil.copy2(ROOT / "README.md", r / "README.md")
    return r


def edit_csv(path: Path, match: dict, column: str, fn) -> None:
    """Apply fn to ``column`` of every row matching ``match``; at least one must match."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header, rows = reader.fieldnames, list(reader)
    hits = [r for r in rows if all(r[k] == v for k, v in match.items())]
    assert hits, f"no row of {path.name} matches {match}"
    for r in hits:
        r[column] = fn(r[column])
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def fails(root: Path, *needles: str) -> list[str]:
    bad, _ = check_outputs.problems(root)
    assert bad, "check_outputs passed on a mutated copy"
    for n in needles:
        assert any(n in b for b in bad), (n, bad)
    return bad


def flip(v: str) -> str:
    return "False" if v == "True" else "True"


# ---- the checks pass on the repository ---------------------------------------------------

def test_check_outputs_is_standard_library_only():
    """§10.3: an independent recompute; nothing of src/, no numpy, no scipy."""
    tree = ast.parse((ROOT / "verification" / "check_outputs.py").read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import"
            mods.add(node.module.split(".")[0])
    assert mods and mods <= set(sys.stdlib_module_names), mods
    r = subprocess.run([sys.executable, "-I", "-c",
                        "import runpy, sys; sys.argv = ['x']; "
                        "runpy.run_path('verification/check_outputs.py', run_name='m'); "
                        "print(sorted(m for m in sys.modules if m.split('.')[0] in "
                        "('numpy', 'scipy', 'src', 'tbprio')))"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "[]", r.stdout + r.stderr


def test_check_outputs_passes_on_the_committed_outputs(committed_problems):
    bad, ok = committed_problems
    assert bad == []
    assert len(ok) == 6 and ok[0].startswith("(a) S3 2023")


def test_check_deviations_passes():
    bad, ok = check_deviations.problems(ROOT)
    assert bad == [] and ok


# ---- mutations: check_outputs -----------------------------------------------------------

def test_mutated_headline_value_fails(root):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H1"}, "value",
             lambda v: repr(float(v) + 0.01))
    fails(root, "(b) headline H1:", "(f) headline H1 value")


def test_mutated_descriptive_headline_row_fails(root):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H3 share S4"}, "value",
             lambda v: repr(float(v) - 0.001))
    fails(root, "(c) headline H3 share S4")


def test_flipped_label_fails(root):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H1"}, "label",
             lambda v: "not established")
    fails(root, "(d) headline H1 label")


def test_coherent_interval_and_label_edit_fails(root):
    """H2's interval and label edited together in headline.csv alone: the interval is
    recomputed, so the edit is caught."""
    p = root / "outputs" / "headline.csv"
    edit_csv(p, {"estimate": "H2"}, "lo", lambda v: "0.01")
    edit_csv(p, {"estimate": "H2"}, "label", lambda v: "supported")
    fails(root, "(c) headline H2 lo", "(d) headline H2 label")


def test_spec_curve_entry_sign_flip_fails(root):
    edit_csv(root / "outputs" / "spec_curve.csv",
             {"estimate": "H2", "benchmark": "p90", "shrinkage": "on",
              "denominator": "per target"}, "value", lambda v: repr(-float(v)))
    fails(root, "(c) spec_curve H2 ('p90', 'on', 'per target')", "(d) spec_curve H2")


def test_altered_rising_flag_in_priority_fails(root):
    edit_csv(root / "outputs" / "state_priority.csv", {"unit": "Bihar", "step": "S3"},
             "rising", flip)
    fails(root, "(e) state_priority Bihar S3 rising")


def test_altered_rising_flag_in_trend_fails(root):
    edit_csv(root / "outputs" / "state_trend.csv",
             {"basis": "main", "unit": "Bihar", "step": "S3"}, "rising", flip)
    fails(root, "(e) state_trend Bihar S3")


def test_tier_inconsistent_with_p_and_rising_fails(root):
    edit_csv(root / "outputs" / "state_priority.csv", {"unit": "Kerala", "step": "S3"},
             "tier", lambda v: "lower priority")
    fails(root, "(e) state_priority Kerala S3 tier")


def test_changed_extracted_panel_cell_fails(root):
    edit_csv(root / "data" / "extracted" / "state_panel.csv",
             {"unit": "Bihar", "step": "S3", "year": "2023"}, "numerator",
             lambda v: str(int(v) + 1))
    fails(root, "(a) S3 2023 prior alpha")


def test_changed_extracted_cell_fails_the_printed_totals():
    with open(itr_state.CELLS_CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert check_extraction_totals.cell_total_problems(rows) == []
    r = next(r for r in rows if r["printed_unit"] == "Bihar" and r["value"].isdigit())
    r["value"] = str(int(r["value"]) + 1)
    assert check_extraction_totals.cell_total_problems(rows)


def test_p_top5_edited_in_both_files_fails_the_independent_draws(root):
    """P(top-5) changed consistently in state_priority.csv and the summary (so the
    source-row tie holds): only the standard-library draws catch it."""
    edit_csv(root / "outputs" / "state_priority.csv", {"unit": "Kerala", "step": "S3"},
             "p_top5", lambda v: "0.05")
    edit_csv(root / "outputs" / "state_harm_draws_summary.csv",
             {"basis": "main", "step": "S3", "year": "2023", "benchmark": "p75",
              "shrinkage": "on", "unit": "Kerala"}, "p_top5", lambda v: "0.05")
    bad = fails(root, "(a) S3 2023 Kerala P(top-5)")
    assert all(b.startswith("(a)") for b in bad), bad


def test_check_outputs_main_exits_1_on_a_mutation(root, capsys):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H2"}, "label",
             lambda v: "supported")
    assert check_outputs.main(["--root", str(root)]) == 1
    assert "FAIL: (d) headline H2 label" in capsys.readouterr().out


# ---- mutations: check_plan_order (temporary clone) ----------------------------------------

def test_edit_above_section12_fails_in_a_clone(tmp_path):
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(ROOT), str(clone)], check=True)
    assert check_plan_order.problems(clone) == []
    plan = clone / "docs" / "analysis_plan.md"
    text = plan.read_text(encoding="utf-8")
    plan.write_text(text.replace("k = 5 (main)", "k = 6 (main)", 1), encoding="utf-8",
                    newline="\n")
    bad = check_plan_order.problems(clone)
    assert len(bad) == 1 and "uncommitted edit" in bad[0]
    subprocess.run(["git", "-C", str(clone), "-c", "user.name=m", "-c", "user.email=m@x",
                    "commit", "-qam", "mutation: edit above section 12"], check=True)
    bad = check_plan_order.problems(clone)
    assert len(bad) == 1 and "above section 12 differs" in bad[0]
    assert check_plan_order.main(clone) == 1


# ---- mutations: check_deviations --------------------------------------------------------

def _append_line(path: Path, line: str) -> None:
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(line + "\n")


@pytest.mark.parametrize("line, ok", [
    ("H9,0.1,,,,,,,,post hoc check", False),
    ("H9,0.1,,,,,,,,exploratory (plan §12.2)", False),        # 12.2 is not exploratory
    ("H9,0.1,,,,,,,,see plan §12.3", False),                  # no such entry
    ("H9,0.1,,,,,,,,a deviation from the plan", False),
    ("H9,0.1,,,,,,,,a deviation from the plan (§12.1)", False),  # 12.1 is no deviation
    ("H9,0.1,,,,,,,,the S6 2022 deviation (plan §12.2)", True),
    ("H9,0.1,,,,,,,,deviations are dated in plan §12", True),
])
def test_unlogged_labels_fail(root, line, ok):
    _append_line(root / "outputs" / "headline.csv", line)
    bad, _ = check_deviations.problems(root)
    assert (bad == []) is ok, bad


def test_unlogged_label_in_readme_and_data_flags_fail(root):
    _append_line(root / "README.md", "A post hoc analysis of S2.")
    edit_csv(root / "data" / "extracted" / "state_panel.csv",
             {"unit": "Bihar", "step": "S3", "year": "2023"}, "flag",
             lambda v: v + ";deviation_plan_12.9")
    bad, _ = check_deviations.problems(root)
    assert any(b.startswith("README.md line") for b in bad), bad
    assert any(b.startswith("data/extracted/state_panel.csv line") for b in bad), bad


def test_undated_section12_entry_fails(root):
    _append_line(root / "docs" / "analysis_plan.md",
                 "\n**12.3 (soon), a post hoc analysis.** Text.")
    bad, _ = check_deviations.problems(root)
    assert any("12.3 has no date" in b for b in bad), bad


def test_post_hoc_line_covered_by_a_dated_post_hoc_entry_passes(root):
    _append_line(root / "docs" / "analysis_plan.md",
                 "\n**12.3 (22 November 2026), a post hoc analysis.** Text.")
    _append_line(root / "outputs" / "headline.csv", "H9,0.1,,,,,,,,post hoc (plan §12.3)")
    bad, _ = check_deviations.problems(root)
    assert bad == []


# ---- check_rerun and check_all ----------------------------------------------------------

def test_rerun_compares_every_output_byte_for_byte(tmp_path, monkeypatch):
    out = tmp_path / "outputs"
    out.mkdir()
    (out / "a.csv").write_bytes(b"x\n1\n")
    (out / "b.html").write_bytes(b"<p>b</p>\n")
    (out / "README.md").write_bytes(b"not generated\n")
    made = {"a.csv": b"x\n1\n", "b.html": b"<p>b</p>\n"}

    def fake(root, tmp):
        d = tmp / "run"
        d.mkdir(exist_ok=True)
        res = {}
        for name, data in made.items():
            (d / name).write_bytes(data)
            res[name] = [d / name]
        return res

    monkeypatch.setattr(check_rerun, "rerun", fake)
    assert check_rerun.problems(tmp_path) == ([], 2)
    made["a.csv"] = b"x\n2\n"
    bad, _ = check_rerun.problems(tmp_path)
    assert bad == ["outputs/a.csv differs from the rerun (run)"]
    del made["a.csv"]
    bad, _ = check_rerun.problems(tmp_path)
    assert bad == ["outputs/a.csv is not produced by any rerun"]
    made["c.csv"] = b"c\n"
    bad, _ = check_rerun.problems(tmp_path)
    assert "the rerun produces c.csv, which is not in outputs/" in bad


def test_check_all_skips_the_manuscript_steps_without_a_manuscript(tmp_path, monkeypatch):
    monkeypatch.setattr(check_all, "ROOT", tmp_path)
    for name in check_all.MANUSCRIPT_STEPS:
        assert check_all.skip_reason(name, []).startswith("SKIPPED")
    assert check_all.skip_reason("check_outputs", []) is None
    (tmp_path / "manuscript").mkdir()
    (tmp_path / "manuscript" / "manuscript_src.md").write_text("x", encoding="utf-8")
    assert check_all.skip_reason("check_docx_tie", []) is None
    names = [n for n, _ in check_all.STEPS]
    assert names[0] == "pytest -q" and names[-2:] == list(check_all.MANUSCRIPT_STEPS)
    for step in ("check_plan_order", "check_deviations", "check_extraction_totals",
                 "check_outputs"):
        assert step in names
    assert any(n.startswith("check_rerun") for n in names)
