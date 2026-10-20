"""The Fed shift probes: the three 200-loan Federal Reserve 2025 corporate portfolios read both ways (decision Q7), on the Polish 3-year model.

Reading (a), real drift with no model: the PSI, CSI, KS and chi-square tests of the engine between the typical, higher-risk and lower-risk
portfolios, variable by variable. Reading (b), the portfolios as the reference of a synthetic shift on the Polish evaluation set: the Polish
ratios cannot be matched to the Fed loan variables, so the Fed portfolios fix the SIZE of the shift. The risk-defining variable of the
portfolios is the rating; the PSI of the rating between the typical and the higher-risk portfolio is the anchor, and the shifts add a mean
displacement of ``score`` standard deviations (the ``shift score`` of the row) to the five features the model leans on most, in the direction
that raises its PD, solved so that the PSI of the model's score on its baseline deciles is 0.25, 0.5 and 1 times the anchor. The labels of
the evaluation rows do not change (a covariate shift: the displacement is known, the concept is constant). Synthetic shifts touch the
evaluation set only; the locked holdout rows are the same rows before and after.

Where labels are withheld: split conformal coverage of the calibrated PD on the baseline and the three shifted windows, and the CBPE estimate
of the AUC on the one-times shift, always labelled an estimate. The resilience test reads the AUC drop on the worst 10 percent of the shifted
rows by a resemblance score against the drops of random development subsets (a development-only permutation reference).
"""
from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

from . import fed, fits, ops
from .conv import CONFORMAL_ALPHA, REJECT_SHARE, WORST_SUBSAMPLE_SHARE, impact_cutoff, parameters_block, t
from . import data
from .data import Frame

PAIRS = (("typical", "higher-risk"), ("typical", "lower-risk"), ("lower-risk", "higher-risk"))
REFERENCE = "higher-risk"
ANCHOR_PAIR = ("typical", "higher-risk")
MULTIPLES = (0.25, 0.5, 1.0)
N_FEATURES_SHIFTED = 5
DELTA_MAX = 6.0
SHIFT_PERMUTATIONS = 199
SHAP_ROWS = 2000
ASSUMPTIONS = (
    ("calibrated-probabilities", t("The PDs are calibrated: the isotonic map is fitted on the calibration slice", "Las PD estan calibradas: el mapa isotonico se ajusta en el tramo de calibracion")),
    ("no-concept-drift", t("The link between the ratios and bankruptcy is unchanged by the shift", "La relacion entre las razones y la quiebra no cambia con el desplazamiento")),
    ("no-extrapolation", t("The shifted rows stay inside the region the model was fitted on", "Las filas desplazadas permanecen dentro de la region en que se ajusto el modelo")),
    ("adequate-sample", t("The window holds enough rows for the expected confusion to be stable", "La ventana tiene filas suficientes para que la confusion esperada sea estable")))


def psi_of(base: np.ndarray, cur: np.ndarray) -> float:
    from riskvalidation.validation.stability import bin_counts, quantile_edges, stability_psi

    edges = quantile_edges(base, 10)
    return float(stability_psi(bin_counts(base, edges).astype(float), bin_counts(cur, edges).astype(float)).metric)


class Shifter:
    """The displacement of the model's five leading features by ``delta`` standard deviations in the direction that raises the PD."""

    def __init__(self, pred: Any, X_dev: np.ndarray, importance: np.ndarray, pd_dev: np.ndarray) -> None:
        """``pred`` is the raw (uncalibrated) PD: the isotonic map is a step function whose plateaus make a PSI on deciles jump."""
        self.cols = np.argsort(-importance, kind="stable")[:N_FEATURES_SHIFTED]
        q1, q3 = np.quantile(X_dev, [0.25, 0.75], axis=0)
        sd = X_dev.std(axis=0, ddof=1)
        robust = (q3 - q1) / 1.349                      # the robust scale: the ratios have outliers that make the standard deviation huge
        self.sd = np.where(robust > 0, robust, sd)
        self.sign = np.array([np.sign(np.corrcoef(X_dev[:, j], pd_dev)[0, 1]) or 1.0 for j in self.cols])
        self.pred = pred

    def __call__(self, X: np.ndarray, delta: float) -> np.ndarray:
        out = X.copy()
        out[:, self.cols] += delta * self.sd[self.cols] * self.sign
        return out

    def solve(self, X: np.ndarray, pd_base: np.ndarray, target: float) -> float:
        """The displacement whose score PSI is ``target`` (bisection; DELTA_MAX when the target is out of reach)."""
        if psi_of(pd_base, self.pred(self(X, DELTA_MAX))) < target:
            return DELTA_MAX
        lo, hi = 0.0, DELTA_MAX
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if psi_of(pd_base, self.pred(self(X, mid))) < target:
                lo = mid
            else:
                hi = mid
        return hi


def real_drift(portfolios: dict[str, fed.Portfolio]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pairs, rows = [], []
    for a, b in PAIRS:
        variables, engine_rows = fed.drift_variables(portfolios[a], portfolios[b])
        pairs.append({"a": a, "b": b, "variables": variables})
        rows.extend(ops.row(r) for r in engine_rows)
    return {"label": "real-drift-no-model", "model": None, "portfolios": list(fed.PORTFOLIOS), "pairs": pairs}, rows


def build(frame: Frame, rungs: dict[str, Any], portfolios: dict[str, fed.Portfolio], seed: int) -> dict[str, Any]:
    from riskvalidation.ml import cbpe, conformal, robustness
    from riskvalidation.ml import explanations as ex
    from riskvalidation.ml import generalisation as gen
    from riskvalidation.validation import ml as mlv

    rung = rungs["P4-lightgbm"]
    model_id = fits.rung_id("P4-lightgbm", frame)
    pred_cal = fits.predictor(rung, frame)
    pred = dataclasses.replace(pred_cal, calibrated=False)      # the raw PD: continuous, so the score PSI and the conformal sets have no ties
    hold, dev, cal = frame.hold, frame.dev_index(), frame.cal
    data.assert_locked(frame)
    data.assert_evaluation_only(frame, hold)
    Xh, yh = fits.matrix(frame, hold), frame.y[hold]
    Xd, yd = fits.matrix(frame, dev), frame.y[dev]
    pd_h = pred(Xh)
    base_auc = ops.auc_brier(pred_cal(Xh), yh)[0]
    cut = fits.cutoff(pd_h, REJECT_SHARE)

    drift, tests = real_drift(portfolios)
    anchor = next(v["psi"] for p in drift["pairs"] if (p["a"], p["b"]) == ANCHOR_PAIR for v in p["variables"] if v["name"] == "rating")

    sub = np.random.default_rng(seed).choice(len(dev), size=min(SHAP_ROWS, len(dev)), replace=False)
    phi, _, _ = fits.shap_values(rung, frame.X.iloc[dev[np.sort(sub)]])
    shifter = Shifter(pred, Xd, fits.mean_abs(phi), pred(Xd))

    cal_p = pred(fits.matrix(frame, cal))
    ycal = frame.y[cal]
    scores = np.where(ycal == 1, 1.0 - cal_p, cal_p)         # the nonconformity score 1 - p(true label)
    qhat = conformal.split_conformal_quantile(scores, CONFORMAL_ALPHA)

    shifts, windows, sets_all, y_all = [], [], [], []
    window_sets = {"baseline": (conformal.conformal_sets(pd_h, qhat), yh)}
    shifted: dict[str, np.ndarray] = {}
    for m in MULTIPLES:
        sid = f"fed-{REFERENCE}-x{m:g}"
        delta = shifter.solve(Xh, pd_h, m * anchor)
        Xs = shifter(Xh, delta)
        ps = pred(Xs)
        shifted[sid] = Xs
        psi_row = ops.row(_psi_row(pd_h, ps, model_id), segment=sid)
        tests.append(psi_row)
        shifts.append({"shift_id": sid, "score": float(delta), "metric": ops.metric_block(pred_cal(Xs), yh, base_auc), "psi": float(psi_row["metric"]),
                       "flip_share": fits.flip_share(pd_h, ps, cut)})
        window_sets[sid] = (conformal.conformal_sets(ps, qhat), yh)
    main = f"fed-{REFERENCE}-x1"

    results = {}
    for w, (sets, y_w) in window_sets.items():
        res = conformal.conformal_coverage(sets, y_w, CONFORMAL_ALPHA, n_cal=len(cal))
        results[w] = res
        tests.append(ops.row(mlv.conformal_coverage(model_id, res), segment=f"window:{w}"))
        windows.append({"window": w, "n": int(res.n), "coverage": float(res.coverage), "binomial_p_value": float(res.p_value_binomial)})
        sets_all.append(sets)
        y_all.append(y_w)
    pooled = conformal.conformal_coverage(np.vstack(sets_all), np.concatenate(y_all), CONFORMAL_ALPHA, n_cal=len(cal))
    tests.append(ops.row(mlv.conformal_coverage(model_id, pooled), segment="window:pooled"))

    est = cbpe.cbpe_auc(pred_cal(shifted[main]))
    tests.append(ops.row(mlv.cbpe_estimate(model_id, est), segment=main))

    score = robustness.shift_score_rank(Xd, shifted[main], seed)
    worst = robustness.worst_subsample_performance(pred_cal, shifted[main], yh, score, WORST_SUBSAMPLE_SHARE)
    ref = robustness.shift_development_reference(pred_cal, Xd, yd, shifted[main], yh, score, WORST_SUBSAMPLE_SHARE, SHIFT_PERMUTATIONS, seed)
    tests.append(ops.row(mlv.shift_resilience(model_id, worst, ref), segment=main))

    Xtr, ytr = frame.part("train")
    tests.append(ops.row(mlv.overfit(model_id, gen.overfit_gap(ops.auc_brier(rung.pd(Xtr), ytr)[0], base_auc, 0.05)), segment="train-vs-holdout"))
    phi_h, base_v, margin = fits.shap_values(rung, frame.X.iloc[hold[:SHAP_ROWS]])
    tests.append(ops.row(mlv.additivity(model_id, ex.shapley_additivity_gap(margin, base_v, phi_h)), segment="holdout"))

    synthetic = {
        "label": "synthetic-shift-fed-reference", "reference_portfolio": REFERENCE,
        "evaluation_set": f"uci-polish-3year-holdout ({len(hold):,} rows, locked)", "shifts": shifts,
        "worst_subsample": {"share": WORST_SUBSAMPLE_SHARE, "metric": {"auc": float(worst.auc), "brier": float(worst.brier),
                                                                       "auc_delta": float(worst.auc - worst.auc_full)}},
        "label_free": {
            "conformal": {"label": "convention", "alpha": CONFORMAL_ALPHA, "target_coverage": float(pooled.target), "coverage": float(pooled.coverage),
                          "binomial_p_value": float(pooled.p_value_binomial), "coverage_by_window": windows},
            "cbpe": {"label": "estimate", "estimated_auc": float(est.estimated_auc),
                     "assumptions": [{"id": i, "text": txt} for i, txt in ASSUMPTIONS]}}}
    outputs = {"kind": "shift", "dataset_id": "fed-2025-corporate", "model_dataset": "uci-polish", "sgcd_notice": None,
               "parameters": parameters_block(), "fairness_battery": None,
               "impact_detail": {"label": "decision-flip", "cutoff": impact_cutoff(),
                                 "rows": [{"shift_id": s["shift_id"], "flip_share": s["flip_share"], "n_decisions": int(len(hold))} for s in shifts]},
               "requirements": ["CT-2006", "CT-2007", "CT-2008", "CT-2009", "CT-2022"], "real_drift": drift, "synthetic_shift": synthetic}
    impact = {"decision_flip_share": {"value": max(s["flip_share"] for s in shifts), "unit": "share",
                                      "label": t("Decisions that flip at the stated cut-off, largest over the shifts",
                                                 "Decisiones que cambian en el punto de corte indicado, la mayor entre los desplazamientos")}}
    return {"outputs": outputs, "tests": tests, "impact": impact, "models": [model_id], "anchor_psi": anchor,
            "limits": [("fed-no-outcome", t("The Fed portfolios carry no default outcome and no decision: they fix the size of a synthetic shift and show real drift, "
                                            "and no model is scored on them",
                                            "Las carteras de la Fed no tienen resultado de incumplimiento ni decision: fijan el tamano de un desplazamiento sintetico y "
                                            "muestran deriva real, y ningun modelo se puntua sobre ellas")),
                       ("synthetic-shift", t("The shift is synthetic: a known mean displacement of five features, its size matched to the rating drift of the Fed "
                                            "higher-risk portfolio, with the labels and the concept unchanged",
                                            "El desplazamiento es sintetico: un desplazamiento medio conocido de cinco variables, de tamano igualado a la deriva de "
                                            "calificacion de la cartera de mayor riesgo de la Fed, con las etiquetas y el concepto sin cambio"))]}


def _psi_row(base: np.ndarray, cur: np.ndarray, model_id: str):
    from riskvalidation.validation.stability import bin_counts, quantile_edges, stability_psi

    edges = quantile_edges(base, 10)
    return stability_psi(bin_counts(base, edges).astype(float), bin_counts(cur, edges).astype(float), model_id=model_id)
