# Adversarial validation: C03 (SME PD by vintage through 2008, on the SBA 7(a) loans)

One row per requirement of [`requirements.md`](requirements.md): what is planted or refuted, and the test that does it. Each gate is a test of `tests/c03/` whose name starts with `test_adversarial`: it plants the defect in the check's input and asserts that the clean input passes and the planted one is found.

| requirement | adversarial check | gate |
|---|---|---|
| CT-801 | A cancelled loan, a zero-term loan and a charge-off with no date are planted among real rows; each is counted under its reason and none is dropped silently. | `tests/c03/test_panel.py::test_adversarial_a_planted_bad_row_is_counted_under_its_reason` |
| CT-802 | A charge-off dated at month 40 is observed at month 30: it must be censored, not an event, and a loan open for 47 months must not count as a non-event. | `tests/c03/test_target.py::test_adversarial_a_label_read_beyond_the_observation_date_is_found` |
| CT-803 | A training window one fiscal year too long (its 5-year mark falls inside the cohort) is planted and refused by the window check. | `tests/c03/test_windows.py::test_adversarial_a_window_that_overlaps_its_cohort_is_refused` |
| CT-804 | A window that includes one more fiscal year than the cutoff allows is fitted: its predictions differ from the clean ones, so the bit-identity test can fail. | `tests/c03/test_cutoff.py::test_adversarial_a_leaky_window_changes_the_fitted_model` |
| CT-805 | A 5-year observed value planted in a vintage row whose mark is after the as-of date is found by the mark check. | `tests/c03/test_target.py::test_adversarial_a_five_year_value_before_the_mark_is_found` |
| CT-806 | A window with every event turned into a non-event is offered: no rung is fitted and the refusal names the counts. | `tests/c03/test_ladder.py::test_adversarial_a_window_without_events_is_refused` |
| CT-807 | A `pd_binomial` formula copied into a package module is found by the engine-logic scan. | `tests/c03/test_engine_calls.py::test_adversarial_an_engine_formula_copied_into_the_product_is_found` |
| CT-808 | A document with an out-of-range PD and a document missing from the manifest are planted and found. | `tests/c03/test_documents.py::test_adversarial_a_document_that_fails_its_schema_is_found` |
| CT-809 | A different seed changes the sampled training rows and so the models, while nothing else moves: the hash comparison can fail. | `tests/c03/test_documents.py::test_adversarial_a_different_seed_changes_the_documents` |
| CT-810 | The variants listed in the reverse order are found by the order check. | `tests/c03/test_documents.py::test_adversarial_variants_out_of_order_are_found` |
| CT-811 | A value outside its declared range is offered to the check and the bake fails naming it. | `tests/c03/test_documents.py::test_adversarial_a_value_outside_its_expected_range_is_found` |
| CT-812 | A page that claims a bank-wide SME result, and one that states a training window other than the documents', are found by the claims check. | `tests/c03/test_case_page.py::test_adversarial_a_page_with_a_wrong_window_or_a_bank_wide_claim_is_found` |
