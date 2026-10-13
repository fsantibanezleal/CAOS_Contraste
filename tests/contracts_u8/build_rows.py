"""Writes the catalog rows fragment of U8-S (docs/contracts/rows/U8.md) and its changelog fragment (changes/U8-S.md).

Run: ``python tests/contracts_u8/build_rows.py``. The rows copy the header of docs/contracts/catalog.md so the fragment
and the table agree on the columns; the integrator merges the rows into the catalog.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs" / "contracts" / "catalog.md"
T = "tests/contracts_u8/test_u8_contracts.py::"
DISC = T + "test_the_fixture_exists_and_is_discovered_by_exactly_one_schema"

C11_EXTRA = (
    "A value the bake may lack is nullable with its reason in the document, never a number (an ES undefined on a day is null and "
    "listed in es_undefined_days; a model that forecasts no ES has a null FZ0 with its reason; a back-test that cannot run is a "
    "not_evaluated row with its reason; the rolling 250-day traffic light of a window shorter than 250 days is not_evaluated; the "
    "realised series of a window with a derived-only component is withheld with its reason). A day missing from a public series is "
    "skipped and counted in data_status.missing_days, never filled; the sign convention is a required field"
)
C13_EXTRA = (
    "A value the bake may lack is nullable with its reason in the document, never a number (a back-test that cannot run is a "
    "not_evaluated row with its reason; a desk with no planted deficiency is the none id with its planted flag false, never an absent "
    "field); the known deficiency and the sign convention are required fields; the synthetic label (truth_status "
    "synthetic-known-truth, generator.notice) is part of every document"
)


def missing(case: str, doc: str, extra: str) -> str:
    return (f"partial: a {case} {doc} is absent; copy-data stops the site build, and at run time getJSON throws ArtifactError; the "
            f"{case} view shows its Pending state (data-state loading) while the data is not there, never an empty chart. {extra}")


def tests(*names: str) -> str:
    return ", ".join(T + n for n in names)


ROWS = [
    ("c11-outputs",
     "U8-S (producer U8-P1 in data-pipeline/pipeline/cases/c11/ with its own tests/c11/ suite, to come; consumer U8-W in "
     "frontend/src/workbench/c11/, to come)",
     "docs/contracts/schemas/c11/variant-window.schema.json", "docs/contracts/fixtures/c11/variant-window-fixture.json",
     tests("test_a_forecast_on_or_before_the_end_of_its_estimation_window_is_caught",
           "test_a_span_that_does_not_end_before_the_window_or_before_2007_is_caught",
           "test_the_forecast_arrays_align_with_the_grid_and_es_is_never_below_var",
           "test_the_exceedances_the_scores_and_the_ftest_inputs_recompute_from_the_realised_series",
           "test_the_rolling_250_day_count_and_the_zone_recompute_at_one_percent_and_are_null_at_2_5",
           "test_the_kupiec_and_christoffersen_rows_recompute_from_the_exceedance_days",
           "test_a_back_test_that_cannot_run_is_a_not_evaluated_row_with_its_reason_never_a_number",
           "test_the_diebold_mariano_rows_recompute_on_the_common_sample",
           "test_a_document_without_its_sign_convention_fails"),
     missing("C11", "window artifact", C11_EXTRA)),
    ("c11-models",
     "U8-S (producer U8-P1 in data-pipeline/pipeline/cases/c11/, to come; consumer U8-W in frontend/src/workbench/c11/, to come)",
     "docs/contracts/schemas/c11/models.schema.json", "docs/contracts/fixtures/c11/models-fixture.json",
     tests("test_the_fixture_exists_and_is_discovered_by_exactly_one_schema", "test_the_window_ids_are_the_six_of_the_sdd",
           "test_the_traffic_light_table_is_the_transcribed_mar32_9_table",
           "test_the_c11_models_ladder_and_the_variant_models_agree"),
     missing("C11", "models artifact", C11_EXTRA)),
    ("c13-outputs",
     "U8-S (producer U8-P2 in data-pipeline/pipeline/cases/c13/ with its own tests/c13/ suite, to come; consumer U8-W in "
     "frontend/src/workbench/c13/, to come)",
     "docs/contracts/schemas/c13/variant-deficiency.schema.json", "docs/contracts/fixtures/c13/variant-deficiency-fixture.json",
     tests("test_a_c13_document_without_its_known_deficiency_fails",
           "test_each_of_the_six_deficiencies_validates_with_its_coupled_fields",
           "test_the_example_replication_recomputes_its_spearman_ks_and_zone", "test_the_zone_counts_close_on_the_replications",
           "test_the_joint_zone_counts_are_consistent_with_the_single_statistic_counts",
           "test_the_desk_back_test_levels_and_limits_are_the_mar32_18_limits",
           "test_the_pla_thresholds_are_the_transcribed_mar32_42_values"),
     missing("C13", "deficiency artifact", C13_EXTRA)),
    ("c13-models",
     "U8-S (producer U8-P2 in data-pipeline/pipeline/cases/c13/, to come; consumer U8-W in frontend/src/workbench/c13/, to come)",
     "docs/contracts/schemas/c13/models.schema.json", "docs/contracts/fixtures/c13/models-fixture.json",
     tests("test_the_fixture_exists_and_is_discovered_by_exactly_one_schema",
           "test_the_c13_models_plan_lists_exactly_the_six_deficiencies"),
     missing("C13", "models artifact", C13_EXTRA)),
]
API_OWNER = ("U8-S (implemented by U8-E in CAOS_RiskValidation riskvalidation.market and riskvalidation.validation.market, with "
             "tests/market/ there, to come; consumed by the bakes U8-P1 and U8-P2 in data-pipeline/pipeline/cases/c11/ and c13/, to come)")
API_MISSING = ("missing: the engine release the product pins lacks a function of this contract; the bake fails with ImportError at its "
               "first call and publishes nothing, the case stays planned in readiness (no partial document). A back-test that cannot "
               "run returns a not_evaluated row with its reason, never a number (a duration test with fewer than 2 exceedances; an ES "
               "back-test where the ES is undefined)")
API_EXAMPLE = "docs/contracts/fixtures/c11/variant-window-fixture.json"
API_PRODUCER = tests("test_every_function_has_a_signature_and_a_golden_value_or_an_invariant",
                     "test_the_engine_contract_carries_the_dossier_goldens_and_marks_what_is_unverified",
                     "test_golden_mar32_9_cumulative_probabilities_recompute",
                     "test_every_validation_function_has_a_light_rule_a_test_id_and_a_golden")
API_CONSUMER = T + "test_the_engine_contract_covers_every_module_of_the_sizing_table"

CHANGES = (
    "- U8-S contracts: the JSON Schemas of the C11 (window) and C13 (deficiency) case documents and models documents under "
    "docs/contracts/schemas/c11 and c13, with plainly labelled fixtures under docs/contracts/fixtures/ that validate by discovery; the "
    "sign convention (the engine stores the return convention, the documents positive loss numbers) is a required field, a C13 "
    "document carries its known planted deficiency, a C11 forecast dated on or before the end of its estimation window is caught by "
    "the leakage check, the hyperparameter span must end before 2007 and before the window it serves, and a back-test that cannot run "
    "is a not_evaluated row with its reason.\n"
    "- U8-S engine contract: docs/contracts/engine/market-api.md (engine-market-api 1.0.0), the signatures, units, invariants, light "
    "rules and golden values of riskvalidation.market (conventions, historical, parametric, garch, evt, caviar, gas_fz, scoring, frtb) "
    "and riskvalidation.validation.market, with the MAR32.9 cumulative probabilities, the chi-square critical values, the EWMA "
    "effective days, the FZ0 reduction and the PLA zone boundaries; the catalog rows are in docs/contracts/rows/U8.md for the "
    "integrator to merge.\n"
)


def main() -> None:
    cat = CATALOG.read_text(encoding="utf-8").splitlines()
    header = next(ln for ln in cat if ln.startswith("| id | version"))
    sep = next(ln for ln in cat if ln.startswith("|---|"))
    lines = [
        "<!-- Catalog rows of unit U8-S (the C11 and C13 case contracts and the engine market API), written as a fragment: the "
        "integrator merges them into the Contracts table of docs/contracts/catalog.md. Status active: the provider is the fixture "
        "under docs/contracts/fixtures/, labelled as a fixture and never published as a result; the real producers are U8-P1 and "
        "U8-P2. -->",
        "", header, sep,
    ]
    for rid, owner, schema, example, producer, miss in ROWS:
        lines.append("| " + " | ".join([rid, "1.0.0", owner, schema, example, producer, DISC, miss, "fixture:" + example, "-", DISC,
                                        "active"]) + " |")
    lines.append("| " + " | ".join(["engine-market-api", "1.0.0", API_OWNER, "docs/contracts/engine/market-api.md", API_EXAMPLE,
                                    API_PRODUCER, API_CONSUMER, API_MISSING, "fixture:" + API_EXAMPLE, "-", API_CONSUMER,
                                    "active"]) + " |")
    (ROOT / "docs" / "contracts" / "rows").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "contracts" / "rows" / "U8.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (ROOT / "changes").mkdir(exist_ok=True)
    (ROOT / "changes" / "U8-S.md").write_text(CHANGES, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
