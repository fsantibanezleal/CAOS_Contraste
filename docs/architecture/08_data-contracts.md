# The two data contracts, the sources and their licences

Contraste is real only if its data flows through two enforced contracts and every input carries its licence.
The design is section 2 of [the SDD](../design/SDD.md); the requirements and their gates are in
[`../design/features/contracts/requirements.md`](../design/features/contracts/requirements.md).

## Sources, licence classes and the data root

`data-pipeline/config/sources.json` declares every data and scenario source the plan names: the publisher, the
landing page, the verbatim fragment of its licence or terms, the redistribution class, the access method, the cases
that read it, and the open questions (anything the research could not confirm at a primary page stays marked
UNVERIFIED). The four classes:

| Class | May a case read it? | What the repository and the web may carry |
|---|---|---|
| mirror-allowed | yes | raw rows (with attribution where required), aggregates, results |
| derived-only | yes | only aggregates, fitted parameters and results; never rows |
| link-only | no | a link to the publisher |
| unusable | no | a link at most, with the reason |

`data-pipeline/fetch.py <source>` downloads a source into the device data root, at
`<data root>/raw/<source>/<file>`. The data root is the environment variable `CONTRASTE_DATA` or the `--data-root`
argument; a root inside the repository is refused. Each file is hashed while it streams, and the licence manifest
`data/sources/manifest.json` records the URL, the retrieval date, the class, the licence text, the SHA-256 and the
byte count. The manifest pins each hash: a later fetch that finds other bytes fails and names the file, unless
`--refresh` accepts the new release (and the diff shows it). A source behind a registration is placed in the data
root by hand and the fetcher only hashes and records it.

## Contract 1, ingestion (raw to pipeline)

`data-pipeline/pipeline/io/contract.py` declares eight families. Each family lists its fields (kind, unit, range or
allowed values, required or not, and what happens when one is missing), its rules across fields or across the
records of a group, and the dataset parameters it needs.

| Family | What it carries | Rules beyond the field ranges |
|---|---|---|
| `scored_sample` | one row per obligor or account at its observation date: target, optional score, PD, grade, segment, protected attribute; the case adds its features | unique per identifier and date; a missing feature is flagged |
| `loan_panel` | one row per account per reporting date: dates, balance, limit, EIR, days past due, default, prepayment and write-off flags, workout cash flows | origination on or before reporting; a revolving limit covers the balance; a workout cash flow carries its date; a rise of days past due above 31 per month is flagged; an open workout at the cutoff is excluded and counted |
| `rating_history` | one rating per obligor and date, on a declared scale that includes D | a withdrawn rating (WR) is excluded, censored or kept as a state, as the case declares, and counted |
| `market_series` | one value per series and date, as a return, a log return, a level or a decimal rate | a gap over five business days is flagged; nothing is forward-filled across a forecast date |
| `curve` | one rate per curve date and tenor, with its compounding | tenors strictly increasing within a date; a rate outside [-0.05, 0.30] is flagged |
| `balance_sheet` | one amount per item, currency (USD, CLP, CLF, EUR) and repricing band (the 19 bands of SRP31.96 Table 3), with its behavioural class | a core share or core maturity above the SRP31 Table 4 cap is flagged, and the engine applies the cap |
| `loss_events` | one row per operational loss event, with its Level 1 event type (OPE25.17 Table 2) | a loss below the collection threshold is rejected (truncation is modelled, not hidden); a recovery above its loss is flagged |
| `macro_path` | one value per scenario, variable and date, with the date the path was published | a path published after the model's observation date is rejected (no look-ahead) |

Values are parsed strictly by their declared kind, so text read from a CSV becomes the declared number or date or
is rejected; nothing is clipped, filled or guessed. `validate()` returns the accepted records, the rejected ones
(every violation with its field, value, expected range and policy), the flagged ones, the excluded ones and the
columns it ignored. The declarations are exported to `data/derived/contract/`, where the web reads them for
bring-your-own-data, and `frontend/src/lib/contract.types.ts` mirrors them; `frontend/src/lib/contract.test.ts`
checks the export against the mirror in both directions.

## Contract 2, artifacts (pipeline to web)

`data-pipeline/pipeline/core/manifest.py` builds three documents, each with a versioned schema id:

- `data/derived/manifests/index.json` (`contraste.index/v1`): every case with its bilingual title and category, and
  the case the App opens on;
- `data/derived/manifests/<case>.json` (`contraste.manifest/v1`): the case's question, its sources, the seed, the
  engine versions, the contract-1 report of its inputs, its expected ranges, and one entry per variant (title,
  regime, truth status, artifact path and bytes, lane and gate verdict);
- `data/derived/<case>/<variant>.json` (`contraste.case/v1`): the model record of every rung, the outputs, the
  `TestResult` rows from `riskvalidation`, the impact (capital, provisions, liquidity, IRRBB), the findings (S1 to
  S4, each citing the tests that evidence it), the provenance and the lane.

`build_artifact` refuses, before anything is written, a lineage that includes a link-only or unusable source or a
source never fetched (no hashes vouch for it), and checks every block: test rows are exactly `TestResult` rows with
a reference, an H0 and a policy version; findings cite tests present in the artifact; impacts are finite with a unit
and a bilingual label. The provenance block is written from the same lineage object that was checked.

## How they are held

| Guard | Where it runs | What fails it |
|---|---|---|
| `tests/test_contract.py` | locally, `pytest` | a family that accepts a violation, coerces a value, or loses its bilingual declaration |
| `tests/test_sources.py` | locally | a registry entry without a class or licence text, a case reading a link-only source, a fetch without a manifest row, a data root inside the repository, a changed hash accepted silently |
| `tests/test_licence_lineage.py`, `tests/test_manifest.py` | locally | an artifact written from a non-publishable lineage, or with a malformed block |
| `scripts/check_artifacts.py` | CI | the index, manifests and artifacts disagree, byte sizes included |
| `scripts/check_provenance.py` | CI | an artifact without true provenance |
| `scripts/check_data_classes.py` | CI | raw rows of a non-mirror source anywhere in the tree, by path or by hash |
| `scripts/check_licences.py` | CI (`--installed` locally) | a requirement without a verified licence, or an AGPL, GPL or BSL package |
| `frontend/src/lib/contract.test.ts` | CI (web job) | the exported contracts or the committed artifacts differ from what the web declares |
