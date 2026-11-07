"""The experiments this manuscript adds to the committed known-truth study of the anchored PD under informative rating
withdrawals (``data-pipeline/pipeline/cases/c04_bounds.py``, 200 repetitions, informative 0, 1, 3 and 9).

Run from the repository root::

    python manuscripts/anchored-pd-under-informative-withdrawals/experiments/extended_study.py

It calls the engine ``riskvalidation`` 1.1.0 (``transitions.withdrawals``, ``transitions.intervals``,
``transitions.estimators``, ``generators.paths``) and the product's own generator settings (the EM generator of S&P's
pooled counts stored in ``data/derived/C04/withdrawals.json``, withdrawal at 6% a year and 6% times (1 + informative) in
the year before default, the 2000 to 2025 cohort sizes of that generator). Every draw has a seed of its own, a pure
function of the case seed 42 and the key ``ms-bs14:...``, so no number of the committed documents moves.

Five studies, written to ``experiments/results/``:

``coverage-grid.json``
    informative 0, 1, 3, 9 and 19; the first-year cohort, the five annual cohorts pooled, the cohort ten times larger;
    1,000 repetitions; the existing treatments (industry k 1, unfollowed k 0, followed), the identified (Manski) band,
    the band of the anchored k alone and the anchored interval. Coverage of the true one-year PD of every grade, mean
    width, relative bias and relative root-mean-square error of the point estimate.
``scale-ladder.json``
    the first-year cohort at informative 9 for cohorts 1, 3, 10 and 30 times the case's.
``capture-ladder.json``
    a second source that counts a share of the true defaults (0.5 to 0.9) or more than they are (1.1, 1.3): coverage,
    bias and the anchored k against the realised k, at informative 3 and 9.
``stability.json``
    on known truth, the share of the five annual cohorts whose anchored k band contains the pooled anchored k (the
    stability criterion applied to the real cohorts), with the second source exact, counting 1.3 times the defaults in
    every year, and counting a multiple drawn each year from 1.0 to 1.6 or from 1.0 to 4.0 (a definition gap that
    changes from year to year); informative 3 and 9; BB, B and CCC to C.
``decisions`` (inside every cell of the coverage grid and of the scale ladder)
    the decision taken at a threshold t = truth (1 + delta): the share of repetitions in which the interval of each
    treatment lies on the correct side, on the wrong side, or across the threshold.
``duration.json``
    the continuous-time duration estimator that treats withdrawals as independent right censoring (Lando and Skodeberg
    2002): relative bias of grade B's PD and coverage of its resampling bootstrap interval. It runs on the draws of the
    coverage grid: the same seed key (``ms-bs14:informative=<iota>``), the same child streams and the same number of
    repetitions; the paths it reads are the grid's observed paths, and only the bootstrap draws come from a second
    stream of their own.
``run-times.json``
    the elapsed seconds of every study that was run, the cost of one call of the method on a cohort, and the machine and
    library versions, all measured by this script (``--only timing`` measures the cost of the call alone).

A study at the default repetitions is timed in ``run-times.json``; ``--reps``, ``--reps-scale`` and ``--reps-duration``
shorten it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import platform
import sys
import time
import warnings
from typing import Any

import numpy as np
from scipy.linalg import expm

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import riskvalidation  # noqa: E402
from riskvalidation.transitions.estimators import duration_generator  # noqa: E402
from riskvalidation.transitions.intervals import pd_bootstrap, pd_jeffreys  # noqa: E402
from riskvalidation.transitions.withdrawals import odds_multiplier, withdrawal_bounds  # noqa: E402

from pipeline.cases import c04_bounds as bnd  # noqa: E402
from pipeline.cases import c04_families as fam  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "results"
CASE_SEED = 42
LEVEL = 0.95
G = 7                                   # the performing grades
M = 8                                   # seven grades and default
B = bnd.B                               # grade B, where the plan's hypothesis is read
GRADES = list(bnd.GRADES)
INFORMATIVE = (0.0, 1.0, 3.0, 9.0, 19.0)
CAPTURES = (0.5, 0.7, 0.8, 0.9, 1.1, 1.3)
SCALES = (3, 10, 30)
DELTAS = (-0.3, -0.15, 0.15, 0.3)
TREATMENTS = ("industry", "unfollowed", "followed", "identified", "band", "anchored")
WITHDRAWAL_RATE, WINDOW = 0.06, 1.0
STABILITY_GRADES = (4, 5, 6)           # BB, B, CCC to C
STABILITY_AT = (3.0, 9.0)              # the informativeness values the stability study is run at
#: the second source of the stability study: exact, 1.3 times the defaults every year, a multiple of the followed
#: cohort's defaults drawn from 1.0 to 1.6 or from 1.0 to 4.0 each year, and a multiple of the defaults the transition
#: page observes drawn each year from 1.6 to 7.0, the range of the ratio of the default page's rate to the transition
#: page's rate of S&P's grade B over its 25 cohorts with defaults (data/derived/C04/sp.json, grade B, 1.62 to 7.00);
#: (capture, label). A capture ``("d", lo, hi)`` scales the observed defaults D, the scale of that ratio.
STABILITY_CAPTURES: tuple[tuple[Any, str], ...] = ((1.0, "1"), (1.3, "1.3"), ((1.0, 1.6), "u1.0-1.6"), ((1.0, 4.0), "u1.0-4.0"),
                                                   (("d", 1.6, 7.0), "d1.6-7.0"))


def seed_of(key: str) -> int:
    """A seed that is a pure function of the case seed and the key (the pipeline's helper)."""
    return fam._seed(CASE_SEED, key)


def load_generator() -> tuple[np.ndarray, list[int]]:
    g = json.loads((ROOT / "data" / "derived" / "C04" / "withdrawals.json").read_text(encoding="utf-8"))["outputs"]["generator"]
    return np.asarray(g["q"], dtype=float), [int(x) for x in g["obligors"]]


def r4(x: Any) -> Any:
    """A float rounded for the JSON (NaN and infinity become None)."""
    if x is None:
        return None
    v = float(x)
    return round(v, 5) if math.isfinite(v) else None


def rl(a: Any) -> list[Any]:
    return [r4(x) for x in np.asarray(a, dtype=float)]


# ---------------------------------------------------------------------------------------------------------------------
# one repetition


def draw(latent: Any, observed: Any, child: np.random.SeedSequence) -> tuple[list[dict[str, Any]], list[np.ndarray]]:
    """The observed annual steps and, for each year, the defaults the default page counts: the cohort as observed at the
    year's start, its end read on the latent path (the study of c04_bounds, repeated)."""
    lat = latent.draw(np.random.default_rng(child))
    obs = observed.draw(np.random.default_rng(child))
    o, la = obs["snapshot_states"], lat["snapshot_states"]
    steps = obs["steps"]
    follow = [latent.snapshot_counts(np.column_stack([o[:, t], la[:, t + 1]]))[0]["counts"][:, M - 1][:G]
              for t in range(len(steps))]
    return steps, follow


def make_anchor(followed: np.ndarray, n: np.ndarray, capture: Any, rng: np.random.Generator,
                observed: np.ndarray | None = None) -> np.ndarray:
    """The second source's count: the true defaults thinned (capture below 1: it counts a share of them) or inflated
    (above 1: it counts the defaults and, besides, a Poisson number of other events at (capture - 1) times them). A
    capture ``("d", lo, hi)`` is a multiple drawn from lo to hi of the defaults the transition page observes (rounded,
    at most the cohort)."""
    if isinstance(capture, tuple) and capture[0] == "d":
        return np.minimum(np.round(float(rng.uniform(capture[1], capture[2])) * observed), n)
    if isinstance(capture, tuple):
        capture = float(rng.uniform(capture[0], capture[1]))
    if capture == 1.0:
        return followed.copy()
    if capture < 1.0:
        return rng.binomial(followed.astype(int), capture).astype(float)
    return np.minimum(followed + rng.poisson((capture - 1.0) * followed), n)


def evaluate(counts: np.ndarray, withdrawn: np.ndarray, followed: np.ndarray, anchor: np.ndarray) -> dict[str, Any]:
    """Each treatment's (lower, upper, point) by grade for one cohort, and the anchored k."""
    res = withdrawal_bounds(counts, withdrawn, anchor_defaults=anchor, level=LEVEL)
    d, s, w, n = res["defaults"], res["survivors"], res["withdrawn"], res["n"]
    out: dict[str, Any] = {}
    for name, (num, den) in {"industry": (d, d + s), "unfollowed": (d, n), "followed": (followed, n)}.items():
        iv = pd_jeffreys(num, den, level=LEVEL)
        out[name] = (np.asarray(iv["lower"], float), np.asarray(iv["upper"], float), np.asarray(iv["estimate"], float))
    idn = res["identified"]
    out["identified"] = (np.asarray(idn["lower"], float), np.asarray(idn["upper"], float),
                         np.asarray(res["pd_industry"], float))
    # the band of the anchored k alone: PD at the k of the anchor's Jeffreys limits (no outer Jeffreys interval)
    jr = pd_jeffreys(anchor, n, level=LEVEL)
    x_lo = np.clip(np.asarray(jr["lower"]) * n - d, 0.0, w)
    x_hi = np.clip(np.asarray(jr["upper"]) * n - d, 0.0, w)
    an = res["anchor"]
    out["band"] = ((d + x_lo) / n, (d + x_hi) / n, np.asarray(an["pd"], float))
    out["anchored"] = (np.asarray(an["lower"], float), np.asarray(an["upper"], float), np.asarray(an["pd"], float))
    out["_k"] = np.asarray(an["k"], float)
    out["_k_true"] = odds_multiplier(d, s, w, np.clip(followed - d, 0.0, w))
    return out


class Cell:
    """The accumulators of one design over the repetitions."""

    def __init__(self, ident: str, reps: int, truth: np.ndarray, meta: dict[str, Any]) -> None:
        self.ident, self.reps, self.truth, self.meta, self.i = ident, reps, truth, meta, 0
        self.hit = {t: np.zeros((reps, G), bool) for t in TREATMENTS}
        self.und = {t: np.zeros((reps, G), bool) for t in TREATMENTS}
        self.width = {t: np.full((reps, G), np.nan) for t in TREATMENTS}
        self.point = {t: np.full((reps, G), np.nan) for t in TREATMENTS}
        self.k = np.full((reps, G), np.nan)
        self.k_true = np.full((reps, G), np.nan)
        self.dec = {t: {dl: np.zeros((reps, 3), bool) for dl in DELTAS} for t in TREATMENTS}

    def add(self, ev: dict[str, Any]) -> None:
        i = self.i
        for t in TREATMENTS:
            lo, hi, pt = ev[t]
            und = ~(np.isfinite(lo) & np.isfinite(hi))
            self.und[t][i] = und
            self.hit[t][i] = (lo <= self.truth) & (self.truth <= hi) & ~und
            self.width[t][i], self.point[t][i] = hi - lo, pt
            tb = self.truth[B]
            for dl in DELTAS:
                thr = tb * (1.0 + dl)
                truth_above = tb > thr
                if not und[B]:
                    above, below = lo[B] > thr, hi[B] < thr
                    correct = above if truth_above else below
                    wrong = below if truth_above else above
                    self.dec[t][dl][i] = (correct, wrong, not (above or below))
                else:
                    self.dec[t][dl][i] = (False, False, True)
        self.k[i], self.k_true[i] = ev["_k"], ev["_k_true"]
        self.i += 1

    def summary(self) -> dict[str, Any]:
        n = self.reps
        tr: dict[str, Any] = {}
        for t in TREATMENTS:
            cov = self.hit[t].mean(axis=0)
            rel = self.point[t] / self.truth - 1.0
            tr[t] = {
                "coverage": rl(cov), "mcse": rl(np.sqrt(cov * (1 - cov) / n)),
                "undefined": [int(x) for x in self.und[t].sum(axis=0)],
                "width": rl(np.nanmean(self.width[t], axis=0)),
                "rel_bias": rl(np.nanmean(rel, axis=0)),
                "rel_bias_mcse": rl(np.nanstd(rel, axis=0, ddof=1) / math.sqrt(n)),
                "rel_rmse": rl(np.sqrt(np.nanmean(rel ** 2, axis=0)))}
        fin = np.where(np.isfinite(self.k), self.k, np.nan)
        kt = np.where(np.isfinite(self.k_true), self.k_true, np.nan)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            kinfo = {"anchored_median": rl(np.nanmedian(fin, axis=0)), "anchored_q05": rl(np.nanquantile(fin, 0.05, axis=0)),
                     "anchored_q95": rl(np.nanquantile(fin, 0.95, axis=0)),
                     "true_median": rl(np.nanmedian(kt, axis=0)),
                     "share_infinite": rl(np.mean(np.isposinf(self.k), axis=0))}
        dec = {t: {f"{dl:+.2f}": {"correct": r4(self.dec[t][dl][:, 0].mean()), "wrong": r4(self.dec[t][dl][:, 1].mean()),
                                  "undetermined": r4(self.dec[t][dl][:, 2].mean())} for dl in DELTAS} for t in TREATMENTS}
        return {"id": self.ident, "reps": n, **self.meta, "truth": rl(self.truth), "treatments": tr, "k": kinfo,
                "decisions": {"grade": GRADES[B], "threshold_rule": "t = truth (1 + delta); lower > t above, upper < t below",
                              "by_treatment": dec}}


def stability_record(steps: list[dict[str, Any]], follow: list[np.ndarray], capture: Any,
                     rng: np.random.Generator) -> dict[int, dict[str, Any]]:
    """The stability criterion of c04_bounds.real_bounds on one repetition's five annual cohorts: the share of cohorts
    whose anchored k band contains the pooled anchored k, per grade."""
    out: dict[int, dict[str, Any]] = {}
    recs: dict[int, list[dict[str, Any]]] = {g: [] for g in STABILITY_GRADES}
    sums: dict[int, np.ndarray] = {g: np.zeros(5) for g in STABILITY_GRADES}
    for st, fo in zip(steps, follow, strict=True):
        c, wd = st["counts"], np.asarray(st["withdrawn"], float)
        dcol = c[:G, M - 1]
        sv = c[:G].sum(axis=1) - dcol
        n = dcol + sv + wd[:G]
        an = make_anchor(fo, n, capture, rng, observed=dcol)
        for g in STABILITY_GRADES:
            if n[g] <= 0 or wd[g] <= 0:
                continue
            recs[g].append(bnd._one(float(dcol[g]), float(sv[g]), float(wd[g]), float(an[g]), float(n[g])))
            sums[g] += (dcol[g], sv[g], wd[g], an[g], n[g])
    for g in STABILITY_GRADES:
        if not recs[g] or sums[g][0] <= 0:
            out[g] = {"usable": 0, "share": float("nan"), "pooled_k": float("nan")}
            continue
        pooled = bnd._one(*(float(x) for x in sums[g]))
        kp = pooled["_k"]["k"]
        usable = [r for r in recs[g] if r["reason"] == "ok" and math.isfinite(r["_k"]["k_low"])
                  and not math.isnan(r["_k"]["k_high"])]
        contain = [r for r in usable if r["_k"]["k_low"] <= kp <= r["_k"]["k_high"]]
        out[g] = {"usable": len(usable), "share": len(contain) / len(usable) if usable else float("nan"),
                  "pooled_k": kp}
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the studies


def log(msg: str) -> None:
    print(f"[{time.perf_counter() - T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def study_grid(q: np.ndarray, ob: list[int], reps: int) -> tuple[list[dict], list[dict]]:
    """The coverage grid, the capture ladder and the decision study on scale-1 draws."""
    latent = fam._paths(q, ob)
    truth = np.asarray(latent.truth()["pd_by_grade"]["1"], float)
    grid: list[dict] = []
    capture_cells: list[dict] = []
    for k in INFORMATIVE:
        observed = fam._paths(q, ob, withdrawal_rate=WITHDRAWAL_RATE, informative=k, window=WINDOW)
        key = f"ms-bs14:informative={k:g}"
        seed = seed_of(key)
        kids, kids2 = (np.random.SeedSequence(seed + j).spawn(reps) for j in (0, 1))
        meta = {"informative": k, "seed_key": key, "seed": seed}
        cells = {"first_year": Cell("first_year", reps, truth, {**meta, "design": "first_year", "scale": 1, "capture": 1.0}),
                 "pooled": Cell("pooled", reps, truth, {**meta, "design": "pooled", "scale": 1, "capture": 1.0})}
        if k in (3.0, 9.0):
            for cap in CAPTURES:
                cells[f"capture={cap}"] = Cell(f"capture={cap}", reps, truth,
                                               {**meta, "design": "capture", "scale": 1, "capture": cap})
        for r in range(reps):
            steps, follow = draw(latent, observed, kids[r])
            rng = np.random.default_rng(kids2[r])
            c0, w0 = steps[0]["counts"], np.asarray(steps[0]["withdrawn"], float)
            n0 = c0[:G].sum(axis=1) + w0[:G]
            cells["first_year"].add(evaluate(c0, w0, follow[0], follow[0]))
            cp = sum(s["counts"] for s in steps)
            wp = sum(np.asarray(s["withdrawn"], float) for s in steps)
            cells["pooled"].add(evaluate(cp, wp, sum(follow), sum(follow)))
            for cap in CAPTURES:
                if f"capture={cap}" in cells:
                    cells[f"capture={cap}"].add(evaluate(c0, w0, follow[0], make_anchor(follow[0], n0, cap, rng)))
        for name, cell in cells.items():
            s = cell.summary()
            (grid if name in ("first_year", "pooled") else capture_cells).append(s)
        log(f"grid: informative {k:g} done ({reps} repetitions)")
    return grid, capture_cells


def study_stability(q: np.ndarray, ob: list[int], reps: int) -> list[dict]:
    """The stability criterion of the real cohorts on known truth: the share of the five annual cohorts whose anchored k
    band holds the pooled anchored k, by informativeness, second source and grade."""
    latent = fam._paths(q, ob)
    out: list[dict] = []
    for k in STABILITY_AT:
        observed = fam._paths(q, ob, withdrawal_rate=WITHDRAWAL_RATE, informative=k, window=WINDOW)
        key = f"ms-bs14:stability:informative={k:g}"
        seed = seed_of(key)
        kids, kids2 = (np.random.SeedSequence(seed + j).spawn(reps) for j in (0, 1))
        shares = {lab: {g: [] for g in STABILITY_GRADES} for _, lab in STABILITY_CAPTURES}
        pooled_k = {lab: {g: [] for g in STABILITY_GRADES} for _, lab in STABILITY_CAPTURES}
        for r in range(reps):
            steps, follow = draw(latent, observed, kids[r])
            rng = np.random.default_rng(kids2[r])
            for cap, lab in STABILITY_CAPTURES:
                rec = stability_record(steps, follow, cap, rng)
                for g in STABILITY_GRADES:
                    shares[lab][g].append(rec[g]["share"])
                    pooled_k[lab][g].append(rec[g]["pooled_k"])
        for _, lab in STABILITY_CAPTURES:
            for g in STABILITY_GRADES:
                sh = np.asarray(shares[lab][g], float)
                pk = np.asarray(pooled_k[lab][g], float)
                ok = np.isfinite(sh)
                out.append({"informative": k, "capture": lab, "grade": GRADES[g], "reps": reps, "defined": int(ok.sum()),
                            "seed_key": key, "seed": seed,
                            "mean_share": r4(sh[ok].mean()) if ok.any() else None,
                            "mean_share_mcse": r4(sh[ok].std(ddof=1) / math.sqrt(ok.sum())) if ok.sum() > 1 else None,
                            "share_stable_at_80": r4((sh[ok] >= bnd.STABILITY_SHARE).mean()) if ok.any() else None,
                            "median_pooled_k": r4(np.nanmedian(pk[np.isfinite(pk)])) if np.isfinite(pk).any() else None})
        log(f"stability: informative {k:g} done ({reps} repetitions)")
    return out


def study_scale(q: np.ndarray, ob: list[int], reps: dict[int, int]) -> list[dict]:
    """The first-year design on cohorts 3, 10 and 30 times the case's: informative 0, 1, 3, 9, 19 for the ten-fold
    cohort and informative 9 for the others."""
    cells: list[dict] = []
    for scale in SCALES:
        big = [int(o) * scale for o in ob]
        latent = fam._paths(q, big, 1)
        truth = np.asarray(latent.truth()["pd_by_grade"]["1"], float)
        for k in (INFORMATIVE if scale == 10 else (9.0,)):
            observed = fam._paths(q, big, 1, withdrawal_rate=WITHDRAWAL_RATE, informative=k, window=WINDOW)
            key = f"ms-bs14:informative={k:g}:x{scale}"
            seed = seed_of(key)
            n_rep = reps[scale]
            cell = Cell(f"x{scale}", n_rep, truth, {"informative": k, "seed_key": key, "seed": seed,
                                                    "design": "first_year", "scale": scale, "capture": 1.0})
            for ch in np.random.SeedSequence(seed).spawn(n_rep):
                steps, follow = draw(latent, observed, ch)
                c0, w0 = steps[0]["counts"], np.asarray(steps[0]["withdrawn"], float)
                cell.add(evaluate(c0, w0, follow[0], follow[0]))
            cells.append(cell.summary())
            log(f"scale x{scale} informative {k:g} done ({n_rep} repetitions)")
    return cells


def study_duration(q: np.ndarray, ob: list[int], reps: int, n_boot: int) -> list[dict]:
    """The duration estimator, withdrawals read as independent right censoring, on the grid's draws: the seed key, the
    child streams and the repetitions of the coverage grid (the five-year observed paths of each repetition are the ones
    whose annual steps the grid reads). The bootstrap draws come from a second stream of their own."""
    latent = fam._paths(q, ob)
    truth = np.asarray(latent.truth()["pd_by_grade"]["1"], float)
    out: list[dict] = []
    for k in INFORMATIVE:
        observed = fam._paths(q, ob, withdrawal_rate=WITHDRAWAL_RATE, informative=k, window=WINDOW)
        key = f"ms-bs14:informative={k:g}"
        seed = seed_of(key)
        kids, kids2 = (np.random.SeedSequence(seed + j).spawn(reps) for j in (0, 1))
        est = np.full((reps, G), np.nan)
        cover = np.zeros((reps, G), bool)
        for i in range(reps):
            d = observed.draw(np.random.default_rng(kids[i]))
            est[i] = expm(duration_generator(d["segments"], M)["generator"])[:G, M - 1]
            b = pd_bootstrap(d["segments"], M, method="resample", horizon=1.0, n_boot=n_boot, level=LEVEL,
                             seed=int(np.random.default_rng(kids2[i]).integers(0, 2**63 - 1)))
            cover[i] = (np.asarray(b["lower"])[:G] <= truth) & (truth <= np.asarray(b["upper"])[:G])
        rel = est / truth - 1.0
        cov = cover.mean(axis=0)
        out.append({"informative": k, "reps": reps, "n_boot": n_boot, "seed_key": key, "seed": seed,
                    "same_draws_as": "coverage-grid.json", "truth": rl(truth),
                    "rel_bias": rl(np.nanmean(rel, axis=0)),
                    "rel_bias_mcse": rl(np.nanstd(rel, axis=0, ddof=1) / math.sqrt(reps)),
                    "coverage": rl(cov), "mcse": rl(np.sqrt(cov * (1 - cov) / reps))})
        log(f"duration: informative {k:g} done ({reps} repetitions, {n_boot} bootstrap replicates)")
    return out


def study_timing(q: np.ndarray, ob: list[int], calls: int) -> dict[str, Any]:
    """The cost of one call of the method on a cohort of seven grades (``withdrawal_bounds`` with the anchor, the
    Jeffreys limits of the three single-answer treatments and the evaluation of the six treatments), over the first
    annual cohorts of ``calls`` draws at informativeness 9; the median and the 95th percentile, in milliseconds."""
    latent = fam._paths(q, ob)
    observed = fam._paths(q, ob, withdrawal_rate=WITHDRAWAL_RATE, informative=9.0, window=WINDOW)
    kids = np.random.SeedSequence(seed_of("ms-bs14:timing")).spawn(calls)
    cohorts = []
    for ch in kids:
        steps, follow = draw(latent, observed, ch)
        cohorts.append((steps[0]["counts"], np.asarray(steps[0]["withdrawn"], float), follow[0]))
    bounds_ms, full_ms = [], []
    for c0, w0, f0 in cohorts:
        t = time.perf_counter()
        withdrawal_bounds(c0, w0, anchor_defaults=f0, level=LEVEL)
        bounds_ms.append(1000.0 * (time.perf_counter() - t))
        t = time.perf_counter()
        evaluate(c0, w0, f0, f0)
        full_ms.append(1000.0 * (time.perf_counter() - t))
    return {"calls": calls,
            "withdrawal_bounds_ms_median": round(float(np.median(bounds_ms)), 3),
            "withdrawal_bounds_ms_p95": round(float(np.quantile(bounds_ms, 0.95)), 3),
            "evaluate_six_treatments_ms_median": round(float(np.median(full_ms)), 3),
            "evaluate_six_treatments_ms_p95": round(float(np.quantile(full_ms, 0.95)), 3)}


def machine() -> dict[str, Any]:
    """The machine and the library versions the times were measured on."""
    import scipy
    return {"platform": platform.platform(), "processor": platform.processor(), "logical_cpus": os.cpu_count(),
            "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "riskvalidation": riskvalidation.__version__}


def record_time(name: str, seconds: float, extra: dict[str, Any]) -> None:
    """Merge one study's elapsed time (and, for ``timing``, the cost of a call) into ``run-times.json``."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "run-times.json"
    doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"studies": {}}
    doc["machine"] = machine()
    doc["studies"][name] = {"elapsed_seconds": round(seconds, 1), **extra}
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + chr(10), encoding="utf-8")


def write(name: str, payload: Any, header: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps({**header, "data": payload}, separators=(",", ":")) + "\n", encoding="utf-8")


T0 = time.perf_counter()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reps", type=int, default=1000, help="repetitions of the grid, capture, stability, decision and ten-fold studies")
    ap.add_argument("--reps-scale", type=int, default=500, help="repetitions of the 3 and 30 times cohorts")
    ap.add_argument("--reps-duration", type=int, default=1000, help="repetitions of the duration estimator study")
    ap.add_argument("--n-boot", type=int, default=200, help="bootstrap replicates per repetition (duration estimator)")
    ap.add_argument("--only", choices=("grid", "stability", "scale", "duration", "timing"), help="run one study")
    ap.add_argument("--timing-calls", type=int, default=200, help="calls of the method timed by the timing study")
    ap.add_argument("--out", type=pathlib.Path, default=None, help="output folder (default experiments/results)")
    a = ap.parse_args()
    q, ob = load_generator()
    header = {"engine": "riskvalidation", "engine_version": riskvalidation.__version__, "case_seed": CASE_SEED,
              "level": LEVEL, "generator_obligors": ob, "withdrawal_rate": WITHDRAWAL_RATE, "window": WINDOW,
              "grades": GRADES}
    if a.out is not None:
        global OUT
        OUT = a.out
    t0 = time.perf_counter()
    if a.only in (None, "grid"):
        grid, capture_cells = study_grid(q, ob, a.reps)
        write("coverage-grid.json", grid, {**header, "reps": a.reps})
        write("capture-ladder.json", capture_cells, {**header, "reps": a.reps})
        record_time("grid", time.perf_counter() - t0, {"reps": a.reps, "writes": ["coverage-grid.json", "capture-ladder.json"]})
        t0 = time.perf_counter()
    if a.only in (None, "stability"):
        write("stability.json", study_stability(q, ob, a.reps), {**header, "reps": a.reps, "stability_share": bnd.STABILITY_SHARE})
        record_time("stability", time.perf_counter() - t0, {"reps": a.reps})
        t0 = time.perf_counter()
    if a.only in (None, "scale"):
        cells = study_scale(q, ob, {3: a.reps_scale, 10: a.reps, 30: a.reps_scale})
        write("scale-ladder.json", cells, header)
        record_time("scale", time.perf_counter() - t0, {"reps": a.reps, "reps_scale": a.reps_scale})
        t0 = time.perf_counter()
    if a.only in (None, "duration"):
        write("duration.json", study_duration(q, ob, a.reps_duration, a.n_boot), header)
        record_time("duration", time.perf_counter() - t0, {"reps": a.reps_duration, "n_boot": a.n_boot})
        t0 = time.perf_counter()
    if a.only in (None, "timing"):
        cost = study_timing(q, ob, a.timing_calls)
        record_time("timing", time.perf_counter() - t0, cost)


if __name__ == "__main__":
    main()
