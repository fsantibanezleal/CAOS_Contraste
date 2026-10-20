"""CT-0204, CT-0205, CT-0217: the leakage-safe preprocessing, the splits and the ladder."""
from __future__ import annotations

import numpy as np
import pandas as pd
from c02_support import PLANTED_ROWS, SEED, ZIP_NAME

from pipeline.cases.c02 import conventions as cv
from pipeline.cases.c02 import fits, prep, reader


def _horizons(planted):
    root, _ = planted
    return reader.read_horizons(root / "raw" / "uci-polish" / ZIP_NAME, check_counts=False)


def test_the_preprocessor_is_fitted_on_the_training_slice_only(planted) -> None:
    h = _horizons(planted)[1]
    sp = fits.split_file(h.y, SEED)
    pp = prep.fit_preprocessor(h.X.iloc[sp.train])
    train = h.X.iloc[sp.train]
    # the medians are the training slice's, the indicators are the ratios missing in at least 5 percent of the training slice
    assert pp.medians["Attr1"] == float(np.nanmedian(train["Attr1"]))
    assert set(pp.indicators) == {a for a in cv.ATTRIBUTES if train[a].isna().mean() >= cv.MISSING_INDICATOR_SHARE} >= {"Attr5", "Attr37"}
    # refutation: a different holdout or calibration slice changes no fitted value
    other = h.X.copy()
    other.iloc[np.r_[sp.calibration, sp.holdout]] = np.where(np.arange(64) % 2 == 0, 1e6, np.nan)
    pp2 = prep.fit_preprocessor(other.iloc[sp.train])
    assert pp2 == pp and pp2.record() == pp.record()
    # transforming applies the training medians to a slice, fills every cell and adds the indicator columns
    out = pp.transform(h.X.iloc[sp.holdout])
    assert not out.isna().any().any() and list(out.columns) == list(pp.columns) and len(pp.columns) == 64 + len(pp.indicators)
    miss = h.X.iloc[sp.holdout]["Attr37"].isna().to_numpy()
    assert (out["Attr37"].to_numpy()[miss] == pp.medians["Attr37"]).all()
    assert (out["Attr37_missing"].to_numpy() == miss.astype(float)).all()
    # the pooled variant passes the horizon indicator through
    assert prep.fit_preprocessor(train.assign(horizon_years=1.0), extra=(cv.HORIZON_FEATURE,)).columns[-1] == cv.HORIZON_FEATURE


def test_the_splits_are_disjoint_stratified_deterministic_and_the_pooled_one_is_their_union(planted) -> None:
    hz = _horizons(planted)
    built = fits.build_fits(hz, SEED, with_ladder=False)
    assert list(built) == ["h1", "h2", "h3", "h4", "h5", "pooled"]
    for hid in ("h1", "h2", "h3", "h4", "h5"):
        f = built[hid]
        sp = f.sp
        assert sp.disjoint() and len(sp.train) + len(sp.calibration) + len(sp.holdout) == len(f.y)
        assert len(sp.holdout) == int(np.ceil(0.30 * len(f.y)))                                    # 30 percent, locked
        for part in (sp.train, sp.calibration, sp.holdout):                                        # stratified: the rate is the file's
            assert abs(f.y[part].mean() - f.y.mean()) < 0.03
        again = fits.split_file(f.y, SEED)
        assert all(np.array_equal(a, b) for a, b in zip((sp.train, sp.calibration, sp.holdout), (again.train, again.calibration, again.holdout)))
        other = fits.split_file(f.y, SEED + 1)
        assert not np.array_equal(sp.holdout, other.holdout)
    p = built["pooled"]
    assert p.years is None and cv.HORIZON_FEATURE in p.X.columns and len(p.y) == sum(len(built[f"h{k}"].y) for k in range(1, 6))
    assert p.sp.disjoint()
    # the pooled slices are the union of the files' slices: its holdout is the union of the five locked holdouts
    offset = 0
    for k in range(1, 6):
        f = built[f"h{k}"]
        for name in ("train", "calibration", "holdout"):
            assert set((getattr(f.sp, name) + offset).tolist()) <= set(getattr(p.sp, name).tolist())
        assert (p.X[cv.HORIZON_FEATURE].to_numpy()[offset:offset + len(f.y)] == k).all()
        offset += len(f.y)
    assert len(p.sp.holdout) == sum(len(built[f"h{k}"].sp.holdout) for k in range(1, 6))
    assert not set(p.sp.holdout.tolist()) & set(p.sp.train.tolist())
    # the transformed slices are fitted on the training slice only, in the pooled variant too
    assert p.pp.medians["Attr1"] == float(np.nanmedian(p.X.iloc[p.sp.train]["Attr1"]))
    assert PLANTED_ROWS and [len(built[f"h{k}"].y) for k in range(1, 6)] == [n + 1 for n in PLANTED_ROWS]


def test_the_ladder_is_the_c01_ladder_and_the_constant_has_no_battery(planted) -> None:
    hz = _horizons(planted)
    f = fits.build_fits({1: hz[1]}, SEED, with_pooled=False)["h1"]
    assert list(f.rungs) == ["P0-constant", "P0-single", "P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm", "P4-xgboost"]
    assert "P5-tabpfn" not in f.rungs
    assert set(cv.RUNG_CODE) == set(f.rungs) and cv.BATTERY_RUNGS == tuple(r for r in f.rungs if r != "P0-constant")
    assert np.ptp(f.rungs["P0-constant"].pd(f.Xhold)) == 0.0                                          # a constant has no risk groups
    for rid in cv.BATTERY_RUNGS:
        p = f.rungs[rid].pd(f.Xhold)
        assert isinstance(p, np.ndarray) and len(p) == len(f.yhold) and ((p > 0) & (p < 1)).all()
    assert isinstance(f.Xhold, pd.DataFrame) and tuple(f.Xhold.columns) == f.pp.columns
    # the learned rungs that need a calibration map have it fitted on the calibration slice (a separate slice)
    assert f.rungs["P3-ebm"].calibration is not None and f.rungs["P1-scorecard"].calibration is None
