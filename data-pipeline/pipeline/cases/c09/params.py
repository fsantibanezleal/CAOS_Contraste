"""The parameter file of the C09 generator: every number the revolving-line generator draws with, its source or its label
"assumption of the case", and the closed form of the known CCF it implies (CT-902, CT-904).

Model (docs/design/features/c09/design.md). A line that defaults draws down its undrawn amount over the twelve months before the
default. The undrawn amount decays geometrically, ``U_m = U_0 exp(-r rho_tier nu sum_{j<=m} w_j)``, with ``nu`` a mean-one gamma
frailty and ``w_j`` the monthly weights of the acceleration level (1 outside the acceleration window, ``factor`` inside it). The
share of the undrawn amount twelve months before default that is drawn by default is then the line's CCF, and its mean over the
defaulters is a closed form (the Laplace transform of the gamma frailty):

    known_ccf(level, h) = sum_t w_t * (1 - (1 + r rho_t S_h(level) / phi) ** (-phi)),     S_h = sum of the last h monthly weights

The draw rate ``r`` is solved once so that level 0 has the anchor CCF; the other levels keep the same ``r`` and differ only
in their weights, so the known CCF of a level is fixed by the parameters and never estimated.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
from scipy.optimize import brentq

CASE_ID = "C09"
GENERATOR = "revolving-line-generator/1.0.0"
TIERS = ("low", "typical", "high")
HORIZON = 12                    # months of drawdown before the default; the fixed-horizon design reads the CCF at its start
MONTHS = 48                     # months of the facility path (January of year 1 to December of year 4)
FIRST_DEFAULT_MONTH = 12        # a default needs twelve months of history before it
TOLERANCE = 0.02                # assumption of the case: a CCF estimate within two CCF points of the truth recovers it

#: acceleration levels: the factor multiplies the monthly drawing weight inside the last ``window`` months before default
LEVELS: tuple[dict[str, Any], ...] = (
    {"level": 0, "factor": 1.0, "window": 0},
    {"level": 1, "factor": 1.25, "window": 6},
    {"level": 2, "factor": 1.5, "window": 6},
    {"level": 3, "factor": 2.0, "window": 6},
    {"level": 4, "factor": 2.5, "window": 6},
    {"level": 5, "factor": 3.0, "window": 6},
)

_FED_FILES = tuple(
    {"tier": t, "name": f"cards-{t}-risk-2025.csv", "url": f"https://www.federalreserve.gov/supervisionreg/files/cards-{t}-risk-2025.csv",
     "bytes": b, "sha256": h, "fetched": "2026-10-13"}
    for t, b, h in (
        ("low", 10293, "53eab855a587b99b8b6b638e1522d666cf72e636059d91bdfddbb889a9227cc8"),
        ("typical", 10180, "2a92d1f1392911fdd9b4827f10503bb64d57b8213a65f71551caa4dbf32b8ace"),
        ("high", 10138, "ced97ff06ad6c0d42e52c09ecfa8ee51e98283d4f4345a52676d24a20cede9cf")))

PARAMS: dict[str, Any] = {
    "generator_version": GENERATOR,
    "sources": list(_FED_FILES),
    #: recalculated from the files by ``calibration.calibrate``; a test compares the two whenever the files are present
    "fed_calibration": {
        "low": {"n": 200, "limit_log_mu": 8.81869, "limit_log_sigma": 0.877511, "p_full": 0.0, "p_over": 0.09, "beta_a": 0.663142,
                "beta_b": 1.76277, "over_excess_mean": 0.457874, "score_mean": 765.435, "score_sd": 41.4693, "apr_mean": 15.9558,
                "apr_sd": 6.77738},
        "typical": {"n": 200, "limit_log_mu": 8.34766, "limit_log_sigma": 1.01027, "p_full": 0.01, "p_over": 0.15, "beta_a": 0.656179,
                    "beta_b": 1.38645, "over_excess_mean": 1.30404, "score_mean": 701.7, "score_sd": 91.5678, "apr_mean": 15.1033,
                    "apr_sd": 7.34275},
        "high": {"n": 200, "limit_log_mu": 7.78616, "limit_log_sigma": 0.930275, "p_full": 0.015, "p_over": 0.26, "beta_a": 1.31887,
                 "beta_b": 1.46726, "over_excess_mean": 0.992515, "score_mean": 635.235, "score_sd": 55.9098, "apr_mean": 18.1429,
                 "apr_sd": 7.20553}},
    "over_cap": 3.0,                      # utilisation above the limit is truncated here (the Fed files reach 5.8)
    "tier_share": (0.40, 0.35, 0.25),     # assumption of the case: the mix of the generated population by risk tier
    "tier_pd": (0.008, 0.030, 0.100),     # assumption of the case: the 12-month default probability by tier
    "ccf_anchor": 0.60,                   # assumption of the case: the known CCF of level 0 (no acceleration)
    "frailty_shape": 2.0,                 # assumption of the case: the gamma shape of the line-level drawing frailty
    "tier_rate_multiplier": (0.85, 1.0, 1.15),   # assumption of the case: riskier tiers draw faster
    "ccf_noise_sd": 0.15,                 # assumption of the case: fees, paydowns and overlimit drawings, on the CCF scale
    "fee_sd": 0.02,                       # assumption of the case: interest and fees capitalised on a fully drawn or overlimit line
    "path_noise_sd": 0.01,                # assumption of the case: month-to-month balance noise, share of the limit
    "small_undrawn_threshold": 50.0,      # USD; the switch of Qi (2009)
    "currency": "USD",
    "band_edges": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 4.0),
    "distribution_edges": (-1.0, -0.5, -0.25, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 2.0),
}


class LevelError(ValueError):
    """The acceleration levels are not six ordered levels with level 0 free of acceleration."""


def validate_levels(levels: tuple[dict[str, Any], ...]) -> None:
    if [x["level"] for x in levels] != [0, 1, 2, 3, 4, 5]:
        raise LevelError("the levels are 0 to 5, in order")
    if levels[0]["factor"] != 1.0 or levels[0]["window"] != 0:
        raise LevelError("level 0 carries no acceleration (factor 1, window 0)")
    for a, b in zip(levels, levels[1:], strict=False):
        if b["factor"] < a["factor"]:
            raise LevelError("the acceleration factor does not decrease with the level")
    if any(not 0 <= x["window"] <= HORIZON for x in levels):
        raise LevelError("an acceleration window lies outside the twelve months before default")


def monthly_weights(level: int) -> np.ndarray:
    """(12,) drawing weights of months 1 to 12 of the run-up; month 12 is the month of default."""
    x = LEVELS[level]
    w = np.ones(HORIZON)
    if x["window"]:
        w[HORIZON - x["window"]:] = x["factor"]
    return w


def horizon_weight(level: int, h: int) -> float:
    """S_h: the sum of the weights of the last h months before default."""
    return float(monthly_weights(level)[HORIZON - h:].sum())


def defined_tier_weights() -> tuple[float, ...]:
    """The share of each tier among the defaulters whose CCF is defined (an interior utilisation at the reference date)."""
    cal = PARAMS["fed_calibration"]
    raw = [s * pd * (1.0 - cal[t]["p_full"] - cal[t]["p_over"])
           for t, s, pd in zip(TIERS, PARAMS["tier_share"], PARAMS["tier_pd"], strict=True)]
    tot = sum(raw)
    return tuple(x / tot for x in raw)


def _mixture(rate: float, s: float) -> float:
    phi = PARAMS["frailty_shape"]
    return sum(w * (1.0 - (1.0 + rate * rho * s / phi) ** (-phi))
               for w, rho in zip(defined_tier_weights(), PARAMS["tier_rate_multiplier"], strict=True))


def solve_draw_rate() -> float:
    """The monthly draw rate r that gives level 0 the anchor CCF at twelve months."""
    s0 = horizon_weight(0, HORIZON)
    return float(brentq(lambda r: _mixture(r, s0) - PARAMS["ccf_anchor"], 1e-6, 5.0, xtol=1e-14, rtol=1e-14))


def known_ccf(level: int, horizon: int = HORIZON) -> float:
    """The known CCF of a level at ``horizon`` months before default (the fixed-horizon design reads ``horizon = 12``)."""
    return _mixture(PARAMS["draw_rate"], horizon_weight(level, horizon))


def parameter_hash() -> str:
    blob = json.dumps({"params": {k: v for k, v in PARAMS.items()}, "levels": LEVELS, "tolerance": TOLERANCE, "months": MONTHS},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


PARAMS["draw_rate"] = solve_draw_rate()      # solved once from the anchor; a test re-solves it
validate_levels(LEVELS)
