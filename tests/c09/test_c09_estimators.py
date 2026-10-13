"""CT-1005, CT-1006: a CCF outside [0, 1] is flagged and never clipped; an undefined CCF is excluded and counted."""
from __future__ import annotations

import numpy as np
from pipeline.cases.c09 import estimators, generator
from riskvalidation.lgd_ead import ccf as engine_ccf


def test_a_ccf_outside_the_unit_interval_is_kept_flagged_and_counted_before_any_treatment(monkeypatch) -> None:
    d = generator.generate(11, 5, 120_000)
    obs = estimators.observe(d, "fixed-horizon")
    finite = obs.ccf[np.isfinite(obs.ccf)]
    assert (finite < 0).any() and (finite > 1).any()
    calls = []
    real = engine_ccf.treat_ccf

    def spy(c, t):
        calls.append(t)
        return real(c, t)

    monkeypatch.setattr(engine_ccf, "treat_ccf", spy)
    none = estimators.treat(obs, "none")
    assert np.array_equal(np.sort(none.values), np.sort(finite)) and none.values.min() < 0 < 1 < none.values.max()
    for t in ("none", "censor", "floor-cap", "bounded-scale"):
        got = estimators.treat(obs, t)
        assert got.n_below_zero == int((finite < 0).sum()) and got.n_above_one == int((finite > 1).sum()), t
    capped = estimators.treat(obs, "floor-cap").values
    assert capped.min() >= 0 and capped.max() <= 1
    assert estimators.treat(obs, "censor").values.size == int(((finite >= 0) & (finite <= 1)).sum())
    assert set(calls) == {"none", "censor", "floor-cap", "bounded-scale"}                       # the engine did the treatments
    est = estimators.aggregate(obs, "none", "mean")
    assert est.share_below_zero == (finite < 0).mean() and est.share_above_one == (finite > 1).mean()
    assert est.flag in ("in-range", "below-zero", "above-one")


def test_an_undefined_ccf_is_excluded_and_counted_and_a_first_month_default_leaves_the_cohort_design() -> None:
    d = generator.generate(12, 3, 120_000)
    obs = estimators.observe(d, "fixed-horizon")
    undrawn = obs.limit_ref - obs.drawn_ref
    assert (undrawn <= 0).sum() > 0 and int(np.isnan(obs.ccf).sum()) == int((undrawn <= 0).sum())
    assert not np.isin(obs.ccf[undrawn <= 0], (0.0, 1.0)).any()
    est = estimators.aggregate(obs, "none", "mean")
    assert est.n_undefined == int((undrawn <= 0).sum()) and est.n_facilities == int((undrawn > 0).sum())
    coh = estimators.observe(d, "cohort")
    first = d.default_month % 12 == 0
    assert first.sum() > 0 and coh.n_excluded == int(first.sum())
    assert not np.isin(coh.fac, np.flatnonzero(first)).any()
    var = estimators.observe(d, "variable-horizon")
    assert var.ccf.size == 4 * d.ead.size and var.n_excluded == 0
