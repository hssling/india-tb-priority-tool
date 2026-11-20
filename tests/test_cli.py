"""Tests of the tool's command line and HTML reports (analysis plan §9.3, §10.2)."""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.tbprio import __main__ as cli
from src.tbprio import state

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "district_example.csv"
NOTIF = ROOT / "data" / "extracted" / "district_notifications.csv"
D2018 = ROOT / "data" / "extracted" / "district_2018.csv"
PANEL = ROOT / "data" / "extracted" / "state_panel.csv"
OUTPUTS = ROOT / "outputs"


def _self_contained(html: str) -> None:
    assert html.startswith("<!doctype html>")
    assert "\r" not in html
    assert not re.search(r"<script|<link|<img|<iframe|@import|url\(\s*['\"]?http", html,
                         re.I)
    assert not re.search(r"(src|href)=\"(https?:)?//", html)
    assert "<svg" in html and "<title" in html
    # no date or time: reruns are byte-identical
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b|\d\d:\d\d:\d\d", html)


def test_cli_writes_report(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for out in (a, b):
        assert cli.main(["district", "--input", str(EXAMPLE), "--state", "Synthetic State",
                         "--out", str(out)]) == 0
    names = sorted(p.name for p in a.iterdir())
    assert names == ["district_synthetic_state.csv", "report_district.html"]
    for n in names:
        assert (a / n).read_bytes() == (b / n).read_bytes()
    html = (a / "report_district.html").read_text(encoding="utf-8")
    _self_contained(html)
    for text in ("How to read this report", "Caveats", "less TB or less case-finding",
                 "fell beyond adjusted limits", "Synthetic District",
                 "cascade_initiated, population, target"):
        assert text in html
    assert "act now" not in html  # no tiers in the change funnel


def test_cli_district_demonstration_states(tmp_path):
    assert cli.main(["district", "--input", str(NOTIF), "--state", "Madhya Pradesh",
                     "--state", "Maharashtra", "--tag", "mp_mh", "--national-2018",
                     str(D2018), "--out", str(tmp_path)]) == 0
    for n in ("district_mp_mh.csv", "district_national_2018.csv", "report_district.html"):
        assert (tmp_path / n).read_bytes() == (OUTPUTS / n).read_bytes(), n
    html = (tmp_path / "report_district.html").read_text(encoding="utf-8")
    _self_contained(html)
    for text in ("2018 data (historical)", "Priority matrix", "Vidisha (printed twice)",
                 "less TB or less case-finding", "rounded_from_percent", "P(top-20)",
                 "referral centres", "count as not initiated",
                 "A point lies beyond the solid lines exactly when the district is flagged"):
        assert text in html


def test_cli_state_writes_report(tmp_path):
    assert cli.main(["state", "--panel", str(PANEL), "--out", str(tmp_path)]) == 0
    for n in state.OUTPUT_FILES:
        assert (tmp_path / n).read_bytes() == (OUTPUTS / n).read_bytes(), n
    html = (tmp_path / "report_state.html").read_bytes()
    assert html == (OUTPUTS / "report_state.html").read_bytes()
    text = html.decode("utf-8")
    _self_contained(text)
    for t in ("Priority matrix",
              "A CTD notification target is a programme goal, not an estimate of disease",
              "shortfall against target: it does not count people with TB who were not found",
              "shortfall against target", "Summary for each State/UT", "watch: rising"):
        assert t in text
    assert "missed cases" not in text  # plan §1.3 wording


def test_cli_errors_are_clear(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text("district,year,count\nA,2022,3\n", encoding="utf-8")
    assert cli.main(["district", "--input", str(bad), "--state", "X", "--out",
                     str(tmp_path / "o")]) == 2
    assert "missing required column(s): notified" in capsys.readouterr().err
    assert cli.main(["district", "--input", str(EXAMPLE), "--state", "Kerala", "--out",
                     str(tmp_path / "o")]) == 2
    assert "no rows for State 'Kerala'" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli.main(["district", "--input", str(EXAMPLE)])  # --state and --out are required


@pytest.mark.skipif(importlib.util.find_spec("tbprio") is None,
                    reason="tbprio is not installed (pip install --no-deps -e .)")
def test_python_m_tbprio_runs(tmp_path):
    r = subprocess.run([sys.executable, "-I", "-m", "tbprio", "district", "--input",
                        str(EXAMPLE), "--state", "Synthetic State", "--out", str(tmp_path)],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "report_district.html").exists()
