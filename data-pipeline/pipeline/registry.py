"""The case registry, cases grouped by CATEGORY (SDD section 5). The App shows ONE selected case; Experiments and
Benchmark show cross-case summaries by category."""
from __future__ import annotations

from typing import Any

from .cases import CASES

Text = dict  # {"en": str, "es": str}

#: the eleven categories, in the order the case selector shows them
CATEGORIES: dict[str, Text] = {
    "credit-scoring": {"en": "Credit scoring", "es": "Scoring de crédito"},
    "ratings-calibration": {"en": "Ratings and calibration", "es": "Calificaciones y calibración"},
    "provisions": {"en": "Provisions", "es": "Provisiones"},
    "lgd-ead": {"en": "LGD and EAD", "es": "LGD y EAD"},
    "portfolio-capital": {"en": "Portfolio capital", "es": "Capital de cartera"},
    "market-ccr": {"en": "Market and counterparty risk", "es": "Riesgo de mercado y de contraparte"},
    "balance-sheet": {"en": "Balance sheet: IRRBB and liquidity", "es": "Balance: IRRBB y liquidez"},
    "operational": {"en": "Operational risk", "es": "Riesgo operacional"},
    "capital-stress": {"en": "Capital and stress testing", "es": "Capital y pruebas de tensión"},
    "ml-ai-risk": {"en": "ML and AI model risk", "es": "Riesgo de modelos de ML e IA"},
    "validator": {"en": "Validating the validator", "es": "Validar al validador"},
}

#: the case the App opens on (a deep link ?case=<id> overrides it)
DEFAULT_CASE = "C01"

_BY_ID: dict[str, Any] = {c.id: c for c in CASES}


def list_cases() -> list[Any]:
    return sorted(CASES, key=lambda c: c.id)


def get_case(case_id: str) -> Any:
    if case_id not in _BY_ID:
        raise KeyError(f"unknown case: {case_id!r}. known: {sorted(_BY_ID)}")
    return _BY_ID[case_id]


def default_case() -> str:
    return DEFAULT_CASE


def category(category_id: str) -> Text:
    if category_id not in CATEGORIES:
        raise KeyError(f"unknown category {category_id!r}; known: {list(CATEGORIES)}")
    return CATEGORIES[category_id]


def list_categories() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {k: [] for k in CATEGORIES}
    for c in list_cases():
        out[c.category_id].append(c.id)
    return {k: v for k, v in out.items() if v}
