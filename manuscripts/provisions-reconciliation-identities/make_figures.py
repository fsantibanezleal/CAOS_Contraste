"""Write the vector figures of the manuscript into ``figures/`` from ``experiments/*.json``.

    python manuscripts/provisions-reconciliation-identities/make_figures.py

Every plot reads the committed experiment outputs; none of its numbers is typed here. The style is the shared one
(``manuscripts/_shared/figkit.py``): serif text, grayscale-safe line styles, vector PDF.
"""
from __future__ import annotations

import glob
import json
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
E1, E2, E4, E6 = (common.load(f) for f in ("e1_gate_power.json", "e2_tolerance_and_rounding.json", "e4_nonlinearity.json", "e6_identity_algebra.json"))
RUNS = [json.loads(pathlib.Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(HERE / "experiments" / "e5_regimes" / "s*-x1.json")))]
LADDER = sorted((json.loads(pathlib.Path(f).read_text(encoding="utf-8")) for f in glob.glob(str(HERE / "experiments" / "e5_regimes" / "s42-x*.json"))),
                key=lambda r: r["scale"])
G = E1["grid"]
DETECTABLE = ("allowance-movement", "allowance-closing", "stage-reallocation", "gca-movement", "waterfall-line", "waterfall-closing", "stage-ecl")
CLASS_LABEL = {"allowance-movement": "allowance movement", "allowance-closing": "allowance closing", "stage-reallocation": "moved between stages",
               "gca-movement": "gross amount movement", "waterfall-line": "waterfall line", "waterfall-closing": "waterfall closing",
               "stage-ecl": "stage ECL", "line-misclassification": "misclassified line"}
T975_9 = 2.2621571627


def power() -> None:
    mults = [float(m) for m in E1["meta"]["multiples"]]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.1), gridspec_kw={"width_ratios": [1.05, 1]})
    for i, (gate, label) in enumerate((("full", "twelve identities"), ("stage", "stage roll-forwards only"), ("total", "pooled row"))):
        k = np.array([sum(G[c][f"{m:g}"][gate][0] for c in DETECTABLE) for m in mults])
        n = np.array([sum(G[c][f"{m:g}"][gate][1] for c in DETECTABLE) for m in mults])
        lo, hi = zip(*[common.wilson(int(kk), int(nn)) for kk, nn in zip(k, n)])
        a.plot(mults, k / n, label=label, **figkit.STYLES[i])
        a.fill_between(mults, lo, hi, color=figkit.STYLES[i]["color"], alpha=0.15, linewidth=0)
    a.axvline(1.0, color="0.5", linewidth=0.7, linestyle=":")
    a.set_xscale("log")
    a.set_xlabel("size of the defect, in multiples of the limit")
    a.set_ylabel("share of cases flagged")
    a.set_title("(a) detection, seven defect classes", loc="left")
    a.legend(loc="center right")
    gates = ["full", "stage", "total"] + [f"drop:{f}" for f in E1["meta"]["families"]]
    glabel = ["full", "stage", "pooled", "$-$allow.", "$-$gross", "$-$closes", "$-$equals", "$-$lines", "$-$ECL tie"]
    classes = list(G)
    mat = np.array([[G[c]["10"][g][0] / G[c]["10"][g][1] for g in gates] for c in classes])
    im = b.imshow(mat, cmap="Greys", vmin=0, vmax=1, aspect="auto")
    b.set_xticks(range(len(gates)), glabel, rotation=60, ha="right")
    b.set_yticks(range(len(classes)), [CLASS_LABEL[c] for c in classes])
    for i in range(len(classes)):
        for j in range(len(gates)):
            b.text(j, i, f"{mat[i, j]:.0f}", ha="center", va="center", color="white" if mat[i, j] > 0.5 else "black", fontsize=7)
    b.set_title("(b) share flagged at ten times the limit", loc="left")
    fig.colorbar(im, ax=b, fraction=0.04, pad=0.02)
    fig.tight_layout()
    figkit.save(fig, OUT, "power")


def incidence() -> None:
    d = E6["dates"]["2008-12"]
    a = np.abs(np.array(d["matrix"]))
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.imshow(a, cmap="Greys", aspect="auto", vmin=0, vmax=1, interpolation="nearest")
    vars_ = d["variable_names"]
    kinds = [v.split("/")[0] for v in vars_]
    edges = [i for i in range(1, len(kinds)) if kinds[i] != kinds[i - 1]]
    for e in edges:
        ax.axvline(e - 0.5, color="0.4", linewidth=0.8)
    starts = [0] + edges + [len(kinds)]
    names = {"A": "allowance rows", "G": "gross amount rows", "W": "waterfall lines", "E": "stage ECL"}
    ax.set_xticks([(starts[i] + starts[i + 1] - 1) / 2 for i in range(len(starts) - 1)], [names[kinds[starts[i]]] for i in range(len(starts) - 1)])
    eq = d["equation_names"]
    labels = []
    for n in eq:
        labels.append(n.replace("waterfall-lines-equal-movements", "lines equal movements").replace("waterfall-equals-stage-closings", "waterfall equals closings")
                      .replace("waterfall-closes", "waterfall closes").replace("allowance-rollforward", "allowance roll-forward")
                      .replace("gca-rollforward", "gross roll-forward").replace("stage-closing-equals-ecl", "closing equals ECL"))
    ax.set_yticks(range(len(eq)), labels, fontsize=6)
    ax.set_xlabel("table entries (67), grouped by table")
    ax.set_ylabel("equations (19)")
    fig.tight_layout()
    figkit.save(fig, OUT, "incidence")


def rounding() -> None:
    r = E2["rounding"]
    keys = ["1", "10", "1000", "10000", "100000", "1e+06"]
    steps = [float(k) for k in keys]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.0))
    p = np.array([r[k]["flagged"][0] / r[k]["flagged"][1] for k in keys])
    ci = np.array([common.wilson(*r[k]["flagged"]) for k in keys])
    a.errorbar(steps, p, yerr=[np.maximum(p - ci[:, 0], 0.0), np.maximum(ci[:, 1] - p, 0.0)], fmt="o-", color="0.0", capsize=2)
    a.set_xscale("log")
    a.set_xlabel("every stored number rounded to (currency units)")
    a.set_ylabel("share of 1,200 clean books flagged")
    a.set_title("(a) false alarms from rounding", loc="left")
    for i, (q, label) in enumerate((("ratio_q50", "median"), ("ratio_q99", "99th percentile"), ("ratio_max", "maximum"))):
        b.plot(steps, [max(r[k][q], 1e-9) for k in keys], label=label, **figkit.STYLES[i])
    b.axhline(1.0, color="0.4", linewidth=0.8, linestyle=":")
    b.set_xscale("log")
    b.set_yscale("log")
    b.set_xlabel("every stored number rounded to (currency units)")
    b.set_ylabel("largest residual, in multiples of the limit")
    b.set_title("(b) residual against the limit", loc="left")
    b.legend(loc="upper left")
    fig.tight_layout()
    figkit.save(fig, OUT, "rounding")


def sweep() -> None:
    pts = E4["sweep"]["sample"]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    style = {"convex": ("o", "0.15", "all factors convex"), "concave": ("s", "0.55", "all factors concave"), "mixed": ("^", "0.35", "both sides")}
    for cls, (mk, col, lab) in style.items():
        xs = [p[0] for p in pts if p[2] == cls]
        ys = [p[1] for p in pts if p[2] == cls]
        ax.scatter(xs, ys, s=5, marker=mk, color=col, label=f"{lab} ({len(xs)})", linewidths=0.3, alpha=0.7)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_yscale("symlog", linthresh=1e-3)
    ax.set_xlabel("weighted mean scenario factor")
    ax.set_ylabel("index: weighted PD over PD at the mean factor, minus one")
    ax.legend(loc="upper left", markerscale=2)
    fig.tight_layout()
    figkit.save(fig, OUT, "sweep")


def designs() -> None:
    d = E4["designs"]["designs"]
    order = ["single", "adhoc3", "tertile3", "gh3", "gh5"]
    names = ["base alone", "25/50/25\nat one sd", "tertile\nmeans", "Gauss-Hermite\n3 points", "Gauss-Hermite\n5 points"]
    stats = []
    for k, n in zip(order, names):
        q = d[k]["quantiles"]
        stats.append({"label": n, "whislo": q["q05"], "q1": q["q25"], "med": q["q50"], "q3": q["q75"], "whishi": q["q95"], "fliers": []})
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.bxp(stats, showfliers=False, boxprops={"color": "0.1"}, medianprops={"color": "0.0", "linewidth": 1.4}, whiskerprops={"color": "0.3"}, capprops={"color": "0.3"})
    ax.axhline(0.0, color="0.5", linewidth=0.8, linestyle=":")
    ax.set_yscale("symlog", linthresh=1e-6)
    ax.set_ylabel("relative error of the expected PD")
    fig.tight_layout()
    figkit.save(fig, OUT, "designs")


def regimes() -> None:
    sids = ["base", "recession", "house-price-fall", "consumer-arrears-shock", "uf-inflation-spike", "combined-severe"]
    labels = ["base", "recession", "house\nprices", "consumer\narrears", "UF\ninflation", "combined\nsevere"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.1), gridspec_kw={"width_ratios": [1.5, 1]})
    rng = np.random.default_rng([common.SEED_BASE, 9])
    for i, sid in enumerate(sids):
        v = np.array([r["scenarios"][sid]["ifrs9_over_b1"] for r in RUNS])
        a.scatter(i + rng.uniform(-0.18, 0.18, v.size), v, s=9, color="0.45", zorder=2, label="a seed" if i == 0 else None)
        m, sd = v.mean(), v.std(ddof=1)
        h = T975_9 * sd / np.sqrt(v.size)
        a.errorbar(i, m, yerr=h, fmt="_", color="0.0", capsize=4, markersize=12, zorder=3, label="mean, 95% interval" if i == 0 else None)
        c = common.doc(f"C07/{sid}.json")["outputs"]
        tot = {x["regime"]: x["total_provision"] for x in c["regimes"]}
        a.scatter(i + 0.3, tot["ifrs9"] / tot["cmf-b1"], marker="D", s=14, color="white", edgecolor="0.0", zorder=4, label="committed (seed 42)" if i == 0 else None)
    a.axhline(1.0, color="0.4", linewidth=0.8, linestyle=":")
    a.set_xticks(range(len(sids)), labels)
    a.set_ylabel("IFRS 9 total over B-1 total")
    a.set_title("(a) ten seeds at full size", loc="left")
    a.legend(loc="upper left")
    acc = [r["n_accounts"] for r in LADDER]
    for i, (sid, lab) in enumerate((("base", "base"), ("recession", "recession"), ("combined-severe", "combined severe"))):
        b.plot(acc, [r["scenarios"][sid]["ifrs9_over_b1"] for r in LADDER], label=lab, **figkit.STYLES[i])
    b.axhline(1.0, color="0.4", linewidth=0.8, linestyle=":")
    b.set_xscale("log")
    b.set_xlabel("accounts in the generated book")
    b.set_ylabel("IFRS 9 total over B-1 total")
    b.set_title("(b) size of the book, seed 42", loc="left")
    b.legend(loc="upper left")
    fig.tight_layout()
    figkit.save(fig, OUT, "regimes")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for fn in (power, incidence, rounding, sweep, designs, regimes):
        fn()
    print("wrote", sorted(p.name for p in OUT.glob("*.pdf")))
