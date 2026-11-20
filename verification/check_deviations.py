# Adapted from hssling/india-tb-acf-campaign (MIT), verification/check_deviations.py
# (itself copied from hssling/india-state-tb-score). Changes: the deviations section is
# §12 of this plan, whose entries are bold paragraphs "**12.N (date), ...**"; the labels
# checked are "post hoc", "exploratory", "deviation" and references to §12 entries; the
# files scanned are outputs/, README.md and the extracted data (whose flag column carries
# the plan_12.N references).
"""Check that every post hoc, exploratory or deviation label, and every reference to a §12
entry, in the outputs, the README and the extracted data is covered by a dated entry of
§12 of docs/analysis_plan.md.

Run as: python -I verification/check_deviations.py [--root DIR]

Files scanned: every file under outputs/ (including outputs/README.md), README.md and
data/extracted/*.csv (whose ``flag`` column carries references such as
``registered_basis_sensitivity_plan_12.2``).

1. Every §12 entry is a bold paragraph beginning "**12.N (<day> <Month> <year>)"; an
   entry without a date is a failure.
2. A reference to a specific entry ("§12.N", "section 12.N", "plan 12.N", "plan_12.N")
   must name an entry that exists.
3. A line labelled "post hoc" or "exploratory" must name, in the same line, an entry
   whose text carries the same label.
4. A line labelled "deviation" must name, in the same line, an entry whose text says
   "deviation", or point to §12 as a whole ("§12", "section 12", "plan 12" with no entry
   number) when it is a general pointer (no "post hoc" or "exploratory" label).

Nothing is edited; a label without a covering entry is a failure.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = Path("docs") / "analysis_plan.md"
HEADING = "## 12. Deviations (dated)"
ENTRY = re.compile(r"^\*\*12\.(\d+)\s*(\(([^)]*)\))?")
DATE = re.compile(r"^\d{1,2} (January|February|March|April|May|June|July|August|September|"
                  r"October|November|December) \d{4}$")
# A reference to one entry: §12.2, § 12.2, section 12.2, plan 12.2, plan_12.2.
REF = re.compile(r"(?:§\s?|section\s|plan[\s_])12\.(\d+)", re.I)
# A pointer to the section as a whole (no entry number).
WHOLE = re.compile(r"(?:§\s?|section\s|plan[\s_])12(?![.\d])", re.I)
LABELS = {"post hoc": re.compile(r"post[\s-]hoc", re.I),
          "exploratory": re.compile(r"exploratory", re.I),
          "deviation": re.compile(r"deviation", re.I)}


def entries(plan: str) -> tuple[dict[str, str], list[str]]:
    """(entry number -> its text, problems) for the entries of §12."""
    lines = plan.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == HEADING]
    if len(starts) != 1:
        return {}, [f"{PLAN.as_posix()}: expected one {HEADING!r} heading, found "
                    f"{len(starts)}"]
    out: dict[str, list[str]] = {}
    bad: list[str] = []
    current = None
    for ln in lines[starts[0] + 1:]:
        if ln.startswith("## "):
            break
        m = ENTRY.match(ln)
        if m:
            current = m.group(1)
            if current in out:
                bad.append(f"§12.{current} appears twice")
            date = (m.group(3) or "").strip()
            if not DATE.match(date):
                bad.append(f"§12.{current} has no date in its heading (found {date!r})")
            out[current] = [ln]
        elif current is not None:
            out[current].append(ln)
        elif ln.strip():
            bad.append(f"text in §12 before its first dated entry: {ln.strip()[:60]!r}")
    return {k: "\n".join(v) for k, v in out.items()}, bad


def files(root: Path) -> list[Path]:
    fs = [f for f in sorted((root / "outputs").rglob("*")) if f.is_file()]
    fs += [root / "README.md"] if (root / "README.md").exists() else []
    fs += sorted((root / "data" / "extracted").glob("*.csv"))
    return fs


def problems(root: Path = ROOT) -> tuple[list[str], list[str]]:
    """(failures, descriptions of covered labels)."""
    plan = (root / PLAN).read_text(encoding="utf-8")
    ent, bad = entries(plan)
    ok: list[str] = []
    for f in files(root):
        rel = f.relative_to(root).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        n_cov = 0
        unlogged: list[str] = []
        for k, ln in enumerate(text.splitlines(), start=1):
            refs = set(REF.findall(ln))
            labels = [name for name, rx in LABELS.items() if rx.search(ln)]
            if not refs and not labels and not WHOLE.search(ln):
                continue
            missing = sorted(r for r in refs if r not in ent)
            if missing:
                unlogged.append(f"line {k}: names §12.{', §12.'.join(missing)}, which "
                                f"does not exist")
                continue
            for name in labels:
                cover = [r for r in refs if LABELS[name].search(ent[r])]
                if cover:
                    continue
                if name == "deviation" and WHOLE.search(ln) and not (
                        {"post hoc", "exploratory"} & set(labels)):
                    continue
                unlogged.append(f"line {k}: labelled {name!r} but names no dated §12 entry "
                                f"that carries that label")
            n_cov += 1
        if unlogged:
            bad += [f"{rel} {u}" for u in unlogged[:5]]
            if len(unlogged) > 5:
                bad.append(f"{rel}: {len(unlogged) - 5} more such line(s)")
        elif n_cov:
            ok.append(f"{rel} ({n_cov} line(s))")
    return bad, ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT), help="repository root (default: this one)")
    root = Path(ap.parse_args(argv).root)
    try:
        bad, ok = problems(root)
    except Exception as e:  # noqa: BLE001  any error is a failed check
        bad, ok = [f"{type(e).__name__}: {e}"], []
    if bad:
        for b in bad:
            print(f"FAIL: {b}".replace("§", "plan "))
        return 1
    ent, _ = entries((root / PLAN).read_text(encoding="utf-8"))
    print(f"OK: {len(ent)} dated plan 12 entries; labelled or referring lines in {len(ok)} "
          f"file(s) are covered: {'; '.join(ok) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
