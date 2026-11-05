"""Checks of the closed forms of the Theory section (``theory.py``) against the generator's own known truth and against a long
simulation of the noise-free model. Run as ``test_core.py``."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import theory  # noqa: E402
from stats_core import generator  # noqa: E402


def test_slope_without_lag_is_one():
    assert theory.slope(0) == 1.0


def test_slope_is_the_generator_pearson_numerator():
    # known_pearson = cov / sqrt(v_hpl v_rt) with cov = v_rt exp(-v (1 - phi^L)): the slope of HPL on RTPL is that exponential
    lag = 20
    v_rt = generator.factor_variance()
    cov = v_rt * theory.slope(lag)
    assert cov / v_rt == pytest.approx(np.exp(-theory.V * (1 - theory.PHI ** lag)))


def test_rolling_corr_is_one_without_lag_and_decreases_with_it():
    assert theory.rolling_corr(0, 20) == pytest.approx(1.0, abs=1e-12)
    vals = [theory.rolling_corr(L, 20) for L in (1, 5, 10, 20, 40, 80, 160)]
    assert all(a > b for a, b in zip(vals, vals[1:], strict=False))
    assert 0.0 < vals[-1] < vals[0] < 1.0


def test_rolling_corr_matches_a_long_window_simulation():
    from scipy.signal import lfilter

    v, phi, lag, w = theory.V, theory.PHI, 10, 20
    rng = np.random.default_rng(5)
    n = 400_000
    g = lfilter([np.sqrt(v * (1 - phi ** 2))], [1.0, -phi], rng.standard_normal(n))
    sigma = np.exp(-v + np.concatenate(([0.0], g[:-1])))
    zeta = rng.standard_normal(n)
    h, r = sigma * zeta, np.concatenate((np.full(lag, sigma[0]), sigma[: n - lag])) * zeta
    k = np.ones(w) / w
    sim = np.corrcoef(np.convolve(np.abs(h), k, "valid"), np.convolve(np.abs(r), k, "valid"))[0, 1]
    assert sim == pytest.approx(theory.rolling_corr(lag, w), abs=0.02)


def test_size_mean_and_sd_of_the_calibrated_rule():
    assert theory.size_mean(10000, 0.01) == pytest.approx(101 / 10001)
    assert theory.size_mean(1000, 0.01) == pytest.approx(11 / 1001)
    assert theory.size_sd(10000, 0.01) == pytest.approx(0.001, rel=0.01)


def test_size_mean_matches_a_gaussian_simulation():
    from scipy import stats

    rng = np.random.default_rng(3)
    n, p, reps = 500, 0.02, 6000
    k = int(np.floor(p * n + 1e-9))
    sizes = [stats.norm.sf(np.sort(rng.standard_normal(n))[::-1][k]) for _ in range(reps)]
    assert np.mean(sizes) == pytest.approx(theory.size_mean(n, p), abs=4 * theory.size_sd(n, p) / np.sqrt(reps))
