"""The governance bake (unit U15-P): reads the committed case documents and writes the inventory, the findings register, the appetite and the reports.

``build`` makes the documents in memory, ``check_documents`` refuses them if the schema or the cross-field checker of U15-S (``tests/contracts_u15/semantics.py``)
finds anything, and ``bake`` writes them (and ``docs/governance.md``). Every computed value is the return value of an engine function of
``riskvalidation.governance`` (0.9.0, ADR-0069); the product holds the inputs (``inputs.json``, the related links of ``edges.json``; the dependency edges are the ``depends_on`` of the case manifests, U16-P1b), the texts and the counting of what the
documents already say. A case document that is absent or invalid stops the bake with the file named and nothing is written. Deterministic: no clock, no random
draw, every list in a fixed order.
"""
from __future__ import annotations

import fnmatch
import hashlib
import importlib.metadata as imd
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from . import APPETITE_REL, FINDINGS_REL, INVENTORY_REL, REPORTS_DIR, SUMS_REL, attributes, edge_table, report_rel
from .readers import REPO_ROOT, BakeError, Case, Reader, newest_release, read_corpus, release_dates
from .reader import reader_text

INPUTS_REL = "data-pipeline/pipeline/governance/inputs.json"
PAGE_REL = "docs/governance.md"
SEMANTICS_REL = "tests/contracts_u15/semantics.py"
GENERATORS = ["contraste:governance-bake"]
SEVERITIES = ("S1", "S2", "S3", "S4")
READINGS = ("A", "B", "C", "D")
#: the tiers whose review is an attestation (06 l.636-640: Tier 4 states an attestation every three years); the engine's table holds the months only
ATTESTATION_TIERS = (4,)
FACTOR_NAMES = ["methodology", "data", "explainability", "dynamic updating", "dependency depth", "reproducibility"]
F7 = {"id": "F7", "name": "history against horizon", "score": None, "tag": "convention",
      "basis": "not scored: history against the forecast horizon is not a field in any committed document (A D2 3.3)"}
RANKS_NOTE = "the rank inside a generation is the layout's"


def T(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def _engine_text(reason: str) -> dict[str, str]:
    """The English reason of an engine function and its Spanish, both from the engine's reason table (``riskvalidation.governance.reasons``, engine-governance-api
    1.1.0): the Spanish carries its accents. A sentence the table does not hold raises ``ValueError``; no text is invented or left in English."""
    from riskvalidation.governance.reasons import bilingual

    try:
        return bilingual(reason)
    except ValueError as exc:
        raise BakeError(f"the engine holds no Spanish text for the reason {reason!r}: {exc}") from exc


@dataclass
class Baked:
    """The documents of one bake and the block of the page."""

    inventory: dict[str, Any]
    findings: dict[str, Any]
    appetite: dict[str, Any]
    reports: dict[str, dict[str, Any]]
    page_block: str = ""
    documents_read: list[dict[str, Any]] = field(default_factory=list)


def _engine() -> SimpleNamespace:
    """The engine modules, read as attributes at call time (a test may replace one function); the validation families register their tests on import."""
    import riskvalidation.validation  # noqa: F401  (spec(test_id) resolves the kind of a test only after the catalogue is registered)
    from riskvalidation.governance import appetite, conventions, findings, inventory, lifecycle, opinion, report, schedule, scope, tiering

    return SimpleNamespace(appetite=appetite, conventions=conventions, findings=findings, inventory=inventory, lifecycle=lifecycle, opinion=opinion,
                           report=report, schedule=schedule, scope=scope, tiering=tiering, version=imd.version("riskvalidation"))


def _semantics():
    """tests/contracts_u15/semantics.py under a name of its own (other suites ship a helper of the same name); it needs only the standard library."""
    name = "contraste_u15_semantics"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / SEMANTICS_REL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --- the inputs --------------------------------------------------------------------------------------------------------------------


def _validate_inputs(inputs: dict[str, Any], cases: dict[str, Case]) -> None:
    """Every built case has its inputs, and every tier input has its tag, its basis and (but for a stated whole or absent balance) its document pointer."""
    for cid in cases:
        c = inputs["cases"].get(cid)
        if c is None:
            raise BakeError(f"{INPUTS_REL}: the built case {cid} has no inputs (a tier input with no committed basis is missing with its reason, never guessed)")
        t = c["tier"]
        blocks = {"exposure": t["exposure"], "regulatory_use": t["regulatory_use"], "decision_criticality": t["decision_criticality"]}
        for name, b in blocks.items():
            if b.get("tag") not in ("doc", "convention"):
                raise BakeError(f"{INPUTS_REL}: {cid} {name} has the tag {b.get('tag')!r}, expected doc or convention")
            if not str(b.get("basis", "")).strip():
                raise BakeError(f"{INPUTS_REL}: {cid} {name} has no basis")
        for name in ("regulatory_use", "decision_criticality"):
            if not t[name].get("pointer"):
                raise BakeError(f"{INPUTS_REL}: {cid} {name} has no document pointer")
        if t["exposure"]["kind"] not in ("whole", "none") and not t["exposure"].get("pointer"):
            raise BakeError(f"{INPUTS_REL}: {cid} exposure has no document pointer")
        if [f["id"] for f in t["factors"]] != [f"F{i}" for i in range(1, 7)]:
            raise BakeError(f"{INPUTS_REL}: {cid} does not score the factors F1 to F6 in order")
        for f in t["factors"]:
            if f.get("tag") not in ("doc", "convention") or not str(f.get("basis", "")).strip() or not f.get("pointer"):
                raise BakeError(f"{INPUTS_REL}: {cid} factor {f['id']} needs a tag, a basis and a document pointer")
            if f["score"] is not None and f["score"] not in (1, 2, 3, 4):
                raise BakeError(f"{INPUTS_REL}: {cid} factor {f['id']} has the score {f['score']!r}")


def _exposure_share(spec: dict[str, Any], cases: dict[str, Case], key: str) -> float | None:
    """The share of the stated balance: a segment of the C07 book or a risk component of the C18 RWA, read from the committed documents (4 decimals)."""
    kind = spec["kind"]
    if kind == "whole":
        return 1.0
    if kind == "none":
        return None
    if kind == "c07-segment-share":
        fit = cases["C07"].models["banco-andino"].doc["fit"]["segments"] if "C07" in cases else None
        if fit is None:
            raise BakeError(f"{key}: the exposure reads the C07 segments and C07 is not built")
        total = sum(s["gross_exposure"] for s in fit)
        part = sum(s["gross_exposure"] for s in fit if s["id"] in spec["segments"])
        if not part:
            raise BakeError(f"{key}: the segments {spec['segments']} are not in the C07 models document")
        return round(part / total, 4)
    if kind == "c18-rwa-share":
        base = cases["C18"].variants["baseline"].doc["outputs"]["capital_start"]["rwa_by_risk"] if "C18" in cases else None
        if base is None:
            raise BakeError(f"{key}: the exposure reads the C18 RWA and C18 is not built")
        return round(base[spec["risk"]] / sum(base.values()), 4)
    raise BakeError(f"{key}: unknown exposure kind {kind!r}")


# --- variants to fits (W15-15) ------------------------------------------------------------------------------------------------------


def _assign(case: Case, extensions: list[str], E: SimpleNamespace) -> tuple[dict[str, list[tuple[str, str]]], list[tuple[str, str]]]:
    """(fit id to [(variant id, basis)], [(variant id, engine reason)]). The engine's rule first; where it finds no fit in a case of several fits, the
    committed identities named in ``extensions``; a variant neither places is returned with the engine's reason."""
    fits = {fit: [i["source"] for i in m.doc["provenance"]["inputs"]] for fit, m in case.models.items()}
    placed: dict[str, list[tuple[str, str]]] = {fit: [] for fit in fits}
    left: list[tuple[str, str]] = []
    for vid, v in case.variants.items():
        sources = [i["source"] for i in v.doc["provenance"]["inputs"]]
        fit, basis = E.inventory.assign_variant(sources, fits)
        if fit is not None:
            placed[fit].append((vid, f"{basis} (W15-15)"))
            continue
        reason = basis
        found = None
        if len(fits) > 1:
            ids = [m["id"] for m in v.doc["model"]]
            if "model-record-ids" in extensions:
                same = [f for f, m in case.models.items() if [x["id"] for x in m.doc["model"]] == ids]
                if len(same) == 1:
                    found = (same[0], f"the variant's model records carry the ids of the fit {same[0]} and of no other fit of the case (W15-15, extension "
                                      f"model-record-ids; the engine found no fit by sources: {reason})")
            if found is None and "variant-id-equals-fit-id" in extensions and vid in fits:
                found = (vid, f"the variant id equals the fit id {vid} of the models document (W15-15, extension variant-id-equals-fit-id: the producers write the models "
                              f"document with fit_id equal to the variant id, c06/_case.py:103 and c08/_case.py:99; the engine found no fit by sources: {reason})")
        if found:
            placed[found[0]].append((vid, found[1]))
        else:
            left.append((vid, reason))
    return placed, left


# --- tier, schedule, scope -----------------------------------------------------------------------------------------------------------


def _fill(text: str, models_path: str, manifest_path: str, default_path: str) -> str:
    return text.replace("{models}", models_path).replace("{manifest}", manifest_path).replace("{default}", default_path)


def _tier_block(E: SimpleNamespace, key: str, inp: dict[str, Any], share: float | None, paths: tuple[str, str, str]) -> dict[str, Any]:
    t = inp["tier"]
    cuts = E.conventions.EXPOSURE_BAND_CUTS
    band = E.tiering.exposure_band(share, cuts)
    reg, dec = t["regulatory_use"], t["decision_criticality"]
    m = {"literal": E.tiering.materiality(band, reg["literal"], dec["score"]), "graded": E.tiering.materiality(band, reg["graded"], dec["score"])}
    factors = []
    for f in t["factors"]:
        ptr = _fill(f["pointer"], *paths)
        factors.append({"id": f["id"], "name": f["name"], "score": f["score"], "tag": f["tag"], "basis": f"{f['basis']} (read at {ptr})"})
    factors.append(dict(F7))
    scores = [f["score"] for f in factors if f["score"] is not None]
    c = {"mean": E.tiering.complexity(scores), "maximum": E.tiering.complexity(scores, aggregation="maximum")}
    rows = E.tiering.tier_sensitivity(share, reg["literal"], reg["graded"], dec["score"], scores, cuts)
    sens = [{"reading": r[0], "regulatory_use": r[1], "complexity": r[2], "m": r[3], "c": r[4], "tier": r[5]} for r in rows]
    adopted = next(r for r in sens if r["reading"] == E.conventions.ADOPTED_READING)
    computed = adopted["tier"]
    exp = t["exposure"]
    exp_ptr = f"; read at {_fill(exp['pointer'], *paths)}" if exp.get("pointer") else ""
    return {
        "materiality": {
            "exposure": {"share": share, "band": band, "tag": exp["tag"],
                         "basis": f"{exp['basis']}; band cut points {', '.join(f'{x * 100:g}' for x in cuts)} percent (a convention, A D2 3.2){exp_ptr}"},
            "regulatory_use": {"literal": reg["literal"], "graded": reg["graded"], "tag": reg["tag"],
                               "basis": f"{reg['basis']} (read at {_fill(reg['pointer'], *paths)})"},
            "decision_criticality": {"score": dec["score"], "tag": dec["tag"], "basis": f"{dec['basis']} (read at {_fill(dec['pointer'], *paths)})"},
            "m": m,
        },
        "complexity": {"factors": factors, "scored": len(scores), "sum": sum(scores), "mean": round(sum(scores) / len(scores), 2), "c": c},
        "adopted_reading": E.conventions.ADOPTED_READING, "computed_tier": computed,
        "override": None, "tier": E.tiering.apply_override(computed, None), "tier_sensitivity": sens,
    }


def _schedule(E: SimpleNamespace, tier: int, last: str) -> dict[str, Any]:
    review, full, monitor = E.schedule.next_dates(tier, date.fromisoformat(last))
    iso = lambda d: None if d is None else d.isoformat()  # noqa: E731
    stated = full is not None and monitor is not None
    return {
        "profile": "default", "review_kind": "attestation" if tier in ATTESTATION_TIERS else "review",
        "last_validation": {"date": last, "type": "full battery", "basis": "convention (A34): the release date of the code version in CHANGELOG.md is read as the date of the last validation"},
        "next_review": iso(review), "next_full_revalidation": iso(full), "next_monitoring": iso(monitor),
        "null_reason": None if stated else T("the frequency table of this tier states no full revalidation or no monitoring interval (06 l.636-640)",
                                             "la tabla de frecuencias de este nivel no fija una revalidación completa o un monitoreo (06 l.636-640)"),
    }


def _scope(E: SimpleNamespace, inputs: dict[str, Any], case_id: str) -> dict[str, Any]:
    a = inputs["scope_answers"]
    answers = E.scope.ScopeAnswers(a["applies_theory"], a["output_is_estimate"], a["deterministic"], a["generative_or_agentic"])
    profiles = [{"profile": d.profile, "in_scope": d.in_scope, "rationale": _engine_text(d.rationale)} for d in E.scope.scope_record(answers)]
    note = inputs["scope_notes"]["cases"].get(case_id)
    basis = (f"{a['basis']}; the profile rules are a reading of the B.1 table (UNVERIFIED beyond it)" + (f"; {note}" if note else ""))
    return {"answers": {k: a[k] for k in ("applies_theory", "output_is_estimate", "deterministic", "generative_or_agentic")}, "profiles": profiles, "basis": basis}


def _components(case_id: str, fit_id: str, models: dict[str, Any], roles: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for m in models["model"]:
        role, tag, basis = roles["default"], roles["tag"], roles["basis"]
        for rule in roles["rules"]:
            if any(fnmatch.fnmatchcase(m["id"], pat) for pat in rule["match"]):
                role, tag, basis = rule["role"], rule.get("tag", roles["tag"]), rule.get("basis", roles["basis"])
                break
        out.append({"key": f"{case_id}/{fit_id}/{m['id']}", "model_id": m["id"], "role": role, "role_tag": tag, "role_basis": basis,
                    "family": m.get("family"), "rung": m.get("rung"), "title": m.get("title")})
    return out


# --- the register (W15-5) -----------------------------------------------------------------------------------------------------------------


def _risk_acceptance() -> dict[str, Any]:
    return {"approver": "not-applicable",
            "approver_reason": T("a stated limit of a synthetic case: Contraste approves no model, so there is no approver",
                                 "un límite declarado de un caso sintético: Contraste no aprueba ningún modelo, por lo que no hay aprobador"),
            "expiry": None,
            "expiry_reason": T("the limit is a property of the case, not a time-limited acceptance of a risk",
                               "el límite es una propiedad del caso, no la aceptación de un riesgo con plazo")}


def _register_rows(E: SimpleNamespace, key: str, owner: str, tier: int, variants: list[tuple[str, str, dict[str, Any]]], as_of: date,
                   dates: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for vid, path, doc in variants:
        cv = doc["provenance"]["code_version"]
        if cv not in dates:
            raise BakeError(f"CHANGELOG.md: no release heading for the code version {cv} of {path}, so its findings have no raised date")
        raised = date.fromisoformat(dates[cv])
        for f in doc["findings"]:
            sev = f["severity"]
            days = E.findings.deadline_days(sev, tier)
            due = E.findings.due_date(raised, days)
            status = E.findings.map_product_status(f["status"])
            anchor, why = E.findings.anchor_from_test_row(f["evidence"], doc["tests"], document=path)
            share, share_why = E.findings.rwea_share_of_anchor(anchor)
            rows.append({
                "key": f"{doc['case_id']}/{vid}/{f['id']}", "case_id": doc["case_id"], "variant_id": vid, "id": f["id"], "entry_key": key,
                "title": f["title"], "severity": sev, "ecb_f": E.findings.severity_to_ecb(sev), "product_status": f["status"], "status": status,
                "evidence": f["evidence"], "anchor": anchor, "anchor_reason": None if why is None else reader_text(_engine_text(why)),
                "rwea_share": share, "rwea_share_reason": None if share_why is None else reader_text(_engine_text(share_why)),
                "owner_role": owner, "tier": tier, "raised": raised.isoformat(), "deadline_days": days, "due": due.isoformat(),
                "ageing_days": E.findings.ageing_days(raised, as_of), "overdue": E.findings.is_overdue(status, due, as_of),
                "remediation": None,
                "remediation_reason": T("no remediation plan: the finding is an open result or a stated limit of a synthetic case",
                                        "sin plan de remediación: el hallazgo es un resultado abierto o un límite declarado de un caso sintético"),
                "risk_acceptance": _risk_acceptance() if status == "risk_accepted" else None,
            })
    return rows


# --- the layout (networkx) -----------------------------------------------------------------------------------------------------------


def _layout(E: SimpleNamespace, keys: list[str], pairs: list[tuple[str, str]]) -> dict[str, tuple[float, float, int]]:
    """(x, y, generation) of each entry: the generation is the engine's (Kahn's algorithm), networkx lays the columns (``multipartite_layout``) and its
    ``topological_generations`` must agree with the engine's."""
    import networkx as nx

    gens = E.inventory.topological_order(keys, pairs)
    depth = {k: i for i, layer in enumerate(gens) for k in layer}
    g = nx.DiGraph()
    for k in sorted(keys):
        g.add_node(k, generation=depth[k])
    g.add_edges_from(sorted(set(pairs)))
    theirs = {k: i for i, layer in enumerate(nx.topological_generations(g)) for k in layer}
    if theirs != depth:
        raise BakeError("the engine's generations of the dependency graph and networkx's differ: " + str(sorted(k for k in depth if theirs.get(k) != depth[k])[:5]))
    layers = {i: sorted(layer) for i, layer in enumerate(gens)}   # a dict of sorted layers: the order inside a column is the key order, never a set's
    pos = nx.multipartite_layout(g, subset_key=layers, align="vertical")
    return {k: (round(float(pos[k][0]), 4), round(float(pos[k][1]), 4), depth[k]) for k in keys}


# --- the documents -------------------------------------------------------------------------------------------------------------------------


def _inventory_conventions(E: SimpleNamespace) -> dict[str, Any]:
    c, C = E.conventions, E.conventions.CONVENTIONS
    freq = []
    for tier, (review, full, monitor) in sorted(c.FREQUENCY.items()):
        freq.append({"tier": tier, "review_kind": "attestation" if tier in ATTESTATION_TIERS else "review", "review_months": review,
                     "revalidation_months": full, "monitoring_months": monitor,
                     "null_reason": None if (full and monitor) else T("the table states none for this tier (06 l.636-640)",
                                                                       "la tabla no fija ninguno para este nivel (06 l.636-640)")})
    return {
        "exposure_band_cuts": {"label": c.CONVENTION, "basis": C["EXPOSURE_BAND_CUTS"]["basis"], "cuts": list(c.EXPOSURE_BAND_CUTS)},
        "regulatory_use_grades": {"label": c.CONVENTION, "basis": C["REGULATORY_USE_GRADES"]["basis"], **{k: dict(v) for k, v in c.REGULATORY_USE_GRADES.items()}},
        "complexity_rounding": {"label": c.CONVENTION, "basis": C["COMPLEXITY_AGGREGATION"]["basis"],
                                "rule": f"{c.COMPLEXITY_AGGREGATION['aggregation']}-rounded-{c.COMPLEXITY_AGGREGATION['rounding']}"},
        "frequency": {"label": c.CONVENTION, "basis": C["FREQUENCY"]["basis"], "tiers": freq},
        "adopted_reading": {"label": c.CONVENTION, "basis": C["ADOPTED_READING"]["basis"], "reading": c.ADOPTED_READING},
    }


def _governance_findings(E: SimpleNamespace) -> list[dict[str, Any]]:
    return [
        {"id": "GOV-RUBRIC-BLIND-SPOT", "severity": "S3", "ecb_f": E.findings.severity_to_ecb("S3"), "status": "open",
         "title": T("The tier rubric has no materiality term for fan-out", "La rúbrica de niveles no tiene un término de materialidad por dependencia"),
         "description": T("The engine and C22's test sizing reach every case, yet C22 keeps the tier its inputs give (Tier 4): the rubric counts feeders in "
                          "complexity and has no term for fan-out in materiality (A D2 3.5 item 3).",
                          "El motor y el dimensionamiento de pruebas de C22 alcanzan a todos los casos, pero C22 conserva el nivel que dan sus insumos (Nivel 4): "
                          "la rúbrica cuenta alimentadores en la complejidad y no tiene un término de dependencia en la materialidad (A D2 3.5, punto 3)."),
         "basis": "W15-3; A D2 3.5 item 3"},
        {"id": "GOV-INDEPENDENCE-NOT-ESTABLISHED", "severity": "S2", "ecb_f": E.findings.severity_to_ecb("S2"), "status": "open",
         "title": T("Independence of the validator is not established", "La independencia del validador no está establecida"),
         "description": T("The pipeline (developer) and the engine (validator) are built in the same programme, so the separation of the first and second "
                          "line is a convention, not a fact (A D1 A31).",
                          "La cadena de cálculo (desarrollador) y el motor (validador) se construyen en el mismo programa, por lo que la separación entre primera y segunda "
                          "línea es una convención y no un hecho (A D1 A31)."),
         "basis": "W15-4; A D1 A31"},
    ]


def _findings_conventions(E: SimpleNamespace) -> dict[str, Any]:
    c, C = E.conventions, E.conventions.CONVENTIONS
    return {
        "deadline_days": {"label": c.CONVENTION, "basis": C["DEADLINE_DAYS"]["basis"],
                          "rows": [{"severity": s, "days": list(c.DEADLINE_DAYS[s])} for s in SEVERITIES]},
        "severity_scale": {"label": c.CONVENTION,
                           "basis": "W15-2: the product keeps S1 critical to S4 minor; the ECB F equivalent is shown beside it (06 l.616-617): S1 is F4 "
                                    "(very high), S2 F3, S3 F2, S4 F1 (low)",
                           "rows": [{"severity": s, "ecb_f": E.findings.severity_to_ecb(s)} for s in SEVERITIES]},
        "status_map": {"label": c.CONVENTION,
                       "basis": "W15-5: open to open, accepted to risk_accepted, closed to validated_closed; overdue is computed from the due date and as_of",
                       "rows": [{"product": p, "register": E.findings.map_product_status(p)} for p in E.findings.PRODUCT_STATUSES]},
    }


def _own_findings_note(metrics: list[dict[str, Any]], own: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The metrics that count findings say in the basis of their threshold that the count includes the inventory's own findings, with their ids."""
    ids = ", ".join(f["id"] for f in own)
    for m in metrics:
        if m["id"] in ("open-high-severity", "overdue-remediation"):
            m["threshold"]["basis"] += f"; the count includes the inventory's own findings ({ids}; W15-3, W15-4)"
    return metrics


def _filtered_provenance(prov: dict[str, Any], keep: set[str]) -> dict[str, Any]:
    return {**prov, "documents_read": [d for d in prov["documents_read"] if d["path"] in keep]}


def build(root: Path | str = REPO_ROOT) -> Baked:
    """The governance documents over the committed case documents under ``root``, checked, not written."""
    E = _engine()
    reader = Reader(root)
    inputs = reader.json(INPUTS_REL)
    dates = release_dates(reader)
    as_of_version, as_of_iso = newest_release(dates)
    as_of = date.fromisoformat(as_of_iso)
    cases, planned = read_corpus(reader)
    table = edge_table.load_edges(reader, {cid: c.manifest for cid, c in cases.items()})
    _validate_inputs(inputs, cases)
    extensions = inputs["variant_assignment"]["extensions"]
    rv = E.version
    code_version = inputs["release"]["code_version"]

    # --- the entries: one per fit (W15-1), with the variants assigned to it (W15-15)
    excluded: list[dict[str, Any]] = []
    plan: list[dict[str, Any]] = []
    for x in planned:
        excluded.append({"case_id": x["case_id"], "variant_id": None,
                         "reason": T(x["reason"], "planificado: no existe documento ni registro de modelos confirmado")})
    for cid in sorted(cases):
        case = cases[cid]
        placed, left = _assign(case, extensions, E)
        for vid, why in left:
            n = len(case.variants[vid].doc["findings"])
            excluded.append({"case_id": cid, "variant_id": vid, "reason": T(
                f"no fit can be assigned to the variant: {why}; its {n} finding rows are not in the register",
                f"no se puede asignar un ajuste a la variante: {_engine_text(why)['es']}; sus {n} filas de hallazgos no están en el registro")})
        order = list(case.variants)
        for fit in sorted(case.models):
            mine = sorted(placed[fit], key=lambda p: order.index(p[0]))
            if not mine:
                excluded.append({"case_id": cid, "variant_id": None, "reason": T(
                    f"the fit {cid}/{fit} has no variant document assigned to it, so it has no test rows or findings to inventory",
                    f"el ajuste {cid}/{fit} no tiene un documento de variante asignado, por lo que no tiene filas de prueba ni hallazgos que inventariar")})
                continue
            plan.append({"case": case, "fit": fit, "variants": mine})
    if not plan:
        raise BakeError("no fit has a variant document: the inventory would hold no entry")

    stubs = [{"key": f"{p['case'].case_id}/{p['fit']}", "case_id": p["case"].case_id, "variants": [{"variant_id": v} for v, _ in p["variants"]]} for p in plan]
    defaults = {cid: cases[cid].manifest["default_variant"] for cid in cases}
    edges, related = edge_table.expand(table, stubs, defaults)
    pairs = [(e["upstream"], e["downstream"]) for e in edges]
    keys = [s["key"] for s in stubs]

    # --- the tier, the schedule and the register of each entry, then its attributes
    draft: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for p in plan:
        case, fit = p["case"], p["fit"]
        cid = case.case_id
        key = f"{cid}/{fit}"
        inp = inputs["cases"][cid]
        models = case.models[fit]
        vids = [v for v, _ in p["variants"]]
        default_id = case.manifest["default_variant"] if case.manifest["default_variant"] in vids else next(v for v in case.variants if v in vids)
        default = case.variants[default_id]
        paths = (models.path, case.manifest_path, default.path)
        share = _exposure_share(inp["tier"]["exposure"], cases, key)
        tb = _tier_block(E, key, inp, share, paths)
        cv = models.doc["provenance"]["code_version"]
        if cv not in dates:
            raise BakeError(f"CHANGELOG.md: no release heading for the code version {cv} of {models.path}, so its last validation has no date")
        last = dates[cv]
        sched = _schedule(E, tb["tier"], last)
        E.lifecycle.allowed_next("in_validation")
        variants = [(v, case.variants[v].path, case.variants[v].doc) for v in vids]
        rows = _register_rows(E, key, inp["owner_role"], tb["tier"], variants, as_of, dates)
        ctx = attributes.Ctx(
            case_id=cid, fit_id=fit, key=key, manifest=case.manifest, manifest_path=case.manifest_path, models=models.doc, models_path=models.path,
            default=default.doc, default_path=default.path, variants=variants, case_inputs=inp, sources=inputs["attribute_sources"], tier_block=tb,
            schedule=sched, upstream=sorted({u for u, d in pairs if d == key}), downstream=sorted({d for u, d in pairs if u == key}),
            validator=f"riskvalidation {rv}", last_validation=last, code_version=cv)
        attrs = attributes.build(ctx, rows)
        draft.append({"key": key, "case_id": cid, "fit_id": fit, "title": case.manifest["title"], "attributes": attrs,
                      "variants": [{"variant_id": v, "basis": b} for v, b in p["variants"]],
                      "components": _components(cid, fit, models.doc, inp["roles"]), "scope": _scope(E, inputs, cid), "tier_block": tb,
                      "lifecycle": {"state": "in_validation", "basis": "convention: the state in_validation reads the committed documents (the full battery has run and no approval exists, SDD non-goal 1); "
                                                                        "transitions are not recorded in them", "transitions": [], "exception": None},
                      "schedule": sched, "_default": default_id, "_models": models, "_case": case, "_variants": variants})
        all_rows += rows

    # --- the engine's inventory: unique keys, acyclic, the metrics of the graph
    eng_entries = [E.inventory.Entry(d["case_id"], d["fit_id"], d["attributes"], tuple((v["variant_id"], v["basis"]) for v in d["variants"]),
                                     tuple(E.inventory.Component(d["case_id"], d["fit_id"], c["model_id"], c["role"]) for c in d["components"])) for d in draft]
    eng = E.inventory.build_inventory(eng_entries, [E.inventory.Edge(e["upstream"], e["downstream"], e["kind"], e["stated_source"]) for e in edges],
                                      related=[(r["a"], r["b"]) for r in related])
    metrics = E.inventory.graph_metrics(eng)
    layout = _layout(E, keys, pairs)

    entries = []
    for d in draft:
        depth, fan_in, fan_out = metrics[d["key"]]
        x, y, gen = layout[d["key"]]
        e = {k: v for k, v in d.items() if not k.startswith("_")}
        e["graph"] = {"depth": depth, "fan_in": fan_in, "fan_out": fan_out}
        e["map"] = {"generation": gen, "x": x, "y": y}
        entries.append(e)
    entries.sort(key=lambda e: e["key"])
    draft.sort(key=lambda d: d["key"])

    # --- documents: the shared header, then the four kinds
    docs_read = reader.documents_read()
    provenance = {"code_version": code_version, "riskvalidation_version": rv, "generators": GENERATORS, "documents_read": docs_read}
    as_of_basis = {"label": "convention", "basis": T(
        f"{inputs['as_of']['basis']['en']} Here: the heading of release {as_of_version}, {as_of_iso}.",
        f"{inputs['as_of']['basis']['es']} Aquí: el encabezado de la versión {as_of_version}, {as_of_iso}.")}
    head = {"case_id": "GOVERNANCE", "schema_version": "1.0.0", "as_of": as_of_iso, "as_of_basis": as_of_basis}
    tiers_by_reading = [[e["tier_block"]["tier_sensitivity"][i]["tier"] for e in entries] for i in range(len(READINGS))]
    inventory = {
        "schema": "contraste.governance.inventory/v1", "governance_id": "inventory", **head, "provenance": provenance,
        "conventions": _inventory_conventions(E),
        "engine_node": {"key": "riskvalidation", "version": rv,
                        "basis": "every entry depends on the engine: it computes every value and runs every test (W15-8)"},
        "entries": entries, "edges": edges, "related": related, "excluded": excluded,
        "completeness": {"entries": len(entries), "attributes": E.inventory.attribute_completeness(entries)},
        "tier_counts": [{"reading": r, "counts": list(E.tiering.tier_counts(t))} for r, t in zip(READINGS, tiers_by_reading)],
        "governance_findings": _governance_findings(E),
    }
    findings = {
        "schema": "contraste.governance.findings/v1", "governance_id": "findings", **head, "provenance": provenance,
        "conventions": _findings_conventions(E), "rows": all_rows, "counts": E.findings.register_counts(all_rows),
    }
    # B.6 counts the inventory's own findings (W15-3, W15-4) too: the findings schema admits only a case entry, so they go to the engine's appetite
    # functions beside the register rows, under the entry key GOVERNANCE
    own = [{"entry_key": "GOVERNANCE", "id": f["id"], "severity": f["severity"], "status": f["status"], "overdue": False} for f in inventory["governance_findings"]]
    counted = all_rows + own
    appetite = {
        "schema": "contraste.governance.appetite/v1", "governance_id": "appetite", **head, "provenance": provenance,
        "population": E.appetite.appetite_population(entries, counted),
        "metrics": _own_findings_note(list(E.appetite.appetite_metrics(entries, counted, as_of)), inventory["governance_findings"]),
    }
    reports: dict[str, dict[str, Any]] = {}
    for d, e in zip(draft, entries):
        case = d["_case"]
        key = e["key"]
        order = [d["_default"]] + [v for v, _, _ in d["_variants"] if v != d["_default"]]
        by_id = {v: (path, doc) for v, path, doc in d["_variants"]}
        variants = [{"variant_id": v, "path": by_id[v][0], "tests": by_id[v][1]["tests"], "seed": by_id[v][1]["provenance"].get("seed"),
                     "code_version": by_id[v][1]["provenance"].get("code_version"),
                     "riskvalidation_version": by_id[v][1]["provenance"].get("riskvalidation_version")} for v in order]
        own = {case.manifest_path, d["_models"].path, *[p for _, p, _ in d["_variants"]], "CHANGELOG.md", INPUTS_REL, edge_table.EDGES_REL}
        scoped = {"provenance": _filtered_provenance(provenance, own), "as_of_basis": as_of_basis}
        reports[key] = _reader_missing(_drop_battery_key(E.report.build_report(e, scoped, [r for r in all_rows if r["entry_key"] == key], variants, as_of)))

    check_documents(inventory, findings, appetite, reports)
    from . import page

    return Baked(inventory, findings, appetite, reports, page.results_block(inventory, findings, appetite, reports), docs_read)


def _drop_battery_key(report: dict[str, Any]) -> dict[str, Any]:
    """The engine returns the key ``battery`` of a policy identity only for a packaged label written with its parameters appended (engine-governance-api 1.1.0); the
    ``governance-report`` schema has no such key and the token stays in the row's ``label``, so the key is dropped (a document never holds a key its contract does not name)."""
    for section in report["sections"]:
        for block in section.get("blocks", []):
            if block.get("kind") == "outcomes":
                for row in block["rows"]:
                    row["policy"].pop("battery", None)
    return report


def _reader_missing(report: dict[str, Any]) -> dict[str, Any]:
    """The engine's sentences on what a report section misses, in reader words (``reader_text``, the rules the governance views apply): its Spanish
    "Replicación independiente del pipeline" reads "de la cadena de cálculo", as the views already showed it (2026-10-27 ruling)."""
    for section in report["sections"]:
        for m in section.get("missing", []):
            for k in ("element", "reason"):
                if isinstance(m.get(k), dict):
                    m[k] = reader_text(m[k])
    return report


def _copied_texts(cases: dict[str, Case]) -> frozenset[str]:
    """The texts the documents copy unchanged from the case documents (a case question and title, a finding title, a model record title): the case's own words, such as
    'approval cohorts' or 'approval rate' in a credit model, stay as the case wrote them (the accent and English checks of the tests skip them). The checker's text rule reads them
    too: its allow list names the phrases that are metrics or cohorts."""
    out: set[str] = set()
    for case in cases.values():
        for field_ in ("question", "title"):
            v = case.manifest.get(field_)
            out.update(v.values() if isinstance(v, dict) else [v])
        for var in case.variants.values():
            for f in var.doc["findings"]:
                out.update(f["title"].values())
        for m in case.models.values():
            for rec in m.doc["model"]:
                for field_ in ("title", "short_title"):
                    if isinstance(rec.get(field_), dict):
                        out.update(rec[field_].values())
    return frozenset(x for x in out if isinstance(x, str) and " " in x)  # an identifier is never a text


def check_documents(inventory: dict[str, Any], findings: dict[str, Any], appetite: dict[str, Any], reports: dict[str, dict[str, Any]]) -> None:
    """The schema and the cross-field checker of U15-S over the documents; any finding refuses them all (nothing is published).

    The checker's text rule reads every string, the copied case texts included; its allow list (``semantics.APPROVAL_ALLOWED``) names the phrases of a credit
    decision that are metrics or cohorts and never a claim about a model."""
    from ..core.schemas import SchemaViolation, validate_document

    sm = _semantics()
    problems: list[str] = []
    named = [(INVENTORY_REL, inventory), (FINDINGS_REL, findings), (APPETITE_REL, appetite)] + [(report_rel(k), r) for k, r in sorted(reports.items())]
    for rel, doc in named:
        try:
            validate_document(f"data/derived/{rel}", doc)
        except SchemaViolation as exc:
            problems.append(str(exc))
        problems += [f"{rel}: {m}" for m in sm.violations(doc)]
    problems += [f"across the documents: {m}" for m in sm.cross_violations(
        {"inventory": inventory, "findings": findings, "appetite": appetite, "reports": reports})]
    if problems:
        more = f" (and {len(problems) - 6} more)" if len(problems) > 6 else ""
        raise BakeError("the governance documents are refused, nothing is written: " + "; ".join(problems[:6]) + more)


# --- writing -----------------------------------------------------------------------------------------------------------------------------


def serialise(doc: dict[str, Any]) -> bytes:
    """The bytes of a document: compact JSON, UTF-8, LF, no trailing newline (the form of every other committed document)."""
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def bake(output_root: Path | str, root: Path | str = REPO_ROOT, write_page: bool = True) -> dict[str, str]:
    """Build, check and write ``<output_root>/governance/`` (the documents and SHA256SUMS.txt); returns the path to sha256 map.

    The page ``docs/governance.md`` of ``root`` has its results block replaced when ``write_page`` is set. Nothing is written when the build refuses."""
    built = build(root)
    out = Path(output_root)
    files: dict[str, bytes] = {INVENTORY_REL: serialise(built.inventory), FINDINGS_REL: serialise(built.findings), APPETITE_REL: serialise(built.appetite)}
    for key, rep in built.reports.items():
        files[report_rel(key)] = serialise(rep)
    sums = {rel: hashlib.sha256(data).hexdigest() for rel, data in files.items()}
    files[SUMS_REL] = "".join(f"{sha}  {rel}\n" for rel, sha in sorted(sums.items())).encode("utf-8")
    reports_dir = out / REPORTS_DIR
    if reports_dir.is_dir():
        for stale in reports_dir.glob("*.json"):
            if f"{REPORTS_DIR}/{stale.name}" not in files:
                stale.unlink()
    for rel, data in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if write_page:
        from . import page

        page.write_page(Path(root) / PAGE_REL, built.page_block)
    return sums


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Bake data/derived/governance/ (inventory, findings, appetite, reports) through riskvalidation.governance")
    ap.add_argument("--output-root", default=str(REPO_ROOT / "data" / "derived"), help="the derived-data root (default data/derived of this repository)")
    args = ap.parse_args(argv)
    sums = bake(args.output_root)
    print(f"wrote {len(sums)} documents under {Path(args.output_root) / 'governance'} and docs/governance.md", file=sys.stderr)
    return 0
