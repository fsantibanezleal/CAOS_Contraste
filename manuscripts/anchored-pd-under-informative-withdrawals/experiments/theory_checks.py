"""Numerical checks of the propositions of the Theory section: the closed forms of the family PD(k), its limits, its
monotonicity and concavity, the bijection between k and the count of withdrawn would-be defaulters, the tipping k, the
anchor identity, and the Jeffreys-limit lemma the coverage bound uses. Deterministic (a seeded draw of counts and an
exhaustive sweep of binomial counts); writes ``experiments/results/theory-checks.json``.

Run from the repository root::

    python manuscripts/anchored-pd-under-informative-withdrawals/experiments/theory_checks.py

Exit code 0 when every check holds, 1 otherwise.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy import stats

import riskvalidation
from riskvalidation.transitions.withdrawals import (
    odds_multiplier,
    tipping_k,
    withdrawal_bounds,
    withdrawal_pd,
    withdrawn_defaulters,
)

OUT = pathlib.Path(__file__).resolve().parent / "results"
SEED = 20261104
DRAWS = 20000
N_MAX_LEMMA = 3000
LARGE_N = (5_000, 10_000, 20_000, 40_000, 100_000)   # cohort sizes checked over every count beyond N_MAX_LEMMA
LEVEL = 0.95


def random_cohorts(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Counts of a grade over a wide range: defaults 1 to 500, survivors 1 to 50,000, withdrawals 1 to 5,000."""
    d = rng.integers(1, 501, DRAWS).astype(float)
    s = np.exp(rng.uniform(0.0, np.log(50_000), DRAWS)).round().clip(1)
    w = np.exp(rng.uniform(0.0, np.log(5_000), DRAWS)).round().clip(1)
    return d, s, w


def check_closed_forms(d: np.ndarray, s: np.ndarray, w: np.ndarray) -> dict[str, float]:
    """Proposition 1: limits, monotonicity, concavity and the independent closed form."""
    n = d + s + w
    out: dict[str, float] = {}
    pd0, pd1, pdinf = (withdrawal_pd(d, s, w, k) for k in (0.0, 1.0, np.inf))
    out["limit_k0_max_abs"] = float(np.max(np.abs(pd0 - d / n)))
    out["limit_k1_max_abs"] = float(np.max(np.abs(pd1 - d / (d + s))))
    out["limit_kinf_max_abs"] = float(np.max(np.abs(pdinf - (d + w) / n)))
    grid = np.array([0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 9.0, 19.0, 49.0, 99.0, 499.0])
    pds = np.vstack([withdrawal_pd(d, s, w, k) for k in grid])
    out["strictly_increasing_share"] = float(np.mean(np.all(np.diff(pds, axis=0) > 0, axis=0)))
    # concavity of X(k) = W k D / (k D + S): the chord of three equally spaced k lies below the curve
    ks = np.array([1.0, 11.0, 21.0])
    x1, x2, x3 = (withdrawn_defaulters(d, s, w, k) for k in ks)
    out["concave_share"] = float(np.mean(x2 >= (x1 + x3) / 2.0 - 1e-12))
    k9 = 9.0
    indep = (d + w * k9 * d / (k9 * d + s)) / n
    out["independent_formula_max_abs"] = float(np.max(np.abs(withdrawal_pd(d, s, w, k9) - indep)))
    # half saturation: X(k) = W/2 at k = S/D
    half = np.array([float(withdrawn_defaulters(di, si, wi, si / di)[0]) for di, si, wi in
                     zip(d[:2000], s[:2000], w[:2000], strict=True)])
    out["half_saturation_max_abs"] = float(np.max(np.abs(half - w[:2000] / 2.0)))
    return out


def check_bijection(d: np.ndarray, s: np.ndarray, w: np.ndarray, rng: np.random.Generator) -> dict[str, float]:
    """Proposition 2: every count x in (0, W) has a unique k, and X(k(x)) = x."""
    x = rng.uniform(0.0, 1.0, d.shape) * w
    k = odds_multiplier(d, s, w, x)
    back = np.array([float(withdrawn_defaulters(di, si, wi, ki)[0]) for di, si, wi, ki in
                     zip(d[:2000], s[:2000], w[:2000], k[:2000], strict=True)])
    return {"roundtrip_max_abs_count": float(np.max(np.abs(back - x[:2000]))),
            "roundtrip_max_rel_count": float(np.max(np.abs(back - x[:2000]) / np.maximum(x[:2000], 1e-12)))}


def check_tipping(d: np.ndarray, s: np.ndarray, w: np.ndarray, rng: np.random.Generator) -> dict[str, float]:
    """Proposition 3: PD(k*) = t for a threshold t inside the identified interval, and the status labels."""
    n = d + s + w
    t = (d + rng.uniform(0.02, 0.98, d.shape) * w) / n
    k = tipping_k(d, s, w, t)
    err = np.array([abs(float(withdrawal_pd(di, si, wi, ki)[0]) - ti) for di, si, wi, ki, ti in
                    zip(d[:2000], s[:2000], w[:2000], k[:2000], t[:2000], strict=True)])
    inside = float(np.mean(np.isfinite(k)))
    below_industry = t < d / (d + s)
    res = withdrawal_bounds([[1.0, 0.0], [0.0, 0.0]], [0.0, 0.0])  # a call that must not fail on a trivial matrix
    return {"tipping_roundtrip_max_abs": float(err.max()), "tipping_finite_share": inside,
            "thresholds_below_industry_share": float(np.mean(below_industry)), "trivial_call_grades": float(len(res["grades"]))}


def check_anchor_identity(d: np.ndarray, s: np.ndarray, w: np.ndarray, rng: np.random.Generator) -> dict[str, float]:
    """Proposition 4: an exact anchor (the second source counts D + X over N) returns k and the PD(k) of the cohort."""
    errs_k, errs_pd = [], []
    for di, si, wi in zip(d[:1000], s[:1000], w[:1000], strict=True):
        k_true = float(np.exp(rng.uniform(np.log(0.05), np.log(200.0))))
        x = float(withdrawn_defaulters(di, si, wi, k_true)[0])
        n = di + si + wi
        r = withdrawal_bounds([[si, di], [0.0, 0.0]], [wi, 0.0], anchor_defaults=[round(di + x, 9)],
                              anchor_obligors=[n])
        a = r["anchor"]
        errs_k.append(abs(float(a["k"][0]) - k_true) / k_true)
        errs_pd.append(abs(float(a["pd"][0]) - (di + x) / n))
    return {"anchor_k_max_rel": float(max(errs_k)), "anchor_pd_max_abs": float(max(errs_pd))}


def check_containment(d: np.ndarray, s: np.ndarray, w: np.ndarray, rng: np.random.Generator) -> dict[str, float]:
    """Proposition 4: with an exact anchor (A = D + X over N) the anchored interval contains the Jeffreys interval of A
    among N, the interval of the oracle that follows every withdrawn rating."""
    from riskvalidation.transitions.intervals import pd_jeffreys

    bad, worst, n_chk, wider = 0, 0.0, 0, []
    for di, si, wi in zip(d[:3000], s[:3000], w[:3000], strict=True):
        x = float(rng.integers(0, int(wi) + 1))
        n = di + si + wi
        r = withdrawal_bounds([[si, di], [0.0, 0.0]], [wi, 0.0], anchor_defaults=[di + x], anchor_obligors=[n])
        jv = pd_jeffreys(np.array([di + x]), np.array([n]), level=LEVEL)
        lo_gap = float(jv["lower"][0] - r["anchor"]["lower"][0])
        hi_gap = float(r["anchor"]["upper"][0] - jv["upper"][0])
        worst = min(worst, lo_gap, hi_gap)
        bad += int(lo_gap < -1e-12 or hi_gap < -1e-12)
        wider.append((r["anchor"]["upper"][0] - r["anchor"]["lower"][0]) / (jv["upper"][0] - jv["lower"][0]))
        n_chk += 1
    return {"cohorts_checked": float(n_chk), "violations": float(bad), "min_margin": float(worst),
            "median_width_ratio": float(np.median(wider)), "max_width_ratio": float(np.max(wider))}


def check_jeffreys_lemma() -> dict[str, float]:
    """Lemma: the Jeffreys limits satisfy L(C) <= C/N <= U(C) for every count, at level 95%."""
    violations, total = 0, 0
    worst_lower, worst_upper = 0.0, 0.0
    for n in [*range(1, N_MAX_LEMMA + 1), *LARGE_N]:
        c = np.arange(0, n + 1, dtype=float)
        a, b = c + 0.5, n - c + 0.5
        lo = np.where(c > 0, stats.beta.ppf((1 - LEVEL) / 2, a, b), 0.0)
        hi = np.where(c < n, stats.beta.ppf(0.5 + LEVEL / 2, a, b), 1.0)
        p = c / n
        bad = (lo > p + 1e-12) | (hi < p - 1e-12)
        violations += int(bad.sum())
        total += n + 1
        worst_lower = max(worst_lower, float(np.max(lo - p)))
        worst_upper = max(worst_upper, float(np.max(p - hi)))
    return {"counts_checked": float(total), "violations": float(violations), "max_lower_minus_rate": worst_lower,
            "max_rate_minus_upper": worst_upper, "n_max": float(N_MAX_LEMMA), "large_n": [float(x) for x in LARGE_N]}


def main() -> int:
    rng = np.random.default_rng(SEED)
    d, s, w = random_cohorts(rng)
    results = {
        "closed_forms": check_closed_forms(d, s, w),
        "bijection": check_bijection(d, s, w, rng),
        "tipping": check_tipping(d, s, w, rng),
        "anchor_identity": check_anchor_identity(d, s, w, rng),
        "containment": check_containment(d, s, w, rng),
        "jeffreys_lemma": check_jeffreys_lemma(),
    }
    cf, bj, tp, ai, jl, ct = (results[k] for k in ("closed_forms", "bijection", "tipping", "anchor_identity", "jeffreys_lemma",
                                                    "containment"))
    ok = (cf["limit_k0_max_abs"] < 1e-12 and cf["limit_k1_max_abs"] < 1e-12 and cf["limit_kinf_max_abs"] < 1e-12
          and cf["strictly_increasing_share"] == 1.0 and cf["concave_share"] == 1.0
          and cf["independent_formula_max_abs"] < 1e-12 and cf["half_saturation_max_abs"] < 1e-6
          and bj["roundtrip_max_rel_count"] < 1e-6 and tp["tipping_roundtrip_max_abs"] < 1e-9
          and ai["anchor_k_max_rel"] < 1e-5 and ai["anchor_pd_max_abs"] < 1e-9 and jl["violations"] == 0
          and ct["violations"] == 0)
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"engine": "riskvalidation", "engine_version": riskvalidation.__version__, "seed": SEED, "draws": DRAWS,
               "level": LEVEL, "checks": results, "all_hold": bool(ok)}
    (OUT / "theory-checks.json").write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=1))
    print("all checks hold" if ok else "SOME CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
