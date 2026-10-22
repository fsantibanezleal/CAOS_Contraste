"""One C08 variant (CT-904 to CT-912): a test default cohort, the ladder trained on what closed before it, and the blocks of
the ``c08-outputs`` document.

Every figure is the engine's or an arrangement of the engine's: the fits are ``riskvalidation.lgd_ead.lgd_models``, the
distribution ``workout.lgd_distribution``, the floors ``floors.apply_lgd_floor``, the tests
``riskvalidation.validation.lgd_ead``. This module selects the rows of each step, carries the range flags and writes the
bilingual labels.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.lgd_ead import floors as rv_floors
from riskvalidation.lgd_ead import workout as rv_work
from riskvalidation.validation import lgd_ead as rv_val

from ...core.text import number
from . import build as bd
from .cutoff import cutoff_for, open_workout_mask, training_mask
from .downturn import DownturnPlan
from .ladder import EPSILONS, RUNGS, Ladder, RungFit, fit_ladder
from .panel import COHORTS, FEATURE_NAMES, Defaults, cohort_bounds

N_MIN_TEST = 30


@dataclass(frozen=True)
class VariantResult:
    variant_id: str
    cohort_id: str
    cutoff: str
    ladder: Ladder
    outputs: dict[str, Any]
    tests: list[dict[str, Any]]
    impact: dict[str, Any]
    findings: list[dict[str, Any]]
    n_train: int
    n_open: int
    values: dict[str, float]


def _gap(realised: np.ndarray, predicted: np.ndarray) -> float:
    return float(realised.mean() - predicted.mean())


def _not_evaluated(test_fn_name: str, rung: RungFit, segment: str | None) -> dict[str, Any]:
    """The engine's own not evaluated row for a test of a rung that was not fitted: the engine called with no data, then the
    reason of the rung written in its notes (no number, never a stand-in)."""
    empty = np.array([], dtype=float)
    fn = getattr(rv_val, test_fn_name)
    if test_fn_name == "lgd_calibration_over_time":
        res = fn(empty, empty, np.array([], dtype=np.int64), model_id=rung.rung_id)
    else:
        res = fn(empty, empty, segment=segment, model_id=rung.rung_id)
    res = dataclasses.replace(res, notes=f"rung {rung.rung_id} not evaluated: {rung.reason}")
    return res.to_dict()


def reference_rung(ladder: Ladder) -> RungFit:
    for rid in bd.REFERENCE_RUNGS:
        if ladder.rungs[rid].evaluated:
            return ladder.rungs[rid]
    raise ValueError(f"no reference rung is fitted at the cutoff {ladder.cutoff}: " +
                     "; ".join(f"{rid}: {ladder.rungs[rid].reason}" for rid in bd.REFERENCE_RUNGS))


def bake_variant(defaults: Defaults, cohort_id: str, seed: int, down: DownturnPlan, freddie_reason: str,
                 *, ladder: Ladder | None = None) -> VariantResult:
    lo, hi = cohort_bounds(cohort_id)
    cutoff = cutoff_for(lo)
    train_mask = training_mask(defaults, cutoff)
    train = defaults.take(train_mask)
    if ladder is None:
        ladder = fit_ladder(train.design(), train.y, cutoff, seed)
    n_open = int(open_workout_mask(defaults, cutoff).sum())
    last = COHORTS[-1][2]
    oot = defaults.take((defaults.year >= lo) & (defaults.year <= last))
    test_mask = (oot.year >= lo) & (oot.year <= hi)
    test = oot.take(test_mask)
    if test.n < N_MIN_TEST:
        raise ValueError(f"cohort {cohort_id}: {test.n} defaults, fewer than the {N_MIN_TEST} a test needs")
    x_oot = oot.design()
    y_oot, y_test = oot.y, oot.y[test_mask]
    preds: dict[str, np.ndarray] = {rid: ladder.predict(ladder.rungs[rid], x_oot)
                                    for rid, _ in RUNGS if ladder.rungs[rid].evaluated}
    seg = f"cohort-{cohort_id}"
    tests: list[dict[str, Any]] = []
    comparison, rvp, buckets = [], [], []
    for rid, _ in RUNGS:
        rung = ladder.rungs[rid]
        if not rung.evaluated:
            tests += [_not_evaluated("lgd_calibration_by_segment", rung, seg), _not_evaluated("lgd_discrimination", rung, seg),
                      _not_evaluated("lgd_calibration_over_time", rung, None)]
            continue
        p_all = preds[rid]
        p = p_all[test_mask]
        cal = rv_val.lgd_calibration_by_segment(y_test, p, segment=seg, model_id=rid)
        disc = rv_val.lgd_discrimination(y_test, p, segment=seg, model_id=rid)
        tests += [cal.to_dict(), disc.to_dict(),
                  rv_val.lgd_calibration_over_time(y_oot, p_all, oot.year, model_id=rid).to_dict()]
        sse = float(((y_test - p) ** 2).sum())
        sst = float(((y_test - y_test.mean()) ** 2).sum())
        r2 = 1.0 - sse / sst if sst > 0 else None
        rho = disc.statistic if disc.light.value != "not_evaluated" else None
        why = None
        if r2 is None:
            why = "the realised LGD of the cohort has no spread: R2 is undefined"
        elif rho is None:
            why = "the rank statistic is undefined: " + disc.notes
        comparison.append({"rung_id": rid, "r2": r2, "rmse": float(np.sqrt(np.mean((y_test - p) ** 2))),
                           "mae": float(np.mean(np.abs(y_test - p))), "spearman": None if rho is None else float(rho),
                           "calibration_gap": _gap(y_test, p), "reason": why})
        for cid, clo, chi in COHORTS:
            if clo < lo:
                continue
            k = (oot.year >= clo) & (oot.year <= chi)
            if not k.any():
                continue
            yr, pr = y_oot[k], p_all[k]
            c = rv_val.lgd_calibration_by_segment(yr, pr, segment=f"cohort-{cid}", model_id=rid)
            pm = float(pr.mean())
            if c.light.value == "not_evaluated":
                continue  # fewer than two defaults in the cohort: no interval, and no row with a stand-in
            lo_ci, hi_ci = pm + float(c.extras["ci_low"]), pm + float(c.extras["ci_high"])
            rvp.append({"rung_id": rid, "cohort_id": cid, "n": int(k.sum()), "realised": bd.lgd(yr.mean()),
                        "predicted": bd.lgd_pred(pm), "ci_low": lo_ci, "ci_high": hi_ci, "gap": _gap(yr, pr)})
        order = np.argsort(p, kind="stable")
        for b, idx in enumerate(np.array_split(order, bd.N_BUCKETS), start=1):
            buckets.append({"rung_id": rid, "bucket": b, "n": int(len(idx)), "predicted": bd.lgd_pred(p[idx].mean()),
                            "realised": bd.lgd(y_test[idx].mean())})
    if not comparison:
        raise ValueError(f"cohort {cohort_id}: no rung is fitted, the document has nothing to compare")
    endpoint = []
    for eps in EPSILONS:
        b = ladder.beta_by_epsilon.get(eps)
        if b is None or not b.evaluated:
            continue
        pb = ladder.predict(b, test.design())
        endpoint.append({"rung_id": "L3-beta", "epsilon": float(eps), "mean_predicted": bd.lgd_pred(pb.mean()),
                         "rmse": float(np.sqrt(np.mean((y_test - pb) ** 2)))})
    if len(endpoint) < 2:
        raise ValueError(f"cohort {cohort_id}: the beta rung fitted at {len(endpoint)} epsilon(s); the sensitivity needs two")
    tests += [dict(t) for t in down.tests]
    # distribution of the realised proxy of the test cohort
    dist = rv_work.lgd_distribution(y_test, np.linspace(0.0, 1.0, bd.N_BINS + 1))
    n = dist.n
    edges = dist.edges
    flag = bd.lgd
    distribution = {
        "n": int(n), "treatment": "flagged-not-clipped",
        "bins": [{"lower": float(edges[i]), "upper": float(edges[i + 1]), "n": int(dist.counts[i]), "share": float(dist.counts[i] / n)}
                 for i in range(len(dist.counts))],
        "mass_at_zero": {"n": int(dist.mass_zero), "share": float(dist.mass_zero / n)},
        "mass_at_one": {"n": int(dist.mass_one), "share": float(dist.mass_one / n)},
        "n_below_zero": int(dist.n_below_zero), "share_below_zero": float(dist.n_below_zero / n),
        "n_above_one": int(dist.n_above_one), "share_above_one": float(dist.n_above_one / n),
        "lowest": flag(y_test.min()), "highest": flag(y_test.max()), "mean": flag(y_test.mean()), "median": flag(np.median(y_test)),
    }
    # floors
    ref = reference_rung(ladder)
    p_ref = preds[ref.rung_id][test_mask]
    seg_idx = bd.segment_of(test.revolver, test.term)
    floor_rows = []
    for k, (sid, fid, _en, _es) in enumerate(bd.SEGMENTS):
        m = seg_idx == k
        if not m.any():
            continue
        value, reference = bd.floor_value(fid)
        bite = rv_floors.apply_lgd_floor(p_ref[m], value)
        floor_rows.append({"segment_id": sid, "floor_id": fid, "floor": value, "reference": reference, "n": int(m.sum()),
                           "share_binding": float(bite.share_binding), "mean_before": bd.lgd_pred(bite.mean_before),
                           "mean_after": bd.lgd_pred(bite.mean_after), "uplift": float(max(bite.uplift, 0.0))})
    floors_bite = {
        "regime": bd.REGIME, "rows": floor_rows,
        "note": bd.t(
            f"Floors of dossier 01 A.5 applied to the {ref.rung_id} predictions of the cohort, by segment; the SBA file has no "
            "collateral field, so the collateral is inferred from the term and the revolving status (lines of credit and loans up to "
            "7 years as unsecured, 7 to 20 years as other physical, 20 years or more as real estate). The bite is the mean uplift.",
            f"Pisos del dossier 01 A.5 aplicados a las predicciones de {ref.rung_id} de la cohorte, por segmento; el archivo SBA no "
            "tiene campo de garantía, de modo que la garantía se infiere del plazo y de si es línea rotativa (líneas y préstamos de "
            "hasta 7 años como sin garantía, de 7 a 20 años como otra física, de 20 años o más como inmobiliaria). El efecto es el "
            "alza media."),
    }
    exposure = {"currency": bd.CURRENCY, "gross_charge_off_total": float(test.chargeoff_amount.sum()),
                "gross_approval_total": float(test.gross_approval.sum())}
    outputs = {
        "kind": "default-cohort", "currency": bd.CURRENCY, "cohort": bd.cohort_block(cohort_id), "lgd_proxy": bd.lgd_proxy_block(),
        "data_status": bd.data_status_block(freddie_reason),
        "training": {"cutoff_date": cutoff, "n_defaults": int(train.n), "n_open_workouts_excluded": n_open,
                     "closure_rule": bd.closure_rule()},
        "workout": bd.workout_block(), "exposure": exposure, "lgd_distribution": distribution, "rung_comparison": comparison,
        "realised_vs_predicted": rvp, "calibration_by_bucket": buckets, "endpoint_sensitivity": endpoint,
        "downturn": {"period": dict(down.period), "approach": dict(down.approach), "rows": [dict(r) for r in down.rows],
                     "coverage": dict(down.coverage)},
        "floors_bite": floors_bite,
    }
    cal_ref = next(t for t in tests if t["test_id"] == "lgd_ead.lgd_calibration_by_segment" and t["model_id"] == ref.rung_id
                   and t["segment"] == seg)
    impact = {
        "mean_lgd_proxy": {"value": float(y_test.mean()), "unit": "share", "label": bd.t("Mean LGD proxy of the cohort", "LGD proxy media de la cohorte")},
        "calibration_gap_reference": {"value": comparison[[c["rung_id"] for c in comparison].index(ref.rung_id)]["calibration_gap"],
                                      "unit": "share", "label": bd.t(f"Mean realised minus mean predicted LGD, {ref.rung_id}",
                                                                      f"LGD realizada media menos predicha media, {ref.rung_id}")},
        "downturn_add_on": {"value": float(down.downturn - down.long_run), "unit": "share",
                            "label": bd.t("Downturn add-on to the long-run LGD", "Ajuste de recesión sobre la LGD de largo plazo")},
    }
    findings = _findings(cal_ref, ref.rung_id, seg, down)
    values = {f"mean-proxy@{cohort_id}": float(y_test.mean())}
    return VariantResult(bd.variant_id(cohort_id), cohort_id, cutoff, ladder, outputs, tests, impact, findings, int(train.n),
                         n_open, values)


def _findings(cal: dict[str, Any], rung_id: str, seg: str, down: DownturnPlan) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if cal["light"] in ("amber", "red") and cal["metric"] is not None:
        sign_en, sign_es = ("under-predicts", "subestima") if cal["metric"] > 0 else ("over-predicts", "sobreestima")
        out.append({"id": f"F-cal-{rung_id}", "severity": "S2" if cal["light"] == "red" else "S3", "status": "open",
                    "evidence": [f"lgd_ead.lgd_calibration_by_segment@{rung_id}@{seg}"],
                    "title": bd.t(f"{rung_id} {sign_en} the realised LGD proxy of the cohort by {abs(cal['metric']) * 100:.1f} points",
                                  f"{rung_id} {sign_es} la LGD proxy realizada de la cohorte en {number(abs(cal['metric']) * 100, 1, lang='es')} puntos")})
    uncovered = [r for r in down.rows if not r["covered"]]
    if uncovered:
        ids = ", ".join(r["cohort_id"] for r in uncovered)
        out.append({"id": "F-downturn-coverage", "severity": "S3", "status": "open", "evidence": ["lgd_ead.downturn_coverage"],
                    "title": bd.t(f"The downturn LGD does not cover the realised loss of the cohorts {ids}",
                                  f"La LGD de recesión no cubre la pérdida realizada de las cohortes {ids}")})
    return out


__all__ = ["bake_variant", "VariantResult", "FEATURE_NAMES", "reference_rung"]
