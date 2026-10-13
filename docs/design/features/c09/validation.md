# Adversarial validation: C09

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test that plants it in a copy of the baked documents or inputs and asserts that the clean copy passes and the planted copy fails (tests named `test_adversarial_*` in `tests/c09/test_adversarial_c09.py`).

| requirement | adversarial check | gate |
|---|---|---|
| CT-901 | A marginal whose source is blank, and one whose source names no Federal Reserve file, are each refused by the marginal validator, and the validator accepts the clean marginals. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_marginal_without_a_source_is_refused` |
| CT-902 | A level 0 generator compared with the known CCF of level 5 is not recovered within the tolerance, while it is within the tolerance of its own. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_generator_with_another_ccf_is_not_recovered` |
| CT-903 | A plan whose test seeds share one development seed, and one whose development seeds repeat, are each found by the independence check. | `tests/c09/test_adversarial_c09.py::test_adversarial_replications_sharing_a_seed_are_found` |
| CT-904 | Levels in reverse order, and a level 0 carrying an acceleration, are each refused by the level validator. | `tests/c09/test_adversarial_c09.py::test_adversarial_levels_out_of_order_are_refused` |
| CT-905 | An engine treatment that clips when the treatment asked for is none is found by the unclipped check, and an untreated estimate above 1 flagged in-range fails its schema. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_clipped_untreated_ccf_is_found` |
| CT-906 | A CCF of 0 written on a line with no undrawn amount is found by the undefined-is-NaN check. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_ccf_of_zero_on_a_fully_drawn_line_is_found` |
| CT-907 | The engine aggregate replaced by a constant changes every C09 estimate to that constant, so an estimate computed outside the engine cannot match the baked one. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_number_not_from_the_engine_is_found` |
| CT-908 | A document with a block removed, and a document edited after its hash was written, are each found. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_document_failing_its_schema_or_its_hash_is_found` |
| CT-909 | A row without its truth, a row whose truth is another level's, and a generator block without its known CCF are each found. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_document_without_its_known_ccf_is_found` |
| CT-910 | A direct-EAD model whose clipped count is null, and a negative predicted EAD flagged in-range, are each refused by the schema. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_direct_ead_model_without_its_clipped_counts_is_found` |
| CT-911 | A different seed gives different bytes and the comparison finds it. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_different_seed_gives_different_bytes` |
| CT-912 | A notice that drops the word synthetic, and a truth status of real outcomes, are each found. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_notice_that_drops_the_word_synthetic_is_found` |
| CT-913 | A page that calls the generated lines the cards of a real bank is found by the claims check. | `tests/c09/test_adversarial_c09.py::test_adversarial_a_page_block_that_differs_from_the_documents_is_found` |
