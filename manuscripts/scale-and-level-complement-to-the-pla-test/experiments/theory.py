"""The closed forms of the Theory section, evaluated for the parameters of the C13 generator.

The desk (``pipeline.cases.c13.generator``): HPL_t = sigma_t zeta_t c + pricing noise, RTPL_t = sigma_{t-L} zeta_t c for the
stale-volatility model, with c the standard deviation of the factor P&L at unit scale, zeta_t a standard normal shared by the two
series, and sigma_t = exp(mu + g_{t-1}) with g a stationary AR(1) of variance v = VOL_SD^2 and persistence phi and mu = -v.
"""
from __future__ import annotations

import numpy as np

from stats_core import params

V = params.VOL_SD ** 2
PHI = params.VOL_PHI
M2 = 2.0 / np.pi   # (E|zeta|)^2


def sigma_cov(h: int, v: float = V, phi: float = PHI) -> float:
    """Cov(sigma_s, sigma_u) at lag h = |s - u|, divided by (E sigma)^2: exp(v phi^|h|) - 1."""
    return float(np.exp(v * phi ** abs(h)) - 1.0)


def slope(lag: float, v: float = V, phi: float = PHI) -> float:
    """The population Mincer-Zarnowitz slope of HPL on RTPL when the volatility input is ``lag`` days old: E[sigma_t sigma_{t-L}]."""
    return float(np.exp(-v * (1.0 - phi ** lag)))


def rolling_corr(lag: int, w: int = 20, v: float = V, phi: float = PHI) -> float:
    """The population Pearson correlation of the w-day rolling means of |HPL| and |RTPL| of the noise-free stale-volatility model,
    Cov(A, B) / Var(A) with A the mean of sigma_s |zeta_s| and B the mean of sigma_{s-L} |zeta_s| over the same w days."""
    e = np.exp(-v)
    num = den = 0.0
    for s in range(w):
        for u in range(w):
            d = s - u
            if d == 0:
                den += 1.0 - M2 * e
                num += float(np.exp(-v * (1.0 - phi ** lag))) - M2 * e
            else:
                den += M2 * e * sigma_cov(d, v, phi)
                num += M2 * e * sigma_cov(d + lag, v, phi)
    return num / den


def size_mean(n: int, p: float) -> float:
    """The expected out-of-sample false-alarm rate of the critical value that is the (k+1)-th most extreme of n exchangeable null
    values, k = floor(p n): (k + 1) / (n + 1)."""
    k = int(np.floor(p * n + 1e-9))
    return (k + 1) / (n + 1)


def size_sd(n: int, p: float) -> float:
    """The standard deviation of the conditional false-alarm rate, Beta(k + 1, n - k)."""
    k = int(np.floor(p * n + 1e-9))
    a, b = k + 1, n - k
    return float(np.sqrt(a * b / ((a + b) ** 2 * (a + b + 1))))
