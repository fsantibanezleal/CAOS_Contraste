#!/usr/bin/env python3
"""CT-005: the default install contains no AGPL, GPL or BSL package (SDD section 8).

Static (CI, standard library only):
  1. every package named by a requirements file of the default install (requirements-precompute.txt and what it
     includes, requirements-api.txt, requirements-dev.txt) has a verified licence in
     data-pipeline/config/licences.json, and none of those licences is forbidden;
  2. every package in frontend/package-lock.json declares a licence, and none is forbidden.

With --installed (locally, in .venv-pipeline after setup): every distribution installed in the running interpreter,
direct or transitive, is read from its own metadata (License-Expression, License, classifiers) and fails on a
forbidden licence; a requirement whose installed licence differs from the table is reported.

LGPL is weak copyleft and is not in the forbidden set. Exit 1 on any finding.
Usage: python scripts/check_licences.py [--installed]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data-pipeline" / "config" / "licences.json"
ROOTS = ("requirements-precompute.txt", "requirements-api.txt", "requirements-dev.txt")
LOCK = ROOT / "frontend" / "package-lock.json"

# GPL and AGPL, not LGPL; the Business Source License by its SPDX id (BUSL) or its name. "BSL-1.0" is the
# permissive Boost Software License, so the bare letters BSL are not matched.
FORBIDDEN = re.compile(r"(?<![A-Za-z])A?GPL|GNU (?:Affero )?General Public|\bBUSL\b|Business Source", re.I)
NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirements(path: Path, seen: set[Path] | None = None) -> list[tuple[str, str]]:
    """(package, where) for every requirement line, following -r includes."""
    seen = seen if seen is not None else set()
    if path in seen or not path.exists():
        return []
    seen.add(path)
    out: list[tuple[str, str]] = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-r ", "--requirement ")):
            out.extend(requirements((path.parent / line.split(None, 1)[1]).resolve(), seen))
            continue
        if line.startswith("-"):
            continue
        m = NAME.match(line)
        if m:
            out.append((normal(m.group(1)), f"{path.relative_to(ROOT).as_posix()}:{n}"))
    return out


def static_findings() -> tuple[list[str], int, int]:
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    known = {normal(k): v for k, v in table["python"].items()}
    findings: list[str] = []
    reqs: list[tuple[str, str]] = []
    for name in ROOTS:
        reqs.extend(requirements(ROOT / name))
    for pkg, where in reqs:
        entry = known.get(pkg)
        if entry is None:
            findings.append(f"{where}: {pkg} has no verified licence in {TABLE.relative_to(ROOT).as_posix()}")
        elif FORBIDDEN.search(entry["licence"]):
            findings.append(f"{where}: {pkg} is licensed {entry['licence']} (forbidden in the default install)")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    n_js = 0
    for key, meta in lock.get("packages", {}).items():
        if not key:
            continue
        n_js += 1
        lic = meta.get("license")
        if not lic:
            findings.append(f"frontend/package-lock.json: {key} declares no licence")
        elif FORBIDDEN.search(str(lic)):
            findings.append(f"frontend/package-lock.json: {key} is licensed {lic} (forbidden)")
    return findings, len({p for p, _ in reqs}), n_js


def installed_findings() -> tuple[list[str], int]:
    import importlib.metadata as md

    table = {normal(k): v for k, v in json.loads(TABLE.read_text(encoding="utf-8"))["python"].items()}
    findings: list[str] = []
    dists = list(md.distributions())
    for d in dists:
        meta = d.metadata
        name = normal(meta["Name"])
        classifiers = [c.split("::")[-1].strip() for c in (meta.get_all("Classifier") or []) if c.startswith("License")]
        declared = " | ".join(x for x in (meta.get("License-Expression"), (meta.get("License") or "").splitlines()[0]
                                          if meta.get("License") else None, *classifiers) if x)
        if FORBIDDEN.search(declared or ""):
            findings.append(f"installed {meta['Name']} {d.version}: {declared} (forbidden in the default install)")
        if name in table and meta.get("License-Expression") and meta["License-Expression"] != table[name]["licence"]:
            print(f"note: {meta['Name']} {d.version} declares {meta['License-Expression']!r}; the table records "
                  f"{table[name]['licence']!r} (re-verify)")
    return findings, len(dists)


def main() -> int:
    findings, n_py, n_js = static_findings()
    extra = ""
    if "--installed" in sys.argv[1:]:
        inst, n = installed_findings()
        findings.extend(inst)
        extra = f"; {n} installed distributions read from their metadata"
    if findings:
        print("LICENCE CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    print(f"check_licences: OK, {n_py} Python requirements with verified licences, {n_js} frontend packages{extra}; "
          "no AGPL, GPL or BSL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
