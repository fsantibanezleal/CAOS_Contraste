"""Helpers of the U9-P2 regulatory parity bake tests (ADR-0074: seconds; the bake reads no data file, so every test runs everywhere)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "data" / "derived" / "regulatory" / "calculators.json"
INPUTS = ROOT / "data-pipeline" / "pipeline" / "regulatory" / "inputs.json"
REQUIREMENTS = ROOT / "data-pipeline" / "requirements.txt"
ENGINE_COMMIT = "25e9538faf10bfdbcde03c5adccffd8e86ec275c"
EAD_PUBLISHED = {"cre99-netting-set-1": 569, "cre99-netting-set-2": 381, "cre99-netting-set-3": 5406,
                 "cre99-netting-set-4": 936, "cre99-netting-set-5": 1879}


def load_semantics():
    """tests/contracts_u9/semantics.py under a name of its own (U10's suite ships a helper of the same name)."""
    name = "u9_p2_semantics"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / "contracts_u9" / "semantics.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def out(entry: dict, name: str):
    return next(v["value"] for v in entry["outputs"] if v["name"] == name)


def by_id(doc: dict) -> dict:
    return {e["id"]: e for e in doc["official_examples"] + doc["invariant_cases"]}
