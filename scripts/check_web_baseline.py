#!/usr/bin/env python3
"""T7: the web baseline a reader never sees go wrong until it does (failure classes 1, 8, 18, 24, 25).

Static checks on frontend/src, against the installed shell (node_modules/@fasl-work/caos-app-shell):
  - every var(--x) the app names is defined, by the shell's stylesheet or by the app's own CSS (an undefined token
    renders as nothing, silently);
  - every class written in a className string has a rule in the shell or in the app's CSS;
  - no app CSS rule redefines a class the shell reserves (reserved-classes.json);
  - no App tab named after the plumbing (contract, trace, learned models, bring your own data);
  - no toLocaleString() without a locale, and no toFixed() in a view (numbers go through formatNumber);
  - no <img> of an .svg (an image cannot read the page's theme tokens);
  - no requestAnimationFrame outside the shell's usePausedViz (a loop at rest burns the reader's battery).
Run after `npm ci` in frontend/. Stdlib only. Usage: python scripts/check_web_baseline.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src"
SHELL = ROOT / "frontend" / "node_modules" / "@fasl-work" / "caos-app-shell"

VAR_USE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")
VAR_DEF = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")
CLASS_RULE = re.compile(r"\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)")
CLASSNAME = re.compile(r"className=(?:\"([^\"]*)\"|'([^']*)'|\{\s*['\"]([^'\"]*)['\"]\s*\})")
TAB_LABEL = re.compile(r"\blabel:\s*\{\s*en:\s*'([^']*)'")
BANNED_TABS = re.compile(r"\b(contract|trace|learned models?|bring your own)\b", re.I)


def css_files() -> list[Path]:
    return sorted(p for p in SRC.rglob("*.css"))


def code_files() -> list[Path]:
    return sorted(p for p in SRC.rglob("*") if p.suffix in {".ts", ".tsx"} and not p.name.endswith(".test.ts"))


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def main() -> int:
    if not SHELL.is_dir():
        print("web baseline: the shell is not installed (run npm ci in frontend/ first)")
        return 1
    shell_css = "".join(strip_comments((SHELL / f).read_text(encoding="utf-8")) for f in ("styles.css", "chart.css"))
    reserved = set(json.loads((SHELL / "reserved-classes.json").read_text(encoding="utf-8"))["classes"])
    app_css = "".join(strip_comments(p.read_text(encoding="utf-8")) for p in css_files())
    defined_vars = set(VAR_DEF.findall(shell_css)) | set(VAR_DEF.findall(app_css))
    styled = set(CLASS_RULE.findall(shell_css)) | set(CLASS_RULE.findall(app_css))
    errs: list[str] = []

    for cls in sorted(set(CLASS_RULE.findall(app_css)) & reserved):
        errs.append(f"app CSS redefines the shell class .{cls} (reserved-classes.json)")

    for f in code_files() + css_files():
        rel = f.relative_to(ROOT).as_posix()
        text = f.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            for var in VAR_USE.findall(line):
                if var not in defined_vars:
                    errs.append(f"{rel}:{n}: var({var}) is not defined by the shell or the app")
            if f.suffix == ".css":
                continue
            for groups in CLASSNAME.findall(line):
                for cls in " ".join(groups).split():
                    if cls not in styled:
                        errs.append(f"{rel}:{n}: class {cls!r} has no rule in the shell or the app CSS")
            if re.search(r"\.toLocaleString\(\s*\)", line):
                errs.append(f"{rel}:{n}: toLocaleString() without a locale; use formatNumber or useFormat")
            if f.suffix == ".tsx" and ".toFixed(" in line:
                errs.append(f"{rel}:{n}: toFixed() in a view; use formatNumber or useFormat (locale and absent values)")
            if re.search(r"<img\b[^>]*\.svg", line):
                errs.append(f"{rel}:{n}: an <img> of an SVG cannot read the theme; inline it (?raw)")
            if "requestAnimationFrame" in line:
                errs.append(f"{rel}:{n}: requestAnimationFrame outside usePausedViz")
        if "/workbench/" in rel:
            for label in TAB_LABEL.findall(text):
                if BANNED_TABS.search(label):
                    errs.append(f"{rel}: the App tab {label!r} is named after the plumbing, not the question")

    for e in errs:
        print(f"web baseline: {e}")
    if not errs:
        print(f"web baseline: OK ({len(code_files())} source files, {len(defined_vars)} tokens, {len(styled)} classes)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
