"""E5. The run time of the band and of its bound rows on the committed settings (the time statement of the method section).

Calls ``riskvalidation.aggregation.band.dependence_band`` once at the committed seed and ``aggregation.bounds.worst_var_bounds``
once, after one untimed call of each that warms the caches, and writes the wall-clock seconds to ``e5_timing.json``. The numbers
depend on the machine; they are a statement about the cost of the method, not a result of the study. Run time: under a minute.

    python manuscripts/dependence-band-with-every-aggregate/experiments/e5_timing.py
"""
from __future__ import annotations

import platform
import time

import bandkit as bk


def main() -> None:
    case = bk.Case()
    case.band(seed=bk.COMMITTED_SEED, n_draws=20_000)
    bk.rv_bounds.worst_var_bounds(case.ppfs, bk.LEVEL, 2_000, bk.BOUNDS_EPS, seed=bk.COMMITTED_SEED)
    t0 = time.perf_counter()
    case.band(seed=bk.COMMITTED_SEED)
    band_seconds = time.perf_counter() - t0
    t0 = time.perf_counter()
    bk.rv_bounds.worst_var_bounds(case.ppfs, bk.LEVEL, bk.BOUNDS_N, bk.BOUNDS_EPS, seed=bk.COMMITTED_SEED)
    bounds_seconds = time.perf_counter() - t0
    out = {"band_seconds": band_seconds, "bounds_seconds": bounds_seconds, "n_draws": bk.N_DRAWS, "bounds_cells": bk.BOUNDS_N,
           "processor": platform.processor(), "python": platform.python_version()}
    path = bk.write_json("e5_timing.json", out)
    print("wrote", path.name, round(band_seconds, 1), "s for the band,", round(bounds_seconds, 1), "s for the bounds")


if __name__ == "__main__":
    main()
