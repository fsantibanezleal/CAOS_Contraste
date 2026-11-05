"""Figures of the validation-tests section of the technical report (sections/16-validation-tests.tex).

Every figure is a vector PDF drawn from the committed documents of cases C20, C21 and C22 (``data/derived``) through
``figkit``; the helpers that read them are those of ``tables/make_validation-tests.py``. Output: ``figures/validation-tests-*.pdf``.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_validation-tests.py
"""
from __future__ import annotations

import importlib.util
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

_spec = importlib.util.spec_from_file_location("vt_tables", HERE.parent / "tables" / "make_validation-tests.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)  # type: ignore[union-attr]

W = 6.3  # text width in inches


def series(idx: dict, test: str, keys: list[str]) -> tuple[list[float], list[float], list[float]]:
    xs, ys, se = [], [], []
    for k in keys:
        s = idx[f"{test}@{k}"]
        xs.append(s["x"])
        ys.append(T.r05(s)["rate"])
        se.append(T.r05(s)["se"])
    return xs, ys, se


def fig_published(out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    G = T.golden_cells()
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.1))
    wp = G["bcbs-wp14"]["cells"]
    for kind, mk in (("normal", "o"), ("traffic", "s")):
        c = [x for x in wp if kind in x["row"] and x["agrees"]]
        axes[0].plot([x["published"] for x in c], [x["measured"] for x in c], mk, color="0.25", markersize=3,
                     label="normal test" if kind == "normal" else "traffic-lights test")
    bad = [x for x in wp if not x["agrees"]]
    axes[0].plot([x["published"] for x in bad], [x["measured"] for x in bad], "D", mfc="none", mec="0.0", markersize=7, label="outside 3.29 SE")
    axes[0].plot([0, 1], [0, 1], "-", color="0.6", linewidth=0.7)
    axes[0].set_xlabel("rate printed in WP14 Tables 7 and 8")
    axes[0].set_ylabel("rate of the rerun")
    axes[0].set_title(f"WP14, {G['bcbs-wp14']['agree']} of {G['bcbs-wp14']['total']} cells agree", fontsize=8)
    axes[0].legend(frameon=False, loc="lower right")
    yn = G["yurdakul-naranjo-2020"]["cells"]
    for rule, mk in (("PSI > 0.10", "o"), ("PSI > 0.25", "s"), ("chi-square", "^")):
        c = [x for x in yn if x["column"].endswith(rule) and x["agrees"]]
        axes[1].plot([x["published"] for x in c], [x["measured"] for x in c], mk, color="0.25", markersize=3, label=rule)
    bad = [x for x in yn if not x["agrees"]]
    axes[1].plot([x["published"] for x in bad], [x["measured"] for x in bad], "D", mfc="none", mec="0.0", markersize=7, label="outside 3.29 SE")
    axes[1].plot([0, 1], [0, 1], "-", color="0.6", linewidth=0.7)
    axes[1].set_xlabel("rate printed in Yurdakul and Naranjo Table 4")
    axes[1].set_title(f"Yurdakul and Naranjo, {G['yurdakul-naranjo-2020']['agree']} of {G['yurdakul-naranjo-2020']['total']} cells agree", fontsize=8)
    axes[1].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    figkit.save(fig, out, "validation-tests-published")


def fig_clustering(out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    idx = T.sim_index(T.c22("clustering"))
    ks = ["rho0", "rho0.02", "rho0.05", "rho0.1", "rho0.15", "rho0.2"]
    rho = [idx[f"pd.binomial@{k}"]["x"] for k in ks]
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.0), sharey=True)
    ax = axes[0]
    for i, t in enumerate(("pd.binomial", "pd.jeffreys", "pd.binomial_vasicek")):
        ys = [T.r05(idx[f"{t}@{k}"])["rate"] for k in ks]
        se = [T.r05(idx[f"{t}@{k}"])["se"] for k in ks]
        ax.errorbar(rho, ys, yerr=[1.96 * s for s in se], capsize=2, label=T.TEST_LABEL[t], **figkit.STYLES[i])
    ex = [idx[f"pd.binomial@{k}"]["exact"]["p<0.05"] for k in ks]
    ax.plot(rho, ex, "-", color="0.0", linewidth=0.6, label="binomial, exact")
    ax.axhline(0.05, color="0.6", linewidth=0.6, linestyle=":")
    ax.set_xlabel("asset correlation of the generator")
    ax.set_ylabel("rejection rate at the 5% level")
    ax.set_title("tests on one default count", fontsize=8)
    ax.legend(frameon=False)
    ax = axes[1]
    for i, t in enumerate(("pd.chi2_grades", "pd.hosmer_lemeshow", "pd.spiegelhalter", "pd.normal_multiperiod", "pd.traffic_lights")):
        ys = [T.r05(idx[f"{t}@{k}"])["rate"] for k in ks]
        se = [T.r05(idx[f"{t}@{k}"])["se"] for k in ks]
        ax.errorbar(rho, ys, yerr=[1.96 * s for s in se], capsize=2, label=T.TEST_LABEL[t], **figkit.STYLES[i])
    ax.axhline(0.05, color="0.6", linewidth=0.6, linestyle=":")
    ax.set_xlabel("asset correlation of the generator")
    ax.set_title("tests on grades, obligors and years", fontsize=8)
    ax.legend(frameon=False)
    fig.tight_layout()
    figkit.save(fig, out, "validation-tests-clustering")


def fig_power(out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    idx = T.sim_index(T.c22("miscalibration"))
    ks = ["k1", "k1.1", "k1.25", "k1.5", "k2", "k3"]
    tests = ("pd.binomial", "pd.jeffreys", "pd.chi2_grades", "pd.hosmer_lemeshow", "pd.spiegelhalter", "pd.normal_multiperiod")
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.0), sharey=True)
    for i, t in enumerate(tests):
        x, y, se = series(idx, t, ks)
        axes[0].errorbar(x, y, yerr=[1.96 * s for s in se], capsize=2, label=T.TEST_LABEL[t], **figkit.STYLES[i])
    axes[0].set_xscale("log")
    axes[0].set_xticks([1, 1.1, 1.25, 1.5, 2, 3])
    axes[0].set_xticklabels(["1", "1.1", "1.25", "1.5", "2", "3"])
    axes[0].set_xlabel("factor on the probability applied")
    axes[0].set_ylabel("rejection rate at the 5% level")
    axes[0].axhline(0.05, color="0.6", linewidth=0.6, linestyle=":")
    axes[0].legend(frameon=False, loc="center right")
    axes[0].set_title("tests that assume independent defaults", fontsize=8)
    for i, t in enumerate(("pd.binomial_vasicek", "pd.traffic_lights", "pd.default_profile")):
        x, y, se = series(idx, t, ks)
        axes[1].errorbar(x, y, yerr=[1.96 * s for s in se], capsize=2, label=T.TEST_LABEL[t], **figkit.STYLES[i])
    ex = [idx[f"pd.traffic_lights@{k}"]["exact"]["p<0.05"] for k in ks]
    axes[1].plot([idx[f"pd.traffic_lights@{k}"]["x"] for k in ks], ex, "-", color="0.55", linewidth=0.6, label="traffic lights, exact")
    axes[1].set_xscale("log")
    axes[1].set_xticks([1, 1.1, 1.25, 1.5, 2, 3])
    axes[1].set_xticklabels(["1", "1.1", "1.25", "1.5", "2", "3"])
    axes[1].set_xlabel("factor on the probability applied")
    axes[1].axhline(0.05, color="0.6", linewidth=0.6, linestyle=":")
    axes[1].legend(frameon=False, loc="center right")
    axes[1].set_title("correlation-aware and shape tests", fontsize=8)
    fig.tight_layout()
    figkit.save(fig, out, "validation-tests-power")


def fig_drift(out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    idx = T.sim_index(T.c22("drift"))
    ks = ["s0", "s0.05", "s0.1", "s0.2", "s0.3", "s0.5"]
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.0), sharey=True)
    for i, t in enumerate(("stability.psi", "stability.chi2", "stability.ks", "pd.hosmer_lemeshow", "pd.spiegelhalter")):
        x, y, se = series(idx, t, ks)
        axes[0].errorbar(x, y, yerr=[1.96 * s for s in se], capsize=2, label=T.TEST_LABEL[t], **figkit.STYLES[i])
    axes[0].axhline(0.05, color="0.6", linewidth=0.6, linestyle=":")
    axes[0].set_xlabel("mean shift (standard deviations)")
    axes[0].set_ylabel("rejection rate at the 5% level")
    axes[0].legend(frameon=False)
    axes[0].set_title("population drift", fontsize=8)
    di = T.sim_index(T.c22("discrimination-decay"))
    ds = ["d0", "d0.01", "d0.02", "d0.03", "d0.05", "d0.08"]
    for i, t in enumerate(("disc.auc_vs_initial", "disc.delong")):
        x, y, se = series(di, t, ds)
        axes[1].errorbar(x, y, yerr=[1.96 * s for s in se], capsize=2, label=T.TEST_LABEL[t], **figkit.STYLES[i])
    axes[1].axhline(0.05, color="0.6", linewidth=0.6, linestyle=":")
    axes[1].set_xlabel("loss of AUC")
    axes[1].legend(frameon=False)
    axes[1].set_title("discrimination decay", fontsize=8)
    fig.tight_layout()
    figkit.save(fig, out, "validation-tests-drift")


def fig_c20(out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    D = T.c20_docs()
    pg = D["perturbation-grid"]
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.0))
    for i, (seg, lab) in enumerate((("preset-eps-0.1", "inputs perturbed"), ("control-zeros-kept:preset-eps-0.1", "control run"))):
        t = T.find(pg, "ml.robustness", seg)
        axes[0].plot(t["extras"]["grid"], t["extras"]["auc"], label=lab, **figkit.STYLES[i])
    axes[0].set_xlabel("noise scale (times each feature SD)")
    axes[0].set_ylabel("AUC on the holdout")
    axes[0].legend(frameon=False)
    axes[0].set_title("robustness to input noise", fontsize=8)
    fs = D["fed-shift"]
    rows = [(t["segment"].replace("window:", "").replace("fed-higher-risk-", "shift "), t["metric"], t["light"]) for t in fs["tests"]
            if t["test_id"] == "ml.conformal_coverage"]
    hatch = {"green": "", "amber": "///", "red": "xxx"}
    for i, (lab, m, light) in enumerate(rows):
        axes[1].bar(i, m, color="0.75", edgecolor="0.0", hatch=hatch[light], linewidth=0.6)
    axes[1].axhline(0.9, color="0.0", linewidth=0.8, linestyle="--")
    axes[1].set_xticks(range(len(rows)))
    axes[1].set_xticklabels([r[0] for r in rows], rotation=35, ha="right", fontsize=7)
    axes[1].set_ylim(0.6, 1.0)
    axes[1].set_ylabel("coverage of the 90% conformal sets")
    axes[1].set_title("coverage on shifted populations (hatching: amber, red)", fontsize=8)
    fig.tight_layout()
    figkit.save(fig, out, "validation-tests-c20")


def fig_c21(out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    P = [T.c21_pair(p) for p in T.C21_PAIRS]
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.0))
    ys = np.arange(len(P))[::-1]
    for y, p in zip(ys, P):
        axes[0].errorbar(p["or"], y, xerr=[[p["or"] - p["or_lo"]], [p["or_hi"] - p["or"]]], fmt="o", color="0.0", capsize=2)
    axes[0].axvline(1.0, color="0.6", linewidth=0.7)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels([p["pair"] for p in P])
    axes[0].set_xscale("log")
    axes[0].set_xticks([0.4, 0.5, 0.6, 0.8, 1.0])
    axes[0].set_xticklabels(["0.4", "0.5", "0.6", "0.8", "1.0"])
    axes[0].set_xlabel("odds ratio of approval (Black vs White)")
    axes[0].set_title("controlled disparity with its 95% interval", fontsize=8)
    axes[1].plot([p["pair"] for p in P], [100 * p["st_share"] for p in P], "o-", color="0.0", label="significant complainants")
    axes[1].axhline(20.0, color="0.35", linestyle="--", linewidth=0.8, label="amber cut 20%")
    axes[1].plot([p["pair"] for p in P], [100 * abs(p["gap"]) for p in P], "s--", color="0.45", label="unconditional gap (points)")
    axes[1].set_ylabel("percent")
    axes[1].tick_params(axis="x", labelrotation=35)
    axes[1].legend(frameon=False, fontsize=7)
    axes[1].set_title("situation testing and the raw gap", fontsize=8)
    fig.tight_layout()
    figkit.save(fig, out, "validation-tests-c21")


def main() -> None:
    out = HERE
    figkit.style()
    fig_published(out)
    fig_clustering(out)
    fig_power(out)
    fig_drift(out)
    fig_c20(out)
    fig_c21(out)
    print("figures written to", out)


if __name__ == "__main__":
    main()
