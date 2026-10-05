"""Leakage: CT-101 to CT-103, on a planted dataset shaped like a scored sample (no data root needed).

The case's own fitting path (split, then every rung of the ladder, then the calibration maps) is run twice: once on
the data, once with everything outside the training information changed (the holdout's labels and inputs, the
calibration slice's inputs). A rung whose record changes read something it must not have.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline.cases.c01_ladder import fit_ladder
from pipeline.stages import split

FEATURES = ("risk_up", "risk_down", "segment_code", "noise")
CATEGORICAL = ("segment_code",)
MONOTONE = {"risk_up": +1, "risk_down": -1, "segment_code": 0, "noise": 0}


def planted(n: int = 2400, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    seg = rng.integers(0, 4, size=n)
    eta = -1.2 + 0.9 * x1 - 0.6 * x2 + np.array([0.0, 0.3, -0.2, 0.5])[seg]
    y = (rng.random(n) < 1.0 / (1.0 + np.exp(-eta))).astype(int)
    return pd.DataFrame({"risk_up": x1, "risk_down": x2, "segment_code": seg, "noise": rng.normal(size=n),
                         "target": y})


def ladder(X: pd.DataFrame, sp: split.Split) -> dict:
    y = X["target"].to_numpy()
    return fit_ladder(X.iloc[sp.train], y[sp.train], X.iloc[sp.calibration], y[sp.calibration], sp.folds,
                      features=FEATURES, categorical=CATEGORICAL, monotone=MONOTONE, seed=11, with_xgboost=False)


@pytest.fixture(scope="module")
def base():
    X = planted()
    sp = split.stratified_split(X["target"].to_numpy(), seed=7)
    return X, sp, ladder(X, sp)


def _records(rungs: dict) -> dict[str, str]:
    return {rid: r.record()["checkpoint_sha256"] for rid, r in rungs.items()}


def test_fitted_transforms_train_only(base):
    X, sp, rungs = base
    assert sp.disjoint()
    moved = X.copy()
    rng = np.random.default_rng(99)
    outside = np.concatenate([sp.holdout, sp.calibration])
    # inputs outside the training slice changed beyond recognition: binning, WoE, rules, scaling must not see them
    for f in ("risk_up", "risk_down", "noise"):
        moved.loc[moved.index[outside], f] = rng.normal(loc=5.0, scale=4.0, size=len(outside))
    # the calibration slice goes in with its inputs moved: it may change the calibration maps, never a transform
    again = fit_ladder(moved.iloc[sp.train], moved["target"].to_numpy()[sp.train], moved.iloc[sp.calibration],
                       moved["target"].to_numpy()[sp.calibration], sp.folds, features=FEATURES,
                       categorical=CATEGORICAL, monotone=MONOTONE, seed=11, with_xgboost=False)
    for rid in rungs:  # every rung's fitted internals; only its calibration map may follow the calibration slice
        a, b = rungs[rid].record(), again[rid].record()
        assert a["details"] == b["details"], rid
    sc = rungs["P1-scorecard"].model
    assert sc.binnings["risk_up"].splits.max() < 4.0  # the bins come from the training slice's range


def test_calibration_slice_disjoint(base):
    X, sp, rungs = base
    assert not set(sp.calibration) & set(sp.holdout)
    assert not set(sp.calibration) & set(sp.train)
    # the calibration maps are a function of the calibration slice: changing the holdout's labels leaves them as they are
    flipped = X.copy()
    flipped.loc[flipped.index[sp.holdout], "target"] = 1 - flipped.loc[flipped.index[sp.holdout], "target"]
    again = ladder(flipped, sp)
    for rid, r in rungs.items():
        if r.calibration is not None:
            assert np.array_equal(r.calibration.x, again[rid].calibration.x), rid
            assert np.array_equal(r.calibration.y, again[rid].calibration.y), rid


def test_outside_information_perturbation_invariance(base):
    X, sp, rungs = base
    moved = X.copy()
    rng = np.random.default_rng(5)
    hold = moved.index[sp.holdout]
    moved.loc[hold, "target"] = rng.integers(0, 2, size=len(hold))
    moved.loc[hold, "risk_up"] = rng.normal(size=len(hold)) * 10
    again = ladder(moved, sp)
    assert _records(rungs) == _records(again)
    # and the check is not vacuous: changing a training label does change the fit
    trained = X.copy()
    k = trained.index[sp.train[:200]]
    trained.loc[k, "target"] = 1 - trained.loc[k, "target"]
    assert _records(ladder(trained, sp))["P1-scorecard"] != _records(rungs)["P1-scorecard"]
