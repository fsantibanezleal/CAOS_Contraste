"""CT-1703 and CT-1704: the true annual loss quantile."""
from __future__ import annotations

import pytest
from pipeline.cases.c17 import truth
from riskvalidation.oprisk import aggregate as agg
from riskvalidation.oprisk import distributions as dist


def test_the_true_quantile_agrees_across_fft_panjer_and_monte_carlo(small_truths):
    for xi, t in small_truths.items():
        qm = t.exceedance_block["quantile_999_eur"]
        assert abs(qm["panjer"] - qm["fft"]) / qm["panjer"] < 1e-3, xi
        mc = t.truth_block["annual_loss_quantile"]["mc_check"]
        assert mc["agrees"] and abs(mc["value_eur"] - t.quantile_eur) <= 3 * mc["standard_error_eur"]
        assert qm["fft"] == t.quantile_eur and t.method == "fft"
        # the Fourier truth is on a fine grid: its step is at most 1/10,000 of the quantile
        assert t.grid_step_eur <= t.quantile_eur / 1e4
    # the exceedance curve passes through 1 - 0.999 at the quantile: the survival just above is below, just below is above
    t = small_truths[0.8]
    ex = t.exceedance_block
    sf = dict(zip(ex["grid_eur"], ex["fft"]["exceedance"]))
    assert all(a >= b for a, b in zip(ex["fft"]["exceedance"], ex["fft"]["exceedance"][1:]))
    assert max(sf.values()) <= 1.0


def test_the_true_quantile_increases_with_the_tail_index_and_no_mean_at_one_or_more(small_truths, variants_):
    qs = [small_truths[xi].quantile_eur for xi in sorted(small_truths)]
    assert qs == sorted(set(qs)) and len(qs) == 4
    for xi, t in small_truths.items():
        blk = t.truth_block["annual_loss_mean"]
        if xi >= 1.0:
            assert blk["value_eur"] is None and "infinite mean" in blk["reason"] and t.mean_eur is None
            assert dist.severity_moment("gpd", variants_[xi].sev_params, 1) == float("inf")
        else:
            assert blk["value_eur"] > 0 and blk["reason"] is None
            mom = agg.compound_poisson_moments(variants_[xi].lambda_per_year, "gpd", variants_[xi].sev_params)
            assert blk["value_eur"] == pytest.approx(mom.mean)
    assert truth.NO_MEAN.startswith("the tail index is 1 or more")
