"""The Hull-White closed forms of the engine against QuantLib 1.44, on the committed curve and on a seeded parameter grid, and the
size of a planted defect that the relative gate of 1e-6 detects.

    python manuscripts/reconciliation-against-reference-engines/experiments/exp_closedforms.py [--out results_closedforms.json]

The engine functions are ``riskvalidation.ccr.hw1f.bond_option`` (the European option on a discount bond) and
``hw1f.swaption_jamshidian`` (the European swaption by Jamshidian's decomposition); the references are QuantLib's
``HullWhite.discountBondOption`` and ``JamshidianSwaptionEngine``. The curve is the zero curve of the committed C12 documents
(US Treasury, 30 September 2025), linear in the zero rate, continuously compounded.

* Part 1 repeats the four cases of the product's reconciliation (bond call, bond put, payer and receiver swaption) with the
  relative difference at full precision (the committed document rounds the statistic).
* Part 2 draws ``--cases`` parameter sets with a fixed seed (mean reversion, volatility, option expiry, bond or swap maturity,
  strike or fixed rate) and reports the distribution of the relative difference.
* Part 3 plants a relative error delta in the engine's volatility and reports the relative difference to QuantLib's price at the
  true volatility, with the elasticity of the price to volatility, to give the smallest volatility error that the gate sees.
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np
import QuantLib as ql

import common as cm

from riskvalidation.ccr import hw1f

HERE = pathlib.Path(__file__).resolve().parent
GATE = 1e-6


class Reference:
    """QuantLib's curve, handle and index for one set of tenors and zero rates."""

    def __init__(self, tenors: np.ndarray, zeros: np.ndarray) -> None:
        self.ref = ql.Date(1, 9, 2027)
        ql.Settings.instance().evaluationDate = self.ref
        self.dc = ql.Thirty360(ql.Thirty360.BondBasis)
        months = [int(round(t * 12)) for t in tenors]
        dates = [self.ref] + [self.ref + ql.Period(m, ql.Months) for m in months]
        curve = ql.ZeroCurve(dates, [float(zeros[0])] + [float(z) for z in zeros], self.dc, ql.NullCalendar(), ql.Linear(), ql.Continuous)
        curve.enableExtrapolation()
        self.curve = curve
        self.handle = ql.YieldTermStructureHandle(curve)
        self.index = ql.IborIndex("C12", ql.Period(6, ql.Months), 0, ql.USDCurrency(), ql.NullCalendar(), ql.Unadjusted, False, self.dc, self.handle)
        self.p0, self.forward = hw1f.curve_functions(zeros, tenors)

    def bond_option(self, call: bool, strike: float, expiry: float, bond: float, a: float, sigma: float) -> tuple[float, float]:
        model = ql.HullWhite(self.handle, a, sigma)
        q = model.discountBondOption(ql.Option.Call if call else ql.Option.Put, strike, expiry, bond)
        e = hw1f.bond_option(call, strike, expiry, bond, a, sigma, self.p0)
        return float(e), float(q)

    def swaption(self, payer: bool, start_m: int, end_m: int, rate: float, a: float, sigma: float, engine_sigma: float | None = None) -> tuple[float, float]:
        notional = 1_000_000.0
        start, end = self.ref + ql.Period(start_m, ql.Months), self.ref + ql.Period(end_m, ql.Months)
        sched = ql.Schedule(start, end, ql.Period(6, ql.Months), ql.NullCalendar(), ql.Unadjusted, ql.Unadjusted, ql.DateGeneration.Forward, False)
        swap = ql.VanillaSwap(ql.VanillaSwap.Payer if payer else ql.VanillaSwap.Receiver, notional, sched, rate, self.dc, sched, self.index, 0.0, self.dc)
        swaption = ql.Swaption(swap, ql.EuropeanExercise(start))
        model = ql.HullWhite(self.handle, a, sigma)
        swaption.setPricingEngine(ql.JamshidianSwaptionEngine(model, self.handle))
        q = swaption.NPV()
        n_pay = (end_m - start_m) // 6
        times = start_m / 12.0 + np.arange(1, n_pay + 1) * 0.5
        amounts = np.full(n_pay, notional * rate * 0.5)
        amounts[-1] += notional
        e = hw1f.swaption_jamshidian(payer, start_m / 12.0, times, amounts, a, sigma if engine_sigma is None else engine_sigma, self.p0, self.forward, nominal=notional)
        return float(e), float(q)


def rel(e: float, q: float) -> float:
    return abs(e - q) / abs(q)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results_closedforms.json"))
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--cases", type=int, default=300)
    args = ap.parse_args()

    inp = cm.C12Inputs("netting-set")
    r = Reference(inp.tenors, inp.zeros)
    a, sigma = inp.a, inp.sigma

    # ---------------------------------------------------------------- part 1: the four committed cases
    part1 = {}
    for name, call, strike in (("bond_call", True, 0.85), ("bond_put", False, 0.93)):
        e, q = r.bond_option(call, strike, 2.0, 5.0, a, sigma)
        part1[name] = {"engine": e, "quantlib": q, "relative_difference": rel(e, q)}
    for name, payer in (("swaption_payer", True), ("swaption_receiver", False)):
        e, q = r.swaption(payer, 24, 60, 0.04, a, sigma)
        part1[name] = {"engine": e, "quantlib": q, "relative_difference": rel(e, q)}
    # the same four cases at the pipeline's mean reversion and volatility are those of the committed document; the document's
    # statistic is rounded, so the full-precision value is recorded here

    # ---------------------------------------------------------------- part 2: a seeded grid
    rng = np.random.default_rng(args.seed)
    rows = []
    for _ in range(args.cases):
        aa = float(rng.uniform(0.02, 0.50))
        ss = float(rng.uniform(0.003, 0.02))
        kind = "bond" if rng.random() < 0.5 else "swaption"
        if kind == "bond":
            expiry = float(rng.choice([0.5, 1.0, 2.0, 3.0, 5.0]))
            mat = expiry + float(rng.choice([1.0, 2.0, 3.0, 5.0]))
            p_exp = float(np.exp(-inp.zeros[np.searchsorted(inp.tenors, mat)] * mat)) if mat <= inp.tenors[-1] else 0.8
            strike = float(p_exp / float(r.p0(np.array(expiry))) * rng.uniform(0.9, 1.1))
            call = bool(rng.random() < 0.5)
            e, q = r.bond_option(call, strike, expiry, mat, aa, ss)
            rows.append({"kind": "bond_call" if call else "bond_put", "a": aa, "sigma": ss, "expiry": expiry, "maturity": mat, "strike": strike,
                         "engine": e, "quantlib": q, "relative_difference": rel(e, q)})
        else:
            start_m = int(rng.choice([6, 12, 24, 36, 60]))
            end_m = start_m + int(rng.choice([12, 24, 36, 60]))
            rate = float(rng.uniform(0.02, 0.06))
            payer = bool(rng.random() < 0.5)
            e, q = r.swaption(payer, start_m, end_m, rate, aa, ss)
            if abs(q) < 1e-3:       # a deep out-of-the-money swaption has no relative scale
                continue
            rows.append({"kind": "swaption_payer" if payer else "swaption_receiver", "a": aa, "sigma": ss, "start_months": start_m, "end_months": end_m,
                         "rate": rate, "engine": e, "quantlib": q, "relative_difference": rel(e, q)})
    rd = np.array([x["relative_difference"] for x in rows])
    worst = sorted(rows, key=lambda x: -x["relative_difference"])[:5]
    part2 = {"rows": [{"kind": x["kind"], "relative_difference": x["relative_difference"], "abs_difference": abs(x["engine"] - x["quantlib"])} for x in rows],
             "cases": len(rows), "seed": args.seed, "max_relative_difference": float(rd.max()), "median_relative_difference": float(np.median(rd)),
             "within_gate": int(np.sum(rd <= GATE)), "worst": worst,
             "by_kind": {k: {"n": sum(x["kind"] == k for x in rows), "max": max(x["relative_difference"] for x in rows if x["kind"] == k)}
                         for k in sorted({x["kind"] for x in rows})}}

    # ---------------------------------------------------------------- part 3: a planted volatility error
    plant = []
    for delta in (1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2):
        e, q = r.swaption(True, 24, 60, 0.04, a, sigma, engine_sigma=sigma * (1 + delta))
        eb = hw1f.bond_option(True, 0.85, 2.0, 5.0, a, sigma * (1 + delta), r.p0)
        _, qb = r.bond_option(True, 0.85, 2.0, 5.0, a, sigma)
        plant.append({"delta": delta, "swaption_relative_difference": rel(e, q), "bond_call_relative_difference": rel(float(eb), qb),
                      "detected_swaption": bool(rel(e, q) > GATE), "detected_bond_call": bool(rel(float(eb), qb) > GATE)})
    h = 1e-4
    ep, qq = r.swaption(True, 24, 60, 0.04, a, sigma, engine_sigma=sigma * (1 + h))
    em, _ = r.swaption(True, 24, 60, 0.04, a, sigma, engine_sigma=sigma * (1 - h))
    elasticity_sw = (np.log(ep) - np.log(em)) / (np.log(1 + h) - np.log(1 - h))
    bp = hw1f.bond_option(True, 0.85, 2.0, 5.0, a, sigma * (1 + h), r.p0)
    bm = hw1f.bond_option(True, 0.85, 2.0, 5.0, a, sigma * (1 - h), r.p0)
    elasticity_bd = (np.log(bp) - np.log(bm)) / (np.log(1 + h) - np.log(1 - h))
    out = {"quantlib_version": ql.__version__, "gate": GATE, "curve_date": inp.curve_date, "a": a, "sigma": sigma, "part1": part1, "part2": part2,
           "part3": {"plants": plant, "elasticity_swaption": float(elasticity_sw), "elasticity_bond_call": float(elasticity_bd),
                     "smallest_detected_sigma_error_swaption": GATE / float(elasticity_sw), "smallest_detected_sigma_error_bond_call": GATE / float(elasticity_bd)}}
    cm.write(pathlib.Path(args.out), out)
    print(part1)
    print({k: v for k, v in part2.items() if k != "worst"})
    print(out["part3"])


if __name__ == "__main__":
    main()
