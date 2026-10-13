"""The C03 models document (``c03-models``): what was fitted, per training window (CT-806, CT-810).

Each variant document carries the summaries of the rungs of its own window; the models document carries the vintage
definition, the target, the five cohort windows (each with its own training window) and the rungs of the latest window (the one
of the last cohort) with their internals.
"""
from __future__ import annotations

from typing import Any

from . import windows
from .fit import RUNG_KINDS, WindowFit


def _records(wf: WindowFit) -> list[dict[str, Any]]:
    out = []
    for rung in wf.rungs.values():
        rec = rung.record()
        rec["parameters"] = {**rec["parameters"], "fit_rows": {"value": float(wf.fit_rows), "unit": "loans"},
                             "calibration_rows": {"value": float(wf.cal_rows), "unit": "loans"},
                             "window_loans": {"value": float(wf.n_loans), "unit": "loans"},
                             "window_events": {"value": float(wf.n_events), "unit": "charge-offs"}}
        out.append(rec)
    return out


def model_records(wf: WindowFit) -> list[dict[str, Any]]:
    """The rungs with their internals (``details``)."""
    return _records(wf)


def model_summaries(wf: WindowFit) -> list[dict[str, Any]]:
    """The rungs without their internals, as a variant document lists them."""
    return [{k: v for k, v in r.items() if k != "details"} for r in _records(wf)]


def _coef(name: str, estimate: float) -> dict[str, Any]:
    return {"name": name, "estimate": float(estimate), "std_error": None}


def ladder_entries(wf: WindowFit) -> list[dict[str, Any]]:
    """One entry per fitted rung: covariates, coefficients (a standard error only where the fit keeps one) and the cutoff."""
    out = []
    for rid, rung in wf.rungs.items():
        d = rung.details
        cov: list[str] = []
        coefs: list[dict[str, Any]] = []
        if rid == "P1-scorecard":
            cov = list(d["features"])
            coefs = [_coef("(intercept)", d["intercept"]), *(_coef(f, b) for f, b in d["coefficients"].items())]
        elif rid == "P2a-l1":
            cov = list(d["coefficients"])
            coefs = [_coef("(intercept)", d["intercept"]), *(_coef(f, b) for f, b in d["coefficients"].items())]
        elif rid == "P2b-pltr":
            cov = list(d["variables"])
            coefs = [_coef("(intercept)", d["intercept"]), *(_coef(f, b) for f, b in d["variables"].items()),
                     *(_coef(r["rule"], r["coefficient"]) for r in d["selected_rules"])]
        elif rid in ("P3-ebm", "P4-lightgbm"):
            cov = list(wf.X_fit.columns)
        out.append({"rung_id": rid, "kind": RUNG_KINDS[rid], "covariates": cov, "coefficients": coefs,
                    "training_cutoff": wf.window.cutoff, "engine": rung.engine})
    return out


def cohort_window(cohort: windows.Cohort, training: dict[str, Any]) -> dict[str, Any]:
    return {"id": cohort.id, "label": {"en": cohort.name, "es": f"AF{cohort.first_fy}-{str(cohort.last_fy)[2:]}"},
            "first_fy": cohort.first_fy, "last_fy": cohort.last_fy, "training": training}
