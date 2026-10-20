"""Builds the four U15-S schema files (docs/contracts/schemas/governance).

Run: ``python tests/contracts_u15/build_schemas.py``. Deterministic, standard library only. The schema files are the contract and are
committed; this script is the compact source they are written from, so a name two files share has one definition (the generator of the
TypeScript types fails on a clash). Conventions of docs/contracts/catalog.md: closed objects, nothing optional, ``$defs`` prefixed by the
document (``inv``, ``fnd``, ``rep``, ``app``) or shared (``gov``), the bilingual ``text`` of the common schemas.

The four documents sit in ``data/derived/governance/`` and are not variant envelopes. Each carries a ``governance_id`` const, a
``schema_version``, the committed ``as_of`` date, a provenance (code version, ``riskvalidation`` version, the sha256 of every case document
read) and bilingual ``text`` wherever a person reads it. Discovery selects a document by its ``schema`` const (``contraste.governance.<id>/v1``)
and ``case_id`` const ``GOVERNANCE`` (the folder name upper-cased, as the regulatory calculators do).

A property computed by the engine has a description that ends with ``Computed by <function>.`` (the dotted name of the function behind it;
ADR-0069: the engine computes every value). The test of the contract checks that the function has its section in
docs/contracts/engine/governance-api.md. A convention table carries
``label: "convention"`` (a const: a table cannot be labelled regulatory) and its basis.

What JSON Schema states (shape, closed objects, the enumerations, the coupled fields) is here; what it cannot state (a tier is the matrix of its
scores, a due date is the raised date plus the deadline, an acyclic graph) is ``semantics.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "contracts" / "schemas" / "governance"
BASE = "https://contraste.fasl-work.com/contracts/"
TXT = {"$ref": "../common/text.schema.json"}
ENG = "riskvalidation.governance."
LABEL_EN = "the rule's output on the evidence; Contraste approves no model"
STATES_B7 = ["open", "action_plan_agreed", "in_progress", "submitted_for_closure", "validated_closed", "overdue", "risk_accepted"]
STATES_B4 = ["proposed", "in_development", "submitted_for_validation", "in_validation", "approved", "approved_with_conditions", "in_use",
             "under_monitoring_alert", "restricted", "in_remediation", "material_change_pending", "decommissioned"]
SECTION_KEYS = ["executive_summary", "model_description", "conceptual_soundness", "data", "implementation", "outcomes_analysis",
                "sensitivity_robustness_stress", "ongoing_monitoring", "limitations_and_controls", "findings_register",
                "opinion_and_recommendation", "appendices"]
SECTION_TITLES = ["Executive summary", "Model description and intended use", "Conceptual soundness", "Data",
                  "Implementation and process verification", "Outcomes analysis", "Sensitivity, robustness and stress", "Ongoing monitoring",
                  "Limitations and compensating controls", "Findings register", "Overall opinion and recommendation", "Appendices"]


def Ob(props: dict, desc: str | None = None) -> dict:
    d: dict = {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}
    if desc:
        d["description"] = desc
    return d


def A(items: dict, minimum: int | None = None, maximum: int | None = None, desc: str | None = None) -> dict:
    d: dict = {"type": "array", "items": items}
    if minimum is not None:
        d["minItems"] = minimum
    if maximum is not None:
        d["maxItems"] = maximum
    if desc:
        d["description"] = desc
    return d


def R(name: str) -> dict:
    return {"$ref": f"#/$defs/{name}"}


def nullable(x: dict, desc: str | None = None) -> dict:
    d: dict = {"anyOf": [x, {"type": "null"}]}
    if desc:
        d["description"] = desc
    return d


def S(desc: str | None = None, **kw) -> dict:
    d: dict = {"type": "string", **kw}
    if desc:
        d["description"] = desc
    return d


def Int(minimum: int | None = None, maximum: int | None = None, desc: str | None = None) -> dict:
    d: dict = {"type": "integer"}
    if minimum is not None:
        d["minimum"] = minimum
    if maximum is not None:
        d["maximum"] = maximum
    if desc:
        d["description"] = desc
    return d


def N(desc: str | None = None, **kw) -> dict:
    d: dict = {"type": "number", **kw}
    if desc:
        d["description"] = desc
    return d


def E(*values: str) -> dict:
    return {"type": "string", "enum": list(values)}


def C(value, desc: str | None = None) -> dict:
    d: dict = {"const": value}
    if desc:
        d["description"] = desc
    return d


B = {"type": "boolean"}
BASIS = S(minLength=1)
DATE = R("govDate")
NUM_OR_NULL = nullable(N())


def eng(node: dict, fn: str) -> dict:
    """Marks a property as computed by the engine function ``riskvalidation.governance.<fn>`` (ADR-0069): its description ends with
    ``Computed by <function>.``. An annotation keyword would fail the strict Ajv of the consumer test, which registers only x-location and
    x-discover, so the name travels in the description."""
    note = f"Computed by {ENG}{fn}."
    return {**node, "description": f"{node['description']} {note}" if node.get("description") else note}


def when(ob: dict, field: str, value, then: dict, otherwise: dict | None = None) -> dict:
    """``if field == value then <properties>`` (else ``<properties>``) on a closed object, narrowing declared properties."""
    ob.setdefault("allOf", []).append({
        "if": {"properties": {field: {"const": value}}, "required": [field]},
        "then": {"properties": then},
        **({"else": {"properties": otherwise}} if otherwise is not None else {}),
    })
    return ob


def when_null(ob: dict, field: str, then_required: list[str]) -> dict:
    """If ``field`` is null the listed fields must not be (coupled null-with-its-reason fields)."""
    ob.setdefault("allOf", []).append({
        "if": {"properties": {field: {"type": "null"}}, "required": [field]},
        "then": {"properties": {f: {"not": {"type": "null"}} for f in then_required}},
        "else": {"properties": {f: {"type": "null"} for f in then_required}},
    })
    return ob


def reachable(root: dict, defs: dict) -> dict:
    """The ``$defs`` a document reaches, in a stable order."""
    seen: dict = {}
    todo: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/"):
                    todo.append(v[len("#/$defs/"):])
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(root)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen[name] = defs[name]
        walk(defs[name])
    return dict(sorted(seen.items()))


# --- shared definitions ---------------------------------------------------------------------------------------------------------------

def shared_defs() -> dict:
    return {
        "govDate": S("An ISO date (YYYY-MM-DD). The dates of a governance document are deterministic: the as-of date and every raised date "
                     "come from committed values (R4 of the U15 sizing); a wall-clock date never enters a document.",
                     pattern=r"^\d{4}-\d{2}-\d{2}$"),
        "govSha256": S(pattern="^[0-9a-f]{64}$"),
        "govProvenance": Ob({
            "code_version": S("The Contraste code version that wrote the document.", minLength=1),
            "riskvalidation_version": S("The engine version that computed it.", minLength=1),
            "generators": A(S(minLength=1), 1, desc="The writer of the document; a fixture is labelled fixture:u15-s-contracts."),
            "documents_read": A(Ob({"path": S(minLength=1), "sha256": R("govSha256")}), 1,
                                desc="Every case document read, with the sha256 of its bytes (line endings normalised to LF)."),
        }, "Where a governance document came from: code and engine versions and the sha256 of every case document it read."),
        "govSeverity": E(*["S1", "S2", "S3", "S4"]),
        "govEcbF": E("F1", "F2", "F3", "F4"),
        "govTier": Int(1, 4),
        "govTag": E("doc", "convention"),
        "govGovFinding": severity_ecb_rules(Ob({
            "id": S(minLength=1),
            "severity": R("govSeverity"),
            "ecb_f": eng(R("govEcbF"), "findings.severity_to_ecb"),
            "status": C("open"),
            "title": TXT,
            "description": TXT,
            "basis": S("The decision or finding of the record that raises it.", minLength=1),
        }, "A governance finding of the inventory itself (W15-3: the rubric blind spot, S3; W15-4: independence not established, S2).")),
    }


def severity_ecb_rules(ob: dict) -> dict:
    """The coupled fields severity and ecb_f: S1 is F4, S2 F3, S3 F2, S4 F1 (W15-2)."""
    for sev, f in (("S1", "F4"), ("S2", "F3"), ("S3", "F2"), ("S4", "F1")):
        when(ob, "severity", sev, {"ecb_f": C(f)})
    return ob


def header(gid: str, extra_required: list[str], extra_props: dict) -> tuple[dict, list[str]]:
    props = {
        "schema": C(f"contraste.governance.{gid}/v1"),
        "case_id": C("GOVERNANCE"),
        "governance_id": C(gid),
        "schema_version": S(pattern=r"^\d+\.\d+\.\d+$"),
        "as_of": R("govDate"),
        "provenance": R("govProvenance"),
        **extra_props,
    }
    return props, list(props)


# --- the inventory -----------------------------------------------------------------------------------------------------------------------

def inventory_defs() -> dict:
    d = shared_defs()
    conv_label = {"label": C("convention"), "basis": BASIS}
    d.update({
        "invAttr": when(when(Ob({"value": {}, "status": E("present", "derivable", "convention", "not-applicable", "missing"), "basis": BASIS},
                              "A B.2 attribute: never a bare value. basis is the JSON pointer read, or the convention's or the absence's reason."),
                        "status", "missing", {"value": C(None)}), "status", "not-applicable", {"value": C(None)}),
        "invAttributes": Ob({f"A{i:02d}": R("invAttr") for i in range(1, 41)}, "The 40 attributes of 06 B.2 (l.539-551), keyed A01 to A40."),
        "invComponent": Ob({
            "key": S("case_id/fit_id/model_id: model ids repeat across cases, so the key is the triple.", pattern=r"^[^/]+/[^/]+/[^/]+$"),
            "model_id": S(minLength=1),
            "role": E("champion", "challenger", "benchmark", "reference"),
            "role_tag": R("govTag"),
            "role_basis": BASIS,
            "family": nullable(S()),
            "rung": nullable(S()),
            "title": nullable(TXT),
        }),
        "invScopeAnswers": Ob({"applies_theory": B, "output_is_estimate": B, "deterministic": B, "generative_or_agentic": B}),
        "invScopeProfile": Ob({"profile": E("us-2026", "pra", "osfi-2027", "ecb"), "in_scope": B, "rationale": TXT}),
        "invScope": Ob({"answers": R("invScopeAnswers"),
                        "profiles": eng(A(R("invScopeProfile"), 4, 4), "scope.scope_record"), "basis": BASIS},
                       "The B.1 scope record: the four answers and the in-scope decision per jurisdiction profile (06 l.523-537)."),
        "invExposure": Ob({"share": nullable(N(minimum=0, maximum=1), "The share of the stated balance; null where no balance exists."),
                           "band": eng(Int(1, 4), "tiering.exposure_band"), "tag": R("govTag"), "basis": BASIS}),
        "invRegUse": Ob({"literal": Int(1, 4), "graded": Int(1, 4), "tag": R("govTag"), "basis": BASIS}),
        "invDecision": Ob({"score": Int(1, 4), "tag": R("govTag"), "basis": BASIS}),
        "invMateriality": Ob({"exposure": R("invExposure"), "regulatory_use": R("invRegUse"), "decision_criticality": R("invDecision"),
                              "m": eng(Ob({"literal": Int(1, 4), "graded": Int(1, 4)}), "tiering.materiality")},
                             "M = max(exposure band, regulatory use, decision criticality), under both readings of regulatory use."),
        "invFactor": Ob({"id": E("F1", "F2", "F3", "F4", "F5", "F6", "F7"), "name": S(minLength=1), "score": nullable(Int(1, 4)),
                         "tag": R("govTag"), "basis": BASIS}),
        "invComplexity": Ob({"factors": A(R("invFactor"), 7, 7), "scored": Int(1, 7), "sum": Int(1), "mean": N(minimum=1, maximum=4),
                             "c": eng(Ob({"mean": Int(1, 4), "maximum": Int(1, 4)}), "tiering.complexity")},
                            "C from the factor scores: the mean rounded half up, and the maximum. A factor with a null score is unscored, with its reason."),
        "invOverride": Ob({"to_tier": R("govTier"), "rationale": S(minLength=1), "approver": S(minLength=1)},
                          "An override of the computed tier: a rationale and an approver are required, never silent (SS1/23 Principle 1.3(d)(e))."),
        "invSensitivity": Ob({"reading": E("A", "B", "C", "D"), "regulatory_use": E("literal", "graded"), "complexity": E("mean", "maximum"),
                              "m": Int(1, 4), "c": Int(1, 4), "tier": R("govTier")}),
        "invTier": Ob({
            "materiality": R("invMateriality"),
            "complexity": R("invComplexity"),
            "adopted_reading": C("B"),
            "computed_tier": eng(R("govTier"), "tiering.matrix_tier"),
            "override": nullable(R("invOverride")),
            "tier": eng(R("govTier"), "tiering.apply_override"),
            "tier_sensitivity": eng(A(R("invSensitivity"), 4, 4), "tiering.tier_sensitivity"),
        }, "The tier block: M, C, the factor scores with their tags, the tier, the override and the tier under the four readings."),
        "invTransition": Ob({"from": E(*STATES_B4), "to": E(*STATES_B4), "date": R("govDate"), "basis": BASIS}),
        "invException": Ob({"type": S(minLength=1), "approver": S(minLength=1), "expiry": R("govDate"), "reason": TXT}),
        "invLifecycle": Ob({"state": eng(E(*STATES_B4), "lifecycle.transition"), "basis": BASIS, "transitions": A(R("invTransition")),
                            "exception": nullable(R("invException"))},
                           "The B.4 lifecycle state; use before validation only with an exception record (type, approver, expiry)."),
        "invLast": Ob({"date": R("govDate"), "type": E("full battery", "annual", "change-triggered", "initial"), "basis": BASIS}),
        "invSchedule": Ob({
            "profile": E("default", "ecb"),
            "review_kind": E("review", "attestation"),
            "last_validation": R("invLast"),
            "next_review": eng(R("govDate"), "schedule.next_dates"),
            "next_full_revalidation": eng(nullable(R("govDate")), "schedule.next_dates"),
            "next_monitoring": eng(nullable(R("govDate")), "schedule.next_dates"),
            "null_reason": nullable(TXT),
        }, "The next review, full revalidation and monitoring dates from the tier and the frequency table (06 B.8)."),
        "invGraph": Ob({"depth": eng(Int(0), "inventory.graph_metrics"), "fan_in": eng(Int(0), "inventory.graph_metrics"),
                        "fan_out": eng(Int(0), "inventory.graph_metrics")}),
        "invMap": Ob({"generation": Int(0), "x": N(), "y": N()}, "The layered layout of the dependency map (the bake's networkx layout, a geometry and not a model value)."),
        "invEntry": Ob({
            "key": S("case_id/fit_id (W15-1).", pattern=r"^C\d{2}/[a-z0-9-]+$"),
            "case_id": S(pattern=r"^C\d{2}$"),
            "fit_id": S(minLength=1),
            "title": TXT,
            "attributes": R("invAttributes"),
            "components": A(R("invComponent"), 1),
            "scope": R("invScope"),
            "tier_block": R("invTier"),
            "lifecycle": R("invLifecycle"),
            "schedule": R("invSchedule"),
            "graph": R("invGraph"),
            "map": R("invMap"),
        }, "One fit of one case (W15-1)."),
        "invEdge": Ob({"upstream": S(minLength=1), "downstream": S(minLength=1), "kind": E("document", "code"), "stated_source": BASIS},
                      "A dependency (W15-8): a document read or a code import, with its stated source. Kept apart from the related links."),
        "invRelated": Ob({"a": S(minLength=1), "b": S(minLength=1),
                          "kind": E("page-statement", "method", "source", "measures", "conceptual"), "source": BASIS},
                         "A link that is not a dependency: a page statement, a shared method, a shared source (A D4 5.1, 5.3)."),
        "invExcluded": Ob({"case_id": S(pattern=r"^C\d{2}$"), "reason": TXT}, "A case left out of the inventory, with the reason (missing-data behavior)."),
        "invTierCounts": Ob({"reading": E("A", "B", "C", "D"), "counts": A(Int(0), 4, 4)}),
        "invAttrCount": Ob({"present": Int(0), "derivable": Int(0), "convention": Int(0), "not_applicable": Int(0), "missing": Int(0)}),
        "invCompleteness": Ob({"entries": Int(1), "attributes": Ob({f"A{i:02d}": R("invAttrCount") for i in range(1, 41)})}),
        "invConventions": Ob({
            "exposure_band_cuts": Ob({**conv_label, "cuts": A(N(minimum=0, maximum=1), 3, 3)}),
            "regulatory_use_grades": Ob({**conv_label, "graded": Ob({"reported_figure": Int(1, 4), "feeding_parameter": Int(1, 4),
                                                                     "compliance_monitoring": Int(1, 4), "none": Int(1, 4)}),
                                         "literal": Ob({"feeds_capital_provisioning_or_reporting": Int(1, 4), "none": Int(1, 4)})}),
            "complexity_rounding": Ob({**conv_label, "rule": C("mean-rounded-half-up")}),
            "frequency": Ob({**conv_label, "tiers": A(Ob({"tier": R("govTier"), "review_kind": E("review", "attestation"),
                                                          "review_months": Int(1), "revalidation_months": nullable(Int(1)),
                                                          "monitoring_months": nullable(Int(1)), "null_reason": nullable(TXT)}), 4, 4)}),
            "adopted_reading": Ob({**conv_label, "reading": C("B")}),
        }, "The tables that are conventions (item 30 of the dossier UNVERIFIED list): named parameters, each labelled convention with its basis."),
    })
    d["invEngineNode"] = Ob({"key": C("riskvalidation"), "version": S(minLength=1), "basis": BASIS},
                            "The engine node every entry depends on (W15-8); its key is never an entry key.")
    return d


def inventory_schema() -> dict:
    d = inventory_defs()
    props, _ = header("inventory", [], {
        "conventions": R("invConventions"),
        "engine_node": R("invEngineNode"),
        "entries": eng(A(R("invEntry"), 1), "inventory.build_inventory"),
        "edges": eng(A(R("invEdge")), "inventory.build_inventory"),
        "related": A(R("invRelated")),
        "excluded": A(R("invExcluded")),
        "completeness": eng(R("invCompleteness"), "inventory.attribute_completeness"),
        "tier_counts": eng(A(R("invTierCounts"), 4, 4), "tiering.tier_counts"),
        "governance_findings": A(R("govGovFinding"), 2),
    })
    root = Ob(props, "Catalog row governance-inventory 1.0.0: the model inventory of Contraste's own case models "
                     "(data/derived/governance/inventory.json): one entry per fit (case_id/fit_id) with the 40 B.2 attributes, the components, the scope "
                     "record, the tier block, the lifecycle state, the schedule dates, the dependency edges, the engine node and the governance findings "
                     "of the inventory itself.")
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{BASE}governance/governance-inventory.schema.json",
            "title": "Governance inventory", **root, "$defs": reachable(root, d)}


# --- the findings register -----------------------------------------------------------------------------------------------------------------

def findings_defs() -> dict:
    d = shared_defs()
    anchor = Ob({"metric": E("statistic", "metric"), "test_id": S(minLength=1), "model_id": S(minLength=1), "segment": nullable(S()),
                 "value": N(), "unit": S(minLength=1), "basis": BASIS},
                "The quantitative anchor: the cited test row's statistic or metric, with its unit and the pointer it was read from.")
    risk = Ob({"approver": C("not-applicable"), "approver_reason": TXT, "expiry": C(None), "expiry_reason": TXT},
              "Risk acceptance of a stated limit of a synthetic case (W15-5): no approver and no expiry exist, each with its reason.")
    row = Ob({
        "key": S("case_id/variant_id/id.", pattern=r"^[^/]+/[^/]+/[^/]+$"),
        "case_id": S(pattern=r"^C\d{2}$"),
        "variant_id": S(minLength=1),
        "id": S(minLength=1),
        "entry_key": S("The inventory entry (case_id/fit_id) the finding belongs to.", pattern=r"^C\d{2}/[a-z0-9-]+$"),
        "title": TXT,
        "severity": R("govSeverity"),
        "ecb_f": eng(R("govEcbF"), "findings.severity_to_ecb"),
        "product_status": E("open", "accepted", "closed"),
        "status": eng(E(*STATES_B7), "findings.map_product_status"),
        "evidence": A(S(minLength=1), 1),
        "anchor": eng(nullable(R("fndAnchor")), "findings.anchor_from_test_row"),
        "anchor_reason": nullable(TXT),
        "owner_role": S(minLength=1),
        "tier": R("govTier"),
        "raised": R("govDate"),
        "deadline_days": eng(Int(1), "findings.deadline_days"),
        "due": eng(R("govDate"), "findings.due_date"),
        "ageing_days": eng(Int(0), "findings.ageing_days"),
        "overdue": eng(B, "findings.is_overdue"),
        "remediation": nullable(TXT),
        "remediation_reason": nullable(TXT),
        "risk_acceptance": nullable(R("fndRisk")),
    }, "One finding of one variant, enriched with the B.7 fields from committed values (R3, W15-5).")
    severity_ecb_rules(row)
    when_null(row, "anchor", ["anchor_reason"])
    when_null(row, "remediation", ["remediation_reason"])
    when(row, "status", "risk_accepted", {"risk_acceptance": R("fndRisk")}, {"risk_acceptance": {"type": "null"}})
    when(row, "product_status", "open", {"status": C("open")})
    when(row, "product_status", "accepted", {"status": C("risk_accepted")})
    when(row, "product_status", "closed", {"status": C("validated_closed")})
    by_sev = Ob({s: Int(0) for s in ("S1", "S2", "S3", "S4")})
    by_status = Ob({s: Int(0) for s in STATES_B7})
    d.update({
        "fndAnchor": anchor, "fndRisk": risk, "fndRow": row,
        "fndBySeverity": by_sev, "fndByStatus": by_status,
        "fndCaseCount": Ob({"case_id": S(pattern=r"^C\d{2}$"), "total": Int(0), "by_severity": R("fndBySeverity"), "by_status": R("fndByStatus"),
                            "overdue": Int(0)}),
        "fndCounts": Ob({"total": Int(0), "by_severity": R("fndBySeverity"), "by_status": R("fndByStatus"), "overdue": Int(0),
                         "by_case": A(R("fndCaseCount"), 1)}, "The counts by case, severity and status."),
        "fndConventions": Ob({
            "deadline_days": Ob({"label": C("convention"), "basis": BASIS,
                                 "rows": A(Ob({"severity": R("govSeverity"), "days": A(Int(1), 4, 4)}), 4, 4)},
                                "Days from the raised date to the due date, by severity (rows) and tier 1 to 4 (columns). No regulatory source prescribes days."),
            "severity_scale": Ob({"label": C("convention"), "basis": BASIS,
                                  "rows": A(Ob({"severity": R("govSeverity"), "ecb_f": R("govEcbF")}), 4, 4)}),
            "status_map": Ob({"label": C("convention"), "basis": BASIS,
                              "rows": A(Ob({"product": E("open", "accepted", "closed"), "register": E(*STATES_B7)}), 3, 3)}),
        }),
    })
    return d


def findings_schema() -> dict:
    d = findings_defs()
    props, _ = header("findings", [], {
        "conventions": R("fndConventions"),
        "rows": A(R("fndRow"), 1),
        "counts": eng(R("fndCounts"), "findings.register_counts"),
    })
    root = Ob(props)
    doc = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{BASE}governance/governance-findings.schema.json",
           "title": "Governance findings register",
           "description": "Catalog row governance-findings 1.0.0: the findings register across cases (data/derived/governance/findings.json): one row per "
                          "case_id/variant_id/id with the product severity and its ECB F equivalent, the mapped B.7 status, the evidence, the anchor, the "
                          "owner role, the raised and due dates, the ageing, the overdue flag, the remediation and the risk acceptance, with the counts.",
           **root, "$defs": reachable(root, d)}
    return doc


# --- the validation report -----------------------------------------------------------------------------------------------------------------

def report_defs() -> dict:
    d = shared_defs()
    cell = {"type": ["string", "number", "boolean", "null"]}
    policy = Ob({
        "label": S(minLength=1),
        "kind": nullable(E("p_value", "upper_bad", "lower_bad")),
        "alpha_amber": NUM_OR_NULL,
        "alpha_red": NUM_OR_NULL,
        "parameters": {"type": "object", "additionalProperties": {"type": ["number", "string"]}},
        "version": nullable(S()),
        "source": eng(E("packaged-policy", "inline-battery", "unresolved"), "policy.resolve_policy"),
        "reason": nullable(S()),
    }, "The policy identity of a test row (W15-6): a packaged label through the policy file, an inline battery string parsed, or unresolved with its reason.")
    when(policy, "source", "unresolved", {"reason": S(minLength=1), "kind": {"type": "null"}})
    outcome_row = Ob({
        "test_id": S(minLength=1), "model_id": nullable(S()), "segment": nullable(S()), "family": S(minLength=1),
        "statistic": NUM_OR_NULL, "p_value": NUM_OR_NULL, "metric": NUM_OR_NULL,
        "light": E("green", "amber", "red", "not_evaluated", "error"),
        "h0": S(), "reference": S(), "policy": R("repPolicy"),
    })
    open_finding = Ob({"key": S(minLength=1), "severity": R("govSeverity"), "rwea_share": nullable(N(minimum=0))})
    opinion = Ob({
        "level": eng(Int(1, 4), "opinion.opinion_level"),
        "level_label": TXT,
        "rule": Ob({"id": C("W15-7"), "text": TXT}),
        "rwea_cut_points_applied": B,
        "open_findings": A(R("repOpenFinding")),
        "recommendation": eng(Ob({"outcome": E("approve", "approve with conditions", "remediate before use"), "text": TXT}),
                              "opinion.recommendation"),
        "label": {"allOf": [TXT, {"properties": {"en": C(LABEL_EN)}}]},
    }, "Section 11: the ECB four-level opinion, the rule that gave it, the open findings it was computed on and the labelled recommendation.")
    block_text = Ob({"kind": C("text"), "text": TXT})
    block_list = Ob({"kind": C("list"), "items": A(TXT, 1)})
    block_table = Ob({"kind": C("table"), "caption": TXT, "columns": A(TXT, 1), "rows": A(A(cell))})
    block_outcomes = Ob({"kind": C("outcomes"), "variant_id": S(minLength=1), "rows": A(R("repOutcomeRow"), 1)})
    section_common = {
        "number": Int(1, 12),
        "key": E(*SECTION_KEYS),
        "title": TXT,
        "status": E("filled", "absent"),
        "inputs": A(R("repInput")),
        "absent_reason": nullable(TXT),
        "blocks": A(R("repBlock")),
        "missing": A(R("repMissing")),
    }
    d.update({
        "repPolicy": policy, "repOutcomeRow": outcome_row, "repOpenFinding": open_finding, "repOpinion": opinion,
        "repBlock": {"oneOf": [block_text, block_list, block_table, block_outcomes]},
        "repInput": Ob({"ref": S(minLength=1), "kind": E("document", "engine", "convention")}, "An input a section names (A D5)."),
        "repMissing": Ob({"element": TXT, "reason": TXT}, "An element of the I.3 template the product holds nothing behind (A D5, the Missing column)."),
        "repCounts": Ob({"green": Int(0), "amber": Int(0), "red": Int(0), "not_evaluated": Int(0), "error": Int(0)}),
    })
    for i, (key, title) in enumerate(zip(SECTION_KEYS, SECTION_TITLES), 1):
        props = {**section_common, "number": C(i), "key": C(key)}
        if i == 1:
            props["opinion_level"] = Int(1, 4)
        if i == 11:
            props["opinion"] = R("repOpinion")
        sec = Ob(props, f"I.3 section {i}: {title} (06 l.1219-1237).")
        when(sec, "status", "filled", {"inputs": {"minItems": 1}, "blocks": {"minItems": 1}, "absent_reason": {"type": "null"}},
             {"blocks": {"maxItems": 0}, "absent_reason": {"not": {"type": "null"}}})
        d[f"repSection{i}"] = sec
    return d


def report_schema() -> dict:
    d = report_defs()
    props, _ = header("report", [], {
        "entry_key": S("The inventory entry (case_id/fit_id) the report is for.", pattern=r"^C\d{2}/[a-z0-9-]+$"),
        "title": TXT,
        "tier": R("govTier"),
        "test_counts": eng(R("repCounts"), "report.executive_counts"),
        "sections": eng({"type": "array", "minItems": 12, "maxItems": 12,
                         "prefixItems": [R(f"repSection{i}") for i in range(1, 13)]}, "report.build_report"),
    })
    root = Ob(props)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{BASE}governance/governance-report.schema.json",
            "title": "Governance validation report",
            "description": "Catalog row governance-report 1.0.0: the I.3 validation report of one inventory entry "
                           "(data/derived/governance/reports/<case>-<fit>.json): twelve sections, each filled from the inputs it names or absent with its "
                           "reason; section 11 holds the opinion level 1 to 4, the rule that gave it and the recommendation, labelled the rule's output.",
            **root, "$defs": reachable(root, d)}


# --- the appetite --------------------------------------------------------------------------------------------------------------------------

def appetite_defs() -> dict:
    d = shared_defs()
    threshold = Ob({"label": C("convention"), "basis": BASIS, "direction": E("higher-is-better", "lower-is-better"),
                    "green_limit": N(), "amber_limit": N()},
                   "The stated threshold of a light: a convention with its basis (item 30), never a regulatory value.")
    metric = Ob({
        "id": E("tier1-validated-on-time", "open-high-severity", "overdue-remediation", "entries-under-exception", "entries-in-breach",
                "pma-magnitude", "owner-and-complete-record"),
        "name": TXT,
        "kind": E("share", "count", "magnitude"),
        "value": eng(NUM_OR_NULL, "appetite.appetite_metrics"),
        "unit": E("share", "count", "share-of-model-output"),
        "numerator": eng(NUM_OR_NULL, "appetite.appetite_metrics"),
        "denominator": eng(NUM_OR_NULL, "appetite.appetite_metrics"),
        "reason": nullable(TXT),
        "threshold": R("appThreshold"),
        "light": eng(E("green", "amber", "red", "not_evaluated"), "appetite.light"),
    }, "One B.6 metric (06 l.606-612) with its value, unit, numerator, denominator and its light under a stated threshold.")
    when_null(metric, "value", ["reason"])
    when(metric, "value", None, {"light": C("not_evaluated")})
    d.update({"appThreshold": threshold, "appMetric": metric})
    return d


def appetite_schema() -> dict:
    d = appetite_defs()
    props, _ = header("appetite", [], {
        "population": Ob({"entries": Int(0), "findings": Int(0), "tier1_entries": Int(0)}),
        "metrics": A(R("appMetric"), 7, 7),
    })
    root = Ob(props)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{BASE}governance/governance-appetite.schema.json",
            "title": "Governance model risk appetite",
            "description": "Catalog row governance-appetite 1.0.0: the model risk appetite metrics of 06 B.6 (data/derived/governance/appetite.json), "
                           "each with its value, unit, numerator, denominator and a light under a stated convention threshold.",
            **root, "$defs": reachable(root, d)}


def write(name: str, doc: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    write("governance-inventory.schema.json", inventory_schema())
    write("governance-findings.schema.json", findings_schema())
    write("governance-report.schema.json", report_schema())
    write("governance-appetite.schema.json", appetite_schema())


if __name__ == "__main__":
    main()
