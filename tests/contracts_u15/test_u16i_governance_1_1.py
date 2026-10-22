"""U16-I: ``engine-governance-api`` 1.1.0 against the engine it describes (``riskvalidation`` 1.0.0) and the ``governance-report`` schema that admits the
policy source of an overridden packaged row. The reasons module, the reworded reasons and the new source are stated in the contract; the fixtures carry the
engine's reasons."""
from __future__ import annotations

import ast
import copy
import inspect
import json
import re

import contract_schemas as cs

ROOT = cs.ROOT
API = ROOT / "docs" / "contracts" / "engine" / "governance-api.md"
SCHEMA = ROOT / "docs" / "contracts" / "schemas" / "governance" / "governance-report.schema.json"
FIX = ROOT / "docs" / "contracts" / "fixtures" / "governance"


def _text() -> str:
    return API.read_text(encoding="utf-8")


def _sections() -> dict[str, str]:
    parts = re.split(r"^### `([^`]+)`\n", _text(), flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def _signature(body: str) -> list[str]:
    code = re.search(r"```python\n(.*?)```", body, flags=re.S).group(1)
    fn = ast.parse(code).body[0]
    a = fn.args
    return [x.arg for x in a.args] + [x.arg for x in a.kwonlyargs] + ([a.vararg.arg] if a.vararg else []) + ([a.kwarg.arg] if a.kwarg else [])


def _engine_signature(fn) -> list[str]:
    return list(inspect.signature(fn).parameters)


def test_the_contract_is_at_1_1_0() -> None:
    assert _text().startswith("# Engine governance API contract: `engine-governance-api` 1.1.0")
    assert "1.1.0" in _text().split("## Conventions", 1)[0]


def test_the_reasons_module_is_in_the_module_table_with_the_engine_signatures() -> None:
    from riskvalidation.governance import reasons

    assert "## Module `riskvalidation/governance/reasons.py`" in _text()
    sections = _sections()
    for name in ("codes", "code_of", "bilingual"):
        body = sections[f"riskvalidation.governance.reasons.{name}"]
        assert _signature(body) == _engine_signature(getattr(reasons, name)), name
        assert re.search(r"^- Golden:", body, flags=re.M) and re.search(r"^- Units:", body, flags=re.M), name
    assert "`REASONS`" in _text().split("## Public constants", 1)[1].split("## Module ", 1)[0]


def test_the_codes_the_contract_names_are_in_the_engine_table() -> None:
    from riskvalidation.governance import reasons

    named = set(re.findall(r"`((?:scope|variant|anchor|policy)\.[a-z0-9_.]+)`", _text()))
    # `scope.profiles` and `policy.resolve_policy` are names of modules and functions, not reason codes
    named -= {n for n in named if n not in reasons.codes() and n.split(".")[0] in ("scope", "policy") and n.split(".", 1)[1] in ("profiles", "resolve_policy")}
    assert named <= set(reasons.codes()), sorted(named - set(reasons.codes()))
    for code in ("policy.rule_not_single_direction", "policy.override_missing"):
        assert code in named, code


def test_the_three_reworded_reasons_are_the_engines_and_no_backlog_id_is_left_in_them() -> None:
    from riskvalidation.governance import policy

    text = _text()
    assert policy.NO_POLICY_FILE in text and policy.KIND_NOT_REGISTERED in text
    assert "no policy file (BL-085)" not in text
    assert "batch 3" not in text.split("## Module `riskvalidation/governance/policy.py`", 1)[1].split("## Module `riskvalidation/governance/report.py`", 1)[0]


def test_resolve_policy_states_the_new_source_the_override_and_the_battery_key() -> None:
    from riskvalidation.governance import policy

    body = _sections()["riskvalidation.governance.policy.resolve_policy"]
    assert _signature(body) == _engine_signature(policy.resolve_policy)
    for needle in ("packaged-policy-overridden", "+custom", "override", "battery", "policy.override_missing"):
        assert needle in body, needle


def test_the_accents_of_the_engine_spanish_are_stated() -> None:
    assert "RAE orthography" in _text()
    assert "without accents" not in _text()


# --- the governance-report schema ---------------------------------------------------------------------------------------------------------


def _report() -> dict:
    return json.loads((FIX / "report-C07-banco-andino-fixture.json").read_text(encoding="utf-8"))


def _first_policy(doc: dict) -> dict:
    return next(b for b in doc["sections"][5]["blocks"] if b["kind"] == "outcomes")["rows"][0]["policy"]


def _errors(doc: dict) -> list[str]:
    ref = cs.schema_for_document(FIX / "report-C07-banco-andino-fixture.json", doc)
    return cs.errors(ref, doc)


def test_the_policy_source_enum_admits_the_overridden_source_and_nothing_else_new() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    enum = schema["$defs"]["repPolicy"]["properties"]["source"]["enum"]
    assert enum == ["packaged-policy", "packaged-policy-overridden", "inline-battery", "unresolved"]


def test_a_row_resolved_as_overridden_validates_and_an_unknown_source_is_refused() -> None:
    from riskvalidation.governance.policy import resolve_policy

    ident, reason = resolve_policy("contraste-liquidity-battery 1.0.0+custom", "liq.survival_monotone_in_severity", None, None,
                                   {"parameters": {"amber": 0.2}})
    assert reason is None and ident["source"] == "packaged-policy-overridden"
    doc = _report()
    assert _errors(doc) == []
    pol = _first_policy(doc)
    pol.update({k: ident[k] for k in ("label", "parameters", "version", "source")})
    assert _errors(doc) == []
    bad = copy.deepcopy(doc)
    _first_policy(bad)["source"] = "packaged-policy-custom"
    assert _errors(bad) != []


def test_the_battery_key_is_not_in_the_schema_and_the_label_keeps_the_token() -> None:
    from riskvalidation.governance.policy import resolve_policy

    ident, _ = resolve_policy("riskvalidation-default 2026.10.1; ml-battery-1.1.0; overfit_tolerance=0.05", "ml.overfitting_gap", None, None)
    assert ident["battery"] == "ml-battery-1.1.0" and "ml-battery-1.1.0" in ident["label"]
    doc = _report()
    _first_policy(doc).update({"label": ident["label"], "parameters": ident["parameters"], "battery": ident["battery"]})
    assert _errors(doc) != [], "the closed policy object refuses the engine key; the bake drops it"


def test_the_fixtures_carry_the_engine_reason_for_an_inline_battery_row() -> None:
    """The 1.0 documents carry packaged battery labels, so the report fixtures hold packaged-policy rows (no inline-battery row remains); the
    policy identity of every one equals ``resolve_policy`` of the engine, and an inline string still carries the engine's NO_POLICY_FILE reason."""
    from riskvalidation.governance import policy

    ident, _ = policy.resolve_policy("contraste-ifrs9-battery-1.0.0; nl_amber=1.0; nl_red=3.0", "ifrs9.scenario_sensitivity", None, None, None)
    assert ident["source"] == "inline-battery" and ident["direction_reason"] == policy.NO_POLICY_FILE
    for name in ("report-C07-banco-andino-fixture.json", "report-C18-banco-andino-fixture.json"):
        doc = json.loads((FIX / name).read_text(encoding="utf-8"))
        rows = next(b for b in doc["sections"][5]["blocks"] if b["kind"] == "outcomes")["rows"]
        packaged = [r for r in rows if r["policy"]["source"] == "packaged-policy" and r["policy"]["label"].startswith("contraste-")]
        assert packaged and not [r for r in rows if r["policy"]["source"] in ("inline-battery", "unresolved")], name
        for r in packaged:
            p = r["policy"]
            got, reason = policy.resolve_policy(p["label"], r["test_id"], p["alpha_amber"], p["alpha_red"], None)
            assert reason is None and got == {k: p[k] for k in got}, (name, r["test_id"])
        assert "BL-085" not in json.dumps(doc), name
