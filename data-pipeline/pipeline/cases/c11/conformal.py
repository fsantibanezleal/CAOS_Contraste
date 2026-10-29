"""BS-16 of the method tiers (beyond the state of the art): adaptive conformal recalibration of the VaR of HS-250, GARCH-t and FHS.

The wrapper is the engine's (``riskvalidation.market.conformal``, Gibbs and Candes 2021, arXiv 2106.00170): a working tail level
``a_t`` starts at the target ``alpha`` and moves after each day by ``gamma (alpha - 1{hit})``; the model is asked for its VaR and
ES at ``a_t``, so a hit makes the next VaR deeper and a quiet day lets it relax. ``gamma`` is the engine's default 0.005 and the
band the engine's ``[0.001, 0.25]``, both fixed before any run and never tuned on a window. The model of a day is the ladder's
own (``forecast.py``: the same slice, the same fit schedule, the same filter, the same ordering check), so the unwrapped run at
``gamma = 0`` is the ladder's forecast to the last digit, which the bake asserts day by day.

A forecast that fails holds the previous day's, as the ladder does, and is counted (``n_fallback_days``); the first day of a window
never falls back. Each (window, model) is computed once for both levels because a GARCH fit does not depend on the level, and is
cached by a hash of the series, the hyperparameters, the engine pin and this method's constants.

The evaluation (plan section 4, BS-16), written before the first run and never changed after it:

- a window is *passed* by a model at a level when the Kupiec proportion-of-failures test and the Christoffersen conditional
  coverage test both have p at least 0.05 (a test that did not run passes nothing);
- the hypothesis holds for a model at a level (a *cell*) when the wrapped model passes in at least one more of the three stress
  windows than the unwrapped one and its FZ0 is worse than the unwrapped one by at most 5 percent in every stress window; it holds
  as a whole when all six cells hold and it is not refuted;
- it is refuted when a wrapped model fails the Christoffersen independence test (p below 0.05) in equity-2007-09;
- the result is reported whatever it is: the verdict is a function of the rows (``hypothesis``), recomputed by a test from the
  committed documents.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from riskvalidation.market import conformal as rv_cf
from riskvalidation.validation import market as rv_val

from ...core.text import number, percent
from . import forecast as fc
from .constants import LEVELS, WINDOWS
from .forecast import Hyper, Spec

GAMMA = 0.005                       # the engine's default step, fixed before any run
LEVEL_MIN, LEVEL_MAX = rv_cf.LEVEL_MIN, rv_cf.LEVEL_MAX
WRAPPED = ("hs-250", "garch-t", "fhs")
STRESS_WINDOWS = ("equity-2007-09", "equity-2020", "rates-2022")
INDEPENDENCE_WINDOW = "equity-2007-09"
PASS_P = 0.05
FZ0_TOLERANCE = 0.05
METHOD_VERSION = "1"                # part of the cache key: bump when a constant or the procedure above changes
SOURCE = ("Gibbs and Candes 2021, NeurIPS 34, arXiv 2106.00170; Christoffersen 1998, Int. Econ. Rev. 39(4); "
          "Acerbi and Szekely 2014, Risk; Fissler and Ziegel 2016, Ann. Statist. 44(4)")


def t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def r9(x: float) -> float:
    """Nine significant digits, the precision the writer keeps (``documents.r9``): scores recompute from the stored arrays."""
    return float(f"{x:.9g}")


# ------------------------------------------------------------------------------------------------------------------- the model

class ModelForecaster:
    """A ladder model as the engine's wrapper sees it: ``forecaster(t, level) -> (var, es)`` in the return convention.

    Day ``t`` is the position in the series; the model reads ``y[t - w:t]`` only. The GARCH-family context of a day (the fit on its
    refit schedule and the filter) is computed once per day and shared by every level and every pass; the passes visit the days in
    order, so the refit schedule is that of the ladder."""

    def __init__(self, spec: Spec, y: np.ndarray, first: int, hp: Hyper):
        self.spec, self.y, self.first, self.hp = spec, np.asarray(y, dtype=float), int(first), hp
        self._out = fc.ModelRun(spec.model_id, {}, {})
        self._fits: dict[Any, Any] = {}
        self._ctx: dict[int, Any] = {}
        self._last: tuple[float, float] | None = None
        self.fallback_days: set[int] = set()

    def __call__(self, day: int, level: float) -> tuple[float, float]:
        spec, hp = self.spec, self.hp
        if day == self.first:
            self._last = None
        try:
            win = fc._slice(self.y, day, fc.look_back(spec, hp), spec.kind)
            if day not in self._ctx:
                try:
                    self._ctx[day] = fc._day_context(spec, win, day - self.first, hp, self._out, self._fits)
                except (ValueError, RuntimeError, FloatingPointError, np.linalg.LinAlgError) as exc:
                    self._ctx[day] = exc                                    # a failed day fails the same way in every pass
            ctx = self._ctx[day]
            if isinstance(ctx, Exception):
                raise ctx
            ve = fc._ordered(fc._one_day(spec, win, level, day - self.first, hp, self._out, self._fits, ctx, True), spec.model_id,
                             float(win.std()))
        except (ValueError, RuntimeError, FloatingPointError, np.linalg.LinAlgError) as exc:
            if self._last is None:
                raise RuntimeError(f"{spec.model_id}: no usable forecast on the first day: {exc}") from exc
            self.fallback_days.add(int(day))
            ve = self._last
        self._last = ve
        return ve


@dataclass
class WrapRun:
    """One model in one window: the wrapped and the unwrapped (``gamma = 0``) run at each level, from the engine."""

    model_id: str
    first: int
    wrapped: dict[float, rv_cf.AciResult]
    plain: dict[float, rv_cf.AciResult]
    n_fallback_days: int = 0
    seconds: float = 0.0
    cached: bool = False
    meta: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        def one(r: rv_cf.AciResult) -> dict:
            return {"alpha": r.alpha, "gamma": r.gamma, "start": r.start, "level_min": r.level_min, "level_max": r.level_max,
                    "levels": r.levels.tolist(), "var": r.var.tolist(), "es": r.es.tolist(), "hits": r.hits.astype(int).tolist(),
                    "clipped": r.clipped.astype(int).tolist(), "n_clipped": r.n_clipped}
        return {"model_id": self.model_id, "first": self.first, "n_fallback_days": self.n_fallback_days, "seconds": self.seconds,
                "wrapped": {repr(a): one(r) for a, r in self.wrapped.items()}, "plain": {repr(a): one(r) for a, r in self.plain.items()}}

    @staticmethod
    def from_json(d: dict) -> WrapRun:
        def one(x: dict) -> rv_cf.AciResult:
            return rv_cf.AciResult(alpha=x["alpha"], gamma=x["gamma"], start=x["start"], level_min=x["level_min"], level_max=x["level_max"],
                                   levels=np.array(x["levels"]), var=np.array(x["var"]), es=np.array(x["es"]),
                                   hits=np.array(x["hits"], dtype=bool), clipped=np.array(x["clipped"], dtype=bool), n_clipped=x["n_clipped"])
        return WrapRun(d["model_id"], d["first"], {float(a): one(x) for a, x in d["wrapped"].items()},
                       {float(a): one(x) for a, x in d["plain"].items()}, d["n_fallback_days"], d["seconds"], True)


def _forecaster(spec: Spec, y: np.ndarray, first: int, hp: Hyper):
    if spec.kind == "hs":
        return rv_cf.historical_forecaster(y, fc.look_back(spec, hp)), None
    f = ModelForecaster(spec, y, first, hp)
    return f, f


def wrap_model(spec: Spec, y: np.ndarray, idx: np.ndarray, hp: Hyper, levels: tuple[float, ...] = LEVELS) -> WrapRun:
    """The engine's ACI wrapper around ``spec`` over the days ``idx`` of ``y`` (contiguous positions), and the same model unwrapped.

    The returns after the last forecast day are cut off: the wrapper walks to the end of the series it is given."""
    t0 = time.perf_counter()
    idx = np.asarray(idx, dtype=int)
    first, last = int(idx[0]), int(idx[-1])
    if not np.array_equal(idx, np.arange(first, last + 1)):
        raise ValueError("the forecast days must be contiguous positions of the series")
    series = np.asarray(y, dtype=float)[: last + 1]
    forecaster, tracked = _forecaster(spec, series, first, hp)
    wrapped, plain = {}, {}
    for a in levels:
        wrapped[a] = rv_cf.aci_var_es(series, forecaster, a, GAMMA, first, LEVEL_MIN, LEVEL_MAX)
        plain[a] = rv_cf.aci_var_es(series, forecaster, a, 0.0, first, LEVEL_MIN, LEVEL_MAX)
    return WrapRun(spec.model_id, first, wrapped, plain, len(tracked.fallback_days) if tracked else 0, time.perf_counter() - t0)


# ------------------------------------------------------------------------------------------------------------------- cache and pool

def fingerprint(y: np.ndarray, idx: np.ndarray, hp: Hyper, spec: Spec, engine: str) -> str:
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(np.asarray(y, dtype=float)[: int(idx[-1]) + 1]).tobytes())
    h.update(np.ascontiguousarray(idx, dtype=np.int64).tobytes())
    h.update(json.dumps([hp.to_json(), spec.model_id, engine, GAMMA, LEVEL_MIN, LEVEL_MAX, list(LEVELS), METHOD_VERSION], sort_keys=True).encode())
    return h.hexdigest()[:20]


def _task(args: tuple) -> tuple[str, str, dict]:
    window_id, model_id, y, idx, hp, path = args
    doc = wrap_model(fc.SPEC_BY_ID[model_id], y, idx, hp).to_json()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(doc), encoding="utf-8")
    tmp.replace(path)
    return window_id, model_id, doc


def wrap_windows(windows: dict[str, tuple[np.ndarray, np.ndarray]], hp: Hyper, cache_dir: Path, engine: str,
                 model_ids: tuple[str, ...] = WRAPPED, workers: int = 1, log=print) -> dict[str, dict[str, WrapRun]]:
    """Every wrapped model of every window, from the cache where it holds and from the engine where it does not."""
    out: dict[str, dict[str, WrapRun]] = {w: {} for w in windows}
    todo = []
    for wid, (y, idx) in windows.items():
        for mid in model_ids:
            path = Path(cache_dir) / f"conformal.{wid}.{mid}.{fingerprint(y, idx, hp, fc.SPEC_BY_ID[mid], engine)}.json"
            if path.exists():
                out[wid][mid] = WrapRun.from_json(json.loads(path.read_text(encoding="utf-8")))
            else:
                todo.append((wid, mid, y, idx, hp, str(path)))
    todo.sort(key=lambda a: -(a[3].size * (1 if a[1] == "hs-250" else 8)))
    log(f"conformal: {sum(len(v) for v in out.values())} cached, {len(todo)} to run with {workers} worker(s)")
    if workers <= 1 or len(todo) <= 1:
        results = [_task(a) for a in todo]
    else:
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ[var] = "1"
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = []
            for r in pool.map(_task, todo):
                log(f"  done {r[0]} {r[1]} in {r[2]['seconds']:.0f}s")
                results.append(r)
    for wid, mid, doc in results:
        out[wid][mid] = WrapRun.from_json({**doc, "seconds": doc["seconds"]})
        out[wid][mid].cached = False
    return out


# ------------------------------------------------------------------------------------------------------------------- the rows

def passes_coverage(score: dict) -> bool:
    """Kupiec and conditional coverage both at least ``PASS_P``; a p-value that was not evaluated is not a pass."""
    kp, cc = score.get("kupiec_p"), score.get("conditional_coverage_p")
    return kp is not None and cc is not None and kp >= PASS_P and cc >= PASS_P


def _p(res) -> float | None:
    p = res.p_value
    return None if p is None or p != p else float(p)


def _score(spec_id: str, a: float, loss: np.ndarray, var: np.ndarray, es: np.ndarray, hp: Hyper, z2_draws: int) -> dict:
    """The scores of one VaR and ES sequence, on the rounded positive-loss arrays the documents store: the engine's coverage tests,
    the Acerbi-Szekely test against the tail-consistent null of the ladder (``documents.tail_null``), and the engine's FZ0 and Z2."""
    from . import documents as docs

    flags = (loss > var).astype(int)
    kup = rv_val.kupiec_pof(flags, a, spec_id)
    ind = rv_val.christoffersen_independence(flags, a, spec_id)
    cc = rv_val.christoffersen_conditional_coverage(flags, a, spec_id)
    zs: list[float] = []
    az = rv_val.acerbi_szekely(loss, var, es, a, docs.tail_null(var, es, a, zs), spec_id, "Z2", z2_draws, hp.seed)
    sc = rv_cf.forecast_scores(-loss, -var, -es, a)
    gates = (kup, cc, az)
    n = int(loss.size)
    out = {"n_exceedances": int(flags.sum()), "expected_exceedances": a * n, "hit_rate": float(flags.sum()) / n,
           "kupiec_p": _p(kup), "independence_p": _p(ind), "conditional_coverage_p": _p(cc), "es_test_p": _p(az),
           "es_test_light": az.light.value, "fz0_mean": sc.fz0_mean, "z2": sc.z2,
           "eligible": not any(g.light.value == "red" for g in gates)}
    out["passes_coverage"] = passes_coverage(out)
    return out


def _stats(x: np.ndarray) -> dict:
    return {"min": float(x.min()), "mean": float(x.mean()), "max": float(x.max())}


def ladder_rank(models: list[dict], a: float, fz0: float | None) -> int | None:
    """1 plus the number of ladder models with a lower average FZ0 at the level: the place of a score among the ladder's."""
    if fz0 is None:
        return None
    return 1 + sum(1 for m in models for lv in m["by_level"] if lv["alpha"] == a and lv["fz0_mean"] is not None and lv["fz0_mean"] < fz0)


def build_rows(spec: Spec, loss: np.ndarray, run: WrapRun, models: list[dict], hp: Hyper, z2_draws: int) -> list[dict]:
    """The rows of one model in one window, one per level: wrapped and unwrapped scores, the change of FZ0, the level path.

    ``loss`` is the window's realised positive loss rounded to nine digits (``documents.r9``), ``models`` the window's ladder rows
    (``outputs.models``). The unwrapped run is checked against the ladder's own exceedance days: it must be the same model."""
    rows = []
    ladder_of = {m["model_id"]: m for m in models}.get(spec.model_id)
    for a in LEVELS:
        w, u = run.wrapped[a], run.plain[a]
        var_w, es_w = (np.array([r9(-x) for x in z]) for z in (w.var, w.es))
        var_u, es_u = (np.array([r9(-x) for x in z]) for z in (u.var, u.es))
        if not (np.all(var_w > 0) and np.all(var_u > 0)):
            raise ValueError(f"{spec.model_id}@{a}: a VaR is not a positive loss")
        sw = _score(spec.model_id, a, loss, var_w, es_w, hp, z2_draws)
        su = _score(spec.model_id, a, loss, var_u, es_u, hp, z2_draws)
        exc_w = [int(i) for i in np.flatnonzero(loss > var_w)]
        if exc_w != [int(i) for i in np.flatnonzero(w.hits)]:
            raise ValueError(f"{spec.model_id}@{a}: the wrapper's hits are not the exceedances of its stored arrays")
        lv = next((x for x in (ladder_of or {}).get("by_level", []) if x["alpha"] == a), None)
        if lv is not None and [int(i) for i in np.flatnonzero(loss > var_u)] != lv["exceedance_days"]:
            raise ValueError(f"{spec.model_id}@{a}: the unwrapped run is not the ladder's model (its exceedance days differ)")
        change = None
        if sw["fz0_mean"] is not None and su["fz0_mean"] is not None and su["fz0_mean"] != 0.0:
            change = (sw["fz0_mean"] - su["fz0_mean"]) / abs(su["fz0_mean"])
        rows.append({
            "model_id": spec.model_id, "rung": spec.rung, "alpha": a, "n_days": int(loss.size),
            "unwrapped": {**su, "ladder_rank": ladder_rank(models, a, su["fz0_mean"])},
            "wrapped": {**sw, "ladder_rank": ladder_rank(models, a, sw["fz0_mean"])},
            "fz0_change": change, "n_clipped": int(w.n_clipped), "n_fallback_days": int(run.n_fallback_days),
            "working_level": _stats(w.levels),
            "series": {"working_level": [r9(x) for x in w.levels], "var": [float(x) for x in var_w], "es": [float(x) for x in es_w],
                       "exceedance_days": exc_w}})
    return rows


# ------------------------------------------------------------------------------------------------------------------- the verdict

def _pct(x: float, lang: str) -> str:
    return percent(x, 1, lang=lang)


def hypothesis(rows_by_window: dict[str, list[dict]], n_days: dict[str, int] | None = None) -> dict:
    """The verdict of BS-16 from the rows of the three stress windows, by the rule of the module docstring (a function of the rows)."""
    cells = []
    for m in WRAPPED:
        for a in LEVELS:
            per = {w: next(r for r in rows_by_window[w] if r["model_id"] == m and r["alpha"] == a) for w in STRESS_WINDOWS}
            un = sum(passes_coverage(r["unwrapped"]) for r in per.values())
            wr = sum(passes_coverage(r["wrapped"]) for r in per.values())
            changes = [r["fz0_change"] for r in per.values()]
            worst = None if any(c is None for c in changes) else max(changes)
            cells.append({"model_id": m, "alpha": a, "windows_passed_unwrapped": un, "windows_passed_wrapped": wr, "extra_windows": wr - un,
                          "worst_fz0_change": worst, "holds": wr - un >= 1 and worst is not None and worst <= FZ0_TOLERANCE})
    indep = []
    for m in WRAPPED:
        for a in LEVELS:
            r = next(r for r in rows_by_window[INDEPENDENCE_WINDOW] if r["model_id"] == m and r["alpha"] == a)
            p = r["wrapped"]["independence_p"]
            indep.append({"model_id": m, "alpha": a, "independence_p": p, "fails": p is not None and p < PASS_P})
    refuted = any(x["fails"] for x in indep)
    n_hold = sum(c["holds"] for c in cells)
    holds = n_hold == len(cells) and not refuted
    sizes = n_days or {}
    total = sum(sizes.get(w, 0) for w in STRESS_WINDOWS)
    def verdict(lang: str) -> str:
        k, n = number(n_hold, lang=lang), number(len(cells), lang=lang)
        gain = number(sum(c["extra_windows"] for c in cells), lang=lang)
        worst = [c["worst_fz0_change"] for c in cells if c["worst_fz0_change"] is not None]
        w = _pct(max(worst), lang) if worst else "-"
        if lang == "en":
            core = (f"The hypothesis holds in {k} of {n} cells (model by tail level): the wrapped models gain {gain} stress-window passes in all, "
                    f"the worst FZ0 change in any stress window is {w}, and the wrapper "
                    + ("fails" if refuted else "does not fail") + f" the independence test in {INDEPENDENCE_WINDOW}.")
            return core + (" It holds as a whole." if holds else (" It is refuted." if refuted else " It does not hold as a whole."))
        core = (f"La hipótesis se cumple en {k} de {n} celdas (modelo por nivel de cola): los modelos envueltos ganan {gain} aprobaciones de ventanas de estrés "
                f"en total, el peor cambio de FZ0 en una ventana de estrés es {w}, y el envoltorio "
                + ("falla" if refuted else "no falla") + f" la prueba de independencia en {INDEPENDENCE_WINDOW}.")
        return core + (" Se cumple en conjunto." if holds else (" Queda refutada." if refuted else " No se cumple en conjunto."))
    return {
        "id": "BS-16",
        "statement": t("HS-250, GARCH-t and FHS, wrapped by adaptive conformal inference, pass the coverage tests in at least one more stress window than unwrapped, without their average FZ0 worsening by more than 5 percent.",
                       "HS-250, GARCH-t y FHS, envueltos por inferencia conforme adaptativa, aprueban las pruebas de cobertura en al menos una ventana de estrés más que sin envolver, sin que su FZ0 medio empeore más de 5 por ciento."),
        "refuted_if": t("The wrapper fails the independence test in equity-2007-09.", "El envoltorio falla la prueba de independencia en equity-2007-09."),
        "pass_rule": t("A window is passed when the Kupiec and the conditional coverage p-values are both at least 0.05; a test that did not run passes nothing.",
                       "Una ventana se aprueba cuando los valores p de Kupiec y de cobertura condicional son ambos de al menos 0,05; una prueba que no corrió no aprueba nada."),
        "run": {"gamma": GAMMA, "level_min": LEVEL_MIN, "level_max": LEVEL_MAX, "stress_windows": list(STRESS_WINDOWS),
                "fz0_tolerance": FZ0_TOLERANCE, "pass_p": PASS_P, "n_stress_days": total, "n_runs": len(cells) * len(STRESS_WINDOWS)},
        "cells": cells, "independence_2007_09": indep, "n_cells": len(cells), "n_cells_hold": n_hold, "refuted": refuted, "holds": holds,
        "verdict": t(verdict("en"), verdict("es"))}


def block(rows: list[dict], hypothesis_doc: dict | None) -> dict:
    """The ``outputs.conformal`` block of a window document."""
    return {
        "method": {
            "id": "BS-16", "tier": "beyond",
            "title": t("Adaptive conformal recalibration of the VaR", "Recalibración conforme adaptativa del VaR"),
            "source": SOURCE, "gamma": GAMMA, "level_min": LEVEL_MIN, "level_max": LEVEL_MAX, "first_level": "alpha",
            "wrapped_models": list(WRAPPED),
            "description": t("The working tail level starts at the target and moves after each day by gamma times the target minus the hit (a hit lowers it, a quiet day raises it); the model is asked for its VaR and ES at that level. The step and the band are fixed before any run; the unwrapped run is the ladder's own model.",
                             "El nivel de cola de trabajo parte del objetivo y se mueve después de cada día en gamma por el objetivo menos la excedencia (una excedencia lo baja, un día tranquilo lo sube); al modelo se le pide su VaR y su ES en ese nivel. El paso y la banda se fijan antes de cualquier corrida; la corrida sin envolver es el modelo mismo de la escalera.")},
        "rows": rows, "hypothesis": hypothesis_doc}
