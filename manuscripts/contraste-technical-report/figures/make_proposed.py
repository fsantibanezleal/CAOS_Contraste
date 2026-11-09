"""Figures of the section on the product's own contributions (sections/17-proposed.tex).

Every figure is a vector PDF drawn from the committed documents of ``data/derived`` through ``figkit``; the data are loaded by
``tables/make_proposed.py`` (the same numbers as the tables). Output: ``figures/proposed-*.pdf``.

Run from the repository root::

    python manuscripts/contraste-technical-report/figures/make_proposed.py
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

_spec = importlib.util.spec_from_file_location("px_tables", HERE.parent / "tables" / "make_proposed.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)  # type: ignore[union-attr]

W = 6.3  # text width in inches


def fig_size(A: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    tests = A["size_tests"]
    fig, ax = plt.subplots(figsize=(W, 3.6))
    x = np.arange(len(tests))
    rate = [100 * s["rates"]["p<0.05"]["rate"] for s in tests]
    se = [100 * 1.96 * s["rates"]["p<0.05"]["se"] for s in tests]
    ax.errorbar(x, rate, yerr=se, fmt="o", color="black", capsize=2, markersize=3.5, linewidth=0.8)
    ax.axhline(5.0, color="0.3", linestyle="--", linewidth=0.8, label="nominal level")
    ax.axhline(100 * A["size_bounds"]["p<0.05"], color="0.5", linestyle=":", linewidth=1.0, label="one-sided size bound")
    ax.set_xticks(x)
    ax.set_xticklabels([s["test_id"] for s in tests], rotation=75, ha="right", fontsize=6.5)
    ax.set_ylabel("Rejection rate at 5% under the null (%)")
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, out, "proposed-size")


def fig_pla(A: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(W, 3.5))
    names = ["Regulatory zone", "Wald", "Absolute Spearman", "Rolling Spearman", "Union (family 1%)"]
    hatch = ["", "//", "..", "xx", "\\\\"]
    shade = ["0.15", "0.4", "0.55", "0.7", "0.85"]
    wd = 0.16
    for j, nm in enumerate(names):
        vals = []
        for v in T.VARIANTS:
            d = A["c13"][v]
            ps = d["pla_complement"]["flags"]["per_statistic"]
            vals.append([100 * d["detection"]["share_amber_or_red"], 100 * ps["wald"]["rate"], 100 * ps["spearman_abs"]["rate"],
                         100 * ps["spearman_roll"]["rate"], 100 * d["pla_complement"]["flags"]["family"]["any"]["rate"]][j])
        ax.bar(np.arange(len(T.VARIANTS)) + (j - 2) * wd, vals, wd, color=shade[j], edgecolor="black", linewidth=0.5, hatch=hatch[j], label=nm)
    ax.set_xticks(range(len(T.VARIANTS)))
    ax.set_xticklabels([T.VLABEL[v].replace(" ", "\n", 1) for v in T.VARIANTS], fontsize=7.5)
    ax.set_ylabel("Replications flagged (%)")
    ax.set_ylim(0, 112)
    ax.legend(frameon=False, ncol=3, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    fig.tight_layout()
    figkit.save(fig, out, "proposed-pla")


def fig_lag(A: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    lag = {x["lag_days"]: x for x in A["c13"]["stale-volatility"]["pla_complement"]["lag_ladder"]}
    xs = sorted(lag)
    fig, ax = plt.subplots(figsize=(W, 3.0))
    for i, (key, lab) in enumerate([("spearman_roll", "Rolling Spearman"), ("spearman_abs", "Absolute Spearman"), ("wald", "Wald")]):
        r = [100 * lag[k]["per_statistic"][key]["rate"] for k in xs]
        lo = [100 * lag[k]["per_statistic"][key]["ci_low"] for k in xs]
        hi = [100 * lag[k]["per_statistic"][key]["ci_high"] for k in xs]
        ax.errorbar(xs, r, yerr=[np.array(r) - lo, np.array(hi) - r], capsize=2, label=lab, **figkit.STYLES[i])
    ax.plot(xs, [100 * lag[k]["pla_amber_or_red"]["rate"] for k in xs], label="Regulatory zone", **figkit.STYLES[3])
    ax.set_xlabel("Age of the volatility used by the risk model (days)")
    ax.set_ylabel("Replications flagged (%)")
    ax.set_xticks(xs)
    ax.legend(frameon=False, fontsize=7, loc="center right")
    fig.tight_layout()
    figkit.save(fig, out, "proposed-lag")


def fig_anchored(A: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    cov = {(r["design"], r["informative"], r["treatment"]): r for r in A["wd"]["bounds_verdict"]["rows"]}
    designs = ["first_year", "pooled", "first_year_x10"]
    lab = ["first-year\ncohort", "five cohorts\npooled", "first year,\n10x cohort"]
    treats = ["industry", "unfollowed", "followed", "anchored"]
    shade = ["0.8", "0.6", "0.4", "0.1"]
    hatch = ["", "//", "..", "xx"]
    fig, ax = plt.subplots(figsize=(W, 3.2))
    wd = 0.2
    for j, tr in enumerate(treats):
        vals, err = [], []
        for dsg in designs:
            r = cov[(dsg, 9.0, tr)]
            vals.append(100 * r["value"])
            err.append(100 * 1.96 * r["mcse"])
        ax.bar(np.arange(3) + (j - 1.5) * wd, vals, wd, yerr=err, capsize=2, color=shade[j], edgecolor="black", linewidth=0.5, hatch=hatch[j],
               label=tr)
    ax.axhline(95, color="0.3", linestyle="--", linewidth=0.8)
    ax.axhline(50, color="0.5", linestyle=":", linewidth=0.8)
    ax.set_xticks(range(3))
    ax.set_xticklabels(lab, fontsize=8)
    ax.set_ylabel("Coverage of the true B-grade PD (%)")
    ax.set_ylim(0, 112)
    ax.legend(frameon=False, ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    fig.tight_layout()
    figkit.save(fig, out, "proposed-anchored")


def fig_sequential(A: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    sc = {s["id"]: s for s in A["seq"]["hits"]["scenarios"]}
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.1))
    ax = axes[0]
    meth = [("e_rate", "E-process"), ("kupiec_trailing", "Kupiec trailing"), ("kupiec_cumulative", "Kupiec cumulative"), ("traffic_light", "Traffic light")]
    shade = ["0.1", "0.4", "0.65", "0.85"]
    for j, (k, lab) in enumerate(meth):
        ax.bar(j, 100 * sc["null"][k]["ever"], color=shade[j], edgecolor="black", linewidth=0.5, hatch=["", "//", "..", "xx"][j])
    ax.axhline(5, color="0.3", linestyle="--", linewidth=0.8)
    ax.set_xticks(range(4))
    ax.set_xticklabels([m[1].replace(" ", "\n") for m in meth], fontsize=7)
    ax.set_ylabel("Right model rejected at some day (%)")
    ax.set_title("Size, read every day", fontsize=8)
    ax = axes[1]
    xs = ["rate-x2", "rate-x3", "rate-x4"]
    for i, (k, lab) in enumerate(meth):
        y = [sc[x][k]["median_day"] if sc[x][k]["median_day"] is not None else np.nan for x in xs]
        ax.plot([2, 3, 4], y, label=lab, **figkit.STYLES[i])
    ax.axhline(250, color="0.5", linestyle=":", linewidth=0.8)
    ax.set_xticks([2, 3, 4])
    ax.set_xlabel("Hit rate over its nominal value")
    ax.set_ylabel("Median first day of rejection")
    ax.set_title("Delay", fontsize=8)
    ax.legend(frameon=False, fontsize=6.5)
    fig.tight_layout()
    figkit.save(fig, out, "proposed-sequential")


def fig_conformal(A: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(W, 3.4))
    pts = []
    for w in T.STRESS:
        for r in A["c11"][w]["conformal"]["rows"]:
            pts.append((w, r))
    x = np.arange(len(pts))
    un = [r["unwrapped"]["hit_rate"] / r["alpha"] for _, r in pts]
    wr = [r["wrapped"]["hit_rate"] / r["alpha"] for _, r in pts]
    ax.plot(x, un, linestyle="none", marker="o", color="black", label="unwrapped")
    ax.plot(x, wr, linestyle="none", marker="D", color="0.55", label="wrapped")
    for i in range(len(pts)):
        ax.plot([i, i], [un[i], wr[i]], color="0.7", linewidth=0.6, zorder=0)
    ax.axhline(1.0, color="0.2", linestyle="--", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{T.MODEL_LABEL[r['model_id']]} {100 * r['alpha']:g}%" for _, r in pts], rotation=75, ha="right", fontsize=6.5)
    ax.set_ylabel("Hit rate over the target level")
    for k, w in enumerate(T.STRESS):
        ax.text(k * 6 + 2.5, ax.get_ylim()[1] * 0.96, w, ha="center", va="top", fontsize=7)
        if k:
            ax.axvline(k * 6 - 0.5, color="0.8", linewidth=0.6)
    ax.legend(frameon=False, fontsize=7, loc="center right")
    fig.tight_layout()
    figkit.save(fig, out, "proposed-conformal")


def fig_band(A: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(W, 3.0))
    rows = A["band"]
    lab = [f"{r['method']}" + (f"\n$\\nu$={r['nu']:g}" if r["nu"] else "") for r in rows]
    vals = [r["capital_clp_m"] / 1000 for r in rows]
    cols = ["0.1" if r["status"] == "headline-capital" else "0.75" for r in rows]
    ax.bar(range(len(rows)), vals, color=cols, edgecolor="black", linewidth=0.5)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(lab, fontsize=6.3)
    ax.set_ylabel("Capital (CLP billion)")
    fig.tight_layout()
    figkit.save(fig, out, "proposed-band")


def fig_oprisk(A: dict, out: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(W, 3.0))
    for i, (tag, doc) in enumerate(A["c17"].items()):
        ys, xs = [], []
        for j, c in enumerate(doc["cells"]):
            r = c["capital"]["lda_splice"]
            if r:
                xs.append(j)
                ys.append(r["iqr_over_truth"])
        ax.plot(xs, ys, label=f"tail index {doc['tail_index']:g}", **figkit.STYLES[i])
    ax.set_xticks(range(4))
    ax.set_xticklabels([c["id"] for c in A["c17"]["xi-0-96"]["cells"]], fontsize=7.5)
    ax.set_xlabel("History length in years and collection threshold in EUR thousand (cell)")
    ax.set_ylabel("Interquartile range over the truth")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    figkit.save(fig, out, "proposed-oprisk")


def main() -> None:
    A = T.build()
    out = HERE
    figkit.style()
    for f in (fig_size, fig_pla, fig_lag, fig_anchored, fig_sequential, fig_conformal, fig_band, fig_oprisk):
        f(A, out)
    print("figures written to", out)


if __name__ == "__main__":
    main()
