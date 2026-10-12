- Contracts U5-S: the C06 case documents (`docs/contracts/schemas/c06/`: `variant-reporting-date` with outputs.kind
  `reporting-date`, and `models`) and the C07 case documents (`c07/`: `variant-three-regime` with outputs.kind
  `three-regime`, and `models`), each strict both ways, PD open (0, 1) at estimate sites, every money block carrying its
  `currency`, nullable fields with their reason where the bake may lack data; four fixture documents under
  `docs/contracts/fixtures/c06/` and `c07/` (labelled fixtures, never results).
- Contracts U5-S: the engine provisions API contract `docs/contracts/engine/provisions-api.md` 1.0.0: signatures, units,
  invariants and goldens (the 2.68% against 1.80% non-linearity example, the B-1 cells, the Annex 9 tables) of the term
  structure, staging, ECL, overlays, reconciliation, IFRS 9 battery, CMF B-1 and BdE Annex 9 modules; catalog rows in
  `docs/contracts/rows/U5.md`; tests in `tests/contracts_u5/`.
- Contracts U5-S, review fixes: the C06 and C07 schemas, the four fixtures, the engine provisions API and the rows fragment are
  corrected after the Opus review (fixes 1 to 14); the contracts stay at version 1.0.0 because nothing has consumed them yet.
  Engine API: competing risks are their own `CompetingRisks` record with `forward_pd` as `(F_D(b) - F_D(a)) / S_all(a)`; one
  tolerance basis `1e-6 * max(1, G)` (G the total gross carrying amount); `Overlay.stage` (null is carried in the stage1
  closing); an explicit POCI mask; the low credit risk exemption scope and `lcr_exempt`; one path for the collective transfer;
  Annex 9 doubtful buckets in days; the 0.50% minimum on the individual normal portfolio; a light rule per validation function;
  Aalen-Johansen when prepayment competes.
- Contracts U5-S, C06: waterfall line ids equal allowance movement ids (`overlay-<id>` for overlays), a GCA movement enum,
  non-negative stage 1 to 3 allowances, a re-balanced fixture, one staging policy source (`settings.sicr` with `default_dpd` and
  `low_credit_risk_pd`), at least two scenarios, no flow out of POCI, cohort and estimator on the lifetime backtest, and the
  12, 24 and 36 month decile calibration.
- Contracts U5-S, C07: the B-1 total is the statutory provisions plus the minimum top-up with additional provisions outside it
  (`booked_total`); a statutory status per regime and exactly three regimes; the IFRS 9 regime is a probability-weighted ECL over
  at least two scenarios (weights, staging policy, EIR basis and the variant `z_shift` in the models), overlays are their own
  lines; `internal` nullable with a reason; Annex 9 segment codes with separate labels; `delta_vs_base` follows the scenario.
- Tests U5-S: `tests/contracts_u5/test_u5_review_fixes.py` holds one plant per review finding; the rows fragment now passes
  `scripts/check_contracts.py`; the generated contract types and OpenAPI are regenerated.
