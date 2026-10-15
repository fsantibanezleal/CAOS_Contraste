# Validation: U10-P1, case C14

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is a test under `tests/adversarial/` or named
`test_adversarial_*`.

| requirement | adversarial check | gate |
|---|---|---|
| CT-1401 | A report dated after the valuation date is planted in the file; `up_to` and `report_at` must not return it. | `tests/c14/test_adversarial_c14.py::test_adversarial_a_later_report_is_never_returned_and_a_missing_date_is_refused` |
| CT-1402 | A later Treasury day is planted; `curve_as_of` must keep the earlier day, and a tenor deleted from a day must be listed. | `tests/c14/test_adversarial_c14.py::test_adversarial_a_later_curve_day_is_not_read_and_a_deleted_tenor_is_listed` |
| CT-1403 | One byte of a raw file is changed; the provenance loader must refuse it. | `tests/c14/test_adversarial_c14.py::test_adversarial_a_changed_raw_file_is_refused_by_its_provenance_record` |
| CT-1404 | An item is planted with a flow total that differs from its amount; the semantic check must name it. | `tests/c14/test_adversarial_c14.py::test_adversarial_an_item_whose_flows_miss_its_amount_is_refused` |
| CT-1405 | The synthetic stamp is removed from an assumption of the registry; the registry check must fail. | `tests/c14/test_adversarial_c14.py::test_adversarial_an_assumption_without_its_source_is_refused` |
| CT-1406 | A committed document is edited so that a share above its cap has `cap_applied` false; schema and semantic checks must both refuse. | `tests/c14/test_adversarial_c14.py::test_adversarial_a_share_above_its_cap_without_cap_applied_is_refused` |
| CT-1407 | A delta EVE of a committed document is shifted by one unit; the engine-call check must name it. | `tests/c14/test_adversarial_c14.py::test_adversarial_an_eve_computed_elsewhere_is_found_by_the_engine_call_check` |
| CT-1408 | The manifest hash of a document is changed; the listing check must fail. | `tests/c14/test_adversarial_c14.py::test_adversarial_a_document_changed_after_hashing_is_found` |
| CT-1409 | The behavioural twin of a scenario is removed; the schema must refuse the document. | `tests/c14/test_adversarial_c14.py::test_adversarial_a_scenario_without_its_twin_is_refused` |
| CT-1410 | A Monte Carlo error is replaced by a made-up value; the engine-call check must name it. | `tests/c14/test_adversarial_c14.py::test_adversarial_a_monte_carlo_error_not_from_the_engine_is_found` |
| CT-1411 | The projected change of the out-of-sample row is replaced by the realised one; the semantic check must refuse it. | `tests/c14/test_adversarial_c14.py::test_adversarial_an_out_of_sample_row_that_does_not_use_the_projection_is_refused` |
| CT-1412 | A call report dated after the valuation date is planted in the document; the dating check must refuse it. | `tests/c14/test_adversarial_c14.py::test_adversarial_a_call_report_after_the_valuation_date_is_refused` |
| CT-1413 | The seed is changed; the documents must differ, so the determinism test is not vacuous. | `tests/c14/test_adversarial_c14.py::test_adversarial_another_seed_changes_the_simulated_blocks` |
| CT-1414 | A figure of the results block is edited; the page check must fail. | `tests/c14/test_adversarial_c14.py::test_adversarial_an_edited_results_block_is_found` |
