"""The hyper-parameter sensitivity of the PC-Hazard rung (S-4), reported beside the pre-registered verdict (CT-521 to CT-523).

The S-4 hypothesis (``backtest.S4_HYPOTHESIS``) was written before the run and is judged on the settings the rung was built with. A reader
cannot tell how much that verdict rests on them. This module refits the rung at a reporting date under nine settings, one hyper-parameter
moved at a time around the defaults, and judges each refit the way the hypothesis judges the main fit:

- the interval width of 1.5, 3 and 6 months, with the interval count set to 120, 60 and 30 so that every grid covers the same 180 months;
- the hidden layers (16, 16), (32, 32) and (64, 64);
- the weight decay 1e-5, 1e-4 and 1e-3;
- the learning rate 0.003, 0.01 and 0.03.

The default is counted once: nine settings, never a grid and never a tuning. Each refit trains on the loans known at the date, with the
hold-out split and the seed of the main fit (``fit_pch`` is given the observation of the date and nothing that follows it), and its
predictions are evaluated by ``backtest.s4_evaluation`` on the same out-of-time accounts: the integrated Brier score, the mean absolute
decile gap against Aalen-Johansen, the c-index and the two criteria of the hypothesis. The default entry is the main fit's own
evaluation, not a second one. A fit that raises is recorded as ``failed`` with its reason and a fit that runs to the epoch cap as
``not_converged`` (its numbers are still reported); neither is dropped.

Over the dates each setting has the verdict ``backtest.s4_verdict`` gives its own dates. The verdict of the case stays the default's,
and ``overall`` counts the settings whose verdict agrees with it. No setting is chosen.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

import numpy as np

from . import backtest as bt
from . import neural
from .neural import PchModel, fit_pch

#: the months every grid of the sweep covers
COVERED_MONTHS = 180.0
#: the two rungs the S-4 evaluation reads
RUNGS = ("L2-cox", "L3-pch")
CASE_SETTING = "default"


@dataclass(frozen=True)
class Setting:
    """One setting of the sweep: the hyper-parameters of a refit and what moved from the default."""

    setting_id: str
    parameter: str                      # "default", "interval_width", "hidden_layers", "weight_decay" or "learning_rate"
    label: dict[str, str]
    interval_months: float
    intervals: int
    hidden: tuple[int, ...]
    learning_rate: float
    weight_decay: float
    is_default: bool = False


def _t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def _setting(sid: str, parameter: str, en: str, es: str, **kw: Any) -> Setting:
    base = dict(interval_months=neural.WIDTH, intervals=neural.N_INTERVALS, hidden=neural.HIDDEN, learning_rate=neural.LEARNING_RATE,
                weight_decay=neural.WEIGHT_DECAY)
    base.update(kw)
    return Setting(setting_id=sid, parameter=parameter, label=_t(en, es), is_default=parameter == "default", **base)


SETTINGS: tuple[Setting, ...] = (
    _setting("default", "default", "Defaults (3-month intervals, hidden layers 32 and 32, weight decay 1e-4, learning rate 0.01)",
             "Valores por defecto (intervalos de 3 meses, capas ocultas 32 y 32, decaimiento de pesos 1e-4, tasa de aprendizaje 0,01)"),
    _setting("width-1.5", "interval_width", "Interval width 1.5 months (120 intervals)", "Ancho de intervalo de 1,5 meses (120 intervalos)",
             interval_months=1.5, intervals=120),
    _setting("width-6", "interval_width", "Interval width 6 months (30 intervals)", "Ancho de intervalo de 6 meses (30 intervalos)",
             interval_months=6.0, intervals=30),
    _setting("hidden-16", "hidden_layers", "Hidden layers 16 and 16", "Capas ocultas de 16 y 16", hidden=(16, 16)),
    _setting("hidden-64", "hidden_layers", "Hidden layers 64 and 64", "Capas ocultas de 64 y 64", hidden=(64, 64)),
    _setting("weight-decay-1e-5", "weight_decay", "Weight decay 1e-5", "Decaimiento de pesos 1e-5", weight_decay=1e-5),
    _setting("weight-decay-1e-3", "weight_decay", "Weight decay 1e-3", "Decaimiento de pesos 1e-3", weight_decay=1e-3),
    _setting("learning-rate-0.003", "learning_rate", "Learning rate 0.003", "Tasa de aprendizaje 0,003", learning_rate=0.003),
    _setting("learning-rate-0.03", "learning_rate", "Learning rate 0.03", "Tasa de aprendizaje 0,03", learning_rate=0.03),
)


def fit_arguments(s: Setting) -> dict[str, Any]:
    """The keyword arguments of ``neural.fit_pch`` that realise ``s``."""
    return {"hidden": tuple(s.hidden), "learning_rate": s.learning_rate, "weight_decay": s.weight_decay, "width": s.interval_months,
            "n_intervals": s.intervals}


def parameters(s: Setting) -> dict[str, Any]:
    return {"interval_months": s.interval_months, "intervals": s.intervals, "hidden": list(s.hidden), "learning_rate": s.learning_rate,
            "weight_decay": s.weight_decay}


def settings_findings(settings: tuple[Setting, ...] = SETTINGS) -> list[str]:
    """What is wrong with a set of settings: it must hold one default, move one hyper-parameter per other setting (the width and its
    interval count are one), and cover ``COVERED_MONTHS`` months with every grid."""
    out: list[str] = []
    defaults = [s for s in settings if s.is_default]
    if len(defaults) != 1:
        return [f"{len(defaults)} default settings, one expected"]
    d = defaults[0]
    for s in settings:
        if abs(s.interval_months * s.intervals - COVERED_MONTHS) > 1e-9:
            out.append(f"{s.setting_id}: the grid covers {s.interval_months * s.intervals:g} months, not {COVERED_MONTHS:g}")
        if s.is_default:
            continue
        moved = [name for name, differs in (("interval_width", (s.interval_months, s.intervals) != (d.interval_months, d.intervals)),
                                            ("hidden_layers", tuple(s.hidden) != tuple(d.hidden)),
                                            ("weight_decay", s.weight_decay != d.weight_decay),
                                            ("learning_rate", s.learning_rate != d.learning_rate)) if differs]
        if moved != [s.parameter]:
            out.append(f"{s.setting_id}: moves {moved or 'nothing'}, declares {s.parameter}")
    return out


# ---------------------------------------------------------------------------------------------------------------------
# one refit


def fit_status(model: PchModel) -> tuple[str, dict[str, str] | None]:
    """``("fitted", None)`` for a fit whose early stopping triggered, ``("not_converged", reason)`` for one that ran to the epoch cap and
    ``("failed", reason)`` for rates that are not finite (nothing to evaluate)."""
    if not np.all(np.isfinite(model.rates)):
        return "failed", _t("the fitted rates are not finite", "las tasas ajustadas no son finitas")
    if model.epochs >= neural.MAX_EPOCHS:
        return "not_converged", _t(f"the fit ran to the cap of {neural.MAX_EPOCHS:,} epochs without the early stopping triggering "
                                   f"(best epoch {model.best_epoch:,}); its numbers are reported as they are",
                                   f"el ajuste llegó al tope de {neural.MAX_EPOCHS:,} épocas sin que la parada temprana se activara "
                                   f"(mejor época {model.best_epoch:,}); sus números se informan tal como son")
    return "fitted", None


def _compact(summary: dict[str, Any]) -> dict[str, Any]:
    g = summary["mean_abs_decile_gap_aalen_johansen"]
    return {"c_index": dict(summary["c_index"]), "integrated_brier": dict(summary["integrated_brier"]),
            "mean_decile_gap": {"pch": g["pch_mean"], "cox": g["cox_mean"]}, "criteria": dict(summary["criteria"]),
            "holds_at_date": summary["holds_at_date"]}


def _entry(s: Setting, model: PchModel | None, status: str, reason: dict[str, str] | None, evaluation: dict[str, Any] | None) -> dict[str, Any]:
    fitted = model is not None and status != "failed"
    return {"setting_id": s.setting_id, "parameter": s.parameter, "is_default": s.is_default, "label": dict(s.label),
            "parameters": parameters(s), "status": status, "reason": reason,
            "epochs": int(model.epochs) if fitted else None, "best_epoch": int(model.best_epoch) if fitted else None,
            "holdout_nll_per_default": float(model.val_nll) if fitted else None,
            "weights_sha256": model.weights_sha256 if fitted else None, "evaluation": evaluation}


def _evaluate(loans: Any, run: Any, follow: bt.FollowUp, model: PchModel) -> dict[str, Any] | None:
    """The S-4 evaluation of ``run`` with ``model`` as its PC-Hazard rung, as ``backtest.s4_evaluation`` gives it (the two rungs only)."""
    swapped = dataclasses.replace(run, ladder=dataclasses.replace(run.ladder, pch=model))
    life = bt.lifetime_results(loans, swapped, follow, rungs=RUNGS, pooled_only=True)
    ev = bt.s4_evaluation(swapped, follow, life)
    return None if ev is None else _compact(ev.summary)


def _method() -> dict[str, str]:
    return _t("The PC-Hazard rung refitted under nine settings, one hyper-parameter moved at a time around the defaults (the interval width "
              "with the interval count set so every grid covers the same 180 months, the hidden layers, the weight decay and the learning "
              "rate): never a grid and never a tuning. Each refit trains on the same loans, hold-out split and seed as the main fit and is "
              "evaluated on the same out-of-time accounts as the hypothesis. No setting is chosen: the verdict of the case stays the one of "
              "the defaults, written before the run.",
              "El peldaño PC-Hazard reajustado con nueve configuraciones, moviendo un hiperparámetro a la vez alrededor de los valores por "
              "defecto (el ancho del intervalo con el número de intervalos fijado para que cada malla cubra los mismos 180 meses, las capas "
              "ocultas, el decaimiento de pesos y la tasa de aprendizaje): nunca una grilla ni un ajuste fino. Cada reajuste entrena con los "
              "mismos préstamos, la misma partición de validación y la misma semilla que el ajuste principal y se evalúa con las mismas cuentas "
              "fuera de tiempo que la hipótesis. No se elige ninguna configuración: el veredicto del caso sigue siendo el de los valores por "
              "defecto, escrito antes de la corrida.")


def sensitivity(loans: Any, run: Any, follow: bt.FollowUp, evaluation: bt.S4Evaluation | None) -> dict[str, Any]:
    """The ``fit.pch_sensitivity`` block of one reporting date (``overall`` stays None: the case fills it once every date is baked).
    ``evaluation`` is the main fit's S-4 evaluation, which is the default entry. When the PC-Hazard rung was not fitted no setting is
    written and the block says why."""
    found = settings_findings()
    if found:
        raise ValueError(f"the sweep's settings are not the ones the unit declares: {found}")
    head = {"method": _method(), "kind": "one-at-a-time", "covers_months": int(COVERED_MONTHS), "same_training": True,
            "selected_setting": None, "overall": None}
    if evaluation is None:
        return {**head, "evaluated": False, "seed": None,
                "reason": _t("the PC-Hazard rung was not fitted at this reporting date (too few loans or defaults): there is nothing to refit",
                             "el peldaño PC-Hazard no se ajustó en esta fecha de reporte (muy pocos préstamos o incumplimientos): no hay nada que reajustar"),
                "settings": []}
    main = run.ladder.pch
    entries = [_entry(SETTINGS[0], main, "fitted", None, _compact(evaluation.summary))]
    for s in SETTINGS[1:]:
        try:
            model = fit_pch(loans, run.obs, reporting_date=run.reporting_date, seed=neural.SEED, **fit_arguments(s))
            status, reason = fit_status(model)
            ev = None if status == "failed" else _evaluate(loans, run, follow, model)
            if status != "failed" and ev is None:
                status, reason = "failed", _t("the PC-Hazard rung of this setting was not evaluated", "el peldaño PC-Hazard de esta configuración no se evaluó")
        except Exception as exc:  # noqa: BLE001  (a failed fit is a result of the sweep: recorded, never dropped)
            model, status, ev = None, "failed", None
            reason = _t(f"the fit raised {type(exc).__name__}: {exc}", f"el ajuste falló con {type(exc).__name__}: {exc}")
        entries.append(_entry(s, model, status, reason, ev))
    return {**head, "evaluated": True, "seed": int(main.seed), "reason": None, "settings": entries}


# ---------------------------------------------------------------------------------------------------------------------
# the verdict over the dates


def overall(holds_by_setting: dict[str, list[bool | None]]) -> dict[str, Any]:
    """The verdict of every setting over the dates (``backtest.s4_verdict``, untouched) and how many agree with the default's, which is
    the verdict of the case. ``holds_by_setting`` maps a setting id to its ``holds_at_date`` at each date (None: not evaluable, not
    fitted or failed). A setting agrees when its verdict is not None and equals the case verdict."""
    case = bt.s4_verdict(holds_by_setting[CASE_SETTING])
    rows = []
    for s in SETTINGS:
        v = bt.s4_verdict(holds_by_setting[s.setting_id])
        rows.append({"setting_id": s.setting_id, "dates": v["dates"], "evaluable": v["evaluable"], "holds_at": v["holds_at"],
                     "verdict": v["verdict"], "agrees": bool(v["verdict"] is not None and v["verdict"] == case["verdict"])})
    return {"dates": case["dates"], "case_setting": CASE_SETTING, "case_verdict": case["verdict"], "settings_count": len(SETTINGS),
            "agree": sum(1 for r in rows if r["agrees"]), "settings": rows}


def overall_findings(stated: dict[str, Any], holds_by_setting: dict[str, list[bool | None]]) -> list[str]:
    """A count, a setting or a verdict of a document that disagrees with its dates."""
    want = overall(holds_by_setting)
    return [f"overall.{k} is {stated.get(k)!r}, the dates give {v!r}" for k, v in want.items() if stated.get(k) != v]


def holds_of(block: dict[str, Any]) -> dict[str, bool | None]:
    """``holds_at_date`` of each setting of one date's block (None when the block holds no setting or a setting has no evaluation)."""
    by = {s["setting_id"]: s for s in block["settings"]}
    return {s.setting_id: (None if by.get(s.setting_id, {}).get("evaluation") is None else by[s.setting_id]["evaluation"]["holds_at_date"])
            for s in SETTINGS}


def holds_by_setting(blocks: list[dict[str, Any]]) -> dict[str, list[bool | None]]:
    per = [holds_of(b) for b in blocks]
    return {s.setting_id: [p[s.setting_id] for p in per] for s in SETTINGS}


__all__ = ["CASE_SETTING", "COVERED_MONTHS", "SETTINGS", "Setting", "fit_arguments", "fit_status", "holds_by_setting", "holds_of", "overall",
           "overall_findings", "sensitivity", "settings_findings"]
