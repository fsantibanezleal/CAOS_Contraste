# Framework card, `interpret` (the explainable boosting machine)

## What and why

The explainable boosting machine, a GA2M: g(E[y]) = beta_0 + sum_j f_j(x_j) + sum_(i,j) f_ij(x_i, x_j), with shape
functions learned by cyclic gradient boosting at a low learning rate and with bagging (Lou et al. 2013; Nori et al.
2019, arXiv 1909.09223). For credit it is a boosted scorecard: each shape function reads as a points table, so reason
codes are exact for the main effects, and monotone constraints are applied at fit time. It is the glass-box
challenger of the ladder (dossier 04 B.2).

## Install (exact, verified)

`interpret-core[required,ebm]==0.7.8` in `data-pipeline/requirements.txt`; the core package without the dashboard.
Verified 2026-10-04 against the repository licence (the wheel's metadata carries no licence field).

## Usage

```python
import numpy as np
import pandas as pd
from interpret.glassbox import ExplainableBoostingClassifier

rng = np.random.default_rng(0)
X = pd.DataFrame({"a": rng.normal(size=4000), "b": rng.normal(size=4000)})
y = (rng.uniform(size=4000) < 1 / (1 + np.exp(1.0 - X.a))).astype(int)
ebm = ExplainableBoostingClassifier(max_bins=64, max_interaction_bins=16, interactions=5, outer_bags=8,
                                    monotone_constraints=[1, 0], random_state=0, n_jobs=1).fit(X, y)
print(ebm.term_names_, ebm.decision_function(X)[:3])
```

## Applying it here

`data-pipeline/pipeline/model/ebm.py` fits P3 with the declared monotone directions on the continuous inputs, five
pairwise terms, at most 64 bins per main term and 16 per pair (the library default is 1024; fewer bins keep the
exported shape functions small and readable), eight outer bags and a fixed seed. `export` writes the binning and the
term scores into the models artifact; `score_logit` evaluates that export without the library and is tested against
the library's own decision function, and the web's live scorer is tested against the exported scores to 1e-9
(CT-105).

## Caveats and licence

MIT. `monotonize()` does not touch pairwise terms, so a monotone main effect does not make the whole score monotone
in that input when a pair includes it; the pairs are shown in the Model group.
