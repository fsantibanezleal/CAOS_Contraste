"""BS-16 (method tiers): adaptive conformal inference wrapped around the VaR and ES of HS-250, GARCH-t and FHS in C11.

The acceptance criterion of the plan (method-tiers-sdd-plan section 4, BS-16): the wrapper is compared with the unwrapped
model on Kupiec, conditional coverage, Z2 and FZ0 in the stress windows; the hypothesis is that each of the three wrapped
models passes in at least one more stress window without its FZ0 worsening by more than 5 percent; it is refuted if the
wrapper fails the independence test in equity-2007-09. These tests hold the machinery to that criterion on synthetic series
(no test bakes the real data, ADR-0074): the forecaster is the ladder's own model, causal; the level follows the ACI
recursion of the engine; the rows recompute from their own arrays; the verdict is the rule written before any run."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest
from riskvalidation.market import conformal as rv_cf

from pipeline.cases.c11 import conformal as cf, forecast as fc
from pipeline.cases.c11.constants import LEVELS


def _y(n: int = 1400, seed: int = 11) -> np.ndarray:
    import sim

    return sim.shocks(n, seed, 0.01)


@pytest.fixture(scope="module")
def hp(tiny):
    return dataclasses.replace(tiny, estimation_window_days=500, garch_refit_every_days=5)


FIRST, N_DAYS = 1000, 40


def _idx(first: int = FIRST, n: int = N_DAYS) -> np.ndarray:
    return np.arange(first, first + n)


def test_the_wrapped_models_are_the_three_of_the_plan_and_the_stress_windows_are_the_three_of_the_hypothesis():
    assert cf.WRAPPED == ("hs-250", "garch-t", "fhs")
    assert cf.STRESS_WINDOWS == ("equity-2007-09", "equity-2020", "rates-2022")
    assert cf.GAMMA == 0.005 and cf.PASS_P == 0.05 and cf.FZ0_TOLERANCE == 0.05
    assert (rv_cf.LEVEL_MIN, rv_cf.LEVEL_MAX) == (cf.LEVEL_MIN, cf.LEVEL_MAX)    # the step and the band are the engine's defaults, fixed before any run


@pytest.mark.parametrize("model_id", cf.WRAPPED)
def test_the_forecaster_at_the_target_level_is_the_ladders_own_forecast(model_id, hp):
    y, idx = _y(), _idx()
    spec = fc.SPEC_BY_ID[model_id]
    ladder = fc.run_model(spec, y, idx, hp)
    run = cf.wrap_model(spec, y, idx, hp)
    for a in LEVELS:
        plain = run.plain[a]
        assert np.array_equal(plain.var, ladder.var[a]) and np.array_equal(plain.es, ladder.es[a])
        assert plain.n_clipped == 0 and np.all(plain.levels == a)             # gamma 0 never moves the level


@pytest.mark.parametrize("model_id", cf.WRAPPED)
def test_the_forecast_of_a_day_reads_only_the_returns_before_it(model_id, hp):
    y = _y()
    spec = fc.SPEC_BY_ID[model_id]
    t = FIRST + 7
    base = cf.ModelForecaster(spec, y, FIRST, hp)
    for day in range(FIRST, t + 1):
        base(day, 0.01)
    z = y.copy()
    z[t:] = z[t:] * 9.0 + 0.2                                               # perturb day t and everything after it
    other = cf.ModelForecaster(spec, z, FIRST, hp)
    for day in range(FIRST, t + 1):
        other(day, 0.01)
    assert base(t, 0.01) == other(t, 0.01) and base(t, 0.025) == other(t, 0.025)
    early = cf.ModelForecaster(spec, y, FIRST, hp)
    assert (base(t, 0.01), base(t, 0.025)) != (early(FIRST, 0.01), early(FIRST, 0.025))     # and the check can fail: another day differs


def test_the_working_level_follows_the_aci_recursion_of_the_engine(hp):
    y, idx = _y(), _idx()
    run = cf.wrap_model(fc.SPEC_BY_ID["hs-250"], y, idx, hp)
    for a in LEVELS:
        w = run.wrapped[a]
        assert w.alpha == a and w.gamma == cf.GAMMA and w.levels[0] == a
        for k in range(len(w.levels) - 1):
            assert w.levels[k + 1] == pytest.approx(rv_cf.aci_update(w.levels[k], bool(w.hits[k]), a, cf.GAMMA))
        assert np.array_equal(w.hits, y[idx] < w.var)                          # a hit is the realised return below the forecast


def test_the_rows_recompute_from_their_own_arrays(hp):
    y, idx = _y(), _idx()
    spec = fc.SPEC_BY_ID["garch-t"]
    ladder = fc.run_model(spec, y, idx, hp)
    run = cf.wrap_model(spec, y, idx, hp)
    loss = np.array([cf.r9(-v) for v in y[idx]])
    models = [{"model_id": "garch-t", "by_level": [
        {"alpha": a, "fz0_mean": 0.0, "exceedance_days": [int(i) for i in np.flatnonzero(loss > np.array([cf.r9(-v) for v in ladder.var[a]]))]}
        for a in LEVELS]}]
    rows = cf.build_rows(spec, loss, run, models, hp, z2_draws=300)
    assert [(r["model_id"], r["alpha"]) for r in rows] == [("garch-t", a) for a in LEVELS]
    for r in rows:
        a, s = r["alpha"], r["series"]
        var, es = np.array(s["var"]), np.array(s["es"])
        assert np.all(var > 0) and np.all(es >= var) and len(var) == len(loss) == r["n_days"]
        assert s["exceedance_days"] == [int(i) for i in np.flatnonzero(loss > var)]
        assert r["wrapped"]["n_exceedances"] == len(s["exceedance_days"])
        sc = rv_cf.forecast_scores(-loss, -var, -es, a)                            # the engine's own reading of the stored arrays
        assert r["wrapped"]["fz0_mean"] == pytest.approx(sc.fz0_mean, abs=1e-9) and r["wrapped"]["z2"] == pytest.approx(sc.z2, abs=1e-9)
        assert r["wrapped"]["kupiec_p"] == pytest.approx(sc.kupiec_p, abs=1e-9)
        un = rv_cf.forecast_scores(y[idx], ladder.var[a], ladder.es[a], a)
        assert r["unwrapped"]["fz0_mean"] == pytest.approx(un.fz0_mean, abs=1e-8)
        assert r["fz0_change"] == pytest.approx((sc.fz0_mean - un.fz0_mean) / abs(un.fz0_mean), abs=1e-7)
        assert r["working_level"]["min"] <= a <= r["working_level"]["max"]
        assert r["n_clipped"] == run.wrapped[a].n_clipped


def test_a_coverage_pass_needs_both_p_values_at_five_percent_and_not_evaluated_is_not_a_pass():
    ok = {"kupiec_p": 0.30, "conditional_coverage_p": 0.06}
    assert cf.passes_coverage(ok) is True
    assert cf.passes_coverage({**ok, "kupiec_p": 0.049}) is False
    assert cf.passes_coverage({**ok, "conditional_coverage_p": 0.0499}) is False
    assert cf.passes_coverage({**ok, "conditional_coverage_p": None}) is False       # a test that did not run passes nothing


def _row(model, alpha, un_pass, w_pass, change, indep=0.4):
    def side(passed):
        return {"kupiec_p": 0.5 if passed else 0.001, "conditional_coverage_p": 0.5 if passed else 0.001, "independence_p": indep}
    return {"model_id": model, "alpha": alpha, "unwrapped": side(un_pass), "wrapped": side(w_pass), "fz0_change": change}


def _rows(table):
    """``table[(window, model, alpha)] = (unwrapped passes, wrapped passes, fz0 change, wrapped independence p)``."""
    out = {w: [] for w in cf.STRESS_WINDOWS}
    for (w, m, a), (u, v, ch, *ind) in table.items():
        out[w].append(_row(m, a, u, v, ch, *(ind or [0.4])))
    return out


def _all(un, wr, ch=0.01, indep=0.4):
    return {(w, m, a): (un[i], wr[i], ch, indep) for i, w in enumerate(cf.STRESS_WINDOWS) for m in cf.WRAPPED for a in LEVELS}


def test_the_hypothesis_holds_when_every_model_and_level_gains_a_window_within_the_fz0_tolerance():
    h = cf.hypothesis(_rows(_all((False, False, True), (True, False, True))))
    assert h["holds"] is True and h["refuted"] is False and h["n_cells"] == 6 and h["n_cells_hold"] == 6
    assert {c["extra_windows"] for c in h["cells"]} == {1}


def test_a_model_with_nothing_to_gain_is_a_cell_that_does_not_hold():
    h = cf.hypothesis(_rows(_all((True, True, True), (True, True, True))))               # the unwrapped model already passes everywhere
    assert h["holds"] is False and h["n_cells_hold"] == 0 and all(c["extra_windows"] == 0 for c in h["cells"])


def test_an_fz0_worsening_above_five_percent_in_any_stress_window_fails_the_cell():
    table = _all((False, False, False), (True, True, True))
    table[("equity-2020", "fhs", 0.01)] = (False, True, 0.0501, 0.4)
    h = cf.hypothesis(_rows(table))
    bad = next(c for c in h["cells"] if c["model_id"] == "fhs" and c["alpha"] == 0.01)
    assert bad["extra_windows"] == 3 and bad["worst_fz0_change"] == pytest.approx(0.0501) and bad["holds"] is False
    assert h["n_cells_hold"] == 5 and h["holds"] is False
    table[("equity-2020", "fhs", 0.01)] = (False, True, 0.05, 0.4)                          # exactly 5 percent is within the tolerance
    assert cf.hypothesis(_rows(table))["holds"] is True


def test_the_hypothesis_is_refuted_when_a_wrapped_model_fails_independence_in_2007_09():
    table = _all((False, False, False), (True, True, True))
    assert cf.hypothesis(_rows(table))["refuted"] is False
    table[("equity-2007-09", "garch-t", 0.025)] = (False, True, 0.0, 0.049)
    h = cf.hypothesis(_rows(table))
    assert h["refuted"] is True and h["holds"] is False
    assert [(x["model_id"], x["alpha"]) for x in h["independence_2007_09"] if x["fails"]] == [("garch-t", 0.025)]


def test_the_verdict_text_states_the_counts_in_both_languages():
    h = cf.hypothesis(_rows(_all((False, False, True), (True, False, True))))
    for lang in ("en", "es"):
        assert "6" in h["verdict"][lang] and h["verdict"][lang].strip()
    assert h["statement"]["en"] != h["statement"]["es"] and h["refuted_if"]["es"]
    assert h["run"]["gamma"] == cf.GAMMA and h["run"]["stress_windows"] == list(cf.STRESS_WINDOWS)


def test_a_forecast_that_fails_holds_the_previous_one_and_is_counted(hp, monkeypatch):
    y, idx = _y(), _idx(n=12)
    spec = fc.SPEC_BY_ID["garch-t"]
    real = fc._day_context
    calls = {"n": 0}

    def flaky(spec_, win, k, hp_, out, fits):
        calls["n"] += 1
        if k == 3:
            raise ValueError("planted failure")
        return real(spec_, win, k, hp_, out, fits)

    monkeypatch.setattr(fc, "_day_context", flaky)
    run = cf.wrap_model(spec, y, idx, hp)
    assert run.n_fallback_days == 1
    for a in LEVELS:
        assert run.plain[a].var[3] == run.plain[a].var[2]                          # held, not filled with a number of its own
    first_day = cf.ModelForecaster(spec, y, FIRST, hp)
    monkeypatch.setattr(fc, "_day_context", lambda *a, **k: (_ for _ in ()).throw(ValueError("planted failure")))
    with pytest.raises(RuntimeError, match="first day"):
        first_day(FIRST, 0.01)                                                      # the first day never falls back


def test_two_runs_are_identical_and_the_cache_returns_the_same_arrays(hp, tmp_path):
    y, idx = _y(), _idx(n=15)
    jobs = {"w": (y[:idx[-1] + 1], idx)}
    first = cf.wrap_windows(jobs, hp, tmp_path, "test-engine", ("hs-250", "fhs"), workers=1, log=lambda *_: None)
    cached = sorted(tmp_path.glob("*.json"))
    assert len(cached) == 2
    again = cf.wrap_windows(jobs, hp, tmp_path, "test-engine", ("hs-250", "fhs"), workers=1, log=lambda *_: None)
    for m in ("hs-250", "fhs"):
        for a in LEVELS:
            assert np.array_equal(first["w"][m].wrapped[a].var, again["w"][m].wrapped[a].var)
            assert np.array_equal(first["w"][m].wrapped[a].levels, again["w"][m].wrapped[a].levels)
    assert sorted(tmp_path.glob("*.json")) == cached                              # nothing was recomputed
    other = cf.wrap_windows(jobs, dataclasses.replace(hp, estimation_window_days=400), tmp_path, "test-engine", ("hs-250",), workers=1, log=lambda *_: None)
    assert len(list(tmp_path.glob("*.json"))) == 3 and other["w"]["hs-250"] is not None   # another hyperparameter set is another cache key


def test_a_run_that_is_not_the_ladders_model_is_refused(hp):
    y, idx = _y(), _idx()
    spec = fc.SPEC_BY_ID["hs-250"]
    run = cf.wrap_model(spec, y, idx, hp)
    loss = np.array([cf.r9(-v) for v in y[idx]])
    wrong = [{"model_id": "hs-250", "by_level": [{"alpha": a, "fz0_mean": 0.0, "exceedance_days": [0, 1, 2]} for a in LEVELS]}]
    with pytest.raises(ValueError, match="not the ladder's model"):
        cf.build_rows(spec, loss, run, wrong, hp, z2_draws=100)
