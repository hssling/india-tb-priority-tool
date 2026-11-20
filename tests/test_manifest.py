"""Every source in data/source_manifest.csv is present in data_raw/ with the
recorded size and SHA-256 (the copies made by tools/fetch_sources.py)."""
import csv
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "source_manifest.csv"
COLUMNS = ["path", "origin", "bytes", "sha256"]


def _rows() -> list[dict]:
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == COLUMNS
        return list(reader)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def test_manifest_has_rows_and_unique_paths():
    rows = _rows()
    assert rows
    paths = [r["path"] for r in rows]
    assert len(paths) == len(set(paths))
    for r in rows:
        assert r["path"].startswith("data_raw/"), r["path"]
        assert len(r["sha256"]) == 64 and r["origin"], r


def test_manifest_digests_match():
    if not (ROOT / "data_raw").is_dir():
        pytest.skip("data_raw/ is not distributed; run python -I tools/fetch_sources.py")
    for r in _rows():
        path = ROOT / r["path"]
        assert path.is_file(), f"missing: {r['path']}"
        assert path.stat().st_size == int(r["bytes"]), r["path"]
        assert _sha256(path) == r["sha256"], r["path"]
