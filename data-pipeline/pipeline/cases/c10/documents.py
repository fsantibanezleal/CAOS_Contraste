"""The c10-outputs (loan types and correlation grids) and c10-models documents of C10 from the engine results (CT-1102 to CT-1111).

The fit, the intervals, the profile, the back-test, the IRB comparison and every rung come from ``riskvalidation`` (see ``ladder``
and ``simulator``); this module orders them, names them and writes the bilingual text.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import chi2
from riskvalidation.engines import vasicek
from riskvalidation.portfolio import asrf_fit
from riskvalidation.portfolio import portfolio as pf
from riskvalidation.validation import portfolio as val

from ...core.text import number, percent
from . import fed, ladder, portfolios
from . import params as P
from .ladder import T, named

SHAPED_ON = "yearly default fractions of a large homogeneous portfolio with one systematic factor (dossier 04 C.4)"



#: the two estimators of the correlation in words (frontend/src/workbench/c10/selection.ts ESTIMATOR_TEXT)
ESTIMATOR_WORDS = {"maximum-likelihood": ("maximum-likelihood", "máxima verosimilitud"),
                   "moments": ("method-of-moments", "método de momentos")}

def rv_version() -> str:
    from importlib.metadata import version

    return version("riskvalidation")


def light(res: Any) -> str:
    return getattr(res.light, "value", res.light)


# --- the loan-type document ---------------------------------------------------------------------------------------------------

LOSS_RATE_DEFINITION = T(
    "Net charge-off rate of the Federal Reserve's charge-off release (All Banks, seasonally adjusted), annualised, as a decimal "
    "per year. The annual rate is the mean of the four quarterly rates; a year with a missing quarter has no rate.",
    "Tasa de castigo neta de la publicación de castigos de la Reserva Federal (todos los bancos, ajustada estacionalmente), "
    "anualizada, como decimal por año. La tasa anual es el promedio de las cuatro tasas trimestrales; un año al que le falta "
    "un trimestre no tiene tasa.")
DATA_NOTICE = T(
    "Real outcomes: the Board's published net charge-off rates by loan type. The charge-off rate stands for the portfolio's yearly "
    "loss rate; it is not a default frequency and is net of recoveries. Page " + P.RAW["url"] + ", retrieved " + P.RAW["retrieved"]
    + f" ({P.RAW['bytes']:,} bytes, SHA-256 {P.RAW['sha256']}), last updated by the Board on " + P.RAW["files_as_of"] + ".",
    "Resultados reales: las tasas de castigo netas publicadas por la Reserva Federal por tipo de préstamo. La tasa de castigo "
    "representa la tasa de pérdida anual de la cartera; no es una frecuencia de incumplimiento y es neta de recuperaciones. Página "
    + P.RAW["url"] + ", obtenida el " + P.RAW["retrieved"] + f" ({number(P.RAW['bytes'], 0, lang='es')} bytes, SHA-256 {P.RAW['sha256']}), actualizada por la "
    "Reserva Federal el " + P.RAW["files_as_of"] + ".")


def check_fit_input(years: Any) -> None:
    """A fit is handed fit-window years only: a year from the evaluation window refuses it (CT-1103)."""
    late = [y for y in years if y > P.FIT["last_year"]]
    if late:
        raise ValueError(f"the fit input holds evaluation-window years {late}; the fit window ends in {P.FIT['last_year']}")


def fit_window_rates(rows: list[fed.AnnualRate]) -> np.ndarray:
    """The fit window's yearly rates, NaN for a year without a rate. Only fit-window years are ever passed to a fit."""
    keep = [r for r in rows if r.year <= P.FIT["last_year"]]
    check_fit_input(r.year for r in keep)
    return np.array([np.nan if r.rate is None else r.rate for r in keep])


def evaluation_rates(rows: list[fed.AnnualRate]) -> np.ndarray:
    return np.array([np.nan if r.rate is None else r.rate for r in rows if r.year >= P.EVALUATION["first_year"]])


@dataclass
class Fit:
    """The two fits of a fit-window series with their intervals."""

    ml: asrf_fit.AsrfFit
    moments: asrf_fit.AsrfFit
    ml_ci: dict[str, tuple[float, float]]
    moments_ci: dict[str, tuple[float, float]]
    n_boot: int
    profile: tuple[list[float], list[float], list[float]]
    cutoff: float


def fit_series(fit_rates: np.ndarray, seed: int, n_boot: int) -> Fit:
    """Maximum likelihood with profile-likelihood intervals and the method of moments with parametric-bootstrap intervals.

    Raises ``ValueError`` (the engine's, with its reason) when the series cannot identify the correlation, and
    ``asrf_fit`` intervals that do not contain their estimate are reported rather than edited."""
    ml = asrf_fit.fit_ml(fit_rates)
    mo = asrf_fit.fit_moments(fit_rates)
    ml_ci = asrf_fit.profile_interval(fit_rates, 0.95)
    mo_ci = asrf_fit.bootstrap_interval(fit_rates, "moments", n_boot, seed, 0.95)
    for name, est, ci in (("ml pd", ml.pd, ml_ci["pd"]), ("ml rho", ml.rho, ml_ci["rho"]), ("moments pd", mo.pd, mo_ci["pd"]),
                          ("moments rho", mo.rho, mo_ci["rho"])):
        if not ci[0] <= est <= ci[1]:
            raise ladder.LadderError(f"the {name} interval {ci} does not contain its estimate {est}")
    lo = max(0.002, 0.5 * min(ml_ci["rho"][0], ml.rho))
    hi = min(0.99, max(1.25 * ml_ci["rho"][1] + 0.02, ml.rho * 1.5))
    base = np.round(np.linspace(lo, hi, 41), 6)
    grid = np.array(sorted({float(x) for x in base} | {float(ml.rho)}))
    ll, pd_at = asrf_fit.profile_likelihood(fit_rates, grid)
    cutoff = float(ml.log_likelihood - 0.5 * float(chi2.ppf(0.95, 1)))
    return Fit(ml, mo, ml_ci, mo_ci, n_boot, ([float(x) for x in grid], [float(x) for x in ll], [float(x) for x in pd_at]), cutoff)


def annual_block(rows: list[fed.AnnualRate], pd: float, rho: float) -> list[dict[str, Any]]:
    q99, q999 = vasicek.lhp_quantile(0.99, pd, rho), vasicek.lhp_quantile(0.999, pd, rho)
    out = []
    for r in rows:
        window = "fit" if r.year <= P.FIT["last_year"] else "evaluation"
        if r.rate is None:
            out.append({"year": r.year, "window": window, "n_quarters": r.n_quarters, "loss_rate": None, "reason": r.reason,
                        "fitted_cdf": None, "implied_factor": None, "exceeds_99": None, "exceeds_999": None})
            continue
        z = float(asrf_fit.implied_factors(np.array([r.rate]), pd, rho)[0])
        out.append({"year": r.year, "window": window, "n_quarters": 4, "loss_rate": r.rate, "reason": None,
                    "fitted_cdf": vasicek.lhp_cdf(r.rate, pd, rho), "implied_factor": z, "exceeds_99": bool(r.rate > q99),
                    "exceeds_999": bool(r.rate > q999)})
    return out


def missing_quarters(table: fed.Table, loan_type: str, rows: list[fed.AnnualRate]) -> list[dict[str, str]]:
    """One entry per year that lacks a quarter (the contract's cross-field check compares them year by year): the first
    missing quarter, with the reason naming every missing quarter of the year."""
    out = []
    for r in rows:
        if r.n_quarters < 4:
            out.append({"quarter": r.missing[0], "reason": r.reason if len(r.missing) == 1 else
                        f"{', '.join(r.missing)}: the Board's table marks them n.a. for this loan type; never interpolated"})
    return out


def backtest_block(realised: np.ndarray, pd: float, rho: float) -> tuple[dict[str, Any], dict[str, Any]]:
    """The engine's tail back-test: one call per level (the light of a level is the engine's, at that level as primary)."""
    rows = []
    primary = None
    for lv in P.BACKTEST_LEVELS:
        res = val.tail_backtest(realised, pd, rho, P.BACKTEST_LEVELS, primary_level=lv, model_id="m-lhp")
        if lv == 0.99:
            primary = res
        if res.light == "not_evaluated" or getattr(res.light, "value", None) == "not_evaluated":
            raise ladder.LadderError("the tail back-test found no evaluation year")
        e = next(x for x in res.extras["levels"] if math.isclose(x["level"], lv))
        rows.append({"level": lv, "fitted_quantile": e["fitted_quantile"], "expected_exceedances": e["expected"],
                     "observed_exceedances": e["observed"],
                     "years_exceeding": [P.EVALUATION["first_year"] + int(i) for i in e["years_exceeding"]],
                     "p_value_upper": e["p_value"], "light": light(res)})
    n_eval = int(np.sum(~np.isnan(realised)))
    return {"n_years_evaluated": n_eval, "rows": rows}, primary.to_dict()


def irb_block(lt: dict[str, Any], pd: float, rho: float) -> dict[str, Any]:
    res = ladder.irb_k(lt, pd)
    ma = res.maturity_adjustment
    ec_unit = pf.lhp_measures(1.0, P.LGD, pd, rho, (0.999,))[0].ec
    ec = ec_unit * (1.0 if ma is None else ma)
    return {"regime": P.IRB_REGIME, "asset_class": lt["irb_asset_class"], "reference": lt["irb_reference"], "pd": pd, "lgd": P.LGD,
            "maturity": res.maturity, "maturity_adjustment": ma, "irb_correlation": res.correlation, "fitted_correlation": rho,
            "k_irb": res.k, "ec_lhp_fitted": ec, "ratio_fitted_to_irb": ec / res.k}


def fitted_distribution(pd: float, rho: float, top: float) -> dict[str, Any]:
    lo = vasicek.lhp_quantile(0.001, pd, rho)
    hi = max(vasicek.lhp_quantile(0.9995, pd, rho), top * 1.15)
    x = np.round(np.linspace(lo, hi, 80), 10)
    return {"pd": pd, "rho": rho,
            "curve": {"x": [float(v) for v in x], "pdf": [vasicek.lhp_pdf(float(v), pd, rho) for v in x],
                      "cdf": [vasicek.lhp_cdf(float(v), pd, rho) for v in x]},
            "quantiles": [{"level": lv, "value": vasicek.lhp_quantile(lv, pd, rho)} for lv in P.QUANTILE_LEVELS]}


#: the Spanish short titles of the rungs where the English one is not also Spanish (U16-R2: "Gaussian 1F" in a Spanish table)
SHORT_ES = {"Gaussian 1F": "Gaussiana 1F", "Gaussian MF": "Gaussiana MF", "Student-t": "t de Student"}


def model_summary(mid: str, rung: str, title: dict[str, str], short: str, engine: str, rv: str) -> dict[str, Any]:
    return {"id": mid, "family": "portfolio-credit-capital", "rung": rung, "title": title, "short_title": T(short, SHORT_ES.get(short, short)),
            "engine": engine, "engine_version": rv, "licence": "BSD-3-Clause", "calibration": None, "parameters": {},
            "checkpoint_sha256": None}


MODEL_IDS: tuple[tuple[str, str, dict[str, str], str, str], ...] = (
    ("m-lhp", "C1", T("Large homogeneous portfolio (Vasicek)", "Cartera homogénea grande (Vasicek)"), "LHP",
     "riskvalidation.portfolio.portfolio.lhp_measures"),
    ("m-gaussian-1f", "C2", T("Gaussian copula, one factor", "Cópula gaussiana, un factor"), "Gaussian 1F",
     "riskvalidation.portfolio.copula.simulate_gaussian"),
    ("m-gaussian-mf", "C2", T("Gaussian copula, sector factors", "Cópula gaussiana, factores sectoriales"), "Gaussian MF",
     "riskvalidation.portfolio.copula.simulate_gaussian"),
    ("m-student-t", "C3", T("Student-t copula", "Cópula t de Student"), "Student-t",
     "riskvalidation.portfolio.copula.simulate_student_t"),
    ("m-creditrisk-plus", "C4", T("CreditRisk+ (stable recursion)", "CreditRisk+ (recursión estable)"), "CreditRisk+",
     "riskvalidation.portfolio.creditrisk_plus.pmf_stable"),
)


def summaries(rv: str, pd: float, rho: float) -> list[dict[str, Any]]:
    out = []
    for mid, rg, title, short, engine in MODEL_IDS:
        m = model_summary(mid, rg, title, short, engine, rv)
        if mid == "m-lhp":
            m["parameters"] = {"pd": {"value": pd, "unit": "decimal"}, "rho": {"value": rho, "unit": "-"}}
        out.append(m)
    return out


def pct(x: float) -> str:
    """A share as a percent in an English text, as the shell writes it ("1.77 %", a no-break space before the sign; R4 c12 n7)."""
    return percent(x, 2, lang="en")


def pct_es(x: float) -> str:
    """``pct`` as a Spanish text writes it (decimal comma, no-break space before the sign)."""
    return percent(x, 2, lang="es")


def _n(x: float, decimals: int) -> str:
    """A number inside a Spanish text, as the shell writes it."""
    return number(x, decimals, lang="es")


def _g(x: float) -> str:
    """``:g`` in Spanish: 5, 0,12."""
    for decimals in range(7):
        if round(x, decimals) == x:
            return number(x, decimals, lang="es")
    return number(x, 6, lang="es")


def _p3(p: float, lang: str) -> str:
    """A p-value with three decimals in the language, or "below 0.001" when three decimals would print 0.000 (R3 c11 n6)."""
    if p < 0.0005:
        return "below 0.001" if lang == "en" else f"menor que {number(0.001, 3, lang='es')}"
    return number(p, 3, lang=lang)


def _signed(x: float, decimals: int) -> str:
    return ("+" if x >= 0 else "") + number(x, decimals, lang="es")


def loan_type_document(lt: dict[str, Any], table: fed.Table, run: ladder.Run, n_boot: int, rv: str,
                       log=lambda _m: None) -> dict[str, Any]:
    """The ``outputs``, ``tests``, ``impact``, ``findings`` and ``model`` of one loan type, and the numbers the models document and
    the case page reuse (``extras``)."""
    rows = fed.annual_rates(table, lt["id"], P.FIT["first_year"], P.EVALUATION["last_year"])
    fit_rates, ev_rates = fit_window_rates(rows), evaluation_rates(rows)
    fit = fit_series(fit_rates, P.SEEDS["bootstrap"], n_boot)
    pd, rho = fit.ml.pd, fit.ml.rho
    log(f"{lt['id']}: ML pd {pd:.5f} rho {rho:.4f}; moments rho {fit.moments.rho:.4f}")
    annual = annual_block(rows, pd, rho)
    backtest, bt_test = backtest_block(ev_rates, pd, rho)
    irb_ref = irb_block(lt, pd, rho)
    groups = portfolios.groups(lt["id"], pd, rho, run.thin)
    lad = ladder.run_ladder(lt, pd, rho, groups, run)
    gran = lad.granularity
    omega = gran.pop("omega_mix")
    grid_rho, grid_ll, grid_pd = fit.profile
    top = max([r.rate for r in rows if r.rate is not None] + [pd])
    ml = {"pd": {"estimate": pd, "ci_low": fit.ml_ci["pd"][0], "ci_high": fit.ml_ci["pd"][1]},
          "rho": {"estimate": rho, "ci_low": fit.ml_ci["rho"][0], "ci_high": fit.ml_ci["rho"][1]},
          "log_likelihood": fit.ml.log_likelihood, "converged": bool(fit.ml.converged), "interval_method": "profile-likelihood",
          "level": 0.95}
    mo = {"pd": {"estimate": fit.moments.pd, "ci_low": fit.moments_ci["pd"][0], "ci_high": fit.moments_ci["pd"][1]},
          "rho": {"estimate": fit.moments.rho, "ci_low": fit.moments_ci["rho"][0], "ci_high": fit.moments_ci["rho"][1]},
          "interval_method": "parametric-bootstrap", "n_bootstrap": n_boot, "level": 0.95}
    port = {"label": "illustrative", "notice": portfolios.NOTICE, "currency": P.CURRENCY, "n_names": lad.portfolio["n_names"],
            "total_ead": lad.portfolio["total_ead"], "groups": groups, "lgd_mean": P.LGD, "lgd_gamma": P.LGD_GAMMA,
            "levels": list(P.LEVELS), "horizon_years": 1, "calibration": {"pd": pd, "rho": rho, "source": "fit-maximum-likelihood"},
            "hhi": lad.portfolio["hhi"], "effective_names": lad.portfolio["effective_names"],
            "largest_share": lad.portfolio["largest_share"]}
    missing = missing_quarters(table, lt["id"], rows)
    out = {
        "kind": "loan-type", "loan_type": lt["id"], "label": lt["label"], "currency": P.CURRENCY,
        "loss_rate_definition": LOSS_RATE_DEFINITION, "windows": {"fit": dict(P.FIT), "evaluation": dict(P.EVALUATION)},
        "data_status": {"source": P.RAW["source"], "table": P.RAW["table"],
                        "series": f"{fed.HEADINGS[fed.COLUMNS[lt['id']]]} (column {fed.COLUMNS[lt['id']]} of the table)",
                        "seasonal_adjustment": "SA", "bank_scope": "all-banks", "files_as_of": P.RAW["files_as_of"],
                        "quarters_expected": P.QUARTERS_EXPECTED, "missing_quarters": missing, "notice": DATA_NOTICE},
        "annual_rates": annual,
        "fit": {"n_years_used": int(np.sum(~np.isnan(fit_rates))), "maximum_likelihood": ml, "moments": mo},
        "profile_likelihood": {"level": 0.95, "rho": grid_rho, "log_likelihood": grid_ll, "pd_at_rho": grid_pd,
                               "max_log_likelihood": fit.ml.log_likelihood, "cutoff": fit.cutoff},
        "fitted_distribution": fitted_distribution(pd, rho, top), "backtest": backtest, "irb_reference": irb_ref,
        "portfolio": port, "rungs": lad.rungs, "granularity": gran, "euler": lad.euler}
    tests = [bt_test, *lad.tests]
    by_id = {r["id"]: r for r in lad.rungs}
    impact, findings = impact_and_findings(lt, out, by_id, tests, omega)
    log(f"{lt['id']}: ladder done, {len(tests)} test rows")
    return {"outputs": out, "tests": tests, "impact": impact, "findings": findings, "model": summaries(rv, pd, rho),
            "extras": {"pd": pd, "rho": rho, "omega": omega, "diagnostics": lad.diagnostics}}


# --- impact and findings -------------------------------------------------------------------------------------------------------


def _rung_var(by_id: dict[str, Any], rid: str, level: float) -> float:
    return next(m["var"] for m in by_id[rid]["measures"] if m["level"] == level)


def impact_and_findings(lt: dict[str, Any], out: dict[str, Any], by_id: dict[str, Any], tests: list[dict[str, Any]],
                        omega: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    i = out["irb_reference"]
    v1, v2, v3 = (_rung_var(by_id, r, 0.999) for r in ("c1-lhp", "c2-gaussian-1f", "c3-student-t"))
    v4, v5 = _rung_var(by_id, "c4-creditrisk-plus", 0.999), _rung_var(by_id, "c5-granularity", 0.999)
    ga999 = next(x for x in out["granularity"]["levels"] if x["q"] == 0.999)
    bt99 = next(r for r in out["backtest"]["rows"] if r["level"] == 0.99)
    n_years_evaluated = out["backtest"]["n_years_evaluated"]
    label = lt["label"]
    imp = {
        "ec_lhp_999_share": {"value": i["ec_lhp_fitted"], "unit": "share of EAD",
                             "label": T("LHP capital at 99.9 % with the fitted correlation", "Capital LHP al 99,9 % con la correlación ajustada")},
        "ec_ratio_fitted_to_irb": {"value": i["ratio_fitted_to_irb"], "unit": "ratio",
                                   "label": T("Fitted capital over IRB capital", "Capital ajustado sobre capital IRB")},
        "var_999_gaussian_over_lhp": {"value": v2 / v1, "unit": "ratio",
                                      "label": T("Gaussian copula VaR over LHP VaR, 99.9 %", "VaR de la cópula gaussiana sobre el VaR LHP, 99,9 %")},
        "var_999_student_t_over_gaussian": {"value": v3 / v2, "unit": "ratio",
                                            "label": T("Student-t copula VaR over Gaussian copula VaR, 99.9 %",
                                                       "VaR de la cópula t sobre el de la cópula gaussiana, 99,9 %")},
        "ga_999_share": {"value": ga999["ga"], "unit": "share of EAD",
                         "label": T("Granularity adjustment at 99.9 %", "Ajuste por granularidad al 99,9 %")},
        "tail_exceedances_99": {"value": float(bt99["observed_exceedances"]), "unit": "years",
                                "label": T("Evaluation years above the fitted 99 % quantile", "Años de evaluación sobre el cuantil 99 % ajustado")},
    }
    tid = {t["test_id"] + "@" + str(t["model_id"]) + (("@" + t["segment"]) if t["segment"] else "") for t in tests}
    find = []
    rho_ml = out["fit"]["maximum_likelihood"]["rho"]
    ratio = i["ratio_fitted_to_irb"]
    find.append({"id": "f-c10-correlation", "severity": "S3" if not 0.8 <= ratio <= 1.25 else "S4",
                 "status": "open" if not 0.8 <= ratio <= 1.25 else "accepted", "evidence": ["design:irb-reference-block"],
                 "title": T(f"{label['en']}: the fitted asset correlation is {rho_ml['estimate']:.3f} (95 % interval {rho_ml['ci_low']:.3f} to "
                            f"{rho_ml['ci_high']:.3f}) against the IRB's {i['irb_correlation']:.3f}; the LHP capital at 99.9 % is {ratio:.2f} "
                            "times the IRB capital",
                            f"{label['es']}: la correlación de activos ajustada es {_n(rho_ml['estimate'], 3)} (intervalo al 95 % de "
                            f"{_n(rho_ml['ci_low'], 3)} a {_n(rho_ml['ci_high'], 3)}) frente a {_n(i['irb_correlation'], 3)} de IRB; el capital "
                            f"LHP al 99,9 % es {_n(ratio, 2)} veces el capital IRB")})
    sev = {"green": ("S4", "accepted"), "amber": ("S3", "open"), "red": ("S2", "open")}[bt99["light"]]
    find.append({"id": "f-c10-tail", "severity": sev[0], "status": sev[1], "evidence": ["portfolio.tail_backtest@m-lhp"],
                 "title": T(f"{bt99['observed_exceedances']} of {out['backtest']['n_years_evaluated']} evaluation years "
                            f"({', '.join(map(str, bt99['years_exceeding'])) or 'none'}) lie above the fitted 99 % quantile "
                            f"{pct(bt99['fitted_quantile'])}; {bt99['expected_exceedances']:.2f} are expected (upper binomial tail "
                            f"{_p3(bt99['p_value_upper'], 'en')})",
                            f"{bt99['observed_exceedances']} de {n_years_evaluated} años de evaluación "
                            f"({', '.join(map(str, bt99['years_exceeding'])) or 'ninguno'}) quedan sobre el cuantil 99 % ajustado "
                            f"{pct_es(bt99['fitted_quantile'])}; se esperan {_n(bt99['expected_exceedances'], 2)} (cola binomial superior "
                            f"{_p3(bt99['p_value_upper'], 'es')})")})
    find.append({"id": "f-c10-tail-dependence", "severity": "S3" if v3 / v2 > 1.1 else "S4", "status": "open" if v3 / v2 > 1.1 else "accepted",
                 "evidence": ["design:copula-ladder"],
                 "title": T(f"At 99.9 % the Student-t copula (ν {P.NU:g}) VaR is {v3 / v2:.2f} times the Gaussian copula's on the same "
                            f"correlation, and CreditRisk+ is {v4 / v2:.2f} times",
                            f"Al 99,9 % el VaR de la cópula t (ν {_g(P.NU)}) es {_n(v3 / v2, 2)} veces el de la cópula gaussiana con la misma "
                            f"correlación, y CreditRisk+ es {_n(v4 / v2, 2)} veces")})
    ga_rel = (v5 - v1) / v1
    find.append({"id": "f-c10-granularity", "severity": "S3" if ga_rel > 0.03 else "S4", "status": "open" if ga_rel > 0.03 else "accepted",
                 "evidence": ["design:granularity-adjustment"],
                 "title": T(f"The granularity adjustment adds {pct(ga999['ga'])} of EAD ({percent(ga_rel, 1, lang='en')} of the LHP VaR) at 99.9 % on a portfolio "
                            f"of {out['portfolio']['n_names']:,} names with {number(out['portfolio']['effective_names'], 0, lang='en')} effective names",
                            f"El ajuste por granularidad suma {pct_es(ga999['ga'])} de la EAD ({percent(ga_rel, 1, lang='es')} del VaR LHP) al 99,9 % en una "
                            f"cartera de {number(out['portfolio']['n_names'], 0, lang='es')} nombres con {number(out['portfolio']['effective_names'], 0, lang='es')} nombres efectivos")})
    for tname, fid in (("portfolio.mc_convergence@m-gaussian-1f@lhp-like-99.9", "f-c10-mc"), ("portfolio.crp_recursion_vs_mc@m-creditrisk-plus", "f-c10-crp")):
        t = next(x for x in tests if f"{x['test_id']}@{x['model_id']}" + (f"@{x['segment']}" if x["segment"] else "") == tname)
        assert tname in tid
        s = {"green": ("S4", "accepted"), "amber": ("S3", "open"), "red": ("S2", "open"), "not_evaluated": ("S3", "open"),
             "error": ("S2", "open")}[t["light"]]
        if fid == "f-c10-mc":
            title = T(f"The 99.9 % Monte Carlo VaR of a portfolio of many identical names is {t['statistic']:+.1f} standard errors from the "
                      "analytic LHP quantile",
                      f"El VaR al 99,9 % de Monte Carlo de una cartera de muchos nombres idénticos está a {_signed(t['statistic'], 1)} errores "
                      "estándar del cuantil LHP analítico")
        else:
            title = T(f"The CreditRisk+ recursion is at Kolmogorov distance {t['statistic']:.4f} from a Monte Carlo of the same model",
                      f"La recursión de CreditRisk+ está a distancia de Kolmogorov {_n(t['statistic'], 4)} de un Monte Carlo del mismo modelo")
        find.append({"id": fid, "severity": s[0], "status": s[1], "evidence": [tname], "title": title})
    return imp, find


# --- the correlation-grid documents ------------------------------------------------------------------------------------------------

GRID_NOTICE = T(
    "Synthetic data: yearly default fractions of a large homogeneous portfolio drawn with a known asset correlation, not observations. "
    "Every estimate is shown beside the correlation it should recover.",
    "Datos sintéticos: fracciones anuales de incumplimiento de una cartera homogénea grande simuladas con una correlación de activos "
    "conocida, no observaciones. Cada estimación se muestra junto a la correlación que debe recuperar.")
SIZE_POWER_DEFINITION = T(
    "Size is the rate at which H0 (the asset correlation equals the correlation under the null) is rejected when the known correlation "
    "is the correlation under the null; power is the same rate at any other known correlation. H0 is rejected when the correlation "
    "under the null lies outside the 95 % interval of the estimator.",
    "El tamaño es la tasa de rechazo de H0 (la correlación de activos es la correlación bajo la nula) cuando la correlación conocida es "
    "la correlación bajo la nula; la potencia es la misma tasa con otra correlación conocida. H0 se rechaza cuando la correlación bajo "
    "la nula queda fuera del intervalo al 95 % del estimador.")


def grid_document(years: int, cells_and_rows: list[tuple[dict[str, Any], list[dict[str, Any]]]], n_replications: int,
                  rv: str) -> dict[str, Any]:
    cells = [c for c, _ in cells_and_rows]
    tests = [row for _, rows in cells_and_rows for row in rows]
    size = next(c for c in cells if c["role"] == "size")
    ml = size["estimators"][0]
    return {
        "outputs": {"kind": "correlation-grid",
                    "label": T(f"Correlation grid, {years} years", f"Grilla de correlaciones, {years} años"),
                    "generator": {"name": "vasicek-lhp-simulator", "shaped_on": SHAPED_ON, "known_pd": P.KNOWN_PD,
                                  "rho_grid": list(P.RHO_GRID), "series_length_years": years, "n_replications": n_replications,
                                  "null_rho": P.NULL_RHO, "alpha": P.ALPHA, "seed": P.SIM_SEED, "notice": GRID_NOTICE},
                    "size_power_definition": SIZE_POWER_DEFINITION, "cells": cells},
        "tests": tests,
        "impact": {"size_ml": {"value": ml["rejection_rate"], "unit": "rate",
                               "label": T("Size of the maximum-likelihood test", "Tamaño de la prueba de máxima verosimilitud")},
                   "size_moments": {"value": size["estimators"][1]["rejection_rate"], "unit": "rate",
                                    "label": T("Size of the method-of-moments test", "Tamaño de la prueba de método de momentos")}},
        "model": [model_summary("m-lhp", "C1", MODEL_IDS[0][2], "LHP", MODEL_IDS[0][4], rv)],
    }


def grid_findings(doc: dict[str, Any]) -> list[dict[str, Any]]:
    cells = doc["outputs"]["cells"]
    size = next(c for c in cells if c["role"] == "size")
    years = doc["outputs"]["generator"]["series_length_years"]
    f = []
    for e in size["estimators"]:
        row = next(t for t in doc["tests"] if t["extras"].get("role") == "size" and t["extras"].get("estimator") == e["estimator"])
        sev = {"green": ("S4", "accepted"), "amber": ("S3", "open"), "red": ("S2", "open")}.get(row["light"], ("S3", "open"))
        f.append({"id": f"f-c10-size-{e['estimator']}-{years}", "severity": sev[0], "status": sev[1],
                  "evidence": [f"portfolio.correlation_size_power@m-lhp@rho={size['known_rho']:g}/{e['estimator']}"],
                  # the estimator in words, never its id (the raw-id scan of 2026-10-24)
                  "title": T(f"With {years} years the {ESTIMATOR_WORDS[e['estimator']][0]} test of ρ = {P.NULL_RHO:g} rejects {e['rejection_rate']:.3f} of the "
                             f"time when it is true (nominal {P.ALPHA:g}; interval {e['rejection_ci_low']:.3f} to {e['rejection_ci_high']:.3f})",
                             f"Con {years} años la prueba de {ESTIMATOR_WORDS[e['estimator']][1]} de ρ = {_g(P.NULL_RHO)} rechaza {_n(e['rejection_rate'], 3)} de las "
                             f"veces cuando es verdadera (nominal {_g(P.ALPHA)}; intervalo {_n(e['rejection_ci_low'], 3)} a {_n(e['rejection_ci_high'], 3)})")})
    return f


# --- the models document ---------------------------------------------------------------------------------------------------------


def models_document(table_columns: dict[str, str], example: dict[str, Any], run: ladder.Run, n_replications: int) -> dict[str, Any]:
    """The ``fit`` block of the c10-models document: loan types, estimators, ladder, the portfolio specification, granularity, simulator."""
    ladder_rows = []
    chunk_free = None
    spec = [
        ("c1-lhp", "C1", "lhp-vasicek", "analytic", chunk_free, "riskvalidation.portfolio.portfolio.lhp_measures",
         "Vasicek (2002), Risk, December 2002; dossier 04 C.4", [named("pd", example["pd"], "decimal"), named("rho", example["rho"], "-")]),
        ("c2-gaussian-1f", "C2", "gaussian-copula-one-factor", "monte-carlo", run.n_scenarios,
         "riskvalidation.portfolio.copula.simulate_gaussian", "Li (2000); dossier 04 H.3", [named("lgd", P.LGD, "decimal")]),
        ("c2-gaussian-mf", "C2", "gaussian-copula-multi-factor", "monte-carlo", run.n_scenarios,
         "riskvalidation.portfolio.copula.simulate_gaussian", "Li (2000); dossier 04 H.3",
         [named("n_factors", 2, "-"), named("factor_correlation", P.SECTOR_CORRELATION, "-")]),
        ("c3-student-t", "C3", "student-t-copula", "monte-carlo", run.n_scenarios, "riskvalidation.portfolio.copula.simulate_student_t",
         "Frey and McNeil (2003); Demarta and McNeil (2005); dossier 04 H.3", [named("nu", P.NU, "-")]),
        ("c4-creditrisk-plus", "C4", "creditrisk-plus", "analytic", chunk_free, "riskvalidation.portfolio.creditrisk_plus.pmf_stable",
         "Haaf, Reiss and Schoenmakers (2004); dossier 04 H.4", [named("loss_unit", P.LOSS_UNIT, P.CURRENCY)]),
        ("c5-granularity", "C5", "granularity-adjustment", "analytic", chunk_free,
         "riskvalidation.portfolio.granularity.granularity_adjustment", "Gordy and Lutkebohmert (2013); dossier 04 H.5",
         [named("xi", P.XI, "-"), named("gamma", P.LGD_GAMMA, "-")]),
        ("c6-is-gaussian", "C6", "importance-sampling", "monte-carlo", run.n_is, "riskvalidation.portfolio.importance.importance_sample_gaussian",
         "Glasserman and Li (2005); dossier 04 H.7 (the twist is UNVERIFIED there; acceptance is unbiasedness against plain Monte Carlo)", []),
        ("c6-is-student-t", "C6", "importance-sampling", "monte-carlo", run.n_is,
         "riskvalidation.portfolio.importance.importance_sample_gaussian",
         "Glasserman and Li (2005); no Student-t twist is specified, so the rung does not run", []),
    ]
    labels = {r["id"]: r["label"] for r in example["rungs"]}
    # whether the rung runs: the loan variants evaluate the same rungs, so the example's flag is the ladder's (R2b c11 B4: a grid,
    # which carries no rungs, drew the planned 100,000 scenarios of the Student-t importance sampler that never runs)
    evaluated = {r["id"]: bool(r["evaluated"]) for r in example["rungs"]}
    for rid, rg, method, est, n, fn, ref, params in spec:
        ladder_rows.append({"id": rid, "rung": rg, "method": method, "label": labels[rid], "estimator": est, "n_scenarios": n,
                            "evaluated": evaluated[rid],
                            "engine_function": fn, "reference": ref, "parameters": params})
    return {
        "currency": P.CURRENCY, "windows": {"fit": dict(P.FIT), "evaluation": dict(P.EVALUATION)},
        "loan_types": [{"id": lt["id"], "label": lt["label"], "table_column": table_columns[lt["id"]],
                        "irb_asset_class": lt["irb_asset_class"], "irb_reference": lt["irb_reference"]} for lt in P.LOAN_TYPES],
        "estimators": [
            {"id": "maximum-likelihood", "label": T("Maximum likelihood", "Máxima verosimilitud"),
             "engine_function": "riskvalidation.portfolio.asrf_fit.fit_ml", "interval_method": "profile-likelihood",
             "reference": "Vasicek (2002); dossier 04 C.4"},
            {"id": "moments", "label": T("Method of moments", "Método de momentos"),
             "engine_function": "riskvalidation.portfolio.asrf_fit.fit_moments", "interval_method": "parametric-bootstrap",
             "reference": "dossier 04 C.4 (E[L^2] = joint default probability)"}],
        "ladder": ladder_rows,
        "portfolio_spec": {
            "label": "illustrative",
            "notice": T(f"Illustrative portfolio: the groups shown are those of {example['label']['en'].lower()}; every loan type has its "
                        "own groups in its document. Constructed for the case, never a bank's.",
                        f"Cartera ilustrativa: los grupos mostrados son los de {example['label']['es'].lower()}; cada tipo de préstamo "
                        "tiene sus propios grupos en su documento. Construida para el caso, nunca la de un banco."),
            "currency": P.CURRENCY, "groups": example["groups"], "lgd_mean": P.LGD, "lgd_gamma": P.LGD_GAMMA, "levels": list(P.LEVELS),
            "horizon_years": 1},
        "granularity": {"xi": P.XI, "gamma": P.LGD_GAMMA, "k_source": "irb-regulatory-correlation", "xi_reference": 0.25,
                        "q_reference": 0.999, "delta_reference": 4.83,
                        "reference": "Gordy and Lutkebohmert (2013), eq. 15 and eq. 16 (dossier 04 H.5)"},
        "simulator": {"known_pd": P.KNOWN_PD, "rho_grid": list(P.RHO_GRID), "series_lengths_years": list(P.SERIES_LENGTHS),
                      "n_replications": n_replications, "null_rho": P.NULL_RHO, "alpha": P.ALPHA, "seed": P.SIM_SEED},
    }
