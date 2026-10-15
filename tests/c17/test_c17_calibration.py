"""CT-1701 and CT-1702: the generator is calibrated to the LDCE medians."""
from __future__ import annotations

import numpy as np
import pytest
from pipeline.cases.c17 import generator
from pipeline.cases.c17 import params as P
from riskvalidation.oprisk import distributions as dist


def _sse(xi: float, beta_prime: float) -> float:
    return float(np.sum(generator._log_residuals(xi, beta_prime) ** 2))


def test_the_fitted_quantiles_reproduce_the_ldce_percentiles_within_the_tolerance(variants_):
    t = P.LDCE_TARGETS
    assert t["label"] == "derived-only" and t["licence_class"] == "derived-only" and t["source"]["id"] == "bcbs160"
    assert t["source"]["url"] == "https://www.bis.org/publ/bcbs160.htm" and t["source"]["table"]
    assert [(r["p"], r["loss_eur"]) for r in t["severity_percentiles"]] == [(0.25, 27632), (0.5, 41916), (0.75, 82608), (0.95, 418400)]
    assert variants_[0.96].max_abs_log_error < 0.1  # the tail index of the dossier's own fit (0.96378) reproduces the four medians
    for xi, v in variants_.items():
        assert v.max_abs_log_error <= P.CALIBRATION_TOLERANCE_LOG, (xi, v.max_abs_log_error)
        p = np.array([q for q, _ in P.LDCE_PERCENTILES])
        want = np.array([x for _, x in P.LDCE_PERCENTILES])
        got = dist.severity_ppf("gpd", (xi, v.scale_above_ldce_eur, 20_000.0), p)
        assert np.allclose(got, v.fitted_quantiles_eur)
        assert np.max(np.abs(np.log((got - 20_000.0) / (want - 20_000.0)))) == pytest.approx(v.max_abs_log_error)
        # the least squares optimum: moving the scale either way raises the squared error
        assert _sse(xi, v.scale_above_ldce_eur) < _sse(xi, v.scale_above_ldce_eur * 1.01)
        assert _sse(xi, v.scale_above_ldce_eur) < _sse(xi, v.scale_above_ldce_eur * 0.99)
        # a GPD conditioned above EUR 20,000 is the GPD with the shifted scale: the floor-based scale reproduces the fit
        assert abs(v.scale_eur + xi * (20_000.0 - P.FLOOR_EUR) - v.scale_above_ldce_eur) < 1e-6


def test_the_generator_counts_the_ldce_median_frequency_above_20000(variants_):
    for xi, v in variants_.items():
        assert abs(generator.expected_count_above(v, 20_000.0) - P.LDCE_FREQUENCY_PER_BN * P.ASSETS_EUR_BN) < 1e-6
        h = generator.draw_history(v, seed=5, n_years=400)
        per_year = np.count_nonzero(h.amount_eur >= 20_000.0) / 400
        sd = np.sqrt(41.0 / 400)
        assert abs(per_year - 41.0) < 4 * sd, (xi, per_year)
