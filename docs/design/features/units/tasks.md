# Tasks: M15, the units gates

Order and owners for the 1.01.000 line (after M0, the base adoption, and BL-107). Each task is one implementer brief from the main
session, test first; the reviewer reads T3 and T6 (the specification and the baseline are what the gates rest on).

| Task | What | Depends on | Size (sizing) |
|---|---|---|---|
| T1 | `stages/unit_gate.py` (standard library only): `Pair`, the three classes, the four kinds, `check_document`, path expressions with `[]` and `<m>`; unit tests on synthetic pairs (CT-2402, CT-2403) | none | 1 day |
| T2 | `config/unit_pairs.json` for the 18 mapped cases from the sizing's D1 and D3 tables, and the unmapped rows (C22 simulations, C10 grids, C05 `ldp-published`, C12 wrong-way risk, C14's two dates, C16 reverse stress, C04 agency and thin) mapped or given their reason; the coverage test (CT-2405) | T1 | 1.5 days (done: the mapping decisions are in `design.md`) |
| T3 | The bake: `write_artifact` calls the gate and raises `UnitGateError` (CT-2401); the manifest's `contract.units`; the hooks in `cases/c13/measure.py`, `cases/c20/fits.py` and C11's withheld windows (CT-2406); a re-bake of the 21 manifests, folded into 1.01.000's re-bakes | T1, T2 | 1.5 days |
| T4 | `scripts/check_units.py` loading `unit_gate.py` by path, in `ci.yml`, `deploy-pages.yml`, `scripts/smoke.sh` and `smoke.ps1` (CT-2404, CT-2409); `scripts/check_ci_budget.py` updated | T1, T2 | 0.5 day |
| T5 | `scripts/check_unit_constants.py`, `scripts/unit_constants_modules.json` (the three reviewed lists, from the sizing's heuristic of 99 method and 19 parameter modules), in `ci.yml` and `smoke.*` (CT-2407, CT-2408) | none | 1 day |
| T6 | `scripts/unit_constants_baseline.json`: the 1,161 method and 456 parameter literals classified (a pattern first pass, then a reader other than the classifier); any literal of the defect class rewritten against a quantity, never baselined (CT-2409) | T5 | 3 to 4 days |
| T7 | The adversarial plants of `validation.md`; the contract documentation (`docs/architecture/08_data-contracts.md`, contract 3 and 3b), the case pages' validation sections; the feature's `Status: live` | T1 to T6 | 1 day |

## Convergence verdict

The verdict of this feature is generated, never written by hand: every requirement of [`requirements.md`](requirements.md) has its
row, with its gate and the gate's result in the release run, in [`../release-1-0/verdict.md`](../release-1-0/verdict.md) (filter the
`feature` column by `units`). While the folder says `Status: planned`, its gates read absent and the verdict is NOT CONVERGED, so the
folder enters the product with T1 and is live by the 1.01.000 release run.
