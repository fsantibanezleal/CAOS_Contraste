"""The reverse stress: the most plausible scenario that takes CET1 to the Chilean legal minimum stack (decision Q11).

The failure point is CET1/RWA at the end of the three-year horizon equal to the Chilean legal minimum stack (4.5 percent + 2.5 +
countercyclical + systemic + the CET1 share of Pillar 2, the engine's ``chilean_cet1_stack``). The factors are the two standardised
satellite regressors (real GDP growth and the unemployment rate) with their covariance from 1985 to 2019; a scenario is a persistent
deviation of both from the Federal Reserve baseline path over the twelve quarters, the loss is the three-year loss of the satellites
(credit) and the expected losses of the other risks, and ``riskvalidation.stress.reverse`` finds the minimum Mahalanobis distance
scenario with ``scipy.optimize`` from several starts (the loss is nonlinear through the probit link). The formal statement is
Contraste's, not regulatory text (01 l.891-894; 05 H.5).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
from riskvalidation.stress import capital as rv_cap
from riskvalidation.stress import reverse as rv_rev
from riskvalidation.validation import stress as rv_vs

from . import params as P

T = P.text
FACTOR_LABELS = {"real_gdp_growth": T("Real GDP growth", "Crecimiento del PIB real"), "unemployment_rate": T("Unemployment rate", "Tasa de desempleo")}


def factor_space(history: Any, ids: tuple[str, ...] = P.REGRESSORS) -> dict[str, Any]:
    """The covariance of the factors over 1985 Q1 to 2019 Q4 of the Federal Reserve history (the fit window of the satellites)."""
    h = history.set_index("quarter_end")
    window = h.loc[P.FIT_START: P.FIT_END, list(ids)].to_numpy(dtype=float)
    cov = np.cov(window, rowvar=False, ddof=1)
    sd = np.sqrt(np.diag(cov))
    return {"window": {"start": P.FIT_START, "end": P.FIT_END},
            "factors": [{"id": i, "label": FACTOR_LABELS[i], "unit": "percentage points", "sd": float(s)} for i, s in zip(ids, sd, strict=True)],
            "covariance": [[float(v) for v in row] for row in cov], "label": "us-calibrated-adaptation"}


def failure_stack(anchors: Any, p2_cet1: dict[str, Any]) -> dict[str, Any]:
    st = anchors.stack
    total = rv_cap.chilean_cet1_stack(st["c_ccyb"], st["c_dsib"], p2_cet1["value"])
    return {"cet1_min": st["cet1_min"], "c_ccob": st["c_ccob"], "c_ccyb": st["c_ccyb"], "c_dsib": st["c_dsib"], "p2_cet1": p2_cet1, "total": total,
            "basis": "chilean-legal-minimum-stack"}


def starts(sd: list[float]) -> list[np.ndarray]:
    """Four deterministic starts in the adverse quadrant (growth falls, unemployment rises), in multiples of the factor sd."""
    grid = ((-1.0, 1.0), (-2.0, 0.5), (-0.5, 2.0), (-2.5, 2.5))
    return [np.array([a * sd[0], b * sd[1]]) for a, b in grid]


def solve(loss_fn: Callable[[np.ndarray], float], space: dict[str, Any], threshold: float) -> tuple[Any, tuple[Any, ...], Any, float]:
    cov = np.array(space["covariance"])
    sd = [f["sd"] for f in space["factors"]]
    best, each = rv_rev.reverse_stress(loss_fn, cov, threshold, starts(sd))
    p = rv_rev.plausibility(best.distance, len(sd))
    test = rv_vs.reverse_solution_check(best.loss_at_x, threshold, best.distance, [s.distance for s in each if s.converged], model_id="c18-capital-engine")
    return best, each, test, p


def blocks(best: Any, each: tuple[Any, ...], p: float, threshold: float, space: dict[str, Any], loss_description: dict[str, str]) -> dict[str, Any]:
    gap = abs(best.loss_at_x - threshold) / threshold
    return {
        "loss_model": {"kind": "nonlinear", "gradient_clp_m_per_unit": None, "description": loss_description},
        "solution": {"method": best.method, "z_star": [float(v) for v in best.z_star], "x_star": [float(v) for v in best.x_star],
                     "mahalanobis_distance": best.distance, "plausibility": {"chi_square_df": len(space["factors"]), "tail_probability": p},
                     "loss_at_z_star_clp_m": best.loss_at_x, "loss_threshold_clp_m": threshold, "relative_gap": gap, "tolerance": 1e-6},
        "starts": [{"start_id": f"start-{k + 1}", "converged": bool(s.converged), "distance": s.distance, "loss_clp_m": s.loss_at_x} for k, s in enumerate(each)]}
