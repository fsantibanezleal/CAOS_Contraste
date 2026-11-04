"""The figures of the chapter on interest rate risk in the banking book and liquidity of the technical report
(``sections/13-alm.tex``), as vector PDF in ``manuscripts/contraste-technical-report/figures/alm-*.pdf``, drawn from the committed
artifacts of cases C14, C15 and C16 under ``data/derived`` with the shared style of ``manuscripts/_shared/figkit.py``
(readable in grayscale).

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_alm.py
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

DATES = ["2021-q4", "2022-q2", "2022-q4"]
DATE_LABEL = {"2021-q4": "2021-Q4", "2022-q2": "2022-Q2", "2022-q4": "2022-Q4"}
SHOCKS = ["parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down"]
SHOCK_SHORT = ["Parallel\nup", "Parallel\ndown", "Steepener", "Flattener", "Short\nup", "Short\ndown"]
HATCH = ["", "//", ".."]
SHADE = ["0.15", "0.5", "0.8"]


def scen(doc: dict, cal: str, nmd: str) -> dict:
    return next(s for s in doc["outputs"]["scenarios"] if s["calibration"] == cal and s["nmd_assumption"] == nmd)


def shapes() -> None:
    """The prescribed shock shapes at the 19 bucket midpoints, as the artifact of 2022-Q2 holds them (2024 sizes)."""
    import matplotlib.pyplot as plt

    d = figkit.doc("C14/vd-2022-q2.json")
    s = scen(d, "2024", "behavioural")
    t = [b["midpoint_years"] for b in figkit.doc("C14/models-svb-2021-2022.json")["fit"]["buckets"]]
    fig, ax = plt.subplots(figsize=(6.2, 3.1))
    names = {"parallel-up": "Parallel up", "steepener": "Steepener", "flattener": "Flattener", "short-up": "Short up", "short-down": "Short down"}
    for k, sh in enumerate(["parallel-up", "steepener", "flattener", "short-up", "short-down"]):
        row = next(r for r in s["shocks"] if r["shock"] == sh)
        ax.plot(t, row["shape_bp"], label=names[sh], **figkit.STYLES[k], markevery=1)
    ax.axhline(0, color="0.6", linewidth=0.6)
    ax.set_xlabel("Bucket midpoint (years)")
    ax.set_ylabel("Shift of the zero rate (bp)")
    ax.set_title("USD shock shapes of the 2024 size table (200, 300 and 225 bp)")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    figkit.save(fig, HERE, "alm-shapes")


def c14_eve() -> None:
    """Change in EVE as a share of Tier 1 by shock and date, for the two treatments of non-maturity deposits."""
    import matplotlib.pyplot as plt

    docs = {d: figkit.doc(f"C14/vd-{d}.json") for d in DATES}
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
    w = 0.26
    for j, nmd in enumerate(("behavioural", "contractual")):
        for k, d in enumerate(DATES):
            s = scen(docs[d], "2024", nmd)
            vals = [100 * next(r for r in s["shocks"] if r["shock"] == sh)["delta_eve"] / s["outlier"]["tier1"] for sh in SHOCKS]
            ax[j].bar([i + (k - 1) * w for i in range(6)], vals, w, label=DATE_LABEL[d], color=SHADE[k], edgecolor="k", linewidth=0.4, hatch=HATCH[k])
        ax[j].axhline(15, color="k", linestyle="--", linewidth=0.9)
        ax[j].axhline(0, color="0.5", linewidth=0.5)
        ax[j].set_xticks(range(6))
        ax[j].set_xticklabels(SHOCK_SHORT, fontsize=7)
        ax[j].set_title("(a) Capped behavioural core split" if j == 0 else "(b) Every deposit slotted overnight")
    ax[0].set_ylabel("Change in EVE (% of Tier 1)")
    ax[0].text(5.4, 17, "15% threshold", ha="right", fontsize=7)
    ax[0].legend(frameon=False, fontsize=7, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, HERE, "alm-c14-eve")


def c14_gap() -> None:
    """The repricing gap by bucket at 2022-Q2 under the two treatments of non-maturity deposits."""
    import matplotlib.pyplot as plt

    d = figkit.doc("C14/vd-2022-q2.json")
    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    w = 0.38
    for k, nmd in enumerate(("behavioural", "contractual")):
        lad = next(x for x in d["outputs"]["ladder"] if x["nmd_assumption"] == nmd)
        gaps = [g["gap"] / 1e6 for g in lad["repricing_gap"]]
        ax.bar([i + (k - 0.5) * w for i in range(19)], gaps, w, label="Capped behavioural" if k == 0 else "Every deposit overnight",
               color=SHADE[k * 2], edgecolor="k", linewidth=0.4, hatch=HATCH[k])
    ax.axhline(0, color="0.5", linewidth=0.5)
    ax.set_xticks(range(19))
    ax.set_xticklabels([str(i + 1) for i in range(19)], fontsize=7)
    ax.set_xlabel("Repricing bucket (1 overnight, 19 beyond 20 years)")
    ax.set_ylabel("Repricing gap (USD bn)")
    ax.set_title("Repricing gap of Silicon Valley Bank at 30 June 2022")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, HERE, "alm-c14-gap")


def c15_annex1() -> None:
    """The prioritisation ratios of the six variants of Banco Andino against their thresholds."""
    import matplotlib.pyplot as plt

    variants = ["long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active"]
    labels = ["Long UF", "Short UF", "CPI surprise", "CLP steepener", "Offset on\nand off", "Floor-exposed\nUF book"]
    docs = {v: figkit.doc(f"C15/{v}.json")["outputs"] for v in variants}
    fig, ax = plt.subplots(1, 3, figsize=(7.4, 3.0), sharey=True)
    names = ["EVE / Tier 1 (threshold 15%)", "NII with charge / Tier 1 (threshold 5%)", "NII / 12-month margin (threshold 18%)"]
    for j in range(3):
        vals = [100 * docs[v]["thresholds"]["tests"][[1, 0, 2][j]]["ratio"] for v in variants]
        thr = 100 * docs[variants[0]]["thresholds"]["tests"][[1, 0, 2][j]]["threshold"]
        shade = ["0.15" if x > thr else "0.75" for x in vals]
        ax[j].barh(range(6), vals, color=shade, edgecolor="k", linewidth=0.4)
        ax[j].axvline(thr, color="k", linestyle="--", linewidth=0.9)
        ax[j].set_title(names[j], fontsize=7)
        ax[j].set_xlabel("%")
    ax[0].set_yticks(range(6))
    ax[0].set_yticklabels(labels, fontsize=7)
    ax[0].invert_yaxis()
    fig.tight_layout()
    figkit.save(fig, HERE, "alm-c15-annex1")


def c16_nlp() -> None:
    """The net liquidity position against the relevant day for three ladders, with the survival period marked."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    spec = [("list-adverse", "LiST Adverse"), ("list-extreme", "LiST Extreme"), ("htm-losses", "Adverse with HTM losses in the CBC")]
    for k, (v, name) in enumerate(spec):
        o = figkit.doc(f"C16/{v}.json")["outputs"]
        lad = o["path"]["ladder"]
        x = lad["day_index"]
        y = [a / 1e6 for a in lad["nlp"]]
        ax.plot(x, y, label=name, color=figkit.STYLES[k]["color"], linestyle=figkit.STYLES[k]["linestyle"])
        day = o["path"]["survival"]["day"]
        if day is not None:
            ax.plot([day], [y[day - 1]], marker=figkit.STYLES[k]["marker"], color="k", markersize=5)
    ax.axhline(0, color="0.5", linewidth=0.6)
    ax.set_xlabel("Relevant day after 31 December 2022")
    ax.set_ylabel("Net liquidity position (USD bn)")
    ax.set_title("Net liquidity position; markers show the survival period")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, HERE, "alm-c16-nlp")


def c16_reverse() -> None:
    """Survival period against the run-off multiplier for the three base scenarios, with the 30-day target."""
    import matplotlib.pyplot as plt

    rv = figkit.doc("C16/reverse-stress.json")["outputs"]
    fig, ax = plt.subplots(figsize=(6.2, 3.1))
    for k, b in enumerate(rv["bases"]):
        pts = [(c["multiplier"], c["survival"]["day"] if c["survival"]["day"] is not None else b["base_survival"]["horizon_days"]) for c in b["curve"]]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], label=b["label"]["en"], **figkit.STYLES[k])
        if b["solved"]["status"] == "solved":
            ax.plot([b["solved"]["multiplier"]], [b["solved"]["survival_at_multiplier"]], marker="*", color="k", markersize=9, linestyle="none")
    ax.axhline(rv["target"]["days"], color="k", linestyle="--", linewidth=0.8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Run-off multiplier on every daily rate")
    ax.set_ylabel("Survival period (days; horizon if none)")
    ax.set_title("Reverse stress: stars mark the multiplier that reaches 30 days")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, HERE, "alm-c16-reverse")


def main() -> None:
    figkit.style()
    shapes()
    c14_eve()
    c14_gap()
    c15_annex1()
    c16_nlp()
    c16_reverse()
    print("6 figures")


if __name__ == "__main__":
    main()
