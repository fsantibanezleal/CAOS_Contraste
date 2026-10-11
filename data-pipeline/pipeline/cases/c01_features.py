"""C01's declared inputs: the features each dataset adds to the `scored_sample` family, with their units, the rules
that flag codes outside the documented scale, and the monotone directions declared before any fit.

Sources: the UCI page of each dataset (read 2026-10-05) and german.doc in the UCI archive. Protected
characteristics (sex, marital status, personal status, foreign-worker status) and age are never inputs; see
docs/design/features/c01-retail-pd/design.md.
"""
from __future__ import annotations

from typing import Any

from ..io.contract import Field, Rule
from ..io.readers import TAIWAN_BILL, TAIWAN_PAID, TAIWAN_PAY


def _t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


# --- Taiwan ------------------------------------------------------------------------------------------------------

_MONTHS = ("September", "August", "July", "June", "May", "April")
_MESES = ("septiembre", "agosto", "julio", "junio", "mayo", "abril")

TAIWAN_FIELDS: tuple[Field, ...] = (
    Field("LIMIT_BAL", "float", _t("Given credit, including the family (supplementary) credit",
                                   "Crédito otorgado, incluido el crédito familiar (adicional)"),
          unit="NT dollars", lo=0.0, lo_open=True, on_missing="flag"),
    Field("EDUCATION", "int", _t("Education (1 graduate school, 2 university, 3 high school, 4 others)",
                                 "Educación (1 posgrado, 2 universidad, 3 secundaria, 4 otros)"), on_missing="flag"),
    *(Field(col, "int", _t(f"Repayment status in {m} 2005 (-1 paid duly, 1 to 8 months late, 9 nine or more)",
                           f"Estado de pago en {e} de 2005 (-1 pagó a tiempo, 1 a 8 meses de atraso, 9 nueve o más)"),
            unit="months of delay", lo=-2, hi=9, on_missing="flag")
      for col, m, e in zip(TAIWAN_PAY, _MONTHS, _MESES)),
    *(Field(col, "float", _t(f"Bill statement in {m} 2005", f"Estado de cuenta de {e} de 2005"),
            unit="NT dollars", on_missing="flag")
      for col, m, e in zip(TAIWAN_BILL, _MONTHS, _MESES)),
    *(Field(col, "float", _t(f"Amount paid in {m} 2005", f"Monto pagado en {e} de 2005"),
            unit="NT dollars", lo=0.0, on_missing="flag")
      for col, m, e in zip(TAIWAN_PAID, _MONTHS, _MESES)),
)


def _education_documented(rec: dict, _p: dict) -> str | None:
    v = rec.get("EDUCATION")
    return None if v is None or v in (1, 2, 3, 4) else f"EDUCATION code {v} is not in the documented scale 1 to 4"


def _repayment_documented(rec: dict, _p: dict) -> str | None:
    odd = [f"{c}={rec[c]}" for c in TAIWAN_PAY if rec.get(c) in (-2, 0)]
    return f"repayment codes outside the documented scale (-1, 1 to 9): {', '.join(odd)}" if odd else None


TAIWAN_RULES: tuple[Rule, ...] = (
    Rule("C01-EDU-CODE", "record", "flag", "EDUCATION",
         _t("EDUCATION takes a documented code (1 to 4); other codes are kept as their own bin and counted.",
            "EDUCATION toma un código documentado (1 a 4); otros códigos se conservan como su propio tramo y se cuentan."),
         _education_documented),
    Rule("C01-PAY-CODE", "record", "flag", "PAY_0",
         _t("A repayment status takes a documented code (-1, 1 to 9); -2 and 0 are kept as their own bins and counted.",
            "Un estado de pago toma un código documentado (-1, 1 a 9); -2 y 0 se conservan como tramos propios y se cuentan."),
         _repayment_documented),
)

#: the model inputs, in order
TAIWAN_FEATURES: tuple[str, ...] = tuple(f.name for f in TAIWAN_FIELDS)
TAIWAN_CATEGORICAL: tuple[str, ...] = ("EDUCATION",)
#: +1: a larger value raises the risk; -1: lowers it; 0: no declared direction
TAIWAN_MONOTONE: dict[str, int] = {
    "LIMIT_BAL": -1, "EDUCATION": 0,
    **{c: +1 for c in TAIWAN_PAY}, **{c: 0 for c in TAIWAN_BILL}, **{c: -1 for c in TAIWAN_PAID},
}

# --- German ------------------------------------------------------------------------------------------------------

_GERMAN_CODES: dict[str, tuple[str, ...]] = {
    "checking_status": ("A11", "A12", "A13", "A14"),
    "credit_history": ("A30", "A31", "A32", "A33", "A34"),
    "purpose": ("A40", "A41", "A42", "A43", "A44", "A45", "A46", "A47", "A48", "A49", "A410"),
    "savings": ("A61", "A62", "A63", "A64", "A65"),
    "employment_since": ("A71", "A72", "A73", "A74", "A75"),
    "other_debtors": ("A101", "A102", "A103"),
    "property": ("A121", "A122", "A123", "A124"),
    "other_installment_plans": ("A141", "A142", "A143"),
    "housing": ("A151", "A152", "A153"),
    "job": ("A171", "A172", "A173", "A174"),
    "telephone": ("A191", "A192"),
}
_GERMAN_MEANING: dict[str, tuple[str, str, str]] = {
    "checking_status": ("Status of the existing checking account", "Estado de la cuenta corriente", ""),
    "duration_months": ("Duration", "Plazo", "months"),
    "credit_history": ("Credit history", "Historial de crédito", ""),
    "purpose": ("Purpose", "Propósito", ""),
    "credit_amount": ("Credit amount", "Monto del crédito", "DM"),
    "savings": ("Savings account and bonds", "Cuenta de ahorro y bonos", ""),
    "employment_since": ("Present employment since", "Antigüedad en el empleo actual", ""),
    "installment_rate": ("Instalment rate in percent of disposable income", "Cuota como porcentaje del ingreso disponible", "rate class 1 to 4"),
    "other_debtors": ("Other debtors and guarantors", "Otros deudores y avales", ""),
    "residence_since": ("Present residence since", "Antigüedad en la residencia actual", "years class 1 to 4"),
    "property": ("Property", "Bienes", ""),
    "other_installment_plans": ("Other instalment plans", "Otros planes de cuotas", ""),
    "housing": ("Housing", "Vivienda", ""),
    "existing_credits": ("Number of existing credits at this bank", "Créditos vigentes en este banco", "count"),
    "job": ("Job", "Empleo", ""),
    "people_liable": ("People liable to provide maintenance for", "Personas a cargo", "count"),
    "telephone": ("Telephone", "Teléfono", ""),
}

GERMAN_FEATURES: tuple[str, ...] = tuple(_GERMAN_MEANING)
GERMAN_CATEGORICAL: tuple[str, ...] = tuple(_GERMAN_CODES)
GERMAN_FIELDS: tuple[Field, ...] = tuple(
    Field(name, "enum", _t(en, es), values=_GERMAN_CODES[name], on_missing="flag") if name in _GERMAN_CODES
    else Field(name, "float", _t(en, es), unit=unit, lo=0.0, on_missing="flag")
    for name, (en, es, unit) in _GERMAN_MEANING.items()
)
GERMAN_MONOTONE: dict[str, int] = {"duration_months": +1, "credit_amount": 0, "installment_rate": +1,
                                   **{n: 0 for n in GERMAN_FEATURES if n not in ("duration_months", "installment_rate")}}


def feature_meta(fields: tuple[Field, ...], monotone: dict[str, int], categorical: tuple[str, ...]) -> list[dict[str, Any]]:
    """The inputs as the artifact records them: name, bilingual meaning, unit, kind and declared direction."""
    return [{"name": f.name, "meaning": f.meaning, "unit": f.unit, "categorical": f.name in categorical,
             "monotone": monotone.get(f.name, 0)} for f in fields]
