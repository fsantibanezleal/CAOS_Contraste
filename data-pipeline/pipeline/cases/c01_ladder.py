"""C01's ladder: fit every rung on one training slice, calibrate where the rung needs it, and describe each rung as
the model record contract 2 writes. See docs/design/features/c01-retail-pd/design.md for the rungs and their gates.
"""
from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
import importlib.metadata as md
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..core.calibration import Isotonic, clip_pd, fit_isotonic
from ..model import benchmark, ebm, gbm, penalised, scorecard


def _v(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "not installed"


def _t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


#: the label a chip, a column header or a chart key shows; the title is the full name
SHORT_TITLES: dict[str, dict[str, str]] = {
    "P0-constant": {"en": "P0 Constant", "es": "P0 Constante"},
    "P0-single": {"en": "P0 One variable", "es": "P0 Una variable"},
    "P1-scorecard": {"en": "P1 Scorecard", "es": "P1 Scorecard"},
    "P2a-l1": {"en": "P2a L1", "es": "P2a L1"},
    "P2b-pltr": {"en": "P2b PLTR", "es": "P2b PLTR"},
    "P3-ebm": {"en": "P3 EBM", "es": "P3 EBM"},
    "P4-lightgbm": {"en": "P4 LightGBM", "es": "P4 LightGBM"},
    "P4-xgboost": {"en": "P4 XGBoost", "es": "P4 XGBoost"},
    "P5-tabpfn": {"en": "P5 TabPFN", "es": "P5 TabPFN"},
}


@dataclass
class Rung:
    id: str
    rung: str
    title: dict
    engine: str
    engine_version: str
    licence: str
    model: Any
    calibration: Isotonic | None = None
    parameters: dict = field(default_factory=dict)
    details: dict = field(default_factory=dict)

    def raw_pd(self, X: pd.DataFrame) -> np.ndarray:
        return clip_pd(self.model.predict_pd(X))

    def pd(self, X: pd.DataFrame) -> np.ndarray:
        raw = self.raw_pd(X)
        return self.calibration(raw) if self.calibration is not None else raw

    def record(self) -> dict[str, Any]:
        body = {"id": self.id, "family": "pd-scoring", "rung": self.rung, "title": self.title,
                "short_title": SHORT_TITLES[self.id], "engine": self.engine,
                "engine_version": self.engine_version, "licence": self.licence,
                "calibration": self.calibration.record() if self.calibration is not None else None,
                "parameters": self.parameters, "details": self.details}
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        return {**body, "checkpoint_sha256": digest}


def fit_ladder(
    X_tr: pd.DataFrame, y_tr: np.ndarray, X_cal: pd.DataFrame, y_cal: np.ndarray, folds, *,
    features: tuple[str, ...], categorical: tuple[str, ...], monotone: dict[str, int], seed: int,
    with_xgboost: bool = True, with_tabpfn: bool = False, log: Callable[[str], None] | None = None,
) -> dict[str, Rung]:
    """Every rung fitted on (X_tr, y_tr); the calibration maps on (X_cal, y_cal); folds index into X_tr."""
    clock = [time.perf_counter()]

    def done(rung: str) -> None:
        if log is not None:
            now = time.perf_counter()
            log(f"  {rung} fitted in {now - clock[0]:.1f}s")
            clock[0] = now

    feats = list(features)
    y_tr = np.asarray(y_tr, dtype=int)
    y_cal = np.asarray(y_cal, dtype=int)
    rungs: dict[str, Rung] = {}

    const = benchmark.fit_constant(y_tr)
    rungs["P0-constant"] = Rung("P0-constant", "P0", _t("Constant PD", "PD constante"), "own", "n/a", "MIT", const,
                                parameters={"pd": {"value": const.pd_value, "unit": "probability"}})

    done("P0-constant")
    sc = scorecard.fit_scorecard(X_tr, y_tr, features=feats, categorical=categorical, monotone=monotone)
    single = benchmark.fit_single_variable(sc, y_tr)
    rungs["P0-single"] = Rung("P0-single", "P0", _t(f"Single variable ({single.feature})", f"Una variable ({single.feature})"),
                              "own on optbinning", _v("optbinning"), "Apache-2.0", single, details=single.record(),
                              parameters={"bins": {"value": len(single.event_rates), "unit": "bins"}})
    rungs["P1-scorecard"] = Rung(
        "P1-scorecard", "P1", _t("WoE logistic scorecard", "Scorecard logística WoE"),
        "optbinning + statsmodels Logit", f"optbinning {_v('optbinning')}, statsmodels {_v('statsmodels')}",
        "Apache-2.0, BSD-3-Clause", sc, details=scorecard.record(sc),
        parameters={"pdo": {"value": sc.pdo, "unit": "points"}, "odds_ref": {"value": sc.odds_ref, "unit": "odds"},
                    "score_ref": {"value": sc.score_ref, "unit": "points"},
                    "iv_min": {"value": scorecard.IV_MIN, "unit": "information value"},
                    "min_bin_size": {"value": scorecard.MIN_BIN_SIZE, "unit": "fraction of records"}})

    done("P1-scorecard and P0-single")
    screened = [f for f in feats if sc.iv[f] >= scorecard.IV_MIN]
    binnings = sc.binnings | _all_binnings(sc, X_tr, y_tr, screened, categorical, monotone)
    l1 = penalised.fit_penalised_woe(sc, binnings, X_tr, y_tr, folds, seed=seed, screened=screened)
    rungs["P2a-l1"] = Rung("P2a-l1", "P2", _t("L1 logistic regression on WoE", "Regresión logística L1 sobre WoE"),
                           "scikit-learn LogisticRegression", _v("scikit-learn"), "BSD-3-Clause", l1, details=l1.record(),
                           parameters={"C": {"value": l1.c, "unit": "inverse penalty"}})

    done("P2a-l1")
    cat_woe = {f: binnings.get(f) or scorecard._fit_binning(f, X_tr[f].to_numpy(), y_tr, True, 0) for f in categorical}
    pl = penalised.fit_pltr(X_tr, y_tr, feats, folds, seed=seed, woe=cat_woe)
    rungs["P2b-pltr"] = Rung("P2b-pltr", "P2", _t("Penalised logistic tree regression (PLTR)",
                                                  "Regresión logística penalizada con árboles (PLTR)"),
                             "scikit-learn trees and LogisticRegression, own rule extraction", _v("scikit-learn"),
                             "BSD-3-Clause", pl, details=pl.record(),
                             parameters={"C": {"value": pl.c, "unit": "inverse penalty"},
                                         "rules": {"value": len(pl.rules), "unit": "candidate rules"}})

    done("P2b-pltr")
    e = ebm.fit_ebm(X_tr, y_tr, features=feats, categorical=categorical, monotone=monotone, seed=seed)
    ex = ebm.export(e)
    rungs["P3-ebm"] = Rung("P3-ebm", "P3", _t("Explainable boosting machine (GA2M)", "Máquina de boosting explicable (GA2M)"),
                           "InterpretML ExplainableBoostingClassifier", _v("interpret-core"), "MIT", e,
                           calibration=fit_isotonic(clip_pd(e.predict_pd(X_cal)), y_cal), details={"export": ex},
                           parameters={k: {"value": v, "unit": "count"} for k, v in ex["config"].items()})

    done("P3-ebm")
    lg = gbm.fit_lightgbm(X_tr, y_tr, folds, features=feats, categorical=categorical, monotone=monotone, seed=seed)
    rungs["P4-lightgbm"] = Rung("P4-lightgbm", "P4", _t("Monotone gradient boosting (LightGBM)",
                                                        "Gradient boosting monótono (LightGBM)"),
                                "LightGBM", _v("lightgbm"), "MIT", lg,
                                calibration=fit_isotonic(clip_pd(lg.predict_pd(X_cal)), y_cal),
                                details={**gbm.record(lg), "monotonicity": gbm.monotonicity(lg, X_tr, seed=seed)},
                                parameters={"rounds": {"value": lg.rounds, "unit": "trees"},
                                            "learning_rate": {"value": gbm.LGB_PARAMS["learning_rate"], "unit": "shrinkage"},
                                            "num_leaves": {"value": gbm.LGB_PARAMS["num_leaves"], "unit": "leaves"}})
    done("P4-lightgbm")
    if with_xgboost:
        xg = gbm.fit_xgboost(X_tr, y_tr, folds, features=feats, categorical=categorical, monotone=monotone, seed=seed)
        rungs["P4-xgboost"] = Rung("P4-xgboost", "P4", _t("Monotone gradient boosting (XGBoost cross-check)",
                                                          "Gradient boosting monótono (contraste con XGBoost)"),
                                   "XGBoost", _v("xgboost"), "Apache-2.0", xg,
                                   calibration=fit_isotonic(clip_pd(xg.predict_pd(X_cal)), y_cal),
                                   details={**gbm.record(xg), "monotonicity": gbm.monotonicity(xg, X_tr, seed=seed)},
                                   parameters={"rounds": {"value": xg.rounds, "unit": "trees"}})
        done("P4-xgboost")
    if with_tabpfn:
        from ..model import tabpfn_rung

        tp = tabpfn_rung.fit_tabpfn(X_tr, y_tr, features=feats, categorical=categorical, seed=seed)
        rungs["P5-tabpfn"] = Rung("P5-tabpfn", "P5", _t("TabPFN v2 (research challenger)", "TabPFN v2 (retador de investigación)"),
                                  "tabpfn", _v("tabpfn"), tabpfn_rung.WEIGHTS_LICENCE, tp,
                                  calibration=fit_isotonic(clip_pd(tp.predict_pd(X_cal)), y_cal),
                                  details=tp.record(), parameters={"n_estimators": {"value": tp.n_estimators, "unit": "ensemble members"}})
        done("P5-tabpfn")
    return rungs


def _all_binnings(sc, X_tr, y_tr, screened, categorical, monotone) -> dict:
    """Binnings for the screened variables the scorecard's sign check dropped (P2a starts from every screened one)."""
    out = {}
    for f in screened:
        if f not in sc.binnings:
            out[f] = scorecard._fit_binning(f, X_tr[f].to_numpy(), y_tr, f in categorical, monotone.get(f, 0))
    return out
