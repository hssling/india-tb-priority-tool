"""Copy the source documents into data_raw/ and verify their SHA-256 digests.

Run as: python -I tools/fetch_sources.py   (stdlib only; from the repository root)

No file is downloaded. The India TB Reports and the NTPS report are copied from
the sibling repositories' data_raw/ folders (tb_state_score, tb_acf_campaign),
which hold them as downloaded from tbcindia.mohfw.gov.in. The Lok Sabha answers
are author-supplied and must already be in data_raw/pq/.

Every file is checked against the digest pinned below before the manifest
data/source_manifest.csv (columns path, origin, bytes, sha256) is written. The
pinned digests of the copied files are those recorded in the sibling
repositories' own manifests; the author-supplied digests were pinned on
21 Nov 2026, when the files were first received. A mismatch is an error and
the manifest is not written.
"""
from __future__ import annotations

import csv
import hashlib
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIBLINGS = ROOT.parent
MANIFEST = ROOT / "data" / "source_manifest.csv"
FIELDS = ["path", "origin", "bytes", "sha256"]
CHUNK = 1 << 20

# (path in this repo, sibling copy relative to the parent folder or None for
#  author-supplied, upstream origin, pinned sha256)
SOURCES: list[tuple[str, str | None, str, str]] = [
    ("data_raw/india_tb_report/India-TB-Report-2019.pdf",
     "tb_acf_campaign/data_raw/official/India-TB-Report-2019.pdf",
     "https://tbcindia.mohfw.gov.in/wp-content/uploads/2023/05/India-TB-Report-2019.pdf",
     "87e546751372ba157cb9eba1620173d54aad0fb99abc1b99f4302e9a2005c03b"),
    ("data_raw/india_tb_report/ITR2020.pdf",
     "tb_state_score/data_raw/india_tb_report/ITR2020.pdf",
     "https://tbcindia.mohfw.gov.in/wp-content/uploads/2023/05/India-TB-Report-2020.pdf",
     "63b9408015dae510858e0eef2711e809d398bfe3149dd21c94390b258c007e7e"),
    ("data_raw/india_tb_report/ITR2021.pdf",
     "tb_state_score/data_raw/india_tb_report/ITR2021.pdf",
     "https://tbcindia.mohfw.gov.in/wp-content/uploads/2023/05/4504484964TB-Annual-Report-2021-210321-High-Resolution.pdf",
     "692267fd532e01289a23c7b6551245ac94a1e5d6894060d2612c4337e6c410c3"),
    ("data_raw/india_tb_report/TBAnnaulReport2022.pdf",
     "tb_acf_campaign/data_raw/official/TBAnnaulReport2022.pdf",
     "https://tbcindia.mohfw.gov.in/wp-content/uploads/2023/05/TBAnnaulReport2022.pdf",
     "dc9ff4a88a28eb87232770d0956fe92b2b266b15e5794f879a7335b7c083418b"),
    ("data_raw/india_tb_report/ITR2023.pdf",
     "tb_state_score/data_raw/india_tb_report/ITR2023.pdf",
     "https://tbcindia.mohfw.gov.in/wp-content/uploads/2023/05/5646719104TB_AR_2023_04-04-2023_LRP_final.pdf",
     "0817ac3a1e7a03273438073d4e685f88aa93507ad115ec5c6588edfddc8f0b7b"),
    ("data_raw/india_tb_report/ITR2024.pdf",
     "tb_state_score/data_raw/india_tb_report/ITR2024.pdf",
     "https://tbcindia.mohfw.gov.in/wp-content/uploads/2024/10/TB-Report_for-Web_08_10-2024-1.pdf",
     "e37f9f406153b5e9a19726538c3f4d09dc4c470281c34fe511adaa56a0e22765"),
    ("data_raw/icmr_ntps/NTPS_2019_21_report.pdf",
     "tb_state_score/data_raw/icmr_ntps/NTPS_2019_21_report.pdf",
     "https://tbcindia.mohfw.gov.in/wp-content/uploads/2023/05/25032022161020NATBPSReport.pdf",
     "884ffdd205d3b69569b06b3058ea77c490d44b1f2af6c3622f99282d60f04f83"),
    ("data_raw/pq/AU802_LlE1Wb.docx", None,
     "author-supplied: Lok Sabha Unstarred Q. 802, answered 7 Feb 2025 (district-wise TB notifications 2022-2024, Madhya Pradesh and Maharashtra)",
     "673f79000b8c6da71fea01ad57ff0e3437e8eb9236166a2fe041e2bba3fe7405"),
    ("data_raw/pq/AU1891_qm5WaQ.docx", None,
     "author-supplied: Lok Sabha Unstarred Q. 1891, answered 2 Aug 2024 (Karnataka); EXCLUDED: annexure heading but no table",
     "a109f02f6b0465e61ccf7ef63d412265418194fe630460b056998714aea972bc"),
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def bring(path: str, sibling: str | None, pinned: str) -> str:
    """Copy (if missing) and verify one source; return a status line.
    Raises ValueError on a digest mismatch, FileNotFoundError if absent."""
    dest = ROOT / path
    how = "verified"
    if not dest.is_file():
        if sibling is None:
            raise FileNotFoundError(f"author-supplied file missing: {path}")
        src = SIBLINGS / sibling
        if not src.is_file():
            raise FileNotFoundError(f"sibling copy missing: {src}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        try:
            shutil.copyfile(src, part)
            if sha256_of(part) != pinned:
                raise ValueError(f"SHA-256 mismatch in copy of {src}")
            os.replace(part, dest)
        finally:
            part.unlink(missing_ok=True)
        how = f"copied from ../{sibling}"
    actual = sha256_of(dest)
    if actual != pinned:
        raise ValueError(f"SHA-256 mismatch for {path}: expected {pinned}, got {actual}")
    return f"{how}: {path}"


def origin_of(sibling: str | None, upstream: str) -> str:
    if sibling is None:
        return upstream
    return f"local copy of ../{sibling}; upstream {upstream}"


def main() -> int:
    rows, failed = [], 0
    for path, sibling, upstream, pinned in SOURCES:
        try:
            print(bring(path, sibling, pinned))
        except (ValueError, OSError) as e:
            failed += 1
            print(f"FAILED {path}: {e}", file=sys.stderr)
            continue
        rows.append({"path": path, "origin": origin_of(sibling, upstream),
                     "bytes": str((ROOT / path).stat().st_size), "sha256": pinned})
    if failed:
        print(f"{failed} of {len(SOURCES)} sources failed; manifest not written", file=sys.stderr)
        return 1
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_name(MANIFEST.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, MANIFEST)
    print(f"{len(rows)} of {len(SOURCES)} sources verified; wrote {MANIFEST.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
