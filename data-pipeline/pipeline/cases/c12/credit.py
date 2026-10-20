"""CVA, DVA and wrong-way risk through ``riskvalidation.ccr.cva`` (ladder rung 5), on the counterparty curve of decision B10.

The base counterparty curve is the HQM corporate spot curve minus the Treasury zero curve of the same month end: an AAA-to-A
market spread, a proxy and a floor for lower ratings. A negative spread is set to zero and counted. Survival is the credit
triangle ``S(t) = exp(-s(t) t / LGD)`` of the engine; the bank's own curve is the flat named spread. The synthetic flat spread of
the named parameters (0.0125, Hull and White's value) is carried as a sensitivity row, never as the base.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.ccr import cva as cv

from . import book, data


@dataclass(frozen=True)
class Curve:
    """The spreads at the report grid (and at 0), the number floored at zero, and the label of the source."""

    spreads: np.ndarray          # (K+1,) at 0 and the report grid
    floored: int
    source: str                  # "hqm-minus-treasury" or "synthetic-flat"


def hqm_curve(hqm: tuple[np.ndarray, np.ndarray], tenors: np.ndarray, zeros: np.ndarray, report: np.ndarray) -> Curve:
    times = np.concatenate([[0.0], report])
    raw = data.hqm_spread(hqm, tenors, zeros, times)
    floored = int(np.sum(raw[1:] < 0.0))
    return Curve(np.maximum(raw, 0.0), floored, "hqm-minus-treasury")


def flat_curve(spread: float, report: np.ndarray) -> Curve:
    return Curve(np.full(report.size + 1, spread), 0, "synthetic-flat")


def survival(curve: Curve, report: np.ndarray, lgd: float) -> np.ndarray:
    """(K+1,) the survival probability at 0 and the report grid."""
    return cv.survival_from_spread(curve.spreads, np.concatenate([[0.0], report]), lgd)


def bank_survival(spread: float, report: np.ndarray, lgd: float) -> np.ndarray:
    return cv.survival_from_spread(np.full(report.size + 1, spread), np.concatenate([[0.0], report]), lgd)


def cva_block(ee_d: np.ndarray, ene_d: np.ndarray, x_paths_d: np.ndarray, y_paths_d: np.ndarray, report: np.ndarray, curve: Curve,
              lgd: float, bank_spread: float, bank_lgd: float) -> dict[str, Any]:
    """The ``cva_dva`` block: buckets, CVA, DVA, BCVA, each total with its Monte Carlo error from the paths (the engine's
    ``wwr_cva`` at b = 0, which is the independent CVA bit for bit)."""
    s_cp, s_bank = survival(curve, report, lgd), bank_survival(bank_spread, report, bank_lgd)
    pd_cp, pd_bank = cv.default_probabilities(s_cp), cv.default_probabilities(s_bank)
    cva, cva_terms = cv.cva(ee_d, pd_cp, lgd)
    dva, dva_terms = cv.dva(ene_d, pd_bank, bank_lgd)
    dt = np.diff(np.concatenate([[0.0], report]))
    w = np.zeros_like(x_paths_d)
    cva_check, cva_se = cv.wwr_cva(w, x_paths_d, s_cp[1:], dt, lgd, 0.0)
    dva_check, dva_se = cv.wwr_cva(w, y_paths_d, s_bank[1:], dt, bank_lgd, 0.0)
    if cva_check != cva or dva_check != dva:
        raise ValueError("the b = 0 value of the engine differs from the independent CVA or DVA on the same paths")
    t_start = np.concatenate([[0.0], report[:-1]])
    buckets = [{"t_start": float(t_start[k]), "t_end": float(report[k]), "spread": float(curve.spreads[k + 1]),
                "survival": float(s_cp[k + 1]), "pd_counterparty": float(pd_cp[k]), "pd_bank": float(pd_bank[k]),
                "epe_discounted": float(ee_d[k]), "ene_discounted": float(ene_d[k]), "cva_term": float(cva_terms[k]),
                "dva_term": float(dva_terms[k])} for k in range(report.size)]
    return {"credit_curve_source": curve.source,
            "credit_curve_label": "proxy: an AAA to A market spread, a floor for lower ratings (R10)",
            "survival_formula": "S(t) = exp(-s t / LGD)",
            "negative_spread_rule": "a negative HQM-minus-Treasury spread is set to zero and counted in spreads_floored_at_zero",
            "spreads_floored_at_zero": curve.floored, "lgd": lgd, "bank_lgd": bank_lgd, "buckets": buckets,
            "cva": {"amount": float(cva), "currency": book.CURRENCY, "mc_se": cva_se},
            "dva": {"amount": float(dva), "currency": book.CURRENCY, "mc_se": dva_se},
            "bcva": {"amount": float(cva - dva), "currency": book.CURRENCY}}


def wrong_way_block(w_musd: np.ndarray, x_paths_d: np.ndarray, report: np.ndarray, curve: Curve, lgd: float,
                    independent: dict[str, Any], b_grid: list[float]) -> dict[str, Any]:
    """The Hull and White (2012) sweep over ``b_grid``: the portfolio value in USD million, the discounted exposure paths, the
    survival target of the curve. ``a_calibration_max_error`` is the largest gap, over the grid points, between the average
    survival of the calibrated hazards and the target. b = 0 is the independent CVA, copied from ``independent``."""
    s_cp = survival(curve, report, lgd)
    dt = np.diff(np.concatenate([[0.0], report]))
    sweep = []
    for b in b_grid:
        value, se = cv.wwr_cva(w_musd, x_paths_d, s_cp[1:], dt, lgd, b)
        _, h = cv.wwr_calibrate_a(w_musd, s_cp[1:], dt, b)
        err = float(np.max(np.abs(np.exp(-np.cumsum(h * dt[None, :], axis=1)).mean(axis=0) - s_cp[1:])))
        sweep.append({"b": float(b), "cva": {"amount": float(value), "currency": book.CURRENCY, "mc_se": se},
                      "independent": bool(b == 0.0), "a_calibration_max_error": err})
    w_max = float(np.max(w_musd))
    return {"model": "Hull and White (2012) hazard rate on the portfolio value, h(t) = exp(a(t) + b w(t))",
            "b_unit": "per USD million of portfolio value", "b_grid": [float(b) for b in b_grid], "w_max_usd_million": w_max,
            "largest_b_w": max(abs(b) for b in b_grid) * w_max, "sweep": sweep,
            "independent_cva": {"amount": independent["cva"]["amount"], "currency": book.CURRENCY},
            "ore_limit": {"en": "ORE's wrong-way example is a different model (a correlated credit LGM), so this variant has no ORE reconciliation.",
                          "es": "El ejemplo de riesgo de direccion equivocada de ORE es otro modelo (un LGM de credito correlacionado), por lo que esta variante no tiene conciliacion con ORE."}}
