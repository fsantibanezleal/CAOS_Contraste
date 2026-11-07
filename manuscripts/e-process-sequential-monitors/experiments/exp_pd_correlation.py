"""Size of the PD monitors when the defaults of a year share a systematic factor.

The monitors of defaults against the predicted PD of each grade assume that, given the past, the defaults of a grade are
binomial: they model no asset correlation. This script measures what that assumption costs. The generator
``riskvalidation.generators.DefaultCounts`` (release 1.1.0) draws one standard normal factor per year, common to every grade,
and conditions the default probability of each grade on it (the one-factor Vasicek model) with asset correlation ``rho``.
The predicted PDs are the true ones, so the null of every rule holds in the average sense and only the correlation differs.

Book: five grades (PD 0.5, 1, 2, 5 and 10 %), 2,000 obligors per grade and year, ten years, ``--reps`` histories per
correlation (default 2,000), ``rho`` in 0, 0.03, 0.12 and 0.24 (the Basel asset-correlation range of the IRB corporate
formula runs from 0.12 to 0.24). Rules, each read every year: the engine's PD e-process combined by product and by average
(two-sided and upper), the chi-square test across grades on the cumulative counts read once at year 10 and read every year.

    python manuscripts/e-process-sequential-monitors/experiments/exp_pd_correlation.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from importlib import metadata

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402

SEED = 20261104
PD_BOOK = (0.005, 0.01, 0.02, 0.05, 0.10)
N_OBL, YEARS = 2000, 10
RHOS = (0.0, 0.03, 0.12, 0.24)


def main() -> int:
    from riskvalidation.generators import DefaultCounts
    from riskvalidation.validation.sequential import detection_time, pd_grade_eprocess

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_pd_correlation.json")
    args = ap.parse_args()
    t0 = time.time()
    pd = np.array(PD_BOOK)
    n = np.full((YEARS, pd.size), float(N_OBL))
    rows = []
    for tag, rho in enumerate(RHOS):
        gen = DefaultCounts(obligors=np.full((YEARS, pd.size), N_OBL), pd_true=np.tile(pd, (YEARS, 1)),
                            pd_forecast=np.tile(pd, (YEARS, 1)), rho=rho)
        rng = np.random.default_rng(np.random.SeedSequence([args.seed, 400 + tag]))
        draws = np.array([gen.draw(rng)["d"].astype(float) for _ in range(args.reps)])
        row: dict = {"rho": rho, "reps": args.reps}
        rules = {
            "e_product": dict(combine="product"), "e_average": dict(combine="average"),
            "e_product_upper": dict(combine="product", direction="upper"),
            "e_average_upper": dict(combine="average", direction="upper"),
        }
        for name, opts in rules.items():
            t = np.array([detection_time(pd_grade_eprocess(d, n, pd, **opts).log_e) or np.inf for d in draws])
            k = int(np.isfinite(t).sum())
            row[name] = {"ever": k / args.reps, "ever_ci": list(cm.wilson(k, args.reps))}
        cum_d, cum_n = np.cumsum(draws, axis=1), np.cumsum(np.broadcast_to(n, draws.shape), axis=1)
        chi2 = (((cum_d - cum_n * pd) ** 2) / (cum_n * pd * (1 - pd))).sum(axis=2)
        rej = stats.chi2.sf(chi2, pd.size) < cm.LEVEL
        k1, k2 = int(rej[:, -1].sum()), int(rej.any(axis=1).sum())
        row["chi2_one_shot_year_10"] = {"ever": k1 / args.reps, "ever_ci": list(cm.wilson(k1, args.reps))}
        row["chi2_every_year"] = {"ever": k2 / args.reps, "ever_ci": list(cm.wilson(k2, args.reps))}
        rows.append(row)
        print(f"[rho {rho}] " + "  ".join(f"{k}={row[k]['ever']:.3f}" for k in row if isinstance(row[k], dict)) + f" [{time.time() - t0:.0f} s]", flush=True)
    result = {"meta": {"seed": args.seed, "reps": args.reps, "pd_book": list(PD_BOOK), "obligors": N_OBL, "years": YEARS,
                       "rhos": list(RHOS), "engine_version": metadata.version("riskvalidation"),
                       "script": "experiments/exp_pd_correlation.py"}, "rows": rows}
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
