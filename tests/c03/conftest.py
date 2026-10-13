"""Fixtures of the C03 tests: the committed sample (10,800 SBA 7(a) rows, 300 disbursed loans from every approval fiscal year,
``tests/c03/data``), read once per session. No test bakes the real data (ADR-0074); the documents under ``data/derived/C03``
are checked as committed."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
sys.path.insert(0, str(ROOT / "data-pipeline"))

SAMPLE_COHORTS = ("fy2008-10",)
SEED = 42


@pytest.fixture(scope="session")
def tables():
    from pipeline.cases.c03 import panel
    from pipeline.io import sba

    df = sba.read_sba(DATA)
    loans, counts = panel.prepare(df)
    return {"frame": df, "loans": loans, "counts": counts}


@pytest.fixture(scope="session")
def cohort_2008():
    from pipeline.cases.c03 import windows

    return next(c for c in windows.COHORTS if c.id == "fy2008-10")


@pytest.fixture(scope="session")
def fit_2008(tables, cohort_2008):
    """The ladder of the FY2008-10 cohort fitted once on the sample (a few thousand loans of FY1991-2002)."""
    from pipeline.cases.c03 import fit, windows

    return fit.fit_window(tables["loans"], windows.training_window(cohort_2008), SEED)


@pytest.fixture(scope="session")
def sample_bake(tmp_path_factory):
    """Two bakes of the case on the sample, one cohort (a ladder fit takes about half a minute), into two output roots (the seed the same)."""
    from pipeline.cases.c03 import _case, windows
    from pipeline.pipeline import PipelinePaths

    out = {}
    mp = pytest.MonkeyPatch()
    cohorts = tuple(c for c in windows.COHORTS if c.id in SAMPLE_COHORTS)
    mp.setattr(_case, "COHORTS", cohorts)
    mp.setattr(_case, "DEFAULT_VARIANT", cohorts[-1].id)
    mp.setattr(_case, "EXPECT", {f"observed_5y_pd@{c.id}": (0.0, 1.0) for c in cohorts})
    try:
        for name in ("a", "b"):
            root = tmp_path_factory.mktemp(f"bake-{name}")
            paths = PipelinePaths.from_output(root)
            manifest = _case.CASE.bake(seed=SEED, paths=paths, data_root=DATA)
            out[name] = (root, manifest)
    finally:
        mp.undo()
    return out
