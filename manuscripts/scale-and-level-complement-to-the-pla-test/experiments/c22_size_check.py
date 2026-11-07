"""Cross-check of the size of the Christoffersen conditional-coverage comparator against the committed C22 documents.

The C22 case of the product validates the size and power of the engine's tests that return a p-value. Its committed document
``data/derived/C22/other-families.json`` holds the size of ``market.christoffersen_conditional_coverage`` on independent hits
(1,500 days at 5%, 2,000 replications, rule p < 0.05 and p < 0.01). This script

1. reads those committed rates;
2. runs the same engine function (``riskvalidation.validation.market.christoffersen_conditional_coverage``, the one that
   ``stats_core.py`` calls for the comparator ``cc_975``) on the same design with this script's own seed, and compares the two
   sizes (two-proportion z test and Wilson intervals);
3. runs it at the design of the manuscript (250 days, 97.5% value-at-risk, i.e. a hit probability of 2.5%) and reports the size of
   the chi-square p-value rule next to the size of the null-calibrated rule that the manuscript uses (``results.json``,
   ``main.none.cc_975``).

    python manuscripts/scale-and-level-complement-to-the-pla-test/experiments/c22_size_check.py [--reps 2000] [--seed 20261107]

The output is ``c22_size_check.json`` beside this file. Run time: a few seconds. Nothing here draws a random number except through
``--seed``.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from riskvalidation.validation import market as vm  # noqa: E402

C22_DOC = ROOT / "data" / "derived" / "C22" / "other-families.json"
OUT = HERE / "c22_size_check.json"
KEY = "market.christoffersen_conditional_coverage@d0"
Z = 1.959964


def wilson(k: int, n: int) -> tuple[float, float]:
    p = k / n
    den = 1 + Z * Z / n
    mid = (p + Z * Z / (2 * n)) / den
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return mid - half, mid + half


def two_prop_z(k1: int, n1: int, k2: int, n2: int) -> float:
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return (k1 / n1 - k2 / n2) / se if se > 0 else 0.0


def size(days: int, alpha: float, reps: int, rng: np.random.Generator) -> dict:
    """Rejection counts of the engine's Christoffersen test on independent hits at probability ``alpha``."""
    k05 = k01 = undefined = 0
    for _ in range(reps):
        ex = rng.random(days) < alpha
        res = vm.christoffersen_conditional_coverage(ex, alpha)
        if res.p_value is None or not np.isfinite(res.p_value):
            undefined += 1  # no exceedance: the engine does not evaluate the test, so no rejection
            continue
        k05 += int(res.p_value < 0.05)
        k01 += int(res.p_value < 0.01)
    out = {"days": days, "hit_probability": alpha, "reps": reps, "undefined": undefined}
    for name, k in (("p<0.05", k05), ("p<0.01", k01)):
        lo, hi = wilson(k, reps)
        out[name] = {"k": k, "rate": k / reps, "lo": lo, "hi": hi}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261107)
    a = ap.parse_args()

    doc = json.loads(C22_DOC.read_text(encoding="utf-8"))
    sim = next(s for s in doc["outputs"]["simulations"] if s["key"] == KEY)
    committed = {r: {"k": v["rejections"], "n": v["n"], "rate": v["rate"], "lo": v["wilson_low"], "hi": v["wilson_high"]}
                 for r, v in sim["rates"].items() if r in ("p<0.05", "p<0.01")}

    rng = np.random.default_rng(a.seed)
    same = size(1500, 0.05, a.reps, rng)
    compare = {}
    for r in ("p<0.05", "p<0.01"):
        c, m = committed[r], same[r]
        compare[r] = {"committed": c, "rerun": m, "z": two_prop_z(c["k"], c["n"], m["k"], a.reps),
                      "intervals_overlap": not (c["hi"] < m["lo"] or m["hi"] < c["lo"])}

    here = size(250, 0.025, a.reps, rng)
    res = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    cal = res["main"]["none"]["cc_975"]
    result = {"seed": a.seed, "reps": a.reps, "c22_design": {"days": 1500, "hit_probability": 0.05},
              "c22_vs_rerun": compare, "manuscript_design_p_value_rule": here,
              "manuscript_calibrated_rule_held_out": {"k": cal["k"], "n": cal["n"], "rate": cal["rate"], "lo": cal["lo"], "hi": cal["hi"]}}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
