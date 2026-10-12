# Requirements: U5-P2, case C07 (the Chile provisions trilogy)

Status: live

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated. The
bake is `data-pipeline/pipeline/cases/c07/`; the documents are `data/derived/C07/` (contracts `c07-models` and
`c07-outputs` 1.0.0); the methods are `riskvalidation` 0.5.0 (engine contract `engine-provisions-api` 1.0.0).

| ID | Requirement | Gate |
|---|---|---|
| CT-701 | THE C07 calibration SHALL give, for every target, its value, unit, source URL, publication and month, taken from a CMF primary publication or labelled UNVERIFIED, and SHALL refuse a target without a source. | `tests/c07/test_calibration.py::test_every_target_names_its_source` |
| CT-702 | THE synthetic Banco Andino SHALL match each calibration target (portfolio mix, provision index and 90-day delinquency ratio by portfolio, the consumer product split) within one per cent relative at the base state, at the test size and at the bake size. | `tests/c07/test_calibration.py::test_generated_aggregates_match_their_targets_within_tolerance` |
| CT-703 | THE six scenario variants SHALL share one portfolio per seed: the account book has one hash and every variant document carries the same portfolio block. | `tests/c07/test_portfolio.py::test_the_portfolio_is_the_same_across_variants` |
| CT-704 | EVERY regime number of a C07 document (the B-1 provisions, the IFRS 9 ECL and the Annex 9 coverage) SHALL be returned by a `riskvalidation` function, never computed in the product, and the pinned engine SHALL reproduce the B-1, Annex 9 and ECL golden values of the engine contract. | `tests/c07/test_engine_calls.py::test_the_pinned_engine_reproduces_the_contract_goldens` |
| CT-705 | THE 0.50 per cent minimum SHALL apply to the individually assessed normal portfolio only, never to a group portfolio, and its top-up SHALL be its own line outside the model segments. | `tests/c07/test_regimes.py::test_the_minimum_applies_to_the_individual_normal_portfolio_only` |
| CT-706 | THE IFRS 9 regime of every variant SHALL be the probability-weighted ECL over at least two weighting scenarios with weights summing to 1, with each single-scenario figure labelled a component and the measure named. | `tests/c07/test_regimes.py::test_the_ifrs9_regime_is_probability_weighted_and_labelled` |
| CT-707 | EVERY IFRS 9 overlay SHALL be its own line of the regime and of the IFRS 9 detail, never inside the model ECL by segment, by stage or by component. | `tests/c07/test_regimes.py::test_overlays_are_separate_lines_outside_the_model_ecl` |
| CT-708 | THE gap bridge from the B-1 comparable total to the IFRS 9 total SHALL be exhaustive and its steps SHALL sum to the gap to within one currency unit, in every variant. | `tests/c07/test_regimes.py::test_the_gap_bridge_closes_to_the_unit` |
| CT-709 | EVERY committed document of `data/derived/C07/` SHALL validate against its `c07-*` schema, say that it is synthetic, and be listed by the manifest with its size and by a checksum file whose digest matches the file. | `tests/c07/test_documents.py::test_every_committed_document_validates_and_is_listed_with_its_hash` |
| CT-710 | THE bake SHALL be deterministic: two bakes with the same seed SHALL write byte-identical documents. | `tests/c07/test_determinism.py::test_two_bakes_with_the_same_seed_write_the_same_bytes` |
| CT-711 | EVERY scenario magnitude SHALL carry a source or the label "assumption of the case", and the six variants SHALL be exactly base, recession, consumer arrears shock, house price fall, UF inflation spike and combined severe. | `tests/c07/test_scenarios.py::test_every_scenario_magnitude_has_a_source_or_an_assumption_label` |
| CT-712 | THE IFRS 9 battery rows (scenario sensitivity, non-linearity, overlay diagnostics, SICR effectiveness, ECL backtest, reconciliation identities) SHALL be `TestResult` rows from `riskvalidation.validation.ifrs9`, and the base-to-variant roll-forward SHALL close its identities. | `tests/c07/test_battery.py::test_the_ifrs9_battery_rows_come_from_the_engine_and_the_rollforward_closes` |
| CT-713 | NO text of C07 SHALL present Banco Andino as a real bank: every document and the case page SHALL carry the synthetic notice, and the CMF figures SHALL appear only as public aggregates with their source. | `tests/c07/test_documents.py::test_no_text_presents_banco_andino_as_a_real_bank` |
