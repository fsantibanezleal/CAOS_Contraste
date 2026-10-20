# Validation: U9-P1, case C12

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is a test under `tests/adversarial/` or named
`test_adversarial_*`.

| requirement | adversarial check | gate |
|---|---|---|
| CT-1201 | One byte of a raw file is changed against its sidecar record; the provenance reader must refuse it, and a missing file must raise the declared absence with its URL. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_changed_raw_file_is_refused_by_its_provenance_record` |
| CT-1202 | A series whose last months lack their 12 month horizon is planted; only the month whose horizon is observed may be a backtest date, and a month end without a curve must carry the earlier day. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_month_whose_horizon_is_not_observed_is_not_a_backtest_date` |
| CT-1203 | An HQM curve below the Treasury curve is planted; the spread must be floored at zero and counted, never negative. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_spread_below_the_treasury_curve_is_floored_and_counted` |
| CT-1204 | The convention label is removed from a named parameter, then replaced by another word; the schema must refuse both. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_parameter_without_the_convention_label_is_refused` |
| CT-1205 | A committed calibration is edited so that its sample ends on the backtest date; the contract's check must name the look-ahead, and a window under three years must raise. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_calibration_window_that_reaches_its_date_is_refused` |
| CT-1206 | A CVA bucket term and the EEPE of a committed document are shifted; the cross-field check must name them. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_cva_term_computed_elsewhere_is_refused` |
| CT-1207 | The MPoR of a CSA is set to 5 business days and a collateralised EE is set above the bound; schema and check must refuse. | `tests/c12/test_adversarial_c12.py::test_adversarial_an_mpor_below_the_floor_or_a_collateral_balance_above_the_bound_is_refused` |
| CT-1208 | The initial margin is relabelled SIMM, its alpha is set to the rounded 2.33 and its MPoR to 10 days in calendar units; each must be refused. | `tests/c12/test_adversarial_c12.py::test_adversarial_initial_margin_labelled_simm_or_with_a_wrong_alpha_is_refused` |
| CT-1209 | The NICA of a margined variant is changed without its replacement cost; the SA-CCR recomputation must name the RC. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_nica_changed_without_its_replacement_cost_is_refused` |
| CT-1210 | The b = 0 point of the sweep is moved by 1e-6, the wrong-way variant is marked reconciled, and a reconciled variant is marked not-applicable; each must be refused. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_wrong_way_sweep_whose_zero_point_differs_from_the_independent_cva_is_refused` |
| CT-1211 | The SA-CCR EAD is raised by one dollar and the GIRR charge by 10 percent; the recomputation must name them. | `tests/c12/test_adversarial_c12.py::test_adversarial_an_ead_or_a_girr_charge_computed_elsewhere_is_refused` |
| CT-1212 | The spread_rose flag is set to false while the peak is above the start; the check must name it. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_stress_window_whose_spread_flag_disagrees_is_refused` |
| CT-1213 | A PIT is edited, a rejection decision is flipped and an iid critical value is changed; W^2, the decision and the schema must each refuse. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_pit_edited_or_a_decision_flipped_is_refused` |
| CT-1214 | The a of the a-plus-one-standard-error case is left at the base value; the check must name it. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_sensitivity_that_does_not_move_a_is_refused` |
| CT-1215 | An ORE agreement flag, the conjunction flag and the ORE version are corrupted; each must be refused. | `tests/c12/test_adversarial_c12.py::test_adversarial_an_ore_flag_that_disagrees_with_its_difference_is_refused` |
| CT-1216 | The engine's bond option is multiplied by 1.01 behind the row; the QuantLib row must turn red. | `tests/c12/test_adversarial_c12.py::test_adversarial_an_engine_closed_form_that_departs_from_quantlib_turns_the_row_red` |
| CT-1217 | A required block is removed, a standard-error array is shortened and a byte of a committed file is changed; schema and checksum must refuse. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_document_with_a_missing_block_or_a_changed_byte_is_refused` |
| CT-1218 | The seed is changed by one; the documents must differ (the determinism gate is not satisfied by constant output). | `tests/c12/test_adversarial_c12.py::test_adversarial_a_different_seed_writes_different_documents` |
| CT-1219 | A committed document is edited in memory; the generated block must change. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_planted_generated_block_is_not_the_committed_one` |
| CT-1220 | A profile with no exposure in the first year is planted; the effective maturity must raise as undefined. | `tests/c12/test_adversarial_c12.py::test_adversarial_a_book_with_no_first_year_exposure_has_no_effective_maturity` |
