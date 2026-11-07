"""The figures of the provisions chapter of the technical report (``sections/08-provisions.tex``), as vector PDF in
``manuscripts/contraste-technical-report/figures/provisions-*.pdf``, drawn from the committed artifacts of cases C03, C06 and
C07 under ``data/derived`` with the shared style of ``manuscripts/_shared/figkit.py`` (readable in grayscale).

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_provisions.py
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

DATES = ["2006-12", "2008-12", "2010-12", "2019-12", "2020-06", "2023-06"]
SCENARIOS = ["base", "recession", "consumer-arrears-shock", "house-price-fall", "uf-inflation-spike", "combined-severe"]
SCEN_SHORT = ["Base", "Recession", "Consumer\narrears", "House\nprice fall", "UF\ninflation", "Combined\nsevere"]
RUNG_NAME = {"L0-km": "Kaplan-Meier", "L1-dth": "Discrete-time hazard", "L2-cox": "Cox", "L3-pch": "PC-Hazard"}


def lifetime_curves() -> None:
    import matplotlib.pyplot as plt

    m = figkit.doc("C06/models-rd-2010-12.json")
    v = figkit.doc("C06/rd-2010-12.json")
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.1))
    for k, e in enumerate(m["fit"]["ladder"]):
        s = figkit.STYLES[k]
        ax[0].plot(e["baseline"]["months"], e["baseline"]["cumulative_pd"], label=RUNG_NAME[e["rung_id"]], **s, markevery=4)
    ax[0].set_xlabel("Loan age (months)")
    ax[0].set_ylabel("Cumulative PD of the reference loan")
    ax[0].set_title("(a) Reference loan, December 2010")
    ax[0].legend(frameon=False)
    obs = None
    for k, rid in enumerate(("L0-km", "L1-dth", "L2-cox", "L3-pch")):
        t = next(t for t in v["tests"] if t["test_id"] == "ifrs9.lifetime_pd_backtest" and t["model_id"] == rid and t["segment"] == "all")
        x = t["extras"]
        ax[1].plot(x["months"], x["predicted"], label=RUNG_NAME[rid], **figkit.STYLES[k])
        obs = x["observed"]
        if rid == "L3-pch":
            ax[1].fill_between(x["months"], x["band_low"], x["band_high"], color="0.85", label="5% Vasicek band, PC-Hazard")
            months = x["months"]
    ax[1].plot(months, obs, color="k", linewidth=2.2, alpha=0.35, label="Observed (Kaplan-Meier)")
    ax[1].set_xlabel("Months after the reporting date")
    ax[1].set_ylabel("Cumulative default")
    ax[1].set_title("(b) Backtest, all cohorts pooled")
    ax[1].legend(frameon=True, framealpha=0.95, fontsize=6.5, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, HERE, "provisions-lifetime-curves")


def decile_calibration() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.9))
    for j, k in enumerate((12, 24, 36)):
        lo, hi = 1e-4, 1.0
        for r, (rid, mk) in enumerate((("L2-cox", "s"), ("L3-pch", "o"))):
            xs, ys = [], []
            for d in DATES:
                p = next(x for x in figkit.doc(f"C06/models-rd-{d}.json")["model"] if x["id"] == rid)
                for row in p["details"]["decile_calibration"]:
                    if row["months"] == k and row["observed_aalen_johansen"]:
                        xs.append(row["predicted_cumulative_pd"])
                        ys.append(row["observed_aalen_johansen"])
            ax[j].scatter(xs, ys, marker=mk, s=9, facecolors="none" if rid == "L2-cox" else "0.2", edgecolors="0.2", linewidths=0.6,
                          label=RUNG_NAME[rid])
        ax[j].plot([lo, hi], [lo, hi], color="0.5", linewidth=0.8)
        ax[j].set_xscale("log")
        ax[j].set_yscale("log")
        ax[j].set_xlim(lo, hi)
        ax[j].set_ylim(lo, hi)
        ax[j].set_title(f"{k} months")
        ax[j].set_xlabel("Predicted cumulative PD")
        if j == 0:
            ax[j].set_ylabel("Observed (Aalen-Johansen)")
            ax[j].legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, HERE, "provisions-decile-calibration")


def pch_vs_cox() -> None:
    import matplotlib.pyplot as plt

    pbs, gap = [], []
    for d in DATES:
        p = next(x for x in figkit.doc(f"C06/models-rd-{d}.json")["model"] if x["id"] == "L3-pch")
        ev = p["details"]["evaluation"]
        pbs.append(ev["integrated_brier"]["pch"] - ev["integrated_brier"]["cox"])
        gap.append(ev["mean_abs_decile_gap_aalen_johansen"]["pch_mean"] - ev["mean_abs_decile_gap_aalen_johansen"]["cox_mean"])
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for a, vals, title in ((ax[0], pbs, "(a) Pooled Brier score"), (ax[1], gap, "(b) Mean absolute decile gap")):
        a.bar(range(6), vals, color=["0.75" if x < 0 else "0.25" for x in vals], edgecolor="k", linewidth=0.5)
        a.axhline(0, color="k", linewidth=0.8)
        a.set_xticks(range(6))
        a.set_xticklabels(DATES, rotation=45, ha="right")
        a.set_title(title)
        a.set_ylabel("PC-Hazard minus Cox (negative: PC-Hazard better)")
    fig.tight_layout()
    figkit.save(fig, HERE, "provisions-pch-vs-cox")


def ecl_by_stage() -> None:
    import matplotlib.pyplot as plt

    s1, s2, nl, ratio = [], [], [], []
    for d in DATES:
        v = figkit.doc(f"C06/rd-{d}.json")
        s1.append(v["impact"]["ecl_stage1"]["value"] / 1e9)
        s2.append(v["impact"]["ecl_stage2"]["value"] / 1e9)
        nl.append(v["impact"]["nl_index"]["value"])
        ratio.append(v["impact"]["ecl_backtest_ratio"]["value"])
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax[0].bar(range(6), s1, color="0.7", edgecolor="k", linewidth=0.5, label="Stage 1")
    ax[0].bar(range(6), s2, bottom=s1, color="0.25", edgecolor="k", linewidth=0.5, label="Stage 2")
    ax[0].set_xticks(range(6))
    ax[0].set_xticklabels(DATES, rotation=45, ha="right")
    ax[0].set_ylabel("Expected credit loss (USD billion)")
    ax[0].set_title("(a) By stage")
    ax[0].legend(frameon=False)
    ax[1].plot(range(6), ratio, **figkit.STYLES[0], label="Realised / 12-month ECL")
    ax[1].axhline(1.0, color="0.5", linewidth=0.8)
    ax[1].set_xticks(range(6))
    ax[1].set_xticklabels(DATES, rotation=45, ha="right")
    ax[1].set_ylabel("Ratio of realised loss to ECL")
    ax[1].set_title("(b) Backtest and non-linearity")
    tw = ax[1].twinx()
    tw.plot(range(6), nl, **figkit.STYLES[1], label="Non-linearity index")
    tw.axhline(0, color="0.8", linewidth=0.6)
    tw.set_ylabel("Non-linearity index")
    h1, l1 = ax[1].get_legend_handles_labels()
    h2, l2 = tw.get_legend_handles_labels()
    ax[1].set_ylim(0.0, 1.45)
    tw.set_ylim(-0.003, 0.034)
    ax[1].legend(h1 + h2, l1 + l2, frameon=True, framealpha=0.95, fontsize=6.5, loc="upper right")
    fig.tight_layout()
    figkit.save(fig, HERE, "provisions-ecl-by-stage")


def regimes() -> None:
    import matplotlib.pyplot as plt

    vals = {k: [] for k in ("provision_cmf_b1", "provision_ifrs9", "provision_bde")}
    for s in SCENARIOS:
        d = figkit.doc(f"C07/{s}.json")
        for k in vals:
            vals[k].append(d["impact"][k]["value"] / 1e9)
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    w = 0.26
    for i, (k, lab, col) in enumerate((("provision_cmf_b1", "CMF B-1", "0.15"), ("provision_ifrs9", "IFRS 9", "0.5"),
                                       ("provision_bde", "BdE Annex 9", "0.8"))):
        ax.bar([x + (i - 1) * w for x in range(6)], vals[k], width=w, color=col, edgecolor="k", linewidth=0.5, label=lab)
    ax.set_xticks(range(6))
    ax.set_xticklabels(SCEN_SHORT, fontsize=7)
    ax.set_ylabel("Provision (CLP billion)")
    ax.legend(frameon=False)
    fig.tight_layout()
    figkit.save(fig, HERE, "provisions-regimes")


def gap_bridge() -> None:
    import matplotlib.pyplot as plt

    d = figkit.doc("C07/base.json")
    b1 = d["impact"]["provision_cmf_b1"]["value"] / 1e9
    steps = d["outputs"]["gap_bridge"]["steps"]
    names = ["Measurement\nbasis", "Lifetime on\nStage 2", "Scenario\nweighting", "Discounting", "B-1\nminimum", "Overlays"]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    level = b1
    ax.bar(0, b1, color="0.15", edgecolor="k", linewidth=0.5)
    for i, s in enumerate(steps, start=1):
        a = s["amount"] / 1e9
        ax.bar(i, a, bottom=level, color="0.75" if a >= 0 else "0.45", edgecolor="k", linewidth=0.5)
        level += a
    ax.bar(len(steps) + 1, level, color="0.15", edgecolor="k", linewidth=0.5)
    ax.set_xticks(range(len(steps) + 2))
    ax.set_xticklabels(["CMF B-1"] + names + ["IFRS 9"], fontsize=7)
    ax.set_ylabel("Provision (CLP billion)")
    ax.set_ylim(0, b1 * 1.1)
    fig.tight_layout()
    figkit.save(fig, HERE, "provisions-gap-bridge")


def sba_vintages() -> None:
    import matplotlib.pyplot as plt

    pts = set()
    for f in ("fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"):
        for r in figkit.doc(f"C03/{f}.json")["outputs"]["vintage_summary"]["rows"]:
            if r["mark_observed"]:
                pts.add((r["fiscal_year"], r["observed_5y_pd"] * 100))
    pts = sorted(pts)
    fig, ax = plt.subplots(figsize=(5.2, 2.9))
    ax.plot([p[0] for p in pts], [p[1] for p in pts], **figkit.STYLES[0])
    ax.set_xlabel("Approval fiscal year")
    ax.set_ylabel("Charged off within 60 months (%)")
    fig.tight_layout()
    figkit.save(fig, HERE, "provisions-sba-vintages")


def main() -> None:
    figkit.style()
    for fn in (lifetime_curves, decile_calibration, pch_vs_cox, ecl_by_stage, regimes, gap_bridge, sba_vintages):
        fn()
    print("figures written to", HERE)


if __name__ == "__main__":
    main()
