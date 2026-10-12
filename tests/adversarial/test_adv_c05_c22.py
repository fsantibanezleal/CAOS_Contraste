"""Plants for C05 (CT-201 to CT-208, CT-311) and C22 (CT-301 to CT-307): a defect planted in a copy of the committed
artifacts or of the readers and generators, the existing gate run on the copy, red on the plant, green on the clean copy."""
from __future__ import annotations

from pathlib import Path

from planting import edit, edit_json, refute

C05 = "tests/test_c05.py"
C22 = "tests/test_c22.py"
PAPERS = "data-pipeline/pipeline/io/papers.py"


def _sim_edit(rel: str, fn):
    return lambda r: edit_json(r, rel, fn)


# ------------------------------------------------------------------ C05

def test_ct201_a_table_whose_grades_do_not_add_up_to_its_all_row_is_read_when_the_sum_check_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{C05}::test_table2_reader_checks_the_print",
           lambda r: edit(r, PAPERS, "if sum(rated) != total_n or sum(defaults) != total_d:", "if False:"),
           "DID NOT RAISE")


def test_ct201_a_printed_rate_that_is_not_the_ratio_of_the_counts_is_read_when_the_rate_check_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{C05}::test_table2_reader_checks_the_print",
           lambda r: edit(r, PAPERS, "if d > n or round(100.0 * d / n, 2) != p:", "if d > n:"),
           "DID NOT RAISE")


def test_ct202_a_table_with_other_rows_than_the_paper_prints_is_read_when_the_shape_check_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{C05}::test_pluto_tasche_reader_reads_every_table",
           lambda r: edit(r, PAPERS, "if tuple(rows) != labels:", "if False:"),
           "Table 1 prints rows")


def test_ct203_a_recomputed_cell_that_differs_from_the_print_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["golden"]["cells"][0]["gap"] = 0.5

    refute(base_copy, repo, f"{C05}::test_golden_cells_within_engine_tolerances", _sim_edit("data/derived/C05/ldp-published.json", mutate),
           "test_golden_cells_within_engine_tolerances")


def test_ct204_a_generator_whose_default_share_is_three_times_the_truth_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        kt = d["outputs"]["known_truth"]
        kt["share_of_defaults_by_grade"][0] *= 3

    refute(base_copy, repo, f"{C05}::test_generator_recovers_truth", _sim_edit("data/derived/C05/ldp-sim-1.json", mutate),
           "test_generator_recovers_truth")


def test_ct205_a_coverage_table_missing_a_confidence_level_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["known_truth"]["coverage"]["scaled"]["C"].pop()

    refute(base_copy, repo, f"{C05}::test_coverage_and_power_reported", _sim_edit("data/derived/C05/ldp-sim-0.json", mutate),
           "test_coverage_and_power_reported")


def test_ct206_an_irb_risk_weight_ten_percent_off_its_curve_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["impact"]["rw_A4-slr"]["value"] *= 1.1

    refute(base_copy, repo, f"{C05}::test_impact_states_its_assumptions", _sim_edit("data/derived/C05/sp-2010.json", mutate),
           "test_impact_states_its_assumptions")


def test_ct207_a_result_outside_its_declared_range_is_found_and_named(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["approaches"]["A3-spd"]["constants"]["c_pd"] = 99.0

    refute(base_copy, repo, f"{C05}::test_expected_ranges_hold", _sim_edit("data/derived/C05/sp-2010.json", mutate), "c_pd_sp-2010")


def test_ct208_a_grade_count_vector_of_the_derived_only_table_in_an_artifact_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["counts"] = list(range(1, 18))

    refute(base_copy, repo, f"{C05}::test_derived_only_counts_not_published", _sim_edit("data/derived/C05/sp-2010.json", mutate),
           "counts")


def test_ct311_a_generator_that_draws_from_another_stream_than_the_engines_is_found(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{C05}::test_generator_is_the_engines",
           lambda r: edit(r, "data-pipeline/pipeline/cases/c05_ldp_calibration.py",
                          "draw = gen.draw(np.random.default_rng(seed))", "draw = gen.draw(np.random.default_rng(seed + 1))"),
           "test_generator_is_the_engines")


# ------------------------------------------------------------------ C22

def test_ct301_a_registered_test_without_its_size_measurement_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        sims = d["outputs"]["simulations"]
        sims.remove(next(s for s in sims if s["key"].endswith("@null")))

    refute(base_copy, repo, f"{C22}::test_size_of_every_test_reported", _sim_edit("data/derived/C22/null.json", mutate),
           "test_size_of_every_test_reported")


def test_ct301_a_size_run_with_too_few_repetitions_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["simulations"][0]["n_rep"] = 100

    refute(base_copy, repo, f"{C22}::test_size_of_every_test_reported", _sim_edit("data/derived/C22/null.json", mutate),
           "test_size_of_every_test_reported")


def test_ct302_a_power_curve_missing_one_severity_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        sims = d["outputs"]["simulations"]
        sims.remove(next(s for s in sims if s["severity"] == 3 and s["key"].count("@") == 1))

    refute(base_copy, repo, f"{C22}::test_power_curves_complete", _sim_edit("data/derived/C22/miscalibration.json", mutate),
           "test_power_curves_complete")


def test_ct303_a_simulated_rate_that_disagrees_with_its_exact_value_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        s = next(s for s in d["outputs"]["simulations"] if s["exact"])
        s["agrees"]["p<0.05"] = False

    refute(base_copy, repo, f"{C22}::test_exact_agrees_with_simulation", _sim_edit("data/derived/C22/null.json", mutate),
           "test_exact_agrees_with_simulation")


def test_ct304_a_published_reproduction_with_one_more_disagreeing_cell_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        g = d["outputs"]["golden"][0]
        g["agree"] = 140

    refute(base_copy, repo, f"{C22}::test_published_reproductions_carried", _sim_edit("data/derived/C22/clustering.json", mutate),
           "test_published_reproductions_carried")


def test_ct305_a_finding_that_cites_a_rate_the_artifact_does_not_carry_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["findings"][0]["evidence"] = ["rate:pd.nothing@nowhere"]

    refute(base_copy, repo, f"{C22}::test_findings_cite_rates", _sim_edit("data/derived/C22/miscalibration.json", mutate),
           "test_findings_cite_rates")


def test_ct305_the_contract_accepts_a_finding_citing_no_simulation_when_the_rate_check_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_licence_lineage.py::test_rate_evidence_names_a_simulation",
           lambda r: edit(r, "data-pipeline/pipeline/core/manifest.py",
                          "unknown = [e for e in evidence if e not in test_ids and e not in rate_keys and not e.startswith(EVIDENCE_PREFIXES)]",
                          "unknown = []"),
           "DID NOT RAISE")


def test_ct306_a_variant_with_a_real_outcomes_truth_status_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["provenance"]["truth_status"] = "real-outcomes"

    refute(base_copy, repo, f"{C22}::test_lineage_and_determinism", _sim_edit("data/derived/C22/miscalibration.json", mutate),
           "test_lineage_and_determinism")


def test_ct306_a_seed_that_ignores_its_label_is_found_by_the_determinism_check(base_copy: Path, repo: Path) -> None:
    out = refute(base_copy, repo, f"{C22}::test_lineage_and_determinism",
                 lambda r: edit(r, "data-pipeline/pipeline/cases/c22_validator.py", "def _seed(", "def _seed_unused("),
                 "_seed")
    assert "test_lineage_and_determinism" in out


def test_ct307_a_declared_range_that_differs_from_the_cases_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["expect"]["hl_size_s05"] = [0.0, 1.0]

    refute(base_copy, repo, f"{C22}::test_expected_ranges_hold", _sim_edit("data/derived/manifests/C22.json", mutate),
           "test_expected_ranges_hold")
