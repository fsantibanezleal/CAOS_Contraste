"""E2. The band rebuilt by the engine from the committed marginal grids (predictions H2 and H3), its variation over independent seeds,
the rearrangement ranges behind the two bound rows, and the t copula row as a function of the degrees of freedom.

Calls ``riskvalidation.aggregation.band.dependence_band`` (the whole band), ``aggregation.bounds.worst_var_bounds`` (the ranges) and
``aggregation.copulas.copula_aggregate`` (the curve). Seeds: 42 for the reproduction (the committed seed), 1001 to 1020 for the
repetitions of the base band and 2001 to 2010 for the stressed band. Writes ``e2_reproduce.json``. Run time: about 9 minutes.

    python manuscripts/dependence-band-with-every-aggregate/experiments/e2_reproduce.py
"""
from __future__ import annotations

import math
import time

import numpy as np

import bandkit as bk

REPS_BASE = list(range(1001, 1021))
REPS_STRESS = list(range(2001, 2011))
NU_CURVE = [2.5, 3.0, 4.0, 6.0, 8.0, 15.0, 30.0, 100.0]


def stats_of(values: list[float]) -> dict[str, float]:
    a = np.array(values)
    return {"mean": float(a.mean()), "sd": float(a.std(ddof=1)), "min": float(a.min()), "max": float(a.max()), "n": int(a.size)}


def main() -> None:
    t0 = time.time()
    h = bk.hypotheses()
    case = bk.Case()
    # --- H2: the reproduction at the committed seed
    band = case.band(seed=bk.COMMITTED_SEED)
    rebuilt = bk.band_dict(band)
    committed = {case.label(r["method"], r["nu"]): r for r in case.committed_band}
    c2 = h["H2"]["criterion"]
    repro = {}
    for key, row in rebuilt.items():
        c = committed[key]
        se = math.sqrt((row["se"] or 0.0) ** 2 + (c["mc_se_clp_m"] or 0.0) ** 2)
        diff = row["capital"] - c["capital_clp_m"]
        tol = max(c2["se_multiple"] * se, c2["relative_tolerance"] * abs(c["capital_clp_m"]))
        repro[key] = {"committed": c["capital_clp_m"], "rebuilt": row["capital"], "difference": diff, "relative_difference": diff / c["capital_clp_m"],
                      "committed_se": c["mc_se_clp_m"], "rebuilt_se": row["se"], "combined_se": se, "tolerance": tol, "within": abs(diff) <= tol}
    print("H2 done", round(time.time() - t0), "s", flush=True)
    # --- the ranges behind the bound rows
    vb = bk.rv_bounds.worst_var_bounds(case.ppfs, bk.LEVEL, bk.BOUNDS_N, bk.BOUNDS_EPS, seed=bk.COMMITTED_SEED)
    ranges = {"lower_range": list(vb.lower_range), "upper_range": list(vb.upper_range), "sweeps": list(vb.sweeps), "converged": vb.converged,
              "el_total": case.el_total, "comonotonic_var": bk.rv_bounds.comonotonic_var(case.ppfs, bk.LEVEL)}
    # --- repetitions of the base band
    base_reps = {}
    for seed in REPS_BASE:
        for key, row in bk.band_dict(case.band(seed=seed)).items():
            base_reps.setdefault(key, []).append(row["capital"])
    print("base repetitions done", round(time.time() - t0), "s", flush=True)
    stress_reps = {}
    for seed in REPS_STRESS:
        for key, row in bk.band_dict(case.band(seed=seed, corr=case.corr_stress)).items():
            stress_reps.setdefault(key, []).append(row["capital"])
    print("stress repetitions done", round(time.time() - t0), "s", flush=True)
    base_stats = {k: stats_of(v) for k, v in base_reps.items()}
    stress_stats = {k: stats_of(v) for k, v in stress_reps.items()}
    # --- H3
    c3 = h["H3"]["criterion"]
    rows = {k: v["capital"] for k, v in rebuilt.items()}
    ses = [v["se"] for v in rebuilt.values() if v["se"]]
    width = rows["worst-case"] - rows["lower-bound"]
    farthest = {}
    for k, v in rows.items():
        farthest[k] = max(abs(o / v - 1.0) for kk, o in rows.items() if kk != k)
    committed_rows = {k: v["capital_clp_m"] for k, v in committed.items()}
    committed_ses = [v["mc_se_clp_m"] for v in committed.values() if v["mc_se_clp_m"]]
    c_width = committed_rows["worst-case"] - committed_rows["lower-bound"]
    c_farthest = {k: max(abs(o / v - 1.0) for kk, o in committed_rows.items() if kk != k) for k, v in committed_rows.items()}
    h3 = {"criterion": c3, "committed": {"width": c_width, "max_se": max(committed_ses), "width_over_max_se": c_width / max(committed_ses),
                                          "farthest_row_relative_difference": c_farthest},
          "rebuilt": {"width": width, "max_se": max(ses), "width_over_max_se": width / max(ses), "farthest_row_relative_difference": farthest}}
    h3["outcome"] = "held" if (h3["committed"]["width_over_max_se"] >= c3["width_over_max_se_min"]
                               and min(c_farthest.values()) > c3["farthest_row_relative_difference_min"]) else "refuted"
    # --- the t row as a function of nu, base and stressed matrix, at the committed seed
    curve = {"nu": NU_CURVE, "base": [], "stress": [], "base_se": [], "stress_se": []}
    el_total = case.el_total
    for nu in NU_CURVE:
        for name, corr in (("base", case.corr), ("stress", case.corr_stress)):
            agg = bk.rv_cop.copula_aggregate(case.ppfs, corr, "t", nu, el_total, bk.LEVEL, bk.N_DRAWS, bk.COMMITTED_SEED, bk.CHUNK)
            curve[name].append(agg.ec)
            curve[name + "_se"].append(agg.var_se)
    for name, corr in (("base", case.corr), ("stress", case.corr_stress)):
        agg = bk.rv_cop.copula_aggregate(case.ppfs, corr, "gaussian", None, el_total, bk.LEVEL, bk.N_DRAWS, bk.COMMITTED_SEED, bk.CHUNK)
        curve["gaussian_" + name], curve["gaussian_" + name + "_se"] = agg.ec, agg.var_se
    # tail dependence coefficients of the bivariate t copula at the pair correlations of the case
    curve["tail_dependence_rho05"] = [bk.rv_cop.t_tail_dependence(0.5, nu) for nu in NU_CURVE]
    curve["tail_dependence_rho02"] = [bk.rv_cop.t_tail_dependence(0.2, nu) for nu in NU_CURVE]
    # monotone in nu? (the conjecture of the theory section)
    curve["monotone_base"] = all(a >= b - 2 * math.hypot(sa, sb) for a, b, sa, sb in zip(curve["base"], curve["base"][1:], curve["base_se"], curve["base_se"][1:]))
    curve["monotone_stress"] = all(a >= b - 2 * math.hypot(sa, sb) for a, b, sa, sb in zip(curve["stress"], curve["stress"][1:], curve["stress_se"], curve["stress_se"][1:]))
    out = {"H2": {"criterion": c2, "per_row": repro, "outcome": "held" if all(v["within"] for v in repro.values()) else "refuted"},
           "H3": h3, "bound_ranges": ranges, "repetitions_base": {"seeds": REPS_BASE, "rows": base_stats},
           "repetitions_stress": {"seeds": REPS_STRESS, "rows": stress_stats}, "nu_curve": curve,
           "rebuilt_at_committed_seed": rebuilt, "seconds": round(time.time() - t0)}
    path = bk.write_json("e2_reproduce.json", out)
    print("wrote", path.name, "H2", out["H2"]["outcome"], "H3", h3["outcome"], "seconds", out["seconds"], flush=True)


if __name__ == "__main__":
    main()
