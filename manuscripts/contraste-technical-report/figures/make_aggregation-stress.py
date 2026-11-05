"""The figures of the chapter on risk aggregation and stress testing of the technical report (``sections/15-aggregation-stress.tex``),
as vector PDF in ``manuscripts/contraste-technical-report/figures/aggregation-stress-*.pdf``, drawn from the committed artifacts of
case C18 under ``data/derived/C18`` with the shared style of ``manuscripts/_shared/figkit.py`` (readable in grayscale).

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_aggregation-stress.py
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys

import numpy as np
import matplotlib.dates as mdates
from matplotlib.ticker import FixedLocator, NullFormatter, ScalarFormatter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

LOAN = {"commercial-industrial": "Commercial and industrial", "commercial-real-estate": "Commercial real estate", "residential": "Residential",
        "credit-cards": "Credit cards", "other-consumer": "Other consumer"}
RISK = {"credit": "Credit", "market": "Market", "irrbb": "IRRBB", "operational": "Operational"}
SCEN = [("baseline", "Federal Reserve baseline"), ("eba-2025-adverse", "EBA adverse"), ("fed-2026-severely-adverse", "Federal Reserve severely adverse"),
        ("ngfs-delayed-transition", "NGFS Delayed transition")]

BASE = figkit.doc("C18/baseline.json")["outputs"]
TCOP = figkit.doc("C18/t-copula-baseline.json")["outputs"]
MODELS = figkit.doc("C18/models-banco-andino.json")
VAR = next(m for m in MODELS["model"] if m["id"] == "c18-var-conditional-forecast")["details"]["var"]
GAR = next(m for m in MODELS["model"] if m["id"] == "c18-growth-at-risk")["details"]["growth_at_risk"]


def day(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def band_figure() -> None:
    import matplotlib.pyplot as plt

    rows = BASE["aggregation"]["band"]
    stressed = TCOP["correlation_stress"]["aggregation"]["band"]
    names = {"lower-bound": "Lower bound", "simple-sum": "Simple sum", "variance-covariance": "Variance-covariance", "gaussian-copula": "Gaussian copula",
             "t-copula": "t copula", "worst-case": "Worst case"}
    fig, ax = plt.subplots(1, 2, figsize=(7.6, 3.3), gridspec_kw={"width_ratios": [1.35, 1.0]})
    y = np.arange(len(rows))[::-1]
    for yi, r, s in zip(y, rows, stressed, strict=True):
        se = r["mc_se_clp_m"] or 0.0
        lab = names[r["method"]] + ("" if r["nu"] is None else f", $\\nu$={r['nu']:.0f}")
        ax[0].barh(yi, r["capital_clp_m"] / 1e3, xerr=2 * se / 1e3 if se else None, color="0.75", edgecolor="0.2", linewidth=0.6, height=0.62,
                   error_kw={"elinewidth": 0.8, "capsize": 2})
        ax[0].plot(s["capital_clp_m"] / 1e3, yi, marker="D", color="0.0", markersize=3.5, linestyle="none")
        ax[0].text(-8, yi, lab, ha="right", va="center", fontsize=7.5)
    ax[0].plot([], [], marker="D", color="0.0", markersize=3.5, linestyle="none", label="market-credit correlation 0.8")
    ax[0].axvline(rows[1]["capital_clp_m"] / 1e3, color="0.3", linestyle=":", linewidth=0.8)
    ax[0].set_yticks([])
    ax[0].set_xlabel("Economic capital, CLP billion")
    ax[0].set_title("(a) The band of aggregation rows")
    ax[0].legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=7)
    nus = [r["nu"] for r in rows if r["method"] == "t-copula"]
    cap = np.array([r["capital_clp_m"] for r in rows if r["method"] == "t-copula"]) / 1e3
    se = np.array([r["mc_se_clp_m"] for r in rows if r["method"] == "t-copula"]) / 1e3
    g = next(r for r in rows if r["method"] == "gaussian-copula")
    ax[1].errorbar(nus, cap, yerr=2 * se, color="0.0", marker="o", linestyle="-", capsize=2, label="t copula, $\\pm 2$ s.e.")
    ax[1].axhline(g["capital_clp_m"] / 1e3, color="0.35", linestyle="--", label="Gaussian copula")
    ax[1].axhspan((g["capital_clp_m"] - 2 * g["mc_se_clp_m"]) / 1e3, (g["capital_clp_m"] + 2 * g["mc_se_clp_m"]) / 1e3, color="0.88", linewidth=0)
    ax[1].set_xscale("log")
    ax[1].set_xticks(nus)
    ax[1].set_xticklabels([f"{v:.0f}" for v in nus])
    ax[1].xaxis.set_minor_formatter(NullFormatter())
    ax[1].set_xlabel("Degrees of freedom $\\nu$")
    ax[1].set_ylabel("Economic capital, CLP billion")
    ax[1].set_title("(b) Copula choice")
    ax[1].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, HERE, "aggregation-stress-band")


def euler_figure() -> None:
    import matplotlib.pyplot as plt

    marg = BASE["aggregation"]["marginals"]
    alloc = {a["risk"]: a for a in BASE["aggregation"]["euler"]["allocation"]}
    ben = {b["risk"]: b["benefit"] for b in BASE["aggregation"]["diversification"]["euler_benefit_by_risk"]}
    risks = [m["risk"] for m in marg]
    ec = np.array([m["ec_clp_m"] for m in marg])
    es = np.array([m["es_clp_m"] for m in marg])
    contrib = np.array([alloc[r]["contribution_clp_m"] for r in risks])
    x = np.arange(len(risks))
    w = 0.26
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.5, 1.0]})
    ax[0].bar(x - w, ec / ec.sum(), w, color="0.85", edgecolor="0.2", linewidth=0.6, label="share of stand-alone EC")
    ax[0].bar(x, es / es.sum(), w, color="0.6", edgecolor="0.2", linewidth=0.6, label="share of stand-alone ES")
    ax[0].bar(x + w, contrib / contrib.sum(), w, color="0.25", edgecolor="0.0", linewidth=0.6, label="share of the Euler allocation")
    ax[0].set_xticks(x)
    ax[0].set_xticklabels([RISK[r] for r in risks])
    ax[0].set_ylim(0, 0.55)
    ax[0].set_ylabel("Share of the total")
    ax[0].set_title("(a) Stand-alone against allocated")
    ax[0].legend(frameon=False, fontsize=7)
    ax[1].bar(x, [100 * ben[r] for r in risks], 0.55, color="0.55", edgecolor="0.2", linewidth=0.6)
    for xi, r in zip(x, risks, strict=True):
        ax[1].text(xi, 100 * ben[r] + 0.8, f"{100 * ben[r]:.1f}", ha="center", fontsize=7)
    ax[1].set_xticks(x)
    ax[1].set_xticklabels([RISK[r] for r in risks], rotation=20)
    ax[1].set_ylim(0, 48)
    ax[1].set_ylabel("Euler diversification benefit (percent)")
    ax[1].set_title("(b) Benefit by risk")
    fig.tight_layout()
    figkit.save(fig, HERE, "aggregation-stress-euler")


def backcast_figure(window_id: str, name: str, title: str) -> None:
    import matplotlib.pyplot as plt

    w = next(w for w in VAR["windows"] if w["window_id"] == window_id)
    fig, axes = plt.subplots(2, 3, figsize=(7.6, 4.3))
    flat = axes.ravel()
    for a, r in zip(flat[:5], w["per_loan_type"], strict=True):
        q = [day(x["quarter_end"]) for x in r["quarters"]]
        every = max(1, len(q) // 8)
        a.plot(q, [100 * x["realised"] for x in r["quarters"]], label="realised", markevery=every, **figkit.STYLES[0])
        a.plot(q, [100 * x["ols"] for x in r["quarters"]], label="OLS satellite", markevery=every, **figkit.STYLES[1])
        a.plot(q, [100 * x["var"] for x in r["quarters"]], label="VAR conditional forecast", markevery=every, **figkit.STYLES[2])
        a.set_title(LOAN[r["fed_loan_type"]], fontsize=8)
        a.xaxis.set_major_locator(mdates.YearLocator())
        a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        a.tick_params(axis="x", labelrotation=30, labelsize=6.5)
        a.set_ylabel("Net charge-off rate (percent)", fontsize=7)
    h, lab = flat[0].get_legend_handles_labels()
    flat[5].axis("off")
    flat[5].legend(h, lab, frameon=False, loc="center", fontsize=8, title=title)
    fig.tight_layout()
    figkit.save(fig, HERE, name)


def ratio_figure() -> None:
    import matplotlib.pyplot as plt

    types = list(LOAN)
    x = np.arange(len(types))
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0))
    for k, w in enumerate(VAR["windows"]):
        ratio = [next(r for r in w["per_loan_type"] if r["fed_loan_type"] == t)["metrics"]["rmse_ratio_var_over_ols"] for t in types]
        ax[0].bar(x + (k - 0.5) * 0.36, ratio, 0.34, color=("0.8", "0.35")[k], edgecolor="0.1", linewidth=0.6,
                  label=("2008 to 2009", "2020 to 2025")[k])
    ax[0].axhline(1.0, color="0.0", linewidth=0.8, linestyle="--")
    ax[0].set_yscale("log")
    ax[0].yaxis.set_major_locator(FixedLocator([0.4, 0.6, 1.0, 1.5, 2.0]))
    ax[0].yaxis.set_major_formatter(ScalarFormatter())
    ax[0].yaxis.set_minor_formatter(NullFormatter())
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(["C&I", "CRE", "Resid.", "Cards", "Other"])
    ax[0].set_ylabel("RMSE of the VAR over RMSE of the OLS")
    ax[0].set_title("(a) Error ratio")
    ax[0].legend(frameon=False, fontsize=7)
    for k, w in enumerate(VAR["windows"]):
        for j, t in enumerate(types):
            m = next(r for r in w["per_loan_type"] if r["fed_loan_type"] == t)["metrics"]
            ax[1].plot([m["ols"]["peak_ratio"]], [m["var"]["peak_ratio"]], marker=("o", "s")[k], color=("0.55", "0.0")[k], linestyle="none",
                       label=("2008 to 2009", "2020 to 2025")[k] if j == 0 else None)
    lim = [0.08, 400]
    ax[1].plot(lim, lim, color="0.0", linewidth=0.8, linestyle="--")
    ax[1].axhline(1.0, color="0.6", linewidth=0.6, linestyle=":")
    ax[1].axvline(1.0, color="0.6", linewidth=0.6, linestyle=":")
    ax[1].set_xscale("log")
    ax[1].set_yscale("log")
    ax[1].set_xlim(lim)
    ax[1].set_ylim(lim)
    ax[1].set_xlabel("Predicted over realised peak, OLS")
    ax[1].set_ylabel("Predicted over realised peak, VAR")
    ax[1].set_title("(b) Peak ratio")
    ax[1].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, HERE, "aggregation-stress-var-ratio")


def gar_figure() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 2, figsize=(7.6, 3.2))
    for a, w, ttl in zip(ax, GAR["windows"], ("(a) Fit to 2007Q4, targets through 2009Q4", "(b) Fit to 2019Q4, targets through 2025Q4"), strict=True):
        q = np.array([o["quantiles"] for o in w["origins"]])
        x = [day(o["origin"]) for o in w["origins"]]
        for k, tau in enumerate(GAR["taus"]):
            a.plot(x, q[:, k], label=f"$\\tau$={tau:g}", **{**figkit.STYLES[k], "marker": None})
        a.plot(x, [o["realised"] for o in w["origins"]], color="0.0", marker="o", linestyle="none", markersize=3.5, label="realised")
        a.set_title(ttl, fontsize=8)
        a.set_xlabel("Forecast origin")
        a.xaxis.set_major_locator(mdates.YearLocator())
        a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        a.tick_params(axis="x", labelrotation=30)
    ax[0].set_ylabel("Average real GDP growth, next four quarters (percent)")
    ax[1].legend(frameon=False, fontsize=6.5, ncol=2)
    fig.tight_layout()
    figkit.save(fig, HERE, "aggregation-stress-gar")


def scenario_figure() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(5.6, 3.2))
    stack = figkit.doc("C18/reverse-stress.json")["outputs"]["failure_point"]["stack"]["total"]
    for k, (v, label) in enumerate(SCEN):
        d = figkit.doc(f"C18/{v}.json")["outputs"]
        y = [100 * d["capital_start"]["cet1_ratio"]] + [100 * r["cet1_ratio"] for r in d["headline_cet1"]["rows"]]
        ax.plot(range(4), y, label=label, **figkit.STYLES[k])
    ax.axhline(100 * stack, color="0.0", linewidth=0.9, linestyle="--")
    ax.text(0.05, 100 * stack + 0.08, "legal minimum stack", fontsize=7)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["start", "year 1", "year 2", "year 3"])
    ax.set_ylabel("CET1 over RWA (percent)")
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, HERE, "aggregation-stress-scenarios")


def main() -> None:
    figkit.style()
    band_figure()
    euler_figure()
    backcast_figure("pandemic-2020", "aggregation-stress-backcast-2020", "2020 to 2025")
    backcast_figure("gfc-2008-09", "aggregation-stress-backcast-2008", "2008 to 2009")
    ratio_figure()
    gar_figure()
    scenario_figure()
    print(len(list(HERE.glob("aggregation-stress-*.pdf"))), "figures")


if __name__ == "__main__":
    main()
