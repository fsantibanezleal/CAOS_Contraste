"""Builds the three U7-S schema files (docs/contracts/schemas/c10).

Run: ``python tests/contracts_u7/build_schemas.py``. Deterministic, standard library only. The schema files are the contract
and are committed; this script is the compact source they are written from, so a name two files of one case share has one
definition (the generator of the TypeScript types fails on a clash). It reuses the helpers of tests/contracts_u6/build_schemas.py
(``Ob``, ``A``, ``R``, ``nullable``, ``one_of``, ``reachable`` ...) and follows the conventions of docs/contracts/catalog.md: one
folder per case, a ``case_id`` const, ``outputs.kind`` on every variant, case-prefixed ``$defs`` (``c10``), the ``variant-envelope``
composition with ``unevaluatedProperties: false``, every object closed, nothing optional (a value the bake may lack is nullable
with its reason).

The shapes transcribe dossier 04 sections C.4 and H (the Vasicek fit, the loss measures, the rungs C1 to C6, the Euler
contributions, the concentration measures), dossier 05 G.4 and G.5 (the Euler principle and the validation of an economic capital
model) and the views the unit sizing lists (plans/contraste/units/U7-sizing.md).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("u6_build_schemas", ROOT / "tests" / "contracts_u6" / "build_schemas.py")
u6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(u6)  # defines the helpers; its main() does not run on import

Ob, A, R, S, N, E, B, Int = u6.Ob, u6.A, u6.R, u6.S, u6.N, u6.E, u6.B, u6.Int
nullable, one_of, reachable, TXT, CUR, DATE, UNIT, LIGHT, NAME_MAP = (
    u6.nullable, u6.one_of, u6.reachable, u6.TXT, u6.CUR, u6.DATE, u6.UNIT, u6.LIGHT, u6.NAME_MAP)
BASE, NOT_EVALUATED_RULE = u6.BASE, u6.NOT_EVALUATED_RULE

OPEN = dict(exclusiveMinimum=0, exclusiveMaximum=1)
PD = N("An estimate-site PD is open: 0 < pd < 1.", **OPEN)
RHO = N("An asset correlation is open: 0 < rho < 1 (the Vasicek model has no value at 0 or 1).", **OPEN)
RATE = N("An observed annual loss rate as a decimal per year, open (0, 1): the implied factor needs it.", **OPEN)
MONEY = N("Money in the `currency` of the enclosing block.", minimum=0)
LEVEL = {"type": "number", "enum": [0.99, 0.999], "description": "A confidence level as a decimal."}
YEAR = Int(1985)

METHODS = ["lhp-vasicek", "gaussian-copula-one-factor", "gaussian-copula-multi-factor", "student-t-copula", "creditrisk-plus",
           "granularity-adjustment", "importance-sampling"]
RUNG_IDS = ["c1-lhp", "c2-gaussian-1f", "c2-gaussian-mf", "c3-student-t", "c4-creditrisk-plus", "c5-granularity",
            "c6-is-gaussian", "c6-is-student-t"]
IRB_RETAIL = ["residential_mortgage", "qrre", "other_retail", "retail_consumer"]
IRB_CLASSES = ["corporate", "sovereign", "bank", "financial_institution", "sme", "hvcre"] + IRB_RETAIL
IRB_REGIMES = ["basel3", "crr3", "basel2", "cl_ran21_6"]
LOAN_TYPES = ["commercial-industrial", "commercial-real-estate", "residential", "credit-cards", "other-consumer"]

ILLUSTRATIVE_INPUT = {"contains": {"properties": {"source": {"const": "illustrative-portfolio"}, "class": {"const": "illustrative"}},
                                   "required": ["source", "class"]}}


def c10_defs() -> dict:
    d: dict = {}
    d["c10FitWindow"] = Ob({"first_year": {"const": 1985}, "last_year": {"const": 2006}, "n_years": {"const": 22}},
                           "The fit window, fixed by the SDD (section 5, case C10): 1985-2006.")
    d["c10EvaluationWindow"] = Ob({"first_year": {"const": 2007}, "last_year": {"const": 2012}, "n_years": {"const": 6}},
                                  "The out-of-sample evaluation window, fixed by the SDD (section 5, case C10): 2007-2012. "
                                  "A fit window that overlaps it, or windows swapped, fail the schema.")
    d["c10Windows"] = Ob({"fit": R("c10FitWindow"), "evaluation": R("c10EvaluationWindow")},
                         "The fit window (1985-2006) and the out-of-sample evaluation window (2007-2012); the fit window "
                         "ends before the evaluation window begins.")
    d["c10Interval"] = Ob({"estimate": RHO, "ci_low": RHO, "ci_high": RHO},
                          "An estimate with its interval, all inside (0, 1); ci_low <= estimate <= ci_high (a producer check).")
    d["c10PdInterval"] = Ob({"estimate": PD, "ci_low": PD, "ci_high": PD},
                            "A PD estimate with its interval, all inside the open interval (0, 1).")
    d["c10MissingQuarter"] = Ob({"quarter": S(pattern=r"^\d{4}Q[1-4]$"), "reason": S(minLength=1)},
                                "A quarter missing from the Federal Reserve table, with its reason; never interpolated.")
    d["c10DataStatus"] = Ob({
        "source": S(), "table": S(), "series": S(),
        "seasonal_adjustment": E("SA", "NSA"), "bank_scope": S(),
        "files_as_of": DATE,
        "quarters_expected": Int(1),
        "missing_quarters": A(R("c10MissingQuarter")),
        "notice": TXT,
    }, "Where the loss-rate series came from: the Federal Reserve charge-off release (dossier 08 B.4, row 23), the table, the "
       "series column and the quarters it lacks.")
    d["c10AnnualRate"] = Ob({
        "year": YEAR,
        "window": E("fit", "evaluation"),
        "n_quarters": Int(0, 4, "Quarters of the year present in the table."),
        "loss_rate": nullable(RATE, "The mean of the four quarterly annualised net charge-off rates; null when a quarter is missing."),
        "reason": nullable(S(), "Why the rate is null; null when it is present."),
        "fitted_cdf": nullable(UNIT, "The fitted Vasicek distribution function at the rate: where the year falls in the fit."),
        "implied_factor": nullable(N(), "The systematic factor z at which the conditional PD equals the rate (dossier 04 C.4)."),
        "exceeds_99": nullable(B, "True when the rate is above the fitted 99% quantile."),
        "exceeds_999": nullable(B, "True when the rate is above the fitted 99.9% quantile."),
    }, "One calendar year of the loss-rate series with its position in the fitted distribution. A year with all four quarters "
       "carries every number and no reason; a year with a missing quarter carries null numbers and the reason, never an "
       "interpolated rate.")
    one_of(d["c10AnnualRate"],
           {"n_quarters": {"const": 4}, "loss_rate": RATE, "reason": {"type": "null"}, "fitted_cdf": UNIT, "implied_factor": N(),
            "exceeds_99": B, "exceeds_999": B},
           {"n_quarters": Int(0, 3), "loss_rate": {"type": "null"}, "reason": S(minLength=1), "fitted_cdf": {"type": "null"},
            "implied_factor": {"type": "null"}, "exceeds_99": {"type": "null"}, "exceeds_999": {"type": "null"}})
    d["c10MlFit"] = Ob({
        "pd": R("c10PdInterval"), "rho": R("c10Interval"),
        "log_likelihood": N(), "converged": B,
        "interval_method": E("profile-likelihood"), "level": {"const": 0.95},
    }, "The maximum-likelihood fit of the Vasicek distribution to the yearly rates of the fit window (dossier 04 C.4; engine "
       "asrf_fit.fit_ml), intervals by the profile likelihood.")
    d["c10MomentsFit"] = Ob({
        "pd": R("c10PdInterval"), "rho": R("c10Interval"),
        "interval_method": E("parametric-bootstrap"), "n_bootstrap": Int(100), "level": {"const": 0.95},
    }, "The method-of-moments fit (engine asrf_fit.fit_moments), intervals by the parametric bootstrap.")
    d["c10Fit"] = Ob({"n_years_used": Int(1), "maximum_likelihood": R("c10MlFit"), "moments": R("c10MomentsFit")},
                     "The two fits of the yearly series; n_years_used counts the fit-window years with a rate.")
    d["c10Profile"] = Ob({
        "level": {"const": 0.95},
        "rho": A(RHO, 8, "The correlation grid, strictly increasing."),
        "log_likelihood": A(N(), 8, "The profile log-likelihood at each grid correlation (the PD maximised out)."),
        "pd_at_rho": A(PD, 8, "The maximising PD at each grid correlation."),
        "max_log_likelihood": N(),
        "cutoff": N("max_log_likelihood minus the chi-square(1) quantile at `level`, halved."),
    }, "The profile likelihood of the asset correlation (dossier 04 C.4; engine asrf_fit.profile_likelihood): the three arrays "
       "have one length.")
    d["c10Curve"] = Ob({
        "x": A(RATE, 8, "Loss rates, strictly increasing."),
        "pdf": A(N(minimum=0), 8, "The Vasicek (large homogeneous portfolio) density at x."),
        "cdf": A(UNIT, 8, "The distribution function at x, nondecreasing."),
    })
    d["c10Quantile"] = Ob({"level": N(**OPEN), "value": RATE})
    d["c10FittedDistribution"] = Ob({
        "pd": PD, "rho": RHO, "curve": R("c10Curve"), "quantiles": A(R("c10Quantile"), 2),
    }, "The fitted (maximum-likelihood) Vasicek distribution of the yearly loss rate: its density and distribution function and "
       "its quantiles; pd and rho equal the maximum-likelihood estimates (a producer check).")
    d["c10BacktestRow"] = Ob({
        "level": {"type": "number", "enum": [0.95, 0.99, 0.999]},
        "fitted_quantile": RATE,
        "expected_exceedances": N(minimum=0),
        "observed_exceedances": Int(0),
        "years_exceeding": A(YEAR),
        "p_value_upper": UNIT,
        "light": LIGHT,
    }, "Years of the evaluation window above one fitted quantile: expected = n_years (1 - level), observed, and the upper "
       "binomial tail probability P(X >= observed) with success probability 1 - level.")
    d["c10Backtest"] = Ob({"n_years_evaluated": Int(1), "rows": A(R("c10BacktestRow"), 3)},
                          "The tail back-test of the evaluation window against the quantiles fitted on the fit window (dossier "
                          "05 G.5; engine validation.portfolio.tail_backtest).")
    d["c10IrbReference"] = Ob({
        "regime": E(*IRB_REGIMES), "asset_class": E(*IRB_CLASSES), "reference": S(minLength=1),
        "pd": PD, "lgd": UNIT,
        "maturity": nullable(N(minimum=1, maximum=5), "Effective maturity in years, 1 to 5; null for a retail class."),
        "maturity_adjustment": nullable(N(exclusiveMinimum=0),
                                        "(1 + (M - 2.5) b) / (1 - 1.5 b) with b = (0.11852 - 0.05478 ln PD)^2; null for a retail class."),
        "irb_correlation": RHO, "fitted_correlation": RHO,
        "k_irb": N(minimum=0, description="The IRB capital requirement per unit of EAD (engine regulatory.irb.capital_requirement), "
                                          "with the maturity adjustment where the class has one."),
        "ec_lhp_fitted": N(minimum=0, description="lgd * (LHP quantile at 99.9% with the fitted correlation - pd) times the same "
                                                  "maturity adjustment as k_irb, per unit of EAD."),
        "ratio_fitted_to_irb": N(minimum=0),
    }, "How the fitted correlation compares with the IRB correlation of the loan type's regulatory class (dossier 04 C.4): the "
       "capital per unit of EAD both ways, with the same maturity treatment on both sides, so the ratio isolates the correlation. "
       "Retail classes carry no maturity and no maturity adjustment; the other classes carry both.")
    one_of(d["c10IrbReference"],
           {"asset_class": E(*IRB_RETAIL), "maturity": {"type": "null"}, "maturity_adjustment": {"type": "null"}},
           {"asset_class": E(*[c for c in IRB_CLASSES if c not in IRB_RETAIL]), "maturity": N(minimum=1, maximum=5),
            "maturity_adjustment": N(exclusiveMinimum=0)})
    d["c10Group"] = Ob({
        "id": S(minLength=1), "label": TXT,
        "n_names": Int(1), "ead_each": N(exclusiveMinimum=0, description="Money in the `currency` of the enclosing block."),
        "pd": PD, "lgd": UNIT,
        "loading": N("The factor loading sqrt(rho) of the group's names on the systematic factor.", **OPEN),
        "sector": S(minLength=1),
    }, "A group of identical names of the illustrative portfolio (dossier 04 H.1: EAD, expected LGD, PD, loading, sector).")
    d["c10Calibration"] = Ob({"pd": PD, "rho": RHO, "source": {"const": "fit-maximum-likelihood"}},
                             "The single PD and correlation the C1 rungs use, taken from the maximum-likelihood fit.")
    d["c10Portfolio"] = Ob({
        "label": {"const": "illustrative"},
        "notice": TXT,
        "currency": CUR,
        "n_names": Int(1),
        "total_ead": N(exclusiveMinimum=0, description="Money in the `currency` of the enclosing block."),
        "groups": A(R("c10Group"), 2),
        "lgd_mean": UNIT,
        "lgd_gamma": N("gamma of V[LGD] = gamma E[LGD] (1 - E[LGD]) (Gordy and Lutkebohmert 2013, eq. 16).", minimum=0),
        "levels": {"type": "array", "const": [0.99, 0.999]},
        "horizon_years": {"const": 1},
        "calibration": R("c10Calibration"),
        "hhi": N(minimum=0, maximum=1),
        "effective_names": N(minimum=1),
        "largest_share": N(minimum=0, maximum=1),
    }, "The illustrative portfolio: constructed, never a bank's (labelled `illustrative` here and in the provenance). hhi = sum "
       "of squared exposure shares and effective_names = 1 / hhi (dossier 04 H.6).")
    d["c10Simulation"] = Ob({"n_scenarios": Int(1), "seed": Int(0), "chunk_size": Int(1)},
                            "How a Monte Carlo rung was run: scenarios, seed, and the chunk bound on memory.")
    d["c10Measure"] = Ob({
        "level": LEVEL,
        "el": MONEY, "var": MONEY,
        "es": nullable(MONEY),
        "es_reason": nullable(S()),
        "ec": MONEY,
        "var_se": nullable(N(minimum=0), "Monte Carlo standard error of the VaR; null for an analytic rung."),
        "es_se": nullable(N(minimum=0), "Monte Carlo standard error of the ES; null for an analytic rung."),
    }, "EL, VaR, ES and EC at one level (dossier 04 H.1): EC = VaR - EL. VaR is not below EL and ES is not below VaR (a producer "
       "check, JSON Schema cannot compare fields). A rung that defines no ES (the granularity adjustment) has es null and the "
       "reason.")
    one_of(d["c10Measure"], {"es": MONEY, "es_reason": {"type": "null"}}, {"es": {"type": "null"}, "es_reason": S(minLength=1)})
    d["c10LossCurve"] = Ob({
        "currency": CUR,
        "loss": A(MONEY, 8, "Portfolio loss in money, strictly increasing."),
        "cdf": A(UNIT, 8, "The distribution function of the loss, nondecreasing."),
        "density": A(N(minimum=0), 8, "The density (per unit of money) or the histogram density."),
    }, "The loss distribution of a rung on a money grid; the three arrays have one length.")
    d["c10Rung"] = Ob({
        "id": E(*RUNG_IDS),
        "rung": E("C1", "C2", "C3", "C4", "C5", "C6"),
        "method": E(*METHODS),
        "label": TXT,
        "currency": CUR,
        "estimator": E("analytic", "monte-carlo", "none"),
        "evaluated": B,
        "reason": nullable(S(), "Why the rung did not run; null when it ran."),
        "parameters": A(NAME_MAP, desc="The declared inputs of the rung; a rung that did not run may keep them."),
        "diagnostics": A(NAME_MAP, desc="Numbers measured by running the rung; empty when the rung did not run."),
        "simulation": nullable(R("c10Simulation")),
        "measures": nullable(A(R("c10Measure"), 2)),
        "distribution": nullable(R("c10LossCurve")),
    }, "One rung of the portfolio ladder (dossier 04 'Portfolio credit risk': C1 LHP, C2 Gaussian copula, C3 Student-t copula, C4 "
       "CreditRisk+, C5 granularity adjustment, C6 importance sampling) on the illustrative portfolio. A rung that did not run "
       "(importance sampling for the Student-t copula) is a not-evaluated row: evaluated false, its reason, no measure, no curve; "
       "never a number.")
    one_of(d["c10Rung"],
           {"evaluated": {"const": True}, "estimator": {"const": "analytic"}, "reason": {"type": "null"},
            "simulation": {"type": "null"},
            "measures": {"type": "array", "items": {"properties": {"var_se": {"type": "null"}, "es_se": {"type": "null"}}}},
            "distribution": R("c10LossCurve")},
           {"evaluated": {"const": True}, "estimator": {"const": "monte-carlo"}, "reason": {"type": "null"},
            "simulation": R("c10Simulation"),
            "measures": {"type": "array", "items": {"properties": {"var_se": N(minimum=0), "es_se": N(minimum=0), "es": MONEY}}},
            "distribution": R("c10LossCurve")},
           {"evaluated": {"const": False}, "estimator": {"const": "none"}, "reason": S(minLength=1), "simulation": {"type": "null"},
            "diagnostics": {"type": "array", "maxItems": 0},
            "measures": {"type": "null"}, "distribution": {"type": "null"}})
    d["c10GaRow"] = Ob({
        "n_names": Int(1), "hhi": N(minimum=0, maximum=1), "ga": N(minimum=0),
        "truth_ga": nullable(N(minimum=0), "alpha_q(L_n) - mu(alpha_q(X)) from the CreditRisk+ recursion of the same single-factor "
                                           "model, as a share of EAD; null with its reason where the recursion was not run."),
        "truth_reason": nullable(S()),
    }, "The granularity adjustment (a share of EAD) of n identical names of the portfolio's mix at the level of by_n_names_level, "
       "with the recursion's value beside it: ga times n is constant.")
    one_of(d["c10GaRow"], {"truth_ga": N(minimum=0), "truth_reason": {"type": "null"}},
           {"truth_ga": {"type": "null"}, "truth_reason": S(minLength=1)})
    d["c10GaLevel"] = Ob({
        "q": LEVEL,
        "alpha_q": N("The q-quantile of the Gamma factor with shape xi and rate xi (mean 1, variance 1/xi).", exclusiveMinimum=1),
        "delta": N(minimum=0),
        "ga": N("The granularity adjustment of the portfolio at this level, a share of EAD (Gordy and Lutkebohmert 2013, eq. 9 "
                "and 17).", minimum=0),
        "ga_money": MONEY,
    }, "The adjustment at one level: ga_money = ga * total_ead (a producer check). The C5 rung's VaR at this level is the C1 VaR "
       "plus ga_money.")
    d["c10Granularity"] = Ob({
        "currency": CUR,
        "xi": N(exclusiveMinimum=0), "gamma": N(minimum=0),
        "k_source": {"const": "irb-regulatory-correlation"},
        "k_star": N("K* = sum_i s_i K_i with K_i the IRB capital per unit of EAD at the regulatory correlation (Gordy and "
                    "Lutkebohmert 2013, algorithm step iv, p. 47).", minimum=0),
        "delta_reference": {"const": 4.83},
        "delta_reference_source": S(minLength=1),
        "levels": A(R("c10GaLevel"), 2),
        "by_n_names_level": {"const": 0.999},
        "by_n_names": A(R("c10GaRow"), 5),
    }, "The granularity adjustment of Gordy and Lutkebohmert (2013) (dossier 04 H.5): delta = (alpha_q - 1)(xi + (1 - xi) / "
       "alpha_q) (eq. 15), 4.83 at xi 0.25 and q 0.999 (p. 46); the adjustment GA is a share of EAD (eq. 9, p. 41; eq. 17), per "
       "level for the portfolio and against the number of names. At xi 0.25 the delta of the 99.9% level lies in [4.825, 4.835].")
    d["c10Granularity"]["if"] = {"properties": {"xi": {"const": 0.25}}, "required": ["xi"]}
    d["c10Granularity"]["then"] = {"properties": {"levels": {"items": {
        "if": {"properties": {"q": {"const": 0.999}}, "required": ["q"]},
        "then": {"properties": {"delta": {"minimum": 4.825, "maximum": 4.835}}}}}}}
    d["c10EulerRow"] = Ob({
        "group_id": S(minLength=1), "ead": MONEY,
        "rc_var": MONEY, "rc_es": MONEY, "share_var": UNIT, "share_es": UNIT,
    }, "The Euler contribution of one group to the VaR and to the ES (dossier 05 G.4: E[L_i | L = VaR], E[L_i | L >= VaR]).")
    d["c10EulerAnchorRow"] = Ob({"group_id": S(minLength=1), "rc_var": MONEY})
    d["c10EulerAnchor"] = Ob({"method": {"const": "asrf-asymptotic"}, "asrf_var": MONEY, "rows": A(R("c10EulerAnchorRow"), 2)},
                             "The asymptotic one-factor VaR contributions u_j * Phi((c_j - sqrt(rho_j) q_(1-alpha)(X)) / "
                             "sqrt(1 - rho_j)): the first term of Emmer and Tasche (2005) eq. 2.17 (Gordy 2003 portfolio "
                             "invariance), not their full contribution. asrf_var is the sum of the rows, the infinitely granular "
                             "VaR; the sample VaR sits near it, not on it (a producer check recomputes both).")
    d["c10EulerLevel"] = Ob({
        "level": LEVEL,
        "var_total": MONEY, "es_total": MONEY,
        "var_sum_tolerance": N("Relative tolerance of the sum of the VaR contributions against var_total.", exclusiveMinimum=0),
        "es_sum_tolerance": N("Relative tolerance of the sum of the ES contributions against es_total.", exclusiveMinimum=0),
        "var_method": E("kernel", "closed-form-one-factor"),
        "es_method": E("tail-sample"),
        "rows": A(R("c10EulerRow"), 2),
        "anchor": nullable(R("c10EulerAnchor")),
        "anchor_reason": nullable(S()),
    }, "The contributions at one level. The contributions of a level sum to its totals within the stated tolerances (a producer "
       "check); the anchor is null with its reason where no closed form exists.")
    one_of(d["c10EulerLevel"], {"anchor": R("c10EulerAnchor"), "anchor_reason": {"type": "null"}},
           {"anchor": {"type": "null"}, "anchor_reason": S(minLength=1)})
    d["c10Euler"] = Ob({
        "rung_method": E("gaussian-copula-one-factor", "gaussian-copula-multi-factor", "student-t-copula", "creditrisk-plus"),
        "currency": CUR,
        "levels": A(R("c10EulerLevel"), 2),
    }, "The Euler contributions of one sample-based rung, by portfolio group, at both levels.")
    d["c10LoanTypeOutputs"] = Ob({
        "kind": {"const": "loan-type"},
        "loan_type": E(*LOAN_TYPES),
        "label": TXT,
        "currency": CUR,
        "loss_rate_definition": TXT,
        "windows": R("c10Windows"),
        "data_status": R("c10DataStatus"),
        "annual_rates": A(R("c10AnnualRate"), 8),
        "fit": R("c10Fit"),
        "profile_likelihood": R("c10Profile"),
        "fitted_distribution": R("c10FittedDistribution"),
        "backtest": R("c10Backtest"),
        "irb_reference": R("c10IrbReference"),
        "portfolio": R("c10Portfolio"),
        "rungs": A(R("c10Rung"), 8),
        "granularity": R("c10Granularity"),
        "euler": A(R("c10Euler"), 1),
    }, "C10 loan-type outputs (outputs.kind loan-type): one Federal Reserve loan type, the Vasicek fit to its yearly loss rates "
       "(fit 1985-2006), the 2007-2012 tail back-test, and the loss distributions of the illustrative portfolio by rung with the "
       "Euler contributions and the concentration measures. Loss rates are decimals per year; money carries its currency.")
    d["c10Estimator"] = Ob({
        "estimator": E("maximum-likelihood", "moments"),
        "mean_estimate": RHO,
        "bias": N("mean_estimate minus known_rho."),
        "rmse": N(minimum=0),
        "coverage": UNIT,
        "rejection_rate": UNIT,
        "rejection_se": N(minimum=0),
        "rejection_ci_low": UNIT, "rejection_ci_high": UNIT,
    }, "One estimator in one grid cell over the valid replications: bias, rmse, the coverage of its 95% interval, and the rate at "
       "which H0: rho = null_rho is rejected at level alpha with its Monte Carlo standard error and Wilson interval.")
    d["c10GridCell"] = Ob({
        "known_rho": RHO,
        "series_length_years": {"type": "integer", "enum": [22, 40]},
        "n_replications": Int(1), "n_valid": Int(0), "n_failed": Int(0),
        "role": E("size", "power"),
        "estimators": A(R("c10Estimator"), 2),
    }, "One cell of the simulator's correlation grid. role is size where known_rho equals the generator's null_rho (the rejection "
       "rate is then the exact size) and power elsewhere (a producer check). n_valid + n_failed = n_replications.")
    d["c10SimGenerator"] = Ob({
        "name": S(), "shaped_on": S(),
        "known_pd": PD,
        "rho_grid": A(RHO, 2, "The known asset correlations, strictly increasing."),
        "series_length_years": {"type": "integer", "enum": [22, 40]},
        "n_replications": Int(1),
        "null_rho": RHO,
        "alpha": {"const": 0.05},
        "seed": Int(0),
        "notice": TXT,
    }, "The Vasicek simulator with a known correlation: a yearly factor draw per year, the large-homogeneous-portfolio default "
       "fraction, then the fit. null_rho is on the grid.")
    d["c10GridOutputs"] = Ob({
        "kind": {"const": "correlation-grid"},
        "label": TXT,
        "generator": R("c10SimGenerator"),
        "size_power_definition": TXT,
        "cells": A(R("c10GridCell"), 2),
    }, "C10 correlation-grid outputs (outputs.kind correlation-grid): the exact size and power of the correlation estimates on a "
       "simulator with a known correlation, for one series length. The known correlation is a required field of the generator "
       "and of every cell.")
    d["c10LoanTypeSpec"] = Ob({
        "id": E(*LOAN_TYPES), "label": TXT,
        "table_column": S(minLength=1),
        "irb_asset_class": E(*IRB_CLASSES), "irb_reference": S(minLength=1),
    }, "A loan type of the Federal Reserve table and the IRB asset class its fitted correlation is compared with.")
    d["c10EstimatorSpec"] = Ob({
        "id": E("maximum-likelihood", "moments"), "label": TXT,
        "engine_function": S(minLength=1), "interval_method": E("profile-likelihood", "parametric-bootstrap"),
        "reference": S(minLength=1),
    })
    d["c10RungSpec"] = Ob({
        "id": E(*RUNG_IDS), "rung": E("C1", "C2", "C3", "C4", "C5", "C6"), "method": E(*METHODS), "label": TXT,
        "estimator": E("analytic", "monte-carlo"),
        "n_scenarios": nullable(Int(1), "Monte Carlo scenarios; null for an analytic rung."),
        "engine_function": S(minLength=1),
        "reference": S(minLength=1),
        "parameters": A(NAME_MAP),
    }, "The specification of one rung: its engine function, its reference and its parameters. A Monte Carlo rung has its "
       "scenario count; an analytic rung has none.")
    one_of(d["c10RungSpec"], {"estimator": {"const": "analytic"}, "n_scenarios": {"type": "null"}},
           {"estimator": {"const": "monte-carlo"}, "n_scenarios": Int(1)})
    d["c10PortfolioSpec"] = Ob({
        "label": {"const": "illustrative"},
        "notice": TXT,
        "currency": CUR,
        "groups": A(R("c10Group"), 2),
        "lgd_mean": UNIT,
        "lgd_gamma": N(minimum=0),
        "levels": {"type": "array", "const": [0.99, 0.999]},
        "horizon_years": {"const": 1},
    }, "The specification of the illustrative portfolio the bake builds per loan type: constructed, never a bank's.")
    d["c10GranularitySpec"] = Ob({
        "xi": N(exclusiveMinimum=0), "gamma": N(minimum=0),
        "k_source": {"const": "irb-regulatory-correlation"},
        "xi_reference": {"const": 0.25}, "q_reference": {"const": 0.999}, "delta_reference": {"const": 4.83},
        "reference": S(minLength=1),
    }, "The granularity parameters and the golden delta of Gordy and Lutkebohmert (2013) (eq. 15): 4.83 at xi 0.25 and q 0.999.")
    d["c10SimSpec"] = Ob({
        "known_pd": PD,
        "rho_grid": A(RHO, 2),
        "series_lengths_years": A({"type": "integer", "enum": [22, 40]}, 1),
        "n_replications": Int(1),
        "null_rho": RHO,
        "alpha": {"const": 0.05},
        "seed": Int(0),
    }, "The simulator's grid: the known correlations, the series lengths, the replications.")
    d["c10ModelsFit"] = Ob({
        "currency": CUR,
        "windows": R("c10Windows"),
        "loan_types": A(R("c10LoanTypeSpec"), 5),
        "estimators": A(R("c10EstimatorSpec"), 2),
        "ladder": A(R("c10RungSpec"), 8),
        "portfolio_spec": R("c10PortfolioSpec"),
        "granularity": R("c10GranularitySpec"),
        "simulator": R("c10SimSpec"),
    }, "C10 models: the five loan types, the two estimators, the eight rungs of the ladder, the illustrative portfolio's "
       "specification, the granularity parameters and the simulator's grid.")
    return d


def write(name: str, doc: dict) -> None:
    path = ROOT / "docs" / "contracts" / "schemas" / "c10" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def variant_schema(ref: str, kind: str, title: str, desc: str, root: str, defs: dict, truth: str, illustrative: bool) -> None:
    provenance: dict = {"truth_status": {"const": truth}}
    if illustrative:
        provenance["inputs"] = ILLUSTRATIVE_INPUT
    write(f"{ref}.schema.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}c10/{ref}.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/variant-envelope.schema.json"},
            {"properties": {"case_id": {"const": "C10"},
                            "outputs": {"$ref": f"#/$defs/{root}", "properties": {"kind": {"const": kind}}}},
             "required": ["case_id", "outputs"]},
            {"properties": {"provenance": {"properties": provenance}}},
            NOT_EVALUATED_RULE,
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    })


def main() -> None:
    d = c10_defs()
    variant_schema("variant-loan-type", "loan-type", "C10 loan-type variant",
                   "Catalog row c10-outputs 1.0.0: one Federal Reserve loan type of the portfolio credit capital case "
                   "(outputs.kind loan-type), real charge-off rates and an illustrative portfolio.", "c10LoanTypeOutputs", d,
                   "real-outcomes", True)
    variant_schema("variant-correlation-grid", "correlation-grid", "C10 correlation-grid variant",
                   "Catalog row c10-outputs-grid 1.0.0: the simulator's correlation grid of the portfolio credit capital case "
                   "(outputs.kind correlation-grid), on a generator with a known correlation.", "c10GridOutputs", d,
                   "synthetic-known-truth", False)
    write("models.schema.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}c10/models.schema.json",
        "title": "C10 models",
        "description": "Catalog row c10-models 1.0.0: the C10 models artifact (loan types, estimators, the rung ladder, the "
                       "illustrative portfolio's specification, the granularity parameters, the simulator grid).",
        "allOf": [
            {"$ref": "../common/models-envelope.schema.json"},
            {"properties": {"case_id": {"const": "C10"}, "fit": {"$ref": "#/$defs/c10ModelsFit"},
                            "provenance": {"properties": {"inputs": ILLUSTRATIVE_INPUT}}},
             "required": ["case_id", "fit"]},
        ],
        "unevaluatedProperties": False,
        "$defs": reachable("c10ModelsFit", d),
    })


if __name__ == "__main__":
    main()
