"""U11-S fix round: the plants the Opus review (wip/contraste/review-u11-s-2026-10-18.md, D3) found ACCEPTED, and the failing cases of
its findings M1 to M5 and m1 to m8, each planted and refused.

A plant is the committed fixture with one defect and every number derived from it recomputed (``rebuild``, ``bf.lcr_block``), so the
only wrong thing is the plant. A plant is judged by the schema (``errs``) or by the producer checker (``semantics``) and the test names
the message the refusal must carry, so a plant refused for another reason does not pass. Run before the fix, these tests fail because the
contract accepts the plant (red); after it they pass.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

import build_fixtures as bf
import contract_schemas as cs
import semantics as sm
from test_u11_contracts import (API, FIXTURES, ROOT, SC, RV, MD, PATH_KEYS, SCENARIO_KEYS, errs, load, out, ref_of)

sys.path.insert(0, str(ROOT / "data-pipeline"))


def messages(doc: dict) -> str:
    return " | ".join(sm.check_document(doc))


def refused_by_checker(key: str, bad: dict, fragment: str) -> None:
    assert errs(ref_of(key), bad) == [], "the plant must be schema-valid so that the checker is what refuses it"
    found = messages(bad)
    assert fragment in found, f"{key}: the checker did not refuse the plant with {fragment!r}; it said: {found or 'nothing (accepted)'}"


def refused_by_schema(key: str, bad: dict) -> None:
    assert errs(ref_of(key), bad) != [], f"{key}: the schema accepted the plant"


def rebuild(doc: dict) -> dict:
    """Recompute every number derived from the CBC classes, the segments' daily rates and the ladder flows of a path variant."""
    o = doc["outputs"]
    v = o["variant"]["id"]
    for c in o["cbc"]["classes"]:
        c["liquidity_value"] = bf.r6((c["value_used"] - c["encumbered"]) * (1 - c["haircut"]["value"]))
    o["cbc"]["total_liquidity_value"] = bf.r6(sum(c["liquidity_value"] for c in o["cbc"]["classes"]))
    o["cbc"]["pledged"]["amount"] = bf.r6(sum(c["encumbered"] for c in o["cbc"]["classes"]))
    if o["htm"] is not None:
        h = o["htm"]
        h["cbc_with_loss"] = o["cbc"]["total_liquidity_value"]
        h["cbc_removed"] = bf.r6(h["cbc_without_loss"] - h["cbc_with_loss"])
    lad = o["path"]["ladder"]
    n = len(lad["nlp"])
    for s in lad["segments"]:
        if s["mechanism"] == "open-maturity-compounding":
            cum, prod = [], 1.0
            for q in s["daily_rates"]:
                prod *= 1.0 - q
                cum.append(1.0 - prod)
            s["cumulative_outflow_share"] = cum
            s["outflows"] = [bf.r6(s["opening_balance"] * (cum[d] - (cum[d - 1] if d else 0.0))) for d in range(n)]
    pts = [(p["day"], p["cumulative_share"]) for p in o["conventions"]["monetisation_schedule"]["points"]]
    classes = {c["class_id"]: c for c in o["cbc"]["classes"]}
    lad["cbc_stack"] = [{"class_id": c["class_id"], "liquidity_value": [bf.r6(classes[c["class_id"]]["liquidity_value"] * bf.share_at(d + 1, pts))
                                                                       for d in range(n)]} for c in lad["cbc_stack"]]
    lad["total_outflows"] = [bf.r6(sum(s["outflows"][d] for s in lad["segments"]) + sum(f["amounts"][d] for f in lad["other_outflows"]))
                             for d in range(n)]
    lad["total_inflows"] = [bf.r6(sum(f["amounts"][d] for f in lad["inflows"])) for d in range(n)]
    lad["cbc_total"] = [bf.r6(sum(c["liquidity_value"][d] for c in lad["cbc_stack"])) for d in range(n)]
    cum_net, run = [], 0.0
    for d in range(n):
        run += lad["total_outflows"][d] - lad["total_inflows"][d]
        cum_net.append(bf.r6(run))
    lad["cumulative_net_outflow"] = cum_net
    lad["nlp"] = [bf.r6(lad["cbc_total"][d] - cum_net[d]) for d in range(n)]
    o["path"] = bf.path_block(v, lad)
    doc["impact"]["survival_days"] = bf.impact_survival(o["path"]["survival"], n)
    o["scoring"] = bf.scoring_block(v, lad["segments"], None)
    return doc


def open_segments(doc: dict) -> list[dict]:
    return [s for s in doc["outputs"]["path"]["ladder"]["segments"] if s["mechanism"] == "open-maturity-compounding"]


def set_rate(seg: dict, q: float, parameter_too: bool = False) -> None:
    seg["daily_rates"] = [q] * len(seg["daily_rates"])
    if parameter_too:
        seg["parameters"][0]["value"] = q


def with_lcr(lcr: dict) -> dict:
    doc = load("lcr-standard")
    doc["outputs"]["lcr"] = lcr
    doc["impact"]["lcr"]["value"] = lcr["ratio"]
    doc["outputs"]["scoring"] = bf.scoring_block("lcr-standard", bf.lcr_scoring_segments(lcr), lcr)
    return doc


def refresh_lcr_totals(doc: dict) -> dict:
    lcr = doc["outputs"]["lcr"]
    for name, total in (("outflows", "total_outflows"), ("inflows", "total_inflows")):
        for r in lcr[name]:
            r["amount"] = bf.r6(r["balance"] * r["rate"])
        lcr[total] = bf.r6(sum(r["amount"] for r in lcr[name]))
    lcr["inflows_counted"] = bf.r6(min(lcr["total_inflows"], 0.75 * lcr["total_outflows"]))
    lcr["net_outflows"] = bf.r6(lcr["total_outflows"] - lcr["inflows_counted"])
    lcr["ratio"] = bf.r10(lcr["hqla"]["hqla"] / lcr["net_outflows"])
    doc["impact"]["lcr"]["value"] = lcr["ratio"]
    return doc


def set_everywhere(doc: dict, mutate: Callable[[dict], None]) -> None:
    """Apply a change to the conventions block of a document (the named parameters)."""
    mutate(doc["outputs"]["conventions"])


# --- the rebuild helper is the identity on the committed fixtures --------------------------------------------------------------


@pytest.mark.parametrize("key", PATH_KEYS)
def test_the_rebuild_of_an_unchanged_path_fixture_is_the_fixture(key: str) -> None:
    doc = load(key)
    assert rebuild(copy.deepcopy(doc)) == doc


# --- M1: the run-off rates are tied to the LiST table, to the parameter set and to the calibrated rate ----------------------------


def test_m1_a_non_operational_nfc_segment_run_at_a_rate_that_is_not_the_list_table_3_3_rate_is_refused() -> None:
    bad = load("list-adverse")
    seg = next(s for s in open_segments(bad) if s["list_class"] == "non-operational-non-financial-corporates")
    set_rate(seg, 0.001, parameter_too=True)
    rebuild(bad)
    refused_by_checker("list-adverse", bad, "LiST Table 3.3")


def test_m1_the_extreme_set_is_tied_to_its_own_column() -> None:
    bad = load("list-extreme")
    seg = next(s for s in open_segments(bad) if s["list_class"] == "other-retail")
    set_rate(seg, 0.00373218, parameter_too=True)   # the Adverse rate in the Extreme document
    rebuild(bad)
    refused_by_checker("list-extreme", bad, "LiST Table 3.3")


def test_m1_segment_parameters_that_differ_from_the_daily_rates_are_refused() -> None:
    bad = load("list-adverse")
    for seg in open_segments(bad):
        seg["parameters"][0]["value"] = 0.5
    refused_by_checker("list-adverse", bad, "parameter")


def test_m1_the_fast_run_rate_is_the_fitted_rate_of_the_models_document() -> None:
    models = load("models")
    fast = load("fast-run")
    assert sm.check_cross_document([fast, models, load("list-adverse"), load("reverse")]) == []
    bad = load("fast-run")
    seg = next(s for s in open_segments(bad) if s["parameters"][0]["source_kind"] == "calibrated-pre-2023")
    set_rate(seg, 0.05, parameter_too=True)
    rebuild(bad)
    assert messages(bad) == "" or "fitted_daily_rate" not in messages(bad)   # a single document cannot know the fitted rate
    found = sm.check_cross_document([bad, models])
    assert any("fitted_daily_rate" in m for m in found), found


def test_m1_a_models_list_table_that_a_scenario_does_not_follow_is_refused_across_documents() -> None:
    models = load("models")
    adverse = load("list-adverse")
    models["fit"]["list_parameters"]["open_maturity_daily"][6]["adverse"] = 0.007   # the schema pins it; the cross check names it too
    found = sm.check_cross_document([adverse, models])
    assert any("LiST" in m for m in found), found


# --- M2: the LCR rows are tied to the Basel table ----------------------------------------------------------------------------------


def test_m2_every_lcr_outflow_rate_at_0_01_is_refused() -> None:
    refused_by_checker("lcr-standard", with_lcr(bf.lcr_block(rate_override=0.01)), "table rate")


def test_m2_an_lcr_category_that_is_not_a_table_key_is_refused_by_the_schema() -> None:
    for name in ("outflows", "inflows"):
        bad = load("lcr-standard")
        bad["outputs"]["lcr"][name][0]["category"] = "anything"
        refused_by_schema("lcr-standard", bad)


def test_m2_an_inflow_category_in_the_outflow_rows_and_the_reverse_is_refused_by_the_schema() -> None:
    bad = load("lcr-standard")
    bad["outputs"]["lcr"]["outflows"][0]["category"] = "retail_and_nonfinancial_wholesale"
    refused_by_schema("lcr-standard", bad)
    worse = load("lcr-standard")
    worse["outputs"]["lcr"]["inflows"][0]["category"] = "retail_less_stable"
    refused_by_schema("lcr-standard", worse)


def test_m2_a_row_that_carries_another_rate_than_the_table_is_refused_in_the_inflows_too() -> None:
    bad = load("lcr-standard")
    bad["outputs"]["lcr"]["inflows"][1]["rate"] = 0.25
    refresh_lcr_totals(bad)
    refused_by_checker("lcr-standard", bad, "table rate")


def test_m2_a_trade_finance_row_is_a_caller_supplied_rate_within_zero_and_five_percent() -> None:
    def with_trade_finance(rate: float) -> dict:
        doc = load("lcr-standard")
        doc["outputs"]["lcr"]["outflows"].append({"category": "trade_finance", "balance": 1_000_000.0, "rate": rate, "amount": 0.0,
                                                  "reference": "LCR99: trade finance contingent outflows 0 to 5 percent at national discretion"})
        return refresh_lcr_totals(doc)

    ok = with_trade_finance(0.03)
    assert "trade finance" not in messages(ok) and errs(SC, ok) == []
    refused_by_checker("lcr-standard", with_trade_finance(0.5), "trade finance")


def test_m2_a_mapping_sensitivity_ratio_that_cannot_be_recomputed_is_refused() -> None:
    bad = load("lcr-standard")
    bad["outputs"]["lcr"]["mapping_sensitivity"][1]["ratio"] = 99.0
    refused_by_checker("lcr-standard", bad, "mapping sensitivity")


def test_m2_the_mapping_sensitivity_rows_carry_what_their_ratio_is_recomputed_from() -> None:
    lcr = out("lcr-standard")["lcr"]
    central = next(r for r in lcr["mapping_sensitivity"] if r["mapping_id"] == "central")
    assert central["ratio"] == lcr["ratio"] and central["total_outflows"] == lcr["total_outflows"]
    for r in lcr["mapping_sensitivity"]:
        assert {"uninsured_outflow", "total_outflows", "inflows_counted", "net_outflows", "ratio"} <= set(r)
        assert r["ratio"] == pytest.approx(lcr["hqla"]["hqla"] / r["net_outflows"], rel=1e-9)
    bad = load("lcr-standard")
    bad["outputs"]["lcr"]["mapping_sensitivity"][2]["net_outflows"] *= 2
    refused_by_checker("lcr-standard", bad, "mapping sensitivity")


# --- M3: the CBC classes follow their framework rows and the valuation basis -----------------------------------------------------


def _row(doc: dict, class_id: str) -> dict:
    return next(r for r in doc["outputs"]["conventions"]["cbc_securities_mapping"]["rows"] if r["class_id"] == class_id)


def _class(doc: dict, class_id: str) -> dict:
    return next(c for c in doc["outputs"]["cbc"]["classes"] if c["class_id"] == class_id)


def test_m3_a_framework_row_whose_haircut_is_not_one_minus_its_margin_is_refused() -> None:
    bad = load("list-adverse")
    row = _row(bad, "treasury")
    assert row["margin"] == 0.98
    row.update(haircut=0.5, haircut_low=0.45, haircut_high=0.55)
    _class(bad, "treasury")["haircut"]["value"] = 0.5
    rebuild(bad)
    refused_by_checker("list-adverse", bad, "1 - margin")


def test_m3_an_inverted_haircut_band_is_refused() -> None:
    bad = load("list-adverse")
    _row(bad, "treasury").update(haircut_low=0.3, haircut_high=0.1)
    refused_by_checker("list-adverse", bad, "band")


def test_m3_a_haircut_outside_its_band_is_refused() -> None:
    bad = load("list-adverse")
    _row(bad, "treasury").update(haircut_low=0.1, haircut_high=0.2)
    refused_by_checker("list-adverse", bad, "band")


def test_m3_a_cbc_class_haircut_that_is_not_its_framework_row_is_refused() -> None:
    bad = load("list-adverse")
    _class(bad, "treasury")["haircut"]["value"] = 0.5
    rebuild(bad)
    refused_by_checker("list-adverse", bad, "framework row")


def test_m3_a_cbc_class_rule_that_is_not_its_framework_row_rule_is_refused() -> None:
    bad = load("list-adverse")
    _class(bad, "municipal")["haircut"]["rule"] = "fifty-percent-fallback"
    refused_by_checker("list-adverse", bad, "framework row")


def test_m3_the_htm_variant_cannot_publish_the_amortised_cbc() -> None:
    bad = load("htm-losses")
    assert bad["outputs"]["cbc"]["htm_valuation_basis"] == "fair-value"
    for c in bad["outputs"]["cbc"]["classes"]:
        if c["fair_value"] is not None:
            c["fair_value"] = c["carrying_value"]
            c["value_used"] = c["carrying_value"]
    rebuild(bad)
    refused_by_checker("htm-losses", bad, "fair value")


def test_m3_a_securities_class_without_a_fair_value_on_the_fair_value_basis_is_refused() -> None:
    bad = load("htm-losses")
    c = _class(bad, "treasury")
    c.update(fair_value=None, value_used=c["carrying_value"])
    rebuild(bad)
    refused_by_checker("htm-losses", bad, "fair value")


def test_m3_the_framework_rows_are_consistent_in_the_fixture() -> None:
    for r in out("list-adverse")["conventions"]["cbc_securities_mapping"]["rows"]:
        if r["margin"] is not None:
            assert r["rule"] == "central-bank-framework" and r["haircut"] == pytest.approx(1 - r["margin"], abs=1e-9)
        assert r["haircut_low"] <= r["haircut"] <= r["haircut_high"]


# --- M4: a survival day never exceeds its horizon; the reverse cap is recomputable -----------------------------------------------


def test_m4_a_time_block_survival_day_beyond_the_horizon_is_refused() -> None:
    bad = load("list-adverse")
    bad["outputs"]["time_block"][1]["survival"] = {"kind": "day", "day": 500, "horizon_days": 125}
    refused_by_checker("list-adverse", bad, "horizon")


def test_m4_a_time_block_horizon_that_is_not_the_variants_is_refused() -> None:
    bad = load("list-adverse")
    bad["outputs"]["time_block"][0]["survival"] = {"kind": "survives-horizon", "day": None, "horizon_days": 5}
    refused_by_checker("list-adverse", bad, "horizon")


def test_m4_a_reverse_base_survival_day_beyond_its_horizon_is_refused() -> None:
    bad = load("reverse")
    base = bad["outputs"]["bases"][0]
    base["base_survival"] = {"kind": "day", "day": 400, "horizon_days": 125}
    base["curve"][0]["survival"] = {"kind": "day", "day": 400, "horizon_days": 125}
    refused_by_checker("reverse", bad, "horizon")


def test_m4_reverse_curve_points_of_one_base_share_one_horizon_and_the_variants() -> None:
    bad = load("reverse")
    base = bad["outputs"]["bases"][0]
    base["curve"][1]["survival"] = {**base["curve"][1]["survival"], "horizon_days": 126}
    refused_by_checker("reverse", bad, "horizon")


def test_m4_a_max_multiplier_that_is_not_one_over_the_largest_rate_below_one_is_refused() -> None:
    bad = load("reverse")
    bad["outputs"]["bases"][0]["max_multiplier"] = 1000.0
    refused_by_checker("reverse", bad, "max_multiplier")


def test_m4_the_max_rate_below_one_is_carried_and_agrees_with_the_scenario_document() -> None:
    reverse = load("reverse")
    scenarios = {k: load(k) for k in ("list-adverse", "list-extreme", "fast-run")}
    for b in reverse["outputs"]["bases"]:
        q = b["max_rate_below_one"]
        assert 0 < q < 1 and b["max_multiplier"] == pytest.approx(1 / q, abs=5e-7)
        rates = [s["daily_rates"][0] for s in open_segments(scenarios[b["base_id"]]) if s["daily_rates"][0] < 1]
        assert q == pytest.approx(max(rates), abs=1e-12)
    bad = load("reverse")
    base = bad["outputs"]["bases"][0]
    base["max_rate_below_one"] = 0.02
    base["max_multiplier"] = round(1 / 0.02, 6)
    found = sm.check_cross_document([bad] + list(scenarios.values()))
    assert any("max_rate_below_one" in m for m in found), found


# --- M5: the views' quantities have fields ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", PATH_KEYS)
def test_m5_the_scenario_carries_the_uninsured_share_and_the_htm_loss_series(key: str) -> None:
    o = out(key)
    sens = o["sensitivities"]
    grid = o["conventions"]["uninsured_share_grid"]["values"]
    hgrid = o["conventions"]["htm_loss_multiple_grid"]["values"]
    assert [p["share"] for p in sens["uninsured_share"]] == grid
    assert [p["multiple"] for p in sens["htm_loss"]] == hgrid
    assert sens["uninsured_share_reason"] is None and sens["htm_loss_reason"] is None
    for p in sens["uninsured_share"]:
        assert p["survival"]["horizon_days"] == o["variant"]["horizon_days"]
    assert sm.check_document(load(key)) == []


def test_m5_the_lcr_variant_carries_the_series_as_null_with_their_reasons() -> None:
    sens = out("lcr-standard")["sensitivities"]
    assert sens["uninsured_share"] is None and sens["uninsured_share_reason"]["en"]
    assert sens["htm_loss"] is None and sens["htm_loss_reason"]["en"]
    bad = load("lcr-standard")
    bad["outputs"]["sensitivities"]["htm_loss"] = out("list-adverse")["sensitivities"]["htm_loss"]
    refused_by_schema("lcr-standard", bad)


def test_m5_a_series_that_is_not_ordered_as_its_grid_is_refused() -> None:
    bad = load("list-adverse")
    pts = bad["outputs"]["sensitivities"]["uninsured_share"]
    pts[0], pts[1] = pts[1], pts[0]
    refused_by_checker("list-adverse", bad, "grid")


def test_m5_a_survival_that_lengthens_with_the_uninsured_share_is_refused() -> None:
    bad = load("list-adverse")
    pts = bad["outputs"]["sensitivities"]["uninsured_share"]
    h = bad["outputs"]["variant"]["horizon_days"]
    pts[-1]["survival"] = {"kind": "survives-horizon", "day": None, "horizon_days": h}
    refused_by_checker("list-adverse", bad, "lengthens")


def test_m5_a_cbc_that_grows_with_the_htm_loss_is_refused() -> None:
    bad = load("list-adverse")
    bad["outputs"]["sensitivities"]["htm_loss"][-1]["cbc"] += 100_000_000.0
    refused_by_checker("list-adverse", bad, "CBC grows")


def test_m5_an_htm_loss_that_is_not_the_multiple_of_the_reported_loss_is_refused() -> None:
    bad = load("list-adverse")
    bad["outputs"]["sensitivities"]["htm_loss"][2]["unrealised_loss"] *= 2
    refused_by_checker("list-adverse", bad, "unrealised_loss")


def test_m5_the_models_carry_the_list_results_annex_as_constants() -> None:
    fit = load("models")["fit"]
    annex = fit["list_parameters"]["results_annex"]
    assert annex["n_banks"] == 103 and annex["median_survival_days"] == {"adverse": 176, "extreme": 122}
    assert annex["sources"]["n_banks_slide"] == 9 and annex["sources"]["median_slides"] == [15]
    assert "05" in annex["sources"]["dossier"] and "240" in annex["sources"]["dossier"]
    for mutate in (lambda a: a.update(n_banks=104), lambda a: a["median_survival_days"].update(adverse=177),
                   lambda a: a["median_survival_days"].update(extreme=121), lambda a: a["sources"].update(n_banks_slide=10)):
        bad = load("models")
        mutate(bad["fit"]["list_parameters"]["results_annex"])
        refused_by_schema("models", bad)
    gone = load("models")
    del gone["fit"]["list_parameters"]["results_annex"]
    refused_by_schema("models", gone)


# --- m1, m2: the generator truth and the goldens ----------------------------------------------------------------------------------


def test_m1_the_generator_truth_is_recomputed_from_its_configuration() -> None:
    bad = load("models")
    for t in bad["fit"]["generator"]["truth"]:
        t["true_outflow_rate"] = round(t["true_outflow_rate"] / 2, 10)
    refused_by_checker("models", bad, "transfer recursion")
    assert sm.check_document(load("models")) == []


def test_m1_the_transfer_recursion_reproduces_the_contract_golden() -> None:
    seg = {"calm_daily_hazard": 0.001, "stress_daily_hazard": 0.01, "p_enter_stress": 1.0, "p_exit_stress": 0.0}
    assert [round(sm.generator_truth(seg, n), 7) for n in (1, 2, 3)] == [0.001, 0.01099, 0.0208801]
    calm = {**seg, "p_enter_stress": 0.0}
    assert sm.generator_truth(calm, 5) == pytest.approx(1 - 0.999 ** 5, abs=1e-12)


def test_m2_the_list_goldens_are_an_ordered_array_with_a_label_per_id() -> None:
    goldens = load("models")["fit"]["list_goldens"]
    assert [(g["id"], g["label"]) for g in goldens] == [
        ("stable-retail-adverse", "dossier-05-line-237"), ("stable-retail-extreme", "recomputed"), ("other-retail-adverse", "recomputed"),
        ("non-operational-nfc-adverse-2-days", "recomputed"), ("committed-credit-facilities-adverse-63-days", "recomputed")]
    bad = load("models")
    for g in bad["fit"]["list_goldens"]:
        g["label"] = "dossier-05-line-237"
    refused_by_schema("models", bad)
    swapped = load("models")
    swapped["fit"]["list_goldens"].reverse()
    refused_by_schema("models", swapped)
    renamed = load("models")
    renamed["fit"]["list_goldens"][1]["id"] = "stable-retail-adverse"
    refused_by_schema("models", renamed)


# --- m3: the derivative add-on is a caller-supplied rate ----------------------------------------------------------------------------


def test_m3_the_nsfr_derivative_addon_is_a_caller_supplied_rate_within_five_and_twenty_percent() -> None:
    text = API.read_text(encoding="utf-8")
    assert "| derivative_liabilities_addon |" not in text
    assert re.search(r"derivative_liabilities_addon[^.]*within \[0\.05, 0\.20\]", text), "the add-on rate interval is not stated"
    assert "NSF30.8" in text


# --- m4: reverse repos are LiST inflows, not a CBC class ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", PATH_KEYS)
def test_m4_the_reverse_repo_is_a_hundred_percent_inflow_of_the_ladder_and_not_a_cbc_class(key: str) -> None:
    o = out(key)
    assert "reverse-repo" not in {c["class_id"] for c in o["cbc"]["classes"]}
    assert "reverse-repo" not in {c["class_id"] for c in o["cbc"]["classes"]} | {r["class_id"] for r in o["conventions"]["cbc_securities_mapping"]["rows"]}
    assert "reverse-repo" not in {c["class_id"] for c in o["path"]["ladder"]["cbc_stack"]}
    frepo = next(i for i in o["balance_sheet"]["items"] if i["source_field"] == "FREPO")
    flows = [f for f in o["path"]["ladder"]["inflows"] if f["kind"] == "inflow-secured-lending"]
    assert len(flows) == 1 and flows[0]["amounts"][0] == frepo["amount"] and sum(flows[0]["amounts"][1:]) == 0.0
    assert flows[0]["source_kind"] == "transcribed-list-2019"
    assert "100 percent" in flows[0]["source"] and "L1.2" in flows[0]["source"]


def test_m4_a_reverse_repo_class_in_the_cbc_is_refused_by_the_schema() -> None:
    bad = load("list-adverse")
    bad["outputs"]["cbc"]["classes"][1]["class_id"] = "reverse-repo"
    refused_by_schema("list-adverse", bad)


# --- m5: the family flag is 0 or 1 and the label says so --------------------------------------------------------------------------------


def test_m5_the_insured_flag_is_zero_or_one_and_its_label_names_the_encoding_and_refuses_a_boolean() -> None:
    from pipeline.io import contract as c

    f = c.FAMILIES["balance_sheet"].field("insured")
    assert f.kind == "flag"
    assert "1" in f.meaning["en"] and "0" in f.meaning["en"] and "boolean" in f.meaning["en"].lower()
    assert "1" in f.meaning["es"] and "0" in f.meaning["es"] and "booleano" in f.meaning["es"].lower()
    base = {"as_of": "2022-12-31", "item": "Insured deposits", "currency": "USD", "amount": -1.0e9, "repricing_bucket": "ON",
            "behavioural_class": "nmd_retail_transactional"}
    for value in (0, 1):
        rep = c.validate("balance_sheet", [{**base, "insured": value}])
        assert len(rep.accepted) == 1 and not rep.rejected
    for value in (True, False):
        rep = c.validate("balance_sheet", [{**base, "insured": value}])
        assert len(rep.rejected) == 1 and not rep.accepted, f"{value!r} must be mapped to 0 or 1 by the producer"


# --- m6: one vocabulary for the LCR categories ---------------------------------------------------------------------------------------


def test_m6_the_mapping_the_lcr_rows_and_the_sensitivity_use_the_engine_keys() -> None:
    o = out("lcr-standard")
    rates = {m.group(1) for m in re.finditer(r"^\| ([a-z0-9_]+) \| [0-9.]+ \|", API.read_text(encoding="utf-8"), flags=re.M)}
    m = o["conventions"]["deposit_category_mapping"]
    cats = {r["lcr_category"] for r in m["rows"] + m["sensitivity_band"]} | {r["lcr_category"] for r in o["lcr"]["mapping_sensitivity"]}
    cats |= {r["category"] for r in o["lcr"]["outflows"] + o["lcr"]["inflows"]}
    assert all("-" not in c for c in cats), sorted(cats)
    assert cats <= rates | {"trade_finance"}, sorted(cats - rates)
    bad = load("lcr-standard")
    bad["outputs"]["conventions"]["deposit_category_mapping"]["rows"][1]["lcr_category"] = "non-financial-corporate"
    refused_by_schema("lcr-standard", bad)


# --- m7: the LCR variant's phase is its own value ------------------------------------------------------------------------------------


def test_m7_the_lcr_variant_phase_is_lcr_30_day_sourced_to_lcr20_2() -> None:
    o = out("lcr-standard")
    row = next(r for r in o["conventions"]["variant_scenarios"]["rows"] if r["variant"] == "lcr-standard")
    assert row["phase"] == "lcr-30-day" and o["variant"]["phase"] == "lcr-30-day"
    assert "LCR20.2" in o["conventions"]["variant_scenarios"]["basis"]["en"]
    assert {out(k)["variant"]["phase"] for k in PATH_KEYS} <= {"acute", "protracted"}
    bad = load("lcr-standard")
    bad["outputs"]["variant"]["phase"] = "protracted"
    bad["outputs"]["conventions"]["variant_scenarios"]["rows"][0]["phase"] = "protracted"
    refused_by_schema("lcr-standard", bad)


# --- m8: the NLP identity holds to the named tolerance only ---------------------------------------------------------------------------


def test_m8_an_nlp_off_by_half_a_thousand_of_a_thousand_dollars_is_refused() -> None:
    bad = load("list-adverse")
    assert bad["outputs"]["conventions"]["nlp_identity_tolerance"]["value"] == 1e-6
    bad["outputs"]["path"]["ladder"]["nlp"][0] += 5e-4
    refused_by_checker("list-adverse", bad, "breaks NLP = CBC")
