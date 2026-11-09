"""The figures of the manuscript, from the committed C04 documents and the experiment outputs.

Run from the repository root, after the four experiment scripts have written their JSON::

    python manuscripts/default-definition-withdrawals-thin-grades/figures/make_figures.py

It writes vector PDFs next to this script. No number is typed: every point is read from ``data/derived/C04`` or from
``experiments/*.json``.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
MS = HERE.parent
ROOT = MS.parents[1]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))

import figkit  # noqa: E402

figkit.style()
import matplotlib.pyplot as plt  # noqa: E402

GRADES = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC-C"]
S = figkit.STYLES


def ex(name: str) -> dict:
    return json.loads((MS / "experiments" / f"{name}.json").read_text(encoding="utf-8"))


def arr(x) -> np.ndarray:
    return np.array([[np.nan if v is None else v for v in row] for row in x], dtype=float)


DEF = ex("definitions")
WD = ex("withdrawals")
TH = ex("theory")
THIN = ex("thin")


def fig_lra() -> None:
    """Long-run average PD by grade under each definition, S&P and Fitch, with Jeffreys intervals of the pooled counts."""
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.9), sharey=True)
    for ax, code, title in zip(axes, ("sp", "fitch"), ("S&P (26 cohorts)", "Fitch (24 cohorts)")):
        a = DEF["agencies"][code]
        x = np.arange(7)
        for i, (key, label) in enumerate((("d2", "default page"), ("d3", "defaults page"),
                                         ("d4", "transition page"), ("keep", "withdrawals kept"))):
            p = a["point"].get(key)
            if p is None:
                continue
            y = np.array(p["lra"], dtype=float)
            y = np.where(y > 0, y, np.nan)
            off = (i - 1.5) * 0.14
            st = S[i]
            err = None
            if key in a["jeffreys"]:
                lo = np.array(a["jeffreys"][key]["lower"], dtype=float)
                hi = np.array(a["jeffreys"][key]["upper"], dtype=float)
                err = np.vstack([np.clip(y - lo, 0, None), np.clip(hi - y, 0, None)])
                err = np.where(np.isfinite(err), err, 0)
            ax.errorbar(x + off, y, yerr=err, fmt=st["marker"], color=st["color"], ms=4, lw=0.8, capsize=1.5,
                        label=label)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels(GRADES, rotation=45, ha="right")
        ax.set_title(title)
        ax.set_ylim(2e-5, 0.6)
        ax.grid(True, which="major", axis="y", lw=0.3, color="0.8")
    axes[0].set_ylabel("long-run average one-year PD")
    axes[0].legend(loc="upper left", frameon=False)
    fig.tight_layout()
    figkit.save(fig, HERE, "lra-definitions")


def fig_yearly() -> None:
    """S&P's yearly rate of B and CCC to C under the default page and the transition page."""
    doc = figkit.doc("C04/sp.json")["outputs"]
    labels = [c["label"] for c in doc["cohorts"]]
    d2, d4 = arr(doc["pd"]["d2"]), arr(doc["pd"]["d4"])
    keep = arr(doc["pd"]["keep"])
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.6), sharex=True)
    for ax, g in zip(axes, (5, 6)):
        t = np.arange(len(labels))
        ax.plot(t, d2[:, g], label="default page", **{**S[0], "marker": "o"})
        ax.plot(t, d4[:, g], label="transition page", **{**S[1], "marker": "s"})
        ax.plot(t, keep[:, g], label="withdrawals kept", **{**S[2], "marker": "^"})
        ax.set_title(f"S&P, grade {GRADES[g]}")
        ax.set_xticks(t[::5])
        ax.set_xticklabels(labels[::5])
        ax.set_xlabel("cohort year")
        ax.grid(True, lw=0.3, color="0.85")
    axes[0].set_ylabel("one-year default rate")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    figkit.save(fig, HERE, "yearly-gap")


def fig_rw() -> None:
    """The bootstrap interval of the IRB risk weight of the cohort mix under each definition, three agencies."""
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    ypos = 0
    ticks, names = [], []
    for code, name in (("sp", "S&P"), ("moodys", "Moody's"), ("fitch", "Fitch")):
        a = DEF["agencies"][code]
        for i, (key, label) in enumerate((("d2", "default page"), ("d4", "transition page"), ("keep", "withdrawals kept"))):
            if key not in a["bootstrap"]:
                continue
            b = a["bootstrap"][key]["rw"]
            pt = a["point"][key]["rw"]
            st = S[i]
            ax.errorbar([pt], [ypos], xerr=[[pt - b["lo"]], [b["hi"] - pt]], fmt=st["marker"], color=st["color"], ms=4,
                        lw=0.9, capsize=2, label=label if code == "sp" else None)
            ticks.append(ypos)
            names.append(f"{name}, {label}")
            ypos -= 1
        ypos -= 0.6
    pop = DEF["fitch_populated_years"]
    for i, (key, label) in enumerate((("d2", "default page"), ("d4", "transition page"))):
        b = pop["rw_" + key]
        pt = pop["point"][key]["rw"]
        st = S[i]
        ax.errorbar([pt], [ypos], xerr=[[pt - b["lo"]], [b["hi"] - pt]], fmt=st["marker"], color=st["color"], ms=4, lw=0.9,
                    capsize=2)
        ticks.append(ypos)
        names.append(f"Fitch, {len(pop['kept_years'])} years, {label}")
        ypos -= 1
    ax.set_yticks(ticks)
    ax.set_yticklabels(names)
    ax.set_xlabel("IRB risk weight of the cohort mix (share of exposure)")
    ax.grid(True, axis="x", lw=0.3, color="0.85")
    fig.tight_layout()
    figkit.save(fig, HERE, "rw-definitions")


def fig_bias() -> None:
    """Relative bias of the B PD against the informativeness k, pooled over five cohorts and on the first-year cohort."""
    rungs = WD["rungs"]
    ks = np.array([r["k"] for r in rungs])
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8), sharey=True)
    for ax, suffix, title in zip(axes, ("", "_y1"), ("five cohorts pooled", "first-year cohort")):
        for i, arm in enumerate(("removed", "kept", "followed", "latent")):
            y = np.array([r[arm + suffix]["rel_bias"][5] for r in rungs]) * 100
            e = np.array([r[arm + suffix]["rel_bias_mcse"][5] for r in rungs]) * 196
            st = S[i]
            ax.errorbar(ks + (i - 1.5) * 0.12, y, yerr=e, fmt=st["marker"],
                        color=st["color"], ms=4, lw=0.8, capsize=1.5, label=arm)
            ax.plot(ks, y, color=st["color"], ls=st["linestyle"], lw=0.8)
        ax.axhline(0, color="0.5", lw=0.6)
        ax.set_title(title)
        ax.set_xlabel("informativeness k of withdrawal")
        ax.grid(True, lw=0.3, color="0.85")
    axes[0].set_ylabel("relative bias of the B one-year PD (%)")
    axes[0].legend(frameon=False, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, HERE, "bias-ladder")


def fig_theory() -> None:
    """The closed forms of the Theory section against the engine's simulation on the two-state chain of B."""
    ch = TH["chains"]["B"]
    ks = np.array([r["k"] for r in ch["rows"]])
    kk = np.linspace(0, 20, 81)
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8), sharey=True)
    for ax, scope, title in zip(axes, ("pooled", "first_year"), ("five cohorts pooled", "first-year cohort")):
        for i, arm in enumerate(("removed", "kept", "followed")):
            st = S[i]
            sim = np.array([r["simulated"][scope][arm]["rel_bias_sim"] for r in ch["rows"]]) * 100
            se = np.array([r["simulated"][scope][arm]["rel_bias_mcse"] for r in ch["rows"]]) * 196
            cf = np.array([r["simulated"][scope][arm]["rel_bias_closed_form"] for r in ch["rows"]]) * 100
            ax.plot(ks, cf, color=st["color"], ls=st["linestyle"], lw=0.9)
            ax.errorbar(ks, sim, yerr=se, fmt=st["marker"], color=st["color"], ms=4, capsize=1.5, lw=0.8, label=arm)
        ax.axhline(0, color="0.5", lw=0.6)
        ax.set_title(title)
        ax.set_xlabel("informativeness k of withdrawal")
        ax.grid(True, lw=0.3, color="0.85")
    axes[0].set_ylabel("relative bias of the PD (%)")
    axes[0].legend(frameon=False, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, HERE, "theory-vs-simulation")


def fig_thin() -> None:
    """Exact coverage of the three intervals against the number of obligors, for AAA and BB, with the closed form."""
    grid = np.array(THIN["grid"])
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8), sharey=True)
    for ax, g in zip(axes, (0, 4)):
        for i, (m, label) in enumerate((("wald", "Wald"), ("agresti_coull", "Agresti-Coull"), ("jeffreys", "Jeffreys"))):
            y = np.array(THIN["coverage_grid"][m])[:, g]
            st = S[i]
            ax.plot(grid, y, color=st["color"], ls=st["linestyle"], marker=st["marker"], ms=3.5, lw=0.9, label=label)
        p = THIN["pd_1y"][g]
        nn = np.logspace(np.log10(grid[0]), np.log10(grid[-1]), 200)
        ax.plot(nn, 1 - (1 - p) ** nn, color="0.6", lw=0.8, ls=(0, (1, 2)), label=r"$1-(1-p)^n$")
        ax.axhline(0.95, color="0.4", lw=0.6)
        ax.set_xscale("log")
        ax.set_title(f"grade {GRADES[g]}, p = {100 * p:.4f}%")
        ax.set_xlabel("obligors in the grade, n")
        ax.set_ylim(-0.02, 1.03)
        ax.grid(True, lw=0.3, color="0.85")
    axes[0].set_ylabel("exact coverage at the true PD")
    axes[0].legend(frameon=False, loc="center right", fontsize=7)
    fig.tight_layout()
    figkit.save(fig, HERE, "thin-coverage")


def fig_tests() -> None:
    """Rejection rates of the case's two matrix tests at the 5% level, against the informativeness of withdrawal."""
    fig, ax = plt.subplots(figsize=(4.6, 2.7))
    for i, tid in enumerate(("rating.time_homogeneity", "rating.matrix_reference")):
        rows = [t for t in WD["tests"] if t["test_id"] == tid]
        ks = np.array([t["rung"] for t in rows])
        rate = np.array([t["rates"]["p<0.05"]["rate"] for t in rows])
        lo = np.array([t["rates"]["p<0.05"]["wilson_low"] for t in rows])
        hi = np.array([t["rates"]["p<0.05"]["wilson_high"] for t in rows])
        st = S[i]
        ax.errorbar(ks + (i - 0.5) * 0.3, rate, yerr=[rate - lo, hi - rate], fmt=st["marker"], color=st["color"], ms=4,
                    capsize=2, lw=0.9, label="time homogeneity" if i == 0 else "last year against exp(Q)")
        ax.plot(ks, rate, color=st["color"], ls=st["linestyle"], lw=0.8)
    ax.axhline(0.05, color="0.5", lw=0.6)
    ax.set_xlabel("informativeness k of withdrawal")
    ax.set_ylabel("rejection rate at the 5% level")
    ax.legend(frameon=False)
    ax.grid(True, lw=0.3, color="0.85")
    fig.tight_layout()
    figkit.save(fig, HERE, "tests-rejection")


def fig_capital() -> None:
    """The error of the IRB risk weight of S&P's cohort mix under each treatment's PDs, against k."""
    rungs = WD["rungs"]
    ks = np.array([r["k"] for r in rungs])
    fig, ax = plt.subplots(figsize=(4.6, 2.7))
    for i, arm in enumerate(("removed", "kept", "followed", "latent")):
        y = np.array([r["rw"][arm]["error"] for r in rungs]) * 100
        e = np.array([r["rw"][arm]["error_mcse"] for r in rungs]) * 196
        st = S[i]
        ax.errorbar(ks, y, yerr=e, fmt=st["marker"], color=st["color"], ms=4, capsize=1.5, lw=0.8, label=arm)
        ax.plot(ks, y, color=st["color"], ls=st["linestyle"], lw=0.8)
    ax.axhline(0, color="0.5", lw=0.6)
    ax.set_xlabel("informativeness k of withdrawal")
    ax.set_ylabel("error of the risk weight (points)")
    ax.legend(frameon=False, loc="lower left")
    ax.grid(True, lw=0.3, color="0.85")
    fig.tight_layout()
    figkit.save(fig, HERE, "rw-error-ladder")


def main() -> None:
    for fn in (fig_lra, fig_yearly, fig_rw, fig_bias, fig_theory, fig_thin, fig_tests, fig_capital):
        fn()
        print("ok", fn.__name__)


if __name__ == "__main__":
    main()
