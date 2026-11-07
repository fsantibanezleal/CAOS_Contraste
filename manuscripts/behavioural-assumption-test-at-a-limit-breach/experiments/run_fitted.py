"""Experiment 3: a fitted behavioural parameter (the weighted average maturity of the replicating portfolio, re-estimated at each date), with an override planted
at breach dates.

    python manuscripts/behavioural-assumption-test-at-a-limit-breach/experiments/run_fitted.py [--workers 20] [--cache DIR]

The banks: 1,000 calibration banks and 2,000 test banks (5 blocks of 400), each a circular block bootstrap (6-quarter blocks) of the 40 real quarterly rows of case C14,
whose 12 consecutive 16-quarter fits are the engine's ``replicating_portfolio``. A history has a breach chain (stationary prevalence 0.10, 0.25 or 0.50, persistence
0.8, at least one breach after the first date); in the alternative arm an override is planted at each breach date with probability 0.5 (at least one): from then on the
weights used are ``(1 - s) w + s e_J`` with the cumulative share ``s`` a multiple of 0.05, 0.10, 0.20 or 0.40 of the number of overrides so far, toward the longest tranche.
The tolerance of the tolerance rules is the conformal quantile at 5% of the largest change at a breach date over the calibration banks of the same prevalence.
A second kind of override adds 0.5, 1, 2 or 4 years to the fitted maturity from each planted date on; a further arm plants an addition of 2 or 4 years at the date
that precedes the first date of a breach spell (a date that is not itself a breach date; each such date with probability 0.5, at least one); a further experiment
plants on the real fitted series of the bank (its last 12 fits). The two tests of a shift in the level of the fitted series (a break at an unknown date, and the same
with the requirement that the estimated break date be a breach date) are calibrated at 5% on the same calibration banks as the tolerance.
Writes ``results_fitted.json``; the per-bank weights are cached under ``--cache`` (temp root), never committed.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import pathlib

import numpy as np

import core

HERE = pathlib.Path(__file__).resolve().parent
SEED = 9301
N_CAL = 1000
BLOCKS = 5
PER_BLOCK = 400
PREVS = (0.10, 0.25, 0.50)
CAL_PREV = 0.25
SHARES = (0.05, 0.10, 0.20, 0.40)
#: the second kind of override: a persistent addition to the fitted weighted average maturity, years (no weights, so no stability test)
ADD_YEARS = (0.5, 1.0, 2.0, 4.0)
PI_M = 0.5
#: the sizes of the anticipatory addition, years; it is placed at the date before the first date of a breach spell
EARLY_YEARS = (2.0, 4.0)
#: the detectors whose critical value is calibrated on the null banks, and the key of the calibrated values
DELTA_KEY = {"tolerance": "peak", "tolerance_lookahead": "peak_lookahead", "shift": "shift", "shift_at_breach": "shift_at_breach"}
NO_WEIGHTS = tuple(d for d in core.DETECTORS if d != "stability")
#: the detectors of the first version of this script, whose bootstrap intervals the later additions must not move
OLD_DETECTORS = core.DETECTORS[:8]
N_REAL_DRAWS = 2000
# The cache lives in the device's temp root (CAOS_TEMP_ROOT, as the pipeline reads it) or where --cache says.
DEFAULT_CACHE = (pathlib.Path(os.environ["CAOS_TEMP_ROOT"]) / "contraste-behavioural-assumption-test-at-a-limit-breach" / "cache"
                 if os.environ.get("CAOS_TEMP_ROOT") else None)

_REAL: dict = {}


def _init(client: np.ndarray, yields: np.ndarray) -> None:
    _REAL["client"], _REAL["yields"] = client, yields


def _bank(args):
    """The 12 rolling fits of one bank: ``(set, block, i)`` -> weights (12, 7)."""
    kind, blk, i = args
    return core.simulate_fits((SEED, kind, blk, i), _REAL["client"], _REAL["yields"])


def banks(pool, cache: pathlib.Path) -> tuple[np.ndarray, np.ndarray]:
    """The calibration banks (N_CAL, 12, 7) and the test banks (BLOCKS * PER_BLOCK, 12, 7), from the cache when it holds them."""
    cache.mkdir(parents=True, exist_ok=True)
    f_cal, f_test = cache / "fitted_cal.npy", cache / "fitted_test.npy"
    if f_cal.exists() and f_test.exists():
        return np.load(f_cal), np.load(f_test)
    cal = np.array(pool.map(_bank, [(0, 0, i) for i in range(N_CAL)], chunksize=10))
    test = np.array(pool.map(_bank, [(1, blk, i) for blk in range(BLOCKS) for i in range(PER_BLOCK)], chunksize=10))
    np.save(f_cal, cal)
    np.save(f_test, test)
    return cal, test


def theta_of(w: np.ndarray) -> np.ndarray:
    return w @ core.MATS / 2.0


def history_draws(rng: np.random.Generator, prev: float) -> tuple[np.ndarray, np.ndarray]:
    b = core.breach_chain(rng, core.T_DEFAULT, prev)
    return b, core.plant_dates(rng, b, PI_M)


def delta_of(det: str, d: dict) -> float:
    """The calibrated critical value that the detector ``det`` reads from the calibration ``d`` of one prevalence (``None`` for a detector without one)."""
    return d[DELTA_KEY[det]] if det in DELTA_KEY else None


def _cal_peaks(args):
    """The calibration null statistics of one bank at each prevalence: the largest change at a breach date, without and with the look-ahead, and the statistic of
    the two shift tests."""
    i, w = args
    th = theta_of(w)
    out = []
    for pi, prev in enumerate(PREVS):
        b, _ = history_draws(np.random.default_rng([SEED, 2, pi, i]), prev)
        out.append((core.peak_at_breach(th, b), core.peak_at_breach(th, b, lookahead=True)) + core.shift_scores(th, b))
    return out


def _test_bank(args):
    """Every statistic of one test bank at each prevalence: the null history, the alternative at each override share, and the anticipatory alternative."""
    blk, i, w = args
    th0 = theta_of(w)
    res = {}
    for pi, prev in enumerate(PREVS):
        b, plant = history_draws(np.random.default_rng([SEED, 3, blk, i, pi]), prev)
        entry = {"m": int(b[1:].sum()), "null": core.scores(th0, b, w), "alt": {}, "ties_null": int(np.sum(np.diff(th0)[b[1:]] == 0.0))}
        for s in SHARES:
            wa = core.overlay_weights(w, plant, s)
            ta = theta_of(wa)
            entry["alt"][str(s)] = core.scores(ta, b, wa)
            entry.setdefault("invisible", {})[str(s)] = bool(np.allclose(wa[plant], w[plant]))
        # the additive override of ``y`` years from each planted date on, and the anticipatory one at the date before the first date of a breach spell
        entry["add"] = {str(y): core.scores(th0 + y * np.cumsum(plant), b) for y in ADD_YEARS}
        early = core.plant_dates_before_spell(np.random.default_rng([SEED, 5, blk, i, pi]), b, PI_M)
        if early.any():
            entry["early"] = {str(y): core.scores(th0 + y * np.cumsum(early), b) for y in EARLY_YEARS}
        res[str(prev)] = entry
    return res


def _real_draw(args):
    """One draw of the semi-synthetic experiment: the real fitted series with a breach chain and an override."""
    i, w = args
    th0 = theta_of(w)
    res = {}
    for pi, prev in enumerate(PREVS):
        b, plant = history_draws(np.random.default_rng([SEED, 4, i, pi]), prev)
        entry = {"m": int(b[1:].sum()), "null": core.scores(th0, b, w), "alt": {}}
        for s in SHARES:
            wa = core.overlay_weights(w, plant, s)
            entry["alt"][str(s)] = core.scores(theta_of(wa), b, wa)
        entry["add"] = {str(y): core.scores(th0 + y * np.cumsum(plant), b) for y in ADD_YEARS}
        res[str(prev)] = entry
    return res


def summarise(rows: list[dict], deltas: dict, blocks: list[int] | None, per_block: int | None, rng: np.random.Generator) -> dict:
    """Per prevalence and share: the flag rate of every detector on the null and on the alternative with Wilson intervals, the area under the ROC curve with a
    bootstrap interval, and the engine's behaviour on ties."""
    out: dict = {}
    # the bootstrap of the first eight detectors draws from ``rng`` in the order of the first version of this script; the later detectors and the anticipatory arm draw
    # from generators of their own, so that adding them leaves every interval of the first eight unchanged
    rng_extra = np.random.default_rng([SEED, 11])
    rng_early = np.random.default_rng([SEED, 12])

    def rng_of(det: str) -> np.random.Generator:
        return rng if det in OLD_DETECTORS else rng_extra

    for prev in map(str, PREVS):
        d = deltas[prev]
        null = [r[prev]["null"] for r in rows]
        n = len(null)
        cell: dict = {"n": n, "mean_breach_dates": float(np.mean([r[prev]["m"] for r in rows])), "delta": d, "null": {}, "alt": {}, "auc": {}}
        cell["share_null_engine_below_m"] = float(np.mean([r[prev]["null"]["engine_count"] < r[prev]["m"] for r in rows]))
        cell["share_null_engine_zero"] = float(np.mean([r[prev]["null"]["engine_count"] == 0 for r in rows]))
        for det in core.DETECTORS:
            dl = delta_of(det, d)
            k = sum(core.flag(s, det, dl) for s in null)
            p, lo, hi = core.wilson(k, n)
            entry = {"k": k, "rate": p, "lo": lo, "hi": hi}
            if blocks is not None:
                per = [sum(core.flag(null[j], det, dl) for j in range(b0 * per_block, (b0 + 1) * per_block)) / per_block for b0 in range(len(blocks))]
                entry["block_sd"] = float(np.std(per, ddof=1))
            cell["null"][det] = entry
        for s in map(str, SHARES):
            alt = [r[prev]["alt"][s] for r in rows]
            cell["alt"][s] = {"invisible_share": float(np.mean([r[prev].get("invisible", {}).get(s, False) for r in rows])) if "invisible" in rows[0][prev] else None}
            cell["auc"][s] = {}
            for det in core.DETECTORS:
                dl = delta_of(det, d)
                k = sum(core.flag(a, det, dl) for a in alt)
                p, lo, hi = core.wilson(k, n)
                entry = {"k": k, "rate": p, "lo": lo, "hi": hi}
                if blocks is not None:
                    per = [sum(core.flag(alt[j], det, dl) for j in range(b0 * per_block, (b0 + 1) * per_block)) / per_block for b0 in range(len(blocks))]
                    entry["block_sd"] = float(np.std(per, ddof=1))
                cell["alt"][s][det] = entry
                a, alo, ahi = core.auc_ci(np.array([core.roc_score(x, det) for x in null]), np.array([core.roc_score(x, det) for x in alt]), rng_of(det), reps=300)
                cell["auc"][s][det] = {"auc": a, "lo": alo, "hi": ahi}
        cell["add"], cell["auc_add"] = {}, {}
        for y in map(str, ADD_YEARS):
            alt = [r[prev]["add"][y] for r in rows]
            cell["add"][y], cell["auc_add"][y] = {}, {}
            for det in NO_WEIGHTS:
                dl = delta_of(det, d)
                k = sum(core.flag(a, det, dl) for a in alt)
                p, lo, hi = core.wilson(k, n)
                cell["add"][y][det] = {"k": k, "rate": p, "lo": lo, "hi": hi}
                a_, alo, ahi = core.auc_ci(np.array([core.roc_score(x, det) for x in null]), np.array([core.roc_score(x, det) for x in alt]), rng_of(det), reps=300)
                cell["auc_add"][y][det] = {"auc": a_, "lo": alo, "hi": ahi}
        if "early" in rows[0][prev]:
            # the banks with a date that precedes a breach spell: the null banks among them, and the detection of the anticipatory addition of each size
            sub = [r for r in rows if "early" in r[prev]]
            cell["early"] = {"n": len(sub), "null": {}, "rates": {}, "auc": {}}
            for det in NO_WEIGHTS:
                dl = delta_of(det, d)
                k = sum(core.flag(r[prev]["null"], det, dl) for r in sub)
                p, lo, hi = core.wilson(k, len(sub))
                cell["early"]["null"][det] = {"k": k, "rate": p, "lo": lo, "hi": hi}
            for y in map(str, EARLY_YEARS):
                cell["early"]["rates"][y], cell["early"]["auc"][y] = {}, {}
                for det in NO_WEIGHTS:
                    dl = delta_of(det, d)
                    k = sum(core.flag(r[prev]["early"][y], det, dl) for r in sub)
                    p, lo, hi = core.wilson(k, len(sub))
                    cell["early"]["rates"][y][det] = {"k": k, "rate": p, "lo": lo, "hi": hi}
                    a_, alo, ahi = core.auc_ci(np.array([core.roc_score(r[prev]["null"], det) for r in sub]), np.array([core.roc_score(r[prev]["early"][y], det) for r in sub]), rng_early, reps=300)
                    cell["early"]["auc"][y][det] = {"auc": a_, "lo": alo, "hi": ahi}
        out[prev] = cell
    return out


def realism(real: core.RealSeries, test_w: np.ndarray) -> dict:
    """The real fitted series against the simulated banks on the properties of the changes that the detectors read."""
    def stats_of(th: np.ndarray) -> dict:
        d = np.abs(np.diff(th))
        return {"median_abs_change": float(np.median(d)), "share_zero_change": float(np.mean(d == 0.0)), "share_at_cap": float(np.mean(th >= core.WAM_MAX - 1e-9)),
                "sd_level": float(th.std()), "max_abs_change": float(d.max())}

    sim = [stats_of(theta_of(w)) for w in test_w]
    out = {"real_last_12": stats_of(real.wam[-12:]), "real_all_25": stats_of(real.wam)}
    out["simulated_mean"] = {k: float(np.mean([s[k] for s in sim])) for k in sim[0]}
    out["simulated_q05"] = {k: float(np.quantile([s[k] for s in sim], 0.05)) for k in sim[0]}
    out["simulated_q95"] = {k: float(np.quantile([s[k] for s in sim], 0.95)) for k in sim[0]}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--cache", type=pathlib.Path, default=DEFAULT_CACHE, required=DEFAULT_CACHE is None,
                    help="cache folder; defaults to $CAOS_TEMP_ROOT/contraste-behavioural-assumption-test-at-a-limit-breach/cache")
    args = ap.parse_args()
    real = core.load_real()
    with mp.Pool(args.workers, initializer=_init, initargs=(real.client_rate, real.tranche_yields)) as pool:
        cal, test = banks(pool, args.cache)
        print("banks:", cal.shape, test.shape, flush=True)
        cal_rows = pool.map(_cal_peaks, [(i, cal[i]) for i in range(N_CAL)], chunksize=20)
        deltas: dict = {}
        for pi, prev in enumerate(PREVS):
            pk = np.array([r[pi][0] for r in cal_rows])
            pl = np.array([r[pi][1] for r in cal_rows])
            sh = np.array([r[pi][2] for r in cal_rows])
            sb = np.array([r[pi][3] for r in cal_rows])
            deltas[str(prev)] = {"peak": core.conformal_threshold(pk, core.ALPHA), "peak_lookahead": core.conformal_threshold(pl, core.ALPHA), "n_cal": int(pk.size),
                                 "shift": core.conformal_threshold(sh, core.ALPHA), "shift_at_breach": core.conformal_threshold(sb, core.ALPHA),
                                 "cal_null_flag_rate_exact": float(np.mean(pk > 0.0))}
        test_rows = pool.map(_test_bank, [(i // PER_BLOCK, i % PER_BLOCK, test[i]) for i in range(test.shape[0])], chunksize=10)
        print("test banks evaluated", flush=True)
        real_rows = pool.map(_real_draw, [(i, real.weights[-12:]) for i in range(N_REAL_DRAWS)], chunksize=20)
    rng = np.random.default_rng([SEED, 9])
    # the calibration of the delta at the calibration prevalence applied at every prevalence (mismatch) and the matched one
    matched = deltas
    mismatched = {prev: deltas[str(CAL_PREV)] for prev in map(str, PREVS)}
    res = {"seed": SEED, "T": core.T_DEFAULT, "alpha": core.ALPHA, "n_cal": N_CAL, "n_test": int(test.shape[0]), "blocks": BLOCKS, "per_block": PER_BLOCK,
           "shares": list(SHARES), "pi_m": PI_M, "block_length": core.BLOCK, "cal_prevalence": CAL_PREV, "deltas": deltas, "realism": realism(real, test),
           "matched": summarise(test_rows, matched, list(range(BLOCKS)), PER_BLOCK, rng),
           "mismatched": summarise(test_rows, mismatched, list(range(BLOCKS)), PER_BLOCK, rng),
           "real_series": summarise(real_rows, matched, None, None, rng), "real_series_n": N_REAL_DRAWS}
    ties = [(r[str(CAL_PREV)]["ties_null"], r[str(CAL_PREV)]["m"]) for r in test_rows]
    res["ties_at_breach_dates"] = {"share_banks_with_a_tie": float(np.mean([t > 0 for t, _ in ties])),
                                   "mean_ties": float(np.mean([t for t, _ in ties])), "mean_breach_dates": float(np.mean([m for _, m in ties]))}
    (HERE / "results_fitted.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote results_fitted.json")


if __name__ == "__main__":
    main()
