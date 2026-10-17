# Validation: U10-P2, case C15

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is a test under `tests/adversarial/` or named
`test_adversarial_*`.

| requirement | adversarial check | gate |
|---|---|---|
| CT-1501 | An answer with `Codigo -5` and one with an observation of status `ND` are planted; the reader must refuse the first and list the second as missing, and a UTF-8 decoding of the Latin-1 bytes must differ from the Latin-1 one. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_refused_answer_and_a_missing_observation_are_not_read_as_data` |
| CT-1502 | A later observation with an absurd value is planted after the valuation date; the curve block must not change, and a series missing on the planted date must move the valuation date back. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_later_observation_changes_no_curve` |
| CT-1503 | A raw file is changed by one byte and a document is planted with a `pass=` URL; the provenance loader and the credential scan must refuse them. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_changed_raw_file_and_a_credentialed_url_are_refused` |
| CT-1504 | A curve whose Nelson-Siegel parameter is edited in a committed document is planted; the engine-call check must name it. | `tests/c15/test_adversarial_c15.py::test_adversarial_an_edited_curve_parameter_is_found_by_the_engine_call_check` |
| CT-1505 | An assumption loses its synthetic stamp and an item is planted whose flows miss its amount; the registry check and the semantic check must refuse them. | `tests/c15/test_adversarial_c15.py::test_adversarial_an_unstamped_assumption_and_an_unreconciled_item_are_refused` |
| CT-1506 | A committed document is edited so that a share above its cap has `cap_applied` false; schema and semantic checks must both refuse. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_share_above_its_cap_without_cap_applied_is_refused` |
| CT-1507 | A delta EVE of a committed document is shifted by one unit; the engine-call check must name it. | `tests/c15/test_adversarial_c15.py::test_adversarial_an_eve_computed_elsewhere_is_found_by_the_engine_call_check` |
| CT-1508 | The manifest hash of a document is changed and a variant is removed from the listing; the listing check must fail. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_document_changed_after_hashing_and_a_missing_variant_are_found` |
| CT-1509 | The offset pair of a document is replaced by the sum of the positive parts although the state is `on`; the semantic check must refuse it. | `tests/c15/test_adversarial_c15.py::test_adversarial_an_offset_not_applied_is_refused` |
| CT-1510 | A floor effect is planted for a bucket the floor does not bind; the semantic check must refuse it. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_floor_effect_that_does_not_recompute_is_refused` |
| CT-1511 | The indexation charge of a document is changed to 3 percent; the semantic check must refuse it. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_wrong_indexation_charge_is_refused` |
| CT-1512 | A monthly NII of the dynamic block is edited; the semantic check must refuse it. | `tests/c15/test_adversarial_c15.py::test_adversarial_an_edited_dynamic_nii_is_refused` |
| CT-1513 | The seed is changed; the book must differ, so the determinism test is not vacuous. | `tests/c15/test_adversarial_c15.py::test_adversarial_another_seed_changes_the_book` |
| CT-1514 | A figure of the results block is edited; the page check must fail. | `tests/c15/test_adversarial_c15.py::test_adversarial_an_edited_results_block_is_found` |
| CT-1515 | A Monte Carlo error is set far above its measure, an EVaR is shifted by one unit and a leg is removed; the semantic check and the schema must refuse them. (That the errors are the engine's is the engine-call test, per variant.) | `tests/c15/test_adversarial_c15.py::test_adversarial_an_error_above_its_measure_a_shifted_quantile_and_a_missing_leg_are_refused` |
| CT-1516 | A number of a built document is changed by one unit and a key is removed; the comparison must name both. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_changed_number_or_key_is_found_by_the_bake_comparison` |
| CT-1517 | A distance, a lowest rate, a bucket and a binds flag are edited, a row is removed and the calibration month is moved after the balance sheet month; the semantic check and the schema must refuse each. | `tests/c15/test_adversarial_c15.py::test_adversarial_a_floor_distance_or_the_calibration_month_that_does_not_recompute_is_refused` |
