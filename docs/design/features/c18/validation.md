# Validation: U13-P1, case C18

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is a test named `test_adversarial_*` under `tests/c18/`.

| requirement | adversarial check | gate |
|---|---|---|
| CT-1801 | The last actual quarter is removed from a copy of the Federal Reserve history; the reader must refuse a history that does not end at the jump-off. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_history_that_does_not_end_at_the_jump_off_is_refused` |
| CT-1802 | A probit fit is asked on rates that include net recoveries; the engine must refuse it (no rate is floored or dropped) and accept the identity link. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_probit_fit_on_net_recoveries_is_refused_and_never_floored` |
| CT-1803 | A workbook without the United States row is planted; the reader must name the country code. | `tests/c18/test_adversarial_c18.py::test_adversarial_an_eba_workbook_without_the_us_row_is_refused` |
| CT-1804 | A Delayed transition variable with a unit that differs by one space is planted; the reader must not read it. | `tests/c18/test_adversarial_c18.py::test_adversarial_an_ngfs_variable_with_the_wrong_unit_is_not_read` |
| CT-1805 | A BCCh series whose only observation postdates the as-of date is planted; the reader must refuse it. | `tests/c18/test_adversarial_c18.py::test_adversarial_an_eur_series_with_no_value_before_the_as_of_date_is_refused` |
| CT-1806 | The end of a fit window in the models document is moved to 2020 Q1 and a real estate window to start in 1985; the schema and the semantic check must refuse them. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_fit_window_that_reaches_2020_is_refused_by_the_schema` |
| CT-1807 | A back-cast is run with a fit that ends inside the episode it predicts; the engine test must return an error row. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_backcast_that_overlaps_its_fit_is_an_error_row` |
| CT-1808 | The vintage of a scenario is moved after the observation date; the semantic check must refuse it. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_path_vintage_after_the_as_of_date_is_refused` |
| CT-1809 | The EC of a marginal is inflated by 10 percent and one marginal is declared at 99 percent; the semantic check and the horizon test must find them. | `tests/c18/test_adversarial_c18.py::test_adversarial_an_ec_that_is_not_var_less_el_and_a_marginal_at_99_are_found` |
| CT-1810 | The horizon factor of the market scaling is replaced by 1; the semantic check must find it. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_changed_market_scaling_is_found` |
| CT-1811 | The headline is replaced by the Gaussian copula figure (a diversified number presented as capital); the semantic check must find it. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_headline_that_is_not_the_simple_sum_is_found` |
| CT-1812 | One Euler contribution is moved by 20 percent and a correlation matrix is made not positive semi-definite; the semantic check must find both. | `tests/c18/test_adversarial_c18.py::test_adversarial_an_euler_contribution_moved_and_a_non_psd_matrix_are_found` |
| CT-1813 | Revenue is added to the loss-only CET1 of year 1 and c_P2 is set below the Pillar 2 requirement; the semantic check must find both. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_c_p2_below_the_requirement_and_a_cet1_with_revenue_are_found` |
| CT-1814 | Row 7.2 of the Annex 3 is set to c_P2 instead of the art. 66 quinquies requirement; the cross-document check must find it. | `tests/c18/test_adversarial_c18.py::test_adversarial_annex3_row_7_2_taken_from_c_p2_is_found` |
| CT-1815 | The loss at the reverse solution is shifted by 1 percent and a start is planted closer than the solution; the semantic check must find both. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_reverse_solution_that_misses_the_threshold_is_found` |
| CT-1816 | One byte of a committed document is appended and the synthetic flag of the bank is set false; the checksum and the schema must refuse them. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_document_changed_after_hashing_is_found` |
| CT-1817 | One byte of a Federal Reserve file is changed under its provenance record; the whole case must stop. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_changed_fed_byte_stops_the_whole_case` |
| CT-1818 | The BCCh fetch is run with a fake account; neither the account nor the password may appear in the provenance record. | `tests/c18/test_adversarial_c18.py::test_adversarial_the_bcch_provenance_never_records_the_account` |
| CT-1819 | The seed is changed; the simulated blocks must differ, so the determinism test is not vacuous. | `tests/c18/test_adversarial_c18.py::test_adversarial_another_seed_changes_the_simulated_blocks` |
| CT-1820 | A module that calls `numpy.quantile` is planted; the scan must find the call and its line. | `tests/c18/test_adversarial_c18.py::test_adversarial_a_quantile_restated_in_the_package_is_found` |
| CT-1821 | A figure of the results block is edited; the page check must fail. | `tests/c18/test_adversarial_c18.py::test_adversarial_an_edited_results_block_is_found` |
