"""Loaders and checks shared by the C14 document tests."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import contract_schemas as cs
import semantics

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived"
C14 = DERIVED / "C14"
VARIANTS = ("vd-2021-q4", "vd-2022-q2", "vd-2022-q4")
MODELS = "models-svb-2021-2022"
SHOCKS = ("parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def variant(vid: str) -> dict[str, Any]:
    return load(C14 / f"{vid}.json")


def models() -> dict[str, Any]:
    return load(C14 / f"{MODELS}.json")


def all_documents() -> dict[str, dict[str, Any]]:
    return {**{v: variant(v) for v in VARIANTS}, MODELS: models()}


def problems(doc: dict[str, Any], path: Path | None = None) -> list[str]:
    """Schema errors then semantic findings of one document."""
    ref = cs.schema_for_document(path or (C14 / "x.json"), doc)
    return [*cs.errors(ref, doc), *semantics.check_document(doc)]


def mutated(doc: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(doc)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
