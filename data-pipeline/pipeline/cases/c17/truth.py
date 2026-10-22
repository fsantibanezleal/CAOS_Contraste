"""The true annual loss distribution of a variant (CT-1703, CT-1704): the compound Poisson of the generator's GPD severity.

The 99.9 percent quantile is computed once, by the engine's Fourier aggregation on a fine grid (step EUR 1,000 or more for the
heaviest variant, 2^21 points), cross-checked by the engine's Panjer recursion on a coarser grid and by a Monte Carlo of the
generator itself. The truth counts every loss the generator draws at or above its floor, whatever the collection threshold (D2 of
the unit sizing). A tail index of 1 or more has no mean and no expected shortfall: none is computed or written.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.oprisk import aggregate as agg
from riskvalidation.oprisk import distributions as dist
from riskvalidation.oprisk import sla

from . import aggregation as ga
from . import params as P
from .generator import Variant

TRUTH_POINTS = 1 << 21
PANJER_POINTS = 32768
COARSE_EXTENT = 1.25  # the Panjer cross-check grid ends at this multiple of the Fourier quantile
NO_MEAN = "the tail index is 1 or more: the severity has an infinite mean, so the annual loss has no mean"
NOTICE = {
    "en": "Synthetic data: the truth is the 99.9 percent quantile of the annual loss of every loss the generator draws at or above its "
          "floor, whatever the collection threshold; it is computed by the engine and checked by a Monte Carlo of the generator.",
    "es": "Datos sintéticos: la verdad es el cuantil 99,9 por ciento de la pérdida anual de toda pérdida que el generador simula sobre "
          "su piso, cualquiera sea el umbral de recolección; la calcula el motor y la verifica una simulación Monte Carlo del generador."}


@dataclass(frozen=True)
class Truth:
    quantile_eur: float
    method: str
    grid_step_eur: float
    truth_block: dict[str, Any]
    exceedance_block: dict[str, Any]
    mean_eur: float | None


def compute(v: Variant, mc_years: int = P.MC_YEARS_TRUTH, seed: int = P.MC_TRUTH_SEED) -> Truth:
    """The truth of a variant; memoised in the process (a pure function of its arguments)."""
    return _compute(v, int(mc_years), int(seed))


@functools.lru_cache(maxsize=None)
def _compute(v: Variant, mc_years: int, seed: int) -> Truth:
    lam, par = v.lambda_per_year, v.sev_params
    q_fft, step, h_fft = ga.grid_aggregate("fft", lam, "gpd", par, n_points=TRUTH_POINTS, step_floor=P.PANJER_STEP_EUR)
    q_pan, step_p, h_pan = ga.grid_aggregate("panjer", lam, "gpd", par, n_points=PANJER_POINTS, start_extent=COARSE_EXTENT * q_fft)
    sample = agg.simulate_annual_losses("poisson", (lam,), "gpd", par, mc_years, seed, chunk_years=P.MC_CHUNK_YEARS)
    q_mc, se_mc = agg.mc_quantile(sample.losses, P.LEVEL)
    axis = ga.exceedance_axis(q_fft)
    srt = np.sort(sample.losses)
    sf_mc = 1.0 - np.searchsorted(srt, axis, side="right") / srt.size
    del srt, sample
    sf_fft = ga.sf_on_grid(h_fft, step, axis)
    sf_pan = ga.sf_within_grid(h_pan, step_p, axis)
    q_sla = sla.sla_var(lam, "gpd", par, P.LEVEL)
    finite_mean = np.isfinite(dist.severity_moment("gpd", par, 1))
    mean = float(agg.compound_poisson_moments(lam, "gpd", par).mean) if finite_mean else None
    mc_check = {"n_years": int(mc_years), "seed": int(seed), "value_eur": float(q_mc), "standard_error_eur": float(se_mc),
                "agrees": bool(abs(q_mc - q_fft) <= 3.0 * se_mc)}
    if not mc_check["agrees"]:
        raise ValueError(f"the Monte Carlo quantile {q_mc:.6g} (se {se_mc:.3g}) disagrees with the Fourier truth {q_fft:.6g} for tail index {v.tail_index}")
    truth_block = {
        "label": "synthetic-known-truth", "currency": P.CURRENCY,
        "frequency": {"law": "poisson", "lambda_per_year": v.lambda_per_year, "counted_above_eur": P.FLOOR_EUR},
        "severity": {"law": "gpd", "location_eur": P.FLOOR_EUR, "scale_eur": v.scale_eur, "tail_index": v.tail_index},
        "annual_loss_quantile": {"level": P.LEVEL, "value_eur": float(q_fft), "method": "fft", "grid_step_eur": float(step),
                                 "mc_check": mc_check},
        "annual_loss_mean": {"value_eur": mean, "reason": None if mean is not None else NO_MEAN},
        "notice": NOTICE,
    }
    exceedance = {
        "currency": P.CURRENCY, "grid_eur": [float(x) for x in axis],
        "monte_carlo": {"n_years": int(mc_years), "seed": int(seed), "exceedance": [float(x) for x in sf_mc]},
        "panjer": {"step_eur": float(step_p), "exceedance": sf_pan},
        "fft": {"n_points": TRUTH_POINTS, "padding_factor": 4, "tilt": 0.0, "exceedance": [float(x) for x in sf_fft]},
        "quantile_999_eur": {"monte_carlo": float(q_mc), "panjer": float(q_pan), "fft": float(q_fft), "sla": float(q_sla)},
    }
    return Truth(float(q_fft), "fft", float(step), truth_block, exceedance, mean)
