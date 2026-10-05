# data/, the contracts and the layout

This folder holds what the pipeline commits: the contract declarations, the licence manifest and the compact
artifacts the web replays. Raw data never lives here; it lives in the device data root (`CONTRASTE_DATA`, see
[`../docs/architecture/08_data-contracts.md`](../docs/architecture/08_data-contracts.md)).

## Layout

| Path | What | Git |
|---|---|---|
| `sources/manifest.json` | the licence manifest: every fetched source with its URL, retrieval date, licence class, licence text and the SHA-256 and byte count of each file | committed |
| `derived/contract/` | contract 1, one declaration per ingestion family (`<family>.json`) and an `index.json`, exported by the pipeline | committed |
| `derived/manifests/` | contract 2: the flat `index.json` and one `<case>.json` per case | committed |
| `derived/<case>/<variant>.json` | contract 2: the per-variant artifact (model, outputs, tests, impact, findings, provenance, lane) | committed |
| `raw/` | never used for fetched data, which goes to the data root; a mirror-allowed sample may be committed here only under `raw/<source>/` | git-ignored |
| `examples/`, `samples/`, `demo/` | small files that pass contract 1, for the bring-your-own-data guide and smoke runs | committed |

## Contract 1, ingestion

Eight families (`scored_sample`, `loan_panel`, `rating_history`, `market_series`, `curve`, `balance_sheet`,
`loss_events`, `macro_path`), declared in `data-pipeline/pipeline/io/contract.py`. Every record is accepted,
rejected (each violation names the field, the value, the expected range and the policy), flagged (accepted and
reported) or excluded (valid, but outside the case's use, and counted). Nothing is coerced.

## Contract 2, artifacts

The index, one manifest per case and one artifact per variant, built only through
`data-pipeline/pipeline/core/manifest.py`, which refuses an artifact whose lineage includes a link-only or
unusable source before anything is written.

## Provenance and licences

Every source is declared in `data-pipeline/config/sources.json` with the verbatim fragment of its licence and its
class: mirror-allowed, derived-only, link-only or unusable. Raw rows are committed only from mirror-allowed sources;
from a derived-only source only aggregates, fitted parameters and results are committed; a link-only or unusable
source is linked from the web and never read. Three guards hold this: `scripts/check_data_classes.py` (no raw rows
of a non-mirror source anywhere, by path and by hash), `scripts/check_provenance.py` (every artifact's provenance
is true against the registry and the licence manifest) and the lineage refusal in the export stage.
