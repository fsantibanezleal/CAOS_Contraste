# Framework card, `xgboost`

## What and why

The second gradient-boosting engine, kept as a cross-check of the first: when two independent implementations with
the same constraints agree on the discrimination, the gain of the challenger is a property of the data, not of one
library. XGBoost was the best method in Gunnarsson et al. (2021).

## Install (exact, verified)

`xgboost==3.4.1` in `data-pipeline/requirements.txt`. Verified 2026-10-05.

## Usage

```python
import numpy as np
import xgboost as xgb

rng = np.random.default_rng(0)
M = rng.normal(size=(5000, 3))
y = (rng.uniform(size=5000) < 1 / (1 + np.exp(1.2 - M[:, 0]))).astype(int)
params = {"objective": "binary:logistic", "eta": 0.05, "max_depth": 4, "tree_method": "hist", "max_bin": 512,
          "monotone_constraints": "(1,0,0)", "seed": 0, "eval_metric": "logloss", "nthread": 1}
cv = xgb.cv(params, xgb.DMatrix(M, label=y), num_boost_round=2000, nfold=5, early_stopping_rounds=50)
booster = xgb.train(params, xgb.DMatrix(M, label=y), num_boost_round=len(cv))
```

## Applying it here

`data-pipeline/pipeline/model/gbm.py` fits the XGBoost rung on the Taiwan fit only, with the same constraints, codes
and folds as LightGBM; it goes through the same calibration map, battery and partial-dependence check. It is one of
the challengers the reader can select, so its battery shows in the Validation group, and its AUC sits beside
LightGBM's in the Model group.

## Caveats and licence

Apache 2.0. With `tree_method` hist or approx the constraints can remove split candidates and leave shallow trees;
the documentation's remedy is a larger `max_bin`, here 512 (dossier 04 B.1). `nthread` is 1 so the bake is
reproducible.
