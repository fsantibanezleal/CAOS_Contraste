"""What every figure and table script of a Contraste manuscript shares (CAOS_MANAGE conventions/manuscript-content-bar.md
section 2, points 5 and 6): the repository root, the committed artifacts read from ``data/derived``, one matplotlib style
that stays readable in grayscale, vector PDF output, and a booktabs table writer, so that no number in a manuscript is
typed by hand.

A script imports it with::

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_shared"))
    import figkit
"""
from __future__ import annotations

import json
import pathlib
from collections.abc import Iterable, Sequence
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived"

#: Line styles and markers that tell series apart without colour (grayscale print).
STYLES = [
    {"color": "0.0", "linestyle": "-", "marker": "o"},
    {"color": "0.35", "linestyle": "--", "marker": "s"},
    {"color": "0.55", "linestyle": "-.", "marker": "^"},
    {"color": "0.2", "linestyle": ":", "marker": "D"},
    {"color": "0.45", "linestyle": (0, (5, 1, 1, 1)), "marker": "v"},
    {"color": "0.65", "linestyle": (0, (1, 1)), "marker": "x"},
]


def doc(rel: str) -> Any:
    """A committed document under ``data/derived`` (``"C04/sp.json"``)."""
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


def style() -> None:
    """The shared matplotlib style: serif text at the document's size, thin axes, no colour needed to read a figure."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.titlesize": 9,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.linewidth": 0.6,
        "lines.linewidth": 1.2,
        "lines.markersize": 4,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
    })


def save(fig: Any, out_dir: pathlib.Path, name: str) -> pathlib.Path:
    """Write a figure as vector PDF into ``out_dir`` and close it."""
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.pdf"
    fig.savefig(path)
    plt.close(fig)
    return path


def tex_escape(text: str) -> str:
    """Escape the characters LaTeX reads as commands in a table cell or a generated sentence."""
    out = []
    for ch in str(text):
        if ch in "&%$#_{}":
            out.append("\\" + ch)
        elif ch == "~":
            out.append("\\textasciitilde{}")
        elif ch == "^":
            out.append("\\textasciicircum{}")
        elif ch == "\\":
            out.append("\\textbackslash{}")
        else:
            out.append(ch)
    return "".join(out)


def fmt(x: Any, digits: int = 3) -> str:
    """A number as a table prints it: fixed digits, a dash for an absent value, the sign of a negative kept."""
    if x is None:
        return "--"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return f"{x:,}"
    if isinstance(x, float):
        if x != x:
            return "--"
        return f"{x:.{digits}f}"
    return tex_escape(str(x))


def table(path: pathlib.Path, header: Sequence[str], rows: Iterable[Sequence[Any]], *, caption: str, label: str,
          align: str | None = None, digits: int = 3, wide: bool = False) -> pathlib.Path:
    """Write a booktabs table environment to ``path`` (a ``.tex`` the document ``\\input``s). Cells are formatted with
    ``fmt``; a cell already a string is escaped unless it starts with ``$`` (math) or ``\\`` (a command)."""
    def cell(v: Any) -> str:
        if isinstance(v, str) and (v.startswith("$") or v.startswith("\\")):
            return v
        return fmt(v, digits)

    rows = [list(r) for r in rows]
    align = align or ("l" + "r" * (len(header) - 1))
    env = "table*" if wide else "table"
    lines = [f"\\begin{{{env}}}[htbp]", "\\centering", "\\small", f"\\caption{{{caption}}}", f"\\label{{{label}}}",
             f"\\begin{{tabular}}{{{align}}}", "\\toprule", " & ".join(header) + " \\\\", "\\midrule"]
    lines += [" & ".join(cell(v) for v in r) + " \\\\" for r in rows]
    lines += ["\\bottomrule", "\\end{tabular}", f"\\end{{{env}}}", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path
