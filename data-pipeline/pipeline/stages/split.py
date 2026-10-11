"""Stage split: the leakage-safe partition of a case's data (dossier 04, "Universal leakage rules").

A locked stratified holdout, a calibration slice disjoint from it, and the training slice; repeated stratified
folds inside the training slice for every choice a rung makes (hyperparameters, penalty strength, number of
rounds). Everything is a pure function of the labels and the seed.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Split:
    """Positions into the case's records. ``folds`` are positions into ``train``."""

    train: np.ndarray
    calibration: np.ndarray
    holdout: np.ndarray
    folds: tuple[tuple[np.ndarray, np.ndarray], ...]

    def disjoint(self) -> bool:
        a, b, c = (set(map(int, s)) for s in (self.train, self.calibration, self.holdout))
        return not (a & b or a & c or b & c)

    def summary(self, y: np.ndarray) -> dict:
        def part(ix: np.ndarray) -> dict:
            return {"n": int(len(ix)), "defaults": int(np.sum(y[ix])), "default_rate": float(np.mean(y[ix]))}
        return {"train": part(self.train), "calibration": part(self.calibration), "holdout": part(self.holdout),
                "folds": {"k": 5, "repeats": len(self.folds) // 5}}


def stratified_split(y: np.ndarray, *, seed: int, holdout: float = 0.30, calibration: float = 0.20,
                     repeats: int = 2) -> Split:
    """Holdout fraction of all records; calibration fraction of the remaining development records."""
    from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split

    y = np.asarray(y, dtype=int)
    idx = np.arange(len(y))
    dev, hold = train_test_split(idx, test_size=holdout, stratify=y, random_state=seed)
    train, cal = train_test_split(dev, test_size=calibration, stratify=y[dev], random_state=seed + 1)
    train, cal, hold = np.sort(train), np.sort(cal), np.sort(hold)
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=seed + 2)
    folds = tuple((tr, va) for tr, va in rskf.split(train, y[train]))
    return Split(train=train, calibration=cal, holdout=hold, folds=folds)


def subsample(train: np.ndarray, y: np.ndarray, n: int, *, seed: int) -> np.ndarray:
    """A stratified subsample of n training positions (the small-sample variant)."""
    from sklearn.model_selection import train_test_split

    keep, _ = train_test_split(train, train_size=n, stratify=y[train], random_state=seed)
    return np.sort(keep)
