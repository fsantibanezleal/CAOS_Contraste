# Adversarial validation: C07

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test that plants it in a copy of the baked documents or inputs and asserts that the clean copy passes and the planted copy fails (tests named `test_adversarial_*` in `tests/c07/test_adversarial_c07.py`).

| requirement | adversarial check | gate |
|---|---|---|
| CT-701 | A calibration target whose source is blank is refused by the target validator, and the validator accepts the clean targets. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_target_without_a_source_is_refused` |
| CT-702 | A generated book whose consumer provision index is 10 per cent off its target is reported out of tolerance by the calibration check. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_book_off_its_target_is_reported` |
| CT-703 | A variant whose portfolio has one account of one segment changed is found by the same-portfolio check. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_variant_with_another_portfolio_is_found` |
| CT-704 | A regime function of the engine replaced by a stub changes the C07 total, so a number computed outside the engine cannot match the baked one. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_regime_number_not_from_the_engine_is_found` |
| CT-705 | A minimum check fed the whole performing book instead of the individual normal portfolio is found by the scope invariant. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_minimum_on_a_group_portfolio_is_found` |
| CT-706 | A document whose IFRS 9 weights sum to 0.9 or whose measure is a single scenario is found by the weighting invariant. | `tests/c07/test_adversarial_c07.py::test_adversarial_an_unlabelled_single_scenario_ifrs9_figure_is_found` |
| CT-707 | An overlay merged into the segment provisions is found by the overlay invariant. | `tests/c07/test_adversarial_c07.py::test_adversarial_an_overlay_inside_the_model_ecl_is_found` |
| CT-708 | A bridge step moved by one peso is found by the closure check. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_bridge_off_by_one_peso_is_found` |
| CT-709 | A document with a field removed, and a document edited after its hash was written, are each found. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_document_failing_its_schema_or_its_hash_is_found` |
| CT-710 | A different seed gives different bytes and the determinism comparison finds it. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_different_seed_gives_different_bytes` |
| CT-711 | A scenario shock without a source or an assumption label is refused by the scenario validator. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_shock_without_a_source_is_refused` |
| CT-712 | A roll-forward with one movement moved by 1.0 fails the engine's reconciliation identities. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_rollforward_with_a_moved_movement_fails` |
| CT-713 | A notice that drops the word synthetic, and a text calling Banco Andino a real bank, are each found. | `tests/c07/test_adversarial_c07.py::test_adversarial_a_text_calling_banco_andino_real_is_found` |
