"""Size of the effect of the copula-loading defect of the ablation (loadings scaled by 0.97) on the four risk measures, over R seeds.

The ablation reports which layers detect that defect; this script says how large the defect is in the units of Proposition 4 of the
manuscript, so that the detection can be read against the minimum detectable shift of the cross-implementation layer.

    python manuscripts/engines-and-test-catalogues/experiments/run_ablation_effect.py
"""
from __future__ import annotations

import dataclasses
import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_portfolio as prt  # noqa: E402
import runstats  # noqa: E402

from riskvalidation.portfolio import copula
from riskvalidation.portfolio import portfolio as pf

R, N, FACTOR = 5, 200_000, 0.97
FS_R, FS_N, FS_SEED = 10, 200_000, 32_000  # full-size comparison: the size and the repetitions of the main comparison of the manuscript
NAMES = ["var99", "es99", "var999", "es999"]


def z_difference(mean_a: float, sd_a: float, mean_b: float, sd_b: float, reps: int) -> float:
    """z of the manuscript: the difference of two means of ``reps`` runs each over its standard error (engine minus reference)."""
    return (mean_a - mean_b) / math.sqrt((sd_a ** 2 + sd_b ** 2) / reps)


def fullsize_comparison(low) -> dict:
    """The defective engine (loadings scaled) at the size of the main comparison against the committed independent simulator.

    The independent route is the 10 runs of 200,000 scenarios stored in ``results_portfolio.json`` (``mc.quantities``), whose mean and standard
    deviation are the ones the main comparison uses; the defective route is ``FS_R`` fresh runs with seeds ``FS_SEED`` onward.
    """
    ind = json.loads((HERE / "results_portfolio.json").read_text(encoding="utf-8"))["mc"]
    assert ind["replications"] == FS_R and ind["scenarios_each"] == FS_N
    runs = []
    for r in range(FS_R):
        x = copula.simulate_gaussian(low, FS_N, FS_SEED + r, 16741).losses
        runs.append([pf.var_from_sample(x, 0.99), pf.es_from_sample(x, 0.99), pf.var_from_sample(x, 0.999), pf.es_from_sample(x, 0.999)])
    d = np.array(runs)
    out = {}
    for j, n in enumerate(NAMES):
        m, sd = float(d[:, j].mean()), float(d[:, j].std(ddof=1))
        q = ind["quantities"][n]
        out[n] = {"defect_mean": m, "defect_sd": sd, "independent_mean": q["independent_mean"], "independent_sd": q["independent_sd"],
                  "relative_shift": m / q["independent_mean"] - 1.0,
                  "z_defect_minus_independent": z_difference(m, sd, q["independent_mean"], q["independent_sd"], FS_R)}
    return {"replications": FS_R, "scenarios_each": FS_N, "seed_first": FS_SEED, "quantities": out}


def main() -> None:
    t0 = runstats.start()
    ci = prt.read("C10", "commercial-industrial")["outputs"]
    book = ci["portfolio"]
    one = pf.portfolio_from_groups(book["groups"], book["currency"], book["lgd_gamma"], one_factor=True)
    low = dataclasses.replace(one, loadings=one.loadings * FACTOR)
    rows = {"clean": [], "defect": []}
    for r in range(R):
        for name, p in (("clean", one), ("defect", low)):
            x = copula.simulate_gaussian(p, N, 31_000 + r, 16741).losses
            rows[name].append([pf.var_from_sample(x, 0.99), pf.es_from_sample(x, 0.99), pf.var_from_sample(x, 0.999), pf.es_from_sample(x, 0.999)])
    c, d = np.array(rows["clean"]), np.array(rows["defect"])
    names = NAMES
    out = {"replications": R, "scenarios_each": N, "loading_factor": FACTOR, "correlation_factor": FACTOR ** 2,
           "relative_change": {n: float((d[:, j].mean() - c[:, j].mean()) / c[:, j].mean()) for j, n in enumerate(names)},
           "clean_sd_relative": {n: float(c[:, j].std(ddof=1) / c[:, j].mean()) for j, n in enumerate(names)},
           "fullsize_comparison": fullsize_comparison(low)}
    out["run"] = runstats.stats(t0)
    (HERE / "results_ablation_effect.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
