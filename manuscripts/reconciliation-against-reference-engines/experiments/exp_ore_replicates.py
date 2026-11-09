"""The ORE reconciliation repeated on new draws: does the committed verdict reproduce, and is a reported gap noise or bias?

    CAOS_TEMP_ROOT=<temp root> python manuscripts/reconciliation-against-reference-engines/experiments/exp_ore_replicates.py
        [--variant netting-set --reps 24 --first-seed 5000 --workers 6 --out results_ore_<variant>.json]

The product's reconciliation of the Hull-White exposure with ORE 1.8.17.0 is one pair of runs (seed 42 for both). One pair cannot
say whether the verdict is a property of the two engines or of the draws. This script reruns the same comparison, with the
pipeline's own code (``pipeline.cases.c12.ore`` for the ORE inputs and runs, ``exposure`` and ``variant`` for the engine,
``reconcile.block`` for the agreement), on ``--reps`` new seeds: the engine with 20,000 paths and ORE with 10,000 samples, both
seeded with 5000 + r. The two generators differ, so the seed does not make the two runs share draws.

For each repetition it records the standardised differences z_k at the 33 report dates, the EEPE and CVA z, the product's
verdict, and the same z with pair-aware standard errors (the engine's pairs are i and i + P/2, ORE's are adjacent samples; the
product's errors treat paths as independent). For the collateralised variant it also repeats the diagnostic run with a zero
minimum transfer amount.

ORE writes its run folder under ``--work`` (default ``$CAOS_TEMP_ROOT/contraste-reconciliation``), where every run folder is removed as soon as its output is read.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import math
import pathlib
import shutil
import time

import numpy as np

import common as cm

HERE = pathlib.Path(__file__).resolve().parent
ORE_SAMPLES = 10_000
LGD = 0.6


def _ccurve():
    from pipeline.cases.c12 import credit

    buckets = cm.derived("C12/netting-set.json")["outputs"]["cva_dva"]["buckets"]
    sp = np.array([buckets[0]["spread"]] + [b["spread"] for b in buckets])
    return credit.Curve(sp, 0, "hqm-minus-treasury")


def run_ore(ore, ospec, run_dir: pathlib.Path, attempts: int = 6) -> tuple[float, str]:
    """Write the inputs and run ORE. ORE exits with status 0 when its XVA analytic fails for lack of memory ("bad allocation"),
    leaving no exposure file, so the output is checked and the run repeated (same inputs, same seed) up to ``attempts`` times."""
    for attempt in range(attempts):
        if run_dir.exists():
            shutil.rmtree(run_dir)
        ore.write_inputs(ospec, run_dir)
        try:
            seconds, platform = ore.run(run_dir)
        except RuntimeError:        # the process could not start when the machine's commit limit was reached
            time.sleep(20.0 * (attempt + 1))
            continue
        if (run_dir / "output" / f"exposure_nettingset_{ore.NETTING_SET}.csv").exists():
            return seconds, platform
        time.sleep(5.0 * (attempt + 1))
    raise RuntimeError(f"ORE produced no exposure file in {run_dir} after {attempts} attempts")


def replicate(task: tuple[str, int, str, bool]) -> dict:
    from riskvalidation.ccr import cva as cv
    from riskvalidation.ccr import exposure as ex
    from pipeline.cases.c12 import credit, ore, reconcile
    from pipeline.cases.c12 import variant as vt

    variant, seed, work, with_mta0 = task
    inp = cm.C12Inputs("netting-set")
    spec = cm.spec_of(variant)
    sim = inp.simulate(seed)
    c = vt.core(sim, spec, seed, None, light=True)
    ccurve = _ccurve()
    report = inp.report
    cva_blk = credit.cva_block(c.mx["ee_d"], c.my["ee_d"], c.x_d, c.y_d, report, ccurve, LGD, 0.008, LGD)
    run_dir = pathlib.Path(work) / variant / f"seed-{seed}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    members = [inp.trades[i] for i in spec.members]
    asof = ore.asof_for(int(inp.curve_date[5:7]))
    ospec = ore.Spec(variant, asof, inp.tenors, inp.zeros, inp.a, inp.sigma, members, spec.mpor, spec.im, report, ORE_SAMPLES, seed)
    seconds, platform = run_ore(ore, ospec, run_dir)
    out = reconcile.ore_result(run_dir, report.size, None)
    blk, rows, flags = reconcile.block(c, out, seconds, platform, ccurve, LGD, cva_blk["cva"]["amount"], cva_blk["cva"]["mc_se"])
    z = np.array([a["difference"] / a["combined_se"] for a in blk["agreement"]])
    ze = blk["eepe_agreement"]["difference"] / blk["eepe_agreement"]["combined_se"]
    zc = blk["cva_agreement"]["difference"] / blk["cva_agreement"]["combined_se"]
    # pair-aware errors: the engine's pairs are (i, i + P/2); ORE's are adjacent samples
    p0r = c.p0r
    pos_py = c.x_d
    half = pos_py.shape[0] // 2
    py_pair = 0.5 * (pos_py[:half] + pos_py[half:])
    se_py = py_pair.std(axis=0, ddof=1) / math.sqrt(half) / p0r
    pos_o = out["pos"]
    o_pair = 0.5 * (pos_o[0::2] + pos_o[1::2])
    se_o = o_pair.std(axis=0, ddof=1) / math.sqrt(o_pair.shape[0]) / p0r
    o_ee = out["epe"] / p0r
    zp = (o_ee - c.mx["ee"]) / np.hypot(se_py, se_o)
    pd = cv.default_probabilities(np.exp(-ccurve.spreads * np.concatenate([[0.0], report]) / LGD))
    cva_py = LGD * (pos_py @ pd)
    cva_o = LGD * (pos_o @ pd)
    cva_py_pair = 0.5 * (cva_py[:half] + cva_py[half:])
    cva_o_pair = 0.5 * (cva_o[0::2] + cva_o[1::2])
    zcp = (cva_o.mean() - cva_py.mean()) / math.hypot(cva_py_pair.std(ddof=1) / math.sqrt(half), cva_o_pair.std(ddof=1) / math.sqrt(cva_o_pair.size))
    res = {"variant": variant, "seed": seed, "z": [round(float(x), 4) for x in z], "z_pair": [round(float(x), 4) for x in zp], "z_eepe": float(ze), "z_cva": float(zc),
           "z_cva_pair": float(zcp), "all_within_two_se": bool(all(flags)), "n_beyond_two": int(np.sum(np.abs(z) > 2)),
           "n_beyond_two_pair": int(np.sum(np.abs(zp) > 2)), "max_abs_z": float(np.abs(z).max()), "max_abs_z_pair": float(np.abs(zp).max()),
           "eepe_python": blk["eepe_agreement"]["python"], "eepe_ore": blk["eepe_agreement"]["ore"], "cva_python": blk["cva_agreement"]["python"],
           "cva_ore": blk["cva_agreement"]["ore"], "ore_seconds": float(seconds),
           "pair_correlation_ore_mean": float(np.mean([np.corrcoef(pos_o[0::2, k], pos_o[1::2, k])[0, 1] for k in range(pos_o.shape[1]) if pos_o[:, k].std() > 0])),
           "pair_correlation_python_mean": float(np.mean([np.corrcoef(pos_py[:half, k], pos_py[half:, k])[0, 1] for k in range(pos_py.shape[1]) if pos_py[:, k].std() > 0]))}
    if with_mta0:
        d0 = pathlib.Path(work) / variant / f"seed-{seed}-mta0"
        if d0.exists():
            shutil.rmtree(d0)
        spec0 = ore.Spec(variant, asof, inp.tenors, inp.zeros, inp.a, inp.sigma, members, spec.mpor, False, report, ORE_SAMPLES, seed, mta=0.0)
        run_ore(ore, spec0, d0)
        c0 = vt.core(sim, spec, seed, None, mta=0.0, light=True)
        out0 = reconcile.ore_result(d0, report.size, None)
        row = reconcile.mta0_row(c0, out0, 0.0)
        res["mta0_max_z"] = float(row["statistic"])
        shutil.rmtree(d0, ignore_errors=True)
    shutil.rmtree(run_dir, ignore_errors=True)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="netting-set", choices=cm.ORE_VARIANTS)
    ap.add_argument("--reps", type=int, default=24)
    ap.add_argument("--first-seed", type=int, default=5000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--mta0", action="store_true", help="repeat the diagnostic run with a zero minimum transfer amount")
    ap.add_argument("--work", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    work = cm.work_root(args.work)
    work.mkdir(parents=True, exist_ok=True)
    out_path = pathlib.Path(args.out) if args.out else HERE / f"results_ore_{args.variant}.json"
    t0 = time.perf_counter()
    tasks = [(args.variant, args.first_seed + r, str(work), args.mta0) for r in range(args.reps)]
    with cf.ProcessPoolExecutor(max_workers=args.workers) as pool:
        reps = list(pool.map(replicate, tasks, chunksize=1))
    z = np.array([r["z"] for r in reps])
    zp = np.array([r["z_pair"] for r in reps])
    passed = sum(r["all_within_two_se"] for r in reps)
    lo, hi = cm.wilson(passed, len(reps))
    summary = {"variant": args.variant, "reps": len(reps), "first_seed": args.first_seed, "ore_samples": ORE_SAMPLES, "python_paths": 20_000,
               "passed_product_rule": passed, "pass_rate": passed / len(reps), "pass_lo": lo, "pass_hi": hi,
               "mean_z_by_date": [round(float(x), 3) for x in z.mean(axis=0)], "sd_z_by_date": [round(float(x), 3) for x in z.std(axis=0, ddof=1 if len(reps) > 1 else 0)],
               "mean_z_pair_by_date": [round(float(x), 3) for x in zp.mean(axis=0)], "sd_z_pair_by_date": [round(float(x), 3) for x in zp.std(axis=0, ddof=1 if len(reps) > 1 else 0)],
               "mean_of_mean_z": float(z.mean()), "mean_of_mean_z_pair": float(zp.mean()),
               "mean_z_eepe": float(np.mean([r["z_eepe"] for r in reps])), "sd_z_eepe": float(np.std([r["z_eepe"] for r in reps], ddof=1 if len(reps) > 1 else 0)),
               "mean_z_cva": float(np.mean([r["z_cva"] for r in reps])), "sd_z_cva": float(np.std([r["z_cva"] for r in reps], ddof=1 if len(reps) > 1 else 0)),
               "mean_z_cva_pair": float(np.mean([r["z_cva_pair"] for r in reps])),
               "median_max_abs_z": float(np.median([r["max_abs_z"] for r in reps])), "median_max_abs_z_pair": float(np.median([r["max_abs_z_pair"] for r in reps])),
               "mean_ore_seconds": float(np.mean([r["ore_seconds"] for r in reps])), "wall_seconds": time.perf_counter() - t0}
    if args.mta0:
        summary["mta0_max_z"] = [r["mta0_max_z"] for r in reps]
    cm.write(out_path, {"summary": summary, "replicates": reps})
    print(args.variant, "pass", passed, "of", len(reps), f"mean z {summary['mean_of_mean_z']:+.2f} mean z pair {summary['mean_of_mean_z_pair']:+.2f}",
          f"eepe {summary['mean_z_eepe']:+.2f}", f"cva {summary['mean_z_cva']:+.2f}", f"{summary['wall_seconds']:.0f}s")


if __name__ == "__main__":
    main()
