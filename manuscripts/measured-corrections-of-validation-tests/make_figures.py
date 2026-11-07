"""Every figure of the manuscript, written as vector PDF to ``figures/`` from the experiment results and the committed documents,
through the style of ``manuscripts/_shared/figkit.py`` (readable in grayscale: line styles and markers, no colour needed).

Usage, from the repository root: python manuscripts/measured-corrections-of-validation-tests/make_figures.py
"""
from __future__ import annotations

import math

import numpy as np

import _data as D
import exp_coverage
import exp_shift
from _data import PAIRS, COVERAGE, EXACT, SHIFT, SITUATION, cov_cell, figkit, shift_cell, sit_cell

figkit.style()
import matplotlib.pyplot as plt  # noqa: E402

S = figkit.STYLES
NM = [{k: v for k, v in d.items() if k != "marker"} for d in S]  # the same line styles without a marker
OUT = D.FIGURES


def bar_errors(rates):
    return [r["se"] for r in rates]


def coverage_size() -> None:
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    curve = [c for c in EXACT["size_curves"] if c["n"] == 1000]
    x = [c["ratio"] for c in curve]
    ax.plot(x, [c["bin"] for c in curve], **NM[0], label="binomial, exact")
    ax.plot(x, [c["normal_approx_bin"] for c in curve], **NM[1], label="binomial, normal approximation")
    ax.plot(x, [c["bb"] for c in curve], **NM[2], label="Beta-Binomial, exact")
    ax.axhline(0.05, color="0.0", linewidth=0.6, linestyle=(0, (1, 2)))
    marks = {200: "o", 1000: "s", 5000: "^"}
    for n, mk in marks.items():
        cells = [c for c in COVERAGE["cells"] if c["n"] == n and c["b"] == 1.0 and 0.09 <= c["ratio"] <= 8.5]
        ax.errorbar([c["ratio"] for c in cells], [c["rates"]["bin"]["rate"] for c in cells], yerr=[2 * c["rates"]["bin"]["se"] for c in cells],
                    fmt=mk, color="0.0", markerfacecolor="white", markersize=4, linewidth=0.8, label=f"binomial, simulated, $n={n:,}$")
        ax.errorbar([c["ratio"] for c in cells], [c["rates"]["bb"]["rate"] for c in cells], yerr=[2 * c["rates"]["bb"]["se"] for c in cells],
                    fmt=mk, color="0.45", markersize=4, linewidth=0.8, label=f"Beta-Binomial, simulated, $n={n:,}$")
    ax.set_xscale("log")
    ax.set_xlabel("test window over calibration window, $m/n$ (dimensionless)")
    ax.set_ylabel("rejection rate at level 0.05 under exchangeability")
    ax.set_ylim(0, 0.62)
    ax.legend(ncol=2, fontsize=6.5, loc="upper left")
    figkit.save(fig, OUT, "coverage_size")


def coverage_power() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.3), sharey=True)
    for ax, tag in zip(axes, ("B", "C")):
        n, m = PAIRS[tag]
        curve = [c for c in EXACT["power_curves"] if c["n"] == n and c["m"] == m]
        loss = [0.9 - c["mean_coverage"] for c in curve]
        for st, key, lab in ((NM[0], "bin", "binomial"), (NM[1], "bb", "Beta-Binomial"), (NM[2], "bin_oracle", "binomial, size-calibrated")):
            ax.plot(loss, [c["power"][key] for c in curve], **st, label=lab)
        for b in exp_coverage.SHAPES:
            c = cov_cell(n, m, b)
            ax.errorbar([0.9 - c["mean_coverage"]] * 2, [c["rates"]["bin"]["rate"], c["rates"]["bb"]["rate"]], yerr=[2 * c["rates"]["bin"]["se"], 2 * c["rates"]["bb"]["se"]],
                        fmt="none", ecolor="0.2", linewidth=0.8)
            ax.plot([0.9 - c["mean_coverage"]], [c["rates"]["bb"]["rate"]], "o", color="0.0", markersize=3.5)
            ax.plot([0.9 - c["mean_coverage"]], [c["rates"]["bin"]["rate"]], "s", color="0.0", markerfacecolor="white", markersize=3.5)
        ax.axhline(0.05, color="0.0", linewidth=0.6, linestyle=(0, (1, 2)))
        ax.set_title(f"$n={n:,}$, $m={m:,}$", fontsize=8)
        ax.set_xlabel("coverage lost (0.90 minus mean)")
    axes[0].set_ylabel("rejection rate at level 0.05")
    axes[0].legend(fontsize=7, loc="lower right")
    figkit.save(fig, OUT, "coverage_power")


def rejection_regions() -> None:
    n, m = 1000, 1000
    t = exp_coverage.tables(n, m)
    c = np.arange(m + 1)
    share = c / m
    keep = (share > 0.84) & (share < 0.96)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.semilogy(share[keep], t["bin"][keep], **NM[0], label="binomial p-value")
    ax.semilogy(share[keep], np.maximum(t["bb"][keep], 1e-12), **NM[1], label="Beta-Binomial p-value")
    ax.axhline(0.05, color="0.0", linewidth=0.6, linestyle=(0, (1, 2)))
    ax.set_ylim(1e-6, 1.5)
    ax.set_xlabel("empirical coverage of the test window, $C/m$")
    ax.set_ylabel("two-sided p-value")
    ax.legend(loc="lower center", fontsize=7)
    figkit.save(fig, OUT, "rejection_regions")


def shift_drops() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.2), sharey=True)
    bins = np.linspace(-0.08, 0.5, 30)
    for ax, s, tone in zip(axes, (0.0, 2.0), ("0.55", "0.25")):
        c = shift_cell(500, s)
        ax.hist(c["drops"], bins=bins, color=tone, edgecolor="white", linewidth=0.3)
        for cut, ls in ((0.05, "--"), (0.10, "-.")):
            ax.axvline(cut, color="0.0", linewidth=0.9, linestyle=ls, label=f"fixed cut {cut:.2f}")
        ax.axvline(c["mean_null_mean"], color="0.0", linewidth=0.9, linestyle=":", label="mean of the reference")
        ax.set_title(f"shift {s:g} ({c['n']} replications)", fontsize=8)
        ax.set_xlabel("AUC drop on the worst quarter")
    axes[0].set_ylabel("replications")
    axes[0].legend(fontsize=6.5)
    figkit.save(fig, OUT, "shift_drops")


def shift_eval_size() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.3), sharey=False)
    rules = (("fixed_0.05", "fixed 0.05"), ("fixed_0.10", "fixed 0.10"), ("z_rule", "variance z rule"), ("perm_199", "permutation, 199 draws"))
    x = exp_shift.EVAL_SIZES
    for ax, s, title in zip(axes, (0.0, 2.0), ("size (no shift)", "power (shift 2)")):
        for st, (rule, lab) in zip(S, rules):
            rs = [shift_cell(e, s)["rules"][rule] for e in x]
            ax.errorbar(x, [r["rate"] for r in rs], yerr=[2 * r["se"] for r in rs], capsize=2, label=lab, **st)
        if s == 0.0:
            ax.axhline(0.05, color="0.0", linewidth=0.6, linestyle=(0, (1, 2)))
        ax.set_xscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([str(e) for e in x])
        ax.minorticks_off()
        ax.set_xlabel("evaluation rows")
        ax.set_title(title, fontsize=8)
    axes[0].set_ylabel("rejection rate")
    axes[1].legend(fontsize=6.5, loc="lower right")
    figkit.save(fig, OUT, "shift_eval_size")


def shift_draws() -> None:
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    draws = exp_shift.DRAW_GRID
    for st, s in zip(S, (0.0, 1.0, 2.0, 3.0)):
        rs = [shift_cell(500, s)["rules"][f"perm_{r}"] for r in draws]
        ax.errorbar(draws, [r["rate"] for r in rs], yerr=[2 * r["se"] for r in rs], capsize=2, label=f"shift {s:g}", **st)
    ax.axhline(0.05, color="0.0", linewidth=0.6, linestyle=(0, (1, 2)))
    ax.set_xscale("log")
    ax.set_xticks(draws)
    ax.set_xticklabels([str(r) for r in draws])
    ax.minorticks_off()
    ax.set_xlabel("permutation draws of the reference, $R$")
    ax.set_ylabel("rejection rate at level 0.05")
    ax.legend(fontsize=7)
    figkit.save(fig, OUT, "shift_draws")


def situation_cuts() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.3), sharey=True)
    cuts = exp_situation_cuts()
    for ax, n in zip(axes, (400, 1000)):
        for st, g in zip(S, (0.0, 0.1, 0.2, 0.4, 0.8)):
            c = sit_cell(n, g)
            ax.plot(cuts, [c["rules"][f"cut_{k:g}"]["rate"] for k in cuts], label=f"gap {g:g}", **st)
        ax.axvline(0.20, color="0.0", linewidth=0.6, linestyle=(0, (1, 2)))
        ax.axhline(0.05, color="0.0", linewidth=0.6, linestyle=(0, (1, 2)))
        ax.set_title(f"{n:,} applicants", fontsize=8)
        ax.set_xlabel("amber cut on the share")
    axes[0].set_ylabel("rejection rate")
    axes[0].legend(fontsize=6.5)
    figkit.save(fig, OUT, "situation_cuts")


def exp_situation_cuts():
    import exp_situation

    return list(exp_situation.CUTS)


def situation_null_share() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.2), sharey=False)
    bins = np.linspace(0, 0.4, 41)
    for ax, n, tone in zip(axes, (400, 1000), ("0.55", "0.3")):
        c = sit_cell(n, 0.0)
        ax.hist(c["shares"], bins=bins, color=tone, edgecolor="white", linewidth=0.3)
        for cut, ls in ((0.10, "--"), (0.20, "-.")):
            ax.axvline(cut, color="0.0", linewidth=0.9, linestyle=ls, label=f"cut {cut:.2f}")
        ax.set_title(f"{n:,} applicants, gap 0 ({c['reps']:,} replications)", fontsize=8)
        ax.set_xlabel("share of significant complainants")
    axes[0].set_ylabel("replications")
    axes[0].legend(fontsize=7)
    figkit.save(fig, OUT, "situation_null_share")


def committed_p() -> None:
    fed = D.jload(figkit.ROOT / "data" / "derived" / "C20" / "fed-shift.json")
    rows = [t for t in fed["tests"] if t["test_id"] == "ml.conformal_coverage"]
    names = [t["segment"].replace("window:", "").replace("fed-higher-risk-", "higher risk ") for t in rows]
    bb = [-math.log10(t["p_value"]) for t in rows]
    bi = [-math.log10(t["extras"]["p_value_binomial"]) for t in rows]
    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(6.2, 3.1))
    ax.barh(y - 0.2, bb, height=0.4, color="0.25", label="Beta-Binomial (sets the light)")
    ax.barh(y + 0.2, bi, height=0.4, color="0.7", label="binomial (shown beside it)")
    for x0, ls in ((-math.log10(0.05), "--"), (-math.log10(0.01), "-.")):
        ax.axvline(x0, color="0.0", linewidth=0.8, linestyle=ls)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("$-\\log_{10}$ of the p-value (dashed: 0.05, dash-dotted: 0.01)")
    ax.legend(fontsize=7, loc="lower right")
    figkit.save(fig, OUT, "committed_p")


def main() -> None:
    for fn in (coverage_size, coverage_power, rejection_regions, shift_drops, shift_eval_size, shift_draws, situation_cuts, situation_null_share, committed_p):
        fn()
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
