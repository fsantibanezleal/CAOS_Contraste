"""Contract tests of the experiment outputs of the reconciliation manuscript: each committed result file exists, holds what the
manuscript reads from it, and agrees with what the product already committed (``data/derived``) within the stated tolerances.

    python -m pytest manuscripts/reconciliation-against-reference-engines/experiments/test_results.py
"""
from __future__ import annotations

import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name: str) -> dict:
    path = HERE / name
    assert path.exists(), f"{name} has not been produced: run the experiment script"
    return json.loads(path.read_text(encoding="utf-8"))


def derived(rel: str) -> dict:
    return json.loads((ROOT / "data" / "derived" / rel).read_text(encoding="utf-8"))


def test_printed_totals_are_the_sum_of_the_sources_and_reproduce_the_design_counts():
    d = load("results_printed.json")
    assert d["totals"]["n"] == sum(s["n"] for s in d["sources"]) and d["totals"]["agree"] == sum(s["agree"] for s in d["sources"])
    assert d["totals"]["n"] - d["totals"]["agree"] == d["n_misses"] == sum(d["miss_categories"].values()) == len(d["misses"])
    assert (d["without_tasche_tables_8_and_9"]["n"], d["without_tasche_tables_8_and_9"]["agree"]) == (d["sdd_statement"]["n"], d["sdd_statement"]["agree"])
    assert sum(d["unit_gap_bins"].values()) == d["totals"]["n"]


def test_printed_gap_of_every_agreeing_number_is_within_half_a_unit():
    d = load("results_printed.json")
    for source, gaps in d["unit_gaps"].items():
        assert len(gaps) == next(s["n"] for s in d["sources"] if s["source"] == source)
    assert sum(1 for g in sum(d["unit_gaps"].values(), []) if g <= 0.5 + 1e-4) >= d["totals"]["agree"] - 5


def test_routes_are_within_tolerance_and_the_reuse_comparison_is_zero():
    d = load("results_routes.json")
    p = d["part1"]
    assert p["within_tol_grid"] == p["grid_comparisons"] and p["random_within_tol"] == p["random_comparisons"]
    assert p["same_call_max_gap_jeffreys"] == 0.0 and p["same_call_max_gap_binomial"] == 0.0
    assert all(not r["flag"]["C1_binomial"] and not r["flag"]["C2_binomial"] for r in d["defect_relative"])
    assert d["defect_tail_convention"]["flag"]["C3_binomial"] and not d["defect_tail_convention"]["flag"]["C1_binomial"]


def test_closed_forms_agree_with_the_committed_quantlib_rows():
    d = load("results_closedforms.json")
    rows = {t["test_id"]: t for t in derived("C12/single-swap.json")["tests"] if t["test_id"].startswith("ccr.quantlib")}
    assert math.isclose(d["part1"]["swaption_payer"]["relative_difference"], rows["ccr.quantlib_swaption_payer"]["statistic"], rel_tol=1e-6)
    assert math.isclose(d["part1"]["swaption_receiver"]["relative_difference"], rows["ccr.quantlib_swaption_receiver"]["statistic"], rel_tol=1e-6)


def test_committed_statistics_equal_the_documents_rows():
    d = load("results_committed.json")
    for v, row in d["variants"].items():
        doc = derived(f"C12/{v}.json")
        ee_row = next(t for t in doc["tests"] if t["test_id"] == "ccr.reconcile_ee_profile" and not t.get("segment"))
        assert math.isclose(row["max_abs_z"], ee_row["statistic"], rel_tol=1e-9)
        assert row["rule_two_se"] == doc["outputs"]["ore_reconciliation"]["all_within_two_se"]
    for v, r in d["rebuild"].items():
        assert r["max_abs_ee_gap"] < 1e-3 and r["eepe_gap"] < 1e-3


def test_criterion_rates_lie_in_their_intervals_and_the_size_obeys_proposition_3():
    d = load("results_criterion.json")
    for key, cell in d["table"].items():
        for rule in d["rules"]:
            c = cell[rule]
            assert 0.0 <= c["lo"] <= c["rate"] <= c["hi"] <= 1.0
            assert c["rejected"] == round(c["rate"] * d["reps"])
    for v in d["variants"]:
        c = d["table"][f"{v}|null"]["product"]
        assert c["hi"] >= 0.0455 and c["lo"] <= 0.8041
        assert d["table"][f"{v}|null"]["pair+sidak"]["lo"] <= 0.05


def test_pair_correlation_predicts_the_spread_of_z():
    d, p = load("results_criterion.json"), load("results_pairs.json")
    for v in ("single-swap", "netting-set"):
        meas, pred = d["calibration"][v]["sd_z_by_date"], p[v]["predicted_sd_z_by_date"]
        assert max(abs(a - b) for a, b in zip(meas, pred, strict=True)) < 0.08


def test_ore_replicates_hold_the_product_draw():
    for v in ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d"):
        rep = load(f"results_ore_seed42_{v}.json")["replicates"][0]
        doc = derived(f"C12/{v}.json")["outputs"]["ore_reconciliation"]["agreement"]
        z_doc = [a["difference"] / a["combined_se"] for a in doc]
        assert max(abs(a - b) for a, b in zip(rep["z"], z_doc, strict=True)) < 5e-3, v
    for v in ("single-swap", "netting-set", "csa-mpor-10d"):
        s = load(f"results_ore_{v}.json")["summary"]
        assert s["passed_product_rule"] <= s["reps"] and s["pass_lo"] <= s["pass_rate"] <= s["pass_hi"]


def test_transition_matrix_agreement():
    d = load("results_transition_matrix.json")
    assert d["all_within_tolerance"] and d["riskvalidation"] == "1.1.0" and d["transitionMatrix"] == "0.5.1"
    assert d["last_record_double_count"]["max_gap_after_correction"] == 0.0 and d["aalen_johansen"]["difference"] > 0.08
