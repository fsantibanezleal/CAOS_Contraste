"""Figures of the market-risk section of the technical report (sections/11-market.tex).

Every figure is a vector PDF drawn from the committed documents of cases C11, C13 and C22 (``data/derived``) through ``figkit``;
the binomial curve of the traffic-light figure is evaluated with SciPy and checked against the committed table of the models
document. Output: ``figures/market-*.pdf``.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_market.py
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

_spec = importlib.util.spec_from_file_location("mk_tables", HERE.parent / "tables" / "make_market.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)  # type: ignore[union-attr]

W = 6.3  # text width in inches
HATCH = ["", "//", "..", "xx"]


def fig_hitrate(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt
    from scipy.stats import binom

    fig, ax = plt.subplots(figsize=(W, 3.3))
    rng = np.random.default_rng(0)
    for i, w in enumerate(T.WINDOWS):
        n = T.n_days(D, w)
        exp = 0.01 * n
        lo, hi = binom.ppf(0.025, n, 0.01) / exp, binom.ppf(0.975, n, 0.01) / exp
        ax.add_patch(plt.Rectangle((i - 0.4, lo), 0.8, hi - lo, facecolor="0.88", edgecolor="0.6", linewidth=0.6, zorder=0))
        for mid in T.MNAME:
            r = T.level(T.models(D, w)[mid], 0.01)["n_exceedances"] / exp
            if mid == "nn-fz":
                continue
            ax.plot(i + rng.uniform(-0.3, 0.3), r, marker="o", color="0.45", markersize=3, linestyle="none", zorder=2)
        r = T.level(T.models(D, w)["nn-fz"], 0.01)["n_exceedances"] / exp
        ax.plot(i, r, marker="D", color="black", markersize=6, linestyle="none", zorder=3)
    ax.axhline(1.0, color="0.2", linestyle="--", linewidth=0.8)
    ax.set_xticks(range(len(T.WINDOWS)))
    ax.set_xticklabels([T.WLABEL[w].replace(" ", "\n", 1) for w in T.WINDOWS])
    ax.set_ylabel("Exceedances over expected (99% VaR)")
    ax.set_xlim(-0.6, len(T.WINDOWS) - 0.4)
    ax.set_ylim(0, None)
    ax.plot([], [], marker="o", color="0.45", linestyle="none", markersize=3, label="seventeen ladder models")
    ax.plot([], [], marker="D", color="black", linestyle="none", markersize=6, label="quantile network")
    ax.add_patch(plt.Rectangle((0, 0), 0, 0, facecolor="0.88", edgecolor="0.6", label="95% band of a correct model"))
    ax.legend(loc="lower center", frameon=False, ncol=3, fontsize=7, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout()
    figkit.save(fig, out, "market-hitrate")


def fig_fz0(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(W, 5.6), sharey=True)
    ids = list(T.MNAME)
    for ax, a, title in zip(axes, (0.01, 0.025), ("Tail level 1%", "Tail level 2.5%")):
        mat = np.full((len(ids), len(T.WINDOWS)), np.nan)
        elig = np.zeros_like(mat, dtype=bool)
        for j, w in enumerate(T.WINDOWS):
            ms = T.models(D, w)
            vals = {mid: T.fz0(D, w, mid, a) for mid in ids if T.level(ms[mid], a)["es_status"] == "forecast"}
            best = min(vals.values())
            for i, mid in enumerate(ids):
                if mid in vals:
                    mat[i, j] = vals[mid] - best
                    elig[i, j] = ms[mid]["eligible"]
        cap = np.nanpercentile(mat, 90)
        ax.imshow(np.where(np.isnan(mat), 0, np.minimum(mat, cap)), cmap="Greys", vmin=0, vmax=cap, aspect="auto")
        for i in range(len(ids)):
            for j in range(len(T.WINDOWS)):
                if np.isnan(mat[i, j]):
                    ax.text(j, i, "n/a", ha="center", va="center", fontsize=6, color="0.4")
                else:
                    dark = mat[i, j] > 0.55 * cap
                    ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=6,
                            color="white" if dark else "black", fontweight="bold" if elig[i, j] else "normal")
        ax.set_xticks(range(len(T.WINDOWS)))
        ax.set_xticklabels([T.WLABEL[w].replace(" ", "\n", 1) for w in T.WINDOWS], fontsize=6)
        ax.set_title(title)
        ax.set_yticks(range(len(ids)))
        ax.set_yticklabels([T.MSHORT[m] for m in ids], fontsize=7)
    fig.tight_layout()
    figkit.save(fig, out, "market-fz0")


def fig_rates(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    w = "rates-2022"
    o = D["win"][w]["outputs"]
    dates = np.array(o["grid"]["dates"], dtype="datetime64[D]")
    loss = np.array(o["grid"]["realised_loss"]["loss"], dtype=float)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W, 5.0), sharex=True, gridspec_kw={"height_ratios": [1.5, 1]})
    a1.plot(dates, loss, linestyle="none", marker=".", color="0.65", markersize=3, label="realised loss")
    styles = {"ewma": ("-", "0.6", "EWMA (champion)"), "gjr-t": ("--", "0.3", "GJR-GARCH-t"), "nn-fz": ("-", "0.0", "Quantile network")}
    for mid, (ls, c, lab) in styles.items():
        v = np.array(T.level(T.models(D, w)[mid], 0.01)["var"])
        a1.plot(dates, v, linestyle=ls, color=c, linewidth=1.0 if mid == "nn-fz" else 1.1, label=f"{lab}, 99% VaR")
    nn_days = T.level(T.models(D, w)["nn-fz"], 0.01)["exceedance_days"]
    a1.plot(dates[nn_days], loss[nn_days], linestyle="none", marker="x", color="black", markersize=5, label="network exceedance")
    a1.set_ylabel("Loss, share of portfolio value")
    a1.set_ylim(-0.03, None)
    a1.legend(loc="lower center", frameon=False, ncol=3, fontsize=7, bbox_to_anchor=(0.5, 1.0))
    n = len(dates)
    t = np.arange(1, n + 1)
    a2.plot(dates, 0.01 * t, color="0.55", linestyle="-", linewidth=0.8, label="expected under correct coverage")
    for mid, (ls, c, lab) in styles.items():
        days = T.level(T.models(D, w)[mid], 0.01)["exceedance_days"]
        cum = np.cumsum(np.isin(np.arange(n), days))
        a2.step(dates, cum, where="post", linestyle=ls, color=c, linewidth=1.3 if mid == "nn-fz" else 1.0, label=lab)
    a2.set_ylabel("Cumulative exceedances")
    a2.legend(loc="upper left", frameon=False, fontsize=7)
    a2.set_xlabel("Forecast day, 2022")
    fig.autofmt_xdate()
    fig.tight_layout()
    figkit.save(fig, out, "market-rates2022")


def fig_z2(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(W, 2.9))
    picks = (("equity-2007-09", "awhs", 0.01), ("rates-2022", "awhs", 0.025))
    for ax, (w, mid, a) in zip(axes, picks):
        e = next(x for x in D["win"][w]["outputs"]["es_backtests"] if x["model_id"] == mid and abs(x["alpha"] - a) < 1e-12)
        edges = np.array(e["histogram"]["edges"])
        counts = np.array(e["histogram"]["counts"])
        ax.bar(edges[:-1], counts / counts.sum(), width=np.diff(edges), align="edge", color="0.8", edgecolor="0.4", linewidth=0.4)
        ax.axvline(e["realised"], color="black", linewidth=1.4, label=f"realised {e['realised']:.2f}")
        ax.axvline(e["critical_5pct"], color="0.3", linestyle="--", linewidth=1.0, label=f"5% critical {e['critical_5pct']:.2f}")
        ax.axvline(e["critical_0_01pct"], color="0.3", linestyle=":", linewidth=1.0, label=f"0.01% critical {e['critical_0_01pct']:.2f}")
        ax.set_title(f"{T.WLABEL[w]}, {T.MSHORT[mid]}, {100 * a:g}%", fontsize=8)
        ax.set_xlabel("$Z_2$ statistic")
        ax.legend(frameon=False, fontsize=6.5, loc="upper right")
    axes[0].set_ylabel("Share of simulated paths")
    fig.tight_layout()
    figkit.save(fig, out, "market-z2null")


def fig_binomial(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt
    from scipy.stats import binom

    rows = D["ladder"]["fit"]["traffic_light"]["rows"]
    zone = {r["exceptions"]: r["zone"] for r in rows}
    cum_doc = {r["exceptions"]: r["cumulative_probability_pct"] for r in rows}
    for k, v in cum_doc.items():
        assert abs(100 * binom.cdf(k, 250, 0.01) - v) < 0.006, (k, v)
    ks = np.arange(0, 15)
    pmf = binom.pmf(ks, 250, 0.01)
    cum = 100 * binom.cdf(ks, 250, 0.01)
    fig, ax = plt.subplots(figsize=(W, 3.0))
    shade = {"green": ("0.9", ""), "amber": ("0.65", "//"), "red": ("0.35", "xx")}
    for k in ks:
        z = zone.get(int(k), "red")
        ax.bar(k, pmf[k], color=shade[z][0], hatch=shade[z][1], edgecolor="0.2", linewidth=0.5)
    ax.set_xlabel("Exceptions in 250 days at 99% coverage")
    ax.set_ylabel("Binomial probability")
    ax2 = ax.twinx()
    ax2.plot(ks, cum, color="black", marker="o", markersize=3, linewidth=1.0)
    ax2.axhline(95, color="0.3", linestyle="--", linewidth=0.7)
    ax2.axhline(99.99, color="0.3", linestyle=":", linewidth=0.7)
    ax2.set_ylabel("Cumulative probability (%)")
    ax2.set_ylim(0, 101)
    from matplotlib.patches import Patch

    handles = [Patch(facecolor=c, hatch=h, edgecolor="0.2", label=z) for z, (c, h) in shade.items()]
    ax.legend(handles=handles, frameon=False, loc="center right", title="Zone", bbox_to_anchor=(0.97, 0.45))
    fig.tight_layout()
    figkit.save(fig, out, "market-binomial")


def fig_plaplane(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    thr = D["c13"]["none"]["outputs"]["pla"]["thresholds"]
    fig, ax = plt.subplots(figsize=(W, 3.6))
    ax.add_patch(plt.Rectangle((thr["spearman_green"], 0), 1.0 - thr["spearman_green"], thr["ks_green"], facecolor="0.88", edgecolor="0.5",
                               linewidth=0.6, zorder=0))
    ax.axvline(thr["spearman_red"], color="0.3", linestyle="--", linewidth=0.8)
    ax.axhline(thr["ks_red"], color="0.3", linestyle="--", linewidth=0.8)
    ax.text(thr["spearman_green"] + 0.01, 0.080, "green zone", fontsize=7, color="0.2")
    for i, v in enumerate(T.VARIANTS):
        p = D["c13"][v]["outputs"]["pla"]
        st = figkit.STYLES[i % len(figkit.STYLES)]
        ax.errorbar(p["spearman"]["mean"], p["ks"]["mean"], xerr=p["spearman"]["sd"], yerr=p["ks"]["sd"], marker=st["marker"], color="black",
                    markersize=6, linestyle="none", capsize=2, linewidth=0.8)
        xt = {"none": (0.62, 0.012), "missing-basis": (0.30, 0.135), "stale-volatility": (0.52, 0.064), "wrong-correlation": (0.55, 0.165),
              "omitted-factor": (0.40, 0.098), "time-misalignment": (0.12, 0.062)}[v]
        ax.annotate(T.VLABEL[v], (p["spearman"]["mean"], p["ks"]["mean"]), xytext=xt, fontsize=7, arrowprops={"arrowstyle": "-", "lw": 0.4, "color": "0.4"})
    ax.set_xlabel("Spearman correlation of hypothetical and risk-theoretical P&L (mean, one sd)")
    ax.set_ylabel("Kolmogorov-Smirnov distance")
    ax.set_xlim(-0.2, 1.02)
    ax.set_ylim(0, 0.19)
    fig.tight_layout()
    figkit.save(fig, out, "market-plaplane")


def fig_detection(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(W, 3.3))
    keys = (("spearman_flagged", "Spearman amber or red"), ("ks_flagged", "KS amber or red"), ("desk_backtest_flagged", "Desk back-test over a limit"))
    wd = 0.26
    for j, (key, lab) in enumerate(keys):
        xs, ys, lo, hi = [], [], [], []
        for i, v in enumerate(T.VARIANTS):
            det = D["c13"][v]["outputs"]["detection"]
            n = det["n_replications"]
            k = det["by_test"][key]
            a, b = T.wilson(k, n)
            xs.append(i + (j - 1) * wd)
            ys.append(100 * k / n)
            lo.append(100 * k / n - 100 * a)
            hi.append(100 * b - 100 * k / n)
        ax.bar(xs, ys, width=wd, color=["0.9", "0.6", "0.25"][j], hatch=HATCH[j], edgecolor="0.2", linewidth=0.5, label=lab)
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt="none", ecolor="black", capsize=1.5, linewidth=0.7)
        for x, y, h in zip(xs, ys, hi):
            ax.text(x, y + h + 1.5, f"{y:.0f}", ha="center", fontsize=6)
    ax.set_xticks(range(len(T.VARIANTS)))
    ax.set_xticklabels([T.VLABEL[v].replace(" ", "\n", 1) for v in T.VARIANTS], fontsize=7)
    ax.set_ylabel("Replications flagged (%)")
    ax.set_ylim(0, 108)
    ax.legend(frameon=False, fontsize=7, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.12))
    fig.tight_layout()
    figkit.save(fig, out, "market-detection")


def fig_sizepower(D: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    pairs = T.t_sizepower_rows(D)
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.7), sharey=True)
    for ax, key, title in zip(axes, ("null", "alt"), ("Size under the null", "Power against one alternative")):
        for i, p in enumerate(pairs):
            s = p[key]
            r = s["rates"][s["study"]["rule_label"]]
            ax.errorbar(100 * r["rate"], i, xerr=[[100 * (r["rate"] - r["wilson_low"])], [100 * (r["wilson_high"] - r["rate"])]], fmt="o",
                        color="black", markersize=3.5, capsize=2, linewidth=0.8)
        ax.set_title(title, fontsize=8)
        ax.set_xlabel("Rejection rate (%)")
    axes[0].axvline(5.0, color="0.4", linestyle="--", linewidth=0.8)
    axes[0].set_xlim(0, 10)
    axes[1].set_xlim(0, 100)
    labels = []
    for p in pairs:
        s = p["alt"]
        lab = s["study"]["label"]["en"]
        labels.append(f"{T.TEST_NAME[p['test']].replace('$', '')}, {lab}")
    axes[0].set_yticks(range(len(pairs)))
    axes[0].set_yticklabels(labels, fontsize=6)
    axes[0].invert_yaxis()
    fig.tight_layout()
    figkit.save(fig, out, "market-sizepower")


FIGS = {"hitrate": fig_hitrate, "fz0": fig_fz0, "rates": fig_rates, "z2": fig_z2, "binomial": fig_binomial, "plaplane": fig_plaplane,
        "detection": fig_detection, "sizepower": fig_sizepower}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*", choices=sorted(FIGS), help="draw only these figures")
    args = ap.parse_args()
    figkit.style()
    D = T.load()
    for name, fn in FIGS.items():
        if args.only and name not in args.only:
            continue
        fn(D, HERE)
    print(f"market figures written to {HERE}")


if __name__ == "__main__":
    main()
