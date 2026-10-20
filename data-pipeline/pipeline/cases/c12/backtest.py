"""The PIT-based exposure backtest of the book and of the short-rate proxy (decision B5, addendum R5, BCBS 185).

On every backtest date (a month end from 2000-01 to the last month whose 12 month horizon is observed):

- the model is calibrated on the observations strictly before the date (``calibration.fit_at``) and fitted to the curve of the
  date; the book is originated at par (the fixed rates are the rule of the document on that date's curve);
- the paths are simulated to the six horizons (10 and 20 business days as 14 and 28 calendar days, 1, 3, 6 and 12 months);
- the **realised** value of the book at each horizon is the engine's ``swap_value`` of the remaining swaps on the curve actually
  published at the end of the horizon (the model with sigma = 0 on that curve, whose bond price is the curve's discount factor);
- the realised value maps to its PIT in the simulated sample by the engine's ``(i + 1) / (N + 2)`` rule, ``W^2`` is the engine's
  Anderson-Darling statistic, and the critical values come from the engine's simulation of the whole backtest under the model.

The risk factor is the 3 month zero rate: simulated as ``-ln P(t, t + 0.25) / 0.25`` from the engine's bond price, realised from
the published 3 month par yield. The sub-windows (before 2008, 2008 to 2019, from 2020) are reported apart.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import scipy.sparse as sp
from riskvalidation.ccr import exposure as ex
from riskvalidation.ccr import hw1f
from riskvalidation.ccr import swaps as sw
from riskvalidation.irrbb.curves import bootstrap_zero_curve
from riskvalidation.validation import ccr as vc
from scipy.stats import norm

from . import book, calibration, data

QUANTILES = (0.90, 0.95, 0.99)
IID_CRITICAL = {"p05": 2.492, "p01": 3.88}
SUB_WINDOWS = (("before-2008", None, "2007-12-31"), ("2008-2019", "2008-01-01", "2019-12-31"), ("from-2020", "2020-01-01", None))
YEAR_DAYS = 365.25


@dataclass
class Measure:
    """Realised values, simulated samples (N, P) and PFE forecasts (Q, N) of one measure at one horizon."""

    realised: np.ndarray
    simulated: np.ndarray
    pfe: np.ndarray
    pits: np.ndarray = field(default_factory=lambda: np.zeros(0))


@dataclass
class Result:
    dates: list[str]
    fits: list[Any]
    realised_dates: dict[str, list[str]]
    measures: dict[str, dict[str, Measure]]     # {"single" | "netting" | "rate": {horizon: Measure}}


def seed_of(seed: int, i: int) -> int:
    return (int(seed) * 1_000_003 + i) % (2**31 - 1)


def _realised_curve_functions(curve_zero: tuple[np.ndarray, np.ndarray], h: float):
    """The discount function on the original timeline whose value at ``t >= h`` is the realised discount factor over ``t - h``,
    and a forward function of zeros: the model with sigma = 0 then prices the remaining swaps off the realised curve."""
    tenors, zeros = curve_zero
    p_real, _ = hw1f.curve_functions(zeros, tenors)

    def p0(t: np.ndarray) -> np.ndarray:
        return p_real(np.maximum(np.asarray(t, dtype=float) - h, 0.0))

    def forward(t: np.ndarray) -> np.ndarray:
        return np.zeros_like(np.asarray(t, dtype=float))

    return p0, forward


def realised_book_value(swaps: list[sw.Swap], members: list[int], h: float, real_zero: tuple[np.ndarray, np.ndarray],
                        fixing: float | None, a: float) -> float:
    """The value of the remaining swaps at the horizon ``h`` on the realised curve. A period already begun carries the coupon
    fixed at the last reset: the simple rate of the curve of the date (``fixing``), known on that date."""
    p0, forward = _realised_curve_functions(real_zero, h)
    r = np.zeros(1)
    total = 0.0
    for s in members:
        sp_ = swaps[s]
        resets = sw.reset_times(sp_)
        j = int(np.searchsorted(resets, h + sw.TIME_TOL, side="right")) - 1
        between = j >= 0 and abs(resets[j] - h) > sw.TIME_TOL and h < sp_.maturity - sw.TIME_TOL
        total += float(sw.swap_value(sp_, h, r, a, 0.0, p0, forward, np.array([fixing]) if between else None)[0])
    return total


def run(curves: data.Curves, series: calibration.Series, dates: list[str], seed: int, n_paths: int,
        members: dict[str, list[str]]) -> Result:
    """The backtest over ``dates`` for the books in ``members`` (name -> trade ids) and the rate proxy."""
    horizons = data.HORIZONS
    h_years = [data.HORIZON_YEARS[h] for h in horizons]
    grid0 = np.unique(np.round(np.array([0.0] + h_years + [0.5]), 12))
    n = len(dates)
    store: dict[str, dict[str, Measure]] = {name: {} for name in [*members, "rate"]}
    for name in store:
        for h in horizons:
            store[name][h] = Measure(np.zeros(n), np.zeros((n, n_paths)), np.zeros((len(QUANTILES), n)))
    fits, real_dates = [], {h: [] for h in horizons}
    trade_ids = [t[0] for t in book.TRADES]
    for i, d in enumerate(dates):
        fit = calibration.fit_at(series, d)
        fits.append(fit)
        tenors, zeros, par = curves.zero(d)
        trades = book.trades_at(par)
        swaps = book.swaps_of(trades)
        p0, forward = hw1f.curve_functions(zeros, tenors)
        grid = sw.simulation_grid(grid0, swaps)
        r = hw1f.simulate_short_rate(grid, fit.a, fit.sigma, forward, n_paths, seed_of(seed, i))
        values = sw.swap_values_on_grid(swaps, grid, r, fit.a, fit.sigma, p0, forward)
        r0 = hw1f.phi(np.array(0.0), fit.a, fit.sigma, forward).reshape(1)
        p_fix = hw1f.bond_price(r0, 0.0, 0.5, fit.a, fit.sigma, p0, forward)
        fixing0 = float((1.0 / p_fix[0] - 1.0) / 0.5)
        for h, hy in zip(horizons, h_years, strict=True):
            k = int(np.searchsorted(grid, hy - sw.TIME_TOL))
            rd = curves.as_of(data.horizon_date(d, h))
            if rd.observation_date <= d:
                raise ValueError(f"{d}: no curve is published after the date within the {h} horizon")
            real_dates[h].append(rd.observation_date)
            rt, rz = rd.tenors(), bootstrap_zero_curve(rd.tenors(), rd.yields())
            for name, ids in members.items():
                idx = [trade_ids.index(t) for t in ids]
                sim = ex.net_values(values[idx][:, :, k:k + 1])[:, 0]
                real = realised_book_value(swaps, idx, hy, (rt, rz), fixing0, fit.a)
                m = store[name][h]
                m.realised[i], m.simulated[i] = real, sim
                m.pfe[:, i] = [float(ex.pfe(sim[:, None], q, seed=0, n_bootstrap=2)[0][0]) for q in QUANTILES]
            p_bond = hw1f.bond_price(r[:, k], hy, hy + data.PROXY_YEARS, fit.a, fit.sigma, p0, forward)
            sim_rate = -np.log(p_bond) / data.PROXY_YEARS
            real_rate = float(np.log1p(data.PROXY_YEARS * rd.par[data.PROXY_LABEL]) / data.PROXY_YEARS)
            m = store["rate"][h]
            m.realised[i], m.simulated[i] = real_rate, sim_rate
            m.pfe[:, i] = [float(ex.pfe(sim_rate[:, None], q, seed=0, n_bootstrap=2)[0][0]) for q in QUANTILES]
    for per_h in store.values():
        for m in per_h.values():
            m.pits = vc.pit_from_simulated(m.realised, m.simulated)
    return Result(dates, fits, real_dates, store)


# ---------------------------------------------------------------------------------------------- critical values


def critical_values(dates: list[str], fits: list[Any], realised_dates: dict[str, list[str]], n_paths: int, n_backtests: int,
                    seed: int) -> dict[str, vc.CriticalValues]:
    """For each horizon the engine's simulation of the whole backtest under the model. One Brownian path on a daily grid drives
    every date: the deviation of the realised state from the date's forecast is ``Y_i = sum_s w_is dW_s`` over the horizon's
    days with the weights of the mean-reverting kernel at the date's own ``a``, so overlapping horizons share increments; the PIT
    is the rank of ``Y_i`` among ``n_paths`` draws of its own law, ``(k + 1) / (n_paths + 2)`` with ``k`` binomial. The value of
    the book and the rate are monotone in that deviation, so one sampler serves both."""
    ords = np.array([dt.date.fromisoformat(d).toordinal() for d in dates])
    start = int(ords.min()) + 1
    out: dict[str, vc.CriticalValues] = {}
    for h in data.HORIZONS:
        ends = np.array([dt.date.fromisoformat(d).toordinal() for d in realised_dates[h]])
        stop = int(ends.max())
        n_days = stop - start + 1
        rows, cols, vals = [], [], []
        for i, f in enumerate(fits):
            days = np.arange(ords[i] + 1, ends[i] + 1)
            w = np.exp(-f.a * (ends[i] - days) / YEAR_DAYS)
            w = w / np.sqrt(np.sum(w**2))
            rows.append(np.full(days.size, i))
            cols.append(days - start)
            vals.append(w)
        mat = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(fits), n_days))

        def sampler(rng: np.random.Generator, mat=mat, n_days=n_days) -> np.ndarray:
            u = norm.cdf(mat @ rng.standard_normal(n_days))
            return (rng.binomial(n_paths, u) + 1.0) / (n_paths + 2.0)

        out[h] = vc.simulate_pit_critical_values(sampler, n_backtests, seed_of(seed, 7919) + data.HORIZONS.index(h))
    return out


# --------------------------------------------------------------------------------------------------- documents


def horizon_block(name: str, h: str, m: Measure, cv: vc.CriticalValues) -> dict[str, Any]:
    w2 = vc.anderson_darling_w2(m.pits)
    return {"horizon": h, "n": int(m.pits.size), "pits": [float(p) for p in m.pits],
            "exceedances": [{"quantile": q, "count": int(np.sum(m.realised > m.pfe[k])),
                             "expected": float(m.pits.size * (1.0 - q))} for k, q in enumerate(QUANTILES)],
            "w2": float(w2), "critical_iid": dict(IID_CRITICAL),
            "critical_simulated": {"p05": float(cv.p05), "p01": float(cv.p01)},
            "effective_sample_size": float(vc.effective_sample_size(m.pits)), "reject_at_5pct": bool(w2 > cv.p05)}


def sub_windows(res: Result, name: str) -> list[dict[str, Any]]:
    out = []
    for label, lo, hi in SUB_WINDOWS:
        sel = [i for i, d in enumerate(res.dates) if (lo is None or d >= lo) and (hi is None or d <= hi)]
        results = [{"horizon": h, "n": len(sel), "w2": float(vc.anderson_darling_w2(res.measures[name][h].pits[sel]))}
                   for h in data.HORIZONS]
        out.append({"window": label, "start": res.dates[sel[0]], "end": res.dates[sel[-1]], "results": results})
    return out


def backtest_document(res: Result, name: str, cvs: dict[str, vc.CriticalValues], paths_per_date: int) -> dict[str, Any]:
    """The ``backtest`` block of a variant whose book is ``name``."""
    return {"window_start": res.dates[0][:7], "window_end": res.dates[-1][:7], "dates": list(res.dates),
            "calibration_rule": "each initialisation date is calibrated on data up to that date only", "pit_rule": "(i + 1) / (N + 2)",
            "statistic": "Anderson-Darling W^2", "paths_per_date": paths_per_date,
            "book_horizons": [horizon_block(name, h, res.measures[name][h], cvs[h]) for h in data.HORIZONS],
            "risk_factor": {"proxy_tenor_years": data.PROXY_YEARS,
                            "horizons": [horizon_block("rate", h, res.measures["rate"][h], cvs[h]) for h in data.HORIZONS]},
            "sub_windows": sub_windows(res, name)}


def test_rows(res: Result, name: str, cvs: dict[str, vc.CriticalValues]) -> list[dict[str, Any]]:
    """The engine's test rows of the backtest: the PIT test of the book at every horizon, the same for the rate, and the PFE
    exceedance test (a secondary row: BCBS 185 paragraph 27, the counts assume independence and the data overlap)."""
    rows = []
    for h in data.HORIZONS:
        cv = cvs[h]
        crit = {"p05": cv.p05, "p01": cv.p01}
        for who, tag in ((name, "book"), ("rate", "risk factor")):
            m = res.measures[who][h]
            r = vc.pit_exposure_backtest(m.realised, m.simulated, crit, vc.effective_sample_size(m.pits)).to_dict()
            r["segment"] = f"{tag}-{h}"
            r["notes"] = (r["notes"] + " " if r["notes"] else "") + f"the {tag} at the {h} horizon"
            rows.append(r)
        m = res.measures[name][h]
        for k, q in enumerate(QUANTILES):
            r = vc.pfe_exceedance_backtest(m.realised, m.pfe[k], q).to_dict()
            r["segment"] = f"book-{h}-q{int(q * 100)}"
            r["extras"] = {**r["extras"], "row_role": "secondary", "reason": "BCBS 185 paragraph 27: exception counts assume independence "
                           "and the overlapping horizons are not independent"}
            r["notes"] = "secondary row. " + r["notes"]
            rows.append(r)
    return rows
