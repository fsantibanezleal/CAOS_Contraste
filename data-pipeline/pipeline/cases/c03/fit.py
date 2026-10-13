"""The ladder of C03 on one training window (CT-804, CT-806).

The rungs are the existing ones of C01 (``cases/c01_ladder.py`` over ``pipeline/model``): constant, WoE scorecard, penalised
logit on WoE, PLTR, explainable boosting machine and monotone gradient boosting, fitted on a stratified sample of the window's
loans (the window of the last cohort holds about a million loans; the sample is capped at 40,000 rows, and its size is in every model record),
with a disjoint stratified sample of the same window for the isotonic maps of the rungs that need one. Nothing outside the
window is read: the loans are selected by approval fiscal year, labelled at the cutoff, and the monotone directions are
declared from the window's own labels before any fit (the sign of the Spearman correlation of each numeric input with the
target, when its magnitude is at least 0.02).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from ..c01_ladder import Rung, _t, fit_ladder
from ...model import benchmark
from ...stages import split
from . import panel
from .windows import Window

FIT_N = 40_000
CAL_N = 20_000
#: a rung beyond the constant needs this many events and this many non-events in the window
MIN_EVENTS = 100
DIRECTION_MIN_RHO = 0.02
MONTHS = (12, 24, 36, 48, 60)

RUNG_KINDS = {"P0-constant": "constant", "P1-scorecard": "woe-scorecard", "P2a-l1": "penalised-logit", "P2b-pltr": "pltr",
              "P3-ebm": "ebm", "P4-lightgbm": "monotone-gbm"}
TABPFN_ID = "P5-tabpfn"
TABPFN_REASON = ("TabPFN is the optional extra (data-pipeline/requirements-tabpfn.txt) and it is not installed in the bake "
                 "environment: the challenger is declared absent, and no number stands in for it")


@dataclass
class WindowFit:
    """The rungs of one training window, with what they were fitted on."""

    window: Window
    rungs: dict[str, Rung]
    not_evaluated: dict[str, str]
    monotone: dict[str, int]
    n_loans: int
    n_events: int
    n_censored: int
    fit_rows: int
    cal_rows: int
    seed: int
    X_fit: pd.DataFrame
    X_cal: pd.DataFrame
    y_cal: np.ndarray
    timing: dict[int, float] = field(default_factory=dict)


def training_data(loans: panel.Loans, window: Window) -> tuple[np.ndarray, np.ndarray]:
    """Positions of the loans of the window with a known outcome at its cutoff, and their labels. Only the loans approved in
    the window's fiscal years are read, and their outcomes as known on the cutoff."""
    sel = np.flatnonzero((loans.fy >= window.first_fy) & (loans.fy <= window.last_fy))
    y = panel.label(loans.take(sel), np.datetime64(window.cutoff))
    known = y != panel.LABEL_CENSORED
    return sel[known], y[known].astype(int)


def declared_directions(X: pd.DataFrame, y: np.ndarray) -> dict[str, int]:
    """+1 where a larger value raises the event rate, -1 where it lowers it, 0 where the input is categorical or the Spearman
    correlation with the target is under 0.02 in magnitude. A function of the window's inputs and labels only."""
    out: dict[str, int] = {}
    for f in panel.FEATURES:
        if f in panel.CATEGORICAL:
            out[f] = 0
            continue
        x = X[f].to_numpy(dtype=float)
        rho = 0.0 if np.ptp(x) == 0 else float(stats.spearmanr(x, y).statistic)
        out[f] = 0 if not np.isfinite(rho) or abs(rho) < DIRECTION_MIN_RHO else (1 if rho > 0 else -1)
    return out


def timing_profile(loans: panel.Loans, idx: np.ndarray, y: np.ndarray) -> dict[int, float]:
    """The share of the 5-year charge-offs of the window that fall by month m (12, 24, 36, 48, 60): the shape the predicted
    cumulative curve of a vintage takes. The 5-year PD is the model's; this only allocates it in time. Half an event is added
    to every count (a continuity correction, negligible where the window holds thousands of events) so that the share by
    month 12 is never exactly zero."""
    ln = loans.take(idx)
    k = {}
    for m in MONTHS:
        by = (ln.exit_kind == panel.EXIT_DEFAULT) & (ln.exit_date <= panel.horizon_end(ln.approval, m)) & (y == 1)
        k[m] = float(by.sum())
    if k[60] <= 0:
        raise ValueError("the window holds no 5-year charge-off to give the curve a shape")
    share = {m: (k[m] + 0.5) / (k[60] + 0.5) for m in MONTHS}
    if not all(share[a] < share[b] for a, b in zip(MONTHS, MONTHS[1:], strict=False)):
        raise ValueError(f"the cumulative charge-off share of the window is not increasing in time: {share}")
    return share


def _constant_rung(y: np.ndarray) -> Rung:
    const = benchmark.fit_constant(y)
    return Rung("P0-constant", "P0", _t("Constant PD", "PD constante"), "own", "n/a", "MIT", const,
                parameters={"pd": {"value": const.pd_value, "unit": "probability"}})


def fit_window(loans: panel.Loans, window: Window, seed: int, *, fit_n: int = FIT_N, cal_n: int = CAL_N,
               min_events: int = MIN_EVENTS, log: Callable[[str], None] | None = None) -> WindowFit:
    idx, y = training_data(loans, window)
    n_window = int(((loans.fy >= window.first_fy) & (loans.fy <= window.last_fy)).sum())
    n_loans, n_events = len(idx), int(y.sum())
    if n_events == 0 or n_events == n_loans:
        raise ValueError(f"the window FY{window.first_fy} to FY{window.last_fy} holds {n_events} events in {n_loans} loans: "
                         "a PD cannot be fitted")
    X_all = panel.features(loans, idx)
    directions = declared_directions(X_all, y)
    pos = np.arange(n_loans)
    n_fit = min(fit_n, int(0.7 * n_loans))
    fit_pos = split.subsample(pos, y, n_fit, seed=seed)
    rest = np.setdiff1d(pos, fit_pos)
    cal_pos = rest if cal_n >= len(rest) else split.subsample(rest, y, cal_n, seed=seed + 1)
    X_fit, y_fit = X_all.iloc[fit_pos].reset_index(drop=True), y[fit_pos]
    X_cal, y_cal = X_all.iloc[cal_pos].reset_index(drop=True), y[cal_pos]
    timing = timing_profile(loans, idx, y)
    not_evaluated = {TABPFN_ID: TABPFN_REASON}
    if n_events < min_events or n_loans - n_events < min_events:
        rungs = {"P0-constant": _constant_rung(y_fit)}
        for rid in RUNG_KINDS:
            if rid != "P0-constant":
                not_evaluated[rid] = (f"not fitted: the window holds {n_events} events and {n_loans - n_events} non-events in "
                                      f"{n_loans} loans, and the rung needs at least {min_events} of each")
    else:
        from sklearn.model_selection import RepeatedStratifiedKFold

        rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=seed + 2)
        folds = tuple((a, b) for a, b in rskf.split(np.zeros(len(y_fit)), y_fit))
        every = fit_ladder(X_fit, y_fit, X_cal, y_cal, folds, features=panel.FEATURES, categorical=panel.CATEGORICAL,
                           monotone=directions, seed=seed, with_xgboost=False, with_tabpfn=False, log=log)
        rungs = {rid: r for rid, r in every.items() if rid in RUNG_KINDS}
    return WindowFit(window=window, rungs=rungs, not_evaluated=not_evaluated, monotone=directions, n_loans=n_loans,
                     n_events=n_events, n_censored=n_window - n_loans, fit_rows=len(fit_pos), cal_rows=len(cal_pos), seed=seed,
                     X_fit=X_fit, X_cal=X_cal, y_cal=y_cal, timing=timing)
