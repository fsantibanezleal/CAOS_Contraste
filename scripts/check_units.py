#!/usr/bin/env python3
"""CONTRACT 3 of the units rule (CAOS_MANAGE ``conventions/units-gate.md``) over the SHIPPED artifacts (CT-2404, CT-2409).

The bake runs the unit gate before it writes an artifact (``stages/export.py``); this script runs the SAME function again over
every committed document under ``data/derived/``, so an artifact baked before the gate existed, or edited by hand, cannot ship
either. Standard library only, and nothing from the pipeline package: it loads ``data-pipeline/pipeline/stages/unit_gate.py``
by path (that module imports only the standard library), reads ``data-pipeline/config/unit_pairs.json`` and judges with
``unit_gate.check_document``. It runs in CI and before a Pages deploy without installing the pipeline, and in ``scripts/smoke.*``.

What it checks, per case of the specification
    pairs         every committed file of ``data/derived/<case>/`` is judged by ``check_document`` (a glob that matches no
                  committed file is an error: the specification and the tree disagree; a path that resolves to nothing, a
                  value that is not a number or any other ``UnitGateError`` is a blocking finding, never a pass)
    withheld      the target is not published, so the pairs are not checkable from the shipped files; the verdict the bake
                  recorded in the case manifest (``contract.units``, task T3) is read, and a verdict that records a blocking
                  violation fails. Before T3 ships no manifest carries one: reported as "no verdict recorded", not a failure
    bake_only     predictions never reach an artifact with their target: reported as checked in the bake
    not_applicable  reported with its reason
A case folder under ``data/derived/`` without an entry in the specification is an error (nothing is skipped silently), and so is
an entry whose folder is missing.

Output is ordered by case, file and pair. Exit 0 when nothing blocks, 1 on any blocking finding or specification error.
Usage: python scripts/check_units.py [repo_root]
"""
from __future__ import annotations

import fnmatch
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
GATE = ROOT / "data-pipeline" / "pipeline" / "stages" / "unit_gate.py"
SPEC = ROOT / "data-pipeline" / "config" / "unit_pairs.json"
DERIVED = ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"
CASE_DIR = re.compile(r"^C\d+")


def load_gate():
    spec = importlib.util.spec_from_file_location("unit_gate_shipped", GATE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["unit_gate_shipped"] = module  # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(module)
    return module


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def recorded_violations(node, where: str):
    """The blocking violations a recorded verdict names: every ``violations`` that is a non-empty list or a count above 0."""
    if isinstance(node, dict):
        for key in sorted(node, key=str):
            value = node[key]
            if key == "violations":
                if (isinstance(value, list) and value) or (isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0):
                    yield where, value
            else:
                yield from recorded_violations(value, f"{where}.{key}")
    elif isinstance(node, list):
        for i, element in enumerate(node):
            yield from recorded_violations(element, f"{where}[{i}]")


def describe(violation: dict) -> str:
    method = "" if violation["method"] is None else f" method {violation['method']}"
    element = "" if violation["element"] is None else f" element {violation['element']}"
    return (f"{violation['case']} {violation['file']} {violation['pair']}{method}{element} {violation['class']}: "
            f"{violation['detail']}")


def main() -> int:
    for path in (GATE, SPEC):
        if not path.is_file():
            print(f"BLOCKING units: {path.relative_to(ROOT).as_posix()} is absent")
            return 1
    gate = load_gate()
    problems: list[str] = []
    advisories: list[str] = []
    lines: list[str] = []
    try:
        spec = read_json(SPEC)
        gate.validate_spec(spec)
    except (ValueError, OSError) as exc:
        print(f"BLOCKING units: {SPEC.relative_to(ROOT).as_posix()} is not a valid specification: {exc}")
        return 1

    folders = sorted(p.name for p in DERIVED.iterdir() if p.is_dir() and CASE_DIR.match(p.name)) if DERIVED.is_dir() else []
    for folder in folders:
        if folder not in spec:
            problems.append(f"{folder}: a case folder of data/derived/ with no entry in unit_pairs.json (no entry, nothing is skipped silently)")

    n_files = n_pairs = 0
    for case in sorted(spec):
        entry = spec[case]
        kind = next(k for k in gate.ENTRY_KINDS if k in entry)
        directory = DERIVED / case
        if not directory.is_dir():
            problems.append(f"{case}: the specification has an entry but data/derived/{case}/ does not exist")
            continue
        files = sorted(p.relative_to(directory).as_posix() for p in directory.rglob("*.json"))
        checked = 0
        case_advisories = 0
        if kind == "pairs" or "withheld" in entry:
            for pair in entry.get("pairs", []) + entry.get("withheld", []):
                if not any(fnmatch.fnmatchcase(rel, pair["file"]) for rel in files):
                    problems.append(f"{case} {pair['id']}: the glob {pair['file']!r} matches no committed file "
                                    f"(the specification and the tree disagree)")
        if "pairs" in entry:
            for rel in files:
                try:
                    result = gate.check_document(case, rel, read_json(directory / rel), spec)
                except gate.UnitGateError as exc:
                    problems.append(f"{case} {rel}: {exc}")
                    continue
                except (ValueError, OSError) as exc:
                    problems.append(f"{case} {rel}: the document cannot be read: {exc}")
                    continue
                n_files += 1
                checked += result.pairs_checked
                problems += [describe(v) for v in result.violations]
                advisories += [describe(v) for v in result.advisories]
                case_advisories += len(result.advisories)
            n_pairs += checked
        extra = ""
        if "withheld" in entry:
            verdict = None
            manifest_path = MANIFESTS / f"{case}.json"
            if manifest_path.is_file():
                units = (read_json(manifest_path).get("contract") or {}).get("units")
                verdict = units.get("withheld") if isinstance(units, dict) else None
            if verdict is None:
                extra = f"; withheld {len(entry['withheld'])} pair(s): no verdict recorded in the manifest yet (task T3)"
            else:
                extra = f"; withheld {len(entry['withheld'])} pair(s): verdict recorded in the manifest"
                for where, value in recorded_violations(verdict, f"{case} manifest contract.units.withheld"):
                    problems.append(f"{where}: the recorded verdict holds blocking violation(s): {json.dumps(value, sort_keys=True)}")
        if kind == "bake_only":
            extra = f"; bake_only: checked in the bake by {entry['bake_only']['hook']}"
        elif kind == "not_applicable":
            extra = f"; not_applicable: {entry['not_applicable']}"
        lines.append(f"{case} {kind}: {len(files)} files, {checked} pair checks, {case_advisories} advisories{extra}")

    for line in lines:
        print(line)
    for line in advisories:
        print(f"ADVISORY {line}")
    for line in problems:
        print(f"BLOCKING {line}")
    status = "FAILED" if problems else "OK"
    print(f"units {status}: {len(spec)} cases, {n_files} documents judged, {n_pairs} pair checks, "
          f"{len(advisories)} advisories, {len(problems)} blocking")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
