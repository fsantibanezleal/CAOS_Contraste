# Adversarial validation: C08 (LGD and downturn LGD on the SBA 7(a) charge-off twin)

One row per requirement of [`requirements.md`](requirements.md): what is planted or refuted, and the test that does it. Each gate is a test of `tests/c08/` whose name starts with `test_adversarial`: it plants the defect in the check's input and asserts that the clean input passes and the planted one is found.

| requirement | adversarial check | gate |
|---|---|---|
| CT-901 | A row with a zero term, a charge-off with no date and a charge-off before its approval are planted among real rows; each is counted under its reason and none is dropped silently. | `tests/c08/test_c08_panel.py::test_adversarial_a_planted_bad_row_is_counted_under_its_reason` |
| CT-902 | A proxy computed over `SBAGuaranteedApproval` instead of `GrossApproval` differs from the document's value and is found by the proxy check. | `tests/c08/test_c08_panel.py::test_adversarial_a_proxy_with_another_denominator_is_found` |
| CT-903 | A realised LGD of 1.4 clipped to 1.0 in a cohort is found by the clipping check (the count above one and the maximum no longer match the raw values). | `tests/c08/test_c08_panel.py::test_adversarial_a_clipped_lgd_is_found` |
| CT-904 | A default charged off after the cutoff planted into the training set is found by the look-ahead check. | `tests/c08/test_c08_cutoff.py::test_adversarial_a_default_after_the_cutoff_in_training_is_found` |
| CT-905 | An open workout kept in the training set (a charge-off inside the twelve-month window) is found by the training check. | `tests/c08/test_c08_cutoff.py::test_adversarial_an_open_workout_kept_in_training_is_found` |
| CT-906 | The variants listed in the reverse order, and a variant that trains on its own cohort, are found by the order and out-of-time checks. | `tests/c08/test_c08_documents.py::test_adversarial_variants_out_of_order_are_found` |
| CT-907 | A prediction of 1.2 planted in a rung's predictions is found by the range check. | `tests/c08/test_c08_ladder.py::test_adversarial_a_prediction_outside_zero_one_is_found` |
| CT-908 | A drifted golden value (a floor of 0.3 instead of 0.25) is found by the golden check. | `tests/c08/test_c08_engine_calls.py::test_adversarial_a_drifted_golden_value_is_found` |
| CT-909 | A copy of the downturn add-on formula planted in a product module is found by the engine-logic scan. | `tests/c08/test_c08_engine_calls.py::test_adversarial_an_engine_formula_copied_into_the_product_is_found` |
| CT-910 | A not evaluated test row carrying a statistic is found by the test-row check. | `tests/c08/test_c08_documents.py::test_adversarial_a_test_row_with_a_number_on_a_not_evaluated_light_is_found` |
| CT-911 | A downturn row for a cohort outside the downturn period is found by the add-on check. | `tests/c08/test_c08_downturn_floors.py::test_adversarial_an_add_on_over_a_non_downturn_cohort_is_found` |
| CT-912 | A floor row whose mean after the floor is below the mean before is found by the bite check. | `tests/c08/test_c08_downturn_floors.py::test_adversarial_a_negative_uplift_is_found` |
| CT-913 | A document that says Freddie Mac data is available while the reader raises its absence is found by the data-status check. | `tests/c08/test_c08_documents.py::test_adversarial_a_variant_claiming_freddie_mac_data_is_found` |
| CT-914 | An LGD of 1.3 planted without its above-one flag fails the schema and is found by the documents check. | `tests/c08/test_c08_documents.py::test_adversarial_a_document_that_fails_its_schema_is_found` |
| CT-915 | A different seed changes the gradient-boosted predictions while nothing else moves: the hash comparison can fail. | `tests/c08/test_c08_documents.py::test_adversarial_a_different_seed_changes_the_boosted_predictions` |
| CT-916 | A page that claims Freddie Mac mortgage results, and one that never names the SBA data, are found by the claims check. | `tests/c08/test_c08_case_page.py::test_adversarial_a_page_that_claims_a_mortgage_or_freddie_result_is_found` |
| CT-917 | A Euro amount planted in an exposure block is found by the currency check. | `tests/c08/test_c08_documents.py::test_adversarial_a_foreign_currency_amount_is_found` |
