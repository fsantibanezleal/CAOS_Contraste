"""The parameters of the C13 desk P&L generator and of its six variants (every number the documents state comes from here).

The desk is a two-factor spread (long factor 1, short factor 2) whose true risk model is known: the factors share a stochastic
volatility path known at the start of the day, their correlation is ``RHO_TRUE`` and a small residual stands for pricing noise
between the hypothetical and the risk-theoretical P&L. Each deficiency is planted in the risk model or in the dating of its P&L
and nowhere else; the strength of each is a parameter below, fixed before the bake (design.md section 3) and never tuned to a
desired catch rate.
"""
from __future__ import annotations

from typing import Any

GENERATOR = "desk-pnl-generator/1.0.0"
GENERATOR_NAME = "desk-pnl-generator"
CASE_SEED = 13
WINDOW_DAYS = 250
BURN_DAYS = 300                    # days simulated before the window so the volatility path is stationary and the lag has history
N_REPLICATIONS = 1000
MAX_REPLICATIONS = 1000            # the seed ranges of two variants are 1000 apart, so a variant has at most 1000 replications
SEED_RULE = "seed_base+replication_index"

#: the true desk: P&L per unit factor shock (decimal of the desk notional per standard deviation of the factor)
LOADINGS = (0.006, -0.004)
RHO_TRUE = 0.6                     # true correlation of the two factors
VOL_PHI = 0.98                     # persistence of the log volatility
VOL_SD = 0.35                      # stationary sd of the log volatility (E[sigma^2] = 1)
RESIDUAL_SHARE = 0.10              # sd of the pricing noise as a share of the sd of the factor P&L, present in every variant

#: the MAR32.42 thresholds and the desk limits, as the documents state them (the engine decides every zone with its own copies)
PLA_THRESHOLDS = {"spearman_green": 0.8, "spearman_red": 0.7, "ks_green": 0.09, "ks_red": 0.12, "ecdf_step": 0.004,
                  "window_days": 250, "reference": "MAR32.42"}
ALPHAS = (0.025, 0.01)             # 97.5 percent and 99 percent, in the order of the contract

#: the six variants in the order of the SDD: id, planted flag, the statistic the deficiency is meant to break, its parameters
DEFICIENCIES: tuple[dict[str, Any], ...] = (
    {"id": "none", "planted": False, "intended": "none", "parameters": []},
    {"id": "missing-basis", "planted": True, "intended": "spearman",
     "parameters": [{"name": "basis_sd_share", "value": 0.65, "unit": "share-of-hpl-sd"}]},
    {"id": "stale-volatility", "planted": True, "intended": "ks",
     "parameters": [{"name": "vol_lag_days", "value": 20.0, "unit": "days"}]},
    {"id": "wrong-correlation", "planted": True, "intended": "either",
     "parameters": [{"name": "correlation_error", "value": 0.3, "unit": "correlation-points"}]},
    {"id": "omitted-factor", "planted": True, "intended": "spearman",
     "parameters": [{"name": "omitted_loading_share", "value": 0.6, "unit": "share-of-hpl-sd"}]},
    {"id": "time-misalignment", "planted": True, "intended": "spearman",
     "parameters": [{"name": "lag_days", "value": 1.0, "unit": "days"}]},
)
IDS = tuple(d["id"] for d in DEFICIENCIES)


def deficiency(did: str) -> dict[str, Any]:
    return next(d for d in DEFICIENCIES if d["id"] == did)


def value(did: str, name: str) -> float:
    return next(p["value"] for p in deficiency(did)["parameters"] if p["name"] == name)


def seed_base(did: str, case_seed: int = CASE_SEED) -> int:
    """Variant k of a bake with case seed s starts at 1000 s + 1000 k (13000, 14000, ... for the case seed 13)."""
    return 1000 * case_seed + 1000 * IDS.index(did)


def seed_of(did: str, index: int, case_seed: int = CASE_SEED) -> int:
    if not 0 <= index < MAX_REPLICATIONS:
        raise ValueError(f"replication index {index} is outside 0..{MAX_REPLICATIONS - 1}: the seed ranges of two variants would meet")
    return seed_base(did, case_seed) + index


def generator_parameters() -> list[dict[str, Any]]:
    return [
        {"name": "loading_1", "value": LOADINGS[0], "unit": "decimal-per-sd"},
        {"name": "loading_2", "value": LOADINGS[1], "unit": "decimal-per-sd"},
        {"name": "factor_correlation", "value": RHO_TRUE, "unit": "correlation"},
        {"name": "vol_persistence", "value": VOL_PHI, "unit": "per-day"},
        {"name": "vol_log_sd", "value": VOL_SD, "unit": "log-points"},
        {"name": "residual_sd_share", "value": RESIDUAL_SHARE, "unit": "share-of-factor-pnl-sd"},
        {"name": "burn_days", "value": float(BURN_DAYS), "unit": "days"},
    ]
