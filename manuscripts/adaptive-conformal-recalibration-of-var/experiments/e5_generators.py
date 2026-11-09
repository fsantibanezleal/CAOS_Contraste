"""Experiment 5: generators of known truth (100 replications per scenario).

    python manuscripts/adaptive-conformal-recalibration-of-var/experiments/e5_generators.py --workers 28

Data-generating process. A latent GARCH(1,1) with unit-variance Student-t(5) innovations, ``sigma_{t+1}^2 = omega + a u_t^2 + b
sigma_t^2``, ``u_t = sigma_t z_t``, omega 2e-6, a 0.08, b 0.90 (unconditional volatility 1 %), generates 1,000 calm days and then
``H`` evaluation days; the observed return is ``r_t = m_t u_t`` with a deterministic volatility multiplier ``m_t`` that no model
sees (``m_t = 1`` in the calm history). The true conditional VaR and ES of day ``t`` are therefore known exactly:
``m_t sigma_t q`` and ``m_t sigma_t e`` with ``q`` and ``e`` the quantile and the tail mean of the unit-variance t(5).

Scenarios (``m_t`` over the evaluation days): ``no-shift`` (m = 1, H = 500); ``crisis-persistent`` (H = 500: linear ramp 1 to 3
over 100 days, 3 until day 250, then 1.5); ``crash-decay`` (H = 100: m = 1 + 3 * 0.5^(t/30)); ``drift-up`` (H = 250: linear 1 to
1.8).

Models (all causal): HS-250 rolling over the whole history; GARCH-t with parameters fitted once on the calm history by the engine
(``market.garch.fit_garch``) and filtered forward; filtered historical simulation with the same frozen filter and the calm
history's standardised residuals (``market.historical.filtered_hs_var_es``). Levels 1 % and 2.5 %.

Methods: ``unwrapped``; ``aci`` (the engine's wrapper, gamma 0.005, band [0.001, 0.25]); ``rolling`` and ``tracker`` (the score-space
recalibrations of experiment 4, applied to the unwrapped forecasts, constants as there).

Predictions written down before the first run of this script (they follow from the theory section and are tested here):
 (a) in every shift scenario, for every model and level, the pass rate (Kupiec and conditional coverage both at least 0.05) of
     ``aci`` is above that of ``unwrapped``;
 (b) in ``no-shift`` the pass rate of ``aci`` is within 0.05 of ``unwrapped`` and the median relative FZ0 change is within 2 %;
 (c) the mean hit rate of ``aci`` is closer to the target than the unwrapped one in every shift scenario;
 (d) the repair is least complete in ``crash-decay``, the shortest window (H = 100);
 (e) ``aci`` lowers the mean absolute log error of the VaR against the true VaR for HS-250 in every shift scenario.
Seeds: replication ``k`` of scenario ``s`` uses ``numpy.random.default_rng(20261104 + 1000 * s + k)``. Output: ``e5_generators.json``.
"""
from __future__ import annotations

import argparse
import math
import os
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

NU = 5.0
OMEGA, A_G, B_G = 2e-6, 0.08, 0.90
CALM = 1000
REPS = 100
SCENARIOS = ("no-shift", "crisis-persistent", "crash-decay", "drift-up")
MODELS = ("hs-250", "garch-t", "fhs")
METHODS = ("unwrapped", "aci", "rolling", "tracker")
W_ROLL, THETA_MIN, THETA_MAX, ETA = 250, 0.25, 4.0, 0.05


def multiplier(scenario: str) -> np.ndarray:
    if scenario == "no-shift":
        return np.ones(500)
    if scenario == "crisis-persistent":
        t = np.arange(500)
        return np.where(t < 100, 1 + 2 * t / 100, np.where(t < 250, 3.0, 1.5))
    if scenario == "crash-decay":
        return 1 + 3 * 0.5 ** (np.arange(100) / 30.0)
    if scenario == "drift-up":
        return 1 + 0.8 * np.arange(250) / 249.0
    raise ValueError(scenario)


def unit_t_var_es(alpha: float, nu: float = NU) -> tuple[float, float]:
    """Quantile and tail mean of the unit-variance Student-t (return convention: both negative)."""
    from scipy import stats

    s = math.sqrt((nu - 2.0) / nu)
    q = stats.t.ppf(alpha, nu)
    es = -stats.t.pdf(q, nu) / alpha * (nu + q * q) / (nu - 1.0)
    return s * q, s * es


def simulate(rng: np.random.Generator, m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Returns ``r`` (calm history then evaluation days) and the latent conditional volatility ``sigma`` of each day."""
    n = CALM + m.size
    z = rng.standard_t(NU, size=n) * math.sqrt((NU - 2.0) / NU)
    sigma = np.empty(n)
    u = np.empty(n)
    s2 = OMEGA / (1 - A_G - B_G)
    for t in range(n):
        sigma[t] = math.sqrt(s2)
        u[t] = sigma[t] * z[t]
        s2 = OMEGA + A_G * u[t] ** 2 + B_G * s2
    mm = np.concatenate([np.ones(CALM), m])
    return mm * u, sigma


def frozen_forecasters(r: np.ndarray):
    """The three causal forecasters of the experiment; GARCH-t and FHS carry parameters fitted on the calm history only."""
    from riskvalidation.market import conformal as cf
    from riskvalidation.market import garch as rg
    from riskvalidation.market import historical as rh

    fit = rg.fit_garch(r[:CALM], kind="garch", innovation="student-t", mean="constant")
    p = fit.params
    mu, om, al, be = float(p["mu"]), float(p["omega"]), float(p["alpha[1]"]), float(p["beta[1]"])
    flt = rg.garch_filter(fit, r[:CALM])
    std_res = np.asarray(flt.std_residuals, float)
    n = r.size
    sig = np.empty(n)                                      # one-step-ahead volatility of day t from the returns before t
    # the forward recursion starts at the unconditional variance of the fit and uses only the returns before day t (causal)
    s2 = om / max(1 - al - be, 1e-6)
    for t in range(n):
        sig[t] = math.sqrt(s2)
        s2 = om + al * (r[t] - mu) ** 2 + be * s2
    hs = cf.historical_forecaster(r, 250)

    def garch_t(t: int, level: float):
        q, eq = rg.innovation_var_es(fit, level)
        return mu + sig[t] * q, mu + sig[t] * eq

    def fhs(t: int, level: float):
        return rh.filtered_hs_var_es(std_res, mu, sig[t], level)

    return {"hs-250": hs, "garch-t": garch_t, "fhs": fhs}


def score_space(loss, var, es, alpha):
    """The two score-space recalibrations of experiment 4 on one sequence of positive-loss VaR and ES."""
    s = loss / var
    n = s.size
    roll = np.ones(n)
    for t in range(n):
        past = s[max(0, t - W_ROLL):t]
        k = math.ceil((past.size + 1) * (1 - alpha))
        if past.size and k <= past.size:
            roll[t] = min(max(np.sort(past)[k - 1], THETA_MIN), THETA_MAX)
    trk, cur = np.ones(n), 1.0
    for t in range(n):
        trk[t] = cur
        cur = max(cur + ETA * (float(s[t] > cur) - alpha), THETA_MIN)
    return {"rolling": roll, "tracker": trk}


def one_rep(args):
    si, scen, k = args
    from riskvalidation.market import conformal as cf

    rng = np.random.default_rng(common.SEED_BOOT + 1000 * si + k)
    m = multiplier(scen)
    r, sigma = simulate(rng, m)
    mm = np.concatenate([np.ones(CALM), m])
    fcs = frozen_forecasters(r)
    first = CALM
    loss = -r[first:]
    out = []
    for model, f in fcs.items():
        for alpha in common.LEVELS:
            q, e = unit_t_var_es(alpha)
            true_var = mm[first:] * sigma[first:] * -q
            true_es = mm[first:] * sigma[first:] * -e
            runs = {"unwrapped": cf.aci_var_es(r, f, alpha, 0.0, first, common.LEVEL_MIN, common.LEVEL_MAX),
                    "aci": cf.aci_var_es(r, f, alpha, common.GAMMA, first, common.LEVEL_MIN, common.LEVEL_MAX)}
            var_u, es_u = -runs["unwrapped"].var, -runs["unwrapped"].es
            variants = {"unwrapped": (var_u, es_u), "aci": (-runs["aci"].var, -runs["aci"].es)}
            for name, th in score_space(loss, var_u, es_u, alpha).items():
                variants[name] = (th * var_u, th * es_u)
            base_s = None
            for name in METHODS:
                v, e = variants[name]
                e = np.maximum(e, v)                       # positive-loss convention: ES at least the VaR (rounding only)
                s = common.scores(loss, v, e, alpha)
                if name == "unwrapped":
                    base_s = s
                out.append({"scenario": scen, "rep": k, "model": model, "alpha": alpha, "method": name, "passes": common.passes(s),
                            "independence_ok": s["independence_p"] is not None and s["independence_p"] >= common.PASS_P,
                            "hit_rate": s["hit_rate"], "fz0_change": None if name == "unwrapped" else common.fz0_change(s, base_s),
                            "log_var_err": float(np.mean(np.abs(np.log(v / true_var)))), "log_var_bias": float(np.mean(np.log(v / true_var))),
                            "log_es_bias": float(np.mean(np.log(e / true_es))), "z2": s["z2"],
                            "n_clipped": int(runs["aci"].n_clipped) if name == "aci" else 0})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--reps", type=int, default=REPS)
    a = ap.parse_args()
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    t0 = time.perf_counter()
    tasks = [(si, s, k) for si, s in enumerate(SCENARIOS) for k in range(a.reps)]
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for i, part in enumerate(pool.map(one_rep, tasks, chunksize=2)):
            rows += part
            if i % 50 == 0:
                print(f"  {i + 1}/{len(tasks)} at {time.perf_counter() - t0:.0f}s", flush=True)
    p = common.dump({"nu": NU, "garch": [OMEGA, A_G, B_G], "calm_days": CALM, "reps": a.reps, "scenarios": list(SCENARIOS),
                     "seed_base": common.SEED_BOOT, "rows": rows, "seconds": round(time.perf_counter() - t0)}, "e5_generators.json")
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
