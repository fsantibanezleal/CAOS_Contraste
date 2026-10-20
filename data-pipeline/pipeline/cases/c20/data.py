"""The model frames of C20: Taiwan, German as carried by SGCD, and Polish (3-year), each through contract 1 and split without leakage.

- Taiwan (``uci-taiwan``, 30,000 accounts): the C01 reader and fields, the stratified 70 / 30 split with the calibration slice taken from the
  development part, exactly as C01 does; ``SEX``, ``AGE`` and ``MARRIAGE`` ride along for the fairness battery and are never inputs.
- German as carried by SGCD (1,000 applicants in 20 batches): the model is fitted on the setup and adaptation batches (S1 to S4, A1 to A10,
  700 records, the protocol's "adapt" phase, F1 nulls included) with a calibration slice taken from them, and the six test batches T1 to T6
  (300 records) are the locked holdout. Every SGCD record is a UCI German applicant (930 of 930 complete records match a UCI row), so the
  model is never fitted on the UCI file as a whole: it would have seen the holdout.
- Polish, the 3-year file (10,503 firm-years): the stratified split of C01; the ratios have missing values (45 percent in ``Attr37``) and
  the median of the training slice fills them in every slice (imputation fitted on the training slice only, the contract's rule).

``max_rows`` keeps a stratified, deterministic subsample of Taiwan (or of Polish, where a caller asks) for the tests; the bake passes none, and
the case bake reads the Polish file whole (a 1,500-row subsample has too few events for the scorecard to be fitted).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ...io import polish, readers
from ...io.contract import Field
from ...stages import split
from ...stages.ingest import ingest
from .. import c01_features as feat
from . import sgcd
from .conv import CASE_ID

TAIWAN_ZIP = "default+of+credit+card+clients.zip"
GERMAN_ZIP = "statlog+german+credit+data.zip"
EXTRA_TAIWAN = (
    Field("AGE", "int", {"en": "Age in years (a protected attribute: the fairness battery only, never an input)",
                         "es": "Edad en años (atributo protegido: solo la batería de equidad, nunca una entrada)"}, unit="years", lo=0, on_missing="flag"),
    Field("MARRIAGE", "int", {"en": "Marital status (1 married, 2 single, 3 others; a protected attribute, never an input)",
                              "es": "Estado civil (1 casado, 2 soltero, 3 otros; atributo protegido, nunca una entrada)"}, on_missing="flag"),
)


# --- Polish, the 3-year file: C20's contract-1 convention over the shared reader (decision G19) --------------------------------------
#: the base model of the Fed shift probes reads the 3-year file only (decision Q6 (a)); the files carry no firm identifier and no date, so
#: ``id`` is the row position in the file (``PL3-<row>``) and ``observation_date`` is the last day of the dataset's span, 2013-12-31 (both
#: named conventions, as the HMDA and German readers write theirs). The 64 ratios keep their names ``Attr1`` to ``Attr64``.
POLISH_FILE = 3
POLISH_MEMBER = polish.member(POLISH_FILE)
POLISH_ATTRS = polish.ATTRIBUTES
OBSERVATION_DATE = "2013-12-31"
POLISH_FIELDS: tuple[Field, ...] = tuple(
    Field(a, "float", {"en": f"Financial ratio {a} of the Polish Companies Bankruptcy data",
                       "es": f"Razón financiera {a} de los datos de quiebra de empresas polacas"}, unit="ratio", on_missing="flag")
    for a in POLISH_ATTRS)
POLISH_MONOTONE: dict[str, int] = {a: 0 for a in POLISH_ATTRS}


def read_polish(zip_path: str | Path) -> list[dict[str, Any]]:
    """One record per firm-year row of the 3-year file: ``Attr1`` to ``Attr64`` (None for ``?``) and the bankruptcy flag as the target."""
    X, y = polish.read_member(zip_path, POLISH_MEMBER)
    vals = X.to_numpy(dtype=float)
    records = []
    for k in range(len(y)):
        rec: dict[str, Any] = {"id": f"PL{POLISH_FILE}-{k + 1:05d}", "observation_date": OBSERVATION_DATE, "target": int(y[k])}
        for j, a in enumerate(POLISH_ATTRS):
            v = float(vals[k, j])
            rec[a] = None if not np.isfinite(v) else v
        records.append(rec)
    return records


@dataclass
class Frame:
    name: str
    source: str
    X: pd.DataFrame
    y: np.ndarray
    features: tuple[str, ...]
    categorical: tuple[str, ...]
    monotone: dict[str, int]
    train: np.ndarray
    cal: np.ndarray
    hold: np.ndarray
    folds: tuple[tuple[np.ndarray, np.ndarray], ...]
    contract: dict[str, Any]
    extras: dict[str, Any] = field(default_factory=dict)

    def part(self, which: str) -> tuple[pd.DataFrame, np.ndarray]:
        ix = {"train": self.train, "cal": self.cal, "hold": self.hold}[which]
        return self.X.iloc[ix], self.y[ix]

    def dev_index(self) -> np.ndarray:
        return np.sort(np.concatenate([self.train, self.cal]))

    def summary(self) -> dict[str, Any]:
        def part(ix: np.ndarray) -> dict[str, Any]:
            return {"n": int(len(ix)), "defaults": int(self.y[ix].sum()), "default_rate": float(self.y[ix].mean())}

        return {"train": part(self.train), "calibration": part(self.cal), "holdout": part(self.hold)}


def _subsample(X: pd.DataFrame, y: np.ndarray, max_rows: int | None, seed: int) -> tuple[pd.DataFrame, np.ndarray]:
    """A stratified, deterministic subsample in input order (for the tests); None keeps every row."""
    if max_rows is None or len(y) <= max_rows:
        return X, y
    from sklearn.model_selection import train_test_split

    keep, _ = train_test_split(np.arange(len(y)), train_size=max_rows, stratify=y, random_state=seed)
    keep = np.sort(keep)
    return X.iloc[keep].reset_index(drop=True), y[keep]


def load_taiwan(data_root: Path, seed: int, max_rows: int | None = None) -> Frame:
    X, rep = ingest(CASE_ID, "uci-taiwan", TAIWAN_ZIP, readers.read_taiwan, data_root=data_root, family="scored_sample",
                    extra_fields=(*feat.TAIWAN_FIELDS, *EXTRA_TAIWAN), extra_rules=feat.TAIWAN_RULES)
    y = X["target"].to_numpy(dtype=int)
    X, y = _subsample(X, y, max_rows, seed)
    sp = split.stratified_split(y, seed=seed)
    return Frame("taiwan", "uci-taiwan", X, y, feat.TAIWAN_FEATURES, feat.TAIWAN_CATEGORICAL, feat.TAIWAN_MONOTONE, sp.train, sp.calibration,
                 sp.holdout, sp.folds, rep.summary())


def load_polish(data_root: Path, seed: int, max_rows: int | None = None) -> Frame:
    X, rep = ingest(CASE_ID, polish.SOURCE_ID, polish.ZIP_NAME, read_polish, data_root=data_root, family="scored_sample",
                    extra_fields=POLISH_FIELDS)
    y = X["target"].to_numpy(dtype=int)
    X, y = _subsample(X, y, max_rows, seed)
    sp = split.stratified_split(y, seed=seed)
    feats = list(POLISH_ATTRS)
    med = X.iloc[sp.train][feats].astype(float).median()
    X = X.copy()
    X[feats] = X[feats].astype(float).fillna(med)      # the training-slice median in every slice
    return Frame("polish", polish.SOURCE_ID, X, y, POLISH_ATTRS, (), POLISH_MONOTONE, sp.train, sp.calibration, sp.holdout, sp.folds,
                 rep.summary(), extras={"imputed_with": "training-slice median", "median": {k: float(v) for k, v in med.items()}})


def load_sgcd(data_root: Path, seed: int, ds: sgcd.Dataset) -> Frame:
    from ...io.contract import validate

    recs = ds.records
    rep = validate("scored_sample", sgcd.contract_records(recs), extra_fields=feat.GERMAN_FIELDS)
    if rep.rejected or len(rep.accepted) != len(recs):
        raise ValueError(f"C20: contract 1 rejects SGCD records: {rep.counts()}; {rep.rejected[:3]}")
    X = pd.DataFrame(rep.accepted)
    if list(X["id"]) != [r.id for r in recs]:
        raise ValueError("C20: contract 1 changed the order of the SGCD records")
    meta = pd.DataFrame([{"batch": r.batch, "stage": r.stage, "shock": r.shock, "cosmetic": r.cosmetic} for r in recs])
    X = pd.concat([X.reset_index(drop=True), meta], axis=1)
    y = X["target"].to_numpy(dtype=int)
    dev = np.flatnonzero(X["stage"].isin(["setup", "adaptation"]).to_numpy())
    hold = np.flatnonzero((X["stage"] == "test").to_numpy())
    from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split

    train, cal = train_test_split(dev, test_size=0.20, stratify=y[dev], random_state=seed + 1)
    train, cal = np.sort(train), np.sort(cal)
    folds = tuple((a, b) for a, b in RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=seed + 2).split(train, y[train]))
    return Frame("german-sgcd", "santanderai-sgcd", X, y, feat.GERMAN_FEATURES, feat.GERMAN_CATEGORICAL, feat.GERMAN_MONOTONE, train, cal,
                 hold, folds, rep.summary(), extras={"batches": sgcd.BATCHES})


class LockedHoldoutError(ValueError):
    """A shift or a fit that would touch the locked holdout, or a shift that would touch a training row."""


def assert_locked(frame: Frame) -> None:
    """The three slices are disjoint; for SGCD the fit rows are the setup and adaptation batches and the holdout the test batches."""
    a, b, c = (set(map(int, s)) for s in (frame.train, frame.cal, frame.hold))
    if a & b or a & c or b & c:
        raise LockedHoldoutError(f"{frame.name}: the training, calibration and holdout slices overlap")
    if frame.name == "german-sgcd":
        stage = frame.X["stage"].to_numpy()
        if set(stage[frame.hold]) != {"test"} or {"test"} & (set(stage[frame.train]) | set(stage[frame.cal])):
            raise LockedHoldoutError("german-sgcd: the holdout is not exactly the test batches, or a test batch is in the fit rows")


def assert_evaluation_only(frame: Frame, ix: np.ndarray) -> None:
    """Synthetic shifts touch the evaluation set only (SDD l.392): a row of the training or the calibration slice is refused."""
    bad = set(map(int, np.asarray(ix))) & (set(map(int, frame.train)) | set(map(int, frame.cal)))
    if bad:
        raise LockedHoldoutError(f"{frame.name}: {len(bad)} rows of the training or calibration slice would be shifted; only the evaluation set is")
