"""Loan-level bootstrap intervals on the S-5 benchmark of C08 (the better of the random forest and the neural network against each of the
six rungs before them, per test cohort), beside its verdict.

The S-5 hypothesis (``ml_benchmark.HYPOTHESIS``) is judged by a count of test cohorts where the better of the two new rungs has a lower
RMSE than every one of the six earlier rungs. A reader cannot tell whether the RMSE difference in one cohort is larger than the sampling
noise of its defaults. This module resamples the defaults of the test cohort with replacement (``cases.bootstrap``), holds the
predictions of every rung fixed (nothing is refitted: the interval is the uncertainty of the comparison on this cohort, not of the fits)
and recomputes the RMSE differences on every resample. The verdict is untouched.

A replicate is the weighted sample of the defaults that draws default ``i`` ``c[i]`` times, so the RMSE of a rung on it is
``sqrt(sum(c * (y - p)^2) / n)``: the formula of ``variant.bake_variant`` on the resample, never a resample of an aggregate (a bucket or a
cohort). The better of the two machine-learning rungs is chosen again inside each replicate, as the hypothesis words it. The RMSE
difference is positive where the machine-learning rung is lower. No statistic the engine provides is computed here: the engine has no
RMSE of an LGD model.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .. import bootstrap as bs
from . import ml_benchmark as ml


def _unfitted(rung_id: str, why: str) -> dict[str, str]:
    return bs.text(f"rung {rung_id} was not fitted: {why}", f"la etapa {rung_id} no se ajustó: {why}")


def _squares(y: np.ndarray, preds: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {rid: (np.asarray(y, dtype=float) - np.asarray(p, dtype=float)) ** 2 for rid, p in preds.items()}


def _rungs(preds: dict[str, np.ndarray]) -> tuple[list[str], list[str]]:
    classical = [r for r in ml.CLASSICAL_RUNGS if r in preds]
    new = [r for r in ml.ML_RUNGS if r in preds]
    if len(new) != len(ml.ML_RUNGS) or not classical:
        raise ValueError("the comparison needs both machine-learning rungs and at least one of the six rungs before them")
    return classical, new


def _from_mse(mse: dict[str, float], classical: list[str], new: list[str]) -> tuple[dict[str, float], float, float]:
    """``(difference of each of the six against the better new rung, gain of the better new rung against the best of the six, the better's RMSE)``."""
    rmse = {r: float(np.sqrt(mse[r])) for r in (*classical, *new)}
    best_new = min(rmse[r] for r in new)
    return {r: rmse[r] - best_new for r in classical}, min(rmse[r] for r in classical) - best_new, best_new


def point_differences(y: np.ndarray, preds: dict[str, np.ndarray]) -> dict[str, Any]:
    """The replicate that draws every default once: the differences ``ml_benchmark.cohort_result`` reports."""
    classical, new = _rungs(preds)
    sq = _squares(y, preds)
    against, gain, _ = _from_mse({r: float(sq[r].mean()) for r in (*classical, *new)}, classical, new)
    return {"against": against, "against_best": gain}


def replicate_differences(y: np.ndarray, preds: dict[str, np.ndarray], seed: int, replicates: int | None = None) -> dict[str, Any]:
    """The differences on every replicate: ``{"against": {rung: (replicates,)}, "against_best": (replicates,)}``."""
    classical, new = _rungs(preds)
    b = bs.REPLICATES if replicates is None else int(replicates)
    sq = _squares(y, preds)
    names = [*classical, *new]
    sq_matrix = np.vstack([sq[r] for r in names])
    n = sq_matrix.shape[1]
    against = {r: np.empty(b) for r in classical}
    best = np.empty(b)
    for i, c in enumerate(bs.draws(n, b, seed)):
        mse = dict(zip(names, (sq_matrix @ c) / n, strict=True))
        diffs, gain, _ = _from_mse(mse, classical, new)
        for r in classical:
            against[r][i] = diffs[r]
        best[i] = gain
    return {"against": against, "against_best": best}


def compare(y: np.ndarray, preds: dict[str, np.ndarray], *, seed: int, replicates: int | None = None) -> dict[str, Any]:
    """The better of the two machine-learning rungs against each of the rungs of ``preds`` among the six, and against the best of them,
    with their percentile intervals. ``preds`` holds the fixed predictions on the test cohort of every fitted rung."""
    reps = bs.REPLICATES if replicates is None else int(replicates)
    classical, new = _rungs(preds)
    sq = _squares(y, preds)
    rmse = {r: float(np.sqrt(sq[r].mean())) for r in (*classical, *new)}
    point = point_differences(y, preds)
    draws = replicate_differences(y, preds, seed, reps)
    best_classical = min(classical, key=lambda r: rmse[r])
    return {
        "better_rung": min(new, key=lambda r: rmse[r]),
        "against_best": {"rung_id": best_classical, **bs.difference(point["against_best"], draws["against_best"], replicates=reps)},
        "against": {r: bs.difference(point["against"][r], draws["against"][r], replicates=reps) for r in classical},
    }


def _block(seed: int, reps: int, defaults: int, *, evaluated: bool, reason: dict[str, str] | None, better: str | None,
           best: dict[str, Any], against: list[dict[str, Any]]) -> dict[str, Any]:
    return {"method": bs.method_text("out-of-time defaults of the test cohort", "los incumplimientos de la cohorte de prueba fuera de tiempo", reps), "resampled_unit": "default",
            "replicates": reps, "level": bs.LEVEL, "seed": int(seed), "predictions_refit": False, "evaluated": evaluated, "reason": reason,
            "defaults": int(defaults), "better_rung": better, "against_best": best, "against": against,
            "interval_excludes_zero": best["excludes_zero"] if evaluated else None, "overall": None}


def interval_block(y: np.ndarray, preds: dict[str, np.ndarray], not_fitted: dict[str, str], *, seed: int,
                   replicates: int | None = None) -> dict[str, Any]:
    """The ``outputs.ml_benchmark`` block of one test cohort. ``preds`` holds the predictions of the rungs that were fitted and
    ``not_fitted`` the reason of each that was not. A rung of the six that is not fitted has no comparison, with its reason; a new
    rung that is not fitted leaves every interval null with the reason, never a number. ``overall`` stays None: the case fills it
    once every cohort is baked."""
    reps = bs.REPLICATES if replicates is None else int(replicates)
    n = int(np.asarray(y).size)

    def null_row(rung_id: str | None, reason: dict[str, str]) -> dict[str, Any]:
        return {"rung_id": rung_id, **bs.difference(None, np.array([]), reason=reason)}

    def null_block(reason: dict[str, str]) -> dict[str, Any]:
        rows = [null_row(r, reason) for r in ml.CLASSICAL_RUNGS]
        return _block(seed, reps, n, evaluated=False, reason=reason, better=None, best=null_row(None, reason), against=rows)

    missing_new = [r for r in ml.ML_RUNGS if r not in preds]
    if missing_new:
        why = "; ".join(f"{r}: {not_fitted.get(r, 'not fitted')}" for r in missing_new)
        return null_block(bs.text(f"a machine-learning rung was not fitted ({why}): there is nothing to compare",
                                  f"una etapa de aprendizaje automático no se ajustó ({why}): no hay nada que comparar"))
    if not any(r in preds for r in ml.CLASSICAL_RUNGS):
        return null_block(bs.text("none of the six rungs before the machine-learning rungs was fitted: there is nothing to compare against",
                                  "ninguna de las seis etapas anteriores a las de aprendizaje automático se ajustó: no hay contra qué comparar"))
    if n < bs.MIN_EVENTS:
        return null_block(bs.text(f"{n} defaults in the test cohort, fewer than the {bs.MIN_EVENTS} an interval needs",
                                  f"{n} incumplimientos en la cohorte de prueba, menos de los {bs.MIN_EVENTS} que necesita un intervalo"))
    out = compare(y, preds, seed=seed, replicates=reps)
    rows = []
    for r in ml.CLASSICAL_RUNGS:
        if r in out["against"]:
            rows.append({"rung_id": r, **out["against"][r]})
        else:
            rows.append(null_row(r, _unfitted(r, not_fitted.get(r, "not fitted"))))
    return _block(seed, reps, n, evaluated=True, reason=None, better=out["better_rung"], best=out["against_best"], against=rows)


def overall(wins_by_cohort: list[bool | None], blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """The verdict of the pre-registered rule (``ml_benchmark.verdict``, untouched) over the cohorts where the comparison is made, and how
    many of the cohorts where it holds have the interval against the best of the six excluding zero."""
    judged = [w for w in wins_by_cohort if w is not None]
    wins = sum(1 for w in judged if w)
    excl = sum(1 for w, b in zip(wins_by_cohort, blocks, strict=True) if w and b["interval_excludes_zero"])
    return {"cohorts": len(wins_by_cohort), "evaluable": len(judged), "wins": wins, "wins_excluding_zero": int(excl),
            "verdict": ml.verdict(wins, len(judged)) if judged else None}


def overall_findings(stated: dict[str, Any], wins_by_cohort: list[bool | None], blocks: list[dict[str, Any]]) -> list[str]:
    """A count or a verdict of a document that disagrees with its cohorts."""
    want = overall(wins_by_cohort, blocks)
    out = [f"overall.{k} is {stated.get(k)!r}, the cohorts give {v!r}" for k, v in want.items() if stated.get(k) != v]
    if stated.get("wins_excluding_zero", 0) > stated.get("wins", 0):
        out.append("more cohorts exclude zero than the hypothesis holds in")
    return out


__all__ = ["compare", "interval_block", "overall", "overall_findings", "point_differences", "replicate_differences"]
