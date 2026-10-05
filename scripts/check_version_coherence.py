#!/usr/bin/env python3
"""T4: VERSION is the single source of the version, and everything that states a version agrees with it.

Fails when:
  - VERSION is not X.XX.XXX;
  - frontend/package.json's version is not the semver form of VERSION (0.02.000 -> 0.2.0);
  - the top entry of CHANGELOG.md is not VERSION;
  - a source file writes a version literal (X.XX.XXX) instead of reading VERSION (Python, TypeScript, TSX);
  - VERSION is behind the latest vX.XX.XXX tag.
Every manifest records the version it was baked with; that is a record, not a source, so data/ is not scanned.
Stdlib only. Usage: python scripts/check_version_coherence.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPLAY = re.compile(r"^(\d+)\.(\d{2})\.(\d{3})$")
LITERAL = re.compile(r"(?<![\d.])\d+\.\d{2}\.\d{3}(?![\d.])")
SCANNED = ("data-pipeline", "app", "frontend/src", "frontend/scripts", "scripts", "tests")
# instantiate.py writes a new product's first version (0.01.000) by design; it is not a source of this version.
SKIP = {"scripts/check_version_coherence.py", "scripts/instantiate.py"}


def semver(display: str) -> str:
    major, minor, patch = DISPLAY.match(display).groups()
    return f"{int(major)}.{int(minor)}.{int(patch)}"


def key(display: str) -> tuple[int, int, int]:
    return tuple(int(x) for x in DISPLAY.match(display).groups())


def main() -> int:
    errs: list[str] = []
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not DISPLAY.match(version):
        print(f"VERSION {version!r} is not X.XX.XXX")
        return 1
    pkg = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    if pkg.get("version") != semver(version):
        errs.append(f"frontend/package.json version {pkg.get('version')} is not {semver(version)} (VERSION {version})")
    top = re.search(r"^## \[([^\]]+)\]", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.MULTILINE)
    if not top or top.group(1) != version:
        errs.append(f"the top CHANGELOG entry is {top.group(1) if top else 'missing'}, not {version}")
    for base in SCANNED:
        for f in sorted((ROOT / base).rglob("*")):
            rel = f.relative_to(ROOT).as_posix()
            if f.suffix not in {".py", ".ts", ".tsx", ".mjs"} or "node_modules" in f.parts or rel in SKIP:
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if LITERAL.search(line):
                    errs.append(f"{rel}:{n}: a version literal; read VERSION instead")
    try:
        tags = subprocess.run(["git", "tag", "--list", "v*"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    released = sorted((t[1:] for t in tags if DISPLAY.match(t[1:])), key=key)
    if released and key(version) < key(released[-1]):
        errs.append(f"VERSION {version} is behind the latest tag v{released[-1]}")
    for e in errs:
        print(f"version: {e}")
    if not errs:
        print(f"version: OK, {version} everywhere")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
