# Framework card, `scikit-learn`

## What and why

The general machine-learning toolkit: stratified splitting and repeated folds, penalised logistic regression,
decision trees and isotonic regression. Each use is a standard estimator with a fixed seed, so the bake stays a pure
function of the inputs and the seed.

## Install (exact, verified)

`scikit-learn==1.9.1` in `data-pipeline/requirements.txt`. Verified 2026-10-05.

## Usage

```python
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

rng = np.random.default_rng(0)
Z = rng.normal(size=(3000, 4))
y = (rng.uniform(size=3000) < 1 / (1 + np.exp(1.3 - Z[:, 0]))).astype(int)
m = LogisticRegression(l1_ratio=1.0, solver="liblinear", C=0.1, max_iter=2000, random_state=0).fit(Z, y)
iso = IsotonicRegression(y_min=1e-6, y_max=1 - 1e-6, increasing=True, out_of_bounds="clip")
calibrated = iso.fit(m.predict_proba(Z)[:, 1], y).predict(m.predict_proba(Z)[:, 1])
```

## Applying it here

- `stages/split.py`: the locked stratified holdout (30%), the calibration slice (20% of the rest) and five stratified
  folds repeated twice inside the training slice (`train_test_split`, `RepeatedStratifiedKFold`).
- `model/penalised.py`: P2a, L1 logistic regression on the WoE inputs, the strength chosen by cross-validated log
  loss over a grid of six values; P2b, PLTR, whose threshold rules come from depth-one and depth-two
  `DecisionTreeClassifier` fits (each leaf at least 5% of the records) and enter an L1 logistic regression.
- `core/calibration.py`: the isotonic map of every machine-learning rung, fitted on the calibration slice only and
  exported as thresholds so the web interpolates the same map.

## Caveats and licence

BSD-3-Clause. scikit-learn 1.9 deprecates `penalty`; the L1 penalty is set with `l1_ratio=1.0`, and the models artifact
lists the coefficients the penalty kept (`selected`). Isotonic regression produces ties (flat steps), so ranking by the
calibrated PD alone is unstable; the approval rule breaks ties by the raw score.
