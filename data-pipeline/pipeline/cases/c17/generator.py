"""The C17 generator: annual operational loss histories of a synthetic bank, calibrated to the BCBS 2008 LDCE medians.

The severity of a variant is a GPD above the generator floor with the variant's tail index; its scale is the one free
parameter, fitted by least squares on the log excess quantiles to the four LDCE median percentiles above EUR 20,000 (the fit
of dossier 05 F.6, with the tail index held at the variant's value). The frequency is Poisson, set so that the expected count of
losses of EUR 20,000 or more is the LDCE median 0.82 per EUR billion of assets times the bank's assets. The true annual loss
distribution of a variant is therefore the compound Poisson of this severity (``truth.py``).

The generator draws a loss as the inverse cdf of a uniform, through ``riskvalidation`` (``severity_ppf``): the product holds no
distribution of its own. A history is a pure function of its seed (CT-1707): three streams spawned from the seed give the
counts, the amounts and the labels (date, event type, business line), so the amounts never depend on the labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.oprisk import distributions as dist
from scipy import optimize

from . import params as P


@dataclass(frozen=True)
class Variant:
    """One variant: the true parameters of the generator for a tail index."""
    tail_index: float
    scale_eur: float  # the GPD scale above the floor (location = floor)
    scale_above_ldce_eur: float  # the fitted scale of the excesses over EUR 20,000
    lambda_per_year: float  # losses per year at or above the floor
    fitted_quantiles_eur: tuple[float, ...]
    max_abs_log_error: float

    @property
    def variant_id(self) -> str:
        return f"xi-{self.tail_index:g}".replace(".", "-")

    @property
    def infinite_mean(self) -> bool:
        return self.tail_index >= 1.0

    @property
    def sev_params(self) -> tuple[float, float, float]:
        return (self.tail_index, self.scale_eur, P.FLOOR_EUR)

    @property
    def lambda_above_ldce(self) -> float:
        return P.LDCE_FREQUENCY_PER_BN * P.ASSETS_EUR_BN


def _log_residuals(xi: float, beta_prime: float) -> np.ndarray:
    p = np.array([q for q, _ in P.LDCE_PERCENTILES])
    target = np.array([x for _, x in P.LDCE_PERCENTILES])
    fitted = dist.severity_ppf("gpd", (xi, beta_prime, P.LDCE_THRESHOLD_EUR), p)
    return np.log(fitted - P.LDCE_THRESHOLD_EUR) - np.log(target - P.LDCE_THRESHOLD_EUR)


def fit_scale_above_ldce(xi: float) -> float:
    """The scale of the GPD of the excesses over EUR 20,000 that minimises the squared log errors to the four LDCE medians."""
    res = optimize.minimize_scalar(lambda lb: float(np.sum(_log_residuals(xi, float(np.exp(lb))) ** 2)),
                                   bounds=(np.log(100.0), np.log(1e7)), method="bounded", options={"xatol": 1e-12})
    return float(np.exp(res.x))


def variant(tail_index: float) -> Variant:
    """The generator of a tail index: the fitted scale, the floor-based scale, the frequency and the fit error."""
    if tail_index not in P.TAIL_INDICES:
        raise ValueError(f"tail index {tail_index} is not one of the C17 variants {P.TAIL_INDICES}")
    bp = fit_scale_above_ldce(tail_index)
    beta = bp - tail_index * (P.LDCE_THRESHOLD_EUR - P.FLOOR_EUR)  # a GPD conditioned above u is a GPD with scale beta + xi (u - floor)
    if beta <= 0:
        raise ValueError(f"the LDCE fit at tail index {tail_index} leaves no positive scale above the floor")
    p = np.array([q for q, _ in P.LDCE_PERCENTILES])
    fitted = dist.severity_ppf("gpd", (tail_index, bp, P.LDCE_THRESHOLD_EUR), p)
    err = float(np.max(np.abs(_log_residuals(tail_index, bp))))
    surv = 1.0 - float(dist.severity_cdf("gpd", (tail_index, beta, P.FLOOR_EUR), np.array([P.LDCE_THRESHOLD_EUR]))[0])
    lam = P.LDCE_FREQUENCY_PER_BN * P.ASSETS_EUR_BN / surv
    return Variant(tail_index, beta, bp, lam, tuple(float(x) for x in fitted), err)


def variants() -> list[Variant]:
    return [variant(xi) for xi in P.TAIL_INDICES]


def expected_count_above(v: Variant, loss_eur: float) -> float:
    """The expected number of losses per year at or above ``loss_eur``: the frequency times the severity survival."""
    sf = 1.0 - float(dist.severity_cdf("gpd", v.sev_params, np.array([loss_eur]))[0])
    return v.lambda_per_year * sf


@dataclass(frozen=True)
class History:
    """Every loss the generator drew in ``n_years`` years, at or above its floor, and the labels of each."""
    seed: int
    n_years: int
    year_index: np.ndarray  # (N,) the accounting year of each loss, 0 .. n_years - 1
    amount_eur: np.ndarray  # (N,) the gross loss, EUR
    day_of_year: np.ndarray  # (N,) 0 .. 364
    event_type: np.ndarray  # (N,) index into params.EVENT_TYPES
    business_line: np.ndarray  # (N,) index into params.BUSINESS_LINES

    def recorded_mask(self, threshold_eur: float) -> np.ndarray:
        """The losses a bank with this collection threshold records: those at or above it (CT-1705)."""
        return self.amount_eur >= threshold_eur

    def recorded(self, threshold_eur: float) -> Recorded:
        m = self.recorded_mask(threshold_eur)
        yi = self.year_index[m]
        amt = self.amount_eur[m]
        return Recorded(self.n_years, threshold_eur, amt, yi, np.bincount(yi, minlength=self.n_years).astype(np.int64),
                        np.bincount(yi, weights=amt, minlength=self.n_years), m)

    def rows(self, threshold_eur: float) -> list[dict[str, Any]]:
        """The recorded losses as rows of the ``loss_events`` family of contract 1."""
        m = self.recorded_mask(threshold_eur)
        idx = np.flatnonzero(m)
        year_start = np.datetime64(str(P.FIRST_YEAR), "Y") + self.year_index[idx].astype("timedelta64[Y]")
        dates = year_start.astype("datetime64[D]") + self.day_of_year[idx].astype("timedelta64[D]")
        ds = np.datetime_as_string(dates, unit="D")
        return [{"event_id": f"{self.seed}-{int(i)}", "date": str(d), "business_line": P.BUSINESS_LINES[int(self.business_line[i])],
                 "event_type": P.EVENT_TYPES[int(self.event_type[i])], "gross_loss": float(self.amount_eur[i]), "recovery": 0.0}
                for i, d in zip(idx, ds)]


@dataclass(frozen=True)
class Recorded:
    """The history as the bank records it above its collection threshold; every fit, rate and annual total reads this."""
    n_years: int
    threshold_eur: float
    amounts: np.ndarray
    year_index: np.ndarray
    counts: np.ndarray  # (n_years,) recorded losses per year
    annual: np.ndarray  # (n_years,) recorded loss per year, EUR (zero recoveries)
    mask: np.ndarray


def draw_history(v: Variant, seed: int, n_years: int) -> History:
    """The history of ``n_years`` years for ``seed``: Poisson counts, GPD amounts by the engine's inverse cdf, then the labels."""
    if int(seed) != seed or seed < 0 or n_years < 1:
        raise ValueError("a history needs a non-negative integer seed and at least one year")
    ss_count, ss_amount, ss_label = np.random.SeedSequence(int(seed)).spawn(3)
    counts = np.random.Generator(np.random.PCG64(ss_count)).poisson(v.lambda_per_year, size=n_years)
    n = int(counts.sum())
    u = np.random.Generator(np.random.PCG64(ss_amount)).random(n)
    amounts = np.asarray(dist.severity_ppf("gpd", v.sev_params, u), dtype=float)
    lab = np.random.Generator(np.random.PCG64(ss_label))
    return History(int(seed), n_years, np.repeat(np.arange(n_years), counts), amounts, lab.integers(0, 365, size=n),
                   lab.choice(len(P.EVENT_TYPES), size=n, p=P.EVENT_WEIGHTS / P.EVENT_WEIGHTS.sum()),
                   lab.choice(len(P.BUSINESS_LINES), size=n, p=P.LINE_WEIGHTS / P.LINE_WEIGHTS.sum()))


def cell_seeds(case_seed: int, variant_index: int, cell_index: int, n_replications: int) -> tuple[int, int]:
    """``(first seed, number)`` of a cell: the seed ranges of the 16 cells never overlap and depend on the case seed."""
    if n_replications > P.SEED_STRIDE:
        raise ValueError(f"at most {P.SEED_STRIDE} replications fit one seed stride")
    return int(case_seed) * P.SEED_SCALE + P.SEED_STRIDE + P.SEED_STRIDE * (variant_index * len(P.CELLS) + cell_index), n_replications


def seed_base(case_seed: int) -> int:
    return int(case_seed) * P.SEED_SCALE + P.SEED_STRIDE
