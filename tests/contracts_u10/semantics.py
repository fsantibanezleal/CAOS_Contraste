"""The cross-field checks of the C14 and C15 documents, as importable functions (D3 of the U10 sizing; as in U7 M3).

JSON Schema cannot hold these: they compare values across fields, recompute numbers, or compare dates. The bakes call
``check_document`` on every document they write (a non-empty list is a refusal to publish), and the producer tests run it
over every committed document (the fixtures and ``data/derived/C14``, ``C15``). The formulas are written here from the
dossiers (01 H, 03 F.2, 05 D) and do not import the fixture builder.

Each function returns a list of messages, empty when the document conforms.
"""
from __future__ import annotations

import math

SHOCKS = ["parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down"]
MIDPOINTS = [0.0028, 0.0417, 0.1667, 0.375, 0.625, 0.875, 1.25, 1.75, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 12.5, 17.5, 25.0]
GAMMA_U = [1.2, 0.8, 0.8, 1.2, 1.2, 0.8]          # SRP31.125 Table 6, the order of SHOCKS
NMD_CLASS_CATEGORY = {
    "nmd-retail-transactional": "retail-transactional", "nmd-retail-non-transactional": "retail-non-transactional",
    "nmd-wholesale": "wholesale", "nmd-retail-operational": "retail-operational",
    "nmd-retail-non-operational": "retail-non-operational",
}


# ------------------------------------------------------------------------------------------------ formulas


def shape_bp(shock: str, par: float, short: float, long: float) -> list[float]:
    s = [short * math.exp(-t / 4) for t in MIDPOINTS]
    lg = [long * (1 - math.exp(-t / 4)) for t in MIDPOINTS]
    return {
        "parallel-up": [par] * 19, "parallel-down": [-par] * 19, "short-up": s, "short-down": [-x for x in s],
        "steepener": [-0.65 * abs(a) + 0.9 * abs(b) for a, b in zip(s, lg)],
        "flattener": [0.8 * abs(a) - 0.6 * abs(b) for a, b in zip(s, lg)],
    }[shock]


def post_rate(r0: float, d_bp: float, floor: float | None) -> float:
    r = r0 + d_bp / 1e4
    return r if floor is None else max(r, min(floor, r0))


def eve_of(cf: list[float], rates: list[float]) -> float:
    return sum(c * math.exp(-r * t) for c, r, t in zip(cf, rates, MIDPOINTS))


def dense(flows: list[dict]) -> list[float]:
    v = [0.0] * 19
    for f in flows:
        v[f["bucket"] - 1] += f["amount"]
    return v


def cmf_pair(clp: float, clf: float, offset: bool = True) -> float:
    """RAN 21-13 Annex 1, dossier 03 F.2: the CLP and CLF pair with the 50 percent offset on opposite signs."""
    if not offset or clp * clf >= 0:
        return max(clp, 0.0) + max(clf, 0.0)
    return max(0.5 * clp + clf, 0.0) if clp <= 0 else max(clp + 0.5 * clf, 0.0)


def simulate_nii(items: list[dict], path: list[float], growth: float = 0.0) -> list[float]:
    """The engine contract's simulate_nii: monthly NII of the items under a short-rate path (m is the 0-based month)."""
    out = []
    for m in range(len(path)):
        total = 0.0
        for it in items:
            k = it["reprice_months"]
            if k == 0:
                rate = it["spread"] + it["beta"] * path[m]
            elif m < k:
                rate = it["rate0"]
            else:
                rate = it["spread"] + it["beta"] * path[(m // k) * k]
            total += (1 if it["side"] == "asset" else -1) * it["balance"] * (1 + growth) ** (m / 12) * rate / 12
        out.append(total)
    return out


def close(a: float, b: float, rel: float = 1e-9, tol: float = 5e-3) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=tol)


class Report(list):
    def need(self, ok: bool, message: str) -> None:
        if not ok:
            self.append(message)


# ------------------------------------------------------------------------------------------------ shared blocks


def check_nmd_segments(out: dict, items: list[dict], rep: Report, where: str) -> None:
    segs = out["nmd_segments"]
    total = sum(s["balance"] for s in segs)
    for s in segs:
        want_share = min(s["requested_core_share"], s["core_share_cap"])
        want_mat = min(s["requested_core_maturity_years"], s["core_maturity_cap_years"])
        rep.need(close(s["core_share_used"], want_share, tol=1e-12), f"{where}: {s['category']} core_share_used is not min(request, cap)")
        rep.need(close(s["core_maturity_used_years"], want_mat, tol=1e-12), f"{where}: {s['category']} core_maturity_used_years is not min(request, cap)")
        exceeds = s["requested_core_share"] > s["core_share_cap"] or s["requested_core_maturity_years"] > s["core_maturity_cap_years"]
        rep.need(s["cap_applied"] == exceeds, f"{where}: {s['category']} cap_applied does not match the request against the cap")
    a = out["assumptions"]
    rep.need(close(a["nmd_core_share"]["value"], sum(s["balance"] * s["core_share_used"] for s in segs) / total, rel=0, tol=1e-9),
             f"{where}: nmd_core_share is not the balance-weighted average of the used values")
    rep.need(close(a["nmd_core_maturity_years"]["value"], sum(s["balance"] * s["core_maturity_used_years"] for s in segs) / total, rel=0,
                   tol=1e-9), f"{where}: nmd_core_maturity_years is not the balance-weighted average of the used values")
    # the NMD items slot the used values: the non-core share overnight, the core share around the used maturity
    for it in items:
        cat = NMD_CLASS_CATEGORY.get(it.get("behavioural_class", ""))
        if cat is None:
            continue
        seg = next((s for s in segs if s["category"] == cat), None)
        if seg is None:
            rep.append(f"{where}: item {it['item_id']} has no nmd_segments entry for {cat}")
            continue
        flows = it["cash_flows"]["behavioural"] if isinstance(it["cash_flows"], dict) else it["cash_flows"]
        v = dense(flows)
        amount = abs(sum(v))
        core = [-x for x in v[1:]]
        core_total = sum(core)
        rep.need(close(-v[0], (1 - seg["core_share_used"]) * amount, tol=1e-3), f"{where}: item {it['item_id']} non-core flow is not (1 - used share) x balance")
        if core_total > 0:
            wam = sum(c * t for c, t in zip(core, MIDPOINTS[1:])) / core_total
            rep.need(close(wam, seg["core_maturity_used_years"], rel=0, tol=1e-6), f"{where}: item {it['item_id']} core maturity is not the used maturity")


def check_dynamic(block: dict, r_short: float, par_bp: float, floor: float | None, rep: Report, where: str, beta: float | None = None) -> None:
    h = block["horizon_months"]
    base_total = None
    names = [s["scenario"] for s in block["scenarios"]]
    rep.need(names == ["base", "parallel-up", "parallel-down"], f"{where}: scenarios are not base, parallel-up, parallel-down")
    for sc in block["scenarios"]:
        bp = {"base": 0.0, "parallel-up": par_bp, "parallel-down": -par_bp}[sc["scenario"]]
        rep.need(sc["shock_bp"] == bp, f"{where}: {sc['scenario']} shock_bp is {sc['shock_bp']}, expected {bp}")
        rep.need(len(sc["short_rate_path"]) == h and len(sc["monthly_nii"]) == h, f"{where}: {sc['scenario']} path or NII is not horizon_months long")
        want_rate = post_rate(r_short, bp, floor)
        rep.need(all(close(x, want_rate, rel=0, tol=1e-8) for x in sc["short_rate_path"]), f"{where}: {sc['scenario']} path is not the floored short rate")
        growth = block["balance_sheet_assumption"]["growth_annual"]
        want = simulate_nii(block["items"] if "items" in block else block["_items"], sc["short_rate_path"], growth)
        rep.need(all(close(a, b, tol=5e-3) for a, b in zip(sc["monthly_nii"], want)), f"{where}: {sc['scenario']} monthly NII does not recompute")
        rep.need(close(sc["total"], sum(sc["monthly_nii"])), f"{where}: {sc['scenario']} total is not the sum of the months")
        if base_total is None:
            base_total = sc["total"]
        rep.need(close(sc["delta_vs_base"], base_total - sc["total"]), f"{where}: {sc['scenario']} delta_vs_base is not base minus scenario")
    if beta is not None:
        rep.need(any(i["side"] == "liability" and close(i["beta"], beta, rel=0, tol=1e-9) for i in block["items"]),
                 f"{where}: no liability item carries the deposit beta of the assumptions")


def check_ear_evar(ee: dict, base_nii: float, base_eve: float, horizon: int, rep: Report, where: str) -> None:
    """One EaR and EVaR block (ladder rung 6): its bases are the dynamic NII's base total and the base EVE, its horizon the dynamic NII's,
    ear and evar are base minus the quantile, and the Monte Carlo errors are present and below the measure."""
    rep.need(close(ee["base_nii"], base_nii), f"{where} ear_evar base_nii is not the base total of the dynamic NII")
    rep.need(close(ee["base_eve"], base_eve), f"{where} ear_evar base_eve is not the base EVE")
    rep.need(ee["horizon_months"] == horizon, f"{where} ear_evar horizon differs from the dynamic NII's")
    for lv in ee["levels"]:
        rep.need(close(lv["ear"], ee["base_nii"] - lv["nii_quantile"]), f"{where} ear at {lv['level']} is not base_nii - the NII quantile")
        rep.need(close(lv["evar"], ee["base_eve"] - lv["eve_quantile"]), f"{where} evar at {lv['level']} is not base_eve - the EVE quantile")
    for lv in ee["levels"]:
        rep.need(lv["ear_se"] >= 0 and (lv["ear"] == 0 or lv["ear_se"] < abs(lv["ear"])), f"{where} ear_se at {lv['level']} is not below |ear|")
        rep.need(lv["evar_se"] >= 0 and (lv["evar"] == 0 or lv["evar_se"] < abs(lv["evar"])), f"{where} evar_se at {lv['level']} is not below |evar|")
    l95, l99 = ee["levels"]
    rep.need(l99["ear"] >= l95["ear"] and l99["evar"] >= l95["evar"], f"{where} EaR or EVaR at 99 percent is below the 95 percent value")


# ------------------------------------------------------------------------------------------------ C14


def dating_violations(doc: dict) -> list[str]:
    """The call reports are read only up to the valuation date (SDD section 5, C14)."""
    o = doc["outputs"]
    v = o["valuation_date"]
    found = [f"call report {r['report_date']} is after the valuation date {v}" for r in o["data"]["call_reports"] if r["report_date"] > v]
    if o["data"]["data_cutoff"] > v:
        found.append(f"data cutoff {o['data']['data_cutoff']} is after the valuation date {v}")
    if o["data"]["call_reports"] and o["data"]["data_cutoff"] != max(r["report_date"] for r in o["data"]["call_reports"]):
        found.append("the data cutoff is not the latest call report date")
    if o["curve"]["date"] != v:
        found.append(f"the curve date {o['curve']['date']} is not the valuation date {v}")
    if o["balance_sheet"]["as_of"] != v:
        found.append(f"the balance sheet is as of {o['balance_sheet']['as_of']}, not the valuation date {v}")
    oos = o["out_of_sample"]
    if oos["projection_date"] != v:
        found.append(f"the out-of-sample projection date {oos['projection_date']} is not the valuation date {v}")
    if oos["applicable"] and not (oos["realised_period_start"] > v and oos["realised_period_end"] >= oos["realised_period_start"]):
        found.append("the realised period of the out-of-sample row does not start after the valuation date")
    return found


def check_c14(doc: dict) -> list[str]:
    rep = Report(dating_violations(doc))
    o = doc["outputs"]
    r0 = o["curve"]["zero_rates_at_midpoints"]
    items = o["balance_sheet"]["items"]
    rep.need(doc["variant_id"].endswith(o["quarter"].lower()), "variant_id does not end with the quarter")
    rep.need(o["valuation_date"][:4] == o["quarter"][:4], "quarter and valuation date differ")
    check_nmd_segments(o, items, rep, "c14")
    flows = {n: [0.0] * 19 for n in ("behavioural", "contractual")}
    for it in items:
        for n in flows:
            for b, v in enumerate(dense(it["cash_flows"][n])):
                flows[n][b] += v
        side = 1.0 if it["side"] == "asset" else -1.0
        for n in flows:
            rep.need(close(sum(dense(it["cash_flows"][n])), side * it["amount"]), f"item {it['item_id']} {n} flows do not sum to its amount")
    bs = o["balance_sheet"]
    rep.need(close(bs["total_assets"], sum(i["amount"] for i in items if i["side"] == "asset")), "total_assets is not the sum of the asset items")
    rep.need(close(bs["total_liabilities"], sum(i["amount"] for i in items if i["side"] == "liability")), "total_liabilities is not the sum of the liability items")
    td = sum(i["amount"] for i in items if i["behavioural_class"] == "term-deposit")
    tdrr = o["assumptions"]["term_deposit_redemption_rate"]["value"]
    by: dict[tuple, dict] = {}
    for sc in o["scenarios"]:
        base = flows[sc["nmd_assumption"]]
        rep.need(close(sc["base_eve"], eve_of(base, r0)), f"{sc['calibration']}/{sc['nmd_assumption']}: base_eve does not recompute")
        sz = sc["shock_size"]
        losses = []
        for idx, s in enumerate(sc["shocks"]):
            tag = f"{sc['calibration']}/{sc['nmd_assumption']}/{s['shock']}"
            for got, want in zip(s["shape_bp"], shape_bp(s["shock"], sz["parallel_bp"], sz["short_bp"], sz["long_bp"])):
                if not math.isclose(got, want, abs_tol=5e-6):
                    rep.append(f"{tag}: shape_bp does not recompute from the shock size")
                    break
            floor = sc["floor"]
            bound = [k + 1 for k in range(19) if r0[k] + s["shape_bp"][k] / 1e4 < (min(floor, r0[k]) if floor is not None else -9)]
            rep.need(s["floor_bound_buckets"] == bound, f"{tag}: floor_bound_buckets do not match the floor")
            moved = td * min(1.0, GAMMA_U[idx] * tdrr)
            want_flows = list(base)
            want_flows[0] -= moved
            want_flows[3] += moved
            rep.need(all(close(a, b) for a, b in zip(s["net_cash_flows"], want_flows)), f"{tag}: net_cash_flows are not the base flows with the term-deposit overlay")
            rates = [post_rate(a, d, floor) for a, d in zip(r0, s["shape_bp"])]
            rep.need(close(s["eve"], eve_of(s["net_cash_flows"], rates)), f"{tag}: eve does not recompute")
            rep.need(close(s["delta_eve"], sc["base_eve"] - s["eve"] + s["kao"]), f"{tag}: delta_eve is not base - eve + kao")
            rep.need(close(s["delta_eve_share_tier1"] * sc["outlier"]["tier1"], s["delta_eve"], rel=1e-7, tol=1e-2), f"{tag}: delta_eve_share_tier1 is not delta_eve / tier1")
            if s["shock"] in ("parallel-up", "parallel-down"):
                want = sum(base[k] * (r0[k] - rates[k]) * (1 - MIDPOINTS[k]) for k in range(6))
                rep.need(close(s["delta_nii"], want), f"{tag}: delta_nii does not recompute")
            losses.append(max(0.0, s["delta_eve"]))
        rep.need(close(sc["eve_risk_measure"], max(losses)), f"{sc['calibration']}/{sc['nmd_assumption']}: eve_risk_measure is not the maximum positive loss")
        worst = max(sc["shocks"], key=lambda x: x["delta_eve"])["shock"] if max(losses) > 0 else None
        rep.need(sc["worst_shock"] == worst, f"{sc['calibration']}/{sc['nmd_assumption']}: worst_shock is not the shock of the maximum")
        ot = sc["outlier"]
        rep.need(close(ot["eve_risk_measure"], sc["eve_risk_measure"]), "outlier eve_risk_measure differs from the scenario's")
        rep.need(math.isclose(ot["ratio"], ot["eve_risk_measure"] / ot["tier1"], rel_tol=1e-6, abs_tol=1e-9), "outlier ratio is not the measure over Tier 1")
        rep.need(ot["breached"] == (ot["ratio"] > 0.15), "outlier breached does not follow the 15 percent threshold")
        by[(sc["calibration"], sc["nmd_assumption"])] = {x["shock"]: x["delta_eve"] for x in sc["shocks"]}
    for row in o["behavioural_comparison"]:
        k = row["calibration"], row["shock"]
        rep.need(close(row["delta_eve_behavioural"], by[(k[0], "behavioural")][k[1]]) and close(row["delta_eve_contractual"], by[(k[0], "contractual")][k[1]]),
                 f"behavioural_comparison {k} does not match the scenarios")
        rep.need(close(row["difference"], row["delta_eve_behavioural"] - row["delta_eve_contractual"]), f"behavioural_comparison {k}: difference is not behavioural - contractual")
    for lad in o["ladder"]:
        n = lad["nmd_assumption"]
        assets, liabs = [0.0] * 19, [0.0] * 19
        for it in items:
            for b, v in enumerate(dense(it["cash_flows"][n])):
                if it["side"] == "asset":
                    assets[b] += v
                else:
                    liabs[b] += -v
        for b, row in enumerate(lad["repricing_gap"]):
            rep.need(close(row["assets"], assets[b]) and close(row["liabilities"], liabs[b]) and close(row["gap"], assets[b] - liabs[b]), f"ladder {n}: gap row {b + 1} does not recompute")
        rep.need(close(lad["delta_nii_gap_100bp_up"], -sum((assets[k] - liabs[k]) * 0.01 * (1 - MIDPOINTS[k]) for k in range(6))), f"ladder {n}: delta_nii_gap does not recompute")
        dg = lad["duration_gap"]
        rep.need(math.isclose(dg["duration_gap_years"], dg["asset_duration_years"] - dg["liability_value"] / dg["asset_value"] * dg["liability_duration_years"], abs_tol=1e-6), f"ladder {n}: duration gap is not D_A - L/A D_L")
        rep.need(close(dg["equity_change_100bp_up"], -dg["duration_gap_years"] * dg["asset_value"] * 0.01), f"ladder {n}: equity change is not -DGAP x A x 0.01")
    # rung 5: the dynamic NII under the base path and the 2024 USD parallel size, rung 6: EaR and EVaR
    sc0 = o["scenarios"][0]
    par = sc0["shock_size"]["parallel_bp"]
    check_dynamic(o["dynamic_nii"], r0[1], par, sc0["floor"], rep, "c14 dynamic_nii", o["assumptions"]["deposit_beta"]["value"])
    base_nii = o["dynamic_nii"]["scenarios"][0]["total"]
    check_ear_evar(o["ear_evar"], base_nii, sc0["base_eve"], o["dynamic_nii"]["horizon_months"], rep, "c14")
    oos = o["out_of_sample"]
    if oos["applicable"]:
        rep.need(close(oos["projected_delta_nii"], o["dynamic_nii"]["scenarios"][1]["delta_vs_base"]), "out_of_sample projected_delta_nii is not the parallel-up delta of the dynamic NII")
        rep.need(math.isclose(oos["relative_error"], abs(oos["projected_delta_nii"] - oos["realised_delta_nii"]) / abs(oos["realised_delta_nii"]), rel_tol=1e-6, abs_tol=1e-9), "out_of_sample relative_error does not recompute")
    return list(rep)


def check_c14_models(doc: dict) -> list[str]:
    rep = Report()
    f = doc["fit"]
    for m in f["nmd_models"]:
        w = [t["weight"] for t in m["tranches"]]
        rep.need(math.isclose(sum(w), 1.0, abs_tol=1e-9) and math.isclose(m["weights_sum"], 1.0, abs_tol=1e-9), "replicating weights do not sum to one")
        rep.need(math.isclose(m["weighted_average_maturity_years"], sum(t["weight"] * t["maturity_years"] / 2 for t in m["tranches"]), abs_tol=1e-6),
                 "weighted_average_maturity_years is not sum w m / 2")
        for win in m["stability"]:
            rep.need(len(win["weights"]) == len(m["tranches"]) and math.isclose(sum(win["weights"]), 1.0, abs_tol=1e-9), "window weights do not sum to one")
            rep.need(math.isclose(win["weighted_average_maturity_years"], sum(x * t["maturity_years"] / 2 for x, t in zip(win["weights"], m["tranches"])), abs_tol=1e-6),
                     "window weighted_average_maturity_years is not sum w m / 2")
            rep.need(win["window_start"] < win["window_end"], "a window ends before it starts")
    for c in f["nmd_parameter_changes"]:
        rep.need(c["from_date"] < c["to_date"], "a parameter change goes backwards in time")
        rep.need(c["flagged"] == (c["from_value"] != c["to_value"] and c["limit_breach_in_window"]), f"{c['parameter']}: flagged does not follow change and breach")
    return list(rep)


# ------------------------------------------------------------------------------------------------ C15


def check_c15(doc: dict) -> list[str]:
    rep = Report()
    o = doc["outputs"]
    uf = o["ur_currency"]["uf_value"]
    legs = {leg["leg"]: leg for leg in o["legs"]}
    state = o["offset_rule"]["state"]
    rep.need(doc["variant_id"] == "fixture-" + o["variant"]["id"] or not doc["variant_id"].startswith("fixture-"), "variant_id differs from variant.id")
    rep.need(o["balance_sheet_month"] == o["curves_month"] == o["as_of"][:7], "balance sheet, curves and as_of are not the same month")
    rep.need(o["curves"]["clp"]["month"] == o["curves"]["ur"]["month"] == o["curves_month"], "a curve is not of the curves_month")
    rep.need(o["ur_currency"]["uf_date"] == o["as_of"], "uf_date is not as_of")
    all_items = [i for leg in o["legs"] for i in leg["items"]]
    check_nmd_segments(o, [i for i in all_items if i["behavioural_class"].startswith("nmd")], rep, "c15")
    base: dict[str, list[float]] = {}
    for name, leg in legs.items():
        conv = uf if name == "UR" else 1.0
        base[name] = [v * conv for v in dense([fl for it in leg["items"] for fl in it["cash_flows"]])]
        rep.need(close(leg["net_position"], sum((1 if i["side"] == "asset" else -1) * i["amount"] for i in leg["items"])), f"{name}: net_position is not assets - liabilities")
        rep.need(close(leg["assets_total"], sum(i["amount"] for i in leg["items"] if i["side"] == "asset")), f"{name}: assets_total is not the sum of the asset items")
        rep.need(close(leg["liabilities_total"], sum(i["amount"] for i in leg["items"] if i["side"] == "liability")), f"{name}: liabilities_total is not the sum of the liability items")
        for it in leg["items"]:
            side = 1 if it["side"] == "asset" else -1
            rep.need(close(sum(dense(it["cash_flows"])), side * it["amount"]), f"{name}: item {it['item_id']} flows do not sum to its amount")
    rates = {"CLP": o["curves"]["clp"]["zero_rates_at_midpoints"], "UR": o["curves"]["ur"]["zero_rates_at_midpoints"]}
    floors = {"CLP": o["floors"]["other_floor"], "UR": o["floors"]["ur_floor"]}
    sizes = {s["currency"]: s for s in o["eve_shock_sizes"]}

    def pair_ok(pair: dict, d_clp: float, d_ur: float, tag: str) -> None:
        rep.need(close(pair["delta_clp"], d_clp) and close(pair["delta_ur"], d_ur), f"{tag}: pair deltas differ from the legs")
        rep.need(pair["opposite_signs"] == (d_clp * d_ur < 0), f"{tag}: opposite_signs is wrong")
        rep.need(close(pair["with_offset"], cmf_pair(d_clp, d_ur, True)), f"{tag}: with_offset is not the Annex 1 offset rule")
        rep.need(close(pair["without_offset"], cmf_pair(d_clp, d_ur, False)), f"{tag}: without_offset is not the sum of the positive parts")
        rep.need(close(pair["used"], pair["without_offset"] if state == "off" else pair["with_offset"]), f"{tag}: used does not follow the offset state {state}")

    base_eve = {"CLP": o["eve"]["base_eve_clp"], "UR": o["eve"]["base_eve_ur"]}
    for name in base:
        rep.need(close(base_eve[name], eve_of(base[name], rates[name])), f"{name}: base EVE does not recompute")
    totals = []
    for row in o["eve"]["rows"]:
        d = {}
        for name, res in (("CLP", row["clp"]), ("UR", row["ur"])):
            tag = f"eve/{row['shock']}/{name}"
            sz = sizes["CLP" if name == "CLP" else "CLF"]
            for got, want in zip(res["shape_bp"], shape_bp(row["shock"], sz["parallel_bp"], sz["short_bp"], sz["long_bp"])):
                if not math.isclose(got, want, abs_tol=5e-6):
                    rep.append(f"{tag}: shape_bp does not recompute from the Annex 1 size")
                    break
            r0 = rates[name]
            bound = [k + 1 for k in range(19) if r0[k] + res["shape_bp"][k] / 1e4 < min(floors[name], r0[k])]
            rep.need(res["floor_bound_buckets"] == bound, f"{tag}: floor_bound_buckets do not match the floor")
            rr = [post_rate(a, x, floors[name]) for a, x in zip(r0, res["shape_bp"])]
            rep.need(close(res["eve"], eve_of(res["net_cash_flows"], rr)), f"{tag}: eve does not recompute")
            rep.need(close(res["delta_eve"], base_eve[name] - res["eve"] + res["kao"]), f"{tag}: delta_eve is not base - eve + kao")
            d[name] = res["delta_eve"]
        pair_ok(row["pair"], d["CLP"], d["UR"], f"eve/{row['shock']}")
        rep.need(close(row["total_delta_eve"], row["pair"]["used"]), f"eve/{row['shock']}: total_delta_eve is not the pair used")
        totals.append(row["total_delta_eve"])
    rep.need(close(o["eve"]["delta_eve"], max(totals)), "eve.delta_eve is not the maximum over the six shocks")
    rep.need(o["eve"]["worst_shock"] == SHOCKS[totals.index(max(totals))], "eve.worst_shock is not the shock of the maximum")
    pairs = []
    for row in o["nii"]["rows"]:
        d = {}
        for name, res in (("CLP", row["clp"]), ("UR", row["ur"])):
            tag = f"nii/{row['shock']}/{name}"
            bp = 300.0 if row["shock"] == "parallel-up" else -300.0
            rep.need(res["shock_bp"] == bp, f"{tag}: shock_bp is not the 300 bp parallel shock")
            r0 = rates[name]
            rr = [post_rate(r0[k], bp, floors[name]) for k in range(6)]
            rep.need(res["floor_bound_buckets"] == [k + 1 for k in range(6) if r0[k] + bp / 1e4 < min(floors[name], r0[k])], f"{tag}: floor_bound_buckets do not match the floor")
            rep.need(all(close(a, b) for a, b in zip(res["cash_flows"], base[name][:6])), f"{tag}: cash_flows are not the first six base flows")
            rep.need(close(res["delta_nii"], sum(base[name][k] * (r0[k] - rr[k]) * (1 - MIDPOINTS[k]) for k in range(6))), f"{tag}: delta_nii does not recompute")
            d[name] = res["delta_nii"]
        pair_ok(row["pair"], d["CLP"], d["UR"], f"nii/{row['shock']}")
        pairs.append(row["pair"]["used"])
    ic, n = o["indexation_charge"], o["nii"]
    pn = legs["UR"]["net_position"] * uf
    rep.need(close(ic["pn_ur"], pn), "indexation_charge.pn_ur is not the net UF position x the UF value")
    rep.need(math.isclose(ic["net_position_uf_units"] * uf, ic["pn_ur"], rel_tol=1e-9, abs_tol=1e-3), "net_position_uf_units x uf_value differs from pn_ur")
    rep.need(close(ic["abs_pn_ur"], abs(ic["pn_ur"])), "abs_pn_ur is not |pn_ur|")
    rep.need(close(ic["charge"], 0.025 * abs(pn)), "the indexation charge is not 2.5 percent of |PN_UR|")
    rep.need(close(n["indexation_charge"], ic["charge"]), "nii.indexation_charge is not the charge")
    rep.need(close(n["max_pair"], max(pairs)), "nii.max_pair is not the maximum pair")
    rep.need(close(n["delta_nii"], max(pairs) + 0.025 * abs(pn)), "delta_nii is not the maximum pair plus the indexation charge")
    cpi = o["cpi_scenario"]
    if cpi is not None:
        rep.need(close(cpi["effect"], -pn * cpi["surprise_pp"] / 100), "cpi_scenario.effect is not -pn_ur x surprise / 100")
    th = o["thresholds"]
    got = {t["id"]: t for t in th["tests"]}
    rep.need(close(got["nii-tier1"]["measure"], n["delta_nii"]) and close(got["eve-tier1"]["measure"], o["eve"]["delta_eve"]) and close(got["nii-margin"]["measure"], n["delta_nii"]), "a threshold test measure is not the document's measure")
    rep.need(close(got["nii-tier1"]["base"], th["tier1"]) and close(got["eve-tier1"]["base"], th["tier1"]) and close(got["nii-margin"]["base"], th["net_interest_and_indexation_margin_12m"]), "a threshold test base is not Tier 1 or the margin")
    for t in th["tests"]:
        rep.need(math.isclose(t["ratio"], t["measure"] / t["base"], rel_tol=1e-6), f"{t['id']}: ratio is not measure / base")
        rep.need(t["breached"] == (t["ratio"] > t["threshold"]), f"{t['id']}: breached does not follow the threshold")
    rep.need(th["prioritised"] == any(t["breached"] for t in th["tests"]), "prioritised is not 'any test breached'")
    rep.need(close(o["eve"]["delta_eve_share_tier1"] * th["tier1"], o["eve"]["delta_eve"], rel=1e-7, tol=1e-2), "eve share of Tier 1 does not recompute")
    for e in o["floors"]["effects"]:
        rep.need(close(e["effect"], e["delta_with_floor"] - e["delta_without_floor"]), "a floor effect is not with - without")
        row = next(r for r in (o["eve"]["rows"] if e["measure"] == "delta-eve" else o["nii"]["rows"]) if r["shock"] == e["shock"])
        res = row["clp"] if e["leg"] == "CLP" else row["ur"]
        r0 = rates[e["leg"]]
        if e["measure"] == "delta-eve":
            nofloor = [r0[k] + res["shape_bp"][k] / 1e4 for k in range(19)]
            rep.need(close(e["delta_with_floor"], res["delta_eve"]), "a floor effect's delta_with_floor is not the leg's delta EVE")
            rep.need(close(e["delta_without_floor"], base_eve[e["leg"]] - eve_of(res["net_cash_flows"], nofloor) + res["kao"]), "a floor effect's delta_without_floor does not recompute")
        else:
            rep.need(close(e["delta_with_floor"], res["delta_nii"]), "a floor effect's delta_with_floor is not the leg's delta NII")
            rep.need(close(e["delta_without_floor"], sum(base[e["leg"]][k] * (-res["shock_bp"] / 1e4) * (1 - MIDPOINTS[k]) for k in range(6))), "a floor effect's delta_without_floor does not recompute")
        rep.need(e["buckets_floored"] == len(res["floor_bound_buckets"]), "buckets_floored differs from the leg's floor_bound_buckets")
    # the distances to the floors: per leg and shock the lowest unfloored post-shock rate, its bucket, the distance, and where a floor binds
    dist = o["floors"]["distances"]
    want_keys = [(leg, m, sh["shock"]) for leg in ("CLP", "UR") for m, rows in (("delta-eve", o["eve"]["rows"]), ("delta-nii", o["nii"]["rows"])) for sh in rows]
    rep.need([(d["leg"], d["measure"], d["shock"]) for d in dist] == want_keys, "floors.distances are not one row per leg, measure and shock in order")
    for d in dist:
        key = "clp" if d["leg"] == "CLP" else "ur"
        row = next((r for r in (o["eve"]["rows"] if d["measure"] == "delta-eve" else o["nii"]["rows"]) if r["shock"] == d["shock"]), None)
        if row is None:
            continue
        n = 19 if d["measure"] == "delta-eve" else 6
        shape = row[key]["shape_bp"] if d["measure"] == "delta-eve" else [row[key]["shock_bp"]] * 19
        free = [rates[d["leg"]][k] + shape[k] / 1e4 for k in range(n)]
        k = min(range(n), key=lambda i: (free[i], i))
        tag = f"floors.distances/{d['leg']}/{d['measure']}/{d['shock']}"
        rep.need(close(d["lowest_rate"], free[k], rel=0, tol=1e-8) and d["bucket"] == k + 1, f"{tag}: the lowest rate or its bucket does not recompute")
        rep.need(close(d["floor"], floors[d["leg"]], rel=0, tol=1e-12), f"{tag}: the floor is not the leg's floor")
        rep.need(close(d["distance_bp"], (d["lowest_rate"] - d["floor"]) * 1e4, rel=0, tol=1e-4), f"{tag}: distance_bp is not (lowest_rate - floor) x 10 000")
        rep.need(d["binds"] == (d["distance_bp"] <= 0), f"{tag}: binds does not hold exactly when the distance is at most zero")
    rep.need(bool(o["floors"]["effects"]) == any(d["binds"] for d in dist), "floors.effects is not non-empty exactly when a distance binds")
    rep.need(o["calibration_month"] <= o["balance_sheet_month"], "calibration_month is after the balance sheet month")
    dn = o["dynamic_nii"]
    for dl in dn["legs"]:
        name = dl["leg"]
        check_dynamic({**dn, "items": dl["items"], "scenarios": dl["scenarios"]}, rates[name][1], 300, floors[name], rep, f"c15 dynamic_nii/{name}")
    ears = {e["leg"]: e for e in o["ear_evar"]}
    rep.need(sorted(ears) == ["CLP", "UR"] and len(o["ear_evar"]) == 2, "c15 ear_evar is not one block per leg")
    for dl in dn["legs"]:
        name = dl["leg"]
        if name in ears:
            check_ear_evar(ears[name], dl["scenarios"][0]["total"], o["eve"]["base_eve_clp" if name == "CLP" else "base_eve_ur"],
                           dn["horizon_months"], rep, f"c15 ear_evar/{name}")
    return list(rep)


def check_c15_models(doc: dict) -> list[str]:
    rep = Report()
    for m in doc["fit"]["nmd_models"]:
        rep.need(math.isclose(sum(t["weight"] for t in m["tranches"]), 1.0, abs_tol=1e-9), "replicating weights do not sum to one")
        rep.need(math.isclose(m["weighted_average_maturity_years"], sum(t["weight"] * t["maturity_years"] / 2 for t in m["tranches"]), abs_tol=1e-6),
                 "weighted_average_maturity_years is not sum w m / 2")
        for win in m["stability"]:
            rep.need(math.isclose(win["weighted_average_maturity_years"], sum(x * t["maturity_years"] / 2 for x, t in zip(win["weights"], m["tranches"])), abs_tol=1e-6),
                     "window weighted_average_maturity_years is not sum w m / 2")
    return list(rep)


def check_document(doc: dict) -> list[str]:
    """The producer-side check a bake calls on every C14 or C15 document it writes."""
    case = doc.get("case_id")
    is_variant = doc.get("schema") == "contraste.case/v1"
    if case == "C14":
        return check_c14(doc) if is_variant else check_c14_models(doc)
    if case == "C15":
        return check_c15(doc) if is_variant else check_c15_models(doc)
    return [f"not a C14 or C15 document: case_id {case!r}"]
