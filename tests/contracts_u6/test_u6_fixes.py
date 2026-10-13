"""U6-S fixes: one plant or test per finding of the Opus review of U6-S (wip/contraste/review-u6-s-2026-10-13.md).

A plant is a deep copy of a committed fixture with one defect; the schema must refuse it. What a JSON Schema cannot express
(arithmetic across two objects, the identity of a copy of a number elsewhere in the document) is checked by the producer-side
helpers ``problems_*`` below, and the plants of those defects must make the helper report a problem; the fixtures must make it
report none.
"""
from __future__ import annotations

import copy
from datetime import date
from typing import Callable

import pytest

import contract_schemas as cs
from test_u6_contracts import C03, C03M, C08, C08M, C09, C09M, API, ROOT, get, load, out

SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
API_TEXT = API.read_text(encoding="utf-8")


def mutate(ref: str, fn: Callable[[dict], None]) -> dict:
    doc = copy.deepcopy(load(ref))
    fn(doc)
    return doc


def refused(ref: str, fn: Callable[[dict], None]) -> bool:
    return cs.errors(ref, mutate(ref, fn)) != []


# --- producer-side helpers (what the schema cannot express) -----------------------------------------------------------


def problems_c03(doc: dict) -> list[str]:
    """The D1 rule and the 5-year-mark identities of a C03 variant document."""
    o = doc["outputs"]
    found: list[str] = []
    as_of = date.fromisoformat(o["data_status"]["files_as_of"])
    t, c = o["training"], o["cohort"]
    if not t["last_fy"] <= c["first_fy"] - 6:
        found.append("training window overlaps the test cohort (D1: last_fy <= cohort.first_fy - 6)")
    if not date.fromisoformat(t["cutoff_date"]) <= date(c["first_fy"] - 1, 9, 30):
        found.append("training cutoff after the first approval of the test cohort")
    rows = {r["fiscal_year"]: r for r in o["vintage_summary"]["rows"]}
    for vc in o["vintage_curves"]:
        row = rows[vc["fiscal_year"]]
        if row["mark_observed"] != (date.fromisoformat(row["five_year_mark_date"]) <= as_of):
            found.append(f"FY{vc['fiscal_year']}: mark_observed disagrees with five_year_mark_date against files_as_of")
        if row["five_year_mark_date"] != f"{vc['fiscal_year'] + 5}-09-30":
            found.append(f"FY{vc['fiscal_year']}: five_year_mark_date is not the end of the fiscal year plus 5 years")
        for m, x in zip(vc["months"], vc["observed_cumulative_pd"]):
            if (x is not None) != (m <= vc["observed_until_month"]):
                found.append(f"FY{vc['fiscal_year']}: observed PD at month {m} against observed_until_month")
        if row["mark_observed"] != (vc["observed_until_month"] >= 60):
            found.append(f"FY{vc['fiscal_year']}: mark_observed disagrees with observed_until_month")
    return found


def problems_c03_models(doc: dict) -> list[str]:
    found: list[str] = []
    for w in doc["fit"]["cohort_windows"]:
        t = w["training"]
        if not t["last_fy"] <= w["first_fy"] - 6:
            found.append(f"{w['id']}: training window overlaps the test cohort")
        if not date.fromisoformat(t["cutoff_date"]) <= date(w["first_fy"] - 1, 9, 30):
            found.append(f"{w['id']}: training cutoff after the first approval of the cohort")
    return found


def problems_c08(doc: dict) -> list[str]:
    o = doc["outputs"]
    cutoff_year = int(o["training"]["cutoff_date"][:4])
    return [] if cutoff_year < o["cohort"]["first_year"] else ["training cutoff not before the first default year of the cohort"]


def problems_c09(doc: dict) -> list[str]:
    o = doc["outputs"]
    truth = o["generator"]["true_ccf"]["value"]
    return [f"row {r['design']}/{r['treatment']}: truth differs from generator.true_ccf"
            for r in o["ccf_by_design"]["rows"] if r["truth"]["value"] != truth]


# --- the fixtures are clean ----------------------------------------------------------------------------------------


def test_the_fixtures_have_no_producer_side_problem() -> None:
    assert problems_c03(load(C03)) == []
    assert problems_c03_models(load(C03M)) == []
    assert problems_c08(load(C08)) == []
    assert problems_c09(load(C09)) == []


# --- B1: the C03 5-year mark ------------------------------------------------------------------------------------------


def unobserved_row(doc: dict) -> dict:
    return next(r for r in doc["outputs"]["vintage_summary"]["rows"] if r["fiscal_year"] == 2019)


def test_b1_a_five_year_pd_reported_before_the_mark_is_refused() -> None:
    def plant(d: dict) -> None:
        r = unobserved_row(d)
        r["observed_5y_pd"], r["gap"], r["reason"] = 0.05, -0.033, None
    assert refused(C03, plant)

    def plant_marked(d: dict) -> None:
        plant(d)
        unobserved_row(d)["mark_observed"] = True
    # claiming the mark is observed passes the schema; the producer identity against files_as_of catches it
    assert not refused(C03, plant_marked)
    assert problems_c03(mutate(C03, plant_marked)) != []


def test_b1_an_unobserved_five_year_pd_needs_its_reason() -> None:
    assert refused(C03, lambda d: unobserved_row(d).update({"reason": None}))
    assert refused(C03, lambda d: unobserved_row(d).update({"reason": ""}))
    assert refused(C03, lambda d: unobserved_row(d).update({"gap": 0.01}))


def test_b1_an_observed_mark_carries_its_value_and_gap_and_no_reason() -> None:
    def row(d: dict) -> dict:
        return next(r for r in d["outputs"]["vintage_summary"]["rows"] if r["fiscal_year"] == 2018)

    assert refused(C03, lambda d: row(d).update({"observed_5y_pd": None}))
    assert refused(C03, lambda d: row(d).update({"gap": None}))
    assert refused(C03, lambda d: row(d).update({"reason": "x"}))
    assert refused(C03, lambda d: row(d).pop("five_year_mark_date"))
    assert refused(C03, lambda d: row(d).pop("mark_observed"))


@pytest.mark.parametrize("ref", [C03, C03M])
def test_b1_the_target_horizon_and_reading_month_are_sixty(ref: str) -> None:
    root = "outputs" if ref == C03 else "fit"
    for key in ("horizon_months", "observed_at_months"):
        for bad in (12, 36, 59, 61):
            assert refused(ref, lambda d, k=key, b=bad: d[root]["target"].update({k: b})), (key, bad)


def test_b1_a_curve_ends_where_the_mark_is_reached_and_says_why_otherwise() -> None:
    def curve(d: dict) -> dict:
        return next(v for v in d["outputs"]["vintage_curves"] if v["fiscal_year"] == 2019)

    def full(d: dict) -> dict:
        return next(v for v in d["outputs"]["vintage_curves"] if v["fiscal_year"] == 2018)

    assert refused(C03, lambda d: curve(d).update({"reason": None}))
    assert refused(C03, lambda d: full(d).update({"reason": "x"}))
    assert refused(C03, lambda d: curve(d).update({"observed_cumulative_pd": [0.009, 0.026, 0.047, 0.066, 0.083]}))


def test_b1_an_observed_value_beyond_the_observed_months_is_caught_by_the_producer_check() -> None:
    def plant(d: dict) -> None:
        v = next(v for v in d["outputs"]["vintage_curves"] if v["fiscal_year"] == 2020)
        v["observed_cumulative_pd"][3] = 0.05  # month 48, beyond observed_until_month 45
    assert problems_c03(mutate(C03, plant)) != []


def test_b1_a_training_window_overlapping_the_test_cohort_is_caught() -> None:
    assert problems_c03(mutate(C03, lambda d: d["outputs"]["training"].update({"last_fy": 2020}))) != []
    assert problems_c03(mutate(C03, lambda d: d["outputs"]["training"].update({"last_fy": 2013}))) != []
    assert problems_c03(mutate(C03, lambda d: d["outputs"]["training"].update({"cutoff_date": "2019-09-30"}))) != []
    assert problems_c03(mutate(C03, lambda d: d["outputs"]["training"].update({"last_fy": 2012}))) == []


def test_b1_every_cohort_window_of_the_models_carries_its_own_training_window() -> None:
    doc = load(C03M)
    assert "training" not in doc["fit"]
    windows = doc["fit"]["cohort_windows"]
    assert [w["id"] for w in windows] == ["fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"]
    assert [w["training"]["crisis_included"] for w in windows] == [False, False, True, True, True]
    assert refused(C03M, lambda d: d["fit"]["cohort_windows"][0].pop("training"))
    assert problems_c03_models(mutate(C03M, lambda d: d["fit"]["cohort_windows"][0]["training"].update({"last_fy": 2006}))) != []


def test_b1_the_training_text_states_the_d1_rule() -> None:
    for ref in ("c03/variant-vintage-cohort", "c03/models"):
        text = (SCHEMAS / f"{ref}.schema.json").read_text(encoding="utf-8")
        assert "precedes the first fiscal year of the test cohort" not in text
        assert "5-year" in text and "mark" in text
    text = (SCHEMAS / "c03" / "variant-vintage-cohort.schema.json").read_text(encoding="utf-8")
    assert "first_fy - 6" in text


# --- B2: the C08 proxy follows decision D2 ------------------------------------------------------------------------------


@pytest.mark.parametrize("ref", [C08, C08M])
def test_b2_the_proxy_is_gross_charge_off_over_gross_approval_biased_low(ref: str) -> None:
    root = "outputs" if ref == C08 else "fit"
    proxy = load(ref)[root]["lgd_proxy"]
    assert proxy["exposure_field"] == "GrossApproval"
    assert proxy["source_field"] == "GrossChargeOffAmount"
    assert proxy["bias_direction"] == "downward"
    assert "GrossApproval" in proxy["formula"]
    assert "exposure_at_charge_off" not in proxy["formula"]
    for plant in (lambda p: p.update({"exposure_field": ""}), lambda p: p.update({"exposure_field": "DisbursementAmount"}),
                  lambda p: p.update({"source_field": "ChargeOffAmount"}), lambda p: p.update({"source_field": ""}),
                  lambda p: p.update({"formula": ""}), lambda p: p.update({"bias_direction": "upward"}),
                  lambda p: p.update({"bias_direction": "unknown"})):
        assert refused(ref, lambda d, f=plant: f(d[root]["lgd_proxy"]))


def test_b2_the_bias_statement_names_both_effects() -> None:
    text = " ".join(out(C08)["lgd_proxy"]["bias_statement"].values()).lower()
    assert "approv" in text or "aprob" in text
    assert "recover" in text or "recuper" in text


def test_b2_the_exposure_total_is_the_gross_approval_total() -> None:
    e = out(C08)["exposure"]
    assert "gross_approval_total" in e and "exposure_at_charge_off_total" not in e
    assert refused(C08, lambda d: d["outputs"]["exposure"].pop("gross_approval_total"))


def test_b2_no_c08_text_names_the_exposure_at_charge_off_or_an_upward_bias() -> None:
    texts = [API_TEXT[API_TEXT.index("The C08 document describes a **proxy**"):][:1200]]
    for name in ("c08/variant-default-cohort.schema.json", "c08/models.schema.json"):
        texts.append((SCHEMAS / name).read_text(encoding="utf-8"))
    for name in ("c08/variant-default-cohort-fixture.json", "c08/models-fixture.json"):
        texts.append((ROOT / "docs" / "contracts" / "fixtures" / name).read_text(encoding="utf-8"))
    for t in texts:
        assert "exposure at charge-off" not in t.lower()
        assert "exposure_at_charge_off" not in t
        assert "upward bias" not in t.lower() and "sesgo al alza" not in t.lower()


# --- B3: a not_evaluated row carries no number ---------------------------------------------------------------------------


@pytest.mark.parametrize("ref", [C03, C08, C09])
def test_b3_every_not_evaluated_fixture_row_has_null_numbers_and_a_reason(ref: str) -> None:
    rows = [r for r in load(ref)["tests"] if r["light"] == "not_evaluated"]
    assert rows
    for r in rows:
        assert r["statistic"] is None and r["p_value"] is None and r["metric"] is None
        assert r["notes"].strip()


@pytest.mark.parametrize("ref", [C03, C08, C09])
@pytest.mark.parametrize("field,value", [("statistic", 3.46), ("p_value", 0.07), ("metric", 0.0), ("statistic", 0.0)])
def test_b3_a_not_evaluated_row_with_a_number_is_refused(ref: str, field: str, value: float) -> None:
    def plant(d: dict) -> None:
        row = next(r for r in d["tests"] if r["light"] == "not_evaluated")
        row[field] = value
    assert refused(ref, plant)


@pytest.mark.parametrize("ref", [C03, C08, C09])
def test_b3_a_not_evaluated_row_without_its_reason_is_refused(ref: str) -> None:
    def plant(d: dict) -> None:
        next(r for r in d["tests"] if r["light"] == "not_evaluated")["notes"] = ""
    assert refused(ref, plant)


@pytest.mark.parametrize("ref", [C03, C08, C09])
def test_b3_an_evaluated_row_keeps_its_numbers(ref: str) -> None:
    def plant(d: dict) -> None:
        row = next(r for r in d["tests"])
        row.update({"light": "green", "statistic": 1.5, "p_value": 0.2, "metric": 0.1})
    assert not refused(ref, plant)


# --- M2: predictions are inside [0, 1] ------------------------------------------------------------------------------------

PREDICTION_PATHS = [
    ("realised_vs_predicted", 0, "predicted"), ("calibration_by_bucket", 0, "predicted"),
    ("endpoint_sensitivity", 0, "mean_predicted"), ("floors_bite", "rows", 0, "mean_before"),
    ("floors_bite", "rows", 0, "mean_after"),
]


@pytest.mark.parametrize("path", PREDICTION_PATHS)
@pytest.mark.parametrize("value,flag", [(1.2, "above-one"), (-0.1, "below-zero")])
def test_m2_a_prediction_outside_the_unit_interval_is_refused_even_flagged(path: tuple, value: float, flag: str) -> None:
    def plant(d: dict) -> None:
        site = get(d["outputs"], path[:-1])
        if isinstance(site, list):
            site = site[0]
        site[path[-1]] = {"value": value, "flag": flag}
    assert refused(C08, plant)


@pytest.mark.parametrize("path", PREDICTION_PATHS)
def test_m2_a_prediction_in_range_still_validates(path: tuple) -> None:
    def plant(d: dict) -> None:
        site = get(d["outputs"], path[:-1])
        if isinstance(site, list):
            site = site[0]
        site[path[-1]] = {"value": 0.5, "flag": "in-range"}
    assert not refused(C08, plant)


# --- m1 to m13 -------------------------------------------------------------------------------------------------------------


def test_m3_the_floor_uplift_is_never_negative() -> None:
    assert refused(C08, lambda d: d["outputs"]["floors_bite"]["rows"][0].update({"uplift": -0.05}))


@pytest.mark.parametrize("ref", [C08, C08M])
def test_m3_the_floor_cells_are_the_twelve_transcribed_cells(ref: str) -> None:
    if ref == C08M:
        assert refused(C08M, lambda d: d["fit"]["floors"]["cells"][0].update({"floor": 0.20}))
        assert refused(C08M, lambda d: d["fit"]["floors"]["cells"][0].update({"portfolio": "corporate", "collateral": "qrre"}))
        assert refused(C08M, lambda d: d["fit"]["floors"]["cells"][5].update({"floor": 0.06}))
    else:
        assert refused(C08, lambda d: d["outputs"]["floors_bite"]["rows"][0].update({"floor": 0.20}))
        assert refused(C08, lambda d: d["outputs"]["floors_bite"]["rows"][0].update({"floor_id": "corporate-qrre"}))


def test_m3_a_floor_cell_not_among_the_twelve_is_refused() -> None:
    def plant(d: dict) -> None:
        d["fit"]["floors"]["cells"][0].update({"id": "corporate-qrre", "collateral": "qrre", "floor": 0.5})
    assert refused(C08M, plant)


def test_m2_the_retail_floor_references_are_the_dossier_joint_citation() -> None:
    cells = load(C08M)["fit"]["floors"]["cells"]
    for c in cells:
        assert c["reference"] == ("CRE32.16" if c["portfolio"] == "corporate" else "CRE32.58 to CRE32.59"), c["id"]


def test_m4_the_endpoint_sensitivity_has_at_least_two_epsilons() -> None:
    assert refused(C08, lambda d: d["outputs"].update({"endpoint_sensitivity": []}))
    assert refused(C08, lambda d: d["outputs"].update({"endpoint_sensitivity": d["outputs"]["endpoint_sensitivity"][:1]}))


def test_m5_a_none_proxy_workout_has_no_discount_rate_and_is_not_applicable() -> None:
    assert refused(C08, lambda d: d["outputs"]["workout"].update({"discount_rate": 0.08}))
    assert refused(C08M, lambda d: d["fit"]["workout"].update({"discount_rate": 0.08}))
    assert refused(C08, lambda d: d["outputs"]["workout"]["incomplete_workouts"].update({"treatment": "excluded"}))

    def eba(d: dict) -> None:
        w = d["outputs"]["workout"]
        w.update({"discount_rate_convention": "eba-interbank-plus-5pp", "discount_rate": None})
    assert refused(C08, eba)

    def eba_ok(d: dict) -> None:
        w = d["outputs"]["workout"]
        w.update({"discount_rate_convention": "eba-interbank-plus-5pp", "discount_rate": 0.0825})
        w["incomplete_workouts"].update({"treatment": "excluded", "n_excluded": 3, "reason": None})
    assert not refused(C08, eba_ok)


def test_m6_the_decile_is_at_most_ten_and_the_rung_kind_is_an_enumeration() -> None:
    assert refused(C03, lambda d: d["outputs"]["calibration"]["rows"][0].update({"decile": 11}))
    assert refused(C03, lambda d: d["outputs"]["calibration"]["rows"][0].update({"decile": 0}))
    assert refused(C03M, lambda d: d["fit"]["ladder"][0].update({"kind": "magic"}))
    assert not refused(C03M, lambda d: d["fit"]["ladder"][0].update({"kind": "penalised-logit"}))


def test_m7_the_direct_ead_model_carries_its_clipped_counts() -> None:
    models = out(C09)["ead_models"]
    direct = next(m for m in models if m["kind"] == "direct-ead")
    assert isinstance(direct["n_clipped_below"], int) and isinstance(direct["n_clipped_above"], int)
    other = next(m for m in models if m["kind"] != "direct-ead")
    assert other["n_clipped_below"] is None and other["n_clipped_above"] is None
    idx = models.index(direct)
    assert refused(C09, lambda d: d["outputs"]["ead_models"][idx].update({"n_clipped_below": None}))
    assert refused(C09, lambda d: d["outputs"]["ead_models"][0].update({"n_clipped_below": 3}))
    assert refused(C09, lambda d: d["outputs"]["ead_models"][idx].pop("n_clipped_above"))
    assert refused(C09M, lambda d: d["fit"]["ead_models"][idx].pop("n_clipped_above"))


def test_m8_an_unclipped_utilisation_change_prediction_has_a_flag_and_may_be_negative() -> None:
    rows = out(C09)["ead_backtest"]["rows"]
    assert all(r["prediction_flag"] == "in-range" for r in rows)
    assert refused(C09, lambda d: d["outputs"]["ead_backtest"]["rows"][0].pop("prediction_flag"))
    # a negative sum with the in-range flag is refused; with the outside-range flag it is kept
    assert refused(C09, lambda d: d["outputs"]["ead_backtest"]["rows"][0].update({"predicted_ead": -5.0}))
    assert not refused(C09, lambda d: d["outputs"]["ead_backtest"]["rows"][0].update(
        {"predicted_ead": -5.0, "prediction_flag": "outside-range", "gap": -5.0 - rows[0]["realised_ead"],
         "relative_gap": (-5.0 - rows[0]["realised_ead"]) / rows[0]["realised_ead"]}))


def test_m12_a_treated_ccf_estimate_is_inside_the_unit_interval() -> None:
    idx = next(i for i, r in enumerate(out(C09)["ccf_by_design"]["rows"]) if r["treatment"] == "floor-cap")
    cens = next(i for i, r in enumerate(out(C09)["ccf_by_design"]["rows"]) if r["treatment"] == "none")
    assert refused(C09, lambda d: d["outputs"]["ccf_by_design"]["rows"][idx].update({"estimate": {"value": 1.2, "flag": "above-one"}}))
    assert refused(C09, lambda d: d["outputs"]["ccf_by_design"]["rows"][idx].update({"treatment": "censor", "estimate": {"value": -0.1, "flag": "below-zero"}}))
    # untreated estimates may still be flagged out of range
    assert not refused(C09, lambda d: d["outputs"]["ccf_by_design"]["rows"][cens].update({"estimate": {"value": 1.2, "flag": "above-one"}}))


def test_c09_a_row_truth_that_differs_from_the_generator_is_caught_by_the_producer_check() -> None:
    plant = mutate(C09, lambda d: d["outputs"]["ccf_by_design"]["rows"][0].update({"truth": {"value": 0.11, "flag": "in-range"}}))
    assert problems_c09(plant) != []


def test_c08_a_training_cutoff_inside_the_default_cohort_is_caught_by_the_producer_check() -> None:
    plant = mutate(C08, lambda d: d["outputs"]["training"].update({"cutoff_date": "2011-12-31"}))
    assert problems_c08(plant) != []


# --- the engine contract text -----------------------------------------------------------------------------------------------


def section(title: str) -> str:
    i = API_TEXT.index(title)
    j = API_TEXT.find("\n### ", i + 5)
    return API_TEXT[i: j if j > 0 else len(API_TEXT)]


def test_m1_the_workout_lgd_rate_invariant_is_conditional() -> None:
    s = section("### `riskvalidation.lgd_ead.workout.workout_lgd`")
    assert "nondecreasing in `costs`, `drawings` and `rate`" not in s
    assert "every net flow" in s and "nonnegative" in s
    assert "1.150000" in s  # the contract's own golden that refutes the unconditional claim


def test_m3_zero_spread_with_a_gap_is_red_not_not_evaluated() -> None:
    seg = section("### `riskvalidation.validation.lgd_ead.lgd_calibration_by_segment`")
    assert "`sd(d) = 0` with `mean(d) != 0` gives `red`" in seg
    assert "`statistic` null" in seg
    cov = section("### `riskvalidation.validation.lgd_ead.downturn_coverage`")
    assert "zero spread with a shortfall gives `red`" in cov
    bias = section("### `riskvalidation.validation.lgd_ead.ccf_estimator_bias`")
    assert "keeps its light for `R >= 1`" in bias
    over = section("### `riskvalidation.validation.lgd_ead.lgd_calibration_over_time`")
    assert 'extras["excluded"]' in over and "every period with at least one observation" in over


def test_m1_the_partially_secured_floor_formula_is_cited_not_denied() -> None:
    assert "blending formula is not transcribed" not in API_TEXT
    assert "CRE32.17" in API_TEXT
    assert "Floor = LGD_U,floor E_U" in API_TEXT


def test_m2_no_dossier_section_b2_and_the_retail_split_is_marked() -> None:
    assert "section B.2" not in API_TEXT and "A.5 and B.2" not in API_TEXT
    assert "section C" in API_TEXT
    assert "CRE32.58 to CRE32.59" in section("### `riskvalidation.lgd_ead.floors.lgd_floor`")
    assert "| retail | mortgage | 0.05 | CRE32.58 to CRE32.59 |" in API_TEXT


def test_m9_small_undrawn_ratio_is_never_aggregated() -> None:
    s = section("### `riskvalidation.lgd_ead.ccf.small_undrawn_rule`")
    assert "never aggregated" in s


def test_m10_the_ead_floor_uses_a_nonnegative_off_balance_amount() -> None:
    s = section("### `riskvalidation.lgd_ead.floors.ead_floor`")
    assert "max(limit - drawn, 0)" in s
    assert "overdrawn" in s


def test_m11_the_ead_backtest_defines_zero_and_empty_denominators() -> None:
    s = section("### `riskvalidation.validation.lgd_ead.ead_backtest_by_band`")
    assert "realised EAD of a band is 0" in s
    assert "every band is empty" in s


def test_m13_the_thresholds_travel_in_extras() -> None:
    assert 'extras["thresholds"]' in API_TEXT
    for fn in ("lgd_discrimination", "ead_backtest_by_band", "ccf_estimator_bias"):
        assert 'extras["thresholds"]' in section(f"### `riskvalidation.validation.lgd_ead.{fn}`")


def test_m8_predict_ead_flags_the_unclipped_prediction_with_the_document_field() -> None:
    s = section("### `riskvalidation.lgd_ead.ccf.predict_ead`")
    assert "prediction_flag" in s


def test_m7_fit_direct_ead_names_the_document_fields_of_the_clipped_counts() -> None:
    s = section("### `riskvalidation.lgd_ead.ccf.fit_direct_ead`")
    assert "n_clipped_below" in s and "ead_models" in s


def test_b2_the_engine_contract_names_gross_approval() -> None:
    assert "GrossApproval" in API_TEXT
    assert "biased low" in API_TEXT
