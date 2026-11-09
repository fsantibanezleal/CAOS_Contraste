"""Contract tests of the experiment outputs of the e-process manuscript: each committed result file exists, holds what the
manuscript reads from it, and agrees with what the product already committed (``data/derived/C22/other-families.json``,
the engine evaluation of the same hypotheses) within the Monte Carlo error.

    python -m pytest manuscripts/e-process-sequential-monitors/experiments/test_results.py
"""
from __future__ import annotations

import json
import math
import pathlib

import pytest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name: str) -> dict:
    path = HERE / name
    assert path.exists(), f"{name} has not been produced: run the experiment script"
    return json.loads(path.read_text(encoding="utf-8"))


def committed_c22() -> dict:
    d = json.loads((ROOT / "data" / "derived" / "C22" / "other-families.json").read_text(encoding="utf-8"))
    return d["outputs"]["sequential"]


def scenario(block: dict, sid: str) -> dict:
    return next(s for s in block["scenarios"] if s["id"] == sid)


@pytest.fixture(scope="module")
def hits() -> dict:
    return load("results_hits.json")


def test_hits_records_engine_release_seed_and_repetitions(hits):
    meta = hits["meta"]
    assert meta["engine_version"] == "1.1.0"
    assert meta["reps"] >= 2000 and meta["horizon"] == 1000 and meta["alpha"] == 0.01
    assert isinstance(meta["seed"], int)
    assert set(meta["critical_values"]) == {"kupiec_cumulative", "cusum_m3"}


def test_every_scenario_has_every_method_with_an_interval(hits):
    need = {"e_rate", "e_rate_upper", "e_cluster", "e_battery", "e_sprt3", "e_wwz", "e_beta", "kupiec_trailing",
            "kupiec_cumulative", "kupiec_sidak", "kupiec_calibrated", "cusum_calibrated", "traffic_light",
            "independence_trailing"}
    for sid, sc in hits["scenarios"].items():
        assert need <= set(sc["methods"]), sid
        for name, m in sc["methods"].items():
            lo, hi = m["ever_ci"]
            assert lo <= m["ever"] <= hi, (sid, name)


def test_null_size_of_the_engine_monitors_is_within_the_anytime_bound(hits):
    null = hits["scenarios"]["null"]["methods"]
    n = null["e_rate"]["n"]
    bound = 0.05 + 3.0 * math.sqrt(0.05 * 0.95 / n)
    for name in ("e_rate", "e_rate_upper", "e_cluster", "e_battery", "e_sprt3", "e_wwz", "e_beta"):
        assert null[name]["ever"] <= bound, name


def test_repeated_fixed_window_tests_exceed_the_bound_on_the_null(hits):
    null = hits["scenarios"]["null"]["methods"]
    n = null["e_rate"]["n"]
    bound = 0.05 + 3.0 * math.sqrt(0.05 * 0.95 / n)
    assert null["kupiec_trailing"]["ever"] > bound
    assert null["kupiec_cumulative"]["ever"] > bound
    assert null["traffic_light"]["ever"] > bound


def test_replication_agrees_with_the_committed_c22_document(hits):
    """Another seed, the same generators and engine: the rates agree within three combined standard errors."""
    ref = committed_c22()
    n_ref = ref["hits"]["reps"]
    for sid_new, sid_ref in (("null", "null"), ("rate-x3", "rate-x3"), ("rate-x4", "rate-x4"), ("cluster-0.4", "cluster-0.4")):
        mine = hits["scenarios"][sid_new]["methods"]
        theirs = scenario(ref["hits"], sid_ref)
        for name_new, name_ref in (("e_rate", "e_rate"), ("kupiec_trailing", "kupiec_trailing"),
                                   ("traffic_light", "traffic_light")):
            p1, p2 = mine[name_new]["ever"], theirs[name_ref]["ever"]
            pooled = (p1 + p2) / 2
            se = math.sqrt(max(pooled * (1 - pooled), 1e-9) * (1 / mine[name_new]["n"] + 1 / n_ref))
            assert abs(p1 - p2) <= 3.3 * se + 1e-9, (sid_new, name_new, p1, p2)


def test_delay_at_severity_four_is_below_the_window_and_at_three_is_reported_as_measured(hits):
    """H2 holds at four times alpha; at three times the pooled median of the seeds study is not below 250 (the outcome
    the manuscript reports as not met), so the test pins that measured fact instead of the stated expectation."""
    assert hits["scenarios"]["rate-x4"]["methods"]["e_rate"]["median_day"] < 250
    x3 = load("results_x3_seeds.json")["factors"]["x3"]
    assert x3["pooled_median_ci"][1] >= 250
    assert load("results_x3_seeds.json")["factors"]["x3_upper"]["pooled_median_ci"][1] < 250


def test_size_over_the_horizon_has_every_curve():
    sh = load("results_size_horizon.json")
    assert {"e_rate", "kupiec_cumulative", "kupiec_trailing", "traffic_light", "e_wwz", "e_beta"} <= set(sh["curves"])
    assert sh["meta"]["horizon"] >= 5000


def test_ablation_has_the_components():
    ab = load("results_ablation.json")
    assert {"hits_grid", "hits_battery", "pd_combine"} <= set(ab)


def test_pd_correlation_experiment_reports_size_by_correlation():
    pc = load("results_pd_correlation.json")
    assert [r["rho"] for r in pc["rows"]][0] == 0.0


def test_real_data_covers_the_six_windows():
    c11 = load("results_c11.json")
    assert set(c11["windows"]) == {"calm-2004-06", "equity-2007-09", "fx-2008", "equity-2020", "rates-2022", "mixed-2023"}


def test_theory_numbers_exist():
    th = load("results_theory.json")
    assert {"kl", "size_matched_power", "null_expectation", "product_counterexample"} <= set(th)
