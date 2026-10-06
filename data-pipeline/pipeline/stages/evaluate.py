"""Stage evaluate: the validation battery and the outputs the web draws, for one rung on one evaluation set.

The tests are riskvalidation's (dossier 06 C.1 to C.4), run under its versioned policy; nothing here re-implements
a statistic. What this stage adds is the evaluation design: which sample each test reads, which reference each
stability test compares against, and the curves and tables the views draw.

- Discrimination: AUC with its DeLong variance; the ECB comparison against the AUC at initial validation (here the
  AUC on the calibration slice, the first out-of-sample measurement the development made); DeLong paired against
  the champion (the scorecard, P1); KS.
- Calibration, on the master scale (core/calibration.py): Jeffreys per grade and for the portfolio, binomial and
  Vasicek-adjusted binomial for the portfolio with the QRRE asset correlation R = 0.04 (CRE31.15), chi-square over
  grades; at obligor level Hosmer-Lemeshow, Spiegelhalter, Brier with the Murphy decomposition, ECE.
- Stability: PSI of the PD against the training slice (ten bins on the training quantiles, the Yurdakul-Naranjo
  benchmark beside the conventional bands), grade concentration (HHI) against the calibration slice; CSI of every
  input is population-level and computed once per evaluation set.

Segments: a test on the whole evaluation set is reported for the segment ``portfolio``; a grade-level Jeffreys test
for its grade (``G01`` to ``G12``); a CSI row for ``characteristic:<name>``, with no model (it reads the inputs, not a
rung). The variant is the artifact itself.

Not run for C01, because the data cannot support them: migration matrices and their tests (one snapshot), the
multi-period normal and traffic-lights tests (one period).
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ..core.calibration import GRADES, grade_of, grade_table, reliability

QRRE_RHO = 0.04  # CRE31.15: asset correlation of qualifying revolving retail exposures
PORTFOLIO = "portfolio"


def _rows(results) -> list[dict[str, Any]]:
    return [r.to_dict() for r in (results if isinstance(results, list) else [results])]


def battery(
    rung: str,
    pd_eval: np.ndarray,
    y_eval: np.ndarray,
    *,
    pd_train: np.ndarray | None,
    pd_cal: np.ndarray | None,
    y_cal: np.ndarray | None,
    champion_pd: np.ndarray | None,
    policy=None,
) -> list[dict[str, Any]]:
    """The battery for one rung on one evaluation set, in a fixed order. The references are optional for a sample
    that has none (a reader's own scored sample without its development sample): without ``pd_train`` the PSI is not
    run; without ``pd_cal`` and ``y_cal`` neither the AUC against the initial validation nor the grade
    concentration."""
    from riskvalidation.validation import calibration as cal
    from riskvalidation.validation import discrimination as disc
    from riskvalidation.validation import rating_system as rs
    from riskvalidation.validation import stability as st

    y_eval = np.asarray(y_eval, dtype=int)
    kw = {"policy": policy, "model_id": rung, "segment": PORTFOLIO}
    rows: list[dict[str, Any]] = []
    constant = float(np.ptp(pd_eval)) == 0.0
    rows += _rows(disc.disc_auc(pd_eval, y_eval, **kw))
    has_initial = pd_cal is not None and y_cal is not None
    if not constant:
        if has_initial:
            auc_initial, *_ = disc.auc_with_variance(pd_cal, np.asarray(y_cal, dtype=int))
            rows += _rows(disc.disc_auc_vs_initial(float(auc_initial), pd_eval, y_eval, **kw))
        if champion_pd is not None:
            rows += _rows(disc.disc_delong(pd_eval, champion_pd, y_eval, **kw))
        rows += _rows(disc.disc_ks(pd_eval, y_eval, **kw))
    table = [g for g in grade_table(pd_eval, y_eval) if g["n"] > 0]
    n = [g["n"] for g in table]
    d = [g["d"] for g in table]
    p = [g["pd"] for g in table]
    # one Jeffreys test per non-empty grade and one for the portfolio (the engine adds the portfolio row)
    rows += _rows(cal.pd_jeffreys_grades(n, d, p, grades=[g["grade"] for g in table], policy=policy, model_id=rung))
    n_all, d_all, p_all = int(len(y_eval)), int(y_eval.sum()), float(np.mean(pd_eval))
    rows += _rows(cal.pd_binomial(n_all, d_all, p_all, **kw))
    rows += _rows(cal.pd_binomial_vasicek(n_all, d_all, p_all, QRRE_RHO, **kw))
    if len(table) > 1:
        rows += _rows(cal.pd_chi2_grades(n, d, p, **kw))
    if not constant:
        rows += _rows(cal.pd_hosmer_lemeshow(y_eval, pd_eval, **kw))
    rows += _rows(cal.pd_spiegelhalter(y_eval, pd_eval, **kw))
    grades_eval = [GRADES[k] for k in grade_of(pd_eval)]
    rows += _rows(cal.pd_brier(y_eval, pd_eval, groups=grades_eval, **kw))
    rows += _rows(cal.pd_ece(y_eval, pd_eval, **kw))
    if not constant and pd_train is not None:
        edges = st.quantile_edges(pd_train, 10)
        rows += _rows(st.stability_psi(st.bin_counts(pd_train, edges), st.bin_counts(pd_eval, edges), **kw))
    if has_initial:
        f_cur = np.bincount(grade_of(pd_eval), minlength=len(GRADES)) / len(pd_eval)
        f_ini = np.bincount(grade_of(pd_cal), minlength=len(GRADES)) / len(pd_cal)
        rows += _rows(rs.rating_hhi(f_cur, f_ini, **kw))
    return rows


def csi_rows(X_train, X_eval, features: list[str], categorical: tuple[str, ...], *,
             policy=None) -> list[dict[str, Any]]:
    """CSI of every input against the training slice: ten training-quantile bins, or the categories."""
    from riskvalidation.validation import stability as st

    rows = []
    for f in features:
        if f in categorical:
            a = X_train[f].astype(str).to_numpy()
            b = X_eval[f].astype(str).to_numpy()
        else:
            a = X_train[f].to_numpy(dtype=float)
            b = X_eval[f].to_numpy(dtype=float)
        if f in categorical or len(np.unique(a)) <= 12:
            cats = np.unique(np.concatenate([a, b]))
            e = np.array([(a == c).sum() for c in cats], dtype=float)
            c_ = np.array([(b == c).sum() for c in cats], dtype=float)
        else:
            edges = np.unique(st.quantile_edges(a, 10))
            e, c_ = st.bin_counts(a, edges), st.bin_counts(b, edges)
        res = st.stability_csi(e, c_, policy=policy, model_id=None, segment=f"characteristic:{f}").to_dict()
        rows.append(res)
    return rows


def _decimate(x: np.ndarray, y: np.ndarray, n: int = 101) -> tuple[list[float], list[float]]:
    if len(x) <= n:
        return [round(float(v), 6) for v in x], [round(float(v), 6) for v in y]
    idx = np.unique(np.round(np.linspace(0, len(x) - 1, n)).astype(int))
    return [round(float(v), 6) for v in x[idx]], [round(float(v), 6) for v in y[idx]]


def roc_points(pd_eval: np.ndarray, y_eval: np.ndarray, n: int = 101) -> dict[str, list[float]]:
    """The ROC decimated to about n points, from the ranking by PD (riskier first)."""
    y = np.asarray(y_eval, dtype=int)
    order = np.argsort(-np.asarray(pd_eval, dtype=float), kind="stable")
    ys = y[order]
    tpr = np.concatenate([[0], np.cumsum(ys)]) / max(1, y.sum())
    fpr = np.concatenate([[0], np.cumsum(1 - ys)]) / max(1, len(y) - y.sum())
    fx, ty = _decimate(fpr, tpr, n)
    return {"fpr": fx, "tpr": ty}


def curves(pd_eval: np.ndarray, y_eval: np.ndarray) -> dict[str, Any]:
    """ROC and CAP, decimated to about 101 points, from the ranking by PD (riskier first)."""
    y = np.asarray(y_eval, dtype=int)
    order = np.argsort(-np.asarray(pd_eval, dtype=float), kind="stable")
    ys = y[order]
    tp = np.concatenate([[0], np.cumsum(ys)])
    fp = np.concatenate([[0], np.cumsum(1 - ys)])
    tpr = tp / max(1, y.sum())
    fpr = fp / max(1, len(y) - y.sum())
    pop = np.arange(len(ys) + 1) / len(ys)
    roc_x, roc_y = _decimate(fpr, tpr)
    cap_x, cap_y = _decimate(pop, tpr)
    return {"roc": {"fpr": roc_x, "tpr": roc_y}, "cap": {"population": cap_x, "defaults": cap_y,
                                                         "default_rate": float(y.mean())}}


def distribution(pd_eval: np.ndarray, y_eval: np.ndarray, bins: int = 30) -> dict[str, Any]:
    """Histogram of log10 PD for defaulters and non-defaulters on shared edges."""
    lp = np.log10(np.clip(np.asarray(pd_eval, dtype=float), 1e-6, 1.0))
    y = np.asarray(y_eval, dtype=int)
    lo, hi = float(lp.min()), float(lp.max())
    if hi - lo < 1e-9:
        hi = lo + 1e-3
    edges = np.linspace(lo, hi, bins + 1)
    return {"log10_pd_edges": [round(float(e), 5) for e in edges],
            "defaulters": np.histogram(lp[y == 1], edges)[0].tolist(),
            "non_defaulters": np.histogram(lp[y == 0], edges)[0].tolist()}


def cutoff_curve(pd_eval: np.ndarray, y_eval: np.ndarray, ead: np.ndarray, points: int = 51,
                 sums: dict[str, dict[str, np.ndarray]] | None = None) -> dict[str, Any]:
    """Approve every applicant at or below a PD cut-off: per cut-off on the PD quantiles, the approval rate, the bad
    rate among the approved, and the sums of PD x EAD and EAD among the approved (EL = LGD x the first). ``sums``
    adds further per-account amounts summed the same way, unrounded (C01's capital at unit LGD, by regime)."""
    p = np.asarray(pd_eval, dtype=float)
    y = np.asarray(y_eval, dtype=int)
    e = np.asarray(ead, dtype=float)
    cuts = np.unique(np.quantile(p, np.linspace(0.02, 1.0, points)))
    out: dict[str, Any] = {"cutoff": [], "approval_rate": [], "bad_rate": [], "pd_ead": [], "ead": []}
    extra = {key: {name: np.asarray(a, dtype=float) for name, a in by.items()} for key, by in (sums or {}).items()}
    for key, by in extra.items():
        out[key] = {name: [] for name in by}
    for c in cuts:
        m = p <= c
        out["cutoff"].append(round(float(c), 6))
        out["approval_rate"].append(round(float(m.mean()), 6))
        out["bad_rate"].append(round(float(y[m].mean()) if m.any() else 0.0, 6))
        out["pd_ead"].append(round(float((p[m] * e[m]).sum()), 2))
        out["ead"].append(round(float(e[m].sum()), 2))
        for key, by in extra.items():
            for name, a in by.items():
                out[key][name].append(float(a[m].sum()))
    return out


def outputs(pd_eval: np.ndarray, y_eval: np.ndarray, *, ead: np.ndarray, pd_raw: np.ndarray | None = None,
            sums: dict[str, dict[str, np.ndarray]] | None = None) -> dict:
    out = {"grades": grade_table(pd_eval, y_eval), "reliability": reliability(pd_eval, y_eval),
           **curves(pd_eval, y_eval), "distribution": distribution(pd_eval, y_eval),
           "cutoff": cutoff_curve(pd_eval, y_eval, ead, sums=sums)}
    # the reliability of the raw score, before the calibration map; None for a rung without one
    out["reliability_raw"] = reliability(pd_raw, y_eval) if pd_raw is not None else None
    return out
