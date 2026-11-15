"""The evaluation bootstrap shared by the two comparisons that were judged by a count of point differences: the S-4 comparison of C06
(PC-Hazard against Cox at each reporting date) and the S-5 benchmark of C08 (the better of the forest and the network against each
of the six rungs, per test cohort).

What it measures. A difference between two models on the out-of-time book is one draw from the sampling of the accounts; a reader
cannot tell whether it is larger than that noise. The evaluation bootstrap resamples the out-of-time accounts (C06) or defaults (C08)
with replacement, as many as there are, and recomputes the difference on each resample with the predictions held fixed. It is the
uncertainty of the comparison on this book, not of the fits: no model is refitted in a replicate, so the variation of a fit with its
training sample is not in the interval. The interval is the 2.5 and 97.5 percentiles of the replicate differences.

What it does not do. It never changes a verdict: the hypotheses of S-4 and S-5 were written before the run and their rules stay as
written (``backtest.s4_verdict``, ``ml_benchmark.verdict``); the interval is reported beside them.

The metrics of a replicate are the engine's where the engine provides them (the C06 integrated Brier score is
``riskvalidation.validation.ifrs9.lifetime_pd_backtest``); this module holds only the resampling and the arrangement of the interval.
"""
from __future__ import annotations

from typing import Any, Iterator

import numpy as np

from ..core.text import number

#: replicates per comparison and the level of the percentile interval, fixed once here and recorded in every document
REPLICATES = 1_000
LEVEL = 0.95
#: a comparison on fewer defaults (C06) or fewer defaults in the test cohort (C08) than this has no interval (the same floor the
#: product uses for a fit, ``run.MIN_DEFAULTS_LGD`` and ``variant.N_MIN_TEST``)
MIN_EVENTS = 30
#: the share of replicates that must be finite for an interval to be reported
MIN_VALID_SHARE = 0.9


def text(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def method_text(unit_en: str, unit_es: str, replicates: int | None = None) -> dict[str, str]:
    """The statement of the method every document carries: what is resampled (``unit_en`` and ``unit_es`` are the noun phrases with their
    article in Spanish, "out-of-time accounts" and "las cuentas fuera de tiempo"), what is held fixed and what the interval measures.
    Numbers are written in the form of each language."""
    reps = REPLICATES if replicates is None else int(replicates)
    lo, hi = (1 - LEVEL) / 2 * 100, (1 + LEVEL) / 2 * 100
    pct = f"{LEVEL * 100:.0f}"
    return text(
        f"Evaluation bootstrap: the {unit_en} are resampled with replacement ({number(reps, 0, lang='en')} replicates, as many as there are) "
        f"and each difference is recomputed on every resample with the predictions held fixed, so no model is refit. The interval is the "
        f"{number(lo, 1, lang='en')} and {number(hi, 1, lang='en')} percentiles of the replicate differences ({pct} percent): it measures the "
        "sampling noise of the comparison on this book, not the uncertainty of the fits. The verdict stays the rule written before the run.",
        f"Remuestreo de evaluación: {unit_es} se remuestrean con reemplazo ({number(reps, 0, lang='es')} réplicas, tantas como hay) y "
        f"cada diferencia se recalcula en cada remuestra con las predicciones fijas, de modo que ningún modelo se reajusta. El intervalo son "
        f"los percentiles {number(lo, 1, lang='es')} y {number(hi, 1, lang='es')} de las diferencias de las réplicas ({pct} por ciento): mide el "
        "ruido de muestreo de la comparación en este libro, no la incertidumbre de los ajustes. El veredicto sigue siendo la regla escrita antes de la corrida.")


def counts(n: int, rng: np.random.Generator) -> np.ndarray:
    """One resample of ``n`` units with replacement, as the number of times each unit is drawn (they add to ``n``)."""
    return np.bincount(rng.integers(0, n, size=n), minlength=n)


def draws(n: int, replicates: int, seed: int) -> Iterator[np.ndarray]:
    """The resamples of a comparison, one after the other: a pure function of ``(n, replicates, seed)``."""
    rng = np.random.default_rng(seed)
    for _ in range(replicates):
        yield counts(n, rng)


def percentile_interval(values: np.ndarray, level: float = LEVEL) -> tuple[float, float, int]:
    """``(low, high, n_valid)``: the central percentile interval of the finite replicate values."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan"), float("nan"), 0
    lo, hi = np.percentile(v, [100.0 * (1.0 - level) / 2.0, 100.0 * (1.0 + level) / 2.0])
    return float(lo), float(hi), int(v.size)


def excludes_zero(lo: float | None, hi: float | None) -> bool | None:
    return None if lo is None or hi is None else bool(lo > 0.0 or hi < 0.0)


def difference(point: float | None, values: np.ndarray, *, reason: dict[str, str] | None = None, replicates: int | None = None) -> dict[str, Any]:
    """One compared difference with its interval: ``{difference, lo, hi, excludes_zero, n_valid, reason}``.

    A difference with no point value (a side not observed), or too few finite replicates, has no interval: its bounds are null and
    ``reason`` says why (``reason`` given, or the shortfall of valid replicates), never a number."""
    wanted = REPLICATES if replicates is None else replicates
    if point is None or not np.isfinite(point):
        return {"difference": None, "lo": None, "hi": None, "excludes_zero": None, "n_valid": 0,
                "reason": reason or text("the difference is not observed", "la diferencia no se observa")}
    lo, hi, n = percentile_interval(values)
    if n < max(1, int(np.ceil(MIN_VALID_SHARE * wanted))) and n < wanted:
        why = reason or text(f"only {n} of {wanted} replicates are finite: no interval", f"solo {n} de {wanted} réplicas son finitas: sin intervalo")
        return {"difference": float(point), "lo": None, "hi": None, "excludes_zero": None, "n_valid": n, "reason": why}
    return {"difference": float(point), "lo": lo, "hi": hi, "excludes_zero": excludes_zero(lo, hi), "n_valid": n, "reason": None}


__all__ = ["REPLICATES", "LEVEL", "MIN_EVENTS", "MIN_VALID_SHARE", "text", "method_text", "counts", "draws", "percentile_interval",
           "excludes_zero", "difference"]
