"""E4: the non-linearity of the probability-weighted PD. Where the weighted value is at least the value at the weighted mean
factor, and how far a short scenario set is from the full distribution of the factor.

    python manuscripts/provisions-reconciliation-identities/experiments/e4_nonlinearity.py

The model is the one-factor conditional PD of the engine (``riskvalidation.provisions.term_structure.ttc_to_pit``):
``PD(z) = Phi((Phi^-1(p) - sqrt(rho) z) / sqrt(1 - rho))``. It is convex for ``z >= z* = Phi^-1(p) / sqrt(rho)`` and concave below.

Part A (sweep, 20,000 draws). Each draw is a PD ``p`` (log-uniform, 0.1% to 20%), a correlation ``rho`` (uniform, 0.01 to
0.30), two to five scenario factors (normal around a centre uniform in [-5, 1], spread uniform in [0.3, 1.5]) and Dirichlet
weights; it goes through the engine's ``ifrs9.nonlinearity_test``. Each draw is classed by where its scenario factors lie
against ``z*``: all in the convex region (convex), all in the concave region (concave), or on both sides (mixed).

Part B (scenario sets against the full distribution, 5,000 draws). The factor over the forecast horizon is normal with mean
``mu`` (uniform in [-3, 1]) and standard deviation ``sigma`` (uniform in [0.3, 1.0]); ``p`` is log-uniform from 0.5% to 10% and
``rho`` uniform from 0.05 to 0.25. The expected PD under that distribution is computed by 64-node Gauss-Hermite
quadrature (the engine's node rule). Five ways to turn the forecast into scenarios are run on the same draw: the base scenario
alone ``single``; three scenarios at ``mu - sigma, mu, mu + sigma`` with weights 25/50/25 (``adhoc3``); three at the means of the
three equal-probability tertiles with weights 1/3 (``tertile3``); the three-point and the five-point Gauss-Hermite rules
(``gh3``, ``gh5``). The error is ``(design - exact) / exact``.

Part C (the six committed C06 dates). The PD-level index recomputed with the engine from the committed scenario factors and
weights, against the committed value, and the committed ECL-level index with the Stage 2 ratio under recomputed and frozen
staging at the grid weight nearest to the committed weights.

Predictions, written before the first run of this script (the author of the unit, 2026-11-07; the notebook of the product had
swept 4,000 draws with another seed on the first claim, so N1 is a reproduction, the others are new):
  N1  convex class: no negative index in any draw;
  N2  concave class: no positive index in any draw, with at least 100 draws in the class (below that the test is vacuous);
  N3  mixed class: both signs occur;
  N4  the second-order formula ``0.5 PD''(z_bar) Var_w(z) / PD(z_bar)`` is within 25% of the index in at least 75% of the convex
      draws whose index exceeds 1e-6;
  R1  among the Part B draws whose forecast lies in the convex region with a margin of two standard deviations
      ((mu - z*) / sigma >= 2) the base scenario alone understates the expected PD in at least 99% of the draws;
  R2  the median absolute error is ordered gh5 < gh3 < tertile3 < adhoc3 < single;
  R3  for adhoc3 in those draws the second-order bias ``-0.25 PD''(mu) sigma^2`` is within 20% of the measured bias
      (design - exact) at the median of the ratio predicted / measured.
Repetitions: Part A draws seeded ``[SEED_BASE, 4, 0, draw]``, Part B ``[SEED_BASE, 4, 1, draw]``; the bootstrap intervals of the
median absolute error use 2,000 resamples seeded ``[SEED_BASE, 4, 2, design index]``.
"""
from __future__ import annotations

import math
import sys
import time
from importlib.metadata import version

import numpy as np
from scipy.special import ndtri

import common as c
from riskvalidation.provisions import ecl as ecl_engine
from riskvalidation.provisions import term_structure as ts
from riskvalidation.validation import ifrs9

DRAWS_A = 20000
DRAWS_B = 5000
SAMPLE = 4000   # the draws kept for the figure (the first ones of the sweep)
DESIGNS = ("single", "adhoc3", "tertile3", "gh3", "gh5")


def pd_second_derivative(p: float, rho: float, z: np.ndarray) -> np.ndarray:
    """PD''(z) = -(rho / (1 - rho)) u phi(u), u = (Phi^-1(p) - sqrt(rho) z) / sqrt(1 - rho): positive where u < 0 (z > z*)."""
    z = np.asarray(z, dtype=float)
    u = (ndtri(p) - math.sqrt(rho) * z) / math.sqrt(1.0 - rho)
    return -(rho / (1.0 - rho)) * u * np.exp(-0.5 * u * u) / math.sqrt(2.0 * math.pi)


def part_a() -> dict:
    counts = {k: {"n": 0, "negative": 0, "positive": 0, "zero": 0, "red": 0, "min": math.inf, "max": -math.inf} for k in ("convex", "concave", "mixed")}
    ratios: list[float] = []
    sample: list[list] = []
    gh_error_max = 0.0
    for k in range(DRAWS_A):
        rng = np.random.default_rng([c.SEED_BASE, 4, 0, k])
        p = float(np.exp(rng.uniform(math.log(0.001), math.log(0.2))))
        rho = float(rng.uniform(0.01, 0.30))
        n = int(rng.integers(2, 6))
        z = rng.normal(rng.uniform(-5.0, 1.0), rng.uniform(0.3, 1.5), n)
        w = rng.dirichlet(np.ones(n))
        res = ifrs9.nonlinearity_test(p, rho, z, w)
        zstar = float(ndtri(p) / math.sqrt(rho))
        cls = "convex" if bool(np.all(z >= zstar)) else "concave" if bool(np.all(z <= zstar)) else "mixed"
        idx = float(res.metric)
        cell = counts[cls]
        cell["n"] += 1
        cell["negative"] += int(idx < 0)
        cell["positive"] += int(idx > 0)
        cell["zero"] += int(idx == 0)
        cell["red"] += int(res.light.value == "red")
        cell["min"], cell["max"] = min(cell["min"], idx), max(cell["max"], idx)
        gh_error_max = max(gh_error_max, float(res.extras["gauss_hermite_error"]))
        if k < SAMPLE:
            sample.append([round(float(np.sum(w * z)), 4), idx, cls])
        if cls == "convex" and idx > 1e-6:
            zbar = float(np.sum(w * z))
            var = float(np.sum(w * (z - zbar) ** 2))
            approx = 0.5 * float(pd_second_derivative(p, rho, np.array([zbar]))[0]) * var / float(ts.ttc_to_pit(np.array([p]), rho, np.array([zbar]))[0])
            ratios.append(approx / idx)
    for cell in counts.values():
        for key in ("min", "max"):
            cell[key] = None if not math.isfinite(cell[key]) else cell[key]
    r = np.array(ratios)
    within = float(np.mean(np.abs(r - 1.0) <= 0.25)) if r.size else None
    return {"draws": DRAWS_A, "sample": sample, "classes": counts, "gauss_hermite_error_max": gh_error_max,
            "second_order": {"n": int(r.size), "within_25pct": within, "ratio_q05": float(np.quantile(r, 0.05)), "ratio_q50": float(np.quantile(r, 0.5)),
                             "ratio_q95": float(np.quantile(r, 0.95))}}


def design_values(p: float, rho: float, mu: float, sigma: float) -> dict[str, float]:
    def pit(z: np.ndarray) -> np.ndarray:
        return ts.ttc_to_pit(np.full(np.size(z), p), rho, np.asarray(z, dtype=float))

    nodes, wts = np.polynomial.hermite_e.hermegauss(64)
    exact = float(np.sum(wts / math.sqrt(2.0 * math.pi) * pit(mu + sigma * nodes)))
    out = {"exact": exact, "single": float(pit(np.array([mu]))[0])}
    out["adhoc3"] = float(ecl_engine.probability_weighted_ecl(pit(mu + sigma * np.array([-1.0, 0.0, 1.0])), np.array([0.25, 0.5, 0.25])))
    t = float(np.exp(-0.5 * ndtri(1.0 / 3.0) ** 2) / math.sqrt(2.0 * math.pi) / (1.0 / 3.0))     # mean of the lower tertile of N(0,1), in magnitude
    out["tertile3"] = float(ecl_engine.probability_weighted_ecl(pit(mu + sigma * np.array([-t, 0.0, t])), np.full(3, 1.0 / 3.0)))
    for name, m in (("gh3", 3), ("gh5", 5)):
        nd, wg = np.polynomial.hermite_e.hermegauss(m)
        out[name] = float(ecl_engine.probability_weighted_ecl(pit(mu + sigma * nd), wg / wg.sum()))
    return out


def part_b() -> dict:
    err = {d: [] for d in DESIGNS}
    margin: list[float] = []
    bias_pred: list[float] = []
    bias_meas: list[float] = []
    for k in range(DRAWS_B):
        rng = np.random.default_rng([c.SEED_BASE, 4, 1, k])
        p = float(np.exp(rng.uniform(math.log(0.005), math.log(0.10))))
        rho = float(rng.uniform(0.05, 0.25))
        mu = float(rng.uniform(-3.0, 1.0))
        sigma = float(rng.uniform(0.3, 1.0))
        v = design_values(p, rho, mu, sigma)
        for d in DESIGNS:
            err[d].append((v[d] - v["exact"]) / v["exact"])
        zstar = float(ndtri(p) / math.sqrt(rho))
        margin.append((mu - zstar) / sigma)
        bias_pred.append(-0.25 * float(pd_second_derivative(p, rho, np.array([mu]))[0]) * sigma ** 2)
        bias_meas.append(v["adhoc3"] - v["exact"])
    margin_a = np.array(margin)
    strong = margin_a >= 2.0
    out: dict = {"draws": DRAWS_B, "strong_margin_draws": int(strong.sum()), "designs": {}}
    for di, d in enumerate(DESIGNS):
        e = np.array(err[d])
        boot_rng = np.random.default_rng([c.SEED_BASE, 4, 2, di])
        meds = [float(np.median(np.abs(boot_rng.choice(e, e.size)))) for _ in range(2000)]
        out["designs"][d] = {
            "quantiles": {f"q{int(q * 100):02d}": float(np.quantile(e, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
            "median_abs": float(np.median(np.abs(e))), "median_abs_ci": [float(np.quantile(meds, 0.025)), float(np.quantile(meds, 0.975))],
            "share_abs_above_5pct": float(np.mean(np.abs(e) > 0.05)), "share_negative": float(np.mean(e < 0)),
            "share_negative_strong_margin": float(np.mean(e[strong] < 0)), "median_abs_strong_margin": float(np.median(np.abs(e[strong])))}
    ratio = np.array(bias_pred)[strong] / np.array(bias_meas)[strong]
    out["adhoc3_bias_ratio_predicted_over_measured"] = {"q05": float(np.quantile(ratio, 0.05)), "q50": float(np.quantile(ratio, 0.5)),
                                                          "q95": float(np.quantile(ratio, 0.95)), "within_20pct": float(np.mean(np.abs(ratio - 1) <= 0.2))}
    return out


def part_c() -> dict:
    out = {}
    for d in c.DATES:
        art = c.doc(f"C06/rd-{d}.json")["outputs"]
        nl = art["non_linearity"]
        pts = nl["scenario_points"]
        z = np.array([s["z"] for s in pts])
        w = np.array([s["weight"] for s in pts])
        p, rho = nl["parameters"]["pd_ttc"], nl["parameters"]["rho"]
        res = ifrs9.nonlinearity_test(p, rho, z, w)
        zstar = float(ndtri(p) / math.sqrt(rho))
        grid = art["weight_grid"]["points"]
        w0 = np.array(w)
        near = min(grid, key=lambda g: float(np.sum((np.array(g["weights"]) - w0) ** 2)))
        out[d] = {"pd_ttc": p, "rho": rho, "zstar": zstar, "z_min": float(z.min()), "z_max": float(z.max()), "weights": [float(x) for x in w],
                  "pd_index_committed": nl["pd_weighted"] / nl["pd_at_mean_z"] - 1.0, "pd_index_engine": float(res.metric),
                  "pd_index_agreement": abs(float(res.metric) - (nl["pd_weighted"] / nl["pd_at_mean_z"] - 1.0)),
                  "ecl_index": nl["index"], "ecl_index_engine": ecl_engine.non_linearity_index(nl["ecl_weighted"], nl["ecl_at_mean_path"]),
                  "stage2_ratio_recomputed": near["stage2_ratio_recomputed"], "stage2_ratio_frozen": near["stage2_ratio_frozen"],
                  "grid_weights": near["weights"], "stage2_gap": abs(near["stage2_ratio_recomputed"] - near["stage2_ratio_frozen"]),
                  "stage2_ratio_committed": art["stage_summary"]["rows"][1]["gross_carrying_amount"] / math.fsum(r["gross_carrying_amount"] for r in art["stage_summary"]["rows"])}
    return out


def reference_example() -> dict:
    """The worked example of the engine's documentation: p = 2%, rho = 0.12, z = (+1, 0, -2), weights (0.25, 0.5, 0.25)."""
    r = ifrs9.nonlinearity_test(0.02, 0.12, np.array([1.0, 0.0, -2.0]), np.array([0.25, 0.5, 0.25]))
    return {"pd_weighted": r.extras["pd_weighted"], "pd_at_mean_z": r.extras["pd_at_mean_z"], "index": float(r.metric), "light": r.light.value}


def main() -> int:
    t0 = time.perf_counter()
    payload = {"meta": {"engine": version("riskvalidation"), "draws_a": DRAWS_A, "draws_b": DRAWS_B, "seed_base": c.SEED_BASE},
               "example": reference_example(), "sweep": part_a(), "designs": part_b(), "committed": part_c()}
    payload["meta"]["seconds"] = round(time.perf_counter() - t0, 1)
    c.save("e4_nonlinearity.json", payload)
    print("done in", payload["meta"]["seconds"], "s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
