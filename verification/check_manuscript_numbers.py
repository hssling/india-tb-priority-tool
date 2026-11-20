# Adapted from hssling/india-tb-acf-campaign (MIT), verification/check_manuscript_numbers.py
# (itself adapted from hssling/india-state-tb-score); modified: one profile, the catalogue of
# this paper (headline estimates, tiers, trends, sensitivities and the district modules from
# outputs/; registration and plan constants from docs/), Elsevier numbered references [n], the
# highlights, the regenerated tables and figure data, and this paper's wording rules.
"""Check every number in the anonymised manuscript against the committed outputs.

Run as: python -I verification/check_manuscript_numbers.py [--manuscript-dir DIR] [--regenerate]

The manuscript folder (default manuscript/; git-ignored, kept private, not in this repository)
holds manuscript_src.md (the anonymised manuscript), highlights.md, title_page_src.md,
cover_letter.md, vitae.md, section_phrases.json, number_skeleton.json and exhibits/. A relative
DIR is taken from the repository root. When the folder or its manuscript_src.md is absent this
prints "SKIPPED: ..." and exits 0 (a fresh clone); check_all then counts the step as skipped. If
manuscript_src.md is present without section_phrases.json (or the reverse) the check FAILS.

Checks (each section's text with its whitespace collapsed; the References are excluded from 1-3):

1. Section phrases. section_phrases.json lists, for each section ("Title", "Abstract", the "## "
   headings, "Highlights"), phrases with {label} placeholders. Each label is a catalogue value
   (catalogue(): from outputs/, docs/registration_event.json, the registered plan and
   ENVIRONMENT.md, formatted by exhibits/formats.py). Every filled phrase must occur whole in its
   own section, so a changed value, a flipped sign or a value moved to another section fails.
2. Every number is accounted for. Each number token of a section gets a label: the placeholder of
   a phrase occurrence that covers it, or a FIXED pattern (exhibit and step names, hypotheses,
   years 2018-2026, catalogue dates, reference numbers [n], the plan's section numbers). A token
   with no label is UNACCOUNTED.
3. The golden skeleton. number_skeleton.json holds each section's ordered {token, label, source}
   of the reviewed text; the current text must give the same tokens and labels in the same order,
   and each golden label must still give the same token. Regenerate only after review:
   python -I verification/check_manuscript_numbers.py --regenerate
4. Claims stated in words (claims()): the labels, which steps have rising flags, which tiers are
   empty, which districts are flagged, and so on, re-tested on the outputs.
5. Exhibits. Tables 1-2 and Figures 1-4 cited, first citations in order; every figure has a
   caption; supplementary tables S1-S12 exist and are first cited in order. exhibits/tables.md
   and each figureN_data.csv are identical to what exhibits/make_tables.py and
   exhibits/make_figures.py produce from outputs/ now (so every cell is traced).
6. References (Elsevier numbered style): citations [n], [n,m] and [n-m] in the text; every number
   in range; every reference cited; numbered 1..N in order of first citation.
7. Highlights: 3 to 5 bullets of at most 85 characters (spaces included). Abstract: at most 250
   words, unstructured, no citation. Keywords: 1 to 7. The whole text (references, tables and
   captions excluded) at most 10,000 words.
8. Anonymisation and wording: no author name, ORCID, institution, e-mail, postcode or repository
   (from the plan's header and the title page) in manuscript_src.md, highlights.md or tables.md;
   the placeholder "[repository and DOI withheld for review]" present; no internal identifiers;
   no American spellings; "shortfall against target", never "missed cases"; no causal or ranking
   language; the H1/H2 labels exactly as in outputs/headline.csv. The AI declaration matches the
   title page word for word.

Exit 1 on any problem.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exhibits.formats import (MINUS, MONTHS, STEP_NAMES, STEPS, and_list, count, day, num, one,  # noqa: E402
                              pct, prob, read_csv, rho, rng, harm)

DEFAULT_MS_DIR = "manuscript"
MS_NAME = "manuscript_src.md"
PHRASES = "section_phrases.json"
SKELETON = "number_skeleton.json"
HIGHLIGHTS = "highlights.md"
TITLE_PAGE = "title_page_src.md"
PLACEHOLDER = "[repository and DOI withheld for review]"
LIMITS = {"abstract": 250, "total": 10000, "highlight_chars": 85}
AI_HEADING = ("Declaration of generative AI and AI-assisted technologies in the manuscript preparation "
              "process")


# --------------------------------------------------------------------------------------
# The plan and the registration
# --------------------------------------------------------------------------------------
def plan_text(root: Path) -> str:
    return (root / "docs" / "analysis_plan.md").read_text(encoding="utf-8")


def plan_has(root: Path, s: str, where: str) -> str:
    """s, after confirming the registered plan states it (so the constant is the plan's)."""
    if s not in re.sub(r"\s+", " ", plan_text(root)):
        raise ValueError(f"the plan ({where}) does not state {s!r}")
    return s


# --------------------------------------------------------------------------------------
# Catalogue: label -> (text as printed, source)
# --------------------------------------------------------------------------------------
def catalogue(root: Path) -> dict[str, tuple[str, str]]:
    c: dict[str, tuple[str, str]] = {}

    def put(label: str, text: str, source: str) -> None:
        if label in c:
            raise ValueError(f"duplicate catalogue label {label}")
        c[label] = (text, source)

    # ---- registration and plan --------------------------------------------------------------
    reg = json.loads((root / "docs" / "registration_event.json").read_text(encoding="utf-8"))
    put("date.registration", day(reg["pushed_at"]), "docs/registration_event.json: pushed_at")
    put("reg.time", reg["pushed_at"][11:19] + " UTC", "docs/registration_event.json: pushed_at")
    put("date.plan", plan_has(root, "21 November 2026", "header and §12"), "docs/analysis_plan.md: date and §12 entries")
    put("date.au802", plan_has(root, "7 February 2025", "§3.1"), "docs/analysis_plan.md §3.1")
    put("plan.draws", plan_has(root, "10,000", "§6.3"), "docs/analysis_plan.md §6.3")
    put("plan.k_main", plan_has(root, "k = 5", "§6.4"), "docs/analysis_plan.md §6.4")
    put("plan.k_sens", plan_has(root, "k = 3 and k = 8", "§6.4"), "docs/analysis_plan.md §6.4")
    put("plan.k_district", plan_has(root, "k = 20", "§9.1"), "docs/analysis_plan.md §9.1")
    for lab, s in (("act", "P ≥ 0.80"), ("probable", "0.50 ≤ P < 0.80"), ("uncertain", "0.20 ≤ P < 0.50"),
                   ("lower", "P < 0.20")):
        plan_has(root, s, "§6.4")
    put("plan.t80", "0.80", "docs/analysis_plan.md §6.4 (act now P ≥ 0.80)")
    put("plan.t50", "0.50", "docs/analysis_plan.md §6.4 (probable priority 0.50 ≤ P < 0.80)")
    put("plan.t20", "0.20", "docs/analysis_plan.md §6.4 (uncertain 0.20 ≤ P < 0.50)")
    put("plan.agree", plan_has(root, "≥80%", "§8.6").replace("≥", "at least "), "docs/analysis_plan.md §8.6")
    put("plan.grid", plan_has(root, "12 entries", "§8.5"), "docs/analysis_plan.md §8.5")
    put("plan.need", plan_has(root, "at least 10 entries agreeing", "§8.6"), "docs/analysis_plan.md §8.6")
    put("plan.z998", plan_has(root, "99.8%", "§9.1"), "docs/analysis_plan.md §9.1")
    put("plan.winsor", plan_has(root, "10%-winsorised", "§9.2"), "docs/analysis_plan.md §9.2")
    put("plan.p75", "75th percentile", plan_has(root, "the 75th percentile of performance", "§6.2") and
        "docs/analysis_plan.md §6.2")
    put("plan.p25", "25th percentile", plan_has(root, "the 25th percentile of loss rates", "§6.2") and
        "docs/analysis_plan.md §6.2")
    put("plan.min_years", plan_has(root, "at least 3 data years", "§7.2"), "docs/analysis_plan.md §7.2")
    put("plan.seed", plan_has(root, "20261121", "§10.1"), "docs/analysis_plan.md §10.1")
    put("plan.denoms", plan_has(root, "about 10⁵ patients", "§10.4").replace("10⁵", "100,000"),
        "docs/analysis_plan.md §10.4 (10⁵ written out)")
    put("plan.ntps_units", plan_has(root, "19–20 units", "§8.1"), "docs/analysis_plan.md §8.1")
    put("plan.ntps_years", "2019 to 2021", plan_has(root, "2019–21", "§3.1") and "docs/analysis_plan.md §3.1")
    put("plan.mp_districts", plan_has(root, "52 distinct districts", "§9.2"), "docs/analysis_plan.md §9.2")
    put("plan.age", plan_has(root, "aged 15 years and over", "§5.2"), "docs/analysis_plan.md §5.2")
    put("plan.pct", plan_has(root, "2.5th and 97.5th percentiles", "§6.3"), "docs/analysis_plan.md §6.3")
    put("plan.d760", plan_has(root, "about 760 districts", "§9.1"), "docs/analysis_plan.md §9.1")
    put("p.band", "between 0.02 and 0.98", "fixed: the band within which a P(top-5) counts as away from 0 and 1 "
        "(the p.mid count; README, Limitations)")

    # ---- the State panel ----------------------------------------------------------------------
    pr = read_csv(root, "outputs/state_priority.csv")
    units = sorted({r["unit"] for r in pr})
    put("units", count(len(units)), "outputs/state_priority.csv: distinct units")
    put("rows", count(len(pr)), "outputs/state_priority.csv: rows")
    put("steps", count(len(STEPS)), "outputs/state_priority.csv: distinct steps")
    mid = [r for r in pr if 0.02 < float(r["p_top5"]) < 0.98]
    put("p.mid", f"{count(len(mid))} of {count(len(pr))}", "outputs/state_priority.csv: 0.02 < p_top5 < 0.98")
    for s in STEPS:
        rs = [r for r in pr if r["step"] == s]
        an = sorted(r["unit"] for r in rs if r["tier"] == "act now")
        put(f"{s}.act", and_list(an), f"outputs/state_priority.csv: {s} tier act now")
        put(f"{s}.n_act", count(len(an)), f"outputs/state_priority.csv: {s} tier act now (count)")
        tot = sum(float(r["harm_averted_mean"]) for r in rs)
        put(f"{s}.total", count(tot), f"outputs/state_priority.csv: {s} sum of harm_averted_mean")
        top = max(rs, key=lambda r: float(r["harm_averted_mean"]))
        put(f"{s}.top", f"{top['unit']}, {harm(top['harm_averted_mean'], top['lo'], top['hi'])}",
            f"outputs/state_priority.csv: {s} largest harm_averted_mean, lo, hi")
        hp = max(rs, key=lambda r: float(r["per_100k"]))
        put(f"{s}.top100k", f"{hp['unit']} ({num(hp['per_100k'], 1)} per 100,000; {hp['tier']})",
            f"outputs/state_priority.csv: {s} largest per_100k and its tier")
    for s in STEPS:
        for t in ("probable priority", "uncertain"):
            names = sorted(r["unit"] for r in pr if r["step"] == s and r["tier"] == t)
            if names:
                put(f"{s}.{t.split()[0]}", and_list(names), f"outputs/state_priority.csv: {s} tier {t}")
    r = one(pr, "Karnataka S1", unit="Karnataka", step="S1")
    put("S1.karnataka_p", prob(r["p_top5"]), "outputs/state_priority.csv: Karnataka S1 p_top5")
    r = one(pr, "Chhattisgarh S1", unit="Chhattisgarh", step="S1")
    put("S1.chh_p", prob(r["p_top5"]), "outputs/state_priority.csv: Chhattisgarh S1 p_top5")
    rising = [r for r in pr if r["rising"] == "True"]
    put("rise.n", count(len(rising)), "outputs/state_priority.csv: rising = True")
    put("rise.act", and_list(sorted(r["unit"] for r in rising if r["tier"] == "act now")),
        "outputs/state_priority.csv: rising and act now")
    put("rise.watch", and_list(sorted(r["unit"] for r in rising if r["tier"] == "watch: rising")),
        "outputs/state_priority.csv: rising and watch: rising")
    put("rise.n_act", count(sum(r["tier"] == "act now" for r in rising)), "outputs/state_priority.csv: rising, act now")
    put("rise.n_watch", count(sum(r["tier"] == "watch: rising" for r in rising)),
        "outputs/state_priority.csv: rising, watch: rising")
    sfb = [r for r in pr if r["small_far_behind"] == "True"]
    put("sfb.n", count(len(sfb)), "outputs/state_priority.csv: small_far_behind = True")
    put("sfb.units", count(len({r["unit"] for r in sfb})), "outputs/state_priority.csv: distinct units small_far_behind")

    # ---- trends --------------------------------------------------------------------------------
    tr = read_csv(root, "outputs/state_trend.csv")
    for s in ("S1", "S3", "S4", "S6"):
        phi = {x["phi"] for x in tr if x["basis"] == "main" and x["step"] == s}
        (p,) = phi
        put(f"phi.{s}", num(p, 1), f"outputs/state_trend.csv: main {s} phi")
    put("trend.differ", count(sum(x["rising_differs"] == "True" for x in tr if x["basis"] == "main")),
        "outputs/state_trend.csv: main rising_differs = True")
    put("trend.reg_rising", count(sum(x["rising"] == "True" for x in tr if x["basis"] == "s6_2022_registered")),
        "outputs/state_trend.csv: s6_2022_registered rising = True")

    # ---- sensitivities and leave-one-out ---------------------------------------------------
    sens = read_csv(root, "outputs/state_priority_sensitivity.csv")
    for an in ("k3", "k8", "benchmark_median", "benchmark_p90"):
        rs = [x for x in sens if x["analysis"] == an]
        put(f"sens.{an}", f"{count(sum(x['tier_changed'] == 'True' for x in rs))} of {count(len(rs))}",
            f"outputs/state_priority_sensitivity.csv: {an} tier_changed")
    loo = read_csv(root, "outputs/leave_one_out.csv")
    most = [x for x in loo if x["analysis"] == "tiers" and x["extreme"] == "most_changes"]
    put("loo.tiers_most", count(most[0]["n_tier_changes"]), "outputs/leave_one_out.csv: tiers most_changes")
    put("loo.tiers_most_units", and_list(sorted(x["omitted"] for x in most)),
        "outputs/leave_one_out.csv: tiers most_changes omitted")
    for an in ("H1", "H2"):
        lo = [x for x in loo if x["analysis"] == an and x["extreme"] == "min"]
        hi = [x for x in loo if x["analysis"] == an and x["extreme"] == "max"]
        put(f"loo.{an}", f"{rho(lo[0]['value'])} (without {and_list(sorted(x['omitted'] for x in lo)).replace(' and ', ' or ')})"
                         f" to {rho(hi[0]['value'])} (without {and_list(sorted(x['omitted'] for x in hi)).replace(' and ', ' or ')})",
            f"outputs/leave_one_out.csv: {an} min and max")

    # ---- headline ------------------------------------------------------------------------------
    hl = {x["estimate"]: x for x in read_csv(root, "outputs/headline.csv")}
    for e in ("H1", "H2"):
        x = hl[e]
        put(f"{e}.value", rho(x["value"]), f"outputs/headline.csv: {e} value")
        put(f"{e}.ci", rng(rho(x["lo"]), rho(x["hi"])), f"outputs/headline.csv: {e} lo, hi")
        put(f"{e}.agree", f"{count(x['n_agree'])} of {count(x['n_grid'])}", f"outputs/headline.csv: {e} n_agree, n_grid")
        put(f"{e}.n", count(x["n"]), f"outputs/headline.csv: {e} n")
        put(f"{e}.label", x["label"], f"outputs/headline.csv: {e} label")
    put("H3.value", pct(hl["H3"]["value"]), "outputs/headline.csv: H3 value")
    for s in ("S2", "S3", "S4", "S5"):
        put(f"H3.{s}", pct(hl[f"H3 share {s}"]["value"]), f"outputs/headline.csv: H3 share {s} value")
    put("H1.gap", rho(hl["H1 rate-gap rho (descriptive)"]["value"]), "outputs/headline.csv: H1 rate-gap rho")
    t = hl["H1 top-5 overlap"]
    put("H1.overlap", f"{count(t['value'])} of {count(t['n'])}", "outputs/headline.csv: H1 top-5 overlap value, n")
    x = hl["H2 signed shortfall per 100,000 (descriptive)"]
    put("H2.signed", f"{rho(x['value'])} ({rng(rho(x['lo']), rho(x['hi']))})",
        "outputs/headline.csv: H2 signed shortfall value, lo, hi")
    h1_units = re.search(r"\((\d+) units\)", hl["H1"]["note"]).group(1)
    put("H1.units", count(h1_units), "outputs/headline.csv: H1 note (units)")
    sp = read_csv(root, "outputs/spec_curve.csv")
    for e in ("H1", "H2"):
        v = [float(x["value"]) for x in sp if x["estimate"] == e]
        put(f"{e}.grid_range", rng(rho(min(v)), rho(max(v))), f"outputs/spec_curve.csv: {e} min and max value")

    # ---- S6 2022 on the registered denominator (plan §12.2) --------------------------------
    dr = read_csv(root, "outputs/state_harm_draws_summary.csv")
    sel = [x for x in dr if x["step"] == "S6" and x["year"] == "2022" and x["benchmark"] == "p75"
           and x["shrinkage"] == "on" and x["p_top5"]]
    top_main = {x["unit"] for x in sel if x["basis"] == "main" and float(x["p_top5"]) >= 0.80}
    top_reg = {x["unit"] for x in sel if x["basis"] == "s6_2022_registered" and float(x["p_top5"]) >= 0.80}
    put("s6reg.common", f"{count(len(top_main & top_reg))} of {count(len(top_main))}",
        "outputs/state_harm_draws_summary.csv: S6 2022 p75/on units with p_top5 >= 0.80 on both bases")
    na = read_csv(root, "outputs/na_cells.csv")
    put("s6reg.na", count(sum(x["na"] == "True" and x["panel"] == "state_panel_s6_2022_registered" for x in na)),
        "outputs/na_cells.csv: registered panel, na = True")

    # ---- district modules ----------------------------------------------------------------
    d = read_csv(root, "outputs/district_national_2018.csv")
    put("d.n", count(len({(x["state"], x["district"]) for x in d})), "outputs/district_national_2018.csv: districts")
    for st in ("D1", "D2"):
        rs = [x for x in d if x["step"] == st]
        put(f"{st}.act", count(sum(x["tier"] == "act now" for x in rs)), f"outputs/district_national_2018.csv: {st} act now")
        put(f"{st}.upper", count(sum(x["tier"] in ("act now", "probable priority", "uncertain") for x in rs)),
            f"outputs/district_national_2018.csv: {st} upper tiers")
        put(f"{st}.above", count(sum(x["funnel_flag"] == "above State limits" for x in rs)),
            f"outputs/district_national_2018.csv: {st} above State limits")
        put(f"{st}.below", count(sum(x["funnel_flag"] == "below State limits" for x in rs)),
            f"outputs/district_national_2018.csv: {st} below State limits")
        put(f"{st}.phi", num(rs[0]["phi"], 1), f"outputs/district_national_2018.csv: {st} phi")
    m = read_csv(root, "outputs/district_mp_mh.csv")
    for s, k in (("Madhya Pradesh", "mp"), ("Maharashtra", "mh")):
        rs = [x for x in m if x["state"] == s]
        put(f"{k}.n", count(len(rs)), f"outputs/district_mp_mh.csv: {s} rows")
        put(f"{k}.change", pct(rs[0]["state_change"], 1), f"outputs/district_mp_mh.csv: {s} state_change")
        put(f"{k}.phi", num(rs[0]["phi"], 2), f"outputs/district_mp_mh.csv: {s} phi")
        fell = sorted(x["district"].replace("_", " ") for x in rs if x["flag"] == "fell beyond adjusted limits")
        rose = sorted(x["district"].replace("_", " ") for x in rs if x["flag"] == "rose beyond adjusted limits")
        put(f"{k}.fell", and_list(fell), f"outputs/district_mp_mh.csv: {s} fell beyond adjusted limits")
        put(f"{k}.n_fell", count(len(fell)), f"outputs/district_mp_mh.csv: {s} fell (count)")
        if rose:
            put(f"{k}.rose", and_list(rose), f"outputs/district_mp_mh.csv: {s} rose beyond adjusted limits")
            put(f"{k}.n_rose", count(len(rose)), f"outputs/district_mp_mh.csv: {s} rose (count)")
    ch = one(m, "Chhatarpur", district="Chhatarpur")
    put("mp.chhatarpur", pct(ch["rel_change"], 1), "outputs/district_mp_mh.csv: Chhatarpur rel_change")
    put("mpmh.flagged", count(sum("beyond" in x["flag"] for x in m)), "outputs/district_mp_mh.csv: flagged districts")

    # ---- software ----------------------------------------------------------------------------
    env = (root / "ENVIRONMENT.md").read_text(encoding="utf-8")
    for pkg in ("Python", "numpy", "scipy", "matplotlib"):
        put(f"sw.{pkg.lower()}", f"{pkg} " + re.search(rf"{pkg} (\d+\.\d+\.\d+)", env).group(1), "ENVIRONMENT.md")
    return c


@lru_cache(maxsize=4)
def catalogue_cached(root: Path) -> dict[str, tuple[str, str]]:
    return catalogue(root)


# --------------------------------------------------------------------------------------
# Claims stated in words, re-tested on the outputs
# --------------------------------------------------------------------------------------
def claims(root: Path) -> list[str]:
    out: list[str] = []

    def need(ok: bool, msg: str) -> None:
        if not ok:
            out.append(f"CLAIM fails: {msg}")

    hl = {x["estimate"]: x for x in read_csv(root, "outputs/headline.csv")}
    need(hl["H1"]["label"] == "supported", "H1 is supported")
    need(hl["H2"]["label"] == "not established", "H2 is not established")
    need(float(hl["H2"]["lo"]) < 0 < float(hl["H2"]["hi"]), "the H2 interval includes 0")
    need(float(hl["H2"]["value"]) > 0 and all(float(x["value"]) > 0 for x in read_csv(root, "outputs/spec_curve.csv")
                                              if x["estimate"] == "H2"), "every H2 grid entry is positive")
    need(float(hl["H1"]["lo"]) > 0, "the H1 interval lies above 0")
    pr = read_csv(root, "outputs/state_priority.csv")
    need({x["step"] for x in pr if x["rising"] == "True"} == {"S3"}, "rising flags occur only for S3")
    need(not any(x["tier"] == "watch: rising" and x["step"] != "S3" for x in pr), "watch: rising only in S3")
    for s in ("S2", "S3", "S4", "S6"):
        need(not any(x["step"] == s and x["tier"] in ("probable priority", "uncertain") for x in pr),
             f"{s} has no probable-priority or uncertain unit")
    need(sum(x["tier"] == "act now" for x in pr if x["step"] in ("S1", "S5")) == 8, "S1 and S5 have four act-now units each")
    need(all(x["tier"] == "act now" for x in pr if x["unit"] in ("Bihar", "Madhya Pradesh") and x["step"] != "S3"),
         "Bihar and Madhya Pradesh are act now in every step but S3")
    need(all(x["tier"] == "watch: rising" for x in pr if x["unit"] in ("Bihar", "Madhya Pradesh") and x["step"] == "S3"),
         "Bihar and Madhya Pradesh are watch: rising in S3")
    big = {s: max((x for x in pr if x["step"] == s), key=lambda x: float(x["per_100k"])) for s in STEPS}
    need(big["S1"]["unit"] == "Chhattisgarh" and big["S1"]["tier"] == "uncertain",
         "the largest S1 harm per 100,000 is Chhattisgarh's, an uncertain unit")
    need(big["S6"]["unit"] == "Delhi", "the largest S6 harm per 100,000 is Delhi's")
    sfb = [x for x in pr if x["small_far_behind"] == "True"]
    need(all(x["tier"] == "lower priority" for x in sfb), "every small-but-far-behind unit is lower priority")
    tr = read_csv(root, "outputs/state_trend.csv")
    need({x["trend_status"] for x in tr if x["step"] == "S2"} == {"not estimable (definition change)"}, "S2 has no trend")
    need({x["trend_status"] for x in tr if x["step"] == "S5"} == {"no trend"}, "S5 has no trend")
    need(not any(x["rising"] == "True" for x in tr if x["basis"] == "s6_2022_registered"),
         "no S6 rising flag on the registered basis")
    need(not any(x["rising_differs"] == "True" for x in tr), "the sensitivity trend model changes no rising flag")
    phis = {x["step"]: float(x["phi"]) for x in tr if x["basis"] == "main" and x["phi"]}
    need(min(phis, key=phis.get) == "S3" and max(phis, key=phis.get) == "S6", "φ smallest for S3 and largest for S6")
    m = read_csv(root, "outputs/district_mp_mh.csv")
    need(all(float(x["state_change"]) < 0 for x in m), "both States' pooled notifications fell")
    need(not any(x["flag"] == "rose beyond adjusted limits" for x in m if x["state"] == "Maharashtra"),
         "no Maharashtra district rose beyond the limits")
    need(all(x["additive_position_998"] == "within adjusted limits" for x in m if x["state"] == "Madhya Pradesh"),
         "under the additive adjustment no Madhya Pradesh district is beyond the limits")
    d = read_csv(root, "outputs/district_national_2018.csv")
    need({x["data_label"] for x in d} == {"2018 data (historical)"}, "the national district module is labelled 2018 (historical)")
    upper = [x for x in d if x["tier"] != "lower priority"]
    need(all(float(x["denominator"]) > 1000 for x in upper), "every upper-tier district has a denominator above 1,000")
    b3 = {x["year"]: float(x["rate_bench"]) for x in read_csv(root, "outputs/state_harm_draws_summary.csv")
          if (x["basis"], x["step"], x["benchmark"], x["shrinkage"]) == ("main", "S3", "p75", "on")}
    need(b3["2018"] < b3["2019"] < b3["2021"] < b3["2022"], "the S3 benchmark rose between 2018 and 2022")
    loo = read_csv(root, "outputs/leave_one_out.csv")
    need(all(x["value"] and float(x["value"]) > 0 for x in loo if x["analysis"] in ("H1", "H2")),
         "every leave-one-out H1 and H2 is positive")
    return out


# --------------------------------------------------------------------------------------
# Section phrases (private; read at run time from <folder>/section_phrases.json)
# --------------------------------------------------------------------------------------
def load_phrase_file(ms_dir: Path) -> dict:
    """{"sections": {section: [phrase, ...]}, "mutation_anchors": {...}}; kept with the manuscript
    (git-ignored) because the phrases quote it."""
    d = json.loads((ms_dir / PHRASES).read_text(encoding="utf-8"))
    secs = d.get("sections") if isinstance(d, dict) else None
    if not isinstance(secs, dict) or not secs or not all(
            isinstance(k, str) and isinstance(v, list) and all(isinstance(x, str) for x in v) for k, v in secs.items()):
        raise ValueError(f"{PHRASES}: 'sections' must map section names to lists of phrases")
    return d


def section_phrases(ms_dir: Path) -> dict[str, list[str]]:
    return load_phrase_file(ms_dir)["sections"]


# --------------------------------------------------------------------------------------
# Fixed (non-result) number patterns
# --------------------------------------------------------------------------------------
SUPPLEMENT = [f"S{k}" for k in range(1, 13)]
TABLES = [1, 2]
FIGURES = [1, 2, 3, 4]
FIXED: list[tuple[str, str]] = [
    ("reference", r"\[\d+(?:[,–]\d+)*\]"),
    ("exhibit", r"\bTables? S\d{1,2}(?:(?:,| and| to|–) ?S\d{1,2})*\b"),
    ("exhibit", r"\b(?:Table|Figure|Fig\.)s? [1-4][A-D]?(?:(?:,| and| to) [1-4][A-D]?)*\b"),
    ("step", r"\b[SD][1-6]\b(?:–[SD][1-6]\b)?"),
    ("hypothesis", r"\b[HQ][1-4]\b"),
    ("ci_level", r"\b95%"),
    ("topk", r"\btop[- ](?:5|20|k|five)\b|\bP\(top-(?:5|20|k)\)"),
    ("per100k", r"\bper[- ]100,000\b"),
    ("section", r"\bSections? [2-7]\.\d{1,2}\b|### \d\.\d{1,2}\.|## \d\. "),
    ("plan_section", r"\b(?:section|sections) 1[12](?:\.\d)?(?: and 1[12]\.\d)?\b"),
    ("date", r"\b\d{1,2} (?:" + "|".join(MONTHS) + r") 20\d\d\b"),
    ("year", r"(?<![\d.,])20(?:1[7-9]|2[0-6])(?![\d]|[.,]\d)"),
]
NUMBER = re.compile(r"\d+(?:,\d{3}(?!\d))*(?:\.\d+)?")


def sections(text: str) -> dict[str, str]:
    """Heading -> whitespace-collapsed text: the title ("Title"), every '## ' section (its
    '### ' subsections included) but the References."""
    out: dict[str, list[str]] = {}
    cur = None
    for ln in text.splitlines():
        if ln.startswith("# ") and not out:
            out["Title"] = [ln[2:]]
            cur = None
        elif ln.startswith("## "):
            cur = re.sub(r"^\d+\.\s+", "", ln[3:].strip())
            out[cur] = []
        elif cur is not None:
            out[cur].append(ln)
    return {k: re.sub(r"\s+", " ", "\n".join(v)).strip() for k, v in out.items() if k != "References"}


def fill(template: str, cat: dict) -> tuple[str, list[tuple[int, int, str]]]:
    out, spans, pos = "", [], 0
    for m in re.finditer(r"\{([^}]+)\}", template):
        out += template[pos:m.start()]
        val = cat[m.group(1)][0]
        spans.append((len(out), len(out) + len(val), m.group(1)))
        out += val
        pos = m.end()
    return out + template[pos:], spans


def _occurrences(body: str, phrase: str) -> list[int]:
    """Where the phrase occurs whole: a phrase that starts (ends) with a digit or sign may not
    continue a number on that side."""
    before = r"(?<![\d.,−-])" if re.match(r"[\d−-]", phrase) else ""
    after = r"(?![\d]|[.,]\d)" if re.search(r"\d$", phrase) else ""
    pat = re.compile(before + re.escape(phrase) + after)
    return [m.start() for m in pat.finditer(body)]


def assign(name: str, body: str, cat: dict, required: list[str]) -> tuple[list[dict], list[str]]:
    """Label every number token of one section; return (skeleton entries, problems)."""
    probs: list[str] = []
    labels: dict[int, tuple[str, str]] = {}
    toks = [(m.start(), m.end(), m.group()) for m in NUMBER.finditer(body)]
    for tpl in required:
        try:
            phrase, spans = fill(tpl, cat)
        except KeyError as e:
            probs.append(f"PHRASES in {name}: unknown label {e}")
            continue
        occ = _occurrences(body, phrase)
        if not occ:
            probs.append(f"MISSING in {name}: {phrase!r}")
            continue
        for at in occ:
            for s, e, _ in toks:
                for ps, pe, lab in spans:
                    if at + ps <= s and e <= at + pe and s not in labels:
                        labels[s] = (lab, cat[lab][1])
    dates = {v[0]: k for k, v in cat.items() if k.startswith("date.")}
    for kind, pat in FIXED:
        for m in re.finditer(pat, body):
            for s, e, _ in toks:
                if m.start() <= s and e <= m.end() and s not in labels:
                    if kind == "date":
                        lab = dates.get(m.group())
                        if lab is None:
                            probs.append(f"DATE in {name} is not a catalogue date: {m.group()!r}")
                            continue
                        labels[s] = (lab, cat[lab][1])
                    else:
                        labels[s] = (f"fixed:{kind}", f"fixed {kind}: {m.group()}")
    entries = []
    for s, e, t in toks:
        if s not in labels:
            probs.append(f"UNACCOUNTED number in {name}: {t!r} in ...{body[max(0, s - 40):e + 20]}...")
            entries.append({"token": t, "label": "UNACCOUNTED", "source": ""})
        else:
            entries.append({"token": t, "label": labels[s][0], "source": labels[s][1]})
    return entries, probs


def all_sections(text: str, highlights: str | None) -> dict[str, str]:
    secs = sections(text)
    if highlights is not None:
        secs["Highlights"] = re.sub(r"\s+", " ", "\n".join(ln for ln in highlights.splitlines()
                                                           if not ln.startswith("#"))).strip()
    return secs


def skeleton(text: str, highlights: str | None, root: Path,
             required: dict[str, list[str]]) -> tuple[dict[str, list[dict]], list[str]]:
    cat = catalogue_cached(root)
    secs = all_sections(text, highlights)
    out, probs = {}, []
    for name in required:
        if name not in secs:
            probs.append(f"MISSING section {name!r}")
    for name, body in secs.items():
        entries, p = assign(name, body, cat, required.get(name, []))
        out[name] = entries
        probs += p
    return out, probs


def skeleton_problems(now: dict, gold: dict | None, root: Path) -> list[str]:
    if gold is None:
        return [f"{SKELETON} missing: after review run python -I verification/check_manuscript_numbers.py --regenerate"]
    cat = catalogue_cached(root)
    out = []
    for name in sorted(set(now) | set(gold)):
        a = [(x["token"], x["label"]) for x in gold.get(name, [])]
        b = [(x["token"], x["label"]) for x in now.get(name, [])]
        if a != b:
            k = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            out.append(f"SKELETON {name}: entry {k + 1} is {b[k] if k < len(b) else '(none)'}, golden has "
                       f"{a[k] if k < len(a) else '(none)'} ({len(b)} tokens now, {len(a)} golden)")
        for x in gold.get(name, []):
            lab = x["label"]
            if lab.startswith("fixed:"):
                continue
            if lab not in cat:
                out.append(f"SKELETON {name}: golden label {lab} is not in the catalogue")
            elif x["token"] not in NUMBER.findall(cat[lab][0]):
                out.append(f"SKELETON {name}: golden token {x['token']!r} is no longer in {lab} = {cat[lab][0]!r}")
    return out


# --------------------------------------------------------------------------------------
# Exhibits: citations, captions, and the tables and figure data regenerated from outputs/
# --------------------------------------------------------------------------------------
def exhibit_problems(text: str) -> list[str]:
    secs = sections(text)
    body = " ".join(v for k, v in secs.items() if k not in ("Title", "Abstract", "Figure captions"))
    out = []
    for kind, want in (("Table", TABLES), ("Figure", FIGURES)):
        seen = []
        alt = r"Fig\." if kind == "Figure" else kind
        for m in re.finditer(rf"(?:\b{kind}s?|\b{alt}) ((?:[1-9][A-D]?(?:, | and | to )?)+)", body):
            seen += [int(n) for n in re.findall(r"[1-9]", m.group(1))]
        first = list(dict.fromkeys(seen))
        if sorted(first) != want:
            out.append(f"EXHIBITS: {kind}s cited {first}, expected each of {want}")
        elif first != want:
            out.append(f"EXHIBITS: first citations of {kind}s out of order: {first}")
    sup: list[str] = []
    for m in re.finditer(r"\bTables? (S\d{1,2}(?:(?:,| and| to|–) ?S\d{1,2})*)", body):
        parts = re.findall(r"S(\d{1,2})", m.group(1))
        if re.search(r"(?: to|–) ?S", m.group(1)) and len(parts) == 2:
            parts = [str(k) for k in range(int(parts[0]), int(parts[1]) + 1)]
        for p in parts:
            s = f"S{p}"
            if s not in SUPPLEMENT:
                out.append(f"EXHIBITS: supplementary {s} does not exist")
            else:
                sup.append(s)
    first = list(dict.fromkeys(sup))
    if first != [s for s in SUPPLEMENT if s in first]:
        out.append(f"EXHIBITS: supplementary tables first cited out of order: {first}")
    never = [s for s in SUPPLEMENT if s not in first]
    if never:
        out.append(f"EXHIBITS: supplementary tables never cited: {never}")
    caps = secs.get("Figure captions", "")
    for n in FIGURES:
        if f"Fig. {n}." not in caps:
            out.append(f"EXHIBITS: no caption for Fig. {n}")
    return out


def regenerated_problems(ms_dir: Path, root: Path) -> list[str]:
    """tables.md and each figureN_data.csv equal what the exhibit scripts produce from outputs/ now."""
    from exhibits import make_figures, make_tables
    out = []
    ex = ms_dir / "exhibits"
    p = ex / "tables.md"
    if not p.exists():
        return ["EXHIBITS: exhibits/tables.md missing (python -I exhibits/make_tables.py)"]
    if p.read_text(encoding="utf-8") != make_tables.render_md(make_tables.build(root)):
        out.append("EXHIBITS: exhibits/tables.md differs from the tables regenerated from outputs/")
    for k, fn in make_figures.FIGURES.items():
        q = ex / f"figure{k}_data.csv"
        if not q.exists() or q.read_bytes() != make_figures.data_csv(fn(root)):
            out.append(f"EXHIBITS: exhibits/figure{k}_data.csv differs from the data regenerated from outputs/")
    return out


# --------------------------------------------------------------------------------------
# References: Elsevier numbered style
# --------------------------------------------------------------------------------------
def ref_list(text: str) -> list[tuple[int, str]]:
    part = text.split("\n## References", 1)
    if len(part) != 2:
        return []
    body = part[1].split("\n## ", 1)[0]
    return [(int(m.group(1)), m.group(2)) for m in re.finditer(r"(?m)^\[(\d+)\] (.+)$", body)]


def citations(text: str) -> list[int]:
    body = text.split("\n## References", 1)[0]
    order: list[int] = []
    for m in re.finditer(r"\[(\d+(?:[,–]\d+)*)\]", body):
        for part in m.group(1).split(","):
            a, _, b = part.partition("–")
            order += list(range(int(a), int(b or a) + 1))
    return order


def reference_problems(text: str) -> list[str]:
    refs = ref_list(text)
    if not refs:
        return ["REFERENCES: no '## References' section with entries '[n] ...'"]
    n = len(refs)
    out = []
    if [k for k, _ in refs] != list(range(1, n + 1)):
        out.append("REFERENCES: list not numbered 1..n")
    order = citations(text)
    for k in sorted(set(order)):
        if not 1 <= k <= n:
            out.append(f"REFERENCES: citation {k} outside 1..{n}")
    first = list(dict.fromkeys(order))
    if first != sorted(first):
        out.append(f"REFERENCES: not numbered in order of first citation: {first}")
    never = sorted(set(range(1, n + 1)) - set(order))
    if never:
        out.append(f"REFERENCES: never cited: {never}")
    for k, e in refs:
        if "doi.org" not in e and "accessed" not in e.lower() and "[software]" not in e and "[dataset]" not in e \
                and "Lok Sabha" not in e:
            out.append(f"REFERENCES: [{k}] has neither a DOI nor an access date")
    return out


# --------------------------------------------------------------------------------------
# Lengths: highlights, abstract, keywords, whole text
# --------------------------------------------------------------------------------------
def words(s: str) -> int:
    return len(re.findall(r"\S+", re.sub(r"[*_#|]", " ", s)))


def bullets(highlights: str) -> list[str]:
    return [ln[2:].strip() for ln in highlights.splitlines() if ln.startswith("- ")]


def length_problems(text: str, highlights: str | None) -> list[str]:
    out = []
    secs = sections(text)
    ab = secs.get("Abstract", "")
    kw = re.search(r"\*\*Keywords:\*\* (.+)$", ab)
    abstract = ab[:kw.start()].strip() if kw else ab
    if words(abstract) > LIMITS["abstract"]:
        out.append(f"LENGTH: abstract {words(abstract)} words, limit {LIMITS['abstract']}")
    if re.search(r"\[\d", abstract):
        out.append("LENGTH: the abstract cites a reference")
    if not kw:
        out.append("LENGTH: no '**Keywords:**' line at the end of the Abstract")
    else:
        k = [x.strip() for x in kw.group(1).split(";") if x.strip()]
        if not 1 <= len(k) <= 7:
            out.append(f"LENGTH: {len(k)} keywords (1 to 7 allowed)")
        for x in k:
            if re.search(r"\b(?:and|of)\b", x) and " " in x:
                out.append(f"LENGTH: keyword {x!r} is a multi-word keyword with 'and' or 'of'")
    total = sum(words(v) for k, v in secs.items() if k not in ("Figure captions",))
    if total > LIMITS["total"]:
        out.append(f"LENGTH: {total} words (references, tables and captions excluded), limit {LIMITS['total']}")
    if highlights is not None:
        b = bullets(highlights)
        if not 3 <= len(b) <= 5:
            out.append(f"HIGHLIGHTS: {len(b)} bullets (3 to 5 required)")
        for x in b:
            if len(x) > LIMITS["highlight_chars"]:
                out.append(f"HIGHLIGHTS: {len(x)} characters (limit {LIMITS['highlight_chars']}): {x!r}")
    return out


# --------------------------------------------------------------------------------------
# Anonymisation and wording
# --------------------------------------------------------------------------------------
BANNED = [
    (r"\bTask \d|\bfix round\b|\breviewer\b|\bcontroller\b|\bimplementer\b|\bdispatch", "drafting-process language"),
    (r"\bITR ?20\d\d\b|\bTBAR\b|\bAU ?802\b|\bA1\.\d", "a shorthand source identifier"),
    (r"§", "a section sign (write 'plan section 12.2')"),
    (r"\b(?:outputs|data|verification|exhibits|src|docs)/\S+|\.py\b|\.csv\b", "a file path"),
    (r"\bplan_12|\bs6_2022_registered\b|\bharm_averted_mean\b|\bp_top5\b", "an internal variable name"),
]
WORDING = [
    (r"\bmissed cases?\b|\bmissing cases?\b", "say 'shortfall against target', never 'missed cases'"),
    (r"\bcaus(?:ed|es|ing)\b|\bled to\b|\bresulted in\b|\bimpact of\b|\beffect of the\b|\bdriven by the programme\b",
     "causal language"),
    (r"\branked (?:first|second|third|\d)|\b(?:first|second|third|top)-ranked\b|\brank(?:ed|s)? (?:first|highest|lowest)\b"
     r"|\bnumber one\b|\bworst[- ]performing\b|\bbest[- ]performing\b|\bfailing\b", "ranking or blaming language"),
]
AMERICAN = [r"\banalyz", r"\bstandardiz", r"(?<!World Health )\borganiz", r"\bprogram\b(?! Plan)", r"\bprograms\b",
            r"\bcolor", r"\bcenter", r"\bbehavior", r"\bmodeling\b", r"\blabeled\b", r"\bminimiz", r"\bprioritiz",
            r"\brecogniz", r"\butiliz", r"\bcategoriz", r"\bhospitaliz", r"\bemphasiz", r"\bfavor", r"\bjudgment"]


def author_markers(root: Path, ms_dir: Path | None = None) -> list[str]:
    """Strings that would de-anonymise: the plan's Author and Repository lines (name, ORCID,
    institution, postcode, repository and account), the title page's e-mail, and the names of
    the author's companion repositories."""
    head = plan_text(root).split("\n---", 1)[0]
    states = {x["unit"] for x in read_csv(root, "outputs/state_priority.csv")} | {"India"}
    marks: list[str] = []
    for ln in head.splitlines():
        if ln.startswith("**Author:**"):
            body = ln.split(":**", 1)[1]
            for p in re.split(r"[,.]", body):
                p = p.strip()
                if len(p) >= 5 and not re.search(r"Professor|Single author|ORCID|Department of Community", p) \
                        and p not in states:
                    marks.append(p)
            marks += re.findall(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", body)
            marks += re.findall(r"\b\d{6}\b", body)
        if ln.startswith("**Repository:**"):
            url = ln.split(":**", 1)[1].strip()
            marks += [url, url.split("github.com/")[-1], url.split("github.com/")[-1].split("/")[0]]
    marks += ["Siddalingaiah", "Shridevi", "Tumkur", "zenodo", "github", "india-state-tb-score",
              "india-tb-acf-campaign", "tb_state_score", "tb_acf_campaign"]
    if ms_dir is not None and (ms_dir / TITLE_PAGE).exists():
        marks += re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", (ms_dir / TITLE_PAGE).read_text(encoding="utf-8"))
    return sorted({m for m in marks if m}, key=str.lower)


def wording_problems(name: str, text: str, root: Path, ms_dir: Path | None, anonymised: bool) -> list[str]:
    out = []
    body = text.split("\n## References", 1)[0]
    if name == "exhibits/tables.md":
        body = "\n".join(ln for ln in body.splitlines() if not ln.startswith("# Tables (generated"))
    if anonymised:
        low = text.lower()
        for m in author_markers(root, ms_dir):
            if m.lower() in low:
                out.append(f"ANONYMISATION in {name}: contains {m!r}")
    for pat, what in BANNED + WORDING:
        for m in re.finditer(pat, body, re.I if (pat, what) in WORDING else 0):
            out.append(f"WORDING in {name}: {what}: {m.group()!r}")
    for pat in AMERICAN:
        for m in re.finditer(pat, body, re.I):
            out.append(f"SPELLING in {name}: American form {m.group()!r}")
    return out


def label_problems(text: str, root: Path) -> list[str]:
    """Each label is written exactly as in outputs/headline.csv wherever H1 or H2 is labelled."""
    hl = {x["estimate"]: x["label"] for x in read_csv(root, "outputs/headline.csv")}
    out = []
    for m in re.finditer(r"\b(H[12])\b[^.\n]{0,160}?\b(supported|not established|established|confirmed|validated)\b",
                         text.split("\n## References", 1)[0]):
        e, lab = m.group(1), m.group(2)
        if lab in ("established", "confirmed", "validated") or (lab == "supported" and hl[e] != "supported") \
                or (lab == "not established" and hl[e] != "not established"):
            out.append(f"LABEL: {e} written as {lab!r} in ...{m.group()[-80:]}...; outputs/headline.csv has {hl[e]!r}")
    return out


def declaration_problems(text: str, title_page: str) -> list[str]:
    ms = sections(text).get(AI_HEADING, "")
    m = re.search(r"\*\*" + re.escape(AI_HEADING) + r"\.?\*\* *(.+)", title_page)
    page = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    if not ms or not page:
        return ["DECLARATION: the AI declaration is missing from the manuscript or the title page"]
    if ms != page:
        return ["DECLARATION: the AI declaration differs between the manuscript and the title page"]
    return []


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------
def manuscript_dir(root: Path, argv: list[str]) -> tuple[Path, list[str]]:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--manuscript-dir", default=DEFAULT_MS_DIR)
    a, rest = ap.parse_known_args(argv)
    d = Path(a.manuscript_dir)
    return (d if d.is_absolute() else root / d), rest


def rel(p: Path, root: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def load_gold(ms_dir: Path) -> dict | None:
    p = ms_dir / SKELETON
    return json.loads(p.read_text(encoding="utf-8"))["sections"] if p.exists() else None


def read_opt(ms_dir: Path, name: str) -> str | None:
    p = ms_dir / name
    return p.read_text(encoding="utf-8") if p.exists() else None


def caveat_problems(text: str, caveats: dict[str, list[str]]) -> list[str]:
    """Each caveat (private: the "caveats" of section_phrases.json) occurs whole in its section."""
    secs = sections(text)
    return [f"CAVEAT missing in {name}: {c!r}" for name, cs in caveats.items() for c in cs
            if c not in secs.get(name, "")]


def problems(root: Path, ms_dir: Path, text: str | None = None, gold: dict | None = None,
             required: dict | None = None, highlights: str | None = None, exhibits: bool = True) -> list[str]:
    """Every problem of the manuscript folder (the arguments override what is read from it;
    exhibits=False skips regenerating the tables and figure data, for the mutation sweep)."""
    text = text if text is not None else (ms_dir / MS_NAME).read_text(encoding="utf-8")
    gold = gold if gold is not None else load_gold(ms_dir)
    required = required if required is not None else section_phrases(ms_dir)
    highlights = highlights if highlights is not None else read_opt(ms_dir, HIGHLIGHTS)
    if not required:
        return [f"PHRASES: no section phrases ({PHRASES} missing or empty)"]
    now, out = skeleton(text, highlights, root, required)
    out += skeleton_problems(now, gold, root)
    out += claims(root)
    out += exhibit_problems(text)
    if exhibits:
        out += regenerated_problems(ms_dir, root)
    caveats = load_phrase_file(ms_dir).get("caveats", {})
    if not caveats:
        out.append(f"CAVEAT: no caveats listed in {PHRASES}")
    out += caveat_problems(text, caveats)
    out += reference_problems(text)
    out += length_problems(text, highlights)
    out += label_problems(text, root)
    out += wording_problems(MS_NAME, text, root, ms_dir, anonymised=True)
    if PLACEHOLDER not in text:
        out.append(f"ANONYMISATION: the placeholder {PLACEHOLDER!r} is missing from {MS_NAME}")
    if highlights is None:
        out.append(f"MISSING: {HIGHLIGHTS}")
    else:
        out += wording_problems(HIGHLIGHTS, highlights, root, ms_dir, anonymised=True)
    tables = read_opt(ms_dir, "exhibits/tables.md")
    if tables is not None:
        out += wording_problems("exhibits/tables.md", tables, root, ms_dir, anonymised=True)
    for name in (TITLE_PAGE, "cover_letter.md", "vitae.md"):
        t = read_opt(ms_dir, name)
        if t is None:
            out.append(f"MISSING: {name}")
            continue
        out += [p for p in wording_problems(name, t, root, ms_dir, anonymised=False)
                if "file path" not in p or name != "cover_letter.md"]
    tp = read_opt(ms_dir, TITLE_PAGE)
    if tp is not None:
        out += declaration_problems(text, tp)
    return out


def golden(text: str, highlights: str | None, root: Path, required: dict) -> dict:
    now, probs = skeleton(text, highlights, root, required)
    if probs:
        raise SystemExit("cannot regenerate the skeleton while phrases or numbers fail:\n" + "\n".join(probs))
    return {"about": "Golden numeric skeleton of manuscript_src.md and highlights.md: for each section, every "
                     "number token in reading order with the catalogue label that accounts for it and its "
                     "source. Written by verification/check_manuscript_numbers.py --regenerate after review.",
            "sections": now}


def main(root: Path = ROOT, argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ms_dir, rest = manuscript_dir(root, argv)
    unknown = [a for a in rest if a != "--regenerate"]
    if unknown:
        print(f"FAIL: unknown arguments {unknown}")
        return 1
    name = rel(ms_dir, root)
    if not ms_dir.is_dir():
        print(f"SKIPPED: {name}/ not present (kept private, not in this repository)")
        return 0
    ms, ph = ms_dir / MS_NAME, ms_dir / PHRASES
    if not ms.exists() and not ph.exists():
        print(f"SKIPPED: {name}/{MS_NAME} not present (kept private, not in this repository)")
        return 0
    if not ms.exists() or not ph.exists():
        have, lack = (MS_NAME, PHRASES) if ms.exists() else (PHRASES, MS_NAME)
        print(f"FAIL: {name}/{have} is present but {name}/{lack} is missing")
        return 1
    try:
        required = section_phrases(ms_dir)
    except ValueError as e:
        print(f"FAIL: {name}/{PHRASES} cannot be read: {e}")
        return 1
    text = ms.read_text(encoding="utf-8")
    if "--regenerate" in rest:
        g = golden(text, read_opt(ms_dir, HIGHLIGHTS), root, required)
        (ms_dir / SKELETON).write_text(json.dumps(g, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                                       newline="\n")
        print(f"wrote {name}/{SKELETON}: {sum(len(v) for v in g['sections'].values())} number tokens")
        return 0
    found = problems(root, ms_dir, text, required=required)
    for ln in found:
        print(ln)
    gold = load_gold(ms_dir) or {}
    n_tok = sum(len(v) for v in gold.values())
    n_traced = sum(1 for v in gold.values() for x in v if not x["label"].startswith("fixed:"))
    print(f"{n_tok} number tokens ({n_traced} traced to a source file, {n_tok - n_traced} fixed labels), "
          f"{sum(len(v) for v in required.values())} section phrases, {len(catalogue_cached(root))} catalogue "
          f"values, {len(ref_list(text))} references; tables and figure data regenerated from outputs/; "
          f"{len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
