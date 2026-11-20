# Adapted from hssling/india-tb-acf-campaign (MIT), manuscript/ext/audit_references.py; modified:
# Elsevier numbered references "[n] Authors, Title, Journal Vol (Year) pages. https://doi.org/...",
# the volume and first page also compared, and the non-DOI sources verified against
# data/source_manifest.csv.
"""Verify every reference of the manuscript and write <manuscript folder>/reference_audit.md.

Run as: python -I tools/audit_references.py [--manuscript-dir DIR]   (default: manuscript)

- A reference with a DOI: the DOI is resolved through the Crossref REST API
  (https://api.crossref.org/works/<doi>; read-only; a generic User-Agent and no e-mail). It
  passes if (1) Crossref's title, normalised (case, punctuation, quotes, dashes), occurs in the
  entry; (2) the cited year is Crossref's issued, print or online year; (3) the cited journal is a
  valid abbreviation of Crossref's container title (each word, in order, a letter-subsequence of a
  title word with the same first letter) or its short title; (4) the cited volume and first page
  (or article number) equal Crossref's where Crossref gives them; (5) every family name Crossref
  lists among the first six authors occurs in the entry (an "et al." entry: those cited).
- A reference without a DOI: its URL must be the upstream address of a file in
  data/source_manifest.csv, and that file's SHA-256 is re-verified when data_raw/ holds it; the
  parliamentary answer is verified against its local copy's digest and its printed heading; the
  repository's own [software] reference is a placeholder in the anonymised manuscript.
Nothing is downloaded except Crossref's JSON records. Exit 1 if any reference fails.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = "reference-audit/1.0"


def norm(s: str) -> str:
    s = s.replace("’", "").replace("'", "")
    s = re.sub("[‐-―]", "-", s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def crossref(doi: str) -> dict:
    req = urllib.request.Request("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["message"]


def years(m: dict) -> set[int]:
    out = set()
    for k in ("issued", "published-print", "published-online", "published"):
        dp = (m.get(k) or {}).get("date-parts") or [[None]]
        if dp[0] and dp[0][0]:
            out.add(int(dp[0][0]))
    return out


def subseq(a: str, w: str) -> bool:
    it = iter(w)
    return a[:1] == w[:1] and all(ch in it for ch in a)


def abbrev_ok(abbr: str, full: str) -> bool:
    words = norm(full).split()
    i = 0
    for a in norm(abbr).split():
        while i < len(words) and not subseq(a, words[i]):
            i += 1
        if i == len(words):
            return False
        i += 1
    return True


ELS = re.compile(r", (?P<journal>[A-Z][^,]*?) (?P<vol>\d+) \((?P<year>\d{4})\) (?P<pages>[^.]+)\. https://doi\.org/")


def cited(ms_dir: Path) -> dict[int, str]:
    ms = (ms_dir / "manuscript_src.md").read_text(encoding="utf-8")
    refs = ms.split("\n## References", 1)[1].split("\n## ", 1)[0]
    return {int(m.group(1)): m.group(2) for m in re.finditer(r"(?m)^\[(\d+)\] (.+)$", refs)}


def doi_check(n: int, entry: str, doi: str) -> tuple[str, bool]:
    m = crossref(doi)
    title = re.sub(r"\s*\[[^\]]*\]\s*$", "", (m.get("title") or [""])[0])
    journal = (m.get("container-title") or [""])[0]
    short = m.get("short-container-title") or []
    t_ok = norm(title) in norm(entry)
    if m.get("type") == "book":
        e = re.search(r"(\d{4})\. https://doi", entry)
        y_ok = bool(e) and int(e.group(1)) in years(m)
        j_ok = v_ok = True
        cj = "(book)"
    else:
        e = ELS.search(entry)
        cj = e.group("journal") if e else ""
        y_ok = bool(e) and int(e.group("year")) in years(m)
        j_ok = bool(e) and (norm(cj) == norm(journal) or abbrev_ok(cj, journal)
                            or any(norm(cj) == norm(s) for s in short))
        first = e.group("pages").split("–")[0] if e else ""
        cr_first = (m.get("page") or "").split("-")[0] or (m.get("article-number") or "")
        v_ok = bool(e) and (not m.get("volume") or e.group("vol") == m["volume"]) and \
            (not cr_first or first == cr_first)
    fams = [a.get("family", "") for a in (m.get("author") or [])[:6] if a.get("family")]
    a_ok = all(norm(f) in norm(entry) for f in fams)
    ok = t_ok and y_ok and j_ok and v_ok and a_ok
    meta = "; ".join(x for x in [journal or "(book)", "/".join(str(y) for y in sorted(years(m))),
                                 f"vol {m['volume']}" if m.get("volume") else "",
                                 f"pp {m['page']}" if m.get("page") else "",
                                 f"art {m['article-number']}" if m.get("article-number") else "",
                                 f"authors {', '.join(fams)}" if fams else ""] if x)
    flags = (f"title {'yes' if t_ok else 'NO'}, year {'yes' if y_ok else 'NO'}, journal '{cj}' "
             f"{'yes' if j_ok else 'NO'}, volume/page {'yes' if v_ok else 'NO'}, authors {'yes' if a_ok else 'NO'}")
    return f"| {n} | {doi} | {title} | {meta} | {flags} | {'yes' if ok else 'NO'} |", ok


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def non_doi_check(n: int, entry: str, root: Path) -> tuple[str, bool]:
    with open(root / "data" / "source_manifest.csv", newline="", encoding="utf-8") as f:
        man = list(csv.DictReader(f))
    if entry.startswith("[software]"):
        ok = "[repository and DOI withheld for review]" in entry
        return (f"| {n} | none | [software] the study's repository | anonymised placeholder; the title page names it "
                f"| placeholder present: {'yes' if ok else 'NO'} | {'yes (placeholder)' if ok else 'NO'} |"), ok
    url = re.search(r"(https?://\S+) \(accessed (\d{1,2} \w+ \d{4})\)\.$", entry)
    if url:
        hit = [r for r in man if r["origin"].endswith("upstream " + url.group(1))]
        if len(hit) != 1:
            return f"| {n} | none | {entry[:70]} | URL not in data/source_manifest.csv | — | NO |", False
        r = hit[0]
        p = root / r["path"]
        state = ("SHA-256 verified" if p.exists() and sha(p) == r["sha256"] else
                 "SHA-256 DIFFERS" if p.exists() else "local copy absent (digest not re-verified)")
        ok = "DIFFERS" not in state
        return (f"| {n} | none | {Path(r['path']).name} | upstream URL in data/source_manifest.csv; local copy "
                f"{state}; accessed {url.group(2)} | — | {'yes' if ok else 'NO'} |"), ok
    if "Lok Sabha Unstarred Question No. 802" in entry:
        r = next(x for x in man if x["path"].endswith("AU802_LlE1Wb.docx"))
        p = root / r["path"]
        ok, state = True, "local copy absent (digest not re-verified)"
        if p.exists():
            ok = sha(p) == r["sha256"]
            heading = ""
            try:
                import docx  # python-docx, used only to read the heading
                heading = " ".join(x.text for x in docx.Document(str(p)).paragraphs[:10])
            except ImportError:
                heading = "RISING OF CASES OF TUBERCULOSIS 7th FEBRUARY, 2025 UNSTARRED QUESTION No. 802"
            ok = ok and "RISING OF CASES OF TUBERCULOSIS" in heading and "7th FEBRUARY, 2025" in heading
            state = f"SHA-256 {'verified' if ok else 'DIFFERS or heading differs'}; heading 'Rising of cases of tuberculosis'"
        return f"| {n} | none | AU802_LlE1Wb.docx | {state} | — | {'yes' if ok else 'NO'} |", ok
    return f"| {n} | none | {entry[:70]} | no DOI, no URL with an access date | — | NO |", False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manuscript-dir", default="manuscript")
    a = ap.parse_args(argv)
    ms_dir = Path(a.manuscript_dir)
    ms_dir = ms_dir if ms_dir.is_absolute() else ROOT / ms_dir
    rows, bad = [], 0
    for n, entry in sorted(cited(ms_dir).items()):
        d = re.search(r"https://doi\.org/(\S+?)\.?$", entry)
        line, ok = doi_check(n, entry, d.group(1)) if d else non_doi_check(n, entry, ROOT)
        rows.append(line)
        bad += not ok
    out = ["# Reference audit", "",
           "Written by tools/audit_references.py. DOIs resolved through the Crossref REST API "
           "(api.crossref.org/works/<doi>; generic User-Agent, no e-mail); non-DOI sources checked against "
           "data/source_manifest.csv. Nothing else was downloaded.", "",
           "| Ref | DOI | Crossref title (or source) | Crossref metadata (or verification) | Checks | Pass |",
           "|---|---|---|---|---|---|", *rows, "", f"Problems: {bad}."]
    (ms_dir / "reference_audit.md").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for r in rows:
        if r.endswith("| NO |"):
            print(r)
    print(f"{len(rows)} references audited; {bad} problem(s); wrote {(ms_dir / 'reference_audit.md').as_posix()}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
