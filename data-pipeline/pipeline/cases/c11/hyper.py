"""The hyperparameters of the ladder, fixed once on 1995-01-01 to 2003-12-31 (decision D1 of the U8 sizing).

The span ends before the earliest test window (calm 2004-06), so no window tunes on itself. Each hyperparameter is chosen
among a short grid by the lowest sum of the average FZ0 loss over two series (the US equity market and the 10-year
Treasury par bond) and the two tail levels, of the rolling one-step forecasts of the one model that uses it:

- ``estimation_window_days`` in 500, 750, 1000: the GARCH(1,1) with Student-t innovations;
- ``ewma_lambda`` in 0.94, 0.97, 0.99: the EWMA;
- ``age_weight_lambda`` in 0.98, 0.99: the age-weighted historical simulation;
- ``evt_threshold_fraction`` in 0.05, 0.10, 0.15: the conditional EVT.

The euro series of the H.10 begins in 2000-01-03, too late to carry a 500 to 1,000 day window inside the span, so the FX leg
is not part of the selection (stated in the case page). The selection scores every ``stride``-th forecast day of the span
(the conditional EVT every ``2 * stride``-th) to bound the cost; the counts of CAViaR and GAS starts and the refit
frequencies are fixed by the compute budget and not tuned. Everything here reads days of the span only: the series passed
in is cut at its end (``tests/c11`` perturbs what follows).
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np
from riskvalidation.market import scoring as rv_scoring

from . import portfolio as pf
from . import quantile_net as qn
from .constants import LEVELS, SPAN, Window
from .forecast import SPEC_BY_ID, Hyper, run_model
from .readers import Series

GRID = {
    "estimation_window_days": (500, 750, 1000),
    "ewma_lambda": (0.94, 0.97, 0.99),
    "age_weight_lambda": (0.98, 0.99),
    "evt_threshold_fraction": (0.05, 0.10, 0.15),
}
MODEL_OF = {"estimation_window_days": "garch-t", "ewma_lambda": "ewma", "age_weight_lambda": "awhs",
            "evt_threshold_fraction": "evt-mf"}
STRIDE = 5
SERIES_CLASSES = ("equity", "rates")


def cut(series: dict[str, Series], end: str = SPAN[1]) -> dict[str, Series]:
    """The series with every observation after ``end`` removed (the selection never sees a test window)."""
    stop = np.datetime64(end, "D")
    out = {}
    for k, s in series.items():
        m = s.dates <= stop
        out[k] = Series(s.series_id, s.unit, s.dates[m], s.values[m], tuple(d for d in s.missing if d <= end), s.files)
    return out


def span_portfolios(series: dict[str, Series]) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Returns and span positions of the equity and rates portfolios, from the series cut at the end of the span."""
    cs = cut(series)
    out = {}
    for cls in SERIES_CLASSES:
        w = Window(f"span-{cls}", cls, SPAN[0], SPAN[1], "", "")
        p = pf.build_for(w, cs)
        out[cls] = (p.returns, pf.forecast_positions(p))
    return out


def _score(args: tuple) -> tuple[str, float, str, float]:
    name, value, cls, y, idx, hp = args
    spec = SPEC_BY_ID[MODEL_OF[name]]
    stride = STRIDE * (2 if name == "evt_threshold_fraction" else 1)
    pos = idx[::stride]
    hp = replace(hp, **{name: value})
    if name == "estimation_window_days":
        hp = replace(hp, garch_refit_every_days=max(1, 20 // STRIDE))
    run = run_model(spec, y, pos, hp)
    total = 0.0
    for a in LEVELS:
        v, e = run.var[a], run.es[a]
        ok = np.isfinite(e)
        if not ok.all():
            total += 1e6        # an undefined ES on a selection day disqualifies the candidate for that level
            continue
        total += rv_scoring.mean_scores(y[pos], v, e, a).fz0_mean
    return name, value, cls, float(total)


def select(series: dict[str, Series], base: Hyper | None = None, workers: int = 1, log=print) -> tuple[Hyper, dict]:
    """Choose the hyperparameters on the span; return them and the full record (every candidate with its score)."""
    base = base or Hyper()
    data = span_portfolios(series)
    tasks = [(name, v, cls, data[cls][0], data[cls][1], base) for name, grid in GRID.items() for v in grid for cls in data]
    if workers <= 1:
        results = [_score(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_score, tasks))
    record: dict = {"span": list(SPAN), "stride": STRIDE, "series": list(SERIES_CLASSES), "grid": {}, "selected": {}}
    chosen = {}
    for name, grid in GRID.items():
        scores = {v: sum(r[3] for r in results if r[0] == name and r[1] == v) for v in grid}
        best = min(grid, key=lambda v: (scores[v], grid.index(v)))
        chosen[name] = best
        record["grid"][name] = {"model": MODEL_OF[name], "candidates": [{"value": v, "score": scores[v]} for v in grid]}
        record["selected"][name] = best
        log(f"  {name}: {best} among {dict(scores)}")
    return replace(base, **chosen), record


def dumps(record: dict) -> str:
    return json.dumps(record, indent=1, sort_keys=True) + "\n"


# ------------------------------------------------------------------------------------------------------------------- the R10 network

#: the network's two hyperparameters that change what it can fit, chosen the same way as the others: on the span, one at a time, by the
#: lowest summed average FZ0 of the rolling one-step forecasts of the network itself; the epochs, the learning rate, the number of starts
#: and the refit frequency are fixed by the compute budget and not tuned (S-1 of the method tiers)
NET_GRID = {"hidden_units": (4, 8, 16), "weight_decay": (1e-3, 1e-2, 1e-1)}


def _score_net(args: tuple) -> tuple[str, float, str, float]:
    name, value, cls, y, idx, hp, base = args
    pos = idx[::STRIDE]
    net = replace(base, **{name: value}, refit_every_days=max(1, base.refit_every_days // STRIDE))
    run = run_model(SPEC_BY_ID["nn-fz"], y, pos, hp, net=net)
    total = 0.0
    for a in LEVELS:
        v, e = run.var[a], run.es[a]
        if not np.isfinite(e).all():
            total += 1e6
            continue
        total += rv_scoring.mean_scores(y[pos], v, e, a).fz0_mean
    return name, value, cls, float(total)


def select_net(series: dict[str, Series], hp: Hyper, base: qn.NetHyper = qn.NET, workers: int = 1, log=print) -> tuple[qn.NetHyper, dict]:
    """Choose the network's hidden units and weight decay on the span (the series cut at its end); return them and the full record."""
    data = span_portfolios(series)
    tasks = [(n, v, cls, data[cls][0], data[cls][1], hp, base) for n, grid in NET_GRID.items() for v in grid for cls in data]
    if workers <= 1:
        results = [_score_net(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_score_net, tasks))
    record: dict = {"span": list(SPAN), "stride": STRIDE, "series": list(SERIES_CLASSES), "base": base.to_json(), "grid": {}, "selected": {}}
    chosen = {}
    for name, grid in NET_GRID.items():
        scores = {v: sum(r[3] for r in results if r[0] == name and r[1] == v) for v in grid}
        best = min(grid, key=lambda v: (scores[v], grid.index(v)))
        chosen[name] = best
        record["grid"][name] = {"model": "nn-fz", "candidates": [{"value": v, "score": scores[v]} for v in grid]}
        record["selected"][name] = best
        log(f"  network {name}: {best} among {dict(scores)}")
    return replace(base, **chosen), record
