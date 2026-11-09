"""Write the vector figures of the manuscript into ``figures/`` from ``experiments/*.json``.

    python manuscripts/adaptive-conformal-recalibration-of-var/make_figures.py
"""
from __future__ import annotations

import collections
import pathlib
import statistics as st
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import common  # noqa: E402
import figkit  # noqa: E402

figkit.style()
import matplotlib.pyplot as plt  # noqa: E402

OUT = HERE / "figures"
E2, E3, E4, E5, E6 = (common.load(f"e{i}_{n}.json") for i, n in ((2, "wrap_ladder"), (3, "ablation"), (4, "score_space"), (5, "generators"), (6, "theory")))
ST = figkit.STYLES
WNAME = {"equity-2007-09": "equity 2007-09", "equity-2020": "equity 2020", "rates-2022": "rates 2022"}
MNAME = {"hs-250": "HS-250", "garch-t": "GARCH-t", "fhs": "FHS", "hs-500": "HS-500", "awhs": "AWHS", "dn-rolling": "delta-normal", "ewma": "EWMA",
         "gjr-t": "GJR-t", "egarch-t": "EGARCH-t", "evt-mf": "cond. EVT"}


def fig_level_paths():
    fig, axs = plt.subplots(3, 3, figsize=(7.2, 5.4), sharey="row")
    for j, w in enumerate(common.STRESS):
        for i, m in enumerate(common.WRAPPED3):
            ax = axs[i, j]
            p = E2["paths"][f"{w}|{m}|0.01"]
            lev = np.array(p["levels"])
            ax.plot(np.arange(lev.size), 100 * lev, color="0.1", lw=0.9)
            ax.axhline(1.0, color="0.5", lw=0.6, ls="--")
            ax.axhline(100 * common.LEVEL_MIN, color="0.7", lw=0.6, ls=":")
            h = p["hit_days"]
            ax.plot(h, [100 * lev[k] for k in h], "v", color="0.35", ms=3)
            if i == 0:
                ax.set_title(WNAME[w])
            if j == 0:
                ax.set_ylabel(f"{MNAME[m]}\nworking level (%)")
            if i == 2:
                ax.set_xlabel("forecast day")
    return figkit.save(fig, OUT, "level-paths")


def fig_hit_rates():
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=False)
    for ax, a in zip(axs, common.LEVELS):
        k = 0
        ticks, labels = [], []
        for w in common.STRESS:
            for m in common.WRAPPED3:
                r = next(x for x in E2["rows"] if x["window"] == w and x["model"] == m and x["alpha"] == a)
                for off, key, mk in ((-0.15, "unwrapped", "o"), (0.15, "wrapped", "s")):
                    s = r[key]
                    ci = r["hit_ci_unwrapped" if key == "unwrapped" else "hit_ci_wrapped"]
                    ax.errorbar(k + off, 100 * s["hit_rate"], yerr=[[100 * (s["hit_rate"] - ci[0])], [100 * (ci[1] - s["hit_rate"])]], fmt=mk,
                                color="0.0" if key == "unwrapped" else "0.5", ms=3.5, lw=0.8, capsize=1.5)
                ticks.append(k)
                labels.append(f"{MNAME[m]}\n{WNAME[w].replace('equity ', 'eq. ')}")
                k += 1
        ax.axhline(100 * a, color="0.4", lw=0.7, ls="--")
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=90, fontsize=6)
        ax.set_ylabel("hit rate (%)")
        ax.set_title(f"target level {100 * a:g}%")
    axs[0].plot([], [], "o", color="0.0", label="unwrapped")
    axs[0].plot([], [], "s", color="0.5", label="wrapped")
    axs[0].legend(loc="upper left")
    fig.tight_layout()
    return figkit.save(fig, OUT, "hit-rates")


def fig_fz0():
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
    models = E2["models"]
    for ax, a in zip(axs, common.LEVELS):
        for wi, w in enumerate(common.STRESS):
            xs, ys, lo, hi = [], [], [], []
            for mi, m in enumerate(models):
                r = next(x for x in E2["rows"] if x["window"] == w and x["model"] == m and x["alpha"] == a)
                xs.append(mi + (wi - 1) * 0.22)
                ys.append(100 * r["fz0_change"])
                lo.append(100 * (r["fz0_change"] - r["ci95"][0]))
                hi.append(100 * (r["ci95"][1] - r["fz0_change"]))
            ax.errorbar(xs, ys, yerr=[lo, hi], fmt=("o", "s", "^")[wi], ms=3, lw=0.7, capsize=1.2, color=("0.0", "0.4", "0.6")[wi], label=WNAME[w])
        ax.axhline(5, color="0.2", lw=0.8, ls="--")
        ax.axhline(0, color="0.6", lw=0.5)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([MNAME[m] for m in models], rotation=60, ha="right", fontsize=6.5)
        ax.set_title(f"target level {100 * a:g}%")
        ax.set_ylim(-60, 20)
    axs[0].set_ylabel("change of mean FZ0 (%), wrapped against unwrapped")
    axs[0].legend(loc="lower left", fontsize=6.5)
    fig.tight_layout()
    return figkit.save(fig, OUT, "fz0-change")


def fig_ladder():
    u = {(r["window"], r["model"], r["alpha"]): r["passes"] for r in E4["rows"] if r["method"] == "unwrapped"}
    wr = {(r["window"], r["model"], r["alpha"]): common.passes(r["wrapped"]) for r in E2["rows"]}
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, a in zip(axs, common.LEVELS):
        for wi, w in enumerate(common.STRESS):
            models = sorted({m for (ww, m, aa) in u if ww == w and aa == a})
            n0 = sum(u[(w, m, a)] for m in models)
            n3 = sum(wr[(w, m, a)] if m in common.WRAPPED3 else u[(w, m, a)] for m in models)
            n10 = sum(wr[(w, m, a)] if (w, m, a) in wr else u[(w, m, a)] for m in models)
            for k, (v, hatch, col) in enumerate(((n0, "", "0.15"), (n3, "//", "0.5"), (n10, "..", "0.8"))):
                ax.bar(wi + (k - 1) * 0.27, v, 0.25, color=col, edgecolor="0.0", hatch=hatch, lw=0.5)
        ax.set_xticks(range(3))
        ax.set_xticklabels([WNAME[w] for w in common.STRESS])
        ax.set_title(f"target level {100 * a:g}%")
    axs[0].set_ylabel("ladder models passing (of 18)")
    for lab, (hatch, col) in zip(("none wrapped", "three wrapped", "ten wrapped"), (("", "0.15"), ("//", "0.5"), ("..", "0.8"))):
        axs[0].bar([0], [0], color=col, edgecolor="0.0", hatch=hatch, label=lab)
    axs[0].legend(loc="upper left", fontsize=6.5)
    fig.tight_layout()
    return figkit.save(fig, OUT, "ladder-pass")



def fig_generators():
    G = collections.defaultdict(list)
    for r in E5["rows"]:
        G[(r["scenario"], r["model"], r["alpha"], r["method"])].append(r)
    fig, axs = plt.subplots(2, 3, figsize=(7.2, 4.4), sharey=True)
    methods = ("unwrapped", "aci", "rolling", "tracker")
    names = {"unwrapped": "unwrapped", "aci": "level wrapper", "rolling": "rolling scale", "tracker": "quantile tracker"}
    for i, a in enumerate(common.LEVELS):
        for j, m in enumerate(common.WRAPPED3):
            ax = axs[i, j]
            for k, me in enumerate(methods):
                ys, lo, hi = [], [], []
                for s in E5["scenarios"]:
                    rs = G[(s, m, a, me)]
                    kk = sum(x["passes"] for x in rs)
                    l, h = common.wilson(kk, len(rs))
                    ys.append(kk / len(rs))
                    lo.append(kk / len(rs) - l)
                    hi.append(h - kk / len(rs))
                ax.errorbar(np.arange(4) + (k - 1.5) * 0.15, ys, yerr=[lo, hi], fmt=ST[k]["marker"], color=ST[k]["color"], ms=3.2, lw=0.7, capsize=1.2,
                            label=names[me])
            ax.set_xticks(range(4))
            ax.set_xticklabels(["no shift", "crisis", "crash", "drift"], fontsize=7)
            if i == 0:
                ax.set_title(MNAME[m])
            if j == 0:
                ax.set_ylabel(f"pass rate, level {100 * a:g}%")
            ax.set_ylim(0, 1.05)
    axs[0, 0].legend(loc="lower left", fontsize=6)
    fig.tight_layout()
    return figkit.save(fig, OUT, "generator-pass")


def fig_gamma():
    V = collections.defaultdict(list)
    for r in E3["rows"]:
        if r["window"] in common.STRESS:
            V[r["variant"]].append(r)
    order = [("off", 0.0), ("gamma-0.001", 0.001), ("gamma-0.0025", 0.0025), ("full", 0.005), ("gamma-0.01", 0.01), ("gamma-0.02", 0.02), ("gamma-0.05", 0.05)]
    xs = np.arange(len(order))
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6))
    pas = [sum(r["passes"] for r in V[v]) for v, _ in order]
    dev = [100 * st.mean(abs(r["scores"]["hit_rate"] - r["alpha"]) for r in V[v]) for v, _ in order]
    worst = [100 * max([r["fz0_change"] for r in V[v] if r["fz0_change"] is not None] or [0]) for v, _ in order]
    for ax, y, lab in zip(axs, (pas, dev, worst), ("cells passing (of 18)", "mean |hit rate - target| (points)", "worst FZ0 change (%)")):
        ax.plot(xs, y, "o-", color="0.1", ms=3.5)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{g:g}" for _, g in order], rotation=60, fontsize=7)
        ax.set_xlabel("step gamma")
        ax.set_ylabel(lab)
    axs[2].axhline(5, color="0.4", ls="--", lw=0.7)
    fig.tight_layout()
    return figkit.save(fig, OUT, "gamma-sweep")


def fig_scale():
    C = E6["C"]["rows"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for k, a in enumerate(common.LEVELS):
        rows = [r for r in C if r["alpha"] == a]
        c = [r["scale_ratio"] for r in rows]
        axs[0].plot(c, [100 * r["hit_rate"] for r in rows], marker=ST[k]["marker"], color=ST[k]["color"], ls=ST[k]["linestyle"], label=f"level {100 * a:g}%")
        axs[0].axvline(rows[0]["c_max"], color=ST[k]["color"], lw=0.6, ls=":")
        axs[1].plot(c, [100 * r["a_star"] for r in rows], marker=ST[k]["marker"], color=ST[k]["color"], ls=ST[k]["linestyle"], label=f"fixed point, {100 * a:g}%")
        axs[1].plot(c, [100 * r["level_mean"] for r in rows], marker=ST[k]["marker"], mfc="none", color=ST[k]["color"], ls="none", label=f"simulated mean, {100 * a:g}%")
    axs[1].axhline(100 * common.LEVEL_MIN, color="0.5", lw=0.7, ls=":")
    axs[1].set_yscale("log")
    axs[0].set_xlabel("scale ratio c of the data to the model")
    axs[1].set_xlabel("scale ratio c of the data to the model")
    axs[0].set_ylabel("long-run hit rate (%)")
    axs[1].set_ylabel("working level (%)")
    axs[0].legend(fontsize=7)
    axs[1].legend(fontsize=6)
    fig.tight_layout()
    return figkit.save(fig, OUT, "scale-sweep")


def fig_methods():
    rows = collections.defaultdict(list)
    for r in E4["rows"]:
        if r["window"] in common.STRESS and r["model"] in E2["models"]:
            rows[r["method"]].append(r["passes"])
    rows["level wrapper"] = [common.passes(r["wrapped"]) for r in E2["rows"] if r["window"] in common.STRESS]
    order = [("unwrapped", "unwrapped"), ("level wrapper", "level wrapper"), ("rolling", "rolling scale"), ("tracker-eta-0.01", "tracker 0.01"),
             ("tracker", "tracker 0.05"), ("tracker-eta-0.2", "tracker 0.2")]
    fig, ax = plt.subplots(figsize=(4.8, 2.8))
    ax.barh(range(len(order)), [sum(rows[k]) for k, _ in order], color="0.55", edgecolor="0.0")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([n for _, n in order])
    ax.invert_yaxis()
    ax.set_xlabel("cells passing (of 60): ten models, two levels, three windows")
    fig.tight_layout()
    return figkit.save(fig, OUT, "methods-pass")


if __name__ == "__main__":
    for f in (fig_level_paths, fig_hit_rates, fig_fz0, fig_ladder, fig_generators, fig_gamma, fig_scale, fig_methods):
        print("wrote", f())
