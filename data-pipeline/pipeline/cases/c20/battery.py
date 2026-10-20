"""The labelled fairness battery on the Taiwan model (decision Q5): twelve engine rows, four tests by three protected attributes.

The tests are the outcome-conditioned ones of ``riskvalidation.validation.fairness`` (equalized odds, equal opportunity, calibration within
groups, AUC by group); the Taiwan data carry an outcome (default next month), so they run here and never on HMDA. The decision is the flag
"declined": the PD at or above the cut-off that declines the worst 20 percent of the variant's baseline decisions (decision Q10), and y = 1
is a default, so the true positive rate is the share of defaulters the cut-off declines. The three attributes are sex, age (four bands) and
marital status (three groups); none is a model input. The rows are labelled evidence on one model of one benchmark, not a statement about
any lender and not a compliance statement; the four-fifths ratio is an employment benchmark and is not part of this battery.

Group values of the document: equalized odds shows the false positive rate of each group (the true positive rate is under equal
opportunity), equal opportunity the true positive rate, calibration within groups the expected calibration error and AUC by group the AUC.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from . import ops
from .conv import REJECT_SHARE, t

ATTRIBUTES = ("sex", "age", "marital_status")
TESTS = ("fair.equalized_odds", "fair.equal_opportunity", "fair.calibration_within_groups", "fair.auc_by_group")
AGE_BANDS = ((0, 30, "under 30"), (30, 40, "30 to 39"), (40, 50, "40 to 49"), (50, 200, "50 and over"))
MARRIAGE = {1: "married", 2: "single"}


def groups_of(X: pd.DataFrame) -> dict[str, np.ndarray]:
    """The three protected attributes of a Taiwan frame as group labels: sex as read, four age bands (a convention) and marital status
    with the codes 3 (others) and 0 (undocumented) in one group, others."""
    age = X["AGE"].to_numpy(dtype=float)
    bands = np.empty(len(age), dtype=object)
    for lo, hi, name in AGE_BANDS:
        bands[(age >= lo) & (age < hi)] = name
    return {"sex": X["protected_attr"].astype(str).to_numpy(dtype=object), "age": bands,
            "marital_status": np.array([MARRIAGE.get(int(v), "others") for v in X["MARRIAGE"]], dtype=object)}


def notice() -> dict[str, str]:
    return t("Labelled evidence on the Taiwan model of this variant: gaps in error rates, calibration and AUC across sex, age band and marital "
             "status groups at a cut-off that declines 20 percent of the baseline decisions. It is a descriptive check on one benchmark, not a "
             "statement about any lender and not a compliance statement.",
             "Evidencia etiquetada sobre el modelo de Taiwan de esta variante: brechas de tasas de error, calibración y AUC entre grupos de sexo, "
             "tramo de edad y estado civil con un punto de corte que rechaza el 20 por ciento de las decisiones base. Es una verificación "
             "descriptiva sobre un benchmark, no una afirmación sobre ningún prestamista ni una declaración de cumplimiento.")


def _group_values(test_id: str, extras: dict[str, Any], names: list[str]) -> dict[str, float | None]:
    if test_id == "fair.equalized_odds":
        return {g: (extras["rates_by_group"].get(g) or {}).get("fpr") for g in names}
    if test_id == "fair.equal_opportunity":
        return {g: (extras["rates_by_group"].get(g) or {}).get("tpr") for g in names}
    if test_id == "fair.calibration_within_groups":
        return {g: extras["ece_by_group"].get(g) for g in names}
    return {g: extras["auc_by_group"].get(g) for g in names}


def run(model_id: str, pd_decision: np.ndarray, cut: float, X: pd.DataFrame, y: np.ndarray) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The battery block of a document and the twelve engine rows behind it. ``pd_decision`` are the PDs of the rows ``X`` (the variant's
    own: clean, noisy or at decision time) and ``cut`` the fixed cut-off."""
    from riskvalidation.validation import fairness as fv

    pdv = np.asarray(pd_decision, dtype=float)
    decision = (pdv >= cut).astype(int)
    yy = np.asarray(y, dtype=int)
    rows: list[dict[str, Any]] = []
    out: list[dict[str, Any]] = []
    for test_id in TESTS:
        for attr, grp in groups_of(X).items():
            if test_id == "fair.equalized_odds":
                res = fv.equalized_odds(model_id, yy, decision, grp)
            elif test_id == "fair.equal_opportunity":
                res = fv.equal_opportunity(model_id, yy, decision, grp)
            elif test_id == "fair.calibration_within_groups":
                res = fv.calibration_within_groups(model_id, pdv, yy, grp)
            else:
                res = fv.auc_by_group(model_id, pdv, yy, grp)
            r = ops.row(res, model_id=model_id, segment=attr)
            rows.append(r)
            names = sorted({str(g) for g in grp})
            vals = _group_values(test_id, r["extras"], names)
            out.append({"test_id": test_id, "attribute": attr, "value": r["metric"],
                        "groups": [{"group": g, "n": int((grp == g).sum()), "value": vals[g]} for g in names], "light": r["light"]})
    return {"label": "labelled-fairness-battery", "model": "uci-taiwan", "notice": notice(), "rows": out}, rows


def cut_for(pd_baseline: np.ndarray) -> float:
    from .fits import cutoff

    return cutoff(pd_baseline, REJECT_SHARE)
