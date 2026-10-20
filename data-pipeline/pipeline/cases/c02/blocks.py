"""The exploratory term-structure and Impact blocks of C02 (decisions Q9 and Q10), through ``riskvalidation.provisions``.

The five files are read as the cumulative PD at 1 to 5 years (``from_cumulative``). The back-test row is the engine's
``lifetime_pd_backtest`` of the champion's mean PD on each holdout against the holdout event rate. The Impact block is the 12-month and
lifetime ECL of one unit of exposure under the cumulative PDs of the term-structure block (the file event rates) (``ecl_scenario``, undiscounted, the loss given default an assumption).
Both are labelled exploratory: the files may not draw one population and their firm overlap is unknown.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import conventions as cv

MONTHS = np.array([12, 24, 36, 48, 60])
BACKTEST_SEGMENT = "term-structure:P1-scorecard,holdout"
ECL_UNIT = "ECL per unit of exposure (EAD 1, LGD 45 percent assumed, undiscounted)"


class TermStructureError(ValueError):
    """The five rates cannot be read as a cumulative PD; the contract has no null for the block, so no document is written."""


def _strictly_increasing(c: np.ndarray) -> bool:
    return bool(np.all(np.isfinite(c)) and np.all(c > 0) and np.all(c < 1) and np.all(np.diff(c) > 0))


def term_structure_block(rows: dict[int, int], events: dict[int, int]) -> dict[str, Any]:
    from riskvalidation.provisions import term_structure as ts

    cum = np.array([events[k] / rows[k] for k in range(1, 6)])
    if not _strictly_increasing(cum):
        raise TermStructureError("C02: the event rates of the five files " + ", ".join(f"{k}y {c:.4f}" for k, c in zip(range(1, 6), cum))
                                 + " are not strictly increasing, so the engine's from_cumulative cannot read them as a cumulative PD")
    t = ts.from_cumulative(cum, MONTHS)
    points = [{"years": k, "cumulative_pd": float(cum[k - 1]), "hazard": float(t.hazard[k - 1])} for k in range(1, 6)]
    return {"label": "exploratory", "reason": cv.TERM_STRUCTURE_REASON, "points": points,
            "cumulative_nondecreasing": bool(np.all(np.diff(cum) >= 0)), "source": cv.TERM_SOURCE}


def backtest_row(pred: np.ndarray, n: np.ndarray, d: np.ndarray) -> dict[str, Any]:
    """The engine's lifetime back-test: the champion's mean PD per horizon against the holdout event rate."""
    from riskvalidation.validation import ifrs9

    n, d = np.asarray(n, dtype=float), np.asarray(d, dtype=float)
    res = ifrs9.lifetime_pd_backtest(MONTHS, np.asarray(pred, dtype=float), d / n, n, d, model_id=None, segment=BACKTEST_SEGMENT)
    return res.to_dict()


def impact_block(horizon_pds: np.ndarray, pd_basis: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """(``impact_detail``, the envelope ``impact``): the ECL of one unit of exposure, or a null with its reason."""
    pds = np.asarray(horizon_pds, dtype=float)
    ecl12 = life = None
    reason = None
    if _strictly_increasing(pds):
        from riskvalidation.provisions import ecl
        from riskvalidation.provisions import term_structure as ts

        t = ts.from_cumulative(pds, MONTHS)
        q = t.marginal[None, :]
        eir = np.array([0.0])
        ecl12 = float(ecl.ecl_scenario(q, cv.LGD, 1.0, eir, MONTHS, 12)[0])
        life = float(ecl.ecl_scenario(q, cv.LGD, 1.0, eir, MONTHS, 60)[0])
    else:
        reason = ("the horizon PDs " + ", ".join(f"{x:.4f}" for x in pds)
                  + " are not strictly increasing, so they cannot form a term structure and no ECL is computed")
    detail = {"label": "exploratory", "reason": cv.IMPACT_REASON, "source": "engine-provisions-api", "pd_basis": pd_basis,
              "lgd": {"value": cv.LGD, "label": "assumption"}, "ecl_12m_effect": ecl12, "ecl_lifetime_effect": life, "unit": ECL_UNIT,
              "reason_if_null": reason}
    impact = {
        "ecl_12m_effect": {"value": ecl12, "unit": ECL_UNIT, "label": cv.t("12-month ECL effect of the horizon PDs (exploratory)",
                                                                           "Efecto en la PCE a 12 meses de las PD por horizonte (exploratorio)")},
        "ecl_lifetime_effect": {"value": life, "unit": ECL_UNIT, "label": cv.t("Lifetime ECL effect of the horizon PDs (exploratory)",
                                                                              "Efecto en la PCE de vida de las PD por horizonte (exploratorio)")}}
    return detail, impact
