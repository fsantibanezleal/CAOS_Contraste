"""The C13 desk P&L generator: a two-factor spread desk with a known true risk model and the six planted deficiencies.

One replication is a pure function of its seed (``np.random.default_rng(seed)``; the draws are made in a fixed order whatever
the deficiency). It returns the hypothetical P&L (HPL), the risk-theoretical P&L (RTPL) and the desk VaR of the risk model at
97.5 and 99 percent over the last 250 days, as decimals of the desk notional. Nothing here computes a PLA statistic, a zone or
a back-test count: that is ``riskvalidation.market`` (CT-1305).

The true model (the closed forms the tests check, see ``known_pearson``):

- the factors are ``x = w @ L(rho).T`` for orthonormal drivers ``w`` and the Cholesky factor of the factor correlation;
- the day's scale ``sigma_t = exp(mu + g_(t-1))`` is a log-AR(1) known at the start of the day, so a VaR built on it is an
  ex-ante forecast, and ``E sigma^2 = 1``;
- HPL = ``sigma_t * l.x_t`` + pricing noise ``u_t``; RTPL = the risk model's revaluation of the same moves;
- a deficiency changes only the risk model: its basis, its volatility input, its correlation, its factor set or the date of
  its P&L.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import lfilter
from scipy.stats import norm

from . import params
from .params import ALPHAS, BURN_DAYS, LOADINGS, RESIDUAL_SHARE, RHO_TRUE, VOL_PHI, VOL_SD, WINDOW_DAYS

_L = np.array(LOADINGS)
_MU = -VOL_SD ** 2                                   # E sigma^2 = exp(2 mu + 2 VOL_SD^2) = 1
_ETA = VOL_SD * np.sqrt(1.0 - VOL_PHI ** 2)          # stationary sd of the log volatility is VOL_SD


def chol(rho: float) -> np.ndarray:
    return np.array([[1.0, 0.0], [rho, np.sqrt(1.0 - rho * rho)]])


def factor_variance(rho: float = RHO_TRUE) -> float:
    """Variance of the factor P&L at unit scale: ``l' R l``."""
    return float(_L @ np.array([[1.0, rho], [rho, 1.0]]) @ _L)


def base_sd() -> float:
    """sd of the HPL of a variant with nothing planted (factor P&L plus pricing noise), the unit of the ``*_share`` parameters."""
    return float(np.sqrt(factor_variance() * (1.0 + RESIDUAL_SHARE ** 2)))


def share_scale(share: float) -> float:
    """sd of a planted term that makes up ``share`` of the sd of the HPL it is added to."""
    return base_sd() * share / np.sqrt(1.0 - share * share)


@dataclass(frozen=True)
class Replication:
    """The last 250 days of one replication: HPL, RTPL and the risk model's desk VaR (positive loss numbers) by tail level."""

    deficiency: str
    index: int
    seed: int
    hpl: np.ndarray
    rtpl: np.ndarray
    var: dict[float, np.ndarray]

    @property
    def loss(self) -> np.ndarray:
        return -self.hpl


def replicate(did: str, index: int, case_seed: int = params.CASE_SEED) -> Replication:
    """Replication ``index`` of deficiency ``did``: seed ``seed_base(did, case_seed) + index``."""
    if did not in params.IDS:
        raise ValueError(f"unknown deficiency {did!r}; known: {list(params.IDS)}")
    seed = params.seed_of(did, index, case_seed)
    rng = np.random.default_rng(seed)
    n = BURN_DAYS + WINDOW_DAYS
    e, w, u, b = rng.standard_normal(n), rng.standard_normal((n, 3)), rng.standard_normal(n), rng.standard_normal(n)
    g = lfilter([_ETA], [1.0, -VOL_PHI], e)
    sigma = np.exp(_MU + np.concatenate(([0.0], g[:-1])))                    # known at the start of the day
    rho_m = RHO_TRUE + (params.value(did, "correlation_error") if did == "wrong-correlation" else 0.0)
    sigma_m = sigma
    if did == "stale-volatility":
        lag = int(params.value(did, "vol_lag_days"))
        sigma_m = np.concatenate((np.full(lag, sigma[0]), sigma[:-lag]))
    x_true, x_model = w[:, :2] @ chol(RHO_TRUE).T, w[:, :2] @ chol(rho_m).T
    hpl = sigma * (x_true @ _L) + RESIDUAL_SHARE * np.sqrt(factor_variance()) * u
    rtpl = sigma_m * (x_model @ _L)
    if did == "missing-basis":
        hpl = hpl + share_scale(params.value(did, "basis_sd_share")) * b
    if did == "omitted-factor":
        hpl = hpl + sigma * w[:, 2] * share_scale(params.value(did, "omitted_loading_share"))
    sd_model = sigma_m * np.sqrt(factor_variance(rho_m))
    if did == "time-misalignment":
        lag = int(params.value(did, "lag_days"))
        rtpl = np.concatenate((np.zeros(lag), rtpl[:-lag]))
        sd_model = sigma * np.sqrt(factor_variance())
    last = slice(BURN_DAYS, n)
    var = {a: norm.ppf(1.0 - a) * sd_model[last] for a in ALPHAS}
    return Replication(did, index, seed, hpl[last].copy(), rtpl[last].copy(), var)


def known_pearson(did: str) -> float:
    """The population Pearson correlation of HPL and RTPL, in closed form from the parameters (the generator's known truth).

    Rank and KS statistics have no closed form; the Pearson correlation is the quantity the planted term is sized in, and the
    tests check the simulation against it at a large sample.
    """
    a = _L @ chol(RHO_TRUE)              # HPL direction in the drivers: l' L
    v_hpl = float(a @ a) * (1.0 + RESIDUAL_SHARE ** 2)
    if did == "time-misalignment":
        return 0.0
    if did == "wrong-correlation":
        b = _L @ chol(RHO_TRUE + params.value(did, "correlation_error"))
        return float(a @ b) / np.sqrt(v_hpl * float(b @ b))
    v_rt = float(a @ a)
    cov = v_rt
    if did == "stale-volatility":
        lag = params.value(did, "vol_lag_days")
        cov = v_rt * float(np.exp(-VOL_SD ** 2 * (1.0 - VOL_PHI ** lag)))
    if did in ("missing-basis", "omitted-factor"):
        name = "basis_sd_share" if did == "missing-basis" else "omitted_loading_share"
        v_hpl += share_scale(params.value(did, name)) ** 2
    return cov / np.sqrt(v_hpl * v_rt)
