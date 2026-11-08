"""BS-15 on C22 (method tiers plan, unit D15): the e-process sequential monitors of the engine (`riskvalidation.validation.sequential`,
1.1.0) against the fixed-window tests read every day, on the engine's generator G17 (VaR hits) and a five-grade PD book.

The hypothesis and the verdict rules are fixed here and in `c22_sequential` before the committed run: H1 size under optional stopping,
H2 detection delay against the Basel traffic light, H3 power cost at the 250-day horizon. The committed document is checked as
committed (no test bakes the case, ADR-0074); the pure functions run on small synthetic inputs."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from pipeline.cases import c22_sequential as sq

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived"


def _det(ever: float, by: float, median: float | None) -> dict:
    return {"ever": ever, "by": by, "median_day": median, "median_day_among_detected": median}


def _hits(size_e=0.022, size_kt=0.655, size_kc=0.336, tl3=250.0, tl4=250.0, e3=239.0, e4=129.0, p3=0.626, p4=0.866,
          by3=0.504, by4=0.785, reps=2000) -> dict:
    """The few numbers of the verdict rules, in the document's shape."""
    sc = [
        {"id": "null", "e_rate": _det(size_e, 0.01, None), "kupiec_trailing": _det(size_kt, 0.0, 700.0),
         "kupiec_cumulative": _det(size_kc, 0.0, None), "traffic_light": _det(0.6, 0.0, 788.0), "kupiec_one_shot_power": 0.096},
        {"id": "rate-x3", "e_rate": _det(0.98, by3, e3), "kupiec_trailing": _det(1.0, 0.0, 250.0),
         "kupiec_cumulative": _det(1.0, 0.5, 111.0), "traffic_light": _det(1.0, 0.0, tl3), "kupiec_one_shot_power": p3},
        {"id": "rate-x4", "e_rate": _det(1.0, by4, e4), "kupiec_trailing": _det(1.0, 0.0, 250.0),
         "kupiec_cumulative": _det(1.0, 0.9, 66.0), "traffic_light": _det(1.0, 0.0, tl4), "kupiec_one_shot_power": p4},
    ]
    return {"reps": reps, "scenarios": sc}


# ---------------------------------------------------------------------------------------------------------------------
# the pure functions

def test_first_true_is_one_based_and_inf_when_never():
    m = np.array([[0, 0, 1, 1], [0, 0, 0, 0], [1, 0, 0, 0]], dtype=bool)
    assert sq.first_true(m).tolist() == [3.0, math.inf, 1.0]
    assert sq.first_true(m, start=1).tolist() == [3.0, math.inf, math.inf]


def test_summary_reports_ever_by_and_the_median_day():
    days = np.array([10.0, 20.0, math.inf, math.inf])
    s = sq.summarise(days, by=15)
    assert s == {"ever": 0.5, "by": 0.25, "median_day": None, "median_day_among_detected": 15.0}
    assert sq.summarise(np.array([3.0, 5.0, 9.0]), by=4)["median_day"] == 5.0


def test_kupiec_rejects_a_clearly_wrong_rate_and_not_the_right_one():
    k = np.array([2.0, 10.0])
    t = np.array([250.0, 250.0])
    assert sq.kupiec_reject(k, t, 0.01).tolist() == [False, True]


def test_the_traffic_light_first_non_green_day_is_the_first_full_window():
    h = np.zeros((2, 400), dtype=bool)
    h[0, 10:20] = True   # ten exceptions in the first 250 days: not green on day 250
    days, k_min = sq.basel_first_non_green(h)
    assert days[0] == 250.0 and math.isinf(days[1])
    assert k_min == 5


def test_a_hit_scenario_is_deterministic_and_the_e_process_keeps_its_size_under_the_null():
    a = sq.run_hits(seed=42, reps=60, horizon=400)
    b = sq.run_hits(seed=42, reps=60, horizon=400)
    assert a == b
    c = sq.run_hits(seed=43, reps=60, horizon=400)
    assert a != c
    null = next(s for s in a["scenarios"] if s["id"] == "null")
    assert null["e_rate"]["ever"] <= 0.05 + 3 * math.sqrt(0.05 * 0.95 / 60)


def test_the_repeated_kupiec_test_exceeds_its_level_where_the_e_process_does_not():
    h = sq.run_hits(seed=7, reps=300, horizon=1000)
    null = next(s for s in h["scenarios"] if s["id"] == "null")
    assert null["kupiec_trailing"]["ever"] > 0.2
    assert null["kupiec_cumulative"]["ever"] > 0.1
    assert null["e_rate"]["ever"] <= 0.08


def test_a_planted_rate_is_detected_earlier_than_the_traffic_light_can_speak():
    h = sq.run_hits(seed=7, reps=120, horizon=1000)
    x4 = next(s for s in h["scenarios"] if s["id"] == "rate-x4")
    assert x4["e_rate"]["median_day"] is not None and x4["e_rate"]["median_day"] < sq.WINDOW
    assert x4["traffic_light"]["median_day"] is not None and x4["traffic_light"]["median_day"] >= sq.WINDOW


def test_the_scenarios_are_the_ladder_of_the_plan():
    h = sq.run_hits(seed=1, reps=8, horizon=300)
    assert [s["id"] for s in h["scenarios"]] == ["null", "rate-x2", "rate-x3", "rate-x4", "cluster-0.1", "cluster-0.2", "cluster-0.4"]
    assert h["alpha"] == 0.01 and h["window"] == 250
    p = sq.run_pd(seed=1, reps=8)
    assert [s["factor"] for s in p["scenarios"]] == [1.0, 1.05, 1.1, 1.25, 1.5, 2.0]
    assert p["pd"] == [0.005, 0.01, 0.02, 0.05, 0.10]


def test_the_pd_book_e_process_holds_its_size_and_the_chi_square_read_every_year_does_not():
    p = sq.run_pd(seed=3, reps=300)
    null = p["scenarios"][0]
    assert null["factor"] == 1.0
    assert null["e_average"]["ever"] <= 0.08 and null["e_product"]["ever"] <= 0.08
    assert null["chi2_every_year"]["ever"] > 0.10
    doubled = p["scenarios"][-1]
    assert doubled["e_average"]["ever"] == 1.0 and doubled["e_average"]["median_day"] == 1.0


# ---------------------------------------------------------------------------------------------------------------------
# the verdict rules (written before the run)

def test_h1_holds_when_the_e_process_keeps_the_bound_and_the_repeated_kupiec_does_not():
    v = sq.verdict(_hits())
    assert v["H1_size"]["holds"] is True
    assert v["H1_size"]["bound"] == pytest.approx(0.05 + 3 * math.sqrt(0.05 * 0.95 / 2000))
    assert sq.verdict(_hits(size_e=0.09))["H1_size"]["holds"] is False
    assert sq.verdict(_hits(size_kt=0.04, size_kc=0.04))["H1_size"]["holds"] is False


def test_h2_needs_a_median_below_250_and_below_the_traffic_light_at_factors_3_and_4():
    assert sq.verdict(_hits())["H2_delay"]["holds"] is True
    assert sq.verdict(_hits(e3=260.0))["H2_delay"]["holds"] is False
    assert sq.verdict(_hits(e4=251.0, tl4=250.0))["H2_delay"]["holds"] is False


def test_h3_is_the_power_cost_at_250_days_under_ten_points_at_both_factors_and_fails_at_12_points():
    v = sq.verdict(_hits())
    assert v["detail"]["rate-x3"]["power_cost"] == pytest.approx(0.626 - 0.504)
    assert v["detail"]["rate-x4"]["power_cost"] == pytest.approx(0.866 - 0.785)
    assert v["H3_power_cost"]["holds"] is False       # 12.2 points at the factor 3
    assert sq.verdict(_hits(by3=0.60))["H3_power_cost"]["holds"] is True


def test_the_hypothesis_holds_only_when_the_three_rules_hold():
    assert sq.verdict(_hits())["holds"] is False
    assert sq.verdict(_hits(by3=0.60))["holds"] is True


# ---------------------------------------------------------------------------------------------------------------------
# the replication: H2 and H3 are judged on the pool of independent seeds, as the final manuscript judges them

def _factor(sid: str, medians: list[float], pooled: float | None, ci: tuple[float | None, float | None], light: float | None,
            cost: float) -> dict:
    return {"id": sid, "factor": float(sid[-1]), "seed_medians": medians, "seed_median_mean": float(np.mean(medians)),
            "seed_median_sd": float(np.std(medians, ddof=1)), "share_of_seeds_below_window": float(np.mean(np.array(medians) < sq.WINDOW)),
            "pooled_n": 40000, "pooled_median": pooled, "pooled_median_ci": list(ci), "pooled_traffic_light_median": light,
            "pooled_share_by_window": 0.5, "pooled_kupiec_power": 0.6, "pooled_power_cost": cost, "pooled_power_cost_se": 0.002}


def _replication(x3: dict, x4: dict, seeds: int = 20) -> dict:
    return {"seeds": seeds, "reps": 2000, "horizon": 1000, "bootstrap": 2000, "factors": [x3, x4]}


GOOD3 = ([240.0] * 14 + [260.0] * 6, 240.0, (236.0, 244.0), 250.0, 0.08)
GOOD4 = ([128.0] * 20, 128.0, (126.0, 129.0), 250.0, 0.085)


def test_the_replication_is_seeds_of_the_committed_size_at_factors_3_and_4_and_is_deterministic():
    a = sq.run_replication(seed=5, seeds=3, reps=40, horizon=400)
    b = sq.run_replication(seed=5, seeds=3, reps=40, horizon=400)
    assert a == b
    assert sq.REPLICATION_SEEDS == 20 and sq.REPLICATION_FACTORS == (3.0, 4.0)
    assert a["seeds"] == 3 and a["reps"] == 40 and a["horizon"] == 400
    assert [f["id"] for f in a["factors"]] == ["rate-x3", "rate-x4"] and [f["factor"] for f in a["factors"]] == [3.0, 4.0]
    for f in a["factors"]:
        assert len(f["seed_medians"]) == 3 and f["pooled_n"] == 120
        assert 0.0 <= f["share_of_seeds_below_window"] <= 1.0
        assert len(f["pooled_median_ci"]) == 2
    assert sq.run_replication(seed=6, seeds=3, reps=40, horizon=400) != a


def test_the_replication_seeds_come_from_the_case_seed_through_derive_seed():
    from pipeline.cases.c22_studies import derive_seed

    keys = sq.replication_keys("rate-x3", 2)
    assert keys == ["sequential:replication:rate-x3:0", "sequential:replication:rate-x3:1"]
    assert len({derive_seed(5, k) for k in keys}) == 2
    a = sq.run_replication(seed=5, seeds=2, reps=30, horizon=300)
    assert a["factors"][0]["seed_medians"][0] != a["factors"][0]["seed_medians"][1]


def test_a_stream_that_never_detects_counts_as_never_in_the_pooled_median():
    days = [np.full(10, math.inf), np.full(10, math.inf)]
    out = sq.pooled_summary(days, [np.full(10, math.inf)] * 2, [np.zeros(10, dtype=bool)] * 2, np.random.default_rng(1), 50)
    assert out["pooled_median"] is None and out["pooled_median_ci"] == [None, None]
    assert out["share_of_seeds_below_window"] == 0.0 and out["pooled_traffic_light_median"] is None


def test_h2_and_h3_follow_the_pooled_rule_not_the_single_run():
    # the single run reads 239 (below 250: the old H2); the pool of 20 seeds is 251 with an interval that holds 250
    single = _hits(e3=239.0, by3=0.60)
    assert sq.verdict(single)["H2_delay"]["holds"] is True
    pooled_no = _replication(_factor("rate-x3", [240.0] * 9 + [260.0] * 11, 251.0, (247.0, 255.0), 250.0, 0.124), _factor("rate-x4", *GOOD4[:1], 128.0, (126.0, 129.0), 250.0, 0.085))
    v = sq.verdict(single, pooled_no)
    assert v["H2_delay"]["holds"] is False
    assert v["detail"]["rate-x3"]["single_run_H2"] is True and v["detail"]["rate-x3"]["H2"] is False
    good = _replication(_factor("rate-x3", *GOOD3), _factor("rate-x4", *GOOD4))
    assert sq.verdict(single, good)["H2_delay"]["holds"] is True


def test_h2_needs_the_whole_interval_below_the_window_and_the_pooled_median_below_the_light():
    x4 = _factor("rate-x4", *GOOD4)
    assert sq.verdict(_hits(), _replication(_factor("rate-x3", *GOOD3), x4))["H2_delay"]["holds"] is True
    edge = _replication(_factor("rate-x3", GOOD3[0], 249.0, (246.0, 250.0), 250.0, 0.08), x4)
    assert sq.verdict(_hits(), edge)["H2_delay"]["holds"] is False       # the upper end must be below 250
    light = _replication(_factor("rate-x3", GOOD3[0], 240.0, (236.0, 244.0), 230.0, 0.08), x4)
    assert sq.verdict(_hits(), light)["H2_delay"]["holds"] is False      # not below the light's pooled median
    never = _replication(_factor("rate-x3", GOOD3[0], None, (None, None), None, 0.08), x4)
    assert sq.verdict(_hits(), never)["H2_delay"]["holds"] is False
    mute = _replication(_factor("rate-x3", GOOD3[0], 240.0, (236.0, 244.0), None, 0.08), x4)
    assert sq.verdict(_hits(), mute)["H2_delay"]["holds"] is True        # a light that never speaks is later than any day


def test_h3_is_the_pooled_power_cost_under_ten_points_at_both_factors():
    assert sq.verdict(_hits(), _replication(_factor("rate-x3", *GOOD3), _factor("rate-x4", *GOOD4)))["H3_power_cost"]["holds"] is True
    over3 = _replication(_factor("rate-x3", GOOD3[0], 240.0, (236.0, 244.0), 250.0, 0.124), _factor("rate-x4", *GOOD4))
    assert sq.verdict(_hits(), over3)["H3_power_cost"]["holds"] is False
    over4 = _replication(_factor("rate-x3", *GOOD3), _factor("rate-x4", GOOD4[0], 128.0, (126.0, 129.0), 250.0, 0.10))
    assert sq.verdict(_hits(), over4)["H3_power_cost"]["holds"] is False


def test_the_texts_name_which_reading_decides_and_carry_the_numbers_of_both():
    rep = _replication(_factor("rate-x3", [240.0] * 9 + [260.0] * 11, 251.0, (247.0, 255.0), 250.0, 0.124),
                       _factor("rate-x4", GOOD4[0], 128.0, (126.0, 129.0), 250.0, 0.085))
    hits = _hits(e3=244.0)
    v = sq.verdict(hits, rep)
    hyp = {h["id"]: h for h in sq.hypotheses(v, hits, rep)}
    en, es = hyp["H2"]["measured"]["en"], hyp["H2"]["measured"]["es"]
    for number in ("251", "247", "255", "244", "45"):                      # the pooled median and interval, the single run, the seeds below 250
        assert number in en and number in es
    assert "decides" in en and "single run" in en and "decide" in es and "corrida" in es
    assert hyp["H2"]["holds"] is False and hyp["H3"]["holds"] is False
    ids = {x["id"] for x in hyp["H2"]["values"]}
    assert {"x3_pooled_median", "x3_pooled_median_ci_high", "x3_share_of_seeds_below_window", "x3_e_median_day"} <= ids
    assert "20" in hyp["H3"]["measured"]["en"]
    text = sq.verdict_block(v)["text"]["en"]
    assert "H2, H3 failed" in text and "pooled" in text


# ---------------------------------------------------------------------------------------------------------------------
# the committed document

def _variant(name: str) -> dict:
    return json.loads((DERIVED / "C22" / f"{name}.json").read_text(encoding="utf-8"))


def test_only_the_other_families_variant_carries_the_block():
    for p in sorted((DERIVED / "C22").glob("*.json")):
        if p.name.startswith("models-"):
            continue
        out = json.loads(p.read_text(encoding="utf-8"))["outputs"]
        assert "sequential" in out, p.name
        assert (out["sequential"] is not None) == (p.stem == "other-families"), p.name


def test_the_committed_block_is_the_run_of_2000_series_per_scenario_on_the_engine_1_1_0():
    s = _variant("other-families")["outputs"]["sequential"]
    assert s["method"]["engine"] == "riskvalidation.validation.sequential" and s["method"]["engine_version"] == "1.1.0"
    assert s["method"]["alpha_level"] == 0.05 and s["method"]["threshold"] == 20.0
    assert s["hits"]["reps"] == 2000 and s["pd_grades"]["reps"] == 2000
    assert [x["id"] for x in s["hits"]["scenarios"]][:4] == ["null", "rate-x2", "rate-x3", "rate-x4"]
    assert len(s["hits"]["scenarios"]) == 7 and len(s["pd_grades"]["scenarios"]) == 6
    assert [h["id"] for h in s["hypotheses"]] == ["H1", "H2", "H3"]
    for h in s["hypotheses"]:
        assert set(h["rule"]) == {"en", "es"} and set(h["measured"]) == {"en", "es"} and isinstance(h["holds"], bool)


def test_the_committed_verdict_is_the_rule_applied_to_the_committed_numbers():
    s = _variant("other-families")["outputs"]["sequential"]
    v = sq.verdict(s["hits"], s["replication"])
    assert [h["holds"] for h in s["hypotheses"]] == [v["H1_size"]["holds"], v["H2_delay"]["holds"], v["H3_power_cost"]["holds"]]
    assert s["verdict"]["holds"] is v["holds"]
    assert s["verdict"]["holds"] == all(h["holds"] for h in s["hypotheses"])


def test_the_committed_e_process_size_is_inside_the_anytime_bound():
    s = _variant("other-families")["outputs"]["sequential"]
    null = next(x for x in s["hits"]["scenarios"] if x["id"] == "null")
    assert null["e_rate"]["ever"] <= 0.05 + 3 * math.sqrt(0.05 * 0.95 / 2000)
    assert null["kupiec_trailing"]["ever"] > 0.05 and null["kupiec_cumulative"]["ever"] > 0.05


def test_the_new_impact_rows_are_named_other_and_carry_both_languages():
    imp = _variant("other-families")["impact"]
    new = [k for k in imp if k.startswith("other_seq_")]
    assert {"other_seq_size_e_process", "other_seq_size_kupiec_trailing", "other_seq_delay_x3", "other_seq_power_cost_x3"} <= set(new)
    for k in new:
        assert set(imp[k]["label"]) == {"en", "es"}


def test_the_text_of_the_block_has_no_dash_or_arrow_and_both_languages():
    s = _variant("other-families")["outputs"]["sequential"]
    texts: list[str] = []

    def walk(x):
        if isinstance(x, dict):
            if set(x) == {"en", "es"}:
                texts.extend(x.values())
            else:
                for v in x.values():
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(s)
    assert texts
    for t in texts:
        assert "\u2014" not in t and "\u2192" not in t and t.strip()


def test_the_committed_document_does_not_say_h2_holds_and_carries_the_replication():
    s = _variant("other-families")["outputs"]["sequential"]
    rep = s["replication"]
    assert rep["seeds"] == 20 and rep["reps"] == 2000 and [f["id"] for f in rep["factors"]] == ["rate-x3", "rate-x4"]
    for f in rep["factors"]:
        assert len(f["seed_medians"]) == 20 and f["pooled_n"] == 40000
        assert f["share_of_seeds_below_window"] == pytest.approx(np.mean(np.array(f["seed_medians"]) < sq.WINDOW))
    h = {x["id"]: x for x in s["hypotheses"]}
    x3 = next(f for f in rep["factors"] if f["id"] == "rate-x3")
    assert h["H2"]["holds"] is False and x3["pooled_median_ci"][1] >= sq.WINDOW
    assert s["verdict"]["held"] == ["H1"] and s["verdict"]["failed"] == ["H2", "H3"]
    for lang in ("en", "es"):
        assert "20" in h["H2"]["measured"][lang] and "20" in h["H3"]["measured"][lang]
    assert "holds: true" not in str(s["hypotheses"][1])
