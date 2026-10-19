"""U13-S: the C18 case contracts (ICAAP and IAPE capital aggregation under macro scenarios), their fixtures, the catalog rows and the two
engine API contracts (aggregation and stress).

Scope: C18 only. The U13 sizing decision E1 (2026-10-19) keeps C19 planned, so no C19 schema, fixture, row or supervisory clause exists,
and a test says so.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict both ways (a
removed or an added key fails); the headline capital is the simple sum; a diversified or allocated figure carries its "information, not
capital" label; every marginal records one year and 99.9 percent; a satellite fit window never reaches 2020; a scenario path carries its
vintage and its transposition label; the P2G proxy carries its approximation label; every named parameter carries convention or case
assumption. The cross-field checks are importable functions in ``semantics.py`` that the bake calls on every document it writes; these
tests run them over the fixtures and over a table of planted defects, each refused by the layer the table says (the schema or the
checker). The two engine contracts name every function of the modules table of plans/contraste/units/U13-sizing.md, with a golden value
or an invariant, and their golden values recompute here from the formulas and the transcribed tables. The fixtures are labelled as
fixtures and never published as results.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

import contract_schemas as cs

ROOT = cs.ROOT
FIX = ROOT / "docs" / "contracts" / "fixtures" / "c18"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
ENGINE = ROOT / "docs" / "contracts" / "engine"
AGG_API = ENGINE / "aggregation-api.md"
STRESS_API = ENGINE / "stress-api.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "U13.md"
CHANGES = ROOT / "changes" / "U13-S.md"
THIS = Path(__file__)

SC, AG, RV, MD = "c18/variant-scenario", "c18/variant-aggregation", "c18/variant-reverse", "c18/models"
FILES = {
    "baseline": (SC, FIX / "variant-scenario-baseline-fixture.json"),
    "eba": (SC, FIX / "variant-scenario-eba-2025-adverse-fixture.json"),
    "fed": (SC, FIX / "variant-scenario-fed-2026-severely-adverse-fixture.json"),
    "ngfs": (SC, FIX / "variant-scenario-ngfs-delayed-transition-fixture.json"),
    "aggregation": (AG, FIX / "variant-aggregation-fixture.json"),
    "reverse": (RV, FIX / "variant-reverse-fixture.json"),
    "models": (MD, FIX / "models-fixture.json"),
}
SCENARIO_KEYS = ["baseline", "eba", "fed", "ngfs"]
VARIANT_KEYS = SCENARIO_KEYS + ["aggregation", "reverse"]
ALL = list(FILES)
KINDS = {SC: "scenario", AG: "aggregation", RV: "reverse"}
SCENARIO_IDS = {"baseline": "baseline", "eba": "eba-2025-adverse", "fed": "fed-2026-severely-adverse", "ngfs": "ngfs-delayed-transition"}
RISKS = ["credit", "market", "irrbb", "operational"]
FED_TYPES = ["commercial-industrial", "commercial-real-estate", "residential", "credit-cards", "other-consumer"]

# --- the transcribed tables of the research record, typed here again (U13 research addendum F6 to F8; dossiers 03, 05, 06) ---------------

ANNEX3 = [  # F7: CMF RAN 21-13 Annex 3 rows as printed
    ("1", "Ratios de capital"), ("1.1", "PE / APR"), ("1.2", "T1 / APR"), ("1.3", "CET1 / APR"),
    ("2", "Patrimonio efectivo"), ("2.T2", "T2"), ("2.AT1", "AT1"), ("2.CET1", "CET1"), ("3", "APR"),
    ("4", "Cuantificacion del capital necesario"), ("4.1", "Riesgo de credito"), ("4.1.1", "Metodo estandar"),
    ("4.1.2", "Modelo interno"), ("4.2", "Riesgo de mercado (ME)"), ("4.3", "Riesgo operacional (ME)"),
    ("4.4", "Riesgo de concentracion"), ("4.4.1", "Individual"), ("4.4.2", "Sectorial"), ("4.4.3", "Otro tipo"),
    ("4.5", "RMLB"), ("4.6", "Riesgo estrategico"), ("4.7", "Riesgo reputacional"), ("4.8", "Otros riesgos materiales"),
    ("5", "OI"),
    ("6", "Cuantificacion del capital necesario por riesgos no cubiertos en pilar 1 (4.4+4.5+4.6+4.7+4.8)"),
    ("7", "Exigencia minima de PE, en periodo de planificacion (8%+7.1+7.2)"),
    ("7.1", "Exigencia adicional de PE por art.66 quater (banco sistemico)"),
    ("7.2", "Exigencia adicional de PE por art.66 quinquies"),
    ("8", "Cuantificacion del capital necesario por riesgos no cubiertos en pilar 1, y no exigidos por art.66 quinquies (6-7.2)"),
    ("9", "Colchones de conservacion y contra ciclico, en periodo de planificacion (art.66 bis y 66 ter)"),
    ("10.1", "Impacto en indice de capital basico de las pruebas de tension severas, sin mitigacion"),
    ("10.2", "Impacto en indice de capital basico de las pruebas de tension severas, con mitigacion"),
    ("11", "Componente d) del OI"),
    ("12", "Holgura de indice de patrimonio efectivo respecto del OI (1.1 - 5)"),
]
NGFS_VARS = [  # F8: names and units as printed (the GDP unit has two spaces)
    ("Unemployment rate ; %(combined)", "Abs. difference"),
    ("Central bank Intervention rate (policy interest rate) ; %(combined)", "Abs. difference"),
    ("Long term interest rate ; %(combined)", "Abs. difference"),
    ("Gross Domestic Product (GDP)(combined)", "% difference,  2017 PPP ; US$ Bn"),
]
EBA_PARAGRAPHS = {"24": 16, "33": 18, "34": 18, "90": 36, "91": 36, "92": 37}  # F6: paragraph and printed page
AGENCY = ["real_gdp_growth", "unemployment_rate", "cpi_inflation", "treasury_3m", "treasury_5y", "treasury_10y", "mortgage_rate", "prime_rate"]
SANTANDER = {  # dossier 03 l.1324-1328 (20-F, Ch$ million): ratios only enter the documents
    "rwa": 41_715_467, "credit": 29_551_588, "market": 7_143_966, "operational": 5_019_913, "cet1": 4_601_923, "pe": 7_047_321,
    "ccob": 1_042_887, "ccyb": 208_577, "dsib": 625_732, "p2r": 52_144,
}


def sm():
    """The checker module, imported when a test needs it (the contract tests read committed JSON and call it by name)."""
    import semantics
    return semantics


def load(key: str) -> Any:
    return cs.load_json(FILES[key][1])


def out(key: str) -> dict:
    return load(key)["outputs"]


def fit() -> dict:
    return load("models")["fit"]


def root_of(ref: str) -> str:
    return "outputs" if "variant" in ref else "fit"


# --- the fixtures -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL)
def test_the_fixture_exists_and_is_discovered_by_exactly_one_schema(key: str) -> None:
    ref, path = FILES[key]
    assert path.is_file(), path
    doc = cs.load_json(path)
    assert cs.schema_for_document(path, doc) == ref
    assert cs.errors(ref, doc) == []
    passing = [c.ref for c in cs.candidates() if cs.errors(c.ref, doc) == []]
    assert passing == [ref], f"{path.name}: validates against {passing}"


@pytest.mark.parametrize("key", ALL)
def test_the_fixture_is_labelled_as_a_fixture(key: str) -> None:
    ref, path = FILES[key]
    doc = load(key)
    assert doc["provenance"]["generators"] == ["fixture:u13-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    assert doc["provenance"]["truth_status"] == "synthetic-calibrated"
    ident = doc["variant_id"] if "variant" in ref else doc["fit_id"]
    assert str(ident).startswith("fixture-")
    assert doc["case_id"] == "C18"


def test_every_u13_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted((SCHEMAS / "c18").glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {f"{r}.schema.json" for r in (SC, AG, RV, MD)}
    for p in files:
        for name in cs.load_json(p).get("$defs", {}):
            assert name.startswith("c18"), f"{p.name}: $defs name {name!r} is not prefixed 'c18'"


def test_a_def_two_files_share_has_one_definition() -> None:
    defs: dict[str, tuple[str, Any]] = {}
    for p in sorted((SCHEMAS / "c18").glob("*.schema.json")):
        for name, body in cs.load_json(p).get("$defs", {}).items():
            if name in defs:
                assert defs[name][1] == body, f"{name} differs between {defs[name][0]} and {p.name}"
            defs.setdefault(name, (p.name, body))


def test_the_variant_schemas_declare_their_outputs_kind_and_none_is_a_default() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    for ref, kind in KINDS.items():
        assert by_ref[ref].consts["outputs.kind"] == kind, ref
        assert by_ref[ref].consts["case_id"] == "C18"
    assert by_ref[MD].consts["case_id"] == "C18"
    assert cs.default_variants().get("C18") is None
    assert cs.default_violations() == []


def test_a_second_kind_less_variant_schema_fails() -> None:
    a = cs.Candidate.from_parts("c18/variant-planted", {"schema": "contraste.case/v1", "case_id": "C18"})
    b = cs.Candidate.from_parts("c18/variant-planted2", {"schema": "contraste.case/v1", "case_id": "C18"})
    assert cs.default_violations(cs.candidates() + (a, b)) != []


def test_c19_stays_planned_nothing_of_it_is_written() -> None:
    """Decision E1 of the U13 sizing (2026-10-19): no C19 schema, fixture, catalog row, supervisory clause or definition."""
    assert not (SCHEMAS / "c19").exists()
    assert not (ROOT / "docs" / "contracts" / "fixtures" / "c19").exists()
    for p in (SCHEMAS / "c18").glob("*.schema.json"):
        text = p.read_text(encoding="utf-8")
        assert "c19" not in text.lower() and "C19" not in text, p.name
    api = STRESS_API.read_text(encoding="utf-8")
    assert "stress/supervisory.py" not in api.replace("`riskvalidation/stress/supervisory.py` is void", "")
    assert "E1" in api and "supervisory" in api, "the stress contract says why the supervisory module is absent"
    rows = ROWS.read_text(encoding="utf-8")
    assert "c19-outputs" not in rows and "c19-models" not in rows


# --- strictness ---------------------------------------------------------------------------------------------------


def objects(node: Any, path: tuple = ()) -> Iterator[tuple[tuple, dict]]:
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from objects(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from objects(v, path + (i,))


def get(doc: Any, path: tuple) -> Any:
    for p in path:
        doc = doc[p]
    return doc


def closed_objects(key: str) -> list[tuple[tuple, dict]]:
    ref, _ = FILES[key]
    doc = load(key)
    return list(objects(doc[root_of(ref)], (root_of(ref),)))


GROUPS = {"scenario": SCENARIO_KEYS, "aggregation": ["aggregation"], "reverse": ["reverse"], "models": ["models"]}


def distinct_targets(keys: list[str]) -> list[tuple[str, tuple, str]]:
    """The (document, object path, key) triples of every shape the documents of a group have: the objects of one array share a shape, so
    only the first item of an array is visited, and a shape that two documents share is visited in the first."""
    seen: set[tuple] = set()
    out: list[tuple[str, tuple, str]] = []
    for key in keys:
        for p, obj in closed_objects(key):
            shape = tuple("*" if isinstance(x, int) else x for x in p)
            if any(isinstance(x, int) and x > 0 for x in p):
                continue
            for k in obj:
                if (shape, k) not in seen:
                    seen.add((shape, k))
                    out.append((key, p, k))
    return out


@pytest.mark.parametrize("group", GROUPS)
def test_a_key_removed_from_any_object_fails(group: str) -> None:
    targets = distinct_targets(GROUPS[group])
    for key, p, k in targets:
        ref, path = FILES[key]
        bad = load(key)
        del get(bad, p)[k]
        assert cs.errors(ref, bad) != [], f"{path.name}: removing {'/'.join(map(str, p))}/{k} still validates"
    assert len(targets) > {"scenario": 300, "aggregation": 150, "reverse": 60, "models": 150}[group]


@pytest.mark.parametrize("group", GROUPS)
def test_a_key_added_to_any_object_fails(group: str) -> None:
    objs = {(key, p) for key, p, _ in distinct_targets(GROUPS[group])}
    assert len(objs) > 15
    for key, p in sorted(objs, key=lambda t: (t[0], [str(x) for x in t[1]])):
        ref, path = FILES[key]
        bad = load(key)
        get(bad, p)["unknown_key"] = 1
        assert cs.errors(ref, bad) != [], f"{path.name}: adding a key at {'/'.join(map(str, p))} still validates"


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_a_document_without_case_id_or_outputs_kind_does_not_pass(key: str) -> None:
    ref, path = FILES[key]
    doc = load(key)
    no_case = copy.deepcopy(doc)
    del no_case["case_id"]
    assert cs.errors(ref, no_case) != []
    with pytest.raises(cs.SelectionError):
        cs.schema_for_document(path, no_case)
    no_kind = copy.deepcopy(doc)
    del no_kind["outputs"]["kind"]
    assert cs.errors(ref, no_kind) != []
    chosen = None
    try:
        chosen = cs.schema_for_document(path, no_kind)
    except cs.SelectionError:
        pass
    assert chosen != ref
    if chosen is not None:
        assert cs.errors(chosen, no_kind) != []


@pytest.mark.parametrize("key", ALL)
def test_a_wrong_case_id_is_rejected(key: str) -> None:
    ref, _ = FILES[key]
    doc = load(key)
    doc["case_id"] = "C19"
    assert cs.errors(ref, doc) != []


@pytest.mark.parametrize("key", ALL)
def test_a_fixture_of_one_case_does_not_validate_against_another_case(key: str) -> None:
    ref, _ = FILES[key]
    doc = load(key)
    others = [c.ref for c in cs.candidates() if c.ref != ref and c.ref.split("/")[0] in ("c10", "c11", "c15", "c17", "c18")]
    assert others
    for other in others:
        assert cs.errors(other, doc) != [], f"{ref} fixture validates against {other}"


def test_the_four_documents_do_not_validate_as_each_other() -> None:
    for a in ALL:
        for b in ALL:
            if a != b and FILES[a][0] != FILES[b][0]:
                assert cs.errors(FILES[b][0], load(a)) != [], f"{a} validates as {FILES[b][0]}"


@pytest.mark.parametrize("key", ALL)
def test_the_truth_status_is_synthetic_calibrated_by_schema(key: str) -> None:
    ref, _ = FILES[key]
    for status in ("real-outcomes", "synthetic-known-truth", "published-answer"):
        bad = load(key)
        bad["provenance"]["truth_status"] = status
        assert cs.errors(ref, bad) != [], status


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_the_impact_keys_are_required(key: str) -> None:
    doc = load(key)
    for k in ("capital_simple_sum", "cet1_ratio_end_stress", "oi_headroom_min", "p2g_proxy"):
        bad = copy.deepcopy(doc)
        del bad["impact"][k]
        assert cs.errors(SC, bad) != [], k


# --- the invariants the schema states -----------------------------------------------------------------------------


def set_at(doc: dict, path: str, value: Any) -> dict:
    node = doc
    parts = path.split("/")
    for p in parts[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value
    return doc


def drop_at(doc: dict, path: str) -> dict:
    node = doc
    parts = path.split("/")
    for p in parts[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    if isinstance(node, list):
        del node[int(parts[-1])]
    else:
        del node[parts[-1]]
    return doc


def band_index(doc_out: dict, method: str, nu: float | None = None) -> int:
    for i, r in enumerate(doc_out["aggregation"]["band"]):
        if r["method"] == method and (nu is None or r["nu"] == nu):
            return i
    raise AssertionError(method)


def test_the_headline_capital_must_be_the_simple_sum_by_schema() -> None:
    for key in SCENARIO_KEYS:
        bad = load(key)
        for method in ("variance-covariance", "gaussian-copula", "t-copula", "worst-case", "lower-bound"):
            bad["outputs"]["aggregation"]["headline"]["method"] = method
            assert cs.errors(SC, bad) != [], f"{key}: headline method {method} validates"
    bad = load("aggregation")
    bad["outputs"]["aggregation"]["headline"]["method"] = "gaussian-copula"
    assert cs.errors(AG, bad) != []
    bad = load("aggregation")
    bad["outputs"]["correlation_stress"]["aggregation"]["headline"]["method"] = "t-copula"
    assert cs.errors(AG, bad) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_every_diversified_figure_carries_its_information_not_capital_label(key: str) -> None:
    doc = load(key)
    agg = doc["outputs"]["aggregation"]
    diversified = [i for i, r in enumerate(agg["band"]) if r["method"] != "simple-sum"]
    assert len(diversified) >= 5
    for i in diversified:
        base = f"outputs/aggregation/band/{i}"
        for field in ("label", "status"):
            assert cs.errors(SC, drop_at(copy.deepcopy(doc), f"{base}/{field}")) != [], f"band row {i} without {field} validates"
        assert cs.errors(SC, set_at(copy.deepcopy(doc), f"{base}/status", "headline-capital")) != [], f"band row {i} passes as headline capital"
    sums = [i for i, r in enumerate(agg["band"]) if r["method"] == "simple-sum"]
    assert len(sums) == 1
    assert cs.errors(SC, set_at(copy.deepcopy(doc), f"outputs/aggregation/band/{sums[0]}/status", "information-not-capital")) != []
    for block in ("euler", "diversification", "model_risk"):
        for field in ("label", "status"):
            assert cs.errors(SC, drop_at(copy.deepcopy(doc), f"outputs/aggregation/{block}/{field}")) != [], f"{block} without {field} validates"
        assert cs.errors(SC, set_at(copy.deepcopy(doc), f"outputs/aggregation/{block}/status", "capital")) != [], block


def test_the_aggregation_variant_labels_its_stressed_band_and_the_reference_run() -> None:
    doc = load("aggregation")
    stressed = doc["outputs"]["correlation_stress"]["aggregation"]
    for i, r in enumerate(stressed["band"]):
        if r["method"] != "simple-sum":
            assert cs.errors(AG, set_at(copy.deepcopy(doc), f"outputs/correlation_stress/aggregation/band/{i}/status", "headline-capital")) != []
    assert cs.errors(AG, set_at(copy.deepcopy(doc), "outputs/rosenberg_schuermann/role", "gate")) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS + ["aggregation"])
def test_a_marginal_with_another_horizon_or_confidence_level_fails(key: str) -> None:
    ref, _ = FILES[key]
    doc = load(key)
    where = "outputs/aggregation" if key != "aggregation" else "outputs/aggregation"
    for i in range(4):
        for field, value in (("horizon_years", 10), ("horizon_years", 0.25), ("confidence_level", 0.99), ("confidence_level", 0.9995)):
            assert cs.errors(ref, set_at(copy.deepcopy(doc), f"{where}/marginals/{i}/{field}", value)) != [], f"{key}: marginal {i} {field}={value}"
    for field, value in (("horizon_years", 10), ("confidence_level", 0.99)):
        assert cs.errors(ref, set_at(copy.deepcopy(doc), f"{where}/{field}", value)) != []
    for i, r in enumerate(doc["outputs"]["aggregation"]["band"]):
        assert cs.errors(ref, set_at(copy.deepcopy(doc), f"{where}/band/{i}/horizon_years", 5)) != []
        assert cs.errors(ref, set_at(copy.deepcopy(doc), f"{where}/band/{i}/confidence_level", 0.99)) != []
    assert cs.errors(ref, set_at(copy.deepcopy(doc), f"{where}/euler/level", 0.99)) != []
    assert cs.errors(ref, set_at(copy.deepcopy(doc), f"{where}/euler/horizon_years", 10)) != []


def test_a_marginal_states_its_source_and_its_scaling() -> None:
    doc = out("baseline")["aggregation"]["marginals"]
    assert [m["risk"] for m in doc] == RISKS
    producers = {m["risk"]: m["producer"] for m in doc}
    assert producers == {
        "credit": "credit-grouped-copula-c07-segments", "market": "market-c11-mixed-portfolio-scaled-to-market-rwa",
        "irrbb": "irrbb-engine-simulation-c15-curve-and-book", "operational": "operational-oprisk-aggregate-c17-parameters-scaled",
    }
    for i, m in enumerate(doc):
        for field in ("producer", "source_documents", "scaling"):
            assert cs.errors(SC, drop_at(load("baseline"), f"outputs/aggregation/marginals/{i}/{field}")) != []
    bad = load("baseline")
    bad["outputs"]["aggregation"]["marginals"][0]["producer"] = "operational-oprisk-aggregate-c17-parameters-scaled"
    assert cs.errors(SC, bad) != [], "a credit marginal cannot name the operational producer"
    scaling = {m["risk"]: [p["name"] for p in m["scaling"]["parameters"]] for m in doc}
    assert scaling["operational"] == ["asset_scaling", "operational_conversion_rate"]
    assert scaling["market"] == ["market_rwa_share", "market_horizon_scaling"]
    assert scaling["credit"] == [] and scaling["irrbb"] == []


@pytest.mark.parametrize("path,where", [
    ("fit/satellites/0/sample_window/end", "models"), ("fit/satellites/3/sample_window/end", "models"),
    ("fit/factor_space/window/end", "models"), ("outputs/factor_space/window/end", "reverse"),
])
@pytest.mark.parametrize("bad_date", ["2020-03-31", "2020-12-31", "2021-06-30", "2025-12-31"])
def test_a_satellite_window_that_reaches_2020_or_later_fails(path: str, where: str, bad_date: str) -> None:
    ref, _ = FILES[where]
    assert cs.errors(ref, set_at(load(where), path, bad_date)) != []
    assert cs.errors(ref, set_at(load(where), path.replace("/end", "/start"), bad_date)) != []


def test_a_window_before_1985_or_off_the_quarter_end_fails_and_the_boundaries_pass() -> None:
    doc = load("models")
    assert cs.errors(MD, set_at(copy.deepcopy(doc), "fit/satellites/0/sample_window/start", "1984-12-31")) != []
    assert cs.errors(MD, set_at(copy.deepcopy(doc), "fit/satellites/0/sample_window/end", "2019-11-30")) != []
    assert cs.errors(MD, set_at(copy.deepcopy(doc), "fit/satellites/0/sample_window/end", "2019-12-31")) == []
    assert cs.errors(MD, set_at(copy.deepcopy(doc), "fit/satellites/0/sample_window/start", "1985-03-31")) == []
    for key in SCENARIO_KEYS:
        for i in range(5):
            bad = set_at(load(key), f"outputs/backcast/per_loan_type/{i}/fit_window/end", "2020-03-31")
            assert cs.errors(SC, bad) != [], key


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_a_scenario_path_without_its_vintage_or_transposition_label_fails(key: str) -> None:
    doc = load(key)
    n = len(doc["outputs"]["scenario"]["paths"])
    assert n >= 3
    for i in range(n):
        base = f"outputs/scenario/paths/{i}"
        for field in ("vintage_date", "transposition", "source", "levels", "transposed", "maps_to_regressor", "level_rule"):
            assert cs.errors(SC, drop_at(copy.deepcopy(doc), f"{base}/{field}")) != [], f"path {i} without {field} validates"
        for field in ("label", "rule", "source_jump_off", "target", "reversion"):
            assert cs.errors(SC, drop_at(copy.deepcopy(doc), f"{base}/transposition/{field}")) != [], f"transposition without {field}"
        assert cs.errors(SC, set_at(copy.deepcopy(doc), f"{base}/transposition/label", "as-published")) != []
        assert cs.errors(SC, set_at(copy.deepcopy(doc), f"{base}/transposed", doc["outputs"]["scenario"]["paths"][i]["transposed"][:11])) != []
    for field in ("vintage_date", "source_document", "source_url", "adaptation_label", "adaptation_statement"):
        assert cs.errors(SC, drop_at(copy.deepcopy(doc), f"outputs/scenario/{field}")) != []
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/scenario/adaptation_label", "native")) != []


def test_a_deviation_path_carries_its_baseline_and_a_level_path_has_none() -> None:
    doc = load("ngfs")
    kinds = [p["level_rule"]["kind"] for p in doc["outputs"]["scenario"]["paths"]]
    assert set(kinds) == {"baseline-plus-deviation", "baseline-times-percent-deviation"} and len(kinds) == 4
    bad = set_at(copy.deepcopy(doc), "outputs/scenario/paths/0/level_rule/baseline", None)
    assert cs.errors(SC, bad) != []
    bad = set_at(copy.deepcopy(doc), "outputs/scenario/paths/0/level_rule/kind", "level")
    assert cs.errors(SC, bad) != []
    bad = set_at(copy.deepcopy(doc), "outputs/scenario/paths/0/level_rule/kind", "baseline-minus-deviation")
    assert cs.errors(SC, bad) != []
    fed = load("fed")
    assert {p["level_rule"]["kind"] for p in fed["outputs"]["scenario"]["paths"]} == {"level"}
    bad = set_at(copy.deepcopy(fed), "outputs/scenario/paths/0/level_rule", {"kind": "level", "baseline": fed["outputs"]["scenario"]["paths"][0]["source"]})
    assert cs.errors(SC, bad) != [], "a level path has no baseline to add"


def test_the_ngfs_scenario_carries_its_policy_window_and_no_other_scenario_does() -> None:
    ngfs = load("ngfs")
    assert ngfs["outputs"]["scenario"]["provider"] == "ngfs"
    assert ngfs["outputs"]["scenario"]["policy_shock_window"] is not None
    assert cs.errors(SC, set_at(copy.deepcopy(ngfs), "outputs/scenario/policy_shock_window", None)) != []
    for key in ("baseline", "eba", "fed"):
        doc = load(key)
        assert doc["outputs"]["scenario"]["policy_shock_window"] is None
        bad = set_at(copy.deepcopy(doc), "outputs/scenario/policy_shock_window",
                     copy.deepcopy(ngfs["outputs"]["scenario"]["policy_shock_window"]))
        assert cs.errors(SC, bad) != [], key
    eba = load("eba")
    assert eba["outputs"]["scenario"]["provider"] == "eba-esrb"
    assert cs.errors(SC, set_at(copy.deepcopy(eba), "outputs/scenario/provider", "fed")) != []
    assert cs.errors(SC, set_at(copy.deepcopy(load("fed")), "outputs/scenario/provider", "eba-esrb")) != []
    assert cs.errors(SC, set_at(copy.deepcopy(ngfs), "outputs/scenario/provider", "fed")) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_the_p2g_proxy_carries_its_approximation_label(key: str) -> None:
    doc = load(key)
    for field in ("label", "formula", "statement", "cmf_calibration_public"):
        assert cs.errors(SC, drop_at(copy.deepcopy(doc), f"outputs/p2g_proxy/{field}")) != []
    for bad in ("regulatory-requirement", "cmf-calibrated", "approximation"):
        assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/p2g_proxy/label", bad)) != []
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/p2g_proxy/cmf_calibration_public", True)) != []
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/p2g_proxy/value", -0.01)) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_the_mitigation_block_is_coupled_to_its_actions(key: str) -> None:
    doc = load(key)
    m = doc["outputs"]["capital_plan"]["mitigation"]
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/capital_plan/mitigation/actions", [])) != [] or m["applies"] is False
    bad = set_at(copy.deepcopy(doc), "outputs/capital_plan/mitigation/applies", not m["applies"])
    assert cs.errors(SC, bad) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["capital_plan"]["mitigation"] = {"applies": False, "reason": None, "actions": []}
    assert cs.errors(SC, bad) != [], "no mitigation without its reason"
    bad = copy.deepcopy(doc)
    bad["outputs"]["capital_plan"]["mitigation"] = {"applies": True, "reason": None, "actions": []}
    assert cs.errors(SC, bad) != [], "mitigation applies but no action is named"


def test_the_three_cases_of_the_plan_are_the_base_and_the_two_stresses_with_their_requirement_basis() -> None:
    doc = load("fed")
    cases = {c["case"]: c for c in doc["outputs"]["capital_plan"]["cases"]}
    assert set(cases) == {"base", "stress-without-mitigation", "stress-with-mitigation"}
    assert all(y["requirement"]["basis"] == "internal-target" for y in cases["base"]["years"])
    for k in ("stress-without-mitigation", "stress-with-mitigation"):
        assert all(y["requirement"]["basis"] == "legal-minimum" for y in cases[k]["years"])
    bad = copy.deepcopy(doc)
    bad["outputs"]["capital_plan"]["cases"][1]["years"][0]["requirement"]["basis"] = "internal-target"
    assert cs.errors(SC, bad) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["capital_plan"]["cases"] = bad["outputs"]["capital_plan"]["cases"][:2]
    assert cs.errors(SC, bad) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_the_annex3_summary_has_the_34_rows_of_the_cmf_form_each_once(key: str) -> None:
    doc = load(key)
    rows = doc["outputs"]["annex3"]["rows"]
    assert [r["row_id"] for r in rows] == [i for i, _ in ANNEX3]
    assert [r["label_cmf"] for r in rows] == [lab for _, lab in ANNEX3]
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/annex3/rows", rows[:-1])) != []
    dup = rows[:-1] + [copy.deepcopy(rows[0])]
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/annex3/rows", dup)) != []
    bad = set_at(copy.deepcopy(doc), "outputs/annex3/rows/0/row_id", "13")
    assert cs.errors(SC, bad) != []
    bad = set_at(copy.deepcopy(doc), "outputs/annex3/rows/4/a", {"value": None, "status": "value"})
    assert cs.errors(SC, bad) != [], "a value cell without a value"
    bad = set_at(copy.deepcopy(doc), "outputs/annex3/rows/4/a", {"value": 1.0, "status": "RI"})
    assert cs.errors(SC, bad) != [], "an RI cell with a value"
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/annex3/money_unit", "CLP thousands")) != []


def test_the_annex3_labels_are_the_cmf_text() -> None:
    doc = load("baseline")
    assert sm().ANNEX3_ROWS == ANNEX3
    bad = set_at(copy.deepcopy(doc), "outputs/annex3/rows/9/label_cmf", "Capital necesario")
    assert cs.errors(SC, bad) == []
    assert sm().violations(bad) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_the_ppnr_row_is_labelled_and_the_headline_is_loss_only(key: str) -> None:
    doc = load(key)
    h = doc["outputs"]["headline_cet1"]
    assert h["method"] == "loss-only-depletion"
    assert h["ppnr"]["label"] == "ppnr-labelled-row"
    for field in ("label", "statement", "nii_source", "fee_ratio", "cost_ratio", "rows"):
        assert cs.errors(SC, drop_at(copy.deepcopy(doc), f"outputs/headline_cet1/ppnr/{field}")) != []
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/headline_cet1/method", "with-ppnr")) != []
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/headline_cet1/ppnr/label", "headline")) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_the_backcast_covers_2020q1_to_2025q4_and_2026_is_rate_only(key: str) -> None:
    doc = load(key)
    b = doc["outputs"]["backcast"]
    assert b["window"] == {"start": "2020-03-31", "end": "2025-12-31"}
    assert [r["fed_loan_type"] for r in b["per_loan_type"]] == FED_TYPES
    for i, r in enumerate(b["per_loan_type"]):
        assert len(r["quarters"]) == 24
        assert r["quarters"][0]["quarter_end"] == "2020-03-31" and r["quarters"][-1]["quarter_end"] == "2025-12-31"
        assert cs.errors(SC, set_at(copy.deepcopy(doc), f"outputs/backcast/per_loan_type/{i}/quarters", r["quarters"][:23])) != []
    assert [r["quarter_end"] for r in b["descriptive_2026"]] == ["2026-03-31", "2026-06-30"]
    for i in range(2):
        d = f"outputs/backcast/descriptive_2026/{i}"
        assert cs.errors(SC, set_at(copy.deepcopy(doc), f"{d}/forecast_claim", True)) != []
        assert cs.errors(SC, set_at(copy.deepcopy(doc), f"{d}/label", "forecast")) != []
        bad = copy.deepcopy(doc)
        bad["outputs"]["backcast"]["descriptive_2026"][i]["predicted"] = 0.01
        assert cs.errors(SC, bad) != [], "a 2026 row carries no forecast"
    assert cs.errors(SC, set_at(copy.deepcopy(doc), "outputs/backcast/window/end", "2026-06-30")) != []


# --- the named parameters -----------------------------------------------------------------------------------------

NAMED = ["nu_set", "correlation_matrix_base", "correlation_matrix_stress", "ppnr_fee_ratio", "ppnr_cost_ratio", "c_p2", "c_d",
         "operational_conversion_rate", "asset_scaling", "market_rwa_share", "market_horizon_scaling", "reverse_p2_cet1"]


def test_every_named_parameter_is_required_with_its_value_and_a_label_that_is_never_regulatory() -> None:
    doc = load("models")
    named = doc["fit"]["named_parameters"]
    assert list(named) == NAMED
    for name in NAMED:
        entry = named[name]
        assert entry["label"] in ("convention", "case assumption"), name
        assert entry["name"] == name
        assert ("values" in entry) == (name == "nu_set") and ("matrix" in entry) == name.startswith("correlation_matrix")
        base = f"fit/named_parameters/{name}"
        assert cs.errors(MD, drop_at(copy.deepcopy(doc), base)) != [], f"{name} is optional"
        assert cs.errors(MD, drop_at(copy.deepcopy(doc), f"{base}/label")) != [], f"{name} passes without its label"
        for bad in ("regulatory", "Regulatory", "regulatory value", "legal", ""):
            assert cs.errors(MD, set_at(copy.deepcopy(doc), f"{base}/label", bad)) != [], f"{name} label {bad!r}"
        value_key = "values" if name == "nu_set" else "matrix" if name.startswith("correlation_matrix") else "value"
        assert cs.errors(MD, drop_at(copy.deepcopy(doc), f"{base}/{value_key}")) != [], f"{name} passes without its value"
        assert cs.errors(MD, drop_at(copy.deepcopy(doc), f"{base}/basis")) != []
        assert cs.errors(MD, drop_at(copy.deepcopy(doc), f"{base}/unit")) != []


def test_a_named_parameter_used_by_a_variant_carries_its_label_there_too() -> None:
    uses = {
        "baseline": [("outputs/internal_capital_target/c_p2", "case assumption"), ("outputs/internal_capital_target/c_d", "case assumption"),
                     ("outputs/headline_cet1/ppnr/fee_ratio", "case assumption"), ("outputs/headline_cet1/ppnr/cost_ratio", "case assumption"),
                     ("outputs/aggregation/correlation", "convention"), ("outputs/aggregation/nu_set", "convention"),
                     ("outputs/aggregation/marginals/3/scaling/parameters/0", "case assumption"),
                     ("outputs/aggregation/marginals/1/scaling/parameters/1", "case assumption")],
        "aggregation": [("outputs/aggregation/correlation", "convention"), ("outputs/aggregation/nu_set", "convention"),
                        ("outputs/correlation_stress/aggregation/correlation", "convention")],
        "reverse": [("outputs/failure_point/stack/p2_cet1", "case assumption")],
    }
    for key, items in uses.items():
        ref, _ = FILES[key]
        doc = load(key)
        for path, expected in items:
            node = doc
            for p in path.split("/"):
                node = node[int(p)] if isinstance(node, list) else node[p]
            assert node["label"] == expected, f"{key} {path}"
            assert cs.errors(ref, drop_at(copy.deepcopy(doc), f"{path}/label")) != [], f"{key} {path} passes without its label"
            assert cs.errors(ref, set_at(copy.deepcopy(doc), f"{path}/label", "regulatory")) != [], f"{key} {path} label regulatory"


@pytest.mark.parametrize("bad", ["bbb_corporate_yield", "house_price_index", "commercial_real_estate_price_index", "dow_jones_total_stock_market_index",
                                 "market_volatility_index", "vix", "equity_index"])
def test_a_satellite_that_reads_a_third_party_series_fails_agency_series_only(bad: str) -> None:
    doc = load("models")
    for i in range(5):
        assert cs.errors(MD, set_at(copy.deepcopy(doc), f"fit/satellites/{i}/regressors/0/name", bad)) != []
    assert cs.errors(MD, set_at(copy.deepcopy(doc), "fit/satellites/0/regressors/0/licence_class", "third-party")) != []
    for scenario in ("fed", "eba"):
        d = load(scenario)
        assert cs.errors(SC, set_at(copy.deepcopy(d), "outputs/scenario/paths/0/maps_to_regressor", bad)) != []
    assert cs.errors(RV, set_at(load("reverse"), "outputs/factor_space/factors/0/id", bad)) != []
    names = {r["name"] for s in fit()["satellites"] for r in s["regressors"]}
    assert names <= set(AGENCY)


def test_the_bank_anchors_are_ratios_only_and_derived_only() -> None:
    doc = load("models")
    a = doc["fit"]["bank_anchors"]
    assert a["licence_class"] == "derived-only" and a["ratios_only"] is True
    assert cs.errors(MD, set_at(copy.deepcopy(doc), "fit/bank_anchors/licence_class", "mirror-allowed")) != []
    assert cs.errors(MD, set_at(copy.deepcopy(doc), "fit/bank_anchors/ratios_only", False)) != []
    assert abs(sum(a["rwa_mix"].values()) - 1.0) < 1e-6
    for k in ("rwa", "cet1", "pe"):
        assert str(SANTANDER[k]) not in json.dumps(doc), "the 20-F absolute figures are not in the documents"
    assert a["rwa_basis"]["cet1_ratio_anchor"] == pytest.approx(0.11, abs=0.0005)
    assert cs.errors(MD, set_at(copy.deepcopy(doc), "fit/bank_anchors/chilean_stack/p2_cap", 0.05)) != []


def test_the_scenario_sources_carry_their_licence_class_and_the_ngfs_variables() -> None:
    doc = load("models")
    sources = {s["scenario_id"]: s for s in doc["fit"]["scenario_sources"]}
    assert set(sources) == set(SCENARIO_IDS.values())
    assert sources["ngfs-delayed-transition"]["licence_class"] == "derived-only"
    assert sources["fed-2026-severely-adverse"]["licence_class"] == "mirror-allowed"
    assert sources["eba-2025-adverse"]["licence_class"] == "mirror-allowed"
    assert [(v["name"], v["unit"]) for v in sources["ngfs-delayed-transition"]["variables"]] == NGFS_VARS
    assert sources["fed-2026-severely-adverse"]["variables"] == []


def test_the_eba_rules_of_the_capital_engine_cite_their_paragraph_and_page() -> None:
    rules = {r["paragraph"]: r for r in fit()["capital_engine"]["rules"]}
    assert set(EBA_PARAGRAPHS) <= set(rules)
    for para, page in EBA_PARAGRAPHS.items():
        assert rules[para]["page"] == page, para
    assert fit()["capital_engine"]["balance_sheet"] == "static"


def test_the_ngfs_variable_names_are_the_nigem_names_of_the_record() -> None:
    names = {p["variable"]: p["unit"] for p in out("ngfs")["scenario"]["paths"]}
    assert dict(NGFS_VARS) == names
    w = out("ngfs")["scenario"]["policy_shock_window"]
    assert (w["start_year"], w["end_year"]) == (2031, 2033)


# --- the reverse variant ------------------------------------------------------------------------------------------


def test_the_reverse_document_has_the_failure_point_the_scenario_its_distance_plausibility_and_loss() -> None:
    o = out("reverse")
    assert o["failure_point"]["stack"]["basis"] == "chilean-legal-minimum-stack"
    assert o["failure_point"]["label"] == "contraste-formulation-not-regulatory"
    s = o["solution"]
    for k in ("z_star", "x_star", "mahalanobis_distance", "plausibility", "loss_at_z_star_clp_m", "loss_threshold_clp_m"):
        assert k in s
        assert cs.errors(RV, drop_at(load("reverse"), f"outputs/solution/{k}")) != []
    for k in ("label", "stack", "cet1_ratio_start", "rwa_clp_m", "definition", "horizon_years"):
        assert cs.errors(RV, drop_at(load("reverse"), f"outputs/failure_point/{k}")) != []
    assert cs.errors(RV, set_at(load("reverse"), "outputs/failure_point/label", "regulatory")) != []
    assert cs.errors(RV, set_at(load("reverse"), "outputs/failure_point/stack/basis", "basel-minimum")) != []
    assert cs.errors(RV, set_at(load("reverse"), "outputs/starts", o["starts"][:2])) != []
    bad = set_at(load("reverse"), "outputs/loss_model/gradient_clp_m_per_unit", None)
    assert cs.errors(RV, bad) != [], "a linear loss carries its gradient"


# --- the layering of every defect: the schema or the checker -------------------------------------------------------


def mut(path: str, fn: Callable[[Any], Any]) -> Callable[[dict], dict]:
    def apply(doc: dict) -> dict:
        node = doc
        parts = path.split("/")
        for p in parts[:-1]:
            node = node[int(p)] if isinstance(node, list) else node[p]
        last = parts[-1]
        if isinstance(node, list):
            node[int(last)] = fn(node[int(last)])
        else:
            node[last] = fn(node[last])
        return doc
    return apply


def scale(factor: float) -> Callable[[Any], Any]:
    return lambda v: v * factor


def plus(amount: float) -> Callable[[Any], Any]:
    return lambda v: v + amount


def const(value: Any) -> Callable[[Any], Any]:
    return lambda _v: value


def find_band(doc: dict, method: str, nu: float | None = None, root: tuple = ("outputs", "aggregation")) -> str:
    node = doc
    for p in root:
        node = node[p]
    for i, r in enumerate(node["band"]):
        if r["method"] == method and (nu is None or r["nu"] == nu):
            return "/".join(root) + f"/band/{i}"
    raise AssertionError(method)


def band_plant(method: str, field: str, fn: Callable[[Any], Any], nu: float | None = None, root: tuple = ("outputs", "aggregation")):
    def apply(doc: dict) -> dict:
        return mut(f"{find_band(doc, method, nu, root)}/{field}", fn)(doc)
    return apply


# (id, document key, mutation, layer that must refuse it: "schema" or "semantic")
PLANTS: list[tuple[str, str, Callable[[dict], dict], str]] = [
    ("headline-not-simple-sum", "fed", mut("outputs/aggregation/headline/method", const("variance-covariance")), "schema"),
    ("headline-capital-differs-from-the-sum", "fed", mut("outputs/aggregation/headline/capital_clp_m", plus(1000.0)), "semantic"),
    ("simple-sum-row-differs-from-the-sum", "fed", band_plant("simple-sum", "capital_clp_m", plus(500.0)), "semantic"),
    ("diversified-row-without-label", "fed", lambda d: drop_key(d, find_band(d, "gaussian-copula") + "/label"), "schema"),
    ("diversified-row-passes-as-headline", "fed", band_plant("variance-covariance", "status", const("headline-capital")), "schema"),
    ("euler-without-label", "fed", lambda d: drop_key(d, "outputs/aggregation/euler/label"), "schema"),
    ("diversification-without-status", "fed", lambda d: drop_key(d, "outputs/aggregation/diversification/status"), "schema"),
    ("marginal-other-confidence", "fed", mut("outputs/aggregation/marginals/0/confidence_level", const(0.99)), "schema"),
    ("marginal-other-horizon", "fed", mut("outputs/aggregation/marginals/2/horizon_years", const(10)), "schema"),
    ("satellite-fit-reaches-2020", "models", mut("fit/satellites/1/sample_window/end", const("2020-03-31")), "schema"),
    ("backcast-fit-window-reaches-2021", "eba", mut("outputs/backcast/per_loan_type/2/fit_window/end", const("2021-12-31")), "schema"),
    ("path-without-vintage", "fed", lambda d: drop_key(d, "outputs/scenario/paths/0/vintage_date"), "schema"),
    ("path-without-transposition", "eba", lambda d: drop_key(d, "outputs/scenario/paths/1/transposition"), "schema"),
    ("p2g-without-approximation-label", "ngfs", lambda d: drop_key(d, "outputs/p2g_proxy/label"), "schema"),
    ("p2g-labelled-regulatory", "baseline", mut("outputs/p2g_proxy/label", const("regulatory-requirement")), "schema"),
    ("named-parameter-without-label", "models", lambda d: drop_key(d, "fit/named_parameters/c_p2/label"), "schema"),
    ("named-parameter-labelled-regulatory", "models", mut("fit/named_parameters/nu_set/label", const("regulatory")), "schema"),
    ("regressor-bbb-yield", "models", mut("fit/satellites/0/regressors/0/name", const("bbb_corporate_yield")), "schema"),
    ("ngfs-without-policy-window", "ngfs", mut("outputs/scenario/policy_shock_window", const(None)), "schema"),
    ("annex3-row-missing", "baseline", lambda d: drop_key(d, "outputs/annex3/rows/33"), "schema"),
    ("reverse-label-regulatory", "reverse", mut("outputs/failure_point/label", const("regulatory")), "schema"),
    ("backcast-2026-forecast-claim", "fed", mut("outputs/backcast/descriptive_2026/0/forecast_claim", const(True)), "schema"),
    ("marginal-ec-not-var-less-el", "fed", mut("outputs/aggregation/marginals/0/ec_clp_m", plus(10.0)), "semantic"),
    ("marginal-es-below-var", "fed", mut("outputs/aggregation/marginals/1/es_clp_m", scale(0.5)), "semantic"),
    ("variance-covariance-row-altered", "fed", band_plant("variance-covariance", "capital_clp_m", scale(1.05)), "semantic"),
    ("diversified-figure-above-the-sum", "fed", band_plant("gaussian-copula", "capital_clp_m", scale(2.0)), "semantic"),
    ("lower-bound-above-another-row", "fed", band_plant("lower-bound", "capital_clp_m", scale(3.0)), "semantic"),
    ("worst-case-below-another-row", "fed", band_plant("worst-case", "capital_clp_m", scale(0.2)), "semantic"),
    ("t-rows-differ-from-the-nu-set", "fed", lambda d: set_nu(d), "semantic"),
    ("correlation-not-symmetric", "fed", mut("outputs/aggregation/correlation/matrix/0/1", const(0.9)), "semantic"),
    ("correlation-not-positive-semidefinite", "fed", lambda d: not_psd(d), "semantic"),
    ("correlation-diagonal-not-one", "fed", mut("outputs/aggregation/correlation/matrix/2/2", const(0.9)), "semantic"),
    ("euler-contributions-do-not-add-up", "fed", mut("outputs/aggregation/euler/allocation/0/contribution_clp_m", plus(500.0)), "semantic"),
    ("euler-total-differs-from-marginals", "fed", mut("outputs/aggregation/euler/es_total_clp_m", scale(0.9)), "semantic"),
    ("diversification-factor-differs-from-its-row", "fed", mut("outputs/aggregation/diversification/factor", plus(0.1)), "semantic"),
    ("model-risk-am-wrong", "fed", mut("outputs/aggregation/model_risk/barrieu_scandolo/am", plus(0.2)), "semantic"),
    ("model-risk-rm-wrong", "fed", mut("outputs/aggregation/model_risk/barrieu_scandolo/rm", const(0.123)), "semantic"),
    ("scenario-losses-total-wrong", "fed", mut("outputs/losses/scenario_losses/1/total", plus(1.0)), "semantic"),
    ("headline-cet1-not-loss-only", "fed", mut("outputs/headline_cet1/rows/1/cet1_clp_m", plus(25_000.0)), "semantic"),
    ("headline-cumulative-loss-wrong", "eba", mut("outputs/headline_cet1/rows/2/cumulative_loss_clp_m", scale(0.8)), "semantic"),
    ("ppnr-row-wrong", "fed", mut("outputs/headline_cet1/ppnr/rows/0/ppnr_clp_m", plus(10_000.0)), "semantic"),
    ("oi-differs-from-its-components", "fed", mut("outputs/internal_capital_target/oi", plus(0.01)), "semantic"),
    ("p2g-value-differs-from-the-formula", "fed", mut("outputs/p2g_proxy/value", plus(0.01)), "semantic"),
    ("annex3-headroom-wrong", "fed", lambda d: annex_cell(d, "12", "a", 0.5), "semantic"),
    ("annex3-label-altered", "baseline", mut("outputs/annex3/rows/9/label_cmf", const("Capital necesario")), "semantic"),
    ("annex3-capital-ratio-wrong", "fed", lambda d: annex_cell(d, "1.3", "a", 0.2), "semantic"),
    ("path-vintage-after-the-observation-date", "fed", mut("outputs/scenario/paths/0/vintage_date", const("2027-01-01")), "semantic"),
    ("transposed-shape-differs-from-the-source", "fed", mut("outputs/scenario/paths/1/transposed/3/value", plus(2.0)), "semantic"),
    ("ngfs-window-not-three-years", "ngfs", mut("outputs/scenario/policy_shock_window/end_year", const(2036)), "semantic"),
    ("ngfs-variable-renamed", "ngfs", mut("outputs/scenario/paths/0/variable", const("Unemployment rate")), "semantic"),
    ("ngfs-level-not-baseline-plus-deviation", "ngfs", mut("outputs/scenario/paths/1/transposed/6/value", plus(1.5)), "semantic"),
    ("class-rate-not-the-weighted-mix", "fed", mut("outputs/satellites/banco_andino_classes/0/quarters/4/rate", scale(1.3)), "semantic"),
    ("class-weights-do-not-sum-to-one", "fed", mut("outputs/satellites/banco_andino_classes/1/weights/0", plus(0.2)), "semantic"),
    ("backcast-rmse-wrong", "fed", mut("outputs/backcast/per_loan_type/0/metrics/rmse", scale(2.0)), "semantic"),
    ("backcast-peak-quarter-wrong", "fed", mut("outputs/backcast/per_loan_type/3/metrics/peak_realised_quarter", const("2020-03-31")), "semantic"),
    ("plan-pe-not-the-sum-of-its-tiers", "fed", mut("outputs/capital_plan/cases/1/years/0/pe/available_clp_m", plus(5_000.0)), "semantic"),
    ("plan-headroom-wrong", "fed", mut("outputs/capital_plan/cases/0/years/1/headroom_pct_of_rwa", plus(0.01)), "semantic"),
    ("plan-deficit-wrong", "fed", mut("outputs/capital_plan/cases/1/years/2/deficit_clp_m", plus(1_000.0)), "semantic"),
    ("capital-start-ratio-wrong", "fed", mut("outputs/capital_start/cet1_ratio", plus(0.01)), "semantic"),
    ("rwa-mix-does-not-add-up", "fed", mut("outputs/capital_start/rwa_by_risk/market", plus(50_000.0)), "semantic"),
    ("satellite-sign-mismatch", "models", lambda d: flip_sign(d), "semantic"),
    ("satellite-n-obs-wrong", "models", mut("fit/satellites/0/n_obs", plus(5)), "semantic"),
    ("anchor-mix-does-not-add-up", "models", mut("fit/bank_anchors/rwa_mix/credit", plus(0.05)), "semantic"),
    ("anchor-rwa-differs-from-its-basis", "models", mut("fit/bank_anchors/rwa_basis/rwa_total_clp_m", scale(1.1)), "semantic"),
    ("class-mapping-weights-wrong", "models", mut("fit/class_mapping/0/weights/0", plus(0.2)), "semantic"),
    ("factor-covariance-not-symmetric", "models", mut("fit/factor_space/covariance/0/1", plus(0.5)), "semantic"),
    ("stress-changes-another-correlation", "aggregation", mut("outputs/correlation_stress/aggregation/correlation/matrix/0/3", const(0.6)), "semantic"),
    ("stress-capital-below-the-base", "aggregation", band_plant("variance-covariance", "capital_clp_m", scale(0.5), None, ("outputs", "correlation_stress", "aggregation")), "semantic"),
    ("sensitivity-row-wrong", "aggregation", mut("outputs/copula_sensitivity/0/relative_difference", plus(0.1)), "semantic"),
    ("rs-overestimate-wrong", "aggregation", mut("outputs/rosenberg_schuermann/case_additive_overestimate", plus(0.1)), "semantic"),
    ("rs-range-flag-wrong", "aggregation", lambda d: flip_flag(d), "semantic"),
    ("reverse-loss-not-the-threshold", "reverse", mut("outputs/solution/loss_at_z_star_clp_m", scale(0.7)), "semantic"),
    ("reverse-distance-not-the-closed-form", "reverse", mut("outputs/solution/mahalanobis_distance", scale(1.2)), "semantic"),
    ("reverse-plausibility-wrong", "reverse", mut("outputs/solution/plausibility/tail_probability", scale(0.5)), "semantic"),
    ("reverse-stack-total-wrong", "reverse", mut("outputs/failure_point/stack/total", plus(0.01)), "semantic"),
    ("reverse-threshold-loss-wrong", "reverse", mut("outputs/solution/loss_threshold_clp_m", scale(1.5)), "semantic"),
    ("reverse-a-start-finds-a-closer-point", "reverse", mut("outputs/starts/1/distance", scale(0.4)), "semantic"),
    ("reverse-z-star-not-standardised", "reverse", mut("outputs/solution/z_star/0", plus(0.5)), "semantic"),
]


def drop_key(doc: dict, path: str) -> dict:
    return drop_at(doc, path)


def set_nu(doc: dict) -> dict:
    i = band_index(doc["outputs"], "t-copula")
    doc["outputs"]["aggregation"]["band"][i]["nu"] = 99.0
    return doc


def not_psd(doc: dict) -> dict:
    m = doc["outputs"]["aggregation"]["correlation"]["matrix"]
    for i in (0, 1, 2):
        for j in (0, 1, 2):
            m[i][j] = 1.0 if i == j else -0.9
    return doc


def annex_cell(doc: dict, row_id: str, col: str, value: float) -> dict:
    for r in doc["outputs"]["annex3"]["rows"]:
        if r["row_id"] == row_id:
            r[col] = {"value": value, "status": "value"}
            return doc
    raise AssertionError(row_id)


def flip_sign(doc: dict) -> dict:
    s = doc["fit"]["satellites"][0]
    for c in s["coefficients"]:
        if c["expected_sign"] == "positive":
            c["estimate"] = -abs(c["estimate"])
            return doc
    raise AssertionError("no positive coefficient")


def flip_flag(doc: dict) -> dict:
    r = doc["outputs"]["rosenberg_schuermann"]
    r["within_published_range"] = not r["within_published_range"]
    return doc


def test_the_fixtures_pass_the_semantic_checker_and_the_cross_document_checks() -> None:
    docs = {k: load(k) for k in ALL}
    for k, d in docs.items():
        assert sm().violations(d) == [], (k, sm().violations(d)[:5])
    assert sm().cross_violations(docs) == []


@pytest.mark.parametrize("plant", PLANTS, ids=[p[0] for p in PLANTS])
def test_a_planted_defect_is_refused_by_the_layer_the_table_names(plant: tuple[str, str, Callable[[dict], dict], str]) -> None:
    name, key, mutate, layer = plant
    ref, _ = FILES[key]
    bad = mutate(load(key))
    schema_errors = cs.errors(ref, bad)
    if layer == "schema":
        assert schema_errors != [], f"{name}: the schema accepts it"
    else:
        assert schema_errors == [], f"{name}: the schema should accept it and the checker refuse it: {schema_errors[:3]}"
        assert sm().violations(bad) != [], f"{name}: the checker accepts it"


def test_the_plant_table_covers_every_must_refute_item_and_both_layers() -> None:
    names = {p[0] for p in PLANTS}
    for must in ("headline-not-simple-sum", "headline-capital-differs-from-the-sum", "diversified-row-without-label",
                 "marginal-other-confidence", "marginal-other-horizon", "satellite-fit-reaches-2020", "path-without-vintage",
                 "path-without-transposition", "p2g-without-approximation-label", "named-parameter-without-label",
                 "regressor-bbb-yield", "annex3-row-missing", "reverse-loss-not-the-threshold"):
        assert must in names, must
    assert {p[3] for p in PLANTS} == {"schema", "semantic"}
    assert len(PLANTS) >= 70


def test_the_cross_document_checks_refuse_a_marginal_that_differs_between_the_baseline_and_the_t_copula_variant() -> None:
    docs = {k: load(k) for k in ALL}
    docs["aggregation"]["outputs"]["aggregation"]["marginals"][0]["ec_clp_m"] += 1.0
    assert sm().cross_violations(docs) != []
    docs = {k: load(k) for k in ALL}
    docs["baseline"]["outputs"]["internal_capital_target"]["c_p2"]["value"] += 0.01
    assert sm().cross_violations(docs) != []
    docs = {k: load(k) for k in ALL}
    docs["models"]["fit"]["satellites"][0]["sample_window"]["start"] = "1990-03-31"
    assert sm().cross_violations(docs) != []
    docs = {k: load(k) for k in ALL}
    docs["fed"]["outputs"]["backcast"]["per_loan_type"][0]["fit_window"]["end"] = "2018-12-31"
    assert sm().cross_violations(docs) != []


# --- the t-copula variant -----------------------------------------------------------------------------------------


def test_the_t_copula_variant_runs_the_baseline_with_the_nu_set_and_the_market_credit_stress() -> None:
    o = out("aggregation")
    assert o["scenario_id"] == "baseline"
    base, stress = o["aggregation"], o["correlation_stress"]["aggregation"]
    nus = base["nu_set"]["values"]
    assert len(nus) >= 2
    assert sorted(r["nu"] for r in base["band"] if r["method"] == "t-copula") == sorted(nus)
    assert sorted(r["nu"] for r in stress["band"] if r["method"] == "t-copula") == sorted(nus)
    assert o["correlation_stress"]["pair"] == {"a": "market", "b": "credit", "value": 0.8}
    order = base["correlation"]["order"]
    assert stress["correlation"]["matrix"][order.index("market")][order.index("credit")] == 0.8
    assert [m["risk"] for m in base["marginals"]] == [m["risk"] for m in stress["marginals"]] == RISKS
    assert [r["nu"] for r in o["copula_sensitivity"]] == sorted(nus) or sorted(r["nu"] for r in o["copula_sensitivity"]) == sorted(nus)
    rs = o["rosenberg_schuermann"]
    assert rs["role"] == "reference-not-a-gate"
    assert (rs["weights"]["market"], rs["weights"]["credit"], rs["weights"]["operational"]) == (0.041, 0.264, 0.695)
    assert (rs["correlations"]["market_credit"], rs["correlations"]["market_operational"], rs["correlations"]["credit_operational"]) == (0.5, 0.2, 0.2)


# --- the C17 exceedance grid (R12) --------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1"])
def test_the_c17_exceedance_grid_resolves_the_999_quantile_by_log_log_interpolation(name: str) -> None:
    """R12 of the U13 sizing: the committed 14-point exceedance grid of C17 brackets the 99.9 percent quantile in every document, and the
    log-log interpolation between its two bracketing points recovers the committed Monte Carlo quantile within one percent. It does not
    resolve the 99.99 percent level or the expected shortfall, and it holds the generator's EUR bank: decision Q5 recomputes the marginal
    through ``oprisk.aggregate`` from the generator parameters rather than reading it from the grid."""
    doc = cs.load_json(ROOT / "data" / "derived" / "C17" / f"{name}.json")
    ex = doc["outputs"]["exceedance"]
    grid, mc = ex["grid_eur"], ex["monte_carlo"]["exceedance"]
    assert len(grid) == 14
    target = 1e-3
    i = next(k for k in range(len(grid) - 1) if mc[k] >= target > mc[k + 1])
    x0, x1, y0, y1 = math.log(grid[i]), math.log(grid[i + 1]), math.log(mc[i]), math.log(mc[i + 1])
    q = math.exp(x0 + (math.log(target) - y0) * (x1 - x0) / (y1 - y0))
    reference = ex["quantile_999_eur"]["monte_carlo"]
    assert abs(q / reference - 1) < 0.01
    assert grid[i + 1] / grid[i] < 2.2, "the bracketing cell is a factor of about two wide"
    assert mc[-1] < target, "the grid ends below the 99.9 percent exceedance; it holds no point at the 99.99 percent level"
    assert mc[-1] > target / 100, "so the 99.99 percent quantile and the expected shortfall are not resolved by the grid"


# --- the rows fragment and the changelog fragment -------------------------------------------------------------------


def row_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


ROW_IDS = ["c18-outputs", "c18-outputs-aggregation", "c18-outputs-reverse", "c18-models", "engine-aggregation-api", "engine-stress-api"]


def fragment_tables() -> tuple[list[str], list[list[str]], list[list[str]]]:
    text = ROWS.read_text(encoding="utf-8")
    tables: list[list[list[str]]] = []
    cur: list[list[str]] = []
    for ln in text.splitlines():
        if ln.startswith("|"):
            cur.append(row_cells(ln))
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    first = tables[0]
    data = [r for r in first[1:] if not all(set(c) <= set(":- ") for c in r)]
    history = [r for r in tables[1][1:] if not all(set(c) <= set(":- ") for c in r)] if len(tables) > 1 else []
    return first[0], data, history


def test_the_rows_fragment_has_the_six_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(row_cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    head, data, history = fragment_tables()
    assert head == header
    assert [r[0] for r in data] == ROW_IDS
    for r in data:
        assert len(r) == len(header), r[0]
        d = dict(zip(header, r))
        assert d["version"] == "1.0.0"
        assert d["status"] == "active"
        assert d["provider"].startswith("fixture:")
        assert (ROOT / d["schema file"]).is_file(), d["schema file"]
        assert (ROOT / d["example"]).is_file(), d["example"]
        assert (ROOT / d["provider"].removeprefix("fixture:")).is_file(), d["provider"]
        for cell in (d["producer test"], d["consumer test"]):
            for t in cell.split(","):
                t = t.strip()
                if t == "-":
                    continue
                path, _, name = t.partition("::")
                assert (ROOT / path).is_file(), path
                if name:
                    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), t
        assert "missing" in d["missing-data behavior"] or "partial" in d["missing-data behavior"], r[0]
    contracts = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0]
    cat_ids = [row_cells(ln)[0] for ln in contracts.splitlines() if ln.startswith("| ")]
    assert not set(ROW_IDS) & set(cat_ids), "the integrator merges these rows; a unit never edits the catalog"
    assert [r[0] for r in history if r[0] in ROW_IDS] == ROW_IDS


def test_the_schema_rows_name_their_schema_file_and_the_engine_rows_their_markdown() -> None:
    _, data, _ = fragment_tables()
    files = {r[0]: r[3] for r in data}
    assert files == {
        "c18-outputs": "docs/contracts/schemas/c18/variant-scenario.schema.json",
        "c18-outputs-aggregation": "docs/contracts/schemas/c18/variant-aggregation.schema.json",
        "c18-outputs-reverse": "docs/contracts/schemas/c18/variant-reverse.schema.json",
        "c18-models": "docs/contracts/schemas/c18/models.schema.json",
        "engine-aggregation-api": "docs/contracts/engine/aggregation-api.md",
        "engine-stress-api": "docs/contracts/engine/stress-api.md",
    }


def test_the_changelog_fragment_has_bullet_lines_only_and_names_the_unit() -> None:
    lines = CHANGES.read_text(encoding="utf-8").splitlines()
    assert lines and all(ln.startswith("- ") or ln.startswith("  ") or ln == "" for ln in lines)
    assert not any(ln.startswith("#") for ln in lines)
    text = "\n".join(lines)
    assert "U13-S" in text and "C18" in text and "C19" in text and "E1" in text
    assert chr(0x2014) not in text and chr(0x2192) not in text


# --- the two engine API contracts -------------------------------------------------------------------------------

AGG_MODULES = {
    "aggregation.simple": ["simple_sum", "check_correlation", "variance_covariance", "hybrid_quantile", "diversification_factor",
                           "euler_diversification_benefit", "std_contributions"],
    "aggregation.copulas": ["marginal_ppf_sample", "marginal_ppf_pmf", "simulate_copula_uniforms", "simulate_component_losses",
                            "t_tail_dependence", "clayton_copula", "clayton_lower_tail_dependence", "CopulaAggregate", "copula_aggregate"],
    "aggregation.bounds": ["comonotonic_var", "rearrangement_algorithm", "VarBounds", "worst_var_bounds"],
    "aggregation.band": ["BandRow", "Band", "dependence_band"],
    "aggregation.model_risk": ["ModelRisk", "barrieu_scandolo", "GlassermanXu", "glasserman_xu_worst_case"],
    "validation.aggregation": ["simple_sum_and_variance_covariance", "copula_choice_sensitivity", "worst_case_bracket", "correlation_stress",
                               "diversification_sign", "horizon_confidence_consistency", "elliptical_mc_agreement",
                               "rosenberg_schuermann_reference"],
}
STRESS_MODULES = {
    "stress.satellites": ["link", "inverse_link", "SatelliteFit", "fit_satellite", "SatelliteProjection", "project_scenario"],
    "stress.paths": ["transpose_path", "revert_to_baseline", "annual_to_quarterly", "level_from_deviation", "check_vintage"],
    "stress.capital": ["cet1_path_loss_only", "PpnrRow", "ppnr_row", "InternalTarget", "internal_capital_target", "chilean_cet1_stack",
                       "capital_plan", "PlanYear", "p2g_proxy", "annex3_summary", "eba_static_balance_sheet"],
    "stress.reverse": ["ReverseSolution", "reverse_stress_linear", "reverse_stress", "plausibility"],
    "stress.scenario_models": ["VarFit", "fit_var", "var_conditional_forecast", "skewed_t_pdf", "SkewedTFit", "gar_quantile_regressions",
                               "fit_skewed_t_to_quantiles"],
    "validation.stress": ["satellite_backcast", "sensitivity_monotonicity", "static_balance_sheet_rules", "bottom_up_vs_top_down",
                          "scenario_severity", "reverse_solution_check"],
}
RESULT_TYPES = {"CopulaAggregate", "VarBounds", "BandRow", "Band", "ModelRisk", "GlassermanXu", "SatelliteFit", "SatelliteProjection",
                "PpnrRow", "InternalTarget", "PlanYear", "ReverseSolution", "VarFit", "SkewedTFit"}
REUSED = ["portfolio.euler.es_contributions", "portfolio.euler.var_contributions_kernel", "portfolio.portfolio.var_from_sample",
          "portfolio.portfolio.es_from_sample", "portfolio.portfolio.measures_from_sample", "portfolio.portfolio.LossMeasures",
          "portfolio.copula.mc_standard_errors", "validation.portfolio.euler_additivity", "engines.vasicek.conditional_pd",
          "engines.vasicek.implied_factor", "provisions.term_structure.ttc_to_pit", "provisions.term_structure.implied_z",
          "oprisk.aggregate", "oprisk.sma", "irrbb.simulation.ear_evar", "irrbb.eve_nii", "core.result.TestResult"]
SIZING_MODULE_FILES = {
    AGG_API: ["aggregation/simple.py", "aggregation/copulas.py", "aggregation/bounds.py", "aggregation/band.py", "aggregation/model_risk.py",
              "validation/aggregation.py"],
    STRESS_API: ["stress/satellites.py", "stress/paths.py", "stress/capital.py", "stress/reverse.py", "stress/scenario_models.py",
                 "validation/stress.py"],
}


def prefix_of(module: str) -> str:
    return f"riskvalidation.{module}"


def key_of(module: str, name: str) -> str:
    return f"{prefix_of(module)}.{name}"


def api_sections(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^### `([^`]+)`\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


API_CASES = [(AGG_API, AGG_MODULES, "engine-aggregation-api"), (STRESS_API, STRESS_MODULES, "engine-stress-api")]


@pytest.mark.parametrize("path,modules,cid", API_CASES, ids=["aggregation", "stress"])
def test_the_engine_contract_exists_with_its_version_and_names_test_result(path: Path, modules: dict, cid: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.startswith(f"# Engine ") and cid in text and "1.0.0" in text
    assert "common/test-result" in text
    assert "Owner: U13-S" in text


@pytest.mark.parametrize("path,modules,cid", API_CASES, ids=["aggregation", "stress"])
def test_the_engine_contract_covers_every_module_of_the_sizing_table(path: Path, modules: dict, cid: str) -> None:
    text = path.read_text(encoding="utf-8")
    for module in SIZING_MODULE_FILES[path]:
        assert f"`riskvalidation/{module}`" in text, module


@pytest.mark.parametrize("path,modules,cid", API_CASES, ids=["aggregation", "stress"])
def test_every_function_has_a_signature_units_and_a_golden_value_or_an_invariant(path: Path, modules: dict, cid: str) -> None:
    sections = api_sections(path)
    for module, names in modules.items():
        for name in names:
            body = sections[key_of(module, name)]
            assert "```python" in body, name
            assert re.search(r"^- (Golden|Invariants):", body, flags=re.M), f"{name}: no golden value or invariant"
            assert re.search(r"^- Units:", body, flags=re.M), f"{name}: no units line"
            if name in RESULT_TYPES:
                assert "@dataclass(frozen=True)" in body, f"{name}: result types are frozen dataclasses"
            if module.startswith("validation."):
                assert "-> TestResult" in body, name
                assert re.search(r"^- Light:", body, flags=re.M), name
                assert re.search(r"^- Golden:", body, flags=re.M), name
                assert re.search(r'test_id = "(aggregation|stress)\.[a-z_0-9]+"', body), name


@pytest.mark.parametrize("path,modules,cid", API_CASES, ids=["aggregation", "stress"])
def test_the_engine_contract_has_no_function_outside_the_table(path: Path, modules: dict, cid: str) -> None:
    declared = {key_of(m, n) for m, names in modules.items() for n in names}
    assert set(api_sections(path)) == declared


def test_the_reused_engine_functions_are_named_as_reused_and_never_restated() -> None:
    texts = [AGG_API.read_text(encoding="utf-8"), STRESS_API.read_text(encoding="utf-8")]
    for text in texts:
        assert "Reused" in text
    reused_agg = texts[0].split("## Reused", 1)[1].split("\n## ", 1)[0]
    for name in REUSED[:8] + ["oprisk.aggregate", "oprisk.sma", "irrbb.simulation.ear_evar", "core.result.TestResult"]:
        assert f"`riskvalidation.{name}" in reused_agg or f"`{name}" in reused_agg, name
    reused_stress = texts[1].split("## Reused", 1)[1].split("\n## ", 1)[0]
    for name in ("engines.vasicek.conditional_pd", "engines.vasicek.implied_factor", "provisions.term_structure.ttc_to_pit",
                 "provisions.term_structure.implied_z", "irrbb.eve_nii", "core.result.TestResult"):
        assert f"`riskvalidation.{name}" in reused_stress or f"`{name}" in reused_stress, name
    for text in texts:
        sections = set(re.findall(r"^### `([^`]+)`", text, flags=re.M))
        for name in REUSED:
            assert f"riskvalidation.{name}" not in sections, f"{name} is reused, never restated"


def test_the_aggregation_contract_carries_the_goldens_and_the_published_benchmark_labelled() -> None:
    text = AGG_API.read_text(encoding="utf-8")
    for golden in ("72.00", "105.14", "244.98", "504.00", "141.67", "203.66", "465.29", "30.47", "9.00", "27.0000", "44.7671", "851.72901",
                   "0.806", "4.1", "26.4", "69.5", "5.0", "0.7071", "0.75", "4.1231"):
        assert golden in text, golden
    for test_id in ("aggregation.simple_sum_and_variance_covariance", "aggregation.copula_choice_sensitivity", "aggregation.worst_case_bracket",
                    "aggregation.correlation_stress", "aggregation.diversification_sign", "aggregation.horizon_confidence_consistency",
                    "aggregation.elliptical_mc_agreement", "aggregation.rosenberg_schuermann_reference"):
        assert test_id in text, test_id
    for cite in ("Embrechts, Puccetti and Ruschendorf", "Table 1", "Table 4", "Rosenberg and Schuermann", "Tasche", "Barrieu and Scandolo",
                 "Glasserman and Xu", "05 l.360", "06 l.692"):
        assert cite in text, cite
    assert "UNVERIFIED" in text
    assert "reference, never a gate" in text.replace("\n", " ")
    assert "information, not capital" in text.replace("\n", " ")


def test_the_stress_contract_carries_the_goldens_and_the_published_figures() -> None:
    text = STRESS_API.read_text(encoding="utf-8")
    for golden in ("4,601,923", "41,715,467", "0.110317", "0.125", "0.50", "1.50", "2.50", "52,144", "0.04", "1,668,618.68", "2.2361", "0.073424",
                   "0.014287", "0.09625", "0.12625"):
        assert golden in text, golden
    for test_id in ("stress.satellite_backcast", "stress.sensitivity_monotonicity", "stress.static_balance_sheet_rules",
                    "stress.bottom_up_vs_top_down", "stress.scenario_severity", "stress.reverse_solution_check"):
        assert test_id in text, test_id
    for cite in ("para 33", "para 90", "para 24", "para 133", "03 l.152", "03 l.1001", "01 l.891", "05 l.390", "04 l.785", "C06", "BL-079"):
        assert cite in text, cite
    assert "UNVERIFIED" in text
    assert "Contraste approximation" in text
    assert "supervisory" in text and "E1" in text


def test_the_stress_contract_states_the_open_conventions_it_proposes() -> None:
    text = STRESS_API.read_text(encoding="utf-8")
    assert "reversion_quarters" in text and "REVERSION_QUARTERS" in text
    assert "loss-only" in text and "PPNR" in text
    assert "no capital action after the reference date" in text.lower() or "no capital measures" in text.lower()


# --- the golden values recompute here from the formulas (standard library only) ---------------------------------------


def varcov(ec: list[float], r: list[list[float]]) -> float:
    return math.sqrt(sum(ec[i] * r[i][j] * ec[j] for i in range(len(ec)) for j in range(len(ec))))


def test_golden_variance_covariance_identities_recompute() -> None:
    ident = [[1.0, 0.0], [0.0, 1.0]]
    ones = [[1.0, 1.0], [1.0, 1.0]]
    half = [[1.0, 0.5], [0.5, 1.0]]
    assert varcov([3.0, 4.0], ident) == pytest.approx(5.0)
    assert varcov([3.0, 4.0], ones) == pytest.approx(7.0)
    assert varcov([3.0, 4.0], half) == pytest.approx(math.sqrt(37.0))
    assert round(math.sqrt(37.0), 4) == 6.0828
    text = AGG_API.read_text(encoding="utf-8")
    for s in ("5.0", "7.0", "6.0828"):
        assert s in text


def test_golden_std_contributions_add_up_to_the_standard_deviation() -> None:
    cov = [[4.0, 2.0], [2.0, 9.0]]
    var_total = sum(cov[i][j] for i in range(2) for j in range(2))
    contribs = [sum(cov[i]) / math.sqrt(var_total) for i in range(2)]
    assert var_total == 17.0
    assert sum(contribs) == pytest.approx(math.sqrt(17.0))
    assert round(sum(contribs), 4) == 4.1231
    assert round(contribs[0], 4) == 1.4552 and round(contribs[1], 4) == 2.6679
    text = AGG_API.read_text(encoding="utf-8")
    assert "1.4552" in text and "2.6679" in text


def test_golden_comonotonic_pareto_values_and_table_1_first_row_recompute() -> None:
    def pareto_ppf(u: float, theta: float = 2.0) -> float:
        return (1.0 - u) ** (-1.0 / theta) - 1.0

    assert pareto_ppf(0.99) == pytest.approx(9.0)
    assert 3 * pareto_ppf(0.99) == pytest.approx(27.0)
    table4 = {(8, 0.99): 72.00, (8, 0.995): 105.14, (8, 0.999): 244.98, (56, 0.99): 504.00, (56, 0.995): 735.96, (56, 0.999): 1714.88,
              (648, 0.99): 5832.00, (648, 0.995): 8516.10, (648, 0.999): 19843.56}
    for (d, a), v in table4.items():
        assert round(d * pareto_ppf(a), 2) == pytest.approx(v, abs=0.011), (d, a)
    # Table 1 part (A): x_(i,j) = F^-1(0.99 + 0.01 (i - 1) / 50), so the last row is F^-1(0.9998) and a column sums to 851.72901
    assert pareto_ppf(0.99 + 0.01 * 49 / 50) == pytest.approx(69.71068, abs=5e-6)
    assert 3 * pareto_ppf(0.99 + 0.01 * 49 / 50) == pytest.approx(209.1320, abs=5e-5)
    assert sum(pareto_ppf(0.99 + 0.01 * (i - 1) / 50) for i in range(1, 51)) == pytest.approx(851.72901, abs=5e-5)
    text = AGG_API.read_text(encoding="utf-8")
    for s in ("735.96", "1714.88", "5832.00", "8516.10", "19843.56", "209.1320", "87.8122", "69.71068", "13.43376"):
        assert s in text, s


def test_golden_rosenberg_schuermann_reference_run_recomputes_and_is_outside_the_published_range() -> None:
    w = [0.041, 0.264, 0.695]
    r = [[1.0, 0.5, 0.2], [0.5, 1.0, 0.2], [0.2, 0.2, 1.0]]
    assert sum(w) == pytest.approx(1.0)
    total = varcov(w, r)
    assert total == pytest.approx(0.80624, abs=5e-6)
    overestimate = sum(w) / total - 1.0
    assert overestimate == pytest.approx(0.24033, abs=5e-5)
    assert not 0.30 <= overestimate <= 0.40, "the benchmark weights are return weights, not capital: the figure is a reference, never a gate"
    text = AGG_API.read_text(encoding="utf-8")
    assert "0.80624" in text and "0.2403" in text


def test_golden_model_risk_identities_recompute() -> None:
    rho0, rho_max, rho_min = 100.0, 130.0, 90.0
    am = rho_max / rho0 - 1.0
    rm = (rho_max - rho0) / (rho_max - rho_min)
    assert am == pytest.approx(0.3) and rm == pytest.approx(0.75)
    text = AGG_API.read_text(encoding="utf-8")
    assert "0.75" in text and "0.3" in text


def t_pdf(x: float, df: float) -> float:
    return math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi) * (1 + x * x / df) ** (-(df + 1) / 2)


def t_cdf(x: float, df: float, n: int = 20000) -> float:
    lo = -200.0
    h = (x - lo) / n
    s = t_pdf(lo, df) + t_pdf(x, df)
    for i in range(1, n):
        s += (4 if i % 2 else 2) * t_pdf(lo + i * h, df)
    return s * h / 3


def test_golden_t_tail_dependence_and_clayton_recompute() -> None:
    nu, rho = 4.0, 0.5
    lam = 2.0 * t_cdf(-math.sqrt((nu + 1) * (1 - rho) / (1 + rho)), nu + 1)
    assert lam == pytest.approx(0.25317, abs=5e-5)
    text = AGG_API.read_text(encoding="utf-8")
    assert f"{lam:.4f}" in text, f"t tail dependence at nu 4, rho 0.5 is {lam:.4f}"
    assert 2 ** (-1 / 2.0) == pytest.approx(0.7071, abs=5e-5) and 2 ** (-1 / 1.0) == 0.5
    theta = 1.0
    assert (0.5 ** -theta + 0.5 ** -theta - 1) ** (-1 / theta) == pytest.approx(1 / 3)
    assert "0.3333" in text


def test_golden_euler_es_contributions_of_the_portfolio_contract_recompute() -> None:
    g1 = [float(i) for i in range(10)]
    g2 = [2.0 * i for i in range(10)]
    losses = [a + b for a, b in zip(g1, g2)]
    q = 0.9
    k = math.ceil(q * 10 - 1e-9)
    srt = sorted(losses)
    var = srt[k - 1]
    es = (sum(srt[k:]) / 10 + (k / 10 - q) * var) / (1 - q)
    assert es == pytest.approx(27.0)
    rc = []
    for g in (g1, g2):
        order = sorted(range(10), key=lambda i: losses[i])
        tail = [g[i] for i in order[k:]]
        boundary = g[order[k - 1]]
        rc.append((sum(tail) / 10 + (k / 10 - q) * boundary) / (1 - q))
    assert rc == pytest.approx([9.0, 18.0]) and sum(rc) == pytest.approx(es)
    text = AGG_API.read_text(encoding="utf-8")
    assert "27.0" in text and "(9.0, 18.0)" in text


def test_golden_santander_chile_capital_ratios_the_4_percent_cap_and_the_stack_recompute() -> None:
    s = SANTANDER
    assert s["credit"] + s["market"] + s["operational"] == s["rwa"]
    assert s["cet1"] / s["rwa"] == pytest.approx(0.110317, abs=5e-7)
    assert s["p2r"] / s["rwa"] == pytest.approx(0.00125, abs=5e-6)
    assert s["ccyb"] / s["rwa"] == pytest.approx(0.0050, abs=5e-6)
    assert s["dsib"] / s["rwa"] == pytest.approx(0.0150, abs=5e-6)
    assert s["ccob"] / s["rwa"] == pytest.approx(0.0250, abs=5e-6)
    assert round(0.04 * s["rwa"], 2) == 1_668_618.68 and s["p2r"] < 0.04 * s["rwa"]
    mix = [s["credit"] / s["rwa"], s["market"] / s["rwa"], s["operational"] / s["rwa"]]
    assert [round(m, 3) for m in mix] == [0.708, 0.171, 0.120]
    oi = 0.08 + 0.015 + 0.00125 + 0.025 + 0.005 + 0.0
    assert oi == pytest.approx(0.12625)
    assert s["pe"] / s["rwa"] - oi == pytest.approx(0.168938 - 0.12625, abs=5e-6)
    assert 0.08 + 0.015 + 0.00125 == pytest.approx(0.09625)
    text = STRESS_API.read_text(encoding="utf-8")
    for needle in ("0.168938", "0.042688", "0.090000", "0.020317"):
        assert needle in text, needle
    assert round(s["pe"] / s["rwa"], 6) == 0.168938 and round(s["pe"] / s["rwa"] - oi, 6) == 0.042688
    assert round(s["cet1"] / s["rwa"] - 0.09, 6) == 0.020317


def test_golden_probit_round_trip_ols_mahalanobis_and_the_capital_path_recompute() -> None:
    from statistics import NormalDist
    nd = NormalDist()
    pd_, rho = 0.02, 0.12
    cond = lambda z: nd.cdf((nd.inv_cdf(pd_) - math.sqrt(rho) * z) / math.sqrt(1 - rho))  # noqa: E731
    assert cond(0.0) == pytest.approx(0.014287, abs=5e-7)
    for z in (-2.0, -0.5, 0.0, 1.5):
        dr = cond(z)
        back = (nd.inv_cdf(pd_) - math.sqrt(1 - rho) * nd.inv_cdf(dr)) / math.sqrt(rho)
        assert back == pytest.approx(z, abs=1e-9)
    assert round(cond(-2.0), 6) == 0.073424
    # OLS of an exact line
    xs, ys = [0.0, 1.0, 2.0, 3.0], [1.0, 3.0, 5.0, 7.0]
    xb, yb = sum(xs) / 4, sum(ys) / 4
    b = sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) / sum((x - xb) ** 2 for x in xs)
    assert (yb - b * xb, b) == (1.0, 2.0)
    # the closed-form Mahalanobis scenario of a linear loss
    sigma, g, l = [1.0, 4.0], [1.0, 1.0], 5.0
    gsg = sum(gi * gi * si for gi, si in zip(g, sigma))
    x_star = [si * gi * l / gsg for gi, si in zip(g, sigma)]
    dist = l / math.sqrt(gsg)
    assert x_star == [1.0, 4.0] and dist == pytest.approx(2.2361, abs=5e-5)
    assert sum(gi * xi for gi, xi in zip(g, x_star)) == pytest.approx(l)
    chi2_sf_df2 = math.exp(-dist ** 2 / 2)
    assert chi2_sf_df2 == pytest.approx(0.0821, abs=5e-5)
    sf3 = math.erfc(dist / math.sqrt(2)) + math.sqrt(2 / math.pi) * dist * math.exp(-dist ** 2 / 2)
    assert sf3 == pytest.approx(0.1717, abs=5e-4)
    # a hand-computed three-year capital path
    rwa, cet1 = 100.0, 11.0
    losses = [1.0, 2.0, 1.5]
    path = []
    for loss in losses:
        cet1 -= loss
        path.append(cet1)
    assert path == [10.0, 8.0, 6.5] and [c / rwa for c in path] == [0.10, 0.08, 0.065]
    peak = max(0.11 - c / rwa for c in path)
    assert peak == pytest.approx(0.045) and max(0.0, peak - 0.02) == pytest.approx(0.025)
    text = STRESS_API.read_text(encoding="utf-8")
    for needle in ("0.073424", "0.0821", "[10.0, 8.0, 6.5]", "0.025"):
        assert needle in text, needle


def test_golden_path_transposition_and_the_skewed_t_reduction_recompute() -> None:
    source, source_jump, target = [6.0, 8.0, 10.0], 5.0, 3.0
    assert [target + (v - source_jump) for v in source] == [4.0, 6.0, 8.0]
    reversion = [8.0 + min(1.0, k / 12) * (5.0 - 8.0) for k in (1, 6, 12, 13)]
    assert reversion == [7.75, 6.5, 5.0, 5.0]
    nu = 5.0
    assert t_pdf(0.0, nu) == pytest.approx(0.379607, abs=5e-7)
    text = STRESS_API.read_text(encoding="utf-8")
    for needle in ("[4.0, 6.0, 8.0]", "[7.75, 6.5, 5.0, 5.0]", "0.379607"):
        assert needle in text, needle
