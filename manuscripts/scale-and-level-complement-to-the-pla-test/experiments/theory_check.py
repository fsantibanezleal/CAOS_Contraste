"""Independent simulation of the noise-free stale-volatility model of the Theory section, to separate the closed forms (population
quantities) from the finite-window behaviour of a 250-day desk-year.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/scale-and-level-complement-to-the-pla-test/experiments/theory_check.py

For each lag L the model HPL_t = sigma_t zeta_t, RTPL_t = sigma_{t-L} zeta_t (scale c = 1, no pricing noise) is simulated with the
generator's volatility law (``VOL_PHI``, ``VOL_SD``); the Mincer-Zarnowitz slope and the Pearson correlation of the 20-day rolling
means of the absolute series are computed on windows of T days. The mean over windows of T = 250 days is compared with the mean
over windows of T = 100,000 days and with the closed forms of ``theory.py``. Seeds: 20261104 + replication.
Writes ``results_theory.json``.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy.signal import lfilter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import theory  # noqa: E402

LAGS = (0, 2, 5, 10, 20, 40, 80)
W = 20


def path(t: int, lag: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    v, phi = theory.V, theory.PHI
    eta, mu = np.sqrt(v * (1 - phi ** 2)), -v
    burn = 600
    n = burn + t + lag
    g = lfilter([eta], [1.0, -phi], rng.standard_normal(n))
    sigma = np.exp(mu + np.concatenate(([0.0], g[:-1])))
    zeta = rng.standard_normal(n)
    hpl = sigma * zeta
    rtpl = np.concatenate((np.full(lag, sigma[0]), sigma[: n - lag])) * zeta
    return hpl[burn:burn + t], rtpl[burn:burn + t]


def stats_of(h: np.ndarray, r: np.ndarray) -> tuple[float, float]:
    slope = float(np.cov(h, r, bias=True)[0, 1] / np.var(r))
    k = np.ones(W) / W
    corr = float(np.corrcoef(np.convolve(np.abs(h), k, "valid"), np.convolve(np.abs(r), k, "valid"))[0, 1])
    return slope, corr


def main() -> int:
    out = []
    for lag in LAGS:
        row = {"lag": lag, "slope_theory": theory.slope(lag), "corr_theory": theory.rolling_corr(lag, W)}
        for label, t, reps in (("T250", 250, 4000), ("T100000", 100000, 20)):
            s, c = [], []
            for i in range(reps):
                h, r = path(t, lag, np.random.default_rng(20261104 + i))
                a, b = stats_of(h, r)
                s.append(a)
                c.append(b)
            row[label] = {"reps": reps, "slope_mean": float(np.mean(s)), "slope_se": float(np.std(s, ddof=1) / np.sqrt(reps)),
                          "corr_mean": float(np.mean(c)), "corr_se": float(np.std(c, ddof=1) / np.sqrt(reps))}
        out.append(row)
        print(row["lag"], round(row["corr_theory"], 4), {k: round(row[k]["corr_mean"], 4) for k in ("T250", "T100000")})
    limit = theory.rolling_corr(10 ** 6, W)
    (HERE / "results_theory.json").write_text(json.dumps({"window": W, "rows": out, "corr_limit_large_lag": limit}, indent=1), encoding="utf-8")
    print("corr limit", limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
