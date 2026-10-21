"""The forty B.2 attributes of an inventory entry (06 l.539-551, the addendum D1 map).

Each attribute is ``{"value", "status", "basis"}``, never a bare value: ``present`` (a committed document holds it, the basis names the JSON pointer),
``derivable`` (computed from committed values), ``convention`` (a stated convention), ``not-applicable`` or ``missing`` (a value of ``None`` and the reason).
An attribute without a source is missing or not-applicable with its reason, never invented. A32 and A33 are not-applicable because Contraste approves no
model (SDD non-goal 1). A22, A23, A24 and A35 summarise blocks the engine computed and A36 to A38 are counted from the documents; nothing here computes a
tier, a date or a deadline.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .readers import BakeError, resolve

SEVERITIES = ("S1", "S2", "S3", "S4")
OPEN_STATES = ("open", "action_plan_agreed", "in_progress", "submitted_for_closure", "overdue")
#: engines whose models are learned ones (ECB complexity driver, A D1 A20); a generalised linear model is not (06 l.289)
ML_ENGINES = ("lightgbm", "xgboost", "catboost", "interpretml", "tabpfn")


@dataclass
class Ctx:
    case_id: str
    fit_id: str
    key: str
    manifest: dict[str, Any]
    manifest_path: str
    models: dict[str, Any]
    models_path: str
    default: dict[str, Any]
    default_path: str
    variants: list[tuple[str, str, dict[str, Any]]]     # (variant id, path, document) assigned to the fit
    case_inputs: dict[str, Any]
    sources: dict[str, Any]                             # inputs.json attribute_sources
    tier_block: dict[str, Any]
    schedule: dict[str, Any]
    upstream: list[str]
    downstream: list[str]
    validator: str                                      # "riskvalidation 0.9.0"
    last_validation: str
    code_version: str


def attr(value: Any, status: str, basis: str) -> dict[str, Any]:
    return {"value": value, "status": status, "basis": basis}


def _fill(template: str, ctx: Ctx) -> str:
    return template.replace("{models}", ctx.models_path).replace("{manifest}", ctx.manifest_path).replace("{default}", ctx.default_path)


def _doc_for(pointer: str, ctx: Ctx) -> Any:
    path = pointer.partition("#")[0]
    if path == ctx.models_path:
        return ctx.models
    if path == ctx.default_path:
        return ctx.default
    raise BakeError(f"{ctx.key}: the pointer {pointer!r} names a document the attribute map does not read")


def _value_at(pointer: str, ctx: Ctx) -> Any:
    ptr = _fill(pointer, ctx)
    try:
        return resolve(_doc_for(ptr, ctx), ptr.partition("#")[2])
    except BakeError as exc:
        raise BakeError(f"{ctx.key}: {exc} in {ptr.partition('#')[0]}") from exc


def _small(value: Any) -> Any:
    """The value itself where it is short, else its size: the document points at the rest."""
    text = json.dumps(value, ensure_ascii=False)
    if len(text) <= 400:
        return value
    return {"items": len(value)} if isinstance(value, (list, dict)) else {"characters": len(text)}


def _from_sources(aid: str, ctx: Ctx) -> dict[str, Any] | None:
    spec = ctx.sources.get(aid, {}).get(ctx.case_id)
    if spec is None:
        return None
    ptrs = [_fill(p, ctx) for p in spec["pointers"]]
    vals = [_value_at(p, ctx) for p in spec["pointers"]]
    last = [p.rsplit("/", 1)[-1] for p in ptrs]
    mode = spec.get("mode", "values")
    if mode == "ids":
        value: Any = {"ids": [v["id"] for v in vals[0]], "source": last[0]}
    elif mode == "count":
        value = {last[0]: len(vals[0])}
    else:
        value = {k: _small(v) for k, v in zip(last, vals)}
    return attr(value, spec.get("status", "derivable"), f"{spec['note']}: read at " + " | ".join(ptrs))


def _lights(ctx: Ctx) -> dict[str, int]:
    out = {"green": 0, "amber": 0, "red": 0, "not_evaluated": 0, "error": 0}
    for _, _, doc in ctx.variants:
        for row in doc["tests"]:
            out[row["light"]] += 1
    return out


def open_by_severity(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {s: sum(1 for r in rows if r["severity"] == s and r["status"] in OPEN_STATES) for s in SEVERITIES}


def build(ctx: Ctx, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """A01 to A40 of the entry; ``rows`` are the register rows of the entry (A37, A38)."""
    m, man, d = ctx.models_path, ctx.manifest_path, ctx.default_path
    md = ctx.models
    n = len(md["model"])
    prov = md["provenance"]
    a: dict[str, dict[str, Any]] = {}
    a["A01"] = attr(ctx.key, "present", f"read at {m}#/case_id | {m}#/fit_id")
    a["A02"] = attr(ctx.manifest["title"], "present", f"read at {man}#/title")
    a["A03"] = attr(f"{ctx.fit_id}@{prov['code_version']}/riskvalidation-{prov['riskvalidation_version']}", "derivable",
                    f"no model version field: the fit id with the code and engine versions identify the build (A D1 A03): {m}#/fit_id | "
                    f"{m}#/provenance/code_version | {m}#/provenance/riskvalidation_version")
    a["A04"] = attr(ctx.manifest["question"], "present", f"case level only; read at {man}#/question")
    families = sorted({x["family"] for x in md["model"] if x.get("family")})
    a["A05"] = attr(families, "present", f"free text, no controlled vocabulary; read at {m}#/model/0/family and the other model records")
    engines = sorted({x["engine"] for x in md["model"] if x.get("engine")})
    a["A06"] = attr(engines, "derivable", "no origin field: derived from the engine of each model record (own riskvalidation or a third-party library): "
                    f"{m}#/model/0/engine and the other model records")
    a["A07"] = attr("in_validation", "derivable", "built from the committed manifest; the B.4 vocabulary does not exist in the documents (A D1 A07); "
                    "no approval is recorded")
    a["A08"] = attr(ctx.manifest["question"], "present", f"read at {man}#/question")
    a["A09"] = _from_sources("A09", ctx) or (
        attr(None, "not-applicable", "C22 is the validator case: it holds no products or portfolios (A D1 A09)") if ctx.case_id == "C22" else
        attr(None, "missing", f"structured field lacking in {ctx.case_id} (A D1 A09); the prose Source line of the case page is not data"))
    a["A10"] = attr(None, "missing", "no field: a benchmark case has no actual use (A D1 A10)")
    a["A11"] = attr(None, "missing", "no field in any committed document (A D1 A11)")
    a["A12"] = attr(None, "missing", "prose only: the case-page Limits sections and the SDD non-goals are not structured data (A D1 A12)")
    a["A13"] = _from_sources("A13", ctx) or attr(None, "missing", f"no training span or split field in the {ctx.case_id} documents (A D1 A13)")
    a["A14"] = attr({"sources": ctx.manifest["sources"], "generators": prov["generators"]}, "present", f"read at {man}#/sources | {m}#/provenance/generators")
    a["A15"] = attr(None, "missing", "no field: no document says whether alternative or unstructured data is used (A D1 A15)")
    link = {"upstream": ctx.upstream, "downstream": ctx.downstream}
    spec = ctx.sources.get("A16", {}).get(ctx.case_id)
    if spec:
        ptrs = [_fill(p, ctx) for p in spec["pointers"]]
        for p in spec["pointers"]:
            _value_at(p, ctx)
        a["A16"] = attr(link, "present", f"{spec['note']}, read at " + " | ".join(ptrs))
    else:
        a["A16"] = attr(link, "derivable", "derived from the edge table of the inventory, each edge with its stated source (W15-8); the case documents hold no "
                        "dependency field")
    a["A17"] = attr({"impact_items": list(ctx.default["impact"])}, "present", f"outputs and impact items of the default variant: {d}#/outputs | {d}#/impact")
    a["A18"] = attr([x["rung"] for x in md["model"]], "present", f"read at {m}#/model/0/rung and the other model records")
    a["A19"] = _from_sources("A19", ctx) or attr(None, "missing", "limits are in prose only; no structured form in this case (A D1 A19)")
    learned = [x["id"] for x in md["model"] if any(e in str(x.get("engine", "")).lower() for e in ML_ENGINES)]
    a["A20"] = attr(bool(learned), "derivable", "derived from the engine of the model records: " + (
        f"machine-learning engines in {', '.join(learned[:6])}{' and others' if len(learned) > 6 else ''}" if learned else
        "no machine-learning engine is present") + f" ({m}#/model/0/engine and the other model records)")
    a["A21"] = attr(None, "missing", "no field; the fits are static per fit_id (A D1 A21)")
    tb = ctx.tier_block
    a["A22"] = attr(tb["materiality"]["m"]["graded"], "convention", "M of the adopted reading B; tier_block.materiality (tiering.materiality)")
    a["A23"] = attr(tb["complexity"]["c"]["mean"], "convention", "C of the adopted reading B; tier_block.complexity (tiering.complexity)")
    a["A24"] = attr(tb["tier"], "convention", "the matrix of M and C (06 B.3) under the adopted reading B; tier_block (tiering.matrix_tier)")
    a["A25"] = attr(None, "missing", "no rating; the explainability evidence by rung is not a rating (A D1 A25)")
    pma = ctx.sources["A26"].get(ctx.case_id)
    if pma and "not_applicable" in pma:
        a["A26"] = attr(None, "not-applicable", pma["not_applicable"])
    elif pma:
        ptr = {k: _fill(v, ctx) for k, v in pma.items()}
        a["A26"] = attr({"overlays_total": _value_at(pma["overlays_total"], ctx), "currency": _value_at(pma["currency"], ctx),
                         "model_output": _value_at(pma["model_output"], ctx), "model_output_pointer": ptr["model_output"]}, "present",
                        f"read at {ptr['overlays_total']}")
    else:
        a["A26"] = attr(None, "not-applicable", "no PMA or overlay exists in this case: A D1 A26 finds PMAs in C06 and C07 only")
    a["A27"] = attr(None, "missing", "no concept of an exception to policy; an accepted finding is a stated limit, not an exception (A D1 A27)")
    a["A28"] = attr(ctx.case_inputs["owner_role"], "convention", "W15-4: a named role of the synthetic bank per risk area, labelled synthetic; the role names are "
                    "set in inputs.json")
    a["A29"] = attr(ctx.case_inputs["developer"], "derivable", "the producing pipeline module, the owner column of docs/contracts/catalog.md (A D1 A29)")
    a["A30"] = attr(None, "missing", "no field: a synthetic bank has no users (A D1 A30)")
    independence = ("independence is not established because the pipeline and the engine are built in the same programme (W15-4, the governance finding "
                    "GOV-INDEPENDENCE-NOT-ESTABLISHED)")
    if ctx.case_id == "C22":
        basis = (f"riskvalidation at the pinned version validates the entry; {independence.split(' (')[0]}; C22 itself is validated by its exact rejection "
                 "probabilities and by the engine's own tests (A D1)")
    else:
        basis = f"riskvalidation at the pinned version; {independence}"
    a["A31"] = attr(ctx.validator, "derivable", basis)
    a["A32"] = attr(None, "not-applicable", "Contraste approves no model (SDD non-goal 1): no approver exists")
    a["A33"] = attr(None, "not-applicable", "Contraste approves no model (SDD non-goal 1): no approval date or authority exists")
    a["A34"] = attr({"date": ctx.last_validation, "type": "full battery"}, "derivable",
                    f"the release date of code version {ctx.code_version} in CHANGELOG.md; the type is one full battery: {m}#/provenance/code_version")
    a["A35"] = attr(ctx.schedule["next_review"], "convention", "schedule.next_dates over the frequency table (a convention, 06 B.8 l.636-640)")
    a["A36"] = attr(_lights(ctx), "derivable", "the lights of every test row of the entry's variants: " + f"{ctx.variants[0][1]}#/tests and the other variants")
    a["A37"] = attr(open_by_severity(rows), "present", "open findings by severity, counted over the findings of the variants (per variant, not per model): "
                    f"{ctx.variants[0][1]}#/findings and the other variants")
    due = sorted(r["due"] for r in rows if r["status"] in OPEN_STATES)
    a["A38"] = attr({"earliest_due": due[0] if due else None}, "convention",
                    "the earliest due date of the entry's open findings in the register (the deadline table is a convention, W15-5)")
    a["A39"] = attr(None, "missing", "no field: no document states how long the model is expected to stay valid (A D1 A39)")
    a["A40"] = attr(None, "missing", "no field: no model is retired (A D1 A40)")
    return a
