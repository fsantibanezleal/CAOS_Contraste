"""The cross-field checks of the C16 documents, as importable functions (as ``tests/contracts_u10/semantics.py`` for C14 and C15).

JSON Schema cannot hold these: they compare values across fields, recompute numbers, or compare dates. The bake calls
``check_document`` on every document it writes (a non-empty list is a refusal to publish), and the producer tests run it over
every committed document (the fixtures and ``data/derived/C16``). The formulas are written here from the dossiers (05 E.1 and
E.5, 01 G.1) and the U11 sizing and do not import the fixture builder.

Each function returns a list of messages, empty when the document conforms.
"""
from __future__ import annotations

import math
import statistics
from typing import Any

TOL = 1e-3        # money in USD thousands, the fixtures round to six decimals
EVENT_AMOUNT = 140_000_000   # over 40 bn USD on 9 March plus over 100 bn USD expected on 10 March, USD thousands (Fed review, 08 E.3)
HQLA_L2_CAP, HQLA_L2B_CAP, INFLOW_CAP = 0.40, 0.15, 0.75


def close(a: float, b: float, rel: float = 1e-9, tol: float = TOL) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=tol)


class Report(list):
    def need(self, ok: bool, message: str) -> None:
        if not ok:
            self.append(message)


def implied_rate(share: float, days: int) -> float:
    return 1.0 - (1.0 - share) ** (1.0 / days)


def check_document(doc: dict) -> list[str]:
    """Dispatch on the document kind; a document that is not a C16 document is refused."""
    if not isinstance(doc, dict) or doc.get("case_id") != "C16":
        return ["not a C16 document"]
    if "outputs" in doc:
        kind = doc["outputs"].get("kind")
        if kind == "scenario":
            return check_scenario(doc)
        if kind == "reverse-stress":
            return check_reverse(doc)
        return [f"unknown outputs.kind {kind!r}"]
    if "fit" in doc:
        return check_models(doc)
    return ["a C16 document has outputs or fit"]


def check_conventions_agree(docs: list[dict]) -> list[str]:
    """The named parameters are the same in every document of one bake (a view reads them from any)."""
    found = [(d.get("variant_id") or d.get("fit_id"), (d.get("outputs") or d.get("fit") or {}).get("conventions")) for d in docs]
    found = [(n, c) for n, c in found if c is not None]
    rep = Report()
    for name, conv in found[1:]:
        rep.need(conv == found[0][1], f"conventions of {name} differ from those of {found[0][0]}")
    return rep


def survival_key(s: dict) -> float:
    return math.inf if s["kind"] == "survives-horizon" else float(s["day"])


def first_negative(nlp: list[float]) -> int | None:
    return next((i + 1 for i, v in enumerate(nlp) if v < 0), None)


# ------------------------------------------------------------------------------------------------ scenario documents


def check_scenario(doc: dict) -> list[str]:
    rep = Report()
    o = doc["outputs"]
    conv = o["conventions"]
    bs = o["balance_sheet"]
    dep = bs["deposits"]
    vid = o["variant"]["id"]
    # the dating rule: never a call report dated after the valuation date
    vd = o["valuation_date"]
    rep.need(all(r["report_date"] <= vd for r in o["data"]["call_reports"]), "a call report is dated after the valuation date")
    rep.need(o["data"]["data_cutoff"] == max(r["report_date"] for r in o["data"]["call_reports"]),
             "data_cutoff is not the latest report date read")
    rep.need(o["data"]["data_cutoff"] <= vd, "data_cutoff is after the valuation date")
    rep.need(o["data"]["read_up_to_valuation_date"] is True, "read_up_to_valuation_date is not true")
    rep.need(bs["as_of"] == vd, "balance_sheet.as_of is not the valuation date")
    _deposits(dep, rep, "balance_sheet.deposits")
    # the variant against the named mapping
    row = next((r for r in conv["variant_scenarios"]["rows"] if r["variant"] == vid), None)
    if row is None:
        rep.append(f"variant {vid} has no row in the conventions' variant_scenarios")
    else:
        for k in ("scenario_family", "phase", "parameter_set", "horizon_days", "axis"):
            rep.need(o["variant"][k] == row[k], f"variant.{k} differs from the conventions' variant_scenarios row of {vid}")
    # the call-report items
    for it in bs["items"]:
        rep.need((it["reported_amount"] is None) == (it["reason_missing"] is not None),
                 f"item {it['item_id']}: reported_amount and reason_missing disagree")
    # the CBC
    cbc = o["cbc"]
    rep.need(cbc["as_of"] == vd, "cbc.as_of is not the valuation date")
    for c in cbc["classes"]:
        used_ok = close(c["value_used"], c["carrying_value"]) or (c["fair_value"] is not None and close(c["value_used"], c["fair_value"]))
        rep.need(used_ok, f"cbc class {c['class_id']}: value_used is neither the carrying value nor the fair value")
        rep.need(close(c["liquidity_value"], (c["value_used"] - c["encumbered"]) * (1 - c["haircut"]["value"])),
                 f"cbc class {c['class_id']}: liquidity_value is not (value used - encumbered) x (1 - haircut)")
    rep.need(close(cbc["total_liquidity_value"], sum(c["liquidity_value"] for c in cbc["classes"])),
             "cbc total_liquidity_value is not the sum of the classes")
    rep.need(close(cbc["pledged"]["amount"], sum(c["encumbered"] for c in cbc["classes"])),
             "cbc pledged amount is not the sum of the encumbered parts")
    # the time block
    for t in o["time_block"]:
        rep.need(t["report_date"] <= t["as_of"] < vd, f"time block {t['as_of']}: report date or as_of after the valuation date")
        _deposits(t["deposits"], rep, f"time_block {t['as_of']}")
        rep.need((t["survival"] is None) == (o["path"] is None), f"time block {t['as_of']}: survival and the daily path disagree")
        rep.need((t["lcr_ratio"] is not None) == (o["lcr"] is not None), f"time block {t['as_of']}: lcr_ratio and the LCR block disagree")
    # the contractual ladder
    cl = o["contractual_ladder"]["buckets"]
    cum = 0.0
    for b in cl:
        cum += b["gap"]
        rep.need(close(b["gap"], b["inflows"] - b["outflows"]), "a contractual bucket gap is not inflows minus outflows")
        rep.need(close(b["cumulative_gap"], cum), "a contractual cumulative gap is not the running sum of the gaps")
    # the daily path
    survival_value = None
    horizon = None
    if o["path"] is not None:
        horizon = _path(o, rep)
        s = o["path"]["survival"]
        survival_value = s["day"]
    rep.need(doc["impact"]["survival_days"]["value"] == survival_value, "impact survival_days does not follow the survival period")
    # the LCR
    if o["lcr"] is not None:
        _lcr(o["lcr"], rep)
        rep.need(doc["impact"]["lcr"]["value"] is not None and close(doc["impact"]["lcr"]["value"], o["lcr"]["ratio"], tol=1e-9),
                 "impact lcr does not follow the LCR ratio")
    else:
        rep.need(doc["impact"]["lcr"]["value"] is None, "impact lcr is a number where the variant runs no LCR")
    # the HTM block
    if o["htm"] is not None:
        _htm(o, rep)
    # the scoring block
    _scoring(o, horizon, rep)
    # the test rows
    for t in doc["tests"]:
        rep.need(t["test_id"].startswith("liq."), f"test id {t['test_id']} does not start with liq.")
    return rep


def _deposits(d: dict, rep: Report, where: str) -> None:
    rep.need(close(d["uninsured_share_of_dep"], d["depuna"] / d["dep"], tol=1e-6),
             f"{where}: uninsured_share_of_dep is not DEPUNA over DEP")
    rep.need(close(d["uninsured_share_of_depdom"], d["depuna"] / d["depdom"], tol=1e-6),
             f"{where}: uninsured_share_of_depdom is not DEPUNA over DEPDOM")


def _path(o: dict, rep: Report) -> int:
    p = o["path"]
    lad = p["ladder"]
    h = len(lad["nlp"])
    conv = o["conventions"]
    series = {"day_index": lad["day_index"], "dates": lad["dates"], "total_outflows": lad["total_outflows"],
              "total_inflows": lad["total_inflows"], "cbc_total": lad["cbc_total"],
              "cumulative_net_outflow": lad["cumulative_net_outflow"], "nlp": lad["nlp"]}
    for name, arr in series.items():
        rep.need(len(arr) == h, f"ladder.{name} has {len(arr)} values, not the horizon {h}")
    for s in lad["segments"]:
        for name in ("cumulative_outflow_share", "outflows"):
            rep.need(len(s[name]) == h, f"segment {s['segment']}: {name} has {len(s[name])} values, not the horizon {h}")
        if s["daily_rates"] is not None:
            rep.need(len(s["daily_rates"]) == h, f"segment {s['segment']}: daily_rates has {len(s['daily_rates'])} values, not {h}")
    for c in lad["cbc_stack"]:
        rep.need(len(c["liquidity_value"]) == h, f"cbc stack {c['class_id']} has {len(c['liquidity_value'])} values, not {h}")
    for f in lad["other_outflows"] + lad["inflows"]:
        rep.need(len(f["amounts"]) == h, f"flow {f['component_id']} has {len(f['amounts'])} values, not {h}")
    rep.need(o["variant"]["horizon_days"] == h, "variant.horizon_days is not the ladder horizon")
    rep.need(lad["day_index"] == list(range(1, h + 1)), "ladder.day_index is not 1 to the horizon")
    rep.need(lad["axis"] == o["variant"]["axis"], "ladder.axis differs from the variant's axis")
    if len(lad["nlp"]) != h or any(len(a) != h for a in series.values()) or any(len(s["outflows"]) != h for s in lad["segments"]):
        return h   # the shape is wrong; the identities below need it
    # the segment run-off curves
    for s in lad["segments"]:
        opening = s["opening_balance"]
        cumulative, prod = [], 1.0
        if s["mechanism"] == "open-maturity-compounding":
            for q in s["daily_rates"]:
                prod *= 1.0 - q
                cumulative.append(1.0 - prod)
        else:
            run = 0.0
            for x in s["outflows"]:
                run += x
                cumulative.append(run / opening if opening else 0.0)
        for d in range(h):
            rep.need(close(s["cumulative_outflow_share"][d], cumulative[d], tol=1e-6),
                     f"segment {s['segment']}: cumulative share of day {d + 1} is not the recomputed one (1 - prod(1 - q))")
            prev = cumulative[d - 1] if d else 0.0
            rep.need(close(s["outflows"][d], opening * (cumulative[d] - prev), tol=TOL),
                     f"segment {s['segment']}: outflow of day {d + 1} is not opening x the cumulative increment")
    # the totals, the CBC, the NLP identity
    running = 0.0
    for d in range(h):
        out = sum(s["outflows"][d] for s in lad["segments"]) + sum(f["amounts"][d] for f in lad["other_outflows"])
        inn = sum(f["amounts"][d] for f in lad["inflows"])
        rep.need(close(lad["total_outflows"][d], out), f"total_outflows of day {d + 1} is not the sum of its components")
        rep.need(close(lad["total_inflows"][d], inn), f"total_inflows of day {d + 1} is not the sum of its components")
        rep.need(close(lad["cbc_total"][d], sum(c["liquidity_value"][d] for c in lad["cbc_stack"])),
                 f"cbc_total of day {d + 1} is not the stack sum")
        running += lad["total_outflows"][d] - lad["total_inflows"][d]
        rep.need(close(lad["cumulative_net_outflow"][d], running), f"cumulative_net_outflow of day {d + 1} is not the running sum")
        rep.need(close(lad["nlp"][d], lad["cbc_total"][d] - lad["cumulative_net_outflow"][d],
                       tol=conv["nlp_identity_tolerance"]["value"] + TOL),
                 f"nlp of day {d + 1} breaks NLP = CBC - cumulative net outflow")
    # the CBC stack follows the monetisation schedule (a step function of the day)
    pts = sorted(conv["monetisation_schedule"]["points"], key=lambda x: x["day"])
    classes = {c["class_id"]: c["liquidity_value"] for c in o["cbc"]["classes"]}
    for c in lad["cbc_stack"]:
        rep.need(c["class_id"] in classes, f"cbc stack class {c['class_id']} is not a class of the CBC block")
        for d in range(h):
            share = 0.0
            for pt in pts:
                if pt["day"] <= d + 1:
                    share = pt["cumulative_share"]
            rep.need(c["class_id"] not in classes or close(c["liquidity_value"][d], classes[c["class_id"]] * share),
                     f"cbc stack {c['class_id']} of day {d + 1} is not its liquidity value x the monetisation share")
    rep.need(close(sum(c["liquidity_value"] for c in o["cbc"]["classes"]), sum(classes.values())), "cbc classes do not sum")
    # the survival period, the minimum, the cliff
    first = first_negative(lad["nlp"])
    s = p["survival"]
    rep.need(s["horizon_days"] == h, "survival.horizon_days is not the ladder horizon")
    if first is None:
        rep.need(s["kind"] == "survives-horizon", "survival is a number where the NLP never turns negative (it survives the horizon)")
    else:
        rep.need(s["kind"] == "day" and s["day"] == first,
                 f"survival is not the first day on which the NLP turns negative (day {first})")
    low = min(lad["nlp"])
    rep.need(close(p["minimum_nlp"]["value"], low) and p["minimum_nlp"]["day"] == lad["nlp"].index(low) + 1,
             "minimum_nlp is not the minimum of the NLP and its first day")
    near, far = conv["cliff_days"]["near"], conv["cliff_days"]["far"]
    if h >= far:
        c = p["cliff"]
        rep.need(c is not None and p["cliff_reason"] is None, "the cliff is null where the horizon reaches the far day")
        if c is not None:
            rep.need(close(c["nlp_near"], lad["nlp"][near - 1]) and close(c["nlp_far"], lad["nlp"][far - 1]),
                     "the cliff NLP values are not those of the near and far days")
            rep.need(close(c["value"], (c["nlp_far"] - c["nlp_near"]) / c["total_assets"], rel=1e-9, tol=1e-9),
                     "the cliff value is not (NLP(far) - NLP(near)) / total assets")
    else:
        rep.need(p["cliff"] is None, "a cliff is stated where the horizon is shorter than the far day")
    return h


def _lcr(lcr: dict, rep: Report) -> None:
    h = lcr["hqla"]
    al1, al2a, al2b = h["adjusted_l1"], h["adjusted_l2a"], h["adjusted_l2b"]
    adj15 = max(al2b - 15 / 85 * (al1 + al2a), al2b - 15 / 60 * al1, 0.0)
    adj40 = max(al2a + al2b - adj15 - 2 / 3 * al1, 0.0)
    rep.need(close(h["adj_15"], adj15), "HQLA Adj15 is not the LCR30.39 formula on the adjusted amounts")
    rep.need(close(h["adj_40"], adj40), "HQLA Adj40 is not the LCR30.39 formula on the adjusted amounts")
    rep.need(close(h["hqla"], h["l1"] + h["l2a"] + h["l2b"] - h["adj_15"] - h["adj_40"]),
             "HQLA is not L1 + L2A + L2B - Adj15 - Adj40 (LCR30.38)")
    if h["hqla"] > 0:
        rep.need(close(h["l2b_share"], (h["l2b"] - h["adj_15"]) / h["hqla"], tol=1e-9), "l2b_share is not Level 2B after Adj15 over HQLA")
        rep.need(close(h["l2_share"], (h["l2a"] + h["l2b"] - h["adj_15"] - h["adj_40"]) / h["hqla"], tol=1e-9),
                 "l2_share is not Level 2 after the adjustments over HQLA")
        rep.need(h["l2b_share"] <= HQLA_L2B_CAP + 1e-9, "Level 2B is above the 15 percent cap of HQLA")
        rep.need(h["l2_share"] <= HQLA_L2_CAP + 1e-9, "Level 2 is above the 40 percent cap of HQLA")
    for name, total in (("outflows", "total_outflows"), ("inflows", "total_inflows")):
        for r in lcr[name]:
            rep.need(close(r["amount"], r["balance"] * r["rate"]), f"LCR {name} row {r['category']}: amount is not balance x rate")
        rep.need(close(lcr[total], sum(r["amount"] for r in lcr[name])), f"LCR {total} is not the sum of its rows")
    expected = min(lcr["total_inflows"], INFLOW_CAP * lcr["total_outflows"])
    rep.need(close(lcr["inflows_counted"], expected), "LCR inflows counted are not min(inflows, 75 percent of outflows)")
    rep.need(lcr["inflows_counted"] <= INFLOW_CAP * lcr["total_outflows"] + TOL, "LCR inflows counted are above 75 percent of outflows")
    rep.need(close(lcr["net_outflows"], lcr["total_outflows"] - lcr["inflows_counted"]), "LCR net outflows are not outflows minus the counted inflows")
    if lcr["net_outflows"] > 0:
        rep.need(close(lcr["ratio"], h["hqla"] / lcr["net_outflows"], rel=1e-9, tol=1e-9), "LCR ratio is not HQLA over net outflows")
    cats = {r["lcr_category"] for r in lcr["mapping_sensitivity"]}
    rep.need({"operational", "non-financial-corporate", "other-legal-entity"} <= cats,
             "the LCR mapping sensitivity does not cover the operational, non-financial corporate and other legal entity classes")


def _htm(o: dict, rep: Report) -> None:
    h = o["htm"]
    r = h["reported"]
    rep.need(close(r["htm_unrealised"], r["htm_fair_value"] - r["htm_amortised_cost"]), "htm_unrealised is not fair value minus amortised cost")
    rep.need(close(r["afs_unrealised"], r["afs_fair_value"] - r["afs_amortised_cost"]), "afs_unrealised is not fair value minus amortised cost")
    rep.need(close(h["cbc_removed"], h["cbc_without_loss"] - h["cbc_with_loss"]), "htm cbc_removed is not the CBC without the loss minus with it")
    rep.need(close(h["cbc_with_loss"], o["cbc"]["total_liquidity_value"]), "htm cbc_with_loss is not the CBC of the fair-value basis")
    rep.need(close(h["btfp_par"]["uplift"], h["btfp_par"]["cbc_at_par"] - h["cbc_without_loss"]), "the par uplift is not the par CBC minus the CBC without the loss")
    rv = h["revaluation"]
    rep.need(close(rv["reported_fair_value"], r["htm_fair_value"]), "the revaluation row's reported fair value is not SCHF")
    if rv["status"] == "evaluated":
        rep.need(close(rv["difference"], rv["model_fair_value"] - rv["reported_fair_value"]), "the revaluation difference is not model minus reported")
        if r["htm_unrealised"]:
            rep.need(close(rv["relative_difference"], abs(rv["difference"]) / abs(r["htm_unrealised"]), tol=1e-9),
                     "the revaluation relative difference is not |difference| over |reported unrealised loss|")


def _modelled_amount(lad: dict, horizon: int) -> float:
    return sum(sum(s["outflows"][:horizon]) for s in lad["segments"])


def _light(ratio: float, conv: dict) -> str:
    if ratio >= conv["scoring_ratio_green"]["value"]:
        return "green"
    return "amber" if ratio >= conv["scoring_ratio_amber"]["value"] else "red"


def _scoring(o: dict, horizon: int | None, rep: Report) -> None:
    sc = o["scoring"]
    conv = o["conventions"]
    dep = o["balance_sheet"]["deposits"]
    rep.need(sc["event"]["horizon_days"] == conv["event_horizon_days"]["value"], "the event horizon is not the convention event_horizon_days")
    base = sc["model_deposit_base"]
    mo = sc["modelled_outflow"]
    if o["path"] is not None:
        lad = o["path"]["ladder"]
        rep.need(close(base, sum(s["opening_balance"] for s in lad["segments"])), "model_deposit_base is not the sum of the segments' opening balances")
        by_seg = {s["segment"]: s["opening_balance"] for s in lad["segments"]}
        if "retail-insured" in by_seg:
            rep.need(close(by_seg["retail-insured"], dep["depins"]), "the retail-insured segment is not DEPINS")
        unins = sum(v for k, v in by_seg.items() if k in ("retail-uninsured", "operational", "non-operational-corporate"))
        rep.need(close(unins, dep["depuna"]), "the uninsured segments do not sum to DEPUNA")
        if mo["at_event_horizon"] is not None:
            e = mo["at_event_horizon"]
            rep.need(e["horizon_days"] == sc["event"]["horizon_days"], "at_event_horizon is not at the event horizon")
            rep.need(close(e["amount"], _modelled_amount(lad, e["horizon_days"])), "the modelled outflow at the event horizon is not the ladder's")
            rep.need(close(e["share_of_model_base"], e["amount"] / base, tol=1e-9), "the modelled share at the event horizon is not amount over base")
        m = mo["at_model_horizon"]
        rep.need(m["horizon_days"] == horizon, "at_model_horizon is not the ladder horizon")
        rep.need(close(m["amount"], _modelled_amount(lad, m["horizon_days"])), "the modelled outflow at the model horizon is not the ladder's")
        rep.need(mo["at_event_horizon"] is not None, "a variant with a daily path states its outflow at the event horizon")
    else:
        rep.need(mo["at_event_horizon"] is None, "the LCR variant has no daily path and so no outflow at the event horizon")
        m = mo["at_model_horizon"]
        rep.need(m["horizon_days"] == o["variant"]["horizon_days"], "at_model_horizon is not the variant's horizon")
        rep.need(close(m["share_of_model_base"], m["amount"] / base, tol=1e-9), "the modelled share is not amount over base")
    rep.need(close(m["share_of_model_base"], m["amount"] / base, tol=1e-9), "the modelled share is not amount over base")
    chosen = mo["at_event_horizon"] if mo["at_event_horizon"] is not None else mo["at_model_horizon"]
    at = "event-horizon" if mo["at_event_horizon"] is not None else "model-horizon"
    board, call = sc["denominators"]
    rep.need(close(board["realised_share"], sc["svb_anchor"]["outflow_share"], tol=1e-9), "the Board's realised share is not the anchor's 85 percent")
    rep.need(close(call["denominator_amount"], dep["dep"]), "the call-report denominator is not DEP")
    rep.need(close(call["realised_amount"], EVENT_AMOUNT), f"the realised amount is not {EVENT_AMOUNT} (over 40 bn plus 100 bn USD)")
    rep.need(close(call["realised_share"], call["realised_amount"] / call["denominator_amount"], rel=1e-9, tol=1e-9),
             "the call-report realised share is not the amount over the denominator")
    for d in (board, call):
        want = chosen["share_of_model_base"] if d is board else chosen["amount"] / dep["dep"]
        rep.need(close(d["modelled_share"], want, rel=1e-9, tol=1e-9), f"{d['id']}: modelled_share is not the ladder's")
        rep.need(d["compared_at"] == at, f"{d['id']}: compared_at is not {at}")
        rep.need(close(d["shortfall"], d["realised_share"] - d["modelled_share"], tol=1e-9), f"{d['id']}: shortfall is not realised minus modelled")
        rep.need(close(d["ratio"], d["modelled_share"] / d["realised_share"], rel=1e-9, tol=1e-9), f"{d['id']}: ratio is not modelled over realised")
        rep.need(d["light"] == _light(d["ratio"], conv), f"{d['id']}: the light breaks the scoring_ratio conventions")
    a = sc["svb_anchor"]
    rep.need(close(a["implied_daily_rate"], implied_rate(a["outflow_share"], a["days"]), tol=5e-7),
             "the anchor's implied daily rate is not 1 - (1 - share)^(1 / days)")
    rep.need(a["forecast_claim"] is False, "the anchor claims a forecast")
    for r in sc["table_a1_scoring"]:
        want_role = ("calibration" if r["year"] < 2023 else "scored") if o["variant"]["id"] == "fast-run" else "reference"
        rep.need(r["role"] == want_role, f"Table A.1 row {r['row_id']}: role {r['role']} is not {want_role}")
        if o["path"] is None or r["horizon_days"] > horizon:
            rep.need(r["modelled_share"] is None and r["error"] is None and r["reason"] is not None,
                     f"Table A.1 row {r['row_id']}: the horizon is beyond the model's ladder, so the share is null with its reason")
        else:
            lad = o["path"]["ladder"]
            rep.need(r["modelled_share"] is not None and r["reason"] is None, f"Table A.1 row {r['row_id']}: modelled share is null")
            if r["modelled_share"] is not None:
                rep.need(close(r["modelled_share"], _modelled_amount(lad, r["horizon_days"]) / base, tol=1e-9),
                         f"Table A.1 row {r['row_id']}: modelled_share is not the ladder's at the row's horizon")
                rep.need(close(r["error"], r["observed_share"] - r["modelled_share"], tol=1e-9),
                         f"Table A.1 row {r['row_id']}: error is not observed minus modelled")


# ------------------------------------------------------------------------------------------------ reverse stress


def check_reverse(doc: dict) -> list[str]:
    rep = Report()
    o = doc["outputs"]
    conv = o["conventions"]
    rep.need(o["target"]["days"] == conv["reverse_target_days"]["value"], "the target is not the convention reverse_target_days")
    tol = conv["round_trip_tolerance_days"]["value"]
    for b in o["bases"]:
        curve = b["curve"]
        ms = [p["multiplier"] for p in curve]
        rep.need(all(x < y for x, y in zip(ms, ms[1:])), f"{b['base_id']}: the multipliers are not strictly increasing")
        rep.need(ms[0] == 1.0, f"{b['base_id']}: the curve does not start at the base multiplier 1")
        rep.need(ms[-1] <= b["max_multiplier"] + 1e-12, f"{b['base_id']}: a curve point is beyond the cap (each rate stays below 1)")
        keys = [survival_key(p["survival"]) for p in curve]
        rep.need(all(x >= y for x, y in zip(keys, keys[1:])), f"{b['base_id']}: SP(m) is not monotone non-increasing in the multiplier")
        rep.need(b["base_survival"] == curve[0]["survival"], f"{b['base_id']}: base_survival is not the survival at multiplier 1")
        sol = b["solved"]
        target = o["target"]["days"]
        rep.need(sol["target_days"] == target, f"{b['base_id']}: the solved target is not the document's target")
        horizon = curve[0]["survival"]["horizon_days"]
        bracketed = keys[0] > target and keys[-1] <= target and target < horizon
        if sol["status"] == "solved":
            rep.need(bracketed, f"{b['base_id']}: solved without a bracketed target")
            rep.need(1.0 <= sol["multiplier"] <= b["max_multiplier"] + 1e-12, f"{b['base_id']}: the solved multiplier is beyond the cap")
            rep.need(sol["round_trip_error"] is not None and close(sol["round_trip_error"], sol["survival_at_multiplier"] - target, tol=1e-9),
                     f"{b['base_id']}: round trip: round_trip_error is not survival_at_multiplier minus the target")
            rep.need(abs(sol["survival_at_multiplier"] - target) <= tol + 1e-12,
                     f"{b['base_id']}: round trip: the survival at the solved multiplier is not the target within the tolerance")
            first = next((p for p in curve if survival_key(p["survival"]) <= target), None)
            if first is not None:
                rep.need(sol["multiplier"] <= first["multiplier"] + 1e-12, f"{b['base_id']}: the solved multiplier is above the first curve point at the target")
        else:
            rep.need(not bracketed, f"{b['base_id']}: refused although the target is bracketed")
            rep.need(sol["refusal_reason"] is not None, f"{b['base_id']}: refused without its reason")
        name = {"list-adverse": "multiplier_list_adverse", "list-extreme": "multiplier_list_extreme", "fast-run": "multiplier_fast_run"}[b["base_id"]]
        want = sol["multiplier"] if sol["status"] == "solved" else None
        got = doc["impact"][name]["value"]
        rep.need((got is None and want is None) or (got is not None and want is not None and close(got, want, tol=1e-9)),
                 f"impact {name} does not follow the solved multiplier")
    return rep


# ------------------------------------------------------------------------------------------------ models


def check_models(doc: dict) -> list[str]:
    rep = Report()
    fit = doc["fit"]
    for g in fit["list_goldens"]:
        rep.need(abs(g["cumulative_outflow"] - (1 - (1 - g["daily_rate"]) ** g["days"])) <= 5e-7,
                 f"golden {g['id']}: cumulative_outflow is not 1 - (1 - q)^n")
    rows = {r["row_id"]: r for r in fit["table_a1"]["rows"]}
    cal = fit["calibration"]
    rates = []
    for r in cal["implied_daily_rates"]:
        src = rows[r["row_id"]]
        rep.need(abs(r["implied_daily_rate"] - implied_rate(src["outflow_share"], src["days"])) <= 5e-7,
                 f"calibration {r['row_id']}: the implied daily rate is not 1 - (1 - share)^(1 / days)")
        rates.append(r["implied_daily_rate"])
    rule = fit["conventions"]["fast_run_calibration_rule"]["rule"]
    pick = {"maximum-implied-daily-rate": max, "median-implied-daily-rate": statistics.median,
            "mean-implied-daily-rate": statistics.fmean}[rule](rates)
    rep.need(abs(cal["fitted_daily_rate"]["value"] - pick) <= 5e-7, f"the fitted daily rate is not the {rule} of the implied rates")
    a = cal["anchor"]
    rep.need(abs(a["implied_daily_rate"] - implied_rate(a["outflow_share"], a["days"])) <= 5e-7,
             "the anchor's implied daily rate is not 1 - (1 - share)^(1 / days)")
    gen = fit["generator"]
    rep.need(abs(sum(s["share_of_deposits"] for s in gen["config"]["segments"]) - 1.0) <= 1e-9, "the generator's segment shares do not sum to one")
    v = gen["verification"]
    red = fit["conventions"]["generator_truth_se_red"]["value"]
    rep.need(v["within_error"] == (v["max_abs_error"] <= red * v["mc_standard_error"] + 1e-15),
             "within_error does not follow max_abs_error against the Monte Carlo standard error")
    by: dict[str, list[tuple[int, float]]] = {}
    for t in gen["truth"]:
        by.setdefault(t["segment"], []).append((t["horizon_days"], t["true_outflow_rate"]))
    for seg, pts in by.items():
        pts.sort()
        rep.need(all(y2 >= y1 for (_, y1), (_, y2) in zip(pts, pts[1:])), f"generator truth of {seg} is not non-decreasing in the horizon")
    return rep
