"""The governance bake (unit U15-P): the model inventory with its tiers and dependency map, the findings register, the model risk
appetite and one twelve-section validation report per inventory entry, written to ``data/derived/governance/``.

The bake reads every committed case document (the manifests, the models documents and the variant documents named by the manifests'
``artifacts``), the product inputs of ``inputs.json`` and the dependency edges of ``edges.json``, and calls ``riskvalidation.governance``
(engine 0.9.0) for every computed value: the scope test, the exposure band, the materiality, the complexity, the tier and its sensitivity
to the rubric's readings, the next review dates, the deadlines, the ageing, the overdue flag, the quantitative anchor, the opinion, the
appetite metrics and the report. The product derives none of them (ADR-0069). It approves no model and certifies none (SDD non-goal 1).

``python -m pipeline.governance [--output-root DIR]`` from ``data-pipeline/`` writes the documents; the heavy modules load when the bake
runs, never at discovery.
"""
from __future__ import annotations

GOVERNANCE_DIR = "governance"
INVENTORY_REL = "governance/inventory.json"
FINDINGS_REL = "governance/findings.json"
APPETITE_REL = "governance/appetite.json"
SUMS_REL = "governance/SHA256SUMS.txt"
REPORTS_DIR = "governance/reports"


def report_rel(entry_key: str) -> str:
    """``governance/reports/<case>-<fit>.json`` of the entry ``case_id/fit_id`` (the path the report reader builds)."""
    return f"{REPORTS_DIR}/{entry_key.replace('/', '-')}.json"


def served_files(derived_root) -> list[str]:
    """The governance documents the site serves, relative to the derived-data root: the three documents and every report on disk, in a fixed order.

    The pipeline's ``served_files`` appends this list to the index (patch 2 of ``changes/U15-P.md``), so the site build copies them to ``data/governance/``.
    """
    from pathlib import Path

    reports = sorted(p.name for p in (Path(derived_root) / REPORTS_DIR).glob("*.json"))
    return [INVENTORY_REL, FINDINGS_REL, APPETITE_REL, *(f"{REPORTS_DIR}/{n}" for n in reports)]
