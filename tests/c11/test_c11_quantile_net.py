"""S-1 (method tiers): the R10 quantile network trained on the FZ0 loss, a state-of-the-art rung of the C11 ladder.

It is trained on each forecast day's estimation window only (``y[i-w:i]``), never on the day itself or later, and its VaR and ES go
through the same eligibility gates and FZ0 ranking as R1 to R9. These tests are the acceptance criterion of the plan: the network
learns (its training FZ0 beats its own starting point), is causal, deterministic, and the training loss is the engine's FZ0."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest
from riskvalidation.market import scoring

from pipeline.cases.c11 import documents as docs, forecast as fc, quantile_net as qn
from pipeline.cases.c11.constants import LEVELS


def _y(n: int = 1100, seed: int = 3) -> np.ndarray:
    import sim

    return sim.shocks(n, seed, 0.01)


FAST = qn.NetHyper(hidden_units=4, epochs=40, n_starts=2, refit_every_days=50)


def test_the_ladder_trains_the_network_as_rung_r10():
    spec = fc.SPEC_BY_ID["nn-fz"]
    assert spec.rung == "R10" and spec.kind == "nn" and spec.forecasts_es and fc.LADDER[-1] is spec
    assert len(fc.LADDER) == 18 and fc.MIN_OBS["nn"] >= 500


def test_the_training_loss_is_the_engines_fz0():
    """The network's loss is the engine's FZ0 (checked on random draws that satisfy e <= v < 0), not a look-alike."""
    import torch

    rng = np.random.default_rng(0)
    for a in LEVELS:
        y = rng.standard_t(5, 400) * 0.01
        v = -np.abs(rng.normal(0.02, 0.005, 400)) - 0.005
        e = v - np.abs(rng.normal(0.01, 0.003, 400)) - 1e-4
        ours = float(qn.net_loss(torch.tensor(y), torch.tensor(v), torch.tensor(e), a))
        assert abs(ours - float(np.mean(scoring.fz0_loss(y, v, e, a)))) < 1e-9


def test_features_of_a_day_never_read_that_day_or_later():
    y = _y(300)
    base, s0 = qn.features(y)
    for cut in (120, 200, 250):
        z = y.copy()
        z[cut:] = z[cut:] * 7.0 + 0.05                    # perturb the day ``cut`` and everything after it
        pert, s1 = qn.features(z)
        rows = cut - qn.FIRST_ROW                         # rows t < cut are the same; the row of t == cut reads only y[:cut]
        assert np.array_equal(base[: rows + 1], pert[: rows + 1]) and np.array_equal(s0[: rows + 1], s1[: rows + 1])
        assert not np.array_equal(base[rows + 2:], pert[rows + 2:])      # and the check can fail: later rows do move


def test_the_forecast_of_a_day_is_causal():
    y = _y()
    idx = np.array([1000, 1001, 1002])
    hp = dataclasses.replace(fc.Hyper(), estimation_window_days=600)
    r = fc.run_model(fc.SPEC_BY_ID["nn-fz"], y, idx, hp, net=FAST)
    z = y.copy()
    z[1001:] = z[1001:] * 5.0                              # change the day 1001 and what follows
    r2 = fc.run_model(fc.SPEC_BY_ID["nn-fz"], z, idx, hp, net=FAST)
    for a in LEVELS:
        assert np.array_equal(r.var[a][:2], r2.var[a][:2]) and np.array_equal(r.es[a][:2], r2.es[a][:2])   # days 1000, 1001 read y[:1001]
        assert r.var[a][2] != r2.var[a][2]                 # the check can fail: day 1002 reads y[1001] and does see the change


def test_the_forecasts_are_losses_with_es_below_var_and_deterministic():
    y = _y()
    idx = np.arange(1000, 1060)
    hp = dataclasses.replace(fc.Hyper(), estimation_window_days=600)
    r1 = fc.run_model(fc.SPEC_BY_ID["nn-fz"], y, idx, hp, net=FAST)
    r2 = fc.run_model(fc.SPEC_BY_ID["nn-fz"], y, idx, hp, net=FAST)
    r3 = fc.run_model(fc.SPEC_BY_ID["nn-fz"], y, idx, dataclasses.replace(hp, seed=7), net=FAST)
    for a in LEVELS:
        assert np.all(r1.var[a] < 0) and np.all(r1.es[a] <= r1.var[a]) and np.all(np.isfinite(r1.es[a]))
        assert np.array_equal(r1.var[a], r2.var[a]) and np.array_equal(r1.es[a], r2.es[a])
    assert not np.array_equal(r1.var[0.01], r3.var[0.01])          # the seed matters
    assert r1.n_refits >= 2 and f"train_fz0@{0.01:g}" in r1.params


def test_the_network_learns_from_its_training_window():
    """A trained net scores a lower FZ0 on its window than the untrained start of the same seed (it is optimising, not echoing)."""
    y = _y()[:700]
    fit = qn.fit_net(y, 0.025, qn.NetHyper(hidden_units=6, epochs=150, n_starts=2), 42)
    start = qn.fit_net(y, 0.025, dataclasses.replace(qn.NetHyper(hidden_units=6, n_starts=2), epochs=0), 42)
    assert fit.converged and fit.train_fz0 < start.train_fz0 - 1e-3
    v, e = qn.predict(fit, y)
    assert v < 0 and e <= v


def test_a_collapsed_or_non_finite_window_is_refused():
    with pytest.raises(ValueError):
        qn.fit_net(np.zeros(600), 0.01, FAST, 1)
    with pytest.raises(ValueError):
        qn.fit_net(_y()[:50], 0.01, FAST, 1)               # too short for the features


def test_the_fingerprint_follows_the_network_hyperparameters_only_for_its_rung():
    y, idx, hp = _y(), np.array([1000]), fc.Hyper()
    a = fc.fingerprint(y, idx, hp, fc.SPEC_BY_ID["nn-fz"], "e", net=FAST)
    b = fc.fingerprint(y, idx, hp, fc.SPEC_BY_ID["nn-fz"], "e", net=dataclasses.replace(FAST, epochs=41))
    assert a != b
    old = fc.fingerprint(y, idx, hp, fc.SPEC_BY_ID["ewma"], "e")
    assert old == fc.fingerprint(y, idx, hp, fc.SPEC_BY_ID["ewma"], "e", net=dataclasses.replace(FAST, epochs=41))   # no cache of R1-R9 is lost


def test_the_model_summary_states_the_network(tiny):
    spec = fc.SPEC_BY_ID["nn-fz"]
    assert docs.refit_days(spec, tiny) == qn.NET.refit_every_days
    summary = docs.model_summary(spec, tiny, "e")
    assert summary["rung"] == "R10" and summary["parameters"]["hidden_units"]["value"] == float(qn.NET.hidden_units)
    assert summary["parameters"]["epochs"]["value"] == float(qn.NET.epochs)


def test_the_network_hyperparameters_are_chosen_on_the_span_by_the_lowest_score(monkeypatch):
    """The selection reads span data only and takes the lowest summed FZ0 per hyperparameter; ties go to the first candidate."""
    from pipeline.cases.c11 import hyper

    seen = []

    def fake_span(series):
        seen.append(series)
        return {"equity": (np.zeros(10), np.arange(10)), "rates": (np.zeros(10), np.arange(10))}

    def fake_score(args):
        name, value, cls, *_ = args
        good = {"hidden_units": 16, "weight_decay": 1e-1}[name]
        return name, value, cls, 0.5 if value == good else 1.0

    monkeypatch.setattr(hyper, "span_portfolios", fake_span)
    monkeypatch.setattr(hyper, "_score_net", fake_score)
    net, record = hyper.select_net({"s": 1}, fc.Hyper())
    assert net.hidden_units == 16 and net.weight_decay == 1e-1 and net.epochs == qn.NET.epochs
    assert record["selected"] == {"hidden_units": 16, "weight_decay": 1e-1} and len(record["grid"]["hidden_units"]["candidates"]) == 3
    assert record["span"] == list(hyper.SPAN) and seen == [{"s": 1}]


def test_the_span_score_of_the_network_is_a_finite_fz0_and_the_network_is_not_scored_beyond_the_span():
    from pipeline.cases.c11 import hyper

    y = _y(1500)
    name, value, cls, total = hyper._score_net(("hidden_units", 4, "equity", y, np.arange(1000, 1400), fc.Hyper(), FAST))
    assert (name, value, cls) == ("hidden_units", 4, "equity") and np.isfinite(total) and abs(total) < 100


def test_the_selected_network_is_cached_by_the_span_data(monkeypatch, tmp_path):
    from pipeline.cases.c11 import bake, hyper

    calls = []
    monkeypatch.setattr(hyper, "select_net", lambda series, hp, base, workers, log: (calls.append(1) or (dataclasses.replace(base, hidden_units=16), {"r": 1})))
    monkeypatch.setattr(bake, "_series_fingerprint", lambda s: "fp")
    monkeypatch.setattr(hyper, "cut", lambda s: s)
    a = bake.fix_net({}, fc.Hyper(), tmp_path, 1)
    b = bake.fix_net({}, fc.Hyper(), tmp_path, 1)
    assert a == b == (dataclasses.replace(qn.NET, hidden_units=16), {"r": 1}) and len(calls) == 1
    assert bake.fix_net({}, dataclasses.replace(fc.Hyper(), seed=1), tmp_path, 1) and len(calls) == 2     # the key follows the hyperparameters
