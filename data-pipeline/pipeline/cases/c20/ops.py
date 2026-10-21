"""Small shared operations of the C20 variants: the metrics, the serialised engine rows and the findings of a document.

Every statistic and test is a ``riskvalidation`` call (ADR-0069); this module only reads a result, names its segment and writes the row.
A row is the engine's ``TestResult.to_dict()``; the product sets the ``segment`` (and the model id where the engine takes none) and never
alters a number, a light or an alpha.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

from .conv import t


def auc_brier(p: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """AUC (the engine's DeLong-variance routine) and Brier score of PDs against 0/1 outcomes."""
    from riskvalidation.validation.discrimination import auc_with_variance

    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=int)
    return float(auc_with_variance(p, y)[0]), float(np.mean((p - y) ** 2))


def metric_block(p: np.ndarray, y: np.ndarray, base_auc: float | None) -> dict[str, float]:
    auc, brier = auc_brier(p, y)
    return {"auc": auc, "brier": brier, "auc_delta": 0.0 if base_auc is None else auc - base_auc}


def row(result: Any, *, model_id: str | None = None, segment: str | None = None) -> dict[str, Any]:
    """The engine row of a ``TestResult`` with the model id and the segment the product names (nothing else changes)."""
    changes: dict[str, Any] = {}
    if model_id is not None and result.model_id is None:
        changes["model_id"] = model_id
    if segment is not None:
        changes["segment"] = segment if result.segment is None else f"{segment}:{result.segment}"
    return dataclasses.replace(result, **changes).to_dict() if changes else result.to_dict()


def evidence_id(r: dict[str, Any]) -> str:
    """The id a finding cites: ``test_id``, ``@model`` and ``@segment`` as the artifact check resolves them."""
    out = r["test_id"]
    if r.get("model_id") is not None:
        out += f"@{r['model_id']}"
        if r.get("segment") is not None:
            out += f"@{r['segment']}"
    return out


_SEVERITY = {"red": "S2", "amber": "S3"}


def findings(tests: list[dict[str, Any]], *, limits: list[tuple[str, dict[str, str]]], prefix: str) -> list[dict[str, Any]]:
    """Statistical findings about the document's own rows: one per test id that has an amber or red row (S3 for amber, S2 for red,
    ``open``), citing only those rows, and one S4 ``accepted`` finding per stated limit citing ``design:``. No finding is a claim of
    compliance or of a defect of a real portfolio: the data are research benchmarks and public hypothetical portfolios."""
    out: list[dict[str, Any]] = []
    by_test: dict[str, list[dict[str, Any]]] = {}
    for r in tests:
        if r["light"] in _SEVERITY:
            by_test.setdefault(r["test_id"], []).append(r)
    for tid, rows in sorted(by_test.items()):
        worst = "red" if any(r["light"] == "red" for r in rows) else "amber"
        n_red, n_amber = sum(r["light"] == "red" for r in rows), sum(r["light"] == "amber" for r in rows)
        out.append({
            "id": f"{prefix}-{tid}", "severity": _SEVERITY[worst], "status": "open", "evidence": [evidence_id(r) for r in rows],
            "title": t(f"{tid}: {n_red} red and {n_amber} amber rows in this document; a statistical finding on the data and the model "
                       f"of this variant, not a compliance statement",
                       f"{tid}: {n_red} filas rojas y {n_amber} ámbar en este documento; un hallazgo estadístico sobre los datos y el modelo de "
                       f"esta variante, no una declaración de cumplimiento")})
    for key, title in limits:
        out.append({"id": f"{prefix}-limit-{key}", "severity": "S4", "status": "accepted", "evidence": [f"design:{key}"], "title": title})
    return out
