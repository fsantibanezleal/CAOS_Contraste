"""Experiment 4: the closed forms of the Theory section against the engine's simulation, on a two-state chain.

On a chain with one performing grade and default (generator [[-lam, lam], [0, 0]]) the expected counts of every
withdrawal treatment have closed forms (Proposition 1 and 2 of the Theory section). This script evaluates them by
numerical quadrature and compares them with the pooled estimators of ``riskvalidation`` on paired draws of
``RatingPaths`` (``informative`` k, ``window`` 1 year, withdrawal rate 6%). The two chains are the PDs of B and of
CCC to C of the C04 generator (one-year PD 1.1731% and 8.0618%).

Prediction stated before the run: the simulated mean of each estimator, pooled over the five annual cohorts and on
the first-year cohort, lies within three Monte Carlo standard errors of its closed form.

Run from the repository root::

    python manuscripts/default-definition-withdrawals-thin-grades/experiments/exp_theory.py

It writes ``experiments/theory.json`` and takes about ten minutes.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
import time
import zlib

import numpy as np
from scipy.integrate import quad

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))
sys.path.insert(0, str(ROOT / "data-pipeline"))

import figkit  # noqa: E402
from riskvalidation.generators.paths import RatingPaths  # noqa: E402
from riskvalidation.transitions.estimators import pooled_cohort  # noqa: E402

CASE_SEED = 42
W = 0.06
WINDOW = 1.0
T = 5
K_LADDER = (0.0, 1.0, 3.0, 9.0, 19.0)
CHAINS = {"B": {"grade": 5, "n": 100000, "reps": 40}, "CCC-C": {"grade": 6, "n": 50000, "reps": 40}}


def overlap(tau: float, a: float, b: float) -> float:
    """Length of the intersection of the elevated window (tau - 1, tau) with (a, b); none where tau lies beyond T."""
    if tau > T:
        return 0.0
    return max(0.0, min(b, tau) - max(a, tau - WINDOW))


def surv(tau: float, b: float, k: float) -> float:
    """P(not withdrawn over (0, b)) for a name that defaults at tau (b <= tau), withdrawal hazard w, w (1 + k) in the
    window before default."""
    return math.exp(-W * (b + k * overlap(tau, 0.0, b)))


def integral(f, lo: float, hi: float) -> float:
    pts = sorted({x for x in (lo + 1.0, hi - 1.0, lo + 2.0, hi) if lo < x < hi})
    val, _ = quad(f, lo, hi, points=pts or None, limit=200, epsabs=1e-14, epsrel=1e-12)
    return val


def cohort_masses(lam: float, k: float, t: int) -> dict[str, float]:
    """Expected shares of the initial obligors in the cohort that starts at year t (outstanding then), and their
    outcomes over (t, t + 1]: observed default D, survivor S, and the defaults a follow-up of the withdrawn would add."""
    dens = lambda tau: lam * math.exp(-lam * tau)  # noqa: E731
    tail = math.exp(-lam * T)
    # outstanding at t: default time beyond t and not withdrawn on (0, t); a default beyond T has no window
    out = integral(lambda s: dens(s) * surv(s, t, k), t, T) + tail * math.exp(-W * t) if t > 0 else 1.0
    d_obs = integral(lambda s: dens(s) * surv(s, s, k), t, t + 1)
    s_end = integral(lambda s: dens(s) * surv(s, t + 1, k), t + 1, T) + tail * math.exp(-W * (t + 1))
    d_followed = integral(lambda s: dens(s) * surv(s, t, k), t, t + 1) if t > 0 else \
        integral(lambda s: dens(s), 0, 1)
    return {"outstanding": out, "defaults": d_obs, "survivors": s_end, "defaults_followed": d_followed}


def closed_form(lam: float, k: float) -> dict[str, dict[str, float]]:
    """The expected value of each estimator, pooled over the T - 1 + 1 = five annual cohorts (counts summed, as
    Anderson and Goodman's (2.8) does) and on the first-year cohort."""
    masses = [cohort_masses(lam, k, t) for t in range(T)]

    def arms(ms: list[dict[str, float]]) -> dict[str, float]:
        d = sum(m["defaults"] for m in ms)
        s = sum(m["survivors"] for m in ms)
        n = sum(m["outstanding"] for m in ms)
        f = sum(m["defaults_followed"] for m in ms)
        return {"removed": d / (d + s), "kept": d / n, "followed": f / n, "latent": 1.0 - math.exp(-lam)}

    return {"pooled": arms(masses), "first_year": arms(masses[:1])}


def seed_for(key: str) -> int:
    return int(np.random.SeedSequence([CASE_SEED, zlib.crc32(key.encode("utf-8"))]).generate_state(1)[0])


def simulate(lam: float, k: float, n: int, reps: int, seed: int) -> dict[str, np.ndarray]:
    q = np.array([[-lam, lam], [0.0, 0.0]])
    snaps = tuple(float(t) for t in range(T + 1))
    lat_gen = RatingPaths(q, (n,), horizon=float(T), snapshots=snaps)
    gen = RatingPaths(q, (n,), horizon=float(T), snapshots=snaps, withdrawal_rate=W, informative=k, window=WINDOW)
    store: dict[str, list] = {a: [] for a in ("removed", "kept", "followed", "latent", "removed_y1", "kept_y1",
                                              "followed_y1", "latent_y1")}
    for child in np.random.SeedSequence(seed).spawn(reps):
        lat = lat_gen.draw(np.random.default_rng(child))
        obs = gen.draw(np.random.default_rng(child))
        o, la = obs["snapshot_states"], lat["snapshot_states"]
        fsteps = [gen.snapshot_counts(np.column_stack([o[:, t], la[:, t + 1]]))[0] for t in range(T)]

        def pooled(steps, treatment="exclude") -> float:
            return float(pooled_cohort([s["counts"] for s in steps], [s["withdrawn"] for s in steps],
                                       treatment=treatment)["matrix"][0, 1])

        store["removed"].append(pooled(obs["steps"]))
        store["kept"].append(pooled(obs["steps"], "state"))
        store["followed"].append(pooled(fsteps))
        store["latent"].append(pooled(lat["steps"]))
        store["removed_y1"].append(pooled(obs["steps"][:1]))
        store["kept_y1"].append(pooled(obs["steps"][:1], "state"))
        store["followed_y1"].append(pooled(fsteps[:1]))
        store["latent_y1"].append(pooled(lat["steps"][:1]))
    return {a: np.array(v) for a, v in store.items()}


def main() -> None:
    t0 = time.time()
    pd_b = figkit.doc("C04/withdrawals.json")["outputs"]["generator"]["pd_1y"]
    out: dict = {"withdrawal_rate": W, "window": WINDOW, "years": T, "ladder": list(K_LADDER), "chains": {}}
    for name, spec in CHAINS.items():
        p = float(pd_b[spec["grade"]])
        lam = -math.log(1.0 - p)
        rows = []
        for k in K_LADDER:
            cf = closed_form(lam, k)
            seed = seed_for(f"bs4:theory:{name}:k={k:g}")
            sim = simulate(lam, k, spec["n"], spec["reps"], seed)
            row = {"k": k, "seed": seed, "reps": spec["reps"], "obligors": spec["n"], "closed_form": cf, "simulated": {}}
            for arm in ("removed", "kept", "followed", "latent"):
                for scope, suffix in (("pooled", ""), ("first_year", "_y1")):
                    x = sim[arm + suffix]
                    mean, se = float(x.mean()), float(x.std(ddof=1) / math.sqrt(x.size))
                    exact = cf[scope][arm]
                    row["simulated"].setdefault(scope, {})[arm] = {
                        "mean": mean, "mcse": se, "closed_form": exact, "z": (mean - exact) / se if se > 0 else 0.0,
                        "rel_bias_closed_form": exact / p - 1.0, "rel_bias_sim": mean / p - 1.0,
                        "rel_bias_mcse": se / p}
            rows.append(row)
            print(f"{name} k={k:g} done ({time.time() - t0:.0f}s)", flush=True)
        out["chains"][name] = {"p": p, "lambda": lam, "rows": rows}
    # the limit k -> infinity of the first-year removed estimator, on both chains (a closed form, no simulation)
    out["limits_first_year"] = {name: {"k_1e6_removed": closed_form(out["chains"][name]["lambda"], 1e6)["first_year"]["removed"],
                                       "k_1e6_kept": closed_form(out["chains"][name]["lambda"], 1e6)["first_year"]["kept"]}
                                for name in CHAINS}
    out["seconds"] = round(time.time() - t0, 1)
    (HERE / "theory.json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    zs = [v["z"] for ch in out["chains"].values() for r in ch["rows"] for s in r["simulated"].values() for v in s.values()]
    print("max |z|", max(abs(z) for z in zs), "n", len(zs))


if __name__ == "__main__":
    main()
