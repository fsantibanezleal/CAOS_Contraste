"""E3. Planted dependence structures with a known capital (predictions H4a, H4b and H4c).

The four marginals of Banco Andino are rebuilt from the committed grids. For each of ten planted dependence structures (six
Gaussian or t copulas, a mixture of two Gaussian regimes, a reflected Clayton and a Gumbel copula) the capital of the sum
``VaR_0.999 - EL`` is estimated from 20 independent samples of 10^6 draws (seeds 3001 + 100 s + r). The rows of the band, as the means of the 20 repetitions of e2
with the named convention (base matrix, nu = 4, 8, 30), are then set against that truth, together with two published single-figure
methods calibrated on the truth itself (the best case for them): the hybrid quantile of Rosenberg and Schuermann with the Pearson
correlation of the truth sample, and the Gaussian copula with the matrix read from the Kendall rank correlation of the truth sample
(``sin(pi tau / 2)``). Reads ``e2_reproduce.json`` for the rows of the band (mean of its 20 repetitions) and writes
``e3_planted_truth.json``. Run time: about 9 minutes.

    python manuscripts/dependence-band-with-every-aggregate/experiments/e3_planted_truth.py
"""
from __future__ import annotations

import json
import math
import time

import numpy as np
from scipy import stats

import bandkit as bk
from riskvalidation.aggregation import simple as rv_simple

REPS = 20
N = 1_000_000
CALIB_N = 200_000
INTERIOR = ["variance-covariance", "gaussian-copula", "t-copula-nu4", "t-copula-nu8", "t-copula-nu30"]


def main() -> None:
    t0 = time.time()
    h = bk.hypotheses()
    case = bk.Case()
    e2 = json.loads((bk.HERE / "e2_reproduce.json").read_text(encoding="utf-8"))
    base = {k: v["mean"] for k, v in e2["repetitions_base"]["rows"].items()}
    stress = {k: v["mean"] for k, v in e2["repetitions_stress"]["rows"].items()}
    lower, worst = base["lower-bound"], base["worst-case"]
    out_rows = []
    for s_idx, st in enumerate(bk.structures(case)):
        caps = []
        for r in range(REPS):
            total = bk.sample_total(case, st, 3001 + 100 * s_idx + r, N).sum(axis=1)
            caps.append(bk.capital_of_total(total, case.el_total)[0])
        truth, truth_se = float(np.mean(caps)), float(np.std(caps, ddof=1) / math.sqrt(REPS))
        # data for the two calibrated comparators: one sample of the structure, kept apart from the truth samples
        sample = bk.sample_total(case, st, 9001 + s_idx, CALIB_N)
        hyb = rv_simple.hybrid_quantile(sample, bk.LEVEL) - case.el_total
        tau = np.eye(4)
        for i in range(4):
            for j in range(i + 1, 4):
                tau[i, j] = tau[j, i] = stats.kendalltau(sample[:50_000, i], sample[:50_000, j]).statistic
        rho = np.sin(math.pi * tau / 2.0)
        np.fill_diagonal(rho, 1.0)
        try:
            gk = bk.rv_cop.copula_aggregate(case.ppfs, rho, "gaussian", None, case.el_total, bk.LEVEL, bk.N_DRAWS, 9501 + s_idx, bk.CHUNK)
            gauss_k, gauss_k_se, gauss_k_note = gk.ec, gk.var_se, "ok"
        except ValueError as exc:
            gauss_k, gauss_k_se, gauss_k_note = float("nan"), float("nan"), str(exc)[:120]
        interior = [base[k] for k in INTERIOR]
        interior_stress = interior + [stress[k] for k in INTERIOR]
        lo_i, hi_i = min(interior), max(interior)
        lo_s, hi_s = min(interior_stress), max(interior_stress)
        w = 3.0 * truth_se
        errors = {k: base[k] / truth - 1.0 for k in ("simple-sum", *INTERIOR)}
        errors["hybrid-calibrated"] = hyb / truth - 1.0
        errors["gaussian-kendall-calibrated"] = gauss_k / truth - 1.0
        row = {"id": st["id"], "label": st["label"], "family": st["family"], "truth": truth, "truth_se": truth_se,
               "truth_over_headline": truth / case.headline, "hybrid_calibrated": float(hyb), "gaussian_kendall_calibrated": gauss_k,
               "gaussian_kendall_se": gauss_k_se, "gaussian_kendall_note": gauss_k_note, "relative_error": errors,
               "covered_sharp_range": bool(lower - w <= truth <= worst + w), "covered_interior": bool(lo_i - w <= truth <= hi_i + w),
               "covered_interior_with_stress": bool(lo_s - w <= truth <= hi_s + w),
               "gaussian_within_tolerance": bool(abs(errors["gaussian-copula"]) <= h["H4c"]["criterion"]["relative_tolerance"]),
               "interior_range": [lo_i, hi_i], "interior_range_with_stress": [lo_s, hi_s],
               "truth_above_worst": bool(truth > worst), "truth_below_lower": bool(truth < lower)}
        out_rows.append(row)
        print(st["id"], round(truth), round(truth_se), "gauss err", round(errors["gaussian-copula"], 3), "sharp", row["covered_sharp_range"],
              "interior", row["covered_interior"], round(time.time() - t0), "s", flush=True)
    n = len(out_rows)
    a = sum(r["covered_sharp_range"] for r in out_rows) / n
    b = sum(r["covered_interior"] for r in out_rows) / n
    b2 = sum(r["covered_interior_with_stress"] for r in out_rows) / n
    c = sum(r["gaussian_within_tolerance"] for r in out_rows) / n
    crit = {k: h[k]["criterion"] for k in ("H4a", "H4b", "H4c")}
    out = {"reps": REPS, "n_draws": N, "structures": out_rows, "band_rows_used": {"base": base, "stress": stress},
           "self_checks": bk.self_checks(),
           "H4a": {"criterion": crit["H4a"], "covered_share": a, "outcome": "held" if a >= crit["H4a"]["covered_min_share"] else "refuted"},
           "H4b": {"criterion": crit["H4b"], "covered_share": b, "covered_share_with_stress": b2,
                   "outcome": "held" if b >= crit["H4b"]["covered_min_share"] else "refuted"},
           "H4c": {"criterion": crit["H4c"], "within_share": c, "outcome": "held" if c <= crit["H4c"]["within_share_max"] else "refuted"},
           "seconds": round(time.time() - t0)}
    path = bk.write_json("e3_planted_truth.json", out)
    print("wrote", path.name, "H4a", out["H4a"]["outcome"], a, "H4b", out["H4b"]["outcome"], b, b2, "H4c", out["H4c"]["outcome"], c, flush=True)


if __name__ == "__main__":
    main()
