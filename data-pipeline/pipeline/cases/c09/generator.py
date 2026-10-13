"""The revolving-line generator with a known CCF (CT-1002, CT-1003, CT-1004).

``draw_population(seed, n_facilities)`` draws the facilities of one replication and which of them default, with every random
number the lines need (level-independent: the same seed gives the same facilities at every acceleration level, so only the drawing
profile differs between levels). ``realise(population, level)`` turns the defaulters' draws into balance paths and an EAD for one
level. Only the defaulters get paths: the CCF is estimated on defaulted facilities only (dossier 04 G.3).

A defaulter's state twelve months before default is drawn from the Federal Reserve marginals of its tier (``params``): an interior
utilisation, a fully drawn line (undrawn amount zero) or a line over its limit. An interior line draws down its undrawn amount
geometrically at a rate ``r rho_tier nu`` (``nu`` a mean-one gamma frailty) weighted by the level's monthly weights; its CCF is
``1 - exp(-r rho nu S)`` plus a normal noise (fees, paydowns, overlimit drawings), and the EAD is ``E0 + CCF (L - E0)`` floored at 0.
A fully drawn or overlimit line cannot draw: its EAD is its balance plus capitalised interest and fees.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import beta as beta_dist

from . import params
from .params import HORIZON, MONTHS, PARAMS, TIERS

SEED_STREAM = 9


@dataclass(frozen=True)
class Population:
    """The level-independent draws of one replication (defaulters only, apart from the counts)."""

    seed: int
    n_facilities: int
    tier: np.ndarray            # (A,) int 0..2
    limit: np.ndarray           # (A,) USD
    utilisation: np.ndarray     # (A,) balance over limit twelve months before default
    interior: np.ndarray        # (A,) bool: 0 < utilisation < 1, a CCF is defined
    score: np.ndarray
    apr: np.ndarray
    default_month: np.ndarray   # (A,) int, the calendar month index of the default
    frailty: np.ndarray
    eps: np.ndarray
    fee: np.ndarray
    path_noise: np.ndarray      # (A, 11)


@dataclass(frozen=True)
class Defaulters:
    """The defaulted facilities of one replication at one acceleration level."""

    seed: int
    level: int
    n_facilities: int
    tier: np.ndarray
    limit: np.ndarray           # (A,)
    score: np.ndarray
    apr: np.ndarray
    interior: np.ndarray
    default_month: np.ndarray   # (A,) calendar month index of the default, 12 to 47
    window: np.ndarray          # (A, 13) balance at months 0 to 12 of the run-up; column 12 is the EAD
    drawn: np.ndarray           # (A, MONTHS) balance by calendar month (flat before the run-up, the EAD after the default)
    ead: np.ndarray             # (A,)
    n_floored: int              # defaulters whose EAD was floored at 0

    @property
    def n_defaults(self) -> int:
        return int(self.ead.size)


def draw_population(seed: int, n_facilities: int) -> Population:
    cal = PARAMS["fed_calibration"]
    rng = np.random.default_rng([int(seed), SEED_STREAM])
    tier_all = rng.choice(len(TIERS), size=n_facilities, p=np.asarray(PARAMS["tier_share"]))
    default = rng.random(n_facilities) < np.asarray(PARAMS["tier_pd"])[tier_all]
    tier = tier_all[default]
    a = int(tier.size)
    z_limit = rng.standard_normal(a)
    u_state, u_beta, u_over = rng.random(a), rng.random(a), rng.random(a)
    z_score, z_apr = rng.standard_normal(a), rng.standard_normal(a)
    month = rng.integers(params.FIRST_DEFAULT_MONTH, MONTHS, size=a)
    frailty = rng.gamma(PARAMS["frailty_shape"], 1.0 / PARAMS["frailty_shape"], size=a)
    eps = rng.standard_normal(a) * PARAMS["ccf_noise_sd"]
    fee = np.abs(rng.standard_normal(a)) * PARAMS["fee_sd"]
    path_noise = rng.standard_normal((a, HORIZON - 1))
    c = [cal[t] for t in TIERS]
    mu = np.array([x["limit_log_mu"] for x in c])[tier]
    sg = np.array([x["limit_log_sigma"] for x in c])[tier]
    limit = np.maximum(np.round(np.exp(mu + sg * z_limit), -1), 100.0)
    util = np.empty(a)
    p_full = np.array([x["p_full"] for x in c])[tier]
    p_over = np.array([x["p_over"] for x in c])[tier]
    is_full = (u_state >= 1.0 - p_full - p_over) & (u_state < 1.0 - p_over)
    is_over = u_state >= 1.0 - p_over
    interior = ~(is_full | is_over)
    for k in range(len(TIERS)):
        m = interior & (tier == k)
        util[m] = 0.995 * beta_dist.ppf(u_beta[m], c[k]["beta_a"], c[k]["beta_b"])
    util[is_full] = 1.0
    excess = np.array([x["over_excess_mean"] for x in c])[tier]
    util[is_over] = 1.0 + np.minimum(-np.log1p(-u_over[is_over]) * excess[is_over], PARAMS["over_cap"] - 1.0)
    score = np.clip(np.array([x["score_mean"] for x in c])[tier] + np.array([x["score_sd"] for x in c])[tier] * z_score, 300.0, 850.0)
    apr = np.clip(np.array([x["apr_mean"] for x in c])[tier] + np.array([x["apr_sd"] for x in c])[tier] * z_apr, 5.0, 35.0)
    return Population(int(seed), int(n_facilities), tier, limit, util, interior, score, apr, month, frailty, eps, fee, path_noise)


def realise(pop: Population, level: int) -> Defaulters:
    """The balance paths and EAD of the defaulters of ``pop`` at one acceleration level."""
    w = params.monthly_weights(level)
    cum = np.concatenate([[0.0], np.cumsum(w)])                     # (13,) cumulative weights, index = month of the run-up
    s_total = float(cum[-1])
    rho = np.asarray(PARAMS["tier_rate_multiplier"])[pop.tier]
    rate = PARAMS["draw_rate"] * rho * pop.frailty                  # (A,)
    e0 = pop.utilisation * pop.limit
    ccf_line = 1.0 - np.exp(-rate * s_total) + pop.eps
    ead_draw = e0 + ccf_line * (pop.limit - e0)
    ead_stuck = e0 * (1.0 + pop.fee)
    ead_raw = np.where(pop.interior, ead_draw, ead_stuck)
    n_floored = int((ead_raw < 0).sum())
    ead = np.maximum(ead_raw, 0.0)
    shape = (1.0 - np.exp(-rate[:, None] * cum[None, :])) / (1.0 - np.exp(-rate * s_total))[:, None]   # (A, 13), 0 to 1
    window = e0[:, None] + (ead - e0)[:, None] * shape
    noise = pop.path_noise * (PARAMS["path_noise_sd"] * pop.limit)[:, None]
    window[:, 1:HORIZON] = np.maximum(window[:, 1:HORIZON] + noise, 0.0)
    window[:, 0], window[:, HORIZON] = e0, ead
    month = np.arange(MONTHS)[None, :] - (pop.default_month - HORIZON)[:, None]          # months into the run-up
    drawn = np.take_along_axis(window, np.clip(month, 0, HORIZON), axis=1)
    return Defaulters(pop.seed, level, pop.n_facilities, pop.tier, pop.limit, pop.score, pop.apr, pop.interior, pop.default_month,
                      window, drawn, ead, n_floored)


def generate(seed: int, level: int, n_facilities: int) -> Defaulters:
    return realise(draw_population(seed, n_facilities), level)
