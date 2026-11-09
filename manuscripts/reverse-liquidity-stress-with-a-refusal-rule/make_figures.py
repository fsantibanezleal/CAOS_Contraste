"""Write every figure of the manuscript from ``experiments/results_*.json`` as vector PDF into ``figures/``.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/make_figures.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import figkit  # noqa: E402

EXP = HERE / "experiments"
OUT = HERE / "figures"


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


C = load("results_reverse_c16.json")
K = load("results_corpus.json")
TH = load("results_theory.json")
figkit.style()
import matplotlib.pyplot as plt  # noqa: E402

S = figkit.STYLES
LABEL = {"list-adverse": "LiST Adverse base", "list-extreme": "LiST Extreme base", "fast-run": "2023 fast-run base"}


def fig_sp_curve() -> None:
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.7))
    for i, b in enumerate(("list-adverse", "list-extreme")):
        e = C["bases"][b]
        ax[0].plot(e["curve_multipliers"], e["curve_sp"], label=LABEL[b], **S[i])
        ax[0].plot([e["engine"]["multiplier"]], [30], marker="*", ms=9, color="k", ls="none")
    ax[0].axhline(30, color="0.5", lw=0.6, ls=":")
    ax[0].set_xscale("log")
    ax[0].set_xlabel("run-off multiplier m (log scale)")
    ax[0].set_ylabel("survival period (days)")
    ax[0].legend(frameon=False)
    e = C["bases"]["fast-run"]
    sp = [6 if s is None else s for s in e["curve_sp"]]
    ax[1].plot(e["curve_multipliers"], sp, **S[2])
    ax[1].axhline(5.5, color="0.5", lw=0.6, ls=":")
    ax[1].set_xlabel("run-off multiplier m")
    ax[1].set_ylabel("survival period (days; 6 = survives)")
    ax[1].set_title("2023 fast-run base, horizon 5 days", fontsize=8)
    figkit.save(fig, OUT, "sp-curve")


def fig_by_target() -> None:
    fig, ax = plt.subplots(figsize=(3.4, 2.7))
    for i, b in enumerate(("list-adverse", "list-extreme")):
        rows = [r for r in C["band"][b]["by_target"] if r["multiplier"] is not None]
        t = np.array([r["target"] for r in rows])
        m = np.array([r["multiplier"] for r in rows])
        ax.plot(t, m, label=LABEL[b], **{**S[i], "marker": None})
        sp0 = C["bases"][b]["base_sp"]
        ax.plot(t, sp0 / t, color=S[i]["color"], ls=":", lw=0.8)
    ax.set_yscale("log")
    ax.set_xlabel("target survival period T (days)")
    ax.set_ylabel("threshold multiplier (log scale)")
    ax.legend(frameon=False)
    figkit.save(fig, OUT, "by-target")


def fig_methods() -> None:
    names = [("proposed", "proposed"), ("grid_case", "case grid"), ("grid_fine", "fine grid"), ("brent_sp", "Brent on SP"),
             ("bisect_no_refusal", "no refusal"), ("uncapped", "no cap"), ("nearest", "nearest decimal"), ("raw_capacity", "raw capacity")]
    fig, ax = plt.subplots(1, 3, figsize=(6.8, 2.6), sharey=True)
    for a, (key, title) in zip(ax, (("false_answer_on_refused", "answer where refused"), ("miss_on_solved", "no answer where solved"),
                                    ("threshold_property_on_solved", "threshold property holds"))):
        for i, (n, lab) in enumerate(names):
            r = K["methods"][n][key]
            a.errorbar([r["rate"]], [i], xerr=[[r["rate"] - r["lo"]], [r["hi"] - r["rate"]]], fmt="o", color="k", ms=3, capsize=2)
        a.set_title(title, fontsize=8)
        a.set_xlim(-0.03, 1.03)
        a.set_xlabel("share of instances")
    ax[0].set_yticks(range(len(names)))
    ax[0].set_yticklabels([n[1] for n in names])
    ax[0].invert_yaxis()
    figkit.save(fig, OUT, "methods")


def fig_scatter() -> None:
    s = K["scatter"]
    m0 = np.array(s["m0"])
    hy = np.array([np.nan if x is None else x for x in s["hyper"]])
    gc = np.array(s["grid_case"])
    flat = np.array(s["flat_no_inflow"])
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.9), layout="constrained")
    lim = [1.0, 150.0]
    ax[0].plot(lim, lim, color="0.6", lw=0.6)
    ax[0].fill_between(lim, [0.9 * x for x in lim], [1.1 * x for x in lim], color="0.9")
    ax[0].plot(m0[flat], hy[flat], ls="none", marker=".", ms=2.5, color="0.1", label="constant capacity, no inflow")
    ax[0].plot(m0[~flat], hy[~flat], ls="none", marker="x", ms=2.5, color="0.5", label="other banks")
    ax[0].set(xscale="log", yscale="log", xlabel="threshold multiplier", ylabel="SP(1) / T")
    ax[0].legend(frameon=False, fontsize=6)
    ax[1].plot(lim, lim, color="0.6", lw=0.6)
    ax[1].plot(m0, gc, ls="none", marker=".", ms=2.5, color="0.1")
    ax[1].set(xscale="log", yscale="log", xlabel="threshold multiplier", ylabel="first case-grid multiplier that reaches T")
    figkit.save(fig, OUT, "scatter")


def fig_gap() -> None:
    s = K["scatter"]
    gap = np.array(s["gap"])
    flat = np.array(s["flat_no_inflow"])
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    bins = np.arange(-0.5, max(8.5, gap.max() + 1.5), 1.0)
    ax.hist([gap[flat], gap[~flat]], bins=bins, color=["0.2", "0.65"], label=["constant capacity, no inflow", "other banks"], log=True)
    ax.set_xlabel("target minus survival period at the multiplier (days)")
    ax.set_ylabel("solved instances (log scale)")
    ax.legend(frameon=False, fontsize=7)
    figkit.save(fig, OUT, "gap")


def fig_labelled() -> None:
    L = C["labelled_run"]
    fig, ax = plt.subplots(figsize=(3.6, 2.8))
    days = np.arange(1, 6)
    for i, (k, lab) in enumerate((("calibrated", "calibrated base, m = 1"), ("reverse_t2", "m at which SP falls to 2 days"),
                                   ("labelled", "m reproducing 85% in 2 days"))):
        ax.plot(days, L["curves"][k], label=lab, **S[i])
    obs = [(r["days"], r["observed"], r["bank"]) for r in L["rows"] if r["modelled"] is not None]
    ax.plot([o[0] for o in obs], [o[1] for o in obs], ls="none", marker="*", ms=8, color="k", label="observed (Table A.1)")
    ax.set_xlabel("day of the run")
    ax.set_ylabel("cumulative outflow, share of deposits")
    ax.legend(frameon=False, fontsize=6)
    figkit.save(fig, OUT, "labelled-run")


def fig_band() -> None:
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.8), layout="constrained")
    for i, b in enumerate(("list-adverse", "list-extreme")):
        rows = C["band"][b]["uninsured_share"]
        ax[0].plot([r["uninsured_share"] for r in rows], [r["multiplier"] for r in rows], label=LABEL[b], **S[i])
    ax[0].set_xlabel("uninsured share of domestic deposits")
    ax[0].set_ylabel("threshold multiplier at T = 30")
    ax[0].legend(frameon=False)
    labels, vals, hatch = [], [], []
    for b in ("list-adverse", "list-extreme"):
        for r in C["band"][b]["haircut_x_monetisation"]:
            labels.append(f"{b.split('-')[1][:3]} {r['haircut'][:3]} {r['monetisation'][:3]}")
            vals.append(r["multiplier"])
    x = np.arange(len(vals))
    ax[1].bar(x, [0 if v is None else v for v in vals], color="0.4")
    for xi, v in zip(x, vals):
        if v is None:
            ax[1].text(xi, 0.05, "refused", rotation=90, fontsize=5, ha="center", va="bottom")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(labels, rotation=90, fontsize=5)
    ax[1].set_ylabel("threshold multiplier at T = 30")
    figkit.save(fig, OUT, "band")


if __name__ == "__main__":
    for f in (fig_sp_curve, fig_by_target, fig_methods, fig_scatter, fig_gap, fig_labelled, fig_band):
        f()
    print("figures written to", OUT)
