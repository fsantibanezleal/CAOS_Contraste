"""The invariants of a C07 document set, returned as violations (an empty list when they hold); the tests assert the
clean documents hold them and the adversarial tests plant a defect and assert it is found."""
from __future__ import annotations

import math
import re
from typing import Any

REGIMES = ("cmf-b1", "ifrs9", "bde-annex9")


def reg(out: dict[str, Any]) -> dict[str, Any]:
    return {r["regime"]: r for r in out["regimes"]}


def regime_totals(out: dict[str, Any]) -> list[str]:
    bad = []
    for r in out["regimes"]:
        extra = sum(x["amount"] for x in r["unallocated_lines"])
        if not math.isclose(r["total_provision"], sum(s["provision"] for s in r["by_segment"]) + extra, abs_tol=1.0, rel_tol=0):
            bad.append(f"{r['regime']}: total is not the segment sum plus the unallocated lines")
    return bad


def bridge(out: dict[str, Any]) -> list[str]:
    tot = {k: v["total_provision"] for k, v in reg(out).items()}
    gap = tot["ifrs9"] - tot["cmf-b1"]
    steps = sum(s["amount"] for s in out["gap_bridge"]["steps"])
    return [] if abs(steps - gap) <= 1.0 else [f"bridge steps {steps:,.2f} against gap {gap:,.2f}"]


def ifrs9_weighting(out: dict[str, Any]) -> list[str]:
    d = out["ifrs9_detail"]
    bad = []
    comps = d["weighted_components"]
    if d["measure"] != "probability-weighted-ecl":
        bad.append("the IFRS 9 measure is not the probability-weighted ECL")
    if len(comps) < 2 or abs(sum(c["weight"] for c in comps) - 1.0) > 1e-9:
        bad.append("the weights are fewer than two or do not sum to 1")
    model = sum(c["weight"] * c["single_scenario_ecl"] for c in comps)
    seg = sum(s["provision"] for s in reg(out)["ifrs9"]["by_segment"])
    if abs(model - seg) > 1.0:
        bad.append(f"the weighted components {model:,.2f} are not the model ECL {seg:,.2f}")
    return bad


def overlays(out: dict[str, Any]) -> list[str]:
    d, r = out["ifrs9_detail"], reg(out)["ifrs9"]
    bad = []
    if [x["amount"] for x in r["unallocated_lines"]] != [x["amount"] for x in d["overlays"]]:
        bad.append("the overlays are not the unallocated lines of the regime")
    if any(x["kind"] != "overlay" for x in r["unallocated_lines"]):
        bad.append("an unallocated IFRS 9 line is not an overlay")
    stage = sum(s["ecl"] for s in d["stage_summary"])
    seg = sum(s["provision"] for s in r["by_segment"])
    if abs(stage - seg) > 1.0:
        bad.append("the stage summary is not the model ECL by segment (an overlay is inside the model ECL)")
    if abs(r["total_provision"] - (seg + d["overlays_total"])) > 1.0:
        bad.append("the IFRS 9 total is not the model ECL plus the overlays")
    return bad


def minimum_scope(out: dict[str, Any]) -> list[str]:
    mc = out["b1_detail"]["minimum_check"]
    individual = next(s["gross_exposure"] for s in out["portfolio"]["segments"] if s["segment_id"] == "commercial-individual")
    bad = []
    if mc["normal_portfolio_exposure"] > individual + 1.0:
        bad.append("the minimum base exceeds the individually assessed book: it includes a group portfolio")
    want = max(0.0, 0.005 * mc["normal_portfolio_exposure"] - mc["normal_portfolio_provision_before_minimum"])
    if abs(mc["top_up"] - want) > 1.0:
        bad.append("the top-up is not the shortfall of the individual normal portfolio against 0.50%")
    lines = [x for x in reg(out)["cmf-b1"]["unallocated_lines"] if x["kind"] == "minimum-top-up"]
    if len(lines) != 1 or abs(lines[0]["amount"] - mc["top_up"]) > 1.0:
        bad.append("the top-up is not its own line")
    return bad


def same_portfolio(outs: dict[str, dict[str, Any]]) -> list[str]:
    first = next(iter(outs.values()))["portfolio"]
    return [f"{sid}: another portfolio" for sid, o in outs.items() if o["portfolio"] != first]


def synthetic(doc: dict[str, Any]) -> list[str]:
    bad = []
    text = repr(doc).lower()
    prov = doc.get("provenance", {})
    if prov.get("truth_status") != "synthetic-calibrated":
        bad.append("truth status is not synthetic-calibrated")
    notice = doc.get("outputs", {}).get("notice") or doc.get("fit", {}).get("bank", {}).get("notice") or {}
    if "synthetic" not in notice.get("en", "").lower() or "sintético" not in notice.get("es", "").lower():
        bad.append("the notice does not say synthetic in both languages")
    if re.search(r"banco andino (is|es) (a )?(real|an actual|un banco real)", text):
        bad.append("a text presents Banco Andino as a real bank")
    return bad


def all_variant(out: dict[str, Any]) -> list[str]:
    return regime_totals(out) + bridge(out) + ifrs9_weighting(out) + overlays(out) + minimum_scope(out)
