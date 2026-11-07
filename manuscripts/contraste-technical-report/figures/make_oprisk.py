"""The figures of the operational-risk chapter of the technical report (``sections/14-oprisk.tex``), as vector PDF in
``manuscripts/contraste-technical-report/figures/oprisk-*.pdf``, drawn from the committed artifacts of case C17 under
``data/derived`` with the shared style of ``manuscripts/_shared/figkit.py`` (readable in grayscale).

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_oprisk.py

The constants and the readers of the artifacts are those of ``tables/make_oprisk.py``, which this script loads by path.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

_spec = importlib.util.spec_from_file_location("oprisk_tables", HERE.parent / "tables" / "make_oprisk.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

XI_LABEL = {"xi-0-6": r"$\xi=0.6$", "xi-0-8": r"$\xi=0.8$", "xi-0-96": r"$\xi=0.96$", "xi-1-1": r"$\xi=1.1$"}
SHORT = {
    "lda_lognormal": "LN\nignored",
    "lda_lognormal_truncated": "LN\ntruncated",
    "lda_splice": "Splice",
    "sla": "SLA",
    "scenario": "Scenario",
    "sla_mean_adjusted": "GPD\nML",
    "sla_cvm": "GPD\nCvM",
    "sla_obre": "GPD\nOBRE",
    "sla_cvm_lognormal": "LN\nCvM",
}


def exceedance(d: dict) -> None:
    """The exceedance probability of the true annual loss by three computations, with the 99.9 percent level and the SLA quantile."""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4), sharey=True)
    for ax, (vid, _, xi) in zip(axes.flat, T.VARIANTS):
        o = d[vid]["outputs"]["exceedance"]
        x = np.array(o["grid_eur"], dtype=float)

        def ok(y):
            y = np.array([np.nan if v is None else v for v in y], dtype=float)
            y[y <= 0] = np.nan
            return y

        ax.loglog(x, ok(o["fft"]["exceedance"]), label="Fourier transform", **figkit.STYLES[0], markevery=1)
        ax.loglog(x, ok(o["panjer"]["exceedance"]), label="Panjer recursion", **figkit.STYLES[1], markevery=1)
        ax.loglog(x, ok(o["monte_carlo"]["exceedance"]), label="Monte Carlo", linestyle="none", marker="x", color="0.35", markersize=4)
        ax.axhline(0.001, color="0.5", linewidth=0.8, linestyle=":")
        ax.axvline(o["quantile_999_eur"]["sla"], color="0.5", linewidth=0.8, linestyle="--")
        ax.set_title(XI_LABEL[vid])
        ax.set_xlabel("Annual loss (EUR)")
        if ax in axes[:, 0]:
            ax.set_ylabel("Probability of exceeding")
        ax.set_ylim(1e-5, 2)
    axes[0, 0].legend(frameon=False, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, HERE, "oprisk-exceedance")


def boxes(d: dict, rungs: tuple[str, ...], name: str, ylim: tuple[float, float]) -> None:
    """Capital over truth by method: 5th to 95th percentile, interquartile box and median, one panel per tail index."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6), sharey=True)
    for ax, (vid, _, xi) in zip(axes.flat, T.VARIANTS):
        c = T.cell(d[vid], T.MAIN_CELL)
        for k, r in enumerate(rungs):
            s = T.summ(c, r)
            if s is None:
                continue
            q = s["ratio_to_truth"]
            ax.vlines(k, q["p05"], q["p95"], color="0.4", linewidth=0.9)
            ax.vlines(k, q["p25"], q["p75"], color="0.0", linewidth=4.5)
            ax.plot([k], [q["median"]], marker="o", color="white", markersize=3.5, zorder=5)
        ax.axhline(1.0, color="0.5", linewidth=0.8, linestyle="--")
        ax.set_yscale("log")
        ax.set_ylim(*ylim)
        ax.set_xlim(-0.6, len(rungs) - 0.4)
        ax.set_xticks(range(len(rungs)))
        ax.set_xticklabels([SHORT[r] for r in rungs], fontsize=6.5)
        ax.set_title(XI_LABEL[vid])
        if ax in axes[:, 0]:
            ax.set_ylabel("Capital over true quantile")
    fig.tight_layout()
    figkit.save(fig, HERE, name)


def tail(d: dict) -> None:
    """The fitted tail index against the threshold, with its 5th to 95th percentile band and the true value of each variant."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    for k, (vid, _, xi) in enumerate(T.VARIANTS):
        t = T.cell(d[vid], T.MAIN_CELL)["threshold_stability"]
        x = [r["threshold_eur"] for r in t]
        med = [r["tail_index"]["median"] for r in t]
        lo = [r["tail_index"]["p05"] for r in t]
        hi = [r["tail_index"]["p95"] for r in t]
        s = figkit.STYLES[k]
        ax.plot(x, med, label=rf"$\xi={xi:g}$", **s)
        ax.fill_between(x, lo, hi, color=s["color"], alpha=0.12, linewidth=0)
        ax.axhline(xi, color=s["color"], linewidth=0.5, linestyle=":")
    ax.axhline(1.0, color="0.0", linewidth=0.8)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Threshold of the GPD fit (EUR)")
    ax.set_ylabel(r"Fitted tail index $\hat\xi$")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    figkit.save(fig, HERE, "oprisk-tail")


def sma(d: dict) -> None:
    """The internal loss multiplier after one added loss, and the standardised capital over the true quantile by variant."""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.1))
    x = np.linspace(0, 3, 200)
    ax[0].plot(x, np.log(np.e - 1 + x ** 0.8), color="0.7", linewidth=1.0, label="formula")
    for k, (vid, _, xi) in enumerate(T.VARIANTS):
        r = d[vid]["outputs"]["sma_response"]
        bic = r["bic_eur"]
        lc = [row["lc_eur"] / bic for row in r["rows"]]
        ilm = [row["ilm"] for row in r["rows"]]
        ax[0].plot(lc, ilm, label=rf"$\xi={xi:g}$", **{**figkit.STYLES[k], "linestyle": "none"})
    ax[0].set_xlim(0, 3)
    ax[0].set_xlabel(r"Loss component over $\mathrm{BIC}$")
    ax[0].set_ylabel("Internal loss multiplier")
    ax[0].set_title("(a) One loss added to a history")
    ax[0].legend(frameon=False, fontsize=7)
    for k, (vid, _, xi) in enumerate(T.VARIANTS):
        s = T.cell(d[vid], T.MAIN_CELL)["sma"]["orc_over_true_quantile"]
        sp = T.summ(T.cell(d[vid], T.MAIN_CELL), "lda_splice")["ratio_to_truth"]
        ax[1].vlines(k - 0.12, s["p05"], s["p95"], color="0.4", linewidth=0.9)
        ax[1].plot([k - 0.12], [s["median"]], marker="s", color="0.0", markersize=4, label="Standardised approach" if k == 0 else None)
        ax[1].vlines(k + 0.12, sp["p05"], sp["p95"], color="0.7", linewidth=0.9)
        ax[1].plot([k + 0.12], [sp["median"]], marker="o", color="0.4", markersize=4, label="Splice LDA" if k == 0 else None)
    ax[1].axhline(1.0, color="0.5", linewidth=0.8, linestyle="--")
    ax[1].set_yscale("log")
    ax[1].set_xticks(range(4))
    ax[1].set_xticklabels([f"{xi:g}" for _, _, xi in T.VARIANTS])
    ax[1].set_xlabel(r"True tail index $\xi$")
    ax[1].set_ylabel("Capital over true quantile")
    ax[1].set_title("(b) Ten years, threshold EUR 20,000")
    ax[1].legend(frameon=False, fontsize=7, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, HERE, "oprisk-sma")


def defined(d: dict) -> None:
    """The number of histories with a finite capital, by method and tail index (out of 1,000)."""
    import matplotlib.pyplot as plt
    import numpy as np

    rungs = ("lda_splice", "sla_mean_adjusted", "sla_cvm", "sla_obre", "sla_cvm_lognormal", "scenario")
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    w = 0.2
    hatches = ["", "//", "..", "xx"]
    for k, (vid, _, xi) in enumerate(T.VARIANTS):
        c = T.cell(d[vid], T.MAIN_CELL)
        vals = [(T.summ(c, r) or {"n_defined": 0})["n_defined"] for r in rungs]
        ax.bar(np.arange(len(rungs)) + (k - 1.5) * w, vals, w, color=str(0.25 + 0.2 * k), edgecolor="0.0", linewidth=0.4,
               hatch=hatches[k], label=rf"$\xi={xi:g}$")
    ax.set_xticks(range(len(rungs)))
    ax.set_xticklabels([SHORT[r] for r in rungs], fontsize=7)
    ax.set_ylabel("Histories with a capital (of 1,000)")
    ax.legend(frameon=False, ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    fig.tight_layout()
    figkit.save(fig, HERE, "oprisk-defined")


def main() -> int:
    figkit.style()
    d = T.load()
    exceedance(d)
    boxes(d, T.M24_RUNGS, "oprisk-m24-boxes", (1e-3, 100))
    boxes(d, T.M32_RUNGS, "oprisk-m32-boxes", (1e-2, 100))
    tail(d)
    sma(d)
    defined(d)
    print("figures written to", HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
