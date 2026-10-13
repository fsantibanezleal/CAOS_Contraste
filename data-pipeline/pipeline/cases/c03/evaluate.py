"""The validation battery of C03 (CT-807): every row is a ``riskvalidation`` ``TestResult`` under the engine's default policy.

Only the tests the engine's policy judges are rows (they have a traffic light): a descriptive metric (AUC, Brier score, KS,
expected calibration error) has no light, the engine labels it ``not_evaluated`` with its number, and the variant contract
reserves ``not_evaluated`` for a test that did not run (null numbers and a reason). The AUC and the Brier score of each rung are
the engine's, in ``rung_comparison`` and the vintage rows. Nothing here re-implements a statistic. What this module adds is the
evaluation design: which sample each test reads, which
reference each stability test compares against, and the rows for a test that cannot run (``not_evaluated``, null numbers and
the reason, the shape the variant contract requires).

- Discrimination: the ECB comparison of the AUC against the AUC on the calibration slice of the training window (the first
  measurement outside the fitted rows); DeLong paired against the champion. The AUC with its normal interval is ``auc``.
- Calibration at the 5-year mark: Jeffreys and the exact binomial for the level, the Vasicek-corrected binomial with a 0.12
  asset correlation (dossier 02 B.4, the one-factor value the provisions case uses; the SBA loans are small-business
  exposures, and the correlation is a stated assumption of the test, not a fitted value), Hosmer-Lemeshow and Spiegelhalter.
- Stability: PSI of the PD distribution of the evaluated loans against the training rows (ten bins on the training
  quantiles).

Segments: ``portfolio`` for the pooled vintages whose 5-year mark is observed, ``fy<YYYY>`` for one vintage.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.core.policy import default_policy
from riskvalidation.core.registry import spec
from riskvalidation.validation import calibration as cal
from riskvalidation.validation import discrimination as disc
from riskvalidation.validation import stability as st

from ...core.manifest import TEST_RESULT_KEYS

PORTFOLIO = "portfolio"
RHO = 0.12


def _rows(results) -> list[dict[str, Any]]:
    return [r.to_dict() for r in (results if isinstance(results, list) else [results])]


def not_evaluated(test_id: str, model_id: str | None, segment: str | None, reason: str, *, n: int | None = None,
                  n_events: int | None = None) -> dict[str, Any]:
    """A row for a test that cannot run: the engine's identity of the test, null numbers, and the reason in ``notes``."""
    s = spec(test_id)
    row = {"test_id": test_id, "model_id": model_id, "segment": segment, "statistic": None, "p_value": None, "metric": None,
           "h0": s.h0, "alternative": "not evaluated", "policy_version": default_policy().label, "alpha_amber": None,
           "alpha_red": None, "light": "not_evaluated", "n": n, "n_events": n_events, "inputs_hash": "", "reference": s.reference,
           "notes": reason, "extras": {}}
    assert set(row) == set(TEST_RESULT_KEYS)
    return row


def engine_rows(rung: str, pd_eval: np.ndarray, y_eval: np.ndarray, *, pd_train: np.ndarray | None = None,
                pd_cal: np.ndarray | None = None, y_cal: np.ndarray | None = None,
                champion_pd: np.ndarray | None = None) -> list[dict[str, Any]]:
    """The battery for one rung on the pooled evaluation set, in a fixed order. The references are optional: without
    ``pd_train`` the PSI is not run; without ``pd_cal`` and ``y_cal`` the AUC against the calibration slice is not run."""
    y = np.asarray(y_eval, dtype=int)
    pd_eval = np.asarray(pd_eval, dtype=float)
    kw = {"model_id": rung, "segment": PORTFOLIO}
    rows: list[dict[str, Any]] = []
    constant = float(np.ptp(pd_eval)) == 0.0
    if not constant:
        if pd_cal is not None and y_cal is not None:
            auc0, s2, *_ = disc.auc_with_variance(pd_cal, np.asarray(y_cal, dtype=int))
            rows += _rows(disc.disc_auc_vs_initial(float(auc0), pd_eval, y, auc_initial_variance=float(s2), **kw))
        if champion_pd is not None:
            rows += _rows(disc.disc_delong(pd_eval, champion_pd, y, **kw))
    n, d, p = int(len(y)), int(y.sum()), float(pd_eval.mean())
    rows += _rows(cal.pd_jeffreys(n, d, p, **kw))
    rows += _rows(cal.pd_binomial(n, d, p, **kw))
    rows += _rows(cal.pd_binomial_vasicek(n, d, p, RHO, **kw))
    if not constant:
        rows += _rows(cal.pd_hosmer_lemeshow(y, pd_eval, fitted=False, **kw))
    rows += _rows(cal.pd_spiegelhalter(y, pd_eval, **kw))
    if not constant and pd_train is not None:
        edges = st.quantile_edges(pd_train, 10)
        rows += _rows(st.stability_psi(st.bin_counts(pd_train, edges), st.bin_counts(pd_eval, edges), **kw))
    return rows


def vintage_rows(rung: str, fy: int, pd_eval: np.ndarray, y_eval: np.ndarray) -> list[dict[str, Any]]:
    """The rows of one vintage whose 5-year mark is observed: Jeffreys and the binomial for the level."""
    y = np.asarray(y_eval, dtype=int)
    kw = {"model_id": rung, "segment": f"fy{fy}"}
    n, d, p = int(len(y)), int(y.sum()), float(np.mean(pd_eval))
    return [*_rows(cal.pd_jeffreys(n, d, p, **kw)), *_rows(cal.pd_binomial(n, d, p, **kw))]


def auc(pd_eval: np.ndarray, y_eval: np.ndarray) -> dict[str, float] | None:
    """The engine's AUC with its normal interval, or None when the sample has one class only."""
    y = np.asarray(y_eval, dtype=int)
    if not 0 < int(y.sum()) < len(y):
        return None
    r = disc.disc_auc(np.asarray(pd_eval, dtype=float), y).to_dict()
    return {"auc": r["metric"], "low": r["extras"]["ci95_low"], "high": r["extras"]["ci95_high"]}


def brier(pd_eval: np.ndarray, y_eval: np.ndarray) -> float:
    return float(cal.pd_brier(np.asarray(y_eval, dtype=int), np.asarray(pd_eval, dtype=float)).metric)


def jeffreys_interval(n: int, d: int, pd_applied: float) -> tuple[float, float]:
    """The 95% Jeffreys posterior interval of the observed rate, from the engine's Jeffreys test."""
    r = cal.pd_jeffreys(n, d, pd_applied).to_dict()
    return float(r["extras"]["posterior_q025"]), float(r["extras"]["posterior_q975"])


def psi(pd_train: np.ndarray, pd_eval: np.ndarray, *, model_id: str, segment: str) -> dict[str, Any]:
    edges = st.quantile_edges(pd_train, 10)
    return st.stability_psi(st.bin_counts(pd_train, edges), st.bin_counts(pd_eval, edges), model_id=model_id,
                            segment=segment).to_dict()
