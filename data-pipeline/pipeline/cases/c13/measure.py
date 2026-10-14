"""The C13 measurement: run the replications of one variant through ``riskvalidation.market`` and keep what the documents report.

Every PLA statistic, zone and exception count is the return value of an engine function (``frtb.pla_spearman``, ``frtb.pla_ks``,
``frtb.pla_zone``, ``frtb.desk_exceptions``); this module only calls them and counts the zones they return (CT-1305). The
single-statistic zones of the contract (green above 0.80 / below 0.09, red below 0.70 / above 0.12) are ``pla_zone`` with the
other statistic held at its best value, so no threshold is written here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.market import frtb
from scipy import stats

from . import generator, params

ZONES = ("green", "amber", "red")
BEST_KS = 0.0            # a KS of 0 never decides a zone, so the zone of (spearman, 0) is the Spearman-only zone
BEST_SPEARMAN = 1.0      # and the zone of (1, ks) is the KS-only zone


@dataclass
class Measurement:
    """What the replications of one variant gave, in replication order."""

    did: str
    case_seed: int
    n: int
    spearman: np.ndarray
    ks: np.ndarray
    zone: list[str]
    zone_spearman: list[str]
    zone_ks: list[str]
    exceptions: dict[float, np.ndarray]
    hpl_all: np.ndarray
    rtpl_all: np.ndarray

    def zone_counts(self, kind: str) -> dict[str, int]:
        zones = {"overall": self.zone, "spearman": self.zone_spearman, "ks": self.zone_ks}[kind]
        return {z: sum(1 for x in zones if x == z) for z in ZONES}

    @property
    def n_amber_or_red(self) -> int:
        return sum(1 for z in self.zone if z != "green")

    @property
    def n_red(self) -> int:
        return sum(1 for z in self.zone if z == "red")

    def n_over_limit(self, alpha: float) -> int:
        return int((self.exceptions[alpha] > frtb.desk_exception_limit(alpha)).sum())

    @property
    def n_desk_flagged(self) -> int:
        """Replications in which the desk is over its limit at either tail level."""
        return int(np.any([self.exceptions[a] > frtb.desk_exception_limit(a) for a in params.ALPHAS], axis=0).sum())

    @property
    def n_spearman_flagged(self) -> int:
        return sum(1 for z in self.zone_spearman if z != "green")

    @property
    def n_ks_flagged(self) -> int:
        return sum(1 for z in self.zone_ks if z != "green")

    @property
    def n_either_flagged(self) -> int:
        return sum(1 for a, b in zip(self.zone_spearman, self.zone_ks, strict=True) if a != "green" or b != "green")

    def intended_flagged(self, intended: str) -> int | None:
        return {"none": None, "spearman": self.n_spearman_flagged, "ks": self.n_ks_flagged, "either": self.n_either_flagged}[intended]


def measure(did: str, case_seed: int, n: int) -> Measurement:
    """Replications ``0..n-1`` of ``did`` for the bake with case seed ``case_seed``, through the engine."""
    sp, ks = np.empty(n), np.empty(n)
    zone, z_sp, z_ks = [], [], []
    exc = {a: np.empty(n, dtype=np.int64) for a in params.ALPHAS}
    hpl, rtpl = np.empty((n, params.WINDOW_DAYS)), np.empty((n, params.WINDOW_DAYS))
    for i in range(n):
        rep = generator.replicate(did, i, case_seed)
        sp[i], ks[i] = frtb.pla_spearman(rep.hpl, rep.rtpl), frtb.pla_ks(rep.hpl, rep.rtpl)
        zone.append(frtb.pla_zone(float(sp[i]), float(ks[i])))
        z_sp.append(frtb.pla_zone(float(sp[i]), BEST_KS))
        z_ks.append(frtb.pla_zone(BEST_SPEARMAN, float(ks[i])))
        for a in params.ALPHAS:
            exc[a][i] = frtb.desk_exceptions(rep.loss, rep.var[a])
        hpl[i], rtpl[i] = rep.hpl, rep.rtpl
    return Measurement(did, case_seed, n, sp, ks, zone, z_sp, z_ks, exc, hpl.ravel(), rtpl.ravel())


def distribution(x: np.ndarray) -> dict[str, float]:
    """The summary the c13 Dist block holds."""
    x = np.asarray(x, dtype=float)
    q = np.quantile(x, [0.05, 0.5, 0.95])
    return {"mean": float(x.mean()), "sd": float(x.std(ddof=1)) if x.size > 1 else 0.0, "q05": float(q[0]), "q50": float(q[1]),
            "q95": float(q[2]), "min": float(x.min()), "max": float(x.max())}


def pnl_summary(series: str, x: np.ndarray) -> dict[str, Any]:
    return {"series": series, "mean": float(x.mean()), "sd": float(x.std(ddof=1)), "skewness": float(stats.skew(x)),
            "excess_kurtosis": float(stats.kurtosis(x)), "min": float(x.min()), "max": float(x.max())}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval of a share (well behaved at 0 and 1, where the normal interval collapses)."""
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))
