"""CONTRACT 2, artifact (pipeline to web), SDD section 2.2.

Three documents, each versioned by its schema id and mirrored by ``frontend/src/lib/contract.types.ts``:

- the index (``data/derived/manifests/index.json``): every case with its bilingual title and category, and the case
  the App opens on;
- one manifest per case (``data/derived/manifests/<case>.json``): the case's question, sources, truth status, the
  contract-1 report of its inputs, its expected ranges, and one entry per variant naming the variant's artifact,
  its byte size and its lane verdict;
- one artifact per variant (``data/derived/<case>/<variant>.json``): the model record, the outputs, the
  ``TestResult`` rows, the impact, the findings, the provenance and the lane.

Every builder checks what it writes; an artifact is built only through ``build_artifact``, which refuses a lineage
with a link-only or unusable input before anything is written. Manifests are pure functions of the inputs and
the seed (no wall-clock), so a re-bake of the same release leaves git clean.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .. import __version__
from .lineage import Lineage, assert_publishable

INDEX_SCHEMA = "contraste.index/v1"
MANIFEST_SCHEMA = "contraste.manifest/v1"
ARTIFACT_SCHEMA = "contraste.case/v1"

#: the keys of ``riskvalidation.TestResult.to_dict()`` (riskvalidation 0.1.0), in its order
TEST_RESULT_KEYS = (
    "test_id", "model_id", "segment", "statistic", "p_value", "metric", "h0", "alternative", "policy_version",
    "alpha_amber", "alpha_red", "light", "n", "n_events", "inputs_hash", "reference", "notes", "extras",
)
LIGHTS = ("green", "amber", "red", "not_evaluated", "error")
SEVERITIES = ("S1", "S2", "S3", "S4")
FINDING_STATUSES = ("open", "accepted", "closed")
MODEL_KEYS = ("id", "family", "rung", "title", "engine", "engine_version", "licence", "checkpoint_sha256",
              "calibration", "parameters")
LANES = ("live", "precompute")


class ContractViolation(ValueError):
    """A document about to be written does not satisfy contract 2."""


def _text(v: Any, where: str) -> None:
    if not (isinstance(v, Mapping) and set(v) == {"en", "es"} and all(isinstance(v[k], str) and v[k] for k in v)):
        raise ContractViolation(f"{where}: a reader-facing text is {{'en': ..., 'es': ...}}, both non-empty")


def _check_tests(tests: Sequence[Mapping[str, Any]], where: str) -> set[str]:
    ids: set[str] = set()
    for k, row in enumerate(tests):
        keys = tuple(row)
        if set(keys) != set(TEST_RESULT_KEYS):
            missing = sorted(set(TEST_RESULT_KEYS) - set(keys))
            extra = sorted(set(keys) - set(TEST_RESULT_KEYS))
            raise ContractViolation(f"{where}: test row {k} is not a TestResult (missing {missing}, extra {extra})")
        if row["light"] not in LIGHTS:
            raise ContractViolation(f"{where}: test row {k} light {row['light']!r} is not one of {list(LIGHTS)}")
        if not row["reference"] or not row["h0"] or not row["policy_version"]:
            raise ContractViolation(f"{where}: test row {k} ({row['test_id']}) lacks its reference, H0 or policy")
        ids.add(row["test_id"] if row.get("segment") is None else f"{row['test_id']}@{row['segment']}")
        ids.add(row["test_id"])
    return ids


def _check_findings(findings: Sequence[Mapping[str, Any]], test_ids: set[str], where: str) -> None:
    seen: set[str] = set()
    for f in findings:
        if f.get("id") in seen or not f.get("id"):
            raise ContractViolation(f"{where}: every finding has a unique id")
        seen.add(f["id"])
        if f.get("severity") not in SEVERITIES:
            raise ContractViolation(f"{where}: finding {f['id']} severity {f.get('severity')!r} is not S1 to S4")
        if f.get("status") not in FINDING_STATUSES:
            raise ContractViolation(f"{where}: finding {f['id']} status {f.get('status')!r} is not one of {list(FINDING_STATUSES)}")
        _text(f.get("title"), f"{where}: finding {f['id']} title")
        evidence = f.get("evidence") or []
        if not evidence:
            raise ContractViolation(f"{where}: finding {f['id']} names the tests that evidence it")
        unknown = [e for e in evidence if e not in test_ids]
        if unknown:
            raise ContractViolation(f"{where}: finding {f['id']} cites tests not in this artifact: {unknown}")


def _check_models(models: Sequence[Mapping[str, Any]], where: str) -> None:
    if not models:
        raise ContractViolation(f"{where}: an artifact records at least one model")
    for m in models:
        missing = [k for k in MODEL_KEYS if k not in m]
        if missing:
            raise ContractViolation(f"{where}: model {m.get('id')} lacks {missing}")
        _text(m["title"], f"{where}: model {m['id']} title")
        for name, p in (m["parameters"] or {}).items():
            if not isinstance(p, Mapping) or "value" not in p or "unit" not in p:
                raise ContractViolation(f"{where}: model {m['id']} parameter {name} is {{'value', 'unit'}}")


def _check_impact(impact: Mapping[str, Any], where: str) -> None:
    for name, v in impact.items():
        if not isinstance(v, Mapping) or not {"value", "unit", "label"} <= set(v):
            raise ContractViolation(f"{where}: impact {name} is {{'value', 'unit', 'label'}}")
        if v["value"] is not None and not (isinstance(v["value"], (int, float)) and math.isfinite(v["value"])):
            raise ContractViolation(f"{where}: impact {name} is not finite")
        _text(v["label"], f"{where}: impact {name} label")


def build_artifact(
    *,
    case_id: str,
    variant_id: str,
    model: Sequence[Mapping[str, Any]],
    outputs: Mapping[str, Any],
    tests: Sequence[Mapping[str, Any]],
    impact: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
    lineage: Lineage,
    lane: Mapping[str, Any],
) -> dict[str, Any]:
    """The per-variant artifact. Refuses a non-publishable lineage first (CT-002), then checks every block."""
    assert_publishable(lineage)
    where = f"{case_id}/{variant_id}"
    if lineage.case_id != case_id:
        raise ContractViolation(f"{where}: the lineage belongs to {lineage.case_id}")
    _check_models(model, where)
    test_ids = _check_tests(tests, where)
    _check_findings(findings, test_ids, where)
    _check_impact(impact, where)
    if lane.get("lane") not in LANES:
        raise ContractViolation(f"{where}: lane {lane.get('lane')!r} is not one of {list(LANES)}")
    return {
        "schema": ARTIFACT_SCHEMA,
        "case_id": case_id,
        "variant_id": variant_id,
        "model": [dict(m) for m in model],
        "outputs": dict(outputs),
        "tests": [dict(t) for t in tests],
        "impact": dict(impact),
        "findings": [dict(f) for f in findings],
        "provenance": lineage.provenance(),
        "lane": dict(lane),
    }


def build_case_manifest(
    *,
    case_id: str,
    title: Mapping[str, str],
    category: Mapping[str, str],
    question: Mapping[str, str],
    sources: Sequence[str],
    seed: int,
    variants: Sequence[Mapping[str, Any]],
    default_variant: str,
    contract: Mapping[str, Any],
    expect: Mapping[str, Sequence[float]],
    riskvalidation_version: str | None,
) -> dict[str, Any]:
    """The case manifest. ``variants`` are ``{variant_id, title, regime, truth_status, path, bytes, lane, gate}``."""
    for name, v in (("title", title), ("category", category), ("question", question)):
        _text(v, f"{case_id} {name}")
    if not variants:
        raise ContractViolation(f"{case_id}: a case has at least one variant")
    ids = [v["variant_id"] for v in variants]
    if len(set(ids)) != len(ids):
        raise ContractViolation(f"{case_id}: variant ids repeat")
    if default_variant not in ids:
        raise ContractViolation(f"{case_id}: the default variant {default_variant!r} is not among {ids}")
    for v in variants:
        _text(v["title"], f"{case_id}/{v['variant_id']} title")
        _text(v["regime"], f"{case_id}/{v['variant_id']} regime")
        if v.get("lane") not in LANES or (v.get("gate") or {}).get("lane") != v.get("lane"):
            raise ContractViolation(f"{case_id}/{v['variant_id']}: the lane and the gate verdict disagree")
    if not expect:
        raise ContractViolation(f"{case_id}: no expected range declared (every case states what a reader should see)")
    return {
        "schema": MANIFEST_SCHEMA,
        "case_id": case_id,
        "title": dict(title),
        "category": dict(category),
        "question": dict(question),
        "sources": list(sources),
        "seed": seed,
        "engine": {"pipeline": __version__, "riskvalidation": riskvalidation_version},
        "default_variant": default_variant,
        "artifacts": [dict(v) for v in variants],
        "contract": dict(contract),
        "expect": {k: [float(lo), float(hi)] for k, (lo, hi) in sorted(expect.items())},
    }


def build_index(entries: Sequence[Mapping[str, Any]], default_case: str) -> dict[str, Any]:
    """entries: ``[{case_id, title, category, manifest_path}]``: the flat inventory, with the case the App opens on."""
    if default_case not in {e["case_id"] for e in entries}:
        raise ContractViolation(f"default case {default_case!r} is not among the baked cases")
    return {
        "schema": INDEX_SCHEMA,
        "engine_version": __version__,
        "n_cases": len(entries),
        "default_case": default_case,
        "cases": sorted((dict(e) for e in entries), key=lambda e: e["case_id"]),
    }
