"""The case registry, cases grouped by CATEGORY (SDD section 5). The App shows ONE selected case; Experiments and
Benchmark show cross-case summaries by category."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cases import CASES

Text = dict  # {"en": str, "es": str}

#: the eleven categories, in the order the case selector shows them
CATEGORIES: dict[str, Text] = {
    "credit-scoring": {"en": "Credit scoring", "es": "Puntuación crediticia"},
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

#: the planned cases, declared once (a case of the plan with no built module); a built case overrides its entry
PLANNED_PATH = Path(__file__).resolve().parents[1] / "config" / "planned_cases.json"
_PLANNED_KEYS = {"case_id", "title", "category_id", "kind", "unit", "question"}


class PlannedCaseError(RuntimeError):
    """An operation that needs a built case was asked of a planned one."""


@dataclass(frozen=True)
class PlannedCase:
    """A case of the plan with no built module: listed, declared absent, never baked, never filled with data."""
    id: str
    title: Text
    category_id: str
    kind: str
    unit: str
    question: Text
    planned: bool = True


def _load_planned(path: Path) -> list[PlannedCase]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out: list[PlannedCase] = []
    for e in raw:
        if set(e) != _PLANNED_KEYS:
            raise ValueError(f"{path}: entry {e.get('case_id')!r} has keys {sorted(e)}, expected {sorted(_PLANNED_KEYS)}")
        if e["category_id"] not in CATEGORIES or e["kind"] not in ("real", "synthetic"):
            raise ValueError(f"{path}: entry {e['case_id']!r} has an unknown category or kind")
        out.append(PlannedCase(e["case_id"], e["title"], e["category_id"], e["kind"], e["unit"], e["question"]))
    ids = [p.id for p in out]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path}: a case id is declared twice")
    return out


def built_cases() -> list[Any]:
    return sorted(CASES, key=lambda c: c.id)


def planned_cases() -> list[PlannedCase]:
    """The planned entries no built case provides, in id order (read from PLANNED_PATH at each call)."""
    built = {c.id for c in CASES}
    return sorted((p for p in _load_planned(PLANNED_PATH) if p.id not in built), key=lambda p: p.id)


def stale_planned_ids() -> list[str]:
    """Planned entries whose case is built: harmless, reported (a test warns), never an error."""
    built = {c.id for c in CASES}
    return sorted(p.id for p in _load_planned(PLANNED_PATH) if p.id in built)


def list_cases() -> list[Any]:
    """Every case of the plan, built and planned, in id order."""
    return sorted([*CASES, *planned_cases()], key=lambda c: c.id)


def get_case(case_id: str) -> Any:
    for c in list_cases():
        if c.id == case_id:
            return c
    raise KeyError(f"unknown case: {case_id!r}. known: {[c.id for c in list_cases()]}")


def get_built_case(case_id: str) -> Any:
    case = get_case(case_id)
    if getattr(case, "planned", False):
        raise PlannedCaseError(f"{case_id} is planned (unit {case.unit}) and not built yet: nothing to bake")
    return case


def index_entries() -> list[dict[str, Any]]:
    """One entry per case of the plan, as ``common/case-index`` requires; the planned state is the readiness's."""
    return [{"case_id": c.id, "title": c.title, "category": category(c.category_id), "category_id": c.category_id,
             "kind": c.kind, "manifest_path": f"manifests/{c.id}.json"} for c in list_cases()]


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
