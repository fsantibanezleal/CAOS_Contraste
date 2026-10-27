"""The c02-models document: every fitted rung of the five files and the pooled variant, with its internals, and the protocol."""
from __future__ import annotations

from typing import Any

from . import conventions as cv
from .fits import Fit


#: the engine of each rung of the ladder (``cases/c01_ladder``) in both languages: the library and class names stay as published, the
#: words around them are translated (U16-R3 c03 B3: "own on optbinning" in the Spanish Context)
ENGINE_TEXT: dict[str, dict[str, str]] = {
    "own": cv.t("own", "propio"),
    "own on optbinning": cv.t("own on optbinning", "propio sobre optbinning"),
    "optbinning + statsmodels Logit": cv.t("optbinning + statsmodels Logit"),
    "scikit-learn LogisticRegression": cv.t("scikit-learn LogisticRegression"),
    "scikit-learn trees and LogisticRegression, own rule extraction": cv.t(
        "scikit-learn trees and LogisticRegression, own rule extraction", "árboles y regresión logística de scikit-learn, extracción de reglas propia"),
    "InterpretML ExplainableBoostingClassifier": cv.t("InterpretML ExplainableBoostingClassifier"),
    "LightGBM": cv.t("LightGBM"),
    "XGBoost": cv.t("XGBoost"),
}


def engine_text(engine: str) -> dict[str, str]:
    """The bilingual engine of a rung; an engine the table does not name raises, so a new rung never prints English in Spanish."""
    try:
        return dict(ENGINE_TEXT[engine])
    except KeyError:
        raise KeyError(f"the engine {engine!r} of a C02 rung has no Spanish in models.ENGINE_TEXT") from None


def summary(rung_record: dict[str, Any], hid: str, rid: str, with_details: bool) -> dict[str, Any]:
    """The model record of one rung of one document: the ladder's record with the document's id and the schema's rung code."""
    rec = dict(rung_record)
    rec["id"] = f"{hid}-{rid}"
    rec["rung"] = cv.RUNG_CODE[rid]
    if not with_details:
        rec.pop("details", None)
    return rec


def model_records(fit: Fit, with_details: bool, only: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    out = []
    for rid, rung in fit.rungs.items():
        if only is not None and rid not in only:
            continue
        rec = summary(rung.record(), fit.horizon_id, rid, with_details)
        if with_details and rid == "P0-constant":
            rec["details"] = {**rec["details"], "preprocessing": fit.pp.record()}      # the fitted state, recorded once per fit
        out.append(rec)
    return out


def fit_document(fits: dict[str, Fit], protocol: dict[str, Any]) -> dict[str, Any]:
    first = next(iter(fits.values()))
    ladder = [{"rung": cv.RUNG_CODE[rid], "label": r.title, "engine": engine_text(r.engine), "reference": "04 PD ladder P0 to P4 (application scorecards)"}
              for rid, r in first.rungs.items()]
    files = [{"horizon_id": f.horizon_id, "years": f.years, "file": f.file, "rows": int(len(f.y)), "events": int(f.y.sum())}
             for f in fits.values() if f.years is not None]
    return {"files": files, "ladder": ladder, "protocol": protocol, "parameters": cv.parameters()}
