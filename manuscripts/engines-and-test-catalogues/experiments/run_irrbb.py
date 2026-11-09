"""Experiment 3: the IRRBB engine against the printed SRP31.92 example, against an independent transcription of the six shock shapes,
and against QuantLib on the committed C15 variants.

For every committed C15 variant, shock and currency leg, the net cash flows per time bucket and the shock shape in basis points are read
from the artifact; the engine's ``eve`` and the present value computed with ``QuantLib.InterestRate.discountFactor`` (continuous
compounding, Actual/365 time in years) are both compared with the EVE the artifact stores, and the shape in the artifact is compared
with the engine's ``shock_curve`` and with a transcription of SRP31.90 to SRP31.92 written here with ``math``.

    python manuscripts/engines-and-test-catalogues/experiments/run_irrbb.py
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import QuantLib as ql

import runstats
import riskvalidation
from riskvalidation.irrbb import eve_nii, shocks, slotting

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VARIANTS = ["long-uf", "short-uf", "floors-active", "offset-on-off", "clp-steepener", "cpi-surprise"]


def spec_shape(shock: str, par: float, short: float, long_: float, t: float, x: float = 4.0) -> float:
    """SRP31.90 to SRP31.92: alpha_short = exp(-t/x), |short| = short alpha, |long| = long (1 - alpha)."""
    a = math.exp(-t / x)
    s, lg = short * a, long_ * (1.0 - a)
    return {"parallel-up": par, "parallel-down": -par, "short-up": s, "short-down": -s,
            "steepener": -0.65 * s + 0.9 * lg, "flattener": 0.8 * s - 0.6 * lg}[shock]


def ql_eve(cf: np.ndarray, rates: np.ndarray, t: np.ndarray) -> float:
    total = 0.0
    for c, r, tt in zip(cf, rates, t):
        total += float(c) * ql.InterestRate(float(r), ql.Actual365Fixed(), ql.Continuous, ql.Annual).discountFactor(float(tt))
    return total


def worked_example() -> dict:
    t = np.array([3.5])
    a_short, _ = shocks.shock_scalars(t, 4.0)
    got = {"alpha_short": (float(a_short[0]), 0.417), "short-up": (float(shocks.shock_curve("short-up", 100, 100, 100, t)[0]), 41.7),
           "steepener": (float(shocks.shock_curve("steepener", 100, 100, 100, t)[0]), 25.4),
           "flattener": (float(shocks.shock_curve("flattener", 100, 100, 100, t)[0]), -1.6)}
    return {k: {"engine": v, "printed": p, "abs_dev": abs(v - p),
                "independent": (math.exp(-3.5 / 4.0) if k == "alpha_short" else spec_shape(k, 100, 100, 100, 3.5))}
            for k, (v, p) in got.items()}


def variants() -> dict:
    mid = slotting.bucket_grid().midpoints
    rows = []
    for name in VARIANTS:
        doc = json.loads((ROOT / "data" / "derived" / "C15" / f"{name}.json").read_text(encoding="utf-8"))["outputs"]
        sizes = {s["currency"]: s for s in doc["eve_shock_sizes"]}
        for leg, cur, curve in (("clp", "CLP", "clp"), ("ur", "CLF", "ur")):
            base_rates = np.asarray(doc["curves"][curve]["zero_rates_at_midpoints"], float)
            sz = sizes[cur]
            for r in doc["eve"]["rows"]:
                d = r[leg]
                shape = np.asarray(d["shape_bp"], float)
                cf = np.asarray(d["net_cash_flows"], float)
                rates = base_rates + shape / 1e4
                eng = eve_nii.eve(cf, rates, mid)
                qlv = ql_eve(cf, rates, mid)
                rec = shocks.shock_curve(r["shock"], sz["parallel_bp"], sz["short_bp"], sz["long_bp"], mid)
                spec = np.array([spec_shape(r["shock"], sz["parallel_bp"], sz["short_bp"], sz["long_bp"], float(t)) for t in mid])
                floor_bound = len(d["floor_bound_buckets"]) > 0
                rows.append({"variant": name, "leg": leg, "shock": r["shock"], "stored_eve": d["eve"], "engine_eve": eng, "ql_eve": qlv,
                             "rel_engine": abs(eng - d["eve"]) / max(abs(d["eve"]), 1.0),
                             "rel_ql": abs(qlv - d["eve"]) / max(abs(d["eve"]), 1.0),
                             "shape_max_abs_engine": float(np.abs(rec - shape).max()),
                             "shape_max_abs_independent": float(np.abs(spec - shape).max()),
                             "floor_bound": floor_bound})
        # the pair rule and the measure
        used = [r["pair"]["used"] for r in doc["eve"]["rows"]]
        again = [eve_nii.cmf_pair(r["pair"]["delta_clp"], r["pair"]["delta_ur"]) for r in doc["eve"]["rows"]]
        rows.append({"variant": name, "leg": "pair", "shock": "all", "pair_max_abs": float(np.abs(np.array(used) - np.array(again)).max()),
                     "measure_stored": doc["eve"]["delta_eve"], "measure_max_used": max(0.0, max(used))})
    legs = [r for r in rows if r["leg"] != "pair"]
    unbound = [r for r in legs if not r["floor_bound"]]
    pairs = [r for r in rows if r["leg"] == "pair"]
    return {"n_legs_shocks": len(legs), "n_unbound": len(unbound),
            "max_rel_engine": max(r["rel_engine"] for r in legs), "max_rel_ql": max(r["rel_ql"] for r in legs),
            "max_shape_engine": max(r["shape_max_abs_engine"] for r in unbound),
            "max_shape_independent": max(r["shape_max_abs_independent"] for r in unbound),
            "pair_max_abs": max(p["pair_max_abs"] for p in pairs),
            "measure_gap": max(abs(p["measure_stored"] - p["measure_max_used"]) for p in pairs),
            "n_variants": len(VARIANTS), "rows": rows}


def main() -> None:
    t0 = runstats.start()
    result = {"riskvalidation": riskvalidation.__version__, "quantlib": ql.__version__ if hasattr(ql, "__version__") else ql.QuantLib.__version__ if hasattr(ql, "QuantLib") else "unknown",
              "worked_example": worked_example(), "variants": variants()}
    result["run"] = runstats.stats(t0)
    (HERE / "results_irrbb.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result["worked_example"], indent=1))
    print({k: v for k, v in result["variants"].items() if k != "rows"})


if __name__ == "__main__":
    main()
