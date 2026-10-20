# Integration notes: U9-P1, case C12

What the unit leaves to the integrator because the files are outside its write scope (the registries, the index, the readiness and
the catalog). None of it changes a C12 document.

1. Add the registry row `treasury-hqm` to `data-pipeline/config/sources.json` (its fields are `HQM_SOURCE` in
   `data-pipeline/pipeline/cases/c12/fetch.py`, class mirror-allowed, cases C12; the licence sentence is UNVERIFIED on the Treasury
   side, FRED tags the series "Public Domain: Citation Requested"), and the licence class in `licences.json`; merge `sources` of
   `data/derived/C12/raw-sources.txt` into `data/sources/manifest.json` (the rows `treasury-par-curve`, 37 files, and
   `treasury-hqm`, 3 files). Until then `scripts/check_provenance.py` cannot pin the C12 inputs.
2. Rebuild the index and the readiness (`python data-pipeline/run.py index`, `readiness`) and update the count tests that name the
   built cases; C12 is discovered by its `CASE` object (`cases/c12/__init__.py`). The category `counterparty` is new; the case
   registry and the catalog rows are the integrator's.
3. `data-pipeline/requirements.txt` now pins the engine by the commit of the batch 3 engine integration branch
   (`25e9538faf10bfdbcde03c5adccffd8e86ec275c`) until the main session tags the release; the other cases ran on v0.07.000, the
   commit is a superset (the C11, C13 and C14 bakes were not re-run in this unit). `data-pipeline/requirements-ore.txt` holds ORE
   1.8.17.0 and QuantLib 1.44 (pipeline only).
4. `docs/design/SDD.md` lines 283 and 482 (ORE in WSL and its fallback) are superseded by decision D4: ORE ran natively from the
   `cp313-win_amd64` wheel, recorded in `ore_reconciliation.platform` with its timing.
5. Contract amendments to consider (each is a question for the contract owner, none blocks the documents):
   - Initial margin (decided by the main session): `check_c12` in `tests/contracts_u9/semantics.py` was amended on this branch, for that
     one rule only, from `ee == max(ee_vm_only - dim, 0)` to `max(ee_vm_only - dim, 0) <= ee <= ee_vm_only`; `dim` is the mean regression
     DIM. The integrator carries the rule into the contract text and the schema description.
   - `c12Regulatory.effective_maturity_years` has no null: a book whose first-year effective EE is zero has an undefined M and no
     document is written (the bake raises); a nullable field with a reason would let the variant publish.
   - The undiscounted EE is a measure-dependent quantity; the contract's `expected_exposure(values, None)` is the mean in the
     simulation measure. The documents use the t-forward measure (see `design.md`); the contract text should say which.
   - The minimum transfer amount acts on the report grid in the engine's `variation_margin_exposure` and on ORE's own call schedule
     in ORE; the ORE rows with MTA = 10,000 USD differ, and the gap shrinks but does not close when MTA is zero (rows `ccr.reconcile_ee_profile`
     with segment `minimum-transfer-amount-0`).
