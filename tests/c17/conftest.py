"""Fixtures of the C17 tests (ADR-0074: seconds to a few minutes, a small plan; the full bake is committed, never run in CI)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tests" / "contracts_u12"))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
DERIVED = ROOT / "data" / "derived"
DOCS = ("xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1")


def load(rel: str) -> dict:
    import json

    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def variants_():
    from pipeline.cases.c17 import generator

    return {v.tail_index: v for v in generator.variants()}


@pytest.fixture(scope="session")
def small_truths(variants_):
    from pipeline.cases.c17 import truth

    return {xi: truth.compute(v, mc_years=300_000) for xi, v in variants_.items()}
