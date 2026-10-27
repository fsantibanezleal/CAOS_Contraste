"""The SGCD shock variants, seen (T1 to T3, F1 and F2) and held-out (T4 to T6, F4): the shipped shocks as shipped and Contraste's own
application of each family to the structured view, each by performance, drift, data quality and attribution stability.

The model is the P4 LightGBM rung fitted on the setup and adaptation batches (``data.load_sgcd``); the evaluation set is the locked
holdout of the group's three test batches. The reference of the drift is the setup batches (S1 to S4, no shocks). A model that reads
the structured view alone is reached by the shipped shocks through F1 only, so the applied block is where the other families act.
Every statistic and test is a ``riskvalidation`` call.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from . import fits, ops, sgcd, shocks
from .conv import REJECT_SHARE, impact_cutoff, parameters_block, sgcd_notice, t
from . import data
from .data import Frame

GROUPS = {"seen": sgcd.SEEN_BATCHES, "held-out": sgcd.HELD_OUT_BATCHES}
SHIPPED_SHOCKS = {"seen": ("F0", "F1", "F2", "F3"), "held-out": ("F0", "F4")}
APPLIED_SHOCKS = {"seen": ("F0", "F1", "F2", "F3", "numeric-noise"), "held-out": ("F0", "F4", "numeric-noise")}
N_CHECK_FEATURES = len(sgcd.feature_names())


#: the design limit of the SGCD variants; the Spanish names the benchmark and the scoring in Spanish (U16-R3 c20 B7)
SGCD_LIMIT = t("SGCD is a research benchmark and must not be used for real-world credit scoring; nothing here scores a person",
               "SGCD es un conjunto de referencia de investigación y no debe usarse para la calificación de crédito real; nada aquí puntúa a una persona")


def _levels(ref: pd.Series, cur: pd.Series) -> list[str]:
    return sorted({"<missing>" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v) for v in (*ref, *cur)})


def counts(ref: pd.Series, cur: pd.Series, bins: int, categorical: bool) -> tuple[np.ndarray, np.ndarray]:
    """Counts of a reference and a current column on bins fixed from the reference: its quantiles for a number, the codes (a missing
    value as its own level) for a category."""
    from riskvalidation.validation.stability import bin_counts, quantile_edges

    if not categorical:
        a, b = ref.to_numpy(dtype=float), cur.to_numpy(dtype=float)
        a, b = a[~np.isnan(a)], b[~np.isnan(b)]
        edges = quantile_edges(a, bins)
        if len(edges) >= 3:
            return bin_counts(a, edges).astype(float), bin_counts(b, edges).astype(float)
        categorical = True
        ref, cur = pd.Series(a), pd.Series(b)
    lv = _levels(ref, cur)

    def tally(s: pd.Series) -> np.ndarray:
        keys = ["<missing>" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v) for v in s]
        return np.array([sum(1 for k in keys if k == level) for level in lv], dtype=float)

    return tally(ref), tally(cur)


def drift_block(ref: pd.DataFrame, cur: pd.DataFrame, features: tuple[str, ...], categorical: tuple[str, ...], pd_ref: np.ndarray,
                pd_cur: np.ndarray, model_id: str, segment: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The drift block of a row: per input the PSI on ten reference-quantile bins, the CSI on five (the engine documents the CSI as the PSI
    of one characteristic; the two bin sets are the convention that tells them apart) and the chi-square p-value; the maxima; and the
    chi-square p-value of the score on its reference deciles. The engine rows of the score are returned beside it."""
    from riskvalidation.validation import stability as st

    variables = []
    for f in features:
        cat = f in categorical
        e10, a10 = counts(ref[f], cur[f], 10, cat)
        e5, a5 = counts(ref[f], cur[f], 5, cat)
        psi = st.stability_psi(e10, a10).metric
        csi = st.stability_csi(e5, a5).metric
        try:
            chi = st.stability_chi2(e10, a10).p_value
        except ValueError:
            chi = None
        variables.append({"name": f, "psi": float(psi), "csi": float(csi), "chi2_p_value": None if chi is None else float(chi)})
    edges = st.quantile_edges(pd_ref, 10)
    e, a = st.bin_counts(pd_ref, edges).astype(float), st.bin_counts(pd_cur, edges).astype(float)
    psi_row = ops.row(st.stability_psi(e, a, model_id=model_id, segment=segment), segment=None)
    chi_row = ops.row(st.stability_chi2(e, a, model_id=model_id, segment=segment), segment=None)
    block = {"psi_max": max(v["psi"] for v in variables), "csi_max": max(v["csi"] for v in variables),
             "chi2_p_value": chi_row["p_value"], "variables": variables}
    return block, [psi_row, chi_row]


def quality(X: pd.DataFrame, features: tuple[str, ...], pairs: tuple[list[str], list[str]] | None, model_id: str, segment: str):
    """The completeness of the model inputs of a row, the consistency of the structured and the text view where the text is read, and the
    engine's data-quality row over them."""
    from riskvalidation.ml import dataquality as dq
    from riskvalidation.validation import ml as mlv

    miss = X[list(features)].isna().to_numpy()
    cells = np.where(miss, np.nan, 0.0)
    counts_ = [dq.dq_completeness(cells)]
    consistency: float | None = None
    if pairs is not None and pairs[0]:
        c = dq.dq_consistency(pairs[0], pairs[1])
        counts_.append(c)
        consistency = float(c.share_ok)
    block = {"completeness": float(counts_[0].share_ok), "consistency": consistency}
    return block, ops.row(mlv.data_quality(model_id, counts_), segment=segment)


class Context:
    """What every row of one document shares: the model, the setup reference and the baseline attribution."""

    def __init__(self, frame: Frame, rung: Any, ds: sgcd.Dataset, codebook: dict[str, dict[str, str]], group: str) -> None:
        self.frame, self.rung, self.ds, self.codebook, self.group = frame, rung, ds, codebook, group
        self.model_id = fits.rung_id("P4-lightgbm", frame)
        self.X = frame.X
        setup = frame.X["stage"] == "setup"
        self.X_setup = frame.X.loc[setup]
        self.pd_setup = rung.pd(self.X_setup)
        batches = GROUPS[group]
        self.in_group = frame.X["batch"].isin(batches).to_numpy()
        self.by_id = {r.id: r for r in ds.records}
        base = self.in_group & (frame.X["shock"] == "F0").to_numpy()
        self.base_ix = np.flatnonzero(base)
        data.assert_evaluation_only(frame, self.base_ix)       # the shocks below touch these rows only
        self.y = frame.y
        self.pd_base = rung.pd(frame.X.iloc[self.base_ix])
        self.base_auc = ops.auc_brier(self.pd_base, self.y[self.base_ix])[0]
        self.phi_base, _, _ = fits.shap_values(rung, frame.X.iloc[self.base_ix])
        self.imp_base = fits.mean_abs(self.phi_base)
        self.cut = fits.cutoff(self.pd_base, REJECT_SHARE)
        self.modal = shocks.modal_codes(self.X_setup)

    def correlation(self, X: pd.DataFrame) -> float | None:
        from riskvalidation.ml.explanations import rank_agreement

        phi, _, _ = fits.shap_values(self.rung, X)
        try:
            return float(rank_agreement(self.imp_base, fits.mean_abs(phi)))
        except ValueError:
            return None


def make_row(ctx: Context, shock_id: str, batches: list[str], X: pd.DataFrame, y: np.ndarray, n_reaching: int, records: list[sgcd.Record] | None,
             block: str) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray]:
    pd_ = ctx.rung.pd(X)
    seg = f"{block}:{shock_id}"
    drift, rows = drift_block(ctx.X_setup, X, ctx.frame.features, ctx.frame.categorical, ctx.pd_setup, pd_, ctx.model_id, seg)
    pairs = sgcd.consistency_pairs(records, ctx.codebook) if records is not None else None
    dq_block, dq_row = quality(X, ctx.frame.features, pairs, ctx.model_id, seg)
    out = {"shock_id": shock_id, "batches": batches, "n_records": int(len(X)), "n_reaching_structured_view": int(n_reaching),
           "performance": ops.metric_block(pd_, y, ctx.base_auc), "drift": drift, "data_quality": dq_block,
           "attribution_rank_correlation": ctx.correlation(X)}
    return out, [*rows, dq_row], pd_


def shipped_block(ctx: Context) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    X, y = ctx.X, ctx.y
    rows, tests = [], []
    batches = list(GROUPS[ctx.group])
    shock = X["shock"].to_numpy()
    cosm = X["cosmetic"].to_numpy()
    for sid in SHIPPED_SHOCKS[ctx.group]:
        sel = ctx.in_group & ((shock == sid) if sid != "F3" else cosm)
        ix = np.flatnonzero(sel)
        if len(ix) < 5 or len(set(y[ix])) < 2:
            continue                                   # no AUC without both classes: nothing is written for the row
        recs = [ctx.by_id[i] for i in X["id"].iloc[ix]]
        reaching = sum(1 for r in recs if any(v is None for v in r.view.values()))
        r, t_, _ = make_row(ctx, sid, batches, X.iloc[ix], y[ix], reaching, recs, "shipped")
        rows.append(r)
        tests.extend(t_)
    return {"label": "shipped", "rows": rows, "parameters_source": None}, tests


def applied_block(ctx: Context) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    meta = ctx.ds.metadata
    base = ctx.X.iloc[ctx.base_ix].reset_index(drop=True)
    yb = ctx.y[ctx.base_ix]
    batches = list(GROUPS[ctx.group])
    rows, tests, flips = [], [], []
    for sid in APPLIED_SHOCKS[ctx.group]:
        if sid == "F0":
            r, t_, _ = make_row(ctx, "F0", batches, base, yb, 0, None, "applied")
        else:
            ap = shocks.apply(sid, base, meta, ctx.group, modal=ctx.modal)
            r, t_, pd_s = make_row(ctx, sid, batches, ap.X, yb, ap.n_changed, None, "applied")
            flips.append({"shift_id": f"applied-{sid}", "flip_share": fits.flip_share(ctx.pd_base, pd_s, ctx.cut), "n_decisions": int(len(base))})
        rows.append(r)
        tests.extend(t_)
    return {"label": "contraste-applied", "rows": rows, "parameters_source": "SGCDataset_metadata.json, seed 42"}, tests, flips


def build(frame: Frame, rungs: dict[str, Any], ds: sgcd.Dataset, codebook: dict[str, dict[str, str]], group: str) -> dict[str, Any]:
    """The shock document of a group (``seen`` or ``held-out``): outputs, engine rows, impact and the models it validates."""
    from riskvalidation.ml import explanations as ex
    from riskvalidation.ml import generalisation as gen
    from riskvalidation.validation import ml as mlv

    data.assert_locked(frame)
    rung = rungs["P4-lightgbm"]
    ctx = Context(frame, rung, ds, codebook, group)
    shipped, t1 = shipped_block(ctx)
    applied, t2, flips = applied_block(ctx)
    Xh, yh = frame.part("hold")
    Xt, yt = frame.part("train")
    auc_tr, auc_ho = ops.auc_brier(rung.pd(Xt), yt)[0], ops.auc_brier(rung.pd(Xh), yh)[0]
    phi, base_v, margin = fits.shap_values(rung, Xh)
    tests = [*t1, *t2,
             ops.row(mlv.overfit(ctx.model_id, gen.overfit_gap(auc_tr, auc_ho, 0.05)), segment="train-vs-holdout"),
             ops.row(mlv.additivity(ctx.model_id, ex.shapley_additivity_gap(margin, base_v, phi)), segment="holdout")]
    outputs = {"kind": "shock", "dataset_id": "sgcd", "model_dataset": "uci-german", "sgcd_notice": sgcd_notice(),
               "parameters": parameters_block(), "fairness_battery": None,
               "impact_detail": {"label": "decision-flip", "cutoff": impact_cutoff(), "rows": flips},
               "requirements": ["CT-2001", "CT-2002", "CT-2003", "CT-2004", "CT-2005", "CT-2022"],
               "seen_or_held_out": group, "model_view": "json_view", "shipped": shipped, "applied": applied}
    worst = max(f["flip_share"] for f in flips)
    impact = {"decision_flip_share": {"value": worst, "unit": "share",
                                      "label": t("Decisions that flip at the stated cut-off, largest over the applied shocks",
                                                 "Decisiones que cambian en el punto de corte indicado, la mayor entre los choques aplicados")}}
    return {"outputs": outputs, "tests": tests, "impact": impact, "models": [fits.rung_id("P4-lightgbm", frame)],
            "limits": [("sgcd-not-for-scoring", SGCD_LIMIT),
                       ("small-groups", t("Each shock row holds 30 to 90 records, so its AUC carries a wide interval; the rows show the direction, not a precise size",
                                         "Cada fila de choque tiene de 30 a 90 registros, de modo que su AUC tiene un intervalo ancho; las filas muestran la dirección, no un tamaño preciso"))]}
