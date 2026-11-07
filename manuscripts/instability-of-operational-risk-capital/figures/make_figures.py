"""The figures of the manuscript, as vector PDF in this folder, from ``experiments/results.json`` and the per-history files.

Every curve and bar is computed from the 16,000 histories; the style is the shared grayscale one of ``manuscripts/_shared/figkit.py``.
Run from the repository root after ``experiments/analyse.py``::

    python manuscripts/instability-of-operational-risk-capital/figures/make_figures.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent / "experiments"
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

R = json.loads((EXP / "results.json").read_text(encoding="utf-8"))
CELLS = R["cells"]
XIS = (0.6, 0.8, 0.96, 1.1)
VIDS = ("xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1")
CELL_IDS = ("y5-h10000", "y5-h20000", "y10-h10000", "y10-h20000")
CELL_TXT = {"y5-h10000": "5 years, EUR 10,000", "y5-h20000": "5 years, EUR 20,000", "y10-h10000": "10 years, EUR 10,000", "y10-h20000": "10 years, EUR 20,000"}
SHORT = {"lda_lognormal": "Lognormal, threshold ignored", "lda_lognormal_truncated": "Truncated lognormal", "lda_splice": "Splice", "sla": "Single loss approx.",
         "scenario": "Scenario", "sla_mean_adjusted": "Mean-adjusted", "sla_cvm": "CvM GPD", "sla_obre": "Bias-robust GPD", "sla_cvm_lognormal": "CvM lognormal"}


def cell(vid: str, cid: str) -> dict:
    return next(c for c in CELLS if c["variant"] == vid and c["id"] == cid)


def histories(vid: str) -> dict:
    return json.loads((EXP / f"histories-{vid}.json").read_text(encoding="utf-8"))


def fig_ecdf() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 4, figsize=(7.6, 2.5), sharey=True)
    rungs = ("lda_lognormal_truncated", "lda_splice", "sla", "scenario")
    for ax, vid, xi in zip(axes, VIDS, XIS, strict=True):
        h = histories(vid)
        c = next(c for c in h["cells"] if c["id"] == "y10-h20000")
        for i, r in enumerate(rungs):
            x = np.sort(np.array([v for v in c["ratio"][r] if v is not None]))
            ax.step(x, np.arange(1, x.size + 1) / 1000.0, where="post", label=SHORT[r], **{k: v for k, v in figkit.STYLES[i].items() if k != "marker"})
        ax.axvline(1.0, color="0.6", lw=0.6)
        ax.set_xscale("log")
        ax.set_xlim(0.01, 100)
        ax.set_title(f"$\\xi={xi:g}$")
        ax.set_xlabel("capital / true quantile")
    axes[0].set_ylabel("share of the 1,000 histories")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.1))
    figkit.save(fig, HERE, "ecdf-ratio")


def fig_iqr_grid() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.8), sharey=True)
    for ax, rung, title in zip(axes, ("lda_splice", "sla"), ("Lognormal-GPD splice", "Single loss approximation"), strict=True):
        for i, cid in enumerate(CELL_IDS):
            ys = [cell(v, cid)["rungs"][rung] for v in VIDS]
            y = np.array([s["iqr"] for s in ys])
            lo = y - np.array([s["ci"]["iqr"][0] for s in ys])
            hi = np.array([s["ci"]["iqr"][1] for s in ys]) - y
            ax.errorbar(np.arange(4) + (i - 1.5) * 0.08, y, yerr=[lo, hi], capsize=2, label=CELL_TXT[cid], **figkit.STYLES[i])
        ax.axhline(0.25, color="0.5", lw=0.6, ls=":")
        ax.set_xticks(range(4))
        ax.set_xticklabels([f"{x:g}" for x in XIS])
        ax.set_xlabel("true tail index $\\xi$")
        ax.set_title(title)
    axes[0].set_ylabel("interquartile range of capital / truth")
    axes[0].legend(frameon=False, fontsize=7)
    figkit.save(fig, HERE, "iqr-by-cell")


def fig_ladder() -> None:
    import matplotlib.pyplot as plt

    rungs = ("lda_lognormal_truncated", "lda_splice", "sla", "scenario", "sla_mean_adjusted", "sla_cvm", "sla_obre", "sla_cvm_lognormal")
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0))
    for k, cid in enumerate(("y5-h10000", "y10-h20000")):
        ax = axes[k]
        w = 0.8 / len(rungs)
        for i, r in enumerate(rungs):
            ys = [cell(v, cid)["rungs"][r] for v in VIDS]
            y = np.array([s["iqr"] for s in ys])
            err = [y - np.array([s["ci"]["iqr"][0] for s in ys]), np.array([s["ci"]["iqr"][1] for s in ys]) - y]
            ax.bar(np.arange(4) + (i - len(rungs) / 2 + 0.5) * w, y, w, yerr=err, capsize=1, color=str(0.15 + 0.08 * i), edgecolor="0.0", linewidth=0.3, label=SHORT[r])
        ax.axhline(0.25, color="0.5", lw=0.6, ls=":")
        ax.set_xticks(range(4))
        ax.set_xticklabels([f"{x:g}" for x in XIS])
        ax.set_xlabel("true tail index $\\xi$")
        ax.set_title(CELL_TXT[cid], fontsize=8)
    axes[0].set_ylabel("interquartile range of capital / truth")
    axes[1].legend(frameon=False, fontsize=6, ncol=2, loc="upper left")
    figkit.save(fig, HERE, "iqr-by-rung")


def fig_median() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for i, r in enumerate(("lda_lognormal_truncated", "lda_splice", "sla", "scenario", "sla_obre")):
        ys = [np.mean([cell(v, cid)["rungs"][r]["median"] for cid in CELL_IDS if cell(v, cid)["rungs"][r]["n_defined"]]) for v in VIDS]
        ax.plot(XIS, ys, label=SHORT[r], **figkit.STYLES[i])
    ax.axhline(1.0, color="0.6", lw=0.6)
    ax.set_xlabel("true tail index $\\xi$")
    ax.set_ylabel("median capital / truth (mean of the four cells)")
    ax.legend(frameon=False, fontsize=7)
    figkit.save(fig, HERE, "median-by-xi")


def fig_theory() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax = axes[0]
    marks = {0.6: "o", 0.8: "s", 0.96: "^", 1.1: "D"}
    for t in R["theory_check"]:
        ax.plot(t["sd_predicted"], t["sd_measured"], marker=marks[t["tail_index"]], color="0.15", mfc="none")
    lim = [0.5, 1.5]
    ax.plot(lim, lim, color="0.5", lw=0.6)
    ax.plot(lim, [x * 1.25 for x in lim], color="0.7", lw=0.5, ls=":")
    ax.plot(lim, [x * 0.75 for x in lim], color="0.7", lw=0.5, ls=":")
    ax.set_xlabel("predicted $\\mathrm{sd}(\\ln \\hat q/q)$")
    ax.set_ylabel("measured, 1,000 histories")
    ax.set_title("Dispersion of the single loss approximation", fontsize=8)
    ax = axes[1]
    for t in R["theory_check"]:
        if t["tail_index"] in (0.96, 1.1):
            ax.plot(t["share_predicted"], t["share_measured"], marker=marks[t["tail_index"]], color="0.15", mfc="none", label=f"$\\xi={t['tail_index']:g}$")
    ax.plot([0, 1], [0, 1], color="0.5", lw=0.6)
    ax.set_xlabel("predicted share with $\\hat\\xi\\geq1$")
    ax.set_ylabel("measured share")
    ax.set_title("Histories that conclude an infinite mean", fontsize=8)
    h, l = ax.get_legend_handles_labels()
    ax.legend(dict(zip(l, h)).values(), dict(zip(l, h)).keys(), frameon=False, fontsize=7)
    figkit.save(fig, HERE, "theory-vs-measured")


def fig_infinite() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    for ax, xi, vid in zip(axes, (0.96, 1.1), ("xi-0-96", "xi-1-1"), strict=True):
        for i, cid in enumerate(CELL_IDS):
            c = cell(vid, cid)
            y = [p["share_at_least_one"] for p in c["tail_profile"]]
            lo = [p["share_at_least_one"] - p["ci_at_least_one"][0] for p in c["tail_profile"]]
            hi = [p["ci_at_least_one"][1] - p["share_at_least_one"] for p in c["tail_profile"]]
            ax.errorbar([1, 2, 4, 8], y, yerr=[lo, hi], capsize=2, label=CELL_TXT[cid], **figkit.STYLES[i])
            ax.plot([1], [c["theory"]["share_xi_hat_at_least_one"]], marker="*", color="0.0", ms=7, ls="none")
        ax.axhline(0.5, color="0.7", lw=0.5, ls=":")
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 2, 4, 8])
        ax.set_xticklabels(["$H$", "$2H$", "$4H$", "$8H$"])
        ax.set_xlabel("threshold of the tail fit")
        ax.set_title(f"true $\\xi={xi:g}$", fontsize=8)
    axes[0].set_ylabel("share of fits with $\\hat\\xi\\geq1$")
    axes[0].legend(frameon=False, fontsize=6.5, loc="upper left")
    figkit.save(fig, HERE, "infinite-mean-share")


def fig_years() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.8, 3.0))
    for i, h in enumerate((10000, 20000)):
        ys = [next(c for c in CELLS if c["variant"] == v and c["threshold_eur"] == h and c["years"] == 5)["theory"]["years_green"] for v in VIDS]
        ax.plot(XIS, ys, label=f"threshold EUR {h:,}", **figkit.STYLES[i])
    for y in (5, 10):
        ax.axhline(y, color="0.5", lw=0.6, ls=":")
        ax.text(0.61, y * 1.08, f"{y} years", fontsize=7, color="0.3")
    ax.set_yscale("log")
    ax.set_xlabel("true tail index $\\xi$")
    ax.set_ylabel("years of history for IQR $\\leq0.25$")
    ax.legend(frameon=False, fontsize=7)
    figkit.save(fig, HERE, "years-for-green")


def fig_precision() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    sizes = R["settings"]["subset_sizes"][:-1]
    for i, (rung, name) in enumerate((("lda_splice", "Splice"), ("sla", "Single loss approximation"))):
        med = []
        for m in sizes:
            rel = [c["subset_iqr"][rung][str(m)]["sd"] / c["subset_iqr"][rung][str(m)]["mean"] for c in CELLS if str(m) in c["subset_iqr"].get(rung, {})]
            med.append(float(np.median(rel)))
        ax.plot(sizes, med, label=name, **figkit.STYLES[i])
    ref = med[0] * math.sqrt(sizes[0])
    ax.plot(sizes, [ref / math.sqrt(m) for m in sizes], color="0.6", lw=0.6, label="$n^{-1/2}$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("histories in the subset")
    ax.set_ylabel("relative sd of the measured IQR")
    ax.legend(frameon=False, fontsize=7)
    figkit.save(fig, HERE, "precision-vs-histories")


def fig_ablation() -> None:
    import matplotlib.pyplot as plt

    names = list(R["ablation"])
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    d = np.array([100 * R["ablation"][n]["delta_within"] for n in names])
    lo = d - np.array([100 * R["ablation"][n]["delta_within_ci"][0] for n in names])
    hi = np.array([100 * R["ablation"][n]["delta_within_ci"][1] for n in names]) - d
    ax.barh(range(len(names)), d, xerr=[lo, hi], color="0.55", edgecolor="0.0", linewidth=0.4, capsize=2)
    ax.axvline(0, color="0.0", lw=0.6)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([n.replace("_", " ") for n in names], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("change in the share of histories within a factor 2 (points)")
    figkit.save(fig, HERE, "ablation-change")


def main() -> int:
    figkit.style()
    for fn in (fig_ecdf, fig_iqr_grid, fig_ladder, fig_median, fig_theory, fig_infinite, fig_years, fig_precision, fig_ablation):
        fn()
    print("wrote", len(list(HERE.glob("*.pdf"))), "figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
