"""Constants of the C10 tests, under a module name of their own (BL-084: a helper imported as `conftest` resolves to another
case's conftest when several case folders run in one pytest session)."""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SAMPLE = HERE / "sample" / "chgallsa-sample.htm"
SCALE = 0.004
SEED = 42
#: loan types the determinism and the seed tests bake (the others add time, not coverage)
ONE_TYPE = ("credit-cards",)
TYPES = ("credit-cards", "residential")   # one retail type with a full history and one whose first six years are n.a.
