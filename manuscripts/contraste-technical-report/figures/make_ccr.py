"""The figures of the counterparty credit risk chapter of the technical report (``sections/12-ccr.tex``), as vector PDF in
``manuscripts/contraste-technical-report/figures/ccr-*.pdf``, drawn from the committed artifacts of case C12 under
``data/derived/C12`` with the shared style of ``manuscripts/_shared/figkit.py`` (readable in grayscale).

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_ccr.py
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

VARIANTS = ["single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im"]
SHORT = {"single-swap": "Single swap", "netting-set": "Netting set", "csa-mpor-10d": "CSA, MPoR 10 d",
         "csa-mpor-20d": "CSA, MPoR 20 d", "with-im": "CSA with initial margin", "wrong-way-risk": "Wrong-way risk"}
HORIZONS = ["10bd", "20bd", "1m", "3m", "6m", "12m"]


def out(v: str) -> dict:
    return figkit.doc(f"C12/{v}.json")["outputs"]


def exposure_profiles() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.2))
    for k, v in enumerate(VARIANTS):
        e = out(v)["exposure"]
        t = np.asarray(e["time_grid_years"])
        ee, se = np.asarray(e["ee"]["values"]), np.asarray(e["ee"]["mc_se"])
        ee = np.maximum(ee, 1.0)
        ax[0].plot(t, ee, label=SHORT[v], markevery=3, **figkit.STYLES[k])
        ax[0].fill_between(t, np.maximum(ee - 2 * se, 1.0), ee + 2 * se, color="0.85", alpha=0.7, linewidth=0)
        pf = np.maximum(np.asarray(e["pfe"]["values"]), 1.0)
        ax[1].plot(t, pf, label=SHORT[v], markevery=3, **figkit.STYLES[k])
    for a, ttl in zip(ax, ("(a) Expected exposure, band of two standard errors", "(b) Potential future exposure at 95%")):
        a.set_yscale("log")
        a.set_xlabel("Time from the valuation date (years)")
        a.set_title(ttl)
    ax[0].set_ylabel("USD (log scale)")
    ax[1].legend(frameon=False, fontsize=6.5, loc="center right", bbox_to_anchor=(1.0, 0.4))
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-ee-profiles")


def ore_gaps() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(6.4, 3.1))
    for k, v in enumerate(VARIANTS):
        ag = out(v)["ore_reconciliation"]["agreement"]
        t = np.array([a["t"] for a in ag])
        z = np.array([a["difference"] / a["combined_se"] if a["combined_se"] > 0 else 0.0 for a in ag])
        ax.plot(t, z, label=SHORT[v], markevery=3, **figkit.STYLES[k])
    ax.axhline(2.0, color="0.5", linewidth=0.8, linestyle="--")
    ax.axhline(-2.0, color="0.5", linewidth=0.8, linestyle="--")
    ax.axhline(0.0, color="0.7", linewidth=0.5)
    ax.set_xlabel("Time from the valuation date (years)")
    ax.set_ylabel("(ORE minus engine) / combined std. error")
    ax.set_title("Expected exposure of the engine against ORE 1.8.17.0; dashed lines at plus and minus two")
    ax.legend(frameon=False, fontsize=7, ncol=2, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-ore-gaps")


def wrong_way() -> None:
    import matplotlib.pyplot as plt

    w = out("wrong-way-risk")["wrong_way_risk"]
    b = np.array([s["b"] for s in w["sweep"]])
    cva = np.array([s["cva"]["amount"] for s in w["sweep"]])
    se = np.array([s["cva"]["mc_se"] for s in w["sweep"]])
    fig, ax = plt.subplots(1, 1, figsize=(5.2, 3.1))
    ax.errorbar(b, cva, yerr=1.96 * se, color="0.0", marker="o", capsize=3, linewidth=1.2, label="Hull and White hazard model, 95% interval")
    ax.axhline(w["independent_cva"]["amount"], color="0.45", linestyle="--", linewidth=1.0, label="Independent exposure and default")
    ax.set_xlabel("Dependence parameter b (per USD million of portfolio value)")
    ax.set_ylabel("CVA of the netting set (USD)")
    ax.set_title("Wrong-way risk raises the CVA monotonically")
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-wwr")


def backtest() -> None:
    import matplotlib.pyplot as plt

    b = out("netting-set")["backtest"]
    x = np.arange(len(HORIZONS))
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.2))
    bk = {h["horizon"]: h for h in b["book_horizons"]}
    rf = {h["horizon"]: h for h in b["risk_factor"]["horizons"]}
    ax[0].plot(x, [bk[h]["w2"] for h in HORIZONS], label="Netting-set value, statistic", **figkit.STYLES[0])
    ax[0].plot(x, [rf[h]["w2"] for h in HORIZONS], label="3 month zero rate, statistic", **figkit.STYLES[1])
    ax[0].plot(x, [bk[h]["critical_simulated"]["p05"] for h in HORIZONS], color="0.5", linestyle=":", marker="s",
               label="Simulated 5% critical value")
    ax[0].plot(x, [bk[h]["critical_simulated"]["p01"] for h in HORIZONS], color="0.5", linestyle="-.", marker="^",
               label="Simulated 1% critical value")
    ax[0].set_yscale("log")
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(HORIZONS)
    ax[0].set_xlabel("Forecast horizon")
    ax[0].set_ylabel("Anderson-Darling $W^2$ (log scale)")
    ax[0].set_title("(a) Statistic against critical values")
    ax[0].legend(frameon=True, framealpha=0.95, fontsize=6.0, loc="center left", bbox_to_anchor=(0.0, 0.5))
    width = 0.27
    obs_b = [next(e for e in bk[h]["exceedances"] if abs(e["quantile"] - 0.95) < 1e-9)["count"] for h in HORIZONS]
    obs_r = [next(e for e in rf[h]["exceedances"] if abs(e["quantile"] - 0.95) < 1e-9)["count"] for h in HORIZONS]
    exp = next(e for e in bk["10bd"]["exceedances"] if abs(e["quantile"] - 0.95) < 1e-9)["expected"]
    ax[1].bar(x - width / 2, obs_b, width, color="0.25", label="Netting-set value")
    ax[1].bar(x + width / 2, obs_r, width, color="0.7", hatch="//", edgecolor="0.2", label="3 month zero rate")
    ax[1].axhline(exp, color="0.0", linestyle="--", linewidth=1.0, label="Expected under the model")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(HORIZONS)
    ax[1].set_xlabel("Forecast horizon")
    ax[1].set_ylabel(f"Exceedances of the 95% PFE in {bk['10bd']['n']} dates")
    ax[1].set_title("(b) Exceedance counts")
    ax[1].legend(frameon=False, fontsize=6.5, loc="upper right")
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-backtest")


def pit_histograms() -> None:
    import matplotlib.pyplot as plt

    b = out("netting-set")["backtest"]
    bk = {h["horizon"]: h for h in b["book_horizons"]}
    rf = {h["horizon"]: h for h in b["risk_factor"]["horizons"]}
    fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.5), sharey=True)
    panels = (("(a) Value, 10bd", bk["10bd"]["pits"]), ("(b) Value, 12m", bk["12m"]["pits"]), ("(c) 3 month rate, 10bd", rf["10bd"]["pits"]))
    for a, (ttl, pits) in zip(ax, panels):
        a.hist(pits, bins=10, range=(0, 1), color="0.45", edgecolor="0.1", density=True)
        a.axhline(1.0, color="0.0", linestyle="--", linewidth=0.9)
        a.set_title(ttl)
        a.set_xlabel("PIT")
    ax[0].set_ylabel("Density (uniform is 1)")
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-pit")


def regulatory() -> None:
    import matplotlib.pyplot as plt

    names = ["netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im"]
    x = np.arange(len(names))
    width = 0.2
    series = [
        ("SA-CCR EAD", [out(v)["sa_ccr"]["ead"]["amount"] for v in names], "0.15", None),
        ("1.4 x EEPE", [out(v)["regulatory_comparison"]["alpha_times_eepe"]["amount"] for v in names], "0.45", "//"),
        ("1.4 x stressed EEPE", [1.4 * out(v)["regulatory_comparison"]["stressed"]["effective_epe"]["amount"] for v in names], "0.7", "xx"),
        ("BA-CVA capital", [out(v)["ba_cva"]["capital"]["amount"] for v in names], "0.88", ".."),
    ]
    fig, ax = plt.subplots(1, 1, figsize=(6.6, 3.2))
    for k, (lab, vals, col, hatch) in enumerate(series):
        ax.bar(x + (k - 1.5) * width, vals, width, color=col, edgecolor="0.0", hatch=hatch, linewidth=0.6, label=lab)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT[v] for v in names])
    ax.set_ylabel("USD (log scale)")
    ax.set_title("Standardised and model measures of the same netting set")
    ax.legend(frameon=False, fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-regulatory")


def calibration_history() -> None:
    import matplotlib.pyplot as plt

    cal = figkit.doc("C12/models-hw1f-treasury-2000-2025.json")["fit"]["calibrations"]
    d = [dt.date.fromisoformat(c["backtest_date"]) for c in cal]
    a = np.array([c["a"] for c in cal])
    a_se = np.array([c["a_se"] for c in cal])
    s = np.array([c["sigma"] for c in cal])
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 2.9))
    ax[0].plot(d, a, color="0.0", linewidth=1.2)
    ax[0].fill_between(d, a - 1.96 * a_se, a + 1.96 * a_se, color="0.82", linewidth=0)
    ax[0].set_ylabel("Mean reversion $a$ (per year)")
    ax[0].set_title("(a) Estimate and 95% band")
    ax[1].plot(d, s, color="0.0", linewidth=1.2)
    ax[1].set_ylabel("Volatility $\\sigma$ (per square-root year)")
    ax[1].set_title("(b) Estimate")
    for a_ in ax:
        a_.set_xlabel("Calibration date (expanding window from 1990)")
    fig.autofmt_xdate()
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-calibration")


def calibration_sensitivity() -> None:
    import matplotlib.pyplot as plt

    ns = out("netting-set")
    t = np.asarray(ns["exposure"]["time_grid_years"])
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0))
    names = {"base": "Base", "a-plus-1se": "a plus one s.e.", "a-minus-1se": "a minus one s.e.",
             "sigma-plus-1se": "sigma plus one s.e.", "sigma-minus-1se": "sigma minus one s.e."}
    for k, r in enumerate(ns["calibration_sensitivity"]):
        ax[0].plot(t, r["ee"]["values"], label=names[r["case"]], markevery=3, **figkit.STYLES[k])
        ax[1].plot(t, r["pfe"]["values"], label=names[r["case"]], markevery=3, **figkit.STYLES[k])
    ax[0].set_title("(a) Expected exposure")
    ax[1].set_title("(b) Potential future exposure at 95%")
    for a in ax:
        a.set_xlabel("Time from the valuation date (years)")
    ax[0].set_ylabel("USD, netting set")
    ax[0].legend(frameon=False, fontsize=6.5, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-sensitivity")


def girr() -> None:
    import matplotlib.pyplot as plt

    ns = out("netting-set")
    tenors = figkit.doc("C12/models-hw1f-treasury-2000-2025.json")["fit"]["girr_parameters"]["tenors_years"]
    x = np.arange(len(tenors))
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0))
    ax[0].bar(x, np.asarray(ns["girr"]["weighted_sensitivities"]) / 1e3, color="0.35", edgecolor="0.0", linewidth=0.6)
    ax[0].set_xticks(x)
    ax[0].set_xticklabels([f"{t:g}" for t in tenors])
    ax[0].set_xlabel("GIRR tenor (years)")
    ax[0].set_ylabel("Weighted sensitivity (USD thousand)")
    ax[0].set_title("(a) Netting set, weights divided by sqrt 2")
    names = ["single-swap", "netting-set"]
    sc = ["low", "medium", "high"]
    w = 0.25
    xx = np.arange(len(names))
    for k, s in enumerate(sc):
        vals = [next(r["k_b"] for r in out(v)["girr"]["scenarios"] if r["scenario"] == s) / 1e3 for v in names]
        ax[1].bar(xx + (k - 1) * w, vals, w, color=("0.85", "0.55", "0.2")[k], edgecolor="0.0", linewidth=0.6, label=f"{s} correlation")
    ax[1].set_xticks(xx)
    ax[1].set_xticklabels([SHORT[v] for v in names])
    ax[1].set_ylabel("Bucket charge (USD thousand)")
    ax[1].set_title("(b) Charge by correlation scenario")
    ax[1].set_ylim(0, 800)
    ax[1].legend(frameon=False, fontsize=6.5, loc="upper center", ncol=3)
    fig.tight_layout()
    figkit.save(fig, HERE, "ccr-girr")


def main() -> None:
    figkit.style()
    exposure_profiles()
    ore_gaps()
    wrong_way()
    backtest()
    pit_histograms()
    regulatory()
    calibration_history()
    calibration_sensitivity()
    girr()
    print("figures:", len(list(HERE.glob("ccr-*.pdf"))))


if __name__ == "__main__":
    main()
