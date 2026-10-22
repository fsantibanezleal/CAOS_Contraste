"""U15-S: the governance contracts (the model inventory with its tiering, the findings register, the validation reports and the model risk
appetite), their fixtures, the catalog rows and the engine governance API contract.

The four documents sit in data/derived/governance/ (not variant envelopes): each carries a ``governance_id`` const, a ``schema_version``, the
committed ``as_of`` date and a provenance with the sha256 of every case document read. The fixtures validate by discovery
(tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict both ways; the cross-field rules JSON Schema cannot
state are importable functions in ``semantics.py`` that the governance bake (U15-P) calls on every document it writes. These tests run them
over the fixtures and over a table of planted defects, each refused by the layer the table says (the schema or the checker). The engine
contract names every function of the modules table of plans/contraste/units/U15-sizing.md with a signature, units, an invariant or a golden
value; the goldens recompute here from formulas typed again in this file (the tiers of the 19 built cases come from the inputs of the U15
research addendum, D2, by a function written here and not imported from the checker). The fixtures are labelled as fixtures and never
published as results.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

import pytest

import contract_schemas as cs

ROOT = cs.ROOT
FIX = ROOT / "docs" / "contracts" / "fixtures" / "governance"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas" / "governance"
API = ROOT / "docs" / "contracts" / "engine" / "governance-api.md"
_ROWS = ROOT / "docs" / "contracts" / "rows" / "U15.md"
ROWS_FRAGMENT = _ROWS if _ROWS.is_file() else Path(__file__).parent / "rows-fragment-merged.md"  # merged at the wave 3 integration
CHANGES = ROOT / "changes" / "U15-S.md"
EXTRACT = Path(__file__).parent / "snapshots" / "source-extract.json"
THIS = Path(__file__)

INV, FND, APP = "governance/governance-inventory", "governance/governance-findings", "governance/governance-appetite"
REP = "governance/governance-report"
FILES = {
    "inventory": (INV, FIX / "inventory-fixture.json"),
    "findings": (FND, FIX / "findings-fixture.json"),
    "appetite": (APP, FIX / "appetite-fixture.json"),
    "report-C07": (REP, FIX / "report-C07-banco-andino-fixture.json"),
    "report-C18": (REP, FIX / "report-C18-banco-andino-fixture.json"),
}
ENTRY_KEYS = ["C01/german", "C07/banco-andino", "C18/banco-andino", "C22/generators"]
REPORT_KEYS = {"report-C07": "C07/banco-andino", "report-C18": "C18/banco-andino"}
SEVERITIES = ["S1", "S2", "S3", "S4"]
STATES_B7 = ["open", "action_plan_agreed", "in_progress", "submitted_for_closure", "validated_closed", "overdue", "risk_accepted"]
OPEN_STATES = ["open", "action_plan_agreed", "in_progress", "submitted_for_closure", "overdue"]
LABEL_EN = "the rule's output on the evidence; Contraste approves no model"


def sm():
    """The checker module, imported when a test needs it (the contract tests read committed JSON and call it by name)."""
    import semantics
    return semantics


def load(key: str) -> Any:
    return cs.load_json(FILES[key][1])


def all_docs() -> dict:
    return {"inventory": load("inventory"), "findings": load("findings"), "appetite": load("appetite"),
            "reports": {REPORT_KEYS[k]: load(k) for k in REPORT_KEYS}}


def entry_of(inv: dict, key: str) -> dict:
    return next(e for e in inv["entries"] if e["key"] == key)


# --- an independent copy of the rules, typed again here from dossier 06 and the research addendum (never imported from semantics.py) ------


def band(share: float | None, cuts: tuple[float, float, float] = (0.25, 0.10, 0.02)) -> int:
    if share is None:
        return 1
    return 4 if share >= cuts[0] else 3 if share >= cuts[1] else 2 if share >= cuts[2] else 1


def matrix(m: int, c: int) -> int:
    """06 B.3 l.571-574."""
    if m == 4 or (m == 3 and c >= 3):
        return 1
    if m == 3 or (m == 2 and c >= 3):
        return 2
    if m == 2 or (m == 1 and c >= 3):
        return 3
    return 4


def c_mean(scores: list[int]) -> int:
    """The mean rounded half up, in integers (06 l.567; the rounding is a named argument of the engine)."""
    return (2 * sum(scores) + len(scores)) // (2 * len(scores))


def months(d: date, n: int) -> date:
    y, mo = divmod(d.year * 12 + d.month - 1 + n, 12)
    mo += 1
    last = [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
    return date(y, mo, min(d.day, last))


def iso(s: str) -> date:
    return date.fromisoformat(s)


# The inputs of A D2 (sections 3.2 and 3.3 of the U15 research addendum): case -> (exposure share or None, regulatory use literal, graded,
# decision criticality, the six factor scores F1 to F6) and the tiers A to D of its table 3.4.
A_D2 = {
    "C01": (0.0531, 4, 3, 3, [4, 2, 3, 1, 1, 1], (1, 2, 1, 1)),
    "C03": (0.2162, 4, 3, 1, [3, 2, 3, 1, 1, 1], (1, 2, 1, 1)),
    "C04": (0.3243, 4, 3, 1, [2, 2, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C05": (0.3243, 4, 3, 1, [2, 2, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C06": (1.0, 4, 4, 1, [2, 2, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C07": (1.0, 4, 4, 1, [2, 1, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C08": (0.2162, 4, 3, 1, [3, 2, 3, 1, 1, 1], (1, 2, 1, 1)),
    "C09": (0.0531, 4, 3, 1, [1, 1, 1, 1, 1, 1], (1, 2, 1, 2)),
    "C10": (0.7084, 4, 3, 1, [2, 2, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C11": (0.1713, 4, 3, 1, [2, 2, 1, 4, 1, 1], (1, 2, 1, 1)),
    "C12": (None, 4, 4, 1, [2, 2, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C13": (0.1713, 4, 3, 1, [2, 1, 1, 1, 1, 1], (1, 2, 1, 2)),
    "C14": (1.0, 4, 4, 1, [2, 2, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C15": (1.0, 4, 4, 1, [2, 2, 1, 1, 2, 1], (1, 1, 1, 1)),
    "C16": (1.0, 4, 4, 1, [1, 2, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C17": (0.1203, 4, 4, 1, [2, 1, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C18": (1.0, 4, 4, 1, [2, 2, 1, 1, 4, 1], (1, 1, 1, 1)),
    "C21": (0.3456, 2, 2, 3, [2, 2, 1, 1, 1, 1], (1, 1, 1, 1)),
    "C22": (None, 1, 1, 1, [2, 1, 1, 1, 1, 1], (4, 4, 4, 4)),
}
A_D2_COUNTS = {0: [18, 0, 0, 1], 1: [12, 6, 0, 1], 2: [18, 0, 0, 1], 3: [16, 2, 0, 1]}   # table 3.4, last row
READINGS = [("A", "literal", "mean"), ("B", "graded", "mean"), ("C", "literal", "maximum"), ("D", "graded", "maximum")]


def tiers_of(case: str) -> tuple[int, int, int, int]:
    share, lit, grd, dec, scores, _ = A_D2[case]
    b = band(share)
    out = []
    for _, reg, agg in READINGS:
        m = max(b, lit if reg == "literal" else grd, dec)
        c = c_mean(scores) if agg == "mean" else max(scores)
        out.append(matrix(m, c))
    return tuple(out)  # type: ignore[return-value]


# --- the fixtures -----------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", list(FILES))
def test_the_fixture_exists_and_is_discovered_by_exactly_one_schema(key: str) -> None:
    ref, path = FILES[key]
    assert path.is_file(), path
    doc = cs.load_json(path)
    assert cs.schema_for_document(path, doc) == ref
    assert cs.errors(ref, doc) == []
    passing = [c.ref for c in cs.candidates() if cs.errors(c.ref, doc) == []]
    assert passing == [ref], f"{path.name}: validates against {passing}"


@pytest.mark.parametrize("key", list(FILES))
def test_the_fixture_is_labelled_as_a_fixture_and_carries_the_governance_header(key: str) -> None:
    ref, _ = FILES[key]
    doc = load(key)
    assert doc["case_id"] == "GOVERNANCE" and doc["schema"] == f"contraste.{ref.split('/')[1].replace('governance-', 'governance.')}/v1"
    assert doc["governance_id"] == ref.split("/")[1].removeprefix("governance-")
    assert doc["schema_version"] == "1.0.0"
    assert doc["provenance"]["generators"] == ["fixture:u15-s-contracts"]
    assert doc["provenance"]["documents_read"], "the sha256 of every case document read"
    assert all(re.fullmatch(r"[0-9a-f]{64}", d["sha256"]) for d in doc["provenance"]["documents_read"])
    assert doc["as_of"] == "2026-12-31"
    basis = doc["as_of_basis"]
    assert basis["label"] == "convention" and "to exercise the overdue rule" in basis["basis"]["en"] and "not the date of publication" in basis["basis"]["en"]
    assert basis["basis"]["es"].strip() and "no es la fecha de publicación" in basis["basis"]["es"]
    for d in doc["provenance"]["documents_read"]:      # every case document is read from the branch the bake runs on (0.13.000)
        assert d["ref"] is None, d["path"]


def test_every_schema_is_a_closed_object_with_a_governance_id_const_and_the_governance_case_id() -> None:
    for ref in (INV, FND, REP, APP):
        s = cs.load_json(SCHEMAS / f"{ref.split('/')[1]}.schema.json")
        assert s["additionalProperties"] is False
        assert s["properties"]["case_id"] == {"const": "GOVERNANCE"}
        assert s["properties"]["governance_id"]["const"] == ref.split("/")[1].removeprefix("governance-")
        assert {"as_of", "provenance", "schema_version"} <= set(s["required"])
    assert cs.case_folder_violations() == []


@pytest.mark.parametrize("key", list(FILES))
def test_the_fixture_passes_the_semantic_checker(key: str) -> None:
    assert sm().violations(load(key)) == []


def test_the_fixtures_pass_the_cross_document_checks() -> None:
    assert sm().cross_violations(all_docs()) == []


@pytest.mark.parametrize("key", list(FILES))
def test_a_removed_or_an_added_key_fails_the_schema(key: str) -> None:
    ref, _ = FILES[key]
    doc = load(key)
    for k in doc:
        broken = {x: v for x, v in doc.items() if x != k}
        assert cs.errors(ref, broken), f"{key}: removing {k} passes"
    assert cs.errors(ref, {**doc, "extra": 1}), f"{key}: an added key passes"


def test_the_fixture_holds_the_four_entries_and_their_fit_ids_come_from_the_committed_models_documents() -> None:
    inv = load("inventory")
    assert [e["key"] for e in inv["entries"]] == ENTRY_KEYS
    ex = cs.load_json(EXTRACT)
    for e in inv["entries"]:
        assert e["fit_id"] == ex["cases"][e["case_id"]]["fit_id"]
        assert e["key"] == f"{e['case_id']}/{e['fit_id']}"
    assert ex["cases"]["C18"]["fit_id"] == "banco-andino"          # data/derived/C18/models-banco-andino.json


def test_the_provenance_hashes_are_the_sha256_of_the_committed_documents() -> None:
    inv = load("inventory")
    ex = cs.load_json(EXTRACT)
    read = {d["path"]: d["sha256"] for d in inv["provenance"]["documents_read"]}
    expected = {}
    for case in ex["cases"].values():
        expected[case["manifest"]["path"]] = case["manifest"]["sha256"]
        expected[case["models_document"]["path"]] = case["models_document"]["sha256"]
        for v in case["variants"]:
            expected[v["path"]] = v["sha256"]
    assert read == expected
    import hashlib
    for path, sha in read.items():
        local = ROOT / path
        if local.is_file():
            assert hashlib.sha256(local.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == sha, path


def test_every_cited_pointer_resolves_in_a_committed_document() -> None:
    ex = cs.load_json(EXTRACT)
    verified = {p for c in ex["cases"].values() for p in c["verified_pointers"]}
    inv = load("inventory")
    cited = set()
    for e in inv["entries"]:
        for a in e["attributes"].values():
            if a["status"] == "present":
                cited.update(re.findall(r"\S+#/\S*", a["basis"]))
    assert cited and cited <= verified, sorted(cited - verified)


# --- the 40 B.2 attributes and the A D1 statuses --------------------------------------------------------------------------------------

ATTRIBUTES = [
    "model ID", "name", "version", "description", "model type", "origin", "status", "purpose", "products and portfolios",
    "intended use vs actual use", "approved uses", "restrictions on use", "model operating boundaries", "input data sources",
    "alternative or unstructured data flag", "upstream and downstream model dependencies", "outputs and their intended use", "methodology",
    "assumptions and limitations", "use of ML", "dynamic or self-updating flag", "materiality rating", "complexity rating", "tier",
    "explainability rating", "PMAs in force", "exceptions to policy", "owner", "developer", "users", "validator", "approver",
    "approval date and authority", "last validation date and type", "next validation date", "monitoring status", "open findings by severity",
    "remediation due dates", "expected validity", "decommission date and rationale",
]
# What A D1 says for the fixture cases (P present, D derivable, M missing in the committed documents), by attribute number, with the cases the
# table lists as lacking it; a status the inventory states by convention or as not applicable replaces a missing one, never a present one.
D1_PRESENT = {1, 2, 4, 5, 8, 14, 17, 18}
D1_DERIVABLE = {3, 6, 7, 20, 29, 31, 34, 36}
D1_MISSING = {10, 11, 12, 15, 21, 25, 27, 30, 39, 40}
D1_COMPUTED = {22, 23, 24, 35, 38}         # missing in the documents, computed by the engine from the tiering and the register (D2, D3)
D1_LACKING = {  # attribute -> cases of the fixture that lack it (A D1 "Cases that lack it" column)
    9: {"C01", "C22"}, 13: {"C07", "C22"}, 16: {"C01", "C07", "C22"}, 19: {"C01", "C07", "C22"}, 26: {"C01", "C18", "C22"},
}


def test_the_forty_attributes_each_an_object_with_a_value_a_status_and_a_basis() -> None:
    inv = load("inventory")
    for e in inv["entries"]:
        assert list(e["attributes"]) == [f"A{i:02d}" for i in range(1, 41)]
        for a in e["attributes"].values():
            assert set(a) == {"value", "status", "basis"}
            assert a["status"] in ("present", "derivable", "convention", "not-applicable", "missing")
            assert a["basis"].strip()
    assert len(ATTRIBUTES) == 40


def test_the_attribute_statuses_follow_the_addendum_d1_table() -> None:
    inv = load("inventory")
    for e in inv["entries"]:
        for i in range(1, 41):
            st = e["attributes"][f"A{i:02d}"]["status"]
            if i in D1_PRESENT:
                assert st == "present", (e["key"], i, st)
            elif i in D1_DERIVABLE:
                assert st == "derivable", (e["key"], i, st)
            elif i in D1_MISSING:
                assert st in ("missing", "not-applicable", "convention"), (e["key"], i, st)
            elif i in D1_LACKING:
                if e["case_id"] in D1_LACKING[i]:
                    assert st in ("missing", "not-applicable", "convention", "derivable"), (e["key"], i, st)
                else:
                    assert st in ("present", "derivable"), (e["key"], i, st)
            elif i in D1_COMPUTED:
                assert st in ("convention", "derivable"), (e["key"], i, st)
    # A32 and A33: no approver and no approval date, because Contraste approves no model (W15-4, SDD non-goal 1)
    for e in inv["entries"]:
        for n in ("A32", "A33"):
            a = e["attributes"][n]
            assert a["status"] == "not-applicable" and a["value"] is None and "Contraste approves no model" in a["basis"]


def test_the_owner_is_a_synthetic_role_the_developer_the_module_and_the_validator_the_engine() -> None:
    inv = load("inventory")
    for e in inv["entries"]:
        owner, dev, val = (e["attributes"][k] for k in ("A28", "A29", "A31"))
        assert owner["status"] == "convention" and "synthetic" in owner["value"] and "W15-4" in owner["basis"]
        assert dev["status"] == "derivable" and dev["value"].startswith("data-pipeline/pipeline/cases/")
        assert val["status"] == "derivable" and val["value"].startswith("riskvalidation ")
        assert "independence" in val["basis"]
    assert entry_of(inv, "C22/generators")["attributes"]["A31"]["basis"].count("exact") >= 1   # the validator of the validator, W15-4


def release_dates() -> dict[str, str]:
    """Code version -> release date, from the headings of CHANGELOG.md (A D1 A34)."""
    log = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return dict(re.findall(r"(?m)^## \[(\d\.\d\d\.\d\d\d)\], (\d{4}-\d\d-\d\d)$", log))


def test_the_attribute_values_equal_the_committed_facts_of_the_extract() -> None:
    inv = load("inventory")
    ex = cs.load_json(EXTRACT)
    for e in inv["entries"]:
        c = ex["cases"][e["case_id"]]
        assert e["attributes"]["A01"]["value"] == e["key"]
        assert e["attributes"]["A02"]["value"] == c["manifest"]["title"]
        assert e["attributes"]["A04"]["value"] == c["manifest"]["question"]
        assert e["attributes"]["A34"]["value"]["date"] == release_dates()[c["models_document"]["code_version"]]
        assert [x["model_id"] for x in e["components"]] == [m["id"] for m in c["models_document"]["models"]]
    pma = entry_of(inv, "C07/banco-andino")["attributes"]["A26"]
    assert pma["status"] == "present" and pma["value"]["overlays_total"] == ex["cases"]["C07"]["pma"]["overlays_total"]


# --- the tier block: A D2 from its stated inputs -----------------------------------------------------------------------------------------


def test_the_addendum_d2_tiers_recompute_from_the_stated_inputs_by_a_function_written_here() -> None:
    for case, row in A_D2.items():
        assert tiers_of(case) == row[5], case
    for i in range(4):
        counts = [sum(1 for case in A_D2 if tiers_of(case)[i] == t) for t in (1, 2, 3, 4)]
        assert counts == A_D2_COUNTS[i], (i, counts)


def test_the_fixture_tier_blocks_are_the_addendum_values_and_recompute() -> None:
    inv = load("inventory")
    for e in inv["entries"]:
        share, lit, grd, dec, scores, expected = A_D2[e["case_id"]]
        tb = e["tier_block"]
        mat, cx = tb["materiality"], tb["complexity"]
        assert mat["exposure"]["share"] == share and mat["exposure"]["band"] == band(share)
        assert (mat["regulatory_use"]["literal"], mat["regulatory_use"]["graded"], mat["decision_criticality"]["score"]) == (lit, grd, dec)
        assert [f["score"] for f in cx["factors"][:6]] == scores and cx["factors"][6]["score"] is None
        assert cx["scored"] == 6 and cx["sum"] == sum(scores) and cx["mean"] == round(sum(scores) / 6, 2)
        assert (cx["c"]["mean"], cx["c"]["maximum"]) == (c_mean(scores), max(scores))
        assert [r["tier"] for r in tb["tier_sensitivity"]] == list(expected)
        assert [r["reading"] for r in tb["tier_sensitivity"]] == ["A", "B", "C", "D"]
        assert tb["adopted_reading"] == "B" and tb["computed_tier"] == expected[1] and tb["override"] is None and tb["tier"] == expected[1]
        for f in cx["factors"]:
            assert f["tag"] in ("doc", "convention") and f["basis"].strip()
    tiers = {e["case_id"]: e["tier_block"]["tier"] for e in inv["entries"]}
    assert tiers == {"C01": 2, "C07": 1, "C18": 1, "C22": 4}      # C22 keeps the tier its inputs give (W15-3)


def test_the_tier_counts_of_the_four_readings_recompute_over_the_fixture_entries() -> None:
    inv = load("inventory")
    for r, (name, _, _) in enumerate(READINGS):
        got = next(t for t in inv["tier_counts"] if t["reading"] == name)["counts"]
        assert got == [sum(1 for case in ("C01", "C07", "C18", "C22") if tiers_of(case)[r] == t) for t in (1, 2, 3, 4)]


def test_the_inventory_states_its_own_two_governance_findings() -> None:
    inv = load("inventory")
    g = {f["id"]: f for f in inv["governance_findings"]}
    assert g["GOV-RUBRIC-BLIND-SPOT"]["severity"] == "S3" and g["GOV-RUBRIC-BLIND-SPOT"]["ecb_f"] == "F2"       # W15-3
    assert g["GOV-INDEPENDENCE-NOT-ESTABLISHED"]["severity"] == "S2" and g["GOV-INDEPENDENCE-NOT-ESTABLISHED"]["ecb_f"] == "F3"   # W15-4


def test_the_edges_the_engine_node_and_the_excluded_list() -> None:
    inv = load("inventory")
    assert inv["engine_node"]["key"] == "riskvalidation"
    kinds = {(e["upstream"], e["downstream"]): e["kind"] for e in inv["edges"]}
    assert kinds == {("C07/banco-andino", "C18/banco-andino"): "document", ("C01/german", "C22/generators"): "code"}
    assert all(e["stated_source"].strip() for e in inv["edges"])
    assert {r["a"] + ">" + r["b"] for r in inv["related"]} == {"C22/generators>C01/german"}
    assert {x["case_id"] for x in inv["excluded"]} == {"C02", "C19", "C20"}
    depth = {e["key"]: (e["graph"]["depth"], e["graph"]["fan_in"], e["graph"]["fan_out"]) for e in inv["entries"]}
    assert depth == {"C01/german": (0, 0, 1), "C07/banco-andino": (0, 0, 1), "C18/banco-andino": (1, 1, 0), "C22/generators": (1, 1, 0)}


# --- the findings register -----------------------------------------------------------------------------------------------------------


def test_the_register_holds_every_finding_row_of_the_four_entries_with_the_committed_severity_and_status() -> None:
    fnd = load("findings")
    ex = cs.load_json(EXTRACT)
    expected = {}
    for case, c in ex["cases"].items():
        for v in c["variants"]:
            for f in v["findings"]:
                expected[f"{case}/{v['variant_id']}/{f['id']}"] = (f["severity"], f["status"])
    got = {r["key"]: (r["severity"], r["product_status"]) for r in fnd["rows"]}
    assert got == expected
    assert fnd["counts"]["total"] == len(expected)


def test_the_register_applies_the_decisions_w15_2_and_w15_5() -> None:
    fnd = load("findings")
    scale = {"S1": "F4", "S2": "F3", "S3": "F2", "S4": "F1"}
    mapped = {"open": "open", "accepted": "risk_accepted", "closed": "validated_closed"}
    ex = cs.load_json(EXTRACT)
    release = {case: release_dates()[c["models_document"]["code_version"]] for case, c in ex["cases"].items()}
    days = {"S1": [30, 45, 60, 90], "S2": [60, 90, 120, 180], "S3": [90, 120, 180, 270], "S4": [180, 270, 365, 365]}
    inv = load("inventory")
    tier = {e["key"]: e["tier_block"]["tier"] for e in inv["entries"]}
    as_of = iso(fnd["as_of"])
    for r in fnd["rows"]:
        assert r["ecb_f"] == scale[r["severity"]] and r["status"] == mapped[r["product_status"]]
        assert r["raised"] == release[r["case_id"]] and r["tier"] == tier[r["entry_key"]]
        assert r["deadline_days"] == days[r["severity"]][r["tier"] - 1]
        assert iso(r["due"]) == iso(r["raised"]) + timedelta(days=r["deadline_days"])
        assert r["ageing_days"] == (as_of - iso(r["raised"])).days
        assert r["overdue"] == (r["status"] in OPEN_STATES and as_of > iso(r["due"]))
        assert r["remediation"] is None and "no remediation plan" in r["remediation_reason"]["en"]
        assert r["rwea_share"] is None and r["rwea_share_reason"]["en"].strip()       # no committed anchor is a share of RWEA
        entry = entry_of(load("inventory"), r["entry_key"])
        assert r["variant_id"] in [v["variant_id"] for v in entry["variants"]]       # W15-15
        if r["status"] == "risk_accepted":
            ra = r["risk_acceptance"]
            assert ra["approver"] == "not-applicable" and ra["expiry"] is None and ra["approver_reason"]["en"] and ra["expiry_reason"]["en"]
        else:
            assert r["risk_acceptance"] is None
        if r["anchor"] is None:
            assert r["anchor_reason"] is not None
        else:
            assert r["anchor_reason"] is None and r["anchor"]["basis"].strip() and r["anchor"]["unit"].strip()
    assert any(r["overdue"] for r in fnd["rows"]) and any(not r["overdue"] and r["status"] == "open" for r in fnd["rows"])


def test_an_anchor_is_the_cited_test_rows_statistic_or_metric_and_null_with_its_reason_otherwise() -> None:
    fnd = load("findings")
    ex = cs.load_json(EXTRACT)
    anchored = 0
    for r in fnd["rows"]:
        v = next(x for x in ex["cases"][r["case_id"]]["variants"] if x["variant_id"] == r["variant_id"])
        cited = [e for e in r["evidence"] if re.fullmatch(r"[a-z0-9_.]+@[^@]+(@.+)?", e)]
        if not cited:
            assert r["anchor"] is None, r["key"]
            continue
        test_id, model_id = cited[0].split("@")[:2]
        rows = [t for t in v["tests"] if t["test_id"] == test_id and t["model_id"] == model_id]
        if r["anchor"] is None:
            assert not rows or all(t["statistic"] is None and t["metric"] is None for t in rows), r["key"]
        else:
            anchored += 1
            a = r["anchor"]
            assert (a["test_id"], a["model_id"]) == (test_id, model_id)
            assert any(a["value"] == (t[a["metric"]]) for t in rows), r["key"]
    assert anchored > 0


def test_the_counts_by_case_severity_and_status_recompute() -> None:
    fnd = load("findings")
    c = fnd["counts"]
    assert c["total"] == len(fnd["rows"]) == sum(c["by_severity"].values()) == sum(c["by_status"].values())
    assert c["overdue"] == sum(1 for r in fnd["rows"] if r["overdue"])
    assert {x["case_id"] for x in c["by_case"]} == {"C01", "C07", "C18", "C22"}
    for x in c["by_case"]:
        rows = [r for r in fnd["rows"] if r["case_id"] == x["case_id"]]
        assert x["total"] == len(rows) and x["by_severity"] == {s: sum(1 for r in rows if r["severity"] == s) for s in SEVERITIES}


# --- the reports ------------------------------------------------------------------------------------------------------------------------

SECTION_KEYS = ["executive_summary", "model_description", "conceptual_soundness", "data", "implementation", "outcomes_analysis",
                "sensitivity_robustness_stress", "ongoing_monitoring", "limitations_and_controls", "findings_register",
                "opinion_and_recommendation", "appendices"]
# A D5: the inputs each section names (a filled section names at least one of these kinds of input)
SECTION_INPUTS = {
    1: ["manifest", "findings", "test rows"], 2: ["models document", "inventory", "tier"], 3: ["models document", "Methodology"],
    4: ["manifest", "provenance"], 5: ["provenance", "seed"], 6: ["test rows"], 7: ["variant"], 8: ["PMA", "overlays"], 9: ["findings"],
    10: ["findings"], 11: ["opinion"], 12: ["provenance"],
}


@pytest.mark.parametrize("key", list(REPORT_KEYS))
def test_a_report_has_the_twelve_sections_in_order_each_filled_with_named_inputs_or_absent_with_its_reason(key: str) -> None:
    rep = load(key)
    assert rep["entry_key"] == REPORT_KEYS[key]
    assert [s["number"] for s in rep["sections"]] == list(range(1, 13))
    assert [s["key"] for s in rep["sections"]] == SECTION_KEYS
    for s in rep["sections"]:
        if s["status"] == "filled":
            assert s["inputs"] and s["blocks"] and s["absent_reason"] is None, s["key"]
            joined = " ".join(i["ref"] for i in s["inputs"]).lower()
            assert any(w.lower() in joined for w in SECTION_INPUTS[s["number"]]), (s["key"], joined)
        else:
            assert s["absent_reason"] and s["absent_reason"]["en"].strip() and not s["blocks"], s["key"]
    assert len({s["status"] for rr in ("report-C07", "report-C18") for s in load(rr)["sections"]}) == 2, "one absent section at least"


@pytest.mark.parametrize("key", list(REPORT_KEYS))
def test_section_11_holds_the_level_the_rule_and_the_labelled_recommendation(key: str) -> None:
    rep = load(key)
    s11, s1 = rep["sections"][10], rep["sections"][0]
    op = s11["opinion"]
    assert 1 <= op["level"] <= 4 and s1["opinion_level"] == op["level"]
    assert op["rule"]["id"] == "W15-7" and op["rule"]["text"]["en"].strip()
    assert op["label"]["en"] == LABEL_EN
    assert op["recommendation"]["outcome"] == {1: "approve", 2: "approve with conditions", 3: "remediate before use", 4: "remediate before use"}[op["level"]]
    assert "approved" not in op["recommendation"]["text"]["en"].lower().replace("approve", "")


def test_the_opinion_levels_are_the_rule_applied_to_the_open_findings_of_each_entry() -> None:
    fnd = load("findings")
    for key, expected in (("report-C07", 3), ("report-C18", 4)):
        rep = load(key)
        open_rows = [r for r in fnd["rows"] if r["entry_key"] == rep["entry_key"] and r["status"] in OPEN_STATES]
        worst = min((SEVERITIES.index(r["severity"]) for r in open_rows), default=None)
        level = 1 if worst is None else {0: 4, 1: 3}.get(worst, 2)
        assert rep["sections"][10]["opinion"]["level"] == level == expected
        assert {o["key"] for o in rep["sections"][10]["opinion"]["open_findings"]} == {r["key"] for r in open_rows}


def test_section_6_states_the_policy_identity_of_every_row_and_the_source_of_its_threshold() -> None:
    rep = load("report-C07")
    block = next(b for b in rep["sections"][5]["blocks"] if b["kind"] == "outcomes")
    ex = cs.load_json(EXTRACT)
    default = next(v for v in ex["cases"]["C07"]["variants"] if v["variant_id"] == "base")
    assert len(block["rows"]) == len(default["tests"]) == sum(rep["test_counts"].values())
    for row in block["rows"]:
        p = row["policy"]
        assert p["source"] in ("packaged-policy", "packaged-policy-overridden", "inline-battery", "unresolved")
        if p["source"] == "unresolved":
            assert p["reason"]
    assert any(r["policy"]["source"] == "inline-battery" and r["policy"]["parameters"] for r in block["rows"])
    decisions = ex["cases"]["C07"]["spec_decisions"]
    assert re.fullmatch(r"[0-9a-f]{40}", ex["engine_commit"])
    for row in block["rows"]:
        p = row["policy"]
        assert p["kind"] == decisions[row["test_id"]]                                  # spec(test_id).decision, None where unregistered
        assert (p["kind"] is None) == (p["kind_reason"] is not None)
        if p["source"] == "inline-battery":
            assert p["direction"] is None and p["direction_reason"] == "no policy file for an inline battery string"


# --- the appetite ------------------------------------------------------------------------------------------------------------------------

METRICS = ["tier1-validated-on-time", "open-high-severity", "overdue-remediation", "entries-under-exception", "entries-in-breach",
           "pma-magnitude", "owner-and-complete-record"]


def test_the_appetite_holds_the_seven_b6_metrics_with_value_unit_numerator_denominator_and_a_light_under_a_stated_threshold() -> None:
    app = load("appetite")
    assert [m["id"] for m in app["metrics"]] == METRICS
    for m in app["metrics"]:
        assert m["unit"] in ("share", "count", "share-of-model-output")
        t = m["threshold"]
        assert t["label"] == "convention" and t["basis"].strip() and t["direction"] in ("higher-is-better", "lower-is-better")
        if m["value"] is None:
            assert m["light"] == "not_evaluated" and m["reason"]
        elif m["denominator"]:
            assert m["unit"] != "count" or m["value"] == m["numerator"]
    assert {m["id"]: m["light"] for m in app["metrics"]}["tier1-validated-on-time"] == "green"


def test_the_appetite_recomputes_from_the_inventory_and_the_register() -> None:
    inv, fnd, app = load("inventory"), load("findings"), load("appetite")
    m = {x["id"]: x for x in app["metrics"]}
    rows = fnd["rows"]
    high = [r for r in rows if r["status"] in OPEN_STATES and r["severity"] in ("S1", "S2")]
    over = [r for r in rows if r["overdue"]]
    distinct = lambda rs: len({(r["entry_key"], r["id"]) for r in rs})   # noqa: E731
    assert m["open-high-severity"]["numerator"] == distinct(high) == 4 and m["open-high-severity"]["register_rows"] == len(high) == 8
    assert m["overdue-remediation"]["numerator"] == distinct(over) == 3 and m["overdue-remediation"]["register_rows"] == len(over) == 7
    assert m["open-high-severity"]["denominator"] == m["overdue-remediation"]["denominator"] == distinct(rows) == 39
    assert all(m[k]["register_rows"] is None for k in m if k not in ("open-high-severity", "overdue-remediation"))
    assert m["entries-under-exception"]["numerator"] == sum(1 for e in inv["entries"] if e["lifecycle"]["exception"])
    assert m["entries-in-breach"]["numerator"] == sum(1 for e in inv["entries"] if e["attributes"]["A36"]["value"]["red"] > 0)
    assert m["pma-magnitude"]["value"] == pytest.approx(324129997.0 / 97592002519.53)
    assert app["population"] == {"entries": 4, "findings": len(rows), "distinct_findings": 39, "tier1_entries": 2}


# --- the planted defects: each refused by the layer the table names ---------------------------------------------------------------------


def _inv_entry(d: dict, key: str) -> dict:
    return entry_of(d["inventory"], key)


def _plant_tier(d: dict) -> None:
    tb = _inv_entry(d, "C01/german")["tier_block"]
    tb["computed_tier"] = 1
    tb["tier"] = 1


def _plant_sensitivity(d: dict) -> None:
    _inv_entry(d, "C01/german")["tier_block"]["tier_sensitivity"][3]["tier"] = 2


def _plant_unknown_edge(d: dict) -> None:
    d["inventory"]["edges"].append({"upstream": "C07/banco-andino", "downstream": "C99/ghost", "kind": "document", "stated_source": "x#1"})


def _plant_cycle(d: dict) -> None:
    d["inventory"]["edges"].append({"upstream": "C18/banco-andino", "downstream": "C07/banco-andino", "kind": "document", "stated_source": "x#1"})


def _plant_dup_component(d: dict) -> None:
    comps = _inv_entry(d, "C07/banco-andino")["components"]
    comps[1] = {**comps[1], "key": comps[0]["key"]}


def _plant_present_no_pointer(d: dict) -> None:
    _inv_entry(d, "C07/banco-andino")["attributes"]["A01"]["basis"] = "read from the document"


def _plant_na_no_reason(d: dict) -> None:
    _inv_entry(d, "C07/banco-andino")["attributes"]["A26"] = {"value": None, "status": "not-applicable", "basis": "n/a"}
    _inv_entry(d, "C01/german")["attributes"]["A26"]["basis"] = " "


def _plant_approval_date(d: dict) -> None:
    a = _inv_entry(d, "C07/banco-andino")["attributes"]["A33"]
    a["value"] = "2026-10-01"
    a["status"] = "present"


def _plant_convention_regulatory_label(d: dict) -> None:
    d["inventory"]["conventions"]["frequency"]["label"] = "regulatory"


def _plant_convention_regulatory_text(d: dict) -> None:
    d["inventory"]["conventions"]["frequency"]["basis"] = "the review frequency is a regulatory requirement of the PRA"


def _plant_convention_regulatory_text_es(d: dict) -> None:
    d["findings"]["conventions"]["deadline_days"]["basis"] = "el plazo regulatorio de cierre por severidad"


def _plant_missing_with_value(d: dict) -> None:
    _inv_entry(d, "C07/banco-andino")["attributes"]["A10"]["value"] = "use as designed"


def _plant_illegal_transition(d: dict) -> None:
    _inv_entry(d, "C07/banco-andino")["lifecycle"]["transitions"] = [
        {"from": "proposed", "to": "in_use", "date": "2026-10-12", "basis": "x"}]
    _inv_entry(d, "C07/banco-andino")["lifecycle"]["state"] = "in_use"


def _plant_schedule(d: dict) -> None:
    _inv_entry(d, "C07/banco-andino")["schedule"]["next_review"] = "2027-10-13"


def _plant_completeness(d: dict) -> None:
    d["inventory"]["completeness"]["attributes"]["A01"]["present"] = 3


def _plant_depth(d: dict) -> None:
    _inv_entry(d, "C18/banco-andino")["graph"]["depth"] = 0


def _plant_override_no_approver(d: dict) -> None:
    tb = _inv_entry(d, "C01/german")["tier_block"]
    tb["override"] = {"to_tier": 1, "rationale": "", "approver": ""}
    tb["tier"] = 1


def _plant_tier_counts(d: dict) -> None:
    d["inventory"]["tier_counts"][1]["counts"] = [4, 0, 0, 0]


def _plant_due(d: dict) -> None:
    d["findings"]["rows"][0]["due"] = "2030-01-01"


def _plant_deadline_days(d: dict) -> None:
    r = d["findings"]["rows"][0]
    r["deadline_days"] += 1
    r["due"] = (iso(r["raised"]) + timedelta(days=r["deadline_days"])).isoformat()


def _plant_overdue_flag(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if x["overdue"])
    r["overdue"] = False


def _plant_overdue_flag_true(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if not x["overdue"] and x["status"] == "open")
    r["overdue"] = True


def _plant_ecb_f(d: dict) -> None:
    d["findings"]["rows"][0]["ecb_f"] = "F1" if d["findings"]["rows"][0]["ecb_f"] != "F1" else "F4"


def _plant_status_map(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if x["product_status"] == "accepted")
    r["status"] = "validated_closed"
    r["risk_acceptance"] = None


def _plant_ageing(d: dict) -> None:
    d["findings"]["rows"][0]["ageing_days"] += 1


def _plant_risk_acceptance_expiry(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if x["status"] == "risk_accepted")
    r["risk_acceptance"]["expiry"] = "2027-01-01"


def _plant_risk_acceptance_missing(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if x["status"] == "risk_accepted")
    r["risk_acceptance"] = None


def _plant_anchor_no_reason(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if x["anchor"] is None)
    r["anchor_reason"] = None


def _plant_key(d: dict) -> None:
    d["findings"]["rows"][0]["key"] = "C01/other/F-X"


def _plant_counts(d: dict) -> None:
    d["findings"]["counts"]["by_severity"]["S2"] += 1


def _plant_row_tier(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if x["entry_key"] == "C07/banco-andino")
    r["tier"] = 2
    r["deadline_days"] = {"S1": [30, 45], "S2": [60, 90], "S3": [90, 120], "S4": [180, 270]}[r["severity"]][1]
    r["due"] = (iso(r["raised"]) + timedelta(days=r["deadline_days"])).isoformat()


def _plant_opinion(d: dict) -> None:
    op = d["reports"]["C18/banco-andino"]["sections"][10]["opinion"]
    op["level"] = 2
    d["reports"]["C18/banco-andino"]["sections"][0]["opinion_level"] = 2


def _plant_opinion_up(d: dict) -> None:
    op = d["reports"]["C07/banco-andino"]["sections"][10]["opinion"]
    op["level"] = 4
    d["reports"]["C07/banco-andino"]["sections"][0]["opinion_level"] = 4


def _plant_label(d: dict) -> None:
    d["reports"]["C07/banco-andino"]["sections"][10]["opinion"]["label"]["en"] = "approved by Contraste"


def _plant_recommendation(d: dict) -> None:
    d["reports"]["C07/banco-andino"]["sections"][10]["opinion"]["recommendation"]["outcome"] = "approve"


def _plant_filled_no_inputs(d: dict) -> None:
    d["reports"]["C07/banco-andino"]["sections"][1]["inputs"] = []


def _plant_absent_no_reason(d: dict) -> None:
    s = next(x for x in d["reports"]["C18/banco-andino"]["sections"] if x["status"] == "absent")
    s["absent_reason"] = None


def _plant_sections_order(d: dict) -> None:
    secs = d["reports"]["C07/banco-andino"]["sections"]
    secs[2], secs[3] = secs[3], secs[2]


def _plant_test_counts(d: dict) -> None:
    d["reports"]["C07/banco-andino"]["test_counts"]["green"] += 1


def _plant_open_findings(d: dict) -> None:
    d["reports"]["C07/banco-andino"]["sections"][10]["opinion"]["open_findings"] = []


def _plant_metric_value(d: dict) -> None:
    m = next(x for x in d["appetite"]["metrics"] if x["id"] == "owner-and-complete-record")
    m["value"] = 0.9


def _plant_metric_light(d: dict) -> None:
    m = next(x for x in d["appetite"]["metrics"] if x["id"] == "overdue-remediation")
    m["light"] = "green" if m["light"] != "green" else "red"


def _plant_metric_numerator(d: dict) -> None:
    m = next(x for x in d["appetite"]["metrics"] if x["id"] == "open-high-severity")
    m["numerator"] += 1
    m["value"] += 1


def _plant_threshold_label(d: dict) -> None:
    d["appetite"]["metrics"][0]["threshold"]["label"] = "regulatory"


def _plant_header(d: dict) -> None:
    d["inventory"]["governance_id"] = "findings"


def _claim_plant(phrase: str):
    def plant(d: dict) -> None:
        d["findings"]["conventions"]["deadline_days"]["basis"] = phrase
    return plant


def _plant_approval_s1(d: dict) -> None:
    d["reports"]["C07/banco-andino"]["sections"][0]["blocks"][1]["text"]["en"] = "Contraste approves this model for use; it is compliant with SR 26-2."


def _plant_approval_rec(d: dict) -> None:
    d["reports"]["C07/banco-andino"]["sections"][10]["opinion"]["recommendation"]["text"]["en"] = "Approved: the model is certified for use."


def _plant_approval_es(d: dict) -> None:
    d["reports"]["C18/banco-andino"]["sections"][0]["blocks"][1]["text"]["es"] = "El modelo esta aprobado y certificado; cumple con la norma."


def _plant_a32_value(d: dict) -> None:
    a = _inv_entry(d, "C07/banco-andino")["attributes"]["A32"]
    a["value"] = "Chief Risk Officer"
    a["status"] = "present"


def _plant_report_rwea_not_in_register(d: dict) -> None:
    d["reports"]["C18/banco-andino"]["sections"][10]["opinion"]["open_findings"][0]["rwea_share"] = 0.12


def _plant_row_rwea_without_anchor(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if x["anchor"] is None)
    r["rwea_share"], r["rwea_share_reason"] = 0.12, None


def _plant_row_rwea_not_the_anchor(d: dict) -> None:
    r = next(x for x in d["findings"]["rows"] if x["anchor"] is None)
    r["anchor"] = {"metric": "metric", "test_id": "t.x", "model_id": "m", "segment": None, "value": 0.05, "unit": "share-of-rwea", "basis": "x#/tests/0/metric"}
    r["anchor_reason"] = None
    r["rwea_share"], r["rwea_share_reason"] = 0.2, None


def _rwea_state(d: dict, share: float, level: int | None, outcome: str | None) -> None:
    """Every open C18 row carries a share-of-RWEA anchor of ``share`` (register and report); the report states ``level`` and ``outcome``."""
    rep = d["reports"]["C18/banco-andino"]
    keys = {f["key"] for f in rep["sections"][10]["opinion"]["open_findings"]}
    for r in d["findings"]["rows"]:
        if r["key"] in keys:
            r["anchor"] = {"metric": "metric", "test_id": "t.x", "model_id": "m", "segment": None, "value": share, "unit": "share-of-rwea",
                           "basis": "x#/tests/0/metric"}
            r["anchor_reason"] = None
            r["rwea_share"], r["rwea_share_reason"] = share, None
    for f in rep["sections"][10]["opinion"]["open_findings"]:
        f["rwea_share"] = share
    if level is not None:
        rep["sections"][10]["opinion"]["level"] = level
        rep["sections"][0]["opinion_level"] = level
        rep["sections"][10]["opinion"]["recommendation"]["outcome"] = outcome


def _plant_anchor_lowers_the_level(d: dict) -> None:
    _rwea_state(d, 0.01, 2, "approve with conditions")      # the review's R1: an S1 finding with a 1 percent share, level 2


def _plant_as_of_before_raised(d: dict) -> None:
    d["findings"]["as_of"] = "2026-10-14"


def _plant_inventory_as_of_before_validation(d: dict) -> None:
    d["inventory"]["as_of"] = "2026-10-01"


def _plant_as_of_basis_label(d: dict) -> None:
    d["findings"]["as_of_basis"]["label"] = "regulatory"


def _plant_variant_not_in_entry(d: dict) -> None:
    e = _inv_entry(d, "C07/banco-andino")
    e["variants"] = [v for v in e["variants"] if v["variant_id"] != "recession"]


def _plant_excluded_variant_assigned(d: dict) -> None:
    d["inventory"]["excluded"].append({"case_id": "C07", "variant_id": "base", "reason": {"en": "no fit determinable", "es": "ningun ajuste determinable"}})


def _plant_duplicate_variant(d: dict) -> None:
    e = _inv_entry(d, "C07/banco-andino")
    e["variants"].append(dict(e["variants"][0]))


def _plant_literal_below_graded(d: dict) -> None:
    _inv_entry(d, "C01/german")["tier_block"]["materiality"]["regulatory_use"]["literal"] = 2


def _plant_report_severity_differs(d: dict) -> None:
    f = d["reports"]["C07/banco-andino"]["sections"][10]["opinion"]["open_findings"][0]
    f["severity"] = "S4" if f["severity"] != "S4" else "S1"


def _plant_related_unknown(d: dict) -> None:
    d["inventory"]["related"].append({"a": "C22/generators", "b": "C99/ghost", "kind": "measures", "source": "x"})


def _plant_edge_repeats(d: dict) -> None:
    d["inventory"]["edges"].append(dict(d["inventory"]["edges"][0]))


def _plant_register_rows(d: dict) -> None:
    next(x for x in d["appetite"]["metrics"] if x["id"] == "open-high-severity")["register_rows"] += 1


def _plant_appetite_counts_rows(d: dict) -> None:
    m = next(x for x in d["appetite"]["metrics"] if x["id"] == "open-high-severity")
    m["numerator"] = m["register_rows"]
    m["value"] = m["register_rows"]


def _plant_kind_not_a_decision(d: dict) -> None:
    d["reports"]["C07/banco-andino"]["sections"][5]["blocks"][0]["rows"][0]["policy"]["kind"] = "upper_bad"


def _plant_kind_without_reason(d: dict) -> None:
    policy = d["reports"]["C07/banco-andino"]["sections"][5]["blocks"][0]["rows"][0]["policy"]
    policy["kind"], policy["kind_reason"] = None, None


# name, mutator, the layers that must refuse it (schema, checker or cross) and a word the checker message must carry
PLANTS: list[tuple[str, Callable[[dict], None], tuple[str, ...], str]] = [
    ("a tier that is not the matrix of its scores", _plant_tier, ("checker",), "tier"),
    ("a sensitivity tier that is not the matrix of its reading", _plant_sensitivity, ("checker",), "tier"),
    ("an edge to an unknown entry", _plant_unknown_edge, ("checker",), "unknown entry"),
    ("a cycle in the dependency graph", _plant_cycle, ("checker",), "cycle"),
    ("a component key that repeats", _plant_dup_component, ("checker",), "component key"),
    ("a present attribute without a pointer", _plant_present_no_pointer, ("checker",), "pointer"),
    ("a not-applicable attribute without a reason", _plant_na_no_reason, ("checker",), "reason"),
    ("an approval date with a value", _plant_approval_date, ("checker",), "approval"),
    ("a convention labelled regulatory", _plant_convention_regulatory_label, ("schema", "checker"), "regulatory"),
    ("a convention called a regulatory requirement", _plant_convention_regulatory_text, ("checker",), "regulatory"),
    ("a convention called regulatorio in Spanish", _plant_convention_regulatory_text_es, ("checker",), "regulatory"),
    ("a missing attribute that holds a value", _plant_missing_with_value, ("schema", "checker"), "value"),
    ("an illegal lifecycle transition", _plant_illegal_transition, ("checker",), "transition"),
    ("a next review date that is not the table's", _plant_schedule, ("checker",), "schedule"),
    ("a completeness count that does not recompute", _plant_completeness, ("checker",), "completeness"),
    ("a depth that is not the longest path", _plant_depth, ("checker",), "depth"),
    ("an override without rationale and approver", _plant_override_no_approver, ("schema", "checker"), "override"),
    ("tier counts that do not recompute", _plant_tier_counts, ("checker",), "tier_counts"),
    ("a due date that is not the raised date plus the deadline", _plant_due, ("checker",), "due"),
    ("a deadline that is not the table's", _plant_deadline_days, ("checker",), "deadline"),
    ("an overdue flag that says not overdue after the due date", _plant_overdue_flag, ("checker",), "overdue"),
    ("an overdue flag that says overdue before the due date", _plant_overdue_flag_true, ("checker",), "overdue"),
    ("an ECB F equivalent that is not the severity's", _plant_ecb_f, ("schema", "checker"), "ecb_f"),
    ("a register status that is not the mapped product status", _plant_status_map, ("checker",), "status"),
    ("an ageing that is not as_of minus raised", _plant_ageing, ("checker",), "ageing"),
    ("a risk acceptance with an expiry", _plant_risk_acceptance_expiry, ("schema", "checker"), "expiry"),
    ("a risk-accepted finding without its risk acceptance", _plant_risk_acceptance_missing, ("schema", "checker"), "risk_acceptance"),
    ("a null anchor without its reason", _plant_anchor_no_reason, ("schema", "checker"), "anchor"),
    ("a register key that is not case/variant/id", _plant_key, ("checker",), "key"),
    ("counts that do not recompute", _plant_counts, ("checker",), "counts"),
    ("a finding row whose tier is not its entry's", _plant_row_tier, ("cross",), "tier"),
    ("an opinion that is not the rule's level (too low)", _plant_opinion, ("checker",), "opinion"),
    ("an opinion that is not the rule's level (too high)", _plant_opinion_up, ("checker",), "opinion"),
    ("a recommendation label that approves", _plant_label, ("schema", "checker"), "label"),
    ("a recommendation that is not the level's", _plant_recommendation, ("checker",), "recommendation"),
    ("a filled section without inputs", _plant_filled_no_inputs, ("schema", "checker"), "inputs"),
    ("an absent section without its reason", _plant_absent_no_reason, ("schema", "checker"), "absent"),
    ("sections out of order", _plant_sections_order, ("schema", "checker"), "section"),
    ("executive counts that disagree with the outcomes rows", _plant_test_counts, ("checker",), "test_counts"),
    ("an opinion listing no open finding while the register holds one", _plant_open_findings, ("cross",), "open"),
    ("an appetite value that is not numerator over denominator", _plant_metric_value, ("checker",), "value"),
    ("an appetite light that disagrees with its threshold", _plant_metric_light, ("checker",), "light"),
    ("an appetite numerator the register does not give", _plant_metric_numerator, ("cross",), "open-high-severity"),
    ("an appetite threshold labelled regulatory", _plant_threshold_label, ("schema", "checker"), "regulatory"),
    ("a governance id that is not the document's", _plant_header, ("schema",), ""),
    ("approval text in section 1", _plant_approval_s1, ("checker",), "approval"),
    ("approval text in the recommendation", _plant_approval_rec, ("checker",), "approval"),
    ("approval text in Spanish", _plant_approval_es, ("checker",), "approval"),
    ("an approver with a value on A32", _plant_a32_value, ("checker",), "approval"),
    ("a deadline basis set by the regulator", _claim_plant("these deadlines are set by the regulator (ECB TRIM)"), ("checker",), "regulatory"),
    ("a deadline basis prescribed by the ECB", _claim_plant("the days are prescribed by the ECB"), ("checker",), "regulatory"),
    ("a deadline basis that is a supervisory requirement", _claim_plant("the table is a supervisory requirement"), ("checker",), "regulatory"),
    ("a deadline basis mandated by SR 26-2", _claim_plant("the interval is mandated by SR 26-2"), ("checker",), "regulatory"),
    ("a deadline basis the PRA requires", _claim_plant("this is the frequency the PRA requires"), ("checker",), "regulatory"),
    ("a deadline basis that is an SS1/23 minimum", _claim_plant("the days are an SS1/23 minimum"), ("checker",), "regulatory"),
    ("a deadline basis the regulator demands in Spanish", _claim_plant("el plazo que exige el regulador"), ("checker",), "regulatory"),
    ("an RWEA share in the report that the register does not hold", _plant_report_rwea_not_in_register, ("cross",), "rwea_share"),
    ("an RWEA share on a row with no RWEA anchor", _plant_row_rwea_without_anchor, ("checker",), "rwea_share"),
    ("an RWEA share that is not the anchor's value", _plant_row_rwea_not_the_anchor, ("checker",), "rwea_share"),
    ("an anchor that lowers a level (S1 with a 1 percent share, level 2)", _plant_anchor_lowers_the_level, ("checker",), "opinion level"),
    ("an as_of earlier than the newest raised date", _plant_as_of_before_raised, ("checker",), "as_of"),
    ("an as_of earlier than the newest last validation", _plant_inventory_as_of_before_validation, ("checker",), "as_of"),
    ("an as_of basis labelled regulatory", _plant_as_of_basis_label, ("schema", "checker"), "as_of_basis"),
    ("a register row whose variant is not in its entry", _plant_variant_not_in_entry, ("cross",), "variant"),
    ("an excluded variant that is also assigned", _plant_excluded_variant_assigned, ("checker",), "also assigned"),
    ("a variant listed twice", _plant_duplicate_variant, ("checker",), "twice"),
    ("a literal regulatory use below the graded one", _plant_literal_below_graded, ("checker",), "literal"),
    ("a report open finding whose severity differs from the register's", _plant_report_severity_differs, ("cross",), "differ"),
    ("a related link to an unknown entry", _plant_related_unknown, ("checker",), "unknown entry"),
    ("a repeated edge", _plant_edge_repeats, ("checker",), "repeats"),
    ("a register_rows count the register does not give", _plant_register_rows, ("cross",), "register_rows"),
    ("an appetite count of register rows instead of distinct findings", _plant_appetite_counts_rows, ("cross",), "open-high-severity"),
    ("a policy kind that is not a registry decision", _plant_kind_not_a_decision, ("schema",), ""),
    ("a policy kind without its reason", _plant_kind_without_reason, ("schema",), ""),
]
DOC_OF_SCHEMA = {INV: "inventory", FND: "findings", APP: "appetite"}


def _layers(d: dict) -> dict[str, list[str]]:
    """What each layer says of a mutated copy of the fixtures."""
    schema = []
    for key, (ref, _) in FILES.items():
        doc = d["inventory"] if key == "inventory" else d["findings"] if key == "findings" else d["appetite"] if key == "appetite" else \
            d["reports"][REPORT_KEYS[key]]
        schema += [f"{key}: {m}" for m in cs.errors(ref, doc)]
    checker = []
    for doc in (d["inventory"], d["findings"], d["appetite"], *d["reports"].values()):
        checker += sm().violations(doc)
    return {"schema": schema, "checker": checker, "cross": sm().cross_violations(d)}


def test_the_unmutated_documents_pass_every_layer() -> None:
    assert all(not v for v in _layers(all_docs()).values())


@pytest.mark.parametrize("name,mutate,layers,needle", PLANTS, ids=[p[0] for p in PLANTS])
def test_a_planted_defect_is_refused_by_the_layer_the_table_names(name: str, mutate: Callable[[dict], None], layers: tuple[str, ...],
                                                                   needle: str) -> None:
    d = copy.deepcopy(all_docs())
    mutate(d)
    found = _layers(d)
    assert any(found[layer] for layer in layers), f"{name}: refused by none of {layers}"
    if "checker" in layers:
        assert needle.lower() in " ".join(found["checker"]).lower(), f"{name}: checker messages {found['checker']}"
    if "cross" in layers:
        assert needle.lower() in " ".join(found["cross"]).lower(), f"{name}: cross messages {found['cross']}"


def test_finding_level_is_the_maximum_of_the_severity_and_the_rwea_level_at_its_boundaries() -> None:
    f = sm().finding_level
    assert [f(sv) for sv in SEVERITIES] == [4, 3, 2, 2]
    assert f("S4", 0.0499) == 2 and f("S4", 0.05) == 3 and f("S3", 0.0999) == 3 and f("S3", 0.10) == 4
    assert f("S1", 0.0499) == 4 and f("S1", 0.05) == 4 and f("S2", 0.10) == 4 and f("S1", 0.01) == 4      # an anchor only raises a level
    assert f("S2", 0.06) == 3 and f("S4", 0.4) == 4
    o = sm().opinion_level
    assert o([]) == 1 and o([{"severity": "S4"}, {"severity": "S3"}]) == 2 and o([{"severity": "S1", "rwea_share": 0.01}]) == 4
    assert o([{"severity": "S3", "rwea_share": 0.05}]) == 3 and o([{"severity": "S4", "rwea_share": 0.10}]) == 4


def test_the_overdue_flag_is_false_on_the_due_date_and_true_the_day_after() -> None:
    d = date(2026, 11, 11)
    assert sm().is_overdue("open", d, d) is False
    assert sm().is_overdue("open", d, d + timedelta(days=1)) is True
    assert sm().is_overdue("overdue", d, d + timedelta(days=1)) is True
    assert sm().is_overdue("risk_accepted", d, d + timedelta(days=400)) is False
    assert sm().is_overdue("validated_closed", d, d + timedelta(days=400)) is False


PATTERN_SAMPLES = [   # a sample that only the pattern of that index matches (a pattern removed is a pattern found missing)
    ("the regulatory deadline applies", 0), ("the table is regulatory", 1), ("applies as required by law", 2), ("el plazo regulatorio", 3),
    ("el umbral es regulatorio", 4), ("prescribed by the ECB", 5), ("the PRA requires an annual review", 6), ("a supervisory requirement", 7),
    ("an SS1/23 minimum", 8), ("el plazo que exige el regulador", 9),
]


@pytest.mark.parametrize("text,index", PATTERN_SAMPLES, ids=[t for t, _ in PATTERN_SAMPLES])
def test_each_regulatory_claim_pattern_has_a_sample_only_it_catches(text: str, index: int) -> None:
    assert sm().regulatory_claim_hits(text) == [index]


def test_the_wider_phrasings_of_the_review_are_all_found_and_the_negation_is_not() -> None:
    for phrase in ("prescribed by the ECB", "set by the regulator", "a supervisory requirement", "mandated by SR 26-2", "the frequency the PRA requires",
                   "an SS1/23 minimum", "el plazo que exige el regulador", "these deadlines are set by the regulator (ECB TRIM)"):
        assert sm().regulatory_claims(phrase), phrase
    assert not sm().regulatory_claims("no regulatory source prescribes days; the table is a convention")
    assert len(sm()._REG_CLAIMS) == len(PATTERN_SAMPLES)


def test_approval_claims_are_found_in_both_languages_and_the_fixed_negations_are_exempt() -> None:
    for text in ("Contraste approves this model for use", "the model is approved", "it is certified for use", "compliant with SR 26-2",
                 "El modelo esta aprobado", "El modelo esta certificado", "cumple con la norma", "the approval of the board"):
        assert sm().approval_claims(text), text
    for text in ("Contraste approves no model", "Contraste no aprueba ningun modelo", "no approval date or authority exists", "no approver exists",
                 "Approve with conditions: only minor findings are open", "compliance monitoring", "the approval rate on card applicants"):
        assert not sm().approval_claims(text), text


def test_an_empty_inventory_is_refused_with_a_stated_message() -> None:
    doc = copy.deepcopy(load("inventory"))
    doc["entries"] = []
    assert sm().violations(doc) == ["the inventory holds no entry: there is nothing to check, nothing to publish"]


def test_an_rwea_anchor_raises_the_opinion_when_the_register_and_the_report_agree() -> None:
    d = copy.deepcopy(all_docs())
    rep = d["reports"]["C07/banco-andino"]
    keys = {f["key"]: f for f in rep["sections"][10]["opinion"]["open_findings"]}
    target = next(r for r in d["findings"]["rows"] if r["key"] in keys and r["severity"] == "S3")
    target["anchor"] = {"metric": "metric", "test_id": "t.x", "model_id": "m", "segment": None, "value": 0.12, "unit": "share-of-rwea",
                        "basis": "x#/tests/0/metric"}
    target["anchor_reason"], target["rwea_share"], target["rwea_share_reason"] = None, 0.12, None
    keys[target["key"]]["rwea_share"] = 0.12
    op = rep["sections"][10]["opinion"]
    assert op["level"] == 3
    op["level"], rep["sections"][0]["opinion_level"] = 4, 4
    op["recommendation"]["outcome"], op["rwea_cut_points_applied"] = "remediate before use", True
    found = _layers(d)
    assert all(not v for v in found.values()), found
    op["level"], rep["sections"][0]["opinion_level"] = 3, 3          # the level the severities alone give is now refused
    assert any("opinion level" in m for m in _layers(d)["checker"])


def test_every_invariant_of_the_brief_has_at_least_one_planted_defect() -> None:
    names = " | ".join(p[0] for p in PLANTS).lower()
    for phrase in ("matrix of its scores", "raised date plus the deadline", "overdue flag", "opinion that is not the rule", "unknown entry",
                   "cycle", "component key that repeats", "present attribute without a pointer", "not-applicable attribute without a reason",
                   "approval date with a value", "convention labelled regulatory", "convention called"):
        assert phrase in names, phrase


# --- the engine governance API contract --------------------------------------------------------------------------------------------------

API_MODULES: dict[str, list[str]] = {
    "scope": ["ScopeAnswers", "ScopeDecision", "scope_test", "scope_record"],
    "inventory": ["Component", "Entry", "Edge", "Inventory", "assign_variant", "build_inventory", "topological_order", "graph_metrics", "attribute_completeness",
                  "find_cycle", "nodes_on_cycles"],
    "tiering": ["exposure_band", "materiality", "complexity", "matrix_tier", "apply_override", "tier_sensitivity", "tier_counts"],
    "lifecycle": ["allowed_next", "transition"],
    "findings": ["Finding", "rwea_share_of_anchor", "severity_to_ecb", "map_product_status", "deadline_days", "due_date", "ageing_days", "is_overdue",
                 "transition_finding", "anchor_from_test_row", "register_counts"],
    "schedule": ["add_months", "next_dates"],
    "opinion": ["finding_level", "opinion_level", "recommendation", "rwea_level"],
    "appetite": ["light", "tier1_validated_on_time", "open_high_severity", "overdue_remediation", "entries_under_exception",
                 "entries_in_breach", "pma_magnitude", "owner_and_complete_record", "appetite_metrics", "appetite_population"],
    "policy": ["resolve_policy"],
    "reasons": ["codes", "code_of", "bilingual"],
    "report": ["executive_counts", "build_report"],
}
VALIDATION = ["inventory_completeness", "findings_overdue", "validation_due", "tier_override_documented", "edges_acyclic"]
VALIDATION_HELPERS = ["GovRow", "gov_threshold", "gov_default_policy"]  # the policy rows of the gov. tests; no TestResult (W15-16)
DATACLASSES = {"ScopeAnswers", "ScopeDecision", "Component", "Entry", "Edge", "Inventory", "Finding", "GovRow"}
REUSED = ["core.result.TestResult", "core.policy.Policy", "core.policy.Threshold", "core.policy.load_policy", "core.policy.default_policy",
          "core.registry.catalogue", "core.registry.spec", "core.suite.SuiteRun", "core.hashing.inputs_hash"]


def declared() -> dict[str, str]:
    out = {f"riskvalidation.governance.{m}.{n}": m for m, names in API_MODULES.items() for n in names}
    out.update({f"riskvalidation.validation.governance.{n}": "validation" for n in VALIDATION})
    out.update({f"riskvalidation.validation.governance.{n}": "validation-helper" for n in VALIDATION_HELPERS})
    return out


def api_sections() -> dict[str, str]:
    text = API.read_text(encoding="utf-8")
    parts = re.split(r"^### `([^`]+)`\n", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def test_the_engine_contract_exists_with_its_header() -> None:
    text = API.read_text(encoding="utf-8")
    assert text.startswith("# Engine governance API contract: `engine-governance-api` 1.1.0")
    for word in ("Owner: U15-S", "Changing a signature, a unit or a golden value is a breaking change", "Reused engine functions", "Conventions (all functions)"):
        assert word in text, word


def test_the_engine_contract_covers_every_module_of_the_sizing_table() -> None:
    text = API.read_text(encoding="utf-8")
    for module in (*API_MODULES, "validation/governance"):
        file = f"riskvalidation/governance/{module}.py" if module != "validation/governance" else "riskvalidation/validation/governance.py"
        assert f"## Module `{file}`" in text, file


def test_every_function_has_a_signature_units_and_a_golden_value_or_an_invariant() -> None:
    sections = api_sections()
    for name, module in declared().items():
        body = sections[name]
        assert "```python" in body, name
        assert re.search(r"^- (Golden|Invariants):", body, flags=re.M), f"{name}: no golden value or invariant"
        assert re.search(r"^- Units:", body, flags=re.M), f"{name}: no units line"
        short = name.rsplit(".", 1)[1]
        if short in DATACLASSES:
            assert "@dataclass(frozen=True)" in body, f"{short}: frozen dataclass"
        else:
            assert f"def {short}(" in body, f"{name}: def {short}( signature"
        if module == "validation":
            assert "-> TestResult" in body, name
            assert re.search(r"^- Light:", body, flags=re.M), name
            assert re.search(r'test_id = "gov\.[a-z_]+"', body), name
            assert re.search(r"^- Reference:", body, flags=re.M) and re.search(r"^- H0:", body, flags=re.M), name


def test_the_engine_contract_has_no_function_outside_the_table() -> None:
    assert set(api_sections()) == set(declared())


def test_the_reused_engine_functions_are_named_as_reused_and_never_restated() -> None:
    text = API.read_text(encoding="utf-8")
    reused = text.split("## Reused engine functions", 1)[1].split("\n## ", 1)[0]
    for name in REUSED:
        assert f"`riskvalidation.{name}`" in reused, name
        assert f"riskvalidation.{name}" not in set(api_sections()), f"{name} is reused, never restated"


def marked_fields() -> dict[tuple[str, str | None, str], str]:
    """Every schema property whose description ends with 'Computed by <function>.', found by walking the schema files (never a list typed here)."""
    out: dict[tuple[str, str | None, str], str] = {}
    rx = re.compile(r"Computed by (riskvalidation\.governance\.[a-z_0-9.]+?)\.(?:\s|$)")
    for f in sorted(SCHEMAS.glob("*.schema.json")):
        s = cs.load_json(f)
        name = f.name.removesuffix(".schema.json")
        for owner, props in [(None, s.get("properties", {}))] + [(d, v.get("properties", {})) for d, v in s["$defs"].items()]:
            for prop, node in props.items():
                found = rx.findall(node.get("description", "")) if isinstance(node, dict) else []
                if found:
                    out[(name, owner, prop)] = found[0]
    return out


def test_every_recomputed_field_names_the_engine_function_behind_it() -> None:
    sections = set(api_sections())
    marked = marked_fields()
    assert len(marked) >= 45, len(marked)
    assert set(marked.values()) <= sections, sorted(set(marked.values()) - sections)
    registry = sm().RECOMPUTED
    assert len(registry) == len(set(registry)) > 40
    missing = [k for k in registry if k not in marked]
    assert missing == [], f"a field the checker recomputes names no engine function: {missing}"
    every = {m for f in SCHEMAS.glob("*.schema.json")
             for m in re.findall(r"Computed by (riskvalidation\.governance\.[a-z_0-9.]+?)\.(?:\s|\"|$)", f.read_text(encoding="utf-8"))}
    assert every and every <= sections, sorted(every - sections)


def test_a_recomputed_field_that_names_no_engine_function_is_found() -> None:
    marked = marked_fields()
    probe = ("governance-findings", "fndRow", "due")
    assert probe in marked
    trimmed = {k: v for k, v in marked.items() if k != probe}
    assert [k for k in sm().RECOMPUTED if k not in trimmed] == [probe]


def test_the_contract_states_the_conventions_as_named_parameters_never_as_regulatory() -> None:
    text = API.read_text(encoding="utf-8")
    flat = text.replace("\n", " ")
    for word in ("exposure band cut points", "deadline table", "frequency table", "appetite thresholds", "convention"):
        assert word in flat, word
    assert sm().regulatory_claims(text) == []
    for label in ("0.25", "0.10", "0.02", "item 30"):
        assert label in text, label


def test_a_text_that_calls_a_convention_regulatory_is_found_by_the_checker() -> None:
    assert sm().regulatory_claims("the deadline table is a regulatory requirement")
    assert sm().regulatory_claims("el plazo regulatorio de cierre")
    assert not sm().regulatory_claims("no regulatory source prescribes days; the table is a convention")


def _golden_text(name: str) -> str:
    return api_sections()[f"riskvalidation.governance.{name}"]


def test_golden_the_tier_matrix_at_its_boundaries_and_the_four_by_four_grid() -> None:
    body = _golden_text("tiering.matrix_tier")
    for m in (4, 3, 2, 1):
        row = " ".join(f"C{c}={matrix(m, c)}" for c in (1, 2, 3, 4))
        assert f"M={m}: {row}" in body, (m, row)


def test_golden_exposure_band_boundaries_and_complexity_rounding() -> None:
    body = _golden_text("tiering.exposure_band")
    for share, want in ((1.0, 4), (0.25, 4), (0.2499, 3), (0.10, 3), (0.0999, 2), (0.02, 2), (0.0199, 1), (0.0, 1)):
        assert f"exposure_band({share}) = {want}" in body, (share, want)
    assert "exposure_band(None) = 1" in body
    body = _golden_text("tiering.complexity")
    for scores, want in (([4, 2, 3, 1, 1, 1], 2), ([2, 2, 1, 1, 2, 1], 2), ([2, 2, 1, 1, 1, 1], 1), ([3, 3, 3, 2, 2, 2], 3), ([2, 1, 1, 1, 1, 1], 1)):
        assert f"complexity({scores}) = {want}" in body, scores


def test_golden_the_addendum_tiers_of_the_19_built_cases_under_the_four_readings() -> None:
    body = _golden_text("tiering.tier_sensitivity")
    for case in A_D2:
        a, b, c, d = tiers_of(case)
        assert f"{case}: A={a} B={b} C={c} D={d}" in body, case
    for i, counts in A_D2_COUNTS.items():
        assert f"reading {READINGS[i][0]}: " + "/".join(str(x) for x in counts) in body


B7_ALLOWED = [("open", "action_plan_agreed"), ("open", "risk_accepted"), ("open", "overdue"),
              ("action_plan_agreed", "in_progress"), ("action_plan_agreed", "risk_accepted"), ("action_plan_agreed", "overdue"),
              ("in_progress", "submitted_for_closure"), ("in_progress", "risk_accepted"), ("in_progress", "overdue"),
              ("submitted_for_closure", "validated_closed"), ("submitted_for_closure", "in_progress"), ("submitted_for_closure", "overdue"),
              ("overdue", "in_progress"), ("overdue", "submitted_for_closure"), ("overdue", "risk_accepted"), ("risk_accepted", "open")]


def test_golden_every_allowed_and_every_refused_b7_transition() -> None:
    body = _golden_text("findings.transition_finding")
    for a, b in B7_ALLOWED:
        assert f"allowed: {a} -> {b}" not in body   # no arrow character: the pairs are written with the word "to"
        assert f"allowed: {a} to {b}" in body, (a, b)
    refused = [(a, b) for a in STATES_B7 for b in STATES_B7 if (a, b) not in B7_ALLOWED]
    assert len(B7_ALLOWED) == 16 and len(refused) == 33
    assert "33 refused pairs" in body and "16 allowed pairs" in body
    assert "refused: validated_closed to open" in body and "refused: open to open" in body
    assert "cannot move from 'validated_closed' to 'open'" in body


B4_ALLOWED = [("proposed", "in_development"), ("in_development", "submitted_for_validation"), ("submitted_for_validation", "in_validation"),
              ("in_validation", "approved"), ("in_validation", "approved_with_conditions"), ("in_validation", "in_development"),
              ("approved", "in_use"), ("approved_with_conditions", "in_use"), ("in_use", "under_monitoring_alert"),
              ("in_use", "material_change_pending"), ("in_use", "in_validation"), ("in_use", "restricted"), ("in_use", "decommissioned"),
              ("under_monitoring_alert", "in_use"), ("under_monitoring_alert", "restricted"), ("under_monitoring_alert", "in_remediation"),
              ("restricted", "in_remediation"), ("restricted", "in_use"), ("restricted", "decommissioned"), ("in_remediation", "in_validation"),
              ("in_remediation", "restricted"), ("in_remediation", "decommissioned"), ("material_change_pending", "submitted_for_validation"),
              ("material_change_pending", "in_use")]


def test_golden_the_b4_transitions_and_the_exception_rule() -> None:
    body = _golden_text("lifecycle.allowed_next")
    for a, b in B4_ALLOWED:
        assert f"allowed: {a} to {b}" in body, (a, b)
    assert "decommissioned is terminal" in body
    assert "with an exception record" in _golden_text("lifecycle.transition")
    assert len(B4_ALLOWED) == 24


def test_golden_the_deadline_ageing_and_overdue_arithmetic_on_dates() -> None:
    assert iso("2026-10-12") + timedelta(days=30) == date(2026, 11, 11)
    assert (iso("2026-12-31") - iso("2026-10-12")).days == 80
    assert "due_date(2026-10-12, 30) = 2026-11-11" in _golden_text("findings.due_date")
    assert "ageing_days(2026-10-12, 2026-12-31) = 80" in _golden_text("findings.ageing_days")
    body = _golden_text("findings.is_overdue")
    assert "is_overdue('open', 2026-11-11, 2026-11-11) = False" in body and "is_overdue('open', 2026-11-11, 2026-11-12) = True" in body
    assert "is_overdue('risk_accepted', 2026-11-11, 2027-06-01) = False" in body
    days = _golden_text("findings.deadline_days")
    for sev, row in {"S1": [30, 45, 60, 90], "S2": [60, 90, 120, 180], "S3": [90, 120, 180, 270], "S4": [180, 270, 365, 365]}.items():
        for t, d in enumerate(row, 1):
            assert f"deadline_days('{sev}', {t}) = {d}" in days, (sev, t)
    sched = _golden_text("schedule.add_months")
    assert months(date(2026, 8, 31), 6) == date(2027, 2, 28) and months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert "add_months(2026-08-31, 6) = 2027-02-28" in sched and "add_months(2024-01-31, 1) = 2024-02-29" in sched
    nd = _golden_text("schedule.next_dates")
    for tier, last, want in ((1, "2026-10-12", ("2027-10-12", "2029-10-12", "2027-01-12")), (2, "2026-10-12", ("2027-10-12", "2029-10-12", "2027-04-12")),
                             (3, "2026-10-12", ("2028-10-12", "None", "2027-10-12")), (4, "2026-10-12", ("2029-10-12", "None", "None"))):
        assert f"next_dates({tier}, {last})" in nd and "(" + ", ".join(want) + ")" in nd.split(f"next_dates({tier}, {last}) = ")[1].split("\n")[0], tier


def test_golden_the_opinion_at_the_severity_rule_and_at_the_rwea_cut_points() -> None:
    body = _golden_text("opinion.opinion_level")
    for text in ("opinion_level([]) = 1", "opinion_level([S4, S3]) = 2", "opinion_level([S3, S2]) = 3", "opinion_level([S2, S1]) = 4"):
        assert text in body, text
    f = _golden_text("opinion.finding_level")
    for text in ("finding_level('S4', rwea_share=0.0499) = 2", "finding_level('S4', rwea_share=0.05) = 3", "finding_level('S3', rwea_share=0.0999) = 3",
                 "finding_level('S3', rwea_share=0.10) = 4", "finding_level('S1', rwea_share=0.0499) = 4",
                 "finding_level('S2', rwea_share=0.10) = 4"):
        assert text in f, text
    assert "risk_accepted" in body and "validated_closed" in body
    rec = _golden_text("opinion.recommendation")
    assert LABEL_EN in rec and "approve with conditions" in rec and "remediate before use" in rec


def test_golden_a_refused_cycle_names_the_cycle() -> None:
    body = _golden_text("inventory.build_inventory")
    assert "dependency cycle: A -> B -> C -> A" not in body            # no arrow character in prose or goldens
    assert "dependency cycle: A, B, C, A" in body
    assert "unknown entry" in body and "component key" in body
    t = _golden_text("inventory.topological_order")
    assert "topological_order(['A', 'B', 'C'], [('A', 'B'), ('B', 'C')]) = [['A'], ['B'], ['C']]" in t


def test_golden_the_policy_identity_of_a_test_row() -> None:
    body = _golden_text("policy.resolve_policy")
    assert "riskvalidation-default 2026.10.1" in body and "packaged-policy" in body
    assert "contraste-ifrs9-battery-1.0.0; nl_amber=1.0; nl_red=3.0" in body and "inline-battery" in body
    assert "unresolved" in body and "reason" in body
    assert "spec(test_id).decision" in body and "no policy file for an inline battery string" in body and "pd.jeffreys" in body and "kind `p_value`" in body


def test_golden_the_appetite_light_rule_and_the_scope_profiles() -> None:
    body = _golden_text("appetite.light")
    for text in ("light(0, 'lower-is-better', 0, 3) = 'green'", "light(3, 'lower-is-better', 0, 3) = 'amber'", "light(4, 'lower-is-better', 0, 3) = 'red'",
                 "light(0.9, 'higher-is-better', 0.9, 0.75) = 'green'", "light(0.8999, 'higher-is-better', 0.9, 0.75) = 'amber'",
                 "light(0.75, 'higher-is-better', 0.9, 0.75) = 'amber'", "light(0.7499, 'higher-is-better', 0.9, 0.75) = 'red'",
                 "light(None, 'lower-is-better', 0, 3) = 'not_evaluated'"):
        assert text in body, text
    sc = _golden_text("scope.scope_record")
    assert "us-2026" in sc and "pra" in sc and "osfi-2027" in sc and "ecb" in sc and "generative" in sc


def test_golden_the_gov_tests_recompute_from_the_fixtures() -> None:
    inv, fnd = load("inventory"), load("findings")
    pairs = [(e["key"], a["status"]) for e in inv["entries"] for a in e["attributes"].values()]
    share = sum(1 for _, s in pairs if s != "missing") / len(pairs)
    body = api_sections()["riskvalidation.validation.governance.inventory_completeness"]
    assert f"metric = {share:.4f}" in body
    open_rows = [r for r in fnd["rows"] if r["status"] in OPEN_STATES]
    share_od = sum(1 for r in open_rows if r["overdue"]) / len(open_rows)
    assert f"metric = {share_od:.4f}" in api_sections()["riskvalidation.validation.governance.findings_overdue"]
    due = sum(1 for e in inv["entries"] if iso(e["schedule"]["next_review"]) < iso(inv["as_of"]))
    assert f"metric = {due}" in api_sections()["riskvalidation.validation.governance.validation_due"]
    assert "metric = 0" in api_sections()["riskvalidation.validation.governance.tier_override_documented"]
    assert "metric = 0" in api_sections()["riskvalidation.validation.governance.edges_acyclic"]


def test_the_conventions_are_labelled_and_the_tables_hold_the_contract_values() -> None:
    inv, fnd, app = load("inventory"), load("findings"), load("appetite")
    conv = inv["conventions"]
    assert conv["exposure_band_cuts"]["cuts"] == [0.25, 0.1, 0.02]
    assert conv["regulatory_use_grades"]["literal"]["compliance_monitoring"] == 2        # m1: C21 literal 2 in A D2
    assert conv["complexity_rounding"]["rule"] == "mean-rounded-half-up"
    assert [(t["tier"], t["review_months"], t["revalidation_months"], t["monitoring_months"]) for t in conv["frequency"]["tiers"]] == [
        (1, 12, 36, 3), (2, 12, 36, 6), (3, 24, None, 12), (4, 36, None, None)]
    assert [r["days"] for r in fnd["conventions"]["deadline_days"]["rows"]] == [[30, 45, 60, 90], [60, 90, 120, 180], [90, 120, 180, 270], [180, 270, 365, 365]]
    for table in (conv["exposure_band_cuts"], conv["regulatory_use_grades"], conv["complexity_rounding"], conv["frequency"], conv["adopted_reading"],
                  fnd["conventions"]["deadline_days"], fnd["conventions"]["severity_scale"], fnd["conventions"]["status_map"]):
        assert table["label"] == "convention" and table["basis"].strip()
    assert all(m["threshold"]["label"] == "convention" for m in app["metrics"])
    api = API.read_text(encoding="utf-8")
    for needle in ("(30, 45, 60, 90)", "(60, 90, 120, 180)", "(90, 120, 180, 270)", "(180, 270, 365, 365)", "UNVERIFIED"):
        assert needle in api, needle


def test_golden_the_register_report_and_appetite_numbers_of_the_contract_equal_the_fixtures() -> None:
    fnd, app, rep = load("findings"), load("appetite"), load("report-C18")
    c = fnd["counts"]
    body = _golden_text("findings.register_counts")
    assert f"total {c['total']}" in body and f"overdue {c['overdue']}" in body
    assert all(f"{s} {n}" in body for s, n in c["by_severity"].items())
    assert "open 49, validated_closed 4, risk_accepted 28" in body and c["by_status"]["open"] == 49
    counts = rep["test_counts"]
    assert json.dumps(counts) in _golden_text("report.executive_counts").replace("'", '"') or str(counts).replace("'", '"') in         _golden_text("report.executive_counts")
    m = {x["id"]: x for x in app["metrics"]}
    for mid, fn in (("open-high-severity", "open_high_severity"), ("overdue-remediation", "overdue_remediation")):
        x = m[mid]
        assert f"({x['numerator']}, {x['denominator']}, {x['value']}, {x['register_rows']})" in _golden_text(f"appetite.{fn}")
    assert f"({m['entries-in-breach']['numerator']}, {m['entries-in-breach']['denominator']}, {m['entries-in-breach']['value']})" in         _golden_text("appetite.entries_in_breach")
    assert f"({m['pma-magnitude']['numerator']}, {m['pma-magnitude']['denominator']}, {m['pma-magnitude']['value']:.7f})" in         _golden_text("appetite.pma_magnitude")
    assert [x["light"] for x in app["metrics"]] == ["green", "red", "amber", "green", "red", "green", "red"]
    assert "lights green, red, amber, green, red, green, red" in _golden_text("appetite.appetite_metrics")
    assert len(rep["sections"][10]["opinion"]["open_findings"]) == 29 and "29 open findings" in _golden_text("report.build_report")


# --- the catalog rows and the changelog fragment ------------------------------------------------------------------------------------------

ROW_IDS = ["governance-inventory", "governance-findings", "governance-report", "governance-appetite", "engine-governance-api"]
COLUMNS = ["id", "version", "owner", "schema file", "example", "producer test", "consumer test", "missing-data behavior", "provider", "model io",
           "swap test", "status"]


def _rows() -> list[dict[str, str]]:
    lines = [ln for ln in ROWS_FRAGMENT.read_text(encoding="utf-8").splitlines() if ln.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    assert header == COLUMNS
    return [dict(zip(header, [c.strip() for c in ln.strip("|").split("|")])) for ln in lines[2:] if not ln.startswith("| contract")][: len(ROW_IDS)]


def test_the_rows_fragment_has_the_five_rows_active_with_the_fixture_as_provider() -> None:
    rows = _rows()
    assert [r["id"] for r in rows] == ROW_IDS
    for r in rows:
        assert r["version"] == "1.0.0" and r["status"] == "active"
        assert r["provider"].startswith("fixture:docs/contracts/fixtures/governance/")
        assert (ROOT / r["provider"].removeprefix("fixture:")).is_file()
        assert (ROOT / r["example"]).is_file() and (ROOT / r["schema file"]).is_file()
        assert r["missing-data behavior"].startswith(("partial:", "missing:")) and len(r["missing-data behavior"]) > 80
    tests = THIS.read_text(encoding="utf-8")
    for r in rows:
        for cell in (r["producer test"], r["consumer test"]):
            for ref in re.findall(r"tests/contracts_u15/test_u15_contracts\.py::(\w+)", cell):
                assert f"def {ref}(" in tests, ref
        assert "test_u15_contracts.py::" in r["producer test"]


def test_the_rows_fragment_has_history_rows_for_the_integrator() -> None:
    text = ROWS_FRAGMENT.read_text(encoding="utf-8")
    hist = text.split("| contract | version | date | change | kind |", 1)[1]
    for cid in ROW_IDS:
        assert re.search(rf"^\| {cid} \| 1\.0\.0 \| 2026-10-20 \| first schema of the contract \| initial \|$", hist, flags=re.M), cid


def test_the_changelog_fragment_holds_bullet_lines_only() -> None:
    if not CHANGES.is_file():  # a release merged and deleted it (fragments.py changelog --apply): its bullets live in the CHANGELOG
        assert "U15-S contracts:" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        return
    lines = CHANGES.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].startswith("- ")
    for ln in lines:
        assert ln.startswith("- ") or ln.startswith("  ") or not ln.strip(), ln
    assert not any(ln.startswith("#") for ln in lines)


def test_no_em_dash_no_arrow_and_no_emoji_in_what_this_unit_writes() -> None:
    fragment = CHANGES if CHANGES.is_file() else ROOT / "CHANGELOG.md"  # the release that merged the fragment holds its text
    paths = [API, ROWS_FRAGMENT, fragment, THIS, *Path(__file__).parent.glob("*.py"), *FIX.glob("*.json"), *SCHEMAS.glob("*.json")]
    for p in paths:
        text = p.read_text(encoding="utf-8")
        for ch in (chr(0x2014), chr(0x2192), chr(0x2190), chr(0x21D2)):
            assert ch not in text, f"{p.name}: {ch!r}"
        assert not re.search("[" + chr(0x1F300) + "-" + chr(0x1FAFF) + chr(0x2600) + "-" + chr(0x27BF) + "]", text), p.name
