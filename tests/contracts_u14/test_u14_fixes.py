"""U14-S fix round (2026-10-19): one test per finding of the Opus review (``wip/contraste/review-u14-s-2026-10-18.md``) and per
decision of the main session (V1 to V7 of the sizing's "Decisions after the U14-S review").

Every plant changes exactly one thing in a copy of a fixture; a plant is refused by the schema, or (a cross-field rule JSON Schema
cannot hold) by ``semantics.py``, the producer-side checks the U14-P bakes call. The tests that read a written page read the page.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

import api_spec as sp
import build_fixtures as bf
import contract_schemas as cs
import values as V
from test_u14_contracts import (C21, DOCS, ENGINE, FIXTURES, H1, POOLED, ROWS, SCHEMAS, SEEDS, SHOCK, load, ref_of, valid)

ROOT = cs.ROOT
sys.path.insert(0, str(ROOT / "data-pipeline"))
SHIFT = FIXTURES / "c20" / "variant-shift-fixture.json"
LEAKAGE = FIXTURES / "c20" / "variant-leakage-fixture.json"
C21_MODELS = FIXTURES / "c21" / "models-fixture.json"
REF = "c21/variant-year-pair"


def sem():
    try:
        import semantics
    except ImportError:
        pytest.fail("tests/contracts_u14/semantics.py (the producer-side checks) does not exist")
    return semantics


def attribute(doc: dict, field: str = "derived_sex") -> dict:
    return next(a for a in doc["outputs"]["attributes"] if a["field"] == field)


def with_attribute(spec: list[tuple[str, int, int]], reference: str, field: str = "derived_sex") -> dict:
    """The C21 fixture with the attribute rebuilt from (group, approved, n) counts and the stated reference group."""
    doc = load(C21)
    doc["outputs"]["attributes"] = [bf.c21_attribute(field, spec, reference) if a["field"] == field else a
                                    for a in doc["outputs"]["attributes"]]
    return doc


# --- M1 and M2: the four-fifths flag --------------------------------------------------------------------------------


def test_m1_exactly_four_fifths_is_not_flagged_and_the_float_ratio_does_not_decide() -> None:
    assert (60 / 100) / (75 / 100) < 0.8, "the float trap the review found: 0.7999999999999999"
    assert Fraction(60, 100) / Fraction(75, 100) == Fraction(4, 5)
    doc = with_attribute([("Male", 75, 100), ("Female", 60, 100)], "Male")
    ff = attribute(doc)["four_fifths"]
    flag = next(g for g in ff["groups"] if g["group"] == "Female")
    assert flag["flag"] is False, "exactly 4/5 does not flag"
    assert valid(REF, doc), "the schema stops forcing the flag from the float"
    assert sem().check_c21(doc) == []
    bad = copy.deepcopy(doc)
    next(g for g in attribute(bad)["four_fifths"]["groups"] if g["group"] == "Female")["flag"] = True
    assert any("four-fifths" in m for m in sem().check_c21(bad)), "the flag raised at exactly 4/5 is refused by the exact counts"


def test_m1_the_flag_is_decided_on_the_counts_in_exact_arithmetic() -> None:
    s = sem()
    assert s.four_fifths_flag(60, 100, 75, 100) is False
    assert s.four_fifths_flag(5999, 10000, 75, 100) is True
    assert s.four_fifths_flag(6001, 10000, 75, 100) is False
    assert s.four_fifths_flag(0, 10, 0, 10) is False, "a highest rate of 0 raises no flag"
    text = (ENGINE / "fairness-api.md").read_text(encoding="utf-8")
    assert "5 * x_g * n_h < 4 * x_h * n_g" in text and "60/100" in text and "75/100" in text


def test_m2_the_flag_compares_each_group_with_the_highest_rate_group() -> None:
    # White 0.75 (reference), Asian 0.90, Black 0.65: against White Black is 0.867 (no flag), against the highest rate 0.722 (flag)
    spec = [("White", 750, 1000), ("Asian", 900, 1000), ("Black or African American", 650, 1000)]
    doc = with_attribute(spec, "White", "derived_race")
    ff = attribute(doc, "derived_race")["four_fifths"]
    assert ff["highest_rate_group"] == "Asian"
    by = {g["group"]: g for g in ff["groups"]}
    assert by["Black or African American"]["flag"] is True and by["White"]["flag"] is False and by["Asian"]["flag"] is False
    assert abs(by["Black or African American"]["ratio_to_highest"] - 650 / 900) < 1e-12
    assert valid(REF, doc) and sem().check_c21(doc) == []
    for edit in (lambda f: f.__setitem__("highest_rate_group", "White"),
                 lambda f: next(g for g in f["groups"] if g["group"] == "Black or African American").__setitem__("flag", False)):
        bad = copy.deepcopy(doc)
        edit(attribute(bad, "derived_race")["four_fifths"])
        assert sem().check_c21(bad), "a flag computed against a group other than the highest-rate group is refused"
    air = next(c for c in attribute(doc, "derived_race")["contrasts"] if c["group"] == "Black or African American")["adverse_impact_ratio"]
    assert abs(air["value"] - 650 / 750) < 1e-12, "the AIR against the chosen reference stays as the parity ratio"
    assert "four_fifths" not in air


def test_m2_the_four_fifths_block_is_closed_and_labelled() -> None:
    doc = load(C21)
    for key, value in (("label", "credit-law threshold"), ("is_credit_law_threshold", True), ("threshold", 0.9),
                       ("citation", "12 CFR 1002.6"), ("compared_with", "reference-group"), ("highest_rate_group", "Martian")):
        bad = copy.deepcopy(doc)
        attribute(bad)["four_fifths"][key] = value
        assert not valid(REF, bad), key
    for key in ("ratio_to_highest", "flag", "group"):
        bad = copy.deepcopy(doc)
        del attribute(bad)["four_fifths"]["groups"][0][key]
        assert not valid(REF, bad), key
    bad = copy.deepcopy(doc)
    del attribute(bad)["four_fifths"]["highest_rate_group"]
    assert not valid(REF, bad)


# --- M3: the SGCD notice cannot be bypassed --------------------------------------------------------------------------


def test_m3_a_shock_document_cannot_leave_sgcd_to_drop_the_notice() -> None:
    doc = load(SHOCK)
    assert doc["outputs"]["dataset_id"] == "sgcd"
    for other in ("uci-german", "uci-taiwan", "uci-polish", "fed-2025-corporate"):
        bad = copy.deepcopy(doc)
        bad["outputs"]["dataset_id"] = other
        bad["outputs"]["sgcd_notice"] = None
        assert not valid("c20/variant-shock", bad), other
    bad = copy.deepcopy(doc)
    bad["outputs"]["sgcd_notice"] = None
    assert not valid("c20/variant-shock", bad)


# --- M4: the groups are the addendum's groups ------------------------------------------------------------------------


def add_contrast_on(doc: dict, group: str) -> dict:
    a = attribute(doc)
    c = copy.deepcopy(a["contrasts"][0])
    c["group"] = group
    a["contrasts"].append(c)
    return doc


@pytest.mark.parametrize("edit,why", [
    (lambda d: add_contrast_on(d, "Joint"), "a contrast on Joint"),
    (lambda d: attribute(d)["groups"].append(dict(attribute(d)["groups"][0], group="Sex Not Available")), "a non-group inside groups"),
    (lambda d: attribute(d)["groups"].append(dict(attribute(d)["groups"][0], group="Martian")), "an unknown group"),
    (lambda d: attribute(d)["contrasts"][0].__setitem__("reference_group", "Joint"), "a contrast against Joint"),
    (lambda d: attribute(d).__setitem__("reference_group", "Sex Not Available"), "a non-group as the reference"),
    (lambda d: attribute(d)["excluded_groups"][0].__setitem__("group", "Female"), "a protected group listed as excluded"),
    (lambda d: attribute(d)["excluded_groups"].append(dict(attribute(d)["excluded_groups"][0], group="Race Not Available")),
     "a non-group of another attribute as excluded"),
    (lambda d: attribute(d)["four_fifths"]["groups"][0].__setitem__("group", "Joint"), "a four-fifths row on Joint"),
], ids=lambda x: x if isinstance(x, str) else "")
def test_m4_a_group_outside_the_addendum_is_refused(edit, why: str) -> None:
    bad = load(C21)
    edit(bad)
    assert not valid(REF, bad), why


def test_m4_every_attribute_carries_only_its_own_groups_and_non_groups() -> None:
    for a in load(C21)["outputs"]["attributes"]:
        assert {g["group"] for g in a["groups"]} <= set(V.GROUPS[a["field"]])
        assert {g["group"] for g in a["excluded_groups"]} <= set(V.NON_GROUPS[a["field"]])
        assert a["reference_group"] in V.GROUPS[a["field"]]


# --- M5: the quantities the views draw ------------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["roc", "cap", "reliability"])
def test_m5_a_c02_rung_carries_its_roc_cap_and_reliability_points(key: str) -> None:
    doc = load(H1)
    assert key in doc["outputs"]["rungs"][0], f"c02 rung has no {key}"
    bad = copy.deepcopy(doc)
    del bad["outputs"]["rungs"][0][key]
    assert not valid("c02/variant-horizon", bad)


def test_m5_the_c02_curves_have_the_shape_of_c01() -> None:
    doc = load(H1)
    r = doc["outputs"]["rungs"][0]
    assert set(r["roc"]) == {"fpr", "tpr"} and set(r["cap"]) == {"population", "defaults", "default_rate"}
    assert set(r["reliability"][0]) == {"n", "pd", "dr", "lo", "hi"}
    bad = copy.deepcopy(doc)
    bad["outputs"]["rungs"][0]["roc"]["fpr"] = []
    assert not valid("c02/variant-horizon", bad), "a curve has points"
    bad = copy.deepcopy(doc)
    bad["outputs"]["rungs"][0]["reliability"][0]["pd"] = 1.0
    assert not valid("c02/variant-horizon", bad)
    assert sem().check_c02(doc) == []
    for edit in (lambda x: x["roc"]["tpr"].pop(), lambda x: x["roc"]["tpr"].__setitem__(2, 0.1),
                 lambda x: x["cap"]["defaults"].pop()):
        bad = copy.deepcopy(doc)
        edit(bad["outputs"]["rungs"][0])
        assert sem().check_c02(bad), "a curve with unequal or decreasing points is refused by the producer check"


def test_m5_c20_carries_the_explainer_agreement_and_the_conformal_coverage_by_window() -> None:
    doc = load(SEEDS)
    ea = doc["outputs"]["explainer_agreement"]
    assert ea[0]["top_features"][0]["ale"]["edges"], "the ALE curves of the top features"
    assert -1 <= ea[0]["rank_correlation"] <= 1
    bad = copy.deepcopy(doc)
    del bad["outputs"]["explainer_agreement"]
    assert not valid("c20/variant-seeds", bad)
    bad = copy.deepcopy(doc)
    del bad["outputs"]["explainer_agreement"][0]["top_features"][0]["ale"]
    assert not valid("c20/variant-seeds", bad)
    shift = load(SHIFT)
    conf = shift["outputs"]["synthetic_shift"]["label_free"]["conformal"]
    assert conf["coverage_by_window"][0]["window"]
    bad = copy.deepcopy(shift)
    del bad["outputs"]["synthetic_shift"]["label_free"]["conformal"]["coverage_by_window"]
    assert not valid("c20/variant-shift", bad)
    bad = copy.deepcopy(shift)
    bad["outputs"]["synthetic_shift"]["label_free"]["conformal"]["coverage_by_window"] = []
    assert not valid("c20/variant-shift", bad)


def test_m5_attribution_rank_correlation_is_defined() -> None:
    schema = cs.load_json(SCHEMAS / "c20" / "variant-shock.schema.json")
    d = schema["$defs"]["c20ShockRow"]["properties"]["attribution_rank_correlation"]
    assert "rank_agreement" in json.dumps(d) and "Spearman" in json.dumps(d)
    text = (ENGINE / "ml-api.md").read_text(encoding="utf-8")
    assert "attribution_rank_correlation" in text, "the engine page says which function produces the field"


# --- M6: the split-conformal reference -------------------------------------------------------------------------------


def test_m6_the_split_conformal_reference_is_the_kth_order_statistic() -> None:
    import numpy as np
    s = np.arange(1, 101, dtype=float)
    k = 91
    assert np.sort(s)[k - 1] == 91.0
    assert np.quantile(s, k / 100, method="higher") == 92.0, "the named reference of the first version returned the 92nd score"
    assert np.quantile(s, k / 100, method="inverted_cdf") == 91.0
    text = (ENGINE / "ml-api.md").read_text(encoding="utf-8")
    body = text.split("### `riskvalidation.ml.conformal.split_conformal_quantile`")[1].split("### `", 1)[0]
    assert "numpy.sort(scores)[k - 1]" in body and "91" in body and "100" in body
    assert "method 'higher'" not in body and "method='higher'" not in body
    assert "MAPIE" in body and "UNVERIFIED" in body


# --- M7 and M8: the lights ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("page,tests,prefix", [("ml-api.md", sp.ML_TESTS, "ml."), ("fairness-api.md", sp.FAIR_TESTS, "fair.")], ids=["ml", "fair"])
def test_m7_the_lights_use_the_engine_policy_and_every_threshold_is_written(page: str, tests: list, prefix: str) -> None:
    text = (ENGINE / page).read_text(encoding="utf-8")
    for undefined in ("MlPolicy", "FairPolicy", "DEFAULT_POLICY"):
        assert undefined not in text, undefined
    assert "riskvalidation.core.policy.Policy" in text and "Threshold(kind, amber, red)" in text
    section = text.split("## Policy thresholds", 1)[1].split("\n## ", 1)[0]
    rows = [ln for ln in section.splitlines() if ln.startswith("| `")]
    keys = {r.split("|")[1].strip(" `") for r in rows}
    for _, tid, _light in tests:
        assert tid in keys or any(k.startswith(tid + ".") for k in keys), f"{tid} has no policy row"
    for r in rows:
        cells_ = [c.strip() for c in r.strip().strip("|").split("|")]
        assert cells_[-1] == "convention" or cells_[-1].startswith("rule, not a convention"), r
        assert re.search(r"\d", cells_[3]) or cells_[3] == "none", r
    blocks = text.split("### `")
    for _, tid, _l in tests:
        sec = next(b for b in blocks if f'test_id = "{tid}"' in b)
        assert "Policy key" in sec or "no policy threshold" in sec, tid
        if "Policy key" in sec:
            assert "policy: Policy | None = None" in sec, tid


def test_m7_the_conventions_of_the_review_are_listed_with_the_label() -> None:
    ml = (ENGINE / "ml-api.md").read_text(encoding="utf-8")
    fair = (ENGINE / "fairness-api.md").read_text(encoding="utf-8")
    for key in ("ml.leakage_screen.single_feature_auc", "ml.leakage_screen.resemblance_auc", "ml.conformal_coverage"):
        assert f"`{key}`" in ml, key
    for key in ("fair.demographic_parity", "fair.situation_testing"):
        assert f"`{key}`" in fair, key
    for conv in ("min_n = 30", "alpha = 0.10"):
        assert conv in ml, conv
    assert "k = 30" in fair and "convention" in fair.split("## Conventions table", 1)[1]


def test_m8_the_robustness_light_does_not_contradict_itself() -> None:
    text = (ENGINE / "ml-api.md").read_text(encoding="utf-8")
    body = text.split('test_id = "ml.robustness"', 1)[1].split("### `", 1)[0]
    assert "amber between the tolerance and twice the tolerance" not in body
    assert "green when the degradation is at most the tolerance" in body and "amber above the tolerance up to twice the tolerance" in body
    assert "red above twice the tolerance" in body
    assert "Threshold.classify" in text and "inclusive" in text


# --- M9 and m12: the HMDA identifier, the dates and the decision -----------------------------------------------------


def contract_module():
    from pipeline.io import contract as c
    return c


def test_m9_public_hmda_gets_a_row_position_id_and_the_activity_years_last_day() -> None:
    c = contract_module()
    rows = [{"id": "2018-1", "observation_date": "2018-12-31", "decision": 1, "derived_sex": "Male"},
            {"id": "2018-2", "observation_date": "2018-12-31", "decision": 0, "derived_sex": "Female"},
            {"id": "2019-1", "observation_date": "2019-12-31", "decision": 1, "derived_sex": "Male"}]
    extra = [c.Field("derived_sex", "str", {"en": "sex", "es": "sexo"}, required=False)]
    rep = c.validate("scored_sample", rows, params={"outcome": "none"}, extra_fields=extra)
    assert len(rep.accepted) == 3 and rep.rejected == []
    note = " ".join(n["en"] for n in c.SCORED_SAMPLE.notes)
    assert V.HMDA_ID_RULE in note and V.HMDA_DATE_RULE in note and "convention" in note
    # a repeated position within one activity year is refused by the family's own uniqueness rule
    dup = rows[:1] + [dict(rows[0])]
    assert len(c.validate("scored_sample", dup, params={"outcome": "none"}).accepted) < 2


def test_m9_the_c21_document_states_the_two_conventions_labelled() -> None:
    doc = load(C21)
    ident = doc["outputs"]["conventions"]["identifiers"]
    assert ident["id"] == V.HMDA_ID_RULE and ident["observation_date"] == V.HMDA_DATE_RULE and ident["label"] == "convention"
    for edit in (lambda i: i.__setitem__("label", "regulatory"), lambda i: i.__setitem__("id", "loan_identifier"),
                 lambda i: i.__setitem__("observation_date", "application_date"), lambda i: i.pop("label")):
        bad = copy.deepcopy(doc)
        edit(bad["outputs"]["conventions"]["identifiers"])
        assert not valid(REF, bad)
    bad = load(C21_MODELS)
    bad["fit"]["conventions"]["identifiers"]["id"] = "loan_identifier"
    assert not valid("c21/models", bad)


def test_m12_a_dataset_that_declares_no_outcome_must_carry_the_decision() -> None:
    c = contract_module()
    row = {"id": "2018-1", "observation_date": "2018-12-31"}
    rep = c.validate("scored_sample", [row], params={"outcome": "none"})
    assert rep.accepted == [], "outcome none without decision is refused"
    assert rep.rejected[0]["violations"][0]["field"] == "decision"
    assert len(c.validate("scored_sample", [dict(row, decision=1)], params={"outcome": "none"}).accepted) == 1
    assert len(c.validate("scored_sample", [dict(row, target=1)]).accepted) == 1, "an existing case with target is unchanged"
    assert c.validate("scored_sample", [dict(row, target=1)], params={"outcome": "target"}).accepted
    doc = cs.load_json(ROOT / "data" / "derived" / "contract" / "scored_sample.json")
    assert "decision" in json.dumps(next(p for p in doc["params"] if p["name"] == "outcome"))


# --- M10: the situation-testing distance -----------------------------------------------------------------------------


def test_m10_gower_distance_takes_a_normalization_and_the_counts_are_claimed_under_standard_only() -> None:
    text = (ENGINE / "fairness-api.md").read_text(encoding="utf-8")
    body = text.split("### `riskvalidation.fairness.situation.gower_distance`")[1].split("### `", 1)[0]
    assert 'normalization: str = "range"' in body
    assert "range" in body and "standard" in body and "default" in body
    st = text.split("### `riskvalidation.fairness.situation.situation_test`")[1].split("### `", 1)[0]
    assert "55" in st and "44" in st and "normalization='standard'" in st, "the 7.6 (2) counts are claimed only under standard"
    toy = text.split("### `riskvalidation.fairness.situation.situation_statistic`")[1].split("### `", 1)[0]
    assert "both normalizations" in text or "holds under both" in text
    assert "## Findings" in text and "StandardScaler" in text.split("## Findings", 1)[1]
    assert toy
    schema = cs.load_json(SCHEMAS / "c21" / "variant-year-pair.schema.json")
    assert schema["$defs"]["c21Situation"]["properties"]["distance_normalization"] == {"const": "range"}
    assert load(C21)["outputs"]["situation_testing"]["distance_normalization"] == "range"
    bad = load(C21)
    bad["outputs"]["situation_testing"]["distance_normalization"] = "standard"
    assert not valid(REF, bad), "C21's choice is the paper's text"


def test_m10_the_two_normalizations_agree_on_the_toy_golden_and_can_differ_in_general() -> None:
    import numpy as np
    score = np.array([10.0, 11, 12, 13, 10.5, 11.5, 12.5, 13.5])
    center = score[:1]
    rng = score.max() - score.min()
    sd = score.std()
    assert list(np.argsort(np.abs(score - center) / rng, kind="stable")) == list(np.argsort(np.abs(score - center) / sd, kind="stable"))
    # two continuous attributes: the k-nearest set can change with the scale
    pool = np.array([[0.0, 4.0], [1.0, 0.0]])
    c = np.array([0.0, 0.0])
    r = np.array([2.0, 10.0])
    s = np.array([1.0, 2.0])
    first = lambda sc: int(np.argmin((np.abs(pool - c) / sc).mean(axis=1)))  # noqa: E731
    assert first(r) != first(s)


# --- m1: enumerable cross-field rules, and the producer checks -----------------------------------------------------


@pytest.mark.parametrize("pair,fit,confirm", [("2018-19", 2019, 2020), ("2018-19", 2018, 2020), ("2019-20", 2018, 2019), ("2023-24", 2022, 2023)])
def test_m1_pair_id_agrees_with_its_two_years(pair: str, fit: int, confirm: int) -> None:
    bad = load(C21)
    bad["outputs"].update({"pair_id": pair, "fit_year": fit, "confirm_year": confirm})
    assert not valid(REF, bad)


def test_m1_every_pair_id_validates_with_its_own_years() -> None:
    for pid, (fy, cy) in V.PAIRS.items():
        doc = load(C21)
        doc["outputs"].update({"pair_id": pid, "fit_year": fy, "confirm_year": cy})
        assert valid(REF, doc), pid


@pytest.mark.parametrize("horizon,years", [("h1", 2), ("h3", 1), ("h5", 4), ("pooled", 1)])
def test_m1_horizon_id_agrees_with_years(horizon: str, years: int) -> None:
    bad = load(POOLED if horizon == "pooled" else H1)
    bad["outputs"]["horizon_id"] = horizon
    bad["outputs"]["years"] = years
    assert not valid("c02/variant-horizon", bad)


def test_m1_every_horizon_validates_with_its_own_years() -> None:
    for hid, years in V.HORIZON_YEARS.items():
        if hid == "pooled":
            continue
        doc = load(H1)
        doc["outputs"]["horizon_id"], doc["outputs"]["years"] = hid, years
        assert valid("c02/variant-horizon", doc), hid


def test_m1_the_producer_checks_refuse_the_cross_field_plants_the_review_listed() -> None:
    s = sem()
    h1 = load(H1)
    assert s.check_c02(h1) == [] and s.check_c20(load(SHOCK)) == [] and s.check_c21(load(C21)) == []
    plants = {
        "auc interval order": (h1, lambda d: d["outputs"]["rungs"][0]["discrimination"]["auc_ci"].update(lo=0.9, hi=0.1), s.check_c02),
        "overfit flag": (h1, lambda d: d["outputs"]["rungs"][0]["overfit"].update(gap=0.2, flag=False), s.check_c02),
        "events above rows": (h1, lambda d: d["outputs"]["counts"].update(events=10 ** 6), s.check_c02),
        "term structure": (h1, lambda d: d["outputs"]["term_structure"]["points"][2].update(cumulative_pd=0.01), s.check_c02),
        "AIR against the rates": (load(C21), lambda d: attribute(d)["contrasts"][0]["adverse_impact_ratio"].update(value=0.5), s.check_c21),
        "situation counts": (load(C21), lambda d: d["outputs"]["situation_testing"].update(n_significant=10 ** 6), s.check_c21),
        "same sign": (load(C21), lambda d: attribute(d)["contrasts"][0]["confirmation"]["estimate"].update(confirm_coefficient=0.5), s.check_c21),
        "confirmation years": (load(C21), lambda d: attribute(d)["contrasts"][0]["confirmation"]["estimate"].update(fit_year=2020), s.check_c21),
        "single feature suspect": (load(LEAKAGE), lambda d: d["outputs"]["screen"]["single_feature_auc"].update(suspect=False), s.check_c20),
        "applied parameters": (load(SHOCK), lambda d: d["outputs"]["parameters"][1].update(value=99), s.check_c20),
    }
    for name, (doc, edit, check) in plants.items():
        bad = copy.deepcopy(doc)
        edit(bad)
        assert check(bad), name


def test_m1_the_rows_fragment_lists_the_producer_checks_per_case_contract() -> None:
    text = ROWS.read_text(encoding="utf-8")
    assert "## producer-checks" in text
    section = text.split("## producer-checks", 1)[1]
    for rid in ("c02-outputs", "c20-outputs", "c20-outputs-shift", "c20-outputs-seeds", "c20-outputs-perturbation", "c20-outputs-leakage",
                "c21-outputs"):
        assert f"### {rid}" in section, rid
    assert "tests/contracts_u14/semantics.py" in section


# --- m2, m3, m4, m5, m6, m14 ----------------------------------------------------------------------------------------


def test_m2_the_shipped_and_applied_blocks_are_bound_to_their_labels() -> None:
    doc = load(SHOCK)
    for edit in (lambda o: o["shipped"].__setitem__("label", "contraste-applied"), lambda o: o["applied"].__setitem__("label", "shipped"),
                 lambda o: o["applied"].__setitem__("parameters_source", None),
                 lambda o: o["shipped"].__setitem__("parameters_source", "SGCDataset_metadata.json, seed 42")):
        bad = copy.deepcopy(doc)
        edit(bad["outputs"])
        assert not valid("c20/variant-shock", bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["shipped"], bad["outputs"]["applied"] = bad["outputs"]["applied"], bad["outputs"]["shipped"]
    assert not valid("c20/variant-shock", bad)


def test_m3_a_c21_test_id_must_be_on_the_allowlist() -> None:
    doc = load(C21)
    for tid in ("fair.equalised_odds", "fair.eq_odds", "fair.true_positive_rate_gap", "ml.calibration_within_groups",
                "pd.calibration_by_group", "fair.equalized_odds", "disc.auc"):
        bad = copy.deepcopy(doc)
        bad["tests"][0]["test_id"] = tid
        assert not valid(REF, bad), tid
    for tid in V.C21_TESTS:
        ok = copy.deepcopy(doc)
        ok["tests"][0]["test_id"] = tid
        assert valid(REF, ok), tid


def test_m4_the_fairness_battery_holds_each_test_and_attribute_once() -> None:
    doc = load(SEEDS)
    rows = doc["outputs"]["fairness_battery"]["rows"]
    assert {(r["test_id"], r["attribute"]) for r in rows} == {(t, a) for t in V.FAIR_TESTS for a in V.FAIR_ATTRIBUTES} and len(rows) == 12
    one_row_four_times = copy.deepcopy(doc)
    one_row_four_times["outputs"]["fairness_battery"]["rows"] = [copy.deepcopy(rows[0]) for _ in range(4)]
    assert not valid("c20/variant-seeds", one_row_four_times)
    twelve_copies = copy.deepcopy(doc)
    twelve_copies["outputs"]["fairness_battery"]["rows"] = [copy.deepcopy(rows[0]) for _ in range(12)]
    assert not valid("c20/variant-seeds", twelve_copies)
    short = copy.deepcopy(doc)
    short["outputs"]["fairness_battery"]["rows"] = rows[:4]
    assert not valid("c20/variant-seeds", short)
    swapped = copy.deepcopy(doc)
    swapped["outputs"]["fairness_battery"]["rows"][0]["attribute"] = "age"
    assert not valid("c20/variant-seeds", swapped), "a (test, attribute) pair held twice and another missing"
    for i, row in enumerate(rows):
        dup = copy.deepcopy(doc)
        dup["outputs"]["fairness_battery"]["rows"][i]["attribute"] = V.FAIR_ATTRIBUTES[(V.FAIR_ATTRIBUTES.index(row["attribute"]) + 1) % 3]
        assert not valid("c20/variant-seeds", dup), f"row {i} duplicated another (test, attribute) pair"


def test_m5_the_c21_schemas_carry_the_hmda_licence_status() -> None:
    for ref, path, root in ((REF, C21, "outputs"), ("c21/models", C21_MODELS, "fit")):
        doc = load(path)
        lic = doc[root]["licence"]
        assert lic["status"] == "UNVERIFIED" and lic["platform_terms"] == V.HMDA_PLATFORM_TERMS and lic["modified_statement"] == V.HMDA_MODIFIED
        for key, value in (("status", "CC0"), ("platform_terms", "public domain"), ("modified_statement", "unmodified")):
            bad = copy.deepcopy(doc)
            bad[root]["licence"][key] = value
            assert not valid(ref, bad), key
        bad = copy.deepcopy(doc)
        del bad[root]["licence"]
        assert not valid(ref, bad)


def test_m6_the_legal_mapping_carries_the_fha_disparate_impact_statement() -> None:
    doc = load(C21)
    for a in doc["outputs"]["attributes"]:
        assert a["legal"]["fha_disparate_impact"] == V.FHA_DISPARATE_IMPACT[a["field"]]
    bad = copy.deepcopy(doc)
    attribute(bad)["legal"]["fha_disparate_impact"] = "assessed"
    assert not valid(REF, bad)
    bad = copy.deepcopy(doc)
    del attribute(bad)["legal"]["fha_disparate_impact"]
    assert not valid(REF, bad)


def test_m7_the_z_result_carries_its_note_and_the_degenerate_case_says_so() -> None:
    text = (ENGINE / "fairness-api.md").read_text(encoding="utf-8")
    assert "class ZResult: statistic: float; p_value: float; n1: int; n2: int; note: str | None" in text


def test_m8_the_one_sided_wald_golden_uses_the_exact_normal_quantile() -> None:
    from statistics import NormalDist
    z = NormalDist().inv_cdf(0.95)
    w = z * (0.25 / 2) ** 0.5
    assert abs(w - 0.58154) < 1e-5 and abs((0.5 - w) - (-0.0815)) < 1e-4
    text = (ENGINE / "fairness-api.md").read_text(encoding="utf-8")
    body = text.split("### `riskvalidation.fairness.situation.wald_interval_one_sided`")[1].split("### `", 1)[0]
    assert "-0.0815" in body and "0.58154" in body and "[-0.082, 1.082]" not in body and "0.581595" not in body
    assert "0.581595" in text.split("## Findings", 1)[1], "the code's value is recorded as a finding, not claimed"


def test_m9_the_conventions_are_labelled_in_the_documents() -> None:
    leak = load(LEAKAGE)["outputs"]
    assert leak["thresholds"]["single_feature_auc"]["label"] == "convention" and leak["thresholds"]["resemblance_auc"]["label"] == "convention"
    bad = load(LEAKAGE)
    bad["outputs"]["thresholds"]["single_feature_auc"]["label"] = "regulatory"
    assert not valid("c20/variant-leakage", bad)
    conf = load(SHIFT)["outputs"]["synthetic_shift"]["label_free"]["conformal"]
    assert conf["label"] == "convention"
    st = load(C21)["outputs"]["situation_testing"]
    assert st["label_parameters"] == "convention"
    bad = load(C21)
    bad["outputs"]["situation_testing"]["label_parameters"] = "regulatory"
    assert not valid(REF, bad)


def test_m10_the_perturbation_tolerance_basis_says_two_and_a_half_standard_errors() -> None:
    basis = V.NAMED["perturbation_tolerance"][2]
    assert "2.5 standard errors" in basis and "three" not in basis
    assert "2.5 standard errors" in json.dumps(load(SHOCK)["outputs"]["parameters"])


def test_m11_the_api_history_row_is_a_major_step() -> None:
    row = next(ln for ln in ROWS.read_text(encoding="utf-8").splitlines() if ln.startswith("| api |"))
    assert row.rstrip().endswith("| major |")


def test_m13_each_label_const_is_pinned_on_its_own() -> None:
    doc = load(C21)
    for lang, other in (("en", "es"), ("es", "en")):
        bad = copy.deepcopy(doc)
        bad["outputs"]["legal"]["label"][lang] = "legal claim"
        assert bad["outputs"]["legal"]["label"][other] == doc["outputs"]["legal"]["label"][other]
        assert not valid(REF, bad), f"the {lang} const alone"
    models = load(C21_MODELS)
    bad = copy.deepcopy(models)
    bad["fit"]["legal"]["label"]["en"] = "legal claim"
    assert not valid("c21/models", bad)
    bad = copy.deepcopy(models)
    bad["fit"]["legal"]["label"]["es"] = "x"
    assert not valid("c21/models", bad)


def test_m13_both_c21_schemas_name_the_hmda_fields_from_the_addendum_only() -> None:
    allowed = set(V.HMDA_FIELDS)
    for ref in (REF, "c21/models"):
        schema = cs.load_json(SCHEMAS / f"{ref}.schema.json")
        enums = [d["enum"] for name, d in schema["$defs"].items() if name in ("c21Hmda", "c21Control") and "enum" in d]
        assert enums and all(set(e) <= allowed for e in enums), ref
        if ref == "c21/models":
            assert set(schema["$defs"]["c21Hmda"]["enum"]) == allowed
    models = load(C21_MODELS)
    models["fit"]["fields"][0]["name"] = "race"
    assert not valid("c21/models", models), "a name outside the addendum is refused"


def test_m14_the_shock_drift_block_carries_per_variable_rows_with_the_chi_square_p_value() -> None:
    doc = load(SHOCK)
    d = doc["outputs"]["shipped"]["rows"][0]["drift"]
    assert d["variables"][0].keys() >= {"name", "psi", "csi", "chi2_p_value"}
    bad = copy.deepcopy(doc)
    del bad["outputs"]["shipped"]["rows"][0]["drift"]["variables"]
    assert not valid("c20/variant-shock", bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["shipped"]["rows"][0]["drift"]["variables"] = []
    assert not valid("c20/variant-shock", bad)
    shift = load(SHIFT)
    var = shift["outputs"]["real_drift"]["pairs"][0]["variables"][0]
    assert "chi2_p_value" in var


def test_the_fixes_files_have_no_em_dash_and_no_emoji() -> None:
    for f in sorted(Path(__file__).parent.glob("*.py")) + [ROWS]:
        text = f.read_text(encoding="utf-8")
        assert chr(0x2014) not in text and chr(0x2015) not in text, f
        assert not any(0x1F000 <= ord(ch) <= 0x1FAFF or ord(ch) == 0xFE0F for ch in text), f
