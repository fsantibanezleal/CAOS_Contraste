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
riskvalidation @ git+https://github.com/fsantibanezleal/CAOS_RiskValidation@v0.02.000
```

Version 0.2.0 (tag `v0.02.000`), Python 3.11 or newer; verified 2026-10-05. 0.2.0 adds the regulatory calculators
(`regulatory.irb`, the IRB functions under Basel III final, CRR3, Basel II and CMF RAN 21-6) and three reference
engines (`engines.vasicek`, `engines.low_default`, `engines.pd_curve`), each reproducing its primary source's tables.

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

`data-pipeline/pipeline/cases/c05_ldp_calibration.py` runs C05 on the 0.2.0 engines:

| Module | Used for |
|---|---|
| `engines.pd_curve` | the 2009 S&P model (`model_from_counts`), its quasi moment matching (`qmm`), every calibration approach of Tasche (2013) for 2010 and 2011, the profile chi-square of case 3 |
| `engines.low_default` | the most prudent bounds (independent and correlated), scaled (section 5) and over five years (section 6), for the paper's example and the generated years |
| `regulatory.irb` | the risk weight of every curve and estimate (the Impact group), and the live calculator's parity points |
| `validation.calibration` | `pd_default_profile` (the paper's Monte Carlo chi-square), `pd_chi2_grades`, `pd_jeffreys_grades`, `pd_binomial`, `pd_binomial_vasicek` |

`data-pipeline/pipeline/cases/c01_capital.py` gives C01 its IRB capital: `regulatory.irb.capital_requirement` at unit
LGD for every account of every rung (qualifying revolving retail, every card a revolver, for the Taiwan cards; other
retail for the German loans), under Basel III final, CRR3 and Basel II, summed along each rung's cut-off curve; the
Capital view multiplies by the rail's LGD, since retail capital is linear in it.

The browser recomputes the IRB risk weight, the most prudent bounds and the four case 1 calibrations with TypeScript
ports (`frontend/src/engine/credit.ts`) held to the engine within 1e-9 on points the pipeline exports
(`frontend/src/engine/credit.test.ts`): corporate points with C05, retail points (QRRE revolvers and transactors,
other retail) with C01.

## Caveats and licence

MIT. The repository stays private until its first PyPI release (backlog BL-039); until then the Pyodide lane is not
wired: the live views re-light committed results (C01) or run the TypeScript ports of the calculators (C05). Migration-matrix tests and the
multi-period tests are in the engine but not run on C01, whose data are one snapshot and one period.
