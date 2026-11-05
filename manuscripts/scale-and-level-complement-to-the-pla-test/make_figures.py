"""Write the figures of the manuscript (vector PDF, grayscale-safe) from ``experiments/results.json``,
``experiments/results_theory.json``, the cached statistic rows of ``experiments/simulate.py`` and the C13 generator.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/scale-and-level-complement-to-the-pla-test/make_figures.py \
        [--cache D:/_Temp/ms-scale-and-level-complement-to-the-2026-11-04/cache]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import matplotlib.ticker
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import figkit  # noqa: E402
import stats_core as sc  # noqa: E402
import theory  # noqa: E402

R = json.loads((HERE / "experiments" / "results.json").read_text(encoding="utf-8"))
RT = json.loads((HERE / "experiments" / "results_theory.json").read_text(encoding="utf-8"))
OUT = HERE / "figures"
DEFAULT_CACHE = pathlib.Path("D:/_Temp/ms-scale-and-level-complement-to-the-2026-11-04/cache")
S = figkit.STYLES


def fig_mechanism() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.5), sharey=True)
    k = np.ones(20) / 20
    for ax, did, title in ((axes[0], "none", "No deficiency (case seed 13, replication 0)"),
                           (axes[1], "stale-volatility", "Volatility input 20 days old")):
        rep = sc.generator.replicate(did, 0, 13)
        h = np.convolve(np.abs(rep.hpl), k, "valid") * 100
        r = np.convolve(np.abs(rep.rtpl), k, "valid") * 100
        x = np.arange(h.size) + 20
        ax.plot(x, h, **{**S[0], "marker": None}, label="20-day mean of |HPL|")
        ax.plot(x, r, **{**S[1], "marker": None}, label="20-day mean of |RTPL|")
        ax.set_title(title)
        ax.set_xlabel("Day of the 250-day window")
    axes[0].set_ylabel("Mean absolute P\\&L (\\% of notional)".replace("\\", ""))
    h, lab = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.legend(h, lab, loc="lower center", ncol=2, frameon=False, fontsize=8)
    figkit.save(fig, OUT, "mechanism")


def fig_power_lag() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    lad = R["ladder"]
    lags = [x["lag"] for x in lad]
    series = [("pla", "Regulatory zone"), ("desk", "Desk back-test"), ("ljung_box_sq", "Ljung-Box, squared residual"),
              ("wald_ols", "MZ Wald, OLS"), ("wald_hc3", "MZ Wald, HC3"), ("abs_spearman", "Spearman, absolute values"),
              ("roll20", "Spearman, rolling means"), ("union", "Union of the three")]
    for i, (key, label) in enumerate(series):
        y = [100 * x[key]["rate"] for x in lad]
        ax.plot(lags, y, label=label, **S[i % len(S)])
    ax.set_xscale("log")
    ax.set_xticks(lags, [str(x) for x in lags])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("Age of the volatility input of the risk model (days)")
    ax.set_ylabel("Replications flagged (%)")
    ax.set_ylim(-3, 103)
    ax.legend(frameon=False, fontsize=7, loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    figkit.save(fig, OUT, "power-by-lag")


def fig_distributions(cache: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    null = np.vstack([np.load(cache / f"null_{cs}.npy") for cs in range(5013, 5023)])
    i = sc.IDX["roll20"]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7))
    bins = np.linspace(0.0, 1.0, 81)
    ax = axes[0]
    ax.hist(null[:, i], bins=bins, histtype="step", color="0.0", density=True, label="No deficiency (10,000)")
    for name, ls, c in (("ladder_5", "--", "0.35"), ("ladder_10", "-.", "0.5")):
        ax.hist(np.load(cache / f"{name}.npy")[:, i], bins=bins, histtype="step", color=c, ls=ls, density=True, label=f"Lag {name.split('_')[1]} days")
    ax.hist(np.load(cache / "committed_stale-volatility.npy")[:, i], bins=bins, histtype="step", color="0.2", ls=":", density=True, lw=1.6, label="Lag 20 days")
    thr = R["thresholds"]["per_statistic"]["roll20"]
    ax.axvline(thr, color="0.0", lw=0.8)
    ax.set_yscale("log")
    ax.set_xlim(0.2, 1.0)
    ax.set_ylim(0.02, 5000)
    ax.set_xlabel("Spearman of the 20-day rolling means")
    ax.set_ylabel("Density (logarithmic axis)")
    ax.legend(frameon=False, fontsize=6.5, loc="upper left")
    ax = axes[1]
    j = sc.IDX["wald_hc3"]
    bins2 = np.linspace(0, 40, 81)
    ax.hist(np.clip(null[:, j], 0, 40), bins=bins2, histtype="step", color="0.0", density=True, label="No deficiency (10,000)")
    ax.hist(np.clip(np.load(cache / "committed_stale-volatility.npy")[:, j], 0, 40), bins=bins2, histtype="step", color="0.35", ls="--", density=True, label="Lag 20 days")
    ax.axvline(R["thresholds"]["per_statistic"]["wald_hc3"], color="0.0", lw=0.8)
    ax.set_xlabel("Wald statistic of (a, b) = (0, 1), HC3 (clipped at 40)")
    ax.legend(frameon=False, fontsize=6.5)
    fig.tight_layout()
    figkit.save(fig, OUT, "statistic-distributions")


def fig_roc() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9), sharey=True)
    names = [("roll20", "Rolling-mean Spearman"), ("abs_spearman", "Absolute-value Spearman"), ("wald_hc3", "Wald, HC3"),
             ("wald_ols", "Wald, OLS"), ("ks_reg", "KS distance"), ("spearman_reg", "Spearman of levels")]
    for ax, key, title in ((axes[0], "power_l10", "Volatility input 10 days old"), (axes[1], "power_l20", "Volatility input 20 days old")):
        for i, (k, label) in enumerate(names):
            xs = [100 * b[k]["held_out"] for b in R["by_size"]]
            ys = [100 * b[k][key] for b in R["by_size"]]
            ax.plot(xs, ys, label=label, **S[i % len(S)])
        ax.set_xscale("log")
        ax.set_xlabel("False-alarm rate on held-out null desks (%)")
        ax.set_title(title)
    axes[0].set_ylabel("Replications flagged (%)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    fig.legend(h, lab, loc="lower center", ncol=3, frameon=False, fontsize=7)
    figkit.save(fig, OUT, "power-against-size")


def fig_heatmap() -> None:
    import matplotlib.pyplot as plt

    dets = ["pla", "desk", "cc_975", "wald_ols", "wald_var", "ljung_box_sq", "wald_hc3", "abs_spearman", "roll20", "union"]
    lab = ["Zone", "Desk", "CC 97.5", "MZ OLS", "MZ sq.", "LB sq.", "MZ HC3", "Abs. Sp.", "Roll Sp.", "Union"]
    ids = ["none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment"]
    z = np.array([[100 * R["main"][v][d]["rate"] for d in dets] for v in ids])
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    im = ax.imshow(z, cmap="Greys", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(dets)), lab, rotation=40, ha="right")
    ax.set_yticks(range(len(ids)), [v.replace("-", " ") for v in ids])
    for a in range(z.shape[0]):
        for b in range(z.shape[1]):
            ax.text(b, a, f"{z[a, b]:.0f}", ha="center", va="center", fontsize=7, color="white" if z[a, b] > 55 else "black")
    fig.colorbar(im, ax=ax, label="Replications flagged (%)")
    fig.tight_layout()
    figkit.save(fig, OUT, "detection-map")


def fig_theory() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.8))
    lags = np.arange(0, 81)
    ax = axes[0]
    for i, w in enumerate((5, 10, 20, 40, 60)):
        ax.plot(lags, [theory.rolling_corr(int(L), w) for L in lags], label=f"window {w}", **{**S[i % len(S)], "marker": None})
    rows = {r["lag"]: r for r in RT["rows"]}
    ax.errorbar(list(rows), [rows[L]["T250"]["corr_mean"] for L in rows], yerr=[2 * rows[L]["T250"]["corr_se"] for L in rows], fmt="o", color="0.0",
                ms=3, capsize=2, label="250-day windows, 20-day mean")
    ax.set_xlabel("Age of the volatility input (days)")
    ax.set_ylabel("Correlation of the rolling means")
    ax.legend(frameon=False, fontsize=6.5)
    ax = axes[1]
    sl = R["theory"]["slope_and_rolling_correlation"]
    ax.plot([s["lag"] for s in sl], [s["slope_theory"] for s in sl], label="Closed form", **{**S[0], "marker": None})
    ax.errorbar([s["lag"] for s in sl], [s["slope_mean"] for s in sl], yerr=[2 * s["slope_sd"] / 1000 ** 0.5 for s in sl], fmt="s", color="0.4", ms=3,
                capsize=2, label="Mean over 1,000 C13 desk-years")
    ax.set_xlabel("Age of the volatility input (days)")
    ax.set_ylabel("Mincer-Zarnowitz slope of HPL on RTPL")
    ax.legend(frameon=False, fontsize=6.5)
    fig.tight_layout()
    figkit.save(fig, OUT, "theory-check")


def fig_alt_null() -> None:
    import matplotlib.pyplot as plt

    keys = ["baseline", "phi090", "phi0995", "sd020", "sd050", "res005", "res030"]
    labs = ["Calibration\nnull", "Persist.\n0.90", "Persist.\n0.995", "Disper.\n0.20", "Disper.\n0.50", "Noise\n5%", "Noise\n30%"]
    fig, ax = plt.subplots(figsize=(5.8, 3.0))
    x = np.arange(len(keys))
    for off, (d, name, hatch) in zip((-0.2, 0.0, 0.2), (("roll20", "Rolling-mean Spearman", ""), ("abs_spearman", "Absolute-value Spearman", "//"), ("union", "Union", "xx"))):
        y = np.array([100 * R["altnull"][k][d]["rate"] for k in keys])
        lo = np.array([100 * R["altnull"][k][d]["lo"] for k in keys])
        hi = np.array([100 * R["altnull"][k][d]["hi"] for k in keys])
        ax.bar(x + off, y, 0.2, yerr=[np.maximum(y - lo, 0), np.maximum(hi - y, 0)], color="0.75" if not hatch else "white", edgecolor="0.0", hatch=hatch, capsize=1.5, label=name, lw=0.6)
    ax.axhline(1.0, color="0.0", lw=0.8, ls="--")
    ax.set_yscale("symlog", linthresh=1.0)
    ax.set_ylim(0, 150)
    ax.set_yticks([0, 1, 10, 100], ["0", "1", "10", "100"])
    ax.set_xticks(x, labs, fontsize=7)
    ax.set_ylabel("False-alarm rate (%), thresholds fixed")
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, OUT, "alternative-nulls")


def fig_windows() -> None:
    import matplotlib.pyplot as plt

    abl = {a["config"]: a for a in R["ablation"]}
    cfg = [("window5", 5), ("window10", 10), ("roll_only", 20), ("window40", 40), ("window60", 60)]
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    for i, (t, label) in enumerate((("stale5", "Lag 5 days"), ("stale10", "Lag 10 days"), ("time-misalignment", "Time misalignment, 1 day"), ("omitted-factor", "Omitted factor"))):
        y = [100 * abl[c]["power"][t]["rate"] for c, _ in cfg]
        ax.plot([w for _, w in cfg], y, label=label, **S[i % len(S)])
    ax.set_xlabel("Rolling window (days)")
    ax.set_ylabel("Replications flagged (%)")
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, OUT, "window-ablation")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=pathlib.Path, default=DEFAULT_CACHE)
    cache = ap.parse_args().cache
    figkit.style()
    import matplotlib
    matplotlib.rcParams["text.usetex"] = False
    fig_mechanism()
    fig_power_lag()
    fig_distributions(cache)
    fig_roc()
    fig_heatmap()
    fig_theory()
    fig_alt_null()
    fig_windows()
    print(f"figures written to {OUT}")


if __name__ == "__main__":
    main()
