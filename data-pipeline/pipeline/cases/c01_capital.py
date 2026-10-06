"""C01's IRB capital (U2; docs/design/features/c01-irb-capital/design.md, CT-212 to CT-215).

The Taiwan cards are qualifying revolving retail, every one a revolver: Basel III defines a transactor by twelve
months of repayment history (BCBS d424, standardised paragraph 56 and IRB paragraph 25) and the data hold six. The
German loans are other retail. Each account's capital (8% of the RWA) at unit LGD is riskvalidation's
``capital_requirement``; retail capital is linear in the LGD, so the web multiplies by the rail's.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np
from riskvalidation.regulatory import capital_requirement
from riskvalidation.regulatory.irb import REGIMES as ENGINE_REGIMES

#: the regimes the capital view compares, in the rail's order
REGIMES: tuple[str, ...] = ("basel3", "crr3", "basel2")
#: the exposure class of each source's accounts
CLASS = {"uci-taiwan": "qrre", "uci-german": "other_retail"}
#: the six months of repayment status the Taiwan data hold (April to September 2005)
PAY_MONTHS = ("PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6")
#: Basel III's LGD input floors for the two classes (BCBS d424, IRB paragraph 121 and its table; CRE32.58 to 59)
LGD_FLOOR_BASEL3 = {"qrre": 0.50, "other_retail": 0.30}
#: a PD of exactly 0 or 1 lies outside the engine's domain; any floor lifts the first, and the second's K is 0
_EPS = 1e-12


@lru_cache(maxsize=None)
def unit_capital(asset_class: str, pd: float, regime: str, revolver: bool) -> float:
    """Capital per unit of EAD at unit LGD: K times the regime's scaling factor (the risk weight over 12.5)."""
    p = min(max(pd, _EPS), 1.0 - _EPS)
    return capital_requirement(asset_class, p, 1.0, revolver=revolver, regime=regime).risk_weight / 12.5


def account_capital(asset_class: str, pds: np.ndarray, ead: np.ndarray, revolver: np.ndarray) -> dict[str, np.ndarray]:
    """Per regime, each account's capital at unit LGD: unit capital times its EAD."""
    rev = np.asarray(revolver, dtype=bool)
    out = {}
    for regime in REGIMES:
        k = np.array([unit_capital(asset_class, float(p), regime, bool(r)) for p, r in zip(pds, rev, strict=True)])
        out[regime] = k * np.asarray(ead, dtype=float)
    return out


def six_month_full_payers(X) -> np.ndarray:
    """The accounts that repaid in full (-1) or did not use the card (-2) in all six recorded months."""
    return np.all(np.isin(X[list(PAY_MONTHS)].to_numpy(dtype=float), (-2.0, -1.0)), axis=1)


def regime_facts(asset_class: str) -> dict[str, Any]:
    """What the artifact states for each regime: the PD floors, the scaling factor and the references."""
    out: dict[str, Any] = {}
    for regime in REGIMES:
        reg = ENGINE_REGIMES[regime]
        ref = capital_requirement(asset_class, 0.01, 1.0, revolver=asset_class == "qrre", regime=regime).references
        out[regime] = {"name": reg.name, "pd_floor_revolver": reg.pd_floor_qrre if asset_class == "qrre" else None,
                       "pd_floor": reg.pd_floor, "scaling": reg.scaling, "references": dict(ref)}
    return out


def parity_points() -> list[dict[str, Any]]:
    """CT-215: the retail risk weight at a grid of PDs and LGDs, revolver or not, under the three regimes."""
    pts = []
    for regime in REGIMES:
        for cls, revolvers in (("qrre", (True, False)), ("other_retail", (False,))):
            for revolver in revolvers:
                for pd in (0.0002, 0.0007, 0.003, 0.02, 0.1, 0.35):
                    for lgd in (0.3, 0.5, 0.85):
                        pts.append({"regime": regime, "asset_class": cls, "revolver": revolver, "pd": pd, "lgd": lgd,
                                    "risk_weight": capital_requirement(cls, pd, lgd, revolver=revolver,
                                                                       regime=regime).risk_weight})
    return pts
