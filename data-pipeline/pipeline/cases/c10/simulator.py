"""The Vasicek simulator with a known correlation, and the size and power of the two correlation estimates (CT-1108).

A replication draws one standard normal factor per year, turns it into the default fraction of a large homogeneous portfolio
with the engine's ``conditional_pd`` (the rate is exactly the conditional PD of dossier 04 C.4), and fits the series with the
two estimators of the engine: maximum likelihood (interval by the profile likelihood) and the method of moments (interval by
the parametric bootstrap). H0: rho = null_rho is rejected when the null lies outside the 95% interval. The rate of rejection
is returned by ``validation.portfolio.correlation_size_power``: the size at the null correlation, the power elsewhere.

Every replication has its own seeded stream (``SeedSequence([seed, i_rho, i_length, replication])``), so a cell is
reproduced exactly whatever the number of processes that computed it, and two replications never share a stream.
"""
from __future__ import annotations

import math
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.engines import vasicek
from riskvalidation.portfolio import asrf_fit
from riskvalidation.validation import portfolio as val

from . import params as P

ESTIMATORS = ("maximum-likelihood", "moments")


def replication_entropy(seed: int, i_rho: int, i_length: int, replication: int) -> tuple[int, int, int, int]:
    """The entropy of one replication's stream: distinct for every (seed, rho, length, replication)."""
    return (int(seed), int(i_rho), int(i_length), int(replication))


def draw_rates(known_pd: float, rho: float, years: int, entropy: tuple[int, ...]) -> np.ndarray:
    """The yearly default fractions of the LHP with one systematic factor and the known (pd, rho)."""
    rng = np.random.default_rng(np.random.SeedSequence(list(entropy)))
    z = rng.standard_normal(years)
    return np.array([vasicek.conditional_pd(known_pd, rho, float(zt)) for zt in z])


@dataclass(frozen=True)
class Replication:
    """One replication: the two estimates and their 95% intervals, or None when an estimator could not be fitted."""

    ok: bool
    rho_ml: float = float("nan")
    rho_mo: float = float("nan")
    ci_ml: tuple[float, float] = (float("nan"), float("nan"))
    ci_mo: tuple[float, float] = (float("nan"), float("nan"))


def replicate(known_pd: float, known_rho: float, years: int, entropy: tuple[int, ...], n_boot: int) -> Replication:
    rates = draw_rates(known_pd, known_rho, years, entropy)
    try:
        ml = asrf_fit.fit_ml(rates)
        ci_ml = asrf_fit.profile_interval(rates, 0.95)["rho"]
        mo = asrf_fit.fit_moments(rates)
        ci_mo = asrf_fit.bootstrap_interval(rates, "moments", n_boot, int(entropy[-1]) + 1, 0.95)["rho"]
    except ValueError:
        return Replication(False)   # no spread in the series, or the moments find no excess dispersion: not identified
    return Replication(True, ml.rho, mo.rho, ci_ml, ci_mo)


def _chunk(args: tuple) -> list[Replication]:
    known_pd, known_rho, years, seed, i_rho, i_len, start, stop, n_boot = args
    return [replicate(known_pd, known_rho, years, replication_entropy(seed, i_rho, i_len, r), n_boot)
            for r in range(start, stop)]


def run_cell(known_rho: float, years: int, i_rho: int, i_len: int, n_replications: int, seed: int = P.SIM_SEED,
             n_boot: int = P.SIM_BOOTSTRAP, known_pd: float = P.KNOWN_PD, workers: int = 1) -> list[Replication]:
    """All replications of one cell, in replication order."""
    if workers <= 1 or n_replications < 8:
        return _chunk((known_pd, known_rho, years, seed, i_rho, i_len, 0, n_replications, n_boot))
    step = math.ceil(n_replications / workers)
    spans = [(a, min(a + step, n_replications)) for a in range(0, n_replications, step)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        parts = ex.map(_chunk, [(known_pd, known_rho, years, seed, i_rho, i_len, a, b, n_boot) for a, b in spans])
    return [r for part in parts for r in part]


def cell_document(known_rho: float, years: int, null_rho: float, alpha: float, reps: list[Replication]) -> tuple[dict[str, Any],
                                                                                                                   list[dict[str, Any]]]:
    """The grid cell and the engine's ``correlation_size_power`` rows (one per estimator) for the valid replications."""
    good = [r for r in reps if r.ok]
    cell: dict[str, Any] = {"known_rho": known_rho, "series_length_years": years, "n_replications": len(reps),
                            "n_valid": len(good), "n_failed": len(reps) - len(good),
                            "role": "size" if math.isclose(known_rho, null_rho, abs_tol=1e-12) else "power", "estimators": []}
    rows: list[dict[str, Any]] = []
    for name in ESTIMATORS:
        est = np.array([r.rho_ml if name == ESTIMATORS[0] else r.rho_mo for r in good])
        ci = np.array([r.ci_ml if name == ESTIMATORS[0] else r.ci_mo for r in good]).reshape(-1, 2)
        rejected = (null_rho < ci[:, 0]) | (null_rho > ci[:, 1])
        res = val.correlation_size_power(rejected, known_rho, null_rho, alpha, estimator=name, model_id="m-lhp",
                                         segment=f"rho={known_rho:g}/{name}")
        x = res.extras
        cell["estimators"].append({
            "estimator": name, "mean_estimate": float(est.mean()), "bias": float(est.mean() - known_rho),
            "rmse": float(np.sqrt(np.mean((est - known_rho) ** 2))),
            "coverage": float(np.mean((ci[:, 0] <= known_rho) & (known_rho <= ci[:, 1]))),
            "rejection_rate": float(x["rate"]), "rejection_se": float(x["se"]), "rejection_ci_low": float(x["ci_low"]),
            "rejection_ci_high": float(x["ci_high"])})
        rows.append(res.to_dict())
    return cell, rows


def default_workers() -> int:
    """Processes for a full bake: a bounded share of the machine, never all of it (other work runs beside)."""
    return max(1, min(8, (os.cpu_count() or 2) // 4))
