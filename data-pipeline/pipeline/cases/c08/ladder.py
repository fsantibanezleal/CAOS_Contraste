"""The LGD ladder of C08 (CT-907): six rungs fitted on the defaults closed before a cutoff, every fit by the engine.

L1 OLS (predictions clipped to [0, 1] by the engine, the only place a model clips), L2 fractional logit (Papke and
Wooldridge 1996), L3 beta regression on the endpoint-transformed LGD (reported at three epsilons, the ladder keeps one),
L4 two-stage hurdle, L5 gradient boosting (catboost's classifier with the cross-entropy loss, which takes a target in [0, 1]; the raw score goes through the logistic link), L6 two-limit
Tobit, then the two machine-learning rungs of S-5 (``ml_benchmark``): L7 random forest and L8 neural network. The covariates are the ones known at the charge-off (``panel.FEATURE_NAMES``); the four continuous ones are
standardised with the moments of the training set, so a fit never sees a moment of the test cohort.

A rung that cannot be fitted (a refusal of the engine, a non-convergence, too few defaults) is reported not evaluated
with its reason and no number: the ladder never stands in a value for it (CT-907).

The engine fits take an LGD in [0, 1]; a default whose proxy lies outside it (a charge-off above the approval) is left out
of the fit by a counted exclusion (``Training.n_out_of_range``), never clipped to the end of the range (CT-903).
"""
from __future__ import annotations

import importlib.metadata as md
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.lgd_ead import lgd_models as rv_models
from scipy import special

from . import ml_benchmark as ml
from .panel import CONTINUOUS, FEATURE_NAMES

#: ``(rung id, kind)`` in ladder order
RUNGS: tuple[tuple[str, str], ...] = (
    ("L1-ols", "ols"), ("L2-fractional-logit", "fractional-logit"), ("L3-beta", "beta"), ("L4-hurdle", "hurdle"),
    ("L5-gradient-boosted", "gradient-boosted"), ("L6-tobit", "tobit"),
    ("L7-random-forest", "random-forest"), ("L8-neural-network", "neural-network"),
)
RUNG_KIND = dict(RUNGS)
#: the endpoint epsilons of the beta rung (Qi and Zhao 2011: the fit is sensitive to it, so it is reported at three)
EPSILONS = (0.0001, 0.001, 0.01)
LADDER_EPSILON = 0.001
#: fewer fitted defaults than this and the ladder is not fitted at all
MIN_DEFAULTS = 200
#: the catboost settings (fixed, one thread: the fit is a pure function of the data and the seed)
BOOST = {"iterations": 200, "depth": 6, "learning_rate": 0.1, "l2_leaf_reg": 3.0, "loss_function": "CrossEntropy",
         "thread_count": 1, "verbose": False, "allow_writing_files": False}
LICENCES = {"engine": "MIT", "catboost": "Apache-2.0", "scikit-learn": ml.LICENCE}
#: the library of each kind that is not the engine's
LIBRARY = {"gradient-boosted": "catboost", "random-forest": "scikit-learn", "neural-network": "scikit-learn"}


@dataclass(frozen=True)
class RungFit:
    rung_id: str
    kind: str
    evaluated: bool
    reason: str | None
    fit: rv_models.LgdFit | None = None
    booster: Any = None
    epsilon: float | None = None

    @property
    def library(self) -> str:
        return LIBRARY.get(self.kind, "riskvalidation")

    @property
    def library_version(self) -> str:
        return md.version(self.library)


@dataclass(frozen=True)
class Scaler:
    mean: np.ndarray
    std: np.ndarray

    def apply(self, x: np.ndarray) -> np.ndarray:
        out = np.array(x, dtype=float, copy=True)
        k = len(self.mean)
        out[:, :k] = (out[:, :k] - self.mean) / self.std
        return out


@dataclass(frozen=True)
class Ladder:
    """The fitted rungs of one cutoff."""

    cutoff: str
    scaler: Scaler
    n_fitted: int
    n_out_of_range: int
    rungs: dict[str, RungFit]
    beta_by_epsilon: dict[float, RungFit] = field(default_factory=dict)

    def names(self) -> tuple[str, ...]:
        return ("const", *FEATURE_NAMES)

    def _matrix(self, x: np.ndarray) -> np.ndarray:
        z = self.scaler.apply(x)
        return np.column_stack([np.ones(len(z)), z])

    def predict(self, rung: RungFit, x: np.ndarray) -> np.ndarray:
        """The LGD estimates of ``rung`` for the raw covariates ``x`` (columns ``FEATURE_NAMES``), in [0, 1]."""
        if not rung.evaluated:
            raise ValueError(f"{rung.rung_id} is not evaluated ({rung.reason}); it has no prediction")
        if rung.kind == "gradient-boosted":
            raw = rung.booster.predict(self.scaler.apply(x), prediction_type="RawFormulaVal")
            return special.expit(np.asarray(raw, dtype=float))
        if rung.kind in ("random-forest", "neural-network"):
            return ml.predict(rung.booster, self.scaler.apply(x))
        return rv_models.predict_lgd(rung.fit, self._matrix(x))


def _not_fitted(rung_id: str, kind: str, reason: str, epsilon: float | None = None) -> RungFit:
    return RungFit(rung_id, kind, False, reason, None, None, epsilon)


def _scaler(x: np.ndarray) -> Scaler:
    k = len(CONTINUOUS)
    mean = x[:, :k].mean(axis=0)
    std = x[:, :k].std(axis=0)
    return Scaler(mean=mean, std=np.where(std > 1e-12, std, 1.0))


def fit_ladder(x_train: np.ndarray, y_train: np.ndarray, cutoff: str, seed: int) -> Ladder:
    """Fit the six rungs on ``x_train`` (raw covariates) and ``y_train`` (the proxy LGD of the training defaults, any
    value). Values of ``y_train`` outside [0, 1] are left out and counted."""
    y_train = np.asarray(y_train, dtype=float)
    inside = (y_train >= 0.0) & (y_train <= 1.0)
    n_out = int((~inside).sum())
    x, y = np.asarray(x_train, dtype=float)[inside], y_train[inside]
    scaler = _scaler(x) if len(y) else Scaler(np.zeros(len(CONTINUOUS)), np.ones(len(CONTINUOUS)))
    if len(y) < MIN_DEFAULTS:
        why = f"{len(y)} defaults closed before the cutoff, fewer than the {MIN_DEFAULTS} a fit needs"
        return Ladder(cutoff, scaler, int(len(y)), n_out, {rid: _not_fitted(rid, kind, why) for rid, kind in RUNGS})
    lad = Ladder(cutoff, scaler, int(len(y)), n_out, {})
    design = lad._matrix(x)
    names = lad.names()
    fits: dict[str, RungFit] = {}

    def run(rid: str, kind: str, fn, epsilon: float | None = None) -> RungFit:
        try:
            fit = fn()
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
            return _not_fitted(rid, kind, f"{type(exc).__name__}: {exc}", epsilon)
        return RungFit(rid, kind, True, None, fit, None, epsilon)

    fits["L1-ols"] = run("L1-ols", "ols", lambda: rv_models.fit_ols(design, y, names))
    fits["L2-fractional-logit"] = run("L2-fractional-logit", "fractional-logit", lambda: rv_models.fit_fractional_logit(design, y, names))
    beta = {e: run("L3-beta", "beta", lambda e=e: rv_models.fit_beta(design, y, e, names), e) for e in EPSILONS}
    fits["L3-beta"] = beta[LADDER_EPSILON]
    fits["L4-hurdle"] = run("L4-hurdle", "hurdle", lambda: rv_models.fit_hurdle(design, y, None, names))
    fits["L5-gradient-boosted"] = _boost(x, y, scaler, seed)
    fits["L6-tobit"] = run("L6-tobit", "tobit", lambda: rv_models.fit_tobit(design, y, names))
    z = scaler.apply(x)
    fits["L7-random-forest"] = _sklearn("L7-random-forest", "random-forest", lambda: ml.fit_forest(z, y, seed))
    fits["L8-neural-network"] = _sklearn("L8-neural-network", "neural-network", lambda: ml.fit_network(z, y, seed))
    return Ladder(cutoff, scaler, int(len(y)), n_out, {rid: fits[rid] for rid, _ in RUNGS}, beta)


def _boost(x: np.ndarray, y: np.ndarray, scaler: Scaler, seed: int) -> RungFit:
    try:
        from catboost import CatBoostClassifier
    except ImportError as exc:  # the pipeline pins catboost; a missing wheel is a reported absence, not a stand-in
        return _not_fitted("L5-gradient-boosted", "gradient-boosted", f"catboost is not installed ({exc})")
    try:
        model = CatBoostClassifier(random_seed=int(seed), **BOOST)
        model.fit(scaler.apply(x), y)
    except Exception as exc:  # noqa: BLE001 - catboost raises its own CatBoostError type
        return _not_fitted("L5-gradient-boosted", "gradient-boosted", f"{type(exc).__name__}: {exc}")
    return RungFit("L5-gradient-boosted", "gradient-boosted", True, None, None, model, None)


def _sklearn(rung_id: str, kind: str, fn) -> RungFit:
    """A scikit-learn rung of S-5: a failure of the fit is a reported absence with its reason, never a stand-in value."""
    try:
        model = fn()
    except ImportError as exc:  # the pipeline pins scikit-learn; a missing wheel is a reported absence
        return _not_fitted(rung_id, kind, f"scikit-learn is not installed ({exc})")
    except Exception as exc:  # noqa: BLE001 - scikit-learn raises ValueError and its own types
        return _not_fitted(rung_id, kind, f"{type(exc).__name__}: {exc}")
    return RungFit(rung_id, kind, True, None, None, model, None)
