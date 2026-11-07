"""The paired comparison of the maximum-T rule with the pair-aware rule at the Sidak bound, read from ``results_maxt.json``.

    python manuscripts/reconciliation-against-reference-engines/experiments/exp_maxt_paired.py [--out results_maxt_paired.json]

The two rules of ``exp_maxt.py`` named ``pair+sidak`` and ``pair+maxT`` read the same statistic on the same pairs of runs: the
largest of the 35 absolute pair-aware standardised differences, ``mp``. They differ only in the bound it is compared with: the Sidak
constant of ``results_criterion.json`` (``sidak_bound``) for the first, and the estimated maximum-T bound for the second (the
``bounds[variant].pair`` of ``results_maxt.json``, one per parity of the repetition). When every estimated bound is below the Sidak
constant, ``mp > Sidak`` implies ``mp > maxT bound`` in each repetition, so the repetitions that only the maximum-T rule rejects are
the difference of the two rejection counts and no repetition is rejected by the Sidak rule alone. The script checks that condition
on the stored bounds and on the stored counts, then reports for each cell the repetitions gained, the gain in percentage points and
the exact two-sided sign test on the discordant repetitions, whose null is that a discordant repetition is as likely to be a gain as a
loss: with no loss it is ``2 x 0.5^gain``.

Because the nesting holds for any estimated covariance, the prediction that the maximum-T rule detects at least as often (M2 of
``predictions.md``) holds by construction and is not evidence about the dependence of the comparisons.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def sign_test_p(gains: int, losses: int) -> float:
    """Exact two-sided sign test on ``gains`` and ``losses`` discordant repetitions."""
    n = gains + losses
    if n == 0:
        return 1.0
    k = min(gains, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0**n
    return min(1.0, 2.0 * tail)


def paired(maxt: dict, sidak_bound: float) -> dict:
    reps = maxt["reps"]
    pair_bounds = [b for v in maxt["bounds"].values() for b in v["pair"].values()]
    nested = max(pair_bounds) < sidak_bound
    cells: dict = {}
    for key, cell in maxt["table"].items():
        a, b = cell["pair+sidak"]["rejected"], cell["pair+maxT"]["rejected"]
        # with nested rejection regions the repetitions rejected by the Sidak rule are a subset of those of the maximum-T rule
        gains, losses = (b - a, 0) if nested else (None, None)
        if nested and gains < 0:
            raise AssertionError(f"{key}: the maximum-T rule rejects fewer repetitions than the Sidak rule, so the regions are not nested")
        cells[key] = {"sidak_rejected": a, "maxT_rejected": b, "gained": gains, "lost": losses, "gain_points": 100.0 * gains / reps,
                      "sign_test_p": sign_test_p(gains, losses)}
    return {"reps": reps, "sidak_bound": sidak_bound, "max_estimated_pair_bound": max(pair_bounds), "regions_nested": nested, "cells": cells}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results_maxt_paired.json"))
    args = ap.parse_args()
    maxt = json.loads((HERE / "results_maxt.json").read_text(encoding="utf-8"))
    crit = json.loads((HERE / "results_criterion.json").read_text(encoding="utf-8"))
    out = paired(maxt, crit["sidak_bound"])
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    for key, c in out["cells"].items():
        print(key.ljust(26), f"sidak {c['sidak_rejected']:3d}  maxT {c['maxT_rejected']:3d}  gained {c['gained']:3d}  lost {c['lost']}  "
              f"{c['gain_points']:.2f} points  sign test p = {c['sign_test_p']:.2e}")
    print("regions nested:", out["regions_nested"], f"(largest estimated bound {out['max_estimated_pair_bound']:.4f} < {out['sidak_bound']:.4f})")


if __name__ == "__main__":
    main()
