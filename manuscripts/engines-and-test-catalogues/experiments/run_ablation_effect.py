"""Size of the effect of the copula-loading defect of the ablation (loadings scaled by 0.97) on the four risk measures, over R seeds.

The ablation reports which layers detect that defect; this script says how large the defect is in the units of Proposition 4 of the
manuscript, so that the detection can be read against the minimum detectable shift of the cross-implementation layer.

    python manuscripts/engines-and-test-catalogues/experiments/run_ablation_effect.py
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_portfolio as prt  # noqa: E402

from riskvalidation.portfolio import copula
from riskvalidation.portfolio import portfolio as pf

R, N, FACTOR = 5, 200_000, 0.97


def main() -> None:
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
    names = ["var99", "es99", "var999", "es999"]
    out = {"replications": R, "scenarios_each": N, "loading_factor": FACTOR, "correlation_factor": FACTOR ** 2,
           "relative_change": {n: float((d[:, j].mean() - c[:, j].mean()) / c[:, j].mean()) for j, n in enumerate(names)},
           "clean_sd_relative": {n: float(c[:, j].std(ddof=1) / c[:, j].mean()) for j, n in enumerate(names)}}
    (HERE / "results_ablation_effect.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
