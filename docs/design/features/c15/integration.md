# Integration notes: U10-P2, case C15

What the unit leaves to the integrator because the files are outside its write scope (the brief of U10-P2 lists the index, the readiness,
the catalog, the planned-cases list, the registry count tests, CHANGELOG.md and VERSION as out of scope). None of it changes a C15 document.

1. The licence manifest rows are done in this unit (`data/sources/manifest.json`, row `bcch-bde`, the 13 raw files of September 2026): the
   provenance check passes with them.
2. Rebuild the index and the readiness: `python data-pipeline/run.py index` and `python data-pipeline/run.py readiness`, then update the count
   tests that name the built cases (`tests/test_registry.py`, `tests/test_readiness.py`, `tests/contracts/test_documents.py`) and the planned-cases
   list: the case is discovered by its `CASE` object (`cases/c15/__init__.py`), so C15 is built as soon as the package is merged. The row C15 of
   `docs/cases/README.md` changes from planned to built.
3. `data-pipeline/config/sources.json` names the source `bcch-bde` with `fetch: null`; the unit fetches with `python -m pipeline.io.bcch fetch`
   (which needs `BCCH_USER` and `BCCH_PASSWORD`), so no fetch specification is added there.
4. Contract questions for the contract owner (none blocks the documents): the EaR and EVaR block of `c15-outputs` and the anchored pesos curve
   (see `design.md`, open questions 1 and 2).
5. `content/executive.json` and the views (`frontend/src/workbench/c15/`) are the views unit's; the documents validate against the same schemas the
   fixtures do.
