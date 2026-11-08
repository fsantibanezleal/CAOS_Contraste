"""The figures of the manuscript, from the committed C15 documents and the experiment outputs.

Run from the repository root, after the five experiment scripts have written their JSON::

    python manuscripts/uf-as-its-own-currency-in-irrbb/figures/make_figures.py

It writes vector PDFs next to this script. No number is typed: every point is read from ``data/derived/C15`` or from
``experiments/*.json``, or computed here with the engine's functions (``cmf_pair``, ``shock_curve``, ``apply_floor``).
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
sys.path.insert(0, str(ROOT / "data-pipeline"))

import figkit  # noqa: E402

figkit.style()
import matplotlib.pyplot as plt  # noqa: E402
from riskvalidation.irrbb import eve_nii, shocks  # noqa: E402

S = figkit.STYLES
VAR = ["long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active"]
VNAME = {"long-uf": "long UF", "short-uf": "short UF", "cpi-surprise": "CPI surprise", "clp-steepener": "CLP steepener",
         "offset-on-off": "offset on/off", "floors-active": "floor-exposed"}
SW = ["curve", "sizes", "floor", "pair", "charge"]
SWNAME = {"curve": "own curve", "sizes": "own sizes", "floor": "own floor", "pair": "pair rule", "charge": "indexation charge"}


def ex(name: str) -> dict:
    return json.loads((MS / "experiments" / f"{name}.json").read_text(encoding="utf-8"))


MAIN, SWEEP, FLOORS, REP = ex("main"), ex("sweep"), ex("floors"), ex("reproduce")


def midpoints() -> np.ndarray:
    from riskvalidation.irrbb import slotting

    return slotting.bucket_grid().midpoints


def fig_pair() -> None:
    """The pair function of Annex 1 and the two bounds of the Theory section, from the engine's ``cmf_pair``."""
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8), sharey=False)
    a = np.linspace(-60, 60, 241)
    for ax, b, title in zip(axes, (-40.0, 25.0), ("UF leg gains 40 (delta = -40)", "UF leg loses 25 (delta = +25)")):
        lines = [("sum of the legs (offset 100%)", [max(x + b, 0.0) for x in a], S[0]),
                 ("Annex 1 pair rule (offset 50%)", [eve_nii.cmf_pair(float(x), b, True) for x in a], S[1]),
                 ("positive parts (offset 0%)", [max(x, 0.0) + max(b, 0.0) for x in a], S[2])]
        for label, y, st in lines:
            ax.plot(a, y, label=label, color=st["color"], linestyle=st["linestyle"])
        ax.set_xlabel("delta of the CLP leg (loss positive)")
        ax.set_title(title)
        ax.grid(alpha=0.25, linewidth=0.4)
    axes[0].set_ylabel("combined measure of the pair")
    axes[0].legend(loc="upper left", frameon=False)
    fig.tight_layout()
    figkit.save(fig, HERE, "pair-function")


def fig_curves() -> None:
    """The two committed zero curves, the floors, and the UR curve after the 300 bp fall of the NII scenario."""
    o = figkit.doc("C15/long-uf.json")["outputs"]
    mid = midpoints()
    clp = np.array(o["curves"]["clp"]["zero_rates_at_midpoints"]) * 100
    ur = np.array(o["curves"]["ur"]["zero_rates_at_midpoints"]) * 100
    fall = shocks.apply_floor(ur / 100, np.full(19, -300.0), None) * 100
    fig, ax = plt.subplots(figsize=(5.6, 3.1))
    ax.plot(mid, clp, label="CLP zero curve", color=S[0]["color"], linestyle=S[0]["linestyle"])
    ax.plot(mid, ur, label="UR (UF) zero curve", color=S[1]["color"], linestyle=S[1]["linestyle"])
    ax.plot(mid, fall, label="UR curve after a 300 bp fall, no floor", color=S[2]["color"], linestyle=S[2]["linestyle"])
    ax.axhline(o["floors"]["ur_floor"] * 100, color="0.2", linestyle=":", linewidth=1.0)
    ax.text(mid[-1], o["floors"]["ur_floor"] * 100 + 0.12, "UR floor, -2 percent", ha="right", fontsize=8)
    ax.axhline(o["floors"]["other_floor"] * 100, color="0.5", linestyle=":", linewidth=1.0)
    ax.text(mid[-1], o["floors"]["other_floor"] * 100 + 0.12, "CLP floor, 0 percent", ha="right", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("bucket midpoint (years, logarithmic)")
    ax.set_ylabel("continuously compounded zero rate (percent)")
    ax.legend(frameon=False, fontsize=7.5, loc="center right")
    ax.grid(alpha=0.25, linewidth=0.4)
    fig.tight_layout()
    figkit.save(fig, HERE, "curves-and-floors")


def fig_fisher() -> None:
    """The ratio of the discount factor on the peso curve to the one on the UF curve: what a peso curve does to an indexed flow."""
    o = figkit.doc("C15/long-uf.json")["outputs"]
    mid = midpoints()
    clp = np.array(o["curves"]["clp"]["zero_rates_at_midpoints"])
    ur = np.array(o["curves"]["ur"]["zero_rates_at_midpoints"])
    ratio = np.exp(-(clp - ur) * mid)
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8))
    axes[0].plot(mid, (clp - ur) * 1e4, color=S[0]["color"], marker=S[0]["marker"])
    axes[0].set_xscale("log")
    axes[0].set_xlabel("bucket midpoint (years, logarithmic)")
    axes[0].set_ylabel("peso minus UF zero rate (bp)")
    axes[1].plot(mid, ratio, color=S[1]["color"], marker=S[1]["marker"])
    axes[1].set_xscale("log")
    axes[1].set_xlabel("bucket midpoint (years, logarithmic)")
    axes[1].set_ylabel("discount factor, peso over UF curve")
    for ax in axes:
        ax.grid(alpha=0.25, linewidth=0.4)
    fig.tight_layout()
    figkit.save(fig, HERE, "peso-curve-on-uf-flows")


def fig_main() -> None:
    """Delta NII and delta EVE of the four treatments as a share of Tier 1, mean and 95 percent interval over 30 books."""
    names = [("annex", "Annex 1", S[0]), ("pos", "positive parts", S[1]), ("single", "single currency", S[2]), ("gap", "gap measures", S[3])]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0), sharey=False)
    x = np.arange(len(VAR))
    for ax, meas, title in zip(axes, ("nii", "eve"), ("delta NII over Tier 1 (percent)", "delta EVE over Tier 1 (percent)")):
        for i, (key, label, st) in enumerate(names):
            ys, es = [], []
            for v in VAR:
                s = MAIN["variants"][v]["summary"]
                k = f"{key}_{meas}"
                t1 = s["tier1"]["mean"]
                ys.append(100 * s[k]["mean"] / t1)
                es.append(100 * s[k]["ci_half"] / t1)
            ax.errorbar(x + (i - 1.5) * 0.13, ys, yerr=es, color=st["color"], marker=st["marker"], linestyle="none", capsize=2, label=label)
        ax.set_xticks(x, [VNAME[v] for v in VAR], rotation=30, ha="right", fontsize=7.5)
        ax.set_title(title)
        ax.grid(alpha=0.25, linewidth=0.4)
    axes[0].legend(frameon=False, fontsize=7.5)
    fig.tight_layout()
    figkit.save(fig, HERE, "treatments-over-tier1")


def fig_shapley() -> None:
    """Exact Shapley value of each switch, mean and 95 percent interval over 30 books, for the three 30 percent variants."""
    vs = ["long-uf", "short-uf", "offset-on-off"]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0))
    x = np.arange(len(SW))
    for ax, meas, title in zip(axes, ("delta_nii", "delta_eve"), ("delta NII (CLP million)", "delta EVE (CLP million)")):
        for i, v in enumerate(vs):
            d = MAIN["variants"][v]["shapley"][meas]
            ax.errorbar(x + (i - 1) * 0.16, [d[s]["mean"] for s in SW], yerr=[d[s]["ci_half"] for s in SW], color=S[i]["color"],
                        marker=S[i]["marker"], linestyle="none", capsize=2, label=VNAME[v])
        ax.axhline(0, color="0.3", linewidth=0.6)
        ax.set_xticks(x, [SWNAME[s] for s in SW], rotation=30, ha="right", fontsize=7.5)
        ax.set_title(title)
        ax.grid(alpha=0.25, linewidth=0.4)
    axes[0].legend(frameon=False, fontsize=7.5)
    fig.tight_layout()
    figkit.save(fig, HERE, "shapley-values")


def fig_sweep() -> None:
    """The two measures of both treatments as a share of Tier 1 against the net UF position, with the two prioritisation lines."""
    pos = list(SWEEP["positions"].values())
    nu = [p["net_uf_share_tier1"] for p in pos]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9))
    for ax, meas, line, title in zip(axes, ("nii", "eve"), (5.0, 15.0), ("delta NII over Tier 1 (percent)", "delta EVE over Tier 1 (percent)")):
        for i, (key, label) in enumerate((("annex", "Annex 1"), ("single", "single currency"))):
            m = np.array([100 * p[f"{key}_{meas}_over_tier1"]["mean"] for p in pos])
            h = np.array([100 * p[f"{key}_{meas}_over_tier1"]["ci_half"] for p in pos])
            ax.plot(nu, m, color=S[i]["color"], linestyle=S[i]["linestyle"], marker=S[i]["marker"], markersize=3, label=label)
            ax.fill_between(nu, m - h, m + h, color=S[i]["color"], alpha=0.15, linewidth=0)
        ax.axhline(line, color="0.4", linestyle=":", linewidth=1.0)
        ax.text(nu[0], line, f"{line:g} percent line", fontsize=7.5, va="bottom")
        ax.set_xlabel("net UF position over Tier 1")
        ax.set_title(title)
        ax.grid(alpha=0.25, linewidth=0.4)
    axes[1].legend(frameon=False, fontsize=7.5, loc="lower right")
    fig.tight_layout()
    figkit.save(fig, HERE, "position-sweep")


def fig_flags() -> None:
    """The number of the 20 books flagged as prioritised by each treatment against the net UF position."""
    pos = list(SWEEP["positions"].values())
    nu = [p["net_uf_share_tier1"] for p in pos]
    fig, ax = plt.subplots(figsize=(5.4, 2.9))
    for i, (key, label) in enumerate((("annex1", "Annex 1"), ("positive_parts", "positive parts"), ("single", "single currency"))):
        ax.plot(nu, [p["any_flag"][key] for p in pos], color=S[i]["color"], linestyle=S[i]["linestyle"], marker=S[i]["marker"], markersize=3,
                label=label)
    ax.set_xlabel("net UF position over Tier 1")
    ax.set_ylabel("books flagged, of 20")
    ax.legend(frameon=False, fontsize=7.5)
    ax.grid(alpha=0.25, linewidth=0.4)
    fig.tight_layout()
    figkit.save(fig, HERE, "prioritised-flags")


def fig_floors() -> None:
    """The effect of the UR floor on delta NII against the translation of the UR curve, mean and 95 percent interval over 20 books."""
    shifts = [float(k) for k in FLOORS["results"]]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9))
    for i, v in enumerate(("long-uf", "short-uf", "floors-active")):
        r = [FLOORS["results"][f"{s:+.0f}"][v] for s in shifts]
        axes[0].errorbar(shifts, [x["nii_effect"]["mean"] for x in r], yerr=[x["nii_effect"]["ci_half"] for x in r], color=S[i]["color"],
                         marker=S[i]["marker"], linestyle=S[i]["linestyle"], capsize=2, markersize=3, label=VNAME[v])
    axes[0].axhline(0, color="0.3", linewidth=0.6)
    axes[0].set_xlabel("translation of the UR curve (bp)")
    axes[0].set_ylabel("effect of the floor on delta NII (CLP million)")
    axes[0].legend(frameon=False, fontsize=7.5)
    r = [FLOORS["results"][f"{s:+.0f}"]["long-uf"] for s in shifts]
    axes[1].plot(shifts, [x["distance_bp"]["mean"] for x in r], color=S[0]["color"], marker=S[0]["marker"], markersize=3)
    axes[1].axhline(0, color="0.3", linewidth=0.6)
    axes[1].set_xlabel("translation of the UR curve (bp)")
    axes[1].set_ylabel("distance of the lowest UR rate to the floor (bp)")
    for ax in axes:
        ax.grid(alpha=0.25, linewidth=0.4)
    fig.tight_layout()
    figkit.save(fig, HERE, "floor-effect")


if __name__ == "__main__":
    for f in (fig_pair, fig_curves, fig_fisher, fig_main, fig_shapley, fig_sweep, fig_flags, fig_floors):
        f()
    print("wrote 8 figures to", HERE)
