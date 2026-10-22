"""U16-P2: the producer side of C22's other families (data-pipeline/pipeline/cases/c22_studies.py).

C22 writes no simulation of its own (ADR-0069): it runs the engine's named studies (`riskvalidation.generators.size_studies`,
U16-E2) through `simulate_study`. These tests need that module, which ships with the engine's 1.0.0 (the branch
`task/u16-e2` until then); the committed-artifact tests in test_c22_all_families.py do not."""
from __future__ import annotations

import math

import numpy as np
import pytest

size_studies = pytest.importorskip("riskvalidation.generators.size_studies",
                                   reason="the engine with the named size studies (U16-E2, riskvalidation 1.0.0)")

from pipeline.cases import c22_studies as cs  # noqa: E402
from pipeline.cases import c22_validator as c22  # noqa: E402

CASE_SEED = 42


def test_every_registered_p_value_test_outside_the_credit_families_has_a_study():
    registered = cs.registered_other_tests()
    assert len(registered) == 21
    assert set(registered) == set(size_studies.STUDIES)
    cs.check_registry(size_studies.STUDIES)


def test_a_registered_test_without_a_study_stops_the_bake_naming_it():
    broken = {k: v for k, v in size_studies.STUDIES.items() if k != "market.kupiec_pof"}
    with pytest.raises(cs.StudyRegistryError, match="market.kupiec_pof"):
        cs.check_registry(broken)


def test_a_study_of_an_unregistered_test_is_refused():
    extra = {**size_studies.STUDIES, "market.not_a_test": size_studies.STUDIES["market.kupiec_pof"]}
    with pytest.raises(cs.StudyRegistryError, match="market.not_a_test"):
        cs.check_registry(extra)


def test_a_missing_optional_extra_stops_the_bake_naming_it():
    def fake_import(name: str):
        if name == "mapie":
            raise ModuleNotFoundError("No module named 'mapie'")
        return object()

    with pytest.raises(cs.MissingExtraError, match="mapie"):
        cs.check_extras(fake_import)
    cs.check_extras(lambda name: object())
    cs.check_extras()  # the venv of the bake has the three extras installed


def test_the_jobs_are_one_per_variant_study_arm_with_a_seed_derived_from_the_case_seed():
    jobs = cs.jobs_for(CASE_SEED, ("null", "other-families"))
    null = [j for j in jobs if j.variant == "null"]
    other = [j for j in jobs if j.variant == "other-families"]
    assert len(null) == 25 and all(j.n_rep == 4000 and j.arm == "null" for j in null)
    assert len(other) == 50 and all(j.n_rep == 2000 for j in other)
    assert {j.arm for j in other} == {"null", "alternative"}
    for j in jobs:
        assert j.seed == c22._seed(CASE_SEED, f"{j.variant}:{j.key}")
    assert len({j.seed for j in jobs}) == len(jobs) == 75
    assert len({(j.variant, j.key) for j in jobs}) == 75
    # a test with several studies keeps one key per study
    assert {j.key for j in null if j.test_id == "market.dynamic_quantile_test"} == {
        "market.dynamic_quantile_test@null", "market.dynamic_quantile_test#1@null",
        "market.dynamic_quantile_test#2@null", "market.dynamic_quantile_test#3@null"}
    assert [j.variant for j in cs.jobs_for(CASE_SEED, ("miscalibration",))] == []


def test_every_study_has_bilingual_texts_a_label_and_a_panel():
    for tid, studies in size_studies.STUDIES.items():
        assert cs.TEST_LABEL[tid]["en"] and cs.TEST_LABEL[tid]["es"], tid
        assert cs.PANEL_OF[tid] in cs.PANEL_LABEL
        for i, st in enumerate(studies):
            t = cs.study_texts(st, i)
            for part in ("label", "null", "alternative"):
                assert t[part]["en"] and t[part]["es"], (tid, i, part)
            assert chr(0x2014) not in "".join(t[p]["es"] for p in t) and " -> " not in t["alternative"]["es"]
    es = " ".join(v["es"] for v in cs.TEST_LABEL.values())
    assert any(c in es for c in "áéíóúñ")


def test_a_job_run_in_a_worker_equals_the_same_study_run_directly():
    """The pool changes nothing: a repetition depends on the seed and its index only."""
    job = cs.Job("null", "ccr.pfe_exceedance_backtest@null", "ccr.pfe_exceedance_backtest", 0, "null", 60, 12345)
    direct = size_studies.simulate_study(size_studies.STUDIES[job.test_id][0], "null", n_rep=60, seed=12345)
    results = cs.run_jobs([job], workers=2)
    got = results[(job.variant, job.key)]
    assert np.array_equal(got.p_values, direct.p_values, equal_nan=True)
    assert got.rates["p<0.05"].rejections == direct.rates["p<0.05"].rejections


def test_the_p_rates_of_a_study_with_another_rule_come_from_its_p_values():
    st = size_studies.STUDIES["market.kupiec_pof"][0]
    assert st.rule == "red"
    sim = size_studies.simulate_study(st, "null", n_rep=80, seed=7)
    rates = cs.study_rates(sim)
    assert list(rates)[:2] == ["p<0.05", "p<0.01"] and "red" in rates
    finite = sim.p_values[np.isfinite(sim.p_values)]
    assert rates["p<0.05"].rejections == int(np.sum(finite < 0.05))
    assert rates["p<0.01"].rejections == int(np.sum(finite < 0.01))
    assert rates["p<0.05"].n == 80 and rates["p<0.05"].undefined == 80 - finite.size
    # a p-rule study keeps the harness's own rates untouched
    p_st = size_studies.STUDIES["ccr.pfe_exceedance_backtest"][0]
    p_sim = size_studies.simulate_study(p_st, "null", n_rep=40, seed=7)
    assert list(cs.study_rates(p_sim)) == ["p<0.05", "p<0.01"]


def test_a_repetition_without_a_p_value_stops_the_bake():
    st = size_studies.STUDIES["ccr.pfe_exceedance_backtest"][0]
    sim = size_studies.simulate_study(st, "null", n_rep=20, seed=7)
    sim.p_values[3] = np.nan
    with pytest.raises(cs.UndefinedRepetitions, match="ccr.pfe_exceedance_backtest"):
        cs.require_defined("ccr.pfe_exceedance_backtest@null", sim)


def test_the_documented_excess_block_is_built_from_the_measure():
    rates = {"p<0.05": {"rate": 0.0522}, "p<0.01": {"rate": 0.0155}}
    block = cs.excess_block("portfolio.mc_convergence", rates, 4000)
    assert block["page"] == "docs/portfolio/07_validation-tests.md"
    assert block["measured"] == 0.0155 and block["exceeds"] is True
    assert block["bound"] == pytest.approx(c22.size_bound(0.01, 4000))
    assert block["excess"] == pytest.approx(0.0155 - block["bound"])
    held = cs.excess_block("portfolio.mc_convergence", {"p<0.05": {"rate": 0.05}, "p<0.01": {"rate": 0.011}}, 4000)
    assert held["exceeds"] is False and held["excess"] < 0
    assert cs.excess_block("ccr.pfe_exceedance_backtest", rates, 4000) is None
    assert math.isclose(block["bound"], 0.0149, abs_tol=2e-4)


def test_the_models_records_name_every_engine_study():
    studies = cs.model_studies()
    assert len(studies) == 25
    assert {s["test_id"] for s in studies} == set(size_studies.STUDIES)
    gens = cs.generator_classes()
    assert {"PfeSeries", "VarHits", "ThresholdBiasPlant", "ExchangeabilityBreakPlant"} <= {g["class"] for g in gens}
    assert all(g["id"].startswith("G") and g["title"]["en"] and g["title"]["es"] for g in gens)
