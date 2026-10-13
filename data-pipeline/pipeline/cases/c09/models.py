"""The EAD model ladder of C09: CCF constants by design and treatment, a bounded-scale CCF model, a direct EAD model and a
utilisation-change model, fitted on the development replications and predicted on the test replications (CT-907, CT-910).

Every fit, prediction and back-test comes from ``riskvalidation``: ``ccf.aggregate_ccf``, ``ccf.fit_direct_ead``,
``ccf.fit_utilisation_change``, ``ccf.predict_ead``, ``ccf.ead_from_ccf``, ``lgd_models.fit_fractional_logit`` and
``validation.lgd_ead.ead_backtest_by_band``. The product chooses the covariates, subsets the observations and orders the rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.lgd_ead import ccf, lgd_models
from riskvalidation.validation import lgd_ead as val

from . import estimators as est
from .params import PARAMS

#: id, kind, design, treatment; ``estimator`` is the aggregator of a CCF constant (pooled: the ratio of sums, right in currency)
MODELS: tuple[dict[str, Any], ...] = (
    {"id": "ccf-fixed-horizon-none", "kind": "ccf-fixed-horizon", "design": "fixed-horizon", "treatment": "none"},
    {"id": "ccf-fixed-horizon-censor", "kind": "ccf-fixed-horizon", "design": "fixed-horizon", "treatment": "censor"},
    {"id": "ccf-fixed-horizon-floor-cap", "kind": "ccf-fixed-horizon", "design": "fixed-horizon", "treatment": "floor-cap"},
    {"id": "ccf-fixed-horizon-bounded-scale", "kind": "ccf-fixed-horizon", "design": "fixed-horizon", "treatment": "bounded-scale"},
    {"id": "ccf-cohort-floor-cap", "kind": "ccf-cohort", "design": "cohort", "treatment": "floor-cap"},
    {"id": "ccf-variable-horizon-floor-cap", "kind": "ccf-variable-horizon", "design": "variable-horizon", "treatment": "floor-cap"},
    {"id": "direct-ead", "kind": "direct-ead", "design": None, "treatment": None},
    {"id": "utilisation-change", "kind": "utilisation-change", "design": None, "treatment": None},
)
MODEL_DESIGN = {m["id"]: m["design"] or "fixed-horizon" for m in MODELS}
CCF_ESTIMATOR = "pooled"


def covariates(model: dict[str, Any]) -> list[str]:
    if model["kind"] in ("direct-ead", "utilisation-change") or model["treatment"] == "bounded-scale":
        return list(est.FEATURE_NAMES[1:])
    return []


@dataclass(frozen=True)
class Fitted:
    """The fit of one model: a CCF constant, a fractional logit or an engine ``EadFit``."""

    model: dict[str, Any]
    ccf: float | None = None
    logit: lgd_models.LgdFit | None = None
    ead_fit: ccf.EadFit | None = None
    thin: int = 1                 # the fit used every thin-th observation of the pooled development sample (1: all of them)


def fit_models(dev: dict[str, est.Observations]) -> dict[str, Fitted]:
    """Fit every model on the pooled development observations of its design."""
    out: dict[str, Fitted] = {}
    for m in MODELS:
        obs = dev[MODEL_DESIGN[m["id"]]]
        if m["kind"] == "direct-ead":
            fit, k = est.fit_robust(lambda o: ccf.fit_direct_ead(est.features(o), o.ead, o.limit_ref, est.FEATURE_NAMES), obs)
            out[m["id"]] = Fitted(m, ead_fit=fit, thin=k)
        elif m["kind"] == "utilisation-change":
            out[m["id"]] = Fitted(m, ead_fit=ccf.fit_utilisation_change(est.features(obs), obs.drawn_ref, obs.ead, obs.limit_ref,
                                                                         est.FEATURE_NAMES))
        elif m["treatment"] == "bounded-scale":
            fit, k = est.fit_bounded(obs)
            out[m["id"]] = Fitted(m, logit=fit, thin=k)
        else:
            tr = est.treat(obs, m["treatment"])
            out[m["id"]] = Fitted(m, ccf=float(ccf.aggregate_ccf(tr.values, tr.undrawn, CCF_ESTIMATOR)))
    return out


def predict(fit: Fitted, obs: est.Observations) -> np.ndarray:
    """The predicted EAD at each observation's reference date. A CCF is applied to the undrawn amount, floored at zero for a
    line already at or over its limit (it has no commitment left to draw), so its EAD is its balance."""
    k = obs.ccf.size
    eff_limit = np.maximum(obs.limit_ref, obs.drawn_ref)
    if fit.ccf is not None:
        return ccf.ead_from_ccf(obs.drawn_ref, eff_limit, np.full(k, fit.ccf))
    if fit.logit is not None:
        return ccf.ead_from_ccf(obs.drawn_ref, eff_limit, lgd_models.predict_lgd(fit.logit, est.features(obs)))
    assert fit.ead_fit is not None
    return ccf.predict_ead(fit.ead_fit, est.features(obs), obs.drawn_ref, obs.limit_ref)


def backtest(fit: Fitted, obs: est.Observations) -> dict[str, Any]:
    """The back-test of one model in currency by utilisation band: the engine test on the whole sample (its row for the document
    ``tests``) and, band by band, the engine test on that band alone (the light and the numbers of ``ead_backtest.rows``)."""
    pred = predict(fit, obs)
    util = obs.drawn_ref / obs.limit_ref
    edges = np.asarray(PARAMS["band_edges"], dtype=float)
    mid = fit.model["id"]
    whole = val.ead_backtest_by_band(pred, obs.ead, util, edges, model_id=mid)
    rows = []
    for b in range(edges.size - 1):
        lo, hi = float(edges[b]), float(edges[b + 1])
        m = (util >= lo) & ((util < hi) if b < edges.size - 2 else (util <= hi))
        if not m.any() or obs.ead[m].sum() <= 0:
            continue
        one = val.ead_backtest_by_band(pred[m], obs.ead[m], util[m], np.array([lo, hi]), model_id=mid)
        band = one.extras["bands"][0]
        outside = bool((pred[m] < 0).any() or (pred[m] > obs.limit_ref[m]).any())
        rows.append({"model_id": mid, "band_id": f"u{b + 1}", "utilisation_lower": lo, "utilisation_upper": hi, "n": int(band["n"]),
                     "predicted_ead": float(band["predicted_ead"]), "prediction_flag": "outside-range" if outside else "in-range",
                     "realised_ead": float(band["realised_ead"]), "gap": float(band["gap"]), "relative_gap": float(band["relative_gap"]),
                     "light": getattr(one.light, "value", one.light)})
    return {"test": whole, "rows": rows, "pred": pred}
