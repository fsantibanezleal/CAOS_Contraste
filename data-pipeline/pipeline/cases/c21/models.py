"""The c21-models document: the HMDA fields the bake reads, the fitted decision models of the fit years and the conventions.

``decision_models`` keeps one entry per fitted pairwise estimate of a fit year (the group against the attribute's reference group): the
logistic decision model and the linear rate-spread model, with every term (the intercept, the protected indicator, the permitted
controls) and its standard error. An estimate that did not converge has no entry; its reason is in the outputs document.
"""
from __future__ import annotations

from typing import Any

from . import legal

#: (field, role, alias): the snapshot spellings of the data dictionary; the Data Browser's loan_to_value_ratio is the alias of the combined ratio
FIELDS = (
    ("derived_race", "attribute", None), ("derived_ethnicity", "attribute", None), ("derived_sex", "attribute", None),
    ("applicant_age", "attribute", None), ("action_taken", "outcome", None), ("rate_spread", "pricing", None),
    ("debt_to_income_ratio", "control", None), ("combined_loan_to_value_ratio", "control", "loan_to_value_ratio"),
    ("income", "control", None), ("loan_amount", "control", None), ("property_value", "control", None), ("loan_type", "control", None),
    ("loan_purpose", "control", None), ("lien_status", "control", None), ("occupancy_type", "control", None))


def fit_document(fits: list[dict[str, Any]], notes: list[dict[str, Any]]) -> dict[str, Any]:
    """The fit block of the models document, from the fits of every fit year (in pair order) and the data notes."""
    return {"fields": [{"name": n, "role": r, "alias": a} for n, r, a in FIELDS], "decision_models": fits,
            "conventions": legal.conventions_block(), "legal": legal.legal_block(), "licence": legal.licence_block(), "data_notes": notes}


__all__ = ["FIELDS", "fit_document"]
