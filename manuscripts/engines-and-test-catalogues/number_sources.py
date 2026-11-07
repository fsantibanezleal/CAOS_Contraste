"""List every number macro of the prose (``tables/numbers.tex``), the sections that use it and its source, as a markdown table.

    python manuscripts/engines-and-test-catalogues/number_sources.py [--unused]

Exit 1 when the prose uses a macro that ``numbers.tex`` does not define (a number that would have to be typed by hand).
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BUILTIN = {
    "doctype", "docversion", "docdate", "versiondoi", "conceptdoi", "docidentity", "docrepo", "headerblock", "cite", "citep", "citet", "ref",
    "eqref", "label", "section", "subsection", "texttt", "emph", "textbf", "text", "input", "includegraphics", "caption", "item", "begin", "end",
    "title", "author", "date", "maketitle", "orcidlink", "small", "centering", "bibliography", "bibliographystyle", "newcommand", "ensuremath",
    "times", "ln", "max", "min", "sum", "frac", "sqrt", "left", "right", "mathrm", "mathbb", "mathbf", "tfrac", "pm", "le", "ge", "ldots",
    "cdots", "dots", "in", "infty", "mid", "inf", "operatorname", "textwidth", "linewidth", "hline", "toprule", "midrule", "bottomrule",
    "State", "For", "If", "Else", "EndFor", "EndIf", "Require", "Ensure", "Return", "Cref", "cref", "href", "url", "nonumber", "quad", "qquad",
    "widehat", "hat", "bar", "alpha", "beta", "delta", "xi", "rho", "sigma", "mu", "nu", "pi", "varepsilon", "Phi", "Delta", "Pr", "ge",
    "geq", "leq", "neq", "approx", "cdot", "to", "subset", "ge", "forall", "exists", "eta", "lambda", "theta", "tau", "boldsymbol", "boldmath",
    "mathcal", "emph", "paragraph", "texttt", "footnotesize", "tiny", "normalsize", "large", "Large", "bf", "it", "tt", "mbox", "hspace",
    "vspace", "noindent", "par", "newline", "linebreak", "pagebreak", "clearpage", "newpage", "centering", "raggedright", "label",
}


def definitions() -> dict[str, str]:
    defs, source = {}, ""
    for line in (ROOT / "tables" / "numbers.tex").read_text(encoding="utf-8").splitlines():
        if line.startswith("% ") and not line.startswith("% Generated"):
            source = line[2:]
        m = re.match(r"\\newcommand\{\\([A-Za-z]+)\}", line)
        if m:
            defs[m.group(1)] = source
    return defs


def usage() -> dict[str, set[str]]:
    used: dict[str, set[str]] = {}
    files = [ROOT / "main.tex"] + sorted((ROOT / "sections").glob("*.tex"))
    for f in files:
        text = re.sub(r"(?<!\\)%.*", "", f.read_text(encoding="utf-8"))
        for m in re.finditer(r"\\([A-Za-z]+)\{\}", text):
            used.setdefault(m.group(1), set()).add(f.stem)
        for m in re.finditer(r"\\([A-Za-z]+)(?![A-Za-z{])", text):
            used.setdefault(m.group(1), set()).add(f.stem)
    return used


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unused", action="store_true")
    a = ap.parse_args()
    defs, used = definitions(), usage()
    undefined = sorted(k for k in used if k not in defs and re.search(r"\\" + k + r"\{\}", "".join(
        re.sub(r"(?<!\\)%.*", "", f.read_text(encoding="utf-8")) for f in [ROOT / "main.tex"] + sorted((ROOT / "sections").glob("*.tex")))))
    print("| Macro | Used in | Source |\n|---|---|---|")
    for k in sorted(defs):
        if k in used or a.unused:
            print(f"| `\\{k}` | {', '.join(sorted(used.get(k, [])))} | {defs[k]} |")
    if undefined:
        print("UNDEFINED macros used as numbers:", ", ".join(undefined), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
