"""Plants for C01 (CT-101 to CT-103, CT-108 to CT-111, CT-212 to CT-214, CT-312, CT-313): a defect planted in the case's
code or in a copy of its committed artifacts, the existing gate run on the copy, red on the plant and green on the clean
copy. A plant that changes nothing fails at the edit, so none can pass vacuously."""
from __future__ import annotations

from pathlib import Path

from planting import edit, edit_json, refute

LEAK = "tests/test_leakage.py"
C01 = "tests/test_c01.py"
HOLDOUT = "data/derived/C01/holdout.json"
MODELS = "data/derived/C01/models-taiwan.json"
CAP = "data-pipeline/pipeline/cases/c01_capital.py"


def test_ct101_a_scorecard_binned_on_the_calibration_slice_is_found_by_the_train_only_check(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{LEAK}::test_fitted_transforms_train_only",
           lambda r: edit(r, "data-pipeline/pipeline/cases/c01_ladder.py",
                          "sc = scorecard.fit_scorecard(X_tr, y_tr, features=feats, categorical=categorical, monotone=monotone)",
                          "sc = scorecard.fit_scorecard(pd.concat([X_tr, X_cal]), np.concatenate([y_tr, y_cal]), "
                          "features=feats, categorical=categorical, monotone=monotone)"),
           "test_fitted_transforms_train_only")


def test_ct102_a_calibration_slice_that_overlaps_the_holdout_is_found_by_the_disjointness_check(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{LEAK}::test_calibration_slice_disjoint",
           lambda r: edit(r, "data-pipeline/pipeline/stages/split.py",
                          "train, cal, hold = np.sort(train), np.sort(cal), np.sort(hold)",
                          "train, cal, hold = np.sort(train), np.sort(cal), np.sort(hold)\n    cal = hold[: len(cal)]"),
           "test_calibration_slice_disjoint")


def test_ct103_a_fit_that_depends_on_state_outside_its_training_information_changes_its_record(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{LEAK}::test_outside_information_perturbation_invariance",
           lambda r: edit(r, "data-pipeline/pipeline/cases/c01_ladder.py", "const = benchmark.fit_constant(y_tr)",
                          "fit_ladder.calls = getattr(fit_ladder, 'calls', 0) + 1\n    const = benchmark.fit_constant(y_tr[: -fit_ladder.calls])"),
           "test_outside_information_perturbation_invariance")


def test_ct108_a_scorecard_score_one_point_off_its_points_table_is_found(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            d["outputs"]["sample"]["scorecard_score"][0] += 1
        edit_json(r, HOLDOUT, mutate)

    refute(base_copy, repo, f"{C01}::test_points_table_recomputes_scores", plant, "test_points_table_recomputes_scores")


def test_ct109_a_rung_without_its_brier_score_is_found_by_the_battery_check(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            d["tests"] = [t for t in d["tests"] if not (t["test_id"] == "pd.brier" and t["model_id"] == "P1-scorecard")]
        edit_json(r, HOLDOUT, mutate)

    refute(base_copy, repo, f"{C01}::test_every_rung_reports_the_battery", plant, "pd.brier")


def test_ct110_a_gradient_boosted_challenger_that_is_not_monotone_on_its_grid_is_found(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            m = next(m for m in d["model"] if m["rung"] == "P4")
            feat = next(iter(m["details"]["monotonicity"]["features"].values()))
            feat["pdp"] = list(reversed(feat["pdp"]))
        edit_json(r, MODELS, mutate)

    refute(base_copy, repo, f"{C01}::test_gbm_monotone_on_pdp_grid", plant, "P4")


def test_ct111_a_result_outside_its_declared_range_is_found_and_named(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            t = next(t for t in d["tests"] if t["test_id"] == "disc.auc" and t["model_id"] == "P1-scorecard" and t["segment"] == "portfolio")
            t["metric"] = 0.01
        edit_json(r, HOLDOUT, mutate)

    refute(base_copy, repo, f"{C01}::test_expected_ranges_hold", plant, "auc_P1-scorecard_holdout")


def test_ct212_a_basel_ii_scaling_factor_of_one_is_found_by_the_stated_assumptions_check(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            d["outputs"]["irb"]["by_regime"]["basel2"]["scaling"] = 1.0
        edit_json(r, HOLDOUT, mutate)

    refute(base_copy, repo, f"{C01}::test_irb_capital_states_its_assumptions", plant, "test_irb_capital_states_its_assumptions")


def test_ct213_a_capital_curve_one_part_in_a_thousand_off_the_engine_sum_is_found(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_c01_capital.py::test_capital_curve_sums_the_engine",
           lambda r: edit(r, CAP, "out[regime] = k * np.asarray(ead, dtype=float)", "out[regime] = 1.001 * k * np.asarray(ead, dtype=float)"),
           "test_capital_curve_sums_the_engine")


def test_ct214_a_report_of_no_six_month_full_payers_is_found_by_the_transactor_check(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            d["outputs"]["irb"]["six_month_full_payers"] = 0
        edit_json(r, HOLDOUT, mutate)

    refute(base_copy, repo, f"{C01}::test_transactor_sensitivity_reported", plant, "test_transactor_sensitivity_reported")


def test_ct214_a_transactor_capital_above_the_revolver_capital_is_found(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            cut = d["outputs"]["rungs"]["P1-scorecard"]["cutoff"]
            cut["capital_per_lgd_transactors"]["basel3"][-1] = cut["capital_per_lgd"]["basel3"][-1] * 2
        edit_json(r, HOLDOUT, mutate)

    refute(base_copy, repo, f"{C01}::test_transactor_sensitivity_reported", plant, "assert")


def test_ct312_a_hosmer_lemeshow_with_two_degrees_of_freedom_too_few_is_found(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            for t in d["tests"]:
                if t["test_id"] == "pd.hosmer_lemeshow":
                    t["extras"]["dof"] = t["extras"]["groups"] - 2
        edit_json(r, HOLDOUT, mutate)

    refute(base_copy, repo, f"{C01}::test_hosmer_lemeshow_uses_g_on_the_holdout", plant, "dof")


def test_ct313_an_auc_test_without_the_development_variance_is_found(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            for t in d["tests"]:
                if t["test_id"] == "disc.auc_vs_initial" and t["p_value"] is not None:
                    t["extras"]["auc_initial_variance"] = 0.0
        edit_json(r, HOLDOUT, mutate)

    refute(base_copy, repo, f"{C01}::test_auc_vs_initial_carries_the_development_variance", plant, "auc_initial_variance")
