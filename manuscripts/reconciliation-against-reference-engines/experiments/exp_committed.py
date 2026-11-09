"""The committed Hull-White reconciliations against ORE 1.8.17.0 read as statistics.

    python manuscripts/reconciliation-against-reference-engines/experiments/exp_committed.py [--out results_committed.json]

Reads ``data/derived/C12/<variant>.json`` for the five variants that carry an ORE run and reports, per variant: the standardised
difference z_k = (ORE - engine) / sqrt(se_ORE^2 + se_engine^2) at each of the 33 report dates (as the document records it), the
number of dates beyond two combined standard errors, the largest |z|, the mean z, the EEPE and CVA differences with their
combined errors, the diagnostic row with a zero minimum transfer amount, and three summaries the document does not hold:

* the smallest symmetric equivalence margin (as a share of the engine's value) at which two one-sided tests at 5 % declare ORE
  and the engine equivalent, Delta = |difference| + 1.645 * se_combined (Schuirmann 1987);
* the smallest relative gap a two-sided test at the acceptance bound 2 detects with probability 0.8, (2 + 0.8416) * se / value;
* the verdict of the product's rule (every z within 2, EEPE and CVA within 2) and of a Sidak-adjusted bound for the 35 comparisons
  at a family size of 5 %.
"""
from __future__ import annotations

import argparse
import math
import pathlib

import numpy as np

import common as cm

HERE = pathlib.Path(__file__).resolve().parent
ORE_SAMPLES = 10_000      # ``ORE_SAMPLES`` of the pipeline's bake (antithetic pairs)
Z_TOST = 1.6448536269514722
Z_POWER = 0.8416212335729143


def sidak_bound(k: int, alpha: float = 0.05) -> float:
    """The two-sided bound c with P(max over k independent |z| <= c) = 1 - alpha."""
    return cm.norm_ppf((1.0 + (1.0 - alpha) ** (1.0 / k)) / 2.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results_committed.json"))
    args = ap.parse_args()
    k_all = 33 + 2
    c_sidak = sidak_bound(k_all)
    variants = {}
    for v in cm.ORE_VARIANTS:
        doc = cm.derived(f"C12/{v}.json")
        out = doc["outputs"]
        ore = out["ore_reconciliation"]
        ag = ore["agreement"]
        z = np.array([a["difference"] / a["combined_se"] for a in ag])
        diff = np.array([a["difference"] for a in ag])
        se = np.array([a["combined_se"] for a in ag])
        # the EE of the engine and ORE at the report dates, for the relative size of the difference
        ee_py = np.array(out["exposure"]["ee"]["values"])
        ee_ore = np.array(ore["ore_ee"]["values"])
        peak = float(ee_py.max())
        scal = {}
        for name, blk, value in (("eepe", ore["eepe_agreement"], ore["eepe_agreement"]["python"]), ("cva", ore["cva_agreement"], ore["cva_agreement"]["python"])):
            d, s = blk["difference"], blk["combined_se"]
            scal[name] = {"python": blk["python"], "ore": blk["ore"], "difference": d, "combined_se": s, "z": d / s, "within_two_se": blk["within_two_se"],
                          "equivalence_margin_rel": (abs(d) + Z_TOST * s) / abs(value), "min_detectable_rel_80": (2.0 + Z_POWER) * s / abs(value),
                          "relative_difference": d / value}
        tests = {(t["test_id"], t.get("segment")): t for t in doc["tests"]}
        mta0 = tests.get(("ccr.reconcile_ee_profile", "minimum-transfer-amount-0"))
        row = {"ore_samples": ORE_SAMPLES, "python_paths": out["named_parameters"]["path_count"]["value"],
               "z": [float(x) for x in z], "t": [a["t"] for a in ag], "n_dates": len(ag), "n_beyond_two": int(np.sum(np.abs(z) > 2.0)),
               "n_beyond_sidak": int(np.sum(np.abs(z) > c_sidak)), "max_abs_z": float(np.abs(z).max()), "mean_z": float(z.mean()),
               "mean_se_over_peak": float(np.mean(se) / peak), "max_abs_diff_over_peak": float(np.abs(diff).max() / peak),
               "peak_ee": peak, "ore_over_python_ee_mean": float(np.mean(ee_ore[ee_py > 0] / ee_py[ee_py > 0])),
               "eepe": scal["eepe"], "cva": scal["cva"],
               "rule_two_se": bool(ore["all_within_two_se"]),
               "rule_sidak": bool(np.abs(z).max() <= c_sidak and abs(scal["eepe"]["z"]) <= c_sidak and abs(scal["cva"]["z"]) <= c_sidak),
               "ee_row_light": tests[("ccr.reconcile_ee_profile", None)]["light"], "ee_row_max_z": tests[("ccr.reconcile_ee_profile", None)]["statistic"],
               "mta0_max_z": None if mta0 is None else mta0["statistic"], "mta0_light": None if mta0 is None else mta0["light"]}
        if ore["dim_agreement"]:
            dz = np.array([a["difference"] / a["combined_se"] for a in ore["dim_agreement"]])
            dim_py = np.array(out["initial_margin"]["dim"]["values"])
            dim_ore = np.array(ore["ore_dim"]["values"])
            row["dim"] = {"max_abs_z": float(np.abs(dz).max()), "n_beyond_two": int(np.sum(np.abs(dz) > 2.0)), "n_dates": int(dz.size),
                          "mean_ratio_ore_over_python": float(np.mean(dim_ore[dim_py > 0] / dim_py[dim_py > 0]))}
        variants[v] = row
    # the exposure of the two uncollateralised variants rebuilt from the committed curve and parameters at the product's seed
    from pipeline.cases.c12 import exposure as xp
    inp = cm.C12Inputs("netting-set")
    sim = inp.simulate(inp.seed)
    rebuild = {}
    for v, members in (("single-swap", [0]), ("netting-set", [0, 1, 2, 3])):
        e = xp.uncollateralised(sim, members)
        mx = xp.measures(e.x, sim.numeraire[:, sim.index(inp.report)], np.asarray(sim.p0(inp.report), dtype=float), inp.report, None, inp.seed)
        doc = cm.derived(f"C12/{v}.json")["outputs"]["exposure"]
        rebuild[v] = {"max_abs_ee_gap": float(np.max(np.abs(mx["ee"] - np.array(doc["ee"]["values"])))),
                      "eepe_gap": float(abs(mx["eepe"] - doc["eepe"]["amount"]))}
    out = {"rebuild": rebuild, "bound": 2.0, "n_comparisons": k_all, "sidak_bound_35": c_sidak, "bonferroni_bound_35": cm.norm_ppf(1 - 0.05 / (2 * k_all)),
           "null_size_upper_bound": 1.0 - (2 * cm.norm_cdf(2.0) - 1.0) ** k_all, "null_size_lower_bound": 1.0 - (2 * cm.norm_cdf(2.0) - 1.0),
           "ore_version": cm.derived("C12/single-swap.json")["outputs"]["ore_reconciliation"]["ore_version"], "variants": variants}
    cm.write(pathlib.Path(args.out), out)
    for v, r in variants.items():
        print(f"{v:14s} beyond2 {r['n_beyond_two']:2d} max|z| {r['max_abs_z']:6.2f} mean z {r['mean_z']:+.2f} eepe z {r['eepe']['z']:+.2f} cva z {r['cva']['z']:+.2f} "
              f"rule {r['rule_two_se']} sidak {r['rule_sidak']} mta0 {r['mta0_max_z']} dim {r.get('dim', {}).get('max_abs_z')}")
    print(out["sidak_bound_35"], out["null_size_upper_bound"], out["null_size_lower_bound"])


if __name__ == "__main__":
    main()
