"""Builds the U15-S fixtures (docs/contracts/fixtures/governance): the inventory, the findings register, the appetite and two reports.

Run: ``python tests/contracts_u15/build_fixtures.py``. Deterministic, standard library only; the facts come from
``snapshots/source-extract.json`` (written by ``extract_sources.py`` from the committed case documents) and from the values of the U15
research addendum typed here (D2: the tiering inputs and the four readings' tiers; D3: the findings; D4: the edges; D5: the report). The
fixtures hold four entries: C01/german, C07/banco-andino, C18/banco-andino and C22/generators (the fit ids are the committed models documents'),
two reports (C07 and C18) and the appetite. They are labelled as fixtures (``fixture:u15-s-contracts``) and never published as results.

This builder does not import ``semantics.py``: it writes the rules again in the small functions below, so that the checker verifies the
fixtures against an independent implementation.

Values that are conventions and not read from a document: the as-of date (the quarter end 2026-12-31, so that the fixture shows overdue rows),
the deadline table (days by severity and tier), the frequency table (06 l.636-640), the appetite thresholds, the synthetic owner roles, the
component roles and the lifecycle state. Each is labelled ``convention`` with its basis in the document. UNVERIFIED: that U15-P's inputs.json
adopts the same deadline days, thresholds and role names (the contract fixes the shape and the rules, the values are the bake's named parameters).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from attribute_table import pointers  # noqa: E402  (this folder is not a package)

ROOT = Path(__file__).resolve().parents[2]
EXTRACT = ROOT / "tests" / "contracts_u15" / "snapshots" / "source-extract.json"
OUT = ROOT / "docs" / "contracts" / "fixtures" / "governance"

AS_OF = "2026-12-31"
AS_OF_BASIS = {"label": "convention", "basis": {
    "en": "a fixture date chosen after the due dates to exercise the overdue rule; not the date of publication",
    "es": "una fecha de fixture elegida después de los vencimientos para ejercer la regla de vencimiento; no es la fecha de publicación"}}
CODE_VERSION = "%d.%02d.%03d" % (0, 15, 0)  # the Contraste release that carries governance (the one before it carries the notebooks)
RV_VERSION = "0.9.0"                  # R1: the engine tag after v0.08.000; UNVERIFIED until the integrator cuts it
GENERATORS = ["fixture:u15-s-contracts"]
# CHANGELOG.md release dates (A D1 A34), read from its headings "## [X.XX.XXX], YYYY-MM-DD"
RELEASE = dict(re.findall(r"(?m)^## \[(\d\.\d\d\.\d\d\d)\], (\d{4}-\d\d-\d\d)$", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")))
ENTRIES = [("C01", "german"), ("C07", "banco-andino"), ("C18", "banco-andino"), ("C22", "generators")]
SEVERITIES = ["S1", "S2", "S3", "S4"]
ECB_F = {"S1": "F4", "S2": "F3", "S3": "F2", "S4": "F1"}
STATUS_MAP = {"open": "open", "accepted": "risk_accepted", "closed": "validated_closed"}
STATES_B7 = ["open", "action_plan_agreed", "in_progress", "submitted_for_closure", "validated_closed", "overdue", "risk_accepted"]
OPEN_STATES = ("open", "action_plan_agreed", "in_progress", "submitted_for_closure", "overdue")
DEADLINES = [[30, 45, 60, 90], [60, 90, 120, 180], [90, 120, 180, 270], [180, 270, 365, 365]]   # severity S1..S4 x tier 1..4
FREQUENCY = [(1, "review", 12, 36, 3), (2, "review", 12, 36, 6), (3, "review", 24, None, 12), (4, "attestation", 36, None, None)]
LABEL_EN = "the rule's output on the evidence; Contraste approves no model"
LABEL_ES = "resultado de la regla sobre la evidencia; Contraste no aprueba ningun modelo"
READINGS = [("A", "literal", "mean"), ("B", "graded", "mean"), ("C", "literal", "maximum"), ("D", "graded", "maximum")]
OWNER = {"C01": "Head of PD models (synthetic role)", "C07": "Head of provisioning models (synthetic role)",
         "C18": "Head of capital planning (synthetic role)", "C22": "Head of validation tooling (synthetic role)"}
DEVELOPER = {"C01": "data-pipeline/pipeline/cases/c01_retail_pd.py", "C07": "data-pipeline/pipeline/cases/c07/",
             "C18": "data-pipeline/pipeline/cases/c18/", "C22": "data-pipeline/pipeline/cases/c22_validator.py"}
# A D2 3.2 and 3.3: share of the stated balance, regulatory use (literal, graded) with its tag, decision criticality, the six factor scores
D2 = {
    "C01": dict(share=0.0531, exposure="consumer-cards segment of the C07 book (a mapping convention)", lit=4, grd=3, reg_tag="doc",
                reg="impact.capital_champion and capital_challenger (IRB capital) in C01/holdout.json; the approval rate on card applicants",
                dec=3, dec_tag="doc", dec_basis="automated credit decision on natural persons (06 B.3): impact.approval_rate, swap_in, swap_out",
                scores=[4, 2, 3, 1, 1, 1],
                f=["P5-tabpfn (a foundation model) in models-german.json", "external sources: uci-taiwan, uci-german",
                   "post hoc explanation for P4 and P5; P3-ebm is glass-box", "static fit per fit_id",
                   "no feeding case (A D4: feeder count 0)", "seed, versions and file hashes in every document"]),
    "C07": dict(share=1.0, exposure="whole C07 loan book (6,000,000 CLP million, IFRS 9 scope)", lit=4, grd=4, reg_tag="doc",
                reg="impact.provision_cmf_b1, provision_ifrs9, provision_bde (the provisions are the reported figures)",
                dec=1, dec_tag="convention", dec_basis="no rubric rule names an automated decision on natural persons in this case",
                scores=[2, 1, 1, 1, 1, 1],
                f=["IFRS9-ecl is a fitted hazard model (B1-standard is 1)", "no outside file: sources is empty, the book is generated",
                   "intrinsically interpretable", "static fit per fit_id", "no feeding case (A D4: feeder count 0)",
                   "seed, versions and file hashes in every document"]),
    "C18": dict(share=1.0, exposure="whole capital of Banco Andino (RWA 7,492,853 CLP million at 2026-08-31)", lit=4, grd=4, reg_tag="doc",
                reg="impact.capital_simple_sum, cet1_ratio_end_stress, p2g_proxy (the capital plan)",
                dec=1, dec_tag="convention", dec_basis="no rubric rule names an automated decision on natural persons in this case",
                scores=[2, 2, 1, 1, 4, 1],
                f=["c18-satellites-us-calibrated and c18-aggregation-ladder are fitted parametric models", "five external sources",
                   "intrinsically interpretable", "static fit per fit_id", "reads C07, C11, C15 and C17 (four feeding cases, D4)",
                   "seed, versions and file hashes in every document"]),
    "C22": dict(share=None, exposure="not a bank balance: C22 tests the tests of the other cases", lit=1, grd=1, reg_tag="doc",
                reg="no regulatory number: it tests the tests of the other cases", dec=1, dec_tag="convention",
                dec_basis="no rubric rule names an automated decision on natural persons in this case", scores=[2, 1, 1, 1, 1, 1],
                f=["the G1 to G7 generators and the X1-exact harness", "generated data", "intrinsically interpretable", "static fit per fit_id",
                   "no feeding case (A D4: feeder count 0)", "seed, versions and file hashes in every document"]),
}
FACTOR_NAMES = ["methodology", "data", "explainability", "dynamic updating", "dependency depth", "reproducibility", "history against horizon"]
FACTOR_TAGS = ["convention", "doc", "doc", "doc", "convention", "convention"]
ROLES = {   # component roles (W15-1): a convention by rung, except where a committed page states the champion (model.ts:8, C03.md:32)
    "C01": {"P0-constant": "benchmark", "P0-single": "benchmark", "P1-scorecard": "champion"},
    "C07": {"G0-banco-andino": "reference", "B1-standard": "benchmark", "IFRS9-ecl": "champion", "BDE-annex9": "benchmark"},
    "C18": {"c18-satellites-us-calibrated": "champion", "c18-aggregation-ladder": "challenger", "c18-capital-engine": "champion"},
    "C22": {"X1-exact": "benchmark"},
}


def T(en: str, es: str) -> dict:
    return {"en": en, "es": es}


# ------------------------------------------------------------------------------------------------------------------ small rules


def band(share: float | None) -> int:
    if share is None:
        return 1
    return 4 if share >= 0.25 else 3 if share >= 0.10 else 2 if share >= 0.02 else 1


def matrix(m: int, c: int) -> int:
    if m == 4 or (m == 3 and c >= 3):
        return 1
    if m == 3 or (m == 2 and c >= 3):
        return 2
    if m == 2 or (m == 1 and c >= 3):
        return 3
    return 4


def months(d: date, n: int) -> date:
    y, mo = divmod(d.year * 12 + d.month - 1 + n, 12)
    mo += 1
    last = [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
    return date(y, mo, min(d.day, last))


def write(name: str, doc: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# ------------------------------------------------------------------------------------------------------------------ the inventory


def provenance(ex: dict) -> dict:
    docs = []
    for case, _ in ENTRIES:
        c = ex["cases"][case]
        ref = None                                                                  # every case is read from the branch (0.13.000)
        docs.append({"path": c["manifest"]["path"], "sha256": c["manifest"]["sha256"], "ref": ref})
        docs.append({"path": c["models_document"]["path"], "sha256": c["models_document"]["sha256"], "ref": ref})
        docs += [{"path": v["path"], "sha256": v["sha256"], "ref": ref} for v in c["variants"]]
    return {"code_version": CODE_VERSION, "riskvalidation_version": RV_VERSION, "generators": GENERATORS, "documents_read": docs}


def attr(value, status: str, basis: str) -> dict:
    return {"value": value, "status": status, "basis": basis}


def light_counts(c: dict) -> dict:
    out = {"green": 0, "amber": 0, "red": 0, "not_evaluated": 0, "error": 0}
    for v in c["variants"]:
        for r in v["tests"]:
            out[r["light"]] += 1
    return out


def tier_block(case: str) -> dict:
    d = D2[case]
    b = band(d["share"])
    scores = d["scores"]
    c_mean = (2 * sum(scores) + len(scores)) // (2 * len(scores))
    c_max = max(scores)
    m = {"literal": max(b, d["lit"], d["dec"]), "graded": max(b, d["grd"], d["dec"])}
    factors = []
    for i, (name, tag, basis) in enumerate(zip(FACTOR_NAMES, FACTOR_TAGS, d["f"]), 1):
        factors.append({"id": f"F{i}", "name": name, "score": scores[i - 1], "tag": tag, "basis": basis})
    factors.append({"id": "F7", "name": FACTOR_NAMES[6], "score": None, "tag": "convention",
                    "basis": "not scored: history against the forecast horizon is not a field in any committed document (A D2 3.3)"})
    sens = []
    for name, reg, agg in READINGS:
        mm, cc = m[reg], c_mean if agg == "mean" else c_max
        sens.append({"reading": name, "regulatory_use": reg, "complexity": agg, "m": mm, "c": cc, "tier": matrix(mm, cc)})
    computed = sens[1]["tier"]
    return {
        "materiality": {
            "exposure": {"share": d["share"], "band": b, "tag": "convention",
                         "basis": f"{d['exposure']}; band cut points 25, 10 and 2 percent (a convention, A D2 3.2)"},
            "regulatory_use": {"literal": d["lit"], "graded": d["grd"], "tag": d["reg_tag"], "basis": d["reg"]},
            "decision_criticality": {"score": d["dec"], "tag": d["dec_tag"], "basis": d["dec_basis"]},
            "m": m,
        },
        "complexity": {"factors": factors, "scored": 6, "sum": sum(scores), "mean": round(sum(scores) / 6, 2),
                       "c": {"mean": c_mean, "maximum": c_max}},
        "adopted_reading": "B", "computed_tier": computed, "override": None, "tier": computed, "tier_sensitivity": sens,
    }


def build_inventory(ex: dict) -> dict:
    entries = []
    edges = [
        {"upstream": "C07/banco-andino", "downstream": "C18/banco-andino", "kind": "document",
         "stated_source": "data-pipeline/pipeline/cases/c18/anchors.py:102-103 loads C07/base.json and C07/models-banco-andino.json; "
                          "the C18 models document $.fit.marginal_sources[0].documents is [\"c07-outputs\"] (the batch 3 release)"},
        {"upstream": "C01/german", "downstream": "C22/generators", "kind": "code",
         "stated_source": "data-pipeline/pipeline/cases/c22_validator.py:68 imports the helpers _t and _v of c01_ladder (A D4 5.1)"},
    ]
    keys = [f"{c}/{f}" for c, f in ENTRIES]
    pairs = [(e["upstream"], e["downstream"]) for e in edges]
    depth = {k: 0 for k in keys}
    for _ in keys:                       # longest path from a source (the graph is acyclic, so len(keys) passes settle it)
        for u, d in pairs:
            depth[d] = max(depth[d], depth[u] + 1)
    rank: dict[int, int] = {}
    for case, fit in ENTRIES:
        c = ex["cases"][case]
        key = f"{case}/{fit}"
        md = c["models_document"]
        man = c["manifest"]
        m_path, man_path = md["path"], man["path"]
        tb = tier_block(case)
        tier = tb["tier"]
        code_version = md["code_version"]
        last = RELEASE[code_version]
        freq = next(f for f in FREQUENCY if f[0] == tier)
        nxt_review = months(date.fromisoformat(last), freq[2]).isoformat()
        nxt_full = months(date.fromisoformat(last), freq[3]).isoformat() if freq[3] else None
        nxt_mon = months(date.fromisoformat(last), freq[4]).isoformat() if freq[4] else None
        pv = c["pointer_values"]
        fams = sorted({m["family"] for m in md["models"] if m["family"]})
        engines = sorted({m["engine"] for m in md["models"] if m["engine"]})
        rungs = [m["rung"] for m in md["models"]]
        up = sorted(u for u, d in pairs if d == key)
        dn = sorted(d for u, d in pairs if u == key)
        findings_open = {s: 0 for s in SEVERITIES}
        a = {}
        rows_of_entry = findings_rows_of(ex, case, fit)
        for r in rows_of_entry:
            if r["status"] in OPEN_STATES:
                findings_open[r["severity"]] += 1
        due_open = sorted(r["due"] for r in rows_of_entry if r["status"] in OPEN_STATES)
        pts = pointers(case, c)
        ptr = lambda aid: " | ".join(pts[aid])   # noqa: E731
        a["A01"] = attr(key, "present", f"read at {ptr('A01')}")
        a["A02"] = attr(man["title"], "present", f"read at {ptr('A02')}")
        a["A03"] = attr(f"{fit}@{code_version}/riskvalidation-{md['riskvalidation_version']}", "derivable",
                        "no model version field: the fit id with the code and engine versions identify the build (A D1 A03): "
                        + ptr("A03"))
        a["A04"] = attr(man["question"], "present", f"case level only; read at {ptr('A04')}")
        a["A05"] = attr(fams, "present", f"free text, no controlled vocabulary; read at {ptr('A05').split(' | ')[0]} and the other model records")
        a["A06"] = attr(engines, "derivable", "no origin field: derived from the engine of each model record (own riskvalidation or a third-party library)")
        a["A07"] = attr("in_validation", "derivable",
                        "built from the committed manifest; the B.4 vocabulary does not exist in the documents (A D1 A07); no approval is recorded")
        a["A08"] = attr(man["question"], "present", f"read at {ptr('A08')}")
        if case == "C07":
            a["A09"] = attr({"classes": ["mortgage", "consumer", "commercial"], "source": "fit.segments"}, "derivable",
                            f"the book segments of the C07 fit: {ptr('A09')}")
        elif case == "C18":
            a["A09"] = attr({"classes": ["commercial", "consumer", "mortgage"], "source": "fit.class_mapping"}, "derivable",
                            f"the class mapping of the C18 fit: {ptr('A09')}")
        elif case == "C22":
            a["A09"] = attr(None, "not-applicable", "C22 is the validator case: it holds no products or portfolios (A D1 A09)")
        else:
            a["A09"] = attr(None, "missing", "structured field lacking in C01 (A D1 A09); the prose Source line of the case page is not data")
        a["A10"] = attr(None, "missing", "no field: a benchmark case has no actual use (A D1 A10)")
        a["A11"] = attr(None, "missing", "no field in any committed document (A D1 A11)")
        a["A12"] = attr(None, "missing", "prose only: the case-page Limits sections and the SDD non-goals are not structured data (A D1 A12)")
        if case == "C01":
            a["A13"] = attr({"split": pv[f"{m_path}#/fit/split"], "train_rows": pv[f"{m_path}#/fit/train_rows"]}, "derivable",
                            f"the training span is the split of the fit; no sample range per risk driver: {ptr('A13')}")
        elif case == "C18":
            a["A13"] = attr({"fit_end_year": pv[f"{m_path}#/model/0/parameters/fit_end_year"]["value"]}, "derivable",
                            f"the satellite fit window ends in 2019: {ptr('A13')}")
        else:
            a["A13"] = attr(None, "missing", f"no training span or split field in the {case} documents (A D1 A13)")
        a["A14"] = attr({"sources": pv[f"{man_path}#/sources"], "generators": pv[f"{m_path}#/provenance/generators"]}, "present",
                        f"read at {ptr('A14')}")
        a["A15"] = attr(None, "missing", "no field: no document says whether alternative or unstructured data is used (A D1 A15)")
        if case == "C18":
            a["A16"] = attr({"upstream": up, "downstream": dn}, "present",
                            f"the edge table agrees with the feeders the models document holds as data, read at {ptr('A16')}")
        else:
            a["A16"] = attr({"upstream": up, "downstream": dn}, "derivable",
                            "derived from the edge table of the inventory, each edge with its stated source (W15-8); the case documents hold no dependency field")
        a["A17"] = attr({"impact_items": c["impact_keys"]}, "present", f"outputs and impact items of the default variant: {ptr('A17')}")
        a["A18"] = attr(rungs, "present", f"read at {ptr('A18').split(' | ')[0]} and the other model records")
        if case == "C18":
            a["A19"] = attr({"named_parameters": c["named_parameters_count"]}, "present", f"labelled parameters: {ptr('A19')}")
        else:
            a["A19"] = attr(None, "missing", "limits are in prose only; no structured form in this case (A D1 A19)")
        ml = case == "C01"
        a["A20"] = attr(ml, "derivable", "derived from the rung and the engine of the model records: "
                        + ("P3-ebm, P4-lightgbm and P5-tabpfn are machine-learning rungs" if ml else "no machine-learning rung or engine is present"))
        a["A21"] = attr(None, "missing", "no field; the fits are static per fit_id (A D1 A21)")
        a["A22"] = attr(tb["materiality"]["m"]["graded"], "convention", "M of the adopted reading B; tier_block.materiality (tiering.materiality)")
        a["A23"] = attr(tb["complexity"]["c"]["mean"], "convention", "C of the adopted reading B; tier_block.complexity (tiering.complexity)")
        a["A24"] = attr(tier, "convention", "the matrix of M and C (06 B.3) under the adopted reading B; tier_block (tiering.matrix_tier)")
        a["A25"] = attr(None, "missing", "no rating; the explainability evidence by rung is not a rating (A D1 A25)")
        if case == "C07":
            p = ex["cases"]["C07"]["pma"]
            a["A26"] = attr({"overlays_total": p["overlays_total"], "currency": p["currency"], "model_output": p["model_output"],
                             "model_output_pointer": p["model_output_pointer"]}, "present", f"read at {p['pointer']}")
        else:
            a["A26"] = attr(None, "not-applicable", "no PMA or overlay exists in this case: A D1 A26 finds PMAs in C06 and C07 only")
        a["A27"] = attr(None, "missing", "no concept of an exception to policy; an accepted finding is a stated limit, not an exception (A D1 A27)")
        a["A28"] = attr(OWNER[case], "convention", "W15-4: a named role of the synthetic bank per risk area, labelled synthetic; the role names are set in inputs.json")
        a["A29"] = attr(DEVELOPER[case], "derivable", "the producing pipeline module, the owner column of docs/contracts/catalog.md (A D1 A29)")
        a["A30"] = attr(None, "missing", "no field: a synthetic bank has no users (A D1 A30)")
        if case == "C22":
            basis = ("riskvalidation at the pinned version validates the entry; independence is not established because the pipeline and the engine are "
                     "built in the same programme (W15-4); C22 itself is validated by its exact rejection probabilities and by the engine's own tests (A D1)")
        else:
            basis = ("riskvalidation at the pinned version; independence is not established because the pipeline and the engine are built in the "
                     "same programme (W15-4, the governance finding GOV-INDEPENDENCE-NOT-ESTABLISHED)")
        a["A31"] = attr(f"riskvalidation {md['riskvalidation_version']}", "derivable", basis)
        a["A32"] = attr(None, "not-applicable", "Contraste approves no model (SDD non-goal 1): no approver exists")
        a["A33"] = attr(None, "not-applicable", "Contraste approves no model (SDD non-goal 1): no approval date or authority exists")
        a["A34"] = attr({"date": last, "type": "full battery"}, "derivable",
                        f"the release date of code version {code_version} in CHANGELOG.md; the type is one full battery: {ptr('A34')}")
        a["A35"] = attr(nxt_review, "convention", "schedule.next_dates over the frequency table (a convention, 06 B.8 l.636-640)")
        a["A36"] = attr(light_counts(c), "derivable", "the lights of every test row of the entry's variants: " + ptr("A36").split(" | ")[0] + " and the other variants")
        a["A37"] = attr(findings_open, "present", "open findings by severity, counted over the findings of the variants (per variant, not per model): "
                        + ptr("A37").split(" | ")[0] + " and the other variants")
        a["A38"] = attr({"earliest_due": due_open[0] if due_open else None}, "convention",
                        "the earliest due date of the entry's open findings in the register (the deadline table is a convention, W15-5)")
        a["A39"] = attr(None, "missing", "no field: no document states how long the model is expected to stay valid (A D1 A39)")
        a["A40"] = attr(None, "missing", "no field: no model is retired (A D1 A40)")
        comps = []
        for m in md["models"]:
            role = ROLES[case].get(m["id"]) or ("challenger" if case == "C01" else "reference")
            tag = "doc" if (case == "C01" and m["id"] == "P1-scorecard") else "convention"
            basis = ("the champion P1-scorecard (frontend/src/workbench/model.ts:8)" if tag == "doc"
                     else f"convention by rung ({m['rung']}): the model records carry no role")
            comps.append({"key": f"{key}/{m['id']}", "model_id": m["id"], "role": role, "role_tag": tag, "role_basis": basis,
                          "family": m["family"], "rung": m["rung"], "title": m["title"]})
        profiles = [
            {"profile": "us-2026", "in_scope": True, "rationale": T(
                "In scope: it applies statistical or economic theory, its output is an estimate and it is not generative or agentic (SR 26-2).",
                "En alcance: aplica teoria estadistica o economica, su resultado es una estimacion y no es generativo ni agentico (SR 26-2).")},
            {"profile": "pra", "in_scope": True, "rationale": T("In scope: it applies a quantitative method (SS1/23 Principle 1.1).",
                                                                 "En alcance: aplica un método cuantitativo (SS1/23 Principio 1.1).")},
            {"profile": "osfi-2027", "in_scope": True, "rationale": T("In scope: it applies theory and its output is an estimate (OSFI E-23).",
                                                                      "En alcance: aplica teoría y su resultado es una estimación (OSFI E-23).")},
            {"profile": "ecb", "in_scope": True, "rationale": T("In scope: it applies theory and its output is an estimate (ECB).",
                                                                "En alcance: aplica teoría y su resultado es una estimación (BCE).")},
        ]
        scope_basis = ("B.1 (06 l.523-537); the four answers are read from the models document; the profile rules are a reading of the B.1 table "
                       "(UNVERIFIED beyond it)" + ("; the components B1-standard and BDE-annex9 are deterministic rule sets, the entry as a whole is not"
                                                   if case == "C07" else ""))
        gen = depth[key]
        rank[gen] = rank.get(gen, -1) + 1
        entries.append({
            "key": key, "case_id": case, "fit_id": fit, "title": man["title"], "attributes": a,
            "variants": [{"variant_id": v["variant_id"],
                          "basis": (f"the variant's provenance reads {', '.join(v['sources'])}, the sources of the fit {fit}" if case == "C01"
                                    else "the single models document of the case (W15-15)")} for v in c["variants"]],
            "components": comps,
            "scope": {"answers": {"applies_theory": True, "output_is_estimate": True, "deterministic": False, "generative_or_agentic": False},
                      "profiles": profiles, "basis": scope_basis},
            "tier_block": tb,
            "lifecycle": {"state": "in_validation", "basis": "the full battery has run and no approval exists (SDD non-goal 1); transitions are not "
                                                             "recorded in the committed documents", "transitions": [], "exception": None},
            "schedule": {"profile": "default", "review_kind": freq[1], "last_validation": {"date": last, "type": "full battery",
                                                                                           "basis": "A34: the release date of the code version"},
                         "next_review": nxt_review, "next_full_revalidation": nxt_full, "next_monitoring": nxt_mon,
                         "null_reason": None if freq[3] and freq[4] else T(
                             "the frequency table of this tier states no full revalidation or no monitoring interval (06 l.636-640)",
                             "la tabla de frecuencias de este nivel no fija revalidacion completa o monitoreo (06 l.636-640)")},
            "graph": {"depth": gen, "fan_in": len(up), "fan_out": len(dn)},
            "map": {"generation": gen, "x": float(gen), "y": float(rank[gen])},
        })
    # completeness and tier counts, over the entries
    comp = {aid: {"present": 0, "derivable": 0, "convention": 0, "not_applicable": 0, "missing": 0} for aid in entries[0]["attributes"]}
    for e in entries:
        for aid, at in e["attributes"].items():
            comp[aid][at["status"].replace("-", "_")] += 1
    counts = [{"reading": r[0], "counts": [sum(1 for e in entries if e["tier_block"]["tier_sensitivity"][i]["tier"] == t) for t in (1, 2, 3, 4)]}
              for i, r in enumerate(READINGS)]
    conv = lambda basis, **kw: {"label": "convention", "basis": basis, **kw}   # noqa: E731
    return {
        "schema": "contraste.governance.inventory/v1", "case_id": "GOVERNANCE", "governance_id": "inventory", "schema_version": "1.0.0",
        "as_of": AS_OF, "as_of_basis": AS_OF_BASIS, "provenance": provenance(ex),
        "conventions": {
            "exposure_band_cuts": conv("A D2 3.2 and W15-3: share of the stated balance at least 25 percent is 4, 10 percent 3, 2 percent 2, below 1; "
                                       "06 B.3 fixes no cut-offs (item 30 of the dossier UNVERIFIED list)", cuts=[0.25, 0.1, 0.02]),
            "regulatory_use_grades": conv("W15-3: 4 where the output is itself the reported or binding figure, 3 where it is a parameter or a back-test "
                                          "that feeds one, 2 for compliance monitoring, 1 for none; the literal reading gives 4 whenever the output "
                                          "feeds capital, provisioning or reporting (A D2 3.2)",
                                          graded={"reported_figure": 4, "feeding_parameter": 3, "compliance_monitoring": 2, "none": 1},
                                          literal={"feeds_capital_provisioning_or_reporting": 4, "compliance_monitoring": 2, "none": 1}),
            "complexity_rounding": conv("06 l.567: C is the mean of the factor scores; the rounding is not in the text, half up is used (A D2 3.3)",
                                        rule="mean-rounded-half-up"),
            "frequency": conv("06 B.8 l.636-640: Tier 1 annual review, full revalidation every 3 years, quarterly monitoring; Tier 2 annual, 3 years, "
                              "semi-annual; Tier 3 every 2 years, annual monitoring; Tier 4 attestation every 3 years. A convention, configurable; "
                              "the ECB minimums override it for IRB profiles (item 30)",
                              tiers=[{"tier": t, "review_kind": k, "review_months": r, "revalidation_months": f, "monitoring_months": mo,
                                      "null_reason": None if (f and mo) else T("the table states none for this tier (06 l.636-640)",
                                                                              "la tabla no fija ninguno para este nivel (06 l.636-640)")}
                                     for t, k, r, f, mo in FREQUENCY]),
            "adopted_reading": conv("W15-3: regulatory use graded, complexity the mean rounded half up; the other three readings are shown beside it "
                                    "(tier_sensitivity)", reading="B"),
        },
        "engine_node": {"key": "riskvalidation", "version": RV_VERSION,
                        "basis": "every entry depends on the engine: it computes every value and runs every test (W15-8)"},
        "entries": entries,
        "edges": edges,
        "related": [{"a": "C22/generators", "b": "C01/german", "kind": "measures",
                     "source": "docs/cases/C22.md:70, 157-158, 180, 182 (C22 measures the size of C01's tests); docs/cases/C01.md:69"}],
        "excluded": [{"case_id": c, "variant_id": None, "reason": T("planned: no committed document or models record exists (A D1)",
                                                 "planificado: no existe documento ni registro de modelos confirmado (A D1)")}
                     for c in ("C02", "C19", "C20")],
        "completeness": {"entries": len(entries), "attributes": comp},
        "tier_counts": counts,
        "governance_findings": [
            {"id": "GOV-RUBRIC-BLIND-SPOT", "severity": "S3", "ecb_f": "F2", "status": "open",
             "title": T("The tier rubric has no materiality term for fan-out", "La rubrica de niveles no tiene termino de materialidad por dependencia"),
             "description": T("The engine and C22's test sizing reach every case, yet C22 keeps the tier its inputs give (Tier 4): the rubric counts "
                              "feeders in complexity and has no term for fan-out in materiality (A D2 3.5 item 3).",
                              "El motor y el dimensionamiento de pruebas de C22 alcanzan a todos los casos, pero C22 conserva el nivel que dan sus insumos "
                              "(Nivel 4): la rubrica cuenta alimentadores en la complejidad y no tiene termino de dependencia en la materialidad (A D2 3.5 punto 3)."),
             "basis": "W15-3; A D2 3.5 item 3"},
            {"id": "GOV-INDEPENDENCE-NOT-ESTABLISHED", "severity": "S2", "ecb_f": "F3", "status": "open",
             "title": T("Independence of the validator is not established", "La independencia del validador no esta establecida"),
             "description": T("The pipeline (developer) and the engine (validator) are built in the same programme, so the separation of the first and "
                              "second line is a convention, not a fact (A D1 A31).",
                              "El pipeline (desarrollador) y el motor (validador) se construyen en el mismo programa, por lo que la separacion de primera "
                              "y segunda linea es una convencion y no un hecho (A D1 A31)."),
             "basis": "W15-4; A D1 A31"},
        ],
    }


# ------------------------------------------------------------------------------------------------------------------ the findings

CITED = re.compile(r"[a-z0-9_.]+@[^@]+(@.+)?")


def anchor_of(finding: dict, variant: dict) -> tuple[dict | None, dict | None]:
    cited = [e for e in finding["evidence"] if CITED.fullmatch(e)]
    if not cited:
        return None, T("the evidence is not a test_id@model row (it is a design:, contract:, rate: or bare test id), so no statistic is read",
                       "la evidencia no es una fila test_id@modelo (es design:, contract:, rate: o un id de prueba sin modelo), por lo que no se lee estadistico")
    parts = cited[0].split("@")
    test_id, model_id = parts[0], parts[1]
    segment = parts[2] if len(parts) > 2 else None
    rows = [(i, t) for i, t in enumerate(variant["tests"]) if t["test_id"] == test_id and t["model_id"] == model_id
            and (segment is None or t["segment"] == segment)]
    for i, t in rows:
        for name in ("statistic", "metric"):
            if t[name] is not None:
                unit = "test statistic (dimensionless)" if name == "statistic" else "metric of the test row (the unit its test defines)"
                return {"metric": name, "test_id": test_id, "model_id": model_id, "segment": t["segment"], "value": t[name], "unit": unit,
                        "basis": f"{variant['path']}#/tests/{i}/{name}"}, None
    return None, T("the cited test row holds no statistic or metric (or no row matches), so the anchor is null",
                   "la fila de prueba citada no tiene estadistico ni metrica (o ninguna fila coincide), por lo que el ancla es nula")


def rwea_share_of_anchor(anchor: dict | None, rwea_total: float | None = None) -> tuple[float | None, dict | None]:
    """(share, reason): non-null only where the anchor's unit states a share of RWEA, or an RWEA amount with the total given (W15-11)."""
    if anchor is not None and anchor["unit"] == "share-of-rwea":
        return anchor["value"], None
    if anchor is not None and anchor["unit"] == "rwea-amount" and rwea_total:
        return anchor["value"] / rwea_total, None
    return None, T("the anchor is not stated as a share of RWEA or as an RWEA amount, so no RWEA level applies",
                   "el ancla no se expresa como proporcion de RWEA ni como monto de RWEA, por lo que no aplica nivel RWEA")


def findings_rows_of(ex: dict, case: str, fit: str) -> list[dict]:
    tier = tier_block(case)["tier"]
    as_of = date.fromisoformat(AS_OF)
    rows = []
    for v in ex["cases"][case]["variants"]:
        raised = date.fromisoformat(RELEASE[v["code_version"]])
        for f in v["findings"]:
            anchor, reason = anchor_of(f, v)
            sev = f["severity"]
            days = DEADLINES[SEVERITIES.index(sev)][tier - 1]
            due = raised + timedelta(days=days)
            status = STATUS_MAP[f["status"]]
            share, share_reason = rwea_share_of_anchor(anchor)
            risk = None
            if status == "risk_accepted":
                risk = {"approver": "not-applicable",
                        "approver_reason": T("a stated limit of a synthetic case: Contraste approves no model, so there is no approver",
                                             "un limite declarado de un caso sintetico: Contraste no aprueba ningun modelo, por lo que no hay aprobador"),
                        "expiry": None,
                        "expiry_reason": T("the limit is a property of the case, not a time-limited acceptance of a risk",
                                           "el limite es una propiedad del caso, no la aceptacion de un riesgo con plazo")}
            rows.append({
                "key": f"{case}/{v['variant_id']}/{f['id']}", "case_id": case, "variant_id": v["variant_id"], "id": f["id"],
                "entry_key": f"{case}/{fit}", "title": f["title"], "severity": sev, "ecb_f": ECB_F[sev], "product_status": f["status"],
                "status": status, "evidence": f["evidence"], "anchor": anchor, "anchor_reason": reason, "rwea_share": share, "rwea_share_reason": share_reason, "owner_role": OWNER[case], "tier": tier,
                "raised": raised.isoformat(), "deadline_days": days, "due": due.isoformat(), "ageing_days": (as_of - raised).days,
                "overdue": status in OPEN_STATES and as_of > due,
                "remediation": None,
                "remediation_reason": T("no remediation plan: the finding is an open result or a stated limit of a synthetic case",
                                        "sin plan de remediacion: el hallazgo es un resultado abierto o un limite declarado de un caso sintetico"),
                "risk_acceptance": risk,
            })
    return rows


def build_findings(ex: dict) -> dict:
    rows = []
    for case, fit in ENTRIES:
        rows += findings_rows_of(ex, case, fit)
    by_sev = {s: sum(1 for r in rows if r["severity"] == s) for s in SEVERITIES}
    by_status = {s: sum(1 for r in rows if r["status"] == s) for s in STATES_B7}
    by_case = []
    for case in sorted({r["case_id"] for r in rows}):
        sub = [r for r in rows if r["case_id"] == case]
        by_case.append({"case_id": case, "total": len(sub), "by_severity": {s: sum(1 for r in sub if r["severity"] == s) for s in SEVERITIES},
                        "by_status": {s: sum(1 for r in sub if r["status"] == s) for s in STATES_B7},
                        "overdue": sum(1 for r in sub if r["overdue"])})
    return {
        "schema": "contraste.governance.findings/v1", "case_id": "GOVERNANCE", "governance_id": "findings", "schema_version": "1.0.0",
        "as_of": AS_OF, "as_of_basis": AS_OF_BASIS, "provenance": provenance(ex),
        "conventions": {
            "deadline_days": {"label": "convention",
                              "basis": "days from the raised date to the due date by severity (rows S1 to S4) and tier (columns 1 to 4); no regulatory source "
                                       "prescribes days (06 B.7), so the table is a proposal (item 30 of the dossier UNVERIFIED list)",
                              "rows": [{"severity": s, "days": DEADLINES[i]} for i, s in enumerate(SEVERITIES)]},
            "severity_scale": {"label": "convention",
                               "basis": "W15-2: the product keeps S1 critical to S4 minor; the ECB F equivalent is shown beside it (06 l.616-617): "
                                        "S1 is F4 (very high), S2 F3, S3 F2, S4 F1 (low)",
                               "rows": [{"severity": s, "ecb_f": ECB_F[s]} for s in SEVERITIES]},
            "status_map": {"label": "convention",
                           "basis": "W15-5: open to open, accepted to risk_accepted, closed to validated_closed; overdue is computed from the due date and as_of",
                           "rows": [{"product": p, "register": r} for p, r in STATUS_MAP.items()]},
        },
        "rows": rows,
        "counts": {"total": len(rows), "by_severity": by_sev, "by_status": by_status, "overdue": sum(1 for r in rows if r["overdue"]),
                   "by_case": by_case},
    }


# ------------------------------------------------------------------------------------------------------------------ the appetite


def metric(mid: str, en: str, es: str, kind: str, unit: str, num, den, direction: str, green: float, amber: float, basis: str,
           reason: tuple[str, str] | None = None, rows: int | None = None) -> dict:
    if unit == "count":
        value = num
    else:
        value = None if (num is None or not den) else num / den
    if value is None:
        lt = "not_evaluated"
    elif direction == "lower-is-better":
        lt = "green" if value <= green else "amber" if value <= amber else "red"
    else:
        lt = "green" if value >= green else "amber" if value >= amber else "red"
    return {"id": mid, "name": T(en, es), "kind": kind, "value": value, "unit": unit, "numerator": num, "denominator": den,
            "register_rows": rows,
            "reason": T(*reason) if (value is None and reason) else None,
            "threshold": {"label": "convention", "basis": basis, "direction": direction, "green_limit": green, "amber_limit": amber},
            "light": lt}


def build_appetite(ex: dict, inv: dict, fnd: dict) -> dict:
    entries, rows = inv["entries"], fnd["rows"]
    as_of = date.fromisoformat(AS_OF)
    t1 = [e for e in entries if e["tier_block"]["tier"] == 1]
    pma = [e["attributes"]["A26"]["value"] for e in entries if e["attributes"]["A26"]["status"] == "present"]
    complete = [e for e in entries if all(a["status"] != "missing" for a in e["attributes"].values())]
    breach = [e for e in entries if e["attributes"]["A36"]["value"]["red"] > 0]
    distinct_all = {(r["entry_key"], r["id"]) for r in rows}
    high_rows = [r for r in rows if r["status"] in OPEN_STATES and r["severity"] in ("S1", "S2")]
    over_rows = [r for r in rows if r["overdue"]]
    high = {(r["entry_key"], r["id"]) for r in high_rows}
    over = {(r["entry_key"], r["id"]) for r in over_rows}
    metrics = [
        metric("tier1-validated-on-time", "Share of Tier 1 entries validated on time", "Proporcion de entradas de Nivel 1 validadas a tiempo",
               "share", "share", sum(1 for e in t1 if date.fromisoformat(e["schedule"]["next_review"]) >= as_of), len(t1),
               "higher-is-better", 0.9, 0.75, "a proposal (item 30): green from 90 percent, amber from 75 percent",
               ("no Tier 1 entry exists", "no existe entrada de Nivel 1")),
        metric("open-high-severity", "Open high-severity findings (S1 and S2)", "Hallazgos abiertos de severidad alta (S1 y S2)",
               "count", "count", len(high), len(distinct_all),
               "lower-is-better", 0, 3, "a proposal (item 30): green at none, amber up to three distinct findings", rows=len(high_rows)),
        metric("overdue-remediation", "Overdue remediation", "Remediacion vencida", "count", "count", len(over), len(distinct_all),
               "lower-is-better", 0, 3, "a proposal (item 30): green at none, amber up to three distinct findings", rows=len(over_rows)),
        metric("entries-under-exception", "Entries used under exception", "Entradas usadas bajo excepcion", "count", "count",
               sum(1 for e in entries if e["lifecycle"]["exception"]), len(entries), "lower-is-better", 0, 1,
               "a proposal (item 30): green at none, amber at one entry"),
        metric("entries-in-breach", "Entries in breach of their thresholds (a red test row)",
               "Entradas que incumplen sus umbrales (una fila de prueba roja)", "count", "count", len(breach), len(entries), "lower-is-better", 0, 1,
               "a proposal (item 30): green at none, amber at one entry"),
        metric("pma-magnitude", "PMA magnitude relative to the model output", "Magnitud de PMA relativa al resultado del modelo", "magnitude",
               "share-of-model-output", sum(p["overlays_total"] for p in pma) if pma else None, sum(p["model_output"] for p in pma) if pma else None,
               "lower-is-better", 0.01, 0.03, "a proposal (item 30): green up to 1 percent of the model output, amber up to 3 percent",
               ("no entry holds a PMA with an amount", "ninguna entrada tiene una PMA con monto")),
        metric("owner-and-complete-record", "Share of entries with an owner role and a complete record",
               "Proporcion de entradas con rol de propietario y registro completo", "share", "share", len(complete), len(entries),
               "higher-is-better", 0.9, 0.5, "a proposal (item 30): green from 90 percent, amber from 50 percent; complete means no attribute is missing"),
    ]
    return {
        "schema": "contraste.governance.appetite/v1", "case_id": "GOVERNANCE", "governance_id": "appetite", "schema_version": "1.0.0",
        "as_of": AS_OF, "as_of_basis": AS_OF_BASIS, "provenance": provenance(ex),
        "population": {"entries": len(entries), "findings": len(rows), "distinct_findings": len(distinct_all), "tier1_entries": len(t1)},
        "metrics": metrics,
    }


# ------------------------------------------------------------------------------------------------------------------ the reports


NO_POLICY_FILE = "no policy file for an inline battery string"   # riskvalidation.governance.policy.NO_POLICY_FILE (engine 1.0.0)


def parse_policy(row: dict, decisions: dict) -> dict:
    """The policy identity of a row (W15-12): the kind is spec(test_id).decision where the test is registered, the direction is null for an inline
    battery string because no policy file holds it."""
    pv = row["policy_version"]
    family = row["test_id"].split(".")[0]
    decision = decisions.get(row["test_id"])
    kind = {"kind": decision, "kind_reason": None} if decision else {
        "kind": None, "kind_reason": "the test id is not in the engine registry (spec() raises KeyError), so it has no decision"}
    base = {"label": pv, **kind, "alpha_amber": row["alpha_amber"], "alpha_red": row["alpha_red"], "_family": family}
    if pv.startswith("riskvalidation-default "):
        return {**base, "direction": None, "direction_reason": "read from the policy file by the engine: the packaged threshold of the test (fixture: not resolved here)",
                "parameters": {}, "version": pv.split(" ", 1)[1], "source": "packaged-policy", "reason": None}
    m = re.fullmatch(r"(contraste-[a-z0-9]+-battery-(\d+\.\d+\.\d+))((?:; [a-z0-9_]+=[^;]+)*)", pv)
    if not m:
        return {**base, "kind": None, "kind_reason": "unresolved identity", "direction": None, "direction_reason": NO_POLICY_FILE, "parameters": {},
                "version": None, "source": "unresolved", "reason": "the policy string matches neither a packaged label nor an inline battery string"}
    params: dict = {}
    for part in [x for x in m.group(3).split("; ") if x]:
        k, v = part.split("=", 1)
        try:
            params[k] = float(v)
        except ValueError:
            params[k] = v
    return {**base, "direction": None, "direction_reason": NO_POLICY_FILE, "parameters": params, "version": m.group(2),
            "source": "inline-battery", "reason": None}


def outcome_rows(variant: dict, decisions: dict) -> list[dict]:
    out = []
    for r in variant["tests"]:
        p = parse_policy(r, decisions)
        family = p.pop("_family")
        out.append({"test_id": r["test_id"], "model_id": r["model_id"], "segment": r["segment"], "family": family, "statistic": r["statistic"],
                    "p_value": r["p_value"], "metric": r["metric"], "light": r["light"], "h0": r["h0"], "reference": r["reference"], "policy": p})
    return out


SECTION_TITLES = [
    ("Executive summary", "Resumen ejecutivo"), ("Model description and intended use", "Descripcion del modelo y uso previsto"),
    ("Conceptual soundness", "Solidez conceptual"), ("Data", "Datos"), ("Implementation and process verification", "Implementacion y verificacion del proceso"),
    ("Outcomes analysis", "Analisis de resultados"), ("Sensitivity, robustness and stress", "Sensibilidad, robustez y estres"),
    ("Ongoing monitoring", "Monitoreo continuo"), ("Limitations and compensating controls", "Limitaciones y controles compensatorios"),
    ("Findings register", "Registro de hallazgos"), ("Overall opinion and recommendation", "Opinion global y recomendacion"),
    ("Appendices", "Anexos"),
]
SECTION_KEYS = ["executive_summary", "model_description", "conceptual_soundness", "data", "implementation", "outcomes_analysis",
                "sensitivity_robustness_stress", "ongoing_monitoring", "limitations_and_controls", "findings_register",
                "opinion_and_recommendation", "appendices"]
LEVEL_LABEL = {1: T("adequate, no deficiencies", "adecuado, sin deficiencias"), 2: T("adequate, minor deficiencies", "adecuado, deficiencias menores"),
               3: T("major deficiencies", "deficiencias mayores"), 4: T("severe deficiencies", "deficiencias severas")}
RECOMMENDATION = {1: "approve", 2: "approve with conditions", 3: "remediate before use", 4: "remediate before use"}
REC_TEXT = {
    "approve": T("Approve: no open finding. This is the rule's output on the evidence; Contraste approves no model.",
                 "Aprobar: sin hallazgos abiertos. Es el resultado de la regla sobre la evidencia; Contraste no aprueba ningun modelo."),
    "approve with conditions": T("Approve with conditions: only minor findings are open. This is the rule's output on the evidence; Contraste approves no model.",
                                 "Aprobar con condiciones: solo hay hallazgos menores abiertos. Es el resultado de la regla sobre la evidencia; Contraste no aprueba ningun modelo."),
    "remediate before use": T("Remediate before use: a significant or critical finding is open. This is the rule's output on the evidence; Contraste approves no model.",
                              "Remediar antes del uso: hay un hallazgo significativo o critico abierto. Es el resultado de la regla sobre la evidencia; Contraste no aprueba ningun modelo."),
}


def text_block(en: str, es: str) -> dict:
    return {"kind": "text", "text": T(en, es)}


def table_block(caption: tuple[str, str], cols: list[tuple[str, str]], rows: list[list]) -> dict:
    return {"kind": "table", "caption": T(*caption), "columns": [T(*c) for c in cols], "rows": rows}


def section(i: int, status: str, inputs: list[tuple[str, str]], blocks: list[dict], missing: list[tuple[tuple[str, str], tuple[str, str]]],
            absent: tuple[str, str] | None = None, **extra) -> dict:
    s = {"number": i, "key": SECTION_KEYS[i - 1], "title": T(*SECTION_TITLES[i - 1]), "status": status,
         "inputs": [{"ref": r, "kind": k} for r, k in inputs], "absent_reason": T(*absent) if absent else None, "blocks": blocks,
         "missing": [{"element": T(*e), "reason": T(*r)} for e, r in missing]}
    s.update(extra)
    return s


def build_report(ex: dict, inv: dict, fnd: dict, case: str, fit: str) -> dict:
    c = ex["cases"][case]
    key = f"{case}/{fit}"
    entry = next(e for e in inv["entries"] if e["key"] == key)
    default = next(v for v in c["variants"] if v["variant_id"] == c["default_variant"])
    rows = [r for r in fnd["rows"] if r["entry_key"] == key]
    open_rows = [r for r in rows if r["status"] in OPEN_STATES]
    level = max((4 if r["severity"] == "S1" else 3 if r["severity"] == "S2" else 2 for r in open_rows), default=1)
    outcomes = outcome_rows(default, c["spec_decisions"])
    counts = {k: 0 for k in ("green", "amber", "red", "not_evaluated", "error")}
    for r in outcomes:
        counts[r["light"]] += 1
    md, man = c["models_document"], c["manifest"]
    tb = entry["tier_block"]
    q = man["question"]
    n_var = len(c["variants"])
    inputs = {
        1: [(f"{man['path']} (manifest: question)", "document"), (f"findings register rows of {key}", "document"),
            (f"test rows of {default['path']}", "document")],
        2: [(f"{md['path']} (models document)", "document"), (f"inventory entry {key} (attributes and components)", "document"),
            ("tier block of the inventory entry (tiering.matrix_tier)", "engine")],
        3: [(f"{md['path']} (models document: the rungs)", "document"), ("frontend/src/pages/Methodology.tsx (Methodology page)", "document")],
        4: [(f"{man['path']} (manifest: sources)", "document"), (f"provenance inputs of {default['path']}", "document")],
        5: [(f"provenance of {md['path']}: seed, code_version, riskvalidation_version", "document")],
        6: [(f"test rows of {default['path']}", "document"), ("policy identity of each row (policy.resolve_policy)", "engine")],
        7: [(f"the {n_var} variants of the entry", "document")],
        9: [(f"findings register rows of {key} with status risk_accepted", "document")],
        10: [(f"findings register rows of {key}", "document")],
        11: [("opinion rule W15-7 (opinion.opinion_level) over the open findings", "engine"), ("recommendation text (opinion.recommendation)", "engine")],
        12: [(f"provenance of the {len(c['variants']) + 2} documents read for the entry", "document")],
    }
    secs = []
    secs.append(section(1, "filled", inputs[1], [
        {"kind": "text", "text": q},
        text_block(f"Scope: the fit {fit} of case {case}; the full battery of the default variant ({len(outcomes)} test rows) and the findings of its {n_var} variants.",
                   f"Alcance: el ajuste {fit} del caso {case}; la bateria completa de la variante por defecto ({len(outcomes)} filas de prueba) y los hallazgos de sus {n_var} variantes."),
        table_block(("Test lights of the default variant", "Luces de las pruebas de la variante por defecto"),
                    [("Light", "Luz"), ("Rows", "Filas")], [[k, v] for k, v in counts.items()]),
        text_block(f"Overall opinion: level {level} of 4 on the ECB scale ({LEVEL_LABEL[level]['en']}); see section 11.",
                   f"Opinion global: nivel {level} de 4 en la escala del BCE ({LEVEL_LABEL[level]['es']}); ver seccion 11."),
    ], [(("Conditions of use", "Condiciones de uso"), ("no structured list of conditions of use exists (A D5 section 1)",
                                                      "no existe una lista estructurada de condiciones de uso (A D5 seccion 1)"))],
        opinion_level=level))
    secs.append(section(2, "filled", inputs[2], [
        text_block(f"{man['title']['en']}: {len(md['models'])} model records in the fit {fit}; tier {tb['tier']} (M {tb['materiality']['m']['graded']}, "
                   f"C {tb['complexity']['c']['mean']}, reading B).",
                   f"{man['title']['es']}: {len(md['models'])} registros de modelo en el ajuste {fit}; nivel {tb['tier']} (M {tb['materiality']['m']['graded']}, "
                   f"C {tb['complexity']['c']['mean']}, lectura B)."),
        table_block(("Components", "Componentes"), [("Model", "Modelo"), ("Role", "Rol"), ("Rung", "Peldano")],
                    [[x["model_id"], x["role"], x["rung"]] for x in entry["components"]]),
        table_block(("Tier under the four readings", "Nivel bajo las cuatro lecturas"), [("Reading", "Lectura"), ("Tier", "Nivel")],
                    [[s["reading"], s["tier"]] for s in tb["tier_sensitivity"]]),
    ], [(("Intended use and operating boundaries", "Uso previsto y limites de operacion"),
         ("no intended-use field exists; the boundaries are not stated for this case (A D5 section 2)",
          "no existe campo de uso previsto; los limites no se declaran para este caso (A D5 seccion 2)"))]))
    secs.append(section(3, "filled", inputs[3], [
        text_block("The design alternatives are the rungs of the ladder in the models document: " + ", ".join(x["model_id"] for x in entry["components"]) + ".",
                   "Las alternativas de diseno son los peldanos de la escalera del documento de modelos: " + ", ".join(x["model_id"] for x in entry["components"]) + "."),
    ], [(("Written soundness assessment and explainability rating", "Evaluacion escrita de solidez y calificacion de explicabilidad"),
         ("no written assessment and no rating exist per case (A D5 section 3)", "no existe evaluacion escrita ni calificacion por caso (A D5 seccion 3)"))]))
    secs.append(section(4, "filled", inputs[4], [
        text_block("Sources: " + (", ".join(man["sources"]) if man["sources"] else "none (a generated book)") + ".",
                   "Fuentes: " + (", ".join(man["sources"]) if man["sources"] else "ninguna (un libro generado)") + "."),
    ], [(("Representativeness and bias examination", "Representatividad y examen de sesgo"),
         ("only C01-style drift tests and C21 examine them (A D5 section 4)", "solo las pruebas de deriva estilo C01 y C21 las examinan (A D5 seccion 4)"))]))
    secs.append(section(5, "filled", inputs[5], [
        text_block(f"Seed {man['seed']}, code version {md['code_version']}, riskvalidation {md['riskvalidation_version']}; every document records them.",
                   f"Semilla {man['seed']}, version de codigo {md['code_version']}, riskvalidation {md['riskvalidation_version']}; cada documento las registra."),
    ], [(("Independent replication of the pipeline", "Replicacion independiente del pipeline"),
         ("no independent replication statement exists (A D5 section 5)", "no existe declaracion de replicacion independiente (A D5 seccion 5)"))]))
    secs.append(section(6, "filled", inputs[6], [
        {"kind": "outcomes", "variant_id": default["variant_id"], "rows": outcomes},
    ], [(("Threshold kind for rows without a policy file", "Tipo de umbral para filas sin archivo de politica"),
         ("the kind is spec(test_id).decision where the test is registered (these tests are not: spec() raises KeyError), and the direction is null for an inline battery string, which has no policy file",
          "el tipo es spec(test_id).decision donde la prueba está registrada (estas no lo están: spec() lanza KeyError), y la dirección es nula para una cadena de batería en línea, que no tiene archivo de política"))]))
    secs.append(section(7, "filled", inputs[7], [
        table_block(("Variants as perturbations", "Variantes como perturbaciones"), [("Variant", "Variante"), ("Test rows", "Filas"), ("Red rows", "Filas rojas")],
                    [[v["variant_id"], len(v["tests"]), sum(1 for t in v["tests"] if t["light"] == "red")] for v in c["variants"]]),
    ], []))
    if case == "C07":
        p = ex["cases"]["C07"]["pma"]
        secs.append(section(8, "filled", [(f"PMA overlays_total at {p['pointer']}", "document")], [
            text_block(f"PMAs in force: overlays of {p['overlays_total']:.0f} {p['currency']} inside the IFRS 9 provision of {p['model_output']:.2f} {p['currency']}.",
                       f"PMA vigentes: ajustes por {p['overlays_total']:.0f} {p['currency']} dentro de la provision IFRS 9 de {p['model_output']:.2f} {p['currency']}."),
        ], [(("Monitoring pack and overrides analysis", "Paquete de monitoreo y analisis de overrides"),
             ("no monitoring pack exists and the word override appears in no committed document (A D5 section 8)",
              "no existe paquete de monitoreo y la palabra override no aparece en ningun documento confirmado (A D5 seccion 8)"))]))
    else:
        secs.append(section(8, "absent", [], [], [], absent=(
            "no monitoring pack, no overrides analysis and no PMA exists for this entry (A D5 section 8)",
            "no existe paquete de monitoreo, analisis de overrides ni PMA para esta entrada (A D5 seccion 8)")))
    accepted = [r for r in rows if r["status"] == "risk_accepted"]
    secs.append(section(9, "filled", inputs[9], [
        text_block(f"{len(accepted)} register rows are stated limits of the synthetic case (risk_accepted); use restrictions are the SDD non-goals.",
                   f"{len(accepted)} filas del registro son limites declarados del caso sintetico (risk_accepted); las restricciones de uso son los no-objetivos del SDD."),
    ], [(("Compensating-control catalogue and use restrictions as data", "Catalogo de controles compensatorios y restricciones de uso como datos"),
         ("neither exists as data (A D5 section 9)", "ninguno existe como datos (A D5 seccion 9)"))]))
    secs.append(section(10, "filled", inputs[10], [
        table_block(("Findings of the entry", "Hallazgos de la entrada"),
                    [("Key", "Clave"), ("Severity", "Severidad"), ("ECB F", "F del BCE"), ("Status", "Estado"), ("Due", "Vence"), ("Overdue", "Vencido")],
                    [[r["key"], r["severity"], r["ecb_f"], r["status"], r["due"], r["overdue"]] for r in rows]),
    ], [(("Remediation plan text", "Texto del plan de remediacion"),
         ("no remediation plan exists: the findings are open results or stated limits (W15-5)", "no existe plan de remediacion: los hallazgos son resultados abiertos o limites declarados (W15-5)"))]))
    opinion = {
        "level": level, "level_label": LEVEL_LABEL[level],
        "rule": {"id": "W15-7", "text": T("Level 1 with no open finding; 2 with S4 or S3 only; 3 with any S2; 4 with any S1 (open and overdue findings, not risk_accepted); "
                                          "where an anchor is a share of RWEA, 5 to 10 percent gives level 3 and 10 percent or more level 4, and an anchor can only raise a level (the maximum of the two). A convention (item 30).",
                                          "Nivel 1 sin hallazgos abiertos; 2 con solo S4 o S3; 3 con algun S2; 4 con algun S1 (hallazgos abiertos y vencidos, no risk_accepted); "
                                          "si el ancla es una proporcion de RWEA, de 5 a 10 por ciento da nivel 3 y 10 por ciento o mas da nivel 4, y un ancla solo puede subir un nivel (el maximo de ambos). Una convencion (punto 30).")},
        "rwea_cut_points_applied": False,
        "open_findings": [{"key": r["key"], "severity": r["severity"], "rwea_share": r["rwea_share"]} for r in open_rows],
        "recommendation": {"outcome": RECOMMENDATION[level], "text": REC_TEXT[RECOMMENDATION[level]]},
        "label": T(LABEL_EN, LABEL_ES),
    }
    secs.append(section(11, "filled", inputs[11], [
        text_block(f"Opinion level {level}: {LEVEL_LABEL[level]['en']}. {REC_TEXT[RECOMMENDATION[level]]['en']}",
                   f"Nivel de opinion {level}: {LEVEL_LABEL[level]['es']}. {REC_TEXT[RECOMMENDATION[level]]['es']}"),
    ], [], opinion=opinion))
    docs_read = [d for d in inv["provenance"]["documents_read"] if d["path"] in
                 {man["path"], md["path"], *[v["path"] for v in c["variants"]]}]
    secs.append(section(12, "filled", inputs[12], [
        table_block(("Documents read", "Documentos leidos"), [("Path", "Ruta"), ("sha256", "sha256")], [[d["path"], d["sha256"]] for d in docs_read]),
    ], [(("Policy-file version and content hash for the inline battery strings", "Version y hash del archivo de politica de las cadenas en linea"),
         ("the contraste-*-battery strings of the committed case documents have no policy file; the next bake of each case writes the packaged battery label",
         "las cadenas contraste-*-battery de los documentos de caso confirmados no tienen archivo de política; la próxima ejecución de cada caso escribe la etiqueta de batería empaquetada"))]))
    return {
        "schema": "contraste.governance.report/v1", "case_id": "GOVERNANCE", "governance_id": "report", "schema_version": "1.0.0",
        "as_of": AS_OF, "as_of_basis": AS_OF_BASIS, "provenance": provenance(ex), "entry_key": key,
        "title": T(f"Validation report: {man['title']['en']}", f"Informe de validacion: {man['title']['es']}"),
        "tier": tb["tier"], "test_counts": counts, "sections": secs,
    }


def main() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ex = json.loads(EXTRACT.read_text(encoding="utf-8"))
    inv = build_inventory(ex)
    fnd = build_findings(ex)
    app = build_appetite(ex, inv, fnd)
    write("inventory-fixture.json", inv)
    write("findings-fixture.json", fnd)
    write("appetite-fixture.json", app)
    write("report-C07-banco-andino-fixture.json", build_report(ex, inv, fnd, "C07", "banco-andino"))
    write("report-C18-banco-andino-fixture.json", build_report(ex, inv, fnd, "C18", "banco-andino"))
    print(f"wrote 5 fixtures to {OUT.relative_to(ROOT)}: {len(inv['entries'])} entries, {len(fnd['rows'])} findings")


if __name__ == "__main__":
    main()
