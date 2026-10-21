"""The c20-models document: the ladder rungs fitted on each dataset of the case and how they were fitted.

The records are the C01 ladder's (``cases/c01_ladder.py``) with their ids made unique by the dataset (``P4-lightgbm-taiwan``); the heavy
internals (scorecard tables, shape functions) belong to C01's models document and are not repeated: ``details`` keeps the fit sizes,
the holdout AUC and, for the boosted rungs, the rounds and the constraints.
"""
from __future__ import annotations

from typing import Any

from ..c01_ladder import Rung
from . import fits, ops
from .conv import SGCD_COMMIT, parameters_block, sgcd_notice
from .data import Frame

DATASET_OF = {"german-sgcd": "uci-german", "taiwan": "uci-taiwan", "polish": "uci-polish"}


def records(frame: Frame, rungs: dict[str, Rung]) -> list[dict[str, Any]]:
    Xh, yh = frame.part("hold")
    out = []
    for rid, rung in rungs.items():
        rec = rung.record()
        auc = ops.auc_brier(rung.pd(Xh), yh)[0]
        det: dict[str, Any] = {"dataset": DATASET_OF[frame.name], "train_rows": int(len(frame.train)), "calibration_rows": int(len(frame.cal)),
                               "holdout_rows": int(len(frame.hold)), "holdout_auc": auc}
        inner = rec.get("details") or {}
        for k in ("engine", "rounds", "constraints"):
            if isinstance(inner, dict) and k in inner:
                det[k] = inner[k]
        out.append({**rec, "id": fits.rung_id(rid, frame), "family": "ml", "details": det})
    return out


def fit_block(frames: dict[str, Frame], rungs: dict[str, dict[str, Rung]], fed_rows: int | None) -> dict[str, Any]:
    ds = []
    if "german-sgcd" in frames:
        ds.append({"id": "sgcd", "rows": int(len(frames["german-sgcd"].X)), "role": "German model fit (setup and adaptation batches) and shock evaluation (test batches)"})
    if "taiwan" in frames:
        ds.append({"id": "uci-taiwan", "rows": int(len(frames["taiwan"].X)), "role": "model fit and locked holdout of the seed, perturbation and leakage variants"})
    if "polish" in frames:
        ds.append({"id": "uci-polish", "rows": int(len(frames["polish"].X)), "role": "model fit and locked holdout of the Fed shift probes (3-year file)"})
    if fed_rows is not None:
        ds.append({"id": "fed-2025-corporate", "rows": int(fed_rows), "role": "real drift between the portfolios and the size of the synthetic shift"})
    ladder = [{"rung": rid, "engine": r.engine, "dataset": DATASET_OF[name]} for name, rs in rungs.items() for rid, r in rs.items()]
    return {"datasets": ds, "ladder": ladder, "sgcd": {"commit": SGCD_COMMIT, "seed": 42, "notice": sgcd_notice()}, "parameters": parameters_block()}
