"""Write frontend/src/workbench/names/registry.json: the test ids the engine registers, with the catalogue's English name and
family, so the frontend's names gate (names.test.ts) can check that every registered test has a name. Run from the repository
root with the bake environment (riskvalidation installed):

    python scripts/names_registry.py
"""
from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import riskvalidation.validation  # noqa: F401  (importing the battery registers every test)
from riskvalidation.core.registry import catalogue

OUT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "workbench" / "names" / "registry.json"


def main() -> None:
    rows = sorted(({"test_id": s.test_id, "name": s.name, "family": s.family} for s in catalogue()), key=lambda r: r["test_id"])
    doc = {"source": f"riskvalidation {version('riskvalidation')}, riskvalidation.core.registry.catalogue(); written by scripts/names_registry.py", "tests": rows}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} tests written to {OUT.as_posix()}")


if __name__ == "__main__":
    main()
