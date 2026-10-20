# Validation: U11-P, case C16

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is a test named `test_adversarial_*` in
`tests/c16/test_adversarial_c16.py`; the plants are made on the documents the bake builds from the committed samples, so they run
wherever the suite runs.

| requirement | adversarial check | gate |
|---|---|---|
| CT-1601 | A report dated 2023-03-31 is planted in the FDIC file; `up_to` and `report_at` must not return it for a date before it, and a date with no report must be refused. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_later_report_is_never_returned_and_a_missing_date_is_refused` |
| CT-1602 | The title of the large banks' table is changed to the small banks', the adjustment to not seasonally adjusted and the unit to millions; the reader must refuse each. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_page_of_another_table_or_adjustment_is_refused` |
| CT-1603 | A table and a line the page lacks are requested and a cell is replaced by text; the reader must refuse and name them, never fill. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_page_of_another_table_or_adjustment_is_refused` |
| CT-1604 | The hash of a provenance record is changed and then the sidecar is deleted; the loader must refuse both. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_changed_raw_file_or_a_lost_sidecar_is_refused` |
| CT-1605 | The uninsured share over DEPDOM is replaced by the share over DEP, and the insured denominator by DEP; the semantic check and the schema must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_an_uninsured_share_on_the_wrong_denominator_is_refused` |
| CT-1606 | A ratio of the mapping sensitivity is replaced by a made-up value and a band row is removed; the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_mapping_band_ratio_not_recomputed_from_the_central_row_is_refused` |
| CT-1607 | The encumbered part of the Treasury class is set to zero and the fair value of a class is set to its carrying value on the fair-value basis; the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_pledged_class_that_keeps_its_securities_in_the_cbc_is_refused` |
| CT-1608 | A derived item is given a reported amount while its reason stays; the schema and the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_an_item_with_a_number_and_a_reason_is_refused` |
| CT-1609 | An outflow and an NLP value are shifted in a document; the engine-call check and the semantic check must name them, and no line of the product may hold a run-off, compounding or survival formula. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_ladder_number_computed_elsewhere_is_found_by_the_engine_call_check` |
| CT-1610 | The SVB row is passed to the calibration and the fitted rate is replaced by the SVB rate; the engine and the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_calibration_that_takes_a_2023_row_is_refused` |
| CT-1611 | A survival day of 400 on a 125-day horizon and a survival that disagrees with the NLP are planted; the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_survival_day_beyond_the_horizon_or_with_a_positive_nlp_is_refused` |
| CT-1612 | The LCR is flagged reported or regulatory, relabelled and multiplied by 1.5; the schema and the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_an_lcr_presented_as_the_reported_one_is_refused` |
| CT-1613 | An empty HQLA stock is built; its shares must be null and never zero, and the engine must refuse a ratio over no net outflow. | `tests/c16/test_adversarial_c16.py::test_adversarial_an_empty_stock_is_never_a_zero_share` |
| CT-1614 | A solved multiplier is planted whose survival is above the target, and one pushed to the cap; the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_solved_multiplier_that_does_not_reach_the_target_is_refused` |
| CT-1615 | The HTM CBC with the loss is replaced by the CBC without it and the revaluation difference is shifted; the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_an_htm_cbc_without_the_loss_is_refused` |
| CT-1616 | One byte of a written document is changed after its hash was taken; the listing check must name it. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_document_changed_after_hashing_is_found` |
| CT-1617 | A call report dated 2023-03-31 is planted in a document and in its time block; the dating check must refuse both. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_call_report_after_the_valuation_date_is_refused` |
| CT-1618 | The light, the denominator and the forecast flag of the scoring are planted wrong; the semantic check and the schema must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_score_with_the_wrong_denominator_or_light_is_refused` |
| CT-1619 | The survival of a time-block row is removed and the aggregate record is removed without its reason; the semantic check and the schema must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_time_block_after_the_valuation_date_or_without_its_survival_is_refused` |
| CT-1620 | The generator truth is halved and the verification flag is flipped; the semantic check must refuse. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_generator_truth_that_is_not_its_recursion_is_refused` |
| CT-1621 | The seed is changed; the generator block must differ, so the determinism test is not vacuous. | `tests/c16/test_adversarial_c16.py::test_adversarial_another_seed_changes_the_generator_block_so_the_determinism_test_is_not_vacuous` |
| CT-1622 | One word of the results block is edited; the page check must find it. | `tests/c16/test_adversarial_c16.py::test_adversarial_an_edited_results_block_is_found` |
| CT-1623 | One byte is added to a re-baked document; the comparison of the two trees must name it. | `tests/c16/test_adversarial_c16.py::test_adversarial_a_rebake_that_differs_by_one_byte_is_found` |
