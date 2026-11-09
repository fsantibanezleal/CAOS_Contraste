"""E5: one synthetic bank under three provisioning regimes, regenerated for several seeds and sizes.

    python manuscripts/provisions-reconciliation-identities/experiments/e5_regimes.py --seeds 42 1 2 3 4 5 6 7 8 9 --scale 1.0
    python manuscripts/provisions-reconciliation-identities/experiments/e5_regimes.py --seeds 42 --scale 0.02 0.05 0.1 0.2 0.5

The script calls the product's own C07 generator and evaluation (``pipeline.cases.c07.bake.build``: the synthetic Banco Andino,
calibrated to the CMF aggregates of ``sources.TARGETS``, evaluated under CMF B-1, IFRS 9 and BdE Annex 9 in six scenarios by
the engine ``riskvalidation`` 1.1.0) for each (seed, scale) pair and writes one compact JSON per pair to
``experiments/e5_regimes/s<seed>-x<scale>.json``; a pair whose file exists is skipped. The committed documents are the pair
(seed 42, scale 1.0).

Per scenario the script records the three regime totals and their ratios; the bridge from the B-1 total to the IFRS 9 total
(its steps, and the difference between the sum of the steps and the gap); the largest difference between a regime total and
the sum of its segments and unallocated lines; the booked B-1 total against the comparable total plus the additional
provisions; the engine's reconciliation-identities test row (light, metric, failing identities); and the scenario-sensitivity
non-linearity index of the IFRS 9 allowance.

Predictions, written before the first run of this script (the author of the unit, 2026-11-07; the totals of the committed seed
and the product's notebook had been read before, so B6 is a reproduction and the others, run on seeds the product has not
published, are new):
  B1  the bridge closes to within 1 currency unit in every seed and scenario;
  B2  the engine's reconciliation-identities test is green in every seed and scenario;
  B3  IFRS 9 is below B-1 in the base, recession, house price, consumer arrears and UF inflation scenarios and above it in the
      combined severe scenario, in every seed at scale 1.0;
  B4  IFRS 9 is above Annex 9 in the base scenario in at least 8 of the 10 seeds;
  B5  the standard deviation over seeds of the ratio IFRS 9 over B-1 in the base scenario is below 0.05;
  B6  the pair (42, 1.0) reproduces the committed total of every regime in every scenario to within 1 currency unit.
Repetitions: ten seeds at scale 1.0 (42 and 1 to 9). The seed of a run is the generator's own (``generator.generate(seed, scale)``).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from importlib.metadata import version

for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):  # the pipeline's pinned thread count, before numpy loads
    os.environ[_var] = "4"

import common as c  # noqa: E402

OUT = c.HERE / "e5_regimes"
REGIMES = ("cmf-b1", "ifrs9", "bde-annex9")


def summarise(built: dict) -> dict:
    out: dict = {"n_accounts": int(built["book"].n), "book_sha256": built["book"].digest(), "scenarios": {}}
    for sid, art in built["variants"].items():
        o = art["outputs"]
        totals = {r["regime"]: float(r["total_provision"]) for r in o["regimes"]}
        steps = {s["id"]: float(s["amount"]) for s in o["gap_bridge"]["steps"]}
        comp = o["comparison"]
        keys = {"cmf-b1": "cmf_b1_provision", "ifrs9": "ifrs9_provision", "bde-annex9": "bde_annex9_provision"}
        sums = max(abs(math.fsum(r[keys[g]] for r in comp["rows"]) + comp["unallocated"][keys[g]] - totals[g]) for g in REGIMES)
        extra = o["b1_detail"]["additional_provisions"]["amount"]
        ident = [t for t in art["tests"] if t["test_id"] == "ifrs9.reconciliation_identities"][0]
        sens = [t for t in art["tests"] if t["test_id"] == "ifrs9.scenario_sensitivity"]
        out["scenarios"][sid] = {
            "totals": totals, "ifrs9_over_b1": totals["ifrs9"] / totals["cmf-b1"], "bde_over_b1": totals["bde-annex9"] / totals["cmf-b1"],
            "bridge_steps": steps, "bridge_residual": abs(math.fsum(steps.values()) - (totals["ifrs9"] - totals["cmf-b1"])),
            "segment_sum_residual": sums, "booked_b1_residual": abs(o["b1_detail"]["booked_total"] - (totals["cmf-b1"] + extra)),
            "identities": {"light": ident["light"], "metric": ident["metric"], "failing": ident["extras"].get("failing_identities", []),
                           "gross": ident["extras"].get("gross_total")},
            "scenario_sensitivity_nl": sens[0]["metric"] if sens else None, "overlay_total": float(o["ifrs9_detail"]["overlays_total"])}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--scale", type=float, nargs="+", required=True)
    a = ap.parse_args()
    from pipeline.cases.c07 import bake

    OUT.mkdir(exist_ok=True)
    for scale in a.scale:
        for seed in a.seeds:
            path = OUT / f"s{seed}-x{scale:g}.json"
            if path.exists():
                print("skip", path.name)
                continue
            t0 = time.perf_counter()
            built = bake.build(seed, scale)
            payload = summarise(built)
            payload.update({"seed": seed, "scale": scale, "seconds": round(time.perf_counter() - t0, 1), "engine": version("riskvalidation")})
            path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8", newline="\n")
            print(path.name, payload["seconds"], "s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
