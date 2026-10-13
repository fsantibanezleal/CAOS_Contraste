"""Fixtures of the C06 tests: the committed sample (a few thousand SBA 7(a) rows and the Federal Reserve tables trimmed to the
columns the case reads, ``tests/c06/data``), read once per session. No test bakes the real data (ADR-0074)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
sys.path.insert(0, str(ROOT / "data-pipeline"))

MIN_QUARTER = 60  # the sample is small: a quarter enters the systematic factor with 60 loans at risk
SAMPLE_DATES = ("2010-12-31", "2020-06-30")


@pytest.fixture(scope="session")
def tables():
    from pipeline.cases.c06 import panel
    from pipeline.io import sba as readers

    df = readers.read_sba(DATA)
    fed = readers.read_fed(DATA)
    loans, counts = panel.prepare(df)
    return {"frame": df, "fed": fed, "loans": loans, "counts": counts}


@pytest.fixture(scope="session")
def variant(tables):
    from pipeline.cases.c06.variant import bake_variant

    return bake_variant(tables["loans"], tables["fed"], np.datetime64("2010-12-31"), 42, min_quarter_at_risk=MIN_QUARTER,
                        cleaning=tables["counts"])


@pytest.fixture(scope="session")
def variant_with_overlay(tables):
    from riskvalidation.provisions.overlays import Overlay

    from pipeline.cases.c06.variant import bake_variant

    ov = Overlay(id="OVL-TEST", rationale_en="A test overlay", rationale_es="Un ajuste de prueba", method="expert", target="pd",
                 segment_id=None, stage="stage1", amount=1_000_000.0, staging_effect="none", review_date="2011-03-31", currency="USD")
    return bake_variant(tables["loans"], tables["fed"], np.datetime64("2010-12-31"), 42, overlays=[ov], min_quarter_at_risk=MIN_QUARTER)


def sample_expect(values):
    """Broad ranges for the sample: the plumbing of the expected-range check, not the real result."""
    return {k: (-1e18, 1e18) for k in values}


@pytest.fixture(scope="session")
def sample_bake(tmp_path_factory, tables):
    """Two sample bakes of the case, two reporting dates, into two output roots (the seed the same)."""
    import pytest as _pt

    from pipeline.cases.c06 import _case
    from pipeline.cases.c06 import build as bd
    from pipeline.pipeline import PipelinePaths

    out = {}
    mp = _pt.MonkeyPatch()
    mp.setattr(_case, "REPORTING_DATES", SAMPLE_DATES)
    mp.setattr(_case, "DEFAULT_VARIANT", "rd-2020-06")
    mp.setattr(bd, "EXPECT", {f"coverage@{d}": (0.0, 1.0) for d in SAMPLE_DATES})
    mp.setattr("pipeline.cases.c06.variant.MIN_QUARTER_DEFAULT", MIN_QUARTER, raising=False)
    mp.setattr(_case, "MIN_QUARTER_AT_RISK", MIN_QUARTER, raising=False)
    try:
        for name in ("a", "b"):
            root = tmp_path_factory.mktemp(f"bake-{name}")
            paths = PipelinePaths.from_output(root)
            manifest = _case.CASE.bake(seed=42, paths=paths, data_root=DATA)
            out[name] = (root, manifest)
    finally:
        mp.undo()
    return out
