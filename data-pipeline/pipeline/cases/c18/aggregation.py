"""The aggregation of the four marginals: the simple sum is the headline capital, every other figure is information (05 l.519).

Every number is ``riskvalidation.aggregation`` (``dependence_band``: the lower bound, the simple sum, variance-covariance, the Gaussian
copula, the t copula at each nu of the set and the worst case, all over the same marginals at one year and 99.9 percent; the Euler
allocation of the aggregate expected shortfall through ``portfolio.euler``; ``model_risk``; ``simple``) or
``riskvalidation.validation.aggregation`` (the tests of G.5). This module only maps the engine's dataclasses onto the document block.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.aggregation import band as rv_band
from riskvalidation.aggregation import copulas as rv_cop
from riskvalidation.aggregation import model_risk as rv_mr
from riskvalidation.aggregation import simple as rv_simple
from riskvalidation.portfolio import euler as rv_euler
from riskvalidation.portfolio import portfolio as rv_port
from riskvalidation.validation import aggregation as rv_va
from riskvalidation.validation import portfolio as rv_vp
from scipy import stats

from . import params as P
from .marginals import Marginal

T = P.text
INFO = T("Information, not capital: a diversified or bound figure shown for the validator")
HEADLINE = T("Headline capital: the simple sum of the four marginals")
MODEL_ID = "c18-aggregation-ladder"


@dataclass(frozen=True)
class AggregationResult:
    block: dict[str, Any]
    band: rv_band.Band
    tests: list[Any]                  # TestResult objects of the band-level tests (without the stress pair)
    ec: np.ndarray
    gaussian: float
    euler_total: float


def marginal_block(m: Marginal, named: dict[str, dict[str, Any]]) -> dict[str, Any]:
    undefined = m.el is None
    return {
        "risk": m.risk, "horizon_years": P.HORIZON_YEARS, "confidence_level": P.LEVEL, "el_clp_m": m.el,
        "el_status": "undefined (infinite mean)" if undefined else "finite", "var_clp_m": m.var, "es_clp_m": m.es, "ec_clp_m": m.ec,
        "ec_basis": "var-alone-infinite-mean" if undefined else "var-less-el",
        "ec_label": T("The severity has an infinite mean (xi of 1 or more): the expected loss is undefined, so the EC is the VaR alone (05 l.482)") if undefined else None,
        "var_se_clp_m": m.var_se, "producer": m.producer, "source_documents": m.source_documents,
        "scaling": {"statement": m.statement, "parameters": [named[p] for p in m.parameters]}}


def run_band(marginals: list[Marginal], corr: list[list[float]], nu_set: tuple[float, ...] = P.NU_SET, n_draws: int = P.N_DRAWS,
             seed: int = P.SEED) -> rv_band.Band:
    ppfs = [m.ppf for m in marginals]
    ec = np.array([m.ec for m in marginals])
    el = np.array([m.el_for_aggregate for m in marginals])
    return rv_band.dependence_band(ppfs, ec, el, np.array(corr), list(nu_set), level=P.LEVEL, horizon_years=P.HORIZON_YEARS, n_draws=n_draws, seed=seed,
                                   chunk_size=min(P.CHUNK, n_draws), bounds_n=min(P.BOUNDS_N, n_draws), bounds_epsilon=P.BOUNDS_EPSILON, ec_consistency_tolerance=P.EC_TOLERANCE)


def band_rows(band: rv_band.Band) -> list[dict[str, Any]]:
    out = []
    for r in band.rows:
        out.append({"method": r.method, "nu": r.nu, "capital_clp_m": r.capital, "diversification_factor": r.diversification_factor,
                    "status": r.status, "label": HEADLINE if r.method == "simple-sum" else INFO, "horizon_years": band.horizon_years,
                    "confidence_level": band.confidence_level, "mc_se_clp_m": r.mc_se})
    return out


def _row(band: rv_band.Band, method: str, nu: float | None = None) -> rv_band.BandRow:
    return next(r for r in band.rows if r.method == method and (method != "t-copula" or r.nu == nu))


def euler_and_risk(marginals: list[Marginal], corr: list[list[float]], band: rv_band.Band, n_draws: int = P.N_DRAWS, seed: int = P.SEED
                   ) -> tuple[dict[str, Any], dict[str, Any], Any, float]:
    """The Euler allocation of the Gaussian aggregate's expected shortfall, the diversification, and the model risk measures."""
    ppfs = [m.ppf for m in marginals]
    joint = rv_cop.simulate_component_losses(ppfs, np.array(corr), "gaussian", None, n_draws, seed, min(P.CHUNK, n_draws))
    total = joint.sum(axis=1)
    es_total = rv_port.es_from_sample(total, P.LEVEL)
    contrib = rv_euler.es_contributions(joint, total, P.LEVEL)
    add = rv_vp.euler_additivity(contrib, es_total, 1e-6, model_id=MODEL_ID)
    s = float(contrib.sum())
    rel = abs(s - es_total) / es_total if es_total else 0.0
    risks = [m.risk for m in marginals]
    euler = {"status": "information-not-capital", "label": T("Information, not capital: an allocation of the aggregate expected shortfall shown for the validator"),
             "risk_measure": "es", "level": P.LEVEL, "horizon_years": P.HORIZON_YEARS, "copula": {"family": "gaussian", "nu": None},
             "es_total_clp_m": es_total,
             "allocation": [{"risk": r, "contribution_clp_m": float(c), "share": float(c) / es_total} for r, c in zip(risks, contrib, strict=True)],
             "additivity": {"sum_clp_m": s, "relative_error": rel, "tolerance": 1e-6}}
    gauss = _row(band, "gaussian-copula")
    benefit = {"status": "information-not-capital",
               "label": T("Information, not capital: the diversification of the Gaussian copula row against the simple sum"),
               "reference_row": {"method": "gaussian-copula", "nu": None}, "factor": gauss.diversification_factor,
               "benefit": 1.0 - gauss.diversification_factor,
               "euler_benefit_by_risk": [{"risk": r, "benefit": rv_simple.euler_diversification_benefit(float(c), m.es)}
                                         for r, c, m in zip(risks, contrib, marginals, strict=True)]}
    # the loss function of the Glasserman and Xu measure: the aggregate loss of the Gaussian copula sample, tilted within a relative entropy budget
    gx = rv_mr.glasserman_xu_worst_case(total, P.GX_BUDGET)
    caps = [r.capital for r in band.rows]
    labels = [(r.method, r.nu) for r in band.rows]
    ref = labels.index(("gaussian-copula", None))
    bs = rv_mr.barrieu_scandolo(caps, ref)
    model_risk = {"status": "information-not-capital",
                  "label": T("Information, not capital: model risk measures are sensitivity information for the validator"),
                  "set_of_models": "band-rows", "reference_model": {"method": "gaussian-copula", "nu": None},
                  "barrieu_scandolo": {"rho_x0_clp_m": bs.rho_x0, "rho_max_clp_m": bs.rho_max, "rho_min_clp_m": bs.rho_min, "am": bs.am, "rm": bs.rm},
                  "glasserman_xu": {"quantity": T("Expected aggregate loss under the Gaussian copula, and its worst case over reweightings of the sample within the relative entropy budget"),
                                    "relative_entropy_budget": P.GX_BUDGET, "theta": gx.theta, "baseline_clp_m": gx.baseline, "worst_case_clp_m": gx.worst_case}}
    return euler, benefit, (model_risk, add), es_total


def aggregation_block(marginals: list[Marginal], named: dict[str, dict[str, Any]], corr_name: str, band: rv_band.Band, n_draws: int = P.N_DRAWS,
                      seed: int = P.SEED) -> AggregationResult:
    corr = named[corr_name]["matrix"]
    euler, div, (model_risk, add), es_total = euler_and_risk(marginals, corr, band, n_draws, seed)
    ec = np.array([m.ec for m in marginals])
    block = {"capital_basis": "economic-capital-var-less-el", "horizon_years": P.HORIZON_YEARS, "confidence_level": P.LEVEL, "correlation": named[corr_name],
             "nu_set": named["nu_set"], "marginals": [marginal_block(m, named) for m in marginals],
             "headline": {"method": "simple-sum", "capital_clp_m": band.headline,
                          "label": T("The headline capital of C18 is the simple sum: the IAPE adds up the capital needed for each risk and the ECB does not "
                                     "recognise inter-risk diversification in the SREP")},
             "band": band_rows(band), "model_risk": model_risk, "euler": euler, "diversification": div}
    gauss = _row(band, "gaussian-copula")
    return AggregationResult(block, band, [add], ec, gauss.capital, es_total)


def band_tests(marginals: list[Marginal], corr: list[list[float]], base: rv_band.Band, stressed: rv_band.Band, add: Any,
               ) -> list[Any]:
    """The tests of G.5 on a base band and its market-credit-0.8 stress."""
    ec = np.array([m.ec for m in marginals])
    gauss, gauss_s = _row(base, "gaussian-copula"), _row(stressed, "gaussian-copula")
    lower, worst = _row(base, "lower-bound"), _row(base, "worst-case")
    between = [r.capital for r in base.rows if r.method not in ("lower-bound", "worst-case")]
    diversified = [r.diversification_factor for r in base.rows if r.method in ("variance-covariance", "gaussian-copula", "t-copula")]
    t_caps = [(r.nu, r.capital) for r in base.rows if r.method == "t-copula"]
    return [
        rv_va.simple_sum_and_variance_covariance(ec, np.array(corr), gauss.capital, model_id=MODEL_ID),
        rv_va.copula_choice_sensitivity(gauss.capital, t_caps, model_id=MODEL_ID),
        rv_va.worst_case_bracket(lower.capital, between, worst.capital, model_id=MODEL_ID),
        rv_va.correlation_stress(gauss.capital, gauss_s.capital, model_id=MODEL_ID),
        rv_va.diversification_sign(diversified, model_id=MODEL_ID),
        rv_va.horizon_confidence_consistency([P.HORIZON_YEARS] * len(marginals), [P.LEVEL] * len(marginals), model_id=MODEL_ID),
        add,
    ]


def elliptical_check(marginals: list[Marginal], corr: list[list[float]], n_draws: int = P.N_DRAWS, seed: int = P.SEED + 7) -> Any:
    """Normal marginals of the same EC, a Gaussian copula and the same matrix: the Monte Carlo capital against the variance-covariance anchor."""
    z = float(stats.norm.ppf(P.LEVEL))
    sds = [m.ec / z for m in marginals]
    ppfs = [(lambda u, s=s: s * stats.norm.ppf(u)) for s in sds]
    agg = rv_cop.copula_aggregate(ppfs, np.array(corr), "gaussian", None, 0.0, P.LEVEL, n_draws, seed, min(P.CHUNK, n_draws))
    vc = rv_simple.variance_covariance(np.array([m.ec for m in marginals]), np.array(corr))
    se = agg.var_se if agg.var_se is not None else 0.0
    return rv_va.elliptical_mc_agreement(agg.ec, se, vc, model_id=MODEL_ID)


def rosenberg_schuermann(base: rv_band.Band, marginals: list[Marginal]) -> tuple[Any, dict[str, Any]]:
    gauss = _row(base, "gaussian-copula")
    total = base.headline
    test = rv_va.rosenberg_schuermann_reference(total, gauss.capital, model_id=MODEL_ID)
    over = total / gauss.capital - 1.0
    block = {"role": "reference-not-a-gate", "weights": {"market": 0.041, "credit": 0.264, "operational": 0.695},
             "correlations": {"market_credit": 0.5, "market_operational": 0.2, "credit_operational": 0.2},
             "published_additive_overestimate": {"low": 0.30, "high": 0.40}, "case_additive_overestimate": over,
             "within_published_range": 0.30 <= over <= 0.40}
    return test, block


def copula_sensitivity(base: rv_band.Band) -> list[dict[str, Any]]:
    gauss = _row(base, "gaussian-copula").capital
    return [{"nu": r.nu, "gaussian_capital_clp_m": gauss, "t_capital_clp_m": r.capital, "relative_difference": r.capital / gauss - 1.0}
            for r in base.rows if r.method == "t-copula"]
