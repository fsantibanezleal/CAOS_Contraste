"""The models document of C16 (``c16-models``): the transcribed parameter sets with their sources, the calibration on the pre-2023
Table A.1 rows, the goldens, and the depositor generator with its known truth.

The tables are the engine's (``riskvalidation.liquidity.runoff``), repeated here with their source so a reader can see what the
variants ran on; a test compares the two. The fast-run rate is calibrated on the rows dated before 2023 only: the engine refuses a
2023 row when the call is marked scored (decision Q4), and the 2023 rows are what the variants are scored against.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.liquidity import runoff, scenarios
from riskvalidation.liquidity.deposits import DepositorConfig, DepositorGenerator, DepositorSegment

from ...io.fdic import Report
from . import balance
from .assumptions import txt
from .document import model_summary
from .variant import BANK, UNITS, _anchor

#: the item names of the contract (``c16-models``) and the key each one has in the engine's tables
OUTFLOW_ITEMS = (("securities-issued", "securities-issued"), ("secured-funding", "secured-funding"), ("stable-retail", "stable-retail"),
                 ("other-retail", "other-retail"), ("operational", "operational"),
                 ("non-operational-credit-institutions", "non-operational-credit-institutions"),
                 ("non-operational-other-financial", "non-operational-other-financial"),
                 ("non-operational-non-financial-corporates", "non-operational-non-financial-corporates"),
                 ("non-operational-others", "non-operational-others"), ("fx-swaps", "fx-swaps"), ("derivatives-payable", "derivatives"),
                 ("other-cash-outflows", "other-cash-outflows"))
INFLOW_ITEMS = (("secured-lending", "secured-lending"), ("loans-retail", "loans-retail"), ("loans-non-financial-corporates", "loans-non-financial-corporates"),
                ("loans-credit-institutions", "loans-credit-institutions"), ("loans-other-financial", "loans-other-financial"),
                ("loans-others", "loans-others"), ("fx-swaps", "fx-swaps"), ("derivatives-receivable", "derivatives"),
                ("paper-own-portfolio", "own-paper"), ("other-cash-inflows", "other-inflows"))
OPEN_ITEMS = ("open-repos", "stable-retail", "other-retail", "operational", "non-operational-credit-institutions", "non-operational-other-financial",
              "non-operational-non-financial-corporates", "non-operational-others", "other-transactions")
DRAWDOWN_ITEMS = ("committed-credit-facilities", "liquidity-facilities")
#: the compounding goldens of the document: id, the LiST severity and class (or facility) the rate is read from, the days, the label
GOLDENS = (("stable-retail-adverse", "adverse", "stable-retail", 125, "dossier-05-line-237"),
           ("stable-retail-extreme", "extreme", "stable-retail", 125, "recomputed"),
           ("other-retail-adverse", "adverse", "other-retail", 125, "recomputed"),
           ("non-operational-nfc-adverse-2-days", "adverse", "non-operational-non-financial-corporates", 2, "recomputed"),
           ("committed-credit-facilities-adverse-63-days", "adverse", "committed-credit-facilities", 63, "recomputed"))
P_ENTER, P_EXIT = 0.01, 0.05                  # the stress-state transition law of the generator: a convention (UNVERIFIED, contract 2.0.0)
N_DEPOSITORS = 1000                           # per segment
GENERATOR_HORIZON = 125
TRUTH_HORIZONS = (2, 5, 30, 125)
RULE = "maximum-implied-daily-rate"


def calibration(rows: list[runoff.ObservedRun], rule: str) -> tuple[dict[str, Any], scenarios.FastRun]:
    """The fast-run calibration block and its parameter set, from the rows the caller selects. The call is marked scored, so the engine
    refuses a 2023 row (decision Q4)."""
    fit = scenarios.fast_run_scenario(rows, rule, scored=True)
    pre = [r for r in runoff.TABLE_A1 if r.year < 2023]
    scored = [r for r in runoff.TABLE_A1 if r.year >= 2023]
    blk = {"split": {"calibrated_on": [r.row_id for r in pre], "scored_on": [r.row_id for r in scored]},
           "implied_daily_rates": [{"row_id": r.row_id, "implied_daily_rate": v} for r, v in zip(rows, fit.implied_rates)],
           "fitted_daily_rate": {"value": fit.daily_rate, "unit": "decimal-per-day", "source_kind": "calibrated-pre-2023",
                                 "source": "maximum of the implied daily rates of the pre-2023 Table A.1 rows (the calibration rule)"},
           "anchor": _anchor(),
           "statement": txt("Calibrated on pre-2023 rows, scored on the 2023 rows; the SVB observation is a labelled anchor, not a forecast.",
                            "Calibrado con filas anteriores a 2023, evaluado en las filas de 2023; la observación de SVB es un ancla rotulada.")}
    return blk, fit


def pre_2023_rows() -> list[runoff.ObservedRun]:
    return [r for r in runoff.TABLE_A1 if r.year < 2023]


def generator_block(report: Report, fit_rate: float, conv: dict, seed: int, n_draws: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """The depositor generator calibrated to the call-report composition, its exact truth and its verification (a seeded large draw
    against the truth, judged by the named Monte Carlo parameters). Returns the ``generator`` block and the rows of the engine test
    ``runoff_vs_generator_truth`` (estimated, truth and standard errors of the checks that have a standard error)."""
    segs = balance.deposit_segments(report)
    total = sum(s["opening"] for s in segs)
    lst = runoff.LIST_PARAMETERS["adverse"]["open_maturity"]
    spec = {"retail-insured": (0.0, lst["other-retail"], "stress hazard: the LiST Adverse rate of other retail sight deposits"),
            "non-operational-corporate": (0.0, fit_rate, "stress hazard: the fast-run daily rate calibrated on the pre-2023 Table A.1 rows"),
            "financial": (0.0, lst["non-operational-other-financial"], "stress hazard: a financial customer's sight deposit leaves in full (LiST para 111)")}
    cfg_segments, doc_segments = [], []
    for s in segs:
        calm, stress, what = spec[s["segment"]]
        share = s["opening"] / total
        cfg_segments.append(DepositorSegment(s["segment"], share, calm, stress))
        doc_segments.append({"segment": s["segment"], "share_of_deposits": share, "calm_daily_hazard": calm, "stress_daily_hazard": stress,
                             "p_enter_stress": P_ENTER, "p_exit_stress": P_EXIT,
                             "basis": txt(f"Share of the call-report deposits mapped to the segment ({s['field']}); no withdrawal in the calm state; {what}; the "
                                          "transition law is a convention.",
                                          f"Proporción de los depósitos del reporte asignada al segmento ({s['field']}); sin retiros en calma; {what}; la ley de "
                                          "transición es una convención.")})
    # engine-liquidity-api 2.0.0 (BL-082): one stress chain shared by every depositor, so its two probabilities belong to the configuration; the
    # document still writes them on each segment row (the c16GeneratorSegment schema requires both), equal to the configuration's
    gen = DepositorGenerator(DepositorConfig(tuple(cfg_segments), N_DEPOSITORS, GENERATOR_HORIZON, P_ENTER, P_EXIT))
    truth = gen.truth()["outflow_rate"]
    rows = [{"segment": k, "horizon_days": n, "true_outflow_rate": float(truth[k][n - 1])} for k in truth for n in TRUTH_HORIZONS]
    checks = [c for c in gen.verify(n_draws, seed) if c.se > 0.0]
    worst = max(checks, key=lambda c: abs(c.observed - c.expected) / c.se)
    red = conv["generator_truth_se_red"]["value"]
    abs_err, se = abs(worst.observed - worst.expected), worst.se
    block = {"config": {"truth_status": "synthetic-known-truth", "seed": seed, "n_depositors": N_DEPOSITORS, "horizon_days": GENERATOR_HORIZON,
                        "segments": doc_segments},
             "truth": rows,
             "verification": {"n_draws": n_draws, "max_abs_error": abs_err, "mc_standard_error": se, "within_error": bool(abs_err <= red * se + 1e-15)}}
    test = {"estimated": np.array([c.observed for c in checks]), "truth": np.array([c.expected for c in checks]), "se": np.array([c.se for c in checks])}
    return block, test


def _rows(sev_keys: tuple, items: tuple[tuple[str, str], ...], table: str) -> list[dict[str, Any]]:
    p = runoff.LIST_PARAMETERS
    return [{"item": name, "baseline": p["baseline"][table][key], "adverse": p["adverse"][table][key], "extreme": p["extreme"][table][key]}
            for name, key in items]


def models_fit(report: Report, conv: dict, cal: dict[str, Any], generator: dict[str, Any]) -> dict[str, Any]:
    """The ``fit`` block of the models document."""
    p = runoff.LIST_PARAMETERS
    goldens = []
    for gid, sev, cls, n, label in GOLDENS:
        q = p[sev]["drawdown"][cls] if cls in p[sev]["drawdown"] else p[sev]["open_maturity"][cls]
        goldens.append({"id": gid, "daily_rate": q, "days": n, "cumulative_outflow": float(runoff.cumulative_outflow_constant(q, n)), "label": label})
    lo, hi, days = runoff.TABLE_A1_LCR_RANGE
    return {
        "currency": "USD", "units": UNITS, "bank": BANK, "conventions": conv,
        "parameter_sets": [
            {"set_id": "basel-lcr", "source": "riskvalidation.regulatory.lcr_nsfr (BCBS LCR20, LCR30, LCR40, LCR99, in force 2019-12-15)", "source_kind": "transcribed-basel-lcr"},
            {"set_id": "list-adverse", "source": "ECB LiST 2019 methodological note, Tables 3.2 and 3.3, Adverse", "source_kind": "transcribed-list-2019"},
            {"set_id": "list-extreme", "source": "ECB LiST 2019 methodological note, Tables 3.2 and 3.3, Extreme", "source_kind": "transcribed-list-2019"},
            {"set_id": "fast-run", "source": "calibrated on the pre-2023 Table A.1 rows by the calibration rule", "source_kind": "calibrated-pre-2023"}],
        "list_parameters": {
            "source": "ECB LiST 2019 methodological note, February 2019, Tables 3.2 and 3.3 and paras 119 to 126",
            "attribution": "European Central Bank, cited as the source; the figures are the note's own and any recomputed figure is labelled recomputed",
            "contractual_outflows": _rows((), OUTFLOW_ITEMS, "contractual_outflow"),
            "open_maturity_daily": _rows((), tuple((i, i) for i in OPEN_ITEMS), "open_maturity"),
            "contractual_inflows": _rows((), INFLOW_ITEMS, "contractual_inflow"),
            "committed_drawdown": [{"item": i, "adverse": p["adverse"]["drawdown"][i], "extreme": p["extreme"]["drawdown"][i]} for i in DRAWDOWN_ITEMS],
            "relevant_days_six_months": runoff.LIST_RELEVANT_DAYS, "relevant_days_three_months": runoff.LIST_FACILITY_DAYS,
            "results_annex": {
                "n_banks": 103, "median_survival_days": {"adverse": 176, "extreme": 122}, "unit": "days",
                "sources": {"annex": "ECB LiST 2019 results annex", "n_banks_slide": 9, "median_slides": [15], "dossier": "dossier 05 E.1 line 240"},
                "statement": txt("Reference points of the LiST 2019 stress test, not results of this model: 103 banks, median reported survival period 176 days "
                                 "under the Adverse and 122 days under the Extreme shock (results annex slides 9 and 15).",
                                 "Puntos de referencia del test de estrés LiST 2019, no resultados de este modelo: 103 bancos, periodo de supervivencia mediano "
                                 "informado de 176 días en el Adverso y 122 en el Extremo.")},
            "calendar_note": txt("The rates are defined on the 2019 TARGET2 relevant-day calendar (125 relevant days in six months); the C16 ladder runs on the "
                                 "US business-day convention.",
                                 "Las tasas se definen sobre el calendario TARGET2 de 2019 (125 días en seis meses); la escalera de C16 usa días hábiles de EE.UU.")},
        "list_goldens": goldens,
        "table_a1": {"source": "BCBS, Report on the 2023 banking turmoil (d555), Box A, Table A.1",
                     "attribution": "Bank for International Settlements, source cited; one table within the limited-extract terms (addendum L2.1)",
                     "rows": [{"row_id": r.row_id, "bank": r.bank, "year": r.year, "outflow_share": r.outflow_share, "days": r.days} for r in runoff.TABLE_A1],
                     "lcr_range": {"label": "LCR deposit outflow rates", "low": lo, "high": hi, "days": days}},
        "calibration": cal, "generator": generator,
        "sources": [{"source_id": sid, "publisher": pub, "licence_class": cls, "licence_basis": basis, "statement": txt(st + " A reading of the notice, not legal advice.", st)}
                    for sid, pub, cls, basis, st in (
            ("fdic-bankfind", "FDIC", "mirror-allowed", "unverified", "Presumed US government public data; the licence sentence is UNVERIFIED."),
            ("fed-h8", "Federal Reserve Board", "mirror-allowed", "notice-read", "Board public-domain statement."),
            ("fed-svb-review", "Federal Reserve Board", "mirror-allowed", "notice-read", "Board public-domain statement."),
            ("bcbs-d555-table-a1", "Bank for International Settlements", "mirror-allowed", "notice-read",
             "Table A.1 enters as constants with the source stated, within the BIS limited-extract terms; the rest of d555 is derived-only."),
            ("ecb-list-2019", "European Central Bank", "mirror-allowed", "notice-read",
             "Parameters used with the ECB cited, the text accurate and any modification stated."))]}


def models_summary(ev: str) -> list[dict[str, Any]]:
    return [model_summary(ev, "behavioural-ladder", details=True)]


__all__ = ["calibration", "generator_block", "models_fit", "models_summary", "pre_2023_rows"]
