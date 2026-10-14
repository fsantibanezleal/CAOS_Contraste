"""The illustrative portfolio of each loan type (CT-1105).

A portfolio is constructed, never a bank's: three groups of identical names (large, mid-size and small), a total exposure of
100 million USD, one expected LGD, and the PD of each group a multiple of the loan type's fitted PD scaled so that the
exposure-weighted PD is exactly the fitted PD. Every name loads on the systematic factor with the square root of the fitted
correlation, so the one-factor rungs carry the correlation the fit estimated. The groups are plain data in the document's
``portfolio.groups`` block; the engine builds the portfolio from them (``portfolio.portfolio_from_groups``).
"""
from __future__ import annotations

import math
from typing import Any

from . import params as P

NOTICE = {
    "en": "Illustrative portfolio: constructed for this case from the fitted PD and correlation of the loan type, never a "
          "bank's. Names, exposures and the split between groups are assumptions of the case.",
    "es": "Cartera ilustrativa: construida para este caso con la PD y la correlación ajustadas del tipo de préstamo, nunca la "
          "de un banco. Los nombres, las exposiciones y el reparto entre grupos son supuestos del caso.",
}


class PortfolioError(ValueError):
    """The portfolio shape of a loan type is not a valid illustrative portfolio."""


def check_shape(loan_type: str) -> None:
    """Total exposure, a whole number of loss units per group and the sector split must hold for the shape."""
    shape = P.PORTFOLIO_SHAPE[loan_type]
    if len(shape) != len(P.GROUP_STYLE):
        raise PortfolioError(f"{loan_type}: {len(shape)} groups for {len(P.GROUP_STYLE)} styles")
    total = sum(n * ead for n, ead in shape)
    if abs(total - P.TOTAL_EAD) > 1e-6:
        raise PortfolioError(f"{loan_type}: the exposures add to {total}, not {P.TOTAL_EAD}")
    for n, ead in shape:
        units = ead * P.LGD / P.LOSS_UNIT
        if n < 1 or abs(units - round(units)) > 1e-9 or round(units) < 1:
            raise PortfolioError(f"{loan_type}: {ead} x LGD is not a whole number of {P.LOSS_UNIT} loss units")


def groups(loan_type: str, pd_hat: float, rho_hat: float, thin: int = 1) -> list[dict[str, Any]]:
    """The ``portfolio.groups`` block: PDs scaled so that the exposure-weighted PD is ``pd_hat``; loadings sqrt(rho_hat).

    ``thin`` divides the names of every group and multiplies their exposure (the tests: the same total exposure and shares with a tenth of
    the names); a full bake uses 1."""
    check_shape(loan_type)
    if not (0.0 < pd_hat < 1.0 and 0.0 < rho_hat < 1.0):
        raise PortfolioError("the fitted PD and correlation are open (0, 1)")
    shape = tuple((max(2, n // thin), ead * (n / max(2, n // thin))) for n, ead in P.PORTFOLIO_SHAPE[loan_type])
    weight = [n * ead / P.TOTAL_EAD for n, ead in shape]
    scale = sum(w * s["pd_multiple"] for w, s in zip(weight, P.GROUP_STYLE, strict=True))
    out = []
    for (n, ead), style in zip(shape, P.GROUP_STYLE, strict=True):
        pd_g = pd_hat * style["pd_multiple"] / scale
        if not 0.0 < pd_g < 1.0:
            raise PortfolioError(f"{loan_type}/{style['id']}: the group PD {pd_g} is outside (0, 1)")
        out.append({"id": style["id"], "label": dict(style["label"]), "n_names": n, "ead_each": ead, "pd": pd_g,
                    "lgd": P.LGD, "loading": math.sqrt(rho_hat), "sector": style["sector"]})
    return out


def chunk_scenarios(n_names: int, cap_bytes: int = P.CHUNK_BYTES) -> int:
    """Scenarios per Monte Carlo chunk so that one chunk of float64 draws holds at most ``cap_bytes`` (engine contract:
    ``chunk_scenarios x N x 8`` bytes)."""
    return max(1000, min(100_000, cap_bytes // (8 * n_names)))
