# Adversarial validation: the generated convergence verdict

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test that plants it in a throwaway world (two
repositories, their result files and scripts, all in pytest's temporary folder) and asserts that the verdict says so. See
[`../../README.md`](../../README.md) for the method and its limits.

| requirement | adversarial check | gate |
|---|---|---|
| CV-001 | A JUnit file with no test cases is planted: every row is still listed, and none reads passed. | `tests/test_convergence_verdict.py::test_adversarial_a_junit_with_no_testcases_makes_every_gate_absent` |
| CV-002 | A gate named `test_ab` and one named `test_a` are planted beside passed tests `test_abc` and `test_ab_other`: both read absent, never passed. | `tests/test_convergence_verdict.py::test_adversarial_a_gate_whose_name_is_a_prefix_of_a_passed_test_is_absent_not_passed` |
| CV-003 | A skip with a reason that names no device precondition is planted with a device stated: it is still not allowed and the verdict stays NOT CONVERGED. | `tests/test_convergence_verdict.py::test_adversarial_a_skip_with_a_made_up_device_reason_is_not_allowed_even_when_a_device_is_stated` |
| CV-004 | One test of a converged run is flipped to failed: the verdict turns NOT CONVERGED and the script exits 1. | `tests/test_convergence_verdict.py::test_adversarial_a_failed_test_planted_in_a_converged_run_flips_the_verdict` |
| CV-005 | A script that prints OK and exits 3 is planted as a gate: the row reads failed with the exit code. | `tests/test_convergence_verdict.py::test_adversarial_a_script_that_prints_ok_and_exits_non_zero_is_failed` |
| CV-006 | The same node id is passed in the product's file and absent in the engine's: the engine row reads absent. | `tests/test_convergence_verdict.py::test_adversarial_a_passed_product_case_never_satisfies_an_engine_gate` |
| CV-007 | The same files are run twice, then one result is changed: the bytes are equal the first time and differ the second. | `tests/test_convergence_verdict.py::test_adversarial_a_changed_result_file_changes_the_bytes_and_an_unchanged_one_does_not` |
| CV-008 | An earlier verdict is on disk and a result file is removed: the script exits 2 and the earlier verdict is untouched. | `tests/test_convergence_verdict.py::test_adversarial_a_stale_verdict_is_left_alone_when_a_result_file_is_missing` |
| CV-009 | A feature folder whose requirement is a prose bullet, not a table row, is planted: it is reported as having no rows and its ID is not listed. | `tests/test_convergence_verdict.py::test_adversarial_a_folder_with_only_a_status_line_and_a_prose_id_is_not_a_converged_feature` |
| CV-010 | A copy of `requirement_rows` is appended to the script, then its import of `check_sdd` is removed: the copy check names each. | `tests/test_convergence_verdict.py::test_adversarial_a_copied_parser_in_the_script_is_found` |
| CV-011 | A provider status is planted on one boundary of a catalog that was clean: the skeleton gate reads failed with exit 2 where the clean copy read passed. | `tests/test_convergence_verdict.py::test_adversarial_a_provider_left_on_a_boundary_fails_the_skeleton_gate_of_the_verdict` |
| CV-012 | A failed row of a generated verdict is edited to passed, and the verdict line to CONVERGED: the consistency check names both. | `tests/test_convergence_verdict.py::test_adversarial_a_verdict_edited_by_hand_is_found` |
| CV-013 | A task list without the section is planted among real ones: the check names the folder (the committed folders are the clean copy). | `tests/test_convergence_verdict.py::test_adversarial_a_task_list_without_the_verdict_section_is_found` |
