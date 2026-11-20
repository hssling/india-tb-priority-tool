# Adapted from hssling/india-tb-acf-campaign (MIT), verification/check_all.py (itself copied
# from hssling/india-state-tb-score). Changes: the steps of this repository (analysis plan
# §10.3), including the byte-for-byte rerun of outputs/; the manuscript steps run on the private
# manuscript folder (manuscript/) and are SKIP only where manuscript/manuscript_src.md does not
# exist (a fresh clone).
"""Run the whole verification (analysis plan §10.3).

Run as: python -I verification/check_all.py   (steps run from the repository root)

Steps, each a `python -I ...` subprocess:
1. pytest -q
2. check_plan_order         registration order; plan text above §12 unchanged
3. check_deviations         every post hoc / exploratory / deviation label has a dated §12 entry
4. check_extraction_totals  extracted tables against their printed totals
5. check_outputs            independent standard-library recompute
6. check_rerun              byte-for-byte rerun of outputs/
7. check_manuscript_numbers }  every number of the manuscript traced to outputs/; the docx tie,
8. check_docx_tie           }  anonymisation and limits. SKIP where manuscript/manuscript_src.md
                               does not exist (the manuscript is private, git-ignored)

Each step prints PASS, FAIL or SKIP. A step that exits 0 and prints only lines beginning
"SKIPPED" (check_plan_order without .git) counts as skipped; one that also prints other
lines passes, with the number of skipped parts noted (check_extraction_totals without the
source PDFs). Prints "N/N checks passed (k skipped)"; exits 1 on any FAIL.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = [sys.executable, "-I"]
MANUSCRIPT_DIR = "manuscript"
MANUSCRIPT = Path(MANUSCRIPT_DIR) / "manuscript_src.md"

STEPS = [
    ("pytest -q", PY + ["-m", "pytest", "-q", "-p", "no:cacheprovider"]),
    ("check_plan_order", PY + ["verification/check_plan_order.py"]),
    ("check_deviations", PY + ["verification/check_deviations.py"]),
    ("check_extraction_totals", PY + ["verification/check_extraction_totals.py"]),
    ("check_outputs", PY + ["verification/check_outputs.py"]),
    ("check_rerun (byte-for-byte rerun of outputs/)", PY + ["verification/check_rerun.py"]),
    ("check_manuscript_numbers", PY + ["verification/check_manuscript_numbers.py", "--manuscript-dir", MANUSCRIPT_DIR]),
    ("check_docx_tie", PY + ["verification/check_docx_tie.py", "--manuscript-dir", MANUSCRIPT_DIR]),
]
MANUSCRIPT_STEPS = ("check_manuscript_numbers", "check_docx_tie")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def tail(text: str, n: int = 15) -> str:
    return "\n".join("    " + ln for ln in text.strip().splitlines()[-n:])


def skip_reason(name: str, cmd: list[str]) -> str | None:
    """Why a manuscript step is skipped, or None when it must run."""
    if name not in MANUSCRIPT_STEPS:
        return None
    if not (ROOT / MANUSCRIPT).exists():
        return f"SKIPPED: {MANUSCRIPT.as_posix()} does not exist"
    return None


def main() -> int:
    tally = {"passed": 0, "failed": 0, "skipped": 0}
    for name, cmd in STEPS:
        why = skip_reason(name, cmd)
        if why is not None:
            tally["skipped"] += 1
            print(f"[SKIP] {name}: {why}")
            continue
        if not (ROOT / cmd[2]).exists() and cmd[2].endswith(".py"):
            tally["failed"] += 1
            print(f"[FAIL] {name}: {cmd[2]} does not exist")
            continue
        r = run(cmd)
        out = r.stdout + r.stderr
        lines = [ln for ln in out.strip().splitlines() if ln.strip()]
        if r.returncode != 0:
            tally["failed"] += 1
            print(f"[FAIL] {name}\n{tail(out)}")
        elif lines and all(ln.startswith("SKIPPED") for ln in lines):
            tally["skipped"] += 1
            print(f"[SKIP] {name}\n{tail(out)}")
        else:
            tally["passed"] += 1
            part = sum(ln.startswith("SKIPPED") for ln in lines)
            note = f" ({part} part(s) skipped: see the step's output)" if part else ""
            print(f"[PASS] {name}: {lines[-1] if lines else ''}{note}")
    total = tally["passed"] + tally["failed"]
    note = f" ({tally['skipped']} skipped)" if tally["skipped"] else ""
    print(f"\n{tally['passed']}/{total} checks passed{note}")
    return 1 if tally["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
