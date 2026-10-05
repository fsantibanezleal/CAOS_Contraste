# Framework card, `tabpfn` (optional extra)

## What and why

A tabular foundation model: a transformer pre-trained on synthetic data that predicts by in-context learning, with
no per-dataset training (TabPFN v2, Hollmann et al. 2025, Nature 637:319-326, DOI 10.1038/s41586-024-08328-6). It is
the open frontier for small samples, which is where credit has the low-default and SME portfolios; the only
credit-specific evidence so far is a conference abstract with preliminary results (De Vos et al. 2025, UNVERIFIED
beyond the abstract). Contraste measures it on the 1,000-record German twin rather than claiming it.

## Install (exact, verified)

The optional extra `data-pipeline/requirements-tabpfn.txt`, not part of the default install:

```bash
.venv-pipeline/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1
.venv-pipeline/bin/pip install -r data-pipeline/requirements-tabpfn.txt   # tabpfn==9.1.0
```

The v2 weights download once into the device models root: `TABPFN_MODEL_CACHE_DIR`, or `<CONTRASTE_MODELS>/tabpfn`.
With neither set, the rung refuses to run rather than write to a user cache. Verified 2026-10-05.

## Usage

```python
from tabpfn import TabPFNClassifier
from tabpfn.constants import ModelVersion

clf = TabPFNClassifier.create_default_for_version(ModelVersion.V2, n_estimators=8, random_state=0, device="cpu")
clf.fit(X_train, y_train)
pd_hat = clf.predict_proba(X_test)[:, 1]
```

## Applying it here

`data-pipeline/pipeline/model/tabpfn_rung.py` is P5, on the German twin only: categorical inputs as integer codes
learned on the training slice and declared as categorical, eight estimators, CPU, a fixed seed. It is calibrated and
tested like every other rung. A bake without the extra skips P5, and the German twin's artifacts then carry no P5 rung.

## Caveats and licence

The code is Apache 2.0. The package's default weights (TabPFN-3.5, and versions 2.5 to 3) are under non-commercial
licences, so the rung selects the v2 weights, under the Prior Labs License v1.1 (Apache 2.0 plus an attribution
clause); the TabPFN view shows that licence and "Built with PriorLabs-TabPFN", and the Context group lists it with
every engine. torch (Apache 2.0 and permissive components) is only
in the extra.
