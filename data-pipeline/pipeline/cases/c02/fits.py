"""The splits and the ladder fits of C02: one locked split per file, the pooled variant as their union, the C01 ladder on each.

The split is C01's stage (``pipeline.stages.split``, a function of the labels and the seed): a locked stratified holdout of 30 percent,
a calibration slice of 20 percent of the rest and the training slice, with repeated stratified folds inside the training slice. The
pooled variant is the union of the five slices, so its holdout is the union of the five locked holdouts and a pooled model can be read
on the holdout of any file. Imputation and the missing indicators are fitted on the training slice only (``prep``). The ladder is
``cases/c01_ladder.fit_ladder`` unchanged (sizing R3).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ...stages import split
from ..c01_ladder import Rung, fit_ladder
from . import conventions as cv
from . import prep
from .reader import Horizon


@dataclass
class Fit:
    horizon_id: str
    years: int | None
    file: str
    X: pd.DataFrame
    y: np.ndarray
    sp: split.Split
    pp: prep.Preprocessor
    Xtr: pd.DataFrame
    Xcal: pd.DataFrame
    Xhold: pd.DataFrame
    rungs: dict[str, Rung] = field(default_factory=dict)

    @property
    def ytr(self) -> np.ndarray:
        return self.y[self.sp.train]

    @property
    def ycal(self) -> np.ndarray:
        return self.y[self.sp.calibration]

    @property
    def yhold(self) -> np.ndarray:
        return self.y[self.sp.holdout]


def split_file(y: np.ndarray, seed: int) -> split.Split:
    """The locked split of one file (C01's stage, stratified on the class)."""
    return split.stratified_split(np.asarray(y, dtype=int), seed=seed)


def _fit_ladder(f: Fit, seed: int, log: Callable[[str], None] | None) -> None:
    cols = f.pp.columns
    f.rungs = fit_ladder(f.Xtr, f.ytr, f.Xcal, f.ycal, f.sp.folds, features=cols, categorical=(), monotone={c: 0 for c in cols},
                         seed=seed, with_xgboost=True, with_tabpfn=False, log=log)


def _make(hid: str, years: int | None, file: str, X: pd.DataFrame, y: np.ndarray, sp: split.Split, extra: tuple[str, ...]) -> Fit:
    pp = prep.fit_preprocessor(X.iloc[sp.train], extra=extra)
    return Fit(hid, years, file, X, y, sp, pp, pp.transform(X.iloc[sp.train]), pp.transform(X.iloc[sp.calibration]),
               pp.transform(X.iloc[sp.holdout]))


def pooled_split(parts: list[tuple[int, split.Split, np.ndarray]], seed: int, strata: np.ndarray) -> split.Split:
    """The union of the files' slices, positions into the stacked rows; the folds are stratified on the class and the file."""
    from sklearn.model_selection import RepeatedStratifiedKFold

    def union(name: str) -> np.ndarray:
        return np.sort(np.concatenate([getattr(sp, name) + off for off, sp, _ in parts]))

    train = union("train")
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=seed + 2)
    folds = tuple((a, b) for a, b in rskf.split(train, strata[train]))
    return split.Split(train=train, calibration=union("calibration"), holdout=union("holdout"), folds=folds)


def build_fits(horizons: dict[int, Horizon], seed: int, *, with_ladder: bool = True, with_pooled: bool = True,
               log: Callable[[str], None] | None = None) -> dict[str, Fit]:
    """Every horizon file and, last, the pooled variant (when all five files are given)."""
    out: dict[str, Fit] = {}
    for k in sorted(horizons):
        h = horizons[k]
        out[h.horizon_id] = _make(h.horizon_id, k, h.file, h.X, h.y, split_file(h.y, seed), ())
    if with_pooled:
        if sorted(horizons) != [1, 2, 3, 4, 5]:
            raise ValueError("the pooled variant stacks the five files, once each")
        offsets, parts, frames, labels, strata = 0, [], [], [], []
        for k in range(1, 6):
            f = out[horizons[k].horizon_id]
            parts.append((offsets, f.sp, f.y))
            frames.append(f.X.assign(**{cv.HORIZON_FEATURE: float(k)}))
            labels.append(f.y)
            strata.append(f.y + 2 * (k - 1))
            offsets += len(f.y)
        X, y = pd.concat(frames, ignore_index=True), np.concatenate(labels)
        sp = pooled_split(parts, seed, np.concatenate(strata))
        out[cv.POOLED] = _make(cv.POOLED, None, "pooled: " + ", ".join(horizons[k].file for k in range(1, 6)), X, y, sp, (cv.HORIZON_FEATURE,))
    if with_ladder:
        for name, f in out.items():
            if log is not None:
                log(f"fit {name}: {len(f.sp.train):,} training rows, {len(f.sp.calibration):,} calibration, {len(f.sp.holdout):,} holdout")
            _fit_ladder(f, seed, log)
    return out
