"""The c15-models document: the Annex 1 tables, the caps, the multipliers, the curve fits, the calibration targets and the behavioural models.

``fit.curve_models`` repeats the Nelson-Siegel fit of each curve; ``fit.calibration_targets`` holds each CMF aggregate the book is calibrated to
with the value the book achieves; ``fit.nmd_models`` holds the stated replicating portfolio of each non-maturity deposit category (synthetic:
the synthetic bank has no deposit-rate history to estimate one from, so the margin volatility is absent with its reason and the stability
table has the one window of the valuation month). The tables are the engine's (``shock_table``); the document repeats them and a test compares.
"""
from __future__ import annotations

from typing import Any

from riskvalidation.irrbb import shocks
from riskvalidation.irrbb import slotting as rv_slotting

from . import assumptions as asm
from . import curves as c15_curves
from .book import MID, Book, t
from .variant import SHOCKS, SIGN, UNITS, UR_FLOOR, OTHER_FLOOR, _size, bank_block

EN = ["Overnight", "O/N to 1M", "1M to 3M", "3M to 6M", "6M to 9M", "9M to 1Y", "1Y to 1.5Y", "1.5Y to 2Y", "2Y to 3Y", "3Y to 4Y",
      "4Y to 5Y", "5Y to 6Y", "6Y to 7Y", "7Y to 8Y", "8Y to 9Y", "9Y to 10Y", "10Y to 15Y", "15Y to 20Y", "Over 20Y"]
ES = ["A la vista", "Hasta 1M", "1M a 3M", "3M a 6M", "6M a 9M", "9M a 1A", "1A a 1,5A", "1,5A a 2A", "2A a 3A", "3A a 4A",
      "4A a 5A", "5A a 6A", "6A a 7A", "7A a 8A", "8A a 9A", "9A a 10A", "10A a 15A", "15A a 20A", "Más de 20A"]
ANNEX1 = "RAN 21-13 Annex 1 (dossier 03 F.2)"
THRESHOLDS = (("nii-tier1", 0.05, "Tier 1 capital"), ("eve-tier1", 0.15, "Tier 1 capital"),
              ("nii-margin", 0.18, "net interest and indexation margin, 12 months"))


def models_document(book: Book, sel: c15_curves.Selection, fits: dict[str, c15_curves.CurveFit], calibration_source: str) -> dict[str, Any]:
    vd = sel.valuation_date
    table = shocks.shock_table("cmf-annex1")
    nmd_models = []
    for cat, rep in book.replicating.items():
        nmd_models.append({
            "valuation_date": vd, "category": cat,
            "tranches": [{"maturity_years": m, "weight": w} for m, w in zip(rep["maturities"], rep["weights"])],
            "weights_sum": float(sum(rep["weights"])), "weighted_average_maturity_years": rep["weighted_average_maturity_years"],
            "margin_volatility": None,
            "margin_volatility_reason": t("The synthetic bank has no history of client rates to estimate the margin of the replicating portfolio from; "
                                          "the portfolio is a stated synthetic assumption. It is built from the requested core maturity, which stands above the Table 4 cap for "
                                          "retail-operational and wholesale deposits: the standardised treatment of the variant documents uses the capped values "
                                          "(core_share_used and core_maturity_used_years of nmd_segments), not these weights.",
                                          "El banco sintético no tiene historia de tasas a clientes para estimar el margen de la cartera replicante; "
                                          "la cartera es un supuesto sintético declarado. Se construye con el plazo estable solicitado, que supera el tope de la Tabla 4 en los "
                                          "depósitos retail operacionales y mayoristas: el tratamiento estándar de los documentos de variante usa los valores con tope "
                                          "(core_share_used y core_maturity_used_years de nmd_segments), no estos pesos."),
            "deposit_beta": {"up": asm.DEPOSIT_BETA, "down": asm.DEPOSIT_BETA, "source_kind": "synthetic-stated",
                             "source": asm.REGISTRY["deposit_beta"].source},
            "stability": [{"window_start": sel.first, "window_end": vd, "weights": rep["weights"],
                           "weighted_average_maturity_years": rep["weighted_average_maturity_years"]}]})
    return {
        "reporting_currency": "CLP", "sign_convention": SIGN, "units": UNITS, "bank": bank_block(book.seed, calibration_source),
        "buckets": [{"bucket": k + 1, "label": t(EN[k], ES[k]), "midpoint_years": float(MID[k])} for k in range(19)],
        "annex1_table": [{"basket": b, "parallel_bp": v[0], "short_bp": v[1], "long_bp": v[2]} for b, v in table.items()],
        "eve_shock_sizes": [_size(shocks.shock_size("CLP", "cmf-annex1")), _size(shocks.shock_size("CLF", "cmf-annex1"))],
        "floors": {"ur_floor": UR_FLOOR, "other_floor": OTHER_FLOOR, "reference": "RAN 21-13 Annex 1 Hoja 9 (dossier 03 F.2)"},
        "prioritised_thresholds": [{"id": i, "threshold": th, "base": b} for i, th, b in THRESHOLDS],
        "offset_share": 0.5, "indexation_rate": 0.025,
        "multipliers": {
            "prepayment_gamma": [{"shock": s, "gamma": rv_slotting.prepayment_cpr(s, 0.5) / 0.5} for s in SHOCKS],
            "term_deposit_u": [{"shock": s, "u": rv_slotting.term_deposit_redemption_rate(s, 0.5) / 0.5} for s in SHOCKS],
            "reference": f"SRP31.119 Table 5 and SRP31.125 Table 6; {ANNEX1} repeats both"},
        "nmd_caps": [{"category": c, "core_share_cap": cs, "core_maturity_cap_years": cm, "reference": f"SRP31 Table 4; {ANNEX1} repeats the numbers"}
                     for c, (cs, cm) in asm.CAPS.items()],
        "curve_models": [{"curve": c, "month": sel.month, "series_codes": fits[c].block["series_codes"], "model": "nelson-siegel",
                          "parameters": fits[c].block["fit"]["parameters"], "rmse_bp": fits[c].block["fit"]["rmse_bp"],
                          "attribution": fits[c].block["attribution"]} for c in ("CLP", "UR")],
        "calibration_targets": book.calibration_rows(),
        "nmd_models": nmd_models,
        "prepayment": {"model": "cpr-constant", "cpr_base": asm.PREPAYMENT_CPR, "psa_percent": None, "source_kind": "synthetic-stated",
                       "source": asm.REGISTRY["prepayment_cpr"].source}}


def check_multipliers() -> None:
    """The tabled multipliers equal the engine's (the models document repeats the contract tables; a test compares them)."""
    for s, g, u in zip(SHOCKS, (0.8, 1.2, 0.8, 1.2, 0.8, 1.2), (1.2, 0.8, 0.8, 1.2, 1.2, 0.8)):
        assert rv_slotting.prepayment_cpr(s, 0.5) == 0.5 * g and rv_slotting.term_deposit_redemption_rate(s, 0.5) == 0.5 * u
