"""Figures of the credit-scoring section (sections/06-credit-scoring.tex), vector PDF into ``figures/credit-scoring-*.pdf``,
drawn from the committed artifacts under ``data/derived`` (cases C01, C02 and C03) through ``figkit``.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_credit-scoring.py

The derived numbers come from ``tables/make_credit-scoring.py`` (``derive``), so the tables and the figures read the same values.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

_spec = importlib.util.spec_from_file_location("cs_tables", HERE.parent / "tables" / "make_credit-scoring.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

S = figkit.STYLES
OUT = HERE
FIG1 = (6.4, 3.0)


def _plt():
    figkit.style()
    import matplotlib.pyplot as plt

    return plt


def legend_below(a, ncol: int = 3, y: float = -0.25, fs: float = 7) -> None:
    """A legend under the axes, so that it never covers a curve."""
    a.legend(loc="upper center", bbox_to_anchor=(0.5, y), frameon=False, ncol=ncol, fontsize=fs)


def style_for(i: int) -> dict:
    return dict(S[i % len(S)])


def fig_roc(D: dict) -> None:
    plt = _plt()
    rungs = D["raw_c01"]["holdout"]["outputs"]["rungs"]
    order = ["P0-single", "P1-scorecard", "P2b-pltr", "P3-ebm", "P4-lightgbm"]
    grid = np.linspace(0, 1, 201)
    fig, ax = plt.subplots(1, 2, figsize=(6.4, 3.3))
    base = None
    for i, rid in enumerate(order):
        roc = rungs[rid]["roc"]
        tpr = np.interp(grid, roc["fpr"], roc["tpr"])
        if rid == "P1-scorecard":
            base = tpr
        ax[0].plot(grid, tpr, label=cs.NAME[rid], **{k: v for k, v in style_for(i).items() if k != "marker"})
    ax[0].plot([0, 1], [0, 1], color="0.75", linewidth=0.6)
    ax[0].set_xlabel("False positive rate")
    ax[0].set_ylabel("True positive rate")
    ax[0].set_title("(a) ROC curves, Taiwan holdout")
    legend_below(ax[0], ncol=3, y=-0.22, fs=6.5)
    for i, rid in enumerate(order):
        if rid == "P1-scorecard":
            continue
        roc = rungs[rid]["roc"]
        ax[1].plot(grid, np.interp(grid, roc["fpr"], roc["tpr"]) - base, label=cs.NAME[rid],
                   **{k: v for k, v in style_for(i).items() if k != "marker"})
    ax[1].axhline(0, color="0.75", linewidth=0.6)
    ax[1].set_xlabel("False positive rate")
    ax[1].set_ylabel("True positive rate minus scorecard")
    ax[1].set_title("(b) Gain over the scorecard")
    fig.tight_layout()
    figkit.save(fig, OUT, "credit-scoring-roc")


def fig_reliability(D: dict) -> None:
    plt = _plt()
    rungs = D["raw_c01"]["holdout"]["outputs"]["rungs"]
    fig, ax = plt.subplots(1, 3, figsize=(6.6, 2.9), sharex=True, sharey=True)
    panels = [("P1-scorecard", "Scorecard", False), ("P3-ebm", "EBM", True), ("P4-lightgbm", "LightGBM", True)]
    for a, (rid, title, has_raw) in zip(ax, panels):
        a.plot([0, 0.6], [0, 0.6], color="0.75", linewidth=0.6)
        cal = rungs[rid]["reliability"]
        a.plot([b["pd"] for b in cal], [b["dr"] for b in cal], label="after isotonic map" if has_raw else "fitted PD",
               **style_for(0))
        if has_raw:
            raw = rungs[rid]["reliability_raw"]
            a.plot([b["pd"] for b in raw], [b["dr"] for b in raw], label="raw", **style_for(1))
        a.set_title(title)
        a.set_xlabel("Mean predicted PD")
        legend_below(a, ncol=1, y=-0.28, fs=7)
    ax[0].set_ylabel("Observed default rate")
    fig.tight_layout()
    figkit.save(fig, OUT, "credit-scoring-reliability")


def fig_variants(D: dict) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ids = ["P1-scorecard", "P2b-pltr", "P3-ebm", "P4-lightgbm"]
    vs = cs.VARIANTS[:6]
    x = np.arange(len(vs))
    for i, rid in enumerate(ids):
        y = np.array([D["c01"][v][rid]["auc"] for v in vs])
        lo = np.array([D["c01"][v][rid]["lo"] for v in vs])
        hi = np.array([D["c01"][v][rid]["hi"] for v in vs])
        ax.errorbar(x + 0.07 * (i - 1.5), y, yerr=[y - lo, hi - y], capsize=2, label=cs.NAME[rid], **style_for(i))
    ax.set_xticks(x)
    ax.set_xticklabels([v.replace("\\%", "%") for v in (cs.VARIANT_LABEL[v] for v in vs)], rotation=20, ha="right")
    ax.set_ylabel("AUC with 95% DeLong interval")
    legend_below(ax, ncol=4, y=-0.42, fs=7)
    fig.tight_layout()
    figkit.save(fig, OUT, "credit-scoring-variants")


def fig_c02(D: dict) -> None:
    plt = _plt()
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 3.7))
    hs = cs.HORIZONS[:5]
    x = np.arange(1, 6)
    ids = ["P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm"]
    for i, rid in enumerate(ids):
        d = [D["c02"][h]["rungs"][rid]["discrimination"] for h in hs]
        y = np.array([k["auc"] for k in d])
        lo = np.array([k["auc_ci"]["lo"] for k in d])
        hi = np.array([k["auc_ci"]["hi"] for k in d])
        ax[0].errorbar(x + 0.06 * (i - 2), y, yerr=[y - lo, hi - y], capsize=2, label=cs.NAME[rid], **style_for(i))
    ax[0].set_xticks(x)
    ax[0].set_xlabel("Forecast horizon (years)")
    ax[0].set_ylabel("Holdout AUC")
    ax[0].set_title("(a) Discrimination")
    legend_below(ax[0], ncol=2, y=-0.22, fs=7)
    for i, rid in enumerate(cs.CHALLENGERS):
        c = [D["c02"][h]["chal"][rid] for h in hs]
        y = np.array([k["auc_diff"] for k in c])
        lo = np.array([k["auc_diff_ci"]["lo"] for k in c])
        hi = np.array([k["auc_diff_ci"]["hi"] for k in c])
        ax[1].errorbar(x + 0.07 * (i - 2), y, yerr=[y - lo, hi - y], capsize=2, label=cs.NAME[rid], **style_for(i + 1))
    ax[1].axhline(0, color="0.7", linewidth=0.6)
    ax[1].set_xticks(x)
    ax[1].set_xlabel("Forecast horizon (years)")
    ax[1].set_ylabel("AUC minus scorecard AUC")
    ax[1].set_title("(b) Paired DeLong difference")
    legend_below(ax[1], ncol=2, y=-0.22, fs=7)
    fig.tight_layout()
    figkit.save(fig, OUT, "credit-scoring-c02")


def fig_c03(D: dict) -> None:
    plt = _plt()
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 3.7))
    x = np.arange(len(cs.COHORTS))
    ids = ["P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm"]
    for i, rid in enumerate(ids):
        r = [D["c03"][c]["rungs"][rid] for c in cs.COHORTS]
        y = np.array([k["auc"] for k in r])
        lo = np.array([k["auc_ci_low"] for k in r])
        hi = np.array([k["auc_ci_high"] for k in r])
        ax[0].errorbar(x + 0.07 * (i - 2), y, yerr=[y - lo, hi - y], capsize=2, label=cs.NAME[rid], **style_for(i))
    ax[0].set_xticks(x)
    ax[0].set_xticklabels([cs.COHORT_LABEL[c].replace("--", "-") for c in cs.COHORTS], rotation=20, ha="right")
    ax[0].set_ylabel("AUC with 95% interval")
    ax[0].set_title("(a) Discrimination by cohort")
    legend_below(ax[0], ncol=2, y=-0.22, fs=7)
    fys, obs, pred = [], [], []
    for c in cs.COHORTS:
        for v in D["c03"][c]["vintages"]:
            fys.append(v["fiscal_year"])
            obs.append(100 * v["observed_5y_pd"])
            pred.append(100 * v["predicted_5y_pd"])
    ax[1].plot(fys, obs, label="observed 5-year charge-off rate", **style_for(0))
    ax[1].plot(fys, pred, label="scorecard mean PD", **style_for(1))
    from matplotlib.ticker import MaxNLocator

    ax[1].xaxis.set_major_locator(MaxNLocator(integer=True))
    ax[1].set_xlabel("Approval fiscal year")
    ax[1].set_ylabel("5-year PD (%)")
    ax[1].set_title("(b) Level by vintage")
    legend_below(ax[1], ncol=1, y=-0.25, fs=7)
    fig.tight_layout()
    figkit.save(fig, OUT, "credit-scoring-c03")


def fig_vintage(D: dict) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    want = [2007, 2008, 2010, 2013]
    i = 0
    for c in cs.COHORTS:
        for cur in D["c03"][c]["curves"]:
            if cur["fiscal_year"] in want:
                st = style_for(i)
                ax.plot(cur["months"], [100 * p for p in cur["observed_cumulative_pd"]], label=f"FY{cur['fiscal_year']} observed",
                        **st)
                ax.plot(cur["months"], [100 * p for p in cur["predicted_cumulative_pd"]], color=st["color"], linestyle=":",
                        marker=st["marker"], markerfacecolor="white", label=f"FY{cur['fiscal_year']} scorecard")
                i += 1
    ax.set_xlabel("Months since approval")
    ax.set_ylabel("Cumulative charge-off probability (%)")
    ax.set_xticks([12, 24, 36, 48, 60])
    legend_below(ax, ncol=2, y=-0.18, fs=7)
    fig.tight_layout()
    figkit.save(fig, OUT, "credit-scoring-vintage")


def fig_reject(D: dict) -> None:
    plt = _plt()
    R = D["reject"]
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 3.7))
    rungs = ["oracle", "accepted-only", "augmentation", "parcelling", "parcelling-prudent"]
    ks = [g["kappa"] for g in R["regimes"]]
    x = np.arange(len(ks))
    for i, rid in enumerate(rungs):
        b = [next(r for r in g["rungs"] if r["id"] == rid)["bias"] for g in R["regimes"]]
        y = np.array([100 * k["mean"] for k in b])
        lo = np.array([100 * k["lo"] for k in b])
        hi = np.array([100 * k["hi"] for k in b])
        ax[0].errorbar(x + 0.06 * (i - 2), y, yerr=[y - lo, hi - y], capsize=2, label=cs.REJECT_NAME[rid], **style_for(i))
        a = [next(r for r in g["rungs"] if r["id"] == rid)["auc"]["mean"] for g in R["regimes"]]
        ax[1].plot(x, a, label=cs.REJECT_NAME[rid], **style_for(i))
    ax[0].axhline(0, color="0.7", linewidth=0.6)
    for a_ in ax:
        a_.set_xticks(x)
        a_.set_xticklabels([f"{k:g}" for k in ks])
        a_.set_xlabel("Weight of the private signal $\\kappa$")
    ax[0].set_ylabel("Level bias (points of default rate)")
    ax[0].set_title("(a) Bias on the accept-all test set")
    ax[1].set_ylabel("AUC on the accept-all test set")
    ax[1].set_title("(b) Ranking")
    legend_below(ax[0], ncol=2, y=-0.22, fs=6.5)
    fig.tight_layout()
    figkit.save(fig, OUT, "credit-scoring-reject")


def fig_stability(D: dict) -> None:
    plt = _plt()
    fig, ax = plt.subplots(1, 2, figsize=(6.4, 3.3))
    fits = [("taiwan", "Taiwan 16,800"), ("taiwan-small", "Taiwan 2,000"), ("german", "German 560")]
    for i, (k, label) in enumerate(fits):
        j = D["fit"][k]["pl_jacc"]
        ax[0].plot(np.arange(1, len(j) + 1), j, label=label, **style_for(i))
        o = D["fit"][k]["reason"]["overlap"]
        ax[1].plot(np.arange(1, len(o) + 1), o, label=label, **style_for(i))
    ax[0].set_xlabel("Bootstrap resample")
    ax[0].set_ylabel("Jaccard index of the PLTR rule set")
    ax[0].set_title("(a) Rule-set stability")
    legend_below(ax[0], ncol=1, y=-0.22, fs=7)
    ax[1].set_xlabel("Bootstrap refit of LightGBM")
    ax[1].set_ylabel("Mean overlap of the top four reasons")
    ax[1].set_title("(b) Reason-code stability")
    ax[1].set_ylim(0.5, 1.0)
    fig.tight_layout()
    figkit.save(fig, OUT, "credit-scoring-stability")


def main() -> None:
    D = cs.derive()
    for fn in (fig_roc, fig_reliability, fig_variants, fig_c02, fig_c03, fig_vintage, fig_reject, fig_stability):
        fn(D)
    print(f"wrote 8 figures to {OUT}")


if __name__ == "__main__":
    main()
