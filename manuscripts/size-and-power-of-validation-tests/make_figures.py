"""Write the vector figures of the manuscript into ``figures/`` from the committed C22 documents and the experiment results.

    python manuscripts/size-and-power-of-validation-tests/make_figures.py

Grayscale-safe (marker and line style carry the series), vector PDF, labelled axes. Nothing is drawn from a typed number.
"""
from __future__ import annotations

import math
import pathlib
import re
import sys

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE))
import figkit  # noqa: E402

import analysis as A  # noqa: E402
import make_numbers  # noqa: E402

OUT = HERE / "figures"
ST = figkit.STYLES


def new(rows: int = 1, cols: int = 1, w: float = 6.3, h: float = 3.0, **kw):
    import matplotlib.pyplot as plt

    figkit.style()
    return plt.subplots(rows, cols, figsize=(w, h), **kw)


def wilson_err(rows, level="p<0.05"):
    y = np.array([r["rates"][level]["rate"] for r in rows])
    lo = np.array([r["rates"][level]["wilson_low"] for r in rows])
    hi = np.array([r["rates"][level]["wilson_high"] for r in rows])
    return y, np.vstack([y - lo, hi - y])


def size_forest() -> None:
    fig, axes = new(1, 2, 6.4, 6.4, sharey=True)
    tbl = A.size_table()
    rep = A.seed_replication()["tests"]
    cv = {r["test"]: r for r in A.committed_verdict_vs_pooled()}
    ys = np.arange(len(tbl))[::-1]
    for ax, lv in zip(axes, A.LEVELS):
        a = A.ALPHA[lv]
        for y, r in zip(ys, tbl):
            x = r[lv]
            ax.errorbar(100 * x["rate"], y + 0.17, xerr=[[100 * (x["rate"] - x["lo"])], [100 * (x["hi"] - x["rate"])]], fmt="o", ms=3.2,
                        color="0.1", mfc="0.1" if cv[r["test"]]["cell_definition"] else "white", capsize=1.5, lw=0.9)
            q = rep[r["test"]][lv]
            ax.errorbar(100 * q["pooled"], y - 0.17, xerr=[[100 * (q["pooled"] - q["pooled_lo"])], [100 * (q["pooled_hi"] - q["pooled"])]],
                        fmt="s", ms=3.0, color="0.45", mfc="0.45" if cv[r["test"]]["pool_definition"] else "white", capsize=1.0, lw=0.8)
            if r["exact"]:
                ax.plot(100 * r["exact"][lv], y, marker="x", color="0.35", ms=5, ls="none")
        ax.axvline(100 * a, color="0.3", lw=0.9)
        ax.axvline(100 * A.bound(a, 4000), color="0.3", lw=0.9, ls="--")
        ax.set_xlabel(f"rejection rate at the {int(a * 100)}% level (%)")
        ax.set_xlim(-0.2 * a * 100, max(100 * A.bound(a, 4000) * 1.6, 100 * max(r[lv]["hi"] for r in tbl) * 1.05))
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels([r["name"] for r in tbl])
    fig.tight_layout()
    figkit.save(fig, OUT, "size_forest")


def p_histograms() -> None:
    doc = A.doc("null")["outputs"]["simulations"]
    keys = ["pd.binomial@null", "pd.normal_multiperiod@null", "pd.hosmer_lemeshow@null", "pd.chi2_grades@null", "disc.auc_vs_initial@null",
            "stability.psi@null", "rating.migration_ztests@null", "rating.hhi@null"]
    rows = {r["key"]: r for r in doc}
    fig, axes = new(2, 4, 6.4, 3.4, sharex=True)
    for ax, k in zip(axes.ravel(), keys):
        r = rows[k]
        h = np.array(r["p_histogram"])
        ax.bar(np.arange(20) / 20 + 0.025, h, width=0.05, color="0.55", edgecolor="0.2", lw=0.4)
        ax.axhline(h.sum() / 20, color="0.0", lw=0.8, ls="--")
        ax.set_title(A.NAME[k.split("@")[0]], fontsize=7)
        ax.tick_params(labelsize=6)
    for ax in axes[1]:
        ax.set_xlabel("p-value")
    for ax in axes[:, 0]:
        ax.set_ylabel("repetitions")
    fig.tight_layout()
    figkit.save(fig, OUT, "p_histograms")


def power_calibration() -> None:
    cur = A.curves("miscalibration")
    groups = [("portfolio", ["pd.binomial", "pd.jeffreys", "pd.binomial_vasicek"], "default counts of one portfolio"),
              ("grades-obligors", [("pd.chi2_grades", "grades"), ("pd.default_profile", "grades"), ("pd.hosmer_lemeshow", "obligors"),
                                   ("pd.spiegelhalter", "obligors")], "grades and obligor level"),
              ("years", ["pd.normal_multiperiod", "pd.traffic_lights"], "five annual cohorts")]
    fig, axes = new(1, 3, 6.5, 2.7, sharey=True)
    for ax, (_, tests, title) in zip(axes, groups):
        for i, t in enumerate(tests):
            test, panel = (t, "portfolio" if t.startswith(("pd.binomial", "pd.jeffreys")) else "years") if isinstance(t, str) else t
            rows = cur[(test, panel)]
            x = np.array([r["x"] for r in rows])
            y, err = wilson_err(rows)
            ax.errorbar(x, 100 * y, yerr=100 * err, capsize=1.2, lw=1.0, **{k: v for k, v in ST[i].items()}, ms=3)
            if all(r.get("exact") for r in rows):
                ax.plot(x, [100 * r["exact"]["p<0.05"] for r in rows], color="0.5", lw=0.8, ls=":")
        ax.axhline(5, color="0.6", lw=0.6)
        ax.set_title(title, fontsize=7.5)
        ax.set_xlabel("true PD / PD applied")
        ax.legend([A.NAME[t if isinstance(t, str) else t[0]] for t in tests], fontsize=5.8, loc="lower right", frameon=False)
    axes[0].set_ylabel("rejection rate at 5% (%)")
    fig.tight_layout()
    figkit.save(fig, OUT, "power_calibration")


def clustering_size() -> None:
    cur = A.curves("clustering", "size")
    fig, ax = new(1, 1, 5.2, 3.2)
    tests = [("pd.binomial", "portfolio"), ("pd.jeffreys", "portfolio"), ("pd.binomial_vasicek", "portfolio"), ("pd.chi2_grades", "grades"),
             ("pd.hosmer_lemeshow", "obligors"), ("pd.spiegelhalter", "obligors"), ("pd.normal_multiperiod", "years"),
             ("pd.traffic_lights", "years")]
    for i, (t, p) in enumerate(tests):
        rows = cur[(t, p)]
        x = [100 * r["x"] for r in rows]
        y, _ = wilson_err(rows)
        ax.plot(x, 100 * y, label=A.NAME[t], **ST[i % 6], ms=3)
        if t == "pd.binomial":
            ax.plot(x, [100 * r["exact"]["p<0.05"] for r in rows], color="0.0", lw=0.7, ls=":")
    ax.axhline(5, color="0.5", lw=0.7)
    ax.set_xlabel("asset correlation of the defaults (%), PDs right")
    ax.set_ylabel("rejection rate at 5% (%)")
    ax.legend(fontsize=6, ncol=2, frameon=False, loc="upper right")
    fig.tight_layout()
    figkit.save(fig, OUT, "clustering_size")


def psi_bands() -> None:
    cells = A.doc("drift")["outputs"]["golden"][0]["cells"]
    fig, ax = new(1, 1, 5.2, 3.2)
    ns = np.geomspace(60, 2500, 200)
    for band, ls in ((0.10, "-"), (0.25, "--")):
        ax.plot(ns, [100 * A.psi_fixed_band_false_alarm(n, band) for n in ns], color="0.2", ls=ls, lw=1.0, label=f"asymptotic, PSI > {band:.2f}")
    ax.axhline(5, color="0.5", lw=0.8, ls=":", label="chi-square benchmark (5%)")
    for rule, mk in (("PSI > 0.10", "o"), ("PSI > 0.25", "s")):
        xs, ys = [], []
        for c in cells:
            m = re.match(r"m (\d+), n (\d+)", c["row"])
            if m and m.group(1) == m.group(2) and c["column"] == f"shift 0 SD, {rule}":
                xs.append(int(m.group(1)))
                ys.append(100 * c["measured"])
        ax.plot(xs, ys, mk, color="0.0", mfc="white" if mk == "s" else "0.0", ms=4, label=f"measured, {rule}")
    ax.set_xscale("log")
    ax.set_xlabel("sample size of each of the two samples")
    ax.set_ylabel("false alarm rate, nothing changed (%)")
    ax.legend(fontsize=6, frameon=False)
    fig.tight_layout()
    figkit.save(fig, OUT, "psi_bands")


def power_families() -> None:
    fig, axes = new(2, 3, 6.6, 4.4, sharey=True)
    panels = [
        ("discrimination-decay", [("disc.auc_vs_initial", "ecb", "ECB test"), ("disc.delong", "delong", "DeLong")], "AUC drop", None),
        ("leakage", [("disc.auc_vs_initial", "auc", "AUC test"), ("stability.csi", "feature", "CSI of the leak")], "shift of the leaked feature", None),
        ("drift", [("stability.psi", "stability", "PSI benchmark"), ("stability.chi2", "stability", "chi-square"), ("stability.ks", "stability", "KS")],
         "mean shift (SD)", ["metric>0.1", "metric>0.25"]),
        ("broken-monotonicity", [("rating.migration_ztests", "migration-500", "z-tests, 500 per grade"),
                                 ("rating.migration_ztests", "migration-2000", "z-tests, 2,000 per grade")], "planted cell / closer neighbour", None),
        ("concentration", [("rating.hhi", "ecb", "ECB (HHI)"), ("stability.chi2", "counts", "chi-square on counts")], "share moved to the modal grade", None),
        ("broken-monotonicity", [("pd.default_profile", "curve", "default profile"), ("pd.chi2_grades", "curve", "chi-square over grades")],
         "grades 3 and 4 swapped (1: fully)", None),
    ]
    for ax, (v, tests, xl, rules) in zip(axes.ravel(), panels):
        cur = A.curves(v)
        i = 0
        for t, p, lab in tests:
            rows = cur[(t, p)]
            x = [r["x"] for r in rows]
            y, err = wilson_err(rows)
            ax.errorbar(x, 100 * y, yerr=100 * err, capsize=1.0, lw=1.0, label=lab, ms=3, **ST[i])
            i += 1
        if rules:
            rows = cur[("stability.psi", "stability")]
            for rule, lab in zip(rules, ("PSI > 0.10 rule", "PSI > 0.25 rule")):
                ax.plot([r["x"] for r in rows], [100 * r["rates"][rule]["rate"] for r in rows], label=lab, ms=3, **ST[i])
                i += 1
        ax.axhline(5, color="0.6", lw=0.6)
        ax.set_xlabel(xl, fontsize=7)
        ax.legend(fontsize=5.5, frameon=False, loc="lower right")
    for ax in axes[:, 0]:
        ax.set_ylabel("rejection rate at 5% (%)")
    fig.tight_layout()
    figkit.save(fig, OUT, "power_families")


def seed_spread() -> None:
    d = A.result("seed_replication.json")
    rep = A.seed_replication()["tests"]
    size = {r["test"]: r for r in A.size_table()}
    fig, ax = new(1, 1, 6.2, 5.2)
    rng = np.random.default_rng(1)
    ys = np.arange(len(A.TEST_ORDER))[::-1]
    for y, t in zip(ys, A.TEST_ORDER):
        ks = np.array([b["k0.05"] for b in d["cells"][f"{t}@null"]]) / d["n_rep"]
        ax.plot(100 * ks, y + rng.uniform(-0.22, 0.22, ks.size), ".", color="0.6", ms=2.5)
        ax.plot(100 * rep[t]["p<0.05"]["pooled"], y, "|", color="0.0", ms=9, mew=1.4)
        ax.plot(100 * size[t]["p<0.05"]["rate"], y, "D", color="0.0", mfc="white", ms=4)
    ax.axvline(5, color="0.3", lw=0.9)
    ax.axvline(100 * A.bound(0.05, 4000), color="0.3", lw=0.9, ls="--")
    ax.set_yticks(ys)
    ax.set_yticklabels([A.NAME[t] for t in A.TEST_ORDER])
    ax.set_xlabel("rejection rate at 5% (%)")
    ax.text(0.99, 0.01, "grey: 50 blocks of 4,000; bar: pooled; diamond: committed cell", transform=ax.transAxes, fontsize=6.5, ha="right")
    fig.tight_layout()
    figkit.save(fig, OUT, "seed_spread")


def interval_coverage() -> None:
    ps = np.array([0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5])
    fig, ax = new(1, 1, 5.2, 3.2)
    for i, (name, f) in enumerate(A.INTERVALS.items()):
        ax.plot(ps, [100 * A.coverage(f, p, 4000) for p in ps], label=name.replace("--", "-"), ms=3, **ST[i])
    ax.axhline(95, color="0.5", lw=0.8, ls=":")
    ax.set_xscale("log")
    ax.set_xlabel("true rejection probability")
    ax.set_ylabel("coverage of the 95% interval (%)")
    ax.set_ylim(88, 100)
    ax.legend(fontsize=6, frameon=False, ncol=2, loc="lower right")
    fig.tight_layout()
    figkit.save(fig, OUT, "interval_coverage")


def resolution() -> None:
    fig, axes = new(1, 2, 6.4, 2.9)
    Rs = np.geomspace(500, 300000, 40)
    for lv, ls in ((0.05, "-"), (0.01, "--")):
        axes[0].plot(Rs, [100 * make_numbers.detectable(lv, int(R)) for R in Rs], color="0.1", ls=ls, label=f"screen, level {int(lv * 100)}%")
        axes[0].plot(Rs, [100 * A.interval_detectable(lv, int(R)) for R in Rs], color="0.55", ls=ls, label=f"definition, level {int(lv * 100)}%")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("repetitions in the cell")
    axes[0].set_ylabel("excess seen with probability 0.8 (points)")
    axes[0].legend(fontsize=6.5, frameon=False)
    fl = A.flag_rates_by_repetitions()
    Rk = [1000, 2000, 4000, 20000]
    for i, (key, lab) in enumerate((("within_bound", "within the level, bound"), ("within_naive", "within the level, naive"),
                                    ("over_bound", "above the level, bound"), ("over_naive", "above the level, naive"))):
        axes[1].plot(Rk, [100 * fl[str(R)][key] for R in Rk], label=lab, ms=3, **ST[i])
    axes[1].set_xscale("log")
    axes[1].set_xlabel("repetitions in the cell")
    axes[1].set_ylabel("cells flagged as oversized (%)")
    axes[1].legend(fontsize=6, frameon=False)
    fig.tight_layout()
    figkit.save(fig, OUT, "resolution")


def reproductions() -> None:
    fig, ax = new(1, 1, 4.6, 4.2)
    for g, mk, lab in ((A.doc("clustering")["outputs"]["golden"][0], "o", "BCBS WP14, Tables 7 and 8"),
                       (A.doc("drift")["outputs"]["golden"][0], "s", "Yurdakul and Naranjo, Table 4")):
        pub = np.array([c["published"] for c in g["cells"]])
        mea = np.array([c["measured"] for c in g["cells"]])
        ok = np.array([c["agrees"] for c in g["cells"]])
        ax.plot(100 * pub[ok], 100 * mea[ok], mk, color="0.3", ms=3, mfc="0.6", label=lab)
        ax.plot(100 * pub[~ok], 100 * mea[~ok], mk, color="0.0", ms=6, mfc="none", mew=1.2)
    ax.plot([0, 100], [0, 100], color="0.3", lw=0.8)
    ax.set_xlabel("printed rejection rate (%)")
    ax.set_ylabel("measured rejection rate (%)")
    ax.legend(fontsize=6.5, frameon=False, loc="upper left")
    ax.text(0.98, 0.04, "ringed: cells that disagree", transform=ax.transAxes, fontsize=6.5, ha="right")
    fig.tight_layout()
    figkit.save(fig, OUT, "reproductions")


def hhi_bound() -> None:
    ec = A.doc("concentration")["outputs"]["exact_curves"][0]
    x = np.array(ec["x"], dtype=float)
    fig, ax = new(1, 1, 5.0, 3.1)
    for i, s in enumerate(ec["series"]):
        y = np.array([np.nan if v is None else v for v in s["y"]], dtype=float)
        ax.plot(x[: len(y)], y, label=s["label"]["en"], **{k: v for k, v in ST[i].items() if k != "marker"})
    ax.axhline(float(stats.norm.ppf(0.95)), color="0.0", lw=0.9, ls="--")
    ax.text(0.01, float(stats.norm.ppf(0.95)) + 0.03, "5% critical value 1.645", ha="left", fontsize=6.5, transform=ax.get_yaxis_transform())
    ax.set_xlabel("coefficient of variation of the current grade frequencies")
    ax.set_ylabel("ECB statistic")
    ax.legend(fontsize=6.5, frameon=False, loc="center right")
    fig.tight_layout()
    figkit.save(fig, OUT, "hhi_bound")


def extension() -> None:
    ext = A.extension_table()
    fig, axes = new(1, 2, 6.6, 5.6, sharey=True)
    ys = np.arange(len(ext))[::-1]
    for y, e in zip(ys, ext):
        axes[0].plot(100 * e["size5"], y, "o", color="0.1", mfc="0.1" if e["holds_definition"] else "white", ms=3.5)
        axes[1].errorbar(100 * e["power5"], y, xerr=[[100 * (e["power5"] - e["power5_lo"])], [100 * (e["power5_hi"] - e["power5"])]], fmt="o",
                         color="0.1", ms=3.5, capsize=1.2, lw=0.8)
    axes[0].axvline(5, color="0.3", lw=0.9)
    axes[0].axvline(100 * A.bound(0.05, 4000), color="0.3", lw=0.9, ls="--")
    axes[0].set_xlabel("size at the 5% level (%)")
    axes[1].set_xlabel("power at 5% against the stated alternative (%)")
    axes[1].axvline(80, color="0.5", lw=0.7, ls=":")
    labels = []
    for e in ext:
        base = re.sub(r"\\'e", "e", EXT_SHORT.get(e["test"], e["test"]))
        labels.append(f"{base}, {e['label']}" if e["test"] in ("portfolio.tail_backtest", "market.dynamic_quantile_test") else base)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(labels, fontsize=6)
    fig.tight_layout()
    figkit.save(fig, OUT, "extension")


EXT_SHORT = {
    "ccr.pfe_exceedance_backtest": "PFE exceedance", "ifrs9.stage_migration_backtest": "IFRS 9 stage migration",
    "lgd_ead.lgd_calibration_by_segment": "LGD by segment", "lgd_ead.lgd_calibration_over_time": "LGD over time",
    "lgd_ead.downturn_coverage": "Downturn LGD coverage", "market.mcneil_frey_residual_test": "McNeil-Frey",
    "portfolio.tail_backtest": "Tail back-test", "portfolio.mc_convergence": "MC convergence", "portfolio.crp_recursion_vs_mc": "CreditRisk+ recursion",
    "fair.two_proportion_z": "Two-proportion z", "fair.fisher_exact": "Fisher exact", "market.kupiec_pof": "Kupiec",
    "market.christoffersen_independence": "Christoffersen independence", "market.christoffersen_conditional_coverage": "Christoffersen cond. coverage",
    "market.duration_test": "Duration", "market.acerbi_szekely": "Acerbi-Szekely", "market.du_escanciano_unconditional": "Du-Escanciano uncond.",
    "market.du_escanciano_conditional": "Du-Escanciano cond.", "market.dynamic_quantile_test": "Dynamic quantile",
    "ml.shift_resilience": "Shift resilience (ML)", "ml.conformal_coverage": "Conformal coverage (ML)",
}


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for f in (size_forest, p_histograms, power_calibration, clustering_size, psi_bands, power_families, seed_spread, interval_coverage,
              resolution, reproductions, hhi_bound, extension):
        f()
        print("figure", f.__name__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
