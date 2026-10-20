# Validation: U14-P1, case C02

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is named `test_adversarial_*` under `tests/c02/`.

| requirement | adversarial check | gate |
|---|---|---|
| CT-0201 | A raw zip with a changed byte and a data root with no zip are planted; the reader must stop and name the file. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_changed_raw_byte_or_a_missing_file_stops_c02` |
| CT-0202 | One byte of the raw zip is changed and the data root is empty with a fetch that does not answer; C02 must stop, name the file and write nothing. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_changed_raw_byte_or_a_missing_file_stops_c02` |
| CT-0203 | A finding that cites a row of no document is planted; the manifest builder (contract 2) must refuse it, so no document with a bad record passes. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_finding_citing_a_row_of_no_document_is_refused` |
| CT-0204 | A preprocessor is fitted on the holdout instead of the training slice; its medians differ from the recorded ones, so the record in the models document names the training fit. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_transformation_fitted_on_the_holdout_is_visible_in_the_models_document` |
| CT-0205 | A different file is pooled; the pooled labels and slices must differ, so the split tests are not vacuous. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_changed_pool_changes_the_split_and_a_decreasing_rate_stops_the_term_structure` |
| CT-0206 | The overfit flag is flipped and an AUC interval is moved off its AUC; the semantic check must name each. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_flipped_flag_or_an_inflated_count_is_found_by_the_semantic_checks` |
| CT-0207 | The AUC difference of a challenger is moved outside its interval in a document; the semantic check must name it. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_flipped_flag_or_an_inflated_count_is_found_by_the_semantic_checks` |
| CT-0208 | The exploratory label of the transfer block is changed to `core` or removed; the schema must refuse it. | `tests/c02/test_adversarial_c02.py::test_adversarial_an_out_of_time_claim_or_a_missing_exploratory_label_is_refused` |
| CT-0209 | The exploratory label of the term structure is changed to `final` or removed; the schema must refuse it. | `tests/c02/test_adversarial_c02.py::test_adversarial_an_out_of_time_claim_or_a_missing_exploratory_label_is_refused` |
| CT-0210 | The exploratory label of the Impact block is changed to `measured` or removed; the schema must refuse it. | `tests/c02/test_adversarial_c02.py::test_adversarial_an_out_of_time_claim_or_a_missing_exploratory_label_is_refused` |
| CT-0211 | A byte of a document is changed after the hash was written, and the events are set above the rows; the listing check and the semantic check must fail. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_document_changed_after_hashing_or_an_edited_page_block_is_found` |
| CT-0212 | The same bake runs on one changed input row; the documents must differ, so the determinism test is not vacuous. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_changed_pool_changes_the_split_and_a_decreasing_rate_stops_the_term_structure` |
| CT-0213 | The generated block of the case page is edited; the comparison with the generated block must fail. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_document_changed_after_hashing_or_an_edited_page_block_is_found` |
| CT-0214 | A pin to an older commit that the SDD row does not name, and a pin to a branch name, are planted; the shared pin rule must name each. | `tests/c02/test_adversarial_c02.py::test_adversarial_an_engine_pin_the_sdd_does_not_name_or_a_branch_pin_is_refused` |
| CT-0215 | A finding that cites a row of no document is planted; the manifest builder must refuse it. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_finding_citing_a_row_of_no_document_is_refused` |
| CT-0216 | The out-of-time claim of the split is set true; the schema must refuse it. | `tests/c02/test_adversarial_c02.py::test_adversarial_an_out_of_time_claim_or_a_missing_exploratory_label_is_refused` |
| CT-0217 | A test row is set to `not_evaluated` while it keeps its number; the schema must refuse it. | `tests/c02/test_adversarial_c02.py::test_adversarial_a_not_evaluated_row_with_a_number_is_refused` |
