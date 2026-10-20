# Integration notes: U11-P, case C16

What the unit leaves to the integrator because the files are outside its write scope. None of it changes a C16 document.

1. **Licence manifest rows.** Merge `sources` of `data/derived/C16/raw-sources.txt` into `data/sources/manifest.json` (the rows
   `fdic-bankfind`, `fed-h8`, `fed-svb-review` and `treasury-par-curve`, in the file's own format). The Treasury rows repeat C14's.
2. **Fetch specifications.** `data-pipeline/config/sources.json` rows `fdic-bankfind`, `fed-h8` and `fed-svb-review` carry `fetch: null`;
   the unit fetches with `data-pipeline/pipeline/cases/c16/fetch.py` (the FDIC wide span 2009-12-31 to 2022-12-31 in its own file, the 19
   H.8 release pages, the Board review PDF), which writes `provenance-c16.json` per folder and never touches C14's file or sidecar. The
   Board's CDN answers 403 for a Friday release date that has no page; the fetch reads that as "try the Thursday". Rows for BCBS d555
   Table A.1 and the ECB LiST note are not added: they are engine constants with their source (sizing R3, A6).
3. **Registry, index and readiness.** The case is discovered by its `CASE` object (`cases/c16/__init__.py`); rebuild with
   `python data-pipeline/run.py index` and `python data-pipeline/run.py readiness`, remove the planned entry of C16 from
   `config/planned_cases.json` and update the count tests that name the built cases.
4. **Contract amendment proposed.** Decision X3 asks for null Level 2 shares with their reason when the HQLA stock is empty. The
   `c16Hqla` definition types `l2_share` and `l2b_share` as numbers in [0, 1] and is a closed object, so such a document cannot validate;
   the bake refuses an empty stock naming this. Proposed: `l2_share` and `l2b_share` nullable and a `shares_reason` label (null when the
   shares are numbers), with the checker of `semantics.py` already skipping the share checks when HQLA is not positive. The real bank has a
   Level 1 stock, so no committed document is affected.
5. **Call-report field list.** `c16Report.fields` is an enumeration of FDIC names; the maturity-band fields the ladder reads (`SCNM*`,
   `SCPT*`, `LNRS*`, `LNOT*`, `CD*`, `OTHBFH1L` and the others) are not in it, so the documents list the enumerated fields only. Adding them
   would let a document name every field it read.
6. **Engine pin.** `data-pipeline/requirements.txt` pins `riskvalidation` by the commit `a52888e` of branch `task/u11-liquidity`; the
   integrator repoints it to the release tag when it is cut. The documents name the engine as `0.7.0+a52888e`; a re-bake after the repoint
   changes that string in `provenance` and the manifest only if the version differs.
7. **Shared registries.** The C16 registry line, the readiness row, the catalog rows `c16-*` and `CHANGELOG.md` are the integrator's; the
   change fragment is `changes/U11-P.md`.
