"""The cross-field checks of the four governance documents, as importable functions (as U7 M3, U10 D3, U11 and U13 do).

JSON Schema cannot hold these: they recompute values from other fields, compare dates, walk a graph, or compare documents. The governance
bake (U15-P) calls ``violations`` on every document it writes and ``cross_violations`` on the set (a non-empty list is a refusal to publish);
the producer tests run both over the fixtures and over ``data/derived/governance``. The rules are written here from dossier 06 (B.1 to B.8,
I.3), the U15 research addendum (D1 to D5) and the decisions W15-1 to W15-9 of the unit sizing; they do not import the fixture builder. The
engine (U15-E) implements the same rules in ``riskvalidation.governance`` and its tests carry the goldens of ``governance-api.md``.
Standard library only.

``violations(doc)`` takes one governance document and returns a list of messages, empty when it conforms; ``cross_violations(docs)`` takes
``{"inventory": ..., "findings": ..., "appetite": ..., "reports": {entry_key: report}}`` and checks what must agree between them;
``regulatory_claims(text)`` returns the phrases of a text that call a convention regulatory.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

SEVERITIES = ["S1", "S2", "S3", "S4"]
ECB_F = {"S1": "F4", "S2": "F3", "S3": "F2", "S4": "F1"}                       # W15-2, 06 l.616-617
STATUS_MAP = {"open": "open", "accepted": "risk_accepted", "closed": "validated_closed"}   # W15-5
STATES_B7 = ["open", "action_plan_agreed", "in_progress", "submitted_for_closure", "validated_closed", "overdue", "risk_accepted"]
OPEN_STATES = ("open", "action_plan_agreed", "in_progress", "submitted_for_closure", "overdue")
READINGS = {"A": ("literal", "mean"), "B": ("graded", "mean"), "C": ("literal", "maximum"), "D": ("graded", "maximum")}
ADOPTED = "B"                                                                   # W15-3
ATTR_IDS = [f"A{i:02d}" for i in range(1, 41)]
ATTR_STATUSES = ("present", "derivable", "convention", "not-applicable", "missing")
POINTER = re.compile(r"\S+#/\S*")
LABEL_EN = "the rule's output on the evidence; Contraste approves no model"
RECOMMENDATION = {1: "approve", 2: "approve with conditions", 3: "remediate before use", 4: "remediate before use"}
SECTION_KEYS = ["executive_summary", "model_description", "conceptual_soundness", "data", "implementation", "outcomes_analysis",
                "sensitivity_robustness_stress", "ongoing_monitoring", "limitations_and_controls", "findings_register",
                "opinion_and_recommendation", "appendices"]
METRIC_IDS = ["tier1-validated-on-time", "open-high-severity", "overdue-remediation", "entries-under-exception", "entries-in-breach",
              "pma-magnitude", "owner-and-complete-record"]
# 06 B.4 l.576-583, a convention: the states and the allowed transitions; use before validation only with an exception record
B4 = {
    "proposed": ["in_development"],
    "in_development": ["submitted_for_validation"],
    "submitted_for_validation": ["in_validation"],
    "in_validation": ["approved", "approved_with_conditions", "in_development"],
    "approved": ["in_use"],
    "approved_with_conditions": ["in_use"],
    "in_use": ["under_monitoring_alert", "material_change_pending", "in_validation", "restricted", "decommissioned"],
    "under_monitoring_alert": ["in_use", "restricted", "in_remediation"],
    "restricted": ["in_remediation", "in_use", "decommissioned"],
    "in_remediation": ["in_validation", "restricted", "decommissioned"],
    "material_change_pending": ["submitted_for_validation", "in_use"],
    "decommissioned": [],
}
B4_PRE_VALIDATION = ("in_development", "submitted_for_validation", "in_validation")   # to in_use only with an exception record
B4_IN_USE = ("in_use", "under_monitoring_alert", "restricted", "material_change_pending", "in_remediation")
TOL = 1e-9

# the phrases that call a convention regulatory (English and Spanish); "no regulatory source prescribes days" is not one of them. Each pattern has a
# sample in the tests that only it matches (a pattern removed is a pattern found missing).
_ACTORS = r"(regulat\w*|supervis\w*|ECB|PRA|OSFI|(?-i:Fed)(?:eral Reserve)?|EBA|BCBS|Basel|SR\s?\d+-\d+|SS1/23|E-23)"
_REG_CLAIMS = [
    re.compile(r"\bregulatory\s+(value|requirement|threshold|deadline|limit|minimum|standard|cut|interval|frequency|table|parameter|band)s?\b", re.I),
    re.compile(r"\b(is|are|as)\s+(a\s+|an\s+)?regulatory\b", re.I),
    re.compile(r"\brequired\s+by\s+(the\s+)?(regulat|law|supervis)\w*", re.I),
    re.compile(r"\b(plazo|valor|umbral|requisito|l[ií]mite|m[ií]nimo|frecuencia|tabla)s?\s+regulatori[oa]s?\b", re.I),
    re.compile(r"\b(es|son)\s+(un\s+|una\s+)?regulatori[oa]s?\b", re.I),
    re.compile(r"\b(prescribed|set|mandated|imposed|dictated|fixed|stipulated)\s+by\s+(the\s+)?" + _ACTORS, re.I),
    re.compile(r"\b(?-i:PRA|ECB|OSFI|Fed|EBA)\s+(requires|require|mandates|prescribes|imposes|sets)\b|\b(regulator|supervisor)\s+(requires|mandates|prescribes|imposes|sets)\b", re.I),
    re.compile(r"\b(a|an|the)\s+supervisory\s+(requirement|minimum|standard|threshold|deadline|interval|limit|value)\b", re.I),
    re.compile(r"\b(SR\s?\d+-\d+|SS1/23|E-23)\s+(minimum|requirement|threshold|deadline|interval|limit)s?\b", re.I),
    re.compile(r"\b(exige|impone|establece|fija|prescribe)\s+(el|la|los|las)\s+(regulador|supervisor|BCE|PRA|OSFI)\w*", re.I),
]
# a statement that Contraste approves, certifies or finds a model compliant (SDD non-goal 1; 06 I.6); the fixed negations and the allowed phrases are removed first
_APPROVAL_CLAIMS = [
    re.compile(r"\bapprov(es|ed|ing|al|e)\b", re.I),
    re.compile(r"\bcertif(y|ies|ied|ication)\b", re.I),
    re.compile(r"\b(compliant|complies|complying)\b|\bcompliance\s+with\b|\bin\s+compliance\b", re.I),
    re.compile(r"\baprob(ado|ada|ados|adas|amos|ar|[oó])\b|\baprueb\w*|\baprobaci[oó]n\b", re.I),
    re.compile(r"\bcertificad[oa]s?\b|\bcertifica\b", re.I),
    re.compile(r"\bcumple\b|\bcumplimiento\s+(de|con)\b|\bconforme\s+a\b", re.I),
]
# the fixed negations: statements that Contraste does NOT approve, and the names of the W15-7 recommendation outcomes, which are labelled the rule's output
_APPROVAL_NEGATIONS = re.compile(
    r"Contraste approves no model|Contraste no aprueba ning[uú]n modelo|\b(no|without)\s+(an?\s+)?(approval|approver)\b|approval date or (the )?authority|"
    r"\bsin\s+(aprobaci[oó]n|aprobador)\b|\bnon-goal\b|"
    r"\bApprove(?: with conditions)?:|\bAprobar(?: con condiciones)?:|^\s*approve(?: with conditions)?\s*$", re.I)
# phrases of a credit decision on a loan, never a statement about a model: a metric, a cohort or an applicant outcome of the case documents (each with its reason).
# A new phrase needs its reason here and a test sample in tests/contracts_u15; a claim about a model never matches one of them.
APPROVAL_ALLOWED: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bapproval[ _-]rates?\b|\btasas?\s+de\s+aprobaci[oó]n\b", re.I), "the share of applications a lender approves: a metric of the credit decision (HMDA, C01, C21)"),
    (re.compile(r"\bapproval\s+cohorts?\b|\bcohortes?\s+de\s+aprobaci[oó]n\b", re.I), "the loans approved in one period, the unit of a vintage analysis (C03)"),
    (re.compile(r"\bapproval\s+fiscal\s+years?\b|\bfirst approval of FY\S+|\bwithin \d+ months of approval\b|\ba[nñ]os?\s+fiscales?\s+de\s+aprobaci[oó]n\b", re.I),
     "the date a loan was approved, a field of the SBA data (C03, C06, C08)"),
    (re.compile(r"\blines? at their approval\b|\bat its full approval\b|\ba su monto aprobado\b|\b(gross|bruto)?\s*(approved amount|monto (bruto )?aprobado)\b", re.I),
     "the approved amount of a loan or line: the exposure at approval (C06, C08, C09)"),
    (re.compile(r"\b(of|among|entre)\s+the\s+approved\b|\bde\s+los\s+aprobados\b|\bentre\s+aprobados\b|\bapproved\s+by\s+the\s+(challenger|champion)\s+only\b|"
                r"\baprobados\s+solo\s+por\b|\bapproved\s+defaulters\b|\baprobados\s+que\s+incumplen\b", re.I),
     "the applicants a scorecard approves, as a population whose loss or bad rate is measured (C01)"),
    (re.compile(r"\bgroup is approved at (higher|lower)\b|\bgrupo es aprobado con (mayores|menores)\b", re.I), "a protected group's approval odds in a disparity test (C21)"),
    (re.compile(r"\bapplications? approved but not accepted\b|\bsolicitudes? aprobadas? pero no aceptadas?\b|\bsolicitudes? aprobadas? no aceptadas?\b|\bapproved applications not accepted\b|"
                r"\b1 approval \(HMDA\b|\bApproval is action taken\b", re.I), "an HMDA action taken: the lender's decision on one application (C21)"),
    (re.compile(r"\bapproved as decision V\d+\b", re.I), "a parameter value of the case, approved as a design decision of the build (decision V6), not a model"),
]
_ALLOWED_RX = re.compile("|".join(f"(?:{rx.pattern})" for rx, _ in APPROVAL_ALLOWED), re.I)


def regulatory_claim_hits(text: str) -> list[int]:
    """The indexes of the patterns that match ``text``."""
    return [i for i, rx in enumerate(_REG_CLAIMS) if rx.search(text)]


def regulatory_claims(text: str) -> list[str]:
    """The phrases of ``text`` that call a convention regulatory."""
    out = []
    for rx in _REG_CLAIMS:
        out += [m.group(0) for m in rx.finditer(text)]
    return out


def approval_claims(text: str) -> list[str]:
    """The phrases of ``text`` that state an approval, a certification or a compliance of a model, the fixed negations exempt."""
    clean = _ALLOWED_RX.sub(" ", _APPROVAL_NEGATIONS.sub(" ", text))
    out = []
    for rx in _APPROVAL_CLAIMS:
        out += [m.group(0) for m in rx.finditer(clean)]
    return out


def text_violations(doc: dict) -> list[str]:
    """Every string of the document is scanned for an approval, certification or compliance claim (M2), whichever object holds it."""
    out = []
    for text in strings(doc):
        for claim in approval_claims(text):
            out.append(f"text states an approval, certification or compliance ({claim!r}): {text[:80]!r}")
    return out


# ------------------------------------------------------------------------------------------------------------------ the rules


def iso(s: str) -> date:
    return date.fromisoformat(s)


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    m += 1
    last = [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def exposure_band(share: float | None, cuts: list[float]) -> int:
    if share is None:
        return 1
    return 4 if share >= cuts[0] else 3 if share >= cuts[1] else 2 if share >= cuts[2] else 1


def matrix_tier(m: int, c: int) -> int:
    """06 B.3 l.571-574."""
    if m == 4 or (m == 3 and c >= 3):
        return 1
    if m == 3 or (m == 2 and c >= 3):
        return 2
    if m == 2 or (m == 1 and c >= 3):
        return 3
    return 4


def c_mean(scores: list[int]) -> int:
    return (2 * sum(scores) + len(scores)) // (2 * len(scores))


def light(value: float | None, direction: str, green: float, amber: float) -> str:
    if value is None:
        return "not_evaluated"
    if direction == "lower-is-better":
        return "green" if value <= green else "amber" if value <= amber else "red"
    return "green" if value >= green else "amber" if value >= amber else "red"


def rwea_level(rwea_share: float | None) -> int:
    """The level an RWEA share gives (ECB Instructions 2019, 2.4.2): 3 from 5 percent, 4 from 10 percent, none (0) below 5 percent."""
    if rwea_share is None:
        return 0
    return 4 if rwea_share >= 0.10 else 3 if rwea_share >= 0.05 else 0


def finding_level(severity: str, rwea_share: float | None = None) -> int:
    """The level one open finding gives (W15-11): the maximum of its severity level and its RWEA level, so an anchor can only raise it."""
    return max({"S1": 4, "S2": 3}.get(severity, 2), rwea_level(rwea_share))


def opinion_level(open_findings: list[dict]) -> int:
    return max((finding_level(f["severity"], f.get("rwea_share")) for f in open_findings), default=1)


def deadline(table_rows: list[dict], severity: str, tier: int) -> int:
    return next(r["days"] for r in table_rows if r["severity"] == severity)[tier - 1]


def is_overdue(status: str, due: date, as_of: date) -> bool:
    return status in OPEN_STATES and as_of > due


def topological(keys: list[str], edges: list[tuple[str, str]]) -> tuple[list[list[str]], list[str]]:
    """Kahn's algorithm by generation: (the generations, the nodes left over by a cycle)."""
    indeg = {k: 0 for k in keys}
    for _, d in edges:
        indeg[d] += 1
    gens, remaining = [], set(keys)
    while True:
        layer = sorted(k for k in remaining if indeg[k] == 0)
        if not layer:
            break
        gens.append(layer)
        remaining -= set(layer)
        for u, d in edges:
            if u in layer:
                indeg[d] -= 1
    return gens, sorted(remaining)


# ------------------------------------------------------------------------------------------------------------------ small helpers


def close(a: float, b: float, rel: float = 1e-9, abs_: float = 1e-9) -> bool:
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


def strings(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)


def convention_dicts(node: Any):
    """Every object that carries a ``label`` (a convention table, or something labelled otherwise)."""
    if isinstance(node, dict):
        if "label" in node and isinstance(node["label"], str):
            yield node
        for v in node.values():
            yield from convention_dicts(v)
    elif isinstance(node, list):
        for v in node:
            yield from convention_dicts(v)


def convention_violations(doc: dict) -> list[str]:
    out = []
    for obj in convention_dicts(doc):
        if obj["label"] != "convention":
            if "regulat" in obj["label"].lower():
                out.append(f"a convention is labelled {obj['label']!r}: no table of this unit is regulatory")
            continue
        for s in strings({k: v for k, v in obj.items() if k != "label"}):
            for claim in regulatory_claims(s):
                out.append(f"a convention calls itself regulatory ({claim!r}): {s[:80]!r}")
    return out


# ------------------------------------------------------------------------------------------------------------------ the inventory


def inventory_violations(doc: dict) -> list[str]:
    out: list[str] = []
    entries = doc["entries"]
    if not entries:
        return ["the inventory holds no entry: there is nothing to check, nothing to publish"]
    keys = [e["key"] for e in entries]
    if len(set(keys)) != len(keys):
        out.append(f"entry keys repeat: {sorted(k for k in set(keys) if keys.count(k) > 1)}")
    conv = doc["conventions"]
    cuts = conv["exposure_band_cuts"]["cuts"]
    if sorted(cuts, reverse=True) != cuts:
        out.append(f"exposure band cut points are not decreasing: {cuts}")
    freq = {t["tier"]: t for t in conv["frequency"]["tiers"]}
    if sorted(freq) != [1, 2, 3, 4]:
        out.append("the frequency table does not hold tiers 1 to 4 once each")
    comp_seen: dict[str, str] = {}
    out += as_of_violations(doc, "inventory", [e["schedule"]["last_validation"]["date"] for e in entries])
    for x in doc["excluded"]:
        if x["variant_id"] is not None and any(x["variant_id"] == v["variant_id"] and x["case_id"] == e["case_id"]
                                                for e in entries for v in e["variants"]):
            out.append(f"excluded variant {x['case_id']}/{x['variant_id']} is also assigned to an entry")
    for e in entries:
        k = e["key"]
        vids = [v["variant_id"] for v in e["variants"]]
        if len(set(vids)) != len(vids):
            out.append(f"{k}: a variant is listed twice")
        for v in e["variants"]:
            if not v["basis"].strip():
                out.append(f"{k}: variant {v['variant_id']} has no basis for its assignment to the fit")
        if k != f"{e['case_id']}/{e['fit_id']}":
            out.append(f"{k}: the key is not case_id/fit_id")
        # components (W15-1): case_id/fit_id/model_id, unique across the inventory
        for c in e["components"]:
            if c["key"] != f"{k}/{c['model_id']}":
                out.append(f"{k}: component key {c['key']!r} is not entry/model_id")
            if c["key"] in comp_seen:
                out.append(f"component key {c['key']!r} repeats (in {comp_seen[c['key']]} and {k})")
            comp_seen[c["key"]] = k
        out += _attributes(e)
        out += _tier_block(e, cuts)
        out += _lifecycle(e)
        out += _schedule(e, freq)
    out += _graph(doc, keys)
    out += _completeness(doc)
    # tier counts per reading
    for rec in doc["tier_counts"]:
        idx = [r["reading"] for r in entries[0]["tier_block"]["tier_sensitivity"]].index(rec["reading"])
        want = [sum(1 for e in entries if e["tier_block"]["tier_sensitivity"][idx]["tier"] == t) for t in (1, 2, 3, 4)]
        if rec["counts"] != want:
            out.append(f"tier_counts of reading {rec['reading']} is {rec['counts']}, the entries give {want}")
    g = {f["id"]: f for f in doc["governance_findings"]}
    for gid, sev in (("GOV-RUBRIC-BLIND-SPOT", "S3"), ("GOV-INDEPENDENCE-NOT-ESTABLISHED", "S2")):
        if gid not in g:
            out.append(f"governance_findings lacks {gid}")
        elif g[gid]["severity"] != sev:
            out.append(f"{gid} is {g[gid]['severity']}, the decision gives {sev}")
    for f in doc["governance_findings"]:
        if ECB_F[f["severity"]] != f["ecb_f"]:
            out.append(f"governance finding {f['id']}: ecb_f is {f['ecb_f']} for {f['severity']}")
    out += convention_violations(doc)
    return out


def as_of_violations(doc: dict, name: str, dates: list[str]) -> list[str]:
    """W15-13: the as-of date carries its basis labelled convention and is never earlier than the newest raised date it ages."""
    out = []
    basis = doc["as_of_basis"]
    if basis["label"] != "convention" or not basis["basis"]["en"].strip() or not basis["basis"]["es"].strip():
        out.append(f"{name}: as_of_basis must be labelled convention with its basis in both languages")
    newest = max(dates, default=None)
    if newest is not None and iso(doc["as_of"]) < iso(newest):
        out.append(f"{name}: as_of {doc['as_of']} is earlier than the newest raised date {newest}")
    return out


def _attributes(e: dict) -> list[str]:
    out = []
    k = e["key"]
    attrs = e["attributes"]
    if list(attrs) != ATTR_IDS:
        out.append(f"{k}: the attributes are not A01 to A40 in order")
        return out
    for aid, a in attrs.items():
        st, basis = a["status"], a["basis"]
        if st not in ATTR_STATUSES:
            out.append(f"{k} {aid}: unknown status {st!r}")
        if st == "present" and not POINTER.search(basis):
            out.append(f"{k} {aid}: status present without a pointer (a path#/pointer in the basis)")
        if st == "not-applicable" and len(basis.strip()) < 8:
            out.append(f"{k} {aid}: status not-applicable without a reason")
        if st in ("missing", "not-applicable") and a["value"] is not None:
            out.append(f"{k} {aid}: status {st} holds a value (an absent attribute holds none, never an invented one)")
        if st in ("derivable", "convention") and not basis.strip():
            out.append(f"{k} {aid}: status {st} without a basis")
    # SDD non-goal 1: Contraste approves no model, so there is no approver and no approval date
    for aid in ("A32", "A33"):
        a = attrs[aid]
        if a["value"] is not None or a["status"] != "not-applicable":
            out.append(f"{k} {aid}: an approval date or approver with a value or a status other than not-applicable (SDD non-goal 1)")
        elif "Contraste approves no model" not in a["basis"]:
            out.append(f"{k} {aid}: the reason must say that Contraste approves no model")
    # the attributes that summarise a block agree with it
    tb = e["tier_block"]
    summaries = {
        "A07": e["lifecycle"]["state"], "A22": tb["materiality"]["m"]["graded"], "A23": tb["complexity"]["c"]["mean"], "A24": tb["tier"],
        "A35": e["schedule"]["next_review"],
    }
    for aid, want in summaries.items():
        if attrs[aid]["value"] != want:
            out.append(f"{k} {aid}: the value {attrs[aid]['value']!r} disagrees with the block it summarises ({want!r})")
    if isinstance(attrs["A34"]["value"], dict) and attrs["A34"]["value"].get("date") != e["schedule"]["last_validation"]["date"]:
        out.append(f"{k} A34: the date disagrees with the schedule's last validation")
    return out


def _tier_block(e: dict, cuts: list[float]) -> list[str]:
    out = []
    k = e["key"]
    tb = e["tier_block"]
    mat, cx = tb["materiality"], tb["complexity"]
    band = exposure_band(mat["exposure"]["share"], cuts)
    if mat["exposure"]["band"] != band:
        out.append(f"{k}: exposure band is {mat['exposure']['band']}, the share and the cut points give {band}")
    if mat["regulatory_use"]["literal"] < mat["regulatory_use"]["graded"]:
        out.append(f"{k}: literal regulatory use {mat['regulatory_use']['literal']} is below the graded {mat['regulatory_use']['graded']}")
    m = {r: max(band, mat["regulatory_use"][r], mat["decision_criticality"]["score"]) for r in ("literal", "graded")}
    if mat["m"] != m:
        out.append(f"{k}: M is {mat['m']}, max(band, regulatory use, decision criticality) gives {m}")
    ids = [f["id"] for f in cx["factors"]]
    if ids != [f"F{i}" for i in range(1, 8)]:
        out.append(f"{k}: the complexity factors are not F1 to F7 in order")
    scores = [f["score"] for f in cx["factors"] if f["score"] is not None]
    if not scores:
        out.append(f"{k}: no complexity factor is scored")
        return out
    if cx["scored"] != len(scores) or cx["sum"] != sum(scores):
        out.append(f"{k}: complexity scored/sum {cx['scored']}/{cx['sum']} disagree with the factors ({len(scores)}/{sum(scores)})")
    if abs(cx["mean"] - sum(scores) / len(scores)) > 0.006:
        out.append(f"{k}: complexity mean {cx['mean']} is not {sum(scores) / len(scores):.2f}")
    c = {"mean": c_mean(scores), "maximum": max(scores)}
    if cx["c"] != c:
        out.append(f"{k}: C is {cx['c']}, the factor scores give {c}")
    for f in cx["factors"]:
        if f["score"] is None and not f["basis"].strip():
            out.append(f"{k}: unscored factor {f['id']} without its reason")
    sens = tb["tier_sensitivity"]
    if [r["reading"] for r in sens] != list(READINGS):
        out.append(f"{k}: tier_sensitivity readings are not A, B, C, D")
    for r in sens:
        reg, agg = READINGS[r["reading"]]
        if (r["regulatory_use"], r["complexity"]) != (reg, agg):
            out.append(f"{k}: tier_sensitivity reading {r['reading']} states {r['regulatory_use']}/{r['complexity']}, not {reg}/{agg}")
        want_m, want_c = m[reg], c[agg]
        if (r["m"], r["c"]) != (want_m, want_c):
            out.append(f"{k}: tier_sensitivity reading {r['reading']} has M/C {r['m']}/{r['c']}, the scores give {want_m}/{want_c}")
        if r["tier"] != matrix_tier(want_m, want_c):
            out.append(f"{k}: tier_sensitivity reading {r['reading']} tier {r['tier']} is not the matrix of its scores ({matrix_tier(want_m, want_c)})")
    reg, agg = READINGS[tb["adopted_reading"]]
    computed = matrix_tier(m[reg], c[agg])
    if tb["computed_tier"] != computed:
        out.append(f"{k}: computed tier {tb['computed_tier']} is not the matrix of its scores under reading {tb['adopted_reading']} ({computed})")
    ov = tb["override"]
    if ov is None:
        if tb["tier"] != tb["computed_tier"]:
            out.append(f"{k}: tier {tb['tier']} differs from the computed tier {tb['computed_tier']} with no override")
    else:
        if not ov["rationale"].strip() or not ov["approver"].strip():
            out.append(f"{k}: an override needs a rationale and an approver, never silent")
        if tb["tier"] != ov["to_tier"]:
            out.append(f"{k}: tier {tb['tier']} is not the override's {ov['to_tier']}")
    return out


def _lifecycle(e: dict) -> list[str]:
    out = []
    k = e["key"]
    lc = e["lifecycle"]
    exc = lc["exception"]
    prev = None
    for t in lc["transitions"]:
        ok = t["to"] in B4.get(t["from"], [])
        if not ok and t["to"] == "in_use" and t["from"] in B4_PRE_VALIDATION and exc is not None:
            ok = True          # use before validation, with its exception record
        if not ok:
            out.append(f"{k}: lifecycle transition {t['from']} to {t['to']} is not allowed")
        if prev is not None and t["from"] != prev:
            out.append(f"{k}: lifecycle transition starts at {t['from']}, the previous one ended at {prev}")
        prev = t["to"]
    if lc["transitions"] and lc["state"] != lc["transitions"][-1]["to"]:
        out.append(f"{k}: lifecycle state {lc['state']} is not the last transition's {lc['transitions'][-1]['to']}")
    validated = any(t["to"] in ("approved", "approved_with_conditions") for t in lc["transitions"])
    if lc["state"] in B4_IN_USE and not validated and exc is None:
        out.append(f"{k}: lifecycle state {lc['state']} (in use) before validation without an exception record")
    return out


def _schedule(e: dict, freq: dict) -> list[str]:
    out = []
    k = e["key"]
    s = e["schedule"]
    row = freq.get(e["tier_block"]["tier"])
    if row is None:
        return out
    review, reval, mon = row["review_months"], row["revalidation_months"], row["monitoring_months"]
    if s["profile"] == "ecb":
        review, reval = min(review, 12), min(reval if reval is not None else 36, 36)
    last = iso(s["last_validation"]["date"])
    want = {"next_review": add_months(last, review).isoformat(),
            "next_full_revalidation": add_months(last, reval).isoformat() if reval is not None else None,
            "next_monitoring": add_months(last, mon).isoformat() if mon is not None else None}
    for field, w in want.items():
        if s[field] != w:
            out.append(f"{k}: schedule {field} is {s[field]}, the frequency table gives {w}")
    if s["review_kind"] != row["review_kind"]:
        out.append(f"{k}: schedule review_kind {s['review_kind']} is not the table's {row['review_kind']}")
    if (None in want.values()) != (s["null_reason"] is not None):
        out.append(f"{k}: schedule null_reason must be present exactly when a date is null")
    return out


def _graph(doc: dict, keys: list[str]) -> list[str]:
    out = []
    engine = doc["engine_node"]["key"]
    if engine in keys:
        out.append(f"the engine node key {engine!r} is also an entry key")
    pairs = []
    seen = set()
    for ed in doc["edges"]:
        u, d = ed["upstream"], ed["downstream"]
        bad = [x for x in (u, d) if x not in keys]
        if bad:
            out.append(f"edge {u} to {d}: unknown entry {bad}")
            continue
        if u == d:
            out.append(f"edge {u} to itself")
            continue
        if (u, d, ed["kind"]) in seen:
            out.append(f"edge {u} to {d} ({ed['kind']}) repeats")
        seen.add((u, d, ed["kind"]))
        pairs.append((u, d))
    for r in doc["related"]:
        bad = [x for x in (r["a"], r["b"]) if x not in keys]
        if bad:
            out.append(f"related link {r['a']} and {r['b']}: unknown entry {bad}")
    gens, left = topological(keys, sorted(set(pairs)))
    if left:
        out.append(f"the dependency graph has a cycle among {left}")
        return out
    depth = {k: i for i, layer in enumerate(gens) for k in layer}
    # depth is the longest path from a source: Kahn's generations give exactly that
    for e in doc["entries"]:
        k = e["key"]
        g = e["graph"]
        want = (depth[k], len({u for u, d in set(pairs) if d == k}), len({d for u, d in set(pairs) if u == k}))
        if (g["depth"], g["fan_in"], g["fan_out"]) != want:
            out.append(f"{k}: graph depth/fan_in/fan_out {(g['depth'], g['fan_in'], g['fan_out'])} are not the edges' {want}")
        if e["map"]["generation"] != depth[k]:
            out.append(f"{k}: map generation {e['map']['generation']} is not the depth {depth[k]}")
        a16 = e["attributes"]["A16"]["value"]
        if isinstance(a16, dict) and "upstream" in a16:
            up = sorted(u for u, d in set(pairs) if d == k)
            dn = sorted(d for u, d in set(pairs) if u == k)
            if (sorted(a16["upstream"]), sorted(a16.get("downstream", []))) != (up, dn):
                out.append(f"{k} A16: upstream/downstream disagree with the edges")
    return out


def _completeness(doc: dict) -> list[str]:
    out = []
    entries = doc["entries"]
    comp = doc["completeness"]
    if comp["entries"] != len(entries):
        out.append(f"completeness entries is {comp['entries']}, the inventory holds {len(entries)}")
    for aid in ATTR_IDS:
        want = {"present": 0, "derivable": 0, "convention": 0, "not_applicable": 0, "missing": 0}
        for e in entries:
            want[e["attributes"][aid]["status"].replace("-", "_")] += 1
        if comp["attributes"][aid] != want:
            out.append(f"completeness of {aid} is {comp['attributes'][aid]}, the entries give {want}")
    return out


# ------------------------------------------------------------------------------------------------------------------ the findings


def findings_violations(doc: dict) -> list[str]:
    out = []
    as_of = iso(doc["as_of"])
    conv = doc["conventions"]
    table = conv["deadline_days"]["rows"]
    if [r["severity"] for r in table] != SEVERITIES:
        out.append("the deadline table rows are not S1 to S4 in order")
        return out
    scale = {r["severity"]: r["ecb_f"] for r in conv["severity_scale"]["rows"]}
    if scale != ECB_F:
        out.append(f"the severity scale {scale} is not S1 F4, S2 F3, S3 F2, S4 F1")
    smap = {r["product"]: r["register"] for r in conv["status_map"]["rows"]}
    if smap != STATUS_MAP:
        out.append(f"the status map {smap} is not open to open, accepted to risk_accepted, closed to validated_closed")
    keys = [r["key"] for r in doc["rows"]]
    if len(set(keys)) != len(keys):
        out.append("register keys repeat")
    out += as_of_violations(doc, "findings", [r["raised"] for r in doc["rows"]])
    for r in doc["rows"]:
        k = r["key"]
        if k != f"{r['case_id']}/{r['variant_id']}/{r['id']}":
            out.append(f"{k}: the key is not case_id/variant_id/id")
        if r["ecb_f"] != ECB_F[r["severity"]]:
            out.append(f"{k}: ecb_f {r['ecb_f']} is not {ECB_F[r['severity']]} for {r['severity']}")
        if r["status"] != STATUS_MAP[r["product_status"]]:
            out.append(f"{k}: status {r['status']} is not the mapped {STATUS_MAP[r['product_status']]} of {r['product_status']}")
        days = deadline(table, r["severity"], r["tier"])
        if r["deadline_days"] != days:
            out.append(f"{k}: deadline_days {r['deadline_days']} is not the table's {days} for {r['severity']} at tier {r['tier']}")
        raised = iso(r["raised"])
        if iso(r["due"]) != raised + timedelta(days=r["deadline_days"]):
            out.append(f"{k}: due {r['due']} is not raised {r['raised']} plus {r['deadline_days']} days")
        if r["ageing_days"] != (as_of - raised).days:
            out.append(f"{k}: ageing_days {r['ageing_days']} is not as_of minus raised ({(as_of - raised).days})")
        if raised > as_of:
            out.append(f"{k}: raised {r['raised']} is after as_of")
        if r["overdue"] != is_overdue(r["status"], iso(r["due"]), as_of):
            out.append(f"{k}: overdue flag {r['overdue']} disagrees with status {r['status']}, due {r['due']} and as_of {doc['as_of']}")
        if (r["status"] == "risk_accepted") != (r["risk_acceptance"] is not None):
            out.append(f"{k}: risk_acceptance must exist exactly when the status is risk_accepted")
        ra = r["risk_acceptance"]
        if ra is not None and (ra["approver"] != "not-applicable" or ra["expiry"] is not None):
            out.append(f"{k}: risk_acceptance holds an approver or an expiry: none exists for a stated limit of a synthetic case")
        if (r["anchor"] is None) != (r["anchor_reason"] is not None):
            out.append(f"{k}: anchor and anchor_reason must be null together with the reason, or an anchor with no reason")
        if r["rwea_share"] is not None:
            an = r["anchor"]
            if an is None or an["unit"] not in ("share-of-rwea", "rwea-amount"):
                out.append(f"{k}: rwea_share is set but the anchor is not stated as a share of RWEA or an RWEA amount")
            elif an["unit"] == "share-of-rwea" and not close(an["value"], r["rwea_share"]):
                out.append(f"{k}: rwea_share {r['rwea_share']} is not the anchor's value {an['value']}")
        if (r["rwea_share"] is None) != (r["rwea_share_reason"] is not None):
            out.append(f"{k}: rwea_share and its reason must be coupled")
        if (r["remediation"] is None) != (r["remediation_reason"] is not None):
            out.append(f"{k}: remediation and its reason must be coupled")
    out += _counts(doc)
    out += convention_violations(doc)
    return out


def _counts(doc: dict) -> list[str]:
    out = []
    rows = doc["rows"]
    c = doc["counts"]
    want_sev = {s: sum(1 for r in rows if r["severity"] == s) for s in SEVERITIES}
    want_st = {s: sum(1 for r in rows if r["status"] == s) for s in STATES_B7}
    if c["total"] != len(rows):
        out.append(f"counts total is {c['total']}, the register holds {len(rows)} rows")
    if c["by_severity"] != want_sev:
        out.append(f"counts by_severity is {c['by_severity']}, the rows give {want_sev}")
    if c["by_status"] != want_st:
        out.append(f"counts by_status is {c['by_status']}, the rows give {want_st}")
    if c["overdue"] != sum(1 for r in rows if r["overdue"]):
        out.append(f"counts overdue is {c['overdue']}, the rows give {sum(1 for r in rows if r['overdue'])}")
    cases = sorted({r["case_id"] for r in rows})
    if [x["case_id"] for x in c["by_case"]] != cases:
        out.append(f"counts by_case lists {[x['case_id'] for x in c['by_case']]}, the rows give {cases}")
    else:
        for x in c["by_case"]:
            sub = [r for r in rows if r["case_id"] == x["case_id"]]
            want = {"total": len(sub), "by_severity": {s: sum(1 for r in sub if r["severity"] == s) for s in SEVERITIES},
                    "by_status": {s: sum(1 for r in sub if r["status"] == s) for s in STATES_B7},
                    "overdue": sum(1 for r in sub if r["overdue"])}
            if {k: x[k] for k in want} != want:
                out.append(f"counts by_case {x['case_id']} does not recompute")
    return out


# ------------------------------------------------------------------------------------------------------------------ the reports


def report_violations(doc: dict) -> list[str]:
    out = []
    secs = doc["sections"]
    for i, s in enumerate(secs, 1):
        if s["number"] != i or s["key"] != SECTION_KEYS[i - 1]:
            out.append(f"section order: position {i} holds section {s['number']} ({s['key']})")
        if s["status"] == "filled":
            if not s["inputs"]:
                out.append(f"section {i}: filled without inputs")
            if not s["blocks"] or s["absent_reason"] is not None:
                out.append(f"section {i}: filled needs blocks and no absent_reason")
        elif s["absent_reason"] is None or not s["absent_reason"]["en"].strip() or s["blocks"]:
            out.append(f"section {i}: absent needs its reason and no blocks")
    if len(secs) == 12:
        op = secs[10]["opinion"]
        level = opinion_level(op["open_findings"])
        if op["level"] != level:
            out.append(f"opinion level is {op['level']}, the rule gives {level} for the open findings")
        if secs[0]["opinion_level"] != op["level"]:
            out.append("section 1 opinion_level disagrees with section 11")
        if op["recommendation"]["outcome"] != RECOMMENDATION[op["level"]]:
            out.append(f"recommendation {op['recommendation']['outcome']!r} is not the level {op['level']}'s {RECOMMENDATION[op['level']]!r}")
        if op["label"]["en"] != LABEL_EN:
            out.append("the recommendation label is not 'the rule's output on the evidence; Contraste approves no model'")
        if op["rwea_cut_points_applied"] != any(rwea_level(f.get("rwea_share")) > 0 for f in op["open_findings"]):
            out.append("opinion rwea_cut_points_applied disagrees with the open findings' anchors")
        outcomes = [b for b in secs[5]["blocks"] if b["kind"] == "outcomes"]
        if outcomes:
            want = {k: 0 for k in doc["test_counts"]}
            for r in outcomes[0]["rows"]:
                want[r["light"]] += 1
            if doc["test_counts"] != want:
                out.append(f"test_counts is {doc['test_counts']}, the outcomes rows give {want}")
    for s in secs:
        for bl in s["blocks"]:
            if bl["kind"] == "outcomes":
                for r in bl["rows"]:
                    if r["policy"]["source"] == "unresolved" and not r["policy"]["reason"]:
                        out.append(f"outcome {r['test_id']}: an unresolved policy needs its reason")
    return out


# ------------------------------------------------------------------------------------------------------------------ the appetite


def appetite_violations(doc: dict) -> list[str]:
    out = []
    if [m["id"] for m in doc["metrics"]] != METRIC_IDS:
        out.append("metrics are not the seven of B.6 in order")
    for m in doc["metrics"]:
        t = m["threshold"]
        i = m["id"]
        if t["label"] != "convention":
            out.append(f"{i}: the threshold is labelled {t['label']!r}, it is a convention")
        num, den, val = m["numerator"], m["denominator"], m["value"]
        if (i in ("open-high-severity", "overdue-remediation")) != (m["register_rows"] is not None):
            out.append(f"{i}: register_rows is the row count behind a distinct-finding count metric, and only those carry it")
        if m["register_rows"] is not None and num is not None and m["register_rows"] < num:
            out.append(f"{i}: register_rows {m['register_rows']} is below the {num} distinct findings")
        if val is not None:
            if m["unit"] == "count":
                ok = num is not None and close(val, num)
            else:
                ok = num is not None and den not in (None, 0) and close(val, num / den)
            if not ok:
                out.append(f"{i}: value {val} is not numerator over denominator ({num}/{den})")
        if m["light"] != light(val, t["direction"], t["green_limit"], t["amber_limit"]):
            out.append(f"{i}: light {m['light']} disagrees with the value {val} under the stated threshold")
    out += convention_violations(doc)
    return out


# ------------------------------------------------------------------------------------------------------------------ dispatch


def violations(doc: dict) -> list[str]:
    """The messages of one governance document (empty when it conforms)."""
    gid = doc.get("governance_id")
    fn = {"inventory": inventory_violations, "findings": findings_violations, "report": report_violations, "appetite": appetite_violations}.get(gid)
    if fn is None:
        return [f"unknown governance_id {gid!r}"]
    try:
        return fn(doc) + text_violations(doc)
    except (KeyError, TypeError, IndexError, ValueError, StopIteration) as exc:   # a document the schema refuses may lack what a rule reads
        return [f"malformed {gid} document: {type(exc).__name__} {exc}"]


def cross_violations(docs: dict) -> list[str]:
    """What must agree between the documents of one bake."""
    out: list[str] = []
    inv, fnd, app, reports = docs["inventory"], docs["findings"], docs["appetite"], docs["reports"]
    entries = {e["key"]: e for e in inv["entries"]}
    as_of = inv["as_of"]
    for name, d in (("findings", fnd), ("appetite", app), *((f"report {k}", r) for k, r in reports.items())):
        if d["as_of"] != as_of:
            out.append(f"{name}: as_of {d['as_of']} differs from the inventory's {as_of}")
    for r in fnd["rows"]:
        e = entries.get(r["entry_key"])
        if e is None:
            out.append(f"{r['key']}: entry_key {r['entry_key']} is not an inventory entry")
            continue
        if r["tier"] != e["tier_block"]["tier"]:
            out.append(f"{r['key']}: tier {r['tier']} is not the entry's tier {e['tier_block']['tier']}")
        if r["variant_id"] not in [v["variant_id"] for v in e["variants"]]:
            out.append(f"{r['key']}: variant {r['variant_id']} is not in the variants of entry {r['entry_key']}")
        if r["owner_role"] != e["attributes"]["A28"]["value"]:
            out.append(f"{r['key']}: owner_role differs from the entry's owner (A28)")
    for k, e in entries.items():
        rows = [r for r in fnd["rows"] if r["entry_key"] == k]
        a37 = e["attributes"]["A37"]["value"]
        want = {s: sum(1 for r in rows if r["severity"] == s and r["status"] in OPEN_STATES) for s in SEVERITIES}
        if isinstance(a37, dict) and a37 != want:
            out.append(f"{k} A37: open findings by severity {a37} differ from the register's {want}")
        due = sorted(r["due"] for r in rows if r["status"] in OPEN_STATES)
        a38 = e["attributes"]["A38"]["value"]
        if isinstance(a38, dict) and a38.get("earliest_due") != (due[0] if due else None):
            out.append(f"{k} A38: earliest due {a38.get('earliest_due')} differs from the register's {due[0] if due else None}")
    for k, rep in reports.items():
        if rep["entry_key"] != k or k not in entries:
            out.append(f"report {k}: its entry_key {rep['entry_key']} is not the inventory entry")
            continue
        if rep["tier"] != entries[k]["tier_block"]["tier"]:
            out.append(f"report {k}: tier {rep['tier']} is not the entry's {entries[k]['tier_block']['tier']}")
        listed = {f["key"]: (f["severity"], f["rwea_share"]) for f in rep["sections"][10]["opinion"]["open_findings"]}
        want_rows = {r["key"]: (r["severity"], r["rwea_share"]) for r in fnd["rows"] if r["entry_key"] == k and r["status"] in OPEN_STATES}
        if listed != want_rows:
            differ = sorted(x for x in set(listed) | set(want_rows) if listed.get(x) != want_rows.get(x))
            out.append(f"report {k}: the opinion's open findings differ from the register's open findings (severity or rwea_share) at {differ[:5]}"
                       f" ({len(listed)} listed against {len(want_rows)})")
    out += _appetite_cross(inv, fnd, app)
    return out


#: the phrase an appetite metric's threshold basis carries when its count includes the inventory's own findings
OWN_FINDINGS_NOTE = "includes the inventory's own findings"


def _distinct(rows: list[dict], pick) -> tuple[int, int]:
    """(distinct (entry, id) findings with a row that ``pick`` selects, rows that ``pick`` selects)."""
    sel = [r for r in rows if pick(r)]
    return len({(r["entry_key"], r["id"]) for r in sel}), len(sel)


def _appetite_cross(inv: dict, fnd: dict, app: dict) -> list[str]:
    out = []
    entries = inv["entries"]
    rows = list(fnd["rows"])
    if any(OWN_FINDINGS_NOTE in m["threshold"]["basis"] for m in app["metrics"]):
        # the appetite counts the inventory's own findings (W15-3, W15-4) beside the register rows, and says so in the basis of the metrics that count findings
        rows += [{"entry_key": "GOVERNANCE", "id": f["id"], "severity": f["severity"], "status": f["status"], "overdue": False}
                 for f in inv["governance_findings"]]
    as_of = iso(inv["as_of"])
    t1 = [e for e in entries if e["tier_block"]["tier"] == 1]
    pma = [e["attributes"]["A26"]["value"] for e in entries if e["attributes"]["A26"]["status"] == "present"]
    complete = [e for e in entries if e["attributes"]["A28"]["status"] in ("present", "derivable", "convention")
                and all(a["status"] != "missing" for a in e["attributes"].values())]
    distinct_all = len({(r["entry_key"], r["id"]) for r in rows})
    high, high_rows = _distinct(rows, lambda r: r["status"] in OPEN_STATES and r["severity"] in ("S1", "S2"))
    over, over_rows = _distinct(rows, lambda r: r["overdue"])
    want = {
        "tier1-validated-on-time": (sum(1 for e in t1 if iso(e["schedule"]["next_review"]) >= as_of), len(t1), None),
        "open-high-severity": (high, distinct_all, high_rows),
        "overdue-remediation": (over, distinct_all, over_rows),
        "entries-under-exception": (sum(1 for e in entries if e["lifecycle"]["exception"]), len(entries), None),
        "entries-in-breach": (sum(1 for e in entries if e["attributes"]["A36"]["value"]["red"] > 0), len(entries), None),
        "pma-magnitude": (sum(p["overlays_total"] for p in pma), sum(p["model_output"] for p in pma), None) if pma else (None, None, None),
        "owner-and-complete-record": (len(complete), len(entries), None),
    }
    pop = {"entries": len(entries), "findings": len(rows), "distinct_findings": distinct_all, "tier1_entries": len(t1)}
    if app["population"] != pop:
        out.append(f"appetite population {app['population']} differs from the documents' {pop}")
    for m in app["metrics"]:
        n, d, rr = want[m["id"]]
        if (m["numerator"], m["denominator"]) != (n, d) and not (
                m["numerator"] is not None and n is not None and close(m["numerator"], n) and close(m["denominator"], d)):
            out.append(f"appetite {m['id']}: numerator/denominator {(m['numerator'], m['denominator'])} differ from the documents' {(n, d)}")
        if m["register_rows"] != rr:
            out.append(f"appetite {m['id']}: register_rows {m['register_rows']} differs from the register's {rr}")
    return out


# the schema properties whose value a rule of this file recomputes: (schema file, $defs name or None for the root, property). The test holds each to
# the engine function named in the property's description, so a recomputed field that names none fails (m6).
RECOMPUTED = [
    ("governance-inventory", "invExposure", "band"), ("governance-inventory", "invMateriality", "m"), ("governance-inventory", "invComplexity", "scored"),
    ("governance-inventory", "invComplexity", "sum"), ("governance-inventory", "invComplexity", "mean"), ("governance-inventory", "invComplexity", "c"),
    ("governance-inventory", "invTier", "computed_tier"), ("governance-inventory", "invTier", "tier"),
    ("governance-inventory", "invTier", "tier_sensitivity"), ("governance-inventory", "invSchedule", "next_review"),
    ("governance-inventory", "invSchedule", "next_full_revalidation"), ("governance-inventory", "invSchedule", "next_monitoring"),
    ("governance-inventory", "invGraph", "depth"), ("governance-inventory", "invGraph", "fan_in"), ("governance-inventory", "invGraph", "fan_out"),
    ("governance-inventory", "invMap", "generation"), ("governance-inventory", None, "completeness"), ("governance-inventory", None, "tier_counts"),
    ("governance-inventory", "invAttributes", "A07"), ("governance-inventory", "invAttributes", "A22"), ("governance-inventory", "invAttributes", "A23"),
    ("governance-inventory", "invAttributes", "A24"), ("governance-inventory", "invAttributes", "A35"), ("governance-inventory", "invAttributes", "A37"),
    ("governance-inventory", "invAttributes", "A38"),
    ("governance-findings", "fndRow", "ecb_f"), ("governance-findings", "fndRow", "status"), ("governance-findings", "fndRow", "deadline_days"),
    ("governance-findings", "fndRow", "due"), ("governance-findings", "fndRow", "ageing_days"), ("governance-findings", "fndRow", "overdue"),
    ("governance-findings", "fndRow", "rwea_share"), ("governance-findings", None, "counts"),
    ("governance-report", "repOpinion", "level"), ("governance-report", "repOpinion", "rwea_cut_points_applied"),
    ("governance-report", "repOpinion", "recommendation"), ("governance-report", "repOpenFinding", "rwea_share"),
    ("governance-report", None, "test_counts"),
    ("governance-appetite", "appMetric", "value"), ("governance-appetite", "appMetric", "light"), ("governance-appetite", "appMetric", "numerator"),
    ("governance-appetite", "appMetric", "denominator"), ("governance-appetite", "appMetric", "register_rows"), ("governance-appetite", None, "population"),
]
