"""The C08 models document (``c08-models``): what was fitted for one cutoff (CT-907, CT-912).

Coefficients are on the link scale of the engine's fit, over the standardised continuous covariates (the moments of the
training set are in ``details``); the engine's fits carry no standard error, so ``std_error`` is null with that reason in the
rung's details. The gradient-boosted rung has no coefficient.
"""
from __future__ import annotations

import importlib.metadata as md
from typing import Any

from . import build as bd
from .ladder import EPSILONS, LADDER_EPSILON, LICENCES, RUNG_KIND, RUNGS, Ladder, RungFit
from .panel import CONTINUOUS, FEATURE_NAMES
from .variant import VariantResult


def _coefs(fit) -> list[dict[str, Any]]:
    return [{"name": n, "estimate": float(c), "std_error": None} for n, c in zip(fit.names, fit.coefficients, strict=True)]


def _engine_version() -> str:
    return md.version("riskvalidation")


def _licence(rung: RungFit) -> str:
    return LICENCES["catboost"] if rung.kind == "gradient-boosted" else LICENCES["engine"]


def ladder_block(res: VariantResult) -> list[dict[str, Any]]:
    lad: Ladder = res.ladder
    out = []
    for rid, kind in RUNGS:
        r = lad.rungs[rid]
        coefs = _coefs(r.fit) if r.evaluated and r.fit is not None else []
        out.append({"rung_id": rid, "kind": kind, "covariates": list(FEATURE_NAMES) if r.evaluated else [], "coefficients": coefs,
                    "epsilon": LADDER_EPSILON if kind == "beta" else None, "training_cutoff": res.cutoff,
                    "library": r.library, "library_version": r.library_version})
    return out


def model_records(res: VariantResult) -> list[dict[str, Any]]:
    lad = res.ladder
    recs = []
    scale = {n: {"mean": float(m), "std": float(s)} for n, m, s in zip(CONTINUOUS, lad.scaler.mean, lad.scaler.std, strict=True)}
    for rid, kind in RUNGS:
        r = lad.rungs[rid]
        title, short = bd.RUNG_TEXT[rid]
        details: dict[str, Any] = {"evaluated": r.evaluated, "reason": r.reason, "standardisation": scale,
                                   "n_fitted": lad.n_fitted, "n_out_of_range_left_out": lad.n_out_of_range,
                                   "std_error": "null: the engine's fits carry no standard error"}
        if r.evaluated and r.fit is not None:
            ex = r.fit.extras
            if kind == "hurdle":
                details["stage1_coefficients"] = [float(c) for c in ex["stage1_coefficients"]]
                details["severity_columns"] = [int(c) for c in ex["severity_columns"]]
            if kind == "beta":
                details["phi"] = float(ex["phi"])
                details["epsilons_reported"] = {str(e): (None if not lad.beta_by_epsilon[e].evaluated else
                                                         [float(c) for c in lad.beta_by_epsilon[e].fit.coefficients])
                                                for e in EPSILONS if e in lad.beta_by_epsilon}
            if kind == "tobit":
                details["sigma"] = float(ex["sigma"])
        if r.evaluated and kind == "gradient-boosted":
            from .ladder import BOOST
            details["settings"] = {k: v for k, v in BOOST.items() if k not in ("verbose", "allow_writing_files")}
            details["feature_importance"] = {n: float(v) for n, v in zip(FEATURE_NAMES, r.booster.get_feature_importance(), strict=True)}
        recs.append({
            "id": rid, "family": "lgd-ead", "rung": kind, "title": bd.t(*title), "short_title": bd.t(*short),
            "engine": r.library, "engine_version": r.library_version, "licence": _licence(r), "calibration": None,
            "parameters": {"n_defaults_fitted": {"value": float(lad.n_fitted), "unit": "defaults"},
                           "n_out_of_range_left_out": {"value": float(lad.n_out_of_range), "unit": "defaults"}},
            "checkpoint_sha256": None, "details": details})
    return recs


def model_summaries(res: VariantResult) -> list[dict[str, Any]]:
    return [{k: v for k, v in r.items() if k != "details"} for r in model_records(res)]


def fit_block(res: VariantResult, freddie_reason: str, down) -> dict[str, Any]:
    return {
        "currency": bd.CURRENCY, "lgd_proxy": bd.lgd_proxy_block(), "data_status": bd.data_status_block(freddie_reason),
        "cohorts": bd.cohort_blocks(),
        "training": {"cutoff_date": res.cutoff, "n_defaults": res.n_train, "n_open_workouts_excluded": res.n_open,
                     "closure_rule": bd.closure_rule()},
        "workout": bd.workout_block(), "ladder": ladder_block(res),
        "downturn": {"approach": dict(down.approach), "period": dict(down.period)},
        "floors": {"regime": bd.REGIME, "cells": bd.floor_cells_block(), "source": dict(bd.FLOOR_SOURCE)},
    }


__all__ = ["fit_block", "model_records", "model_summaries", "ladder_block", "RUNG_KIND"]
