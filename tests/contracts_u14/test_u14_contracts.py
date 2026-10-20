"""U14-S: the C02, C20 and C21 case contracts, their fixtures, the ``scored_sample`` family bump, the catalog rows and the two engine APIs.

The fixtures validate by discovery against exactly one schema; the schemas are strict both ways (a removed or an added key fails);
the exploratory blocks and the Impact block carry their label; a C20 variant on SGCD carries the dataset-card notice; a C21 document
carries the "no legal claim" label, labels the four-fifths line an employment benchmark and holds no outcome-conditioned test; every
named parameter carries the label "convention"; an HMDA field is named only from the U14 research addendum H1; the family bump keeps
every existing case valid and lets a case that declares no outcome omit ``target``; the engine contracts list every function of the
sizing's modules with its check. The fixtures are labelled as fixtures and never published as results.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest

import api_spec as sp
import contract_schemas as cs
import values as V

ROOT = cs.ROOT
sys.path.insert(0, str(ROOT / "data-pipeline"))
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
ENGINE = ROOT / "docs" / "contracts" / "engine"
ROWS_FRAGMENT = ROOT / "docs" / "contracts" / "rows" / "U14.md"
# merged into the catalog at the batch 3 integration (task/0-13-000-wave2, 2026-10-19) and deleted by fragments.py rows;
# the fragment as merged is kept beside these tests, so its producer-checks section and History rows stay checked
ROWS = ROWS_FRAGMENT if ROWS_FRAGMENT.is_file() else Path(__file__).parent / "rows-fragment-merged.md"
CHANGES = ROOT / "changes" / "U14-S.md"

DOCS: list[tuple[str, Path]] = [
    ("c02/variant-horizon", FIXTURES / "c02" / "variant-horizon-h1-fixture.json"),
    ("c02/variant-horizon", FIXTURES / "c02" / "variant-horizon-pooled-fixture.json"),
    ("c02/models", FIXTURES / "c02" / "models-fixture.json"),
    ("c20/variant-shock", FIXTURES / "c20" / "variant-shock-fixture.json"),
    ("c20/variant-shift", FIXTURES / "c20" / "variant-shift-fixture.json"),
    ("c20/variant-seeds", FIXTURES / "c20" / "variant-seeds-fixture.json"),
    ("c20/variant-perturbation", FIXTURES / "c20" / "variant-perturbation-fixture.json"),
    ("c20/variant-leakage", FIXTURES / "c20" / "variant-leakage-fixture.json"),
    ("c20/models", FIXTURES / "c20" / "models-fixture.json"),
    ("c21/variant-year-pair", FIXTURES / "c21" / "variant-year-pair-fixture.json"),
    ("c21/models", FIXTURES / "c21" / "models-fixture.json"),
]
IDS = [f"{r.split('/')[0]}-{p.stem}" for r, p in DOCS]
KINDS = {"c02/variant-horizon": "horizon", "c20/variant-shock": "shock", "c20/variant-shift": "shift", "c20/variant-seeds": "seeds",
         "c20/variant-perturbation": "perturbation", "c20/variant-leakage": "leakage", "c21/variant-year-pair": "year-pair"}
P = {k: p for (k, p) in [(r, p) for r, p in DOCS]}  # last of each ref
H1 = FIXTURES / "c02" / "variant-horizon-h1-fixture.json"
POOLED = FIXTURES / "c02" / "variant-horizon-pooled-fixture.json"
SHOCK = FIXTURES / "c20" / "variant-shock-fixture.json"
SEEDS = FIXTURES / "c20" / "variant-seeds-fixture.json"
C21 = FIXTURES / "c21" / "variant-year-pair-fixture.json"
C20_VARIANTS = [p for r, p in DOCS if r.startswith("c20/variant")]


def load(path: Path) -> Any:
    return cs.load_json(path)


def root_of(ref: str) -> str:
    return "outputs" if "variant" in ref else "fit"


def ref_of(path: Path) -> str:
    return next(r for r, p in DOCS if p == path)


def valid(ref: str, doc: Any) -> bool:
    return cs.validator(ref).is_valid(doc)


# --- the fixtures -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_the_fixture_exists_and_is_discovered_by_exactly_one_schema(ref: str, path: Path) -> None:
    assert path.is_file(), path
    doc = load(path)
    assert cs.schema_for_document(path, doc) == ref
    assert cs.errors(ref, doc) == []
    passing = [c.ref for c in cs.candidates() if valid(c.ref, doc)]
    assert passing == [ref], f"{path.name}: validates against {passing}"


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_the_fixture_is_labelled_as_a_fixture(ref: str, path: Path) -> None:
    doc = load(path)
    assert doc["provenance"]["generators"] == ["fixture:u14-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    key = "variant_id" if "variant" in ref else "fit_id"
    assert str(doc[key]).startswith("fixture-")


def test_every_u14_schema_is_case_folder_conformant_case_prefixed_and_declares_its_kind() -> None:
    assert cs.case_folder_violations() == []
    assert cs.default_violations() == []
    by_ref = {c.ref: c for c in cs.candidates()}
    for case in ("c02", "c20", "c21"):
        for p in sorted((SCHEMAS / case).glob("*.schema.json")):
            for name in cs.load_json(p).get("$defs", {}):
                assert name.startswith(case), f"{p.name}: $defs name {name!r} is not prefixed {case!r}"
    for ref, kind in KINDS.items():
        assert by_ref[ref].consts["outputs.kind"] == kind and by_ref[ref].consts["case_id"] == ref[:3].upper()
        assert cs.default_variants().get(ref[:3].upper()) is None, "every U14 variant schema declares a kind: none is a default"
    assert {p.relative_to(SCHEMAS).as_posix() for case in ("c02", "c20", "c21") for p in (SCHEMAS / case).glob("*.schema.json")} == \
        {f"{r}.schema.json" for r in [*KINDS, "c02/models", "c20/models", "c21/models"]}


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


def closed(ref: str, path: Path) -> list[tuple[tuple, dict]]:
    doc = load(path)
    return [(p, o) for p, o in objects(doc[root_of(ref)], (root_of(ref),)) if o]


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_a_key_removed_from_any_object_fails(ref: str, path: Path) -> None:
    doc = load(path)
    checked = 0
    for p, obj in closed(ref, path):
        for key in list(obj):
            if key == "term_structure_reason":      # optional since c02-outputs 1.1.0 (U14 G22): every 1.0.0 document lacks it and stays valid
                continue
            bad = copy.deepcopy(doc)
            del get(bad, p)[key]
            assert not valid(ref, bad), f"{path.name}: removing {'/'.join(map(str, p))}/{key} still validates"
            checked += 1
    assert checked > 10


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_a_key_added_to_any_object_fails(ref: str, path: Path) -> None:
    doc = load(path)
    for p, o in closed(ref, path):
        bad = copy.deepcopy(doc)
        get(bad, p)["unknown_key"] = 1
        assert not valid(ref, bad), f"{path.name}: adding a key at {'/'.join(map(str, p))} still validates"


@pytest.mark.parametrize("path", [H1, SHOCK, C21], ids=["c02", "c20", "c21"])
def test_a_document_without_case_id_or_outputs_kind_does_not_pass(path: Path) -> None:
    ref = ref_of(path)
    doc = load(path)
    no_case = copy.deepcopy(doc)
    del no_case["case_id"]
    assert not valid(ref, no_case)
    with pytest.raises(cs.SelectionError):
        cs.schema_for_document(path, no_case)
    no_kind = copy.deepcopy(doc)
    del no_kind["outputs"]["kind"]
    assert not valid(ref, no_kind)
    try:
        chosen = cs.schema_for_document(path, no_kind)
    except cs.SelectionError:
        chosen = None
    assert chosen != ref
    assert chosen is None or not valid(chosen, no_kind)


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_a_wrong_case_id_is_rejected(ref: str, path: Path) -> None:
    bad = load(path)
    bad["case_id"] = "C01"
    assert not valid(ref, bad)


def test_a_fixture_of_one_case_does_not_validate_against_another() -> None:
    for ref, path in DOCS:
        doc = load(path)
        others = [c.ref for c in cs.candidates() if c.ref != ref and c.ref.split("/")[0] in ("c02", "c20", "c21") and valid(c.ref, doc)]
        assert others == [], (path.name, others)


# --- C02 ----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("block", ["transfer", "term_structure", "impact_detail"])
def test_the_c02_exploratory_blocks_cannot_appear_without_their_label(block: str) -> None:
    doc = load(H1)
    assert doc["outputs"][block]["label"] == "exploratory"
    for bad_label in ("final", "", None):
        bad = copy.deepcopy(doc)
        bad["outputs"][block]["label"] = bad_label
        assert not valid("c02/variant-horizon", bad)
    bad = copy.deepcopy(doc)
    del bad["outputs"][block]["label"]
    assert not valid("c02/variant-horizon", bad)
    bad = copy.deepcopy(doc)
    del bad["outputs"][block]
    assert not valid("c02/variant-horizon", bad)


def test_the_c02_impact_block_names_the_12_month_and_lifetime_ecl_effect_in_the_envelope_impact() -> None:
    doc = load(H1)
    assert set(doc["impact"]) == {"ecl_12m_effect", "ecl_lifetime_effect"}
    bad = copy.deepcopy(doc)
    del bad["impact"]["ecl_lifetime_effect"]
    assert not valid("c02/variant-horizon", bad)


def test_the_pooled_variant_carries_the_firm_overlap_caveat_and_the_five_files() -> None:
    doc = load(POOLED)
    assert doc["outputs"]["years"] is None and len(doc["outputs"]["pooled"]["files"]) == 5
    assert doc["outputs"]["pooled"]["horizon_indicator"] is True
    bad = copy.deepcopy(doc)
    bad["outputs"]["firm_overlap_caveat"] = None
    assert not valid("c02/variant-horizon", bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["pooled"] = None
    assert not valid("c02/variant-horizon", bad)
    single = load(H1)
    single["outputs"]["horizon_id"] = "pooled"
    assert not valid("c02/variant-horizon", single)


def test_the_c02_split_states_no_out_of_time_claim_and_a_training_slice_only_fit() -> None:
    doc = load(H1)
    s = doc["outputs"]["split"]
    assert s["out_of_time_claim"] is False and s["fit_on_training_slice_only"] is True and s["resampling_before_calibration"] is False
    for k, v in (("out_of_time_claim", True), ("fit_on_training_slice_only", False), ("resampling_before_calibration", True)):
        bad = copy.deepcopy(doc)
        bad["outputs"]["split"][k] = v
        assert not valid("c02/variant-horizon", bad)


def test_the_c02_term_structure_has_the_five_horizons_and_cumulative_pd_open_interval() -> None:
    pts = load(H1)["outputs"]["term_structure"]["points"]
    assert [p["years"] for p in pts] == [1, 2, 3, 4, 5]
    bad = load(H1)
    bad["outputs"]["term_structure"]["points"][0]["cumulative_pd"] = 1.0
    assert not valid("c02/variant-horizon", bad)


# --- C20 ----------------------------------------------------------------------------------------------------------


def test_a_c20_variant_on_sgcd_without_the_dataset_card_notice_fails() -> None:
    doc = load(SHOCK)
    assert doc["outputs"]["dataset_id"] == "sgcd" and doc["outputs"]["sgcd_notice"]["quote"] == V.SGCD_QUOTE
    bad = copy.deepcopy(doc)
    bad["outputs"]["sgcd_notice"] = None
    assert not valid("c20/variant-shock", bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["sgcd_notice"]["quote"] = "a different sentence"
    assert not valid("c20/variant-shock", bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["sgcd_notice"]["commit"] = "0" * 40
    assert not valid("c20/variant-shock", bad)


def test_the_sgcd_notice_is_null_off_sgcd_and_a_notice_without_sgcd_fails() -> None:
    doc = load(SEEDS)
    assert doc["outputs"]["dataset_id"] != "sgcd" and doc["outputs"]["sgcd_notice"] is None
    bad = copy.deepcopy(doc)
    bad["outputs"]["sgcd_notice"] = load(SHOCK)["outputs"]["sgcd_notice"]
    assert not valid("c20/variant-seeds", bad)


def test_the_taiwan_model_variants_carry_the_labelled_fairness_battery_and_others_do_not() -> None:
    for p in C20_VARIANTS:
        ref = ref_of(p)
        doc = load(p)
        taiwan = doc["outputs"]["model_dataset"] == "uci-taiwan"
        assert (doc["outputs"]["fairness_battery"] is not None) == taiwan, p.name
        bad = copy.deepcopy(doc)
        bad["outputs"]["fairness_battery"] = None if taiwan else load(SEEDS)["outputs"]["fairness_battery"]
        assert not valid(ref, bad), p.name
    battery = load(SEEDS)["outputs"]["fairness_battery"]
    assert battery["label"] == "labelled-fairness-battery"
    assert {r["test_id"] for r in battery["rows"]} == set(V.FAIR_TESTS)
    bad = load(SEEDS)
    bad["outputs"]["fairness_battery"]["label"] = "result"
    assert not valid("c20/variant-seeds", bad)


def test_every_c20_variant_carries_the_decision_flip_impact_block_and_envelope_item() -> None:
    for p in C20_VARIANTS:
        ref = ref_of(p)
        doc = load(p)
        assert doc["outputs"]["impact_detail"]["label"] == "decision-flip" and "decision_flip_share" in doc["impact"]
        bad = copy.deepcopy(doc)
        del bad["impact"]["decision_flip_share"]
        assert not valid(ref, bad)
        bad = copy.deepcopy(doc)
        bad["outputs"]["impact_detail"]["label"] = "other"
        assert not valid(ref, bad)


def test_the_shift_kind_carries_both_readings_each_labelled() -> None:
    doc = load(FIXTURES / "c20" / "variant-shift-fixture.json")
    o = doc["outputs"]
    assert o["real_drift"]["label"] == "real-drift-no-model" and o["real_drift"]["model"] is None
    assert o["synthetic_shift"]["label"] == "synthetic-shift-fed-reference"
    for key, other in (("real_drift", "label"), ("synthetic_shift", "label")):
        bad = copy.deepcopy(doc)
        bad["outputs"][key][other] = "unlabelled"
        assert not valid("c20/variant-shift", bad)
        bad = copy.deepcopy(doc)
        del bad["outputs"][key]
        assert not valid("c20/variant-shift", bad)
    cbpe = o["synthetic_shift"]["label_free"]["cbpe"]
    assert cbpe["label"] == "estimate" and len(cbpe["assumptions"]) == 4


def test_the_shock_kind_separates_the_shipped_shocks_from_contrastes_own_application() -> None:
    o = load(SHOCK)["outputs"]
    assert o["shipped"]["label"] == "shipped" and o["applied"]["label"] == "contraste-applied"
    assert o["model_view"] == "json_view"
    bad = load(SHOCK)
    bad["outputs"]["shipped"]["label"] = "invented"
    assert not valid("c20/variant-shock", bad)


def test_the_leakage_kind_carries_the_four_screens() -> None:
    o = load(FIXTURES / "c20" / "variant-leakage-fixture.json")["outputs"]
    assert set(o["screen"]) == {"temporal_order", "single_feature_auc", "entity_overlap", "resemblance_auc"}


# --- named parameters (Q8) ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("path,names", [(H1, V.C02_NAMES)] + [(p, V.C20_NAMES) for p in C20_VARIANTS], ids=lambda x: getattr(x, "stem", "names"))
def test_every_named_parameter_is_required_with_its_value_and_the_convention_label(path: Path, names: list[str]) -> None:
    ref = ref_of(path)
    doc = load(path)
    params = doc["outputs"]["parameters"]
    assert [p["name"] for p in params] == names
    assert all(p["label"] == "convention" for p in params)
    for i in range(len(params)):
        bad = copy.deepcopy(doc)
        bad["outputs"]["parameters"][i]["label"] = "regulatory"
        assert not valid(ref, bad), f"{names[i]}: a regulatory label passes"
        bad = copy.deepcopy(doc)
        del bad["outputs"]["parameters"][i]["label"]
        assert not valid(ref, bad)
        bad = copy.deepcopy(doc)
        del bad["outputs"]["parameters"][i]
        assert not valid(ref, bad), f"{names[i]}: a missing parameter passes"
        bad = copy.deepcopy(doc)
        del bad["outputs"]["parameters"][i]["value"]
        assert not valid(ref, bad)


def test_the_proposed_values_are_listed_with_a_basis_and_the_c20_models_repeat_them() -> None:
    assert set(V.NAMED) == set(V.C20_NAMES) and len(V.C20_NAMES) == 9
    m = load(FIXTURES / "c20" / "models-fixture.json")["fit"]["parameters"]
    assert [p["name"] for p in m] == V.C20_NAMES
    for name, (value, unit, basis) in V.NAMED.items():
        assert unit and basis, name
    assert V.NAMED["worst_subsample_share"][0] == 0.10, "the dossier's example (06 C.7 l.1013-1014)"


# --- C21 ----------------------------------------------------------------------------------------------------------


def test_a_c21_document_without_the_no_legal_claim_label_fails() -> None:
    doc = load(C21)
    assert doc["outputs"]["legal"]["label"]["en"] == "no legal claim"
    for edit in (lambda o: o["legal"].__setitem__("label", {"en": "legal finding", "es": "x"}),
                 lambda o: o["legal"].pop("label"), lambda o: o.pop("legal"),
                 lambda o: o["legal"].__setitem__("is_a_finding_of_violation", True),
                 lambda o: o["legal"]["regulation_b"].__setitem__("quote", "The effects test applies."),
                 lambda o: o["legal"].pop("procedures")):
        bad = copy.deepcopy(doc)
        edit(bad["outputs"])
        assert not valid("c21/variant-year-pair", bad)
    models = load(FIXTURES / "c21" / "models-fixture.json")
    bad = copy.deepcopy(models)
    bad["fit"]["legal"]["label"]["en"] = "x"
    assert not valid("c21/models", bad)


def test_the_legal_sentences_are_the_addendum_quotes_and_the_unconditional_rates_are_indicators_only() -> None:
    legal = load(C21)["outputs"]["legal"]
    assert legal["regulation_b"]["quote"].startswith("The Act does not provide that the 'effects test' applies")
    assert "Inclusive Communities" in legal["fair_housing_act"]["citation"]
    assert legal["procedures"]["quote"].startswith("Gross HMDA denial or approval rate disparities are not appropriate")
    assert legal["unconditional_rates_are"] == "indicators-only"


def contrast(doc: dict) -> dict:
    return doc["outputs"]["attributes"][0]["contrasts"][0]


def test_the_four_fifths_flag_is_labelled_an_employment_benchmark_and_follows_the_counts() -> None:
    import semantics
    doc = load(C21)
    ff = doc["outputs"]["attributes"][0]["four_fifths"]
    assert ff["label"] == "employment benchmark" and ff["is_credit_law_threshold"] is False and ff["decided_on"] == "exact-counts"
    for key, value in (("label", "credit-law threshold"), ("is_credit_law_threshold", True), ("threshold", 0.9)):
        bad = copy.deepcopy(doc)
        bad["outputs"]["attributes"][0]["four_fifths"][key] = value
        assert not valid("c21/variant-year-pair", bad), key
    bad = copy.deepcopy(doc)
    del bad["outputs"]["attributes"][0]["four_fifths"]["label"]
    assert not valid("c21/variant-year-pair", bad)
    flipped = copy.deepcopy(doc)
    row = flipped["outputs"]["attributes"][0]["four_fifths"]["groups"][1]
    row["flag"] = not row["flag"]
    assert any("four-fifths" in m for m in semantics.check_c21(flipped)), "a flag the counts do not give is refused by the producer check"


def test_the_adverse_impact_ratio_equals_the_parity_ratio_and_the_rates_are_the_counts_over_n() -> None:
    for attr in load(C21)["outputs"]["attributes"]:
        for g in attr["groups"]:
            assert abs(g["selection_rate"] - g["n_approved"] / g["n"]) < 1e-12 and g["n_approved"] + g["n_denied"] == g["n"]
        for c in attr["contrasts"]:
            assert abs(c["adverse_impact_ratio"]["value"] - c["parity_ratio"]) < 1e-12 and "four_fifths" not in c["adverse_impact_ratio"]
            assert abs(c["parity_gap"] - (c["selection_rate_group"] - c["selection_rate_reference"])) < 1e-12


def test_a_c21_document_with_an_outcome_conditioned_test_fails() -> None:
    doc = load(C21)
    for tid in V.FAIR_TESTS:
        bad = copy.deepcopy(doc)
        bad["tests"][0]["test_id"] = tid
        assert not valid("c21/variant-year-pair", bad), tid
    for key in ("equalized_odds", "equal_opportunity", "calibration_within_groups", "auc_by_group", "fairness_battery"):
        bad = copy.deepcopy(doc)
        bad["outputs"][key] = {}
        assert not valid("c21/variant-year-pair", bad), key
    ok = copy.deepcopy(doc)
    ok["tests"][0]["test_id"] = "fair.adverse_impact"
    assert valid("c21/variant-year-pair", ok)


def test_every_controlled_estimate_names_the_missing_credit_score_and_both_confirmations_are_by_sign_and_size() -> None:
    doc = load(C21)
    c = contrast(doc)
    for k in ("controlled", "rate_spread"):
        assert c[k]["estimate"]["missing_controls"] == ["credit_score"]
        bad = copy.deepcopy(doc)
        contrast(bad)[k]["estimate"]["missing_controls"] = []
        assert not valid("c21/variant-year-pair", bad)
    conf = c["confirmation"]["estimate"]
    assert conf["same_sign"] == ((conf["fit_coefficient"] > 0) == (conf["confirm_coefficient"] > 0))
    bad = copy.deepcopy(doc)
    contrast(bad)["controlled"] = {"estimate": None, "reason": None}
    assert not valid("c21/variant-year-pair", bad), "an estimate and its reason are never both absent"
    ok = copy.deepcopy(doc)
    contrast(ok)["controlled"] = {"estimate": None, "reason": {"x": 1}}
    assert not valid("c21/variant-year-pair", ok)
    ok = copy.deepcopy(doc)
    contrast(ok)["controlled"] = {"estimate": None, "reason": "too few rows in the group"}
    assert valid("c21/variant-year-pair", ok), "a missing estimate is a null with its reason"


def test_hmda_field_names_come_from_the_research_addendum_only() -> None:
    allowed = set(V.HMDA_FIELDS)
    # the addendum H1 names (sections 2.2 and 2.4, snapshot spellings)
    assert allowed == {"derived_race", "derived_ethnicity", "derived_sex", "applicant_age", "applicant_age_above_62", "action_taken",
                       "debt_to_income_ratio", "combined_loan_to_value_ratio", "income", "loan_amount", "property_value", "loan_type",
                       "loan_purpose", "lien_status", "occupancy_type", "rate_spread", "denial_reason_1", "denial_reason_2",
                       "denial_reason_3", "denial_reason_4"}
    schema = cs.load_json(SCHEMAS / "c21" / "variant-year-pair.schema.json")
    assert set(schema["$defs"]["c21Hmda"]["enum"]) == allowed
    assert set(schema["$defs"]["c21Control"]["enum"]) <= allowed
    assert set(schema["$defs"]["c21Attribute"]["properties"]["field"]["enum"]) == set(V.ATTRIBUTE_FIELDS)
    for hyphen in ("applicant_ethnicity-1", "\"loan_to_value_ratio\"", "ageapplicant"):
        assert hyphen not in json.dumps(schema), "aliases are values of a document's `alias` field, never a schema name"
    for p in (C21, FIXTURES / "c21" / "models-fixture.json"):
        text = p.read_text(encoding="utf-8")
        for name in re.findall(r'"(?:field|name)": "([a-z0-9_]+)"', text):
            assert name in allowed or name in {"credit_score", "debt_to_income_ratio"}, (p.name, name)


def test_the_legal_mapping_of_each_attribute_is_the_addendum_table_and_a_mismatch_fails() -> None:
    doc = load(C21)
    for attr in doc["outputs"]["attributes"]:
        basis, ecoa, fha = V.LEGAL[attr["field"]]
        assert (attr["legal"]["basis"], attr["legal"]["ecoa"], attr["legal"]["fha"]) == (basis, ecoa, fha)
    assert V.LEGAL["applicant_age"][2] is False, "age is ECOA only (not in 42 U.S.C. 3605(a))"
    assert V.LEGAL["derived_ethnicity"][0].endswith("UNVERIFIED")
    bad = copy.deepcopy(doc)
    bad["outputs"]["attributes"][0]["legal"]["basis"] = "race_color"
    assert not valid("c21/variant-year-pair", bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["attributes"][0]["field"] = "derived_race"
    assert not valid("c21/variant-year-pair", bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["attributes"][0]["field"] = "applicant_race_1"
    assert not valid("c21/variant-year-pair", bad)


def test_non_attribute_categories_are_carried_as_excluded_groups_and_never_as_a_contrast() -> None:
    for attr in load(C21)["outputs"]["attributes"]:
        names = [g["group"] for g in attr["groups"]]
        for ex in attr["excluded_groups"]:
            assert ex["group"] in V.NON_GROUPS[attr["field"]] and ex["group"] not in names
        for c in attr["contrasts"]:
            assert c["group"] in names and c["reference_group"] == attr["reference_group"]


def test_the_outcome_convention_and_the_year_pair_are_fixed() -> None:
    o = load(C21)["outputs"]
    assert o["conventions"]["outcome"]["approval_codes"] == [1, 2] and o["conventions"]["outcome"]["denial_codes"] == [3]
    assert o["conventions"]["label"] == "convention"
    assert o["confirm_year"] == o["fit_year"] + 1 and o["pair_id"] == "2018-19"
    bad = load(C21)
    bad["outputs"]["conventions"]["outcome"]["approval_codes"] = [1]
    assert not valid("c21/variant-year-pair", bad)
    bad = load(C21)
    bad["outputs"]["pair_id"] = "2017-18"
    assert not valid("c21/variant-year-pair", bad)


def test_situation_testing_is_in_with_the_ceteris_paribus_comparator_only() -> None:
    st = load(C21)["outputs"]["situation_testing"]
    assert st["comparator"] == "ceteris-paribus" and st["counterfactual_test"]["run"] is False
    bad = load(C21)
    bad["outputs"]["situation_testing"]["counterfactual_test"]["run"] = True
    assert not valid("c21/variant-year-pair", bad)
    bad = load(C21)
    bad["outputs"]["situation_testing"]["comparator"] = "mutatis-mutandis"
    assert not valid("c21/variant-year-pair", bad)


def test_a_field_hmda_bins_is_a_nullable_value_with_its_reason() -> None:
    notes = load(C21)["outputs"]["data_notes"]
    assert {n["field"] for n in notes} >= {"debt_to_income_ratio", "loan_amount"} and all(n["n_missing"] is None for n in notes)
    bad = load(C21)
    bad["outputs"]["data_notes"][0]["reason"] = None
    assert not valid("c21/variant-year-pair", bad)
    bad = load(C21)
    bad["outputs"]["data_notes"][0]["n_missing"] = "unknown"
    assert not valid("c21/variant-year-pair", bad)


# --- requirement ids ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("path,pattern", [(H1, r"^CT-02\d\d$"), (SHOCK, r"^CT-20\d\d$"), (C21, r"^CT-21\d\d$")], ids=["c02", "c20", "c21"])
def test_requirement_ids_follow_decision_q14(path: Path, pattern: str) -> None:
    ref = ref_of(path)
    doc = load(path)
    assert all(re.match(pattern, r) for r in doc["outputs"]["requirements"])
    bad = copy.deepcopy(doc)
    bad["outputs"]["requirements"] = ["CT-9999"]
    assert not valid(ref, bad)


# --- the scored_sample family bump ----------------------------------------------------------------------------------


def contract_module():
    from pipeline.io import contract as c
    return c


ROW = {"id": "a1", "observation_date": "2024-12-31", "target": 1, "pd": 0.04}


def test_an_existing_case_without_target_still_fails_after_the_bump() -> None:
    c = contract_module()
    rep = c.validate("scored_sample", [{"id": "a1", "observation_date": "2024-12-31", "pd": 0.04}])
    assert rep.accepted == [] and rep.rejected[0]["violations"][0]["field"] == "target"
    rep = c.validate("scored_sample", [{"id": "a1", "observation_date": "2024-12-31", "pd": 0.04}], params={"outcome": "target"})
    assert rep.accepted == [], "declaring outcome = target keeps target required"
    assert c.validate("scored_sample", [ROW]).accepted


def test_a_dataset_that_declares_no_outcome_passes_without_target_and_a_wrong_target_still_fails() -> None:
    c = contract_module()
    row = {"id": "h1", "observation_date": "2024-12-31", "decision": 1}
    rep = c.validate("scored_sample", [row], params={"outcome": "none"})
    assert len(rep.accepted) == 1 and rep.accepted[0]["target"] is None and rep.accepted[0]["decision"] == 1
    assert c.validate("scored_sample", [dict(row, target="2")], params={"outcome": "none"}).accepted == []
    assert c.validate("scored_sample", [row]).accepted == [], "without the parameter the row has no target"
    with pytest.raises(c.ContractError):
        c.validate("scored_sample", [row], params={"outcome": "maybe"})


def test_the_decision_field_is_an_optional_flag_and_rejects_other_values() -> None:
    c = contract_module()
    assert c.validate("scored_sample", [dict(ROW, decision=0)]).accepted[0]["decision"] == 0
    assert "decision" not in c.validate("scored_sample", [ROW]).accepted[0], "an absent decision leaves the record as it was before the bump"
    for bad in (2, "yes", True):
        assert c.validate("scored_sample", [dict(ROW, decision=bad)]).accepted == []
    f = c.SCORED_SAMPLE.field("decision")
    assert f is not None and f.kind == "flag" and f.required is False and "action taken" in f.meaning["en"]


def test_several_protected_attributes_are_the_cases_declared_open_fields_and_protected_attr_is_unchanged() -> None:
    c = contract_module()
    assert c.SCORED_SAMPLE.open_fields is True
    pa = c.SCORED_SAMPLE.field("protected_attr")
    assert pa is not None and pa.kind == "str" and pa.required is False
    extra = [c.Field("derived_race", "str", {"en": "race", "es": "raza"}, required=False),
             c.Field("derived_sex", "str", {"en": "sex", "es": "sexo"}, required=False)]
    rep = c.validate("scored_sample", [{"id": "h", "observation_date": "2024-12-31", "decision": 0, "derived_race": "Asian", "derived_sex": "Female"}],
                     params={"outcome": "none"}, extra_fields=extra)
    assert rep.accepted[0]["derived_race"] == "Asian" and rep.accepted[0]["derived_sex"] == "Female"


def test_the_committed_declaration_is_regenerated_from_the_producer_and_the_other_families_are_unchanged(tmp_path: Path) -> None:
    c = contract_module()
    c.export_contracts(tmp_path)
    for name in ("scored_sample", "loan_panel", "rating_history", "market_series", "curve", "balance_sheet", "loss_events", "macro_path", "index"):
        committed = (ROOT / "data" / "derived" / "contract" / f"{name}.json").read_text(encoding="utf-8")
        assert (tmp_path / f"{name}.json").read_text(encoding="utf-8") == committed, name
    doc = load(ROOT / "data" / "derived" / "contract" / "scored_sample.json")
    assert cs.errors("common/contract-family", doc) == []
    assert [f["name"] for f in doc["fields"]][:3] == ["id", "observation_date", "target"] and "decision" in [f["name"] for f in doc["fields"]]
    assert next(f for f in doc["fields"] if f["name"] == "target")["required"] is True
    assert next(p for p in doc["params"] if p["name"] == "outcome")["values"] == ["target", "none", "population"]
    assert doc["open_fields"] is True


# --- the catalog rows and the change fragment -----------------------------------------------------------------------

ROW_IDS = ["c02-outputs", "c02-models", "c20-outputs", "c20-outputs-shift", "c20-outputs-seeds", "c20-outputs-perturbation",
           "c20-outputs-leakage", "c20-models", "c21-outputs", "c21-models", "engine-ml-api", "engine-fairness-api"]


def cells(line: str) -> list[str]:
    body = line.strip().strip("|")
    return [c.strip() for c in re.split(r"(?<!\\)\|", body)]


def test_the_rows_fragment_has_the_twelve_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    lines = [ln for ln in ROWS.read_text(encoding="utf-8").splitlines() if ln.startswith("|")]
    assert cells(lines[0]) == header
    data = [cells(ln) for ln in lines[1:] if not all(set(c) <= set(":- ") for c in cells(ln))]
    contract_rows = [r for r in data if len(r) == len(header)]
    assert [r[0] for r in contract_rows] == ROW_IDS
    for r in contract_rows:
        d = dict(zip(header, r))
        assert d["version"] == "1.0.0" and d["status"] == "active" and d["provider"].startswith("fixture:")
        assert (ROOT / d["schema file"]).is_file(), d["schema file"]
        assert (ROOT / d["example"]).is_file(), d["example"]
        assert (ROOT / d["provider"].removeprefix("fixture:")).is_file(), d["provider"]
        for cell in (d["producer test"], d["consumer test"]):
            for t in cell.split(","):
                path, _, name = t.strip().partition("::")
                assert (ROOT / path).is_file(), path
                if name:
                    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), t
    text = ROWS.read_text(encoding="utf-8")
    assert "contract-family" in text and "1.1.0" in text, "the family bump is stated for the integrator"
    for rid in ("api",):
        assert rid in text
    cat_ids = [cells(ln)[0] for ln in catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0].splitlines() if ln.startswith("| ")]
    if ROWS_FRAGMENT.is_file():
        assert not set(ROW_IDS) & set(cat_ids), "the integrator merges these rows; a unit never edits the catalog"
    else:  # merged at the batch 3 integration: each row is in the Contracts table exactly once
        assert all(cat_ids.count(i) == 1 for i in ROW_IDS), [i for i in ROW_IDS if cat_ids.count(i) != 1]


def test_the_changes_fragment_is_bullets_only() -> None:
    lines = CHANGES.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].startswith("- ")
    for ln in lines:
        assert ln.startswith("- ") or ln.startswith("  ") or ln == "", ln
    assert not any(ln.startswith("#") for ln in lines)
    assert "1.1.0" in "\n".join(lines) and "scored_sample" in "\n".join(lines)


# --- the engine contracts -------------------------------------------------------------------------------------------


def sections(path: Path) -> dict[str, str]:
    parts = re.split(r"^### `([^`]+)`\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


ML_PATHS = ["robustness", "seeds", "explanations", "effects", "generalisation", "conformal", "leakage", "dataquality", "cbpe", "challenger", "plants"]
FAIR_PATHS = ["metrics", "inference", "conditional", "replication", "situation", "plants"]
RESULT_TYPES = re.compile(r"^@dataclass\(frozen=True\)", re.M)


@pytest.mark.parametrize("api,pkg,mods,tests,test_mod,prefix", [
    ("ml-api.md", "ml", sp.ML_MODULES, sp.ML_TESTS, "ml", "ml."),
    ("fairness-api.md", "fairness", sp.FAIR_MODULES, sp.FAIR_TESTS, "fairness", "fair."),
], ids=["ml", "fairness"])
def test_the_engine_contract_lists_every_function_of_the_sizing_modules_with_its_check(api, pkg, mods, tests, test_mod, prefix) -> None:
    path = ENGINE / api
    text = path.read_text(encoding="utf-8")
    version = "2.0.0" if pkg == "ml" else "1.0.0"  # engine-ml-api 2.0.0 (U14 G18); the fairness page names its history from 1.0.0
    assert f"engine-{pkg if pkg == 'fairness' else 'ml'}-api" in text and version in text and "common/test-result" in text
    sec = sections(path)
    expected_modules = ML_PATHS if pkg == "ml" else FAIR_PATHS
    assert list(mods) == expected_modules, "every module of the sizing's Modules and functions table"
    for m in expected_modules:
        assert f"`riskvalidation/{pkg}/{m}.py`" in text, m
    assert f"`riskvalidation/validation/{test_mod}.py`" in text
    declared = set()
    for m, (_, mod_pkg, funcs) in mods.items():
        assert len(funcs) >= 2, m
        for name, *_ in funcs:
            key = f"{mod_pkg}.{name}"
            declared.add(key)
            body = sec[key]
            assert "```python" in body, key
            for label in ("Units", "Invariants", "Check"):
                assert re.search(rf"^- {label}: \S", body, flags=re.M), f"{key}: no {label} line"
            if name[0].isupper():
                assert RESULT_TYPES.search(body) or "(GeneratorBase)" in body, f"{key}: result types are frozen dataclasses"
    if pkg == "ml":
        assert "`riskvalidation/ml/policy.py`" in text
        for mod_pkg, names in sp.ML_ADDED_2_0_0.values():
            for name in names:
                key = f"{mod_pkg}.{name}"
                declared.add(key)
                body = sec[key]
                assert "```python" in body, key
                for label in ("Units", "Invariants", "Check"):
                    assert re.search(rf"^- {label}: \S", body, flags=re.M), f"{key}: no {label} line"
    for name, tid, light in tests:
        key = f"riskvalidation.validation.{test_mod}.{name}"
        declared.add(key)
        body = sec[key]
        assert "-> TestResult" in body and tid.startswith(prefix), key
        assert f'test_id = "{tid}"' in body and re.search(r"^- Light: \S", body, flags=re.M), key
        assert "4,000 repetitions" in body and "no golden value is claimed" in body, key
    assert set(sec) == declared, "no function outside the modules table, none missing"


def test_the_fairness_contract_never_runs_outcome_conditioned_tests_on_hmda_and_labels_the_four_fifths_line() -> None:
    text = (ENGINE / "fairness-api.md").read_text(encoding="utf-8")
    assert "never run on HMDA" in text and "employment benchmark" in text and "never a credit-law threshold" in text
    for name in ("equalized_odds", "equal_opportunity", "calibration_within_groups", "auc_by_group"):
        body = sections(ENGINE / "fairness-api.md")[f"riskvalidation.validation.fairness.{name}"]
        assert "outcome-conditioned" in body and "not_evaluated" in body
    assert "29 CFR 1607.4(D)" in text and "0.8 exactly does not flag" in text and "highest-rate group" in text


def test_the_ml_contract_names_every_planted_defect_the_sizing_lists() -> None:
    sec = sections(ENGINE / "ml-api.md")
    for name in ("LeakPlant", "CovariateShiftPlant", "NoiseSensitivityPlant", "SeedUnstablePlant", "ExchangeabilityBreakPlant"):
        assert f"riskvalidation.ml.plants.{name}" in sec
    for name in ("ThresholdBiasPlant", "LabelNoiseBiasPlant", "ProxyFeaturePlant"):
        assert f"riskvalidation.fairness.plants.{name}" in sections(ENGINE / "fairness-api.md")


def test_the_new_files_have_no_em_dash_and_no_emoji() -> None:
    files = [ENGINE / "ml-api.md", ENGINE / "fairness-api.md", ROWS, CHANGES, *sorted(Path(__file__).parent.glob("*.py"))]
    for c in ("c02", "c20", "c21"):
        files += sorted((SCHEMAS / c).glob("*.json")) + sorted((FIXTURES / c).glob("*.json"))
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert chr(0x2014) not in text and chr(0x2015) not in text, f
        assert not any(0x1F000 <= ord(ch) <= 0x1FAFF or ord(ch) == 0xFE0F for ch in text), f


def test_the_merged_rows_are_in_the_catalog_contracts_table_exactly_once() -> None:
    if ROWS_FRAGMENT.is_file():
        return  # not merged yet: the fragment tests above hold
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    contracts = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0]
    ids = [ln.split("|")[1].strip() for ln in contracts.splitlines() if ln.startswith("| ")]
    ours = [ln.split("|")[1].strip() for ln in ROWS.read_text(encoding="utf-8").split("## producer-checks")[0].splitlines()
            if ln.startswith("| ") and not ln.startswith("| id ") and not ln.startswith("|---") and ln.split("|")[2].strip() == "1.0.0"
            and ln.count("|") > 6]
    assert len(ours) == 12, ours
    assert all(ids.count(i) == 1 for i in ours), [i for i in ours if ids.count(i) != 1]

