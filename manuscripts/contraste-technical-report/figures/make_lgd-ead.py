"""Figures of the section 'Methods: loss given default and exposure at default' of the technical report.

Reads the committed documents of cases C08 and C09 (``data/derived``) through ``figkit`` and writes vector PDFs into
``figures/``: ``lgd-ead-distribution``, ``lgd-ead-rmse``, ``lgd-ead-reliability``, ``lgd-ead-ccf-bias`` and ``lgd-ead-ead-bands``.
Nothing is drawn from a number typed here: the thresholds of the back-test lights are read from the test row's own
``extras.thresholds``.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_lgd-ead.py
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

figkit.style()
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COHORTS = ["2003-06", "2007-08", "2009-10", "2011-13", "2014-19", "2020-23"]
REF = "2009-10"
RUNG_NAME = {
    "L1-ols": "OLS", "L2-fractional-logit": "Fractional logit", "L3-beta": "Beta regression", "L4-hurdle": "Hurdle",
    "L5-gradient-boosted": "Gradient boosting", "L6-tobit": "Tobit", "L7-random-forest": "Random forest",
    "L8-neural-network": "Neural network",
}
#: eight series need two more styles than the kit's six (still distinguishable in grayscale by marker and dash)
STYLES8 = figkit.STYLES + [
    {"color": "0.3", "linestyle": (0, (3, 1, 1, 1, 1, 1)), "marker": "*"},
    {"color": "0.5", "linestyle": (0, (6, 2)), "marker": "P"},
]
C08 = {c: figkit.doc(f"C08/dc-{c}.json") for c in COHORTS}
C09 = {lv: figkit.doc(f"C09/level-{lv}.json") for lv in range(6)}


def fig_distribution() -> None:
    d = C08[REF]["outputs"]["lgd_distribution"]
    edges = [b["lower"] for b in d["bins"]] + [d["bins"][-1]["upper"]]
    share = [100.0 * b["share"] for b in d["bins"]]
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    ax.bar([(edges[i] + edges[i + 1]) / 2 for i in range(len(share))], share, width=0.09, color="0.55", edgecolor="0.1", linewidth=0.5)
    ax.set_xlabel("Loss given default proxy (charge-off over approval)")
    ax.set_ylabel("Share of the cohort defaults (%)")
    ax.set_xlim(0, 1)
    ax.annotate(f"mass at exactly 1: {100.0 * d['mass_at_one']['share']:.1f}%\nabove 1: {100.0 * d['share_above_one']:.1f}%",
                xy=(0.55, 40.0), fontsize=8, ha="left", va="top")
    ax.grid(axis="y", linewidth=0.3, color="0.8")
    figkit.save(fig, HERE, "lgd-ead-distribution")


def fig_rmse() -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.3))
    x = np.arange(len(COHORTS))
    base = {c: {r["rung_id"]: r["rmse"] for r in C08[c]["outputs"]["rung_comparison"]} for c in COHORTS}
    for k, rid in enumerate(RUNG_NAME):
        # the RMSE of each rung minus that of the fractional logit, the rung the case page uses as reference
        y = [base[c][rid] - base[c]["L2-fractional-logit"] for c in COHORTS]
        ax.plot(x, y, label=RUNG_NAME[rid], **STYLES8[k])
    ax.axhline(0.0, color="0.7", linewidth=0.5)
    ax.set_xticks(x, [c.replace("-", "\u2013") for c in COHORTS])
    ax.set_xlabel("Test default cohort")
    ax.set_ylabel("RMSE minus RMSE of the fractional logit")
    ax.legend(ncol=2, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    ax.grid(axis="y", linewidth=0.3, color="0.85")
    figkit.save(fig, HERE, "lgd-ead-rmse")


def fig_reliability() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.0), sharey=True)
    rungs = ["L2-fractional-logit", "L5-gradient-boosted", "L7-random-forest", "L8-neural-network"]
    for ax, cid in zip(axes, ("2009-10", "2014-19")):
        buckets = C08[cid]["outputs"]["calibration_by_bucket"]
        for k, rid in enumerate(rungs):
            b = [x for x in buckets if x["rung_id"] == rid]
            ax.plot([x["predicted"]["value"] for x in b], [x["realised"]["value"] for x in b], label=RUNG_NAME[rid], **figkit.STYLES[k])
        lo = min(min(x["predicted"]["value"], x["realised"]["value"]) for x in buckets if x["rung_id"] in rungs)
        hi = max(max(x["predicted"]["value"], x["realised"]["value"]) for x in buckets if x["rung_id"] in rungs)
        ax.plot([lo, hi], [lo, hi], color="0.75", linewidth=0.7, zorder=0)
        ax.set_title(f"Test cohort {cid.replace('-', chr(0x2013))}")
        ax.set_xlabel("Mean predicted LGD of the bucket")
        ax.grid(linewidth=0.3, color="0.88")
    axes[0].set_ylabel("Mean realised LGD of the bucket")
    axes[1].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    figkit.save(fig, HERE, "lgd-ead-reliability")


def ccf_series(design: str, treatment: str, agg: str) -> tuple[list[float], list[float]]:
    bias, half = [], []
    for lv in range(6):
        r = next(r for r in C09[lv]["outputs"]["ccf_by_design"]["rows"]
                 if r["design"] == design and r["treatment"] == treatment and r["estimator"] == agg)
        bias.append(r["bias"])
        half.append((r["ci_high"] - r["ci_low"]) / 2)
    return bias, half


def fig_ccf_bias() -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.3))
    tol = C09[3]["outputs"]["ccf_by_design"]["tolerance"]
    x = np.arange(6)
    series = [("fixed-horizon", "none", "mean", "Fixed horizon, untreated, mean"),
              ("fixed-horizon", "none", "pooled", "Fixed horizon, untreated, pooled"),
              ("fixed-horizon", "bounded-scale", "mean", "Fixed horizon, bounded scale"),
              ("cohort", "none", "pooled", "Cohort, untreated, pooled"),
              ("variable-horizon", "none", "pooled", "Variable horizon, untreated, pooled")]
    for k, (d, t, a, name) in enumerate(series):
        b, h = ccf_series(d, t, a)
        ax.errorbar(x + 0.04 * (k - 2), b, yerr=h, capsize=2, label=name, elinewidth=0.7, **figkit.STYLES[k])
    ax.axhspan(-tol, tol, color="0.9", zorder=0)
    ax.axhline(0.0, color="0.6", linewidth=0.5)
    ax.set_xticks(x, [f"{lv}\n({C09[lv]['outputs']['generator']['true_ccf']['value']:.3f})" for lv in range(6)])
    ax.set_xlabel("Acceleration level (known CCF at 12 months)")
    ax.set_ylabel("Bias against the known CCF")
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    ax.grid(axis="y", linewidth=0.3, color="0.85")
    figkit.save(fig, HERE, "lgd-ead-ccf-bias")


def fig_ead_bands() -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.3))
    d0 = C09[3]["outputs"]["ead_backtest"]
    edges = d0["bands"]
    models = [("ccf-fixed-horizon-floor-cap", "Fixed-horizon CCF, floor and cap"), ("direct-ead", "Direct EAD"),
              ("utilisation-change", "Utilisation change"), ("ccf-cohort-floor-cap", "Cohort CCF, floor and cap")]
    for k, (mid, name) in enumerate(models):
        rows = [r for r in d0["rows"] if r["model_id"] == mid]
        ax.plot([int(r["band_id"][1:]) for r in rows], [r["relative_gap"] for r in rows], label=name, **figkit.STYLES[k])
    th = next(t for t in C09[3]["tests"] if t["test_id"] == "lgd_ead.ead_backtest_by_band")["extras"]["thresholds"]
    for g, ls in ((th["gap_amber"], "--"), (th["gap_red"], ":")):
        ax.axhline(g, color="0.6", linewidth=0.6, linestyle=ls)
        ax.axhline(-g, color="0.6", linewidth=0.6, linestyle=ls)
    ax.axhline(0.0, color="0.4", linewidth=0.5)
    ax.set_xticks(range(1, len(edges)), [f"{edges[i]:g}\u2013{edges[i + 1]:g}" for i in range(len(edges) - 1)], fontsize=7)
    ax.set_xlabel("Utilisation band at the reference date (drawn over limit)")
    ax.set_ylabel("Relative gap of predicted against realised EAD")
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    ax.grid(axis="y", linewidth=0.3, color="0.85")
    figkit.save(fig, HERE, "lgd-ead-ead-bands")


def main() -> None:
    fig_distribution()
    fig_rmse()
    fig_reliability()
    fig_ccf_bias()
    fig_ead_bands()
    print("wrote", ", ".join(sorted(p.name for p in HERE.glob("lgd-ead-*.pdf"))))


if __name__ == "__main__":
    main()
