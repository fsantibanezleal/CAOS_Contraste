"""Builds every figure of the manuscript as vector PDF from ``experiments/results/*.json`` and the committed documents of
``data/derived``. Grayscale-safe: series differ by marker and line style as well as by tone.

    python manuscripts/leakage-safe-validation-protocol/make_figures.py
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

figkit.style()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

RES = HERE / "experiments" / "results"
OUT = HERE / "figures"
ST = figkit.STYLES


def load(name: str) -> dict:
    return json.loads((RES / name).read_text(encoding="utf-8"))


LEAKS = {"none": "protocol", "impute_full": "imputation, all rows", "scale_full": "scaling, all rows", "bin_full": "bin edges, all rows",
         "woe_full": "WoE, holdout labels", "screen_full": "screen, holdout labels", "fit_full": "fit on train + holdout",
         "select_test": "choice on holdout", "cal_test": "calibration on holdout", "cal_overlap": "calibration overlaps holdout",
         "cv_in": "5-fold, inside", "cv_pre": "5-fold, before"}


def fig_bias_by_leak() -> None:
    syn, small = load("e1_synthetic.json")["summary"], load("e1_synthetic-small.json")["summary"]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6), sharex=True)
    for ax, model in zip(axes, ("woe", "linear")):
        keys = [k for k in LEAKS if f"{model}/{k}" in syn]
        y = np.arange(len(keys))[::-1]
        for off, (data, lab, sty) in enumerate(((syn, "2,500 rows", ST[0]), (small, "800 rows", ST[1]))):
            b = [data[f"{model}/{k}"]["auc_bias"] for k in keys]
            e = [1.96 * data[f"{model}/{k}"]["auc_bias_se"] for k in keys]
            ax.errorbar(b, y + (0.17 if off else -0.17), xerr=e, fmt=sty["marker"], color=sty["color"], ms=3.5, capsize=2, lw=0.9, label=lab)
        ax.axvline(0, color="0.5", lw=0.6)
        ax.set_yticks(y)
        ax.set_yticklabels([LEAKS[k] for k in keys])
        ax.set_title("WoE scorecard" if model == "woe" else "standardised logit")
        ax.set_xlabel("AUC bias (estimate minus reference)")
    axes[1].legend(loc="lower right", frameon=False)
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-bias-by-leak")


def fig_coverage() -> None:
    d = load("e1_synthetic.json")["summary"]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    keys = [k for k in LEAKS if f"woe/{k}" in d and "coverage" in d[f"woe/{k}"]]
    x = np.arange(len(keys))
    for off, (m, sty) in enumerate((("woe", ST[0]), ("linear", ST[1]))):
        ks = [k for k in keys if f"{m}/{k}" in d]
        xs = np.array([keys.index(k) for k in ks]) + (0.12 if off else -0.12)
        c = np.array([d[f"{m}/{k}"]["coverage"] for k in ks])
        lo = np.array([d[f"{m}/{k}"]["coverage_lo"] for k in ks])
        hi = np.array([d[f"{m}/{k}"]["coverage_hi"] for k in ks])
        ax.errorbar(xs, c, yerr=[np.maximum(c - lo, 0), np.maximum(hi - c, 0)], fmt=sty["marker"], color=sty["color"], ms=3.5, capsize=2, lw=0.9,
                    label="WoE scorecard" if m == "woe" else "standardised logit")
    ax.axhline(0.95, color="0.4", lw=0.7, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels([LEAKS[k] for k in keys], rotation=40, ha="right")
    ax.set_ylabel("coverage of the 95% interval")
    ax.set_ylim(0.3, 1.02)
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-coverage")


def fig_bias_distribution() -> None:
    d = load("e1_synthetic.json")["summary"]
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    bins = np.linspace(-0.08, 0.14, 45)
    for sty, k in zip(ST[:4], ("woe/none", "woe/cal_test", "woe/woe_full", "woe/fit_full")):
        ax.hist(d[k]["bias_draws"], bins=bins, histtype="step", color=sty["color"], ls=sty["linestyle"], lw=1.3, label=LEAKS[k.split("/")[1]])
    ax.axvline(0, color="0.5", lw=0.6)
    ax.set_xlabel("bias of the AUC estimate in one repetition (estimate minus reference)")
    ax.set_ylabel("repetitions")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-bias-distribution")


def fig_gate_matrix() -> None:
    m = load("e2_matrix.json")["pass_rates"]
    keys = list(m)
    cols = ["G1", "G2", "G3", "any"]
    M = np.array([[1 - m[k]["G1"], 1 - m[k]["G2"], 1 - m[k]["G3"], m[k]["any_gate_fails"]] for k in keys])
    fig, ax = plt.subplots(figsize=(5.4, 6.0))
    ax.imshow(M, cmap="Greys", vmin=0, vmax=1.15, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{100 * M[i, j]:.0f}", ha="center", va="center", fontsize=7, color="white" if M[i, j] > 0.55 else "black")
    ax.set_xticks(range(4))
    ax.set_xticklabels(["G1", "G2", "G3", "any gate"])
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([("WoE: " if k.startswith("woe") else "logit: ") + LEAKS[k.split("/")[1]] for k in keys], fontsize=7)
    ax.set_title("detection rate (%) by gate")
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-gate-matrix")


def fig_planted() -> None:
    d = load("e3_planted_leak.json")["levels"]
    s = np.array([float(k) for k in d])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))
    ax = axes[0]
    grid = np.linspace(0, 3, 100)
    from scipy.stats import norm
    ax.plot(grid, norm.cdf((1 + grid) / 2), color="0.1", lw=1.0, label="development, Proposition 4")
    ax.plot(grid, np.full_like(grid, norm.cdf(0.5)), color="0.4", ls="--", lw=1.0, label="decision time, Proposition 4")
    ax.errorbar(s, [d[k]["dev_auc"]["mean"] for k in d], yerr=[1.96 * d[k]["dev_auc"]["se"] for k in d], fmt="o", color="0.1", ms=3.5, capsize=2)
    ax.errorbar(s, [d[k]["cur_auc"]["mean"] for k in d], yerr=[1.96 * d[k]["cur_auc"]["se"] for k in d], fmt="s", color="0.4", ms=3.5, capsize=2)
    ax.set_xlabel("leak s (shift of the feature for defaulters in development)")
    ax.set_ylabel("AUC of the model score")
    ax.legend(frameon=False, loc="center right", fontsize=7)
    ax = axes[1]
    for sty, (k, lab) in zip(ST, (("auc_test", "AUC against development"), ("csi_test", "CSI of the leaked feature"),
                                  ("resemblance_flag", "resemblance AUC"), ("single_feature_flag", "single-feature AUC screen"))):
        r = np.array([d[x][k]["rate"] for x in d])
        lo = np.array([d[x][k]["lo"] for x in d])
        hi = np.array([d[x][k]["hi"] for x in d])
        ax.errorbar(s, r, yerr=[np.maximum(r - lo, 0), np.maximum(hi - r, 0)], color=sty["color"], ls=sty["linestyle"], marker=sty["marker"], ms=3.5, capsize=2, lw=1.0, label=lab)
    ax.axhline(0.05, color="0.6", lw=0.6)
    ax.set_xlabel("leak s")
    ax.set_ylabel("rejection rate at 5%")
    ax.legend(frameon=False, fontsize=7, loc="center right")
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-planted-leak")


def fig_draws() -> None:
    dr = load("e2_draws.json")["detection_by_draws"]
    th = load("theory_checks.json")["detection"]["by_m"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
    ax = axes[0]
    R = np.array([1, 2, 3, 5])
    for sty, (m, K, lab) in zip(ST, (("woe", 8, "WoE scorecard, K = 8"), ("linear", 2, "standardised logit, K = 2"))):
        ax.plot(R, [dr[m][str(r)] for r in R], color=sty["color"], ls="none", marker=sty["marker"], ms=4, label=lab + " (simulated)")
        grid = np.linspace(1, 5, 50)
        ax.plot(grid, 1 - K ** (-grid), color=sty["color"], ls=sty["linestyle"], lw=0.9)
    ax.set_xlabel("independent perturbation draws of the gate")
    ax.set_ylabel("detection of the choice made on the holdout")
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    ax.set_ylim(0.4, 1.02)
    ax = axes[1]
    ms = np.array([int(k) for k in th])
    ex = np.array([th[k]["exact"] for k in th])
    sim = np.array([th[k]["simulated"] for k in th])
    ax.semilogy(ms, 1 - ex, color="0.1", ls="-", lw=1.0, label="exact miss probability")
    ax.semilogy(ms, np.maximum(1 - sim, 3e-5), color="0.3", ls="none", marker="o", ms=4, label="simulated (floor at 3e-5)")
    ax.semilogy(ms, 0.1 ** ms, color="0.5", ls="--", lw=0.9, label="$0.1^m$")
    ax.set_xlabel("outside rows moved beyond the training range, m")
    ax.set_ylabel("probability that the gate misses a bin-edge leak")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-detection-draws")


def fig_cv() -> None:
    d = load("e5_cv_scaling.json")
    cells = d["cells"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
    ax = axes[0]
    a = sorted([c for c in cells if c["p"] == 40], key=lambda c: c["n"])
    n = np.array([c["n"] for c in a])
    for sty, k, lab in ((ST[0], "outside", "preprocessing before the folds"), (ST[1], "inside", "preprocessing inside the folds")):
        b = np.array([c[k]["bias"] for c in a])
        e = np.array([1.96 * c[k]["se"] for c in a])
        ax.errorbar(n, b, yerr=e, color=sty["color"], ls=sty["linestyle"], marker=sty["marker"], ms=3.5, capsize=2, lw=1.0, label=lab)
    f = d["loglog_fit_p40"]
    ax.plot(n, math.exp(f["intercept"]) * n.astype(float) ** f["exponent"], color="0.6", lw=0.8, ls=":")
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=0.005)
    ax.set_xticks(n)
    ax.set_xticklabels([f"{v:,}" for v in n], fontsize=7)
    ax.minorticks_off()
    ax.set_xlabel("development rows (40 inputs)")
    ax.set_ylabel("bias of the cross-validated AUC")
    ax.legend(frameon=False, fontsize=7)
    ax = axes[1]
    b2 = sorted([c for c in cells if c["n"] == 1600], key=lambda c: c["p"])
    p = np.array([c["p"] for c in b2])
    for sty, k in ((ST[0], "outside"), (ST[1], "inside")):
        ax.errorbar(p, [c[k]["bias"] for c in b2], yerr=[1.96 * c[k]["se"] for c in b2], color=sty["color"], ls=sty["linestyle"],
                    marker=sty["marker"], ms=3.5, capsize=2, lw=1.0)
    ax.set_xscale("log")
    ax.set_xlabel("inputs (1,600 development rows)")
    ax.set_ylabel("bias of the cross-validated AUC")
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-cv-scaling")


def fig_oot() -> None:
    d = load("e4_out_of_time.json")["cohorts"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))
    x = np.arange(len(d))
    ax = axes[0]
    for sty, (rid, lab) in zip(ST, (("P1-scorecard", "scorecard"), ("P4-lightgbm", "gradient boosting"))):
        ax.plot(x, [100 * c["rungs"][rid]["random_gap"] for c in d], color=sty["color"], ls="none", marker=sty["marker"], ms=5,
                fillstyle="none", label=f"{lab}, random split")
        ax.plot(x, [100 * c["rungs"][rid]["oot_gap"] for c in d], color=sty["color"], ls=sty["linestyle"], marker=sty["marker"], ms=4,
                label=f"{lab}, out of time")
    ax.axhline(0, color="0.6", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([c["cohort"].replace("FY", "") for c in d], rotation=25)
    ax.set_ylabel("observed minus predicted 5-year rate (points)")
    ax.legend(frameon=False, fontsize=7)
    ax = axes[1]
    for sty, (rid, lab) in zip(ST, (("P1-scorecard", "scorecard"), ("P4-lightgbm", "gradient boosting"))):
        ax.plot(x, [c["rungs"][rid]["random_auc"] for c in d], color=sty["color"], ls="none", marker=sty["marker"], ms=5, fillstyle="none")
        ax.plot(x, [c["rungs"][rid]["oot_auc"] for c in d], color=sty["color"], ls=sty["linestyle"], marker=sty["marker"], ms=4)
    ax.set_xticks(x)
    ax.set_xticklabels([c["cohort"].replace("FY", "") for c in d], rotation=25)
    ax.set_ylabel("AUC (open markers: random split)")
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-out-of-time")


def fig_protocol() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    def box(x, y, w, h, text, fc="0.93", fs=7.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.0", fc=fc, ec="0.2", lw=0.8))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)

    box(1, 36, 17, 9, "case data\n(one snapshot or\ndated cohorts)")
    box(24, 40, 20, 8, "locked holdout H\n(stratified, opened once)", fc="0.8")
    box(24, 30, 20, 8, "calibration slice C\n(disjoint from H)", fc="0.88")
    box(24, 20, 20, 8, "training slice T\n(+ folds inside T)", fc="0.97")
    box(24, 8, 20, 8, "out-of-time cohort\n(dated cases only)", fc="0.8")
    box(52, 20, 22, 8, "fit: impute, scale, bin,\nWoE, screen, choose,\nlogit (rows read: T)")
    box(52, 30, 22, 8, "calibration map\n(rows read: C)")
    box(52, 40, 22, 8, "estimate on H;\ntest on the cohort")
    box(81, 30, 18, 8, "G1: transforms\nunchanged when inputs\noutside T move", fc="0.85", fs=6.5)
    box(81, 20, 18, 8, "G2: slices disjoint;\nmap unchanged when\nH labels flip", fc="0.85", fs=6.5)
    box(81, 10, 18, 8, "G3: every parameter\nunchanged when H\nis perturbed", fc="0.85", fs=6.5)
    box(52, 8, 22, 8, "record: split sizes,\nseed, limits (no\nout-of-time claim)")
    for (x0, y0, x1, y1) in ((18, 41, 24, 44), (18, 40, 24, 34), (18, 38, 24, 24), (18, 37, 24, 12), (44, 24, 52, 24), (44, 34, 52, 34),
                             (44, 44, 52, 44), (74, 24, 81, 24), (74, 34, 81, 34), (74, 42, 81, 15)):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", lw=0.7, color="0.2"))
    fig.tight_layout()
    figkit.save(fig, OUT, "fig-protocol")


def main() -> None:
    for f in (fig_protocol, fig_bias_by_leak, fig_coverage, fig_bias_distribution, fig_gate_matrix, fig_planted, fig_draws, fig_cv, fig_oot):
        f()
        print("ok", f.__name__)


if __name__ == "__main__":
    main()
