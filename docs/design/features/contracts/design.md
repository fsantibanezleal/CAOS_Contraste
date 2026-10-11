# Design: U0, the contracts, the sources and their licences

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 2 and 6.

## Contract 1, the ingestion families

`data-pipeline/pipeline/io/contract.py` declares eight families (section 2.1 of the SDD). A family is a tuple of
`Field` declarations (name, kind, unit, range with open or closed ends, allowed values, required or optional) plus
cross-field rules (`origination_date <= reporting_date`, `limit >= balance` for revolving lines, monotone tenors
within a curve date). `validate(family, records)` returns the accepted records, the rejected ones (each with the
field, the value, the expected range and the policy that applied) and the flags (accepted, but reported: a gap of
more than five business days, a rate outside [-0.05, 0.30], a missing optional feature). Nothing is coerced: a
string where a number is declared is rejected, not parsed. `export_contracts()` writes each family as JSON to
`data/derived/contract/<family>.json`, which the web reads for bring-your-own-data and which
`frontend/src/lib/contract.types.ts` mirrors.

## The source registry and the licence manifest

`data-pipeline/config/sources.json` declares every source the plan names (dossier 08, the master matrix): id,
publisher, landing page, download URLs (when direct), the verbatim licence fragment, the licence class, the access
method, the cases that use it and the open questions (UNVERIFIED items stay marked). `pipeline/io/sources.py`
loads and checks it: each class is one of the four, each fragment is non-empty, and a case may read a link-only or
unusable source only to link it, never as an input.

`pipeline/io/fetch.py` downloads a source's files into the device data root (`CONTRASTE_DATA` or `--data-root`,
refused if it resolves inside the repository), streams each file through SHA-256, and writes the licence manifest
`data/sources/manifest.json`. The manifest pins each file's hash: a later fetch that finds a different hash fails
and names the file unless `--refresh` is given, in which case the new hash and date are recorded and the change is
visible in the diff. Sources behind a registration (Freddie Mac) or a bot wall (BCCh IEF) have a manual
placement path: the file is placed in the data root by hand, and the fetcher only hashes and records it.

## Lineage and provenance

`pipeline/core/lineage.py` carries, for every artifact, the list of inputs (source id, class, file hashes) and the
truth status. The export stage calls `assert_publishable(lineage)` before writing: a link-only or unusable input
raises `LicenceError` naming the source. Every artifact's `provenance` block is written from the same object, so
what the artifact claims and what the gate checked cannot differ.

## The guards

- `scripts/check_licences.py`: every requirement of the default install (`requirements-precompute.txt`,
  `requirements-api.txt`) has a verified licence in `data-pipeline/config/licences.json`, none of them AGPL, GPL or
  BSL; the frontend's installed packages are read from `frontend/package-lock.json`. With `--installed` it also
  compares the table with the metadata of the packages installed in the running interpreter.
- `scripts/check_data_classes.py`: raw rows may be committed only under `data/raw/<source>/` and only for a
  mirror-allowed source; no tracked file anywhere else may match the hash of a fetched file of a non-mirror source.
- `scripts/check_provenance.py`: every artifact the index reaches carries a provenance block whose truth status,
  licence classes and file hashes agree with its manifest, the registry and the licence manifest, and the
  manifest's `sources` are exactly what its artifacts read.
- `tests/test_guards.py` plants a violation for each guard in a throwaway tree and runs the real script, so a guard
  that stops catching its violation fails the suite (ADR-0078: the base validates itself).
