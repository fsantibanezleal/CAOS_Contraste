# Requirements: U1, case C01 (retail cards PD, champion vs challenger)

Status: live

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.

| ID | Requirement | Gate |
|---|---|---|
| CT-101 | THE split stage SHALL fit binning, WoE, imputation and scaling on the training slice only. | `tests/test_leakage.py::test_fitted_transforms_train_only` |
| CT-102 | THE calibration map SHALL be fitted on a calibration slice disjoint from the test slice. | `tests/test_leakage.py::test_calibration_slice_disjoint` |
| CT-103 | IF a value outside the training information set is perturbed (a holdout label, or a value dated after the observation date), THEN every fitted parameter SHALL be unchanged. | `tests/test_leakage.py::test_outside_information_perturbation_invariance` |
| CT-104 | THE web SHALL label every threshold as a policy threshold and never as a regulatory one unless the artifact carries a regulatory paragraph reference for it. | `frontend/src/lib/labels.test.ts` |
| CT-105 | WHERE a live recompute is offered, THE live result SHALL equal the committed artifact within 1e-9 for deterministic functions. | `frontend/src/engine/parity.test.ts` |
| CT-108 | THE scorecard's points table SHALL recompute every holdout score exactly. | `tests/test_c01.py::test_points_table_recomputes_scores` |
| CT-109 | THE evaluate stage SHALL report, for every rung on the locked holdout, AUC with its DeLong interval, KS, Brier, calibration by grade and PSI. | `tests/test_c01.py::test_every_rung_reports_the_battery` |
| CT-110 | WHERE a feature is declared monotone, THE gradient-boosted challenger SHALL be monotone in it on its partial-dependence grid. | `tests/test_c01.py::test_gbm_monotone_on_pdp_grid` |
| CT-111 | WHEN the bake runs C01, THE pipeline SHALL fail if a result lies outside the range the case declares, naming the result. | `tests/test_c01.py::test_expected_ranges_hold` |
