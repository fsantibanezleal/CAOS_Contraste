"""U8-S follow-up after the Opus engine review (review-u8-engine-2026-10-13.md): one test per contract amendment. The golden
values of the age-weighted HS recompute from the worked example of Boudoukh, Richardson and Whitelaw (1998, pages 6 and 7)
with market_math.brw_var_es, written from the paper and not from the engine.
"""
from __future__ import annotations

import math

import market_math as mm
from test_u8_contracts import API, section


def test_a1_the_volatility_updated_hs_domain_is_widened_to_alpha_0_5() -> None:
    for name_module, name in (("conventions", "var_es_from_sample"), ("historical", "volatility_updated_hs_var_es")):
        body = section(name_module, name)
        assert "(0, 0.5]" in body, name
    assert "`alpha = 0.5`" in section("historical", "volatility_updated_hs_var_es")


def test_a2_the_age_weighted_hs_reproduces_the_brw_worked_example() -> None:
    initial = mm.brw_example(0)
    later = [0.005] * 125
    for pct, age in ((-3.3, 3), (-2.9, 2), (-2.7, 65), (-2.5, 45), (-2.4, 5), (-2.3, 30)):
        later[125 - age - 25] = pct / 100
    v1, e1 = mm.brw_var_es(initial, 0.05, 0.98, 100)
    v2, e2 = mm.brw_var_es(later, 0.05, 0.98, 100)
    assert round(-v1 * 100, 2) == 2.63 and round(-v2 * 100, 2) == 2.34       # pages 6 and 7 of the paper
    text = section("historical", "age_weighted_var_es")
    for number in (f"{v1:.6f}", f"{e1:.6f}", f"{v2:.6f}", f"{e2:.6f}", "2.63", "2.34", "0.0511", "halfway"):
        assert number in text, number
    assert "UNVERIFIED" not in text.split("- Golden")[0].split("- Invariants")[1], "the interpolation is no longer unverified"


def test_a2_the_equal_weight_limit_is_the_brw_halfway_value_not_historical_var() -> None:
    v, _ = mm.brw_var_es(mm.brw_example(0), 0.05, 0.999999, 100)
    assert math.isclose(v, -0.0235, abs_tol=1e-6)                           # the paper: HS 2.35%, halfway between 2.40% and 2.30%
    text = section("historical", "age_weighted_var_es")
    assert "within one return spacing of `historical_var_es`" in text
    assert "result tends to\n  `historical_var_es`" not in text


def test_a2_the_es_is_the_tail_integral_of_the_corrected_quantile_function() -> None:
    text = section("historical", "age_weighted_var_es")
    assert "D-9" in text and "tail integral" in text and "knot" in text
    _, es = mm.brw_var_es(mm.brw_example(0), 0.05, 0.98, 100)
    v, _ = mm.brw_var_es(mm.brw_example(0), 0.05, 0.98, 100)
    assert es < v < 0


def test_a3_conditional_evt_uses_a_constant_mean_garch_without_an_ar_term() -> None:
    text = section("evt", "conditional_evt_forecast")
    assert "constant-mean GARCH" in text and "no AR term" in text
    assert "an AR-GARCH filter" not in text


def test_a4_the_taylor_es_caviar_estimator_is_stated_with_its_equations_and_its_decision() -> None:
    text = section("caviar", "caviar_es_forecast")
    assert "ES_t = VaR_t - x_t" in text and "g0" in text and "asymmetric Laplace" in text
    assert "D-10" in text and "two-step" in text and "joint" in text
    assert "arXiv 2603.02357" in text
    assert "equations are not transcribed there" not in text
    assert "D-9" in API.read_text(encoding="utf-8").split("## Open items")[1]
    assert "D-10" in API.read_text(encoding="utf-8").split("## Open items")[1]


def test_a5_the_dq_test_must_have_nominal_size_on_correct_forecasts() -> None:
    text = section("validation.market", "dynamic_quantile_test")
    assert "size" in text and "Monte Carlo" in text and "p_value_asymptotic" in text
    for cfg in ("(0.01, T = 250)", "(0.025, T = 250)", "(0.01, T = 750)"):
        assert cfg in text, cfg
    assert "0.03" in text and "0.07" in text
