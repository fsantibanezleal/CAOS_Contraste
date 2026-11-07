"""Write the figures of the reconciliation manuscript from the experiment outputs and the committed documents.

    python manuscripts/reconciliation-against-reference-engines/make_figures.py

Every figure is a vector PDF in ``figures/``, readable in grayscale, drawn only from ``experiments/results_*.json`` and
``data/derived/C12/*.json``; no number is typed here.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import figkit  # noqa: E402

EXP = HERE / "experiments"
OUT = HERE / "figures"
S = figkit.STYLES


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


def fig_printed_gaps(plt) -> None:
    d = load("results_printed.json")
    names = list(d["unit_gaps"])
    short = {n: n.replace("Pluto and Tasche (2005)", "Pluto-Tasche").replace("Schuermann and Hanson (2004)", "Schuermann-Hanson")
             .replace("Israel, Rosenthal and Wei (2001)", "Israel et al.").replace("Engelmann (2024)", "Engelmann").replace("Tasche (2013)", "Tasche")
             for n in names}
    kinds = {s["source"]: s["kind"] for s in d["sources"]}
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    rng = np.random.default_rng(1)
    for i, n in enumerate(names):
        g = np.array(d["unit_gaps"][n])
        y = i + rng.uniform(-0.28, 0.28, g.size)
        ax.scatter(np.maximum(g, 0.01), y, s=7, color="0.15" if kinds[n] == "recomputed" else "0.6", marker="o" if kinds[n] == "recomputed" else "s", linewidths=0)
    ax.set_xscale("log")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([short[n] for n in names], fontsize=7)
    ax.invert_yaxis()
    for x, ls, lab in ((0.5, "-", "half a unit (digit rule)"), (1.0, "--", "1 unit"), (2.0, ":", "2 units")):
        ax.axvline(x, color="0.4", linestyle=ls, linewidth=0.8, label=lab)
    ax.legend(fontsize=6.5, loc="lower right")
    ax.set_xlabel("absolute gap in units of the last printed digit (log scale; zero drawn at 0.01)")
    ax.set_xlim(0.008, 60)
    ax.set_ylim(len(names) - 0.4, -0.6)
    fig.tight_layout()
    figkit.save(fig, OUT, "printed-gaps")


def fig_routes(plt) -> None:
    d = load("results_routes.json")
    p1 = d["part1"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.1))
    n = len(p1["grid_gaps_jeffreys"])
    floor = 1e-17
    a.scatter(range(n), np.maximum(p1["grid_gaps_jeffreys"], floor), s=14, color="0.1", label="Jeffreys against the quadrature")
    a.scatter(range(n), np.maximum(p1["grid_gaps_binomial"], floor), s=14, marker="s", color="0.55", label="binomial against the exact sum")
    a.axhline(d["tolerance"], color="0.3", linestyle="--", linewidth=0.8)
    a.text(1, d["tolerance"] * 2.2, "tolerance 1e-9", fontsize=7)
    a.set_yscale("log")
    a.set_ylim(1e-17, 1e-4)
    a.set_xlabel("case of the grid of 36")
    a.set_ylabel("absolute difference of the p-value")
    a.legend(fontsize=6.5, loc="upper left")
    eps = [r["eps"] for r in d["defect_relative"]]
    for key, lab, st in (("C1_binomial", "reuse of the engine's helper (C1)", S[1]), ("C2_binomial", "same library, parameters from the definition (C2)", S[2]),
                         ("C3_binomial", "independent route (C3)", S[0])):
        b.plot(eps, [max(r[key], 1e-17) for r in d["defect_relative"]], label=lab, **st)
    b.axhline(d["tolerance"], color="0.3", linestyle="--", linewidth=0.8)
    b.set_xscale("log")
    b.set_yscale("log")
    b.set_xlabel("relative error planted inside the SciPy function")
    b.set_ylabel("largest difference to the engine")
    b.set_ylim(1e-17, 1e-1)
    b.legend(fontsize=6.0, loc="lower right")
    fig.tight_layout()
    figkit.save(fig, OUT, "routes")


def fig_closed(plt) -> None:
    d = load("results_closedforms.json")
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.1))
    kinds = ["bond_call", "bond_put", "swaption_payer", "swaption_receiver"]
    rng = np.random.default_rng(2)
    rows = d["part2"]["rows"]
    for i, k in enumerate(kinds):
        v = np.array([r["relative_difference"] for r in rows if r["kind"] == k])
        a.scatter(i + rng.uniform(-0.25, 0.25, v.size), np.maximum(v, 1e-16), s=8, color=str(0.1 + 0.2 * i), linewidths=0)
    a.axhline(d["gate"], color="0.3", linestyle="--", linewidth=0.8)
    a.text(-0.4, d["gate"] * 1.6, "gate 1e-6", fontsize=7)
    a.set_yscale("log")
    a.set_xticks(range(4))
    a.set_xticklabels([k.replace("_", "\n") for k in kinds], fontsize=7)
    a.set_ylabel("relative difference to QuantLib")
    delta = [r["delta"] for r in d["part3"]["plants"]]
    b.plot(delta, [r["swaption_relative_difference"] for r in d["part3"]["plants"]], label="payer swaption (elasticity %.2f)" % d["part3"]["elasticity_swaption"], **S[0])
    b.plot(delta, [max(r["bond_call_relative_difference"], 1e-12) for r in d["part3"]["plants"]], label="bond call (elasticity %.3f)" % d["part3"]["elasticity_bond_call"], **S[1])
    b.axhline(d["gate"], color="0.3", linestyle="--", linewidth=0.8)
    b.set_xscale("log")
    b.set_yscale("log")
    b.set_xlabel("relative error planted in the engine's volatility")
    b.set_ylabel("relative difference to QuantLib")
    b.legend(fontsize=6.5, loc="upper left")
    fig.tight_layout()
    figkit.save(fig, OUT, "closed-forms")


def fig_z_profiles(plt) -> None:
    d = load("results_committed.json")
    fig, ax = plt.subplots(2, 3, figsize=(7.2, 4.2), sharex=True)
    titles = {"single-swap": "single swap", "netting-set": "netting set", "csa-mpor-10d": "CSA, 10 days", "csa-mpor-20d": "CSA, 20 days", "with-im": "CSA, 10 days, initial margin"}
    for a, (v, r) in zip(ax.flat, d["variants"].items()):
        a.plot(r["t"], r["z"], color="0.1", marker="o", markersize=2.5, linewidth=0.9)
        a.axhspan(-2, 2, color="0.85", zorder=0)
        a.axhline(0, color="0.5", linewidth=0.5)
        a.set_title(titles[v] + f" ({r['n_beyond_two']} of {r['n_dates']} beyond 2)", fontsize=7)
        a.set_ylim(-14, 14)
    ax.flat[5].axis("off")
    for a in ax[1, :2]:
        a.set_xlabel("report date, years")
    ax.flat[2].set_xlabel("")
    for a in (ax[0, 0], ax[1, 0]):
        a.set_ylabel("z, ORE minus engine")
    fig.tight_layout()
    figkit.save(fig, OUT, "z-profiles")


def fig_pairs(plt) -> None:
    pr = load("results_pairs.json")
    cr = load("results_criterion.json")
    t = pr["t"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for v, st in (("single-swap", S[0]), ("netting-set", S[1])):
        a.plot(t, pr[v]["rho_by_date"], label=v.replace("-", " "), **st)
    a.set_xlabel("report date, years")
    a.set_ylabel("correlation of the two paths of a pair")
    a.legend(fontsize=7)
    for v, st, lab in (("single-swap", S[0], "single swap"), ("netting-set", S[1], "netting set")):
        b.plot(t, cr["calibration"][v]["sd_z_by_date"], label=f"measured, {lab}", **st)
    b.plot(t, pr["netting-set"]["predicted_sd_z_by_date"], color="0.0", linestyle=":", linewidth=1.4, label="predicted sqrt(1 + rho), netting set")
    b.plot(t, cr["calibration"]["netting-set"]["sd_z_pair_by_date"], color="0.5", linestyle="-", linewidth=0.8, label="pair-aware errors, netting set")
    b.axhline(1.0, color="0.7", linewidth=0.6)
    b.set_xlabel("report date, years")
    b.set_ylabel("standard deviation of z over repetitions")
    b.set_ylim(0.2, 1.55)
    b.legend(fontsize=6.0, loc="upper right")
    fig.tight_layout()
    figkit.save(fig, OUT, "pairs")


def fig_power(plt) -> None:
    cr = load("results_criterion.json")
    conds = cr["conditions"]
    rules = [("product", "product rule", S[0]), ("pair+sidak", "pair-aware errors, bound 3.18", S[1]), ("sidak", "bound 3.18", S[2]),
             ("pair", "pair-aware errors, bound 2", S[3]), ("fixed 2%", "fixed tolerance 2 %", S[4])]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    for ax, v in zip(axes, cr["variants"]):
        x = np.arange(len(conds))
        for key, lab, st in rules:
            y = [cr["table"][f"{v}|{c}"][key]["rate"] for c in conds]
            lo = [cr["table"][f"{v}|{c}"][key]["lo"] for c in conds]
            hi = [cr["table"][f"{v}|{c}"][key]["hi"] for c in conds]
            ax.plot(x, y, label=lab, **st)
            ax.fill_between(x, lo, hi, color=st["color"], alpha=0.12, linewidth=0)
        ax.set_xticks(x)
        ax.set_xticklabels([c.replace("sigma", "vol.").replace("a+", "rev.+").replace("+", "\n+", 1) if c != "null" and c != "measure" else c for c in conds], fontsize=6.5)
        ax.set_title(v.replace("-", " "), fontsize=8)
        ax.axhline(0.05, color="0.6", linestyle=":", linewidth=0.7)
        ax.set_ylim(-0.02, 1.02)
    axes[0].set_ylabel("rejection rate over repetitions")
    axes[0].legend(fontsize=6.0, loc="center right")
    fig.tight_layout()
    figkit.save(fig, OUT, "power")


def fig_null_z(plt) -> None:
    cr = load("results_criterion.json")
    z = np.array(cr["calibration"]["netting-set"]["z_null"]).ravel()
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    bins = np.linspace(-4, 4, 61)
    ax.hist(z[np.abs(z) > 0], bins=bins, density=True, color="0.6", label="product's errors (independent paths)")
    grid = np.linspace(-4, 4, 400)
    ax.plot(grid, np.exp(-grid**2 / 2) / np.sqrt(2 * np.pi), color="0.0", linewidth=1.2, label="standard normal")
    ax.set_xlabel("standardised difference z of two runs of the same model")
    ax.set_ylabel("density")
    ax.legend(fontsize=7)
    fig.tight_layout()
    figkit.save(fig, OUT, "null-z")


def fig_ore(plt) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.0), sharey=False)
    t = load("results_committed.json")["variants"]["single-swap"]["t"]
    for ax, (name, lab) in zip(axes, (("netting-set", "netting set"), ("single-swap", "single swap"), ("csa-mpor-10d", "CSA, 10 days"))):
        s = load(f"results_ore_{name}.json")["summary"]
        ax.plot(t, s["mean_z_by_date"], label="mean z, product's errors", **S[0])
        ax.plot(t, s["mean_z_pair_by_date"], label="mean z, pair-aware errors", **S[1])
        ax.axhspan(-2, 2, color="0.88", zorder=0)
        ax.axhline(0, color="0.5", linewidth=0.5)
        ax.set_title(f"{lab}, {s['reps']} seeds", fontsize=7.5)
        ax.set_xlabel("report date, years")
    axes[0].set_ylabel("mean over seeds of z, ORE minus engine")
    axes[0].legend(fontsize=6.0, loc="lower left")
    fig.tight_layout()
    figkit.save(fig, OUT, "ore-replicates")


def main() -> None:
    figkit.style()
    import matplotlib.pyplot as plt

    for f in (fig_printed_gaps, fig_routes, fig_closed, fig_z_profiles, fig_pairs, fig_power, fig_null_z, fig_ore):
        f(plt)
        print("wrote", f.__name__)


if __name__ == "__main__":
    main()
