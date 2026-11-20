# Adapted from hssling/india-tb-acf-campaign (MIT), exhibits/make_figures.py; modified: the four
# figures of this paper (priority matrix, harm averted, trajectories, district modules), drawn
# from outputs/ with colour-blind-safe sequential shading and text labels.
"""Draw the manuscript's figures from outputs/ into <manuscript folder>/exhibits/.

Run as: python -I exhibits/make_figures.py [--manuscript-dir DIR]   (default: manuscript)

Writes figure1.pdf ... figure4.pdf (vector; the build renders each to a 1000 dpi TIFF), a PNG
preview of each (figureN.png, 200 dpi, for reading the layout only) and figureN_data.csv, the
values each figure plots, read from outputs/ by figure_data() (the number check regenerates
them and requires the CSVs to be identical). Needs matplotlib (3.10.7). The PDFs carry no
creation date, so a rerun gives the same bytes on the same platform.

Figure 1  the State priority matrix, data year 2023: units x steps, shaded by P(top-5)
          (sequential, colour-blind safe), with the tier letter and a triangle for a rising trend
Figure 2  harm averted with its 95% interval for the eight units with the most harm averted in each
          step (A), and the same units per 100,000 population (B)
Figure 3  State trajectories of the observed rate by data year (S1, S3, S4, S6), with the benchmark
          of each year and the units with a rising flag drawn and named
Figure 4  the national district module, data year 2018 (D1, D2: loss rate against district size,
          upper-tier districts marked) and the Madhya Pradesh and Maharashtra funnels of the change
          in notifications, 2022 to 2024
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exhibits.formats import STEP_NAMES, STEPS, TIER_LETTER, num, read_csv  # noqa: E402

DEFAULT_MS_DIR = "manuscript"
WIDTH = 7.48  # inches: Elsevier full-page width (190 mm)
TOP_N = 8     # units shown per step in Figure 2
RISE = "▲"
TIER_MARK = {"act now": ("o", True), "probable priority": ("s", True), "uncertain": ("^", False),
             "watch: rising": ("D", False), "lower priority": ("o", False)}
Z998, Z95 = 3.09, 1.96


def short_step(s: str) -> str:
    return f"{s} {STEP_NAMES[s]}"


# --------------------------------------------------------------------------------------
# The data of each figure (all from outputs/)
# --------------------------------------------------------------------------------------
def fig1_data(root: Path) -> list[dict]:
    rows = []
    for r in read_csv(root, "outputs/state_priority.csv"):
        rows.append({"unit": r["unit"], "step": r["step"], "p_top5": r["p_top5"], "tier": r["tier"],
                     "letter": TIER_LETTER[r["tier"]] if r["tier"] != "lower priority" else "",
                     "rising": r["rising"]})
    return sorted(rows, key=lambda r: (r["unit"], r["step"]))


def fig2_data(root: Path) -> list[dict]:
    pr = read_csv(root, "outputs/state_priority.csv")
    rows = []
    for s in STEPS:
        rs = sorted((r for r in pr if r["step"] == s), key=lambda r: (-float(r["harm_averted_mean"]), r["unit"]))
        for i, r in enumerate(rs[:TOP_N], 1):
            rows.append({"step": s, "order": str(i), "unit": r["unit"], "harm_averted_mean": r["harm_averted_mean"],
                         "lo": r["lo"], "hi": r["hi"], "per_100k": r["per_100k"], "tier": r["tier"],
                         "rising": r["rising"]})
    return rows


def fig3_data(root: Path) -> list[dict]:
    rising = {(r["unit"], r["step"]) for r in read_csv(root, "outputs/state_priority.csv") if r["rising"] == "True"}
    rows = []
    for r in read_csv(root, "outputs/state_harm_draws_summary.csv"):
        if (r["basis"], r["benchmark"], r["shrinkage"]) != ("main", "p75", "on") or r["step"] not in ("S1", "S3", "S4", "S6"):
            continue
        if r["rate_observed"] == "":
            continue
        rows.append({"step": r["step"], "unit": r["unit"], "year": r["year"], "rate_observed": r["rate_observed"],
                     "rate_bench": r["rate_bench"], "rising": str((r["unit"], r["step"]) in rising)})
    return sorted(rows, key=lambda r: (r["step"], r["unit"], r["year"]))


def fig4_data(root: Path) -> list[dict]:
    rows = []
    for r in read_csv(root, "outputs/district_national_2018.csv"):
        if r["na"] != "False":
            continue
        rows.append({"panel": r["step"], "state": r["state"], "district": r["district"], "x": r["denominator"],
                     "y": r["rate_observed"], "centre": r["rate_bench"], "phi": r["phi"], "tier": r["tier"],
                     "flag": r["funnel_flag"]})
    for r in read_csv(root, "outputs/district_mp_mh.csv"):
        if r["na"]:
            continue
        rows.append({"panel": r["state"], "state": r["state"], "district": r["district"], "x": r["n_2022"],
                     "y": r["rel_change"], "centre": r["state_change"], "phi": r["phi"], "tier": "",
                     "flag": r["flag"]})
    return rows


FIGURES = {1: fig1_data, 2: fig2_data, 3: fig3_data, 4: fig4_data}


def data_csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


# --------------------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------------------
def setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "axes.linewidth": 0.6,
        "xtick.major.width": 0.5, "ytick.major.width": 0.5, "pdf.fonttype": 42, "svg.hashsalt": "tbprio",
        "axes.spines.top": False, "axes.spines.right": False,
    })
    return plt


def draw1(rows: list[dict], plt):
    from matplotlib import colormaps
    units = sorted({r["unit"] for r in rows})
    cell = {(r["unit"], r["step"]): r for r in rows}
    cmap = colormaps["Blues"]
    fig, ax = plt.subplots(figsize=(WIDTH, 8.6))
    for i, u in enumerate(units):
        for j, s in enumerate(STEPS):
            r = cell.get((u, s))
            if r is None:
                ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor="white", edgecolor="#bbbbbb", hatch="////", lw=0.3))
                continue
            p = float(r["p_top5"])
            ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=cmap(0.04 + 0.9 * p), edgecolor="white", lw=0.8))
            label = r["letter"] + (RISE if r["rising"] == "True" else "")
            if label:
                ax.text(j + 0.5, i + 0.52, label, ha="center", va="center", fontsize=7.5, fontweight="bold",
                        color="white" if p >= 0.5 else "black")
    ax.set_xlim(0, len(STEPS))
    ax.set_ylim(len(units), 0)
    ax.set_xticks([j + 0.5 for j in range(len(STEPS))])
    ax.set_xticklabels([f"{s}\n" + STEP_NAMES[s].replace(" (", "\n(").replace("not tested for", "not tested for\n")
                        .replace("treatment not", "treatment\nnot").replace("shortfall against", "shortfall\nagainst")
                        .replace("status not", "status\nnot")
                        for s in STEPS], fontsize=6.5)
    ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(units))])
    ax.set_yticklabels(units)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    from matplotlib.colors import ListedColormap
    sm = plt.cm.ScalarMappable(cmap=ListedColormap([cmap(0.04 + 0.9 * k / 255) for k in range(256)]),
                               norm=plt.Normalize(0, 1))
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.025, pad=0.02, aspect=40)
    cb.set_label("P(top-5): probability of being among the five units with the most harm averted in the step")
    cb.outline.set_linewidth(0.4)
    fig.text(0.5, 0.012, f"A, act now (P ≥ 0.80); P, probable priority (0.50 to <0.80); U, uncertain (0.20 to <0.50); "
             f"W, watch: rising; blank, lower priority;\n{RISE}, rising trend (95% interval of the slope wholly on the "
             f"worsening side). Units alphabetical; data year 2023.", ha="center", va="bottom", fontsize=6.5)
    fig.subplots_adjust(left=0.27, right=0.97, top=0.91, bottom=0.10)
    return fig


def draw2(rows: list[dict], plt):
    fig, axes = plt.subplots(len(STEPS), 2, figsize=(WIDTH, 9.4), gridspec_kw={"width_ratios": [1.45, 1]})
    for i, s in enumerate(STEPS):
        rs = [r for r in rows if r["step"] == s]
        y = list(range(len(rs)))
        a, b = axes[i]
        dp = 2 if max(float(r["per_100k"]) for r in rs) < 1 else 1
        for k, r in enumerate(rs):
            m, filled = TIER_MARK[r["tier"]]
            mean, lo, hi = (float(r[c]) for c in ("harm_averted_mean", "lo", "hi"))
            a.plot([lo, hi], [k, k], color="black", lw=0.9, solid_capstyle="butt")
            a.plot(mean, k, marker=m, ms=4, color="black", mfc="black" if filled else "white", mew=0.7)
            lab = TIER_LETTER[r["tier"]] + (RISE if r["rising"] == "True" else "")
            a.annotate(lab, (hi, k), xytext=(4, 0), textcoords="offset points", va="center", fontsize=6.5)
            b.barh(k, float(r["per_100k"]), height=0.55, color="#9ecae1", edgecolor="black", lw=0.4)
            b.annotate(num(r["per_100k"], dp), (float(r["per_100k"]), k), xytext=(2, 0),
                       textcoords="offset points", va="center", fontsize=6)
        for ax in (a, b):
            ax.set_ylim(len(rs) - 0.5, -0.5)
            ax.set_yticks(y)
        a.set_yticklabels([r["unit"] for r in rs])
        b.set_yticklabels([])
        a.set_xlim(0, max(float(r["hi"]) for r in rs) * 1.12)
        b.set_xlim(0, max(float(r["per_100k"]) for r in rs) * 1.22)
        a.set_title(short_step(s), loc="left", fontweight="bold")
        a.ticklabel_format(axis="x", style="plain")
        a.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        if i == len(STEPS) - 1:
            a.set_xlabel("Harm averted, patients (mean and 95% interval)")
            b.set_xlabel("Harm averted per 100,000 population")
    axes[0][0].annotate("A", (-0.42, 1.25), xycoords="axes fraction", fontsize=9, fontweight="bold")
    axes[0][1].annotate("B", (-0.05, 1.25), xycoords="axes fraction", fontsize=9, fontweight="bold")
    fig.text(0.5, 0.008, "The eight units with the most harm averted in each step, data year 2023. Marker and letter: "
             "A (filled circle), act now; P (filled square), probable priority;\nU (open triangle), uncertain; "
             f"W (open diamond), watch: rising; L (open circle), lower priority; {RISE}, rising trend.",
             ha="center", va="bottom", fontsize=6.3)
    fig.subplots_adjust(left=0.19, right=0.98, top=0.96, bottom=0.085, hspace=0.62, wspace=0.08)
    return fig


def spread(vals: list[float], gap: float) -> list[float]:
    """Positions for labels at vals (sorted ascending in place order), at least `gap` apart."""
    order = sorted(range(len(vals)), key=lambda k: vals[k])
    pos = [0.0] * len(vals)
    last = -math.inf
    for k in order:
        pos[k] = max(vals[k], last + gap)
        last = pos[k]
    shift = (max(pos) - max(vals)) / 2 if vals else 0
    return [p - shift for p in pos]


def draw3(rows: list[dict], plt):
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 6.6))
    for ax, s in zip(axes.flat, ("S1", "S3", "S4", "S6")):
        rs = [r for r in rows if r["step"] == s]
        units = sorted({r["unit"] for r in rs})
        years = sorted({int(r["year"]) for r in rs})
        ends, names = [], []
        for u in units:
            ur = sorted((r for r in rs if r["unit"] == u), key=lambda r: r["year"])
            xs = [int(r["year"]) for r in ur]
            ys = [100 * float(r["rate_observed"]) for r in ur]
            if ur[0]["rising"] == "True":
                ax.plot(xs, ys, color="black", lw=1.1, marker="o", ms=2.5, zorder=3)
                ends.append(ys[-1])
                names.append(u)
            else:
                ax.plot(xs, ys, color="#bdbdbd", lw=0.6, zorder=1)
        bench = {}
        for r in rs:
            bench[int(r["year"])] = 100 * float(r["rate_bench"])
        ax.plot(sorted(bench), [bench[y] for y in sorted(bench)], color="#08519c", lw=1.3, ls="--", zorder=2)
        ax.set_xticks(years)
        ax.set_xticklabels([str(y) for y in years])
        ax.set_xlim(min(years) - 0.3, max(years) + (1.9 if names else 0.3))
        ax.set_title(short_step(s), loc="left", fontweight="bold")
        ax.set_ylabel("Achievement, notified ÷ target (%)" if s == "S1" else "Loss rate (%)")
        if names:
            lo, hi = ax.get_ylim()
            pos = spread(ends, (hi - lo) * 0.045)
            for e, p, n in zip(ends, pos, names):
                ax.annotate(f"{n} {RISE}", (max(years), e), xytext=(max(years) + 0.25, p), fontsize=6,
                            va="center", arrowprops=dict(arrowstyle="-", lw=0.4, color="black"))
        note = f"{len(names)} of {len(units)} units with a rising flag" if names else f"no rising flag ({len(units)} units)"
        ax.text(0.02, 0.97, note, transform=ax.transAxes, va="top", fontsize=6.3)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color="#bdbdbd", lw=0.8), Line2D([], [], color="black", lw=1.1, marker="o", ms=2.5),
               Line2D([], [], color="#08519c", lw=1.3, ls="--")]
    fig.legend(handles, ["unit without a rising flag", f"unit with a rising flag ({RISE}), named",
                         "benchmark (better quartile of units)"], loc="lower center", ncol=3, frameon=False)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.95, bottom=0.10, hspace=0.32, wspace=0.18)
    return fig


def draw4(rows: list[dict], plt):
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 6.8))
    titles = {"D1": "A  D1 not initiated on treatment, 2018", "D2": "B  D2 public-sector treatment not successful, 2018",
              "Madhya Pradesh": "C  Madhya Pradesh, change in notifications 2022 to 2024",
              "Maharashtra": "D  Maharashtra, change in notifications 2022 to 2024"}
    for ax, panel in zip(axes.flat, titles):
        rs = [r for r in rows if r["panel"] == panel]
        ax.set_title(titles[panel], loc="left", fontweight="bold")
        ax.set_xscale("log")
        if panel in ("D1", "D2"):
            low = [r for r in rs if r["tier"] == "lower priority"]
            ax.scatter([float(r["x"]) for r in low], [100 * float(r["y"]) for r in low], s=3, color="#bdbdbd",
                       lw=0, zorder=1)
            for t in ("act now", "probable priority", "uncertain"):
                m, filled = TIER_MARK[t]
                tr = [r for r in rs if r["tier"] == t]
                ax.scatter([float(r["x"]) for r in tr], [100 * float(r["y"]) for r in tr], s=12, marker=m,
                           facecolor="black" if filled else "white", edgecolor="black", lw=0.6, zorder=3)
            ax.axhline(100 * float(rs[0]["centre"]), color="#08519c", ls="--", lw=1.1)
            ax.set_xlabel("District denominator, patients (log scale)")
            ax.set_ylabel("Loss rate (%)")
            n_up = sum(r["tier"] in ("act now", "probable priority", "uncertain") for r in rs)
            ax.text(0.98, 0.97, f"{len(rs)} districts; {n_up} in the upper tiers", transform=ax.transAxes,
                    ha="right", va="top", fontsize=6.3)
        else:
            centre, phi = float(rs[0]["centre"]), float(rs[0]["phi"])
            R = 1 + centre
            xs = sorted(float(r["x"]) for r in rs)
            grid = [math.exp(math.log(xs[0] * 0.8) + k * (math.log(xs[-1] * 1.25) - math.log(xs[0] * 0.8)) / 200)
                    for k in range(201)]
            for z, ls in ((Z998, "-"), (Z95, ":")):
                w = [z * math.sqrt(phi) * math.sqrt(n * (1 + R)) / n for n in grid]
                ax.plot(grid, [100 * (centre + v) for v in w], color="#08519c", ls=ls, lw=0.9)
                ax.plot(grid, [100 * (centre - v) for v in w], color="#08519c", ls=ls, lw=0.9)
            ax.axhline(100 * centre, color="#08519c", lw=1.1, ls="--")
            within = [r for r in rs if "beyond" not in r["flag"]]
            ax.scatter([float(r["x"]) for r in within], [100 * float(r["y"]) for r in within], s=9,
                       facecolor="white", edgecolor="#636363", lw=0.6, zorder=2)
            flagged = sorted((r for r in rs if "beyond" in r["flag"]), key=lambda r: float(r["x"]))
            mid = math.sqrt(xs[0] * xs[-1])
            for i, r in enumerate(flagged):
                fell = r["flag"].startswith("fell")
                x, y = float(r["x"]), 100 * float(r["y"])
                ax.scatter(x, y, s=16, marker="v" if fell else "^", color="black", zorder=3)
                near = i > 0 and x / float(flagged[i - 1]["x"]) < 1.6 and abs(y - 100 * float(flagged[i - 1]["y"])) < 8
                dy = (-9 if near else 5) if not fell else -8
                right = x > mid
                ax.annotate(r["district"].replace("_", " "), (x, y), xytext=(-4 if right else 4, dy),
                            textcoords="offset points", fontsize=6, ha="right" if right else "left")
            ax.set_ylim(min(-60.0, ax.get_ylim()[0]), max(60.0, ax.get_ylim()[1]))
            ax.set_xlabel("Notifications in 2022 (log scale)")
            ax.set_ylabel("Change, 2022 to 2024 (%)")
            n_f = sum(r["flag"].startswith("fell") for r in rs)
            n_r = sum(r["flag"].startswith("rose") for r in rs)
            ax.text(0.98, 0.97, f"{len(rs)} districts; {n_f} fell and {n_r} rose beyond the limits",
                    transform=ax.transAxes, ha="right", va="top", fontsize=6.3)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", color="black", ms=4), Line2D([], [], marker="s", ls="", color="black", ms=4),
         Line2D([], [], marker="^", ls="", mfc="white", mec="black", ms=4),
         Line2D([], [], marker="o", ls="", color="#bdbdbd", ms=3), Line2D([], [], color="#08519c", ls="--", lw=1.1),
         Line2D([], [], color="#08519c", lw=0.9), Line2D([], [], color="#08519c", ls=":", lw=0.9),
         Line2D([], [], marker="v", ls="", color="black", ms=4), Line2D([], [], marker="^", ls="", color="black", ms=4)]
    fig.legend(h, ["act now", "probable priority", "uncertain", "lower priority",
                   "benchmark (A, B) or State change (C, D)", "99.8% limits, widened for overdispersion",
                   "95% limits, widened", "fell beyond the 99.8% limits", "rose beyond the 99.8% limits"],
               loc="lower center", ncol=3, frameon=False, fontsize=6.3)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.17, hspace=0.42, wspace=0.22)
    return fig


DRAW = {1: draw1, 2: draw2, 3: draw3, 4: draw4}


def write(ms_dir: Path, root: Path = ROOT, png: bool = True) -> list[str]:
    plt = setup()
    ex = ms_dir / "exhibits"
    ex.mkdir(parents=True, exist_ok=True)
    out = []
    for k, fn in FIGURES.items():
        rows = fn(root)
        (ex / f"figure{k}_data.csv").write_bytes(data_csv(rows))
        fig = DRAW[k](rows, plt)
        fig.savefig(ex / f"figure{k}.pdf", metadata={"CreationDate": None, "Creator": None, "Producer": None})
        if png:
            fig.savefig(ex / f"figure{k}.png", dpi=200)
        plt.close(fig)
        out.append(f"figure{k}.pdf: {len(rows)} data rows")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manuscript-dir", default=DEFAULT_MS_DIR)
    a = ap.parse_args(argv)
    d = Path(a.manuscript_dir)
    d = d if d.is_absolute() else ROOT / d
    for ln in write(d):
        print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
