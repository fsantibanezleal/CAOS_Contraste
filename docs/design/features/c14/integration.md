# Integration notes: U10-P1, case C14

What the unit leaves to the integrator because the files are outside its write scope (the brief of U10-P1 lists the index, the
readiness and the catalog as out of scope). None of it changes a C14 document.

1. Register the licence manifest rows: merge `sources` of `data/derived/C14/raw-sources.txt` into `data/sources/manifest.json` (the
   two rows `fdic-bankfind` and `treasury-par-curve`, in the file's own format). Until then `scripts/check_provenance.py` reports the
   input hashes of C14 as not pinned by the licence manifest.
2. Add the two fetch specifications to `data-pipeline/config/sources.json` if `data-pipeline/fetch.py` is to fetch them (the unit
   fetches with `data-pipeline/pipeline/cases/c14/fetch.py`, which writes the same records).
3. Rebuild the index and the readiness: `python data-pipeline/run.py index` and `python data-pipeline/run.py readiness`, then update the
   count tests that name the built cases (`tests/test_registry.py`, `tests/test_readiness.py`, `tests/contracts/test_documents.py`):
   the case is discovered by its `CASE` object (`cases/c14/__init__.py`), so C14 is built as soon as the package is merged.
4. Move `cases/c14/treasury.py` to `pipeline/io/treasury.py` when the C11 bake (U8-P1) needs the same reader (sizing reservation R2).
5. Contract amendments to consider (each is a question for the contract owner, none blocks the documents): an `observation_date` in
   `c14Curve` for a valuation date that is not a business day; per-shock prepayment flows in `net_cash_flows` (SRP31.119); a floor
   that can be the maturity-dependent one of SRP31.93; the `ear_se` below `|ear|` rule of `check_c14`, which refuses a statistically
   zero EaR (the 95 percent EaR of 2022-Q4 is 0.0 within its Monte Carlo error at 10 000 paths, so the bake uses 100 000).
