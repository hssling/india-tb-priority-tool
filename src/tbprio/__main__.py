"""The TB priority tool's command line (analysis plan §9.3, §10.2).

    python -I -m tbprio state --panel data/extracted/state_panel.csv --out outputs/
    python -I -m tbprio district --input <csv> --state <name> --out <dir>

``state`` runs the State analysis (src/tbprio/state.py, the same computation as
src/run_state.py) on a long-format panel and writes the State output files and
report_state.html. The registered-basis S6 2022 panel and the population file are read
from beside the panel (state_panel_s6_2022_registered.csv, state_population.csv) when
present, or from --registered / --population.

``district`` reads a district CSV in the schema of plan §9.3 (required: district, year,
notified; optional: state, target, population, cascade_*), and for each --state (repeat
the option for several States) gives the change in notifications between the first and
last year (or --base-year / --final-year) and its funnel (plan §9.2). It writes
district_<tag>.csv and report_district.html. With --national-2018
data/extracted/district_2018.csv it also runs the national district module for data year
2018 (plan §9.1), writes district_national_2018.csv and adds it to the report. The
optional columns are validated and carried; the analysis uses notifications only.

The tool needs the package importable as ``tbprio``: from the repository root, run once
``python -I -m pip install --no-deps --no-build-isolation -e .``.
"""
from __future__ import annotations

import argparse
import re
import sys
import warnings
from pathlib import Path

from . import district, panel, report, schema, state
from .table import write_csv


def _sibling(panel_path: Path, name: str, given: str | None) -> Path | None:
    if given:
        return Path(given)
    p = panel_path.parent / name
    return p if p.exists() else None


def cmd_state(a: argparse.Namespace) -> int:
    panel_path = Path(a.panel)
    out = Path(a.out)
    rows = panel.load(panel_path)
    reg_path = _sibling(panel_path, "state_panel_s6_2022_registered.csv", a.registered)
    pop_path = _sibling(panel_path, "state_population.csv", a.population)
    registered = panel.load(reg_path) if reg_path else None
    population = panel.load_population(pop_path) if pop_path else None
    tables = state.run(rows, registered, population, panel_path.stem,
                       reg_path.stem if reg_path else "")
    paths = state.write(tables, out)
    for m in state.messages(tables):
        print(m)
    if not tables["state_priority"]:
        print(f"no data year {state.PRIORITY_YEAR} cells in {panel_path.name}: "
              f"report_state.html not written", file=sys.stderr)
        return 1
    html_path = out / "report_state.html"
    report.write(html_path, report.state_report(tables["state_priority"], state.STEP_NAMES,
                                                panel_path.name, state.PRIORITY_YEAR))
    for p in paths + [html_path]:
        print(f"wrote {p.as_posix()}")
    return 0


def _slug(names: list[str]) -> str:
    return "_".join(re.sub(r"[^a-z0-9]+", "_", n.casefold()).strip("_") for n in names)


def cmd_district(a: argparse.Namespace) -> int:
    inp = Path(a.input)
    out = Path(a.out)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", schema.SchemaWarning)
        rows = schema.read_csv(inp)
    for w in caught:
        print(f"warning: {w.message}", file=sys.stderr)
    change_rows, info, years = district.notifications(rows, a.state, a.base_year,
                                                      a.final_year)
    canon = list(info)
    tag = a.tag or _slug(canon)
    paths = []
    p = out / f"district_{tag}.csv"
    write_csv(p, district.change_cols(years), change_rows)
    paths.append(p)
    nat_rows = nat_info = None
    if a.national_2018:
        nat_path = Path(a.national_2018)
        nat_rows, nat_info = district.national(read_district_2018(nat_path))
        p = out / "district_national_2018.csv"
        write_csv(p, district.NATIONAL_COLS, nat_rows)
        paths.append(p)
    au802 = any("AU802" in (r.get("table_id") or "") for r in rows)
    html_path = out / "report_district.html"
    report.write(html_path, report.district_report(
        change_rows, info, years, inp.name, nat_rows, nat_info,
        Path(a.national_2018).name if a.national_2018 else "", district.STEPS_2018,
        au802, optional_columns(rows)))
    paths.append(html_path)
    for s, v in info.items():
        fell = sum(r["flag"] == district.FELL for r in change_rows if r["state"] == s)
        rose = sum(r["flag"] == district.ROSE for r in change_rows if r["state"] == s)
        print(f"{s}: {v['districts']} districts; pooled change {100 * v['change']:+.2f}%; "
              f"phi {v['phi']:.3f}; tau2 {v['tau2']:.6f}; fell {fell}, rose {rose}")
    if nat_info:
        for s, v in nat_info.items():
            print(f"2018 {s}: {v['units']} districts; benchmark {v['rate_bench']:.5f}; "
                  f"phi {v['phi']:.3f}; tau2 {v['tau2']:.6f}")
    for p in paths:
        print(f"wrote {p.as_posix()}")
    return 0


def optional_columns(rows: list[dict]) -> list[str]:
    """The optional count columns present in validated district rows (§9.3)."""
    return sorted(k for k in rows[0] if k in ("target", "population")
                  or k.startswith(schema.CASCADE_PREFIX)) if rows else []


NATIONAL_INT_COLS = ("notified", "initiated", "success_public_n", "pdf_page")


def read_district_2018(path: Path) -> list[dict]:
    """data/extracted/district_2018.csv (written by src/extract/itr2019_districts.py)."""
    import csv

    need = ("state", "district", "notified", "initiated", "success_public_n",
            "success_public_pct", "source_file", "pdf_page", "table_id")
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in need if c not in (reader.fieldnames or [])]
        if missing:
            raise schema.SchemaError(f"{path}: not the extracted ITR 2019 A1.13 table "
                                     f"(missing {', '.join(missing)})")
        out = []
        for r in reader:
            d = {k: r[k] for k in need}
            for k in NATIONAL_INT_COLS:
                d[k] = None if d[k] == "" else int(d[k])
            d["success_public_pct"] = d["success_public_pct"] or None
            out.append(d)
    return out


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -I -m tbprio",
        description="TB priority tool: State priorities and district funnels "
                    "(docs/analysis_plan.md).")
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("state", help="State priorities and report_state.html")
    s.add_argument("--panel", required=True, help="long-format State panel CSV")
    s.add_argument("--out", required=True, help="output folder")
    s.add_argument("--registered", help="registered-basis S6 2022 panel (default: "
                                        "beside the panel, if present)")
    s.add_argument("--population", help="population CSV (default: beside the panel, if "
                                        "present)")
    s.set_defaults(fn=cmd_state)
    d = sub.add_parser("district", help="district change funnel and report_district.html")
    d.add_argument("--input", required=True, help="district CSV (district, year, notified)")
    d.add_argument("--state", required=True, action="append",
                   help="State to analyse (repeat for several)")
    d.add_argument("--out", required=True, help="output folder")
    d.add_argument("--tag", help="output name district_<tag>.csv (default: the State "
                                 "names)")
    d.add_argument("--base-year", type=int, help="default: the first year in the input")
    d.add_argument("--final-year", type=int, help="default: the last year in the input")
    d.add_argument("--national-2018", help="data/extracted/district_2018.csv: also run "
                                           "the national 2018 module")
    d.set_defaults(fn=cmd_district)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    try:
        return a.fn(a)
    except (schema.SchemaError, ValueError, KeyError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
