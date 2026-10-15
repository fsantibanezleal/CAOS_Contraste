# Adversarial validation: C17

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test that plants it in a copy of the generator, the baked documents or the inputs and asserts that the clean copy passes and the planted copy fails (tests named `test_adversarial_*` in `tests/c17/test_adversarial_c17.py`).

| requirement | adversarial check | gate |
|---|---|---|
| CT-1701 | A scale inflated by a factor of 2.5 over the fitted one is found by the calibration check (its fitted quantiles leave the tolerance), while the fitted scale passes. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_scale_off_the_ldce_fit_is_found` |
| CT-1702 | A generator frequency counted per EUR billion without the survival adjustment above EUR 20,000 is found by the expected-count check. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_frequency_without_the_survival_adjustment_is_found` |
| CT-1703 | A true quantile shifted by 5 percent is found by the Fourier and Panjer agreement check, and one shifted by 50 percent by the Monte Carlo band, while the computed one passes both. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_shifted_true_quantile_is_found` |
| CT-1704 | A finite mean written for a tail index of 1.1, and two variants whose true quantiles are swapped, are each refused by the document checks. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_mean_for_a_tail_index_of_one_point_one_is_refused` |
| CT-1705 | A fit handed a loss below the collection threshold is refused by the engine, and a recorded set that keeps such a loss is found by the recorded-set check. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_fit_on_losses_below_the_threshold_is_refused` |
| CT-1706 | A row below the collection threshold and a repeated event identifier are each rejected by contract 1. | `tests/c17/test_adversarial_c17.py::test_adversarial_rows_below_the_threshold_are_rejected_by_contract_one` |
| CT-1707 | Two cells sharing a seed range are found by the disjointness check, and a history that does not follow its seed is found by the reproduction check. | `tests/c17/test_adversarial_c17.py::test_adversarial_overlapping_seed_ranges_are_found` |
| CT-1708 | An engine function replaced by one returning a different Panjer quantile is found by the golden check. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_changed_engine_golden_is_found` |
| CT-1709 | A planted `0.12 * min(bi, 1e9)` or `** 0.8` formula in a copy of the package is found by the formula scan. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_formula_in_the_product_is_found` |
| CT-1710 | A document with its truth removed, a disordered percentile, and a ratio that is not capital over the truth are each refused by the schema or `semantic_findings`. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_document_without_its_truth_or_with_a_disordered_summary_is_refused` |
| CT-1711 | A mean-corrected single loss approximation written for the tail index 1.1 is refused by the schema. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_mean_corrected_sla_for_a_tail_index_above_one_is_refused` |
| CT-1712 | An ILM computed on a 3-year cell is refused by the schema, and the engine returns the BIC only for 3 years. | `tests/c17/test_adversarial_c17.py::test_adversarial_an_ilm_on_three_years_is_refused` |
| CT-1713 | A page line calling the synthetic bank real, and a page that never says synthetic, are each found by the claim check. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_page_that_calls_the_bank_real_is_found` |
| CT-1714 | A bake that draws from the clock instead of its seed gives different bytes, found by the determinism check. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_bake_that_ignores_its_seed_is_found` |
| CT-1715 | A page block edited by hand differs from the generated block and is found by the comparison. | `tests/c17/test_adversarial_c17.py::test_adversarial_a_hand_edited_results_block_is_found` |
