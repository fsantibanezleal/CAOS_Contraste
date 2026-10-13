"""U5-S review fixes (review of 2026-10-12, fixes 1 to 14): one plant per defect the review found.

Each test fails on the contracts as reviewed (commit 1962394) and passes after the fixes. They cover the engine
provisions API text (fixes 1 to 7, 9 and the lower-priority items), the C06 and C07 schemas and fixtures (fixes 8,
10 to 12 and the decision on Q1) and the catalog rows fragment (fix 13).
"""
from __future__ import annotations

import copy
import math
import re
import subprocess
import sys
from typing import Any

import pytest

import contract_schemas as cs
from test_u5_contracts import API, EXPECTED, ROOT, ROWS, SCHEMAS, api_sections, load

C06 = "c06/variant-reporting-date"
C07 = "c07/variant-three-regime"
C06M = "c06/models"
C07M = "c07/models"
RV = "riskvalidation.provisions."
VAL = "riskvalidation.validation.ifrs9."


def section(name: str) -> str:
    return api_sections()[name]


def schema(ref: str) -> dict:
    return cs.load_json(SCHEMAS / f"{ref}.schema.json")


def out(ref: str) -> dict:
    return load(ref)["outputs"]


def mutated(ref: str, fn) -> list[str]:
    doc = copy.deepcopy(load(ref))
    fn(doc)
    return cs.errors(ref, doc)


# --- fix 1: competing risks (F-E1) ------------------------------------------------------------------------------------


def test_competing_risks_is_its_own_record_and_forward_pd_is_the_default_only_probability() -> None:
    body = section(RV + "term_structure.competing_risks")
    assert "CompetingRisks" in body
    assert "returns a `TermStructure`" not in body and "-> TermStructure" not in body
    assert "(F_D(b) - F_D(a)) / S_all(a)" in body
    fwd = section(RV + "term_structure.forward_pd")
    assert "CompetingRisks" in fwd and "(F_D(b) - F_D(a)) / S_all(a)" in fwd
    # the contract's own golden: h_D = 0.01, h_P = 0.02, two periods of 3 months, default only over (0, 6]
    s_all, f_d, s_prev = [], [], 1.0
    cum = 0.0
    for _ in range(2):
        cum += s_prev * 0.01
        s_prev *= 1 - 0.01 - 0.02
        s_all.append(s_prev)
        f_d.append(cum)
    assert math.isclose(f_d[1], 0.0197, abs_tol=1e-12) and math.isclose(1 - s_all[1], 0.0591, abs_tol=1e-12)
    assert "0.0197" in body and "0.0591" in body


# --- fix 2: one tolerance basis (F-E2) ------------------------------------------------------------------------------


def test_one_tolerance_basis_is_defined_once_and_used_everywhere() -> None:
    text = API.read_text(encoding="utf-8")
    assert "portfolio amount" not in text
    assert "1e-6 * max(1, G)" in text and "total gross carrying amount" in text
    assert "1e-6 * max(1, |closing|)" not in text
    desc = schema(C06)["$defs"]["c06Reconciliation"]["description"]
    assert "max(1, G)" in desc and "gross carrying amount" in desc


def reference_check_identities(o: dict, tol: float = 1e-6) -> list[str]:
    """The engine's check_identities on the C06 document blocks, by the one tolerance basis of the contract."""
    rec = o["reconciliation"]
    big_g = sum(abs(r["closing"]) for r in rec["gross_carrying_amount"])
    scale = tol * max(1.0, big_g)
    fails = []
    for kind, rows in (("allowance-rollforward", rec["allowance"]), ("gca-rollforward", rec["gross_carrying_amount"])):
        for r in rows:
            if abs(r["closing"] - (r["opening"] + sum(m["amount"] for m in r["movements"]))) > scale:
                fails.append(f"{kind}:{r['stage']}")
    lines = o["waterfall"]["lines"]
    opening = next(x["amount"] for x in lines if x["kind"] == "opening")
    closing = next(x["amount"] for x in lines if x["kind"] == "closing")
    moves = [x for x in lines if x["kind"] not in ("opening", "closing")]
    if abs(opening + sum(x["amount"] for x in moves) - closing) > scale:
        fails.append("waterfall-closes")
    if abs(sum(r["closing"] for r in rec["allowance"]) - closing) > scale:
        fails.append("waterfall-equals-stage-closings")
    by_id: dict[str, float] = {}
    for r in rec["allowance"]:
        for m in r["movements"]:
            by_id[m["line_id"]] = by_id.get(m["line_id"], 0.0) + m["amount"]
    if set(by_id) != {x["id"] for x in moves} or any(abs(by_id[x["id"]] - x["amount"]) > scale for x in moves):
        fails.append("waterfall-lines-equal-movements")
    ecl = {r["stage"]: r["ecl"] for r in o["stage_summary"]["rows"]}
    ovl: dict[str, float] = {}
    for v in o["overlays"]:
        st = v["stage"] or "stage1"
        ovl[st] = ovl.get(st, 0.0) + v["amount"]
    for r in rec["allowance"]:
        if abs(r["closing"] - (ecl.get(r["stage"], 0.0) + ovl.get(r["stage"], 0.0))) > scale:
            fails.append(f"stage-closing-equals-ecl:{r['stage']}")
    return fails


def test_every_fixture_identity_closes_on_the_one_tolerance_basis_and_a_moved_movement_fails() -> None:
    o = out(C06)
    assert reference_check_identities(o) == []
    bad = copy.deepcopy(o)
    bad["reconciliation"]["allowance"][0]["movements"][0]["amount"] += 1.0
    assert reference_check_identities(bad) != []
    # the declared residuals are the exact differences
    for r in o["reconciliation"]["allowance"] + o["reconciliation"]["gross_carrying_amount"]:
        assert math.isclose(r["residual"], r["closing"] - (r["opening"] + sum(m["amount"] for m in r["movements"])),
                            abs_tol=1e-9)


# --- fix 3: the overlay stage (F-E3) -----------------------------------------------------------------------------------


def test_overlay_record_and_document_carry_a_nullable_stage_with_a_closing_rule() -> None:
    body = section(RV + "overlays.Overlay")
    assert re.search(r"^\s+stage: str \| None", body, flags=re.M)
    assert "null" in body and "stage1 closing" in body
    ovl = schema(C06)["$defs"]["c06Overlay"]
    assert "stage" in ovl["required"]
    o = out(C06)
    assert all("stage" in v for v in o["overlays"])
    line = {x["overlay_id"]: x for x in o["waterfall"]["lines"] if x["kind"] == "overlay"}
    for v in o["overlays"]:
        assert line[v["id"]]["stage"] == v["stage"]
    assert mutated(C06, lambda d: d["outputs"]["overlays"][0].__setitem__("stage", "stage9")) != []
    assert mutated(C06, lambda d: d["outputs"]["overlays"][0].__setitem__("stage", None)) == []


# --- fix 4: the POCI mask (F-E4) ---------------------------------------------------------------------------------------


def test_portfolio_allowance_takes_an_explicit_poci_mask_and_always_returns_four_stage_keys() -> None:
    body = section(RV + "ecl.portfolio_allowance")
    assert "poci: np.ndarray" in body
    assert "excluded from stages 1 to 3" in body
    assert "always has the four keys" in body
    assert "poci: 0.0" in body


# --- fix 5: the low-credit-risk exemption (F-E5) ------------------------------------------------------------------------


def test_the_lcr_exemption_scope_and_the_lcr_exempt_output_are_stated() -> None:
    body = section(RV + "staging.allocate_stages")
    assert "lcr_exempt" in body
    assert "only `relative-absolute` and `threefold`" in body
    assert "5.5.11" in body
    pol = section(RV + "staging.StagingPolicy")
    assert "only `relative-absolute` and `threefold`" in pol or "lcr_exempt" in pol


# --- fix 6: one path for the collective transfer (F-E6) --------------------------------------------------------------


def test_the_collective_transfer_has_one_path_into_stages_and_ecl() -> None:
    body = section(RV + "staging.collective_transfer")
    assert "reports only" in body
    assert "`collective` mask" in body
    assert "never added to any allowance" in body
    assert "descending current PD" in body


# --- fix 7: Annex 9 doubtful buckets in days (F-E8) -------------------------------------------------------------------


def test_annex9_doubtful_buckets_are_in_days_and_the_non_arrears_doubtful_case_raises() -> None:
    text = API.read_text(encoding="utf-8")
    assert "months_past_due" not in text
    body = section(RV + "local_es.annex9_doubtful_coverage")
    assert "days_past_due: int" in body
    assert "(90, 183]" in body and "639" in body
    assert "30.4375" in body
    cov = section(RV + "local_es.annex9_coverage")
    assert "days_past_due: int | None" in cov
    assert "other than arrears" in cov and "raises `ValueError`" in cov


# --- fix 8: group max rule with no internal method (F-E9) -----------------------------------------------------------


def test_group_max_rule_internal_is_nullable_with_a_reason() -> None:
    def no_internal(d: dict, reason: Any) -> None:
        g = d["outputs"]["b1_detail"]["group_max_rule"][0]
        g["internal"], g["internal_reason"], g["method"], g["applied"] = None, reason, "standard", g["standard"]

    assert mutated(C07, lambda d: no_internal(d, "no internal method")) == []
    assert mutated(C07, lambda d: no_internal(d, None)) != []
    assert mutated(C07, lambda d: d["outputs"]["b1_detail"]["group_max_rule"][0].__setitem__("internal", None)) != []


# --- fix 9: scope of the 0.50% minimum (F-E10) ----------------------------------------------------------------------


def test_the_minimum_applies_to_the_individually_assessed_normal_portfolio() -> None:
    body = section(RV + "local_cl.b1_minimum_normal_check")
    assert "individually assessed normal portfolio" in body and "A1 to A6" in body
    assert "never the group" in body or "not the group" in body


# --- fix 10: the B-1 total (F-S3) ---------------------------------------------------------------------------------------


def regimes(o: dict) -> dict:
    return {r["regime"]: r for r in o["regimes"]}


def test_the_b1_total_is_statutory_plus_the_minimum_top_up_and_additional_provisions_stay_outside() -> None:
    o = out(C07)
    reg = regimes(o)
    b1 = reg["cmf-b1"]
    top_up = o["b1_detail"]["minimum_check"]["top_up"]
    assert top_up > 0
    assert [(x["kind"], x["amount"]) for x in b1["unallocated_lines"]] == [("minimum-top-up", top_up)]
    seg_sum = sum(s["provision"] for s in b1["by_segment"])
    assert math.isclose(b1["total_provision"], seg_sum + top_up, abs_tol=1e-6)
    add = o["b1_detail"]["additional_provisions"]["amount"]
    assert add > 0
    assert math.isclose(o["b1_detail"]["booked_total"], b1["total_provision"] + add, abs_tol=1e-6)
    ids = {s["id"] for s in o["gap_bridge"]["steps"]}
    assert "b1-additional-provisions" not in ids and "b1-minimum-top-up" in ids
    gap = reg["ifrs9"]["total_provision"] - b1["total_provision"]
    assert math.isclose(sum(s["amount"] for s in o["gap_bridge"]["steps"]), gap, abs_tol=1e-6)
    desc = schema(C07)["$defs"]["c07Regime"]["properties"]["total_provision"]["description"]
    assert "minimum top-up" in desc and "additional provisions" in desc


def test_every_regime_total_is_the_segment_sum_plus_its_unallocated_lines_and_the_comparison_agrees() -> None:
    o = out(C07)
    for r in o["regimes"]:
        extra = sum(x["amount"] for x in r["unallocated_lines"])
        assert math.isclose(r["total_provision"], sum(s["provision"] for s in r["by_segment"]) + extra, abs_tol=1e-6)
    reg = regimes(o)
    un = o["comparison"]["unallocated"]
    assert math.isclose(un["cmf_b1_provision"], sum(x["amount"] for x in reg["cmf-b1"]["unallocated_lines"]), abs_tol=1e-6)
    assert math.isclose(un["ifrs9_provision"], sum(x["amount"] for x in reg["ifrs9"]["unallocated_lines"]), abs_tol=1e-6)
    assert math.isclose(un["gap_ifrs9_minus_b1"], un["ifrs9_provision"] - un["cmf_b1_provision"], abs_tol=1e-6)
    rows_gap = sum(r["gap_ifrs9_minus_b1"] for r in o["comparison"]["rows"])
    assert math.isclose(rows_gap + un["gap_ifrs9_minus_b1"],
                        reg["ifrs9"]["total_provision"] - reg["cmf-b1"]["total_provision"], abs_tol=1e-6)


# --- fix 11 and Q1: statutory markers, overlays and the IFRS 9 weighting (F-S4, F-S5, F-S6) -----------------------


def test_each_regime_states_its_status_and_the_notice_carries_the_i5_sentence() -> None:
    o = out(C07)
    status = {r["regime"]: r["status"] for r in o["regimes"]}
    assert status == {"cmf-b1": "statutory-chile-loans", "ifrs9": "comparison-measure",
                      "bde-annex9": "spanish-gaap-alternative-solutions"}
    assert "IFRS 9" in o["notice"]["en"] and "not the provision" in o["notice"]["en"]
    assert "statutory" in schema(C07)["$defs"]["c07Outputs"]["description"]
    bad = copy.deepcopy(load(C07))
    bad["outputs"]["regimes"][0]["status"] = "comparison-measure"
    assert cs.errors(C07, bad) != []


def test_the_ifrs9_regime_is_a_probability_weighted_ecl_and_overlays_are_their_own_lines() -> None:
    o = out(C07)
    det = o["ifrs9_detail"]
    assert det["measure"] == "probability-weighted-ecl"
    comps = det["weighted_components"]
    assert len(comps) >= 2
    assert math.isclose(sum(c["weight"] for c in comps), 1.0, abs_tol=1e-9)
    ifrs = regimes(o)["ifrs9"]
    model_ecl = sum(c["weight"] * c["single_scenario_ecl"] for c in comps)
    assert math.isclose(model_ecl, sum(s["provision"] for s in ifrs["by_segment"]), abs_tol=1e-3)
    assert math.isclose(model_ecl, sum(r["ecl"] for r in det["stage_summary"]), abs_tol=1e-3)
    assert math.isclose(ifrs["total_provision"], model_ecl + det["overlays_total"], abs_tol=1e-3)
    assert math.isclose(det["overlays_total"], sum(x["amount"] for x in det["overlays"]), abs_tol=1e-6)
    assert [x["amount"] for x in ifrs["unallocated_lines"]] == [x["amount"] for x in det["overlays"]]
    assert all(x["kind"] == "overlay" for x in ifrs["unallocated_lines"])
    assert det["overlays"], "the fixture exercises a non-zero overlay"
    # a single scenario is never the measure
    assert mutated(C07, lambda d: d["outputs"]["ifrs9_detail"].__setitem__(
        "weighted_components", d["outputs"]["ifrs9_detail"]["weighted_components"][:1])) != []
    assert mutated(C07, lambda d: d["outputs"]["ifrs9_detail"].__setitem__("measure", "single-scenario")) != []
    desc = schema(C07)["$defs"]["c07Ifrs9Detail"]["description"]
    assert "never an IFRS 9 measure" in desc and "model ECL excluding overlays" in desc


def test_the_c07_models_carry_the_ifrs9_weights_the_staging_policy_and_the_eir_basis() -> None:
    fit = load(C07M)["fit"]
    ifrs = fit["ifrs9"]
    ws = ifrs["weighting_scenarios"]
    assert len(ws) >= 2 and math.isclose(sum(w["weight"] for w in ws), 1.0, abs_tol=1e-9)
    assert ifrs["eir_basis"] in ("original", "current", "credit-adjusted")
    pol = ifrs["staging_policy"]
    for key in ("dpd_backstop", "default_dpd", "threefold_ratio", "absolute_floor", "probation_months",
                "low_credit_risk_pd", "multiplier_schedule"):
        assert key in pol, key
    assert all("z_shift" in s for s in fit["scenarios"])
    assert [s for s in fit["scenarios"] if s["id"] == "base"][0]["z_shift"] == 0.0
    doc = copy.deepcopy(load(C07M))
    doc["fit"]["ifrs9"]["weighting_scenarios"] = ws[:1]
    assert cs.errors(C07M, doc) != []
    # the variant's weighting components are those of the models
    comps = {c["scenario_id"]: c["weight"] for c in out(C07)["ifrs9_detail"]["weighted_components"]}
    assert comps == {w["id"]: w["weight"] for w in ws}


# --- fix 12: C06 ids, GCA movement enum and the fixture economics (F-S1, F-S2) -------------------------------------


def test_every_allowance_line_id_is_a_waterfall_line_id_and_amounts_agree() -> None:
    o = out(C06)
    lines = {x["id"]: x for x in o["waterfall"]["lines"]}
    seen: dict[str, float] = {}
    for r in o["reconciliation"]["allowance"]:
        for m in r["movements"]:
            assert m["line_id"] in lines, m["line_id"]
            seen[m["line_id"]] = seen.get(m["line_id"], 0.0) + m["amount"]
    for lid, amt in seen.items():
        assert math.isclose(lines[lid]["amount"], amt, abs_tol=1e-6), lid
    for v in o["overlays"]:
        assert f"overlay-{v['id']}" in lines
    rec_desc = schema(C06)["$defs"]["c06AllowanceMovement"]["properties"]["line_id"]["description"]
    assert "waterfall" in rec_desc


def test_gca_movement_ids_are_an_enum() -> None:
    assert "c06GcaMovement" in schema(C06)["$defs"]
    enum = schema(C06)["$defs"]["c06GcaMovement"]["properties"]["line_id"]["enum"]
    assert {"originations", "transfer-1-2", "transfer-2-3", "repayments", "write-off"} <= set(enum)
    for r in out(C06)["reconciliation"]["gross_carrying_amount"]:
        for m in r["movements"]:
            assert m["line_id"] in enum
    bad = copy.deepcopy(load(C06))
    bad["outputs"]["reconciliation"]["gross_carrying_amount"][1]["movements"][0]["line_id"] = "stage2-to-stage3"
    assert cs.errors(C06, bad) != []


def test_stage1_to_stage3_allowances_are_not_negative_and_only_poci_may_be() -> None:
    o = out(C06)
    gca = {r["stage"]: r for r in o["reconciliation"]["gross_carrying_amount"]}
    for r in o["reconciliation"]["allowance"]:
        assert r["opening"] >= 0 and r["closing"] >= 0, r["stage"]
        assert r["opening"] <= gca[r["stage"]]["opening"], f"{r['stage']}: opening coverage above 100 per cent"
        assert r["closing"] <= gca[r["stage"]]["closing"]

    def neg(d: dict) -> None:
        d["outputs"]["reconciliation"]["allowance"][0]["opening"] = -1.0

    assert mutated(C06, neg) != []

    def poci(d: dict) -> None:
        d["outputs"]["reconciliation"]["allowance"].append(
            {"stage": "poci", "opening": -5.0, "movements": [], "closing": -5.0, "residual": 0.0})

    assert mutated(C06, poci) == []


def test_the_waterfall_sign_is_stated() -> None:
    desc = schema(C06)["$defs"]["c06Waterfall"]["description"]
    assert "positive amount raises the allowance" in desc


# --- fix 13: the catalog rows fragment ----------------------------------------------------------------------------------


def test_the_rows_fragment_passes_the_catalog_checker_and_cites_tests_that_exist() -> None:
    res = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_contracts.py"), str(ROWS),
                          "--repo-root", str(ROOT)], capture_output=True, text=True, cwd=ROOT)
    assert res.returncode == 0, res.stdout + res.stderr
    text = ROWS.read_text(encoding="utf-8")
    for path, name in re.findall(r"(tests/[\w/\.]+\.py)::(\w+)", text):
        src = (ROOT / path).read_text(encoding="utf-8")
        assert re.search(rf"^def {name}\(", src, flags=re.M), f"{path}::{name} does not exist"
    rows = {ln.split("|")[1].strip(): ln for ln in text.splitlines() if ln.startswith("| c0") or ln.startswith("| engine")}
    for rid in ("c07-outputs", "c07-models"):
        assert "C06 data_status" not in rows[rid], rid


# --- fix 14: the lower-priority items ----------------------------------------------------------------------------------


def test_goldens_without_a_tolerance_now_state_one() -> None:
    for name in ("term_structure.weighted_pit_pd", "ecl.probability_weighted_ecl", "ecl.non_linearity_index",
                 "ecl.stage3_ecl"):
        body = section(RV + name)
        gold = next(ln for ln in body.splitlines() if ln.startswith("- Golden"))
        assert re.search(r"to \d(\.\d+)?e-\d+", body.split("- Golden")[1]) or "tolerance" in gold, name
    for name in ("scenario_sensitivity", "nonlinearity_test"):
        body = section(VAL + name)
        assert re.search(r"to \d(\.\d+)?e-\d+", body.split("- Golden")[1]), name
    assert "22222.2222" in section(RV + "ecl.stage3_ecl")


def test_the_lifetime_backtest_names_the_estimator_and_the_sdd_decile_calibration_is_in_the_document() -> None:
    body = section(VAL + "lifetime_pd_backtest")
    assert "Aalen-Johansen" in body and "competing_prepayment" in body
    o = out(C06)
    assert {r["months"] for r in o["decile_calibration"]["rows"]} == {12, 24, 36}
    assert {r["decile"] for r in o["decile_calibration"]["rows"]} == set(range(1, 11))
    assert all(r["estimator"] in ("kaplan-meier", "aalen-johansen") for r in o["decile_calibration"]["rows"])
    assert all("origination_cohort" in r and "estimator" in r for r in o["lifetime_backtest"]["rows"])


def test_horizon_membership_the_simplified_cap_and_the_b1_boundary_rounding_are_stated() -> None:
    assert "member of `months`" in section(RV + "ecl.ecl_scenario")
    assert "min(sum(gca), m * sum(gca * rate))" in section(RV + "ecl.simplified_matrix_ecl")
    assert "1e-9" in section(RV + "local_cl.b1_default_provision") and "rounded" in section(
        RV + "local_cl.b1_default_provision")


@pytest.mark.parametrize("name", ["lifetime_pd_backtest", "sicr_effectiveness", "sicr_threshold_stability",
                                  "stage_migration_backtest", "ecl_backtest", "scenario_sensitivity",
                                  "nonlinearity_test", "overlay_diagnostics", "reconciliation_identities"])
def test_every_validation_function_states_its_light_rule(name: str) -> None:
    assert re.search(r"^- Light:", section(VAL + name), flags=re.M), name


def test_the_annex9_segments_are_codes_and_the_fixture_covers_every_mapped_segment() -> None:
    fit = load(C07M)["fit"]
    codes = {"A.1.1", "A.1.2", "A.1.3", "A.2.1", "A.2.2", "A.2.3", "B.1.1", "B.1.2", "B.1.3", "B.2", "B.2.1", "B.3"}
    defs = schema(C07M)["$defs"]
    enum = defs["c07Fit"]["properties"]["segments"]["items"]["properties"]["bde_segment"]["enum"]
    assert set(enum) == codes
    mapped = {s["bde_segment"] for s in fit["segments"]}
    assert mapped <= codes
    assert all(s["bde_segment_label"]["en"] for s in fit["segments"])
    for block in (fit["bde"]["normal_coverage"], fit["bde"]["doubtful_coverage"]):
        assert mapped <= {r["segment"] for r in block}
    assert len(fit["bde"]["doubtful_bucket_upper_days"]) == len(fit["bde"]["doubtful_bucket_labels"]) == 7
    assert fit["bde"]["doubtful_bucket_upper_days"][-1] is None
    doc = copy.deepcopy(load(C07M))
    doc["fit"]["segments"][0]["bde_segment"] = "B.1.1 Vivienda habitual, LTV <= 80%"
    assert cs.errors(C07M, doc) != []


def test_the_coverage_rate_denominator_is_stated() -> None:
    defs = schema(C07)["$defs"]
    assert "portfolio.gross_exposure" in defs["c07Regime"]["properties"]["coverage_rate"]["description"]
    assert "portfolio.gross_exposure" in defs["c07Regime"]["properties"]["by_segment"]["items"]["properties"][
        "coverage_rate"]["description"]
    o = out(C07)
    expo = {s["segment_id"]: s["gross_exposure"] for s in o["portfolio"]["segments"]}
    for r in o["regimes"]:
        assert math.isclose(r["coverage_rate"], r["total_provision"] / sum(expo.values()), abs_tol=1e-7)
        for s in r["by_segment"]:
            assert math.isclose(s["coverage_rate"], s["provision"] / expo[s["segment_id"]], abs_tol=1e-7)


def walk_currencies(node: Any):
    if isinstance(node, dict):
        if "currency" in node:
            yield node["currency"]
        for v in node.values():
            yield from walk_currencies(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_currencies(v)


@pytest.mark.parametrize("ref", list(EXPECTED))
def test_every_currency_of_one_document_is_the_same(ref: str) -> None:
    assert len(set(walk_currencies(load(ref)))) == 1


def test_the_regime_set_is_exactly_the_three_in_order_and_delta_vs_base_follows_the_scenario() -> None:
    assert mutated(C07, lambda d: d["outputs"]["regimes"].append(copy.deepcopy(d["outputs"]["regimes"][0]))) != []
    assert mutated(C07, lambda d: d["outputs"]["regimes"].pop()) != []
    assert mutated(C07, lambda d: d["outputs"]["regimes"].reverse()) != []

    def base_with_delta(d: dict) -> None:
        d["outputs"]["delta_vs_base"] = {"currency": "CLP", "cmf_b1_delta": 1.0, "ifrs9_delta": 1.0,
                                         "bde_annex9_delta": 1.0}

    def shock_without_delta(d: dict) -> None:
        d["outputs"]["scenario_id"] = "recession"

    assert mutated(C07, base_with_delta) != []
    assert mutated(C07, shock_without_delta) != []

    def shock_with_delta(d: dict) -> None:
        shock_without_delta(d)
        base_with_delta(d)

    assert mutated(C07, shock_with_delta) == []


def test_the_ifrs9_stage_accounts_sum_to_the_portfolio_accounts() -> None:
    o = out(C07)
    assert sum(s["accounts"] for s in o["ifrs9_detail"]["stage_summary"]) == sum(
        s["accounts"] for s in o["portfolio"]["segments"])


def test_the_c06_staging_policy_has_one_source_and_the_models_repeat_it() -> None:
    sicr = out(C06)["settings"]["sicr"]
    pol = load(C06M)["fit"]["staging_policy"]
    for key in ("dpd_backstop", "default_dpd", "threefold_ratio", "absolute_floor", "multiplier_schedule",
                "low_credit_risk_pd"):
        assert key in sicr and key in pol, key
        assert sicr[key] == pol[key], key
    assert out(C06)["settings"]["probation_months"] == pol["probation_months"]
    assert out(C06)["settings"]["low_credit_risk_exemption"] == (pol["low_credit_risk_pd"] is not None)
    assert "authoritative" in schema(C06M)["$defs"]["c06StagingPolicy"]["description"]


def test_scenarios_need_two_poci_stays_poci_and_the_conventions_are_stated() -> None:
    assert mutated(C06, lambda d: d["outputs"].__setitem__("scenarios", d["outputs"]["scenarios"][:1])) != []

    def poci_out(d: dict) -> None:
        d["outputs"]["stage_flows"]["flows"].append(
            {"source": "poci", "target": "stage1", "accounts": 1, "gross_carrying_amount": 1.0})

    assert mutated(C06, poci_out) != []
    defs = schema(C06)["$defs"]
    assert "credit-adjusted" in defs["c06Settings"]["properties"]["eir_basis"]["description"]
    assert "frozen" in defs["c06EclByScenario"]["description"]
