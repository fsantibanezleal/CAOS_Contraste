"""CT-705 to CT-708: the minimum scope, the IFRS 9 weighting, the overlays and the bridge, on every variant."""
from __future__ import annotations

import numpy as np
from pipeline.cases.c07 import b1
from pipeline.cases.c07 import book as bk
from riskvalidation.provisions import local_cl as cl
import invariants


def test_the_minimum_applies_to_the_individual_normal_portfolio_only(built, outs) -> None:
    for sid, out in outs.items():
        assert invariants.minimum_scope(out) == [], sid
        mc = out["b1_detail"]["minimum_check"]
        assert mc["minimum_rate"] == 0.005
    book, ev = built["book"], built["evaluations"]["base"]
    res, state = ev["b1"], ev["state"]
    ind = book.seg == b1.INDIVIDUAL_ID
    # the base of the minimum is the A1 to A6 individual debtors: no group account, no substandard, no default
    assert res.normal_mask.sum() > 0
    assert (res.normal_mask <= ind).all()
    assert (state.cat[res.normal_mask] <= 5).all() and not state.default[res.normal_mask].any()
    mc = cl.b1_minimum_normal_check(float(book.e[res.normal_mask].sum()), float(res.provision[res.normal_mask].sum()))
    assert outs["base"]["b1_detail"]["minimum_check"]["top_up"] == round(mc.top_up, 2)
    # a group portfolio below 0.50 per cent is never topped up: the low-LTV mortgages are provisioned at their B-1 factor
    lo = bk.SEG_IDS.index("mortgage-ltv-le80")
    seg = {s["segment_id"]: s for s in invariants.reg(outs["base"])["cmf-b1"]["by_segment"]}["mortgage-ltv-le80"]
    assert seg["coverage_rate"] < 0.005
    assert seg["provision"] == round(float(res.provision[book.seg == lo].sum()), 2)
    # forcing the shortfall on the individual book moves only the top-up line: engine check on a synthetic shortfall
    forced = cl.b1_minimum_normal_check(float(book.e[res.normal_mask].sum()), 0.001 * float(book.e[res.normal_mask].sum()))
    assert forced.binding and forced.top_up > 0
    assert [x["kind"] for x in invariants.reg(outs["base"])["cmf-b1"]["unallocated_lines"]] == ["minimum-top-up"]


def test_the_ifrs9_regime_is_probability_weighted_and_labelled(outs) -> None:
    for sid, out in outs.items():
        d = out["ifrs9_detail"]
        assert invariants.ifrs9_weighting(out) == [], sid
        assert d["measure"] == "probability-weighted-ecl"
        assert [c["scenario_id"] for c in d["weighted_components"]] == ["upside", "central", "downside"]
        assert invariants.reg(out)["ifrs9"]["status"] == "comparison-measure"
        assert "not the provision" in out["notice"]["en"] and "synthetic" in out["notice"]["en"].lower()
        comp = [c["single_scenario_ecl"] for c in d["weighted_components"]]
        model = sum(s["provision"] for s in invariants.reg(out)["ifrs9"]["by_segment"])
        assert min(comp) < model < max(comp)       # the weighted measure is none of its components
        assert invariants.reg(out)["cmf-b1"]["status"] == "statutory-chile-loans"


def test_overlays_are_separate_lines_outside_the_model_ecl(outs) -> None:
    for sid, out in outs.items():
        assert invariants.overlays(out) == [], sid
        d = out["ifrs9_detail"]
        assert {x["id"] for x in d["overlays"]} == {"OVL-HOUSING", "OVL-CARDS"}
        assert d["overlays_total"] > 0
        assert [x["id"] for x in invariants.reg(out)["ifrs9"]["unallocated_lines"]] == ["overlay-OVL-HOUSING", "overlay-OVL-CARDS"]


def test_the_gap_bridge_closes_to_the_unit(outs) -> None:
    for sid, out in outs.items():
        assert invariants.bridge(out) == [], sid
        ids = [s["id"] for s in out["gap_bridge"]["steps"]]
        assert ids == ["measurement-basis", "lifetime-horizon", "forward-looking", "discounting", "b1-minimum-top-up", "ifrs9-overlays"]
        assert out["gap_bridge"]["from_regime"] == "cmf-b1" and out["gap_bridge"]["to_regime"] == "ifrs9"
        assert invariants.regime_totals(out) == [], sid
        # the additional provisions are outside both totals and are not a step
        b = out["b1_detail"]
        assert b["booked_total"] == round(invariants.reg(out)["cmf-b1"]["total_provision"] + b["additional_provisions"]["amount"], 2)
        assert "b1-additional-provisions" not in ids
    deltas = {sid: out["delta_vs_base"] for sid, out in outs.items()}
    assert deltas["base"] is None and all(deltas[s] is not None for s in deltas if s != "base")
    assert deltas["combined-severe"]["ifrs9_delta"] > deltas["recession"]["ifrs9_delta"] > 0


def test_group_max_rule_without_an_internal_method_is_standard(outs) -> None:
    rule = outs["base"]["b1_detail"]["group_max_rule"]
    assert [r["segment_id"] for r in rule] == [s for s in bk.SEG_IDS if s != "commercial-individual"]
    for r in rule:
        assert r["internal"] is None and r["method"] == "standard" and r["applied"] == r["standard"] and r["internal_reason"]
    assert np.isclose(sum(r["applied"] for r in rule) + outs["base"]["b1_detail"]["individual"]["normal_substandard_provision"]
                      + outs["base"]["b1_detail"]["individual"]["default_provision"],
                      sum(s["provision"] for s in invariants.reg(outs["base"])["cmf-b1"]["by_segment"]), atol=1.0)
