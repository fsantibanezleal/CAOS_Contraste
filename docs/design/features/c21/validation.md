# Validation: U14-P3, case C21

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is a test under `tests/adversarial/` or named
`test_adversarial_*`.

| requirement | adversarial check | gate |
|---|---|---|
| CT-2101 | A file with a required column deleted, a file with another state and a file with a row of another year are planted; the reader must refuse each. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_bad_column_state_or_year_is_refused` |
| CT-2102 | A row of code 4 (withdrawn) and a row of code 3 (denied) are planted; the withdrawn row must not enter the rates and the denied one must be a denial. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_withdrawn_row_never_enters_the_rates` |
| CT-2103 | The decision is removed from the records; contract 1 with `outcome: none` must reject every one. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_decision_sample_without_the_decision_is_rejected_by_contract_1` |
| CT-2104 | One byte of a raw file is changed; the provenance loader must refuse it. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_changed_raw_file_is_refused_by_its_provenance_record` |
| CT-2105 | A race category outside the dictionary is planted; the reader must refuse it and must not fold it into a group. | `tests/c21/test_adversarial_c21.py::test_adversarial_an_unknown_category_is_refused_and_never_folded_into_a_group` |
| CT-2106 | A document flag is decided on a float at exactly four-fifths (60 of 100 against 75 of 100); the semantic check must name the flag. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_flag_decided_on_a_float_is_found_by_the_exact_check` |
| CT-2107 | The z statistic of one contrast is shifted; the semantic check must name it. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_z_statistic_from_elsewhere_is_found` |
| CT-2108 | The missing control is removed from a controlled estimate of a document; the schema must refuse it. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_controlled_estimate_without_the_missing_credit_score_is_refused` |
| CT-2109 | The confirmation coefficient is flipped without `same_sign`; the semantic check must name it. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_flipped_confirmation_sign_is_found` |
| CT-2110 | A document claims the counterfactual test ran and another claims the standard normalization; the schema must refuse both. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_counterfactual_claim_or_standard_normalization_is_refused` |
| CT-2111 | A row with the id `fair.equalized_odds` is planted in a document; the schema must refuse it. | `tests/c21/test_adversarial_c21.py::test_adversarial_an_outcome_conditioned_test_row_is_refused` |
| CT-2112 | The label is removed from a document and `is_a_finding_of_violation` is set true in another; the schema must refuse both. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_document_without_the_label_or_with_a_violation_finding_is_refused` |
| CT-2113 | The download of 2020 is made to fail; no document of the pairs 2019-20 and 2020-21 may be written and the others must be. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_failed_year_writes_nothing_for_its_pairs` |
| CT-2114 | The manifest hash of a document is changed after the bake; the listing check must fail. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_document_changed_after_hashing_is_found` |
| CT-2115 | One input row is changed; the documents must differ, so the determinism test is not vacuous. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_changed_input_row_changes_the_documents` |
| CT-2116 | The generated block of the case page is edited; the check must fail. | `tests/c21/test_adversarial_c21.py::test_adversarial_an_edited_results_block_is_found` |
| CT-2117 | A data licence sentence is written into a document; the schema must refuse it. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_data_licence_sentence_is_refused` |
| CT-2118 | A finding that cites a test row of no document, and a finding with no evidence, are planted; the manifest check must refuse each. | `tests/c21/test_adversarial_c21.py::test_adversarial_a_finding_citing_a_row_of_no_document_or_with_no_evidence_is_refused` |
| CT-2119 | A pin to an older commit that the SDD row does not name, and a pin to a branch name, are planted; the shared pin rule must name each. | `tests/c21/test_adversarial_c21.py::test_adversarial_an_engine_pin_the_sdd_does_not_name_or_a_branch_pin_is_refused` |
