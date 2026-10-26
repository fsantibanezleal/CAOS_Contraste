"""The c14-models document: the shock tables, the caps, the multipliers and the fits of the valuation dates.

``fit.nmd_models`` holds, per valuation date, the replicating portfolio fitted on the quarters up to the date (the engine's
``replicating_portfolio``), its weighted average maturity, margin volatility, the deposit betas and the weights of the stability
windows. ``nmd_parameter_changes`` lists the parameters between consecutive dates and flags a change that coincides with a breach
of the standardised outlier test at the later date (the engine's ``behavioural_change_at_breach`` states the same rule).
"""
from __future__ import annotations

from typing import Any

from riskvalidation.irrbb import shocks
from riskvalidation.irrbb import slotting as rv_slotting

from . import assumptions as asm
from .slotting import t
from .variant import BANK, MID, SHOCKS, SIGN, UNITS, VariantResult

EN = ["Overnight", "O/N to 1M", "1M to 3M", "3M to 6M", "6M to 9M", "9M to 1Y", "1Y to 1.5Y", "1.5Y to 2Y", "2Y to 3Y", "3Y to 4Y",
      "4Y to 5Y", "5Y to 6Y", "6Y to 7Y", "7Y to 8Y", "8Y to 9Y", "9Y to 10Y", "10Y to 15Y", "15Y to 20Y", "Over 20Y"]
ES = ["A la vista", "Hasta 1M", "1M a 3M", "3M a 6M", "6M a 9M", "9M a 1A", "1A a 1,5A", "1,5A a 2A", "2A a 3A", "3A a 4A",
      "4A a 5A", "5A a 6A", "6A a 7A", "7A a 8A", "8A a 9A", "9A a 10A", "10A a 15A", "15A a 20A", "Más de 20A"]
TABLES = {
    "2024": ("SRP31.90 Table 2 (in force 2026-01-01; d578 recalibration, dossier 01 H.3)", "January 2000 to December 2023",
             "99.9th percentile of local rolling six-month average absolute changes", 25),
    "2016": ("BCBS d368 Annex 2 Table 1 (dossier 01 H.3)", "2000 to 2015", "99th percentile of global factors", 50),
}


def _rows(calibration: str) -> list[dict[str, Any]]:
    return [{"currency": c, "parallel_bp": p, "short_bp": s, "long_bp": lg} for c, (p, s, lg) in shocks.shock_table(calibration).items()]


def _applied(calibration: str) -> dict[str, Any]:
    z = shocks.shock_size("USD", calibration)
    return {"currency": z.currency, "parallel_bp": z.parallel_bp, "short_bp": z.short_bp, "long_bp": z.long_bp, "origin": z.origin,
            "label": z.label, "method": z.method}


def models_document(dates: list[str], results: dict[str, VariantResult]) -> dict[str, Any]:
    """The fit block (``dates`` in order, ``results`` by valuation date)."""
    nmd_models = []
    for vd in dates:
        fit = results[vd].fit
        beta = fit["beta"]
        mv = fit["fit"]["margin_volatility"]
        nmd_models.append({
            "valuation_date": vd, "category": "wholesale",
            "tranches": [{"maturity_years": m, "weight": w} for (_, m), w in zip(asm.TRANCHES, fit["fit"]["weights"])],
            "weights_sum": float(sum(fit["fit"]["weights"])),
            "weighted_average_maturity_years": fit["fit"]["weighted_average_maturity_years"],
            "margin_volatility": mv,
            "margin_volatility_reason": None if mv is not None else t("The window holds too few quarters for a margin volatility.",
                                                                       "La ventana tiene muy pocos trimestres para una volatilidad del margen."),
            "deposit_beta": {"up": beta["up"], "down": beta["down"], "source_kind": "fitted",
                             "source": f"{asm.REGISTRY['deposit_beta'].source} {beta['n_up']} quarters up, {beta['n_down']} down. One "
                                       "series (the bank's cost of deposits) stands for all non-maturity deposits and is filed under "
                                       "the dominant category."},
            "stability": [{"window_start": w["window_start"], "window_end": w["window_end"], "weights": w["weights"],
                           "weighted_average_maturity_years": w["weighted_average_maturity_years"]} for w in fit["stability"]]})
    changes = []
    req = asm.REQUESTS["wholesale"]
    for a, b in zip(dates, dates[1:]):
        breach = results[b].breached
        for name, unit, va, vb, note_en, note_es in (
            ("replicating-portfolio weighted average maturity, wholesale", "years",
             results[a].fit["fit"]["weighted_average_maturity_years"], results[b].fit["fit"]["weighted_average_maturity_years"],
             "Fitted on the quarters up to each date.", "Ajustado con los trimestres hasta cada fecha."),
            ("requested core share, wholesale", "share", req.share, req.share, "Stated by Contraste; not changed between the dates.",
             "Declarado por Contraste; no cambia entre las fechas."),
            ("requested core maturity, wholesale", "years", req.maturity, req.maturity, "Stated by Contraste; not changed between the dates.",
             "Declarado por Contraste; no cambia entre las fechas."),
        ):
            changes.append({
                "parameter": name, "category": "wholesale", "from_date": a, "to_date": b, "from_value": va, "to_value": vb, "unit": unit,
                "limit_breach_in_window": bool(breach), "flagged": bool(va != vb and breach),
                "note": t(f"{note_en} The standardised outlier test is {'breached' if breach else 'not breached'} at {b}.",
                          f"{note_es} El umbral de la prueba estandarizada de valores atípicos {'se excede' if breach else 'no se excede'} al {b}.")})  # "se supera" read as "passes" (superar una prueba): the threshold is what is exceeded (R2b c15 m4)
    return {
        "currency": "USD", "sign_convention": SIGN, "units": UNITS, "bank": BANK,
        "buckets": [{"bucket": k + 1, "label": t(EN[k], ES[k]), "midpoint_years": float(MID[k])} for k in range(19)],
        "shock_tables": [{"calibration": c, "source": TABLES[c][0], "data_window": TABLES[c][1], "percentile": TABLES[c][2],
                          "rounding_bp": TABLES[c][3], "rows": _rows(c)} for c in ("2024", "2016")],
        "applied_sizes": [_applied("2024"), _applied("2016")],
        "shock_shape": {"x": 4, "steepener_short": -0.65, "steepener_long": 0.9, "flattener_short": 0.8, "flattener_long": -0.6,
                        "short_form": "exp(-t_k / x)", "long_form": "1 - exp(-t_k / x)", "reference": "SRP31.91 to SRP31.92"},
        "nmd_caps": [{"category": c, "core_share_cap": cs, "core_maturity_cap_years": cm,
                      "reference": "SRP31 Table 4 (SRP31.107 to SRP31.112)"} for c, (cs, cm) in asm.CAPS.items()],
        "multipliers": {
            "prepayment_gamma": [{"shock": s, "gamma": g} for s, g in zip(SHOCKS, (0.8, 1.2, 0.8, 1.2, 0.8, 1.2))],
            "term_deposit_u": [{"shock": s, "u": u} for s, u in zip(SHOCKS, (1.2, 0.8, 0.8, 1.2, 1.2, 0.8))],
            "reference": "SRP31.119 Table 5 and SRP31.125 Table 6"},
        "nmd_models": nmd_models, "nmd_parameter_changes": changes,
        "outlier": {"threshold_share_tier1": 0.15, "reference": "SRP31.82 to SRP31.83"}}


def check_multipliers() -> None:
    """The tabled multipliers equal the engine's (the models document repeats the contract tables; a test compares them)."""
    for s, g, u in zip(SHOCKS, (0.8, 1.2, 0.8, 1.2, 0.8, 1.2), (1.2, 0.8, 0.8, 1.2, 1.2, 0.8)):
        assert rv_slotting.prepayment_cpr(s, 0.5) == 0.5 * g and rv_slotting.term_deposit_redemption_rate(s, 0.5) == 0.5 * u
