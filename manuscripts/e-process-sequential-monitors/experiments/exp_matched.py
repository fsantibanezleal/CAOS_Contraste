"""The single-alternative e-process matched to the severity, at every severity of the delay table.

The first-order delay of the theory is the time of the matched likelihood ratio, the bet whose alternative is the true hit
rate. The main run measured only one single alternative, the one at three times the nominal rate (``e_sprt3``), which is
matched at that severity and not at the others, so the comparison of the measured medians with the first-order times held
at one severity only. This script measures, at each factor m of the severity ladder (1.5, 2, 3, 4, 6, 10), the engine's
single-alternative monitor with the multiplier m, on the same streams as the main run (the seed sequence ``[seed, tag]`` of
``exp_hits.py``, 2,000 streams of 1,000 days), with the median first-rejection day and its bootstrap interval, the share of
streams rejected by day 250 and within the horizon.

    python manuscripts/e-process-sequential-monitors/experiments/exp_matched.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from importlib import metadata

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402

SEED = 20261104
#: factor -> the scenario tag it has in exp_hits.py, so the streams are those of the main run
FACTORS: dict[str, tuple[float, int]] = {"x1.5": (1.5, 1), "x2": (2.0, 2), "x3": (3.0, 3), "x4": (4.0, 4), "x6": (6.0, 5), "x10": (10.0, 6)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_matched.json")
    args = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(np.random.SeedSequence([args.seed, 780]))
    out: dict = {"meta": {"seed": args.seed, "reps": args.reps, "alpha": cm.ALPHA, "horizon": cm.HORIZON,
                          "engine_version": metadata.version("riskvalidation"), "script": "experiments/exp_matched.py"},
                 "factors": {}}
    for name, (m, tag) in FACTORS.items():
        h = cm.draw_hits(args.seed, tag, args.reps, rate_factor=m)
        days = cm.first_true(cm.engine_paths(h, cm.ALPHA, multipliers=[m]) >= cm.CROSS)
        res = cm.summarise(days, cm.WINDOW, rng)
        out["factors"][name] = {"multiplier": m, **res}
        print(f"[{name}] matched single alternative median {res['median_day']} ci {res['median_ci']} by250 {res['by']:.3f} [{time.time() - t0:.0f} s]", flush=True)
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
