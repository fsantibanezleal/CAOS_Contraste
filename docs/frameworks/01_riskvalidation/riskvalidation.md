# Framework card, `riskvalidation`

## What and why

The engine of the product: validation tests, regulatory calculators and reference engines for financial risk models,
in its own repository ([CAOS_RiskValidation](https://github.com/fsantibanezleal/CAOS_RiskValidation), MIT). Every test
returns one `TestResult` with the statistic, the null hypothesis, the primary source that defines the test, the
policy that classified it and a fingerprint of its inputs. Thresholds live in versioned policy files and are presented
as policy, never as regulation. A product never re-implements a statistic: the SDD makes this a rule (section 3), so
a test is reviewed once, in the engine, against the published worked example or an independent reference, and every
case reads the same implementation.

Its core depends only on NumPy and SciPy, so the same wheel runs in the pipeline and, once published, in the browser
under Pyodide (the live lane, [04_live-lane.md](../../architecture/04_live-lane.md)).

## Install (exact, verified)

Pinned to its release tag until the first PyPI release, in `data-pipeline/requirements.txt`:

```text
riskvalidation @ git+https://github.com/fsantibanezleal/CAOS_RiskValidation@v0.01.000
```

Version 0.1.0 (tag `v0.01.000`), Python 3.11 or newer; verified 2026-10-05.

## Usage

```python
import numpy as np
from riskvalidation import default_policy
from riskvalidation.validation import calibration as cal, discrimination as disc, stability as st

policy = default_policy()
pd_eval = np.array([0.02, 0.05, 0.11, 0.30, 0.04, 0.08])
y_eval = np.array([0, 0, 1, 1, 0, 0])
for r in cal.pd_jeffreys_grades(n=[400, 900, 300], d=[2, 14, 19], pd=[0.004, 0.012, 0.05],
                                grades=["G01", "G02", "G03"], policy=policy, model_id="P1"):
    print(r.segment, r.p_value, r.light.value)
print(disc.disc_auc(pd_eval, y_eval, policy=policy, model_id="P1", segment="portfolio").to_dict())
```

## Applying it here

`data-pipeline/pipeline/stages/evaluate.py` runs the C01 battery on every rung and evaluation set:

| Family | Tests |
|---|---|
| discrimination | `disc_auc`, `disc_auc_vs_initial` (the ECB comparison against the AUC on the calibration slice), `disc_delong` (paired against the champion), `disc_ks` |
| calibration | `pd_jeffreys_grades` (per grade and the portfolio), `pd_binomial`, `pd_binomial_vasicek` (R = 0.04, CRE31.15), `pd_chi2_grades`, `pd_hosmer_lemeshow`, `pd_spiegelhalter`, `pd_brier` (Murphy decomposition by grade), `pd_ece` |
| stability | `stability_psi` (ten bins on the training quantiles), `stability_csi` (every input), `rating_hhi` |

Each `TestResult.to_dict()` is written unchanged into the variant artifact (`tests`); contract 2 checks its keys
against `TEST_RESULT_KEYS`. The engine's version is recorded in every artifact's lineage.

## Caveats and licence

MIT. The repository stays private until its first PyPI release (backlog BL-039); until then the Pyodide lane is not
wired and the live views re-light committed results instead of recomputing them. Migration-matrix tests and the
multi-period tests are in the engine but not run on C01, whose data are one snapshot and one period.
