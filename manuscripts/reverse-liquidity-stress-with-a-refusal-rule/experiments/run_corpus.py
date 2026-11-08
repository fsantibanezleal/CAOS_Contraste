"""Experiment 1: the engine's reverse-stress solver and its comparators on a seeded corpus of synthetic banks with an independent oracle.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/experiments/run_corpus.py [--n 1000] [--out PATH]

Five independent corpora (seeds 20261107 to 20261111) of 1,000 banks each, every bank solved at the targets of 2, 5, 10 and 30 days
(20,000 instances). For every instance the oracle of ``core.py`` gives the outcome (solved, or refused for one of three reasons) and
the root of the window function; the engine solver, a scan of the case design's multiplier grid, a scan of a finer grid, Brent's method on
the survival period, a bisection without the refusal rule, the proposed solver without the cap, without the upward rounding and
without the inflows and flows outside the segments are scored against it. The predictions H1 to H6 of ``hypotheses.json`` are evaluated
here. Writes ``results_corpus.json`` (rates with Wilson 95% intervals on the pooled counts and the standard deviation over the five
corpora; quantiles with bootstrap intervals; measured times).
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import platform
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import core  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SEEDS = [20261107 + k for k in range(5)]

METHODS = ["proposed", "grid_case", "grid_fine", "brent_sp", "bisect_no_refusal", "uncapped", "nearest", "raw_capacity"]


def run(n: int) -> dict:
    grid = core.grid_convention()
    fine = core.fine_grid()
    rec: dict[str, list] = {k: [] for k in ("seed", "target", "status", "reason", "m0", "sp0", "cap", "flat", "inflows", "others", "horizon")}
    per: dict[str, dict[str, list]] = {m: {k: [] for k in ("answered", "m", "evals", "t", "reason", "thr", "violates")} for m in METHODS}
    extra: dict[str, list] = {k: [] for k in ("sp_at_mstar", "gap", "agree_class", "hyper_rel", "overshoot_grid", "mono_ok")}
    wall0 = time.perf_counter()
    for seed in SEEDS:
        for b in core.corpus(seed, n):
            for t in core.TARGETS:
                o = core.oracle(b.opening, b.rates, b.cbc_eff, t)
                for k, v in (("seed", seed), ("target", t), ("status", o.status), ("reason", o.reason), ("m0", o.m0), ("sp0", o.sp0), ("cap", o.cap),
                             ("flat", b.flat), ("inflows", b.inflows), ("others", b.others), ("horizon", b.horizon)):
                    rec[k].append(v)
                calls = {
                    "proposed": lambda: core.solve_engine(b, t),
                    "grid_case": lambda: core.solve_grid(b, t, grid),
                    "grid_fine": lambda: core.solve_grid(b, t, fine),
                    "brent_sp": lambda: core.solve_brent_on_sp(b, t),
                    "bisect_no_refusal": lambda: core.solve_bisect_no_refusal(b, t),
                    "uncapped": lambda: core.solve_uncapped(b, t),
                    "nearest": lambda: core.solve_nearest(b, t),
                    "raw_capacity": lambda: core.solve_raw_capacity(b, t),
                }
                for name, fn in calls.items():
                    a, dt = core.timed(fn)
                    d = per[name]
                    d["answered"].append(a.answered)
                    d["m"].append(a.m)
                    d["evals"].append(a.evals)
                    d["t"].append(dt)
                    d["reason"].append(a.reason)
                    thr = None
                    if a.answered and o.status == "solved":
                        thr = core.threshold_ok(b.opening, b.rates, b.cbc_eff, t, a.m)
                    d["thr"].append(thr)
                    d["violates"].append(bool(a.answered and a.m > o.cap * (1.0 + 1e-9)))
                pa = per["proposed"]
                # the agreement of the engine's outcome with the oracle's
                agree = (pa["answered"][-1] == (o.status == "solved")) and (o.status == "solved" or pa["reason"][-1] == o.reason)
                extra["agree_class"].append(bool(agree))
                if o.status == "solved" and pa["answered"][-1]:
                    m = pa["m"][-1]
                    sp = core.sp_np(core.nlp_np(b.opening, b.rates, b.cbc_eff, m))
                    extra["sp_at_mstar"].append(sp)
                    extra["gap"].append(t - sp)
                    extra["hyper_rel"].append(abs(o.sp0 / t - o.m0) / o.m0 if math.isfinite(o.sp0) else None)
                    g = per["grid_case"]
                    extra["overshoot_grid"].append((g["m"][-1] - o.m0) / o.m0 if g["answered"][-1] else None)
                else:
                    extra["sp_at_mstar"].append(None)
                    extra["gap"].append(None)
                    extra["hyper_rel"].append(None)
                    extra["overshoot_grid"].append(None)
    wall = time.perf_counter() - wall0
    return {"rec": rec, "per": per, "extra": extra, "wall": wall}


def summarise(raw: dict, n: int) -> dict:
    rec, per, extra = raw["rec"], raw["per"], raw["extra"]
    rng = np.random.default_rng(20261107)
    N = len(rec["status"])
    seed = np.array(rec["seed"])
    solved = np.array([s == "solved" for s in rec["status"]])
    reason = np.array([r or "" for r in rec["reason"]])
    m0 = np.array([x if x is not None else np.nan for x in rec["m0"]], dtype=float)
    flat = np.array(rec["flat"])
    infl = np.array(rec["inflows"])
    oth = np.array(rec["others"])
    out: dict = {
        "design": {
            "seeds": SEEDS, "banks_per_seed": n, "targets": list(core.TARGETS), "instances": N,
            "solved": int(solved.sum()), "refused_horizon": int((reason == "horizon").sum()),
            "refused_base": int((reason == "base").sum()), "refused_unreachable": int((reason == "unreachable").sum()),
            "solved_flat_no_inflow": int((solved & flat & ~infl).sum()), "solved_growing": int((solved & ~flat).sum()),
            "solved_with_inflow_or_other": int((solved & (infl | oth)).sum()),
            "rates_in_corpus": "constant daily rates log-uniform on [0.0005, 0.08]; two-phase path with probability 0.3; financial segment of rate 1 with probability 0.15",
            "wall_seconds_total": raw["wall"],
        },
        "platform": {"python": platform.python_version(), "machine": platform.machine(), "processor": platform.processor(), "system": platform.system()},
        "methods": {},
    }

    def rate(mask_num: np.ndarray, mask_den: np.ndarray) -> dict:
        k, d = int((mask_num & mask_den).sum()), int(mask_den.sum())
        p, lo, hi = core.wilson(k, d)
        per_seed = [((mask_num & mask_den & (seed == s)).sum() / max(1, (mask_den & (seed == s)).sum())) for s in SEEDS]
        return {"k": k, "n": d, "rate": p, "lo": lo, "hi": hi, "sd_over_corpora": float(np.std(per_seed, ddof=1)) if d else None}

    for name in METHODS:
        d = per[name]
        ans = np.array(d["answered"])
        thr = np.array([bool(x) if x is not None else False for x in d["thr"]])
        viol = np.array(d["violates"])
        m = np.array([x if x is not None else np.nan for x in d["m"]], dtype=float)
        ok = solved & ans
        rel = (m[ok] - m0[ok]) / m0[ok]
        q50 = core.boot_quantile(np.abs(rel), 0.5, rng)
        q95 = core.boot_quantile(np.abs(rel), 0.95, rng)
        out["methods"][name] = {
            "false_answer_on_refused": rate(ans, ~solved),
            "miss_on_solved": rate(~ans, solved),
            "threshold_property_on_solved": rate(thr, solved),
            "answered_beyond_cap": rate(viol, np.ones(N, dtype=bool)),
            "abs_rel_error_median": {"est": q50[0], "lo": q50[1], "hi": q50[2]},
            "abs_rel_error_q95": {"est": q95[0], "lo": q95[1], "hi": q95[2]},
            "signed_rel_error_median": float(np.median(rel)) if rel.size else None,
            "evals_mean": float(np.mean(d["evals"])),
            "evals_mean_solved": float(np.mean(np.array(d["evals"])[solved])),
            "time_us_median": float(np.median(d["t"]) * 1e6),
            "time_us_q90": float(np.quantile(d["t"], 0.9) * 1e6),
        }

    # H1: classification
    agree = np.array(extra["agree_class"])
    out["H1"] = {"instances": N, "disagreements": int((~agree).sum()), "held": bool(agree.all())}
    # H2: threshold exactness on solved instances
    pm = np.array([x if x is not None else np.nan for x in per["proposed"]["m"]], dtype=float)
    diff = pm[solved] - m0[solved]
    pthr = np.array([bool(x) for x in np.array(per["proposed"]["thr"], dtype=object)[solved]])
    out["H2"] = {"solved": int(solved.sum()), "diff_min": float(diff.min()), "diff_max": float(diff.max()),
                 "within_rounding": int(((diff >= -1e-9) & (diff <= 1e-6 + 1e-9)).sum()), "threshold_property": int(pthr.sum()),
                 "held": bool(((diff >= -1e-9) & (diff <= 1e-6 + 1e-9)).all() and pthr.all())}
    # H3: exact round trip
    sp = np.array([x if x is not None else np.nan for x in extra["sp_at_mstar"]], dtype=float)
    gap = np.array([x if x is not None else np.nan for x in extra["gap"]], dtype=float)
    mono = solved & flat & ~infl
    grow = solved & ~flat
    out["H3"] = {
        "monotone": {**rate(np.nan_to_num(gap, nan=1) == 0, mono), "definition": "constant capacity and no inflow"},
        "growing": {**rate(np.nan_to_num(gap, nan=0) > 0, grow), "definition": "a monetisation schedule"},
        "gap_days_growing_quantiles": {str(q): float(np.nanquantile(gap[grow], q)) for q in (0.5, 0.9, 1.0)},
    }
    out["H3"]["held_monotone"] = out["H3"]["monotone"]["rate"] >= 0.99
    out["H3"]["held_growing"] = out["H3"]["growing"]["rate"] >= 0.05
    # H4: coarse grid overshoot
    ov = np.array([x if x is not None else np.nan for x in extra["overshoot_grid"]], dtype=float)
    has = solved & ~np.isnan(ov)
    out["H4"] = {**rate(np.nan_to_num(ov, nan=0) > 0.10, has), "answered_solved": int(has.sum()),
                 "overshoot_quantiles": {str(q): float(np.nanquantile(ov[has], q)) for q in (0.5, 0.75, 0.9)}}
    out["H4"]["held"] = out["H4"]["rate"] >= 0.30
    # H5: Brent on the survival period
    bm = np.array([x if x is not None else np.nan for x in per["brent_sp"]["m"]], dtype=float)
    bans = np.array(per["brent_sp"]["answered"])
    sel = solved & bans
    out["H5"] = {**rate(np.nan_to_num(bm - m0, nan=0) > 1e-6, solved & bans), "answered_solved": int(sel.sum()),
                 "above_threshold_of_answered": int(((bm - m0)[sel] > 1e-6).sum()),
                 "held": None}
    p5 = out["H5"]["k"] / max(1, int(solved.sum()))
    out["H5"]["rate_of_all_solved"] = p5
    out["H5"]["held"] = bool(p5 >= 0.10)
    # H6: hyperbolic rule
    hr = np.array([x if x is not None else np.nan for x in extra["hyper_rel"]], dtype=float)
    den = mono & ~np.isnan(hr)
    out["H6"] = {**rate(np.nan_to_num(hr, nan=1) <= 0.10, den), "relative_error_quantiles": {str(q): float(np.nanquantile(hr[den], q)) for q in (0.5, 0.8, 0.9)}}
    out["H6"]["held"] = out["H6"]["rate"] >= 0.80
    # data for the figures
    idx = np.flatnonzero(solved & ~np.isnan(ov))
    sub = rng.choice(idx, size=min(2500, idx.size), replace=False)
    sp0 = np.array(rec["sp0"], dtype=float)
    out["scatter"] = {
        "m0": [round(float(x), 6) for x in m0[sub]],
        "grid_case": [round(float(per["grid_case"]["m"][i]), 6) for i in sub],
        "hyper": [round(float(sp0[i] / rec["target"][i]), 6) if math.isfinite(sp0[i]) else None for i in sub],
        "target": [int(rec["target"][i]) for i in sub],
        "flat_no_inflow": [bool(flat[i] and not infl[i]) for i in sub],
        "gap": [float(gap[i]) for i in sub],
    }
    out["m0_quantiles"] = {str(q): float(np.nanquantile(m0, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}
    # error of the raw-capacity variant on the banks that have inflows or flows outside the segments
    rc = np.array([x if x is not None else np.nan for x in per["raw_capacity"]["m"]], dtype=float)
    both = solved & ~np.isnan(rc) & (infl | oth)
    out["raw_capacity_on_flows"] = {"n": int(both.sum()), "median_abs_rel_error": float(np.nanmedian(np.abs(rc[both] - m0[both]) / m0[both])) if both.any() else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--out", default=str(HERE / "results_corpus.json"))
    args = ap.parse_args()
    t0 = time.time()
    res = summarise(run(args.n), args.n)
    pathlib.Path(args.out).write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print(f"wrote {args.out} in {time.time() - t0:.0f} s; H1 {res['H1']['held']} H2 {res['H2']['held']} "
          f"H3 {res['H3']['held_monotone']}/{res['H3']['held_growing']} H4 {res['H4']['held']} H5 {res['H5']['held']} H6 {res['H6']['held']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
