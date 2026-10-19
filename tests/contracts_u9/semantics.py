"""The cross-field checks of the C12 and regulatory-calculators documents, as importable functions (as U10's semantics.py).

JSON Schema cannot hold these: they recompute numbers and compare dates. The C12 bake calls ``check_c12`` on every document it
writes and the regulatory parity bake calls ``check_regulatory`` (a non-empty list is a refusal to publish); the producer tests
run them over every committed document. The formulas are written from dossier 01 (E.1, E.2, D.2), the addendum (R5, R7, R9) and
dossier 05 C.1 and C.2.

Each function returns a list of messages, empty when the document conforms.
"""
from __future__ import annotations

import datetime as dt
import math

REL = 1e-6


def close(a: float, b: float, rel: float = REL, abs_: float = 1e-9) -> bool:
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


# ------------------------------------------------------------------------------------------------ formulas


def supervisory_duration(start: float, end: float) -> float:
    """CRE52.34 (dossier 01 E.2)."""
    return (math.exp(-0.05 * start) - math.exp(-0.05 * end)) / 0.05


def maturity_factor(maturity_years: float, mpor_business_days: int | None) -> float:
    """CRE52.48 unmargined and CRE52.52 margined (dossier 01 E.2): 250 business days to the year."""
    if mpor_business_days is None:
        return math.sqrt(min(maturity_years, 1.0) / 1.0)
    return 1.5 * math.sqrt(mpor_business_days / 250.0)


def ir_bucket(end_years: float) -> str:
    """CRE52.57: B1 under one year, B2 one to five years, B3 over five."""
    return "B1" if end_years < 1 else ("B2" if end_years <= 5 else "B3")


def ir_effective_notional(d1: float, d2: float, d3: float, offset: bool = True) -> float:
    """CRE52.57 offset and no-offset formulas (dossier 01 E.2)."""
    if not offset:
        return abs(d1) + abs(d2) + abs(d3)
    return math.sqrt(d1 * d1 + d2 * d2 + d3 * d3 + 1.4 * d1 * d2 + 1.4 * d2 * d3 + 0.6 * d1 * d3)


def multiplier(v_minus_c: float, addon: float) -> float:
    """CRE52.23: floor 5 percent."""
    if addon <= 0:
        return 1.0
    return min(1.0, 0.05 + 0.95 * math.exp(v_minus_c / (2 * 0.95 * addon)))


def rc_unmargined(v: float, c: float) -> float:
    return max(v - c, 0.0)


def rc_margined(v: float, c: float, th: float, mta: float, nica: float) -> float:
    return max(v - c, th + mta - nica, 0.0)


def ba_cva_df(m: float) -> float:
    return (1 - math.exp(-0.05 * m)) / (0.05 * m)


def scva(rw: float, ead: float, m: float, df: float) -> float:
    """MAR50.15 with alpha 1.4, one netting set per counterparty."""
    return rw * m * ead * df / 1.4


def k_reduced(scvas: list[float], rho: float = 0.5) -> float:
    return math.sqrt((rho * sum(scvas)) ** 2 + (1 - rho * rho) * sum(x * x for x in scvas))


def scenario_rho(rho: float, scenario: str) -> float:
    """MAR21.6: medium prescribed, high min(1.25 rho, 1), low max(2 rho - 1, 0.75 rho)."""
    if scenario == "medium":
        return rho
    if scenario == "high":
        return min(1.25 * rho, 1.0)
    return max(2 * rho - 1.0, 0.75 * rho)


def sbm_bucket(ws: list[float], corr: list[list[float]], scenario: str) -> float:
    """MAR21.4 within-bucket aggregation, K_b = sqrt(max(0, sum WS^2 + sum_{k != l} rho WS WS))."""
    total = 0.0
    for k, a in enumerate(ws):
        for l, b in enumerate(ws):
            total += a * a if k == l else scenario_rho(corr[k][l], scenario) * a * b
    return math.sqrt(max(0.0, total))


def anderson_darling_w2(pits: list[float]) -> float:
    """R5: W^2 = -n - sum (2k - 1) / n [ln F(x_k) + ln(1 - F(x_{n+1-k}))] on the sorted PITs."""
    x = sorted(pits)
    n = len(x)
    return -n - sum((2 * k - 1) / n * (math.log(x[k - 1]) + math.log(1 - x[n - k])) for k in range(1, n + 1))


def effective_ee(ee: list[float]) -> list[float]:
    """CRE53.12 equation 2 (the running maximum of EE)."""
    out, run = [], 0.0
    for v in ee:
        run = max(run, v)
        out.append(run)
    return out


def eepe(grid: list[float], eff: list[float]) -> float:
    """CRE53.13 equation 3: weighted by the time steps over the first year or to maturity."""
    total, prev = 0.0, 0.0
    for t, v in zip(grid, eff):
        if t > 1.0 + 1e-12:
            break
        total += v * (t - prev)
        prev = t
    return total / prev if prev else 0.0


# ------------------------------------------------------------------------------------------------ the C12 checker


def check_c12(doc: dict) -> list[str]:
    msgs: list[str] = []
    o = doc["outputs"]
    grid = o["exposure"]["time_grid_years"]
    n = len(grid)
    if grid != sorted(set(grid)):
        msgs.append("time grid not strictly increasing")
    for name in ("ee", "ee_discounted", "ene", "ene_discounted", "pfe", "effective_ee"):
        pr = o["exposure"][name]
        if len(pr["values"]) != n or len(pr["mc_se"]) != n:
            msgs.append(f"exposure.{name}: values and mc_se must have one entry per grid point")
    ee = o["exposure"]["ee"]["values"]
    eff = o["exposure"]["effective_ee"]["values"]
    if any(b < a - 1e-9 for a, b in zip(eff, eff[1:])):
        msgs.append("effective EE is not non-decreasing")
    if any(e + 1e-9 < v for e, v in zip(eff, ee)):
        msgs.append("effective EE below EE")
    epe_v = o["exposure"]["eepe"]["amount"]
    if epe_v > max(ee) + 1e-9:
        msgs.append("EEPE above the maximum of EE")
    if not close(epe_v, eepe(grid, eff)):
        msgs.append("EEPE is not the time-weighted average of the effective EE over the first year")
    nb = o["netting_benefit"]
    for k in range(n):
        s = sum(t["ee"]["values"][k] for t in nb["per_trade_ee"])
        if not close(s, nb["sum_of_single_trade_ee"]["values"][k]):
            msgs.append(f"netting_benefit: sum of single-trade EE differs at point {k}")
        if nb["netted_ee"]["values"][k] > s + 1e-9:
            msgs.append(f"netting_benefit: netted EE above the sum of single-trade EE at point {k}")
        if not close(nb["benefit"]["values"][k], s - nb["netted_ee"]["values"][k]):
            msgs.append(f"netting_benefit: benefit is not sum minus netted at point {k}")
    if len(nb["per_trade_ee"]) != len(o["book"]["trades"]):
        msgs.append("netting_benefit has not one profile per trade")
    if o["exposure"]["basis"] == "uncollateralised" and not all(close(a, b) for a, b in zip(ee, nb["netted_ee"]["values"])):
        msgs.append("an uncollateralised EE must equal the netted EE")
    cva = o["cva_dva"]
    pairs = list(zip([0.0] + grid[:-1], grid))
    if [(b["t_start"], b["t_end"]) for b in cva["buckets"]] != pairs:
        msgs.append("cva buckets are not the grid intervals")
    tc = td = 0.0
    for b in cva["buckets"]:
        tc += b["cva_term"]
        td += b["dva_term"]
        if not close(b["cva_term"], b["pd_counterparty"] * cva["lgd"] * b["epe_discounted"]):
            msgs.append("cva term is not PD x LGD x discounted EPE")
        if not close(b["dva_term"], b["pd_bank"] * cva["bank_lgd"] * b["ene_discounted"]):
            msgs.append("dva term is not PD x LGD x discounted ENE")
        if b["t_end"] in grid and not close(b["epe_discounted"], o["exposure"]["ee_discounted"]["values"][grid.index(b["t_end"])]):
            msgs.append("cva bucket EPE is not the discounted EE at the bucket end")
    if not close(tc, cva["cva"]["amount"]):
        msgs.append("CVA is not the sum of its terms")
    if not close(td, cva["dva"]["amount"]):
        msgs.append("DVA is not the sum of its terms")
    if not close(cva["bcva"]["amount"], cva["cva"]["amount"] - cva["dva"]["amount"]):
        msgs.append("BCVA is not CVA minus DVA")
    if any(s["spread"] == 0 for s in cva["buckets"]) and cva["cva"]["amount"] != 0:
        msgs.append("CVA with a zero spread must be zero")
    w = o["wrong_way_risk"]
    if w is not None:
        zero = [p for p in w["sweep"] if p["b"] == 0]
        if len(zero) != 1 or not zero[0]["independent"] or any(p["independent"] for p in w["sweep"] if p["b"] != 0):
            msgs.append("wrong-way sweep: the independent point is b = 0 only and exactly once")
        elif zero[0]["cva"]["amount"] != w["independent_cva"]["amount"] or w["independent_cva"]["amount"] != cva["cva"]["amount"]:
            msgs.append("wrong-way risk with b = 0 must equal the independent CVA exactly")
        if [p["b"] for p in w["sweep"]] != w["b_grid"]:
            msgs.append("wrong-way sweep is not the b grid in order")
    sa = o["sa_ccr"]
    trades = o["book"]["trades"]
    if sorted(t["trade_id"] for t in sa["trades"]) != sorted(t["trade_id"] for t in trades):
        msgs.append("sa_ccr trades are not the book's trades")
    margined = sa["margined"]
    if margined != (sa["mpor_business_days"] is not None):
        msgs.append("sa_ccr: margined iff an MPoR is stated")
    sets: dict[str, list[float]] = {}
    for t in sa["trades"]:
        bt = next((x for x in trades if x["trade_id"] == t["trade_id"]), None)
        if bt is None:
            continue
        sd = supervisory_duration(t["start_years"], t["end_years"])
        if not close(t["supervisory_duration"], sd):
            msgs.append(f"{t['trade_id']}: supervisory duration")
        if not close(t["adjusted_notional"]["amount"], bt["notional"]["amount"] * sd):
            msgs.append(f"{t['trade_id']}: adjusted notional")
        if t["delta"] != ("1" if bt["side"] == "payer" else "-1"):
            msgs.append(f"{t['trade_id']}: supervisory delta of a {bt['side']} swap")
        if not close(t["maturity_factor"], maturity_factor(t["end_years"], sa["mpor_business_days"])):
            msgs.append(f"{t['trade_id']}: maturity factor")
        if t["bucket"] != ir_bucket(t["end_years"]):
            msgs.append(f"{t['trade_id']}: maturity bucket")
        if not close(t["effective_notional"], t["adjusted_notional"]["amount"] * float(t["delta"]) * t["maturity_factor"]):
            msgs.append(f"{t['trade_id']}: effective notional")
        sets.setdefault(t["hedging_set"], [0.0, 0.0, 0.0])["B1 B2 B3".split().index(t["bucket"])] += t["effective_notional"]
    addon_ir = 0.0
    for hs in sa["hedging_sets"]:
        d = sets.get(hs["hedging_set"], [0.0] * 3)
        if not all(close(a, b) for a, b in zip(d, (hs["d_b1"], hs["d_b2"], hs["d_b3"]))):
            msgs.append(f"{hs['hedging_set']}: bucket effective notionals")
        if not close(hs["effective_notional"], ir_effective_notional(*d, offset=hs["offset"])):
            msgs.append(f"{hs['hedging_set']}: hedging-set effective notional")
        if not close(hs["addon"], 0.005 * hs["effective_notional"]):
            msgs.append(f"{hs['hedging_set']}: add-on is not 0.5 percent of the effective notional")
        addon_ir += hs["addon"]
    ac = sa["addon_by_class"]
    if not close(ac["interest_rate"], addon_ir):
        msgs.append("sa_ccr: interest rate add-on is not the sum of the hedging sets")
    if not close(sa["addon_aggregate"]["amount"], sum(ac.values())):
        msgs.append("sa_ccr: aggregate add-on is not the sum of the five classes")
    v, c = sa["v"]["amount"], sa["c"]["amount"]
    rc = rc_margined(v, c, sa["th"]["amount"], sa["mta"]["amount"], sa["nica"]["amount"]) if margined else rc_unmargined(v, c)
    if not close(sa["rc"]["amount"], rc):
        msgs.append("sa_ccr: RC")
    if not close(sa["multiplier"], multiplier(v - c, sa["addon_aggregate"]["amount"])):
        msgs.append("sa_ccr: multiplier")
    if not close(sa["pfe"]["amount"], sa["multiplier"] * sa["addon_aggregate"]["amount"]):
        msgs.append("sa_ccr: PFE")
    if not close(sa["ead"]["amount"], 1.4 * (sa["rc"]["amount"] + sa["pfe"]["amount"])):
        msgs.append("sa_ccr: EAD")
    ba = o["ba_cva"]
    sc = []
    for cp in ba["counterparties"]:
        if not close(cp["discount_factor"], ba_cva_df(cp["m_years"])):
            msgs.append("ba_cva: discount factor")
        if not close(cp["scva"], scva(cp["risk_weight"], cp["ead"]["amount"], cp["m_years"], cp["discount_factor"])):
            msgs.append("ba_cva: SCVA")
        sc.append(cp["scva"])
    if not close(ba["k_reduced"], k_reduced(sc)):
        msgs.append("ba_cva: K_reduced")
    if not close(ba["capital"]["amount"], 0.65 * ba["k_reduced"]):
        msgs.append("ba_cva: capital")
    rg = o["regulatory_comparison"]
    if not close(rg["alpha_times_eepe"]["amount"], 1.4 * epe_v):
        msgs.append("regulatory: alpha times EEPE")
    if rg["sa_ccr_ead"]["amount"] != sa["ead"]["amount"]:
        msgs.append("regulatory: the SA-CCR EAD differs from the sa_ccr block")
    if not close(rg["sa_ccr_over_alpha_eepe"], sa["ead"]["amount"] / rg["alpha_times_eepe"]["amount"]):
        msgs.append("regulatory: ratio")
    if rg["stressed"]["spread_rose"] != (rg["stressed"]["hqm_spread_peak"] > rg["stressed"]["hqm_spread_start"]):
        msgs.append("regulatory: spread_rose disagrees with the spreads")
    if rg["stressed"]["window_start"] >= rg["stressed"]["window_end"]:
        msgs.append("regulatory: the stress window is not ordered")
    g = o["girr"]
    if [s["scenario"] for s in g["scenarios"]] != ["low", "medium", "high"]:
        msgs.append("girr: scenarios must be low, medium, high in order")
    if g["delta_charge"]["amount"] > g["delta_charge_undivided"]["amount"] + 1e-9:
        msgs.append("girr: the divided charge exceeds the undivided one")
    if not close(g["delta_charge"]["amount"], max(s["k_b"] for s in g["scenarios"])):
        msgs.append("girr: the charge is not the maximum over the three scenarios")
    bt = o["backtest"]
    for blk in [bt["book_horizons"], bt["risk_factor"]["horizons"]]:
        for h in blk:
            if h["n"] != len(h["pits"]):
                msgs.append(f"backtest {h['horizon']}: n is not the number of PITs")
            if not close(h["w2"], anderson_darling_w2(h["pits"])):
                msgs.append(f"backtest {h['horizon']}: W^2 does not recompute from the PITs")
            if h["reject_at_5pct"] != (h["w2"] > h["critical_simulated"]["p05"]):
                msgs.append(f"backtest {h['horizon']}: the decision disagrees with the simulated critical value")
            for e in h["exceedances"]:
                if not close(e["expected"], h["n"] * (1 - e["quantile"])):
                    msgs.append(f"backtest {h['horizon']}: expected exceedances")
    cal = o["calibration_used"]
    if not (cal["sample_start"] < cal["sample_end"] < cal["backtest_date"]):
        msgs.append("calibration: the sample window must end before the backtest date (look-ahead)")
    if cal["backtest_date"] != o["curve"]["curve_date"]:
        msgs.append("calibration: backtest_date is not the curve date")
    yrs = (dt.date.fromisoformat(cal["sample_end"]) - dt.date.fromisoformat(cal["sample_start"])).days / 365.25
    if yrs + 0.01 < cal["history_years"] or cal["history_years"] < 3:
        msgs.append("calibration: less than three years of history")
    cv = o["curve"]
    present = [p["tenor_years"] for p in cv["points"]]
    if present != cv["tenors_present"] or set(present) & set(cv["tenors_absent"]):
        msgs.append("curve: tenors_present must be the points' tenors and disjoint from tenors_absent")
    cs = {s["case"]: s for s in o["calibration_sensitivity"]}
    if sorted(cs) != sorted(["base", "a-plus-1se", "a-minus-1se", "sigma-plus-1se", "sigma-minus-1se"]):
        msgs.append("sensitivity: the five cases")
    elif not (close(cs["a-plus-1se"]["a"], cal["a"] + cal["a_se"]) and close(cs["sigma-minus-1se"]["sigma"], cal["sigma"] - cal["sigma_se"])):
        msgs.append("sensitivity: a and sigma are not moved by one standard error")
    ore = o["ore_reconciliation"]
    if ore["status"] == "reconciled":
        for a in ore["agreement"]:
            if a["within_two_se"] != (abs(a["difference"]) <= 2 * a["combined_se"]):
                msgs.append("ore: within_two_se disagrees with the difference")
        if ore["all_within_two_se"] != all(a["within_two_se"] for a in ore["agreement"]):
            msgs.append("ore: all_within_two_se")
        if len(ore["agreement"]) != n or len(ore["ore_ee"]["values"]) != n:
            msgs.append("ore: one agreement per grid point")
    for t in doc["tests"]:
        if not t["test_id"].startswith("ccr."):
            msgs.append("tests: a C12 test id starts with ccr.")
    return msgs


def check_c12_models(doc: dict) -> list[str]:
    msgs: list[str] = []
    cals = doc["fit"]["calibrations"]
    dates = [c["backtest_date"] for c in cals]
    if dates != sorted(set(dates)):
        msgs.append("calibration dates are not unique and increasing")
    for c in cals:
        if not (c["sample_start"] < c["sample_end"] < c["backtest_date"]):
            msgs.append(f"{c['backtest_date']}: the sample window ends on or after the backtest date (look-ahead)")
    girr = doc["fit"]["girr_parameters"]
    corr, ten = girr["correlation_percent"], girr["tenors_years"]
    for k in range(10):
        for l in range(10):
            want = 100.0 if k == l else max(100 * math.exp(-0.03 * abs(ten[k] - ten[l]) / min(ten[k], ten[l])), 40.0)
            if abs(corr[k][l] - want) > 0.051 or corr[k][l] != corr[l][k]:
                msgs.append(f"girr correlation ({ten[k]}, {ten[l]}) differs from MAR21.46 Table 2")
    return msgs


# ------------------------------------------------------------------------------------------ the regulatory checker


def check_regulatory(doc: dict) -> list[str]:
    msgs: list[str] = []
    ex = {e["id"]: e for e in doc["official_examples"]}
    iv = {e["id"]: e for e in doc["invariant_cases"]}

    def val(e: dict, group: str, name: str) -> float:
        return next(v["value"] for v in e[group] if v["name"] == name)

    for k in [f"cre99-netting-set-{i}" for i in range(1, 6)]:
        e = ex.get(k)
        if e is None:
            msgs.append(f"missing official example {k}")
            continue
        rc, mult, addon = val(e, "outputs", "rc"), val(e, "outputs", "multiplier"), val(e, "outputs", "addon_aggregate")
        ead = 1.4 * (rc + mult * addon)
        pub = next(p for p in e["published"] if p["name"] == "ead")["value"]
        if abs(ead - pub) > 1.0:
            msgs.append(f"{k}: EAD recomputes to {ead:.3f}, published {pub}")
        if k in ("cre99-netting-set-2", "cre99-netting-set-5"):
            vc = val(e, "inputs", "v_minus_c")
            if abs(multiplier(vc, addon) - mult) > 5e-4:
                msgs.append(f"{k}: multiplier recomputes to {multiplier(vc, addon):.4f}")
    e1 = ex.get("cre99-netting-set-1")
    if e1 and not close(val(e1, "outputs", "addon_ir"), 0.005 * (val(e1, "outputs", "en_usd") + val(e1, "outputs", "en_eur"))):
        msgs.append("cre99-netting-set-1: AddOn IR is not 0.5 percent of the two effective notionals")
    f = ex.get("rbc20-13-output-floor")
    if f:
        want = max(val(f, "inputs", "rwa_nominated"), val(f, "inputs", "floor_factor") * val(f, "inputs", "rwa_sa_only"))
        if not close(val(f, "outputs", "rwa_floored"), want):
            msgs.append("output floor: not max(nominated, f x SA)")
    c = ex.get("rbc20-13-output-floor-capped")
    if c:
        pre = val(c, "inputs", "rwa_nominated")
        want = min(max(pre, val(c, "inputs", "floor_factor") * val(c, "inputs", "rwa_sa_only")), pre * (1 + val(c, "inputs", "cap_share")))
        if not close(val(c, "outputs", "rwa_floored"), want):
            msgs.append("output floor with the RBC90.2 cap")
    b = iv.get("ba-cva-rho-one")
    if b and not close(val(b, "outputs", "k_reduced"), sum(v["value"] for v in b["inputs"] if v["name"].startswith("scva"))):
        msgs.append("BA-CVA with rho = 1 must give the sum of SCVA")
    for g in doc["cre20_grid"]:
        if not (0 <= g["risk_weight"] <= 4):
            msgs.append("cre20 grid: risk weight out of range")
    return msgs
