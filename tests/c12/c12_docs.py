"""Loaders and checks shared by the C12 document tests."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import c12_support  # noqa: F401  (puts the contract test folders on the path)
import contract_schemas as cs
from c12_support import semantics

ROOT = c12_support.ROOT
DERIVED = ROOT / "data" / "derived"
C12 = DERIVED / "C12"
VARIANTS = ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im", "wrong-way-risk")
MODELS = "models-hw1f-treasury-2000-2025"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def variant(vid: str) -> dict[str, Any]:
    return load(C12 / f"{vid}.json")


def models() -> dict[str, Any]:
    return load(C12 / f"{MODELS}.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def problems(doc: dict[str, Any], path: Path | None = None) -> list[str]:
    """Schema errors then the contract's semantic findings of one document."""
    ref = cs.schema_for_document(path or (C12 / "x.json"), doc)
    found = cs.errors(ref, doc)
    if found:
        return [f"schema: {found[0]}"]
    return semantics.check_c12(doc) if "outputs" in doc else semantics.check_c12_models(doc)


def mutated(doc: dict[str, Any], fn) -> dict[str, Any]:
    out = copy.deepcopy(doc)
    fn(out)
    return out
