"""CSV writing shared by the analysis outputs (analysis plan §10.1: LF line endings,
byte-identical reruns)."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "True" if v else "False"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        v = float(v)
        return "" if v != v else repr(v)
    return str(v)


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow([fmt(r[h]) for h in header])
