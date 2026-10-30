# Contraste

**Site:** https://contraste.fasl-work.com (GitHub Pages), published from `main`.

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

## Areas

The repository by areas. Each row links its folder, says whether the area is active or dormant, and points to the area's own
document. The 22 cases (21 committed, C19 planned: `data/derived/readiness.json`) are described one page each in
[`docs/cases/`](docs/cases/README.md), with the coverage matrix.

| Area | Folder | Status | What it holds |
|---|---|---|---|
| Web | [frontend/](frontend/) | active | The static React site on the shared CAOS app shell (`@fasl-work/caos-app-shell`, pinned exactly in `frontend/package.json`): the App workbench and the pages Introduction, Methodology, Implementation, Experiments and Benchmark, in English and Spanish, light and dark; it replays the committed artifacts and computes live what a reader changes. Run it with `cd frontend && npm ci && npm run dev`; `npm test`, `npm run build` and `npm run gate` (the measured UI gate, local only). Live at https://contraste.fasl-work.com. Design: [docs/design/features/web/](docs/design/features/web/requirements.md) |
| API | [app/](app/) | dormant: this solution does not require a request-time backend at the moment | A FastAPI layer kept for activation on an ADR-0002 trigger: six read-only endpoints over the committed documents: `GET /api/cases`, `/api/cases/{case_id}/manifest`, `/api/artifacts/{path}` and `/api/readiness`, plus the health checks `/health` and `/healthz`. See [app/README.md](app/README.md) and [the guide](docs/guides/04_run-the-api.md) |
| Core pipelines | [data-pipeline/](data-pipeline/) | active: offline only, never in CI | Fetch with a licence manifest, contract 1 on every input record, the model ladder, the validation battery and contract 2 on every artifact: `fetch.py`, `run.py` (a sandbox bake with `--output <folder>`, the release bake without) and `validate.py` (your own scored sample). One package of code per case under `pipeline/cases/`. See [the fetch and bake guide](docs/guides/01_fetch-and-bake.md) and [the pipeline architecture](docs/architecture/05_precompute-pipeline.md) |
| Packages | (PyPI) [riskvalidation 1.1.0](https://pypi.org/project/riskvalidation/1.1.0/) | active: one package, published on PyPI | `riskvalidation`, the engine of every validation test, regulatory calculator and generator (MIT), consumed as a dependency and never copied: the notebooks pin the release v0.08.000 as `riskvalidation==1.1.0`, and the pipeline pins it in `data-pipeline/requirements.txt`. The third-party packages are pinned in the same files, in the SDD technology table and in [the framework cards](docs/frameworks.md) |
| Notebooks | [notebooks/](notebooks/) | active | Didactic notebooks in two trees, [English](notebooks/en/README.md) and [Spanish](notebooks/es/README.md), by topic and from simple to complex (fundamentals, the method in practice, comparison with published methods, proposed methods), executed and committed. Fourteen topics, from installing the engine to validating the validator. Run them with `./scripts/setup.sh --notebooks` and `python scripts/run_notebooks.py`. See [notebooks/README.md](notebooks/README.md) |
| Data | [data/](data/) | active | The licence manifest of every source (`data/sources/manifest.json`), the committed derived artifacts and manifests the site replays (`data/derived/`, one folder per case, plus `readiness.json`) and two synthetic scored samples for your own-model door (`data/examples/`). Raw data never lives here: it lives under `CONTRASTE_DATA`. Every source has a licence class (mirror-allowed, derived-only, link-only, unusable). See [data/README.md](data/README.md) |
| Contracts | [docs/contracts/](docs/contracts/) | active | The catalog of every boundary and model slot with its version, schema, producer and consumer tests; the JSON schemas, the engine API documents, the fixtures served while a case is unbuilt, the OpenAPI document and the version lock. See [the catalog](docs/contracts/catalog.md) |
| Documentation | [docs/](docs/) | active | The software design document with every requirement and the gate that fails when it is violated, the feature folders, the architecture pages, the framework cards, the guides and the case pages. See [docs/README.md](docs/README.md) and [the design](docs/design/SDD.md) |
| Tests and gates | [tests/](tests/), [scripts/](scripts/) | active | The pipeline, contract, guard, notebook-layer and adversarial tests (a folder per case and per contract unit), and the guards CI runs: SDD, contracts, artifacts, provenance, licences, notebooks and this README's areas. Tests run locally, not in CI. See [scripts/README.md](scripts/README.md) |
| Deploy | [deploy/](deploy/) | active | One place: GitHub Pages with the custom domain contraste.fasl-work.com, deployed by a workflow that runs after CI succeeds on `main`, checks the committed artifacts, builds and deploys; it never rebakes. See [deploy/pages.md](deploy/pages.md) |

## The web

Six routes on the shared CAOS shell, in English and Spanish, light and dark: the App (a workbench with six groups:
Model, Validation, Impact, Findings, Variants, Context), Introduction, Methodology, Implementation, Experiments and
Benchmark. The App replays the committed artifacts and computes live what a reader changes: the scorecard and EBM
scores of an applicant, the lights under the reader's own policy thresholds, the decision and the IRB capital at the
reader's approval rate and LGD (C01); a portfolio's drift under an agency's one-year matrix towards its TTC
portfolio, the PD intervals at the reader's default correlation and the IRB risk weight under each default definition
(C04); the PD curve of every calibration approach, the low-default bounds and their
capital (C05); the exact size and power of the binomial, Vasicek-corrected and Jeffreys tests for the reader's own
portfolio (C22). Every live computation is a TypeScript port held to the engine on exported parity points.

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
are under the Prior Labs License v1.1: built with PriorLabs-TabPFN. C04 reads ESMA's CEREP, whose reproduction is
authorised provided the source is acknowledged: every C04 table says "Source: ESMA CEREP; tables transformed by
Contraste" and names the agency's entity. The three papers C04 recomputes (Israel, Rosenthal and Wei 2001; Schuermann
and Hanson 2004; Engelmann 2024) are read from the data root, and only the numbers recomputed from them are committed,
never the agency matrices they reprint.

Licensed under the MIT License (see [LICENSE](LICENSE)).
