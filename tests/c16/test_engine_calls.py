"""CT-1609 to CT-1615: the consumer test of ``engine-liquidity-api`` 1.2.0. Every liquidity number of a document equals a
``riskvalidation`` call on the inputs the document carries (ADR-0069: the product holds no formula), run on the committed samples."""
from __future__ import annotations

import numpy as np
import pytest

PATH_VARIANTS = ("list-adverse", "list-extreme", "fast-run", "htm-losses")


def close(a, b, rtol=1e-9, atol=1e-6) -> bool:
    return bool(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), rtol=rtol, atol=atol))


def _rates(seg: dict, h: int) -> np.ndarray:
    return np.full(h, 1.0) if seg["daily_rates"] is None else np.array(seg["daily_rates"], dtype=float)


def _points(conv: dict) -> list[tuple[int, float]]:
    return [(p["day"], p["cumulative_share"]) for p in conv["monetisation_schedule"]["points"]]


def test_every_ladder_number_equals_the_engine_call_on_the_inputs(built):
    from riskvalidation.liquidity import cbc as ecbc
    from riskvalidation.liquidity import ladder, runoff, scenarios

    for vid in PATH_VARIANTS:
        o = built.variants[vid]["outputs"]
        lad, conv = o["path"]["ladder"], o["conventions"]
        h = len(lad["nlp"])
        opening = np.array([s["opening_balance"] for s in lad["segments"]])
        rates = np.vstack([_rates(s, h) for s in lad["segments"]])
        out = ladder.behavioural_outflows(opening, rates)
        for k, s in enumerate(lad["segments"]):
            assert close(s["cumulative_outflow_share"], runoff.cumulative_outflow_path(rates[k])), (vid, s["segment"])
            assert close(s["outflows"], out[k]), (vid, s["segment"])
        # the transcribed LiST rates are the engine's
        sev = "extreme" if o["variant"]["parameter_set"] == "list-extreme" else "adverse"
        lst = scenarios.list_scenario(sev)
        for s in lad["segments"]:
            if s["parameters"][0]["source_kind"] == "transcribed-list-2019" and s["mechanism"] == "open-maturity-compounding":
                assert s["daily_rates"] == [lst.class_rate(s["list_class"])] * h
        # the CBC: the stack is the engine's, class by class, from the value used, the encumbered part and the haircut
        classes = {c["class_id"]: (c["value_used"], c["encumbered"], c["haircut"]["value"]) for c in o["cbc"]["classes"]}
        stack = ecbc.cbc_stack(classes, _points(conv), h)
        for c in lad["cbc_stack"]:
            assert close(c["liquidity_value"], stack[c["class_id"]]), (vid, c["class_id"])
        for c in o["cbc"]["classes"]:
            assert close(c["liquidity_value"], ecbc.liquidity_value(c["value_used"], c["haircut"]["value"], c["encumbered"]))
            rule = next(r for r in conv["cbc_securities_mapping"]["rows"] if r["class_id"] == c["class_id"])
            if rule["rule"] == "central-bank-framework":
                got = ecbc.haircut_rule("non-equity", central_bank_eligible=True, central_bank_haircut=1.0 - rule["margin"])
                assert got[1] == "central-bank-framework" and close(got[0], c["haircut"]["value"])
        total_out = out.sum(axis=0) + sum(np.array(f["amounts"]) for f in lad["other_outflows"]) if lad["other_outflows"] else out.sum(axis=0)
        total_in = sum((np.array(f["amounts"]) for f in lad["inflows"]), np.zeros(h))
        cbc_total = sum((stack[k] for k in stack), np.zeros(h))
        nlp = ladder.net_liquidity_position(cbc_total, total_out, total_in)
        assert close(lad["total_outflows"], total_out) and close(lad["total_inflows"], total_in) and close(lad["cbc_total"], cbc_total)
        assert close(lad["nlp"], nlp)
        sv = ladder.survival_period(nlp)
        want = {"kind": "survives-horizon", "day": None, "horizon_days": h} if sv.survives else {"kind": "day", "day": sv.day, "horizon_days": h}
        assert o["path"]["survival"] == want
        low, day = ladder.minimum_nlp(nlp)
        assert close(o["path"]["minimum_nlp"]["value"], low) and o["path"]["minimum_nlp"]["day"] == day
        near, far = conv["cliff_days"]["near"], conv["cliff_days"]["far"]
        if h >= far:
            assert close(o["path"]["cliff"]["value"], ladder.cliff_effect(nlp, o["balance_sheet"]["total_assets"], near, far), atol=1e-12)
        else:
            assert o["path"]["cliff"] is None and o["path"]["cliff_reason"]["en"]
        # the contractual ladder: gaps and cumulative gaps are the engine's
        b = o["contractual_ladder"]["buckets"]
        gap, cum = ladder.contractual_gaps(np.array([x["inflows"] for x in b]), np.array([x["outflows"] for x in b]))
        assert close([x["gap"] for x in b], gap) and close([x["cumulative_gap"] for x in b], cum)
    # the goldens of the contract reproduce on the pinned engine, and the models document repeats them
    assert abs(float(runoff.cumulative_outflow_constant(0.00103258, 125)) - 0.121148) <= 5e-7
    assert abs(float(runoff.cumulative_outflow_constant(0.00161494, 125)) - 0.182930) <= 5e-7
    for g in built.models["fit"]["list_goldens"]:
        assert abs(g["cumulative_outflow"] - float(runoff.cumulative_outflow_constant(g["daily_rate"], g["days"]))) <= 5e-7
    # every test row of a document is a riskvalidation TestResult row
    from pipeline.core.manifest import TEST_RESULT_KEYS

    for d in built.variants.values():
        for t in d["tests"]:
            assert set(t) == set(TEST_RESULT_KEYS) and t["test_id"].startswith("liq.")


def test_the_fast_run_is_calibrated_on_the_pre_2023_rows_only(built):
    from riskvalidation.liquidity import runoff, scenarios

    pre = [r for r in runoff.TABLE_A1 if r.year < 2023]
    scored = [r for r in runoff.TABLE_A1 if r.year >= 2023]
    fit = scenarios.fast_run_scenario(pre, "maximum-implied-daily-rate", scored=True)
    cal = built.models["fit"]["calibration"]
    assert cal["split"]["calibrated_on"] == [r.row_id for r in pre] and cal["split"]["scored_on"] == [r.row_id for r in scored]
    assert cal["fitted_daily_rate"]["value"] == fit.daily_rate and cal["fitted_daily_rate"]["source_kind"] == "calibrated-pre-2023"
    assert [x["implied_daily_rate"] for x in cal["implied_daily_rates"]] == pytest.approx(list(fit.implied_rates), abs=1e-6)
    # a 2023 row never calibrates a scored variant: the engine refuses it, and a rate that took it in would be the SVB rate
    with pytest.raises(ValueError, match="2023"):
        scenarios.fast_run_scenario(scored, "maximum-implied-daily-rate", scored=True)
    with_2023 = scenarios.fast_run_scenario(list(runoff.TABLE_A1), "maximum-implied-daily-rate")
    assert with_2023.daily_rate > fit.daily_rate and cal["fitted_daily_rate"]["value"] != with_2023.daily_rate
    # the fast-run document runs the calibrated rate on the uninsured segment, labels the rows by role and carries the anchor
    doc = built.variants["fast-run"]["outputs"]
    seg = next(s for s in doc["path"]["ladder"]["segments"] if s["segment"] == "non-operational-corporate")
    assert seg["parameters"][0]["source_kind"] == "calibrated-pre-2023" and set(seg["daily_rates"]) == {fit.daily_rate}
    roles = {r["row_id"]: r["role"] for r in doc["scoring"]["table_a1_scoring"]}
    assert {roles[r.row_id] for r in pre} == {"calibration"} and {roles[r.row_id] for r in scored} == {"scored"}
    anchor = doc["scoring"]["svb_anchor"]
    want = scenarios.anchor_from_observation(0.85, 2)
    assert anchor["implied_daily_rate"] == pytest.approx(want["implied_daily_rate"], abs=1e-6) and anchor["forecast_claim"] is False
    assert anchor["outflow_share"] == 0.85 and anchor["days"] == 2 and anchor["label"]["en"].startswith("Labelled anchor, not a forecast")
    assert doc["conventions"]["fast_run_calibration_rule"]["rule"] == "maximum-implied-daily-rate"


def test_a_survival_period_is_a_day_or_survives_the_horizon_with_its_horizon():
    from pipeline.cases.c16 import variant

    assert variant.survival_block(np.array([70.0, 40.0, -10.0, -70.0])) == {"kind": "day", "day": 3, "horizon_days": 4}
    assert variant.survival_block(np.array([5.0, 4.0, 3.0])) == {"kind": "survives-horizon", "day": None, "horizon_days": 3}
    assert variant.survival_block(np.array([1.0, 0.0, 0.0])) == {"kind": "survives-horizon", "day": None, "horizon_days": 3}   # zero is not negative
    assert variant.survival_block(np.array([-1.0, 5.0])) == {"kind": "day", "day": 1, "horizon_days": 2}


def test_the_lcr_is_labelled_a_basel_formula_and_carries_the_mapping_band(built):
    from riskvalidation.regulatory import lcr_nsfr

    doc = built.variants["lcr-standard"]
    lcr = doc["outputs"]["lcr"]
    assert lcr["label"] == "basel-formula-on-call-report-aggregates" and lcr["reported_or_regulatory"] is False
    st = lcr["statement"]
    assert "not the bank's reported or regulatory LCR" in st["en"] and "no es el LCR" in st["es"]
    assert doc["outputs"]["path"] is None and doc["outputs"]["path_reason"]["en"]
    h = lcr["hqla"]
    eng = lcr_nsfr.hqla_stock(h["l1"], h["l2a"], h["l2b"], h["adjusted_l1"], h["adjusted_l2a"], h["adjusted_l2b"])
    assert h["hqla"] == pytest.approx(eng.hqla, rel=1e-12) and h["adj_15"] == pytest.approx(eng.adj_15, abs=1e-6)
    assert h["adj_40"] == pytest.approx(eng.adj_40, abs=1e-6) and h["l2_share"] == pytest.approx(eng.l2_share, rel=1e-9)
    out = lcr_nsfr.lcr_outflows({r["category"]: r["balance"] for r in lcr["outflows"]})
    inn = lcr_nsfr.lcr_inflows({r["category"]: r["balance"] for r in lcr["inflows"]})
    net = lcr_nsfr.net_cash_outflows(out.total, inn.total, lcr["inflow_cap"])
    assert lcr["total_outflows"] == pytest.approx(out.total, rel=1e-12) and lcr["total_inflows"] == pytest.approx(inn.total, rel=1e-12)
    assert lcr["inflows_counted"] == pytest.approx(net.inflows_counted, rel=1e-12) and lcr["net_outflows"] == pytest.approx(net.net, rel=1e-12)
    assert lcr["ratio"] == pytest.approx(lcr_nsfr.lcr_ratio(eng.hqla, net.net), rel=1e-12)
    for r in lcr["outflows"]:
        if r["category"] != "trade_finance":
            assert r["rate"] == lcr_nsfr.LCR_OUTFLOW_RATES[r["category"]]
    assert doc["impact"]["lcr"]["value"] == lcr["ratio"] and "Basel formula" in doc["impact"]["lcr"]["label"]["en"]
    # the band: the central row is the block itself, every other row swaps the uninsured outflow for its category's table rate
    band = {r["mapping_id"]: r for r in lcr["mapping_sensitivity"]}
    assert band["central"]["ratio"] == lcr["ratio"] and {r["lcr_category"] for r in band.values()} >= {
        "operational", "non_financial_corporate", "other_legal_entity"}
    uninsured = doc["outputs"]["balance_sheet"]["deposits"]["depuna"]
    for r in band.values():
        assert r["uninsured_outflow"] == pytest.approx(uninsured * lcr_nsfr.LCR_OUTFLOW_RATES[r["lcr_category"]], rel=1e-12)
        n2 = lcr_nsfr.net_cash_outflows(r["total_outflows"], inn.total, lcr["inflow_cap"])
        assert r["ratio"] == pytest.approx(lcr_nsfr.lcr_ratio(eng.hqla, n2.net), rel=1e-9)
    assert band["band-other-legal-entity"]["ratio"] < band["central"]["ratio"] < band["band-operational"]["ratio"]
    assert [d["lcr_ratio"] is not None for d in doc["outputs"]["time_block"]] == [True, True]


def test_an_empty_hqla_stock_gives_null_shares_with_their_reason():
    from pipeline.cases.c16 import variant

    empty = variant.hqla_block(0.0, 0.0, 0.0)
    assert empty["hqla"] == 0.0 and empty["l2_share"] is None and empty["l2b_share"] is None
    assert empty["shares_reason"]["en"] and empty["shares_reason"]["es"]
    # a stock that has levels gives the shares, with no reason
    full = variant.hqla_block(100.0, 20.0, 30.0)
    assert full["l2b_share"] == pytest.approx(0.15, abs=1e-9) and full["adj_15"] == pytest.approx(8.823529, abs=1e-6)
    assert full["hqla"] == pytest.approx(141.176471, abs=1e-6) and full["shares_reason"] is None
    # an LCR over an empty stock is a ratio of zero over a positive net outflow only when the caller asks; the block never calls it 0 share
    assert variant.hqla_block(100.0, 0.0, 0.0)["hqla"] == 100.0


def test_the_reverse_stress_solves_the_threshold_multiplier_with_its_round_trip(built):
    from riskvalidation.liquidity import cbc as ecbc
    from riskvalidation.liquidity import reverse
    from riskvalidation.liquidity.scenarios import Scenario, ScenarioSegment
    from riskvalidation.validation import liquidity as val

    from pipeline.cases.c16 import reverse as rev

    doc = built.reverse
    target = doc["outputs"]["target"]["days"]
    assert target == doc["outputs"]["conventions"]["reverse_target_days"]["value"] == 30
    for b in doc["outputs"]["bases"]:
        vid = b["base_id"]
        lad = built.variants[vid]["outputs"]["path"]["ladder"]
        h = len(lad["nlp"])
        segs = tuple(ScenarioSegment(s["segment"], s["list_class"], s["opening_balance"], _rates(s, h)) for s in lad["segments"])
        scn = Scenario("idiosyncratic", "protracted", h, segs)
        # the engine's NLP takes no flows but the segments' and no inflows: the document hands it the CBC plus the cumulative
        # inflows less the cumulative other outflows, which leaves the same NLP (the other flows do not scale with the multiplier)
        seg_out = np.sum([s["outflows"] for s in lad["segments"]], axis=0)
        eff = np.array(lad["cbc_total"]) + np.cumsum(lad["total_inflows"]) - np.cumsum(np.array(lad["total_outflows"]) - seg_out)
        assert close(eff - np.cumsum(seg_out), lad["nlp"])
        assert close(rev.effective_cbc(lad), eff)
        base_sv = reverse.survival_vs_multiplier(scn, eff, np.array([1.0]))[0]
        assert b["base_survival"]["day"] == base_sv.day and b["base_survival"] == built.variants[vid]["outputs"]["path"]["survival"]
        assert b["max_rate_below_one"] == pytest.approx(1.0 / reverse.max_multiplier(scn), rel=1e-12)
        sol = b["solved"]
        if sol["status"] == "refused":
            assert sol["refusal_reason"]["en"] and sol["multiplier"] is None
            continue
        # the threshold property through the survival just below the multiplier
        want = reverse.solve_multiplier(scn, eff, target)
        assert want.status == "solved" and sol["multiplier"] == want.multiplier and sol["survival_at_multiplier"] == want.survival_at_multiplier
        assert sol["round_trip_error"] == sol["survival_at_multiplier"] - target <= 0
        below = want.survival_just_below
        assert below.survives or below.day > target
        rt = next(t for t in doc["tests"] if t["test_id"] == "liq.reverse_stress_round_trip" and t["segment"] == vid)
        ref = val.reverse_stress_round_trip(want.multiplier, want.survival_at_multiplier, target, 0.0, survival_just_below=below)
        assert rt["light"] == ref.light.value and rt["statistic"] == ref.statistic
    # a target not below the horizon is refused with its reason, never a number (the fast run's ladder is 5 days)
    fast = next(b for b in doc["outputs"]["bases"] if b["base_id"] == "fast-run")
    assert fast["solved"]["status"] == "refused" and "not below the" in fast["solved"]["refusal_reason"]["en"]
    nr = next(t for t in doc["tests"] if t["test_id"] == "liq.reverse_stress_round_trip" and t["segment"] == "fast-run")
    assert nr["light"] == "not_evaluated" and nr["statistic"] is None and nr["notes"]
    # the product's solver wraps the engine: one segment of 1000 at q 0.01 with a CBC that steps (the contract's step case)
    seg = ScenarioSegment("retail-insured", "other-retail", 1000.0, np.full(60, 0.01))
    scn = Scenario("idiosyncratic", "protracted", 60, (seg,))
    stepped = ecbc.monetisation_capacity(1000.0, [(1, 0.015), (2, 1.0)], 60)
    block = rev.solved_block(scn, stepped, 5)
    assert block["status"] == "solved" and block["survival_at_multiplier"] == 1 and block["round_trip_error"] == -4
    assert block["survival_just_below"] == {"kind": "survives-horizon", "day": None, "horizon_days": 60}


def test_the_htm_variant_carries_the_par_counterfactual_and_the_revaluation_row(built):
    from riskvalidation.liquidity import cbc as ecbc
    from riskvalidation.validation import liquidity as val

    doc = built.variants["htm-losses"]
    o = doc["outputs"]
    htm = o["htm"]
    assert o["cbc"]["htm_valuation_basis"] == "fair-value"
    rep = htm["reported"]
    assert rep["htm_unrealised"] == pytest.approx(rep["htm_fair_value"] - rep["htm_amortised_cost"], abs=1e-6) and rep["htm_unrealised"] < 0
    assert htm["application"]["method"] == "whole-book"
    # the CBC with and without the loss and the par counterfactual are engine calls on the same classes
    without = built.variants["list-adverse"]["outputs"]["cbc"]["total_liquidity_value"]
    assert htm["cbc_without_loss"] == pytest.approx(without, rel=1e-12) and htm["cbc_with_loss"] == pytest.approx(o["cbc"]["total_liquidity_value"], rel=1e-12)
    assert htm["cbc_removed"] == pytest.approx(without - o["cbc"]["total_liquidity_value"], rel=1e-9) and htm["cbc_removed"] > 0
    assert htm["btfp_par"]["announced"] == "2023-03-12" and "after the run" in htm["btfp_par"]["label"]["en"]
    assert htm["btfp_par"]["cbc_at_par"] > without >= o["cbc"]["total_liquidity_value"]
    par = sum(ecbc.liquidity_value(c["carrying_value"], 0.0 if c["class_id"] in ("treasury", "mortgage-backed", "other-agency") else c["haircut"]["value"],
                                   c["encumbered"]) for c in built.variants["list-adverse"]["outputs"]["cbc"]["classes"])
    assert htm["btfp_par"]["cbc_at_par"] == pytest.approx(par, rel=1e-9) and htm["btfp_par"]["uplift"] == pytest.approx(par - without, rel=1e-9)
    one = ecbc.cbc_with_htm_loss(100.0, 85.0, 20.0, 0.1)
    assert (one.cbc_without_loss, one.cbc_with_loss) == (72.0, 58.5)
    # the revaluation of the HTM book from its maturity profile under the Treasury curve is a validation row against the reported value
    rv = htm["revaluation"]
    assert rv["status"] == "evaluated" and rv["engine_ref"] == "engine-irrbb-api" and rv["curve_date"] <= "2022-12-31"
    assert rv["reported_fair_value"] == rep["htm_fair_value"] and rv["difference"] == pytest.approx(rv["model_fair_value"] - rv["reported_fair_value"], abs=1e-6)
    row = next(t for t in doc["tests"] if t["test_id"] == "liq.htm_revaluation_vs_reported")
    ref = val.htm_revaluation_vs_reported(rv["model_fair_value"], rv["reported_fair_value"], rep["htm_amortised_cost"], 0.05, 0.15)
    assert row["light"] == ref.light.value and row["statistic"] == pytest.approx(ref.statistic, rel=1e-12)
    # the Treasury curve is read up to the date: without any curve the row is not_evaluated with its reason, never a number
    from pipeline.cases.c16 import bake

    from .helpers import sample_inputs

    inp = sample_inputs()
    inp.curves = {}
    d2 = bake.build(42, inp, n_draws=50, only=("htm-losses",)).variants["htm-losses"]["outputs"]["htm"]["revaluation"]
    assert d2["status"] == "not_evaluated" and d2["model_fair_value"] is None and d2["reason"]["en"]
