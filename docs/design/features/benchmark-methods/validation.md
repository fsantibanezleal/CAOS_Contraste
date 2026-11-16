# Validation: BL-113, the methods compared (task T2)

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is a test of
`tests/test_benchmark_methods.py`; the plants are made on the committed document in memory or on the ladder the step reads, so they
run wherever the suite runs.

| requirement | adversarial check | gate |
|---|---|---|
| BM-001 | The step runs twice into two empty folders; the bytes must be equal and equal the committed document. A re-bake of any cited file that moves a number makes the committed document differ until the step is rerun. | `tests/test_benchmark_methods.py::test_adversarial_bm001_a_changed_byte_is_not_the_committed_document` |
| BM-002 | One value of the first row is raised by 1.0, and then one hash is replaced by zeros; each plant must fail naming the cited file and, for the value, the pointer. | `tests/test_benchmark_methods.py::test_adversarial_bm002_a_changed_value_or_a_moved_hash_fails_naming_the_file_and_the_pointer` |
| BM-003 | The tier of M-18 is flipped to the recent published tier in the ladder the step reads; every M-18 row must follow. A ladder id the SDD lacks (M-39) and a measurement row (BS-1) must stop the build. | `tests/test_benchmark_methods.py::test_adversarial_bm003_the_standing_moves_with_the_ladder_and_a_missing_row_stops_the_build` |
| BM-004 | The long-established and recent published rows of Q3 are removed; the check must find a question with a proposed method and none beside it. | `tests/test_benchmark_methods.py::test_adversarial_bm004_a_proposed_method_removed_from_its_question_is_caught` |
| BM-005 | A recent published ladder row M-99 with no row, no absence and no left-out entry is added to the ladder; the check must find it unplaced. | `tests/test_benchmark_methods.py::test_adversarial_bm005_a_new_recent_ladder_row_with_no_place_is_caught` |
| BM-006 | The manuscript run of Q2 (seed 20261104) and the case run (seed 42) are checked for disjoint files; a cell of one run citing the file of the other fails. | `tests/test_benchmark_methods.py::test_adversarial_bm006_a_cell_citing_the_file_of_another_run_is_caught` |
| BM-007 | A tie (two equal values), a null, a distance to a target and an order are fed to the ranking rule; the best method, the tie and the skipped null must be exact, and the standings of the committed document must equal an independent recomputation. The breach test of Q9 must not be best on any false-flag column. | `tests/test_benchmark_methods.py::test_adversarial_bm007_ties_are_stated_and_a_null_is_never_ranked` |
| BM-008 | The multiplier row of Q10 is checked: not ranked, never best in a standing, its multiplier cells filled. Q13 and Q14 must be in `not_built` and in no question. | `tests/test_benchmark_methods.py::test_adversarial_bm008_ranking_the_multiplier_would_change_the_standings` |
| BM-009 | Every null cell of every question is checked for its reason in both languages; a value must carry none. The K-1 cells of Q1 must name the backlog row. | `tests/test_benchmark_methods.py::test_adversarial_bm009_a_null_stripped_of_its_reason_is_refused_and_a_value_with_one_too` |
| BM-010 | The tier-word pattern is tested on a planted sentence ("a method of the beyond tier", "BS-14 refuted") and must match; no text of the document may match it. | `tests/test_benchmark_methods.py::test_adversarial_bm010_a_planted_tier_word_in_a_text_or_a_ladder_id_is_caught` |
| BM-011 | An unknown key is planted at seven levels, a citation is removed or loses its hash, a null loses its reason, a standing is removed or set to a tier word, and a Spanish text is deleted; the schema must refuse each. | `tests/test_benchmark_methods.py::test_adversarial_bm011_an_unknown_key_fails_at_every_level` |
| BM-012 | The index builder's served files must include the document; the sums file must hold the document's hash. | `tests/test_benchmark_methods.py::test_adversarial_bm012_an_index_without_the_document_or_a_sums_file_without_its_hash_is_caught` |
