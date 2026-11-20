"""Rerun the whole analysis into a temporary folder and compare it with outputs/ byte for
byte (analysis plan §10.1, §10.3). Nothing in outputs/ is written.

Run as: python -I verification/check_rerun.py [--root DIR]

The reruns are those of the README's reproduction commands, each into its own temporary
folder:
- src/run_state.py (state_trend, state_priority, state_priority_sensitivity,
  state_harm_draws_summary, na_cells);
- src/run_validate.py (headline, spec_curve, leave_one_out);
- the tool's ``state`` command on data/extracted/state_panel.csv (the same five State files
  and report_state.html);
- the tool's ``district`` command on the Lok Sabha Q802 notifications for Madhya Pradesh
  and Maharashtra with the national 2018 module (district_mp_mh.csv,
  district_national_2018.csv, report_district.html).

Every file of outputs/ except README.md must be reproduced, and every reproduced file must
be in outputs/ with the same bytes. Exit 1 otherwise.
"""
import argparse
import contextlib
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOT_GENERATED = {"README.md"}


def rerun(root: Path, tmp: Path) -> dict[str, list[Path]]:
    """Run the analysis from ``root`` into folders under ``tmp``; output name -> files."""
    sys.path.insert(0, str(root))
    from src import run_state, run_validate  # noqa: PLC0415
    from src.tbprio import __main__ as cli  # noqa: PLC0415

    ext = root / "data" / "extracted"
    made: dict[str, list[Path]] = {}
    with contextlib.redirect_stdout(io.StringIO()):
        steps = (
            ("run_state", lambda d: run_state.main(d)),
            ("run_validate", lambda d: run_validate.main(d)),
            ("tbprio state", lambda d: cli.main(["state", "--panel",
                                                 str(ext / "state_panel.csv"),
                                                 "--out", str(d)])),
            ("tbprio district", lambda d: cli.main(
                ["district", "--input", str(ext / "district_notifications.csv"),
                 "--state", "Madhya Pradesh", "--state", "Maharashtra", "--tag", "mp_mh",
                 "--national-2018", str(ext / "district_2018.csv"), "--out", str(d)])),
        )
        for name, fn in steps:
            d = tmp / name.replace(" ", "_")
            if fn(d) != 0:
                raise RuntimeError(f"{name} exited with an error")
            for p in sorted(d.iterdir()):
                made.setdefault(p.name, []).append(p)
    return made


def problems(root: Path = ROOT) -> tuple[list[str], int]:
    out_dir = root / "outputs"
    with tempfile.TemporaryDirectory() as t:
        made = rerun(root, Path(t))
        bad = []
        committed = {p.name for p in out_dir.iterdir() if p.is_file()} - NOT_GENERATED
        for name in sorted(committed - set(made)):
            bad.append(f"outputs/{name} is not produced by any rerun")
        for name in sorted(made):
            if name not in committed:
                bad.append(f"the rerun produces {name}, which is not in outputs/")
                continue
            ref = (out_dir / name).read_bytes()
            for p in made[name]:
                if p.read_bytes() != ref:
                    bad.append(f"outputs/{name} differs from the rerun "
                               f"({p.parent.name.replace('_', ' ')})")
        return bad, len(committed)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT), help="repository root (default: this one)")
    root = Path(ap.parse_args(argv).root).resolve()
    try:
        bad, n = problems(root)
    except Exception as e:  # noqa: BLE001  any error is a failed check
        bad, n = [f"{type(e).__name__}: {e}"], 0
    if bad:
        for b in bad:
            print(f"FAIL: {b}")
        return 1
    print(f"OK: all {n} files of outputs/ (README.md aside) are reproduced byte for byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
