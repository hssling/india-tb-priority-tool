# Adapted from hssling/india-tb-acf-campaign (MIT), verification/check_plan_order.py, which was
# itself copied from hssling/india-state-tb-score. Changes: the frozen text ends at
# "## 12. Deviations (dated)"; the guarded paths are outputs/ and the four estimation modules
# src/tbprio/{harm,shrink,priority,trend}.py; a missing docs/registration_event.json is a FAIL
# ("NOT REGISTERED YET"); the LGD and extension checks of that repository are dropped.
"""Check that the analysis plan was registered before any estimate or output.

Run as: python -I verification/check_plan_order.py

Four assertions:

1. docs/registration_event.json exists. Before the controller records the public push it
   does not, and the check FAILS with "NOT REGISTERED YET": a missing registration record
   never switches the other checks off.
2. The registration commit named in that file is an ancestor of HEAD.
3. No commit that is not a strict descendant of the registration commit touches outputs/
   or src/tbprio/harm.py, shrink.py, priority.py or trend.py (full history, so a commit on a
   merged side branch is found even when the merge dropped its change; the registration
   commit itself may not touch them either).
4. The text of docs/analysis_plan.md above the "## 12. Deviations (dated)" heading is
   byte-identical at the registration commit and at every commit in registration..HEAD
   (git rev-list, merged side branches included), so an edit that was later reverted is
   also caught.

In a copy without .git (a release archive) the history cannot be checked: this prints
"SKIPPED: not a git checkout ..." and exits 0.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDED = ("outputs", "src/tbprio/harm.py", "src/tbprio/shrink.py",
           "src/tbprio/priority.py", "src/tbprio/trend.py")
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


def registered_commit(repo: Path) -> str:
    """The registration commit recorded in docs/registration_event.json.

    Raises FileNotFoundError if the file is missing and ValueError if it names no commit."""
    f = repo / EVENT
    if not f.exists():
        raise FileNotFoundError(NOT_REGISTERED)
    try:
        event = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{EVENT.as_posix()} is not valid JSON ({e})") from e
    for key in COMMIT_KEYS:
        if isinstance(event, dict) and isinstance(event.get(key), str) and event[key].strip():
            return event[key].strip()
    raise ValueError(f"{EVENT.as_posix()} names no registration commit (expected the key "
                     f"{COMMIT_KEYS[0]!r})")


def problems(repo: Path = ROOT, registration: str | None = None,
             guarded: tuple[str, ...] = GUARDED) -> list[str]:
    """Every violation of assertions 2-4, given the registration commit (read from
    docs/registration_event.json when not given)."""
    out: list[str] = []
    registration = registration or registered_commit(repo)
    try:
        reg = git(repo, "rev-parse", "--verify", f"{registration}^{{commit}}").stdout.strip()
    except RuntimeError:
        return [f"registration commit {registration[:7]} does not exist in this repository"]
    if not is_ancestor(repo, reg, "HEAD"):
        return [f"registration commit {registration[:7]} is not an ancestor of HEAD"]
    for c in git(repo, "log", "--full-history", "--format=%H", "--", *guarded).stdout.split():
        if c == reg or not is_ancestor(repo, reg, c):
            out.append(f"commit {c[:7]} touches outputs/ or an estimation module "
                       f"(src/tbprio/harm.py, shrink.py, priority.py, trend.py) but is not a "
                       f"descendant of the registration commit {registration[:7]}")
    try:
        frozen = plan_above_section12(repo, reg)
    except RuntimeError as e:
        return out + [f"the registration commit's plan cannot be read ({e})"]
    for c in git(repo, "rev-list", f"{reg}..HEAD").stdout.split():
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
    n = len(git(root, "rev-list", f"{reg}..HEAD").stdout.split())
    print(f"OK: registration commit {reg[:7]} is an ancestor of HEAD; no commit touching "
          f"outputs/ or an estimation module precedes it; the plan text above section 12 is "
          f"byte-identical across {n} later commits; {EVENT.as_posix()} exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
