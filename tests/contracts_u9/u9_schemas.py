"""Builds the U9-S schema files: docs/contracts/schemas/c12 (the variant and the models documents) and
docs/contracts/schemas/regulatory (the regulatory-calculators document).

Run: ``python tests/contracts_u9/u9_schemas.py``. Deterministic, standard library only. The schema files are the contract and
are committed; this script is the compact source they are written from. It reuses the helper functions of the U10 builder
(tests/contracts_u10/build_schemas.py) rather than copying them: one folder per case, a ``case_id`` const, ``outputs.kind``
on the variant, case-prefixed ``$defs``, the ``variant-envelope`` composition with ``unevaluatedProperties: false``, every object
closed, nothing optional.

Transcribed from the U9 sizing (plans/contraste/units/U9-sizing.md, modules and views rows, decisions D1 to D8 and B1 to B10),
the U9 research addendum (R1 wrong-way risk, R2 initial margin, R3 MPoR, R5 backtest, R6 estimators, R7 GIRR, R9 IMM measures,
R10 credit curve), dossier 01 (C, C.1, D.2, D.3, E.1, E.2, M.1, M.3) and the SDD sections 3 to 5.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import semantics as sm  # noqa: E402

ROOT = HERE.parents[1]
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
BASE = "https://contraste.fasl-work.com/contracts/"


def _u10():
    spec = importlib.util.spec_from_file_location("u10_build_schemas", ROOT / "tests" / "contracts_u10" / "build_schemas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


U = _u10()
Ob, A, R, nullable, S, Int, N, E, C, B = U.Ob, U.A, U.R, U.nullable, U.S, U.Int, U.N, U.E, U.C, U.B
DATE, TXT, one_of, ordered, reachable, write = U.DATE, U.TXT, U.one_of, U.ordered, U.reachable, U.write

# --- the values typed here again, each with its source line ----------------------------------------------------------------

VARIANTS = ["single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im", "wrong-way-risk"]
#: the six backtest horizons, in order: B5 adds the two MPoR horizons (BCBS 185 paragraphs 18 and 19) to D7's four
HORIZONS = ["10bd", "20bd", "1m", "3m", "6m", "12m"]
SUB_WINDOWS = ["before-2008", "2008-2019", "from-2020"]  # D7
GIRR_TENORS, GIRR_RW, GIRR_CORR = sm.GIRR_TENORS, sm.GIRR_RW, sm.GIRR_CORR  # MAR21.8, MAR21.42 Table 1, MAR21.46 Table 2 (R7)
BA_CVA_SECTORS = list(sm.BA_CVA_RW)
#: the named parameters of decision D6 and the settings the methods leave to the bake; each is required with the label "convention"
NAMED = ["notionals", "maturities_years", "sides", "netting_set_members", "single_swap_member", "fixed_rate_rule",
         "csa_threshold", "csa_minimum_transfer_amount", "csa_independent_amount", "mpor_business_days_short",
         "mpor_business_days_long", "counterparty_spread", "counterparty_lgd", "bank_spread", "bank_lgd", "pfe_quantile",
         "path_count", "seed", "time_grid_years", "wwr_b_grid", "im_quantile", "im_horizon_calendar_days",
         "im_mpor_calendar_days", "im_regression_order", "ba_cva_sector", "ba_cva_rating", "stress_window_start",
         "stress_window_end", "backtest_window_start", "backtest_paths_per_date", "backtest_simulated_critical_count",
         "reconciliation_se_threshold", "ee_check_k_se"]


SENS_DESC = ("s_k = (V(r + 0.0001) - V(r)) / 0.0001 at each GIRR tenor, in USD per unit of rate: the change in value for a 1 basis "
             "point shift divided by 0.0001 (MAR21.19), not the PV01 per basis point. The weighted sensitivity is RW_k s_k / sqrt(2).")


def LBL(p: str) -> dict:
    return R(p + "Label")


# ---------------------------------------------------------------------------------------------------------------- C12


def c12_defs() -> dict:
    p = "c12"
    d: dict = {}
    d[p + "Sign"] = Ob({
        "ee": C("positive-exposure-to-the-counterparty"), "ene": C("bank-own-exposure-reported-positive"),
        "cva": C("positive-is-cost"), "dva": C("positive-is-benefit"), "statement": TXT,
    }, "Sign convention, stated in the document: EE is the positive exposure to the counterparty, ENE the bank's own, CVA a "
       "positive cost and DVA a positive benefit.")
    d[p + "Units"] = Ob({
        "money": C("amount with its ISO 4217 currency code, USD in this case"), "rate": C("decimal"),
        "compounding": C("continuous"), "time": C("years-from-the-valuation-date"), "mpor": C("business-days"),
        "dates": C("ISO-8601"),
    }, "Units of every number: money in USD with its currency code, rates as decimals discounted continuously, times in years "
       "from the valuation date, the margin period of risk in business days, dates ISO.")
    d[p + "Money"] = Ob({"amount": N(), "currency": C("USD")}, "An amount of money with its currency code.")
    d[p + "MoneySe"] = Ob({"amount": N(), "currency": C("USD"), "mc_se": N(minimum=0)},
                          "An amount of money with its currency code and its Monte Carlo standard error.")
    d[p + "Profile"] = Ob({
        "currency": C("USD"), "values": A(N(), 2, desc="One value per point of the time grid."),
        "mc_se": A(N(minimum=0), 2, desc="The Monte Carlo standard error of each value."),
    }, "A money profile on the time grid with its Monte Carlo standard errors (same length as the grid: a producer check).")
    d[p + "NonNegProfile"] = Ob({
        "currency": C("USD"), "values": A(N(minimum=0), 2, desc="One non-negative value per point of the time grid."),
        "mc_se": A(N(minimum=0), 2, desc="The Monte Carlo standard error of each value."),
    }, "A non-negative money profile (an EE, ENE, PFE, effective EE or DIM) on the time grid with its Monte Carlo standard errors "
       "(same length as the grid: a producer check).")
    d[p + "Convention"] = Ob({
        "value": {"type": ["number", "string", "array"]}, "unit": S(minLength=1), "label": C("convention"),
    }, "A named parameter of the synthetic book or of a method (decision D6): its value, its unit and the label \"convention\". "
       "A parameter without the label fails.")
    d[p + "NamedParameters"] = Ob({k: R(p + "Convention") for k in NAMED},
                                  "Every named parameter, required, each with its value and the label convention.")
    d[p + "Trade"] = Ob({
        "trade_id": S(minLength=1), "notional": R(p + "Money"), "fixed_rate": N(), "side": E("payer", "receiver"),
        "start_years": N(minimum=0), "maturity_years": N(exclusiveMinimum=0), "fixed_frequency_per_year": Int(1, 12),
        "floating_leg": C("USD floating leg on the single curve of the case"), "label": C("convention"),
    }, "One fixed-for-floating USD interest rate swap: payer pays the fixed rate. Its terms are conventions.")
    d[p + "Book"] = Ob({
        "netting_set_id": S(minLength=1), "currency": C("USD"), "trades": A(R(p + "Trade"), 1),
    }, "The synthetic book of the variant: one swap for the single-swap variant and at least two for the netting set.")
    d[p + "CurvePoint"] = Ob({"tenor_years": N(exclusiveMinimum=0), "par_yield": N(), "zero_rate": N()},
                             "One tenor of the curve: the source par yield (decimal) and the continuously compounded zero rate.")
    d[p + "Curve"] = Ob({
        "curve_date": DATE, "source": C("US Treasury daily par yield curve (home.treasury.gov)"),
        "licence_class": C("mirror-allowed"), "par_yield_unit": C("decimal, bond-equivalent"),
        "zero_compounding": C("continuous"), "points": A(R(p + "CurvePoint"), 1),
        "tenors_present": A(N(exclusiveMinimum=0), 1), "tenors_absent": A(N(exclusiveMinimum=0)),
        "interpolated_silently": C(False),
    }, "The curve of the curve date. A Treasury tenor absent on that date is absent from the curve and listed in tenors_absent, "
       "with the tenors present stated, never interpolated silently.")
    d[p + "Calibration"] = Ob({
        "backtest_date": DATE, "model": C("hw1f"),
        "estimator": C("exact AR(1) OLS on the shortest Treasury zero rate (Brigo et al., arXiv 0812.4210, equations 55 to 57)"),
        "proxy_tenor_years": N(exclusiveMinimum=0), "sample_start": DATE, "sample_end": DATE, "n_obs": Int(2),
        "history_years": N(minimum=3, description="At least three years of history (CRE53.51)."),
        "a": N(exclusiveMinimum=0), "sigma": N(exclusiveMinimum=0), "a_se": N(minimum=0), "sigma_se": N(minimum=0),
        "fit_to_curve": C("phi(t) = f(0,t) + sigma^2 (1 - exp(-a t))^2 / (2 a^2), the QuantLib 1.44 fitting parameter"),
    }, "The Hull-White one-factor calibration at one backtest date: a and sigma from the history only, the fit to the curve of "
       "the date by phi(t). The sample window ends strictly before the backtest date (no look-ahead: a producer check).")
    d[p + "Exposure"] = Ob({
        "basis": E("uncollateralised", "collateralised-vm", "collateralised-vm-im"),
        "time_grid_years": A(N(exclusiveMinimum=0), 2), "ee": R(p + "NonNegProfile"), "ee_discounted": R(p + "NonNegProfile"),
        "ene": R(p + "NonNegProfile"), "ene_discounted": R(p + "NonNegProfile"), "pfe_quantile": N(exclusiveMinimum=0, exclusiveMaximum=1),
        "pfe": R(p + "NonNegProfile"), "effective_ee": R(p + "NonNegProfile"), "epe": R(p + "MoneySe"), "eepe": R(p + "MoneySe"),
        "eepe_horizon_years": N(exclusiveMinimum=0, maximum=1), "measure_note": TXT,
    }, "The exposure measures of the variant on the time grid, each with its Monte Carlo error: EE and ENE undiscounted "
       "(Basel style, dossier 05 C.1) and discounted under the numeraire (the CVA input), the PFE at the stated quantile, the "
       "effective EE (running maximum, CRE53.12) and EEPE (CRE53.13) over the first year or to maturity.")
    d[p + "NettingBenefit"] = Ob({
        "per_trade_ee": A(Ob({"trade_id": S(minLength=1), "ee": R(p + "NonNegProfile")}), 1),
        "sum_of_single_trade_ee": R(p + "NonNegProfile"), "netted_ee": R(p + "NonNegProfile"), "benefit": R(p + "NonNegProfile"),
    }, "The netting benefit: the netting-set EE is at most the sum of the single-trade EE; the benefit is their difference.")
    d[p + "Csa"] = Ob({
        "threshold": R(p + "Money"), "minimum_transfer_amount": R(p + "Money"), "independent_amount": R(p + "Money"),
        "mpor_business_days": Int(10), "remargining_days": Int(1), "closeout": C("sticky-date close-out grid (ORE, R3)"),
        "floor_reference": S(minLength=1),
    }, "The CSA terms of the variant (ORE credit support amount and delivery amount equations, R3).")
    d[p + "Collateral"] = Ob({
        "csa": R(p + "Csa"), "uncollateralised_ee": R(p + "NonNegProfile"), "collateral_balance": R(p + "Profile"),
        "limit": R(p + "Label"),
    }, "The variation-margin variant: the CSA terms, the uncollateralised EE on the same axis and the mean collateral balance. "
       "The limit states what the close-out model leaves out (the Andersen, Pykhtin and Sokol timelines).")
    d[p + "Label"] = Ob({"en": S(minLength=1), "es": S(minLength=1)}, "A non-empty bilingual label.")
    d[p + "Im"] = Ob({
        "method": C("ORE dynamic initial margin by regression (R2)"), "labelled": C("regression proxy, not SIMM"),
        "simm_used": C(False), "quantile": N(exclusiveMinimum=0, exclusiveMaximum=1), "alpha": N(exclusiveMinimum=0),
        "horizon_calendar_days": Int(1), "mpor_calendar_days": Int(1), "regression_order": Int(0),
        "dim": R(p + "NonNegProfile"), "ee_vm_only": R(p + "NonNegProfile"), "limit": R(p + "Label"),
    }, "Initial margin as a separate balance: DIM(t) = alpha S(t) sqrt(horizon / MPoR) applied as max(exposure - DIM, 0), alpha "
       "the normal quantile of `quantile`, the horizon and the MPoR in calendar days as ORE computes horizonCalendarDays / "
       "mporCalendarDays (10 business days are 14 calendar days, 20 are 28). "
       "Labelled a regression proxy, never SIMM (SIMM is not used: its public notice restricts use to a participant's own "
       "transactions).")
    d[p + "CvaBucket"] = Ob({
        "t_start": N(minimum=0), "t_end": N(exclusiveMinimum=0), "spread": N(minimum=0), "survival": N(minimum=0, maximum=1),
        "pd_counterparty": N(minimum=0, maximum=1), "pd_bank": N(minimum=0, maximum=1),
        "epe_discounted": N(minimum=0), "ene_discounted": N(minimum=0), "cva_term": N(minimum=0), "dva_term": N(minimum=0),
    }, "One time bucket of the discretised CVA: PD x LGD x discounted EPE (dossier 05 C.2).")
    d[p + "Cva"] = Ob({
        "credit_curve_source": E("hqm-minus-treasury", "synthetic-flat"),
        "credit_curve_label": C("proxy: an AAA to A market spread, a floor for lower ratings (R10)"),
        "survival_formula": C("S(t) = exp(-s t / LGD)"),
        "negative_spread_rule": C("a negative HQM-minus-Treasury spread is set to zero and counted in spreads_floored_at_zero"),
        "spreads_floored_at_zero": Int(0), "lgd": N(exclusiveMinimum=0, maximum=1),
        "bank_lgd": N(exclusiveMinimum=0, maximum=1), "buckets": A(R(p + "CvaBucket"), 1),
        "cva": R(p + "MoneySe"), "dva": R(p + "MoneySe"), "bcva": R(p + "Money"),
    }, "CVA and DVA by the discretised formula, with the bucket terms so a view or a test recomputes them from the EE.")
    d[p + "WwrPoint"] = Ob({"b": N(), "cva": R(p + "MoneySe"), "independent": B,
                            "a_calibration_max_error": N(minimum=0)},
                           "CVA at one value of the dependence parameter b, with the largest calibration error of the "
                           "survival constraint; independent is true at b = 0 only.")
    d[p + "Wwr"] = Ob({
        "model": C("Hull and White (2012) hazard rate on the portfolio value, h(t) = exp(a(t) + b w(t))"),
        "b_unit": C("per USD million of portfolio value"), "b_grid": A(N(), 3),
        "w_max_usd_million": N(exclusiveMinimum=0, description="The largest portfolio value of the simulated paths, in USD million."),
        "largest_b_w": N(minimum=0, description="max |b| of the grid times w_max_usd_million: the largest exponent b w the grid "
                                                 "reaches on this book, so the reader sees whether the sweep moves the hazard."),
        "sweep": A(R(p + "WwrPoint"), 3), "independent_cva": R(p + "Money"), "ore_limit": R(p + "Label"),
    }, "The wrong-way risk variant (B1): CVA over the grid of b, a(t) calibrated sequentially on the simulated paths to the "
       "survival curve. b = 0 equals the independent CVA exactly. ORE's wrong-way example is a different model, so this variant "
       "has no ORE reconciliation and says so.")
    d[p + "SaTrade"] = Ob({
        "trade_id": S(minLength=1), "hedging_set": S(pattern="^[A-Z]{3}$"), "start_years": N(minimum=0),
        "end_years": N(exclusiveMinimum=0), "notional": R(p + "Money"), "supervisory_duration": N(minimum=0),
        "adjusted_notional": R(p + "Money"), "delta": {"type": "number", "enum": [1, -1]}, "maturity_factor": N(exclusiveMinimum=0),
        "bucket": E("B1", "B2", "B3"), "effective_notional": N(),
    }, "The CRE52 intermediates of one trade: supervisory duration (CRE52.34), adjusted notional, supervisory delta, maturity "
       "factor (CRE52.48 to CRE52.52), the maturity bucket of its end date (CRE52.57) and the effective notional d x delta x MF.")
    d[p + "SaHedgingSet"] = Ob({
        "hedging_set": S(pattern="^[A-Z]{3}$"), "d_b1": N(), "d_b2": N(), "d_b3": N(), "offset": B,
        "effective_notional": N(minimum=0), "supervisory_factor": C(0.005), "addon": N(minimum=0),
    }, "An interest rate hedging set (one per currency): the bucket effective notionals D(B1) to D(B3), the offset or no-offset "
       "formula of CRE52.57, the effective notional EN and AddOn = SF x EN.")
    d[p + "SaAddOns"] = Ob({
        "interest_rate": N(minimum=0), "fx": N(minimum=0), "credit": N(minimum=0), "equity": N(minimum=0),
        "commodity": N(minimum=0)}, "The add-on by asset class (CRE52.24 to CRE52.25).")
    d[p + "SaCcr"] = Ob({
        "paragraph": C("CRE52"), "in_force_date": C("2023-01-01"), "margined": B,
        "v": R(p + "Money"), "c": R(p + "Money"), "th": R(p + "Money"), "mta": R(p + "Money"), "nica": R(p + "Money"),
        "mpor_business_days": nullable(Int(10)), "rc": R(p + "Money"), "trades": A(R(p + "SaTrade"), 1),
        "hedging_sets": A(R(p + "SaHedgingSet"), 1), "addon_by_class": R(p + "SaAddOns"), "addon_aggregate": R(p + "Money"),
        "multiplier_floor": C(0.05), "multiplier": N(minimum=0.05, maximum=1), "pfe": R(p + "Money"), "alpha": C(1.4),
        "ead": R(p + "Money"),
    }, "The SA-CCR block (CRE52): the trade inputs and every intermediate value, RC, the hedging sets with buckets B1 to B3, "
       "the effective notionals, the add-ons, the multiplier and EAD = 1.4 (RC + PFE), so a live port is checked step by step.")
    d[p + "BaCvaCounterparty"] = Ob({
        "counterparty_id": S(minLength=1), "sector": E(*BA_CVA_SECTORS), "rating_class": E("investment-grade", "high-yield-or-not-rated"),
        "risk_weight": N(exclusiveMinimum=0), "ead": R(p + "Money"), "m_years": N(exclusiveMinimum=0),
        "discount_factor": N(exclusiveMinimum=0, maximum=1), "scva": N(minimum=0),
    }, "One counterparty of the BA-CVA reduced approach (MAR50.14 to MAR50.16 Table 1).")
    d[p + "BaCva"] = Ob({
        "paragraph": C("MAR50.14 to MAR50.16"), "in_force_date": C("2023-01-01"), "imm_bank": C(False),
        "ds": C(0.65), "rho": C(0.5), "alpha": C(1.4), "counterparties": A(R(p + "BaCvaCounterparty"), 1),
        "k_reduced": N(minimum=0), "capital": R(p + "Money"),
        "limit": R(p + "Label"),
    }, "The BA-CVA reduced block: sector, rating, EAD, M, DF, SCVA, K_reduced and the capital DS x K_reduced. No official "
       "numeric example is verified (B8); the limit says so.")
    d[p + "StressedEpe"] = Ob({
        "window_start": DATE, "window_end": DATE, "label": C("convention"), "effective_epe": R(p + "Money"),
        "hqm_spread_start": N(minimum=0), "hqm_spread_peak": N(minimum=0), "spread_rose": B, "paragraph": C("CRE53.7 and CRE53.51"),
    }, "The stressed Effective EPE (B9): a named three-year window containing a stress period, and the HQM spread rising in it "
       "(B10).")
    d[p + "Regulatory"] = Ob({
        "alpha": C(1.4), "alpha_paragraph": C("CRE53.14"), "effective_maturity_years": N(minimum=1, maximum=5),
        "alpha_times_eepe": R(p + "Money"), "sa_ccr_ead": R(p + "Money"), "sa_ccr_over_alpha_eepe": N(minimum=0),
        "stressed": R(p + "StressedEpe"),
    }, "The regulatory measures beside the modelled ones: alpha times EEPE (CRE53.11) against the SA-CCR EAD, the effective "
       "maturity M of CRE53.20 (capped at 5 years) and the stressed Effective EPE.")
    d[p + "GirrScenario"] = Ob({"scenario": E("low", "medium", "high"), "k_b": N(minimum=0)},
                               "The bucket charge under one correlation scenario (MAR21.6).")
    d[p + "GirrCharge"] = Ob({
        "paragraph": C("MAR21.42 to MAR21.50"), "in_force_date": C("2023-01-01"), "currency": C("USD"),
        "sqrt2_division": C(True), "sqrt2_label": C("convention"), "sensitivities": A(N(), 10, 10, desc=SENS_DESC),
        "weighted_sensitivities": A(N(), 10, 10), "scenarios": A(R(p + "GirrScenario"), 3, 3),
        "delta_charge": R(p + "Money"), "delta_charge_undivided": R(p + "Money"),
    }, "The FRTB SA GIRR delta charge of the same book (single USD bucket): the sensitivities s_k per tenor as MAR21.19 defines "
       "them, the weighted sensitivities with "
       "the MAR21.44 division by sqrt(2) (a named convention) and the charge, the maximum over the three correlation scenarios, "
       "with the undivided charge beside it.")
    d[p + "Pit"] = N("A PIT value in (0, 1) by the (i + 1) / (N + 2) rule.", exclusiveMinimum=0, exclusiveMaximum=1)
    d[p + "Exceedance"] = Ob({"quantile": N(exclusiveMinimum=0, exclusiveMaximum=1), "count": Int(0), "expected": N(minimum=0)},
                             "The exceedances of the PFE at one quantile (a secondary row, BCBS 185 paragraph 27).")
    d[p + "BacktestHorizon"] = Ob({
        "horizon": E(*HORIZONS), "n": Int(2), "pits": A(R(p + "Pit"), 2), "exceedances": A(R(p + "Exceedance"), 2),
        "w2": N(minimum=0), "critical_iid": Ob({"p05": C(2.492), "p01": C(3.880)}),
        "critical_simulated": Ob({"p05": N(exclusiveMinimum=0), "p01": N(exclusiveMinimum=0)}),
        "effective_sample_size": N(exclusiveMinimum=0), "reject_at_5pct": B,
    }, "The PIT backtest at one horizon: the PITs, the Anderson-Darling W^2 against the critical values simulated under the "
       "model itself (same dates, overlapping horizons) with the iid table values beside them, the effective sample size and "
       "several PFE percentiles (BCBS 185 paragraph 31).")
    d[p + "BacktestHorizons"] = ordered([{"$ref": f"#/$defs/{p}BacktestHorizon", "properties": {"horizon": {"const": h}}}
                                         for h in HORIZONS],
                                        "The six horizons in order: 10 and 20 business days, 1, 3, 6 and 12 months.")
    d[p + "SubWindowResult"] = Ob({"horizon": E(*HORIZONS), "n": Int(1), "w2": N(minimum=0)}, "W^2 of one horizon in a sub-window.")
    d[p + "SubWindow"] = Ob({
        "window": E(*SUB_WINDOWS), "start": DATE, "end": DATE, "results": A(R(p + "SubWindowResult"), 1),
    }, "One reporting sub-window of the backtest (D7).")
    d[p + "Backtest"] = Ob({
        "window_start": MONTHDATE(), "window_end": MONTHDATE(), "dates": A(DATE, 3),
        "calibration_rule": C("each initialisation date is calibrated on data up to that date only"),
        "pit_rule": C("(i + 1) / (N + 2)"), "statistic": C("Anderson-Darling W^2"),
        "paths_per_date": Int(1), "book_horizons": R(p + "BacktestHorizons"),
        "risk_factor": Ob({"proxy_tenor_years": N(exclusiveMinimum=0), "horizons": R(p + "BacktestHorizons")}),
        "sub_windows": ordered([{"$ref": f"#/$defs/{p}SubWindow", "properties": {"window": {"const": w}}} for w in SUB_WINDOWS],
                               "before 2008, 2008 to 2019, from 2020, in that order."),
    }, "The PIT-based exposure backtest (B5): the book revalued on the realised curves, and the risk factor (the short-rate "
       "proxy) backtested as well (BCBS 185 paragraph 20).")
    d[p + "SensitivityCase"] = Ob({
        "case": E("base", "a-plus-1se", "a-minus-1se", "sigma-plus-1se", "sigma-minus-1se"), "a": N(exclusiveMinimum=0),
        "sigma": N(exclusiveMinimum=0), "eepe": R(p + "Money"), "pfe_peak": R(p + "Money"),
        "ee": R(p + "NonNegProfile"), "pfe": R(p + "NonNegProfile"),
    }, "EE and PFE (the profiles and their summaries) under the base calibration and with a and sigma moved by one standard error "
       "(B6).")
    d[p + "PointAgreement"] = Ob({"t": N(exclusiveMinimum=0), "difference": N(), "combined_se": N(minimum=0), "within_two_se": B},
                                 "The agreement at one grid point: the difference ORE minus Python, the combined Monte Carlo "
                                 "standard error and whether the difference is within two of them.")
    d[p + "ScalarAgreement"] = Ob({"python": N(), "ore": N(), "difference": N(), "combined_se": N(minimum=0), "within_two_se": B},
                                  "The agreement of one scalar (EEPE or CVA): the Python value, the ORE value, their difference "
                                  "(ORE minus Python), the combined standard error and the two-standard-error flag.")
    d[p + "OreReconciliation"] = one_of(Ob({
        "status": E("reconciled", "not-applicable"), "ore_version": nullable(C("1.8.17.0")), "platform": nullable(S(minLength=1)),
        "run_seconds": nullable(N(minimum=0)), "ore_ee": nullable(R(p + "NonNegProfile")),
        "ore_ee_discounted": nullable(R(p + "NonNegProfile")), "ore_eepe": nullable(R(p + "Money")),
        "ore_cva": nullable(R(p + "Money")), "ore_dim": nullable(R(p + "NonNegProfile")),
        "agreement": nullable(A(R(p + "PointAgreement"), 2)), "eepe_agreement": nullable(R(p + "ScalarAgreement")),
        "cva_agreement": nullable(R(p + "ScalarAgreement")), "dim_agreement": nullable(A(R(p + "PointAgreement"), 2)),
        "all_within_two_se": nullable(B), "reason": nullable(R(p + "Label")),
    }, "The reconciliation of the Python measures against ORE 1.8.17.0 on the same curve and model parameters (ADR-0069: the "
       "bake's): the EE profile at every grid point, the EEPE and the CVA recomputed from the ORE profiles, and for the initial-"
       "margin variant the DIM profile, each with its agreement. Every variant but the wrong-way one is reconciled (S2); the "
       "wrong-way one is not-applicable with its reason. An ORE run that fails stops the bake: a variant is never published as "
       "not-applicable because ORE failed."),
        {"status": C("reconciled"), "ore_version": C("1.8.17.0"), "platform": {"type": "string"}, "run_seconds": {"type": "number"},
         "ore_ee": R(p + "NonNegProfile"), "ore_ee_discounted": R(p + "NonNegProfile"), "ore_eepe": R(p + "Money"),
         "ore_cva": R(p + "Money"), "agreement": {"type": "array"}, "eepe_agreement": R(p + "ScalarAgreement"),
         "cva_agreement": R(p + "ScalarAgreement"), "all_within_two_se": {"type": "boolean"}, "reason": {"type": "null"}},
        {"status": C("not-applicable"), "ore_version": {"type": "null"}, "platform": {"type": "null"},
         "run_seconds": {"type": "null"}, "ore_ee": {"type": "null"}, "ore_ee_discounted": {"type": "null"},
         "ore_eepe": {"type": "null"}, "ore_cva": {"type": "null"}, "ore_dim": {"type": "null"}, "agreement": {"type": "null"},
         "eepe_agreement": {"type": "null"}, "cva_agreement": {"type": "null"}, "dim_agreement": {"type": "null"},
         "all_within_two_se": {"type": "null"}, "reason": R(p + "Label")})
    return d


def MONTHDATE() -> dict:
    return S(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


def c12_outputs() -> dict:
    p = "c12"
    d = c12_defs()
    props = {
        "kind": C("swap-exposure"), "variant": E(*VARIANTS), "sign_convention": R(p + "Sign"), "units": R(p + "Units"),
        "named_parameters": R(p + "NamedParameters"), "book": R(p + "Book"), "curve": R(p + "Curve"),
        "calibration_used": R(p + "Calibration"), "exposure": R(p + "Exposure"), "netting_benefit": R(p + "NettingBenefit"),
        "collateral": nullable(R(p + "Collateral")), "initial_margin": nullable(R(p + "Im")), "cva_dva": R(p + "Cva"),
        "wrong_way_risk": nullable(R(p + "Wwr")), "sa_ccr": R(p + "SaCcr"), "ba_cva": R(p + "BaCva"),
        "regulatory_comparison": R(p + "Regulatory"), "girr": R(p + "GirrCharge"), "backtest": R(p + "Backtest"),
        "calibration_sensitivity": A(R(p + "SensitivityCase"), 5, 5), "ore_reconciliation": R(p + "OreReconciliation"),
    }
    ob = Ob(props, "The outputs of one C12 variant: the book, the curve, the calibration, the exposure measures, CVA and DVA, "
                   "the regulatory measures, the backtest and the ORE reconciliation.")

    def alt(variant, basis, mpor, trades, coll, im, wwr):
        a = {"variant": C(variant),
             "exposure": {"type": "object", "properties": {"basis": C(basis)}, "required": ["basis"]},
             "book": {"type": "object", "properties": {"trades": trades}, "required": ["trades"]},
             "collateral": {"type": "null"} if not coll else {"type": "object", "properties": {"csa": {"type": "object", "properties": {
                 "mpor_business_days": C(mpor)}, "required": ["mpor_business_days"]}}, "required": ["csa"]},
             # the SA-CCR block is margined exactly when the variant has a CSA, with the CSA's MPoR (CRE52.50, CRE52.52)
             "sa_ccr": {"type": "object", "properties": {"margined": C(bool(coll)), "mpor_business_days": C(mpor)},
                        "required": ["margined", "mpor_business_days"]},
             "initial_margin": R(p + "Im") if im else {"type": "null"},
             "wrong_way_risk": R(p + "Wwr") if wwr else {"type": "null"}}
        # S2: ORE reconciles every variant but the wrong-way one (a different model); the IM variant carries ORE's DIM (B2)
        a["ore_reconciliation"] = {"type": "object", "properties": {"status": C("not-applicable" if wwr else "reconciled")},
                                   "required": ["status"]}
        if im:
            a["ore_reconciliation"]["properties"].update({"ore_dim": R(p + "NonNegProfile"), "dim_agreement": {"type": "array"}})
            a["ore_reconciliation"]["required"] += ["ore_dim", "dim_agreement"]
        elif not wwr:
            a["ore_reconciliation"]["properties"].update({"ore_dim": {"type": "null"}, "dim_agreement": {"type": "null"}})
        return a

    one = {"minItems": 1, "maxItems": 1}
    many = {"minItems": 2}
    alts = [
        alt("single-swap", "uncollateralised", None, one, False, False, False),
        alt("netting-set", "uncollateralised", None, many, False, False, False),
        alt("csa-mpor-10d", "collateralised-vm", 10, many, True, False, False),
        alt("csa-mpor-20d", "collateralised-vm", 20, many, True, False, False),
        alt("with-im", "collateralised-vm-im", 10, many, True, True, False),
        alt("wrong-way-risk", "uncollateralised", None, many, False, False, True),
    ]
    # conditional on the variant (if/then), so the outputs object stays one plain object for the descriptors of the views
    ob["allOf"] = [{"if": {"properties": {"variant": a["variant"]}, "required": ["variant"]}, "then": {"properties": a}} for a in alts]
    d[p + "Outputs"] = ob
    return d


def c12_models() -> dict:
    p = "c12"
    d = c12_defs()
    d[p + "GirrParameters"] = Ob({
        "paragraph": C("MAR21.42 to MAR21.50, MAR21.99"), "in_force_date": C("2023-01-01"),
        "tenors_years": ordered([C(t) for t in GIRR_TENORS], "The ten GIRR delta tenors of MAR21.8."),
        "risk_weights": ordered([C(w) for w in GIRR_RW], "MAR21.42 Table 1, in the order of the tenors."),
        "correlation_percent": A(A(N(minimum=40, maximum=100), 10, 10), 10, 10,
                                 "MAR21.46 Table 2 (percent): the table is the primary value, the formula max(exp(-0.03 |Tk - Tl| / "
                                 "min(Tk, Tl)), 40%) a reconstructed check."),
        "same_tenor_other_curve": C(0.999), "gamma_between_buckets": C(0.5), "curvature_shock": C(0.017),
        "sqrt2_divisor": C(1.4142135623730951), "sqrt2_applies_to": C("USD, a specified currency (MAR21.44 footnote 12)"),
        "vega": Ob({"liquidity_horizon_days": C(60), "risk_weight": C(1.0), "correlation_alpha": C(0.01),
                    "footnote_24_formula": C("not transcribed (UNVERIFIED)")}),
    }, "The GIRR parameters of the addendum's R7, transcribed. A swap book has no vega, so the vega formula of footnote 24 is "
       "not needed and not transcribed.")
    d[p + "CreditCurve"] = Ob({
        "base": C("US Treasury HQM corporate spot curve minus the Treasury zero curve of the same date"),
        "label": C("proxy"), "derivation": R(p + "Label"), "source_url": S(minLength=1),
        "licence_class": C("mirror-allowed with citation"), "licence_basis": R(p + "Label"),
        "negative_spread_rule": C("a negative HQM-minus-Treasury spread is set to zero and counted, never carried as a negative spread"),
        "synthetic_spread": R(p + "Convention"),
    }, "The counterparty curve (B10): a derived AAA to A market spread, labelled a proxy; the synthetic spread stays for the "
       "BA-CVA rating and the sensitivity rows.")
    d[p + "Fit"] = Ob({
        "estimator": C("exact AR(1) OLS on the shortest Treasury zero rate (Brigo et al., arXiv 0812.4210, equations 55 to 57)"),
        "calibrations": A(R(p + "Calibration"), 2), "min_history_years": C(3),
        "closed_forms_source": C("QuantLib 1.44: hullwhite.hpp, hullwhite.cpp, jamshidianswaptionengine.cpp"),
        "closed_forms_status": C("formulas transcribed from the engine source; the journal derivations are UNVERIFIED as papers"),
        "credit_curve": R(p + "CreditCurve"), "girr_parameters": R(p + "GirrParameters"),
        "limits": A(R(p + "Label"), 1),
    }, "The HW1F calibration per backtest date with its sample window (which ends before the date), the counterparty curve, "
       "the GIRR parameters and the stated limits of the case.")
    d[p + "Fit"]["description"] += " The calibration dates are unique and increasing."
    return d


# ------------------------------------------------------------------------------------------------------------ regulatory

CALCULATORS = ["standardised-credit-risk-weights", "output-floor", "sa-ccr", "ba-cva", "frtb-sbm", "frtb-liquidity-cascade"]
PARA = r"^(CRE|RBC|MAR)\d+(\.\d+)?$"
EXPOSURE_CLASSES = ["sovereign", "eca", "bank-ecra", "bank-scra", "corporate", "retail", "equity", "residential-re", "commercial-re",
                    "defaulted", "ccf", "currency-mismatch"]
#: the keys the engine's standardised.lookup takes: rating buckets, grades, kinds and an LTV as a string of the number
CRE20_KEYS = ["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to B-", "below B-", "unrated", "BB+ to BB-", "below BB-",
              "0", "1", "2", "3", "4", "5", "6", "7", "A", "B", "C", "investment-grade-unrated", "sme-unrated",
              "regulatory-retail-sme", "regulatory", "transactor", "other", "equity", "speculative-unlisted",
              "legislated-programme", "subordinated-debt", "0.5", "0.6", "0.8", "0.9", "1.0", "1.5",
              "provision-below-20pct", "provision-at-least-20pct", "residential-non-cash-flow-dependent", "multiplier", "cap",
              *sm.CCF]
CHAPTERS = sorted(sm.IN_FORCE)
TABLE_IDS = ["cre52-72-table-2", "mar50-16-table-1", "mar33-12-table-2", "mar33-4-table-1"]


def regulatory_defs() -> dict:
    p = "regulatory"
    d: dict = {}
    d[p + "Value"] = Ob({
        "name": S(minLength=1), "symbol": S(minLength=1),
        "value": {"type": ["number", "string", "array"], "items": {"type": "number"},
                  "description": "A number, a string (a currency, a position, an option type, an entity) or an array of numbers "
                                 "(a vector or a matrix in row-major order)."},
        "unit": S(minLength=1), "basis": E("transcribed", "recomputed", "constructed"),
        "paragraph": S(pattern=PARA, description="The paragraph this value comes from, for example CRE52.23."),
    }, "One named value: an input or an output, with its unit, the paragraph it comes from and its basis: transcribed from a source "
       "line, recomputed from the inputs by the engine's formulas, or constructed by the fixture for an invariant.")
    d[p + "Published"] = Ob({
        "name": S(minLength=1), "value": N(), "unit": S(minLength=1), "rounding": E("nearest integer", "3 decimal places",
                                                                                       "4 decimal places", "none"),
        "paragraph": S(pattern=PARA),
    }, "A value the framework publishes for a worked example (for example the EAD after rounding to an integer, or the multiplier to "
       "three decimals); it must equal the recomputed output rounded as stated.")
    d[p + "Trade"] = Ob({
        "trade_id": S(minLength=1), "nature": S(minLength=1), "paragraph": S(pattern=PARA),
        "terms": A(R(p + "Value"), 1),
    }, "One trade of a worked example with its contractual terms as values (strings for currency, position and option type), "
       "transcribed from the CRE99 table with its paragraph.")
    d[p + "Entry"] = Ob({
        "id": S(pattern=r"^[a-z0-9-]+$"), "calculator": E(*CALCULATORS), "title": TXT,
        "kind": E("official-example", "invariant"),
        "paragraph": S(pattern=PARA, description="The paragraph (or the first paragraph of a range) of the rule."),
        "paragraph_range": S(minLength=1), "in_force_date": DATE, "published_date": DATE, "source": S(minLength=1),
        "trades": A(R(p + "Trade")),
        "inputs": A(R(p + "Value"), 1), "outputs": A(R(p + "Value"), 1), "published": A(R(p + "Published")),
        "statement": nullable(TXT), "holds": nullable(B), "tolerance_relative": C(1e-9),
    }, "A calculator entry of the regulation page: the trades (for an SA-CCR example), the inputs, the engine's outputs, the values "
       "the framework publishes, the paragraph and the in-force date of the chapter. The live ports are held to it at 1e-9 relative.")
    d[p + "Entry"] = one_of(d[p + "Entry"],
                            {"kind": C("official-example"), "published": {"minItems": 1}, "statement": {"type": "null"},
                             "holds": {"type": "null"}},
                            {"kind": C("invariant"), "published": {"maxItems": 0}, "statement": TXT, "holds": C(True)})
    d[p + "GridRow"] = Ob({
        "exposure_class": E(*EXPOSURE_CLASSES), "key": E(*CRE20_KEYS), "band": S(minLength=1),
        "short_term": B, "cash_flow_dependent": B, "counterparty_weight": nullable(N(minimum=0)),
        "risk_weight": N(minimum=0), "table": S(minLength=1),
        "paragraph": S(pattern=PARA), "in_force_date": DATE,
    }, "One cell of the CRE20 lookup grid, keyed as the engine's standardised.lookup(exposure_class, key, short_term, "
       "cash_flow_dependent, counterparty_weight): the risk weight as a decimal, the band as the table prints it, the table, its "
       "paragraph and the in-force date of the chapter. For an LTV band the key is a representative LTV (the upper edge, or 1.5 "
       "above 1.0 and 1.0 above 0.8).")
    d[p + "PhaseIn"] = Ob({
        "year": Int(2023), "effective_from": DATE, "factor": N(exclusiveMinimum=0, maximum=1), "table": C("RBC90.1 Table 1"),
        "paragraph": C("RBC90.1"), "in_force_date": DATE,
    }, "One row of the output-floor phase-in (RBC90.1 Table 1): the year, the date it applies from and the floor factor.")
    d[p + "ParameterRow"] = Ob({"key": S(minLength=1), "parameter": S(minLength=1), "value": N(), "unit": S(minLength=1)},
                               "One parameter of a regulatory table: the row key, the parameter's name, its value and its unit.")
    d[p + "ParameterTable"] = Ob({
        "id": E(*TABLE_IDS), "title": TXT, "calculator": E(*CALCULATORS), "table": S(minLength=1), "paragraph": S(pattern=PARA),
        "in_force_date": DATE, "source": S(minLength=1), "rows": A(R(p + "ParameterRow"), 1),
    }, "A parameter table the live ports display (CRE52.72 Table 2, MAR50.16 Table 1, MAR33.4 Table 1, MAR33.12 Table 2), with its "
       "paragraph and the in-force date of the chapter.")
    d[p + "Engine"] = Ob({"name": C("riskvalidation"), "version": S(minLength=1)}, "The engine release that produced the outputs.")
    d[p + "Units"] = Ob({"money": C("as stated per value (USD thousands for CRE99, index points for RBC20.13)"),
                         "rate": C("decimal"), "dates": C("ISO-8601")}, "Units of every number, per value.")
    return d


def regulatory_doc() -> dict:
    p = "regulatory"
    d = regulatory_defs()
    root = Ob({
        "schema": C("contraste.regulatory/v1"), "case_id": C("REGULATORY"), "document_id": S(minLength=1),
        "engine": R(p + "Engine"), "units": R(p + "Units"),
        "official_examples": A(R(p + "Entry"), 7),
        "invariant_cases": A(R(p + "Entry"), 7), "output_floor_phase_in": A(R(p + "PhaseIn"), 6, 6),
        "parameter_tables": A(R(p + "ParameterTable"), 4, 4), "cre20_grid": A(R(p + "GridRow"), 1),
        "provenance": {"$ref": "../common/provenance.schema.json"}, "lane": {"$ref": "../common/lane-block.schema.json"},
    }, "The regulatory-calculators document.")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}regulatory/calculators.schema.json",
        "title": "Regulatory calculators",
        "description": "The official worked examples (the five CRE99 SA-CCR netting sets from their trades, the RBC20.13 output floor) "
                       "and the invariant cases (BA-CVA, the FRTB SBM aggregation with its cross-bucket fallback, the liquidity-"
                       "horizon cascade) of the regulatory calculators run through the engine, the output-floor phase-in, the "
                       "parameter tables and a CRE20 lookup grid, each with its paragraph and in-force date. The live ports of the "
                       "regulation page are held to this document at 1e-9 relative.",
        **{k: v for k, v in root.items() if k != "description"},
        "$defs": reachable_of(root, d),
    }


def reachable_of(root: dict, defs: dict) -> dict:
    holder = "__root__"
    return {k: v for k, v in reachable(holder, {**defs, holder: root}).items() if k != holder}


def main() -> None:
    d = c12_outputs()
    U.variant_schema("C12", "variant-swap-exposure", "swap-exposure", "C12 variant (swap exposure, CVA and SA-CCR)",
                     "One variant of case C12 (swap exposure, CVA and SA-CCR): the six SDD variants share this schema and are "
                     "told apart by outputs.variant. Every object is closed and nothing is optional; a block a variant does not "
                     "run is null.", "c12Outputs", d)
    # the calibrations of the variant document must be as the SDD says: only ccr.* tests
    path = SCHEMAS / "c12" / "variant-swap-exposure.schema.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["allOf"].append({"properties": {"tests": {"items": {"properties": {"test_id": {"pattern": r"^ccr\."}}}}}})
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    m = c12_models()
    U.models_schema("C12", "C12 models (HW1F calibration per backtest date)",
                    "The C12 models document: the Hull-White one-factor calibration per backtest date with its sample window, "
                    "the counterparty curve, the transcribed GIRR parameters and the stated limits.", "c12Fit", m)
    doc = regulatory_doc()
    out = SCHEMAS / "regulatory" / "calculators.schema.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
