# Adversarial validation: C13

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test that plants it in a copy of the baked documents or inputs and asserts that the clean copy passes and the planted copy fails (tests named `test_adversarial_*` in `tests/c13/test_adversarial_c13.py`).

| requirement | adversarial check | gate |
|---|---|---|
| CT-1301 | The no-deficiency generator compared with the closed form of the missing-basis variant is not recovered within the tolerance, while it is within the tolerance of its own. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_generator_with_another_deficiency_is_not_recovered` |
| CT-1302 | A window of 249 days, one with a NaN and one with an infinite value are each refused by the window validator, and the clean 250-day window passes. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_short_or_non_finite_window_is_refused` |
| CT-1303 | A plan in which two replications share a seed, and one in which a variant's seed range overlaps another's, are each found by the independence check. | `tests/c13/test_adversarial_c13.py::test_adversarial_replications_sharing_a_seed_are_found` |
| CT-1304 | A different seed gives different bytes and the comparison finds it. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_different_seed_gives_different_bytes` |
| CT-1305 | The engine's Spearman replaced by a constant changes every zone count of a small bake, so a statistic computed outside the engine cannot match the baked one. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_number_not_from_the_engine_is_found` |
| CT-1306 | A document with a block removed, one edited after its hash was written and one whose zone counts contradict the producer checks are each found. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_document_failing_its_schema_its_producer_checks_or_its_hash_is_found` |
| CT-1307 | A document whose known deficiency is another variant's, and one whose size or power role is swapped, are each found. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_document_without_its_known_deficiency_is_found` |
| CT-1308 | The counts of a planted variant presented as the no-deficiency variant are refused by the size check, and the clean no-deficiency counts pass. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_no_deficiency_variant_that_is_not_green_is_found` |
| CT-1309 | A document whose red count was raised by one without moving the detection counts is found by the closure check, and one whose counts differ from a fresh count is found by the recount. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_catch_rate_that_does_not_recompute_is_found` |
| CT-1310 | A desk row with the 99 percent limit 30 instead of 12, and an aggregate row that is no replication's row, are each found. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_desk_row_with_the_wrong_limit_is_found` |
| CT-1311 | An example whose series is another seed's, and one whose zone was edited, are each found. | `tests/c13/test_adversarial_c13.py::test_adversarial_an_example_that_is_not_the_seeds_output_is_found` |
| CT-1312 | A notice that drops the word synthetic, and a truth status of real outcomes, are each found. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_notice_that_drops_the_word_synthetic_is_found` |
| CT-1313 | A page that calls the generated P&L the book of a real desk is found by the claims check, and a block that differs from the documents is found by the comparison. | `tests/c13/test_adversarial_c13.py::test_adversarial_a_page_block_that_differs_from_the_documents_is_found` |
