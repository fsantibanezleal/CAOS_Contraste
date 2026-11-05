"""Checks of the comparators written for this manuscript against independent implementations, and of the shared decision rule
against the engine's own calibration. Run from the repository root:

    E:/_venvs/contraste-u16-i/Scripts/python.exe -m pytest manuscripts/scale-and-level-complement-to-the-pla-test/experiments -q
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import stats_core as sc  # noqa: E402
from riskvalidation.market import pla_complement as pc  # noqa: E402


@pytest.fixture(scope="module")
def pair():
    rep = sc.generator.replicate("stale-volatility", 3, 13)
    return rep.hpl, rep.rtpl


def test_wald_ols_matches_statsmodels(pair):
    import statsmodels.api as sm

    h, r = pair
    fit = sm.OLS(h, sm.add_constant(r)).fit()
    # the statistic of H0 (a, b) = (0, 1) with the ordinary (OLS) covariance, from statsmodels' covariance matrix
    d = fit.params - np.array([0.0, 1.0])
    ref = float(d @ np.linalg.solve(fit.cov_params(), d))
    assert sc.wald_ols(h, r) == pytest.approx(ref, rel=1e-9)


def test_hc3_wald_matches_statsmodels(pair):
    import statsmodels.api as sm

    h, r = pair
    fit = sm.OLS(h, sm.add_constant(r)).fit(cov_type="HC3")
    d = fit.params - np.array([0.0, 1.0])
    ref = float(d @ np.linalg.solve(fit.cov_params(), d))
    assert pc.pla_mz_wald(h, r).wald == pytest.approx(ref, rel=1e-9)


def test_ljung_box_matches_statsmodels(pair):
    from statsmodels.stats.diagnostic import acorr_ljungbox

    h, r = pair
    x = (h - r) ** 2
    ref = float(acorr_ljungbox(x, lags=[sc.LB_LAGS], return_df=True)["lb_stat"].iloc[0])
    assert sc.ljung_box(x) == pytest.approx(ref, rel=1e-9)


def test_ljung_box_of_constant_is_zero():
    assert sc.ljung_box(np.ones(250)) == 0.0


def test_critical_matches_engine_calibration():
    rng = np.random.default_rng(7)
    n = 2000
    null = [pc.PLAComplementStatistics(wald=float(w), p_value=0.5, intercept=0.0, slope=1.0, spearman_abs=float(a),
                                       spearman_roll=float(s), window=20, n=250)
            for w, a, s in zip(rng.chisquare(2, n), rng.uniform(size=n), rng.uniform(size=n), strict=True)]
    th = pc.pla_complement_calibrate(null, 0.01, "none")
    assert sc.critical(np.array([s.wald for s in null]), 0.01, True) == th.wald
    assert sc.critical(np.array([s.spearman_abs for s in null]), 0.01, False) == th.spearman_abs
    assert sc.critical(np.array([s.spearman_roll for s in null]), 0.01, False) == th.spearman_roll


def test_critical_refuses_an_unresolvable_size():
    with pytest.raises(ValueError):
        sc.critical(np.arange(50.0), 0.01, True)


def test_critical_flags_at_most_k_of_the_null():
    null = np.random.default_rng(1).normal(size=1000)
    t = sc.critical(null, 0.02, True)
    assert sc.flag(null, t, True).sum() <= 20
    assert sc.flag(null, sc.critical(null, 0.02, False), False).sum() <= 20


def test_row_has_every_column_and_matches_the_engine(pair):
    rep = sc.generator.replicate("stale-volatility", 3, 13)
    x = sc.row(rep)
    assert x.shape == (len(sc.COLUMNS),) and np.all(np.isfinite(x))
    st = pc.pla_complement_statistics(rep.hpl, rep.rtpl, 20)
    assert x[sc.IDX["wald_hc3"]] == st.wald and x[sc.IDX["roll20"]] == st.spearman_roll
    assert x[sc.IDX["abs_spearman"]] == st.spearman_abs


def test_wilson_interval_contains_the_rate_and_is_in_unit_interval():
    lo, hi = sc.wilson(0, 1000)
    assert lo == pytest.approx(0.0, abs=1e-12) and 0.0 < hi < 0.005
    lo, hi = sc.wilson(500, 1000)
    assert lo < 0.5 < hi
