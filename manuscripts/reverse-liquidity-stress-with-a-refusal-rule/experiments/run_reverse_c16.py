"""Experiment 2: the reverse stress on the committed bases of case C16, its sensitivity to the case conventions, and the labelled run.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/experiments/run_reverse_c16.py

Rebuilds the three bases (LiST Adverse, LiST Extreme, the 2023 fast run) from the committed documents of ``data/derived/C16`` and calls the
engine ``riskvalidation`` 1.1.0 on them. (R1 to R3, R5) the solved multipliers and the refusal against ``reverse-stress.json``; (H7) the
implicit-function derivative of the threshold with respect to the capacity against repeated solves; (H8, H9) the multiplier under the
haircut band, the monetisation schedules, the mapping band of the uninsured balance, the uninsured share and the target; (R4, H10 to H12) the
labelled run of the 2023 rows, the calibration rules and the multiplier of the labelled run. Writes ``results_reverse_c16.json``.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
import time

import numpy as np
from scipy import optimize

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import core  # noqa: E402
from riskvalidation.liquidity import cbc as ecbc  # noqa: E402
from riskvalidation.liquidity import reverse as ereverse  # noqa: E402
from riskvalidation.liquidity import runoff, scenarios  # noqa: E402
from riskvalidation.liquidity.scenarios import Scenario, ScenarioSegment  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
BASES = ("list-adverse", "list-extreme", "fast-run")
TARGET = 30


def sp_day(r) -> int | None:
    return None if r.survives else int(r.day)


def solve_block(scn: Scenario, cbc: np.ndarray, target: int) -> dict:
    with core._Count() as cnt:
        r = ereverse.solve_multiplier(scn, cbc, target)
    if r.status != "solved":
        return {"status": "refused", "reason": r.reason, "multiplier": None, "evals": cnt.n}
    jb = r.survival_just_below
    return {"status": "solved", "multiplier": float(r.multiplier), "sp_at": int(r.survival_at_multiplier), "sp_just_below": sp_day(jb),
            "evals": cnt.n}


def time_solve(scn: Scenario, cbc: np.ndarray, target: int, reps: int = 50) -> float:
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        ereverse.solve_multiplier(scn, cbc, target)
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts) * 1e6)


def scaled_scenario(scn: Scenario, rates: np.ndarray) -> Scenario:
    segs = tuple(ScenarioSegment(s.segment_id, s.liquidity_class, s.opening, rates[j]) for j, s in enumerate(scn.segments))
    return Scenario(scn.family, scn.phase, scn.horizon, segs)


def window_derivative(scn: Scenario, cbc: np.ndarray, m0: float, target: int) -> dict:
    """The implicit-function derivative of the threshold with respect to a level shift of the capacity: ``1 / X'_{t0}(m0)`` where ``X_t`` is the
    cumulative outflow of the scaled scenario and ``t0`` the day at which the window function reaches its minimum."""
    opening, rates = scn.opening, scn.rates()
    nlp = core.nlp_np(opening, rates, cbc, m0)
    t0 = int(np.argmin(nlp[:target]))  # zero-based index of the day
    x = 0.0
    for j in range(rates.shape[0]):
        r = rates[j, : t0 + 1]
        if np.any(m0 * r >= 1.0):
            continue
        p = float(np.prod(1.0 - m0 * r))
        x += opening[j] * p * float(np.sum(r / (1.0 - m0 * r)))
    return {"t0_day": t0 + 1, "capacity_at_t0": float(cbc[t0]), "dX_dm": x, "dm_dcapacity": 1.0 / x}


def main() -> int:
    conv = core.doc("models-svb-liquidity")["fit"]["conventions"]
    committed = {b["base_id"]: b for b in core.doc("reverse-stress")["outputs"]["bases"]}
    out: dict = {"bases": {}, "band": {}, "labelled_run": {}}
    state = {}
    # ------------------------------------------------------------------------------------------ R1 to R3, R5
    for base in BASES:
        scn, cbc, lad, d = core.c16_base(base)
        state[base] = (scn, cbc, lad, d)
        sol = solve_block(scn, cbc, TARGET)
        com = committed[base]
        cap = ereverse.max_multiplier(scn)
        grid = np.array([m for m in conv["runoff_multiplier_grid"]["values"] if m <= cap])
        curve = [sp_day(r) for r in ereverse.survival_vs_multiplier(scn, cbc, grid)]
        com_curve = [c["survival"].get("day") for c in com["curve"]]
        base_sp = sp_day(eladder_sp(scn, cbc))
        entry = {
            "engine": sol, "committed": com["solved"], "cap": float(cap), "base_sp": base_sp, "horizon": scn.horizon,
            "curve_multipliers": [float(x) for x in grid], "curve_sp": curve, "curve_equals_committed": curve == com_curve,
            "time_us_median": time_solve(scn, cbc, TARGET),
            "opening_total": float(scn.opening.sum()),
        }
        if sol["status"] == "solved":
            entry["equals_committed"] = bool(com["solved"]["status"] == "solved" and abs(sol["multiplier"] - com["solved"]["multiplier"]) < 1e-12
                                              and sol["sp_at"] == com["solved"]["survival_at_multiplier"])
            entry["hyperbolic_rule"] = {"value": base_sp / TARGET, "rel_error": abs(base_sp / TARGET - sol["multiplier"]) / sol["multiplier"]}
        else:
            entry["equals_committed"] = bool(com["solved"]["status"] == "refused")
        raw = ereverse.solve_multiplier(scn, np.array(lad["cbc_total"]), TARGET)
        entry["raw_capacity_multiplier"] = float(raw.multiplier) if raw.status == "solved" else None
        out["bases"][base] = entry

    # ---------------------------------------------------------------------------------------------- H7 derivative
    out["derivative"] = {}
    for base in ("list-adverse", "list-extreme"):
        scn, cbc, lad, d = state[base]
        m0 = out["bases"][base]["engine"]["multiplier"]
        dd = window_derivative(scn, cbc, m0, TARGET)
        eps = 1e-3 * dd["capacity_at_t0"]
        up = ereverse.solve_multiplier(scn, cbc + eps, TARGET).multiplier
        dn = ereverse.solve_multiplier(scn, cbc - eps, TARGET).multiplier
        fd = (up - dn) / (2 * eps)
        dd.update({"finite_difference": float(fd), "rel_difference": abs(dd["dm_dcapacity"] - fd) / abs(fd), "eps": eps,
                   "elasticity": dd["dm_dcapacity"] * dd["capacity_at_t0"] / m0, "multiplier_up": float(up), "multiplier_down": float(dn)})
        out["derivative"][base] = dd

    # ------------------------------------------------------------------------------- H8 and H9: the convention band
    hb = float(conv["cbc_haircut_band"]["value"])
    sched = {k: [(int(p["day"]), float(p["cumulative_share"])) for p in v] for k, v in
             (("central", conv["monetisation_schedule"]["points"]), *((b["id"], b["points"]) for b in conv["monetisation_schedule"]["sensitivity_band"]))}
    for base in ("list-adverse", "list-extreme"):
        scn, cbc, lad, d = state[base]
        classes = d["outputs"]["cbc"]["classes"]
        h = scn.horizon

        def eff(shift: float, mon: str) -> np.ndarray:
            cl = {c["class_id"]: (c["value_used"], c["encumbered"], min(1.0, max(0.0, c["haircut"]["value"] + shift))) for c in classes}
            stack = ecbc.cbc_stack(cl, sched[mon], h)
            return core.effective_cbc(lad, sum(stack.values(), np.zeros(h)))

        central = eff(0.0, "central")
        assert np.allclose(central, cbc, rtol=1e-12, atol=1e-6), "the rebuilt central capacity differs from the committed ladder"
        grid_rows = []
        for shift_name, shift in (("low", -hb), ("central", 0.0), ("high", hb)):
            for mon in ("immediate", "central", "slow"):
                r = solve_block(scn, eff(shift, mon), TARGET)
                grid_rows.append({"haircut": shift_name, "monetisation": mon, **r})
        out["band"][base] = {"haircut_x_monetisation": grid_rows}
        ms = [r["multiplier"] for r in grid_rows if r["multiplier"] is not None]
        m_c = out["bases"][base]["engine"]["multiplier"]
        out["band"][base]["joint_min"], out["band"][base]["joint_max"] = min(ms), max(ms)
        out["band"][base]["joint_max_rel_deviation"] = max(abs(x - m_c) / m_c for x in ms)
        out["band"][base]["all_solved"] = len(ms) == len(grid_rows)
        # one at a time
        one = []
        for shift_name, shift in (("low", -hb), ("high", hb)):
            r = solve_block(scn, eff(shift, "central"), TARGET)
            one.append({"factor": f"haircut {shift_name}", **r})
        for mon in ("immediate", "slow"):
            r = solve_block(scn, eff(0.0, mon), TARGET)
            one.append({"factor": f"monetisation {mon}", **r})
        out["band"][base]["one_at_a_time"] = one
        # mapping band of the uninsured balance
        lst = scenarios.list_scenario("extreme" if base == "list-extreme" else "adverse")
        rates = scn.rates().copy()
        ci = [s.segment_id for s in scn.segments].index("non-operational-corporate")
        mapping = []
        for label, cls in (("operational deposits", "operational"), ("non-financial corporates (central)", "non-operational-non-financial-corporates"),
                           ("other legal entities", "non-operational-other-financial")):
            rr = rates.copy()
            rr[ci] = lst.class_rate(cls)
            sc2 = scaled_scenario(scn, rr)
            r = solve_block(sc2, cbc, TARGET)
            nl = core.nlp_np(sc2.opening, rr, cbc, 1.0)
            mapping.append({"mapping": label, "class_rate": float(lst.class_rate(cls)), "base_sp": None if math.isinf(core.sp_np(nl)) else int(core.sp_np(nl)), **r})
        out["band"][base]["mapping"] = mapping
        # uninsured share grid
        shares = [float(x) for x in conv["uninsured_share_grid"]["values"]]
        segs = scn.segments
        ins_i = [s.segment_id for s in segs].index("retail-insured")
        pairs = scenarios.uninsured_share_grid(segs[ins_i].opening, segs[ci].opening, shares)
        rows = []
        for sh, (ins, unin) in zip(shares, pairs):
            op = [s.opening for s in segs]
            op[ins_i], op[ci] = ins, unin
            sc2 = Scenario(scn.family, scn.phase, scn.horizon, tuple(ScenarioSegment(s.segment_id, s.liquidity_class, op[j], s.daily_rates)
                                                                      for j, s in enumerate(segs)))
            r = solve_block(sc2, cbc, TARGET)
            nl = core.nlp_np(sc2.opening, sc2.rates(), cbc, 1.0)
            rows.append({"uninsured_share": sh, "base_sp": None if math.isinf(core.sp_np(nl)) else int(core.sp_np(nl)), **r})
        out["band"][base]["uninsured_share"] = rows
        # the multiplier as a function of the target
        tcurve = []
        for t in range(1, scn.horizon):
            r = solve_block(scn, cbc, t)
            tcurve.append({"target": t, "status": r["status"], "multiplier": r["multiplier"], "reason": r.get("reason")})
        out["band"][base]["by_target"] = tcurve
        ts = [x["multiplier"] for x in tcurve if x["multiplier"] is not None]
        out["band"][base]["by_target_monotone"] = bool(all(a >= b - 1e-12 for a, b in zip(ts, ts[1:])))
        out["band"][base]["by_target_solved_up_to"] = max(x["target"] for x in tcurve if x["status"] == "solved")

    # ------------------------------------------------------------------------------------- the labelled run (R4, H10 to H12)
    scn, cbc, lad, d = state["fast-run"]
    sc = d["outputs"]["scoring"]
    base_total = float(scn.opening.sum())
    out_matrix = scn.outflows()
    cum_share = np.cumsum(out_matrix.sum(axis=0)) / base_total
    scoring = {r["row_id"]: r for r in sc["table_a1_scoring"]}
    rows = []
    ratio_green, ratio_amber = float(conv["scoring_ratio_green"]["value"]), float(conv["scoring_ratio_amber"]["value"])

    def light(ratio: float) -> str:
        return "green" if ratio >= ratio_green else "amber" if ratio >= ratio_amber else "red"

    for rid, r in scoring.items():
        if r["modelled_share"] is None:
            rows.append({"row_id": rid, "bank": r["bank"], "year": r["year"], "days": r["horizon_days"], "observed": r["observed_share"], "role": r["role"],
                         "modelled": None, "ratio": None, "light": None, "equals_committed": True})
            continue
        mod = float(cum_share[r["horizon_days"] - 1])
        ratio = mod / r["observed_share"]
        rows.append({"row_id": rid, "bank": r["bank"], "year": r["year"], "days": r["horizon_days"], "observed": r["observed_share"], "role": r["role"],
                     "modelled": mod, "ratio": ratio, "light": light(ratio), "equals_committed": bool(abs(mod - r["modelled_share"]) < 1e-12)})
    out["labelled_run"]["rows"] = rows
    out["labelled_run"]["denominators"] = [{"id": x["id"], "realised_share": x["realised_share"], "modelled_share": x["modelled_share"], "ratio": x["ratio"],
                                             "light": x["light"]} for x in sc["denominators"]]
    out["labelled_run"]["svb_modelled_2d"] = float(cum_share[1])
    out["labelled_run"]["svb_ratio_2d"] = float(cum_share[1]) / 0.85
    # the calibration rules
    pre = [r for r in runoff.TABLE_A1 if r.year < 2023]
    ci = [s.segment_id for s in scn.segments].index("non-operational-corporate")
    rule_rows = []
    for rule in scenarios.FAST_RUN_RULES:
        fit = scenarios.fast_run_scenario(pre, rule, scored=True)
        rr = scn.rates().copy()
        rr[ci] = fit.daily_rate
        sc2 = scaled_scenario(scn, rr)
        cs = np.cumsum(sc2.outflows().sum(axis=0)) / base_total
        rule_rows.append({"rule": rule, "rate": float(fit.daily_rate), "modelled_2d": float(cs[1]), "ratio_2d": float(cs[1]) / 0.85, "light": light(float(cs[1]) / 0.85)})
    out["labelled_run"]["rules"] = rule_rows
    loo = []
    for i, r in enumerate(pre):
        rest = [x for j, x in enumerate(pre) if j != i]
        fit = scenarios.fast_run_scenario(rest, "maximum-implied-daily-rate", scored=True)
        loo.append({"left_out": r.bank, "rate": float(fit.daily_rate)})
    out["labelled_run"]["leave_one_out"] = loo
    out["labelled_run"]["implied_rates"] = {r.bank: float(runoff.daily_rate_from_cumulative(r.outflow_share, r.days)) for r in pre}
    # the multiplier of the labelled run: every segment's rate scaled until the model reproduces 85 percent in 2 days
    rates0 = scn.rates()
    cap_fast = ereverse.max_multiplier(scn)

    def share2(m: float) -> float:
        sc2 = scaled_scenario(scn, np.minimum(m * rates0, 1.0))
        return float((sc2.outflows()[:, :2].sum() / base_total))

    m_svb = float(optimize.brentq(lambda m: share2(m) - 0.85, 1.0, cap_fast, xtol=1e-12))
    sc_svb = scaled_scenario(scn, np.minimum(m_svb * rates0, 1.0))
    sp_svb = core.sp_np(core.nlp_np(sc_svb.opening, sc_svb.rates(), cbc, 1.0))
    by_t = {}
    for t in (1, 2, 3, 4, 5, 30):
        by_t[str(t)] = solve_block(scn, cbc, t)
    out["labelled_run"]["multiplier_of_labelled_run"] = m_svb
    out["labelled_run"]["share_2d_at_that_multiplier"] = share2(m_svb)
    out["labelled_run"]["sp_at_that_multiplier"] = None if math.isinf(sp_svb) else int(sp_svb)
    out["labelled_run"]["cap"] = float(cap_fast)
    out["labelled_run"]["reverse_by_target"] = by_t
    m2 = by_t["2"]["multiplier"]
    out["labelled_run"]["ratio_labelled_to_reverse_t2"] = m_svb / m2
    # cumulative share curves for the figure (days 1 to 5)
    def curve(m: float) -> list[float]:
        sc2 = scaled_scenario(scn, np.minimum(m * rates0, 1.0))
        return [float(x) for x in np.cumsum(sc2.outflows().sum(axis=0)) / base_total]

    out["labelled_run"]["curves"] = {"calibrated": curve(1.0), "reverse_t2": curve(m2), "labelled": curve(m_svb)}
    out["labelled_run"]["cbc_total_day"] = [float(x) for x in cbc]
    out["labelled_run"]["opening_total"] = base_total

    # ---------------------------------------------------------------------------------------------- hypotheses
    out["R"] = {
        "R1": out["bases"]["list-adverse"]["equals_committed"] and abs(out["bases"]["list-adverse"]["engine"]["multiplier"] - 2.118175) < 1e-12,
        "R2": out["bases"]["list-extreme"]["equals_committed"] and abs(out["bases"]["list-extreme"]["engine"]["multiplier"] - 1.383141) < 1e-12,
        "R3": out["bases"]["fast-run"]["equals_committed"] and out["bases"]["fast-run"]["engine"]["status"] == "refused",
        "R4": abs(out["labelled_run"]["svb_modelled_2d"] - 0.17083002185967083) < 1e-12,
        "R5": all(out["bases"][b]["engine"]["sp_at"] == TARGET and (out["bases"][b]["engine"]["sp_just_below"] or 10**9) > TARGET
                  for b in ("list-adverse", "list-extreme")),
    }
    out["H"] = {
        "H7": {b: out["derivative"][b]["rel_difference"] for b in out["derivative"]},
        "H7_held": all(out["derivative"][b]["rel_difference"] <= 0.01 for b in out["derivative"]),
        "H8_joint_max_rel_deviation": out["band"]["list-adverse"]["joint_max_rel_deviation"],
        "H8_held": out["band"]["list-adverse"]["joint_max_rel_deviation"] < 0.25,
        "H9_row": [r for r in out["band"]["list-adverse"]["mapping"] if r["mapping"] == "other legal entities"][0],
        "H9_held": [r for r in out["band"]["list-adverse"]["mapping"] if r["mapping"] == "other legal entities"][0]["status"] == "refused",
        "H10_ratio_2d": out["labelled_run"]["svb_ratio_2d"], "H10_held": out["labelled_run"]["svb_ratio_2d"] >= 0.5,
        "H11_ratio": out["labelled_run"]["ratio_labelled_to_reverse_t2"], "H11_held": out["labelled_run"]["ratio_labelled_to_reverse_t2"] >= 2.0,
        "H12_max_ratio_other_rules": max(r["ratio_2d"] for r in rule_rows if r["rule"] != "maximum-implied-daily-rate"),
        "H12_held": max(r["ratio_2d"] for r in rule_rows if r["rule"] != "maximum-implied-daily-rate") < 0.5,
    }
    (HERE / "results_reverse_c16.json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print("R:", out["R"])
    print("H:", {k: v for k, v in out["H"].items() if k.endswith("held")})
    return 0


def eladder_sp(scn: Scenario, cbc: np.ndarray):
    from riskvalidation.liquidity import ladder as eladder
    nlp = core.nlp_np(scn.opening, scn.rates(), cbc, 1.0)
    return eladder.survival_period(nlp)


if __name__ == "__main__":
    raise SystemExit(main())
