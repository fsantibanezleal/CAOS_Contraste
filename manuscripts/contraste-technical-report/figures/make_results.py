"""Figures of the results across the cases (sections/19-results.tex), vector PDF into ``figures/results-*.pdf``, drawn from the
committed findings register and validation reports under ``data/derived/governance`` through ``figkit``.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/figures/make_results.py

The derived values come from ``tables/make_results.py`` (``derive``), so the tables and the figures read the same artifacts.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

_spec = importlib.util.spec_from_file_location("results_tables", HERE.parent / "tables" / "make_results.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)

OUT = HERE
SHADES = ["0.05", "0.35", "0.62", "0.85"]
HATCHES = ["", "//", "..", ""]


def _plt():
    figkit.style()
    import matplotlib.pyplot as plt

    return plt


def fig_findings(data: dict) -> None:
    """Findings of each case by severity, stacked, with the total at the end of each bar."""
    plt = _plt()
    cases = [c for c in data["cases"] if c["findings"]]
    ids = [c["id"] for c in cases]
    y = np.arange(len(cases))
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    left = np.zeros(len(cases))
    for k, s in enumerate(rt.SEV):
        vals = np.array([c["findings"]["by_severity"][s] for c in cases], dtype=float)
        ax.barh(y, vals, left=left, color=SHADES[k], edgecolor="black", linewidth=0.4, hatch=HATCHES[k], label=s)
        left += vals
    for yi, tot in zip(y, left):
        ax.text(tot + 1.0, yi, f"{int(tot)}", va="center", fontsize=7)
    ax.set_yticks(y)
    ax.set_yticklabels(ids)
    ax.invert_yaxis()
    ax.set_xlabel("Findings in the register (count)")
    ax.set_xlim(0, left.max() * 1.1)
    ax.legend(title="Severity", loc="lower right", frameon=False, ncol=2)
    ax.grid(axis="x", linewidth=0.3, color="0.8")
    ax.set_axisbelow(True)
    figkit.save(fig, OUT, "results-findings")


def fig_lights(data: dict) -> None:
    """Share of the tests of each case that end green, amber, red or not evaluated, over all its validation reports."""
    plt = _plt()
    cases = [c for c in data["cases"] if c["reports"]]
    ids = [c["id"] for c in cases]
    keys = ["green", "amber", "red", "not_evaluated"]
    names = ["Green", "Amber", "Red", "Not evaluated"]
    tot = np.array([[sum(r["counts"][k] for r in c["reports"]) for k in keys] for c in cases], dtype=float)
    share = tot / tot.sum(axis=1, keepdims=True)
    y = np.arange(len(cases))
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    left = np.zeros(len(cases))
    for k in range(4):
        ax.barh(y, 100 * share[:, k], left=left, color=SHADES[3 - k] if k < 3 else "white", edgecolor="black", linewidth=0.4,
                hatch=["", "//", "", ".."][k], label=names[k])
        left += 100 * share[:, k]
    ax.set_yticks(y)
    ax.set_yticklabels(ids)
    ax.invert_yaxis()
    ax.set_xlabel("Tests of the case (percent)")
    ax.set_xlim(0, 100)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), frameon=False, ncol=4)
    figkit.save(fig, OUT, "results-lights")


def fig_architecture(n_sources: int) -> None:
    """The data flow of the system: sources, contract 1, the offline pipeline and the engine, contract 2, and the three lanes."""
    plt = _plt()
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(6.6, 3.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")

    def box(x, y, w, h, text, shade="1.0", hatch=None):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", facecolor=shade, edgecolor="black",
                                    linewidth=0.7, hatch=hatch))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=6.6)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", lw=0.8, color="black"))

    box(1, 36, 16, 14, "Source registry\nand fetcher\n(" + str(n_sources) + " sources)", "0.92")
    box(1, 14, 16, 14, "Licence\nmanifest\n(SHA-256)", "0.92")
    box(24, 36, 17, 14, "Contract 1:\neight ingestion\nfamilies", "0.82")
    box(24, 14, 17, 14, "Licence\nlineage check", "0.92")
    box(48, 22, 20, 28, "Offline pipeline\ningest, split,\ntrain, infer,\nevaluate, export", "0.88")
    box(48, 4, 20, 14, "Engine\nriskvalidation\n(PyPI)", "0.75")
    box(75, 36, 22, 14, "Contract 2:\nmanifests, variants,\nmodels, governance", "0.82")
    box(75, 20, 22, 11, "Replay lane:\nstatic site", "0.95")
    box(75, 6, 22, 11, "Live lane:\nTypeScript ports\nwith parity tests", "0.95")
    arrow(17.5, 43, 23.5, 43)
    arrow(9, 35.5, 9, 28.5)
    arrow(41.5, 43, 47.5, 43)
    arrow(33, 35.5, 33, 28.5)
    arrow(58, 17.5, 58, 21.5)
    arrow(68.5, 43, 74.5, 43)
    arrow(86, 35.5, 86, 31.5)
    arrow(86, 19.5, 86, 17.5)
    ax.text(50, 53.5, "committed artifacts under data/derived are the only product of the offline lane", ha="center", fontsize=6.6, style="italic")
    figkit.save(fig, OUT, "results-architecture")


def main() -> None:
    data = rt.derive()
    fig_findings(data)
    fig_lights(data)
    fig_architecture(len(data["sources"]["sources"]))
    print("wrote results-findings.pdf, results-lights.pdf and results-architecture.pdf")


if __name__ == "__main__":
    main()
