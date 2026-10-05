"""C01, retail cards PD: champion vs challenger, validated as a model risk function would.

The design is docs/design/features/c01-retail-pd/design.md; the requirements CT-101 to CT-111 hold it. Data: UCI
Default of Credit Card Clients (Taiwan) and, as the small-sample twin, UCI Statlog German Credit (both CC BY 4.0).
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .. import __version__
from ..core import expect as expectations
from ..core import lineage as lin
from ..core.calibration import GRADES, MASTER_SCALE_UPPER
from ..core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ..io import readers
from ..io.formats import write_json
from ..model.ebm import score_logit
from ..stages import evaluate, split
from ..stages.export import write_artifact
from ..stages.ingest import ingest
from . import c01_features as feat
from .c01_ladder import Rung, _t, _v, fit_ladder

CASE_ID = "C01"
SOURCES = ("uci-taiwan", "uci-german")
TAIWAN_ZIP = "default+of+credit+card+clients.zip"
GERMAN_ZIP = "statlog+german+credit+data.zip"
CHAMPION = "P1-scorecard"
CHALLENGER = "P4-lightgbm"
LGD = 0.50  # CRE32.58: the Basel III LGD input floor for QRRE, the stated assumption of the decision impact
APPROVAL = 0.80  # the approval rate at which the champion and the challenger are compared
ENGINES = {"optbinning", "statsmodels", "scikit-learn", "interpret", "lightgbm", "xgboost", "riskvalidation"}
#: the gate's run time: the offline fit and evaluation of a variant takes seconds to minutes, far above the
#: interaction budget, so the artifacts are replayed; the web recomputes only additive scores and policy lights
RUN_MS = 60_000.0

GERMAN_COST = {"bad_accepted": 5.0, "good_rejected": 1.0}  # german.doc, section 8

VARIANTS: tuple[dict[str, Any], ...] = (
    {"id": "holdout", "fit": "taiwan", "truth": "real-outcomes",
     "title": _t("Holdout as observed", "Muestra reservada tal como se observa"), "short": _t("Holdout", "Reservada"),
     "regime": _t("The locked 30% holdout, opened once.", "La muestra reservada del 30%, abierta una sola vez.")},
    {"id": "drift-moderate", "fit": "taiwan", "truth": "synthetic-known-truth",
     "title": _t("Covariate drift, moderate", "Deriva de covariables, moderada"), "short": _t("Drift 0.25", "Deriva 0,25"),
     "regime": _t("Real holdout rows resampled toward recent delinquency, weights exp(0.25 z).",
                  "Filas reales de la muestra reservada remuestreadas hacia mora reciente, pesos exp(0,25 z).")},
    {"id": "drift-severe", "fit": "taiwan", "truth": "synthetic-known-truth",
     "title": _t("Covariate drift, severe", "Deriva de covariables, severa"), "short": _t("Drift 0.6", "Deriva 0,6"),
     "regime": _t("The same shift at exp(0.6 z).", "El mismo desplazamiento con exp(0,6 z).")},
    {"id": "prior-shift", "fit": "taiwan", "truth": "synthetic-known-truth",
     "title": _t("Prior shift x1.5", "Cambio de prior x1,5"), "short": _t("Prior x1.5", "Prior x1,5"),
     "regime": _t("Real holdout rows resampled so the default rate is 1.5 times the observed one.",
                  "Filas reales remuestreadas para que la tasa de incumplimiento sea 1,5 veces la observada.")},
    {"id": "label-noise", "fit": "taiwan", "truth": "synthetic-known-truth",
     "title": _t("Label noise 5%", "Ruido de etiqueta 5%"), "short": _t("Noise 5%", "Ruido 5%"),
     "regime": _t("5% of the holdout labels flipped at random.", "El 5% de las etiquetas de la muestra reservada invertidas al azar.")},
    {"id": "small-sample", "fit": "taiwan-small", "truth": "real-outcomes",
     "title": _t("Small sample (2,000 rows)", "Muestra pequeña (2.000 filas)"), "short": _t("2,000 rows", "2.000 filas"),
     "regime": _t("The ladder retrained on 2,000 training rows, evaluated on the same holdout.",
                  "La escalera reentrenada con 2.000 filas de entrenamiento, evaluada en la misma muestra reservada.")},
    {"id": "german-twin", "fit": "german", "truth": "real-outcomes",
     "title": _t("German Credit twin", "Gemelo German Credit"), "short": _t("German", "Alemán"),
     "regime": _t("The ladder on Statlog German Credit (1,000 applicants), with the TabPFN challenger.",
                  "La escalera sobre Statlog German Credit (1.000 solicitantes), con el retador TabPFN.")},
)

#: what a reader should see, declared before the bake (CT-111); see the design page for each basis
EXPECT: dict[str, tuple[float, float]] = {
    "holdout_default_rate": (0.21, 0.235),          # the dataset's 6,636 defaults in 30,000 (22.12%), stratified
    "auc_P0-constant_holdout": (0.5, 0.5),          # a constant ranks nobody
    "auc_P1-scorecard_holdout": (0.70, 0.82),       # plausibility bounds for a scorecard on this dataset
    "auc_P3-ebm_holdout": (0.70, 0.82),
    "auc_P4-lightgbm_holdout": (0.70, 0.82),
    "psi_P1-scorecard_holdout": (0.0, 0.02),        # same population: E[PSI] = (1/n + 1/m)(B - 1), about 0.0015
    "psi_P1-scorecard_drift-severe": (0.05, 3.0),   # the severe shift must show in the score distribution
    "jeffreys_p_P1-scorecard_prior-shift": (0.0, 0.01),  # 1.5 times the defaults: the PD is underestimated
    "auc_P1-scorecard_german-twin": (0.65, 0.85),
}


_T0 = time.perf_counter()


def _log(msg: str) -> None:
    """Progress on stderr (the bake is long); nothing of it reaches an artifact."""
    print(f"[C01 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


@dataclass
class Fit:
    fit_id: str
    source: str
    X: pd.DataFrame
    y: np.ndarray
    sp: split.Split
    train: np.ndarray
    rungs: dict[str, Rung]
    features: tuple[str, ...]
    categorical: tuple[str, ...]
    ead: np.ndarray
    contract: dict


def _load_taiwan(data_root: Path):
    return ingest(CASE_ID, "uci-taiwan", TAIWAN_ZIP, readers.read_taiwan, data_root=data_root, family="scored_sample",
                  extra_fields=feat.TAIWAN_FIELDS, extra_rules=feat.TAIWAN_RULES)


def _load_german(data_root: Path):
    return ingest(CASE_ID, "uci-german", GERMAN_ZIP, readers.read_german, data_root=data_root, family="scored_sample",
                  extra_fields=feat.GERMAN_FIELDS)


def _fit(fit_id: str, source: str, X: pd.DataFrame, report, *, features, categorical, monotone, seed: int,
         train_n: int | None = None, base_split: split.Split | None = None, with_tabpfn: bool = False,
         ead_col: str) -> Fit:
    y = X["target"].to_numpy(dtype=int)
    sp = base_split if base_split is not None else split.stratified_split(y, seed=seed)
    train = split.subsample(sp.train, y, train_n, seed=seed) if train_n else sp.train
    folds = sp.folds
    if train_n is not None:
        # folds of the subsample: positions into `train`, from the same stratified fold scheme on its labels
        from sklearn.model_selection import RepeatedStratifiedKFold

        rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=seed + 2)
        folds = tuple((a, b) for a, b in rskf.split(train, y[train]))
    Xtr, Xcal = X.iloc[train], X.iloc[sp.calibration]
    _log(f"fit {fit_id}: {len(train):,} training rows, {len(sp.calibration):,} calibration, {len(sp.holdout):,} holdout")
    rungs = fit_ladder(Xtr, y[train], Xcal, y[sp.calibration], folds, features=features, categorical=categorical,
                       monotone=monotone, seed=seed, with_xgboost=fit_id == "taiwan", with_tabpfn=with_tabpfn, log=_log)
    ead = np.clip(X[ead_col].to_numpy(dtype=float), 0.0, None)
    _log(f"fit {fit_id}: {len(rungs)} rungs fitted")
    return Fit(fit_id, source, X, y, sp, train, rungs, tuple(features), tuple(categorical), ead, report.summary())


def _resample(rng: np.random.Generator, n: int, p: np.ndarray) -> np.ndarray:
    return rng.choice(n, size=n, replace=True, p=p / p.sum())


def evaluation_set(fit: Fit, variant: str, *, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Positions into fit.X of the evaluation set, and its labels (label noise changes labels, not rows)."""
    hold = fit.sp.holdout
    y = fit.y[hold].copy()
    rng = np.random.default_rng(seed + 1000 + [v["id"] for v in VARIANTS].index(variant))
    if variant in ("drift-moderate", "drift-severe"):
        lam = 0.25 if variant == "drift-moderate" else 0.6
        x = fit.X["PAY_0"].to_numpy(dtype=float)[hold]
        z = (x - x.mean()) / x.std()
        pick = _resample(rng, len(hold), np.exp(lam * z))
        return hold[pick], y[pick]
    if variant == "prior-shift":
        pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
        n1 = int(round(1.5 * y.mean() * len(y)))
        pick = np.concatenate([rng.choice(pos, n1, replace=True), rng.choice(neg, len(y) - n1, replace=True)])
        pick = np.sort(pick)
        return hold[pick], y[pick]
    if variant == "label-noise":
        flip = rng.choice(len(y), size=int(round(0.05 * len(y))), replace=False)
        y[flip] = 1 - y[flip]
        return hold, y
    return hold, y


def _psi_value(rows: list[dict], rung: str) -> float | None:
    for r in rows:
        if r["test_id"] == "stability.psi" and r["model_id"] == rung:
            return r["metric"] if r["metric"] is not None else r["statistic"]
    return None


def _p(rows: list[dict], test_id: str, rung: str) -> float | None:
    for r in rows:
        if r["test_id"] == test_id and r["model_id"] == rung and r["segment"] == evaluate.PORTFOLIO:
            return r["p_value"]
    return None


def _approve(pd_: np.ndarray, raw: np.ndarray, share: float) -> np.ndarray:
    """Approve exactly the share of lowest-PD applicants; ties (a calibration map is a step function) are broken by
    the rung's raw score, then by position, so two rungs are compared at the same approval count."""
    n = int(round(share * len(pd_)))
    order = np.lexsort((np.arange(len(pd_)), raw, pd_))
    out = np.zeros(len(pd_), dtype=bool)
    out[order[:n]] = True
    return out


def _impact(fit: Fit, pds: dict[str, np.ndarray], raws: dict[str, np.ndarray], y: np.ndarray,
            ead: np.ndarray) -> dict[str, Any]:
    """The champion and the challenger at the same approval rate: bad rates, expected loss, the swap sets."""
    other = CHALLENGER if CHALLENGER in pds else "P5-tabpfn"
    champ, chall = pds[CHAMPION], pds[other]
    a = _approve(champ, raws[CHAMPION], APPROVAL)
    b = _approve(chall, raws[other], APPROVAL)
    lab = lambda en, es: {"en": en, "es": es}  # noqa: E731
    cur = "NT dollars" if fit.source == "uci-taiwan" else "DM"
    out = {
        "approval_rate": {"value": float(a.mean()), "unit": "fraction", "label": lab("Approval rate (both models)", "Tasa de aprobación (ambos modelos)")},
        "bad_rate_champion": {"value": float(y[a].mean()), "unit": "fraction", "label": lab("Bad rate among approved, champion", "Tasa de malos entre aprobados, campeón")},
        "bad_rate_challenger": {"value": float(y[b].mean()), "unit": "fraction", "label": lab("Bad rate among approved, challenger", "Tasa de malos entre aprobados, retador")},
        "el_champion": {"value": float(LGD * (champ[a] * ead[a]).sum()), "unit": cur, "label": lab("Expected loss of the approved, champion (LGD 50%)", "Pérdida esperada de los aprobados, campeón (LGD 50%)")},
        "el_challenger": {"value": float(LGD * (chall[b] * ead[b]).sum()), "unit": cur, "label": lab("Expected loss of the approved, challenger (LGD 50%)", "Pérdida esperada de los aprobados, retador (LGD 50%)")},
        "loss_champion": {"value": float(LGD * ead[a & (y == 1)].sum()), "unit": cur, "label": lab("Realised loss of the approved defaulters, champion (LGD 50%)", "Pérdida realizada de los aprobados que incumplen, campeón (LGD 50%)")},
        "loss_challenger": {"value": float(LGD * ead[b & (y == 1)].sum()), "unit": cur, "label": lab("Realised loss of the approved defaulters, challenger (LGD 50%)", "Pérdida realizada de los aprobados que incumplen, retador (LGD 50%)")},
        "swap_in": {"value": float((b & ~a).sum()), "unit": "applicants", "label": lab("Approved by the challenger only", "Aprobados solo por el retador")},
        "swap_out": {"value": float((a & ~b).sum()), "unit": "applicants", "label": lab("Approved by the champion only", "Aprobados solo por el campeón")},
        "swap_in_bad_rate": {"value": float(y[b & ~a].mean()) if (b & ~a).any() else None, "unit": "fraction", "label": lab("Bad rate of the challenger-only approvals", "Tasa de malos de los aprobados solo por el retador")},
        "swap_out_bad_rate": {"value": float(y[a & ~b].mean()) if (a & ~b).any() else None, "unit": "fraction", "label": lab("Bad rate of the champion-only approvals", "Tasa de malos de los aprobados solo por el campeón")},
    }
    if fit.source == "uci-german":
        def cost(p: np.ndarray) -> tuple[float, float]:
            best = (np.inf, 0.0)
            for c in np.unique(p):
                acc = p <= c
                total = GERMAN_COST["bad_accepted"] * (y[acc] == 1).sum() + GERMAN_COST["good_rejected"] * (y[~acc] == 0).sum()
                best = min(best, (float(total), float(c)))
            return best
        for key, p in (("champion", champ), ("challenger", chall)):
            total, c = cost(p)
            out[f"min_cost_{key}"] = {"value": total, "unit": "cost units", "label": lab(
                f"Least cost under the German cost matrix, {key} (bad accepted 5, good rejected 1)",
                f"Costo mínimo con la matriz de costos de German, {'campeón' if key == 'champion' else 'retador'} (malo aceptado 5, bueno rechazado 1)")}
    return out


#: the case's severity policy: (finding family, tests, severity when a test is red, when amber). The level of the PD
#: (is the average right: Jeffreys, binomial, Vasicek-adjusted binomial) weighs more than its fit across the range
#: (chi-square over grades, Hosmer-Lemeshow, Spiegelhalter), which at thousands of obligors rejects for deviations
#: too small to matter, and which BCBS WP14 warns under-states its type I error when defaults are correlated.
SEVERITY: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("calibration level", ("pd.jeffreys", "pd.binomial", "pd.binomial_vasicek"), "S2", "S3"),
    ("calibration fit", ("pd.chi2_grades", "pd.hosmer_lemeshow", "pd.spiegelhalter"), "S3", "S4"),
    ("stability", ("stability.psi",), "S2", "S3"),
    ("discrimination", ("disc.auc_vs_initial",), "S2", "S3"),
)
_ES = {"calibration level": "nivel de calibración", "calibration fit": "ajuste de calibración",
       "stability": "estabilidad", "discrimination": "discriminación"}


def _findings(rows: list[dict], variant: str, fit: Fit) -> list[dict[str, Any]]:
    """Findings from the battery under the case's severity policy (SEVERITY), for the champion and the challenger;
    the design limits and the data-quality flags are S3 and S4."""
    out: list[dict[str, Any]] = []
    for rung in (CHAMPION, CHALLENGER if CHALLENGER in fit.rungs else "P5-tabpfn"):
        for family, ids, on_red, on_amber in SEVERITY:
            hit = [r for r in rows if r["model_id"] == rung and r["test_id"] in ids and r["light"] in ("red", "amber")
                   and r["segment"] == evaluate.PORTFOLIO]
            if not hit:
                continue
            sev = on_red if any(r["light"] == "red" for r in hit) else on_amber
            ev = sorted({f"{r['test_id']}@{rung}" for r in hit})
            names = ", ".join(sorted({r["test_id"] for r in hit}))
            tag = "".join(w[0] for w in family.split()).upper()
            out.append({"id": f"F-{tag}-{rung}", "severity": sev, "status": "open", "evidence": ev,
                        "title": _t(f"{rung}: {family} tests flag the {variant} population ({names})",
                                    f"{rung}: las pruebas de {_ES[family]} alertan en la población {variant} ({names})")})
    out.append({"id": "F-OOT", "severity": "S3", "status": "accepted", "evidence": ["design:single-snapshot"],
                "title": _t("No out-of-time validation is possible: the data is a single snapshot",
                            "No es posible validar fuera del tiempo: los datos son una sola foto")})
    flags = (fit.contract.get("by_rule") or {}).get("flagged") or {}
    if flags:
        out.append({"id": "F-CODES", "severity": "S4", "status": "accepted",
                    "evidence": [f"contract:{k}" for k in sorted(flags)],
                    "title": _t("Codes outside the documented scale are kept as their own bins (" +
                                ", ".join(f"{k}: {v:,}" for k, v in sorted(flags.items())) + " records)",
                                "Códigos fuera de la escala documentada se conservan como tramos propios (" +
                                ", ".join(f"{k}: {v:,}" for k, v in sorted(flags.items())).replace(",", ".") + " registros)")})
    return out


def _sample(fit: Fit, rows_pos: np.ndarray) -> dict[str, Any]:
    """50 scored applicants for the live parity test: inputs, the scorecard's points and score, the EBM logit."""
    X = fit.X.iloc[rows_pos]
    sc = fit.rungs[CHAMPION].model
    ex = fit.rungs["P3-ebm"].details["export"]
    return {"ids": X["id"].tolist(), "targets": [int(t) for t in fit.y[rows_pos]],
            "inputs": {f: X[f].tolist() for f in fit.features},
            "scorecard_points": sc.points(X).tolist(), "scorecard_score": sc.score(X).tolist(),
            "scorecard_pd": fit.rungs[CHAMPION].pd(X).tolist(), "ebm_logit": score_logit(ex, X).tolist()}


def _models_doc(fit: Fit, *, seed: int, lineage) -> dict[str, Any]:
    models = [r.record() for r in fit.rungs.values()]
    rows_pos = fit.sp.holdout[:200]
    extra: dict[str, Any] = {"reason_stability": None}
    if CHALLENGER in fit.rungs:
        from ..model import gbm

        g = fit.rungs[CHALLENGER].model
        extra["reason_stability"] = gbm.reason_stability(
            g, fit.X.iloc[fit.train], fit.y[fit.train], fit.X.iloc[rows_pos], categorical=fit.categorical,
            monotone=feat.TAIWAN_MONOTONE if fit.source == "uci-taiwan" else feat.GERMAN_MONOTONE, seed=seed)
    fields = feat.TAIWAN_FIELDS if fit.source == "uci-taiwan" else feat.GERMAN_FIELDS
    monotone = feat.TAIWAN_MONOTONE if fit.source == "uci-taiwan" else feat.GERMAN_MONOTONE
    fitinfo = {"source": fit.source, "split": fit.sp.summary(fit.y), "train_rows": int(len(fit.train)),
               "features": feat.feature_meta(fields, monotone, fit.categorical), "seed": seed,
               "master_scale": {"grades": list(GRADES), "upper": list(MASTER_SCALE_UPPER)},
               **extra}
    return build_models_artifact(case_id=CASE_ID, fit_id=fit.fit_id, model=models, fit=fitinfo, lineage=lineage,
                                 lane={"lane": "precompute", "reasons": []})


class C01:
    id = CASE_ID
    slug = "retail-cards-pd"
    category_id = "credit-scoring"
    kind = "real"  # observed outcomes; its perturbed variants are labelled as such
    title = _t("Retail cards PD: champion vs challenger", "PD de tarjetas: campeón vs retador")
    question = _t("Does a monotone WoE scorecard match the challengers the literature says can beat it, once "
                  "calibration is required, and what do the validation tests say when the population shifts?",
                  "¿Iguala una scorecard WoE monótona a los retadores que según la literatura pueden superarla, "
                  "cuando se exige calibración, y qué dicen las pruebas de validación cuando la población cambia?")
    sources = SOURCES

    def bake(self, *, seed: int, paths, data_root: Path) -> dict[str, Any]:
        tw, tw_rep = _load_taiwan(data_root)
        de, de_rep = _load_german(data_root)
        fits = {
            "taiwan": _fit("taiwan", "uci-taiwan", tw, tw_rep, features=feat.TAIWAN_FEATURES,
                           categorical=feat.TAIWAN_CATEGORICAL, monotone=feat.TAIWAN_MONOTONE, seed=seed,
                           ead_col="BILL_AMT1"),
            "german": _fit("german", "uci-german", de, de_rep, features=feat.GERMAN_FEATURES,
                           categorical=feat.GERMAN_CATEGORICAL, monotone=feat.GERMAN_MONOTONE, seed=seed,
                           with_tabpfn=_tabpfn_available(), ead_col="credit_amount"),
        }
        base = fits["taiwan"]
        fits["taiwan-small"] = _fit("taiwan-small", "uci-taiwan", tw, tw_rep, features=feat.TAIWAN_FEATURES,
                                    categorical=feat.TAIWAN_CATEGORICAL, monotone=feat.TAIWAN_MONOTONE, seed=seed,
                                    train_n=2000, base_split=base.sp, ead_col="BILL_AMT1")
        rv = _v("riskvalidation")
        entries: list[dict[str, Any]] = []
        values: dict[str, float] = {}
        for fit_id, fit in fits.items():
            lineage = lin.build(CASE_ID, sources=[fit.source], truth_status="real-outcomes", seed=seed,
                                code_version=__version__, riskvalidation_version=rv)
            rel = f"{CASE_ID}/models-{fit_id}.json"
            # the rungs' internals are written exactly: the live scorers recompute from them to 1e-9 (CT-105)
            entry = write_artifact(paths.root, rel, _models_doc(fit, seed=seed, lineage=lineage),
                                   exact=frozenset({"details", "calibration"}), engines=ENGINES, run_ms=RUN_MS)
            entries.append({"role": "models", "variant_id": f"models-{fit_id}", "truth_status": "real-outcomes",
                            "title": _t(f"Models fitted on {fit_id}", f"Modelos ajustados en {fit_id}"),
                            "short_title": _t(f"Models {fit_id}", f"Modelos {fit_id}"),
                            "regime": _t(f"{len(fit.train):,} training rows of {fit.source}",
                                         f"{len(fit.train):,} filas de entrenamiento de {fit.source}".replace(",", ".")),
                            **entry})
        for v in VARIANTS:
            fit = fits[v["fit"]]
            pos, y = evaluation_set(fit, v["id"], seed=seed)
            X = fit.X.iloc[pos]
            Xtr, Xcal, ycal = fit.X.iloc[fit.train], fit.X.iloc[fit.sp.calibration], fit.y[fit.sp.calibration]
            pds = {rid: r.pd(X) for rid, r in fit.rungs.items()}
            rows: list[dict] = []
            outputs: dict[str, Any] = {"rungs": {}}
            for rid, r in fit.rungs.items():
                rows += evaluate.battery(rid, pds[rid], y, pd_train=r.pd(Xtr), pd_cal=r.pd(Xcal), y_cal=ycal,
                                         champion_pd=None if rid == CHAMPION else pds[CHAMPION])
                outputs["rungs"][rid] = evaluate.outputs(pds[rid], y, ead=fit.ead[pos],
                                                         pd_raw=r.raw_pd(X) if r.calibration is not None else None)
            rows += evaluate.csi_rows(Xtr, X, list(fit.features), fit.categorical)
            outputs["n"] = int(len(y))
            outputs["defaults"] = int(y.sum())
            outputs["groups"] = _by_group(fit, pos, y, pds)
            # 50 scored applicants for the live parity test, on the two variants whose rows are not resampled
            outputs["sample"] = _sample(fit, pos[:50]) if v["id"] in ("holdout", "german-twin") else None
            lineage = lin.build(CASE_ID, sources=[fit.source], truth_status=v["truth"], seed=seed,
                                code_version=__version__, riskvalidation_version=rv)
            art = build_artifact(case_id=CASE_ID, variant_id=v["id"], model=_model_summaries(fit), outputs=outputs, tests=rows,
                                 impact=_impact(fit, pds, {rid: r.raw_pd(X) for rid, r in fit.rungs.items()}, y, fit.ead[pos]),
                                 findings=_findings(rows, v["id"], fit), lineage=lineage,
                                 lane={"lane": "precompute", "reasons": []})
            rel = f"{CASE_ID}/{v['id']}.json"
            # the scored sample is written exactly: it is what the live parity test compares against
            entry = write_artifact(paths.root, rel, art, exact=frozenset({"sample"}), engines=ENGINES, run_ms=RUN_MS)
            _log(f"variant {v['id']}: {len(rows)} test results, {entry['bytes']:,} bytes")
            entries.append({"role": "variant", "variant_id": v["id"], "title": v["title"], "short_title": v["short"],
                            "regime": v["regime"],
                            "truth_status": v["truth"], "models_ref": f"{CASE_ID}/models-{v['fit']}.json", **entry})
            for rid in fit.rungs:
                auc = next(r["metric"] if r["metric"] is not None else r["statistic"]
                           for r in rows if r["test_id"] == "disc.auc" and r["model_id"] == rid)
                values[f"auc_{rid}_{v['id']}"] = auc
                psi = _psi_value(rows, rid)
                if psi is not None:
                    values[f"psi_{rid}_{v['id']}"] = psi
                pj = _p(rows, "pd.jeffreys", rid)
                if pj is not None:
                    values[f"jeffreys_p_{rid}_{v['id']}"] = pj
            if v["id"] == "holdout":
                values["holdout_default_rate"] = float(y.mean())
        ranges = expectations.check(CASE_ID, EXPECT, values)
        manifest = build_case_manifest(
            case_id=CASE_ID, title=self.title, category={"en": "Credit scoring", "es": "Scoring de crédito"},
            question=self.question, sources=list(SOURCES), seed=seed, variants=entries, default_variant="holdout",
            contract={"uci-taiwan": tw_rep.summary(), "uci-german": de_rep.summary()}, expect=ranges,
            riskvalidation_version=rv, source_details=_source_details(SOURCES))
        write_json(paths.manifests / f"{CASE_ID}.json", manifest)
        return manifest


def _source_details(ids) -> dict[str, dict[str, str]]:
    """What the Context view shows of each source: its name, publisher, landing page, licence, class, attribution."""
    from ..io import sources as registry

    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing,
                "licence": reg[i].licence, "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}


def _model_summaries(fit: Fit) -> list[dict[str, Any]]:
    """The model records without their internals (those live in the fit's models artifact)."""
    return [{k: v for k, v in r.record().items() if k != "details"} for r in fit.rungs.values()]


def _by_group(fit: Fit, pos: np.ndarray, y: np.ndarray, pds: dict[str, np.ndarray]) -> dict[str, Any]:
    """Discrimination by protected group (sex), for the record; the fairness battery is C21's. The ROC of the
    champion and of every challenger within each group (51 points) is what the By group view draws."""
    from riskvalidation.validation.discrimination import auc_with_variance

    groups = fit.X["protected_attr"].to_numpy()[pos]
    out: dict[str, Any] = {}
    for g in sorted(set(groups)):
        m = groups == g
        if y[m].min() == y[m].max():
            continue
        out[str(g)] = {"n": int(m.sum()), "default_rate": float(y[m].mean()),
                       "auc": {rid: float(auc_with_variance(p[m], y[m])[0]) for rid, p in pds.items()
                               if np.ptp(p[m]) > 0},
                       "roc": {rid: evaluate.roc_points(p[m], y[m], 51) for rid, p in pds.items()
                               if not rid.startswith("P0") and np.ptp(p[m]) > 0}}
    return out


def _tabpfn_available() -> bool:
    try:
        import tabpfn  # noqa: F401
    except Exception:  # noqa: BLE001 (an optional extra)
        return False
    return True


CASE = C01()
