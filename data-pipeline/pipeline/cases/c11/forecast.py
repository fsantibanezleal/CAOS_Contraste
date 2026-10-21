"""The strictly rolling one-step forecasts of the ladder (SDD C11, dossier 05 A.2 and "Candidate cases and leakage-safe
evaluation windows").

For the forecast day at position ``i`` of the return series ``y`` (``y[i]`` is that day's return), every model sees only
``y[max(0, i - w):i]``: the ``w`` days before it, never the day itself. A model that is refitted only every ``R`` forecast days
keeps its parameters between refits and runs its filter over the current window, so the parameters of a day come from data
before an earlier day and never from a later one. Every VaR, ES, fit and filter is ``riskvalidation.market``; this module
only slices the window, schedules the refits and collects the numbers (ADR-0069). Forecasts are in the engine's return
convention (negative); the conversion to positive losses is made once, in ``documents``.

A fit that fails (not converged, or a recursion that leaves its domain) keeps the previous fit and is counted
(``n_failures``; with no previous fit the GARCH family uses the unconverged one); a day on which no usable forecast exists holds the previous day's forecast and is counted
(``n_fallback_days``). Both counts are in the models document. The first day of a window never falls back: it raises.

Refit frequency: GARCH family and filtered HS every ``garch_refit_every_days`` forecast days, CAViaR every
``caviar_refit_every_days``, GAS-FZ every ``gas_refit_every_days``; the conditional EVT and the ES step of CAViaR are
refitted every day. Each window's forecasts are cached (``cache_dir``), keyed by a hash of the series, the hyperparameters
and the engine, so a re-run reuses them.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from riskvalidation.market import caviar as rv_caviar
from riskvalidation.market import evt as rv_evt
from riskvalidation.market import garch as rv_garch
from riskvalidation.market import gas_fz as rv_gas
from riskvalidation.market import historical as rv_hist
from riskvalidation.market import parametric as rv_par

from .constants import LEVELS


@dataclass(frozen=True)
class Hyper:
    """The hyperparameters fixed once on 1995-01-01 to 2003-12-31 (decision D1); the counts and the seed are fixed by the
    compute budget and the determinism rule, not tuned."""

    estimation_window_days: int = 1000
    ewma_lambda: float = 0.94
    age_weight_lambda: float = 0.98
    evt_threshold_fraction: float = 0.10
    garch_refit_every_days: int = 1
    caviar_refit_every_days: int = 5
    gas_refit_every_days: int = 20
    caviar_n_starts: int = 20
    gas_n_starts: int = 20
    seed: int = 42

    def to_json(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Spec:
    model_id: str
    rung: str
    kind: str                       # hs, awhs, dn, cf, ewma, garch, fhs, evt, caviar, caviar-es, gas
    arg: str                        # the variant of the kind: 250, garch/gjr/egarch, sav/as, one-factor/two-factor/hybrid
    en: str
    es: str
    source: str
    innovation: str
    es_method: str
    forecasts_es: bool


#: the ladder of dossier 05 "Method ladders", rung 1 to 9; rung 10 is the challenger that is never trained here
LADDER: tuple[Spec, ...] = (
    Spec("hs-250", "R1", "hs", "250", "Historical simulation, 250 days", "Simulación histórica, 250 días",
         "historical simulation (textbook; Pritsker 2001)", "empirical", "tail mean of the sorted window", True),
    Spec("hs-500", "R1", "hs", "500", "Historical simulation, 500 days", "Simulación histórica, 500 días",
         "historical simulation (textbook; Pritsker 2001)", "empirical", "tail mean of the sorted window", True),
    Spec("awhs", "R2", "awhs", "250", "Age-weighted historical simulation", "Simulación histórica ponderada por edad",
         "Boudoukh, Richardson and Whitelaw 1998, Risk 11(5)", "empirical", "tail integral of the interpolated weighted quantile function", True),
    Spec("dn-rolling", "R3", "dn", "", "Delta-normal, rolling moments", "Delta-normal, momentos móviles",
         "RiskMetrics Technical Document 1996", "normal", "normal ES from the window mean and volatility", True),
    Spec("cf-rolling", "R3", "cf", "", "Cornish-Fisher VaR, rolling moments", "VaR de Cornish-Fisher, momentos móviles",
         "Cornish and Fisher 1938, Rev. Inst. Int. Statistique 5(4)", "normal", "none: the Cornish-Fisher expansion gives the VaR only", False),
    Spec("ewma", "R4", "ewma", "", "EWMA (RiskMetrics)", "EWMA (RiskMetrics)",
         "RiskMetrics Technical Document 1996, section 5.3.2", "normal", "normal ES from the EWMA volatility", True),
    Spec("garch-t", "R5", "garch", "garch", "GARCH(1,1) with Student-t innovations", "GARCH(1,1) con innovaciones t de Student",
         "Bollerslev 1986, J. Econometrics 31(3)", "student-t", "Student-t tail mean of the unit-variance innovation", True),
    Spec("gjr-t", "R5", "garch", "gjr", "GJR-GARCH with Student-t innovations", "GJR-GARCH con innovaciones t de Student",
         "Glosten, Jagannathan and Runkle 1993, J. Finance 48(5)", "student-t", "Student-t tail mean of the unit-variance innovation", True),
    Spec("egarch-t", "R5", "garch", "egarch", "EGARCH with Student-t innovations", "EGARCH con innovaciones t de Student",
         "Nelson 1991, Econometrica 59(2)", "student-t", "Student-t tail mean of the unit-variance innovation", True),
    Spec("fhs", "R6", "fhs", "", "Filtered historical simulation", "Simulación histórica filtrada",
         "Barone-Adesi, Giannopoulos and Vosper 1999, J. Futures Markets 19(5)", "empirical",
         "tail mean of the GARCH-filtered standardised residuals", True),
    Spec("evt-mf", "R7", "evt", "", "Conditional EVT (McNeil and Frey)", "EVT condicional (McNeil y Frey)",
         "McNeil and Frey 2000, J. Empirical Finance 7(3-4)", "gpd-tail", "GPD tail ES, undefined for xi at or above 1", True),
    Spec("caviar-sav", "R8", "caviar", "sav", "CAViaR, symmetric absolute value", "CAViaR, valor absoluto simétrico",
         "Engle and Manganelli 2004, JBES 22(4)", "none", "none: CAViaR forecasts the VaR only", False),
    Spec("caviar-as", "R8", "caviar", "as", "CAViaR, asymmetric slope", "CAViaR, pendiente asimétrica",
         "Engle and Manganelli 2004, JBES 22(4)", "none", "none: CAViaR forecasts the VaR only", False),
    Spec("caviar-es", "R8", "caviar-es", "sav", "ES-CAViaR (two-step, Taylor)", "ES-CAViaR (dos pasos, Taylor)",
         "Taylor 2019, JBES 37(1); two-step estimation declared in the engine (D-10)", "none",
         "autoregressive gap below the CAViaR VaR, fitted by the asymmetric Laplace likelihood", True),
    Spec("gas-fz-1", "R9", "gas", "one-factor", "GAS-FZ, one factor", "GAS-FZ, un factor",
         "Patton, Ziegel and Chen 2019, J. Econometrics 211(2)", "none", "joint VaR and ES from one dynamic factor (FZ0 estimation)", True),
    Spec("gas-fz-2", "R9", "gas", "two-factor", "GAS-FZ, two factors", "GAS-FZ, dos factores",
         "Patton, Ziegel and Chen 2019, J. Econometrics 211(2)", "none", "joint VaR and ES from two dynamic factors (FZ0 estimation)", True),
    Spec("gas-hybrid", "R9", "gas", "hybrid", "Hybrid GARCH-FZ", "GARCH-FZ híbrido",
         "Patton, Ziegel and Chen 2019, J. Econometrics 211(2), eq 27", "none", "one dynamic factor with a log absolute return term (FZ0 estimation)", True),
)
SPEC_BY_ID = {s.model_id: s for s in LADDER}
CHALLENGER = {"model_id": "nn-fz", "rung": "R10", "en": "Quantile network trained on FZ0 (challenger)",
              "es": "Red de cuantiles entrenada con FZ0 (retador)", "source": "arXiv 2606.04576 (preprint; challenger only)",
              "reason": "challenger only: it must enter the 90 percent MCS on FZ0 out of sample, and the U8 bake does not train it"}

#: a tail VaR below this share of the estimation window's standard deviation is a collapsed fit, not a forecast
MIN_VAR_SCALE = 0.1
PARAM_NAMES = {
    "sav": ("b1", "b2", "b3"), "as": ("b1", "b2", "b3", "b4"),
    "one-factor": ("beta", "gamma", "a", "b"), "hybrid": ("beta", "gamma", "delta", "a", "b"),
    "two-factor": ("w_v", "w_e", "B_vv", "B_ee", "A_vv", "A_ve", "A_ev", "A_ee"),
}
MIN_OBS = {"hs": 250, "awhs": 250, "dn": 60, "cf": 60, "ewma": 60, "garch": 250, "fhs": 250, "evt": 250, "caviar": 500,
           "caviar-es": 500, "gas": 500}


@dataclass
class ModelRun:
    """The forecasts of one model in one window, in the return convention; ``es`` is NaN where undefined or not forecast."""

    model_id: str
    var: dict[float, np.ndarray]
    es: dict[float, np.ndarray]
    n_refits: int = 0
    n_failures: int = 0
    n_fallback_days: int = 0
    params: dict[str, list[float]] = field(default_factory=dict)
    seconds: float = 0.0
    cached: bool = False

    def to_json(self) -> dict:
        return {"model_id": self.model_id, "n_refits": self.n_refits, "n_failures": self.n_failures,
                "n_fallback_days": self.n_fallback_days, "params": self.params, "seconds": self.seconds,
                "var": {repr(a): v.tolist() for a, v in self.var.items()},
                "es": {repr(a): [None if not np.isfinite(x) else x for x in v] for a, v in self.es.items()}}

    @staticmethod
    def from_json(d: dict) -> ModelRun:
        return ModelRun(d["model_id"], {float(a): np.array(v, dtype=float) for a, v in d["var"].items()},
                        {float(a): np.array([np.nan if x is None else x for x in v], dtype=float) for a, v in d["es"].items()},
                        d["n_refits"], d["n_failures"], d["n_fallback_days"], d["params"], d["seconds"], True)


def look_back(spec: Spec, hp: Hyper) -> int:
    """The nominal estimation window of a model, in observed days."""
    if spec.kind == "hs":
        return int(spec.arg)
    if spec.kind == "awhs":
        return int(spec.arg)
    return hp.estimation_window_days


def _slice(y: np.ndarray, i: int, w: int, kind: str) -> np.ndarray:
    w_eff = min(w, i)
    if w_eff < MIN_OBS[kind]:
        raise ValueError(f"only {w_eff} observed days before position {i}; the {kind} model needs {MIN_OBS[kind]}")
    return y[i - w_eff:i]


def _record(params: dict[str, list[float]], names: tuple[str, ...], values: np.ndarray) -> None:
    for n, v in zip(names, values, strict=True):
        params.setdefault(n, []).append(float(v))


def run_model(spec: Spec, y: np.ndarray, idx: np.ndarray, hp: Hyper, levels: tuple[float, ...] = LEVELS) -> ModelRun:
    """The one-step forecasts of ``spec`` for the days at positions ``idx`` of ``y``; each sees ``y[:i]`` only."""
    t0 = time.perf_counter()
    n = idx.size
    out = ModelRun(spec.model_id, {a: np.full(n, np.nan) for a in levels}, {a: np.full(n, np.nan) for a in levels})
    kind, w = spec.kind, look_back(spec, hp)
    fits: dict[Any, Any] = {}
    last: dict[float, tuple[float, float]] = {}
    for k, i in enumerate(map(int, idx)):
        win = _slice(y, i, w, kind)
        try:
            ctx = _day_context(spec, win, k, hp, out, fits)
            for j, a in enumerate(levels):
                last[a] = _ordered(_one_day(spec, win, a, k, hp, out, fits, ctx, j == 0), spec.model_id, float(win.std()))
        except (ValueError, RuntimeError, FloatingPointError, np.linalg.LinAlgError) as exc:
            if not last or k == 0:
                raise RuntimeError(f"{spec.model_id}: no usable forecast on the first day: {exc}") from exc
            out.n_failures += 1
            out.n_fallback_days += 1
        for a in levels:
            out.var[a][k], out.es[a][k] = last[a]
    out.seconds = time.perf_counter() - t0
    return out


def _ordered(ve: tuple[float, float], model_id: str, scale: float = 0.0) -> tuple[float, float]:
    """The engine's ES is at most its VaR (return convention). A last-digit excess (a tail integral that meets the quantile, as in
    the age-weighted rule when the level falls in the first knot) is rounding and is set equal to the VaR; a larger one is an error. A VaR that is not a loss (a CAViaR recursion that
    crosses zero) or one below a tenth of the window's standard deviation (a GAS recursion that collapsed) is refused, and the day falls back to the previous forecast and is counted."""
    v, e = ve
    if not v < 0.0:
        raise ValueError(f"{model_id}: the VaR {v} is not a loss; the day holds the previous forecast and is counted")
    if scale > 0.0 and -v < MIN_VAR_SCALE * scale:
        raise ValueError(f"{model_id}: the VaR {v} is below {MIN_VAR_SCALE} of the window's standard deviation: a degenerate fit")
    if np.isfinite(e) and e > v:
        if e - v > 1e-12 * max(1.0, abs(v)):
            raise ValueError(f"{model_id}: the ES {e} is above the VaR {v}")
        e = v
    return v, e


def _refit_due(k: int, every: int, have: bool) -> bool:
    return (not have) or k % every == 0


def _day_context(spec: Spec, win: np.ndarray, k: int, hp: Hyper, out: ModelRun, fits: dict) -> dict:
    """What a day needs once for every level: the GARCH fit (on its schedule) and the filter run through the window."""
    if spec.kind not in ("garch", "fhs"):
        return {}
    gk, inn = (spec.arg, "student-t") if spec.kind == "garch" else ("garch", "normal")
    if _refit_due(k, hp.garch_refit_every_days, "garch" in fits):
        fit = rv_garch.fit_garch(win, kind=gk, innovation=inn, mean="constant")
        out.n_refits += 1
        if not fit.converged:
            out.n_failures += 1
        if fit.converged or "garch" not in fits:
            # with no converged fit to keep, the unconverged one is used (an integrated-GARCH boundary: the filter and its forecast
            # are still defined) and counted as a failure; it is replaced at the next refit that converges
            fits["garch"] = fit
            for n_, v_ in fit.params.items():
                out.params.setdefault(n_, []).append(float(v_))
    fit = fits["garch"]
    return {"fit": fit, "flt": rv_garch.garch_filter(fit, win)}


def _one_day(spec: Spec, win: np.ndarray, a: float, k: int, hp: Hyper, out: ModelRun, fits: dict, ctx: dict,
             first_level: bool) -> tuple[float, float]:
    kind = spec.kind
    nan = float("nan")
    if kind == "hs":
        return rv_hist.historical_var_es(win, a, win.size)
    if kind == "awhs":
        return rv_hist.age_weighted_var_es(win, a, hp.age_weight_lambda, win.size)
    if kind == "dn":
        return rv_par.delta_normal_var_es(float(win.mean()), float(win.std(ddof=1)), a)
    if kind == "cf":
        m, s = float(win.mean()), float(win.std(ddof=1))
        z = (win - m) / s
        r = rv_par.cornish_fisher_var(m, s, float(np.mean(z ** 3)), float(np.mean(z ** 4) - 3.0), a)
        if first_level:
            out.params.setdefault("expansion_valid", []).append(1.0 if r.valid else 0.0)
        return r.var, nan
    if kind == "ewma":
        return rv_par.ewma_var_es(win, hp.ewma_lambda, a, float(win.var()))
    if kind == "fhs":
        flt = ctx["flt"]
        return rv_hist.filtered_hs_var_es(flt.std_residuals, flt.mu_next, flt.sigma_next, a)
    if kind == "garch":
        flt = ctx["flt"]
        q, eq = rv_garch.innovation_var_es(ctx["fit"], a)
        return flt.mu_next + flt.sigma_next * q, flt.mu_next + flt.sigma_next * eq
    if kind == "evt":
        r = rv_evt.conditional_evt_forecast(win, a, hp.evt_threshold_fraction, kind="garch")
        if first_level:
            out.n_refits += 1
        out.params.setdefault(f"xi@{a:g}", []).append(float(r.xi))
        return r.var, (nan if r.es is None else r.es)
    if kind in ("caviar", "caviar-es"):
        if _refit_due(k, hp.caviar_refit_every_days, a in fits):
            fit = rv_caviar.fit_caviar(win, a, spec.arg, hp.caviar_n_starts, hp.seed)
            out.n_refits += 1
            if fit.converged or a not in fits:
                fits[a] = fit
                _record(out.params, tuple(f"{n_}@{a:g}" for n_ in PARAM_NAMES[spec.arg]), fit.params)
            else:
                out.n_failures += 1
        if kind == "caviar":
            return rv_caviar.caviar_var_forecast(fits[a], win), nan
        r = rv_caviar.caviar_es_fit(fits[a], win)
        return r.var, r.es
    if kind == "gas":
        if _refit_due(k, hp.gas_refit_every_days, a in fits):
            fits[a] = _fit_gas(spec.arg, win, a, hp)
            out.n_refits += 1
            if not fits[a].converged:
                out.n_failures += 1
            _record(out.params, tuple(f"{n_}@{a:g}" for n_ in PARAM_NAMES[spec.arg]), fits[a].params)
        try:
            return rv_gas.gas_fz_forecast(fits[a], win)
        except ValueError:
            fits[a] = _fit_gas(spec.arg, win, a, hp)          # the fitted recursion left its domain: refit now, once
            out.n_refits += 1
            out.n_failures += 1
            return rv_gas.gas_fz_forecast(fits[a], win)
    raise ValueError(f"unknown model kind {kind!r}")


def _fit_gas(variant: str, win: np.ndarray, a: float, hp: Hyper):
    if variant == "hybrid":
        return rv_gas.fit_hybrid_garch_fz(win, a, hp.gas_n_starts, hp.seed)
    return rv_gas.fit_gas_fz(win, a, variant, hp.gas_n_starts, hp.seed)


# ------------------------------------------------------------------------------------------------------------------- cache and pool

def fingerprint(y: np.ndarray, idx: np.ndarray, hp: Hyper, spec: Spec, engine: str) -> str:
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(y, dtype=float).tobytes())
    h.update(np.ascontiguousarray(idx, dtype=np.int64).tobytes())
    h.update(json.dumps([hp.to_json(), spec.model_id, engine], sort_keys=True).encode())
    return h.hexdigest()[:20]


def _task(args: tuple) -> tuple[str, str, dict]:
    window_id, model_id, y, idx, hp, path = args
    run = run_model(SPEC_BY_ID[model_id], y, idx, hp)
    doc = run.to_json()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(doc), encoding="utf-8")
    tmp.replace(path)
    return window_id, model_id, doc


def forecast_window(window_id: str, y: np.ndarray, idx: np.ndarray, hp: Hyper, cache_dir: Path, engine: str,
                    model_ids: tuple[str, ...] | None = None, workers: int = 1, log=print) -> dict[str, ModelRun]:
    """Every model of the ladder for one window, from the cache where it holds and from the engine where it does not."""
    return forecast_windows({window_id: (y, idx)}, hp, cache_dir, engine, model_ids, workers, log)[window_id]


def forecast_windows(windows: dict[str, tuple[np.ndarray, np.ndarray]], hp: Hyper, cache_dir: Path, engine: str,
                     model_ids: tuple[str, ...] | None = None, workers: int = 1, log=print) -> dict[str, dict[str, ModelRun]]:
    ids = model_ids or tuple(s.model_id for s in LADDER)
    out: dict[str, dict[str, ModelRun]] = {w: {} for w in windows}
    todo = []
    for wid, (y, idx) in windows.items():
        for mid in ids:
            path = Path(cache_dir) / f"{wid}.{mid}.{fingerprint(y, idx, hp, SPEC_BY_ID[mid], engine)}.json"
            if path.exists():
                out[wid][mid] = ModelRun.from_json(json.loads(path.read_text(encoding="utf-8")))
            else:
                todo.append((wid, mid, y, idx, hp, str(path)))
    todo.sort(key=lambda t: -(t[3].size * (3 if SPEC_BY_ID[t[1]].kind in ("gas", "caviar", "caviar-es") else 1)))
    log(f"forecast: {sum(len(v) for v in out.values())} cached, {len(todo)} to run with {workers} worker(s)")
    if workers <= 1:
        results = [_task(t) for t in todo]
    else:
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ[var] = "1"
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = []
            for r in pool.map(_task, todo):
                log(f"  done {r[0]} {r[1]} in {r[2]['seconds']:.0f}s")
                results.append(r)
    for wid, mid, doc in results:
        out[wid][mid] = ModelRun.from_json(doc)
    return out
