"""What the experiment scripts of the adaptive conformal recalibration manuscript share.

Every script is run from the repository root with the product's interpreter::

    python manuscripts/adaptive-conformal-recalibration-of-var/experiments/<script>.py

and writes one compact JSON next to itself. The scripts read the committed C11 documents (``data/derived/C11``), the
engine ``riskvalidation`` 1.1.0 and, where a model must be asked for a forecast at another tail level, the C11 pipeline's
own forecasting code (``data-pipeline/pipeline/cases/c11``) on the raw series in the device data root (the Kenneth French
series is derived-only: its returns are never written here, only scores computed from them).

Conventions. The documents store positive losses; the engine works in the return convention (negative decimals). The
helpers below convert once, at the boundary, and score every sequence with the engine's own function so that a number
here equals the number of the committed document.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
MANUSCRIPT = HERE.parent
ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived"
sys.path.insert(0, str(ROOT / "data-pipeline"))

WINDOWS = ("equity-2007-09", "equity-2020", "rates-2022", "fx-2008", "mixed-2023", "calm-2004-06")
STRESS = ("equity-2007-09", "equity-2020", "rates-2022")
LEVELS = (0.01, 0.025)
WRAPPED3 = ("hs-250", "garch-t", "fhs")
PASS_P = 0.05
GAMMA = 0.005
LEVEL_MIN, LEVEL_MAX = 1e-3, 0.25
#: seeds: one base per script so that no two scripts share a stream (each states how it derives the per-run seed)
SEED_BOOT = 20261104


def doc(window: str) -> dict:
    """A committed C11 window document."""
    return json.loads((DERIVED / "C11" / f"{window}.json").read_text(encoding="utf-8"))


def ladder_models() -> list[dict]:
    return json.loads((DERIVED / "C11" / "models-ladder.json").read_text(encoding="utf-8"))["model"]


def dump(obj: Any, name: str) -> pathlib.Path:
    """Write ``obj`` as compact, deterministic JSON beside the scripts."""
    path = HERE / name
    path.write_text(json.dumps(obj, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    return path


def load(name: str) -> Any:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------------------------- scores

def scores(loss: np.ndarray, var: np.ndarray, es: np.ndarray, alpha: float) -> dict:
    """The engine's back-tests and scores of a positive-loss VaR and ES sequence (``market.conformal.forecast_scores``).

    ``loss``, ``var`` and ``es`` are positive-loss decimals, one per day. Returns the p-values (None where the engine
    does not evaluate a test), the hit count, the mean FZ0 and the Acerbi-Szekely Z2 statistic."""
    from riskvalidation.market import conformal as cf

    s = cf.forecast_scores(-np.asarray(loss, float), -np.asarray(var, float), -np.asarray(es, float), alpha)
    return {"n": s.n, "n_hits": s.n_hits, "hit_rate": s.hit_rate, "kupiec_p": s.kupiec_p, "independence_p": s.independence_p,
            "cc_p": s.cc_p, "fz0_mean": s.fz0_mean, "z2": s.z2}


def passes(s: dict) -> bool:
    """A window is passed when the Kupiec and the conditional coverage p-values are both at least 0.05 (None passes nothing)."""
    return s["kupiec_p"] is not None and s["cc_p"] is not None and s["kupiec_p"] >= PASS_P and s["cc_p"] >= PASS_P


def fz0_days(loss: np.ndarray, var: np.ndarray, es: np.ndarray, alpha: float) -> np.ndarray:
    """The FZ0 loss of every day (engine ``market.scoring.fz0_loss``, positive-loss input)."""
    from riskvalidation.market.scoring import fz0_loss

    return np.asarray(fz0_loss(-np.asarray(loss, float), -np.asarray(var, float), -np.asarray(es, float), alpha), float)


def fz0_change(sw: dict, su: dict) -> float | None:
    """(FZ0 wrapped - FZ0 unwrapped) / |FZ0 unwrapped|; positive is worse (the engine's ``aci_compare`` definition)."""
    if sw["fz0_mean"] is None or su["fz0_mean"] is None or su["fz0_mean"] == 0.0:
        return None
    return (sw["fz0_mean"] - su["fz0_mean"]) / abs(su["fz0_mean"])


# ------------------------------------------------------------------------------------------------------------------- intervals

def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """The Wilson score interval of a binomial proportion (Brown, Cai and DasGupta 2001)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def block_bootstrap_mean(x: np.ndarray, block: int, reps: int, rng: np.random.Generator) -> np.ndarray:
    """Moving-block bootstrap draws of the mean of ``x`` (circular blocks of ``block`` days), ``reps`` draws."""
    n = x.size
    nb = int(math.ceil(n / block))
    starts = rng.integers(0, n, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    return x[idx.reshape(reps, -1)[:, :n]].mean(axis=1)


def ci95(draws: np.ndarray) -> tuple[float, float]:
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


# ------------------------------------------------------------------------------------------------------------------- real data

def _data_root() -> pathlib.Path:
    """The raw-series root of the product, from the environment variable CONTRASTE_DATA (never a path in the repository)."""
    import os

    v = os.environ.get("CONTRASTE_DATA")
    if not v:
        raise RuntimeError("set CONTRASTE_DATA to the Contraste data root (the folder that holds raw/ and cache/c11)")
    return pathlib.Path(v)


DATA_ROOT = None  # resolved on first use by data_root()


def data_root() -> pathlib.Path:
    global DATA_ROOT
    if DATA_ROOT is None:
        DATA_ROOT = _data_root()
    return DATA_ROOT


def hyper():
    """The C11 hyperparameters, read from the pipeline's cache of the 1995-2003 selection (``fix_hyperparameters``)."""
    from dataclasses import asdict

    from pipeline.cases.c11 import bake
    from pipeline.cases.c11.forecast import Hyper

    series = bake.load_series(data_root())
    hp, _ = bake.fix_hyperparameters(series, data_root() / "cache" / "c11", 1)
    return Hyper(**{**asdict(hp), "seed": 42}), series


def window_data(series=None, cache: pathlib.Path | None = None) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """``{window: (returns of the common calendar, forecast positions)}`` for the six C11 windows, from the raw series.

    ``cache`` (a ``.npz`` under the temp root) keeps the parsed returns between runs; the French series is derived-only, so
    the cache lives outside the repository and nothing of it is committed."""
    from pipeline.cases.c11 import bake, portfolio as pf

    if cache is not None and cache.exists():
        z = np.load(cache)
        return {w: (z[f"{w}.r"], z[f"{w}.i"]) for w in WINDOWS}
    series = series or bake.load_series(data_root())
    out = {}
    for w in WINDOWS:
        p = pf.build(w, series)
        out[w] = (np.asarray(p.returns, float), np.asarray(pf.forecast_positions(p, None), int))
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache, **{f"{w}.r": out[w][0] for w in WINDOWS}, **{f"{w}.i": out[w][1] for w in WINDOWS})
    return out


def loss_of(returns: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """The realised positive loss of the forecast days, rounded to nine significant digits as the documents store it."""
    return np.array([float(f"{-x:.9g}") for x in returns[idx]])


BOOT_REPS, BLOCK = 2000, 10


def patch_forecaster() -> None:
    """A model that returns a non-finite VaR or ES at a deep working level is treated as the pipeline treats a failed fit:
    the previous day's forecast is held and the day is counted in ``n_fallback_days``. The engine's wrapper refuses a
    non-finite forecast by design (it never fills one). Call it at module level, before any worker is spawned."""
    import math

    from pipeline.cases.c11 import conformal as cf

    base = cf.ModelForecaster

    class SafeForecaster(base):
        def __call__(self, day: int, level: float):
            prev = self._last
            ve = super().__call__(day, level)
            if math.isfinite(ve[0]) and math.isfinite(ve[1]):
                return ve
            if prev is None or day == self.first:
                raise RuntimeError(f"{self.spec.model_id}: no finite forecast on the first day")
            self.fallback_days.add(int(day))
            self._last = prev
            return prev

    cf.ModelForecaster = SafeForecaster


def paired_change(loss, var_u, es_u, var_w, es_w, alpha, seed: int) -> dict:
    """The relative FZ0 change and its moving-block bootstrap 95 % interval (paired days)."""
    fu = fz0_days(loss, var_u, es_u, alpha)
    fw = fz0_days(loss, var_w, es_w, alpha)
    rng = np.random.default_rng(seed)
    n = fu.size
    nb = int(np.ceil(n / BLOCK))
    starts = rng.integers(0, n, size=(BOOT_REPS, nb))
    idx = ((starts[:, :, None] + np.arange(BLOCK)[None, None, :]) % n).reshape(BOOT_REPS, -1)[:, :n]
    mu, mw = fu[idx].mean(axis=1), fw[idx].mean(axis=1)
    rel = (mw - mu) / np.abs(mu)
    lo, hi = ci95(rel)
    return {"fz0_change": float((fw.mean() - fu.mean()) / abs(fu.mean())), "ci95": [lo, hi],
            "diff_mean": float(fw.mean() - fu.mean())}
