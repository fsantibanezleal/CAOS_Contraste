"""Figures of the manuscript on the anchored PD under informative rating withdrawals (vector PDF, readable in grayscale).

Reads the committed documents ``data/derived/C04/{sp,fitch}.json`` and the outputs of ``experiments/extended_study.py``
under ``experiments/results/``; the curve of the first figure is computed with the engine's ``withdrawal_pd``.

Run from the repository root::

    python manuscripts/anchored-pd-under-informative-withdrawals/figures/make_figures.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))
import figkit  # noqa: E402

figkit.style()
import matplotlib.pyplot as plt  # noqa: E402
from riskvalidation.transitions.withdrawals import withdrawal_pd  # noqa: E402

RES = HERE.parent / "experiments" / "results"
B = 5
INF = (0.0, 1.0, 3.0, 9.0, 19.0)
S = figkit.STYLES


def load(name: str) -> dict:
    return json.loads((RES / name).read_text(encoding="utf-8"))["data"]


def grade(o: dict, name: str) -> dict:
    return next(g for g in o["withdrawal_bounds"]["grades"] if g["grade"] == name)


def fig_pd_curve(sp: dict) -> None:
    g = grade(sp, "B")
    p, tp = g["pooled"], g["tipping"]
    d, s, w = p["defaults"], p["survivors"], p["withdrawn"]
    ks = np.logspace(-1.5, 3, 400)
    pd = np.array([float(withdrawal_pd(d, s, w, k)[0]) for k in ks]) * 100
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    ax.plot(ks, pd, **{**S[0], "marker": None}, label="PD$(k)$, S&P grade B, pooled 2000 to 2025")
    ax.axhline(100 * float(withdrawal_pd(d, s, w, np.inf)[0]), color="0.5", lw=0.8, ls=(0, (6, 2)))
    ax.text(0.04, 100 * float(withdrawal_pd(d, s, w, np.inf)[0]) * 0.93, "Manski bound $(D+W)/N$", fontsize=7, color="0.3")
    ax.axvspan(p["k_low"], p["k_high"], color="0.85", label="anchored $k$ band")
    ax.plot([p["k"]], [100 * p["pd_anchored"]], marker="o", color="0", ls="none", label="anchored PD at the anchored $k$")
    ax.plot([1.0], [100 * p["pd_industry"]], marker="s", color="0", mfc="white", ls="none", label="removed ($k=1$)")
    ax.plot([ks[0]], [100 * d / (d + s + w)], marker="^", color="0", mfc="white", ls="none", label="kept ($k=0$)")
    ax.plot([tp["k"]], [100 * tp["threshold"]], marker="D", color="0", mfc="white", ls="none",
            label="tipping $k^*$ to the next grade")
    ax.axhline(100 * tp["threshold"], color="0.3", lw=0.7, ls=":")
    ax.set_xscale("log")
    ax.set_xlabel("odds ratio $k$ of withdrawal for a rating that defaults within the year")
    ax.set_ylabel("one-year PD (%)")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.88), frameon=False, fontsize=7)
    figkit.save(fig, HERE, "fig-pd-curve")


def fig_coverage_k(grid: list, scale: list) -> None:
    cells = {("fy" if c["design"] == "first_year" else "pool", c["informative"]): c for c in grid}
    for c in scale:
        if c["scale"] == 10:
            cells[("x10", c["informative"])] = c
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.9), sharey=True)
    titles = {"fy": "first-year cohort", "pool": "five cohorts pooled", "x10": "ten times the cohort"}
    series = (("industry", "removed ($k=1$)"), ("unfollowed", "kept ($k=0$)"), ("followed", "followed (oracle)"),
              ("band", "anchored $k$ band alone"), ("anchored", "anchored interval"))
    for ax, des in zip(axes, ("fy", "pool", "x10")):
        for j, (t, name) in enumerate(series):
            ax.plot(range(len(INF)), [100 * cells[(des, i)]["treatments"][t]["coverage"][B] for i in INF], label=name, **S[j])
        ax.axhline(95, color="0.6", lw=0.6, ls=":")
        ax.axhline(50, color="0.6", lw=0.6, ls=":")
        ax.set_xticks(range(len(INF)), [f"{i:g}" for i in INF])
        ax.set_xlabel("informativeness $\\iota$")
        ax.set_title(titles[des])
        ax.set_ylim(-3, 103)
    axes[0].set_ylabel("coverage of the true PD, grade B (%)")
    axes[0].legend(loc="lower left", frameon=False, fontsize=6.5)
    figkit.save(fig, HERE, "fig-coverage-k")


def fig_scale(grid: list, scale: list) -> None:
    cells = {c["scale"]: c for c in scale if c["informative"] == 9.0}
    cells[1] = next(c for c in grid if c["design"] == "first_year" and c["informative"] == 9.0)
    xs = (1, 3, 10, 30)
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9))
    for j, (t, name) in enumerate((("industry", "removed"), ("followed", "followed (oracle)"), ("anchored", "anchored"))):
        axes[0].plot(range(4), [100 * cells[x]["treatments"][t]["coverage"][B] for x in xs], label=name, **S[j])
    axes[0].axhline(95, color="0.6", lw=0.6, ls=":")
    axes[0].set_ylabel("coverage of the true PD, grade B (%)")
    axes[0].legend(frameon=False, fontsize=7, loc="center left")
    for j, (t, name) in enumerate((("anchored", "anchored interval"), ("followed", "followed (oracle)"),
                                   ("identified", "Manski band"))):
        axes[1].plot(range(4), [100 * cells[x]["treatments"][t]["width"][B] for x in xs], label=name, **S[j])
    axes[1].set_yscale("log")
    axes[1].set_ylabel("mean width (percentage points)")
    axes[1].legend(frameon=False, fontsize=7)
    for ax in axes:
        ax.set_xticks(range(4), [f"$\\times{x}$" for x in xs])
        ax.set_xlabel("cohort size relative to the case's")
    figkit.save(fig, HERE, "fig-scale")


def fig_capture(grid: list, cap: list) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.9))
    for j, iota in enumerate((9.0, 3.0)):
        cs = sorted([c for c in cap if c["informative"] == iota], key=lambda c: c["capture"])
        fy = next(c for c in grid if c["design"] == "first_year" and c["informative"] == iota)
        cs = sorted(cs + [{**fy, "capture": 1.0}], key=lambda c: c["capture"])
        x = [c["capture"] for c in cs]
        axes[0].plot(x, [100 * c["treatments"]["anchored"]["coverage"][B] for c in cs], label=f"anchored, $\\iota={iota:g}$", **S[j])
        axes[0].plot(x, [100 * c["treatments"]["band"]["coverage"][B] for c in cs], label=f"band alone, $\\iota={iota:g}$", **S[j + 2])
        axes[1].plot(x, [100 * c["treatments"]["anchored"]["rel_bias"][B] for c in cs], label=f"anchored, $\\iota={iota:g}$", **S[j])
        axes[1].axhline(100 * fy["treatments"]["industry"]["rel_bias"][B], color="0.35", lw=0.8, ls=(0, (3, 2)) if j else (0, (6, 2)))
        axes[1].text(0.51, 100 * fy["treatments"]["industry"]["rel_bias"][B] + 1.5, f"removed, $\\iota={iota:g}$", fontsize=6.5, color="0.3")
    axes[0].axhline(95, color="0.6", lw=0.6, ls=":")
    axes[1].axhline(0, color="0.6", lw=0.6, ls=":")
    axes[0].set_ylabel("coverage of the true PD, grade B (%)")
    axes[1].set_ylabel("relative bias of the point estimate (%)")
    for ax in axes:
        ax.set_xlabel("capture $c$ of the second source")
    axes[0].legend(frameon=False, fontsize=6.5, loc="lower center")
    axes[1].legend(frameon=False, fontsize=6.5, loc="lower right")
    fig.subplots_adjust(wspace=0.38)
    figkit.save(fig, HERE, "fig-capture")


def fig_forest(sp: dict, fi: dict) -> None:
    panels = (("S&P, grade B", sp, "B"), ("S&P, CCC to C", sp, "CCC-C"), ("Fitch, grade B", fi, "B"))
    fig, axes = plt.subplots(1, 3, figsize=(7.8, 3.3), sharey=False)
    for ax, (title, o, name) in zip(axes, panels):
        g = grade(o, name)
        p = g["pooled"]
        ax.axhspan(p["k_low"], p["k_high"], color="0.85")
        ax.axhline(p["k"], color="0.2", lw=0.9)
        xs, ys, lo, hi = [], [], [], []
        for i, c in enumerate(g["cohorts"]):
            if c["k"] is None or c["k_low"] is None or c["k_high"] is None or c["reason"] != "ok":
                continue
            xs.append(i)
            ys.append(c["k"])
            lo.append(c["k"] - c["k_low"])
            hi.append(c["k_high"] - c["k"])
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o", color="0.1", ms=2.8, elinewidth=0.7, capsize=1.5)
        ax.set_yscale("log")
        labels = [c["label"] for c in g["cohorts"]]
        ticks = list(range(0, len(labels), 5))
        ax.set_xticks(ticks, [labels[t] for t in ticks])
        ax.set_title(title)
        ax.set_xlabel("annual cohort")
    axes[0].set_ylabel("anchored odds ratio $k$ (log scale)")
    figkit.save(fig, HERE, "fig-forest")


def fig_stability(stab: list, sp: dict) -> None:
    grades = ("BB", "B", "CCC-C")
    sh = {(s["informative"], s["capture"], s["grade"]): s for s in stab}
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    width = 0.135
    groups = ((r"known truth, $\iota=9$, exact source", lambda gr: 100 * sh[(9.0, "1", gr)]["mean_share"], "0.15", None),
              (r"known truth, $\iota=9$, source at 1.3 times", lambda gr: 100 * sh[(9.0, "1.3", gr)]["mean_share"], "0.5", "//"),
              (r"known truth, $\iota=9$, multiple 1.0 to 1.6 by year", lambda gr: 100 * sh[(9.0, "u1.0-1.6", gr)]["mean_share"], "0.75", "xx"),
              (r"known truth, $\iota=9$, multiple 1.0 to 4.0 by year", lambda gr: 100 * sh[(9.0, "u1.0-4.0", gr)]["mean_share"], "0.6", "oo"),
              (r"known truth, $\iota=9$, multiple of observed defaults, grade's own ratio range, by year", lambda gr: 100 * sh[(9.0, "dobs", gr)]["mean_share"], "0.4", ".."),
              ("real S&P cohorts", lambda gr: 100 * grade(sp, gr)["stability"]["share_cohorts_containing_pooled_k"], "white", "\\\\"))
    for j, (name, fn, colr, hatch) in enumerate(groups):
        ax.bar(np.arange(3) + (j - 2.5) * width, [fn(g) for g in grades], width, label=name, color=colr, edgecolor="0.1",
               hatch=hatch, lw=0.6)
    ax.axhline(80, color="0.3", lw=0.8, ls=":", label="criterion: 80% of the cohorts")
    ax.set_xticks(range(3), ["BB", "B", "CCC to C"])
    ax.set_ylabel("cohorts holding the pooled $k$ (%)")
    ax.set_ylim(0, 112)
    ax.legend(frameon=False, fontsize=6.5, loc="upper center", ncol=1, bbox_to_anchor=(0.5, -0.12))
    figkit.save(fig, HERE, "fig-stability")


def fig_tipping(sp: dict, fi: dict) -> None:
    rows = []
    for label, o in (("S&P", sp), ("Fitch", fi)):
        for g in o["withdrawal_bounds"]["grades"]:
            p, tp = g["pooled"], g["tipping"]
            if p is None or p["k"] is None or not tp or tp["k"] is None:
                continue
            rows.append((f"{label} {g['grade'].replace('CCC-C', 'CCC to C')}", p, tp))
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    for i, (name, p, tp) in enumerate(rows):
        ax.plot([p["k_low"], p["k_high"]], [i, i], color="0.2", lw=2.2, solid_capstyle="butt")
        ax.plot([p["k"]], [i], "o", color="0", ms=4)
        ax.plot([tp["k"]], [i], "D", color="0", mfc="white", ms=5)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xscale("log")
    ax.invert_yaxis()
    ax.set_xlabel("odds ratio $k$ (log scale)")
    ax.plot([], [], "o", color="0", label="pooled anchored $k$ with its band")
    ax.plot([], [], "D", color="0", mfc="white", label="tipping $k^*$ to the next grade")
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    figkit.save(fig, HERE, "fig-tipping")


def fig_decisions(grid: list, scale: list) -> None:
    cells = {("fy" if c["design"] == "first_year" else "pool"): c for c in grid if c["informative"] == 9.0}
    cells["x10"] = next(c for c in scale if c["scale"] == 10 and c["informative"] == 9.0)
    titles = {"fy": "first-year cohort", "pool": "five cohorts pooled", "x10": "ten times the cohort"}
    deltas = ("-0.30", "-0.15", "+0.15", "+0.30")
    from matplotlib.patches import Patch

    fig, axes = plt.subplots(1, 3, figsize=(8.0, 3.2), sharey=True)
    for ax, des in zip(axes, ("fy", "pool", "x10")):
        pos = 0.0
        centers = []
        for dl in deltas:
            start = pos
            for t in ("industry", "anchored"):
                v = cells[des]["decisions"]["by_treatment"][t][dl]
                c, w, u = 100 * v["correct"], 100 * v["wrong"], 100 * v["undetermined"]
                ax.bar(pos, c, 0.8, color="0.2", edgecolor="0.1", lw=0.5)
                ax.bar(pos, u, 0.8, bottom=c, color="0.85", edgecolor="0.1", lw=0.5)
                ax.bar(pos, w, 0.8, bottom=c + u, color="white", edgecolor="0.1", hatch="////", lw=0.5)
                pos += 1.0
            centers.append((start + pos - 1.0) / 2.0)
            pos += 0.7
        ax.set_xticks(centers, [d.replace("-", "$-$") for d in deltas], fontsize=7)
        ax.set_title(titles[des])
        ax.set_xlabel(r"threshold offset $\delta$", fontsize=8)
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("repetitions (%)")
    handles = [Patch(facecolor="0.2", edgecolor="0.1", label="correct side"),
               Patch(facecolor="0.85", edgecolor="0.1", label="interval across the threshold"),
               Patch(facecolor="white", edgecolor="0.1", hatch="////", label="wrong side")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=7, bbox_to_anchor=(0.5, -0.08))
    figkit.save(fig, HERE, "fig-decisions")


def main() -> None:
    grid, scale, cap, stab = (load(n) for n in ("coverage-grid.json", "scale-ladder.json", "capture-ladder.json", "stability.json"))
    sp = figkit.doc("C04/sp.json")["outputs"]
    fi = figkit.doc("C04/fitch.json")["outputs"]
    fig_pd_curve(sp)
    fig_coverage_k(grid, scale)
    fig_scale(grid, scale)
    fig_capture(grid, cap)
    fig_forest(sp, fi)
    fig_stability(stab, sp)
    fig_tipping(sp, fi)
    fig_decisions(grid, scale)
    print("figures written to", HERE)


if __name__ == "__main__":
    main()
