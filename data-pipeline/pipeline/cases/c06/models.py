"""The C06 models document (``c06-models``): what was fitted for one reporting date (CT-506, CT-512)."""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.provisions import term_structure as rv_ts

from . import macro as mc
from . import neural
from .build import (CURRENCY, NOTICE, RUNG_KIND, RUNG_TEXT, SEGMENT_LABELS, month_label, policy_block, t)
from .ladder import AGE_LABELS, Ladder, N_BANDS
from .panel import N_STRATA, SECTOR_NAMES, SEGMENT_IDS
from .run import CAP_Q, LIFETIME_CAP_MONTHS, PERIOD_MONTHS, RHO, DateRun, decode_stratum

REFERENCE_STRATUM = ((0 * 4 + 0) * len(SECTOR_NAMES) + (len(SECTOR_NAMES) - 1)) * 2 + 0
MONTHS = PERIOD_MONTHS * np.arange(1, CAP_Q + 1)


def _coefs(names, params, bse) -> list[dict[str, Any]]:
    return [{"name": n, "estimate": float(p), "std_error": float(b) if np.isfinite(b) else None} for n, p, b in zip(names, params, bse, strict=True)]


def _positive_curve(months: np.ndarray, f: np.ndarray) -> dict[str, Any]:
    f = np.asarray(f, dtype=float)
    keep = (f > 0.0) & (f < 1.0) & np.isfinite(f)
    return {"months": months[keep].astype(int).tolist(), "cumulative_pd": f[keep].tolist()}


#: the licence expression of torch as data-pipeline/config/licences.json verifies it (package metadata of the pinned wheel)
TORCH_LICENCE = "Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT"


def ladder_blocks(run: DateRun, cleaning: dict[str, int] | None = None, evaluation: Any = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """``(fit.ladder, model records)``: one entry per rung, evaluated or not. ``evaluation`` (``backtest.S4Evaluation``) adds the
    S-4 deciles to the Cox and PC-Hazard records and the PC-Hazard summary beside Cox."""
    lad: Ladder = run.ladder
    cutoff = str(np.datetime64(run.reporting_date, "D"))
    entries, records = [], []
    for rung in ("L0-km", "L1-dth", "L2-cox", "L3-pch"):
        title, short = RUNG_TEXT[rung]
        status = {"L0-km": lad.km.status, "L1-dth": lad.dth.status, "L2-cox": lad.cox.status, "L3-pch": lad.pch.status}[rung]
        engine, engine_version, licence, checkpoint = (("torch", _torch_version(), TORCH_LICENCE, None) if rung == "L3-pch"
                                                       else ("statsmodels", _statsmodels_version(), "BSD-3-Clause", None))
        extra_params: dict[str, Any] = {}
        cov, macro_cov, coefs, base, details = [], [], [], {"months": [], "cumulative_pd": []}, {}
        if status.evaluated and rung == "L0-km":
            f = 1.0 - lad.km.survival.at(MONTHS.astype(float) + 0.0, 1.0)
            base = _positive_curve(MONTHS, f)
            details = {"estimator": "Kaplan-Meier product-limit on loan age in months, all loans selected at the cutoff"}
        if status.evaluated and rung == "L1-dth":
            m = lad.dth
            cov = [n for n in m.names if n not in mc.MACRO_VARS and n != "const"]
            macro_cov = [n for n in m.names if n in mc.MACRO_VARS]
            coefs = _coefs(m.names, m.params, m.bse)
            lag = mc.lagged_for_hazard(run.history, run.paths["baseline"])
            hz = m.hazard_path(np.array([REFERENCE_STRATUM]), np.array([0]), lag)
            ts = rv_ts.from_hazard(hz, MONTHS)
            base = _positive_curve(MONTHS, ts.cumulative[0])
            details = {"cells": m.n_cells, "log_likelihood": m.log_likelihood, "converged": m.converged,
                       "age_bands_quarters": list(AGE_LABELS), "macro_lag_quarters": 1,
                       "macro_support": {v: [float(lo), float(hi)] for v, lo, hi in zip(mc.MACRO_VARS, m.macro_lo, m.macro_hi, strict=True)},
                       "macro_scaler": {v: [float(a), float(b)] for v, a, b in zip(mc.MACRO_VARS, m.scaler.mean, m.scaler.std, strict=True)},
                       "baseline_reference": "a loan under 50,000 USD, term up to 5 years, other or unknown sector, not revolving, from age 0, under the baseline macro path"}
        if status.evaluated and rung == "L2-cox":
            m = lad.cox
            cov = list(m.names)
            coefs = _coefs(m.names, m.params, m.bse)
            f = 1.0 - np.exp(-m.cumulative_hazard.at(MONTHS.astype(float), 0.0))
            base = _positive_curve(MONTHS, f)
            details = {"ties": "breslow", "time_scale": "loan age in months", "macro": "none: statsmodels PHReg has no time-varying covariates"}
            if evaluation is not None:
                details["decile_calibration"] = evaluation.deciles["L2-cox"]
        if status.evaluated and rung == "L3-pch":
            m = lad.pch
            cov = list(m.names)
            f = m.cumulative(np.array([REFERENCE_STRATUM]), np.array([0.0]), MONTHS.astype(float))[0]
            base = _positive_curve(MONTHS, f)
            checkpoint = m.weights_sha256
            extra_params = {"network_parameters": {"value": float(m.n_parameters), "unit": "weights"},
                            "best_epoch": {"value": float(m.best_epoch), "unit": "epochs"},
                            "holdout_loans": {"value": float(m.n_val_loans), "unit": "loans"}}
            details = {"method": ("PC-Hazard (Kvamme and Borgan 2019, arXiv 1910.06724): a feed-forward network maps the loan covariates to a "
                                  "piecewise-constant hazard rate per three-month interval of loan age; the likelihood is the discrete-time "
                                  "one of the interval counts (defaults and exposure)"),
                       "architecture": {"inputs": len(m.names), "hidden": list(m.hidden), "activation": "relu", "outputs": neural.N_INTERVALS,
                                        "output_transform": "softplus (a positive rate per month)"},
                       "grid": {"interval_months": neural.WIDTH, "intervals": neural.N_INTERVALS, "last_interval": "open: its rate holds beyond"},
                       "training": {"optimiser": "adam", "learning_rate": neural.LEARNING_RATE, "weight_decay": neural.WEIGHT_DECAY,
                                    "batch": "full", "max_epochs": neural.MAX_EPOCHS, "patience": neural.PATIENCE,
                                    "holdout_share": neural.VAL_SHARE, "epochs_run": m.epochs, "best_epoch": m.best_epoch,
                                    "train_nll_per_default": m.train_nll, "holdout_nll_per_default": m.val_nll,
                                    "train_loans": m.n_train_loans, "holdout_loans": m.n_val_loans},
                       "seed": m.seed, "time_scale": "loan age in months", "macro": "none: the rung stands on the loan covariates, as Cox",
                       "covariates_as": "L2-cox",
                       "baseline_reference": "a loan under 50,000 USD, term up to 5 years, other or unknown sector, not revolving, from age 0"}
            if evaluation is not None:
                details["decile_calibration"] = evaluation.deciles["L3-pch"]
                details["evaluation"] = evaluation.summary
        entries.append({"rung_id": rung, "kind": RUNG_KIND[rung], "covariates": cov, "macro_covariates": macro_cov,
                        "competing_prepayment": False, "training_cutoff": cutoff, "coefficients": coefs, "baseline": base})
        params = {"n_loans": {"value": float(status.n_loans), "unit": "loans"}, "n_defaults": {"value": float(status.n_events), "unit": "defaults"},
                  **extra_params}
        records.append({"id": rung, "family": "lifetime-pd", "rung": RUNG_KIND[rung], "title": t(*title), "short_title": t(*short),
                        "engine": engine, "engine_version": engine_version, "licence": licence,
                        "calibration": None, "parameters": params, "checkpoint_sha256": checkpoint,
                        "details": {"evaluated": status.evaluated, "reason": status.reason, "cleaning": dict(cleaning or {}), **details}})
    return entries, records


def _statsmodels_version() -> str:
    import statsmodels

    return statsmodels.__version__


def _torch_version() -> str:
    import torch

    return str(torch.__version__)


def fit_block(run: DateRun) -> dict[str, Any]:
    segments = [{"id": sid, "label": t(*SEGMENT_LABELS[sid]), "pd_ttc": float(min(max(run.seg_pd_ttc[g], 1e-6), 1 - 1e-6)),
                 "accounts": int(run.seg_counts[g])} for g, sid in enumerate(SEGMENT_IDS) if run.seg_counts[g] > 0]
    n_live = len(next(iter(run.z_paths.values())))
    defs = []
    for s, sid in enumerate(run.scenario_ids):
        path = run.paths[sid]
        defs.append({"id": sid, "label": t(mc.SCENARIO_LABELS[sid]["en"], mc.SCENARIO_LABELS[sid]["es"]), "weight": float(run.weights[s]),
                     "source": mc.SCENARIO_SOURCES[sid],
                     "z_path": [{"months": int(PERIOD_MONTHS * (k + 1)), "z": float(run.z_paths[sid][k])} for k in range(n_live)],
                     "macro": [{"variable": v, "unit": mc.MACRO_UNITS[v], "months": MONTHS.astype(int).tolist(),
                                "values": path[:, j].tolist()} for j, v in enumerate(mc.MACRO_VARS)]})
    zq, zh = run.z_hat
    sat = run.satellite
    pit = {"rho": RHO, "method": ("one-factor Vasicek conversion (riskvalidation implied_z and ttc_to_pit): the factor of each past quarter from "
                                   "the book's realised default rate; each scenario's factor from the default rate the hazard rung implies "
                                   "for the book under that scenario; the satellite is the least-squares reduced form of the hazard rung"),
           "z_hat": [{"period": mc.quarter_end(int(q)).date().isoformat(), "z": float(z)} for q, z in zip(zq, zh, strict=True)],
           "satellite": {"intercept": sat.intercept, "ar1": sat.ar1,
                         "coefficients": [{"name": v, "value": sat.coefficients[v]} for v in mc.MACRO_VARS]}}
    ladder, _ = ladder_blocks(run)
    lgd = {"kind": "charge-off severity proxy", "discounting": "original EIR, mid-period convention",
           "segments": [{"segment_id": x["segment_id"], "lgd": x["lgd"], "basis": x["basis"]} for x in run.lgd_segments
                        if run.seg_counts[SEGMENT_IDS.index(x["segment_id"])] > 0]}
    ead = {"amortising": True, "ccf_revolving": 1.0,
           "reason": ("the file has no balance: a term loan amortises as a level-payment annuity at its EIR over its term; a revolving line "
                      "is carried at its full approval (conversion factor 1)")}
    staging = {**policy_block(), "source": ("multiplier schedule, absolute floor and threefold ratio of the engine-provisions-api contract; "
                                            "30 and 90 days past due are IFRS 9 5.5.11 and B5.5.37 (no delinquency data in the file); no "
                                            "probation (the file has no cure dates and the reporting dates are a year apart)"),
               "probation_months": 0}
    return {"currency": CURRENCY, "segments": segments, "scenario_definitions": defs, "pit": pit, "ladder": ladder, "lgd": lgd, "ead": ead,
            "staging_policy": staging}


def model_records(run: DateRun, cleaning: dict[str, int] | None = None, evaluation: Any = None) -> list[dict[str, Any]]:
    return ladder_blocks(run, cleaning, evaluation)[1]


def model_summaries(run: DateRun) -> list[dict[str, Any]]:
    out = []
    for r in model_records(run):
        s = {k: v for k, v in r.items() if k != "details"}
        out.append(s)
    return out


__all__ = ["fit_block", "model_records", "model_summaries", "NOTICE", "month_label", "LIFETIME_CAP_MONTHS", "N_BANDS", "N_STRATA",
           "decode_stratum"]
