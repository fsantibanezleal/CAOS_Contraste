"""E1: the power of the reconciliation gate on planted defects, against two comparators and with each identity family left out.

    python manuscripts/provisions-reconciliation-identities/experiments/e1_gate_power.py

Data: the six committed C06 documents (SBA 7(a) loans, six reporting dates), the tables of ``outputs.reconciliation`` and
``outputs.waterfall``. Defects: the eight classes of ``common.DEFECTS``, planted one at a time at a random location, of a
size that is a multiple of the engine's limit ``1e-6 * max(1, G)`` of the date. Gates: the twelve identities of the engine
(``full``), the two roll-forwards of each stage alone (``stage``, the disclosure arithmetic of IFRS 7 35H and 35I), one
pooled row for the whole book (``total``), and the full set with one identity family left out (``drop:<family>``).

Predictions, written before the first run of this script (the author of the unit, 2026-11-07; the notebook of the product
had measured the first of them on one defect class, so the first is a reproduction, the others are new):

  P1  the smallest defect the full gate names equals the limit (the ratio of the bisected size to the limit is 1 within 1e-6)
      for every class except the misclassification, which no identity sees;
  P2  the pooled gate and the stage gate detect, above the limit, the allowance movement, the allowance closing and the
      gross-amount movement in every case, and detect none of the stage reallocation, the waterfall line, the waterfall
      closing and the stage ECL at any size; the full gate detects all seven classes above the limit in every case and
      none of the misclassification;
  P3  leaving one identity family out loses a defect class entirely for exactly two families: the gross-amount roll-forward
      (the gross-amount movement) and the tie of the stage closing to the stage ECL (the stage reallocation and the stage
      ECL); the other four families are redundant for single-entry detection.

Repetitions: 100 locations per date and class (600 cases per class); the location of a case is drawn from a generator seeded
``[SEED_BASE, 1, date index, class index, case index]`` and is the same at every size, so that the rates at different sizes
are over the same cases. Intervals are Wilson (95%).
"""
from __future__ import annotations

import math
import sys
import time
from importlib.metadata import version

import numpy as np

import common as c

REPS = 100
MULTIPLES = (0.25, 0.5, 0.9, 0.99, 1.01, 1.1, 2.0, 10.0, 100.0)
BISECT_CASES = 20
BISECT_STEPS = 60


def case_seed(di: int, ci: int, k: int) -> list[int]:
    return [c.SEED_BASE, 1, di, ci, k]


def flagged(book: c.Book, gate: str) -> bool:
    res, lim = c.residuals(book), c.limit(book)
    if gate == "full":
        return c.gate_full(res, lim)
    if gate == "stage":
        return c.gate_stage(res, lim)
    if gate == "total":
        return c.gate_total(book, lim)
    return c.gate_full(res, lim, drop=gate.split(":", 1)[1])


GATES = ("full", "stage", "total", *[f"drop:{f}" for f in c.FAMILIES])


def main() -> int:
    t0 = time.perf_counter()
    books = c.committed_books()
    grid: dict[str, dict[str, dict[str, list[int]]]] = {}
    localisation: dict[str, list[int]] = {}
    threshold: dict[str, dict] = {}
    for ci, (name, fn) in enumerate(c.DEFECTS.items()):
        grid[name] = {f"{m:g}": {g: [0, 0] for g in GATES} for m in MULTIPLES}
        counts: list[int] = []
        ratios: list[float] = []
        for di, date in enumerate(c.DATES):
            base = books[date]
            lim0 = c.limit(base)
            for k in range(REPS):
                seed = case_seed(di, ci, k)
                for m in MULTIPLES:
                    bad = fn(base, m * lim0, np.random.default_rng(seed))
                    res, lim = c.residuals(bad), c.limit(bad)
                    verdict = {"full": c.gate_full(res, lim), "stage": c.gate_stage(res, lim), "total": c.gate_total(bad, lim)}
                    for f in c.FAMILIES:
                        verdict[f"drop:{f}"] = c.gate_full(res, lim, drop=f)
                    cell = grid[name][f"{m:g}"]
                    for g in GATES:
                        cell[g][0] += int(verdict[g])
                        cell[g][1] += 1
                    if m == 10.0:
                        counts.append(sum(1 for v in res.values() if not v <= lim))
                if k < BISECT_CASES:
                    lo, hi = 0.0, 1000.0 * lim0
                    if not flagged(fn(base, hi, np.random.default_rng(seed)), "full"):
                        continue
                    for _ in range(BISECT_STEPS):
                        mid = 0.5 * (lo + hi)
                        if flagged(fn(base, mid, np.random.default_rng(seed)), "full"):
                            hi = mid
                        else:
                            lo = mid
                    ratios.append(hi / lim0)
        localisation[name] = [int(np.min(counts)), int(np.max(counts)), float(np.mean(counts))]
        threshold[name] = {"n_bisected": len(ratios), "n_cases": BISECT_CASES * len(c.DATES),
                           "min_ratio": min(ratios) if ratios else None, "max_ratio": max(ratios) if ratios else None}
        print(f"{name:24s} bisected {len(ratios):3d} ratio {threshold[name]['min_ratio']} {threshold[name]['max_ratio']}", flush=True)
    clean = {}
    for d, b in books.items():
        r = c.residuals(b)
        clean[d] = {"n_identities": len(r), "max_residual": max(r.values()), "limit": c.limit(b), "gross": b.gross(),
                    "flagged": c.gate_full(r, c.limit(b))}
    c.save("e1_gate_power.json", {
        "meta": {"engine": version("riskvalidation"), "tolerance": c.TOLERANCE, "reps": REPS, "multiples": list(MULTIPLES),
                 "dates": list(c.DATES), "seed_base": c.SEED_BASE, "bisect_cases": BISECT_CASES, "bisect_steps": BISECT_STEPS,
                 "gates": list(GATES), "families": list(c.FAMILIES), "seconds": round(time.perf_counter() - t0, 1)},
        "grid": grid, "threshold": threshold, "identities_flagged_at_10x": localisation, "clean": clean})
    print("done in", round(time.perf_counter() - t0, 1), "s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
