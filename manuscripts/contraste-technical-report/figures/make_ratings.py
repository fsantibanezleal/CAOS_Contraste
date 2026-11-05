"""Figures of the ratings chapter of the technical report (``sections/07-ratings.tex``): vector PDFs ``figures/ratings-*.pdf``
drawn from the committed artifacts of cases C04 and C05 through ``figkit``; the quantities come from ``compute`` of
``tables/make_ratings.py`` so that a figure and the table or sentence beside it read one computation.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_ratings.py
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

_spec = importlib.util.spec_from_file_location("ratings_tables", HERE.parent / "tables" / "make_ratings.py")
tables = importlib.util.module_from_spec(_spec)
sys.modules["ratings_tables"] = tables
_spec.loader.exec_module(tables)

S = figkit.STYLES


def fig_zfactor(R) -> None:
    import matplotlib.pyplot as plt

    sp = R["agencies"]["sp"]
    years = [int(y) for y in sp["labels"]]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    for i, g in enumerate(tables.ZGRADES):
        z = sp["z"][g]["z"]
        ax.plot(years, z, label=f"{tables.GRADES[g]} (n = {sp['z'][g]['n']})", **S[i])
    ax.axhline(0.0, color="0.5", linewidth=0.6)
    ax.axhspan(-1.0, 1.0, color="0.92", zorder=0)
    ax.set_xlabel("cohort year")
    ax.set_ylabel("implied credit-cycle factor $\\hat z_t$")
    ax.legend(ncol=3, loc="lower right", frameon=False)
    fig.tight_layout()
    figkit.save(fig, HERE, "ratings-zfactor")


def fig_calibration(R) -> None:
    import matplotlib.pyplot as plt

    shown = (("A1-idp", "Invariant default profile"), ("A2-iar", "Invariant accuracy ratio"), ("A3-spd", "Scaled PDs"),
             ("A4-slr", "Scaled likelihood ratio"), ("C1-ipc", "2009 curve unchanged"))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    for ax, y in zip(axes, (2010, 2011)):
        o = R["cal"][y]["o"]
        x = np.arange(len(o["grades"]))
        for i, (aid, label) in enumerate(shown):
            ax.plot(x, 100 * np.array(o["approaches"][aid]["curve"]), label=label, **S[i])
        obs = 100 * np.array(o["default_rate1"])
        pos = obs > 0
        ax.scatter(x[pos], obs[pos], s=14, facecolors="none", edgecolors="0.0", zorder=5, label=f"observed {y} (rate above zero)")
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels(o["grades"], rotation=90, fontsize=6)
        ax.set_title(f"Forecast for {y}")
        ax.set_xlabel("grade")
    axes[0].set_ylabel("PD or default rate (%)")
    axes[0].legend(fontsize=6, frameon=False, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, HERE, "ratings-calibration")


def fig_ldp(R) -> None:
    import matplotlib.pyplot as plt

    lo = R["ldp"]
    gam = np.array(lo["gammas"])
    ind, cor = np.array(lo["bounds"]["independent"]), np.array(lo["bounds"]["correlated"])
    x = np.arange(len(gam))
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    k = 0
    for ai, a in enumerate(tables.LDP_GRADES):
        ax.plot(x, 100 * ind[:, ai], label=f"{a}, independent", **S[k])
        k += 1
    for ai, a in enumerate(tables.LDP_GRADES):
        st = dict(S[ai])
        st["linestyle"] = "-"
        st["marker"] = "x"
        st["color"] = str(0.15 + 0.2 * ai)
        ax.plot(x, 100 * cor[:, ai], label=f"{a}, correlation 12%", **st)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{100 * g:g}%" for g in gam])
    ax.set_xlabel("confidence level $\\gamma$")
    ax.set_ylabel("most prudent PD bound (%)")
    ax.legend(fontsize=6.5, ncol=2, frameon=False, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, HERE, "ratings-ldp-bounds")


def fig_estimators(R) -> None:
    import matplotlib.pyplot as plt

    est = R["markov"]["est"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.2), gridspec_kw={"width_ratios": [2.2, 1.0]})
    x = np.arange(len(tables.GRADES))
    for i, (k, label) in enumerate(tables.ESTIMATORS):
        rel = np.array(est[k]["rmse"]) / np.array(est[k]["truth"])
        a.plot(x, rel, label=label, **S[i])
    a.set_yscale("log")
    a.set_xticks(x)
    a.set_xticklabels(tables.GRADES)
    a.set_xlabel("grade")
    a.set_ylabel("RMSE of the one-year PD over its truth")
    a.legend(fontsize=6.5, frameon=False, ncol=2, loc="upper right")
    zero = [r["rate"] for r in est["cohort"]["zero"]]
    b.bar(x, 100 * np.array(zero), color="0.4")
    b.set_xticks(x)
    b.set_xticklabels(tables.GRADES, rotation=90, fontsize=7)
    b.set_xlabel("grade")
    b.set_ylabel("panels with a zero cohort PD (%)")
    fig.tight_layout()
    figkit.save(fig, HERE, "ratings-estimators")


def fig_ttc(R) -> None:
    import matplotlib.pyplot as plt

    eng = R["pub"]["engelmann"]
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    labels = {"W_init": "initial portfolio 1", "W_init 2": "initial portfolio 2", "W tilde": "initial portfolio 3", "W hat": "initial portfolio 4"}
    for i, pf in enumerate(eng["portfolios"]):
        path = 100 * np.array(pf["pd_path"])
        ax.plot(np.arange(len(path)), path, label=labels[pf["name"]], **{**S[i], "marker": None})
    ax.axhline(100 * eng["ttc_pd"]["recomputed"], color="0.0", linewidth=0.7, linestyle=(0, (1, 2)))
    ax.text(len(eng["portfolios"][0]["pd_path"]) - 1, 100 * eng["ttc_pd"]["recomputed"], " TTC portfolio PD", va="bottom", ha="right", fontsize=7)
    ax.set_xlabel("projection year")
    ax.set_ylabel("portfolio default rate (%)")
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    figkit.save(fig, HERE, "ratings-ttc-drift")


def main() -> None:
    figkit.style()
    R = tables.compute()
    fig_zfactor(R)
    fig_calibration(R)
    fig_ldp(R)
    fig_estimators(R)
    fig_ttc(R)
    print("wrote", sorted(p.name for p in HERE.glob("ratings-*.pdf")))


if __name__ == "__main__":
    main()
