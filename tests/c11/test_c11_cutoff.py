"""CT-604, CT-605: no forecast uses its own day or later; the hyperparameters see nothing after 2003-12-31."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from pipeline.cases.c11 import forecast as fc
from pipeline.cases.c11 import hyper
from pipeline.cases.c11.readers import Series

HEAVY = {"caviar", "caviar-es", "gas"}


def _y(n: int = 1100, seed: int = 3) -> np.ndarray:
    import sim

    return sim.shocks(n, seed, 0.01)


@pytest.mark.parametrize("spec", fc.LADDER, ids=lambda s: s.model_id)
def test_adversarial_no_forecast_uses_its_own_day_or_later(spec, tiny):
    """Perturb every return from the third forecast day onward: the forecasts of the first three days are bit-identical
    (each read only days before it), and the fourth, which reads the perturbed day, changes (so the test can fail)."""
    y = _y()
    idx = np.arange(1000, 1004)
    hp = dataclasses.replace(tiny, garch_refit_every_days=2, caviar_refit_every_days=2, gas_refit_every_days=2)
    levels = (0.025,) if spec.kind in HEAVY else (0.01, 0.025)
    base = fc.run_model(spec, y, idx, hp, levels)
    y2 = y.copy()
    y2[idx[2]:] = y2[idx[2]:] * -3.0 + 0.05               # the day idx[2] and everything after it
    y2[idx[2]] = -0.4                                     # an extreme loss on the day the fourth forecast may see
    alt = fc.run_model(spec, y2, idx, hp, levels)
    for a in levels:
        assert np.array_equal(base.var[a][:3], alt.var[a][:3]), f"{spec.model_id}: a forecast read its own day or later"
        assert np.array_equal(base.es[a][:3], alt.es[a][:3], equal_nan=True)
        seen = not (np.array_equal(base.var[a][3:], alt.var[a][3:]) and np.array_equal(base.es[a][3:], alt.es[a][3:], equal_nan=True))
        assert seen, f"{spec.model_id}: the perturbation must be visible to the day after it"


def test_a_window_short_of_history_raises_and_never_pads():
    spec = fc.SPEC_BY_ID["garch-t"]
    with pytest.raises(ValueError, match="needs 250"):
        fc.run_model(spec, _y(300), np.array([100]), fc.Hyper())


def test_adversarial_hyperparameters_ignore_everything_after_the_span(series, monkeypatch):
    monkeypatch.setattr(hyper, "GRID", {"ewma_lambda": (0.94, 0.97), "age_weight_lambda": (0.98, 0.99)})
    monkeypatch.setattr(hyper, "STRIDE", 60)
    base = fc.Hyper(estimation_window_days=500)
    hp1, rec1 = hyper.select(series, base)
    cut_at = np.datetime64("2003-12-31")
    changed = {}
    rng = np.random.default_rng(0)
    for k, s in series.items():
        v = s.values.copy()
        late = s.dates > cut_at
        v[late] = v[late] * rng.uniform(0.2, 5.0, late.sum())      # a different world after the span
        changed[k] = Series(s.series_id, s.unit, s.dates, v, s.missing, s.files)
    hp2, rec2 = hyper.select(changed, base)
    assert hp1 == hp2 and rec1 == rec2, "a hyperparameter depended on a day after 2003-12-31"
    stale = hyper.cut(changed)
    assert all(s.dates.max() <= cut_at for s in stale.values())
    # and the check can fail: changing a value inside the span changes at least one score
    inside = {k: Series(s.series_id, s.unit, s.dates, np.where(s.dates == s.dates[s.dates <= cut_at][-300], s.values * 4.0, s.values),
                        s.missing, s.files) for k, s in series.items()}
    _, rec3 = hyper.select(inside, base)
    assert rec3 != rec1


def test_the_selection_never_picks_outside_its_grid(series, monkeypatch):
    monkeypatch.setattr(hyper, "GRID", {"ewma_lambda": (0.94, 0.99)})
    monkeypatch.setattr(hyper, "STRIDE", 100)
    hp, rec = hyper.select(series, fc.Hyper(estimation_window_days=500))
    assert hp.ewma_lambda in (0.94, 0.99) and rec["span"] == ["1995-01-01", "2003-12-31"]
