"""CT-506: the three rungs and the thin vintage."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.cases.c06 import ladder, macro, panel
from pipeline.cases.c06.run import RungNotEvaluated, run_date


def test_the_three_rungs_fit_and_say_what_they_stand_on(variant):
    lad = variant.run.ladder
    for status in (lad.km.status, lad.dth.status, lad.cox.status):
        assert status.evaluated and status.n_loans >= ladder.MIN_LOANS and status.n_events >= ladder.MIN_EVENTS
    ages = np.array([0.0, 12.0, 36.0])
    horizons = np.array([12.0, 36.0])
    km = lad.km.cumulative(ages, horizons)
    cox = lad.cox.cumulative(variant.run.stratum[:3], ages, horizons)
    for curve in (km, cox):
        assert ((curve > 0.0) & (curve < 1.0)).all() and (np.diff(curve, axis=1) > 0).all()
    hz = lad.dth.hazard_path(variant.run.stratum[:5], variant.run.age_m[:5] // 3, macro.lagged_for_hazard(variant.run.history, variant.run.paths["baseline"]))
    assert ((hz > 0) & (hz < 1)).all()
    assert lad.dth.converged and set(macro.MACRO_VARS) <= set(lad.dth.names)
    rungs = {m["id"]: m for m in variant.document["model"]}
    assert set(rungs) == {"L0-km", "L1-dth", "L2-cox"}
    assert all(m["engine"] == "statsmodels" for m in rungs.values())


def test_a_thin_vintage_is_reported_with_its_count_and_not_fitted(tables):
    loans, fed = tables["loans"], tables["fed"]
    early = np.datetime64("1991-06-30")
    obs = panel.observe(loans, early)
    hist = macro.history_known(fed, early)
    lad = ladder.fit_ladder(loans, obs, hist)
    n = int(obs.selected.sum())
    assert n < ladder.MIN_LOANS
    for status in (lad.km.status, lad.dth.status, lad.cox.status):
        assert not status.evaluated and status.n_loans == n
        assert f"{n} loans" in status.reason and f"{status.n_events} defaults" in status.reason
    assert lad.dth.params.size == 0 and lad.km.survival is None and lad.cox.cumulative_hazard is None
    with pytest.raises(RungNotEvaluated, match="fewer than"):
        run_date(loans, fed, early, min_quarter_at_risk=60)


def test_a_hazard_never_reads_macro_outside_its_training_range(variant):
    m = variant.run.ladder.dth
    wild = np.array([[99.0, -99.0, 99.0]])
    clipped = m.clip_macro(wild)
    assert (clipped <= m.macro_hi).all() and (clipped >= m.macro_lo).all()
    assert np.array_equal(m.clip_macro(clipped), clipped)


def test_adversarial_a_vintage_with_too_few_defaults_is_not_fitted(tables):
    import dataclasses

    loans, fed = tables["loans"], tables["fed"]
    # every default of the sample turned into a payment: plenty of loans, no defaults
    calm = dataclasses.replace(loans, exit_kind=np.where(loans.exit_kind == panel.EXIT_DEFAULT, panel.EXIT_PAID, loans.exit_kind))
    r = np.datetime64("2010-12-31")
    obs = panel.observe(calm, r)
    lad = ladder.fit_ladder(calm, obs, macro.history_known(fed, r))
    assert int(obs.selected.sum()) > ladder.MIN_LOANS
    for status in (lad.km.status, lad.dth.status, lad.cox.status):
        assert not status.evaluated and status.n_events == 0 and "0 defaults" in status.reason
