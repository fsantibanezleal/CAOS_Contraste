"""List every number macro of the prose (``tables/numbers.tex``), the sections that use it and its source, as a markdown table.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/number_sources.py [--unused]

Exit 1 when the prose uses a macro that ``numbers.tex`` does not define (a number that would have to be typed by hand), or when a source file holds a control
character other than a line ending or a tab (a carriage return inside a line turns ``\\randomN`` into ``andomN`` in the typeset text).
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SECTION = {
    "main": "Abstract", "s01-introduction": "1 Introduction", "s02-related-work": "2 Related work", "s03-problem": "3 Problem formulation",
    "s04-proposed-method": "4 Proposed method", "s05-theory": "5 Theory", "s06-experimental-design": "6 Experimental design", "s07-results": "7 Results",
    "s08-ablation": "8 Ablation", "s09-discussion": "9 Discussion", "s10-limitations": "10 Limitations", "s11-reproducibility": "11 Reproducibility",
    "s12-conclusions": "12 Conclusions",
}
ORDER = list(SECTION.values())
HEADER_MACROS = {"doctype", "docversion", "docdate", "versiondoi", "conceptdoi", "docidentity"}


def definitions() -> dict[str, tuple[str, str]]:
    defs: dict[str, tuple[str, str]] = {}
    source = ""
    for line in (ROOT / "tables" / "numbers.tex").read_text(encoding="utf-8").splitlines():
        if line.startswith("% ") and not line.startswith("% Generated"):
            source = line[2:]
        m = re.match(r"\\newcommand\{\\(\w+)\}\{(.*)\}$", line)
        if m:
            defs[m.group(1)] = (m.group(2), source)
    return defs


def control_characters() -> list[str]:
    """The ``file:line`` of every control character in the TeX sources other than a tab and a line ending (LF or CRLF)."""
    bad = []
    files = [ROOT / "main.tex"] + sorted((ROOT / "sections").glob("*.tex")) + sorted((ROOT / "tables").glob("*.tex"))
    for f in files:
        for n, line in enumerate(f.read_bytes().replace(b"\r\n", b"\n").split(b"\n"), 1):
            if any(c < 0x20 and c != 0x09 for c in line):
                bad.append(f"{f.relative_to(ROOT).as_posix()}:{n}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unused", action="store_true", help="also list the macros no section uses")
    args = ap.parse_args()
    defs = definitions()
    used: dict[str, set[str]] = {}
    for f in [ROOT / "main.tex"] + sorted((ROOT / "sections").glob("*.tex")):
        for m in re.finditer(r"\\([A-Za-z]+)\{\}", f.read_text(encoding="utf-8")):
            used.setdefault(m.group(1), set()).add(SECTION[f.stem])
    missing = sorted(k for k in used if k not in defs and k not in HEADER_MACROS)
    print("| Macro | Value | Sections | Source (JSON path under experiments/ or committed file) |\n|---|---|---|---|")
    rows = sorted(((min(ORDER.index(s) for s in secs), k) for k, secs in used.items() if k in defs))
    for _, k in rows:
        v, s = defs[k]
        secs = ", ".join(sorted(used[k], key=ORDER.index))
        print(f"| `{k}` | {v.replace('|', '/')} | {secs} | {s} |")
    if args.unused:
        for k in sorted(set(defs) - set(used)):
            print(f"| `{k}` | {defs[k][0]} | (not used) | {defs[k][1]} |")
    print(f"\nmacros used: {len(rows)}; defined: {len(defs)}; used but undefined: {len(missing)} {missing}")
    bad = control_characters()
    print(f"control characters in the sources: {len(bad)} {bad}")
    return 1 if missing or bad else 0


if __name__ == "__main__":
    sys.exit(main())
