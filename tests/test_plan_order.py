"""Tests of verification/check_plan_order.py on synthetic temporary git repositories
(never the real repository)."""
import json
import subprocess

import pytest

from verification import check_plan_order

PLAN = "# Plan\n\nBefore.\n\n## 12. Deviations (dated)\n"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
                   check=True, capture_output=True)


def commit(repo, files, msg):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))
        git(repo, "add", rel)
    git(repo, "commit", "-m", msg)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


def event(sha):
    return json.dumps({"registered_commit": sha, "pushed_at": "2026-11-21T00:00:00Z"})


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    return tmp_path


def test_clean_history_passes_and_section12_edit_is_allowed(repo, capsys):
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    commit(repo, {"docs/registration_event.json": event(reg)}, "registration event")
    commit(repo, {"docs/analysis_plan.md": PLAN + "\n**22 November 2026.** A deviation.\n"},
           "deviation")
    commit(repo, {"src/tbprio/harm.py": "x = 1\n", "outputs/state_priority.csv": "a\n"},
           "estimates")
    assert check_plan_order.problems(repo, reg) == []
    assert check_plan_order.main(repo) == 0
    assert capsys.readouterr().out.startswith("OK:")


def test_missing_registration_event_is_not_registered_yet(repo, capsys):
    commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    assert check_plan_order.main(repo) == 1
    out = capsys.readouterr().out
    assert out.startswith("FAIL: NOT REGISTERED YET")
    assert "docs/registration_event.json does not exist" in out


def test_registration_event_without_commit_fails(repo, capsys):
    commit(repo, {"docs/analysis_plan.md": PLAN,
                  "docs/registration_event.json": json.dumps({"pushed_at": "x"})}, "plan")
    assert check_plan_order.main(repo) == 1
    assert "names no registration commit" in capsys.readouterr().out


def test_unknown_registration_commit_fails(repo, capsys):
    commit(repo, {"docs/analysis_plan.md": PLAN,
                  "docs/registration_event.json": event("0" * 40)}, "plan")
    assert check_plan_order.main(repo) == 1
    assert "does not exist" in capsys.readouterr().out


def test_output_committed_before_registration_is_flagged(repo, capsys):
    commit(repo, {"outputs/state_priority.csv": "a\n"}, "output first")
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    commit(repo, {"docs/registration_event.json": event(reg)}, "registration event")
    bad = check_plan_order.problems(repo, reg)
    assert len(bad) == 1 and "not a descendant" in bad[0]
    assert check_plan_order.main(repo) == 1
    assert capsys.readouterr().out.startswith("FAIL: commit")


@pytest.mark.parametrize("module", ["harm", "shrink", "priority", "trend"])
def test_estimation_module_before_registration_is_flagged(repo, module):
    commit(repo, {f"src/tbprio/{module}.py": "x = 1\n"}, "module first")
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    bad = check_plan_order.problems(repo, reg)
    assert len(bad) == 1 and "src/tbprio/" in bad[0]


def test_estimation_module_in_registration_commit_is_flagged(repo):
    reg = commit(repo, {"docs/analysis_plan.md": PLAN, "src/tbprio/shrink.py": "x\n"},
                 "plan+code")
    assert len(check_plan_order.problems(repo, reg)) == 1


def test_any_tbprio_module_before_registration_is_flagged(repo):
    """All of src/tbprio/ is guarded; the allow-list is empty."""
    assert check_plan_order.ALLOWED == ()
    commit(repo, {"src/tbprio/panel.py": "x = 1\n"}, "loader first")
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    bad = check_plan_order.problems(repo, reg)
    assert len(bad) == 1 and "src/tbprio/" in bad[0]


def test_allow_listed_loader_and_extraction_code_before_registration_pass(repo):
    commit(repo, {"src/tbprio/panel.py": "x = 1\n", "src/extract/itr_state.py": "y = 1\n"},
           "loader first")
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    assert check_plan_order.problems(repo, reg, allowed=("src/tbprio/panel.py",)) == []


def test_allow_list_does_not_cover_a_second_module_in_the_same_commit(repo):
    commit(repo, {"src/tbprio/panel.py": "x\n", "src/tbprio/validate.py": "y\n"}, "two")
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    assert len(check_plan_order.problems(repo, reg, allowed=("src/tbprio/panel.py",))) == 1


def test_renamed_tbprio_module_before_registration_is_flagged(repo):
    commit(repo, {"src/scratch.py": "x = 1\n"}, "scratch")
    git(repo, "mv", "src/scratch.py", "src/tbprio_tmp.py")
    git(repo, "commit", "-q", "-m", "rename outside")
    (repo / "src" / "tbprio").mkdir()
    git(repo, "mv", "src/tbprio_tmp.py", "src/tbprio/harm.py")
    git(repo, "commit", "-q", "-m", "rename into tbprio")
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    assert len(check_plan_order.problems(repo, reg)) == 1


def test_moved_registration_anchor_is_flagged(repo, capsys):
    """A later commit may not re-point the registration record at another commit."""
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    commit(repo, {"docs/registration_event.json": event(reg)}, "registration event")
    commit(repo, {"docs/analysis_plan.md": PLAN.replace("Before.", "Changed.")}, "edit")
    later = commit(repo, {"outputs/x.csv": "a\n"}, "output")
    commit(repo, {"docs/registration_event.json": event(later)}, "move the anchor")
    assert check_plan_order.main(repo) == 1
    assert "the anchor must never move" in capsys.readouterr().out


def test_deleted_then_restored_registration_event_is_flagged(repo):
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    commit(repo, {"docs/registration_event.json": event(reg)}, "registration event")
    git(repo, "rm", "-q", "docs/registration_event.json")
    git(repo, "commit", "-q", "-m", "delete event")
    commit(repo, {"docs/registration_event.json": event(reg)}, "restore event")
    bad = check_plan_order.problems(repo, reg)
    assert len(bad) == 1 and "names no commit" in bad[0]


def test_old_plan_on_a_branch_merged_after_registration_is_not_a_later_commit(repo):
    """--ancestry-path: a side commit made before registration, merged after it, is not
    one of the commits whose plan text must equal the registered text."""
    commit(repo, {"README.md": "r\n"}, "root")
    git(repo, "checkout", "-q", "-b", "side")
    commit(repo, {"docs/analysis_plan.md": PLAN.replace("Before.", "Draft.")}, "draft plan")
    git(repo, "checkout", "-q", "-")
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    git(repo, "merge", "-q", "-s", "ours", "side", "-m", "merge, keeping our tree")
    assert check_plan_order.problems(repo, reg) == []


def test_output_on_a_merged_side_branch_is_found_over_the_full_history(repo):
    """History simplification would hide a side-branch commit whose change a merge drops."""
    commit(repo, {"README.md": "r\n"}, "root")
    git(repo, "checkout", "-q", "-b", "side")
    side = commit(repo, {"outputs/headline.csv": "a\n"}, "output on a side branch")
    git(repo, "checkout", "-q", "-")
    git(repo, "merge", "-q", "-s", "ours", "side", "-m", "merge, keeping our tree")
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    bad = check_plan_order.problems(repo, reg)
    # the side-branch commit is named; the merge that dropped its change is reported too
    assert any(b.startswith(f"commit {side[:7]} ") for b in bad)
    assert all("not a descendant" in b for b in bad)


def test_edit_above_section12_is_flagged(repo, capsys):
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    commit(repo, {"docs/registration_event.json": event(reg)}, "registration event")
    commit(repo, {"docs/analysis_plan.md": PLAN.replace("Before.", "Changed.")}, "edit")
    bad = check_plan_order.problems(repo, reg)
    assert len(bad) == 1 and "above section 12" in bad[0]
    assert check_plan_order.main(repo) == 1
    assert "above section 12 differs" in capsys.readouterr().out


def test_reverted_edit_above_section12_is_still_flagged(repo):
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    commit(repo, {"docs/analysis_plan.md": PLAN.replace("Before.", "Changed.")}, "edit")
    commit(repo, {"docs/analysis_plan.md": PLAN}, "revert")
    bad = check_plan_order.problems(repo, reg)
    assert len(bad) == 1 and "above section 12" in bad[0]


def test_line_ending_change_above_section12_is_flagged(repo):
    """Byte identity, not line identity: a CRLF conversion of the frozen text fails."""
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    commit(repo, {"docs/analysis_plan.md": PLAN.replace("Before.\n", "Before.\r\n")}, "crlf")
    assert len(check_plan_order.problems(repo, reg)) == 1


def test_removed_or_duplicated_section12_heading_is_flagged(repo):
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    commit(repo, {"docs/analysis_plan.md": PLAN + "\n## 12. Deviations (dated)\n"}, "dup")
    bad = check_plan_order.problems(repo, reg)
    assert len(bad) == 1 and "cannot be read" in bad[0]


def test_registration_not_ancestor_is_flagged(repo):
    reg = commit(repo, {"docs/analysis_plan.md": PLAN}, "plan")
    git(repo, "checkout", "-q", "--orphan", "other")
    commit(repo, {"docs/analysis_plan.md": PLAN}, "unrelated history")
    bad = check_plan_order.problems(repo, reg)
    assert len(bad) == 1 and "not an ancestor" in bad[0]


def test_plan_order_skips_without_git(tmp_path, capsys):
    """A release archive has no .git: the history check is skipped, not failed."""
    assert check_plan_order.main(tmp_path) == 0
    assert capsys.readouterr().out.startswith("SKIPPED: not a git checkout")


def test_real_plan_has_exactly_one_section12_heading():
    """The registered plan in this repository carries the heading the check looks for."""
    data = (check_plan_order.ROOT / check_plan_order.PLAN).read_bytes()
    assert b"\r" not in data
    assert [ln for ln in data.split(b"\n") if ln == check_plan_order.HEADING] == \
        [check_plan_order.HEADING]
