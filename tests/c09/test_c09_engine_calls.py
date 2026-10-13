"""CT-1007: the pinned engine reproduces the CCF and EAD goldens of docs/contracts/engine/lgd-ead-api.md (the consumer test),
and the C09 numbers come from it."""
from __future__ import annotations

import math
import pathlib
import re

import numpy as np
import pytest
from pipeline.cases.c09 import estimators, generator
from riskvalidation.lgd_ead import ccf, floors, lgd_models
from riskvalidation.lgd_ead.workout import range_flag
from riskvalidation.validation import lgd_ead as val

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_the_pin_is_riskvalidation_0_6_0() -> None:
    from importlib.metadata import version

    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    tag = re.search(r"CAOS_RiskValidation@v(\d+)\.(\d+)\.(\d+)", req)
    assert tag is not None
    assert version("riskvalidation") == ".".join(str(int(g)) for g in tag.groups())          # tag v0.06.000 is release 0.6.0


def test_the_pinned_engine_reproduces_the_contract_goldens() -> None:
    assert list(ccf.reference_indices("fixed-horizon", 21)) == [9]
    assert list(ccf.reference_indices("cohort", 21, cohort_start_index=12)) == [12]
    assert list(ccf.reference_indices("variable-horizon", 21)) == [9, 12, 15, 18]
    with pytest.raises(ValueError):
        ccf.reference_indices("cohort", 24, cohort_start_index=24)                            # a default in the first month of its cohort
    drawn = np.zeros(24)
    drawn[[9, 12, 15, 18]] = [420, 500, 560, 640]
    c, u = ccf.ccf_observations(drawn, np.full(24, 1000.0), 900.0, np.array([9, 12, 15, 18]))
    assert np.allclose(u, [580, 500, 440, 360]) and np.allclose(c, [0.827586, 0.8, 0.772727, 0.722222], atol=5e-7)
    assert math.isclose(ccf.aggregate_ccf(c, u, "mean"), 0.780634, abs_tol=5e-7)
    assert math.isclose(ccf.aggregate_ccf(c, u, "pooled"), 1480 / 1880, abs_tol=1e-12)
    ccf_in = np.array([-0.1, 0.0, 0.2, 0.6, 1.3])
    assert math.isclose(float(ccf.treat_ccf(ccf_in, "none").values.mean()), 0.4, abs_tol=1e-12)
    cen, fc = ccf.treat_ccf(ccf_in, "censor"), ccf.treat_ccf(ccf_in, "floor-cap")
    assert list(cen.values) == [0.0, 0.2, 0.6] and cen.n_dropped == 2 and math.isclose(float(fc.values.mean()), 0.36)
    assert (cen.n_below_zero, cen.n_above_one) == (1, 1)
    assert float(ccf.ead_from_ccf(np.array([600.0]), np.array([1000.0]), np.array([0.75]))[0]) == 900.0
    leq, ccf_us, eadf = ccf.to_us_terms(np.array([600.0]), np.array([1000.0]), np.array([900.0]))
    assert (float(leq[0]), float(ccf_us[0]), float(eadf[0])) == (0.75, 1.5, 0.9)
    sw, ratio = ccf.small_undrawn_rule(np.array([980.0, 600.0]), np.array([1000.0, 1000.0]), np.array([990.0, 900.0]), 50.0)
    assert list(sw) == [True, False] and np.allclose(ratio, [0.99, 0.75])
    X = np.array([[1, 0], [1, 0], [1, 1], [1, 1.0]])
    fit = ccf.fit_direct_ead(X, np.array([0, 500, 500, 1000.0]), np.full(4, 1000.0))
    assert np.allclose(fit.coefficients, [-1.098612, 2.197225], atol=5e-7)
    pred = ccf.predict_ead(fit, np.array([[1, 1.0]]), np.array([0.0]), np.array([1000.0]))
    assert math.isclose(float(pred[0]), 750.0, abs_tol=1e-6)
    uc = ccf.fit_utilisation_change(np.ones((3, 1)), np.array([400, 500, 600.0]), np.array([700, 800, 900.0]), np.full(3, 1000.0))
    assert np.allclose(uc.coefficients, [0.3])
    assert float(ccf.predict_ead(uc, np.ones((1, 1)), np.array([600.0]), np.array([1000.0]))[0]) == 900.0
    assert math.isclose(ccf.ccf_bias(0.83, 0.60), 0.23, abs_tol=1e-12)
    assert floors.supervisory_ccf("unconditionally-cancellable") == 0.1 and floors.supervisory_ccf("commitments") == 0.4
    fl = floors.ead_floor(np.array([600.0, 600.0]), np.array([1000.0, 1000.0]), np.array([0.4, 0.4]))
    assert np.allclose(fl, 680.0)
    bite = floors.apply_ead_floor(np.array([650.0, 700.0]), np.array([680.0, 680.0]))
    assert list(bite.applied) == [680.0, 700.0] and bite.share_binding == 0.5 and bite.uplift == 15.0
    assert list(range_flag(np.array([-0.1, 0.5, 1.2]))) == ["below-zero", "in-range", "above-one"]
    lf = lgd_models.fit_fractional_logit(X, np.array([0, 0.5, 0.5, 1.0]))
    assert np.allclose(lf.coefficients, [-1.098612, 2.197225], atol=5e-7)
    bt = val.ead_backtest_by_band(np.array([900.0, 500.0]), np.array([800.0, 600.0]), np.array([0.2, 0.8]), np.array([0.0, 0.5, 1.0]))
    assert math.isclose(bt.metric, 0.166667, abs_tol=5e-7) and bt.light == "amber"
    bias = val.ccf_estimator_bias(np.array([0.61, 0.63, 0.65]), 0.60, 0.05)
    assert math.isclose(bias.metric, 0.03, abs_tol=1e-12) and math.isclose(bias.statistic, 2.598076, abs_tol=5e-7)
    assert math.isclose(bias.p_value, 0.121690, abs_tol=5e-7) and bias.light == "green"


def test_a_c09_number_is_the_engines_not_the_products(monkeypatch) -> None:
    d = generator.generate(5, 2, 20_000)
    obs = estimators.observe(d, "fixed-horizon")
    real = estimators.aggregate(obs, "none", "mean").value
    assert 0.0 < real < 1.0
    monkeypatch.setattr(ccf, "aggregate_ccf", lambda c, u, a: 0.123)
    assert estimators.aggregate(obs, "none", "mean").value == 0.123
