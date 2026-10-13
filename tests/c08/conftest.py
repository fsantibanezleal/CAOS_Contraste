"""Fixtures of the C08 tests: the committed sample (about ten thousand SBA 7(a) rows, ``tests/c08/data``), read once per session.
No test bakes the real data (ADR-0074); the sample bakes below stand for the plumbing and the invariants, never for a result."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session")
def tables():
    from pipeline.cases.c08 import panel
    from pipeline.io import sba as readers

    df = readers.read_sba(DATA)
    defaults, counts = panel.prepare(df)
    return {"frame": df, "defaults": defaults, "counts": counts, "annual": panel.annual_rate(df)}


@pytest.fixture(scope="session")
def annual(tables):
    """A constructed annual charge-off rate for the sample years (labelled so, not the book's): the sample keeps a fixed number of
    charge-offs per year, so its own rates say nothing about a cycle. 1.5 percent a year with a mild wiggle and 6 percent in
    2009 to 2011, which the policy threshold (the mean plus one standard deviation) flags, giving the cohort 2009-10 as the
    downturn cohort of the sample."""
    from pipeline.cases.c08.panel import AnnualRate

    real = tables["annual"]
    rate = 0.015 + 0.002 * np.sin(np.arange(len(real.years)))
    rate = np.where((real.years >= 2009) & (real.years <= 2011), 0.06, rate)
    return AnnualRate(years=real.years, at_risk=real.at_risk, chargeoffs=real.chargeoffs, rate=rate)


@pytest.fixture(scope="session")
def sample_bake(tmp_path_factory, annual):
    """Two sample bakes of the case into two output roots (the seed the same)."""
    import pytest as _pt

    from pipeline.cases.c08 import _case, panel
    from pipeline.cases.c08 import build as bd
    from pipeline.pipeline import PipelinePaths

    out = {}
    mp = _pt.MonkeyPatch()
    mp.setattr(bd, "EXPECT", {"n-defaults-total": (0.0, 1e18), **{f"mean-proxy@{c}": (-1e18, 1e18) for c in
                                                                 ("2003-06", "2007-08", "2009-10", "2011-13", "2014-19", "2020-23")}})
    mp.setattr(panel, "annual_rate", lambda df: annual)
    try:
        for name in ("a", "b"):
            root = tmp_path_factory.mktemp(f"bake-{name}")
            paths = PipelinePaths.from_output(root)
            manifest = _case.CASE.bake(seed=42, paths=paths, data_root=DATA)
            out[name] = (root, manifest)
    finally:
        mp.undo()
    return out


@pytest.fixture(scope="session")
def docs(sample_bake):
    """The variant documents of the first sample bake, by variant id, and its models documents."""
    import json

    root, manifest = sample_bake["a"]
    variants = {a["variant_id"]: json.loads((root / a["path"]).read_text(encoding="utf-8")) for a in manifest["artifacts"] if a["role"] == "variant"}
    models = {a["variant_id"]: json.loads((root / a["path"]).read_text(encoding="utf-8")) for a in manifest["artifacts"] if a["role"] == "models"}
    return {"variants": variants, "models": models, "manifest": manifest, "root": root}


def first_train(defaults, cutoff):
    from pipeline.cases.c08 import cutoff as C

    return defaults.take(C.training_mask(defaults, cutoff))


__all__ = ["np"]
