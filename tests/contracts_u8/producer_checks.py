"""The producer-side checks of the C11 and C13 documents: the rules a JSON Schema cannot state (a date comparison, an
array length against another field, a statistic recomputed from the series it summarises). Each function returns the list
of violations (empty when the document is sound) and runs on the fixtures and on every committed document of the case, so
a bake document that leaks, miscounts or contradicts itself is refused (review F8, F9, F14).

CI runs no pytest (ADR-0074), so these checks run in a local pytest run; U8-P1 and U8-P2 take ``pytest tests/contracts_u8``
green on their committed documents as an acceptance check.
"""
from __future__ import annotations

from datetime import date

import market_math as mm

GATES = ("market.kupiec_pof", "market.christoffersen_conditional_coverage", "market.acerbi_szekely")
WINDOWS = ["equity-2007-09", "equity-2020", "rates-2022", "fx-2008", "mixed-2023", "calm-2004-06"]
D1_SPAN = ("1995-01-01", "2003-12-31")
D2_DATES = {  # decision D2 of plans/contraste/units/U8-sizing.md
    "equity-2007-09": ("2007-07-02", "2009-06-30"), "equity-2020": ("2020-02-03", "2020-06-30"),
    "rates-2022": ("2022-01-03", "2022-12-30"), "fx-2008": ("2008-07-01", "2009-06-30"),
    "mixed-2023": ("2023-03-01", "2023-05-31"), "calm-2004-06": ("2004-01-02", "2006-12-29"),
}
DEFICIENCIES = ["none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment"]


def d(s: str) -> date:
    return date.fromisoformat(s)


def leakage_violations(o: dict) -> list[str]:
    """The leakage rule (SDD C11: strictly rolling, the forecast for day t uses data to t-1)."""
    g = o["grid"]
    n = len(g["dates"])
    found = []
    if not (len(g["estimation_start"]) == len(g["estimation_end"]) == n):
        return ["the estimation arrays do not align with the forecast dates"]
    for i in range(n):
        if not d(g["estimation_end"][i]) < d(g["dates"][i]):
            found.append(f"day {i}: forecast {g['dates'][i]} is not after its estimation end {g['estimation_end'][i]}")
        if not d(g["estimation_start"][i]) <= d(g["estimation_end"][i]):
            found.append(f"day {i}: the estimation window starts after it ends")
        if i and not (d(g["dates"][i]) > d(g["dates"][i - 1]) and d(g["estimation_end"][i]) >= d(g["estimation_end"][i - 1])):
            found.append(f"day {i}: dates or window ends go backwards")
    return found


def span_violations(o: dict) -> list[str]:
    """Decision D1: the span is 1995-01-01 to 2003-12-31, so it ends before the earliest test window (calm 2004-06)."""
    h, w = o["hyperparameters"]["fixed_on"], o["window"]
    found = []
    if (h["start"], h["end"]) != D1_SPAN:
        found.append(f"the span is {h['start']} to {h['end']}, not {D1_SPAN[0]} to {D1_SPAN[1]}")
    if not d(h["end"]) < date(2004, 1, 2):
        found.append(f"the span ends {h['end']}, not before the earliest test window (2004-01-02)")
    if not d(h["end"]) < d(w["start_date"]):
        found.append(f"the span ends {h['end']}, not before the window start {w['start_date']}")
    return found


def window_violations(w: dict) -> list[str]:
    want = D2_DATES.get(w["window_id"])
    if want is None or (w["start_date"], w["end_date"]) != want:
        return [f"{w['window_id']}: dates {w['start_date']} to {w['end_date']}, decision D2 says {want}"]
    return []


def _es_state(lv: dict) -> list[str]:
    nulls = [i for i, e in enumerate(lv["es"]) if e is None]
    st = lv["es_status"]
    if st == "forecast" and (nulls or lv["es_undefined_days"]):
        return ["es_status forecast with null or undefined days"]
    if st == "undefined-on-days" and (not nulls or nulls != lv["es_undefined_days"]):
        return ["es_status undefined-on-days does not match the null days"]
    if st == "not-forecast" and (len(nulls) != len(lv["es"]) or lv["es_undefined_days"]):
        return ["es_status not-forecast while es holds numbers"]
    return []


def c11_variant_violations(doc: dict) -> list[str]:
    o = doc["outputs"]
    v = leakage_violations(o) + span_violations(o) + window_violations(o["window"])
    g, w = o["grid"], o["window"]
    n = len(g["dates"])
    if n != w["n_forecast_days"]:
        v.append(f"n_forecast_days {w['n_forecast_days']} but {n} grid days")
    if doc["variant_id"].removeprefix("fixture-") != w["window_id"]:
        v.append(f"variant id {doc['variant_id']} does not carry the window {w['window_id']}")
    ds = o["data_status"]
    if ds["missing_days"]["count"] != len(ds["missing_days"]["dates"]) or set(g["dates"]) & set(ds["missing_days"]["dates"]):
        v.append("missing days are not counted or are in the grid")
    derived = any(c["source_class"] == "derived-only" for c in o["portfolio"]["components"])
    rl = g["realised_loss"]
    if (rl["status"] == "withheld-derived-only") != derived:
        v.append("the realised series is not withheld exactly when a component is derived-only")
    loss = rl["loss"]
    if loss is not None and len(loss) != n:
        v.append("the realised series is not as long as the grid")
    cmp = o["comparison"]
    if any(r["hac_lags"] != cmp["hac_lags"] for r in cmp["dm"]):
        v.append("a Diebold-Mariano row uses a lag count other than comparison.hac_lags")
    rows = {(t["test_id"], t["model_id"], t["segment"]): t for t in doc["tests"]}
    listed = set()
    for m in o["models"]:
        failed = set()
        for lv in m["by_level"]:
            a, name = lv["alpha"], f"{m['model_id']}@{lv['alpha']}"
            if not (len(lv["var"]) == len(lv["es"]) == n):
                v.append(f"{name}: forecast arrays are not as long as the grid")
                continue
            v += [f"{name}: {x}" for x in _es_state(lv)]
            for var, es in zip(lv["var"], lv["es"]):
                if es is not None and es < var:
                    v.append(f"{name}: ES below VaR")
                    break
            exc = lv["exceedance_days"]
            if exc != sorted(set(exc)) or any(not 0 <= i < n for i in exc) or lv["n_exceedances"] != len(exc) or lv["n_scored"] != n:
                v.append(f"{name}: exceedance indices or counts are inconsistent")
            if abs(lv["expected_exceedances"] - a * n) > 1e-6:
                v.append(f"{name}: expected exceedances is not alpha times n")
            if loss is not None:
                if [i for i in range(n) if loss[i] > lv["var"][i]] != exc:
                    v.append(f"{name}: exceedances do not recompute from the realised series")
                tick = sum(mm.tick_loss(loss[i], lv["var"][i], a) for i in range(n)) / n
                if abs(tick - lv["tick_loss_mean"]) > 1e-8:
                    v.append(f"{name}: tick loss mean does not recompute")
                fz = [mm.fz0_loss(loss[i], lv["var"][i], lv["es"][i], a) for i in range(n) if lv["es"][i] is not None]
                if lv["n_fz0"] != len(fz) or (fz and abs(sum(fz) / len(fz) - lv["fz0_mean"]) > 1e-8) or (not fz and lv["fz0_mean"] is not None):
                    v.append(f"{name}: FZ0 mean does not recompute")
            tl = lv["traffic_light"]
            if tl is not None:
                flags = [1 if i in set(exc) else 0 for i in range(n)]
                if n < 250:  # decision D3
                    if tl["final_zone"] != "not_evaluated":
                        v.append(f"{name}: fewer than 250 forecast days, the traffic light must be not_evaluated (D3)")
                else:
                    counts = mm.rolling_counts(flags, 250)
                    zs = [mm.traffic_zone(c) for c in counts]
                    if (tl["final_zone"] == "not_evaluated" or tl["n_windows"] != len(counts) or tl["max_rolling_exceedances"] != max(counts)
                            or tl["final_rolling_exceedances"] != counts[-1] or tl["final_zone"] != mm.traffic_zone(counts[-1])
                            or (tl["days_green"], tl["days_amber"], tl["days_red"]) != (zs.count("green"), zs.count("amber"), zs.count("red"))):
                        v.append(f"{name}: the traffic light does not recompute from the exceedance days")
            for tid in lv["test_ids"]:
                key = (tid, m["model_id"], f"alpha={a}")
                listed.add(key)
                if key not in rows:
                    v.append(f"{name}: test row {tid} is missing")
                elif tid in GATES and rows[key]["light"] == "red":
                    failed.add(tid)
        if set(m["failed_gates"]) != failed or m["eligible"] != (not failed):
            v.append(f"{m['model_id']}: eligible or failed_gates contradict the red gate rows")
    for key in rows:
        if key not in listed and key[1] is not None:
            v.append(f"test row {key} is listed by no level result")
    return v


def c11_models_violations(doc: dict) -> list[str]:
    fit = doc["fit"]
    v = []
    if [p["window_id"] for p in fit["windows"]] != WINDOWS:
        v.append("the windows are not the six of the SDD in order")
    for p in fit["windows"]:
        v += window_violations(p)
        if (p["fixed_on"]["start"], p["fixed_on"]["end"]) != D1_SPAN:
            v.append(f"{p['window_id']}: span is not the D1 span")
    rows = fit["traffic_light"]["rows"]
    if [r["exceptions"] for r in rows] != list(range(11)) or [r["frtb_multiplier"] for r in rows] != mm.FRTB_MULTIPLIER \
            or [r["us_multiplier"] for r in rows] != mm.US_MULTIPLIER or [r["zone"] for r in rows] != [mm.traffic_zone(i) for i in range(11)] \
            or [r["cumulative_probability_pct"] for r in rows] != [round(100 * mm.binom_cdf(i, 250, 0.01), 2) for i in range(11)]:
        v.append("the traffic-light table is not MAR32.9 Table 1")
    return v


def c13_variant_violations(doc: dict) -> list[str]:
    o = doc["outputs"]
    v = []
    did = o["known_deficiency"]["deficiency_id"]
    if doc["variant_id"].removeprefix("fixture-") != did:
        v.append(f"variant id {doc['variant_id']} does not carry the deficiency {did}")
    ex = o["example"]
    if len(ex["hpl"]) != 250 or len(ex["rtpl"]) != 250:
        v.append("the example is not 250 days")
    else:
        rho, ks = mm.spearman(ex["hpl"], ex["rtpl"]), mm.ks_statistic(ex["hpl"], ex["rtpl"])
        if abs(ex["spearman"] - rho) > 1e-6 or abs(ex["ks"] - ks) > 1e-6:
            v.append("the example statistics do not recompute")
        if ex["zone"] != mm.pla_zone(rho, ks):
            v.append(f"the example zone {ex['zone']} contradicts MAR32.42 ({mm.pla_zone(rho, ks)})")
    n = o["generator"]["n_replications"]
    z = o["pla"]["zones"]
    if z["n"] != n or any(sum(z[k].values()) != n for k in ("overall", "spearman", "ks")):
        v.append("the zone counts do not close on the replications")
    if z["overall"]["red"] < max(z["spearman"]["red"], z["ks"]["red"]) or z["overall"]["green"] > min(z["spearman"]["green"], z["ks"]["green"]):
        v.append("the joint zone counts contradict the single-statistic counts")
    for dk in o["desk_backtest"]:
        if dk["n_within_limit"] + dk["n_over_limit"] != n or abs(dk["share_over_limit"] - dk["n_over_limit"] / n) > 1e-9:
            v.append("the desk counts do not close")
    det = o["detection"]
    if det["n_replications"] != n or det["n_amber_or_red"] != z["overall"]["amber"] + z["overall"]["red"] or det["n_red"] != z["overall"]["red"]:
        v.append("the detection counts contradict the zone counts")
    return v


def c13_models_violations(doc: dict) -> list[str]:
    fit = doc["fit"]
    v = []
    if [p["deficiency_id"] for p in fit["deficiencies"]] != DEFICIENCIES or [p["planted"] for p in fit["deficiencies"]] != [False] + [True] * 5:
        v.append("the deficiencies are not the six of the SDD with their planted flags")
    if {(x["alpha"], x["limit_exceptions"]) for x in fit["desk_limits"]} != {(0.025, 30), (0.01, 12)}:
        v.append("the desk limits are not MAR32.18 to MAR32.19")
    return v
