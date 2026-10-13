"""The market-risk formulas of dossier 05 (sections A and B) and dossier 01 (D.4), in pure Python, used by the fixture
builder and by the contract tests to recompute what a U8 document states. Each function names its dossier line.
Losses are positive numbers (the document convention); the engine stores the return convention (dossier 05 A.0)."""
from __future__ import annotations

import math
from statistics import NormalDist

ND = NormalDist()


# --- binomial and chi-square (dossier 05 B.1, B.2, B.4; dossier 01 D.4) --------------------------------------------


def binom_pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * p**k * (1 - p) ** (n - k)


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k), X ~ Bin(n, p): the MAR32.9 Table 1 cumulative probability at n = 250, p = 0.01 (dossier 01 D.4)."""
    return sum(binom_pmf(i, n, p) for i in range(0, k + 1))


def chi2_sf(x: float, df: int) -> float:
    if df == 1:
        return math.erfc(math.sqrt(x / 2))
    if df == 2:
        return math.exp(-x / 2)
    raise ValueError(df)


def chi2_ppf(q: float, df: int) -> float:
    lo, hi = 0.0, 50.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if 1 - chi2_sf(mid, df) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _xlogy(x: float, y: float) -> float:
    return 0.0 if x == 0 else x * math.log(y)


def kupiec_lr(n: int, x: int, p: float) -> float:
    """LR_POF of dossier 05 B.1, with pi_hat = x / n and the convention 0 ln 0 = 0."""
    pi = x / n
    return -2.0 * ((n - x) * math.log(1 - p) + _xlogy(x, p) - _xlogy(n - x, 1 - pi) - _xlogy(x, pi))


def kupiec_exact_p(n: int, x: int, p: float) -> float:
    """Exact two-sided binomial p-value: the total probability of the outcomes at most as likely as x (the contract
    decision D-1 of docs/contracts/engine/market-api.md; the dossier says only: exact binomial p-value)."""
    px = binom_pmf(x, n, p)
    return min(1.0, sum(binom_pmf(k, n, p) for k in range(n + 1) if binom_pmf(k, n, p) <= px * (1 + 1e-7)))


def transitions(ind: list[int]) -> tuple[int, int, int, int]:
    n00 = n01 = n10 = n11 = 0
    for a, b in zip(ind, ind[1:]):
        if a == 0 and b == 0:
            n00 += 1
        elif a == 0 and b == 1:
            n01 += 1
        elif a == 1 and b == 0:
            n10 += 1
        else:
            n11 += 1
    return n00, n01, n10, n11


def christoffersen_ind_lr(ind: list[int]) -> float:
    """LR_ind of dossier 05 B.2 (the convention 0^0 = 1, i.e. 0 ln 0 = 0)."""
    n00, n01, n10, n11 = transitions(ind)
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)
    pi01 = n01 / (n00 + n01) if n00 + n01 else 0.0
    pi11 = n11 / (n10 + n11) if n10 + n11 else 0.0
    null = _xlogy(n00 + n10, 1 - pi) + _xlogy(n01 + n11, pi)
    alt = _xlogy(n00, 1 - pi01) + _xlogy(n01, pi01) + _xlogy(n10, 1 - pi11) + _xlogy(n11, pi11)
    return -2.0 * (null - alt)


# --- the FZ class and the tick loss (dossier 05 A.1, B.6), return convention -------------------------------------------


def fz_general(y: float, v: float, e: float, alpha: float, g1, g2, cal_g2) -> float:
    """L_FZ of A.1 (arXiv 1707.05108 eq. 4) in the return convention: v, e < 0."""
    hit = 1.0 if y <= v else 0.0
    return (hit - alpha) * (g1(v) - g1(y)) + g2(e) * (e - v + hit * (v - y) / alpha) - cal_g2(e)


def fz0_return(y: float, v: float, e: float, alpha: float) -> float:
    """FZ0 of A.1 (eq. 6): -(1/(alpha e)) 1{y <= v}(v - y) + v/e + log(-e) - 1, with y the return, v < 0, e <= v."""
    hit = 1.0 if y <= v else 0.0
    return -(1.0 / (alpha * e)) * hit * (v - y) + v / e + math.log(-e) - 1.0


def fz0_loss(loss: float, var: float, es: float, alpha: float) -> float:
    """FZ0 from positive loss numbers: y = -loss, v = -var, e = -es (A.0 conversion)."""
    return fz0_return(-loss, -var, -es, alpha)


def tick_loss(loss: float, var: float, alpha: float) -> float:
    """Tick loss of A.2 row 11, (alpha - 1{y < f})(y - f) with y = -loss and f = -var."""
    hit = 1.0 if loss > var else 0.0
    return (alpha - hit) * (var - loss)


# --- Diebold-Mariano (dossier 05 B.6; the Bartlett-kernel HAC is the contract decision D-2) ----------------------------


def dm_statistic(d: list[float], lags: int) -> float:
    t = len(d)
    mean = sum(d) / t
    c = [x - mean for x in d]

    def gamma(j: int) -> float:
        return sum(c[i] * c[i - j] for i in range(j, t)) / t

    lrv = gamma(0) + 2.0 * sum((1.0 - j / (lags + 1.0)) * gamma(j) for j in range(1, lags + 1))
    return mean / math.sqrt(lrv / t)


def two_sided_p(z: float) -> float:
    return 2.0 * (1.0 - ND.cdf(abs(z)))


# --- EWMA, Cornish-Fisher, age weights, normal VaR and ES (dossier 05 A.2) -------------------------------------------


def ewma_effective_days(lam: float, eps: float) -> float:
    """K = ln(eps) / ln(lambda) (A.2 row 6): 74.4 for (0.94, 0.01) and 151.2 for (0.97, 0.01); the dossier says 74 and 151."""
    return math.log(eps) / math.log(lam)


def age_weights(lam: float, k: int) -> list[float]:
    """w_i = (1 - lambda) / (1 - lambda^K) lambda^(i-1), i = 1..K (A.2 row 2)."""
    return [(1 - lam) / (1 - lam**k) * lam ** (i - 1) for i in range(1, k + 1)]


def cornish_fisher_z(z: float, skew: float, ex_kurt: float) -> float:
    """z_CF of A.2 row 5."""
    return z + (z**2 - 1) * skew / 6 + (z**3 - 3 * z) * ex_kurt / 24 - (2 * z**3 - 5 * z) * skew**2 / 36


def normal_var_es_loss(mu: float, sigma: float, alpha: float) -> tuple[float, float]:
    """Delta-normal VaR and ES as positive losses (A.2 row 4)."""
    z = ND.inv_cdf(alpha)
    return -(mu + z * sigma), -mu + sigma * ND.pdf(z) / alpha


# --- the Basel traffic light (dossier 01 D.4, dossier 05 B.4) -----------------------------------------------------------

FRTB_MULTIPLIER = [1.50] * 5 + [1.70, 1.76, 1.83, 1.88, 1.92] + [2.00]  # exceptions 0..10 (10 = ten or more), MAR32.9
US_MULTIPLIER = [3.00] * 5 + [3.40, 3.50, 3.65, 3.75, 3.85] + [4.00]    # 12 CFR 217.204, dossier 05 B.4


def traffic_zone(exceptions: int) -> str:
    return "green" if exceptions <= 4 else "amber" if exceptions <= 9 else "red"


def rolling_counts(flags: list[int], window: int) -> list[int]:
    out, run = [], 0
    for i, f in enumerate(flags):
        run += f
        if i >= window:
            run -= flags[i - window]
        if i >= window - 1:
            out.append(run)
    return out


# --- the ES back-test Z2 (dossier 05 B.5) ------------------------------------------------------------------------------


def z2(loss: list[float], var: list[float], es: list[float], alpha: float) -> float:
    """Z2 = sum X_t I_t / (T alpha ES_t) + 1 with X_t the P&L (-loss) and ES_t > 0."""
    t = len(loss)
    return sum((-lo) * (1 if lo > v else 0) / (t * alpha * e) for lo, v, e in zip(loss, var, es)) + 1.0


# --- PLA (dossier 01 D.4: MAR32.36 to MAR32.42) -------------------------------------------------------------------------


def ranks(x: list[float]) -> list[float]:
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]) -> float:
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return cov / math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))


def ks_statistic(x: list[float], y: list[float], step: float = 0.004) -> float:
    """KS = sup |F_RTPL - F_HPL| with F(x) = step * #{obs <= x} (MAR32.39 to MAR32.41); x is HPL, y is RTPL."""
    sx, sy = sorted(x), sorted(y)
    pts = sorted(set(x) | set(y))
    import bisect
    return max(abs(step * bisect.bisect_right(sy, p) - step * bisect.bisect_right(sx, p)) for p in pts)


def pla_zone(rho: float, ks: float) -> str:
    """MAR32.42: green rho > 0.80 and KS < 0.09; red rho < 0.70 or KS > 0.12; amber otherwise."""
    if rho < 0.70 or ks > 0.12:
        return "red"
    if rho > 0.80 and ks < 0.09:
        return "green"
    return "amber"


def spearman_zone(rho: float) -> str:
    return "green" if rho > 0.80 else "red" if rho < 0.70 else "amber"


def ks_zone(ks: float) -> str:
    return "green" if ks < 0.09 else "red" if ks > 0.12 else "amber"
