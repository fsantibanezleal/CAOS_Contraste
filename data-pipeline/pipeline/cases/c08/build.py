"""The shared blocks and labels of the C08 documents (CT-902, CT-913, CT-917): the proxy statement, the data status, the
cohorts, the floor cells and the bilingual texts.

Every figure of a C08 document comes from the engine (see ``variant`` and ``downturn``); this module arranges the blocks that
do not depend on a fit and adds the labels.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.lgd_ead.floors import lgd_floor
from riskvalidation.lgd_ead.workout import range_flag

from .cutoff import WORKOUT_WINDOW_MONTHS
from .panel import COHORTS

CURRENCY = "USD"
CASE_ID = "C08"
PRIMARY_SOURCE = "sba-7a-chargeoff-twin"
REGIME = "basel-iii-final"
FLOOR_SOURCE = {
    "en": "dossier 01 section A.5 (Basel III final, CRE32.16, CRE32.17 and CRE32.58 to CRE32.59); the retail secured order is UNVERIFIED",
    "es": "dossier 01, sección A.5 (Basilea III final, CRE32.16, CRE32.17 y CRE32.58 a CRE32.59); el orden de los minoristas garantizados está NO VERIFICADO"}
#: the cell rung used where one rung must stand for the ladder (calibration buckets for the floors, the floors): chosen before
#: seeing a test cohort, in this order, the first fitted
REFERENCE_RUNGS = ("L2-fractional-logit", "L1-ols")
#: the policy parameter of the downturn threshold: the mean plus this many standard deviations of the annual charge-off rate
DOWNTURN_SD = 1.0
N_BUCKETS = 5
N_BINS = 10


def t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


RUNG_TEXT = {
    "L1-ols": (("OLS, clipped to [0, 1]", "MCO, recortado a [0, 1]"), ("L1 OLS", "L1 MCO")),
    "L2-fractional-logit": (("Fractional logit (quasi-likelihood)", "Logit fraccional (cuasi-verosimilitud)"), ("L2 Fractional logit", "L2 Logit fraccional")),
    "L3-beta": (("Beta regression on the endpoint-adjusted LGD", "Regresión beta sobre la LGD con extremos ajustados"), ("L3 Beta", "L3 Beta")),
    "L4-hurdle": (("Two-stage hurdle (loss or not, then severity)", "Dos etapas (hay pérdida o no, luego severidad)"), ("L4 Hurdle", "L4 Hurdle")),
    "L5-gradient-boosted": (("Gradient-boosted trees (catboost, cross-entropy)", "Árboles con gradiente (catboost, entropía cruzada)"), ("L5 Boosted trees", "L5 Árboles")),
    "L6-tobit": (("Two-limit Tobit", "Tobit de dos límites"), ("L6 Tobit", "L6 Tobit")),
}

NOTICE = t(
    "Small-business loans, not mortgages: the SBA 7(a) charge-offs are the public twin of the mortgage case. Freddie Mac's data is "
    "not used (the owner's account is missing). The LGD is a proxy: the file has no recovery cash flows after the charge-off.",
    "Préstamos a pequeñas empresas, no hipotecas: los castigos SBA 7(a) son el gemelo público del caso hipotecario. No se usan los "
    "datos de Freddie Mac (falta la cuenta del propietario). La LGD es un proxy: el archivo no tiene flujos de recuperación "
    "posteriores al castigo.")


def lgd_proxy_block() -> dict[str, Any]:
    return {
        "definition": t(
            "LGD proxy = gross charge-off amount over the gross approved amount (SBA 7(a) fields GrossChargeOffAmount and "
            "GrossApproval, the only exposure field the file carries). It is a proxy, not a workout LGD.",
            "Proxy de LGD = monto bruto castigado sobre el monto bruto aprobado (campos SBA 7(a) GrossChargeOffAmount y "
            "GrossApproval, el único campo de exposición del archivo). Es un proxy, no una LGD de recuperación."),
        "formula": "GrossChargeOffAmount / GrossApproval",
        "source_field": "GrossChargeOffAmount",
        "exposure_field": "GrossApproval",
        "recovery_cash_flows_available": False,
        "bias_direction": "downward",
        "bias_statement": t(
            "The proxy is biased low: the approved amount overstates the exposure at default of an amortising loan, so the "
            "denominator is too large. A second effect pushes the other way: the SBA 7(a) public file has no recovery cash flows "
            "after charge-off, so the proxy ignores recoveries and costs and overstates the loss net of recoveries; it can also "
            "exceed 1 when capitalised interest or fees are charged off. The stated direction is the denominator effect "
            "(decision D2).",
            "El proxy tiene sesgo a la baja: el monto aprobado sobreestima la exposición al incumplimiento de un crédito que se "
            "amortiza, de modo que el denominador es demasiado grande. Un segundo efecto va en sentido contrario: el archivo "
            "público SBA 7(a) no tiene flujos de recuperación posteriores al castigo, de modo que el proxy ignora recuperaciones y "
            "costos y sobreestima la pérdida neta de recuperaciones; también puede superar 1 si se castigan intereses "
            "capitalizados o comisiones. La dirección declarada es el efecto del denominador (decisión D2)."),
    }


#: the declared absence of the Freddie Mac slot (``pipeline.io.sba.FREDDIE_REASON``) in both languages; any other reason is an error, so
#: a Spanish view never prints an English sentence (U16-R2 b04 B5)
FREDDIE_REASONS_ES = {
    "Freddie Mac: the owner's account is missing; the SBA twin is published":
        "Freddie Mac: falta la cuenta del propietario; se publica el gemelo SBA",
}


def freddie_reason_block(reason: str) -> dict[str, str]:
    """The Freddie Mac reason as the bilingual text the documents carry."""
    try:
        return t(reason, FREDDIE_REASONS_ES[reason])
    except KeyError:
        raise ValueError(f"the Freddie Mac reason {reason!r} has no Spanish text: add it to FREDDIE_REASONS_ES") from None


def data_status_block(freddie_reason: str) -> dict[str, Any]:
    return {"primary_source": PRIMARY_SOURCE, "freddie_mac_available": False, "freddie_mac_reason": freddie_reason_block(freddie_reason),
            "notice": NOTICE}


def workout_block() -> dict[str, Any]:
    return {
        "discount_rate_convention": "none-proxy", "discount_rate": None,
        "incomplete_workouts": {"treatment": "not-applicable", "n_excluded": 0, "n_projected": 0,
                                "reason": t("the SBA file has no workout cash flows to discount or to project; the charge-off is the whole record",
                                            "el archivo SBA no tiene flujos de recuperación que descontar ni proyectar; el castigo es todo el registro")},
        "note": t("No discounting applies to a charge-off proxy; a workout LGD would use the EBA/GL/2017/16 rate (paragraph UNVERIFIED).",
                  "No se descuenta un proxy de castigo; una LGD de recuperación usaría la tasa de EBA/GL/2017/16 (párrafo NO VERIFICADO)."),
    }


def closure_rule() -> dict[str, str]:
    return t(
        "Only defaults whose charge-off closed strictly before the cutoff enter the training set (the file has no later record of a "
        "workout); later default cohorts are the tests. The file has no default date before the charge-off, so the open workouts "
        f"excluded are counted as the charge-offs of the {WORKOUT_WINDOW_MONTHS} months after the cutoff, a stated stand-in.",
        "Solo entran al entrenamiento los incumplimientos cuyo castigo cerro estrictamente antes del corte (el archivo no tiene "
        "registro posterior de una recuperación); las cohortes posteriores son de prueba. El archivo no tiene fecha de "
        "incumplimiento anterior al castigo, de modo que los procesos abiertos excluidos se cuentan como los castigos de los "
        f"{WORKOUT_WINDOW_MONTHS} meses posteriores al corte, un sustituto declarado.")


def cohort_block(cohort_id: str) -> dict[str, Any]:
    for cid, lo, hi in COHORTS:
        if cid == cohort_id:
            return {"id": cid, "label": t(f"Defaults {cid}", f"Incumplimientos {cid}"), "first_year": lo, "last_year": hi}
    raise KeyError(cohort_id)


def cohort_blocks() -> list[dict[str, Any]]:
    return [cohort_block(c[0]) for c in COHORTS]


#: ``(floor id, portfolio, collateral, reference)``: the 12 cells of dossier 01 A.5 (the value is the engine's ``lgd_floor``)
FLOOR_CELLS: tuple[tuple[str, str, str, str], ...] = (
    ("corporate-unsecured", "corporate", "unsecured", "CRE32.16"),
    ("corporate-financial", "corporate", "financial", "CRE32.16"),
    ("corporate-receivables", "corporate", "receivables", "CRE32.16"),
    ("corporate-real-estate", "corporate", "real-estate", "CRE32.16"),
    ("corporate-other-physical", "corporate", "other-physical", "CRE32.16"),
    ("retail-mortgage", "retail", "mortgage", "CRE32.58 to CRE32.59"),
    ("retail-qrre", "retail", "qrre", "CRE32.58 to CRE32.59"),
    ("retail-other-unsecured", "retail", "unsecured", "CRE32.58 to CRE32.59"),
    ("retail-other-financial", "retail", "financial", "CRE32.58 to CRE32.59"),
    ("retail-other-receivables", "retail", "receivables", "CRE32.58 to CRE32.59"),
    ("retail-other-real-estate", "retail", "real-estate", "CRE32.58 to CRE32.59"),
    ("retail-other-physical", "retail", "other-physical", "CRE32.58 to CRE32.59"),
)
CELL = {c[0]: c for c in FLOOR_CELLS}


def floor_cells_block() -> list[dict[str, Any]]:
    return [{"id": cid, "portfolio": p, "collateral": col, "floor": float(lgd_floor(p, col)), "reference": ref}
            for cid, p, col, ref in FLOOR_CELLS]


def floor_value(floor_id: str) -> tuple[float, str]:
    _, p, col, ref = CELL[floor_id]
    return float(lgd_floor(p, col)), ref


#: the segments of the floors bite: the SBA file has no collateral field, so the collateral is inferred from the term and
#: the revolving status (a line of credit and a short loan are working-capital credit, taken as unsecured; a loan of 20
#: years or more is a real-estate loan; the rest finances equipment, taken as other physical collateral). Stated as an
#: inference wherever it is shown.
SEGMENTS: tuple[tuple[str, str, str, str], ...] = (
    ("sme-revolver", "corporate-unsecured", "Lines of credit", "Líneas de crédito"),
    ("sme-term-up-to-84", "corporate-unsecured", "Term loans up to 7 years", "Préstamos a plazo hasta 7 años"),
    ("sme-term-85-239", "corporate-other-physical", "Term loans of 7 to 20 years", "Préstamos a plazo de 7 a 20 años"),
    ("sme-term-240-plus", "corporate-real-estate", "Term loans of 20 years or more", "Préstamos a plazo de 20 años o más"),
)


def segment_of(revolver: np.ndarray, term: np.ndarray) -> np.ndarray:
    """The segment index (into ``SEGMENTS``) of each loan."""
    seg = np.where(term >= 240, 3, np.where(term >= 85, 2, 1))
    return np.where(np.asarray(revolver, dtype=bool), 0, seg).astype(np.int64)


def lgd(value: float) -> dict[str, Any]:
    """A realised LGD with its range flag: the value is kept as it is, never clipped (CT-903)."""
    v = float(value)
    return {"value": v, "flag": str(range_flag(np.array([v]))[0])}


def lgd_pred(value: float) -> dict[str, Any]:
    """A predicted LGD: always in [0, 1], flag in-range (the engine's models return a value in [0, 1])."""
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"a predicted LGD must lie in [0, 1], got {v}")
    return {"value": v, "flag": "in-range"}


def variant_id(cohort_id: str) -> str:
    return f"dc-{cohort_id}"


#: the numeric expectations the bake enforces (CT-917): broad plausibility ranges of a result, never a fit target
EXPECT = {
    "mean-proxy@2003-06": (0.45, 0.95), "mean-proxy@2007-08": (0.5, 1.0), "mean-proxy@2009-10": (0.5, 1.0),
    "mean-proxy@2011-13": (0.45, 0.95), "mean-proxy@2014-19": (0.4, 0.95), "mean-proxy@2020-23": (0.4, 0.95),
    "n-defaults-total": (100_000.0, 400_000.0),
}
