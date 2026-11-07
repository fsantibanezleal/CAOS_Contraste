"""Write the figures of the manuscript (vector PDF, readable in grayscale) from ``experiments/results_*.json`` and the committed artifacts.

    python manuscripts/engines-and-test-catalogues/make_figures.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import figkit  # noqa: E402

EXP, OUT, S = HERE / "experiments", HERE / "figures", figkit.STYLES
figkit.style()
import matplotlib.pyplot as plt  # noqa: E402


def load(n: str) -> dict:
    return json.loads((EXP / n).read_text(encoding="utf-8"))


ECB, PRT, IRR, ABL, CAT = (load(n) for n in ("results_ecb.json", "results_portfolio.json", "results_irrbb.json", "results_ablation.json",
                                             "results_catalogue.json"))


def fig_ecb_agreement() -> None:
    names = {"pd.jeffreys": "Jeffreys", "disc.auc_vs_initial": "AUC vs\ndevelopment", "rating.mwb": "MWB", "rating.migration_ztests": "migration\nz-tests",
             "rating.hhi": "concentration"}
    fig, ax = plt.subplots(figsize=(5.6, 2.8))
    x = np.arange(len(names))
    mx = [max(ECB["part_a"][k]["max_abs_diff"], 1e-17) for k in names]
    mn = [max(ECB["part_a"][k]["mean_abs_diff"], 1e-18) for k in names]
    ax.bar(x - 0.18, mx, 0.35, color="0.25", label="largest difference")
    ax.bar(x + 0.18, mn, 0.35, color="0.7", label="mean difference")
    ax.set_yscale("log")
    ax.set_xticks(x, list(names.values()))
    ax.set_ylabel("absolute difference from the transcription")
    ax.legend()
    figkit.save(fig, OUT, "ecb-agreement")


def fig_jeffreys_binomial() -> None:
    rows = ECB["part_b"]["rows"]
    fig, ax = plt.subplots(figsize=(4.4, 4.0))
    ax.scatter([r["p_binomial"] for r in rows], [r["p_jeffreys"] for r in rows], s=14, c="0.2")
    ax.plot([0, 1], [0, 1], color="0.6", lw=0.8, ls=":")
    ax.axhline(0.05, color="0.5", lw=0.8, ls="--")
    ax.axvline(0.05, color="0.5", lw=0.8, ls="--")
    ax.set_xlabel("exact binomial test, one-sided p-value")
    ax.set_ylabel("ECB Jeffreys test, p-value")
    figkit.save(fig, OUT, "jeffreys-binomial")


def fig_lhp_anchor() -> None:
    from riskvalidation.engines.vasicek import lhp_cdf, lhp_pdf
    from scipy import integrate

    ci = figkit.doc("C10/commercial-industrial.json")["outputs"]["fit"]["maximum_likelihood"]
    pd_hat, rho_hat = ci["pd"]["estimate"], ci["rho"]["estimate"]
    pts = np.array([0.002, 0.005, 0.01, 0.02, 0.035, 0.05, 0.07])
    areas = np.array([integrate.quad(lambda t: float(lhp_pdf(t, pd_hat, rho_hat)), 0, x, limit=200)[0] for x in pts])
    cdf = np.array([float(lhp_cdf(x, pd_hat, rho_hat)) for x in pts])
    grid = np.linspace(0.0005, 0.07, 300)
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.8))
    a.plot(100 * grid, [float(lhp_cdf(x, pd_hat, rho_hat)) for x in grid], color="0.0", label="engine distribution function")
    a.plot(100 * pts, areas, "s", color="0.4", mfc="white", label="quadrature of the density")
    a.set_xlabel("loss rate, %")
    a.set_ylabel("probability that the loss rate is at most x")
    a.legend(fontsize=7)
    b.semilogy(100 * pts, np.maximum(np.abs(areas - cdf), 1e-16), "o-", color="0.2")
    b.set_xlabel("loss rate, %")
    b.set_ylabel("absolute difference of the two routes")
    fig.tight_layout()
    figkit.save(fig, OUT, "lhp-anchor")


def fig_mc_agreement() -> None:
    q = PRT["mc"]["quantities"]
    names = [("var99", "VaR 99%"), ("es99", "ES 99%"), ("var999", "VaR 99.9%"), ("es999", "ES 99.9%")]
    fig, ax = plt.subplots(figsize=(5.4, 2.8))
    for i, (k, lab) in enumerate(names):
        e, d = q[k]["engine_mean"], q[k]["independent_mean"]
        ax.errorbar(i - 0.08, e / d, yerr=q[k]["engine_sd"] / d, fmt="o", color="0.0", capsize=3, label="engine sampler" if i == 0 else None)
        ax.errorbar(i + 0.08, 1.0, yerr=q[k]["independent_sd"] / d, fmt="s", color="0.5", mfc="white", capsize=3,
                    label="independent simulator" if i == 0 else None)
    ax.set_xticks(range(len(names)), [n[1] for n in names])
    ax.set_ylabel("mean over the runs, relative to the independent mean")
    ax.legend(fontsize=7)
    figkit.save(fig, OUT, "mc-agreement")


def fig_coverage() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.9), sharey=True)
    reps = PRT["grids"]["22"]["n_replications"]
    half = 2.576 * math.sqrt(0.95 * 0.05 / reps)
    for ax, y in zip(axes, ("22", "40")):
        cells = PRT["grids"][y]["cells"]
        rho = [c["rho"] for c in cells]
        for est, st in (("maximum-likelihood", S[0]), ("moments", S[1])):
            ax.plot(rho, [c[est]["coverage"] for c in cells], label=est, **st)
        ax.axhline(0.95, color="0.5", lw=0.8, ls=":")
        ax.axhspan(0.95 - half, 0.95 + half, color="0.85", alpha=0.6)
        ax.set_xlabel("known correlation")
        ax.set_title(f"{y} years", fontsize=9)
    axes[0].set_ylabel("coverage of the 95% interval")
    axes[0].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, OUT, "coverage-grid")


def fig_eve() -> None:
    rows = [r for r in IRR["variants"]["rows"] if r["leg"] != "pair"]
    fig, ax = plt.subplots(figsize=(5.8, 2.8))
    ax.semilogy(range(len(rows)), [max(r["rel_ql"], 1e-17) for r in rows], "o", color="0.2", ms=3, label="QuantLib present value")
    ax.semilogy(range(len(rows)), [max(r["rel_engine"], 1e-17) for r in rows], "s", color="0.6", mfc="white", ms=3, label="engine present value")
    ax.set_xlabel("variant, currency leg and shock (72 in all)")
    ax.set_ylabel("relative difference from the stored EVE")
    ax.legend(fontsize=7)
    figkit.save(fig, OUT, "eve-reconciliation")


def fig_ablation() -> None:
    mut = ABL["mutants"]
    m = np.array([[1.0 if x["detected_by"][k] else 0.0 for k in "ABCDE"] for x in mut])
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    ax.imshow(1 - 0.75 * m, cmap="gray", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(5), list("ABCDE"))
    ax.set_yticks(range(len(mut)), [x["id"].replace("m", "M") + (" (equivalent)" if x["equivalent"] else "") for x in mut], fontsize=7)
    ax.set_xticks(np.arange(-0.5, 5), minor=True)
    ax.set_yticks(np.arange(-0.5, len(mut)), minor=True)
    ax.grid(which="minor", color="white", lw=1.2)
    ax.tick_params(which="minor", length=0)
    ax.set_xlabel("verification layer (dark: the layer detects the defect)")
    figkit.save(fig, OUT, "ablation-matrix")


def fig_is() -> None:
    q = PRT["is_euler"]
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    ax.errorbar([0], [q["plain_mean"]], yerr=q["plain_sd"], fmt="o", color="0.0", capsize=4)
    ax.errorbar([1], [q["is_mean"]], yerr=q["is_sd"], fmt="s", color="0.4", capsize=4)
    ax.axhline(0.001, color="0.6", ls=":", lw=0.8)
    ax.set_xticks([0, 1], ["plain Monte Carlo", "importance sampling"])
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylabel("probability of a loss above the 99.9% VaR")
    figkit.save(fig, OUT, "importance-sampling")


for fn in (fig_ecb_agreement, fig_jeffreys_binomial, fig_lhp_anchor, fig_mc_agreement, fig_coverage, fig_eve, fig_ablation, fig_is):
    fn()
print(len(list(OUT.glob("*.pdf"))), "figures")
