# Contract catalog: Contraste

Phase 2 of contract-first parallel delivery (ADR-0080; rule 11 sections 11 to 20 in CAOS_MANAGE). One row per
boundary. Each schema file under `docs/contracts/schemas/` is the single source of its contract (JSON Schema 2020-12,
one file per document kind, one folder per case): the Python producer tests and the TypeScript consumer tests
validate every committed document against it, and the TypeScript types are generated from it
(`frontend/src/lib/contract.gen.ts`, from `docs/contracts/api.openapi.json`, which `npm run gen:contracts` builds from
`docs/contracts/api.paths.json` plus one component per schema file found by walking `docs/contracts/schemas/`).
A change to a contract bumps its row's version and updates both sides in one pull request.

Contraste keeps two contracts of ADR-0057 and they are rows here, not a second system: contract 1 (the eight
ingestion families, `contract-family`, `contract-index`) and contract 2 (`case-index`, `case-manifest` and the variant
and models artifacts of each case). The run-time descriptors in `frontend/src/lib/contract.types.ts` stay and are tied
to the generated types with `satisfies Record<keyof X, Kind>`: `tsc` catches a change to the top-level keys of a tied
descriptor only. The consumer test walks each schema and its descriptor in parallel at every nesting level (key sets and
kinds), so a nested key or a type change the descriptors miss fails `npm test`.

Checks: `python scripts/check_contracts.py docs/contracts/catalog.md --repo-root .` (every field, every path),
`python scripts/check_skeleton.py docs/contracts/catalog.md` (exit 2 lists the rows still served by a provider; every
row below is `real`), `python -m pytest tests/contracts -q` (producer side) and, in `frontend/`,
`npm run check:contracts` (the generated files are current) and `npm test` (consumer side).

Discovery: a document is matched to its schema, never to a list. A schema selects by the `const` of `schema`,
`case_id`, `fit_id` and `outputs.kind` it declares and, for the hand-kept files, by an `x-location` glob; the most
specific match wins and zero or a tie fails the producer test with the path. The variant schema that declares no
`outputs.kind` is the default variant of its case: exactly one per `case_id` may (C01's and C22's today), in the Python
selector and in the TypeScript selector alike, and two for one case fail with both schema names. Every schema under
`schemas/<case>/` declares a `case_id` const equal to its folder name upper-cased (a test enforces it), so none becomes a
catch-all for its kind; every wave 2 variant schema declares an `outputs.kind` const unless it is its case's one default. Files named `*-envelope` are abstract bases that case schemas
compose (`allOf` plus `unevaluatedProperties: false`). A case added later adds a folder `schemas/<case>/` and its rows,
and edits no file of another case.
Three more conventions keep parallel units apart: the `$defs` names share one global component namespace in the generated
types (`gen-contract-types.mjs` fails on a clash), so a case prefixes its own (`c04Print`, `c05SpFit`); a name two files of
one case share must have one definition; and an `x-location` glob is single-level (`*` does not cross `/`; the Python
selector's `fnmatch` would, the TypeScript one does not, and every glob in use agrees). A schema may have no committed
document under `data/` only when its row's status is `active` (a provider serves it) or a document of it sits under
`docs/contracts/fixtures/`; `tests/contracts/test_documents.py` and `contract.test.ts` derive that set, no schema is named.
Rows of units that land after this catalog (the C01 model slot, readiness, live parity) are written as fragments in
a per-unit rows fragment (`docs/contracts/rows/<unit>.md`, a folder that exists only while a unit's rows wait) and
merged into the table below by the integrator, never edited into it by a unit.

PD ranges: PD is open (0, 1) at every estimate site and at the C05 parity points (SDD section Units gate). It stays
closed [0, 1] at the engine-input parity grids that were not narrowed (`c04-models` capital parity, whose PD 0 probes the
CRE32.4 floor and is not an estimate; the C01 irb parity; the C22 models parity), and each says so in its description or
here. Narrowing the ranges is a breaking change: `c01-variant`, `c05-sp`, `c05-ldp` and `c05-models-sp` are at 2.0.0.

## Contracts

| id | version | owner | schema file | example | producer test | consumer test | missing-data behavior | provider | model io | swap test | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| case-index | 1.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/common/case-index.schema.json | data/derived/manifests/index.json | tests/contracts/test_documents.py::test_index_validates | frontend/src/lib/contract.test.ts | missing: copy-data stops the site build (no site without an inventory); at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. stale: engine_version differs from VERSION (the index records the engine that baked it) | fixture:data/derived/manifests/index.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| case-manifest | 1.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/common/case-manifest.schema.json | data/derived/manifests/C04.json | tests/contracts/test_documents.py::test_manifests_validate | frontend/src/lib/contract.test.ts | partial: a manifest the index lists is absent; copy-data stops the build, and at run time loadManifest fails for that case only (getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart); the other cases work. stale: as case-index | fixture:data/derived/manifests/C04.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| variant-envelope | 1.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/common/variant-envelope.schema.json | data/derived/C22/null.json | tests/contracts/test_documents.py::test_every_variant_matches_the_envelope | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. The other variants and cases keep working | fixture:data/derived/C22/null.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| models-envelope | 1.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/common/models-envelope.schema.json | data/derived/C22/models-generators.json | tests/contracts/test_documents.py::test_models_validate | frontend/src/lib/contract.test.ts | partial: the models artifact a variant names (models_ref) is absent; loadCase throws ArtifactError for the variants that read it | fixture:data/derived/C22/models-generators.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| test-result | 1.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/common/test-result.schema.json | docs/contracts/examples/common.test-result.json | tests/contracts/test_documents.py::test_every_test_row_validates | frontend/src/lib/contract.test.ts | partial: a variant without tests carries an empty tests array (C04 simulation families do); the Validation view says no tests ran for that variant, never a blank table | fixture:data/derived/C05/ldp-published.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c01-variant | 2.0.0 | data-pipeline/pipeline/cases/c01_retail_pd.py | docs/contracts/schemas/c01/variant.schema.json | data/derived/C01/holdout.json | tests/contracts/test_documents.py::test_variants_validate | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. The other variants and cases keep working | fixture:data/derived/C01/holdout.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c01-models | 1.0.0 | data-pipeline/pipeline/cases/c01_retail_pd.py | docs/contracts/schemas/c01/models.schema.json | data/derived/C01/models-taiwan.json | tests/contracts/test_documents.py::test_models_validate | frontend/src/lib/contract.test.ts | partial: the models artifact of a fit (german, taiwan, taiwan-small) is absent; loadCase throws ArtifactError for the variants scored by it | fixture:data/derived/C01/models-taiwan.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c04-agency | 1.0.0 | data-pipeline/pipeline/cases/c04_agency.py | docs/contracts/schemas/c04/variant-agency.schema.json | data/derived/C04/sp.json | tests/contracts/test_documents.py::test_variants_validate | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. The other variants and cases keep working | fixture:data/derived/C04/sp.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c04-family | 1.0.0 | data-pipeline/pipeline/cases/c04_families.py | docs/contracts/schemas/c04/variant-generator.schema.json | data/derived/C04/thin.json | tests/contracts/test_documents.py::test_variants_validate | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. The other variants and cases keep working | fixture:data/derived/C04/thin.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c04-published | 1.0.0 | data-pipeline/pipeline/cases/c04_published.py | docs/contracts/schemas/c04/variant-published.schema.json | data/derived/C04/published.json | tests/contracts/test_documents.py::test_variants_validate | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. The other variants and cases keep working | fixture:data/derived/C04/published.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c04-models | 1.0.0 | data-pipeline/pipeline/cases/c04_transitions.py | docs/contracts/schemas/c04/models.schema.json | data/derived/C04/models-transitions.json | tests/contracts/test_documents.py::test_models_validate | frontend/src/lib/contract.test.ts | partial: the C04 models artifact is absent; loadCase throws ArtifactError for every C04 variant | fixture:data/derived/C04/models-transitions.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c05-sp | 2.0.0 | data-pipeline/pipeline/cases/c05_ldp_calibration.py | docs/contracts/schemas/c05/variant-sp.schema.json | data/derived/C05/sp-2010.json | tests/contracts/test_documents.py::test_variants_validate | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. The other variants and cases keep working | fixture:data/derived/C05/sp-2010.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c05-ldp | 2.0.0 | data-pipeline/pipeline/cases/c05_ldp_calibration.py | docs/contracts/schemas/c05/variant-ldp.schema.json | data/derived/C05/ldp-published.json | tests/contracts/test_documents.py::test_variants_validate | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. The other variants and cases keep working | fixture:data/derived/C05/ldp-published.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c05-models-sp | 2.0.0 | data-pipeline/pipeline/cases/c05_ldp_calibration.py | docs/contracts/schemas/c05/models-sp.schema.json | data/derived/C05/models-sp2009.json | tests/contracts/test_documents.py::test_models_validate | frontend/src/lib/contract.test.ts | partial: the S&P models artifact is absent; loadCase throws ArtifactError for the S&P variants | fixture:data/derived/C05/models-sp2009.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c05-models-ldp | 1.0.0 | data-pipeline/pipeline/cases/c05_ldp_calibration.py | docs/contracts/schemas/c05/models-ldp.schema.json | data/derived/C05/models-ldp.json | tests/contracts/test_documents.py::test_models_validate | frontend/src/lib/contract.test.ts | partial: the low-default models artifact is absent; loadCase throws ArtifactError for the ldp variants | fixture:data/derived/C05/models-ldp.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c22-variant | 1.0.0 | data-pipeline/pipeline/cases/c22_validator.py | docs/contracts/schemas/c22/variant.schema.json | data/derived/C22/null.json | tests/contracts/test_documents.py::test_variants_validate | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError (an HTTP status or a non-JSON answer); a view shows its Pending state (data-state loading) while the data is not there, and the C04 result sections show a LoadError alert (data-state error), never an empty chart. The other variants and cases keep working | fixture:data/derived/C22/null.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| c22-models | 1.0.0 | data-pipeline/pipeline/cases/c22_validator.py | docs/contracts/schemas/c22/models.schema.json | data/derived/C22/models-generators.json | tests/contracts/test_documents.py::test_models_validate | frontend/src/lib/contract.test.ts | partial: the C22 models artifact is absent; loadCase throws ArtifactError for every C22 variant | fixture:data/derived/C22/models-generators.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| contract-family | 1.0.0 | data-pipeline/pipeline/io/contract.py | docs/contracts/schemas/common/contract-family.schema.json | data/derived/contract/loan_panel.json | tests/contracts/test_documents.py::test_contract_declarations_validate | frontend/src/lib/contract.test.ts | missing: the Contract view of a family whose declaration is absent says so; copy-data stops the build for a file the index names | fixture:data/derived/contract/loan_panel.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| contract-index | 1.0.0 | data-pipeline/pipeline/io/contract.py | docs/contracts/schemas/common/contract-index.schema.json | data/derived/contract/index.json | tests/contracts/test_documents.py::test_contract_declarations_validate | frontend/src/lib/contract.test.ts | missing: copy-data stops the build (the case index lists contract/index.json as a further file) | fixture:data/derived/contract/index.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| source-registry | 1.0.0 | data-pipeline/pipeline/io/sources.py | docs/contracts/schemas/common/source-registry.schema.json | data-pipeline/config/sources.json | tests/contracts/test_documents.py::test_registries_validate | tests/contracts/test_documents.py::test_registries_validate | missing: the pipeline stops before any bake (the registry is hand-kept and committed, so it is never absent on a clone); a source without a fetch plan is read from a file the user supplies | fixture:data-pipeline/config/sources.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| licences | 1.0.0 | data-pipeline/config/licences.json | docs/contracts/schemas/common/licences.schema.json | data-pipeline/config/licences.json | tests/contracts/test_documents.py::test_registries_validate | tests/contracts/test_documents.py::test_registries_validate | missing: scripts/check_licences.py fails (a dependency without a verified licence is not allowed); hand-kept and committed | fixture:data-pipeline/config/licences.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| licence-manifest | 1.0.0 | data-pipeline/pipeline/io/fetch.py | docs/contracts/schemas/common/licence-manifest.schema.json | data/sources/manifest.json | tests/contracts/test_documents.py::test_registries_validate | tests/contracts/test_documents.py::test_registries_validate | missing: nothing was fetched on this device; a case reads the source files from the device data root or its committed derived copy, and the lineage test names the file that is absent | fixture:data/sources/manifest.json | - | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | real |
| api | 2.0.0 | app/ | docs/contracts/api.openapi.json | data/derived/manifests/index.json | tests/contracts/test_documents.py::test_every_document_matches_exactly_one_schema_and_validates | frontend/src/lib/contract.test.ts | missing: the API lane is dormant (app/ is not deployed); the site reads the committed documents. When active, a document that does not exist answers 404 with a detail string, never an empty body | fixture:data/derived/manifests/index.json | - | frontend/src/lib/contract.test.ts | real |
| readiness | 1.0.0 | data-pipeline/pipeline/core/readiness.py | docs/contracts/schemas/common/readiness.schema.json | data/derived/readiness.json | tests/test_readiness.py::test_committed_readiness_is_current | frontend/src/readiness/readiness.test.ts | missing: the site build stops at copy-data; if the document cannot be loaded at run time the views keep working and each says readiness unknown; the API answers 503 missing. The 18 planned cases are declared absent here (case-manifest is partial with their manifest paths), never filled with data | fixture:data/derived/readiness.json | - | frontend/src/readiness/readiness.test.ts | real |
| c01-pd-rung | 1.0.0 | data-pipeline/pipeline/cases/c01_ladder.py | docs/contracts/schemas/c01/models.schema.json | data/derived/C01/models-taiwan.json | tests/test_model_slot.py::test_swap_baseline_and_fitted_rungs | tests/test_readiness.py::test_a_rung_missing_from_the_models_artifact_is_training_on_the_baseline | training: a C01 models artifact lacks the fitted record of a rung (or none exists), the benchmark rung P0 answers (provenance baseline) and the Benchmark page labels the metrics with the model that answered | baseline:data-pipeline/pipeline/model/benchmark.py | in: the C01 feature matrix (a table with the columns and units of docs/cases/C01.md, one row per account); out: PD per row (number in (0, 1), a probability) | tests/test_model_slot.py::test_swap_baseline_and_fitted_rungs | real |

Parts: the sub-documents that the rows above compose have their own schema files under `docs/contracts/schemas/common/`
and an example under `docs/contracts/examples/` (`common.<name>.json`, validated by `test_examples_validate`):
`text`, `gate-verdict`, `artifact-entry`, `source-details`, `contract-summary`, `model-summary`, `model-record`,
`impact-item`, `finding`, `provenance`, `lane-block`. The `readiness` schema (`common/readiness.schema.json`, copied
from the template at v0.04.000) is produced by the provider tree of CF-B, which adds its catalog row.

## Missing-data states

One vocabulary for every row (ADR-0080 decision 3). Today the product reads committed files only, so a row is either
present (`available`) or its file is absent, and every surface says so. The states of the template apply unchanged
once CF-B adds the readiness document (written by the pipeline next to the case index), which computes each row's state from this
catalog and the repository:

| Row kind | Condition | state | provenance | reason en | reason es |
|---|---|---|---|---|---|
| case-manifest | every manifest the index lists as absent belongs to a case planned and not built (an entry of `data-pipeline/config/planned_cases.json` with no module in `cases/`) | `partial` | `real` | {{n}} of {{total}} cases are planned and not built yet: {{ids}}. | {{n}} de {{total}} casos están planificados y aún no construidos: {{ids}}. |
| c01-pd-rung | a C01 models artifact lacks the record of a fitted rung (P0-constant, P0-single, P1-scorecard, P2a-l1, P2b-pltr, P3-ebm, P4-lightgbm), or none exists | `training` | `baseline` | Fitted rung absent from the models artifact ({{artifacts}}): {{rungs}}; the benchmark rung (P0) answers. | Peldaño ajustado ausente del artefacto de modelos ({{artifacts}}): {{rungs}}; responde el benchmark (P0). |
| any | the catalog `status` is `active` | `provider` | the provider kind | Served by its provider ({{provider}}); the real producer is not built yet. | Lo sirve su proveedor ({{provider}}); el productor real aún no está construido. |
| case-index, case-manifest, variant and models rows | `data/derived/manifests/index.json` is absent | `missing` | null | The pipeline has not baked this build. | El pipeline no ha generado esta versión. |
| case-manifest | a manifest the index lists is absent | `partial` | `real` | {{n}} of {{total}} manifests are absent. | Faltan {{n}} de {{total}} manifiestos. |
| variant and models rows | an artifact a present manifest names is absent | `partial` | `real` | {{n}} of {{total}} artifacts are absent. | Faltan {{n}} de {{total}} artefactos. |
| case-index, case-manifest, variant and models rows | the index `engine_version` differs from `VERSION` | `stale` | `real` | Baked by {{engine_version}}; the product is {{version}}. | Generado por {{engine_version}}; el producto es {{version}}. |
| api | always, in the static document | `missing` | null | The API lane is dormant; the site reads the committed documents. | La API está inactiva; el sitio lee los documentos versionados. |
| any | otherwise | `available` | `real` | null | null |

What each surface does today: the workbench (`frontend/src/api/artifacts.ts`, `frontend/src/workbench/Pending.tsx`)
fetches every document through `getJSON`, which throws `ArtifactError` on an HTTP error or a non-JSON answer; a view
whose data is not there yet shows its Pending state (`data-state="loading"`), never an empty chart, and `copy-data`
stops the site build when a file the index declares is absent. The `missing` list of a `partial` state is the absent
paths relative to `data/derived/`, sorted. Contraste specifics (the training state of a model slot does not apply: no
model is trained at serve time; the readiness rows and the provider tree arrive with CF-B).

## Providers

Every row is `real`: its four built cases (C01, C04, C05, C22) have real producers, and the provider cell names the
committed document itself (`fixture:<path under data/derived>`), the file the contract tests and the frontend read.
The provider tree for the planned cases, with a readiness document that labels each served row, is CF-B's
(a fixtures folder under docs/contracts, created there). A provider is scaffolding: labelled on every surface by the readiness
document, never counted as done for the unit that owes the real producer.

## History

One row per contract version (`scripts/check_contract_versions.py`): the first row of each contract is `initial`;
a later version names its step. Schemas were written in 0.07.000 (CF-A); four rows narrowed the PD to an open interval
at estimate sites after the review (a breaking change, 2.0.0).

| contract | version | date | change | kind |
|---|---|---|---|---|
| case-index | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| case-manifest | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| variant-envelope | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| models-envelope | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| test-result | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c01-variant | 1.0.0 | 2026-10-11 | first schema, transcribed from the hand-kept descriptors (CF-A) | initial |
| c01-variant | 2.0.0 | 2026-10-12 | the PD is an open interval (0, 1) at estimate sites (CF-A review, fix 5) | major |
| c01-models | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c04-agency | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c04-family | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c04-published | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c04-models | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c05-sp | 1.0.0 | 2026-10-11 | first schema, transcribed from the hand-kept descriptors (CF-A) | initial |
| c05-sp | 2.0.0 | 2026-10-12 | the PD is an open interval (0, 1) at estimate sites (CF-A review, fix 5) | major |
| c05-ldp | 1.0.0 | 2026-10-11 | first schema, transcribed from the hand-kept descriptors (CF-A) | initial |
| c05-ldp | 2.0.0 | 2026-10-12 | the PD is an open interval (0, 1) at estimate sites (CF-A review, fix 5) | major |
| c05-models-sp | 1.0.0 | 2026-10-11 | first schema, transcribed from the hand-kept descriptors (CF-A) | initial |
| c05-models-sp | 2.0.0 | 2026-10-12 | the PD is an open interval (0, 1) at estimate sites (CF-A review, fix 5) | major |
| c05-models-ldp | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c22-variant | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c22-models | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| contract-family | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| contract-index | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| source-registry | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| licences | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| licence-manifest | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| api | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| api | 2.0.0 | 2026-10-12 | the C06 and C07 models and variant schemas added to the documents the API may serve (U5); a client that handles every known document meets new ones | major |
| readiness | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
| c01-pd-rung | 1.0.0 | 2026-10-11 | first schema of the contract | initial |
