"""The correlation of the antithetic pairs of the engine's exposure simulation at each report date.

    python manuscripts/reconciliation-against-reference-engines/experiments/exp_pairs.py [--reps 40] [--out results_pairs.json]

Proposition 5 of the manuscript says that the standardised difference of two independent runs of one model, formed with
standard errors that treat the paths as independent, has variance 1 + rho when both runs share the pair correlation rho. This
script measures rho_k, the correlation between the discounted exposure of path i and of path i + P/2 (the engine's antithetic
pair), at each of the 33 report dates, for the single swap and the netting set, averaged over ``--reps`` simulations of 20,000
paths with seeds 2,000,000 + r, and gives the prediction sqrt(1 + rho_k) of the spread of z at each date for comparison with the
spread measured by ``exp_criterion.py``.
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np

import common as cm

HERE = pathlib.Path(__file__).resolve().parent
MEMBERS = {"single-swap": [0], "netting-set": [0, 1, 2, 3]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=40)
    ap.add_argument("--out", default=str(HERE / "results_pairs.json"))
    args = ap.parse_args()
    from pipeline.cases.c12 import exposure as xp

    inp = cm.C12Inputs("netting-set")
    rho = {v: [] for v in MEMBERS}
    cva_rho = {v: [] for v in MEMBERS}
    surv = np.concatenate([[1.0], [b["survival"] for b in cm.derived("C12/netting-set.json")["outputs"]["cva_dva"]["buckets"]]])
    pd = surv[:-1] - surv[1:]
    for r in range(args.reps):
        sim = inp.simulate(2_000_000 + r)
        num = sim.numeraire[:, sim.index(inp.report)]
        for v, members in MEMBERS.items():
            e = xp.uncollateralised(sim, members)
            pos = e.x / num
            half = pos.shape[0] // 2
            c = np.array([np.corrcoef(pos[:half, k], pos[half:, k])[0, 1] if pos[:, k].std() > 0 else np.nan for k in range(pos.shape[1])])
            rho[v].append(c)
            cv = pos @ pd
            cva_rho[v].append(float(np.corrcoef(cv[:half], cv[half:])[0, 1]))
    out = {"reps": args.reps, "paths": inp.paths, "seed_base": 2_000_000, "t": [float(t) for t in inp.report]}
    for v in MEMBERS:
        a = np.array(rho[v])
        out[v] = {"rho_by_date": [None if np.isnan(x) else round(float(x), 4) for x in np.nanmean(a, axis=0)],
                  "predicted_sd_z_by_date": [None if np.isnan(x) else round(float(np.sqrt(1 + x)), 4) for x in np.nanmean(a, axis=0)],
                  "rho_cva": float(np.mean(cva_rho[v])), "predicted_sd_z_cva": float(np.sqrt(1 + np.mean(cva_rho[v])))}
    cm.write(pathlib.Path(args.out), out)
    for v in MEMBERS:
        print(v, "rho at dates 1, 12, 20, 33:", [out[v]["rho_by_date"][i] for i in (0, 11, 19, 32)], "cva rho", round(out[v]["rho_cva"], 3))


if __name__ == "__main__":
    main()
