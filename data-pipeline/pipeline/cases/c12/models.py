"""The c12-models document: the HW1F calibration at every backtest date with its sample window, the counterparty curve, the GIRR
parameters (transcribed in the engine) and the stated limits of the case."""
from __future__ import annotations

from typing import Any

from riskvalidation.regulatory import frtb

from . import book, calibration

CLOSED_FORMS_SOURCE = "QuantLib 1.44: hullwhite.hpp, hullwhite.cpp, jamshidianswaptionengine.cpp"
CLOSED_FORMS_STATUS = "formulas transcribed from the engine source; the journal derivations are UNVERIFIED as papers"
HQM_URL = "https://home.treasury.gov/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve"


def text(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def girr_block() -> dict[str, Any]:
    p = frtb.girr_parameters(True)
    return {"paragraph": "MAR21.42 to MAR21.50, MAR21.99", "in_force_date": "2023-01-01", "tenors_years": [float(t) for t in p.tenors],
            "risk_weights": [round(float(w), 6) for w in p.risk_weights_table],
            "correlation_percent": [[round(float(x) * 100.0, 6) for x in row] for row in p.correlation],
            "same_tenor_other_curve": round(p.same_tenor_other_curve, 6), "gamma_between_buckets": round(p.gamma, 6),
            "curvature_shock": round(p.curvature_shock_undivided, 6), "sqrt2_divisor": 2 ** 0.5,
            "sqrt2_applies_to": "USD, a specified currency (MAR21.44 footnote 12)",
            "vega": {"liquidity_horizon_days": 60, "risk_weight": 1.0, "correlation_alpha": 0.01,
                     "footnote_24_formula": "not transcribed (UNVERIFIED)"}}


def credit_curve_block() -> dict[str, Any]:
    return {"base": "US Treasury HQM corporate spot curve minus the Treasury zero curve of the same date", "label": "proxy",
            "derivation": text("The HQM end-of-month spot rate (semiannually compounded, equation 5.7a of the Treasury's XRM methodology) "
                               "converted to continuous compounding, minus the continuously compounded Treasury zero rate of the same "
                               "month end at the same maturity; survival is exp(-s t / LGD). An AAA-to-A market spread that includes "
                               "liquidity and tax effects, a floor for lower ratings.",
                               "La tasa spot HQM de fin de mes (capitalización semestral, ecuación 5.7a de la metodología XRM del "
                               "Tesoro) convertida a capitalización continua, menos la tasa cero continua del Tesoro del mismo fin de mes "
                               "al mismo plazo; la supervivencia es exp(-s t / LGD). Un spread de mercado AAA a A que incluye efectos de "
                               "liquidez e impuestos, un piso para calificaciones menores."),
            "source_url": HQM_URL, "licence_class": "mirror-allowed with citation",
            "licence_basis": text("FRED tags the HQM series Public Domain: Citation Requested; no Treasury page states the licence that we have "
                                  "found, so every use cites the U.S. Department of the Treasury.",
                                  "FRED etiqueta la serie HQM como Public Domain: Citation Requested; ninguna página del Tesoro que hayamos "
                                  "encontrado indica la licencia, por lo que cada uso cita al Departamento del Tesoro de EE. UU."),
            "negative_spread_rule": "a negative HQM-minus-Treasury spread is set to zero and counted, never carried as a negative spread",
            "synthetic_spread": book.named_parameters(0)["counterparty_spread"]}


LIMITS = [
    text("Real-world a and sigma come from one short-rate proxy (the 3 month zero rate) by the exact AR(1) regression on every "
         "observation from 1990 up to the day before each date (an expanding window of at least ten years for the first backtest "
         "date; a rolling window of five or ten years was measured and refused because the regression is not mean-reverting at a "
         "third of the dates). The fit to the curve of the date is the engine's phi.",
         "a y sigma del mundo real vienen de un solo sustituto de la tasa corta (la tasa cero a 3 meses) por la regresión AR(1) exacta sobre "
         "cada observación desde 1990 hasta el día anterior a cada fecha (una ventana creciente de al menos diez años para la primera "
         "fecha; una ventana móvil de cinco o diez años se midió y se rechazó porque la regresión no revierte a la media en un tercio "
         "de las fechas). El ajuste a la curva de la fecha es el phi del motor."),
    text("The stressed Effective EPE re-estimates a and sigma on 2007-01-01 to 2009-12-31 (2.996 years of observations; the floor of "
         "the engine is lowered to 2.99 for this window only) and re-prices the same book on the curve date.",
         "El EPE efectivo bajo estrés re-estima a y sigma en 2007-01-01 a 2009-12-31 (2,996 años de observaciones; el piso del motor se "
         "baja a 2,99 solo para esta ventana) y revalúa el mismo libro en la fecha de la curva."),
    text("The counterparty curve is a market proxy (HQM minus Treasury, AAA to A), a floor for lower ratings; the base-credit "
         "spread of the BA-CVA rating and the sensitivity rows is the synthetic flat 0.0125.",
         "La curva de la contraparte es una aproximación de mercado (HQM menos Tesoro, AAA a A), un piso para calificaciones menores; el spread "
         "base de la calificación BA-CVA y de las filas de sensibilidad es el sintético plano 0,0125."),
    text("Dynamic initial margin is ORE's regression proxy, never ISDA SIMM; the Andersen, Pykhtin and Sokol margin-period timelines are "
         "not modelled.",
         "El margen inicial dinámico es la aproximación por regresión de ORE, nunca ISDA SIMM; no se modelan las cronologías del periodo de "
         "margen de Andersen, Pykhtin y Sokol."),
    text("The journal derivations of the Hull-White closed forms (Hull and White 1990 and 1994, Jamshidian 1989) were not read as "
         "papers; the engine's bond option and swaption are reconciled to QuantLib 1.44 numerically instead.",
         "Las derivaciones de revista de las formas cerradas de Hull-White (Hull y White 1990 y 1994, Jamshidian 1989) no se leyeron "
         "como artículos; la opción sobre bono y la swaption del motor se concilian numéricamente con QuantLib 1.44."),
    text("The GIRR vega risk-weight formula (MAR21 footnote 24) is not transcribed: a swap book has no vega.",
         "La fórmula del peso de riesgo vega GIRR (nota 24 de MAR21) no está transcrita: un libro de swaps no tiene vega."),
]


def fit_block(records: list[dict[str, Any]]) -> dict[str, Any]:
    """The ``fit`` object: the calibration of every backtest date in date order."""
    return {"estimator": calibration.ESTIMATOR_TEXT, "calibrations": records, "min_history_years": 3,
            "closed_forms_source": CLOSED_FORMS_SOURCE, "closed_forms_status": CLOSED_FORMS_STATUS, "credit_curve": credit_curve_block(),
            "girr_parameters": girr_block(), "limits": LIMITS}
