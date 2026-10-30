"""BS-13 (beyond tier): the scale-and-level complement to the PLA test on C13. The statistics, the thresholds and the decisions are
the engine's (``riskvalidation.market.pla_complement``, engine 1.1.0); the product calibrates them on a null it simulates, applies
them to the six variants and to a lag ladder, and states the verdict of the plan's hypothesis whatever it is."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from pipeline.cases.c13 import complement, generator, params
from riskvalidation.market import pla_complement as pc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import contract_schemas as cs  # noqa: E402

N = 50   # the replications per variant of the small bake (conftest SCALE)
NB = 100  # the null block: the smallest that resolves a 0.1 percent size (ten blocks, 1,000 desk-years)


def block(built, did: str) -> dict:
    return built["variants"][did]["outputs"]["pla_complement"]


def test_the_constants_are_the_plans_and_are_fixed_before_the_run() -> None:
    assert complement.WINDOW == 20 and complement.SIZE == 0.01 and complement.CORRECTION == "bonferroni"
    assert complement.NULL_CASE_SEEDS == tuple(range(5013, 5023))
    assert complement.LAGS == (5, 10, 20, 40)
    assert (complement.HOLDS_POWER, complement.REFUTED_POWER) == (0.30, 0.10)
    assert not set(complement.NULL_CASE_SEEDS) & {params.CASE_SEED}          # no seed of the null meets a committed one


@pytest.mark.parametrize("power,size,verdict", [(0.999, 0.009, "holds"), (0.30, 0.01, "holds"), (0.2999, 0.0, "not-established"),
                                                 (0.5, 0.02, "not-established"), (0.0999, 0.0, "refuted"), (0.0, 0.0, "refuted")])
def test_the_verdict_rule(power: float, size: float, verdict: str) -> None:
    assert complement.verdict(power, size) == verdict


def test_every_variant_carries_the_complement_block_with_its_engine_provenance(built) -> None:
    for did in params.IDS:
        b = block(built, did)
        assert b["tier"] == "beyond" and b["plan_id"] == "BS-13" and b["engine_function"] == "riskvalidation.market.pla_complement"
        assert b["window_days"] == 20 and b["size"] == 0.01 and b["correction"] == "bonferroni" and b["n_replications"] == N
        assert b["role"] == ("size" if did == "none" else "power")
        cal = b["calibration"]
        assert cal["null_case_seeds"] == list(range(5013, 5023)) and cal["n_null"] == 10 * NB and cal["n_per_block"] == NB
        for key in ("thresholds_per_statistic", "thresholds_family"):
            assert set(cal[key]) == {"wald", "spearman_abs", "spearman_roll"}
        assert cal["thresholds_family"]["wald"] >= cal["thresholds_per_statistic"]["wald"]            # a stricter size, a wider band
        assert cal["thresholds_family"]["spearman_roll"] <= cal["thresholds_per_statistic"]["spearman_roll"]


def test_the_thresholds_are_the_engines_on_a_null_simulated_here(built) -> None:
    null = []
    for cs_ in complement.NULL_CASE_SEEDS:
        for i in range(NB):
            rep = generator.replicate("none", i, cs_)
            null.append(pc.pla_complement_statistics(rep.hpl, rep.rtpl, 20))
    for tag, corr in (("thresholds_per_statistic", "none"), ("thresholds_family", "bonferroni")):
        th = pc.pla_complement_calibrate(null, 0.01, corr)
        got = block(built, "none")["calibration"][tag]
        assert got == {"wald": th.wald, "spearman_abs": th.spearman_abs, "spearman_roll": th.spearman_roll}


def test_the_flag_counts_are_the_engines_decisions_on_the_replications(built) -> None:
    b = block(built, "stale-volatility")
    th = pc.PLAComplementThresholds(**{**_thresholds(b, "thresholds_per_statistic", "none")})
    flags = {"wald": 0, "spearman_abs": 0, "spearman_roll": 0, "any": 0}
    for i in range(N):
        rep = generator.replicate("stale-volatility", i)
        d = pc.pla_complement_decide(pc.pla_complement_statistics(rep.hpl, rep.rtpl, 20), th)
        flags["wald"] += d.flag_wald
        flags["spearman_abs"] += d.flag_spearman_abs
        flags["spearman_roll"] += d.flag_spearman_roll
        flags["any"] += d.flagged
    for k, v in flags.items():
        r = b["flags"]["per_statistic"][k]
        assert (r["k"], r["n"]) == (v, N) and r["rate"] == v / N and r["ci_low"] <= r["rate"] <= r["ci_high"], k


def _thresholds(b: dict, tag: str, corr: str) -> dict:
    cal = b["calibration"]
    return {**cal[tag], "size": b["size"], "per_statistic_size": b["size"] if corr == "none" else b["size"] / 3, "n_null": cal["n_null"],
            "window": b["window_days"], "correction": corr}


def test_the_complement_is_added_to_the_regulatory_zone_not_substituted_for_it(built) -> None:
    for did in params.IDS:
        o = built["variants"][did]["outputs"]
        b = o["pla_complement"]
        assert b["flags"]["pla_amber_or_red"]["k"] == o["detection"]["n_amber_or_red"]                      # the zone is the PLA's, unchanged
        union = b["flags"]["family_with_pla"]
        assert union["k"] >= max(o["detection"]["n_amber_or_red"], b["flags"]["family"]["any"]["k"])


def test_the_computing_code_calls_the_engine_and_a_patched_engine_changes_the_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from pipeline.cases.c13 import bake

    real = pc.pla_complement_statistics

    def forged(hpl, rtpl, window=20):
        s = real(hpl, rtpl, window)
        return pc.PLAComplementStatistics(wald=1e6, p_value=0.0, intercept=s.intercept, slope=s.slope, spearman_abs=s.spearman_abs,
                                          spearman_roll=s.spearman_roll, window=s.window, n=s.n)
    monkeypatch.setattr(pc, "pla_complement_statistics", forged)
    out = bake.build(13, 0.02)                        # 20 replications per variant, the floor of replications_for
    r = out["variants"]["none"]["outputs"]["pla_complement"]["flags"]["per_statistic"]["wald"]
    assert r["rate"] == 1.0 or r["rate"] == 0.0       # every statistic is the same constant, so the threshold is it and nothing exceeds it
    assert out["variants"]["none"]["outputs"]["pla_complement"]["calibration"]["thresholds_per_statistic"]["wald"] == 1e6


def test_the_lag_ladder_is_on_the_stale_volatility_variant_only_and_its_lag_20_row_is_the_variant(built) -> None:
    for did in params.IDS:
        if did != "stale-volatility":
            assert block(built, did)["lag_ladder"] is None and block(built, did)["hypothesis"] is None
    b = block(built, "stale-volatility")
    ladder = b["lag_ladder"]
    assert [r["lag_days"] for r in ladder] == [5, 10, 20, 40]
    row20 = next(r for r in ladder if r["lag_days"] == 20)
    assert row20["per_statistic"] == b["flags"]["per_statistic"] and row20["pla_amber_or_red"] == b["flags"]["pla_amber_or_red"]
    assert row20["family_any"] == b["flags"]["family"]["any"]
    o = built["variants"]["stale-volatility"]["outputs"]
    assert o["known_deficiency"]["parameters"][0]["value"] == 20.0                              # the ladder did not change the variant


def test_a_lag_override_changes_only_the_stale_volatility_lag() -> None:
    a = generator.replicate("stale-volatility", 3)
    assert np.array_equal(a.rtpl, generator.replicate("stale-volatility", 3, vol_lag_days=20.0).rtpl)
    assert not np.array_equal(a.rtpl, generator.replicate("stale-volatility", 3, vol_lag_days=5.0).rtpl)
    assert np.array_equal(a.hpl, generator.replicate("stale-volatility", 3, vol_lag_days=5.0).hpl)   # the desk is the same, only the model moves
    assert params.value("stale-volatility", "vol_lag_days") == 20.0
    with pytest.raises(ValueError):
        generator.replicate("missing-basis", 0, vol_lag_days=5.0)


def test_the_hypothesis_block_states_the_measured_number_the_run_size_and_the_verdict(built) -> None:
    h = block(built, "stale-volatility")["hypothesis"]
    assert h["plan_id"] == "BS-13" and h["power_threshold"] == 0.30 and h["refuted_below"] == 0.10 and h["size_limit"] == 0.01
    assert h["measured_power"]["n"] == N and h["held_out_size"]["n"] == N and h["n_null_desk_years"] == 10 * NB
    assert h["verdict"] == complement.verdict(h["measured_power"]["rate"], h["held_out_size"]["rate"])
    for lang in ("en", "es"):
        assert h["statement"][lang] and h["reading"][lang]
    assert h["measured_power"]["rate"] == block(built, "stale-volatility")["flags"]["family"]["spearman_roll"]["rate"]
    assert h["held_out_size"]["rate"] == block(built, "none")["flags"]["family"]["spearman_roll"]["rate"]


def test_the_secondary_clause_compares_the_wald_statistic_with_ks_alone(built) -> None:
    for did in ("wrong-correlation", "missing-basis"):
        s = block(built, did)["against_ks"]
        o = built["variants"][did]["outputs"]
        assert s["ks_flagged"] == o["detection"]["by_test"]["ks_flagged"] and s["wald_flagged"] == block(built, did)["flags"]["per_statistic"]["wald"]["k"]
    assert block(built, "none")["against_ks"] is None


def test_the_power_by_size_table_is_monotone_in_size(built) -> None:
    rows = block(built, "stale-volatility")["by_size"]
    assert [r["size"] for r in rows] == [0.001, 0.005, 0.01, 0.02, 0.05]
    for key in ("wald", "spearman_abs", "spearman_roll"):
        flagged = [r[key]["k"] for r in rows]
        assert flagged == sorted(flagged), key
        held = [r[key + "_held_out"]["k"] for r in rows]
        assert held == sorted(held), key


def test_the_findings_and_texts_state_the_complement_in_both_languages_without_a_raw_id(built) -> None:
    for did, doc in built["variants"].items():
        f = next(x for x in doc["findings"] if x["id"] == "F-COMPLEMENT")
        assert f["title"]["en"] and f["title"]["es"] and "BS-13" not in f["title"]["en"] and "_" not in f["title"]["en"]
        assert "complement" in f["title"]["en"].lower() and "complemento" in f["title"]["es"].lower()


def test_the_small_bake_validates_against_the_schema(built) -> None:
    for vid, doc in built["variants"].items():
        assert cs.errors("c13/variant-deficiency", doc) == [], vid
