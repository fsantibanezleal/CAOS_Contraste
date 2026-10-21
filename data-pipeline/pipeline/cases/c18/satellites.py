"""The macro satellites of the five Fed loan types: fitted on the Board's net charge-off rates of 1985 to 2019 and evaluated out of time.

Every fit, projection and back-cast statistic is ``riskvalidation.stress`` (``fit_satellite``, ``project_scenario``) or
``riskvalidation.validation.stress`` (``satellite_backcast``, ``sensitivity_monotonicity``). The rates are signed (decision W1): the
residential and commercial real estate series are missing before 1991 Q1 and hold quarters of net recoveries, so those two use the
identity link and start in 1991 Q1; the other three use the probit link from 1985 Q1. No quarter is floored or dropped, and no quarter
from 2020 on is read by a fit (the window is explicit and the function refuses to read outside it). Regressors are the agency series
only (decision Q7); the satellites are fitted on United States data and applied to Banco Andino, a labelled adaptation (decision Q6).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.stress import satellites as rv_sat
from riskvalidation.validation import stress as rv_vs

from . import params as P
from .fed import FedInputs, Rates

SERIES_TEXT = {"real_gdp_growth": "Federal Reserve historic table, real GDP growth (agency series)",
               "unemployment_rate": "Federal Reserve historic table, unemployment rate (agency series)"}
MODEL_ID = "c18-satellites-us-calibrated"


def model_id(loan_type: str) -> str:
    return f"c18-satellite-{loan_type}"


@dataclass(frozen=True)
class Satellite:
    loan_type: str
    series_id: str
    fit: rv_sat.SatelliteFit
    non_positive: int
    quarters: tuple[str, ...]          # the aligned quarters of the data the fit was drawn from
    rates: np.ndarray
    x: np.ndarray


def fit_all(rates: Rates, fed: FedInputs) -> dict[str, Satellite]:
    """One fit per loan type on its window to 2019 Q4."""
    qs = [q for q in rates.quarters if q in set(fed.history["quarter_end"])]
    hq = fed.history.set_index("quarter_end")
    x = np.column_stack([hq.loc[qs, name].to_numpy(dtype=float) for name in P.REGRESSORS])
    out = {}
    for ltype, (col, link, first) in P.FED_TYPES.items():
        r = np.array([rates.rates[ltype][rates.quarters.index(q)] for q in qs])
        fit = rv_sat.fit_satellite(r, x, P.REGRESSORS, P.LAGS, P.AR_ORDER, link, qs, first, P.FIT_END)
        win = r[qs.index(first): qs.index(P.FIT_END) + 1]
        out[ltype] = Satellite(ltype, col, fit, int(np.sum(win <= 0.0)), tuple(qs), r, x)
    return out


def record(s: Satellite) -> dict[str, Any]:
    """The models document's ``fit.satellites[*]`` entry."""
    f = s.fit
    regs = [{"name": name, "lag": lag, "source_series": SERIES_TEXT[name], "licence_class": "agency"} for name in f.regressor_names for lag in f.lags]
    coefs = [{"name": n, "estimate": e, "std_error": se, "expected_sign": P.EXPECTED_SIGN[n]}
             for n, e, se in zip(f.coefficient_names, f.estimates, f.std_errors, strict=True)]
    return {"model_id": model_id(s.loan_type), "fed_loan_type": s.loan_type, "series_id": s.series_id, "link": f.link,
            "sample_window": {"start": f.window_start, "end": f.window_end}, "non_positive_quarters_in_window": s.non_positive,
            "ar_order": f.ar_order, "n_obs": f.n_obs, "regressors": regs, "coefficients": coefs,
            "fit_statistics": {"r_squared": f.r_squared, "residual_sd": f.residual_sd}, "estimation": "ols-numpy-with-standard-errors"}


def project(s: Satellite, path: np.ndarray) -> rv_sat.SatelliteProjection:
    """The 12 quarters after the jump-off for a transposed regressor path (columns in ``P.REGRESSORS`` order)."""
    i = s.quarters.index(P.JUMP_OFF)
    last = rv_sat.link(s.fit.link, np.array([s.rates[i]]))
    hist = s.x[i - max(s.fit.lags) + 1: i + 1]
    return rv_sat.project_scenario(s.fit, last, hist, path)


def path_matrix(transposed: dict[str, np.ndarray]) -> np.ndarray:
    return np.column_stack([transposed[name] for name in P.REGRESSORS])


def backcast(s: Satellite) -> dict[str, Any]:
    """The back-cast of 2020 Q1 to 2025 Q4: the recursion of the fit from 2019 Q4 on the realised regressors, against the realised rates."""
    i0 = s.quarters.index(P.FIT_END)
    i1 = s.quarters.index(P.BACKCAST_END)
    qs = list(s.quarters[i0 + 1: i1 + 1])
    last = rv_sat.link(s.fit.link, np.array([s.rates[i0]]))
    hist = s.x[i0 - max(s.fit.lags) + 1: i0 + 1]
    pred = rv_sat.project_scenario(s.fit, last, hist, s.x[i0 + 1: i1 + 1]).rates
    real = s.rates[i0 + 1: i1 + 1]
    if np.any(~np.isfinite(real)):
        raise ValueError(f"{s.loan_type}: the Board's table has a missing quarter in 2020 to 2025; a missing quarter is never filled")
    test = rv_vs.satellite_backcast(pred, real, qs, P.FIT_END, model_id=model_id(s.loan_type), segment=s.loan_type)
    ip, ir = int(np.argmax(pred)), int(np.argmax(real))
    rmse = float(np.sqrt(np.mean((pred - real) ** 2)))
    return {"fed_loan_type": s.loan_type, "series_id": s.series_id, "link": s.fit.link,
            "fit_window": {"start": s.fit.window_start, "end": s.fit.window_end},
            "quarters": [{"quarter_end": q, "predicted": float(p), "realised": float(r)} for q, p, r in zip(qs, pred, real, strict=True)],
            "metrics": {"rmse": rmse, "peak_predicted": float(pred[ip]), "peak_predicted_quarter": qs[ip], "peak_realised": float(real[ir]),
                        "peak_realised_quarter": qs[ir], "peak_timing_error_quarters": ip - ir}, "_test": test}


def descriptive_2026(rates: Rates) -> list[dict[str, Any]]:
    """2026 Q1 and Q2 as realised rates only: no forecast claim (decision Q8)."""
    rows = []
    for q in P.DESCRIPTIVE_2026:
        if q not in rates.quarters:
            raise ValueError(f"the Board's table has no rate for {q}; the descriptive row of 2026 is not written from a made-up value")
        rows.append({"quarter_end": q, "realised_rates": [
            {"fed_loan_type": lt, "rate": float(rates.rates[lt][rates.quarters.index(q)])} for lt in P.FED_TYPES],
            "label": "rate-only-descriptive", "forecast_claim": False})
    return rows


def sensitivity_test(s: Satellite) -> Any:
    f = s.fit
    return rv_vs.sensitivity_monotonicity(list(f.estimates), [P.EXPECTED_SIGN[n] for n in f.coefficient_names],
                                          model_id=model_id(s.loan_type), segment=s.loan_type)


# ------------------------------------------------------------------------------------------------ the Banco Andino classes and the credit loss


def project_all(sats: dict[str, Satellite], transposed: dict[str, np.ndarray]) -> dict[str, rv_sat.SatelliteProjection]:
    path = path_matrix(transposed)
    return {lt: project(s, path) for lt, s in sats.items()}


def class_rates(proj: dict[str, rv_sat.SatelliteProjection]) -> dict[str, np.ndarray]:
    """The weighted mix of the Fed loan types each Banco Andino class maps from (decision Q6)."""
    out = {}
    for klass, (types, weights) in P.CLASS_MAP.items():
        out[klass] = sum(w * proj[t].rates for w, t in zip(weights, types, strict=True))
    return out


def credit_losses(rates: dict[str, np.ndarray], exposure: dict[str, float]) -> list[float]:
    """The credit loss of each year: the exposure of each class times the mean of the four quarterly annualised rates of the year."""
    return [float(sum(exposure[c] * float(np.mean(rates[c][4 * y: 4 * y + 4])) for c in P.CLASSES)) for y in range(3)]


def blocks(sats: dict[str, Satellite], proj: dict[str, rv_sat.SatelliteProjection], exposure: dict[str, float]) -> dict[str, Any]:
    """The variant's ``outputs.satellites`` block."""
    qs = P.next_quarters(P.JUMP_OFF, P.HORIZON_QUARTERS)
    cr = class_rates(proj)
    return {
        "fed_loan_types": [{"fed_loan_type": lt, "series_id": s.series_id, "model_id": model_id(lt), "link": s.fit.link,
                            "quarters": [{"quarter_end": q, "rate": float(r), "link_value": float(v)}
                                         for q, r, v in zip(qs, proj[lt].rates, proj[lt].link_values, strict=True)]} for lt, s in sats.items()],
        "banco_andino_classes": [{"banco_andino_class": c, "maps_from": list(P.CLASS_MAP[c][0]), "weights": list(P.CLASS_MAP[c][1]),
                                  "exposure_clp_m": exposure[c], "label": "us-calibrated-adaptation",
                                  "quarters": [{"quarter_end": q, "rate": float(r)} for q, r in zip(qs, cr[c], strict=True)]} for c in P.CLASSES]}
