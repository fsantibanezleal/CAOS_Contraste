# Framework card, `statsmodels`

## What and why

The statistical models of the pipeline that need inference, not only prediction: maximum-likelihood logistic
regression with standard errors and p-values, which the scorecard's sign check reads. scikit-learn's logistic
regression is penalised by default and reports no p-values, so the unpenalised scorecard is fitted here.

## Install (exact, verified)

`statsmodels==0.15.0` in `data-pipeline/requirements.txt`; also one of the wheels the live lane may load
(`core/gate.py`). Verified 2026-10-05.

## Usage

```python
import numpy as np
import statsmodels.api as sm

rng = np.random.default_rng(0)
W = rng.normal(size=(2000, 3))
y = (rng.uniform(size=2000) < 1 / (1 + np.exp(1.2 + W @ [0.8, 0.5, 0.0]))).astype(int)
res = sm.Logit(y, sm.add_constant(W, has_constant="add")).fit(disp=0, method="newton", maxiter=100)
print(res.params, res.pvalues)
```

## Applying it here

`data-pipeline/pipeline/model/scorecard.py` fits the logistic regression of P1 on the WoE of the kept
characteristics, by Newton's method. With the WoE sign convention every sound coefficient is negative; while one is
positive, the wrong-signed characteristic with the largest p-value is dropped and the model refitted (dossier 04
A.6), and the reason is recorded in the models artifact (`dropped`).

## Caveats and licence

BSD-3-Clause. Quasi-separation on a tiny segment makes Newton's method diverge; the IV screen and the 5% minimum bin
size keep the C01 fits away from it.
