# Adversarial validation: C06 (lifetime PD, IFRS 9 staging and ECL on the SBA 7(a) twin)

One row per requirement of [`requirements.md`](requirements.md): what is planted or refuted, and the test that does it. Each gate is a test of `tests/c06/` whose name starts with `test_adversarial`: it plants the defect in the check's input and asserts that the clean input passes and the planted one is found.

| requirement | adversarial check | gate |
|---|---|---|
| CT-501 | A row with a zero term, a cancelled loan and a charge-off with no date are planted among real rows; each is counted under its reason and none is dropped silently. | `tests/c06/test_c06_readers.py::test_adversarial_a_planted_bad_row_is_counted_under_its_reason` |
| CT-502 | A macro row stamped with the 2026 Federal Reserve release is offered for a 2010 reporting date and the contract refuses it. | `tests/c06/test_c06_readers.py::test_adversarial_a_late_vintage_path_is_refused` |
| CT-503 | A variant that says Freddie Mac data is available while the reader raises its absence is found by the data-status check. | `tests/c06/test_c06_documents.py::test_adversarial_a_variant_claiming_freddie_mac_data_is_found` |
| CT-504 | A charge-off dated after the reporting date is planted: the loan is open and not an event at the date, and an event one year later. | `tests/c06/test_c06_cutoff.py::test_adversarial_a_charge_off_after_the_date_is_not_an_event` |
| CT-505 | A ten-year loan observed for 47 months must contribute 15 and two thirds of a quarter of exposure: a count to its 40-quarter term is above the bound and is found. | `tests/c06/test_c06_cutoff.py::test_adversarial_an_open_loan_counted_to_its_term_is_found` |
| CT-506 | Every default of the sample is turned into a payment: plenty of loans, none defaults, and no rung is fitted. | `tests/c06/test_c06_ladder.py::test_adversarial_a_vintage_with_too_few_defaults_is_not_fitted` |
| CT-507 | A rho constant of 0.13 instead of 0.12 moves the golden PIT PDs past 1e-8 and the golden check fails. | `tests/c06/test_c06_engine_calls.py::test_adversarial_a_drifted_golden_value_is_found` |
| CT-508 | A `dpd-backstop` trigger planted among the SICR points of a file with no delinquency data is found. | `tests/c06/test_c06_documents.py::test_adversarial_a_delinquency_trigger_in_a_file_without_delinquency_is_found` |
| CT-509 | An overlay amount added to the Stage 1 model ECL breaks the identity of the stage closing against the stage ECL. | `tests/c06/test_c06_documents.py::test_adversarial_an_overlay_inside_the_model_ecl_is_found` |
| CT-510 | One allowance movement moved by ten times the tolerance basis (1e-6 of the gross carrying amount) makes the engine's `check_identities` return a failing identity. | `tests/c06/test_c06_documents.py::test_adversarial_a_moved_movement_breaks_the_identities` |
| CT-511 | A battery with the ECL backtest removed is found by the battery check. | `tests/c06/test_c06_documents.py::test_adversarial_a_battery_missing_a_test_is_found` |
| CT-512 | A coverage of 7 planted in a stage summary fails the schema and is found by the documents check. | `tests/c06/test_c06_documents.py::test_adversarial_a_document_that_fails_its_schema_is_found` |
| CT-513 | A different seed changes the sampled accounts and so the document, while nothing else moves: the hash comparison can fail. | `tests/c06/test_c06_documents.py::test_adversarial_a_different_seed_changes_the_sampled_accounts` |
| CT-514 | A page that claims Freddie Mac mortgage results, and one that calls the data mortgage loans, are found by the claims check. | `tests/c06/test_c06_case_page.py::test_adversarial_a_page_that_claims_mortgage_or_freddie_mac_results_is_found` |
| CT-515 | An `ecl_scenario` formula copied into a product module is found by the engine-logic scan. | `tests/c06/test_c06_engine_calls.py::test_adversarial_an_engine_formula_copied_into_the_product_is_found` |
| CT-516 | The variants listed in the reverse order are found by the order check. | `tests/c06/test_c06_documents.py::test_adversarial_variants_out_of_order_are_found` |
| CT-517 | A Euro amount planted in a stage summary is found by the currency check. | `tests/c06/test_c06_documents.py::test_adversarial_a_foreign_currency_amount_is_found` |
