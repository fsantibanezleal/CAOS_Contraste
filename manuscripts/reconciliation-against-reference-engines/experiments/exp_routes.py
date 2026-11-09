"""Independent routes for the p-values of the Jeffreys and binomial tests, and the planted defects that separate three kinds of
reference.

    python manuscripts/reconciliation-against-reference-engines/experiments/exp_routes.py [--out results_routes.json]

The engine computes the Jeffreys p-value as ``scipy.stats.beta.cdf(pd, d + 1/2, n - d + 1/2)`` and the binomial p-value as
``scipy.stats.binom.sf(d - 1, n, pd)`` (through its helper ``default_count_sf``). Two references call neither SciPy function:

* ``quadrature``: the Beta density integrated from 0 to the applied PD, after the substitution x = p u^2 that removes the
  singularity at 0, with a 400-point Gauss-Legendre rule, divided by the Beta function written with ``math.lgamma``;
* ``exact_sum``: one minus the sum of the first d binomial terms in rational arithmetic (``fractions.Fraction`` of the float PD),
  rounded once at the end.

Part 1 compares the engine with both on the grid of 36 cases of the product's notebook and on 600 cases drawn with a fixed seed.
Part 2 plants defects and runs three kinds of reference against the defective engine:

* C1 reuse: the engine's own helper, or the same SciPy call with the engine's parameters (what a test that imports the
  implementation under test computes);
* C2 same library, parameters from the definition: ``binom.sf(d - 1, n, pd)`` and ``beta.cdf(pd, d + 1/2, n - d + 1/2)`` written
  from the definition of the test;
* C3 independent: the two routes above.

The planted defects are (P1) the tail convention of the binomial helper moved by one (``sf(k)`` in place of ``sf(k - 1)``), and
(P2) a relative error of size eps inside the SciPy function itself (``scipy.stats.beta.cdf`` and ``scipy.stats.binom.sf``
multiplied by 1 + eps and capped at 1, because the engine refuses a p-value above 1), with eps from 1e-12 to 1e-3. A reference flags a defect when its largest absolute difference to the engine
on the 36-case grid exceeds the tolerance 1e-9.
"""
from __future__ import annotations

import argparse
import functools
import math
import pathlib
from fractions import Fraction

import numpy as np
from scipy import stats

import common as cm

from riskvalidation.validation import calibration as cal

HERE = pathlib.Path(__file__).resolve().parent
TOL = 1e-9
GRID = [(n, d, p) for n in (50, 500, 5000) for d in (0, 1, 3, 10) for p in (0.001, 0.01, 0.05)]
NODES, WEIGHTS = np.polynomial.legendre.leggauss(400)
U, W = (NODES + 1) / 2, WEIGHTS / 2


@functools.lru_cache(maxsize=None)
def quadrature(n: int, d: int, p: float) -> float:
    """The Jeffreys p-value as the integral of the Beta(d + 1/2, n - d + 1/2) density from 0 to p."""
    a, b = d + 0.5, n - d + 0.5
    integral = 2 * p**a * float(np.sum(W * U ** (2 * d) * (1 - p * U**2) ** (b - 1)))
    return integral / math.exp(math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b))


@functools.lru_cache(maxsize=None)
def exact_sum(n: int, d: int, p: float) -> float:
    """P(D >= d) as one minus the exact rational sum of the first d binomial terms."""
    q = Fraction(p)
    return float(1 - sum(math.comb(n, k) * q**k * (1 - q) ** (n - k) for k in range(d)))


def engine_j(n: int, d: int, p: float) -> float:
    return cal.pd_jeffreys(n=n, d=d, pd=p).p_value


def engine_b(n: int, d: int, p: float) -> float:
    return cal.pd_binomial(n=n, d=d, pd=p).p_value


def gaps(grid, engine, reference) -> list[float]:
    return [abs(engine(*c) - reference(*c)) for c in grid]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results_routes.json"))
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--random-cases", type=int, default=600)
    args = ap.parse_args()

    # ------------------------------------------------------------------ part 1: the grid and a random set
    gj, gb = gaps(GRID, engine_j, quadrature), gaps(GRID, engine_b, exact_sum)
    same_j = gaps(GRID, engine_j, lambda n, d, p: float(stats.beta.cdf(p, d + 0.5, n - d + 0.5)))
    same_b = gaps(GRID, engine_b, lambda n, d, p: float(stats.binom.sf(d - 1, n, p)) if d > 0 else 1.0)
    rng = np.random.default_rng(args.seed)
    cases = []
    while len(cases) < args.random_cases:
        n = int(np.exp(rng.uniform(math.log(10), math.log(5000))))
        d = int(rng.integers(0, min(n, 50) + 1))
        p = float(np.exp(rng.uniform(math.log(1e-4), math.log(0.3))))
        if d <= n:
            cases.append((n, d, p))
    rj, rb = gaps(cases, engine_j, quadrature), gaps(cases, engine_b, exact_sum)
    part1 = {"grid": [list(c) for c in GRID], "grid_gaps_jeffreys": gj, "grid_gaps_binomial": gb, "grid_cases": len(GRID), "jeffreys_max_gap": max(gj), "binomial_max_gap": max(gb),
             "within_tol_grid": int(sum(x < TOL for x in gj + gb)), "grid_comparisons": 2 * len(GRID),
             "same_call_max_gap_jeffreys": max(same_j), "same_call_max_gap_binomial": max(same_b),
             "random_cases": len(cases), "random_seed": args.seed,
             "random_jeffreys_max_gap": max(rj), "random_binomial_max_gap": max(rb),
             "random_within_tol": int(sum(x < TOL for x in rj + rb)), "random_comparisons": 2 * len(cases),
             "random_jeffreys_fail": [{"n": c[0], "d": c[1], "p": c[2], "gap": g} for c, g in zip(cases, rj, strict=True) if g >= TOL][:10],
             "random_binomial_fail": [{"n": c[0], "d": c[1], "p": c[2], "gap": g} for c, g in zip(cases, rb, strict=True) if g >= TOL][:10]}

    # ------------------------------------------------------------------ part 2: planted defects
    helper_original = cal.default_count_sf
    beta_cdf_original, binom_sf_original = stats.beta.cdf, stats.binom.sf

    def helper_off_by_one(k: int, n: int, pd: float, rho: float = 0.0) -> float:
        return float(stats.binom.sf(k, n, pd)) if k > 0 else 1.0     # the tail convention moved by one

    def run_reference_set(eps: float | None, helper_defect: bool) -> dict:
        """The largest differences of the engine to the three kinds of reference under one planted defect."""
        # C1 reuse
        c1_b = max(abs(engine_b(*c) - cal.default_count_sf(c[1], c[0], c[2])) for c in GRID)
        c1_j = max(abs(engine_j(*c) - float(stats.beta.cdf(c[2], c[1] + 0.5, c[0] - c[1] + 0.5))) for c in GRID)
        # C2 same library, parameters from the definition
        c2_b = max(abs(engine_b(*c) - (float(stats.binom.sf(c[1] - 1, c[0], c[2])) if c[1] > 0 else 1.0)) for c in GRID)
        c2_j = c1_j     # for the Jeffreys test the definition and the engine's call coincide
        # C3 independent
        c3_b = max(gaps(GRID, engine_b, exact_sum))
        c3_j = max(gaps(GRID, engine_j, quadrature))
        return {"eps": eps, "helper_defect": helper_defect,
                "C1_binomial": c1_b, "C1_jeffreys": c1_j, "C2_binomial": c2_b, "C2_jeffreys": c2_j, "C3_binomial": c3_b, "C3_jeffreys": c3_j,
                "flag": {k: bool(v > TOL) for k, v in {"C1_binomial": c1_b, "C1_jeffreys": c1_j, "C2_binomial": c2_b, "C2_jeffreys": c2_j,
                                                       "C3_binomial": c3_b, "C3_jeffreys": c3_j}.items()}}

    baseline = run_reference_set(None, False)
    cal.default_count_sf = helper_off_by_one           # the engine's functions look the helper up in the module at call time
    p1 = run_reference_set(None, True)
    cal.default_count_sf = helper_original
    p2 = []
    try:
        for eps in (1e-12, 1e-11, 1e-10, 1e-9, 1e-8, 1e-6, 1e-4, 1e-3):
            stats.beta.cdf = lambda x, a, b, _f=beta_cdf_original, _e=eps: np.minimum(_f(x, a, b) * (1.0 + _e), 1.0)
            stats.binom.sf = lambda k, n, p, _f=binom_sf_original, _e=eps: np.minimum(_f(k, n, p) * (1.0 + _e), 1.0)
            p2.append(run_reference_set(eps, False))
    finally:
        stats.beta.cdf, stats.binom.sf = beta_cdf_original, binom_sf_original
        cal.default_count_sf = helper_original
    # the smallest eps flagged in at least one case by the independent routes, and the largest p-value on the grid
    max_p_j = max(engine_j(*c) for c in GRID)
    max_p_b = max(engine_b(*c) for c in GRID)
    after = run_reference_set(None, False)
    assert after["C3_jeffreys"] < TOL and after["C3_binomial"] < TOL, "the patched functions were not restored"
    out = {"tolerance": TOL, "part1": part1, "baseline": baseline, "defect_tail_convention": p1, "defect_relative": p2,
           "max_p_value_grid": {"jeffreys": max_p_j, "binomial": max_p_b},
           "quadrature_nodes": int(NODES.size)}
    cm.write(pathlib.Path(args.out), out)
    print(part1)
    print("baseline", baseline["flag"], "P1", p1["flag"], p1["C1_binomial"], p1["C2_binomial"], p1["C3_binomial"])
    for r in p2:
        print(r["eps"], {k: f"{r[k]:.1e}" for k in ("C1_binomial", "C2_binomial", "C3_binomial", "C1_jeffreys", "C3_jeffreys")}, r["flag"]["C3_binomial"], r["flag"]["C3_jeffreys"])


if __name__ == "__main__":
    main()
