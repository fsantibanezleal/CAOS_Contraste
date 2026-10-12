# Catalog rows of unit CF-B (producers, readiness, the 22-case index, the C01 model slot)

The integrator merges the two tables below into `docs/contracts/catalog.md` (the `## Contracts` and the
`## Missing-data states` tables), deletes this file, and then runs `python data-pipeline/run.py readiness`: the
readiness is computed from the catalog, so it changes with the merge (its `catalog_sha256` and the two new rows).
`tests/test_readiness.py` reads this fragment next to the catalog until it is merged.

## Contracts

| id | version | owner | schema file | example | producer test | consumer test | missing-data behavior | provider | model io | swap test | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| readiness | 1.0.0 | data-pipeline/pipeline/core/readiness.py | docs/contracts/schemas/common/readiness.schema.json | data/derived/readiness.json | tests/test_readiness.py::test_committed_readiness_is_current | frontend/src/readiness/readiness.test.ts | missing: the site build stops at copy-data; if the document cannot be loaded at run time the views keep working and each says readiness unknown; the API answers 503 missing. The 18 planned cases are declared absent here (case-manifest is partial with their manifest paths), never filled with data | fixture:data/derived/readiness.json | - | frontend/src/readiness/readiness.test.ts | real |
| c01-pd-rung | 1.0.0 | data-pipeline/pipeline/cases/c01_ladder.py | docs/contracts/schemas/c01/models.schema.json | data/derived/C01/models-taiwan.json | tests/test_model_slot.py::test_swap_baseline_and_fitted_rungs | tests/test_readiness.py::test_a_rung_missing_from_the_models_artifact_is_training_on_the_baseline | training: a C01 models artifact lacks the fitted record of a rung (or none exists), the benchmark rung P0 answers (provenance baseline) and the Benchmark page labels the metrics with the model that answered | baseline:data-pipeline/pipeline/model/benchmark.py | in: the C01 feature matrix (a table with the columns and units of docs/cases/C01.md, one row per account); out: PD per row (number in (0, 1), a probability) | tests/test_model_slot.py::test_swap_baseline_and_fitted_rungs | real |

Change to an existing row (not a new row): the `api` row's producer test gains `tests/test_dormant_api.py` (the
service layer, `/api/readiness`, 503 with the declared state for a planned case's manifest, 404 for an unknown case),
and `docs/contracts/api.paths.json` needs the `/api/readiness` route and the 503 body of the manifest route (outside
this unit's write scope).

## Missing-data states

Rows to insert in the catalog's table, in this order: the first before the row for an absent manifest, the second after
the row for the api.

| Row kind | Condition | state | provenance | reason en | reason es |
|---|---|---|---|---|---|
| case-manifest | every manifest the index lists as absent belongs to a case planned and not built (an entry of `data-pipeline/config/planned_cases.json` with no module in `cases/`) | `partial` | `real` | {{n}} of {{total}} cases are planned and not built yet: {{ids}}. | {{n}} de {{total}} casos están planificados y aún no construidos: {{ids}}. |
| c01-pd-rung | a C01 models artifact lacks the record of a fitted rung (P0-constant, P0-single, P1-scorecard, P2a-l1, P2b-pltr, P3-ebm, P4-lightgbm), or none exists | `training` | `baseline` | Fitted rung absent from the models artifact ({{artifacts}}): {{rungs}}; the benchmark rung (P0) answers. | Peldaño ajustado ausente del artefacto de modelos ({{artifacts}}): {{rungs}}; responde el benchmark (P0). |
