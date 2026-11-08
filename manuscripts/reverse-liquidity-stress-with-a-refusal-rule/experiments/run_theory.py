"""Experiment 3: numerical checks of the propositions of the Theory section.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/experiments/run_theory.py

(a) the position is non-increasing in the multiplier (Proposition 1); (b) the closed form of the threshold for one segment with a constant
capacity (Proposition 3) against the engine, with its refusal conditions; (c) the threshold is non-increasing in the target and
non-decreasing in the capacity (Proposition 2); (d) the exact round trip of Proposition 4 and its sufficient condition; (e) the two-sided
bound of the hyperbolic rule of Proposition 5. Writes ``results_theory.json``.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import core  # noqa: E402
from riskvalidation.liquidity import reverse as ereverse  # noqa: E402
from riskvalidation.liquidity.scenarios import Scenario, ScenarioSegment  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SEED = 20261120


def check_monotone_in_multiplier(rng: np.random.Generator, n: int = 3000) -> dict:
    viol = 0
    total = 0
    worst = 0.0
    for b in core.corpus(int(rng.integers(1, 10**9)), n):
        cap = core.cap_of(b.rates)
        top = min(cap if math.isfinite(cap) else 50.0, 50.0)
        ms = np.linspace(1.0, top, 40)
        prev = None
        for m in ms:
            nl = core.nlp_np(b.opening, b.rates, b.cbc_eff, float(m))
            if prev is not None:
                d = float((nl - prev).max())  # an increase of the position with the multiplier would be a violation
                worst = max(worst, d)
                total += 1
                if d > 1e-9 * float(np.abs(b.opening).sum()):
                    viol += 1
            prev = nl
    return {"banks": n, "comparisons": total, "violations": viol, "largest_increase": worst}


def single_segment(rng: np.random.Generator) -> core.Bank:
    a = float(rng.uniform(10.0, 200.0))
    q = float(np.exp(rng.uniform(np.log(1e-3), np.log(0.1))))
    kappa = float(rng.uniform(0.02, 0.9))
    h = 125
    rates = np.full((1, h), q)
    cbc = np.full(h, kappa * a)
    scn = Scenario("idiosyncratic", "protracted", h, (ScenarioSegment("s", "synthetic", a, rates[0]),))
    return core.Bank(scn, np.array([a]), rates, cbc, cbc, True, False, False, h)


def check_closed_form(rng: np.random.Generator, n: int = 3000) -> dict:
    diffs, below, n_solved, n_refused = [], 0, 0, 0
    cond_mismatch = 0
    bound_viol = 0
    hyper_viol = 0
    hyper_rel = []
    hyper_n = 0
    for _ in range(n):
        b = single_segment(rng)
        a, q, kappa = float(b.opening[0]), float(b.rates[0, 0]), float(b.cbc_eff[0] / b.opening[0])
        t = int(rng.integers(2, 61))
        ans = core.solve_engine(b, t)
        base_ok = (1.0 - q) ** t >= 1.0 - kappa  # SP(1) > T: the capacity covers T days of the unscaled run-off
        cf_solved = base_ok and kappa < 1.0
        if cf_solved != ans.answered:
            cond_mismatch += 1
        if not ans.answered:
            n_refused += 1
            continue
        n_solved += 1
        m_cf = (1.0 - (1.0 - kappa) ** (1.0 / t)) / q
        diffs.append(abs(ans.m - m_cf))
        if ans.m < m_cf - 1e-9:
            below += 1
        # Proposition 5: bounds of the hyperbolic rule
        al = -math.log(1.0 - kappa)
        be = -math.log(1.0 - q)
        lo = (al / t) * (1.0 - al / (2.0 * t)) / q
        hi = (al / t) / q
        if not (lo - 1e-9 <= m_cf <= hi + 1e-9):
            bound_viol += 1
        sp0 = core.sp_np(core.nlp_np(b.opening, b.rates, b.cbc_eff, 1.0))
        mt = sp0 / t
        if al < 2.0 * t and math.isfinite(sp0):
            ratio_lo = 1.0 - q
            ratio_hi = (1.0 + be / al) / (1.0 - al / (2.0 * t))
            r = mt / m_cf
            hyper_n += 1
            hyper_rel.append(abs(r - 1.0))
            if not (ratio_lo - 1e-9 <= r <= ratio_hi + 1e-9):
                hyper_viol += 1
    return {"instances": n, "solved": n_solved, "refused": n_refused, "condition_mismatches": cond_mismatch,
            "max_abs_difference": float(max(diffs)), "median_abs_difference": float(np.median(diffs)), "engine_below_closed_form": below,
            "multiplier_bound_violations": bound_viol, "hyperbolic_bound_violations": hyper_viol, "hyperbolic_instances": hyper_n,
            "hyperbolic_relative_error_median": float(np.median(hyper_rel)), "hyperbolic_relative_error_q90": float(np.quantile(hyper_rel, 0.9))}


def check_monotone_targets_and_capacity(rng: np.random.Generator, n: int = 600) -> dict:
    tv, tc, cv, cc = 0, 0, 0, 0
    for b in core.corpus(int(rng.integers(1, 10**9)), n):
        ms = {}
        for t in (1, 2, 3, 5, 8, 10, 15, 20, 30, 45):
            a = core.solve_engine(b, t)
            if a.answered:
                ms[t] = a.m
        ks = sorted(ms)
        for x, y in zip(ks, ks[1:]):
            tc += 1
            if ms[x] < ms[y] - 1e-12:
                tv += 1
        for t in (5, 10, 30):
            a0 = core.solve_engine(b, t)
            a1 = core.solve_engine(b, t, cbc=b.cbc_eff * 1.05)
            if a0.answered and a1.answered:
                cc += 1
                if a1.m < a0.m - 1e-12:
                    cv += 1
    return {"targets": {"banks": n, "pairs": tc, "violations": tv}, "capacity": {"banks": n, "pairs": cc, "violations": cv}}


def check_exact_round_trip(rng: np.random.Generator, n: int = 1500) -> dict:
    """Proposition 4: with a constant capacity and no inflow the rounded multiplier has SP(m*) = T whenever the outflow of day T is at least
    delta times the bound Q_T = sum_j A_j sum_{s <= T} q_js of the slope of the cumulative outflow."""
    cond, cond_and_exact, exact, total = 0, 0, 0, 0
    margins = []
    fails_exact_no_cond = 0
    for b in core.corpus(int(rng.integers(1, 10**9)), n):
        if not (b.flat and not b.inflows):
            continue
        for t in core.TARGETS:
            a = core.solve_engine(b, t)
            if not a.answered:
                continue
            total += 1
            m = a.m
            nl = core.nlp_np(b.opening, b.rates, b.cbc_eff, m)
            sp = core.sp_np(nl)
            out_t = float(core.nlp_np(b.opening, b.rates, b.cbc_eff, m)[t - 2] - nl[t - 1]) if t >= 2 else float("inf")
            qT = float((b.opening[:, None] * b.rates[:, :t]).sum())
            margin = out_t / (core.ROUNDING * qT)
            margins.append(margin)
            holds = margin >= 1.0
            ex = sp == t
            cond += holds
            exact += ex
            cond_and_exact += holds and ex
            if holds and not ex:
                fails_exact_no_cond += 1
    return {"solved_flat_no_inflow": total, "condition_holds": int(cond), "exact": int(exact), "condition_and_exact": int(cond_and_exact),
            "violations_of_the_proposition": int(fails_exact_no_cond), "margin_min": float(min(margins)), "margin_median": float(np.median(margins))}


def main() -> int:
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED}
    out["monotone_in_multiplier"] = check_monotone_in_multiplier(rng)
    out["closed_form_single_segment"] = check_closed_form(rng)
    mt = check_monotone_targets_and_capacity(rng)
    out["monotone_in_target"] = mt["targets"]
    out["monotone_in_capacity"] = mt["capacity"]
    out["exact_round_trip"] = check_exact_round_trip(rng)
    (HERE / "results_theory.json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in out.items()}, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
