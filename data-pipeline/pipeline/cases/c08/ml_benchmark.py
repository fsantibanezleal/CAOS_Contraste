"""S-5 of the method tiers plan: the machine-learning LGD benchmark beyond one boosted model (CT-907).

Bellotti, Brigo, Gambetti and Vrins (2021, "Forecasting recovery rates on non-performing loans with machine learning",
International Journal of Forecasting 37(1), https://doi.org/10.1016/j.ijforecast.2020.06.009) compare twenty techniques on
record-level loss data and find the random forest and the neural network among the best. This module adds both to the LGD
ladder of C08, beside the six rungs before them, on the same covariates, the same training span and the same test cohorts:

- L7 random forest (scikit-learn ``RandomForestRegressor``, squared-error splits on the LGD proxy);
- L8 neural network (scikit-learn ``MLPRegressor``, two hidden layers, early stopping on a tenth of the training span).

The settings below are fixed here, once, before any run: they are not tuned on a test cohort (the rule of
``conventions/method-tiers-and-manuscripts.md``: a result that does not improve is still reported). Both models are a pure
function of the training data and the seed (one thread, a fixed ``random_state``); their predictions are clipped to [0, 1], as
the OLS rung is, because neither has a link that keeps them inside.

The module also carries the hypothesis, the comparison against the six rungs before and its verdict, written down once and read
by the producer (``variant``) and by the case page (``page``), so a verdict is computed from the committed documents, never typed.
"""
from __future__ import annotations

from typing import Any

import numpy as np

#: the rung ids of the two new rungs, in ladder order
ML_RUNGS = ("L7-random-forest", "L8-neural-network")
#: the six rungs before them
CLASSICAL_RUNGS = ("L1-ols", "L2-fractional-logit", "L3-beta", "L4-hurdle", "L5-gradient-boosted", "L6-tobit")
LICENCE = "BSD-3-Clause"
#: the forest: 100 trees of leaves of at least 30 defaults on half of the training defaults each, a third of the covariates at
#: every split (the regression default of Breiman's recommendation); half the sample per tree keeps the 200 thousand defaults of
#: the last cutoff to a minute of one thread
FOREST: dict[str, Any] = {"n_estimators": 100, "min_samples_leaf": 30, "max_features": 0.34, "max_samples": 0.5, "bootstrap": True,
                          "criterion": "squared_error", "n_jobs": 1}
#: the network: two hidden layers of 32 and 16 units, rectified linear units, Adam with a batch of 512, L2 penalty 1e-4, at most
#: 100 epochs, stopped when the score of a tenth of the training defaults (set aside by the fit, never a test default) has not
#: improved for 10 epochs
NETWORK: dict[str, Any] = {"hidden_layer_sizes": (32, 16), "activation": "relu", "solver": "adam", "alpha": 1e-4, "batch_size": 512,
                           "learning_rate_init": 1e-3, "max_iter": 100, "early_stopping": True, "validation_fraction": 0.1,
                           "n_iter_no_change": 10}

#: the hypothesis, stated before the run (plan section 3, S-5; Bellotti et al. 2021)
HYPOTHESIS = {
    "en": "Hypothesis: on the same out-of-time split as the six rungs before them, the better of the random forest and the "
          "neural network has a lower RMSE than every one of those six rungs in at least two thirds of the test cohorts.",
    "es": "Hipótesis: en la misma partición fuera de tiempo que las seis etapas anteriores, el mejor entre el bosque aleatorio "
          "y la red neuronal tiene un RMSE menor que cada una de esas seis etapas en al menos dos tercios de las cohortes de prueba."}
REFUTED_IF = {
    "en": "Refuted if it does so in at most one third of the test cohorts; in between the verdict is mixed. The result is reported "
          "whatever it is, and the settings are not tuned on a test cohort.",
    "es": "Refutada si lo logra en un tercio o menos de las cohortes de prueba; entre ambos extremos el veredicto es mixto. El "
          "resultado se informa sea cual sea, y los parámetros no se ajustan con una cohorte de prueba."}


def _scaled(scaler, x: np.ndarray) -> np.ndarray:
    return scaler.apply(x)


def fit_forest(x_scaled: np.ndarray, y: np.ndarray, seed: int):
    """The random forest on the standardised covariates of the training span; raises on a failure the ladder reports."""
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(random_state=int(seed), **FOREST)
    model.fit(x_scaled, y)
    return model


def fit_network(x_scaled: np.ndarray, y: np.ndarray, seed: int):
    """The neural network on the standardised covariates of the training span."""
    from sklearn.neural_network import MLPRegressor

    model = MLPRegressor(random_state=int(seed), **NETWORK)
    model.fit(x_scaled, y)
    return model


def predict(model, x_scaled: np.ndarray) -> np.ndarray:
    """The LGD estimate in [0, 1] (the models have no link, so the estimate is clipped to the range, stated in the document)."""
    return np.clip(np.asarray(model.predict(x_scaled), dtype=float), 0.0, 1.0)


def cohort_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The best of the six rungs before the new ones against the better of the two new ones, by RMSE, for one test cohort.

    ``rows`` is ``outputs.rung_comparison``. A new rung missing from it is an error: a cohort never silently drops one.
    A classical rung missing (not fitted) is left out of the minimum; at least one must be there."""
    rmse = {r["rung_id"]: float(r["rmse"]) for r in rows}
    missing = [rid for rid in ML_RUNGS if rid not in rmse]
    if missing:
        raise ValueError(f"the comparison has no row for {', '.join(missing)}")
    classical = {rid: rmse[rid] for rid in CLASSICAL_RUNGS if rid in rmse}
    if not classical:
        raise ValueError("the comparison has none of the six rungs before the machine-learning rungs")
    best_c = min(classical.items(), key=lambda kv: kv[1])
    best_m = min(((rid, rmse[rid]) for rid in ML_RUNGS), key=lambda kv: kv[1])
    gain = best_c[1] - best_m[1]
    return {"classical": best_c, "ml": best_m, "gain": gain, "ml_wins": gain > 0.0}


def verdict(wins: int, cohorts: int) -> str:
    """holds at two thirds of the cohorts or more, refuted at one third or less, mixed between."""
    if cohorts <= 0:
        raise ValueError("a verdict needs at least one cohort")
    share = wins / cohorts
    if share >= 2 / 3 - 1e-12:
        return "holds"
    if share <= 1 / 3 + 1e-12:
        return "refuted"
    return "mixed"


__all__ = ["ML_RUNGS", "CLASSICAL_RUNGS", "FOREST", "NETWORK", "HYPOTHESIS", "REFUTED_IF", "LICENCE", "fit_forest", "fit_network",
           "predict", "cohort_result", "verdict"]
