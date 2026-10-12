# Adversarial validation: 

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test under `tests/adversarial/` that plants it in a throwaway copy of the committed files, runs the existing gate on the copy and asserts that the clean copy passes and the planted copy fails. See [`../../README.md`](../../README.md) for the method and its limits.

| requirement | adversarial check | gate |
|---|---|---|
| CT-201 | A table whose grades do not add up to its All row, and a printed rate that is not the ratio of the counts, are each read when the check is removed; the reader test fails. | `tests/adversarial/test_adv_c05_c22.py::test_ct201_a_table_whose_grades_do_not_add_up_to_its_all_row_is_read_when_the_sum_check_is_removed`, `tests/adversarial/test_adv_c05_c22.py::test_ct201_a_printed_rate_that_is_not_the_ratio_of_the_counts_is_read_when_the_rate_check_is_removed` |
| CT-202 | A table with other rows than the paper prints is read when the shape check is removed; the reader test fails. | `tests/adversarial/test_adv_c05_c22.py::test_ct202_a_table_with_other_rows_than_the_paper_prints_is_read_when_the_shape_check_is_removed` |
| CT-203 | A recomputed cell with a gap of 0.5 against its print is found by the tolerance test. | `tests/adversarial/test_adv_c05_c22.py::test_ct203_a_recomputed_cell_that_differs_from_the_print_is_found` |
| CT-204 | A default share three times the true PD is found by the generator-recovery test. | `tests/adversarial/test_adv_c05_c22.py::test_ct204_a_generator_whose_default_share_is_three_times_the_truth_is_found` |
| CT-205 | A coverage table missing a confidence level is found by the coverage test. | `tests/adversarial/test_adv_c05_c22.py::test_ct205_a_coverage_table_missing_a_confidence_level_is_found` |
| CT-206 | An IRB risk weight ten percent off its curve is found by the assumptions test. | `tests/adversarial/test_adv_c05_c22.py::test_ct206_an_irb_risk_weight_ten_percent_off_its_curve_is_found` |
| CT-207 | A constant of 99 outside its declared range is found and named by the expected-ranges test. | `tests/adversarial/test_adv_c05_c22.py::test_ct207_a_result_outside_its_declared_range_is_found_and_named` |
| CT-208 | A 17-count vector of the derived-only table planted in an artifact is found by the no-counts test. | `tests/adversarial/test_adv_c05_c22.py::test_ct208_a_grade_count_vector_of_the_derived_only_table_in_an_artifact_is_found` |
| CT-209 | A risk weight one part in a million off the live port is found by the web parity test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct209_an_irb_risk_weight_one_part_in_a_million_off_the_live_port_is_found` |
| CT-210 | A renamed group of the C05 instrument breaks the six-question order test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct210_a_renamed_group_of_the_c05_instrument_is_found_by_the_order_test` |
| CT-211 | A site whose App route is forced wider than the viewport fails the measured gate on C05's route (local-only: needs node, the installed frontend packages, a built site and a Playwright browser). | `tests/adversarial/test_adv_gate.py::test_ct106_ct211_ct217_ct310_ct413_a_workbench_wider_than_the_viewport_fails_the_measured_gate` |
