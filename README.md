# Contraste

**Site:** https://contraste.fasl-work.com (GitHub Pages), published with the first release from `main`; not live yet.

[![CI](https://img.shields.io/github/actions/workflow/status/fsantibanezleal/CAOS_Contraste/ci.yml?branch=main&label=CI)](https://github.com/fsantibanezleal/CAOS_Contraste/actions)
[![License](https://img.shields.io/github/license/fsantibanezleal/CAOS_Contraste)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/fsantibanezleal/CAOS_Contraste?label=version&sort=semver)](https://github.com/fsantibanezleal/CAOS_Contraste/tags)

Build financial risk models, then validate them the way a model risk function and a supervisor would.

*Construir modelos de riesgo financiero y validarlos como lo harían una función de riesgo de modelos y un supervisor.*

Contraste fits a ladder of models on public data, from the constant PD to gradient boosting and a tabular foundation
model, and runs on every rung the battery a validator would: discrimination, calibration level and fit, stability,
by grade and for the portfolio, each test with its null hypothesis, its primary source and the policy that turned
its p-value into a light. Perturbed variants of each case carry a known truth, so the page shows what each test
detects and what it misses. It is for validators, risk modellers and supervisors who want to see the evidence
behind a model opinion, and for students of credit risk. The tests come from the engine
[`riskvalidation`](https://github.com/fsantibanezleal/CAOS_RiskValidation) (MIT).

## What is built

| Case | Question | Data | Status |
|---|---|---|---|
| [C01](docs/cases/C01.md) | Does a monotone WoE scorecard match the challengers the literature says beat it, once calibration is required, and what do the tests say when the population shifts? | UCI Taiwan credit cards (30,000), UCI Statlog German Credit (1,000), both CC BY 4.0 | built |

C01's ladder: the constant PD and the strongest single variable (P0), the WoE scorecard (P1), L1 logistic
regression and penalised logistic tree regression (P2), the explainable boosting machine (P3), monotone LightGBM
with XGBoost as cross-check (P4), and TabPFN v2 on the German twin (P5). Seven variants: the holdout, moderate and
severe covariate drift, a prior shift, label noise, a small training sample and the German twin. The other 21 cases
(IFRS 9 and the Chilean provisions, LGD and EAD, portfolio capital, market risk and FRTB, IRRBB and liquidity,
operational risk, ICAAP and IAPE stress, machine-learning and fairness validation, the size and power of the tests
themselves) are planned in [the coverage matrix](docs/cases/README.md).

## The web

Six routes on the shared CAOS shell, in English and Spanish, light and dark: the App (a workbench with six groups:
Model, Validation, Impact, Findings, Variants, Context), Introduction, Methodology, Implementation, Experiments and
Benchmark. The App replays the committed artifacts and computes live what a reader changes: the scorecard and EBM
scores of an applicant, the lights under the reader's own policy thresholds, the decision at the reader's approval
rate and LGD.

## Run it

```bash
./scripts/setup.sh                     # the pipeline environment (.venv-pipeline); setup.ps1 on Windows
.venv-pipeline/bin/python data-pipeline/fetch.py --all          # the sources, into $CONTRASTE_DATA
.venv-pipeline/bin/python data-pipeline/run.py C01 --output <dir>   # a sandbox bake; no --output: the release bake
.venv-pipeline/bin/python -m pytest    # the pipeline tests, sandboxed
cd frontend && npm ci && npm run dev   # the web on http://localhost:5173; npm test, npm run build, npm run gate
```

Set `CONTRASTE_DATA` and `CONTRASTE_MODELS` (`.env.example`) to directories outside the repository. The full path,
from fetching to the measured gate, is [guide 01](docs/guides/01_fetch-and-bake.md).

## Validate your own model

```bash
.venv-pipeline/bin/python data-pipeline/validate.py scored.csv --reference development.csv --output <dir>
```

A CSV with `id`, `observation_date`, `target` and `pd` per obligor goes through contract 1 and the same battery the
cases run; the report is written outside the repository. Two known-truth examples ship in `data/examples/`.
[Guide 02](docs/guides/02_validate-your-own-model.md) walks through them, and
[guide 03](docs/guides/03_read-a-validation-report.md) reads the report.

## Architecture at a glance

An offline Python pipeline (`data-pipeline/`: fetch with a licence manifest, contract 1 on every input record, the
ladder, the battery, contract 2 on every artifact) writes compact, deterministic artifacts into `data/derived/`; a
static React site (`frontend/`, Vite, the `@fasl-work/caos-app-shell` shell, uPlot) replays them. The pipeline's
engines and their licences are in [docs/frameworks.md](docs/frameworks.md); the design, with every requirement and
the gate that fails when it is violated, is [docs/design/SDD.md](docs/design/SDD.md); the architecture pages are in
[docs/architecture.md](docs/architecture.md).

## Data and licences

Every source is declared with its licence class (mirror-allowed, derived-only, link-only, unusable) and the
verbatim fragment of its terms (`data-pipeline/config/sources.json`); raw rows are committed only from mirror-allowed
sources, and the export refuses an artifact whose lineage includes a link-only or unusable source. C01 reads the UCI
datasets under CC BY 4.0 (Yeh 2009, DOI 10.24432/C55S3H; Hofmann 1994, DOI 10.24432/C5NC77). TabPFN's v2 weights
are under the Prior Labs License v1.1: built with PriorLabs-TabPFN.

Licensed under the MIT License (see [LICENSE](LICENSE)).
