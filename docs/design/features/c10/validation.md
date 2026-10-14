# Adversarial validation: C10

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test that plants it in a copy of the baked documents or inputs and asserts that the clean copy passes and the planted copy fails (tests named `test_adversarial_*` in `tests/c10/test_adversarial_c10.py`).

| requirement | adversarial check | gate |
|---|---|---|
| CT-1101 | A page whose cell holds a word that is neither a rate nor n.a., a page whose column heading changed and a page with two rows for one quarter are each refused; the same page with its columns shuffled still reads the right series. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_page_the_reader_does_not_know_is_refused` |
| CT-1102 | A quarter filled in by the reader (a planted reader that interpolates the gap) changes the annual rate of the year, and the missing-quarter check finds the document whose gap carries a number. | `tests/c10/test_adversarial_c10.py::test_adversarial_an_interpolated_quarter_is_found` |
| CT-1103 | A fit that is handed the 2007 rate as well as the fit window is found by the window check, and the clean fit is identical when 2007-2012 change. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_fit_that_sees_an_evaluation_year_is_found` |
| CT-1104 | The engine's quantile replaced by a constant changes the C1 measures, so a number computed outside the engine cannot match the baked one; a document edited by hand is found by the recomputation of its cross-field checks. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_number_not_from_the_engine_is_found` |
| CT-1105 | A portfolio block labelled with anything but illustrative, and a provenance without the illustrative input, are each refused by the schema and the label check. | `tests/c10/test_adversarial_c10.py::test_adversarial_an_unlabelled_portfolio_is_found` |
| CT-1106 | A rung with ES below VaR, a rung that did not run but carries a measure, and an importance-sampling VaR a long way from the plain one are each found. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_broken_ladder_is_found` |
| CT-1107 | Euler contributions that do not sum, an anchor row that is not the asymptotic contribution and a delta that is not the paper's are each found by the cross-field checks. | `tests/c10/test_adversarial_c10.py::test_adversarial_euler_rows_that_do_not_add_up_are_found` |
| CT-1108 | A grid document with a cell off the grid, a cell without its known correlation and one whose null correlation is off the grid are each refused. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_grid_without_its_known_correlation_is_found` |
| CT-1109 | A different seed gives different bytes and the comparison finds it. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_different_seed_gives_different_bytes` |
| CT-1110 | A document with a block removed, and a document edited after its hash was written, are each found. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_document_failing_its_schema_or_its_hash_is_found` |
| CT-1111 | A page saved with other bytes than the pinned ones and other numbers over the years used is refused, and a loan-type document with no file hash in its provenance is found. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_page_that_is_not_the_pinned_one_is_refused` |
| CT-1112 | A page block that differs from the documents is found, and a page that calls the portfolio a bank's is found by the claims check. | `tests/c10/test_adversarial_c10.py::test_adversarial_a_page_block_that_differs_from_the_documents_is_found` |
