"""The grid plumbing around the engine's aggregation: a grid whose end is a multiple of the single loss scale of the fit, grown
until it carries the 99.9 percent quantile. Every probability, quantile and exceedance is the engine's (``panjer_recursion``,
``fft_aggregate``, ``quantile_from_pmf``, ``exceedance_from_pmf``); this module chooses the step and nothing else."""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from riskvalidation.oprisk import aggregate as agg
from riskvalidation.oprisk import sla

from . import params as P

GROWTH = 4.0
MAX_GROWTHS = 6


def grid_aggregate(method: str, lam: float, law: str, sev_params: Sequence[float], *, level: float = P.LEVEL,
                   n_points: int = P.REPLICATION_GRID_POINTS, step_floor: float = 0.0, padding: int = 4,
                   start_extent: float | None = None) -> tuple[float, float, np.ndarray]:
    """``(quantile, step, pmf)`` of the compound Poisson(``lam``) of the severity ``law``, by ``method`` (``panjer`` or ``fft``).

    The extent of the grid starts at four times the single loss approximation and is multiplied by four while the grid does not
    reach the quantile (the engine refuses a quantile the grid does not reach, never extrapolates)."""
    if method not in ("panjer", "fft"):
        raise ValueError(f"unknown aggregation {method!r}")
    extent = start_extent if start_extent is not None else GROWTH * sla.sla_var(lam, law, sev_params, level)
    last: Exception | None = None
    for _ in range(MAX_GROWTHS):
        step = max(extent / n_points, step_floor)
        f = agg.discretise_severity(law, sev_params, step, n_points)
        h = agg.panjer_recursion("poisson", (lam,), f) if method == "panjer" else agg.fft_aggregate("poisson", (lam,), f, padding_factor=padding)
        try:
            return agg.quantile_from_pmf(h, step, level), step, h
        except ValueError as exc:
            last = exc
            extent *= GROWTH
    raise ValueError(f"the grid never reached the quantile: {last}")


def sf_on_grid(h: np.ndarray, step: float, x: np.ndarray) -> np.ndarray:
    """The exceedance P(Z > x) on the points ``x``, read from the engine's exceedance curve of the pmf (linear between nodes)."""
    nodes, sf = agg.exceedance_from_pmf(h, step)
    return np.interp(x, nodes, sf)


def sf_within_grid(h: np.ndarray, step: float, x: np.ndarray) -> list[float | None]:
    """``sf_on_grid`` where the pmf grid reaches, and ``None`` past its last node: the recursion computes no probability there, and the
    interpolation would hold its last value flat as if it were data (U16-R2, b08 M1)."""
    nodes, sf = agg.exceedance_from_pmf(h, step)
    inside = np.interp(x, nodes, sf)
    return [float(v) if xi <= nodes[-1] else None for v, xi in zip(inside, x)]


def exceedance_axis(quantile: float, n: int = P.EXCEEDANCE_POINTS) -> np.ndarray:
    """A geometric axis of ``n`` points from a ten-thousandth of the 99.9 percent quantile to ten times it, rounded to 3 digits."""
    lo, hi = math.log10(quantile) - 3.0, math.log10(quantile) + 1.0
    return np.unique(np.array([float(f"{10 ** t:.3g}") for t in np.linspace(lo, hi, n)]))
