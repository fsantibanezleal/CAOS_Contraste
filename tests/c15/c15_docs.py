"""Loaders and checks shared by the C15 document tests."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import c15_support  # noqa: F401  (puts the contract test folders on the path)
import contract_schemas as cs
from c15_support import semantics
from c15_support import ROOT, SHOCKS, VARIANT_IDS  # noqa: F401

DERIVED = ROOT / "data" / "derived"
C15 = DERIVED / "C15"
MODELS = "models-banco-andino-2026-09"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def variant(vid: str) -> dict[str, Any]:
    return load(C15 / f"{vid}.json")


def models() -> dict[str, Any]:
    return load(C15 / f"{MODELS}.json")


def all_documents() -> dict[str, dict[str, Any]]:
    return {**{v: variant(v) for v in VARIANT_IDS}, MODELS: models()}


def problems(doc: dict[str, Any], path: Path | None = None) -> list[str]:
    """Schema errors then semantic findings of one document."""
    ref = cs.schema_for_document(path or (C15 / "x.json"), doc)
    return [*cs.errors(ref, doc), *semantics.check_document(doc)]


def mutated(doc: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(doc)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(a: Any, b: Any, path: str = "", rel: float = 1e-12, abs_tol: float = 1e-9) -> list[str]:
    """The places where two documents differ: a number beyond ``rel`` (and ``abs_tol``), any other value, a key or a length."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = [f"{path}: keys differ {sorted(set(a) ^ set(b))}"] if set(a) != set(b) else []
        for k in sorted(set(a) & set(b)):
            out += differences(a[k], b[k], f"{path}/{k}", rel, abs_tol)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} against {len(b)}"]
        return [x for i, (u, v) in enumerate(zip(a, b)) for x in differences(u, v, f"{path}[{i}]", rel, abs_tol)]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return [] if abs(a - b) <= max(abs_tol, rel * max(abs(a), abs(b))) else [f"{path}: {a} against {b}"]
    return [] if a == b else [f"{path}: {a!r} against {b!r}"]
