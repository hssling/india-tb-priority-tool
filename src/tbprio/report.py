"""Self-contained HTML reports of the tool (analysis plan §10.2).

``state_report`` and ``district_report`` return one HTML document each: inline CSS and
inline SVG only (no script, no external font, image or stylesheet), so the file can be
opened offline, e-mailed and printed on A4. The text carries no date or time, so reruns on
the same inputs give byte-identical files.

Accessibility: every coloured mark also carries a text label (tier code and probability in
the heat-map cells; marker shape and name for flagged districts in the funnels); the
heat-map colour is a sequential single-hue (blue) scale of P(top-k); each SVG has a title
and a description.
"""
from __future__ import annotations

import html
import math

TIER_CODE = {"act now": "A", "probable priority": "P", "uncertain": "U",
             "lower priority": "L", "watch: rising": "W"}
TIER_ORDER = ("act now", "probable priority", "uncertain", "watch: rising", "lower priority")

# sequential single-hue scale (light to dark blue) for P(top-k)
_LIGHT = (0xEE, 0xF3, 0xFA)
_DARK = (0x0B, 0x3D, 0x7A)

CSS = """
:root { --ink: #1a1f29; --muted: #4f5866; --rule: #c9d1dc; --paper: #ffffff;
  --band: #f3f6fa; --accent: #0b3d7a; --warn: #7a2e0b; color-scheme: light; }
* { box-sizing: border-box; }
html { background: var(--paper); }
body { margin: 0; background: var(--paper); color: var(--ink);
  font: 14px/1.5 "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
main { max-width: 190mm; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 22px; line-height: 1.25; margin: 0 0 4px; }
h2 { font-size: 17px; margin: 32px 0 8px; padding-top: 8px; border-top: 2px solid var(--accent); }
h3 { font-size: 15px; margin: 20px 0 6px; }
p, li { max-width: 72ch; }
.sub { color: var(--muted); margin: 0 0 12px; }
.banner { background: var(--band); border-left: 4px solid var(--warn); padding: 8px 12px;
  margin: 12px 0; }
.note { color: var(--muted); font-size: 12.5px; }
nav ol { margin: 4px 0 0; padding-left: 20px; }
dl.legend { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 8px 0; }
dl.legend dt { font-weight: 600; }
dl.legend dd { margin: 0; }
figure { margin: 12px 0 20px; }
figcaption { font-size: 12.5px; color: var(--muted); margin-top: 4px; max-width: 72ch; }
svg { display: block; width: 100%; height: auto; }
svg text { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; fill: var(--ink); }
.tablewrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; margin: 6px 0 16px; }
th, td { text-align: left; padding: 3px 6px; border-bottom: 1px solid var(--rule);
  vertical-align: top; }
th { background: var(--band); font-weight: 600; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
tbody tr.first td { border-top: 1px solid var(--muted); }
.kv { display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; font-size: 13px; }
.kv dt { color: var(--muted); }
.kv dd { margin: 0; font-variant-numeric: tabular-nums; }
@media print {
  @page { size: A4; margin: 12mm; }
  main { max-width: none; padding: 0; }
  h2 { break-after: avoid; }
  figure, tr { break-inside: avoid; }
}
"""


# ---- helpers ------------------------------------------------------------------------

def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def fnum(v, d: int = 0) -> str:
    if v is None or v != v:
        return "–"
    if math.isinf(v):
        return "∞"
    return f"{v:,.{d}f}".replace("-", MINUS)


MINUS = "−"


def signed(v: float, d: int) -> str:
    """'+1.5', '0.0', '−1.5': a true minus sign, legible in print."""
    s = f"{v:+.{d}f}"
    if float(s) == 0:
        return f"{0:.{d}f}"
    return s.replace("-", MINUS)


def pct(v, d: int = 1) -> str:
    if v is None or v != v:
        return "–"
    return signed(100 * v, d) + "%"


def colour(p: float) -> str:
    p = min(1.0, max(0.0, p))
    c = [round(a + (b - a) * p) for a, b in zip(_LIGHT, _DARK)]
    return "#" + "".join(f"{x:02x}" for x in c)


def text_colour(p: float) -> str:
    return "#ffffff" if p >= 0.5 else "#1a1f29"


def page(title: str, body: str) -> str:
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{esc(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<main>\n"
            f"{body}\n</main>\n</body>\n</html>\n")


def _nice_log_ticks(lo: float, hi: float) -> list[float]:
    out = []
    k = math.floor(math.log10(lo))
    while 10 ** k <= hi * 1.0001:
        for m in (1, 2, 5):
            v = m * 10 ** k
            if lo <= v <= hi:
                out.append(float(v))
        k += 1
    return out


def _nice_ticks(lo: float, hi: float, n: int = 6) -> list[float]:
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.ceil(lo / step) * step
    out = []
    v = start
    while v <= hi + 1e-12:
        out.append(round(v, 10))
        v += step
    return out


def _fmt_tick(v: float) -> str:
    if abs(v) >= 1000:
        s = f"{v:,.0f}"
    elif v == int(v):
        s = f"{int(v)}"
    else:
        s = f"{v:g}"
    return s.replace("-", MINUS)


def _legend_scale(x0: float, y0: float, width: float, label: str) -> str:
    """A labelled colour bar for P(top-k) with ticks at the tier thresholds."""
    parts = []
    n = 50
    for i in range(n):
        p = (i + 0.5) / n
        parts.append(f'<rect x="{x0 + i * width / n:.2f}" y="{y0:.1f}" '
                     f'width="{width / n + 0.3:.2f}" height="10" fill="{colour(p)}"/>')
    for t in (0, 0.2, 0.5, 0.8, 1.0):
        x = x0 + t * width
        parts.append(f'<line x1="{x:.1f}" y1="{y0 + 10:.1f}" x2="{x:.1f}" y2="{y0 + 14:.1f}" '
                     f'stroke="#1a1f29"/>')
        parts.append(f'<text x="{x:.1f}" y="{y0 + 25:.1f}" font-size="10" '
                     f'text-anchor="middle">{t:g}</text>')
    parts.append(f'<text x="{x0:.1f}" y="{y0 - 4:.1f}" font-size="11">{esc(label)}</text>')
    return "".join(parts)


# ---- heat-map -----------------------------------------------------------------------

def heatmap(units: list[str], steps: list[tuple[str, str]], cells: dict, k: int,
            title: str, label_width: int = 200) -> str:
    """Unit x step heat-map of P(top-k). ``cells[(unit, step)]`` = {"p", "tier",
    "rising", "small_far_behind"}; a missing cell is drawn as NA."""
    cw, ch, top = 92, 20, 64
    width = label_width + cw * len(steps) + 8
    height = top + ch * len(units) + 56
    hid = f"hm{len(units)}x{len(steps)}"
    out = [f'<svg viewBox="0 0 {width} {height}" style="max-width:{width}px" role="img" '
           f'aria-labelledby="{hid}-t {hid}-d" xmlns="http://www.w3.org/2000/svg">',
           f'<title id="{hid}-t">{esc(title)}</title>',
           f'<desc id="{hid}-d">Each cell shows the tier code and P(top-{k}) of one unit at one '
           f'step; darker blue means a higher P(top-{k}).</desc>']
    for j, (code, name) in enumerate(steps):
        x = label_width + j * cw + cw / 2
        out.append(f'<text x="{x:.1f}" y="18" font-size="12" font-weight="600" '
                   f'text-anchor="middle">{esc(code)}</text>')
        words = name.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 16 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        for li, t in enumerate(lines[:3]):
            out.append(f'<text x="{x:.1f}" y="{31 + 11 * li}" font-size="9.5" '
                       f'text-anchor="middle">{esc(t)}</text>')
    for i, u in enumerate(units):
        y = top + i * ch
        if i % 2 == 0:
            out.append(f'<rect x="0" y="{y}" width="{label_width - 4}" height="{ch}" '
                       f'fill="#f3f6fa"/>')
        out.append(f'<text x="4" y="{y + 14}" font-size="11">{esc(u)}</text>')
        for j, (code, _) in enumerate(steps):
            x = label_width + j * cw
            c = cells.get((u, code))
            if c is None:
                out.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cw - 2}" height="{ch - 2}" '
                           f'fill="#ffffff" stroke="#c9d1dc"/>'
                           f'<text x="{x + cw / 2:.1f}" y="{y + 14}" font-size="10.5" '
                           f'text-anchor="middle" fill="#4f5866">NA</text>')
                continue
            p = c["p"]
            mark = ("↑" if c.get("rising") and c["tier"] != "watch: rising" else "") + \
                   ("•" if c.get("small_far_behind") else "")
            lab = f'{TIER_CODE[c["tier"]]} {p:.2f}{mark}'
            out.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cw - 2}" height="{ch - 2}" '
                       f'fill="{colour(p)}"/>'
                       f'<text x="{x + cw / 2:.1f}" y="{y + 14}" font-size="10.5" '
                       f'text-anchor="middle" style="fill:{text_colour(p)}">{esc(lab)}</text>')
    ly = top + ch * len(units) + 22
    out.append(_legend_scale(label_width, ly, min(300, cw * len(steps)), f"P(top-{k})"))
    out.append("</svg>")
    return "\n".join(out)


def tier_legend(k: int, with_rising: bool) -> str:
    rows = [("A", "act now", f"P(top-{k}) ≥ 0.80"),
            ("P", "probable priority", "0.50 ≤ P < 0.80"),
            ("U", "uncertain", "0.20 ≤ P < 0.50"),
            ("L", "lower priority", "P < 0.20")]
    if with_rising:
        rows.insert(3, ("W", "watch: rising", "uncertain or lower priority, and the loss "
                        "rate is rising (the 95% interval of its trend lies wholly on the "
                        "worsening side)"))
    items = "".join(f"<dt>{c} = {esc(n)}</dt><dd>{esc(d)}</dd>" for c, n, d in rows)
    return f'<dl class="legend">{items}</dl>'


# ---- funnels ------------------------------------------------------------------------

def _marker(kind: str, x: float, y: float) -> str:
    if kind == "up":
        return (f'<path d="M{x:.1f},{y - 5:.1f} L{x + 4.5:.1f},{y + 3.5:.1f} '
                f'L{x - 4.5:.1f},{y + 3.5:.1f} Z" fill="#0b3d7a"/>')
    if kind == "down":
        return (f'<path d="M{x:.1f},{y + 5:.1f} L{x + 4.5:.1f},{y - 3.5:.1f} '
                f'L{x - 4.5:.1f},{y - 3.5:.1f} Z" fill="#0b3d7a"/>')
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#9aa6b6" '
            f'fill-opacity="0.85"/>')


def _labels(cands: list[tuple[float, float, str]], left: float, right: float) -> list[str]:
    """Labels for flagged points, nudged apart vertically."""
    out = []
    placed: list[tuple[float, float]] = []
    for x, y, name in sorted(cands, key=lambda t: t[1]):
        ly = y
        for _ in range(30):
            if all(abs(ly - py) > 11 or abs(x - px) > 120 for px, py in placed):
                break
            ly += 11
        placed.append((x, ly))
        anchor = "end" if x > (left + right) / 2 else "start"
        dx = -7 if anchor == "end" else 7
        out.append(f'<text x="{x + dx:.1f}" y="{ly + 3.5:.1f}" font-size="10" '
                   f'text-anchor="{anchor}">{esc(name)}</text>')
    return out


NATIONAL_Z_DESC = ("Each point is a district: its denominator (horizontal, log scale) and "
                   "its z-score against its own State (vertical). Horizontal lines: the 95% "
                   "(dashed) and 99.8% (solid) limits after the overdispersion adjustment. "
                   "Triangles are districts beyond the 99.8% limits (up: above, down: below "
                   "the State).")


def z_funnel_svg(fid: str, title: str, points: list[dict], limit95: float,
                 limit998: float, xlabel: str, desc: str = NATIONAL_Z_DESC,
                 ylabel: str = "z against the State proportion",
                 label_flagged: bool = False) -> str:
    """Standardised funnel for State-relative comparisons with different State centres:
    the z-score of each district (horizontal lines at the adjusted 95% and 99.8% limits)
    against its denominator (log scale)."""
    W, H = 720, 360
    ml, mr, mt, mb = 62, 16, 16, 52
    ns = [p["n"] for p in points]
    xlo = 10 ** math.floor(math.log10(min(ns)))
    xhi = 10 ** math.ceil(math.log10(max(ns)))
    zs = [p["z"] for p in points]
    m = max(max(abs(v) for v in zs), limit998) * 1.08
    ylo, yhi = -m, m

    def X(n):
        return ml + (math.log10(n) - math.log10(xlo)) / (math.log10(xhi) - math.log10(xlo)) \
            * (W - ml - mr)

    def Y(v):
        return mt + (yhi - v) / (yhi - ylo) * (H - mt - mb)

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="{fid}-t {fid}-d" '
           f'xmlns="http://www.w3.org/2000/svg">',
           f'<title id="{fid}-t">{esc(title)}</title>',
           f'<desc id="{fid}-d">{esc(desc)}</desc>',
           f'<rect x="{ml}" y="{mt}" width="{W - ml - mr}" height="{H - mt - mb}" '
           f'fill="#ffffff" stroke="#c9d1dc"/>']
    for t in _nice_ticks(ylo, yhi, 8):
        y = Y(t)
        out.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{W - mr}" y2="{y:.1f}" stroke="#eef1f5"/>'
                   f'<text x="{ml - 6}" y="{y + 3.5:.1f}" font-size="10" '
                   f'text-anchor="end">{_fmt_tick(t)}</text>')
    for t in _nice_log_ticks(xlo, xhi):
        x = X(t)
        out.append(f'<line x1="{x:.1f}" y1="{H - mb}" x2="{x:.1f}" y2="{H - mb + 4}" '
                   f'stroke="#1a1f29"/><text x="{x:.1f}" y="{H - mb + 16}" font-size="10" '
                   f'text-anchor="middle">{_fmt_tick(t)}</text>')
    for lim, dash in ((limit95, ' stroke-dasharray="5 4"'), (limit998, "")):
        for s in (1, -1):
            out.append(f'<line x1="{ml}" y1="{Y(s * lim):.1f}" x2="{W - mr}" '
                       f'y2="{Y(s * lim):.1f}" stroke="#4f5866"{dash}/>')
    out.append(f'<line x1="{ml}" y1="{Y(0):.1f}" x2="{W - mr}" y2="{Y(0):.1f}" '
               f'stroke="#0b3d7a" stroke-width="1.4"/>')
    out.append(f'<text x="{(ml + W - mr) / 2:.1f}" y="{H - 12}" font-size="11.5" '
               f'text-anchor="middle">{esc(xlabel)} (log scale)</text>')
    out.append(f'<text transform="translate(14,{(mt + H - mb) / 2:.1f}) rotate(-90)" '
               f'font-size="11.5" text-anchor="middle">{esc(ylabel)}</text>')
    flagged = []
    for p in sorted(points, key=lambda p: (p["kind"] != "none", p["name"])):
        out.append(_marker(p["kind"], X(p["n"]), Y(p["z"])))
        if p["kind"] != "none":
            flagged.append((X(p["n"]), Y(p["z"]), p["name"]))
    if label_flagged:
        out += _labels(flagged, ml, W - mr)
    out.append("</svg>")
    return "\n".join(out)


# ---- State report -------------------------------------------------------------------

STATE_CAVEATS = [
    "A CTD notification target is a programme goal, not an estimate of disease. S1 is a "
    "shortfall against target: it does not count people with TB who were not found.",
    "Harm averted counts patients lost at one step of the care pathway. Steps count "
    "different kinds of loss and are never added together; no combined score is formed.",
    "With denominators of about 100,000 patients, P(top-5) mostly reflects binomial noise, "
    "so it is close to 0 or 1. The tiers therefore express little uncertainty beyond "
    "sampling (plan §10.4).",
    "Harm averted is an absolute count, so large States have large values at every step. "
    "The temporal-stability estimate (H1, outputs/headline.csv) is largely driven by unit "
    "size for the same reason (plan §10.4).",
    "The association of the S1 shortfall with the National TB Prevalence Survey (H2) may "
    "be circular if CTD targets were set from burden estimates that include the survey "
    "(plan §10.4).",
    "Small UTs are merged into the unit they adjoin (Dadra and Nagar Haveli and Daman and "
    "Diu into Gujarat, Lakshadweep into Kerala, Ladakh into Jammu and Kashmir) and are not "
    "prioritised separately.",
    "The results describe programme data, not the performance or effort of any State's "
    "staff. They are associations in published data: no causal effect of any intervention "
    "and no cost are estimated.",
    "S3 and S4 describe the 2022 treatment cohort and S5 the 2021 MDR/RR-TB cohort (ITR "
    "2024); S2 counts bacteriologically confirmed patients without a valid rapid "
    "rifampicin result.",
]


def state_report(prio: list[dict], step_names: dict[str, str], source: str,
                 year: int = 2023, k: int = 5) -> str:
    units = sorted({r["unit"] for r in prio})
    steps = sorted({r["step"] for r in prio})
    cells = {(r["unit"], r["step"]): {"p": r["p_top5"], "tier": r["tier"],
                                       "rising": r["rising"],
                                       "small_far_behind": r["small_far_behind"]}
             for r in prio}
    by = {(r["unit"], r["step"]): r for r in prio}
    body = [f"<header><h1>Where closing a gap in TB care would avert the most harm: "
            f"States and UTs, data year {year}</h1>",
            f'<p class="sub">TB priority tool, State report. Input: {esc(source)}. Method: '
            f"the registered analysis plan (docs/analysis_plan.md, §6). Tiers, not "
            f"ranks.</p></header>",
            "<nav><strong>Contents</strong><ol><li><a href=\"#legend\">How to read this "
            "report</a></li><li><a href=\"#matrix\">Priority matrix</a></li><li><a "
            "href=\"#steps\">Largest harm averted at each step</a></li><li><a "
            "href=\"#units\">Summary for each State/UT</a></li><li><a "
            "href=\"#caveats\">Caveats</a></li></ol></nav>"]
    body.append('<section id="legend"><h2>How to read this report</h2>')
    body.append(
        "<p>For each step of the TB care pathway, the tool asks how many patients would not "
        "have been lost if a State's loss rate were as good as the benchmark: the rate of "
        "the better quarter of States. This number is the <strong>harm averted</strong>. It "
        "is counted in patients and is shown with a 95% interval. For S1 it is the "
        "shortfall of notifications against the benchmark share of the target.</p>")
    body.append(
        f"<p>The tool then simulates 10,000 plausible versions of the data. "
        f"<strong>P(top-{k})</strong> is the share of these in which the State is among the "
        f"{k} with the largest harm averted at that step. The <strong>tier</strong> is set "
        f"from P(top-{k}):</p>")
    body.append(tier_legend(k, True))
    body.append(
        '<dl class="legend"><dt>↑</dt><dd>the loss rate is rising (shown when it does not '
        "already set the tier to W)</dd><dt>•</dt><dd>small but far behind: the State's "
        "rate gap is among the worst quarter, but its harm averted is below the median. "
        "This never changes the tier.</dd><dt>per 100,000</dt><dd>harm averted per 100,000 "
        "population (ITR 2024 population), shown alongside and never used for tiers.</dd>"
        "</dl>")
    body.append("<p>Steps:</p><ul>" + "".join(
        f"<li><strong>{esc(s)}</strong>: {esc(step_names.get(s, s))}</li>" for s in steps)
        + "</ul></section>")
    body.append('<section id="matrix"><h2>Priority matrix</h2><figure>')
    body.append(heatmap(units, [(s, step_names.get(s, s)) for s in steps], cells, k,
                        f"Priority matrix, data year {year}: tier and P(top-{k}) of each "
                        f"State/UT at each step"))
    body.append(f"<figcaption>Each cell: tier code and P(top-{k}); the colour shows P(top-"
                f"{k}) on a single-hue scale (darker = higher). The tier and the number "
                f"carry the same information as the colour.</figcaption></figure></section>")
    body.append('<section id="steps"><h2>Largest harm averted at each step</h2>')
    for s in steps:
        rs = sorted((r for r in prio if r["step"] == s),
                    key=lambda r: (-r["harm_averted_mean"], r["unit"]))
        shown = [r for r in rs if r["tier"] in ("act now", "probable priority", "uncertain",
                                                "watch: rising")]
        body.append(f"<h3>{esc(s)}: {esc(step_names.get(s, s))}</h3>")
        if not shown:
            body.append("<p>No State/UT is in a tier above lower priority.</p>")
            continue
        body.append('<div class="tablewrap"><table><thead><tr><th>State/UT</th><th>Tier</th>'
                    '<th class="n">Harm averted (95% interval)</th><th class="n">per '
                    f'100,000</th><th class="n">P(top-{k})</th></tr></thead><tbody>')
        for r in shown:
            body.append(f"<tr><td>{esc(r['unit'])}</td><td>{esc(r['tier'])}</td>"
                        f'<td class="n">{fnum(r["harm_averted_mean"])} ({fnum(r["lo"])} to '
                        f'{fnum(r["hi"])})</td><td class="n">{fnum(r["per_100k"], 1)}</td>'
                        f'<td class="n">{r["p_top5"]:.2f}</td></tr>')
        body.append("</tbody></table></div>")
    body.append("</section>")
    body.append('<section id="units"><h2>Summary for each State/UT</h2>'
                '<div class="tablewrap"><table><thead><tr><th>State/UT</th><th>Step</th>'
                '<th class="n">Harm averted (95% interval)</th><th class="n">per 100,000</th>'
                f'<th class="n">P(top-{k})</th><th>Tier</th><th>Flags</th></tr></thead>'
                "<tbody>")
    for u in units:
        first = True
        for s in steps:
            r = by.get((u, s))
            cls = ' class="first"' if first else ""
            name = esc(u) if first else ""
            first = False
            if r is None:
                body.append(f"<tr{cls}><td>{name}</td><td>{esc(s)}</td><td colspan=\"5\">"
                            f"NA (see outputs/na_cells.csv)</td></tr>")
                continue
            fl = [x for x, on in (("rising", r["rising"]),
                                  ("small but far behind", r["small_far_behind"])) if on]
            body.append(f"<tr{cls}><td>{name}</td><td>{esc(s)}</td>"
                        f'<td class="n">{fnum(r["harm_averted_mean"])} ({fnum(r["lo"])} to '
                        f'{fnum(r["hi"])})</td><td class="n">{fnum(r["per_100k"], 1)}</td>'
                        f'<td class="n">{r["p_top5"]:.2f}</td><td>{esc(r["tier"])}</td>'
                        f"<td>{esc(', '.join(fl))}</td></tr>")
    body.append("</tbody></table></div></section>")
    body.append('<section id="caveats"><h2>Caveats</h2><ul>' +
                "".join(f"<li>{esc(c)}</li>" for c in STATE_CAVEATS) + "</ul></section>")
    return page(f"State TB priorities {year}", "\n".join(body))


# ---- district report ----------------------------------------------------------------

def _change_kind(flag: str) -> str:
    return {"rose beyond adjusted limits": "up",
            "fell beyond adjusted limits": "down"}.get(flag or "", "none")


def _state_kind(flag: str) -> str:
    return {"above State limits": "up", "below State limits": "down"}.get(flag or "", "none")


DISTRICT_CAVEATS_CHANGE = [
    "A fall in notifications can mean less TB or less case-finding, and a rise can mean "
    "more TB or more case-finding. Notifications alone cannot tell these apart.",
    "The notification funnel has no tiers: a flag marks a change beyond what the State's "
    "own districts make usual, not a ranking or a judgement of any district.",
    "The overdispersion adjustment (phi) is estimated within each State; when phi is well "
    "above 1 the limits are wide and few districts are flagged. The additive (tau²) "
    "adjustment is shown alongside.",
]
DISTRICT_CAVEATS_AU802 = [
    "Lok Sabha Question 802 (answered 7 February 2025) prints Madhya Pradesh's district "
    "\"Vidisha\" twice with identical values; it is kept once and flagged. The three "
    "Madhya Pradesh districts created in 2023 are not printed and are not added. Districts "
    "renamed or split since 2018 are not linked to the 2018 table.",
]
DISTRICT_CAVEATS_2018 = [
    "The national district results are 2018 data (historical), from the India TB Report "
    "2019. Many districts have since been renamed or split; the results are not linked to "
    "current districts and are a demonstration of method, not current priorities.",
    "D1 compares patients notified by the diagnosing facility in the district with patients "
    "initiated on treatment in the district (ITR 2019 Annexure 1.13 footnote). Patients "
    "diagnosed in one district and treated in another (for example at referral centres in "
    "large cities) count as not initiated in the first.",
    "D2's cohort size is rebuilt from the printed success count and a rounded percentage; "
    "each value is flagged rounded_from_percent and carries the range implied by the "
    "rounding (outputs/district_national_2018.csv).",
    "With denominators of thousands of patients, P(top-20) mostly reflects binomial noise "
    "and is close to 0 or 1; the tiers express little uncertainty beyond sampling.",
    "Harm averted is an absolute count, so large districts have large values. It describes "
    "programme data, not the performance or effort of any district's staff, and is not a "
    "causal estimate.",
]


def district_report(change_rows: list[dict], change_info: dict, years: list[int],
                    source: str, national_rows: list[dict] | None = None,
                    national_info: dict | None = None, national_source: str = "",
                    step_names_2018: dict[str, str] | None = None,
                    au802: bool = False, optional_cols: list[str] | None = None) -> str:
    states = list(change_info)
    b = change_rows[0]["base_year"] if change_rows else years[0]
    f = change_rows[0]["final_year"] if change_rows else years[-1]
    body = [f"<header><h1>TB notifications by district: {esc(', '.join(states))}, "
            f"{b} to {f}</h1>",
            f'<p class="sub">TB priority tool, district report (a demonstration of method). '
            f"Input: {esc(source)}. Method: the registered analysis plan (docs/"
            f"analysis_plan.md, §9).</p></header>"]
    toc = ['<li><a href="#legend">How to read this report</a></li>']
    toc += [f'<li><a href="#change-{i}">{esc(s)}: change in notifications</a></li>'
            for i, s in enumerate(states)]
    if national_rows is not None:
        toc.append('<li><a href="#national">National district module, 2018 data '
                   '(historical)</a></li>')
    toc.append('<li><a href="#caveats">Caveats</a></li>')
    body.append("<nav><strong>Contents</strong><ol>" + "".join(toc) + "</ol></nav>")
    body.append('<section id="legend"><h2>How to read this report</h2>')
    body.append(
        f"<p><strong>Change in notifications.</strong> For each district, the change in the "
        f"number of TB patients notified from {b} to {f} is compared with the change for "
        f"the State as a whole. A district far from the State's change, given its size, "
        f"lies outside the funnel. Because districts differ for many ordinary reasons, the "
        f"limits are widened by an overdispersion factor estimated from the State's own "
        f"districts.</p>")
    body.append(
        '<dl class="legend"><dt>▲ rose beyond adjusted limits</dt><dd>the district rose '
        "more than the State, beyond the 99.8% limits after the adjustment</dd>"
        "<dt>▼ fell beyond adjusted limits</dt><dd>the district fell more than the State, "
        "beyond the 99.8% limits after the adjustment</dd><dt>● within adjusted limits</dt>"
        "<dd>the district's change is in line with the State's</dd></dl>")
    if national_rows is not None:
        body.append(
            "<p><strong>National district module (2018 data).</strong> For two steps of the "
            "care pathway, the tool asks how many patients would not have been lost if a "
            "district's loss rate were as good as the benchmark (the better quarter of all "
            "districts): the <strong>harm averted</strong>. P(top-20) is the share of 10,000 "
            "simulations in which the district is among the 20 with the largest harm "
            "averted at that step; the tier is set from it:</p>")
        body.append(tier_legend(20, False))
        body.append(
            '<dl class="legend"><dt>▲ above State limits</dt><dd>the district loses a larger '
            "share of patients than its State, beyond the 99.8% limits after the "
            "adjustment</dd><dt>▼ below State limits</dt><dd>a smaller share than its "
            "State</dd><dt>•</dt><dd>small but far behind (never changes the tier)</dd>"
            "</dl>")
    if optional_cols:
        body.append(f'<p class="note">Optional input columns {esc(", ".join(optional_cols))} '
                    f"were checked and carried, but not analysed: with notifications, the "
                    f"tool gives the change and funnel of plan §9.2 (§9.3).</p>")
    body.append("</section>")

    for i, s in enumerate(states):
        info = change_info[s]
        rs = [r for r in change_rows if r["state"] == s]
        body.append(f'<section id="change-{i}"><h2>{esc(s)}: change in notifications, '
                    f"{b} to {f}</h2>")
        body.append(
            '<dl class="kv">'
            f"<dt>Districts</dt><dd>{info['districts']}</dd>"
            f"<dt>State total</dt><dd>{fnum(info['N_base'])} in {b}, {fnum(info['N_final'])}"
            f" in {f} (pooled change {pct(info['change'])})</dd>"
            f"<dt>Overdispersion phi</dt><dd>{fnum(info['phi'], 2)} (99.8% limits at z = "
            f"±{fnum(info['limit_998'], 2)})</dd>"
            f"<dt>Additive tau²</dt><dd>{info['tau2']:.5f} (relative-change scale)</dd>"
            f"<dt>Flagged</dt><dd>"
            f"{sum(r['flag'] == 'fell beyond adjusted limits' for r in rs)} fell, "
            f"{sum(r['flag'] == 'rose beyond adjusted limits' for r in rs)} rose beyond the "
            f"adjusted limits</dd></dl>")
        if info["na"]:
            body.append(f"<p>Not tested ({b} count 0): {esc(', '.join(info['na']))}.</p>")
        if info["phi"] == info["phi"]:
            fz = math.sqrt(max(1.0, info["phi"]))
            pts = [{"name": r["district"], "n": r[f"n_{b}"], "z": r["z"] / fz,
                    "kind": _change_kind(r["flag"])} for r in rs if r["z"] is not None]
        else:
            pts = []
        if len(pts) >= 2:
            body.append("<figure>")
            body.append(z_funnel_svg(
                f"fc{i}", f"{s}: change in TB notifications by district, {b} to {f}", pts,
                1.96, 3.09, f"Notified in {b}",
                desc=(f"Each point is a district: its notifications in {b} (horizontal, log "
                      f"scale) and the z-score of its change to {f} against the State's "
                      f"pooled change, divided by the square root of phi (vertical). "
                      f"Horizontal lines: the adjusted 95% (dashed) and 99.8% (solid) limits. "
                      f"Triangles are districts beyond the 99.8% limits (pointing up: rose; "
                      f"down: fell), named."),
                ylabel=f"z of the change ÷ √phi", label_flagged=True))
            body.append(f"<figcaption>Standardised funnel around the State's pooled change "
                        f"({pct(info['change'])}): each district's z, computed with its own "
                        f"standard error √(n{b} + n{f}), divided by √phi (phi = "
                        f"{fnum(info['phi'], 2)}), so the adjusted limits are at ±1.96 "
                        f"(dashed) and ±3.09 (solid). A point lies beyond the solid lines "
                        f"exactly when the district is flagged.</figcaption></figure>")
        body.append('<div class="tablewrap"><table><thead><tr><th>District</th>' +
                    "".join(f'<th class="n">{y}</th>' for y in years) +
                    '<th class="n">Change</th><th class="n">Change %</th><th class="n">z</th>'
                    "<th>Funnel (multiplicative)</th><th>Additive</th></tr></thead><tbody>")
        order = sorted(rs, key=lambda r: ({"fell beyond adjusted limits": 0,
                                           "rose beyond adjusted limits": 1}.get(r["flag"], 2),
                                          r["district"]))
        for r in order:
            body.append(
                f"<tr><td>{esc(r['district'])}"
                f"{' (printed twice)' if 'duplicate_entry' in (r['entry_flag'] or '') else ''}"
                "</td>" + "".join(f'<td class="n">{fnum(r[f"n_{y}"])}</td>' for y in years) +
                f'<td class="n">{fnum(r["change"])}</td><td class="n">{pct(r["rel_change"])}'
                f'</td><td class="n">{fnum(r["z"], 1)}</td><td>{esc(r["flag"] or r["na"])}'
                f'</td><td>{esc(r["additive_position_998"])}</td></tr>')
        body.append("</tbody></table></div></section>")

    if national_rows is not None:
        names = step_names_2018 or {}
        body.append('<section id="national"><h2>National district module, 2018 data '
                    "(historical)</h2>")
        body.append(f'<p class="banner"><strong>2018 data (historical).</strong> India TB '
                    f"Report 2019, Annexure 1.13 ({esc(national_source)}). A demonstration "
                    f"of method, not current priorities.</p>")
        steps = list(names)
        body.append('<dl class="kv">' + "".join(
            f"<dt>{esc(s)}: {esc(names[s])}</dt><dd>{national_info[s]['units']} districts; "
            f"benchmark loss rate {100 * national_info[s]['rate_bench']:.2f}%; phi "
            f"{fnum(national_info[s]['phi'], 1)}; tau² {national_info[s]['tau2']:.5f}; "
            f"no funnel: {esc(', '.join(sorted(national_info[s]['no_funnel'])) or 'none')}"
            f"</dd>" for s in steps) + "</dl>")
        by = {(r["state"], r["district"], r["step"]): r for r in national_rows}
        keys = sorted({(r["state"], r["district"]) for r in national_rows
                       if r["p_top20"] is not None and r["p_top20"] >= 0.20})
        cells = {}
        for st, d in keys:
            for s in steps:
                r = by.get((st, d, s))
                if r is not None and r["p_top20"] is not None:
                    cells[(f"{st} | {d}", s)] = {"p": r["p_top20"], "tier": r["tier"],
                                                 "rising": False,
                                                 "small_far_behind": r["small_far_behind"]}
        body.append("<h3>Priority matrix</h3><figure>")
        body.append(heatmap([f"{st} | {d}" for st, d in keys],
                            [(s, names[s].split(" (")[0]) for s in steps], cells, 20,
                            "Priority matrix, 2018 data (historical): districts with P(top-20)"
                            " of at least 0.20 at either step", label_width=250))
        body.append("<figcaption>Districts with P(top-20) ≥ 0.20 at D1 or D2. Each cell: tier "
                    "code and P(top-20). All districts are in outputs/district_national_"
                    "2018.csv.</figcaption></figure>")
        for j, s in enumerate(steps):
            rs = [r for r in national_rows if r["step"] == s and r["z"] is not None]
            info = national_info[s]
            pts = [{"name": f"{r['district']} ({r['state']})", "n": r["denominator"],
                    "z": r["z"] / math.sqrt(max(1.0, info["phi"])),
                    "kind": _state_kind(r["funnel_flag"])} for r in rs]
            body.append(f"<h3>{esc(s)}: {esc(names[s])}</h3><figure>")
            body.append(z_funnel_svg(f"fz{j}", f"{s}, 2018 data: each district against its "
                                     f"own State", pts, 1.96, 3.09,
                                     "Denominator (patients)"))
            body.append(f"<figcaption>Standardised funnel: z divided by √phi (phi = "
                        f"{fnum(info['phi'], 1)}), so the adjusted limits are at ±1.96 "
                        f"(dashed) and ±3.09 (solid). Each district is compared with its "
                        f"own State's pooled proportion.</figcaption></figure>")
            top = sorted((r for r in national_rows if r["step"] == s
                          and r["tier"] in ("act now", "probable priority", "uncertain")),
                         key=lambda r: (-r["harm_averted_mean"], r["state"], r["district"]))
            body.append('<div class="tablewrap"><table><thead><tr><th>District</th>'
                        '<th>State</th><th class="n">n</th><th class="n">Lost</th>'
                        '<th class="n">Harm averted (95% interval)</th><th class="n">'
                        "P(top-20)</th><th>Tier</th><th>Against its State</th></tr></thead>"
                        "<tbody>")
            for r in top:
                body.append(
                    f"<tr><td>{esc(r['district'])}</td><td>{esc(r['state'])}</td>"
                    f'<td class="n">{fnum(r["denominator"])}</td><td class="n">'
                    f'{fnum(r["numerator"])}</td><td class="n">{fnum(r["harm_averted_mean"])} '
                    f'({fnum(r["lo"])} to {fnum(r["hi"])})</td><td class="n">'
                    f'{r["p_top20"]:.2f}</td><td>{esc(r["tier"])}'
                    f'{" •" if r["small_far_behind"] else ""}</td>'
                    f"<td>{esc(r['funnel_flag'])}</td></tr>")
            body.append("</tbody></table></div>")
            fl = sorted((r for r in rs if r["funnel_flag"] in ("above State limits",
                                                                "below State limits")),
                        key=lambda r: (r["funnel_flag"], r["state"], r["district"]))
            if fl:
                body.append(f"<p><strong>Beyond the State limits at {esc(s)}</strong> "
                            f"({len(fl)} districts): " + "; ".join(
                                f"{esc(r['district'])} ({esc(r['state'])}, "
                                f"{'above' if r['funnel_flag'].startswith('above') else 'below'})"
                                for r in fl) + ".</p>")
        body.append("</section>")

    cav = list(DISTRICT_CAVEATS_CHANGE)
    if au802:
        cav += DISTRICT_CAVEATS_AU802
    if national_rows is not None:
        cav += DISTRICT_CAVEATS_2018
    body.append('<section id="caveats"><h2>Caveats</h2><ul>' +
                "".join(f"<li>{esc(c)}</li>" for c in cav) + "</ul></section>")
    return page(f"District TB report {b}-{f}", "\n".join(body))


def write(path, text: str) -> None:
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
