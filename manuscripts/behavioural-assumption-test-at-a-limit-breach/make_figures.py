"""Write the figures of the manuscript (vector PDF, grayscale-safe) from ``experiments/results_*.json`` and the cached banks of ``experiments/run_fitted.py``.

    python manuscripts/behavioural-assumption-test-at-a-limit-breach/make_figures.py [--cache <temp root>/contraste-behavioural-assumption-test-at-a-limit-breach/cache]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import figkit  # noqa: E402
import core  # noqa: E402

EXP = HERE / "experiments"
OUT = HERE / "figures"
S = figkit.STYLES
# The cache lives in the device's temp root (CAOS_TEMP_ROOT, as the pipeline reads it) or where --cache says.
DEFAULT_CACHE = (pathlib.Path(os.environ["CAOS_TEMP_ROOT"]) / "contraste-behavioural-assumption-test-at-a-limit-breach" / "cache"
                 if os.environ.get("CAOS_TEMP_ROOT") else None)


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


R1, R2, R3, R4 = (load(n) for n in ("results_reproduction.json", "results_stated.json", "results_fitted.json", "results_theory.json"))


def fig_history() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.6), gridspec_kw={"width_ratios": [2.2, 1]})
    rb = R1["rebuilt"]
    x = np.arange(rb["n_fits"])
    ax = axes[0]
    ax.plot(x, rb["wam"], color="0.0", marker="o", ms=3)
    idx = {d: rb["fit_dates"].index(d) for d in R1["committed"]["dates"]}
    flagged = R1["committed"]["series"]["weighted average maturity of the fitted portfolio"]["flagged_dates"]
    for d, i in idx.items():
        ax.plot(i, rb["wam"][i], marker="s", color="0.0", ms=7, mfc="white" if d not in flagged else "0.5", mew=1.2)
    ax.axhline(core.WAM_MAX, color="0.6", ls=":", lw=0.8)
    ax.text(0.2, core.WAM_MAX + 0.08, "cap of the tranche grid, 5 years", fontsize=7, color="0.3")
    ticks = list(range(0, rb["n_fits"], 4))
    ax.set_xticks(ticks, [rb["fit_dates"][i][:7] for i in ticks], rotation=30, ha="right")
    ax.set_ylabel("Fitted weighted average maturity (years)")
    ax.set_xlabel("Quarter of the fit (16 quarters ending there)")
    ax.set_ylim(0.5, 5.6)
    ax2 = axes[1]
    dts = [d[:7] for d in R1["committed"]["dates"]]
    vals = R1["committed"]["series"]["weighted average maturity of the fitted portfolio"]["values"]
    held = R1["committed"]["series"]["requested core maturity"]["values"]
    ax2.plot(range(3), held, color="0.45", ls="--", marker="s", label="requested core maturity (held)")
    ax2.plot(range(3), vals, color="0.0", marker="o", label="fitted maturity")
    for i, d in enumerate(R1["committed"]["dates"]):
        if d in flagged:
            ax2.plot(i, vals[i], marker="o", ms=9, mfc="none", color="0.0")
    ax2.set_xticks(range(3), dts, rotation=30, ha="right")
    ax2.set_xlim(-0.4, 2.4)
    ax2.set_ylim(0.5, 5.6)
    ax2.set_yticklabels([])
    ax2.legend(fontsize=6, loc="lower left")
    ax2.set_xlabel("Valuation date")
    fig.tight_layout()
    figkit.save(fig, OUT, "history")


def fig_false_flag() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    m = np.linspace(1, 8, 50)
    for k, lam in enumerate((0.05, 0.10, 0.20)):
        st = S[k]
        ax.plot(m, 1 - (1 - lam) ** m, color=st["color"], ls=st["linestyle"], lw=1.0, label=f"closed form, $\\lambda={lam:.2f}$")
        cells = [c for c in R2["cells"] if abs(c["lam"] - lam) < 1e-9 and abs(c["pi_m"] - 0.5) < 1e-9]
        xs = [c["mean_breach_dates"] for c in cells]
        ys = [c["rates"]["null"]["engine"]["rate"] for c in cells]
        lo = [c["rates"]["null"]["engine"]["rate"] - c["rates"]["null"]["engine"]["lo"] for c in cells]
        hi = [c["rates"]["null"]["engine"]["hi"] - c["rates"]["null"]["engine"]["rate"] for c in cells]
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt=st["marker"], color=st["color"], ms=4, capsize=2, lw=0.8)
    ax.axhline(0.05, color="0.6", ls=":", lw=0.8)
    ax.text(7.9, 0.06, "5%", fontsize=7, ha="right", color="0.3")
    ax.set_xlabel("Mean number of breach dates $m$ in the history")
    ax.set_ylabel("False-flag rate of the proposed test")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    figkit.save(fig, OUT, "false-flag")


def fig_hypergeometric() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    n = core.T_DEFAULT - 1
    m = np.arange(0, 9)
    for j, k in enumerate((1, 2, 3, 5)):
        st = S[j]
        ax.plot(m, [core.p_coincidence_hypergeometric(n, k, int(mm)) for mm in m], color=st["color"], ls=st["linestyle"], lw=1.0, label=f"$k={k}$ changes")
        rows = [r for r in R4["hypergeometric"]["rows"] if r["k"] == k]
        ax.errorbar([r["m"] for r in rows], [r["simulated"] for r in rows], yerr=[[r["simulated"] - r["lo"] for r in rows], [r["hi"] - r["simulated"] for r in rows]],
                    fmt=st["marker"], color=st["color"], ms=4, capsize=2, lw=0.8)
    ax.set_xlabel("Number of breach dates $m$ among $n=11$ dates")
    ax.set_ylabel("Probability that a change falls on a breach date")
    ax.legend(fontsize=7, loc="lower right")
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    figkit.save(fig, OUT, "hypergeometric")


def fig_operating_points() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    names = {"engine": "proposed test", "any_change": "any change", "fisher": "Fisher exact", "mannwhitney": "Mann--Whitney", "welch": "Welch"}
    for j, det in enumerate(("engine", "any_change", "fisher", "mannwhitney", "welch")):
        st = S[j]
        xs = [c["rates"]["null"][det]["rate"] for c in R2["cells"] if c["pi_m"] == 0.5]
        ys = [c["rates"]["alt"][det]["rate"] for c in R2["cells"] if c["pi_m"] == 0.5]
        ax.plot(xs, ys, ls="none", marker=st["marker"], color=st["color"], ms=5, mfc="none" if j % 2 else st["color"], label=names[det])
    ax.plot([0, 1], [0, 1], color="0.7", lw=0.8, ls=":")
    ax.set_xlabel("False-flag rate (changes unrelated to the breach)")
    ax.set_ylabel("Detection rate (changes planted at breach dates)")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=7, loc="center right")
    fig.tight_layout()
    figkit.save(fig, OUT, "operating-points")


def fig_fitted_power() -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.5), sharex=True)
    ys = ("0.5", "1.0", "2.0", "4.0")
    xs = [float(y) for y in ys]
    dets = ("engine", "tolerance", "mannwhitney", "welch", "fisher", "shift", "shift_at_breach")
    names = {"engine": "proposed test", "tolerance": "calibrated tolerance", "mannwhitney": "Mann--Whitney", "welch": "Welch", "fisher": "Fisher exact",
             "shift": "level-shift test", "shift_at_breach": "level-shift test, break on a breach date"}
    # figkit holds six styles; the seventh detector takes a marker and a dash pattern of its own
    styles = list(S) + [{"color": "0.25", "linestyle": (0, (3, 1, 1, 1, 1, 1)), "marker": "P"}]
    for j, det in enumerate(dets):
        st = styles[j]
        axes[0].plot(xs, [R3["matched"]["0.25"]["add"][y][det]["rate"] for y in ys], color=st["color"], ls=st["linestyle"], marker=st["marker"], label=names[det])
        axes[1].plot(xs, [R3["matched"]["0.25"]["auc_add"][y][det]["auc"] for y in ys], color=st["color"], ls=st["linestyle"], marker=st["marker"])
        if det in ("tolerance", "mannwhitney", "shift", "shift_at_breach"):
            axes[1].plot(xs, [R3["real_series"]["0.25"]["auc_add"][y][det]["auc"] for y in ys], color=st["color"], ls="none", marker=st["marker"], mfc="none", ms=7)
    axes[0].set_ylabel("Detection rate at the calibrated size")
    axes[1].set_ylabel("Area under the ROC curve")
    axes[1].axhline(0.5, color="0.7", ls=":", lw=0.8)
    for ax in axes:
        ax.set_xlabel("Lengthening planted at breach dates (years)")
        ax.set_xscale("log", base=2)
        ax.set_xticks(xs, [f"{x:g}" for x in xs])
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=4, fontsize=6.5, frameon=False)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    figkit.save(fig, OUT, "fitted-power")


def fig_gaussian() -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for j, row in enumerate(R4["tolerance_closed_forms"]["rows"]):
        st = S[j]
        pts = row["points"]
        mu = [p["mu_over_sigma"] for p in pts]
        ax.plot(mu, [p["formula"] for p in pts], color=st["color"], ls=st["linestyle"], lw=1.0, label=f"closed form, $m={row['m']}$")
        ax.plot(mu, [p["simulated"] for p in pts], ls="none", marker=st["marker"], color=st["color"], ms=5, mfc="none")
    ax.axhline(R4["tolerance_closed_forms"]["alpha"], color="0.6", ls=":", lw=0.8)
    ax.set_xlabel("Planted shift over the standard deviation of a change, $\\mu/\\sigma$")
    ax.set_ylabel("Probability that the tolerance rule flags")
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    figkit.save(fig, OUT, "gaussian-power")


def fig_changes(cache: pathlib.Path) -> None:
    import matplotlib.pyplot as plt

    test = np.load(cache / "fitted_test.npy")
    sim = np.abs(np.diff(test @ core.MATS / 2.0, axis=1)).ravel()
    rb = R1["rebuilt"]
    real = np.abs(np.diff(np.array(rb["wam"])))
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for arr, lab, st in ((sim, "simulated banks (22,000 changes)", S[1]), (real, "real fitted series (24 changes)", S[0]), (real[-11:], "real, last 12 fits (11 changes)", S[2])):
        v = np.sort(arr)
        ax.step(v, np.arange(1, v.size + 1) / v.size, where="post", color=st["color"], ls=st["linestyle"], lw=1.2, label=lab)
    ax.set_xlabel("Absolute change of the weighted average maturity between two dates (years)")
    ax.set_ylabel("Empirical distribution function")
    ax.set_xlim(0, 3.5)
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    figkit.save(fig, OUT, "changes-ecdf")


def fig_conformal() -> None:
    import matplotlib.pyplot as plt

    c = R4["conformal"]
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    ax.hist(np.array(c["rates"]) * 100, bins=24, color="0.6", edgecolor="0.2", linewidth=0.5)
    ax.axvline(c["alpha"] * 100, color="0.0", ls="--", lw=1.0, label="size $\\alpha=5\\%$")
    ax.axvline(c["mean_rate"] * 100, color="0.3", ls="-", lw=1.0, label="mean over calibrations")
    ax.set_xlabel("Realised false-flag rate on 20,000 fresh null histories (%)")
    ax.set_ylabel("Calibrations of 1,000 histories")
    ax.legend(fontsize=7)
    fig.tight_layout()
    figkit.save(fig, OUT, "conformal-validity")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=pathlib.Path, default=DEFAULT_CACHE, required=DEFAULT_CACHE is None,
                    help="cache folder; defaults to $CAOS_TEMP_ROOT/contraste-behavioural-assumption-test-at-a-limit-breach/cache")
    args = ap.parse_args()
    figkit.style()
    fig_history()
    fig_false_flag()
    fig_hypergeometric()
    fig_operating_points()
    fig_fitted_power()
    fig_gaussian()
    fig_changes(args.cache)
    fig_conformal()
    print("figures:", sorted(p.name for p in OUT.glob("*.pdf")))


if __name__ == "__main__":
    main()
