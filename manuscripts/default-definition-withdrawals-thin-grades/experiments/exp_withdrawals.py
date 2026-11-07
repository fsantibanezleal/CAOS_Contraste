"""Experiment 2: informative rating withdrawals on rating paths of known truth.

The generator is the one of the case C04's ``withdrawals`` family (``riskvalidation.generators.paths.RatingPaths`` with
the EM generator of S&P's pooled CEREP counts, cohorts like S&P's: ``data/derived/C04/withdrawals.json``), withdrawal at
6% a year and at 6% (1 + k) within the year before default. Four estimators of the one-year PD by grade read the same
paired draws: the pooled cohort matrix with withdrawals removed (the transition page's treatment), with withdrawals kept
in the denominator, with withdrawals followed to the year end (EBA/GL/2017/16 paragraph 76, the end read on the latent
path), and the latent chain's own pooled PD (every obligor followed every year, the no-withdrawal reference).

Part A reproduces the four committed rungs (k = 0, 1, 3, 9; 200 repetitions; the committed seeds) and reports the largest
difference from the committed means. Part B runs the extension this manuscript needs, on seeds of its own: 1,000
repetitions per rung on k = 0, 1, 2, 3, 5, 9, 19, each estimator also on the first-year cohort alone, the IRB risk
weight of S&P's cohort mix under each estimator's PDs, and the rejection rates of the two matrix tests of the case at
k = 0, 9 and 19 over 1,000 repetitions. Run from the repository root::

    python manuscripts/default-definition-withdrawals-thin-grades/experiments/exp_withdrawals.py

It writes ``experiments/withdrawals.json`` and takes about five minutes (a draw is 0.03 s).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import zlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))
sys.path.insert(0, str(ROOT / "data-pipeline"))

import figkit  # noqa: E402
from pipeline.cases import c04_families as fam  # noqa: E402
from pipeline.cases.c05_ldp_calibration import _irb_rw  # noqa: E402

CASE_SEED = 42
COMMITTED_LADDER = (0.0, 1.0, 3.0, 9.0)
COMMITTED_REPS = 200
NEW_LADDER = (0.0, 1.0, 2.0, 3.0, 5.0, 9.0, 19.0)
NEW_REPS = 1000
TEST_LADDER = (0.0, 9.0, 19.0)
TEST_REPS = 1000
ARMS = ("removed", "kept", "followed", "latent")
GRADES = fam.GRADES
D = fam.D
YEARS = fam.YEARS


def seed_for(key: str) -> int:
    """The case's seed helper (C22's): a pure function of the case seed and the key."""
    return int(np.random.SeedSequence([CASE_SEED, zlib.crc32(key.encode("utf-8"))]).generate_state(1)[0])


def rep_estimates(latent_gen, gen, child) -> dict[str, np.ndarray]:
    """One paired draw: the four pooled estimators and their first-year-cohort versions, one PD per grade each."""
    lat = latent_gen.draw(np.random.default_rng(child))
    obs = gen.draw(np.random.default_rng(child))
    fam.truncation(lat["segments"], obs["segments"])  # the observed paths are the latent ones, cut at a withdrawal
    o, la = obs["snapshot_states"], lat["snapshot_states"]
    followed_steps = [gen.snapshot_counts(np.column_stack([o[:, t], la[:, t + 1]]))[0] for t in range(YEARS)]
    out = {
        "removed": fam._pooled(obs["steps"])["matrix"][:D, D],
        "kept": fam._pooled(obs["steps"], treatment="state")["matrix"][:D, D],
        "followed": fam._pooled(followed_steps)["matrix"][:D, D],
        "latent": fam._pooled(lat["steps"])["matrix"][:D, D],
        "removed_y1": fam._pooled(obs["steps"][:1])["matrix"][:D, D],
        "kept_y1": fam._pooled(obs["steps"][:1], treatment="state")["matrix"][:D, D],
        "followed_y1": fam._pooled(followed_steps[:1])["matrix"][:D, D],
        "latent_y1": fam._pooled(lat["steps"][:1])["matrix"][:D, D],
    }
    return out


def run_rung(q, obligors, k: float, seed: int, reps: int) -> dict[str, np.ndarray]:
    latent_gen = fam._paths(q, obligors)
    gen = fam._paths(q, obligors, withdrawal_rate=fam.WITHDRAWAL_RATE, informative=k, window=fam.WINDOW)
    store: dict[str, list] = {}
    for child in fam._children(seed, reps):
        for name, est in rep_estimates(latent_gen, gen, child).items():
            store.setdefault(name, []).append(est)
    return {name: np.array(v) for name, v in store.items()}


def rw_of(pds: np.ndarray, mix: np.ndarray) -> float:
    return float(sum(w * _irb_rw(float(p)) for p, w in zip(pds, mix) if w > 0))


def summarise(est: np.ndarray, truth: np.ndarray) -> dict:
    """Mean, bias, relative bias and their Monte Carlo standard errors by grade."""
    n = est.shape[0]
    mean = est.mean(axis=0)
    sd = est.std(axis=0, ddof=1)
    return {"n": n, "mean": mean.tolist(), "sd": sd.tolist(), "bias": (mean - truth).tolist(),
            "bias_mcse": (sd / np.sqrt(n)).tolist(), "rel_bias": ((mean - truth) / truth).tolist(),
            "rel_bias_mcse": (sd / np.sqrt(n) / truth).tolist(),
            "rmse": np.sqrt(((est - truth) ** 2).mean(axis=0)).tolist(),
            "share_zero": (est == 0).mean(axis=0).tolist()}


def main() -> None:
    t0 = time.time()
    wd = figkit.doc("C04/withdrawals.json")["outputs"]
    q = np.array(wd["generator"]["q"])
    obligors = list(wd["generator"]["obligors"])
    sp = figkit.doc("C04/sp.json")["outputs"]
    mix = np.array(sp["origination"][:7], dtype=float)
    mix = mix / mix.sum()
    truth = np.array(fam._pd(fam._paths(q, obligors)), dtype=float)
    rw_truth = rw_of(truth, mix)
    result: dict = {"case_seed": CASE_SEED, "grades": GRADES, "truth_pd": truth.tolist(), "rw_truth": rw_truth,
                    "mix": mix.tolist(), "withdrawal_rate": fam.WITHDRAWAL_RATE, "window": fam.WINDOW,
                    "obligors": obligors}

    # Part A: the committed rungs reproduced
    reproduction = []
    for k, committed in zip(COMMITTED_LADDER, wd["rungs"]):
        key = f"withdrawals:informative={k:g}"
        seed = seed_for(key)
        assert seed == committed["seed"], (seed, committed["seed"])
        est = run_rung(q, obligors, k, seed, COMMITTED_REPS)
        worst = 0.0
        for arm in ARMS:
            ref = np.array(committed[f"pd_{arm}"]["mean"], dtype=float)
            worst = max(worst, float(np.max(np.abs(est[arm].mean(axis=0) - ref))))
        reproduction.append({"k": k, "seed_key": key, "seed": seed, "reps": COMMITTED_REPS,
                             "max_abs_diff_of_means": worst})
        print(f"A k={k:g} max abs diff {worst:.3e} ({time.time() - t0:.0f}s)", flush=True)
    result["reproduction"] = reproduction

    # Part B: the extension
    rungs = []
    for k in NEW_LADDER:
        key = f"bs4:withdrawals:informative={k:g}"
        seed = seed_for(key)
        est = run_rung(q, obligors, k, seed, NEW_REPS)
        rung: dict = {"k": k, "seed_key": key, "seed": seed, "reps": NEW_REPS}
        for name, arr in est.items():
            rung[name] = summarise(arr, truth)
        # the risk weight of S&P's cohort mix under each pooled estimator's PDs
        rw = {}
        for arm in ARMS:
            vals = np.array([rw_of(p, mix) for p in est[arm]])
            rw[arm] = {"mean": float(vals.mean()), "sd": float(vals.std(ddof=1)),
                       "error": float(vals.mean() - rw_truth), "error_mcse": float(vals.std(ddof=1) / np.sqrt(NEW_REPS))}
        rung["rw"] = rw
        # the paired contrast: the withdrawal effect (removed minus latent) with the paired and the unpaired SE
        paired = {}
        for arm in ("removed", "kept", "followed"):
            diff = est[arm] - est["latent"]
            paired[arm] = {
                "mean": diff.mean(axis=0).tolist(),
                "se_paired": (diff.std(axis=0, ddof=1) / np.sqrt(NEW_REPS)).tolist(),
                "se_unpaired": (np.sqrt(est[arm].var(axis=0, ddof=1) + est["latent"].var(axis=0, ddof=1))
                                / np.sqrt(NEW_REPS)).tolist()}
        rung["paired_contrast_vs_latent"] = paired
        rungs.append(rung)
        print(f"B k={k:g} done ({time.time() - t0:.0f}s)", flush=True)
    result["rungs"] = rungs

    # the matrix tests of the case on larger repetitions
    latent_gen = fam._paths(q, obligors)
    tests = [("rating.time_homogeneity", fam._feed_periods),
             ("rating.matrix_reference",
              fam._feed_last_step(np.asarray(latent_gen.truth()["one_year_matrix"])))]
    test_rows = []
    for k in TEST_LADDER:
        gen = fam._paths(q, obligors, withdrawal_rate=fam.WITHDRAWAL_RATE, informative=k, window=fam.WINDOW)
        seed = seed_for(f"bs4:tests:informative={k:g}")
        rows = fam._simulations(gen, tests, seed=seed, reps=TEST_REPS, rung=k, label=f"k{k:g}")
        test_rows += rows
        print(f"tests k={k:g} done ({time.time() - t0:.0f}s)", flush=True)
    result["tests"] = test_rows
    result["seconds"] = round(time.time() - t0, 1)
    (HERE / "withdrawals.json").write_text(json.dumps(result, indent=1), encoding="utf-8", newline="\n")
    print("written", flush=True)


if __name__ == "__main__":
    main()
