# Architecture, overview

Contraste is an instance of the CAOS product archetype (ADR-0057): the science runs offline, its results are
committed, and a static web workbench replays them and recomputes, live, what is light and exact. The base (the
layout, the two contracts, the stage names, the lanes, the guards, the shared shell) comes from the template and the
shell; Contraste's own work is the core: the model families, the cases, the validation, the views and the content.

## The lanes

| Lane | Where | What runs |
|---|---|---|
| Offline | `data-pipeline/`, in `.venv-pipeline` | fetch and contract 1, the leakage-safe split, every rung of every ladder, the battery of `riskvalidation`, export through contract 2; the only lane that writes artifacts |
| Replay | `data/derived/`, copied into the site | the committed artifacts, read as they are; gradient-boosting and TabPFN scores are always replayed |
| Live | `frontend/src/engine/`, `frontend/src/lib/policy.ts` | an applicant's scorecard and EBM scores, every light under the reader's policy, the decision at any approval rate and LGD; held to the pipeline by parity tests |
| API | `app/` | dormant (no server state, no private data, no request-time compute) |

## The flow

A source of the registry (`data-pipeline/config/sources.json`) is fetched into the device data root and hashed into
the licence manifest (`data/sources/manifest.json`); its reader maps the publisher's layout; contract 1 accepts,
rejects, flags or excludes each record; the split locks a holdout and a calibration slice; the ladder is fitted on
the training slice; the battery runs on each variant's evaluation set; every result is checked against the case's
expected ranges; contract 2 writes the index, the case manifest, the models artifacts and the variant artifacts, each
with its provenance. The web copies exactly the declared files, reads them as JSON, and recomputes the live parts.

## What holds it

The pipeline's tests run in a sandbox that fails the session if a committed artifact changes; the leakage tests run
the ladder twice and require that nothing outside the training information moves it. The web's contract test reads
every committed artifact against the web's declaration in both directions; the parity tests hold the live scorers to
the pipeline to 1e-9 and the live policy to every committed light; the measured gate walks the built site at five
sizes, in both themes and both languages. In CI: the artifacts and their manifests, the provenance, the data
classes, the licences, the version, the SDD, the deploy place, the content standards and the CI budget.
