"""The seed sweep: the boosted rungs of the Taiwan ladder refitted across 20 seeds, and the reason codes across 100 bootstrap refits.

For each boosted rung (the P4 LightGBM and XGBoost rungs: the learning engines whose training is random; the scorecard and the penalised
rungs are deterministic given the data, and the EBM and PLTR rungs have no TreeSHAP attribution, so they are not swept, stated) the
rung is refitted with each seed on the same training slice with the number of rounds chosen on the first fit and an isotonic map refitted on
the calibration slice. The engine reads the dispersion of the AUC on the locked holdout, the share of obligors whose master-scale grade
differs between seeds, the Kendall rank stability of the mean absolute TreeSHAP attribution per feature, the top-four reason overlap across
100 bootstrap refits (signed attribution on the log-odds of default, the four largest contributions toward default), and the agreement of
the attribution ranks with the ranges of the accumulated local effects (Apley and Zhu).
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ...core.calibration import MASTER_SCALE_UPPER, clip_pd, fit_isotonic
from . import battery, fits, ops
from .conv import N_BOOTSTRAP_REFITS, N_SEEDS, REJECT_SHARE, TOP_K, impact_cutoff, parameters_block, t
from .data import Frame

SEED0 = 42
SHAP_ROWS = 1000
ALE_ROWS = 2000
ALE_BINS = 10
N_TOP = 10
RUNGS = ("P4-lightgbm", "P4-xgboost")


def _refit(frame: Frame, rung_id: str, base: Any, seed: int, ix: np.ndarray | None = None) -> Any:
    model = base.model
    if rung_id == "P4-lightgbm":
        return fits.refit_lightgbm(frame, seed, model.rounds, ix, model.codes)
    return fits.refit_xgboost(frame, seed, model.rounds, ix, model.codes)


def ale_effects(pred: Any, X: np.ndarray, names: tuple[str, ...]) -> tuple[np.ndarray, dict[int, tuple[np.ndarray, np.ndarray]]]:
    """The range of the ALE curve of every feature and the curves themselves; the bins are lowered until the quantile edges are distinct
    (a feature with fewer than two distinct values has no effect: range 0)."""
    from riskvalidation.ml.effects import accumulated_local_effects

    ranges = np.zeros(len(names))
    curves: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for j in range(len(names)):
        for nb in range(ALE_BINS, 1, -1):
            try:
                edges, eff = accumulated_local_effects(pred, X, j, nb)
            except ValueError:
                continue
            ranges[j] = float(eff.max() - eff.min())
            curves[j] = (edges, eff)
            break
    return ranges, curves


def build(frame: Frame, rungs: dict[str, Any], seed: int) -> dict[str, Any]:
    from riskvalidation.ml import explanations as ex
    from riskvalidation.ml import generalisation as gen
    from riskvalidation.ml import seeds as sd
    from riskvalidation.validation import ml as mlv

    hold = frame.hold
    Xh_df, yh = frame.part("hold")
    Xh = fits.matrix(frame, hold)
    Xcal_df, ycal = frame.part("cal")
    shap_ix = np.arange(min(SHAP_ROWS, len(hold)))
    ale_ix = np.random.default_rng(seed).choice(len(hold), size=min(ALE_ROWS, len(hold)), replace=False)
    edges = np.array(MASTER_SCALE_UPPER[:-1], dtype=float)
    seeds = [SEED0 + k for k in range(N_SEEDS)]
    rows, explainers, tests, models, flips = [], [], [], [], []
    Xtr_df = frame.part("train")[0]
    base_pd_hold = None
    for rid in RUNGS:
        mid = fits.rung_id(rid, frame)
        base = rungs[rid]
        models.append(mid)
        cache: dict[int, Any] = {}
        pds, importances = [], []
        for s in seeds:
            m = _refit(frame, rid, base, s)
            iso = fit_isotonic(clip_pd(m.predict_pd(Xcal_df)), ycal)
            r = fits.as_rung(m, base, iso)
            cache[s] = fits.Predictor(r, tuple(frame.features), fits.predictor(base, frame).int_columns)
            pds.append(r.pd(Xh_df))
            phi, _, _ = fits.shap_values(r, Xh_df.iloc[shap_ix])
            importances.append(fits.mean_abs(phi))
        disp = sd.seed_auc_dispersion(lambda s: cache[s], Xh, yh, seeds)
        grade = sd.grade_assignment_stability(np.vstack(pds), edges)
        tau = sd.attribution_rank_stability(np.vstack(importances))
        rng = np.random.default_rng([seed, 7, RUNGS.index(rid)])
        att = np.empty((N_BOOTSTRAP_REFITS, len(shap_ix), len(frame.features)))
        for b in range(N_BOOTSTRAP_REFITS):
            ix = rng.integers(0, len(frame.train), len(frame.train))
            mb = _refit(frame, rid, base, SEED0 + 1000 + b, ix)
            phi, _, _ = fits.shap_values(fits.as_rung(mb, base, None), Xh_df.iloc[shap_ix])
            att[b] = phi
        over = ex.reason_code_overlap(att, TOP_K)
        rows.append({"rung": rid, "n_seeds": disp.n_seeds,
                     "auc": {"mean": disp.mean, "sd": disp.sd, "min": disp.minimum, "max": disp.maximum},
                     "grade_assignment_changed_share": float(grade),
                     "attribution_rank_tau": {"mean": tau.mean_tau, "min": tau.min_tau},
                     "reason_code_overlap": {"top_k": over.top_k, "n_refits": over.n_refits, "mean": over.mean, "p05": over.p05}})
        tests.append(ops.row(mlv.seed_stability(mid, disp), segment=f"{N_SEEDS}-seeds"))
        tests.append(ops.row(mlv.reason_code_stability(mid, over), segment=f"{N_BOOTSTRAP_REFITS}-bootstrap-refits"))
        # the explainer agreement: the first fit's mean absolute attribution against the range of its ALE curve
        pred = fits.predictor(base, frame)
        phi0, base_v, margin0 = fits.shap_values(base, Xh_df.iloc[shap_ix])
        imp = fits.mean_abs(phi0)
        ranges, curves = ale_effects(pred, Xh[ale_ix], tuple(frame.features))
        try:
            rho: float | None = float(ex.rank_agreement(imp, ranges))
            reason = None
            tests.append(ops.row(mlv.effect_agreement(mid, rho, len(frame.features)), segment="shap-vs-ale-range"))
        except ValueError as exc:
            rho, reason = None, str(exc)
        top = []
        for j in np.argsort(-imp, kind="stable")[:N_TOP]:
            if int(j) not in curves:
                continue
            e, eff = curves[int(j)]
            top.append({"feature": frame.features[int(j)], "shap_importance": float(imp[j]), "effect_range": float(ranges[j]),
                        "ale": {"edges": [float(v) for v in e], "effect": [float(v) for v in eff]}})
        explainers.append({"rung": rid, "effect_reference": "ale", "n_features": len(frame.features), "rank_correlation": rho,
                           "reason_if_null": reason, "top_features": top})
        tests.append(ops.row(mlv.additivity(mid, ex.shapley_additivity_gap(margin0, base_v, phi0)), segment="holdout"))
        auc_tr = ops.auc_brier(base.pd(Xtr_df), frame.y[frame.train])[0]
        auc_ho = ops.auc_brier(base.pd(Xh_df), yh)[0]
        tests.append(ops.row(mlv.overfit(mid, gen.overfit_gap(auc_tr, auc_ho, 0.05)), segment="train-vs-holdout"))
        if rid == "P4-lightgbm":
            base_pd_hold = base.pd(Xh_df)
            cut = fits.cutoff(base_pd_hold, REJECT_SHARE)
            flips = [{"shift_id": f"seed-{s}", "flip_share": fits.flip_share(base_pd_hold, pd_s, cut), "n_decisions": int(len(hold))}
                     for s, pd_s in zip(seeds, pds)]
            bat, bat_rows = battery.run(mid, base_pd_hold, cut, frame.X.iloc[hold], yh)
            tests.extend(bat_rows)
    outputs = {"kind": "seeds", "dataset_id": "uci-taiwan", "model_dataset": "uci-taiwan", "sgcd_notice": None, "parameters": parameters_block(),
               "fairness_battery": bat, "impact_detail": {"label": "decision-flip", "cutoff": impact_cutoff(), "rows": flips},
               "requirements": ["CT-2010", "CT-2011", "CT-2012", "CT-2016", "CT-2022"], "rows": rows, "explainer_agreement": explainers}
    impact = {"decision_flip_share": {"value": max(f["flip_share"] for f in flips), "unit": "share",
                                      "label": t("Decisions that flip at the stated cut-off between the first fit and a reseeded fit, largest over the seeds",
                                                 "Decisiones que cambian en el punto de corte indicado entre el primer ajuste y uno con otra semilla, la mayor entre las semillas")}}
    return {"outputs": outputs, "tests": tests, "impact": impact, "models": models,
            "limits": [("rungs-swept", t("Only the two boosted-tree rungs are swept: the others are deterministic given the data or have no TreeSHAP attribution",
                                         "Solo se barren las dos etapas de arboles potenciados: las demas son deterministas dado los datos o no tienen atribucion TreeSHAP")),
                       ("xgboost-float32", t("XGBoost computes in single precision, so the Shapley additivity gap of its rung is about 1e-6 and the engine's 1e-9 tolerance flags it; "
                                             "it is a precision remark on the arithmetic, not an error of the attributions",
                                             "XGBoost calcula en precision simple, de modo que la brecha de aditividad de Shapley de su etapa es cercana a 1e-6 y la tolerancia de 1e-9 del motor la senala; "
                                             "es una observacion de precision aritmetica, no un error de las atribuciones")),
                       ("fixed-rounds", t("The number of boosting rounds is the one chosen on the first fit and is not re-chosen per seed, so the dispersion is the seed's effect with the model size held",
                                         "El numero de rondas se elige en el primer ajuste y no se reelige por semilla, de modo que la dispersion es el efecto de la semilla con el tamano del modelo fijo"))]}
