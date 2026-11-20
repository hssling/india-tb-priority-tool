# Adapted from hssling/india-tb-acf-campaign (MIT), verification/check_plan_order.py, which was
# itself copied from hssling/india-state-tb-score. Changes: the frozen text ends at
# "## 12. Deviations (dated)"; a missing docs/registration_event.json is a FAIL ("NOT
# REGISTERED YET"); every committed version of that file must name the same commit; all of
# src/tbprio/ and outputs/ are guarded except an explicit allow-list; later commits are
# listed with --ancestry-path; the LGD and extension checks of that repository are dropped.
"""Check that the analysis plan was registered before any estimate or output.

Run as: python -I verification/check_plan_order.py

Assertions:

1. docs/registration_event.json exists. Before the controller records the public push it
   does not, and the check FAILS with "NOT REGISTERED YET": a missing registration record
   never switches the other checks off.
2. Every committed version of docs/registration_event.json (full history, deletions
   included) names the same commit as the working-tree file, so the anchor cannot be moved.
3. The registration commit named in that file is an ancestor of HEAD.
4. No commit that is not a strict descendant of the registration commit touches outputs/
   (any file) or src/tbprio/ (any file except the explicit allow-list ALLOWED, empty for
   now). Full history, deletions and renames included (--no-renames lists a rename as a
   deletion and an addition), so a commit on a merged side branch is found even when the
   merge dropped its change; the registration commit itself may not touch them either.
5. The text of docs/analysis_plan.md above the "## 12. Deviations (dated)" heading is
   byte-identical at the registration commit and at every commit in
   `git rev-list --ancestry-path <registration>..HEAD`, so an edit that was later reverted
   is also caught.

In a copy without .git (a release archive) the history cannot be checked: this prints
"SKIPPED: not a git checkout ..." and exits 0.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDED = ("outputs", "src/tbprio")
# Loader modules that may be committed before registration (repository paths, e.g.
# "src/tbprio/panel.py"). Empty: none is allowed.
ALLOWED: tuple[str, ...] = ()
PLAN = "docs/analysis_plan.md"
HEADING = b"## 12. Deviations (dated)"
EVENT = Path("docs") / "registration_event.json"
COMMIT_KEYS = ("registered_commit", "registration_commit")

NOT_GIT = ("SKIPPED: not a git checkout (clone the repository to verify history and byte "
           "reproduction)")
NOT_REGISTERED = ("NOT REGISTERED YET: docs/registration_event.json does not exist. The plan "
                  "must be pushed to the public repository and the registration commit and "
                  "pushed_at time recorded in that file before any estimate is computed.")


def git(repo: Path, *args: str, ok=(0,), text=True) -> subprocess.CompletedProcess:
    kw = {"text": True, "encoding": "utf-8"} if text else {}
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, **kw)
    if r.returncode not in ok:
        err = r.stderr if text else r.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"git {' '.join(args)} failed: {err.strip()}")
    return r


def is_ancestor(repo: Path, a: str, b: str) -> bool:
    return git(repo, "merge-base", "--is-ancestor", a, b, ok=(0, 1)).returncode == 0


def plan_above_section12(repo: Path, rev: str) -> bytes:
    """The bytes of the plan above its deviations heading (exactly one such line)."""
    data = git(repo, "show", f"{rev}:{PLAN}", text=False).stdout
    pos, found = 0, []
    for line in data.split(b"\n"):
        if line.rstrip(b"\r") == HEADING:
            found.append(pos)
        pos += len(line) + 1
    if len(found) != 1:
        raise RuntimeError(f"{PLAN} at {rev[:7]}: expected one {HEADING.decode()!r} heading, "
                           f"found {len(found)}")
    return data[:found[0]]


def commit_named(text: str) -> str | None:
    """The registration commit named in the text of a registration_event.json, or None."""
    try:
        event = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, dict):
        return None
    for key in COMMIT_KEYS:
        if isinstance(event.get(key), str) and event[key].strip():
            return event[key].strip()
    return None


def registered_commit(repo: Path) -> str:
    """The registration commit recorded in docs/registration_event.json.

    Raises FileNotFoundError if the file is missing and ValueError if it names no commit."""
    f = repo / EVENT
    if not f.exists():
        raise FileNotFoundError(NOT_REGISTERED)
    text = f.read_text(encoding="utf-8")
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"{EVENT.as_posix()} is not valid JSON ({e})") from e
    named = commit_named(text)
    if named is None:
        raise ValueError(f"{EVENT.as_posix()} names no registration commit (expected the key "
                         f"{COMMIT_KEYS[0]!r})")
    return named


def event_versions(repo: Path) -> list[tuple[str, str | None]]:
    """(commit, named registration commit) for every commit that touched
    docs/registration_event.json; None where that commit deleted it or it names none."""
    out = []
    for c in git(repo, "log", "--full-history", "--format=%H", "--",
                 EVENT.as_posix()).stdout.split():
        r = git(repo, "show", f"{c}:{EVENT.as_posix()}", ok=(0, 128))
        out.append((c, commit_named(r.stdout) if r.returncode == 0 else None))
    return out


def same_commit(a: str, b: str) -> bool:
    return a.startswith(b) or b.startswith(a)


def guarded_commits(repo: Path, guarded: tuple[str, ...] = GUARDED,
                    allowed: tuple[str, ...] = ALLOWED) -> list[str]:
    """Commits (full history, no simplification, no rename detection) that touch a guarded
    path other than an allowed one."""
    # --diff-merges=separate lists a merge's changes against each parent, so a merge that
    # itself introduces a guarded file (an "evil merge") is not silently skipped.
    log = git(repo, "log", "--full-history", "--no-renames", "--diff-merges=separate",
              "--name-only", "--format=%x00%H", "--", *guarded).stdout
    hits = []
    for block in log.split("\x00")[1:]:
        sha, *names = block.split("\n")
        if any(n.strip() and n.strip() not in allowed for n in names) and sha.strip() not in hits:
            hits.append(sha.strip())
    return hits


def later_commits(repo: Path, reg: str) -> list[str]:
    return git(repo, "rev-list", "--ancestry-path", f"{reg}..HEAD").stdout.split()


def problems(repo: Path = ROOT, registration: str | None = None,
             guarded: tuple[str, ...] = GUARDED,
             allowed: tuple[str, ...] = ALLOWED) -> list[str]:
    """Every violation of assertions 2-5, given the registration commit (read from
    docs/registration_event.json when not given)."""
    out: list[str] = []
    registration = registration or registered_commit(repo)
    for c, named in event_versions(repo):
        if named is None or not same_commit(named, registration):
            out.append(f"commit {c[:7]}: the committed {EVENT.as_posix()} names "
                       f"{named[:7] if named else 'no commit'}, not the registration commit "
                       f"{registration[:7]} (the anchor must never move)")
    try:
        reg = git(repo, "rev-parse", "--verify", f"{registration}^{{commit}}").stdout.strip()
    except RuntimeError:
        return out + [f"registration commit {registration[:7]} does not exist in this "
                      f"repository"]
    if not is_ancestor(repo, reg, "HEAD"):
        return out + [f"registration commit {registration[:7]} is not an ancestor of HEAD"]
    for c in guarded_commits(repo, guarded, allowed):
        if c == reg or not is_ancestor(repo, reg, c):
            out.append(f"commit {c[:7]} touches outputs/ or src/tbprio/ (outside the "
                       f"allow-list) but is not a descendant of the registration commit "
                       f"{registration[:7]}")
    try:
        frozen = plan_above_section12(repo, reg)
    except RuntimeError as e:
        return out + [f"the registration commit's plan cannot be read ({e})"]
    for c in later_commits(repo, reg):
        try:
            same = plan_above_section12(repo, c) == frozen
        except RuntimeError as e:
            out.append(f"commit {c[:7]}: {PLAN} above section 12 cannot be read ({e})")
            continue
        if not same:
            out.append(f"commit {c[:7]}: {PLAN} above section 12 differs from its content at "
                       f"the registration commit {registration[:7]}")
    return out


def main(root: Path = ROOT) -> int:
    if not (root / ".git").exists():
        print(NOT_GIT)
        return 0
    try:
        reg = registered_commit(root)
        bad = problems(root, reg)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"FAIL: {e}")
        return 1
    if bad:
        for b in bad:
            print(f"FAIL: {b}")
        return 1
    n = len(later_commits(root, reg))
    print(f"OK: registration commit {reg[:7]} is an ancestor of HEAD; every committed "
          f"{EVENT.as_posix()} names it; no commit touching outputs/ or src/tbprio/ precedes "
          f"it; the plan text above section 12 is byte-identical across {n} later commits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
