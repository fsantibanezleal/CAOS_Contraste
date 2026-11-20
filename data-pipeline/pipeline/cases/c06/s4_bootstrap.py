"""Loan-level bootstrap intervals on the S-4 comparison of C06 (PC-Hazard against Cox at a reporting date), beside its verdict.

The S-4 hypothesis (``backtest.S4_HYPOTHESIS``) is judged by two point differences at each date, the integrated Brier score and the
mean absolute decile gap against Aalen-Johansen, and by a count of the dates where both favour PC-Hazard. A reader cannot tell whether a
difference at one date is larger than the sampling noise of the out-of-time accounts. This module resamples those accounts with
replacement (``cases.bootstrap``), holds the predictions of both rungs fixed (nothing is refitted: the interval is the uncertainty of the
comparison on this book, not of the fits) and recomputes both differences on every resample. The verdict is untouched.

A resample is kept as the number of times each account is drawn, so a replicate is a weighted sample of the accounts, never a resample of
an aggregate (a decile or a horizon). The statistics of a replicate are the ones ``backtest`` computes at the date:

- the integrated Brier score is ``riskvalidation.validation.ifrs9.lifetime_pd_backtest`` (the engine), fed the predicted mean cumulative PD
  of the resample and the Kaplan-Meier estimate of the resample at the six horizons;
- the decile gap is the predicted-risk deciles of the resample (the accounts in the order of the rung's predicted PD, split into ten parts
  of equal size as ``np.array_split`` does, a drawn-twice account counting twice, possibly across two deciles) with the observed cumulative
  incidence of each decile by Aalen-Johansen, as ``backtest.decile_calibration_rows``. Kaplan-Meier and Aalen-Johansen take integer weights
  here (``weighted_estimates``); the tests check them against the unweighted estimators on the expanded sample, and the replicate that
  draws every account once against ``backtest.s4_evaluation``, which the bake also asserts before it writes an interval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.validation import ifrs9 as rv_ifrs9

from .. import bootstrap as bs
from . import backtest as bt

HORIZONS = bt.HORIZONS
DECILE_HORIZONS = bt.DECILE_HORIZONS
MIN_COHORT = bt.MIN_COHORT
#: the two measures, in the order of the document
MEASURES = ("integrated_brier", "mean_decile_gap")
#: the arms of the comparison: the first minus the second (PC-Hazard minus Cox: negative favours PC-Hazard)
ARMS = (("pch", "L3-pch"), ("cox", "L2-cox"))
EPS = 1e-9


@dataclass
class Arm:
    """One rung's predictions on the accounts of the book, fixed for every replicate."""

    cum: np.ndarray                 # (N, 6) cumulative PD at ``HORIZONS``, before clipping
    risk: dict[int, np.ndarray]     # horizon in months -> (N,) cumulative PD, for the deciles


@dataclass
class _Partition:
    """The accounts in the order of one rung's predicted risk at one horizon, with what a decile needs of each."""

    order: np.ndarray
    pred: np.ndarray
    tb: np.ndarray
    ev: np.ndarray
    ex: np.ndarray
    tg: np.ndarray
    kb_km: int
    kb_aj: int


@dataclass
class Inputs:
    """The out-of-time accounts with their follow-up and the fixed predictions of both rungs, prepared once for all replicates."""

    n: int
    horizon: float
    m: int
    tb: np.ndarray
    ev: np.ndarray
    ex: np.ndarray
    tg: np.ndarray
    arms: dict[str, Arm]
    kb6_km: np.ndarray
    observed6: np.ndarray
    events_to: np.ndarray           # (N, 6) 1 where the account defaulted within the horizon
    bounds: np.ndarray              # (11,) the decile edges in drawn accounts
    valid_group: np.ndarray         # (10,) the decile holds at least ``MIN_COHORT`` accounts
    partitions: dict[tuple[str, int], _Partition] = field(default_factory=dict)
    decile_ks: tuple[int, ...] = ()


# ---------------------------------------------------------------------------------------------------------------------
# weighted Kaplan-Meier and Aalen-Johansen


def _safe_div(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    out = np.zeros_like(a, dtype=float)
    np.divide(a, b, out=out, where=b > 0)
    return out


def _curves(tb: np.ndarray, w: np.ndarray, ev: np.ndarray, ex: np.ndarray, tg: np.ndarray, m: int, kb_km: np.ndarray,
            kb_aj: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Kaplan-Meier cumulative default (an exit that is not a default censors) and Aalen-Johansen cumulative incidence of the default
    (every exit competes) at the horizons given as counts of time bins (``kb_*``), for accounts with weights ``w``."""
    wb = np.bincount(tb, weights=w, minlength=m)
    at_risk = w.sum() - (np.cumsum(wb) - wb)
    km_s = np.cumprod(1.0 - _safe_div(np.bincount(tb, weights=w * ev, minlength=m), at_risk))
    km = np.where(kb_km > 0, 1.0 - km_s[np.clip(kb_km - 1, 0, None)], 0.0)
    surv = np.cumprod(1.0 - _safe_div(np.bincount(tb, weights=w * ex, minlength=m), at_risk))
    prev = np.concatenate(([1.0], surv[:-1]))
    cif = np.cumsum(prev * _safe_div(np.bincount(tb, weights=w * tg, minlength=m), at_risk))
    aj = np.where(kb_aj > 0, cif[np.clip(kb_aj - 1, 0, None)], 0.0)
    return km, aj


def weighted_estimates(time: np.ndarray, event: np.ndarray, cause: np.ndarray, weights: np.ndarray,
                       horizons: tuple[int, ...] | list[float]) -> tuple[np.ndarray, np.ndarray]:
    """``(km, aj)`` at ``horizons``: the Kaplan-Meier cumulative default (``backtest.km_observed``) and the Aalen-Johansen cumulative
    incidence (``neural.aalen_johansen``, target 1) of accounts that count ``weights`` times each (a resample that draws an account twice
    gives it weight 2). With integer weights they equal the unweighted estimators on the expanded sample."""
    time = np.asarray(time, dtype=float)
    ut, tb = np.unique(time, return_inverse=True)
    h = np.asarray(horizons, dtype=float)
    kb_km = np.searchsorted(ut + EPS, h + EPS, side="right")
    kb_aj = np.searchsorted(ut, h, side="right")
    cause = np.asarray(cause)
    return _curves(tb, np.asarray(weights, dtype=float), np.asarray(event, dtype=float), (cause > 0).astype(float),
                   (cause == 1).astype(float), ut.size, kb_km, kb_aj)


# ---------------------------------------------------------------------------------------------------------------------
# the prepared inputs


def prepare(time: np.ndarray, event: np.ndarray, cause: np.ndarray, horizon: float, arms: dict[str, Arm]) -> Inputs:
    n = int(time.size)
    ut, tb = np.unique(np.asarray(time, dtype=float), return_inverse=True)
    ev = np.asarray(event, dtype=float)
    ex = (np.asarray(cause) > 0).astype(float)
    tg = (np.asarray(cause) == 1).astype(float)
    hz = np.asarray(HORIZONS, dtype=float)
    kb6 = np.searchsorted(ut + EPS, hz + EPS, side="right")
    events_to = ((np.asarray(event, dtype=bool)[:, None]) & (np.asarray(time)[:, None] <= hz[None, :])).astype(float)
    sizes = np.array([len(p) for p in np.array_split(np.arange(n), 10)])
    inp = Inputs(n=n, horizon=float(horizon), m=ut.size, tb=tb, ev=ev, ex=ex, tg=tg, arms=arms, kb6_km=kb6,
                 observed6=hz <= horizon + 1e-9, events_to=events_to, bounds=np.concatenate(([0], np.cumsum(sizes))).astype(np.int64),
                 valid_group=sizes >= MIN_COHORT)
    inp.decile_ks = tuple(k for k in DECILE_HORIZONS if k <= horizon + 1e-9)
    for name, arm in arms.items():
        for k in inp.decile_ks:
            order = np.argsort(arm.risk[k], kind="stable")
            inp.partitions[(name, k)] = _Partition(
                order=order, pred=arm.risk[k][order], tb=tb[order], ev=ev[order], ex=ex[order], tg=tg[order],
                kb_km=int(np.searchsorted(ut + EPS, k + EPS, side="right")), kb_aj=int(np.searchsorted(ut, float(k), side="right")))
    return inp


def inputs_from_run(run: Any, follow: bt.FollowUp) -> Inputs:
    """The accounts of the S-4 backtest (those with a full 36-month life) with the fixed predictions of Cox and PC-Hazard, taken from the
    same calls ``backtest`` makes; nothing here refits a rung."""
    elig = run.horizon_q >= bt.BACKTEST_Q
    arms = {}
    for name, rung in ARMS:
        cum = bt._predicted(rung, run, run.ladder, elig, HORIZONS)
        arms[name] = Arm(cum=cum, risk={k: bt._predicted(rung, run, run.ladder, elig, (k,))[:, 0] for k in DECILE_HORIZONS})
    return prepare(follow.time[elig], follow.event[elig], follow.cause[elig], follow.horizon, arms)


# ---------------------------------------------------------------------------------------------------------------------
# the statistics of one (re)sample


def _integrated_brier(inp: Inputs, c: np.ndarray, km6: np.ndarray, ev_n: np.ndarray, arm: Arm, name: str) -> float | None:
    pred = bt.clean((c @ arm.cum) / inp.n)
    res = rv_ifrs9.lifetime_pd_backtest(np.asarray(HORIZONS), pred, km6, np.full(len(HORIZONS), float(inp.n)), ev_n, rho=None,
                                        competing_prepayment=False, model_id=name, segment="all")
    brier = res.extras.get("brier")
    return float(np.mean(brier)) if brier else None


def _mean_decile_gap(inp: Inputs, c: np.ndarray, name: str) -> float | None:
    per_k = []
    for k in inp.decile_ks:
        part = inp.partitions[(name, k)]
        cs_ = c[part.order]
        cs = np.cumsum(cs_)
        gaps = []
        for g in range(10):
            if not inp.valid_group[g]:
                continue
            b0, b1 = int(inp.bounds[g]), int(inp.bounds[g + 1])
            lo = int(np.searchsorted(cs, b0, side="right"))
            hi = int(np.searchsorted(cs, b1, side="left")) + 1
            e = cs[lo:hi]
            w = (np.minimum(e, b1) - np.maximum(e - cs_[lo:hi], b0)).astype(float)
            pred = float(np.clip(part.pred[lo:hi] @ w / (b1 - b0), 1e-9, 1 - 1e-9))
            _, aj = _curves(part.tb[lo:hi], w, part.ev[lo:hi], part.ex[lo:hi], part.tg[lo:hi], inp.m, np.array([part.kb_km]),
                            np.array([part.kb_aj]))
            gaps.append(abs(pred - float(aj[0])))
        if gaps:
            per_k.append(float(np.mean(gaps)))
    return float(np.mean(per_k)) if per_k else None


def statistics(inp: Inputs, c: np.ndarray) -> dict[str, dict[str, float | None]]:
    """The two measures of both arms on the resample that draws account ``i`` ``c[i]`` times."""
    c = np.asarray(c, dtype=float)
    ev_n = c @ inp.events_to
    kms, _ = _curves(inp.tb, c, inp.ev, inp.ex, inp.tg, inp.m, inp.kb6_km, inp.kb6_km)
    km6 = np.where(inp.observed6, kms, np.nan)
    out: dict[str, dict[str, float | None]] = {}
    for name, arm in inp.arms.items():
        out[name] = {"integrated_brier": _integrated_brier(inp, c, km6, ev_n, arm, name),
                     "mean_decile_gap": _mean_decile_gap(inp, c, name)}
    return out


def point_statistics(inp: Inputs) -> dict[str, dict[str, float | None]]:
    """The replicate that draws every account once: the statistics ``backtest.s4_evaluation`` reports."""
    return statistics(inp, np.ones(inp.n))


def replicate_statistics(inp: Inputs, seed: int, replicates: int | None = None) -> dict[str, dict[str, np.ndarray]]:
    """The two measures of both arms on every replicate (NaN where a measure is not defined on a resample)."""
    b = bs.REPLICATES if replicates is None else int(replicates)
    out = {name: {m: np.full(b, np.nan) for m in MEASURES} for name in inp.arms}
    for i, c in enumerate(bs.draws(inp.n, b, seed)):
        stats = statistics(inp, c)
        for name, row in stats.items():
            for m, v in row.items():
                if v is not None:
                    out[name][m][i] = v
    return out


def _diff(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def compare(time: np.ndarray, event: np.ndarray, cause: np.ndarray, horizon: float, arms: dict[str, Arm], *, seed: int,
            replicates: int | None = None) -> dict[str, dict[str, Any]]:
    """The first arm minus the second on both measures, with their percentile intervals (pure arrays: the planted cases of the tests)."""
    reps = bs.REPLICATES if replicates is None else int(replicates)
    inp = prepare(time, event, cause, horizon, arms)
    first, second = list(arms)
    point = point_statistics(inp)
    draws = replicate_statistics(inp, seed, reps)
    return {m: bs.difference(_diff(point[first][m], point[second][m]), draws[first][m] - draws[second][m], replicates=reps) for m in MEASURES}


# ---------------------------------------------------------------------------------------------------------------------
# the block of the models document


def _unobserved(measure: str) -> dict[str, str]:
    if measure == "integrated_brier":
        return bs.text("no horizon of the backtest is observed yet at this date", "ningún horizonte de la prueba retrospectiva se observa aún en esta fecha")
    return bs.text(f"no horizon of 12, 24 or 36 months is observed at this date, or its deciles hold fewer than {MIN_COHORT} accounts",
                   f"ningún horizonte de 12, 24 o 36 meses se observa en esta fecha, o sus deciles tienen menos de {MIN_COHORT} cuentas")


def _block(seed: int, reps: int, *, evaluated: bool, reason: dict[str, str] | None, accounts: int | None,
           differences: list[dict[str, Any]]) -> dict[str, Any]:
    flags = [d["excludes_zero"] for d in differences]
    if not evaluated:
        both = None
    elif any(f is False for f in flags):
        both = False
    else:
        both = None if any(f is None for f in flags) else True
    return {"method": bs.method_text("out-of-time accounts", "las cuentas fuera de tiempo", reps), "resampled_unit": "account", "replicates": reps, "level": bs.LEVEL, "seed": int(seed),
            "predictions_refit": False, "evaluated": evaluated, "reason": reason, "accounts": accounts, "differences": differences,
            "both_exclude_zero": both, "overall": None}


def s4_bootstrap(run: Any, follow: bt.FollowUp, evaluation: bt.S4Evaluation | None, *, seed: int, replicates: int | None = None) -> dict[str, Any]:
    """The ``fit.s4_bootstrap`` block of one reporting date. Null differences with their reason (never a number) when the PC-Hazard rung
    was not fitted (``evaluation`` is None) or the followed accounts hold fewer than ``bootstrap.MIN_EVENTS`` defaults. ``overall``
    stays None: the case fills it once every date is baked."""
    reps = bs.REPLICATES if replicates is None else int(replicates)

    def null(reason: dict[str, str], accounts: int | None) -> dict[str, Any]:
        return _block(seed, reps, evaluated=False, reason=reason, accounts=accounts,
                      differences=[{"measure": m, **bs.difference(None, np.array([]), reason=reason)} for m in MEASURES])

    if evaluation is None:
        return null(bs.text("the PC-Hazard rung was not fitted at this reporting date (too few loans or defaults): there is no comparison to bootstrap",
                            "el peldaño PC-Hazard no se ajustó en esta fecha de reporte (muy pocos préstamos o incumplimientos): no hay comparación que remuestrear"), None)
    elig = run.horizon_q >= bt.BACKTEST_Q
    defaults = int(follow.event[elig].sum())
    if defaults < bs.MIN_EVENTS:
        return null(bs.text(f"{defaults} defaults followed, fewer than the {bs.MIN_EVENTS} an interval needs", f"{defaults} incumplimientos seguidos, menos de los {bs.MIN_EVENTS} que necesita un intervalo"),
                    int(elig.sum()))
    inp = inputs_from_run(run, follow)
    point = point_statistics(inp)
    s = evaluation.summary
    expected = {"pch": {"integrated_brier": s["integrated_brier"]["pch"], "mean_decile_gap": s["mean_abs_decile_gap_aalen_johansen"]["pch_mean"]},
                "cox": {"integrated_brier": s["integrated_brier"]["cox"], "mean_decile_gap": s["mean_abs_decile_gap_aalen_johansen"]["cox_mean"]}}
    for name in expected:
        for m in MEASURES:
            a, e = point[name][m], expected[name][m]
            if (a is None) != (e is None) or (a is not None and abs(a - e) > 1e-9):
                raise ValueError(f"the identity replicate of {name} {m} is {a}, the S-4 evaluation says {e}: the bootstrap would judge another statistic")
    draws = replicate_statistics(inp, seed, reps)
    diffs = []
    for m in MEASURES:
        d = bs.difference(_diff(point["pch"][m], point["cox"][m]), draws["pch"][m] - draws["cox"][m], reason=_unobserved(m), replicates=reps)
        diffs.append({"measure": m, **d})
    return _block(seed, reps, evaluated=True, reason=None, accounts=inp.n, differences=diffs)


# ---------------------------------------------------------------------------------------------------------------------
# the count over the dates


def overall(holds_by_date: list[bool | None], blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """The verdict of the pre-registered rule (``backtest.s4_verdict``, untouched) and how many of the dates where it holds have both
    intervals excluding zero."""
    v = bt.s4_verdict(holds_by_date)
    n = sum(1 for h, b in zip(holds_by_date, blocks, strict=True) if h and b["both_exclude_zero"])
    return {"dates": v["dates"], "evaluable": v["evaluable"], "holds_at": v["holds_at"], "holds_excluding_zero": int(n), "verdict": v["verdict"]}


def overall_findings(stated: dict[str, Any], holds_by_date: list[bool | None], blocks: list[dict[str, Any]]) -> list[str]:
    """A count or a verdict of a document that disagrees with its dates."""
    want = overall(holds_by_date, blocks)
    out = [f"overall.{k} is {stated.get(k)!r}, the dates give {v!r}" for k, v in want.items() if stated.get(k) != v]
    if stated.get("holds_excluding_zero", 0) > stated.get("holds_at", 0):
        out.append("more dates exclude zero than the hypothesis holds at")
    return out


__all__ = ["Arm", "Inputs", "compare", "inputs_from_run", "overall", "overall_findings", "point_statistics", "prepare", "replicate_statistics",
           "s4_bootstrap", "statistics", "weighted_estimates", "HORIZONS", "DECILE_HORIZONS", "MEASURES"]
