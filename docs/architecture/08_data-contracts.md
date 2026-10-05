# The two data contracts

A product is real when its data flows through two enforced contracts.

## Contract 1, ingestion (raw to pipeline)

`data-pipeline/pipeline/io/contract.py` declares the required fields, their units and ranges, and the outlier
policy. A record is rejected with its reason when a value is missing, non-numeric, NaN, infinite or out of range
(and, in the example, when the initial infected exceed the population); a plausible but unusual record is accepted
and flagged (the example flags R0 above 20), and the flag is carried into the manifest. Nothing is coerced. This is
the door through which a reader's own data enters ([guide 02](../guides/02_bring-your-own-data.md)).

## Contract 2, artifacts (pipeline to web)

`data-pipeline/pipeline/core/trace.py` and `data-pipeline/pipeline/core/manifest.py` write, into `data/derived/`:

- `data/derived/manifests/index.json` (`example.index/v2`): every case with its bilingual title and category, and the case the
  App opens on;
- `manifests/<case>.json` (`example.manifest/v3`): parameters, seed, engine and version, the artifact and its byte
  size, the lane verdict, the evaluation metrics, the expected ranges, and the bilingual expected band;
- `<case>/trace.json` (`example.trace/v1`): 200 points of the trajectory, two decimals, and its summary.

## How they are held

- The bake fails when a result lies outside its case's expected range (`data-pipeline/pipeline/core/expect.py`).
- `scripts/check_artifacts.py` (CI) checks that the index, the manifests and the artifacts agree, byte sizes
  included, and that each lane matches its gate.
- `frontend/src/lib/contract.types.ts` declares contract 2 for the web, as interfaces and as run-time descriptors
  tied to them by `tsc`; `frontend/src/lib/contract.test.ts` reads every committed artifact against the descriptors
  in both directions: a key written and not read, a key read and not written, and a value of the wrong type (a
  boolean is not a number) each fail.
- `frontend/scripts/copy-data.mjs` copies exactly the declared files into the site and fails on a missing one; the
  web fetches them with the version in the address and refuses an answer that is not JSON.
