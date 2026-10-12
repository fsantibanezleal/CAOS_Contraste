# Adversarial validation: 

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test under `tests/adversarial/` that plants it in a throwaway copy of the committed files, runs the existing gate on the copy and asserts that the clean copy passes and the planted copy fails. See [`../../README.md`](../../README.md) for the method and its limits.

| requirement | adversarial check | gate |
|---|---|---|
| CT-101 | The scorecard binned on the calibration slice as well as the training slice is found by the train-only perturbation check. | `tests/adversarial/test_adv_c01.py::test_ct101_a_scorecard_binned_on_the_calibration_slice_is_found_by_the_train_only_check` |
| CT-102 | A calibration slice overlapping the holdout is found by the disjointness check. | `tests/adversarial/test_adv_c01.py::test_ct102_a_calibration_slice_that_overlaps_the_holdout_is_found_by_the_disjointness_check` |
| CT-103 | A fit that depends on state outside its training information (a random draw standing in for it) changes its record under the holdout perturbation and is found. | `tests/adversarial/test_adv_c01.py::test_ct103_a_fit_that_depends_on_state_outside_its_training_information_changes_its_record` |
| CT-104 | A threshold label reading Regulatory threshold with no paragraph reference in the artifact is found by the label test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct104_a_threshold_labelled_regulatory_without_a_paragraph_reference_is_found` |
| CT-105 | A committed scorecard score one point off the live scorer is found by the web parity test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct105_a_committed_score_one_point_off_the_live_scorecard_is_found` |
| CT-108 | A scorecard score one point off its points table is found by the recomputation test. | `tests/adversarial/test_adv_c01.py::test_ct108_a_scorecard_score_one_point_off_its_points_table_is_found` |
| CT-109 | A rung without its Brier score is found by the battery-completeness test. | `tests/adversarial/test_adv_c01.py::test_ct109_a_rung_without_its_brier_score_is_found_by_the_battery_check` |
| CT-110 | A reversed partial-dependence curve of the gradient-boosted rung is found by the monotonicity test. | `tests/adversarial/test_adv_c01.py::test_ct110_a_gradient_boosted_challenger_that_is_not_monotone_on_its_grid_is_found` |
| CT-111 | An AUC of 0.01 outside its declared range is found and named by the expected-ranges test. | `tests/adversarial/test_adv_c01.py::test_ct111_a_result_outside_its_declared_range_is_found_and_named` |
