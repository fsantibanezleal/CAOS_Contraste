"""What the experiments of this manuscript share: the repository root, the committed null document, one cell run and its
counts, and the writer of the compact JSON results (``experiments/results/``)."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

LEVELS = (0.05, 0.01)
SLICE = 1000          # repetitions per slice: a slice is a valid simulation of 1,000 repetitions on its own


def run_cell(key: str, seed: int, n_rep: int) -> dict[str, Any]:
    """Run the null cell ``key`` of ``scenarios.credit_null_scenarios`` (the engine's ``simulate``, one stream per
    repetition) and return its rejection counts per level, in total and per slice of ``SLICE`` repetitions."""
    from riskvalidation.harness import simulate

    import scenarios

    sc = next(s for s in scenarios.credit_null_scenarios() if s.key == key)
    sim = simulate(sc.test_id, sc.generator, n_rep=n_rep, seed=seed, feed=sc.feed, alphas=LEVELS,
                   test_kwargs=sc.test_kwargs)
    p = sim.p_values
    out: dict[str, Any] = {"key": key, "seed": int(seed), "n_rep": int(n_rep),
                           "undefined": int(np.sum(~np.isfinite(p)))}
    for a in LEVELS:
        hit = np.isfinite(p) & (p < a)
        out[f"k{a:g}"] = int(hit.sum())
        out[f"slices{a:g}"] = [int(hit[i:i + SLICE].sum()) for i in range(0, n_rep, SLICE)]
    return out


def write_json(name: str, payload: Any) -> pathlib.Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path
