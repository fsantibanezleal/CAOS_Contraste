# Framework card, `lightgbm`

## What and why

Gradient-boosted trees with monotone constraints, the challenger the benchmark literature puts ahead of the logistic
scorecard on retail data (Lessmann et al. 2015; Gunnarsson et al. 2021: boosted trees best, deep networks no better).
A regulated PD challenger must keep the business direction of each input, and LightGBM's constraint methods
"intermediate" and "advanced" constrain less than "basic", which over-constrains predictions (its documentation,
dossier 04 B.1).

## Install (exact, verified)

`lightgbm==4.7.0` in `data-pipeline/requirements.txt` (Python 3.10 or newer). Verified 2026-10-05.

## Usage

```python
import lightgbm as lgb
import numpy as np

rng = np.random.default_rng(0)
M = rng.normal(size=(5000, 3))
y = (rng.uniform(size=5000) < 1 / (1 + np.exp(1.2 - M[:, 0]))).astype(int)
params = {"objective": "binary", "learning_rate": 0.05, "num_leaves": 15, "monotone_constraints": [1, 0, 0],
          "monotone_constraints_method": "advanced", "deterministic": True, "force_row_wise": True,
          "seed": 0, "verbose": -1}
cv = lgb.cv(params, lgb.Dataset(M, y), num_boost_round=2000, nfold=5, stratified=True,
            callbacks=[lgb.early_stopping(50, verbose=False)])
booster = lgb.train(params, lgb.Dataset(M, y), num_boost_round=len(next(iter(cv.values()))))
```

## Applying it here

`data-pipeline/pipeline/model/gbm.py` fits P4: the declared directions as constraints (categorical inputs as integer
codes learned on the training slice, unconstrained), the number of rounds by early stopping on the training folds,
`deterministic` set for a reproducible bake. The isotonic map is fitted on the calibration slice. Three checks ride
along and are written into the models artifact: the partial-dependence grid (individual conditional expectation
curves on 200 records and up to 30 quantiles of each constrained input never move against the declared direction,
CT-110), the SHAP reason codes and their bootstrap stability ([08_shap](../08_shap/shap.md)).

## Caveats and licence

MIT. The constraint holds on the raw score; the isotonic map is non-decreasing, so the calibrated PD keeps the
direction, with flat steps. The trees themselves are not exported; the web reads the scored sample and the
partial-dependence curves, not the model.
