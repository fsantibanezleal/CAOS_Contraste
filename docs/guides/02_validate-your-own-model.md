# Guide: validate your own model

Contraste's battery applies to any PD model, not only to its baked cases. The door is
`data-pipeline/validate.py`: give it your model's scored sample, and optionally the development sample, and it
returns the same `TestResult` rows the cases carry. It runs offline, on your machine; nothing is uploaded.

## The input

A CSV in the `scored_sample` family of contract 1 (`data-pipeline/pipeline/io/contract.py`), one row per obligor:

| Column | Required | Meaning |
|---|---|---|
| `id` | yes | obligor or account identifier, unique per observation date |
| `observation_date` | yes | `YYYY-MM-DD`, the date the inputs were observed |
| `target` | yes | 1 if the obligor defaulted over the horizon, else 0 |
| `pd` | for the battery | the PD your model assigned, strictly between 0 and 1 |
| `score`, `grade`, `segment`, `protected_attr` | no | carried and reported; `protected_attr` is never a model input |

Contract 1 parses every value by its declared kind and never coerces one: a PD of `1.2` or a target of `yes` is
rejected with the field, the value and the expected range; a duplicate identifier on the same date is rejected; any
column the family does not declare is listed as ignored and never used.

## Run it

Two synthetic samples with a known truth ship in `data/examples/` (`pipeline/io/examples.py`): a development sample
calibrated by construction, and a current sample from a riskier population whose defaults arrive at 1.5 times the PD.

```bash
.venv-pipeline/bin/python data-pipeline/validate.py data/examples/scored_sample_current.csv \
    --reference data/examples/scored_sample_development.csv --model-id my-model --output E:/_Temp/contraste/own
```

The tool prints one line per test and writes `my-model-validation.json` (schema `contraste.own-validation/v1`) into
`--output`, which must be outside the repository (CT-014). The report holds the engine versions, the contract-1
report of each file, the light counts and every `TestResult`.

## What the example shows

| Test | Light | Why |
|---|---|---|
| `stability.psi` | red | PSI 0.063: inside the conventional 0.10 band, yet the Yurdakul-Naranjo benchmark at n = 2,000 per sample says the population moved |
| `disc.auc_vs_initial` | green | the ranking is intact: defaults still rise with the PD |
| `pd.jeffreys`, `pd.binomial` (portfolio) | red | 207 defaults where the PDs expect about 138: the level is under-estimated |
| `pd.binomial_vasicek` | green | with an asset correlation of 0.04 one period's excess can be a systematic shock; one period cannot tell the two apart |
| `pd.chi2_grades`, `pd.hosmer_lemeshow`, `pd.spiegelhalter` | red | the fit across grades fails with the level |

Run the development sample alone and every level test is green: that is the calibrated truth. Without
`--reference`, the PSI, the AUC against the initial validation and the grade concentration are not run, since each
compares against the development. The master scale is the case's twelve geometric grades; the thresholds are the
engine's default policy, policy and not regulation ([guide 03](03_read-a-validation-report.md)).

## In Python

```python
from pipeline.own_sample import validate_own, write_report   # with data-pipeline/ on sys.path

report = validate_own("scored.csv", reference="development.csv", model_id="retail-pd-v3")
print(report["lights"])
write_report(report, "E:/_Temp/contraste/own")
```

The web's own upload, which runs the same battery in the browser under Pyodide, arrives with the engine's PyPI
release (backlog BL-039).
