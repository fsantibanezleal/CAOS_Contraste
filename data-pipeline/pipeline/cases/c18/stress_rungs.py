"""The two state-of-the-art rungs of the macro stress ladder that sit beside the OLS satellites: the VAR conditional forecast and the
growth-at-risk quantile satellite (plan S-2 of the Contraste method tiers, tier ``sota``).

Both are computed by ``riskvalidation.stress.scenario_models`` (``fit_var``, ``var_conditional_forecast``, ``gar_quantile_regressions``,
``fit_skewed_t_to_quantiles``) and scored by ``riskvalidation.validation.stress`` (``satellite_backcast``, ``sensitivity_monotonicity``),
on the Board's historic table and charge-off rates the OLS satellites read, and nothing else (agency series only, decision Q7). Every
fit reads the train span only: the quarters up to the window's ``fit_end``, which is before the first quarter of the episode it
predicts; a window whose fit ends at or after its start is refused (a leakage). Two windows are back-cast: the global financial crisis
(fit to 2007 Q4, predict 2008 Q1 to 2009 Q4) and the pandemic window the OLS satellites already carry (fit to 2019 Q4, predict 2020
Q1 to 2025 Q4). The OLS satellite is refitted on the same train span and back-cast over the same quarters, so each loan type shows the
classical and the state-of-the-art rung on one split.

* VAR: ``y_t = [real GDP growth, unemployment rate, g(rate_t)]`` with ``g`` the satellite's link, one lag (the satellite's AR order), fitted
  by OLS. The back-cast is a conditional forecast given the realised real GDP growth path alone: unemployment and the loss rate respond
  through the system. (Given both macro paths the conditional forecast of a VAR(1) is the OLS satellite's own regression, to rounding:
  ``full_conditioning_gap_to_ols`` records it, and that form would add no model.) Expected signs of the rate equation are declared here
  before the fit.
* Growth-at-risk (Adrian, Boyarchenko and Giannone 2019): quantile regressions of the average real GDP growth over the next four quarters
  on a constant, the current growth and the term spread. The Chicago Fed NFCI of the original is not one of the registered agency series
  of the case, so the spread of the 10-year Treasury yield over the prime rate stands in for the financial conditions; it is a named
  substitution, not the paper's variable. The check is a rolling origin one: the coefficients are fixed at the end of the train span and
  every origin from there on is scored against the realised four-quarter growth, beside the unconditional quantile of the train span.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from riskvalidation.stress import satellites as rv_sat
from riskvalidation.stress import scenario_models as rv_sm
from riskvalidation.validation import stress as rv_vs

from ...core import text as ct
from . import params as P
from . import satellites as sat

T = P.text
VAR_MODEL_ID = "c18-var-conditional-forecast"
GAR_MODEL_ID = "c18-growth-at-risk"
VAR_LAGS = 1
GAR_HORIZON = 4
GAR_TAUS = (0.05, 0.25, 0.5, 0.75, 0.95)
GAR_REGRESSORS = ("real_gdp_growth", "term_spread")
#: the sign each coefficient of the VAR rate equation is expected to carry, declared before the fit: the loss rate persists, a lower
#: growth and a higher unemployment last quarter raise it (the lagged terms only; the same-quarter effect runs through the covariance)
VAR_EXPECTED_SIGN = {"intercept": "none", "ar_1": "positive", "real_gdp_growth_lag1": "negative", "unemployment_rate_lag1": "positive"}
#: the sign each coefficient of the growth-at-risk quantile regression is expected to carry at every quantile, declared before the fit:
#: growth persists and a steeper curve (a higher spread) goes with higher growth ahead
GAR_EXPECTED_SIGN = {"intercept": "none", "real_gdp_growth": "positive", "term_spread": "positive"}


@dataclass(frozen=True)
class Window:
    window_id: str
    fit_end: str
    start: str
    end: str
    label: dict[str, str]


WINDOWS = (
    Window("gfc-2008-09", "2007-12-31", P.GFC_START, P.GFC_END,
           T("Global financial crisis, 2008 Q1 to 2009 Q4, fitted to 2007 Q4", "Crisis financiera global, 2008 T1 a 2009 T4, ajustada hasta 2007 T4")),
    Window("pandemic-2020", P.FIT_END, P.BACKCAST_START, P.BACKCAST_END,
           T("Pandemic window, 2020 Q1 to 2025 Q4, fitted to 2019 Q4", "Ventana de la pandemia, 2020 T1 a 2025 T4, ajustada hasta 2019 T4")),
)


def _check_window(quarters: list[str] | tuple[str, ...], win: Window) -> tuple[int, int, int]:
    """The indices of the fit end, the first and the last quarter of the episode; a fit that reaches the episode is refused."""
    for q in (win.fit_end, win.start, win.end):
        if q not in quarters:
            raise ValueError(f"{win.window_id}: the quarter {q} is not in the data")
    i_fit, i0, i1 = quarters.index(win.fit_end), quarters.index(win.start), quarters.index(win.end)
    if i_fit >= i0:
        raise ValueError(f"{win.window_id}: the fit ends {win.fit_end}, not before the episode starts {win.start} (the train span would see the episode)")
    if i0 != i_fit + 1:
        raise ValueError(f"{win.window_id}: the episode must start the quarter after the fit ends ({win.fit_end} to {win.start})")
    return i_fit, i0, i1


def _peak_metrics(pred: np.ndarray, real: np.ndarray, qs: list[str], fit_end: str, model_id: str, loan: str) -> dict[str, Any]:
    test = rv_vs.satellite_backcast(pred, real, qs, fit_end, model_id=model_id, segment=loan)
    ip, ir = int(np.argmax(pred)), int(np.argmax(real))
    return {"rmse": float(np.sqrt(np.mean((pred - real) ** 2))), "peak_predicted": float(pred[ip]), "peak_predicted_quarter": qs[ip],
            "peak_realised": float(real[ir]), "peak_realised_quarter": qs[ir], "peak_timing_error_quarters": ip - ir,
            "peak_ratio": None if test.extras.get("peak_ratio") is None else float(test.extras["peak_ratio"]), "light": test.light.value}


def ols_backcast(s: sat.Satellite, win: Window) -> np.ndarray:
    """The OLS satellite refitted on the train span of the window and fed the realised regressors of the episode."""
    qs = list(s.quarters)
    i_fit, i0, i1 = _check_window(qs, win)
    first = P.FED_TYPES[s.loan_type][2]
    fit = rv_sat.fit_satellite(s.rates, s.x, P.REGRESSORS, P.LAGS, P.AR_ORDER, P.FED_TYPES[s.loan_type][1], qs, first, win.fit_end)
    last = rv_sat.link(fit.link, np.array([s.rates[i_fit]]))
    hist = s.x[i_fit - max(fit.lags) + 1: i_fit + 1]
    return np.asarray(rv_sat.project_scenario(fit, last, hist, s.x[i0: i1 + 1]).rates, dtype=float)


def var_backcast(s: sat.Satellite, win: Window) -> dict[str, Any]:
    """The VAR(1) of growth, unemployment and the linked loss rate on the train span, and its conditional forecast of the episode."""
    qs = list(s.quarters)
    i_fit, i0, i1 = _check_window(qs, win)
    link_name = P.FED_TYPES[s.loan_type][1]
    i_first = qs.index(P.FED_TYPES[s.loan_type][2])
    z_all = rv_sat.link(link_name, s.rates[i_first: i_fit + 1])
    y = np.column_stack([s.x[i_first: i_fit + 1, 0], s.x[i_first: i_fit + 1, 1], z_all])
    fit = rv_sm.fit_var(y, VAR_LAGS)
    # the scenario is its real GDP growth path; unemployment and the loss rate respond through the system (the stress-testing use of a conditional forecast)
    out = rv_sm.var_conditional_forecast(fit, y[-VAR_LAGS:], s.x[i0: i1 + 1, :1], [0])
    pred = np.asarray(rv_sat.inverse_link(link_name, out[:, 2]), dtype=float)
    # with BOTH macro paths given the conditional forecast is the OLS satellite's own regression (partitioned regression: the Gaussian
    # conditional mean on the OLS residual covariance reproduces it), so that form adds no model; the gap is the check that says so
    both = rv_sm.var_conditional_forecast(fit, y[-VAR_LAGS:], s.x[i0: i1 + 1], [0, 1])
    full = np.asarray(rv_sat.inverse_link(link_name, both[:, 2]), dtype=float)
    real = s.rates[i0: i1 + 1]
    if np.any(~np.isfinite(real)):
        raise ValueError(f"{s.loan_type}: the Board's table has a missing quarter in {win.start} to {win.end}; a missing quarter is never filled")
    # the classical errors of the rate equation (the engine's fit returns the point estimates and the residual covariance only)
    x = np.column_stack([np.ones(y.shape[0] - VAR_LAGS), y[:-VAR_LAGS]])
    cov = float(fit.sigma[2, 2]) * np.linalg.inv(x.T @ x)
    est = [float(fit.intercept[2]), float(fit.coefficients[0][2, 2]), float(fit.coefficients[0][2, 0]), float(fit.coefficients[0][2, 1])]
    se = [float(np.sqrt(cov[0, 0])), float(np.sqrt(cov[3, 3])), float(np.sqrt(cov[1, 1])), float(np.sqrt(cov[2, 2]))]
    names = ["intercept", "ar_1", "real_gdp_growth_lag1", "unemployment_rate_lag1"]
    sign = rv_vs.sensitivity_monotonicity(est, [VAR_EXPECTED_SIGN[n] for n in names], model_id=VAR_MODEL_ID, segment=s.loan_type)
    ols = ols_backcast(s, win)
    quarters = qs[i0: i1 + 1]
    m_var = _peak_metrics(pred, real, quarters, win.fit_end, VAR_MODEL_ID, s.loan_type)
    m_ols = _peak_metrics(ols, real, quarters, win.fit_end, sat.MODEL_ID, s.loan_type)
    ratio = m_var["rmse"] / m_ols["rmse"]
    gap = float(np.max(np.abs(full - ols)))
    return {"fed_loan_type": s.loan_type, "series_id": s.series_id, "link": link_name,
            "fit_window": {"start": qs[i_first], "end": win.fit_end}, "n_obs": int(y.shape[0] - VAR_LAGS),
            "coefficients": [{"name": n, "estimate": e, "std_error": d, "expected_sign": VAR_EXPECTED_SIGN[n]} for n, e, d in zip(names, est, se, strict=True)],
            "sign_check": {"wrong_signs": int(sign.statistic), "offending": [names[i] for i in sign.extras["offending_indices"]], "light": sign.light.value},
            "conditioned_on": ["real_gdp_growth"], "full_conditioning_gap_to_ols": gap,
            "quarters": [{"quarter_end": q, "var": float(a), "ols": float(b), "realised": float(c), "unemployment_var": float(d), "unemployment_realised": float(e)}
                         for q, a, b, c, d, e in zip(quarters, pred, ols, real, out[:, 1], s.x[i0: i1 + 1, 1], strict=True)],
            "metrics": {"var": m_var, "ols": m_ols, "rmse_ratio_var_over_ols": float(ratio)},
            "closer": "var" if ratio < 1.0 else "ols" if ratio > 1.0 else "tie"}


def _pinball(y: np.ndarray, q: np.ndarray, tau: float) -> float:
    d = y - q
    return float(np.mean(np.where(d >= 0.0, tau * d, (tau - 1.0) * d)))


def gar_window(history: pd.DataFrame, win: Window, taus: tuple[float, ...] = GAR_TAUS, horizon: int = GAR_HORIZON) -> dict[str, Any]:
    """The quantile regressions on the train span of the window, and the rolling origins of the episode scored beside the unconditional quantiles."""
    h = history.reset_index(drop=True)
    qs = list(h["quarter_end"])
    i_fit, _i0, i1 = _check_window(qs, win)
    growth = h["real_gdp_growth"].to_numpy(dtype=float)
    spread = (h["treasury_10y"] - h["prime_rate"]).to_numpy(dtype=float)
    x_all = np.column_stack([np.ones(len(qs)), growth, spread])

    def realised(t: int) -> float:
        return float(np.mean(growth[t + 1: t + horizon + 1]))

    train = np.arange(0, i_fit - horizon + 1)            # the target of the last train origin ends at the fit end, never after it
    y_tr = np.array([realised(int(t)) for t in train])
    beta = rv_sm.gar_quantile_regressions(y_tr, x_all[train], taus)
    names = ["intercept", *GAR_REGRESSORS]
    coefs = []
    for tau, b in zip(taus, beta, strict=True):
        sign = rv_vs.sensitivity_monotonicity(list(b), [GAR_EXPECTED_SIGN[n] for n in names], model_id=GAR_MODEL_ID, segment=f"tau-{tau:g}")
        coefs.append({"tau": float(tau), "terms": [{"name": n, "estimate": float(v), "expected_sign": GAR_EXPECTED_SIGN[n]} for n, v in zip(names, b, strict=True)],
                      "sign_check": {"wrong_signs": int(sign.statistic), "offending": [names[i] for i in sign.extras["offending_indices"]], "light": sign.light.value}})
    # the unconditional quantile is the quantile regression on a constant alone (the engine's estimator, not a restated one)
    uncond = rv_sm.gar_quantile_regressions(y_tr, np.ones((y_tr.size, 1)), taus)[:, 0]
    origins = list(range(i_fit, i1 - horizon + 1))
    rows, crossed = [], 0
    for t in origins:
        raw = x_all[t] @ beta.T
        q = np.sort(raw)                                   # rearrangement: crossing quantiles are sorted, and counted
        crossed += int(np.any(np.diff(raw) < 0.0))
        rows.append({"origin": qs[t], "target_end": qs[t + horizon], "realised": realised(t), "quantiles": [float(v) for v in q]})
    y_o = np.array([r["realised"] for r in rows])
    q_o = np.array([r["quantiles"] for r in rows])
    cov, pin = [], []
    for k, tau in enumerate(taus):
        hits = int(np.sum(y_o < q_o[:, k]))
        cov.append({"tau": float(tau), "hits": hits, "n": len(rows), "rate": hits / len(rows)})
        c, u = _pinball(y_o, q_o[:, k], tau), _pinball(y_o, np.full(len(rows), uncond[k]), tau)
        pin.append({"tau": float(tau), "conditional": c, "unconditional": u, "ratio": c / u})
    first = np.array(rows[0]["quantiles"])
    try:
        st = rv_sm.fit_skewed_t_to_quantiles(first, taus)
        skew: dict[str, Any] = {"status": "fitted", "mu": float(st.mu), "sigma": float(st.sigma), "alpha": float(st.alpha), "nu": float(st.nu), "distance": float(st.distance)}
    except (ValueError, OverflowError) as exc:
        # the engine's search overflows when the quantiles are close to a normal's (the degrees of freedom run off): reported, never filled
        skew = {"status": "not-fitted", "reason": f"{type(exc).__name__}: {exc}"}
    return {"window_id": win.window_id, "fit_end": win.fit_end, "train_origins": {"first": qs[int(train[0])], "last": qs[int(train[-1])], "n": int(train.size)},
            "coefficients": coefs, "unconditional_quantiles": [float(v) for v in uncond], "origins": rows, "coverage": cov, "pinball": pin,
            "mean_pinball_ratio": float(np.mean([p["ratio"] for p in pin])), "crossing_origins": crossed, "skewed_t_at_first_origin": skew,
            "first_origin": {"origin": rows[0]["origin"], "realised": rows[0]["realised"], "growth_at_risk_5": rows[0]["quantiles"][0],
                             "below_growth_at_risk": bool(rows[0]["realised"] < rows[0]["quantiles"][0])}}


# ------------------------------------------------------------------------------------------------ the details of the two model records


def _signs_text(var_rows: list[dict[str, Any]], gar: list[dict[str, Any]]) -> tuple[int, int]:
    return sum(r["sign_check"]["wrong_signs"] for r in var_rows), sum(c["sign_check"]["wrong_signs"] for g in gar for c in g["coefficients"])


def build(sats: dict[str, sat.Satellite], history: pd.DataFrame) -> dict[str, Any]:
    """Everything both rungs add to the models document: the per window and loan type VAR back-cast, the growth-at-risk rolling origins, the
    verdicts as counts of the measured values, and the acceptance criterion of the plan stated against them."""
    var_windows, gar_windows = [], []
    for win in WINDOWS:
        rows = [var_backcast(s, win) for s in sats.values()]
        var_windows.append({"window_id": win.window_id, "label": win.label, "fit_end": win.fit_end, "start": win.start, "end": win.end, "per_loan_type": rows})
        gar_windows.append(gar_window(history, win))
    summary = []
    for w in var_windows:
        n = len(w["per_loan_type"])
        wins = sum(1 for r in w["per_loan_type"] if r["closer"] == "var")
        summary.append({"window_id": w["window_id"], "loan_types": n, "var_closer": wins, "ols_closer": n - wins,
                        "sign_checks_red": sum(1 for r in w["per_loan_type"] if r["sign_check"]["light"] != "green")})
    gar_summary = [{"window_id": g["window_id"], "origins": len(g["origins"]), "mean_pinball_ratio": g["mean_pinball_ratio"],
                    "better_than_unconditional": bool(g["mean_pinball_ratio"] < 1.0), "first_origin_realised_below_5": g["first_origin"]["below_growth_at_risk"]}
                   for g in gar_windows]
    leak_free = all(r["metrics"][k]["light"] != "error" for w in var_windows for r in w["per_loan_type"] for k in ("var", "ols"))
    complete = all(len(w["per_loan_type"]) == len(P.FED_TYPES) for w in var_windows) and len(gar_windows) == len(WINDOWS)
    wrong_var, wrong_gar = _signs_text([r for w in var_windows for r in w["per_loan_type"]], gar_windows)
    n_var = sum(len(w["per_loan_type"]) for w in var_windows)
    n_gar = sum(len(g["coefficients"]) for g in gar_windows)
    return {
        "tier": "sota", "var": {"lags": VAR_LAGS, "variables": ["real_gdp_growth", "unemployment_rate", "linked_loss_rate"], "windows": var_windows, "summary": summary},
        "growth_at_risk": {"horizon_quarters": GAR_HORIZON, "taus": [float(t) for t in GAR_TAUS], "regressors": list(GAR_REGRESSORS), "windows": gar_windows, "summary": gar_summary},
        "acceptance": {"leak_free": leak_free, "complete": complete, "sign_checks_reported": True, "var_wrong_signs": wrong_var, "var_sign_checks": n_var,
                       "gar_wrong_signs": wrong_gar, "gar_sign_checks": n_gar,
                       "met": bool(leak_free and complete)},
    }


def statement(block: dict[str, Any]) -> dict[str, str]:
    """The verdict in words, from the measured counts (the numbers are the block's)."""
    out = {}
    for lang in ("en", "es"):
        parts = []
        for s in block["var"]["summary"]:
            win = next(w for w in WINDOWS if w.window_id == s["window_id"])
            if lang == "en":
                parts.append(f"{win.label['en']}: the VAR is closer to the realised rates than the OLS satellite for {s['var_closer']} of {s['loan_types']} loan types")
            else:
                parts.append(f"{win.label['es']}: el VAR queda más cerca de las tasas realizadas que el satélite MCO en {s['var_closer']} de {s['loan_types']} tipos de préstamo")
        for g in block["growth_at_risk"]["summary"]:
            win = next(w for w in WINDOWS if w.window_id == g["window_id"])
            r = ct.number(g["mean_pinball_ratio"], 2, lang=lang)
            if lang == "en":
                verdict = "below" if g["better_than_unconditional"] else "not below"
                parts.append(f"{win.label['en']}: the growth-at-risk quantiles score {r} of the unconditional quantiles' pinball loss over {g['origins']} origins ({verdict} 1)")
            else:
                verdict = "bajo" if g["better_than_unconditional"] else "no bajo"
                parts.append(f"{win.label['es']}: los cuantiles de crecimiento en riesgo puntúan {r} de la pérdida pinball de los cuantiles incondicionales en {g['origins']} orígenes ({verdict} 1)")
        out[lang] = "; ".join(parts) + "."
    return out


def records(engine_version: str, block: dict[str, Any]) -> list[dict[str, Any]]:
    """The two model records the models document adds after the three it had: the details carry the measured block, the tier and the verdict."""
    def rec(mid: str, rung: str, en: str, es: str, short_en: str, short_es: str, params: dict[str, tuple[float, str]], details: dict[str, Any]) -> dict[str, Any]:
        return {"id": mid, "family": "stress", "rung": rung, "title": T(en, es), "short_title": T(short_en, short_es), "engine": "riskvalidation",
                "engine_version": engine_version, "licence": "MIT", "calibration": None, "parameters": {k: {"value": v, "unit": u} for k, (v, u) in params.items()},
                "checkpoint_sha256": None, "details": {"engine_commit": engine_version, "tier": block["tier"], **details}}

    return [
        rec(VAR_MODEL_ID, "var-conditional-forecast", "VAR conditional forecast of the net charge-off rates, back-cast through 2008 to 2009 and 2020",
            "Pronóstico condicional VAR de las tasas de castigo netas, retroproyectado por 2008 a 2009 y 2020", "VAR conditional forecast", "Pronóstico condicional VAR",
            {"lags": (float(VAR_LAGS), "lags")},
            {"var": block["var"], "acceptance": block["acceptance"], "statement": statement(block)}),
        rec(GAR_MODEL_ID, "growth-at-risk-quantile", "Growth-at-risk quantile satellite of the four-quarter real GDP growth, scored on rolling origins through 2008 to 2009 and 2020",
            "Satélite de cuantiles de crecimiento en riesgo del crecimiento del PIB real a cuatro trimestres, evaluado en orígenes móviles por 2008 a 2009 y 2020",
            "Growth-at-risk quantiles", "Cuantiles de crecimiento en riesgo", {"horizon": (float(GAR_HORIZON), "quarters")}, {"growth_at_risk": block["growth_at_risk"]}),
    ]
