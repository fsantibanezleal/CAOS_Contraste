"""CT-518 to CT-520: the S-4 comparison (PC-Hazard against Cox) carries loan-level bootstrap intervals beside its pre-registered verdict.

The bootstrap resamples the out-of-time accounts with replacement and holds the predictions fixed: it measures the sampling noise of
the comparison, not of the fits. The tests state it on known truth (a planted case of two rungs that differ by noise only), on the
estimators it re-implements with weights (the existing Kaplan-Meier and Aalen-Johansen, checked on expanded samples), on the point
statistics of ``s4_evaluation`` (the replicate that draws every account once), and on the documents of the sample bake."""
from __future__ import annotations

import dataclasses
import json

import numpy as np
import pytest

from pipeline.cases import bootstrap as bs
from pipeline.cases.c06 import backtest as bt
from pipeline.cases.c06 import page, s4_bootstrap as s4
from pipeline.cases.c06.neural import aalen_johansen

REPLICATES = 80


# ---------------------------------------------------------------------------------------------------------------------
# the shared helper


def test_the_defaults_are_the_pre_registered_ones() -> None:
    assert bs.REPLICATES == 1000 and bs.LEVEL == 0.95 and bs.MIN_EVENTS == 30


def test_a_draw_is_a_resample_with_replacement_of_the_accounts_and_a_pure_function_of_the_seed() -> None:
    a = list(bs.draws(500, 5, seed=7))
    b = list(bs.draws(500, 5, seed=7))
    c = list(bs.draws(500, 5, seed=8))
    assert len(a) == 5 and all(x.shape == (500,) and x.sum() == 500 and x.dtype.kind in "iu" for x in a)
    assert all(np.array_equal(x, y) for x, y in zip(a, b, strict=True))
    assert not np.array_equal(a[0], c[0])
    assert max(int(x.max()) for x in a) > 1 and min(int(x.min()) for x in a) == 0  # with replacement: some twice, some never


def test_the_percentile_interval_is_the_2_5_and_97_5_percentiles_of_the_finite_replicates() -> None:
    v = np.arange(1.0, 1001.0)
    lo, hi, n = bs.percentile_interval(np.concatenate([v, [np.nan, np.inf]]))
    assert (lo, hi, n) == (pytest.approx(np.percentile(v, 2.5)), pytest.approx(np.percentile(v, 97.5)), 1000)


def test_a_difference_states_its_interval_and_whether_it_excludes_zero_and_is_null_with_a_reason_otherwise() -> None:
    rng = np.random.default_rng(0)
    d = bs.difference(-0.5, rng.normal(-0.5, 0.1, 1000))
    assert d["excludes_zero"] is True and d["lo"] < d["difference"] < d["hi"] < 0 and d["n_valid"] == 1000 and d["reason"] is None
    near = bs.difference(0.01, rng.normal(0.01, 0.1, 1000))
    assert near["excludes_zero"] is False and near["lo"] < 0 < near["hi"]
    none = bs.difference(None, np.array([]), reason=bs.text("no horizon is observed", "ningún horizonte se observa"))
    assert none["difference"] is None and none["lo"] is None and none["hi"] is None and none["excludes_zero"] is None
    assert none["n_valid"] == 0 and none["reason"]["en"] and none["reason"]["es"]
    few = bs.difference(0.2, np.array([0.2, np.nan, np.nan]))
    assert few["lo"] is None and few["reason"]["en"] and few["n_valid"] == 1


def test_the_method_statement_says_what_is_resampled_and_what_is_not_refit() -> None:
    t = bs.method_text("out-of-time accounts", "las cuentas fuera de tiempo")
    assert "accounts" in t["en"] and "cuentas" in t["es"]
    assert "1,000" in t["en"] and "2.5" in t["en"] and "1.000" in t["es"] and "2,5" in t["es"] and "97,5" in t["es"]  # each language's number form
    assert "not refit" in t["en"].lower() or "held fixed" in t["en"].lower()
    assert "fijas" in t["es"].lower() or "no se reajust" in t["es"].lower()


# ---------------------------------------------------------------------------------------------------------------------
# the weighted estimators: the existing Kaplan-Meier and Aalen-Johansen on a resample


def _sample(n: int, seed: int):
    rng = np.random.default_rng(seed)
    t = np.round(rng.exponential(30.0, n), 1) + 0.5          # rounded: ties between accounts, as the file has
    cause = rng.choice([0, 1, 2], size=n, p=[0.4, 0.3, 0.3])
    horizon = 40.0
    event = (cause == 1) & (t <= horizon)
    t = np.minimum(t, horizon)
    cause = np.where(t >= horizon, 0, cause)
    return t, event, cause


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_the_weighted_estimators_equal_the_existing_ones_on_the_expanded_sample(seed: int) -> None:
    t, ev, cause = _sample(600, seed)
    w = np.random.default_rng(seed + 10).integers(0, 4, t.size)
    rep = np.repeat(np.arange(t.size), w)
    hz = (6, 12, 18, 24, 30, 36)
    km, aj = s4.weighted_estimates(t, ev, cause, w.astype(float), hz)
    km0, _ = bt.km_observed(t[rep], ev[rep], hz, 40.0)
    aj0 = aalen_johansen(t[rep], cause[rep], np.array(hz, float), target=1)
    assert np.allclose(km, km0, atol=1e-12, rtol=0) and np.allclose(aj, aj0, atol=1e-12, rtol=0)


def test_a_weighted_group_with_no_event_has_zero_cumulative_default() -> None:
    t = np.array([1.0, 2.0, 3.0])
    km, aj = s4.weighted_estimates(t, np.zeros(3, bool), np.zeros(3, int), np.ones(3), (6, 12))
    assert km.tolist() == [0.0, 0.0] and aj.tolist() == [0.0, 0.0]


# ---------------------------------------------------------------------------------------------------------------------
# a planted case: two rungs that differ by noise only, and one that is worse


def _planted(n: int, seed: int, worse: bool = False):
    rng = np.random.default_rng(seed)
    risk = rng.lognormal(0.0, 0.7, n)
    lam = 0.004 * risk                                         # per month
    t_event = rng.exponential(1.0 / lam)
    t_cens = rng.uniform(20.0, 60.0, n)
    time = np.minimum(np.minimum(t_event, t_cens), 40.0)
    event = (t_event <= np.minimum(t_cens, 40.0))
    cause = event.astype(int)
    hz = np.array(s4.HORIZONS, float)

    def arm(noise: float, bias: float = 1.0) -> s4.Arm:
        e = rng.normal(0.0, noise, n)
        cum = np.clip((1.0 - np.exp(-lam[:, None] * hz[None, :])) * np.exp(e)[:, None] * bias, 1e-6, 1 - 1e-6)
        return s4.Arm(cum=cum, risk={k: cum[:, s4.HORIZONS.index(k)] for k in s4.DECILE_HORIZONS})

    return time, event, cause, arm(0.15), arm(0.15, 3.0 if worse else 1.0)


def _planted_interval(seed: int, worse: bool = False) -> dict:
    time, event, cause, a, b = _planted(4000, seed, worse)
    return s4.compare(time, event, cause, 40.0, {"pch": a, "cox": b}, seed=11, replicates=REPLICATES)


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_two_rungs_that_differ_by_noise_only_give_intervals_that_cover_zero(seed: int) -> None:
    out = _planted_interval(seed)
    for key in ("integrated_brier", "mean_decile_gap"):
        d = out[key]
        assert d["lo"] < 0 < d["hi"] and d["excludes_zero"] is False, (seed, key, d)


def test_a_rung_that_is_clearly_worse_gives_an_interval_that_excludes_zero() -> None:
    out = _planted_interval(1, worse=True)
    assert out["mean_decile_gap"]["excludes_zero"] is True and out["mean_decile_gap"]["hi"] < 0   # pch (first) is better than cox
    assert out["integrated_brier"]["excludes_zero"] is True and out["integrated_brier"]["hi"] < 0


def test_adversarial_a_different_seed_moves_the_interval_and_noise_covers_zero() -> None:
    time, event, cause, a, b = _planted(3000, 5)
    one = s4.compare(time, event, cause, 40.0, {"pch": a, "cox": b}, seed=1, replicates=REPLICATES)
    again = s4.compare(time, event, cause, 40.0, {"pch": a, "cox": b}, seed=1, replicates=REPLICATES)
    two = s4.compare(time, event, cause, 40.0, {"pch": a, "cox": b}, seed=2, replicates=REPLICATES)
    assert one == again
    assert one["mean_decile_gap"]["lo"] != two["mean_decile_gap"]["lo"] and one["integrated_brier"]["hi"] != two["integrated_brier"]["hi"]
    assert one["mean_decile_gap"]["difference"] == two["mean_decile_gap"]["difference"]  # the point does not depend on the seed


# ---------------------------------------------------------------------------------------------------------------------
# the real estimators: the identity replicate is the point statistics of s4_evaluation


def _context(tables, variant):
    run = variant.run
    follow = bt.follow_up(tables["loans"], run)
    life = bt.lifetime_results(tables["loans"], run, follow)
    ev = bt.s4_evaluation(run, follow, life)
    return run, follow, life, ev


def test_the_identity_replicate_reproduces_the_point_statistics_and_the_intervals_follow_the_seed(tables, variant) -> None:
    run, follow, life, ev = _context(tables, variant)
    assert ev is not None
    inputs = s4.inputs_from_run(run, follow)
    point = s4.point_statistics(inputs)
    s = ev.summary
    assert point["pch"]["integrated_brier"] == pytest.approx(s["integrated_brier"]["pch"], abs=1e-12)
    assert point["cox"]["integrated_brier"] == pytest.approx(s["integrated_brier"]["cox"], abs=1e-12)
    assert point["pch"]["mean_decile_gap"] == pytest.approx(s["mean_abs_decile_gap_aalen_johansen"]["pch_mean"], abs=1e-12)
    assert point["cox"]["mean_decile_gap"] == pytest.approx(s["mean_abs_decile_gap_aalen_johansen"]["cox_mean"], abs=1e-12)
    a = s4.s4_bootstrap(run, follow, ev, seed=42, replicates=REPLICATES)
    b = s4.s4_bootstrap(run, follow, ev, seed=42, replicates=REPLICATES)
    c = s4.s4_bootstrap(run, follow, ev, seed=43, replicates=REPLICATES)
    assert a == b and a != c
    assert a["seed"] == 42 and a["replicates"] == REPLICATES and a["level"] == 0.95
    diffs = {d["measure"]: d for d in a["differences"]}
    assert diffs["integrated_brier"]["difference"] == pytest.approx(s["integrated_brier"]["pch"] - s["integrated_brier"]["cox"], abs=1e-12)
    assert diffs["mean_decile_gap"]["difference"] == pytest.approx(
        s["mean_abs_decile_gap_aalen_johansen"]["pch_mean"] - s["mean_abs_decile_gap_aalen_johansen"]["cox_mean"], abs=1e-12)


def test_the_brier_score_of_every_replicate_is_the_engines(tables, variant, monkeypatch) -> None:
    """No statistic the engine provides is computed in the product: the integrated Brier score of each replicate is read from the
    engine's ``lifetime_pd_backtest`` (twice per replicate, once per rung, and twice for the point)."""
    run, follow, life, ev = _context(tables, variant)
    from riskvalidation.validation import ifrs9

    calls = []
    real = ifrs9.lifetime_pd_backtest

    def spy(*a, **k):
        calls.append(1)
        return real(*a, **k)

    monkeypatch.setattr(s4.rv_ifrs9, "lifetime_pd_backtest", spy)
    s4.s4_bootstrap(run, follow, ev, seed=1, replicates=5)
    assert len(calls) == 2 * (5 + 1)


def test_the_bootstrap_resamples_accounts_and_never_refits(tables, variant, monkeypatch) -> None:
    run, follow, life, ev = _context(tables, variant)
    ladder = run.ladder

    def boom(*a, **k):
        raise AssertionError("the ladder was asked to fit or predict again inside the replicates")

    inputs = s4.inputs_from_run(run, follow)
    for name in ("fit_ladder",):
        monkeypatch.setattr("pipeline.cases.c06.ladder." + name, boom, raising=False)
    monkeypatch.setattr(type(ladder.cox), "cumulative", boom)
    monkeypatch.setattr(type(ladder.pch), "cumulative", boom)
    out = s4.replicate_statistics(inputs, seed=3, replicates=4)       # the predictions are in ``inputs``: nothing is predicted again
    assert len(out["pch"]["integrated_brier"]) == 4 and inputs.n == int((run.horizon_q >= 12).sum())
    draws = list(bs.draws(inputs.n, 2, 3))
    assert all(d.shape == (inputs.n,) for d in draws)       # accounts, not rows of an aggregate (deciles or horizons)


# ---------------------------------------------------------------------------------------------------------------------
# the documents of the sample bake


def _fits(sample_bake, which="a"):
    root, manifest = sample_bake[which]
    out = {}
    for a in manifest["artifacts"]:
        if a["role"] == "models":
            d = json.loads((root / a["path"]).read_text(encoding="utf-8"))
            out[a["variant_id"]] = d
    return out


def test_every_date_carries_both_intervals_or_a_null_with_its_reason(sample_bake) -> None:
    fits = _fits(sample_bake)
    assert fits
    for vid, doc in fits.items():
        blk = doc["fit"]["s4_bootstrap"]
        assert blk["replicates"] == bs.REPLICATES and blk["level"] == 0.95 and blk["seed"] == 42
        assert blk["resampled_unit"] == "account" and blk["predictions_refit"] is False
        assert blk["method"]["en"] and blk["method"]["es"]
        assert [d["measure"] for d in blk["differences"]] == ["integrated_brier", "mean_decile_gap"]
        for d in blk["differences"]:
            if blk["evaluated"] and d["difference"] is not None:
                assert d["lo"] is not None and d["hi"] is not None and d["lo"] <= d["hi"], vid
                assert d["n_valid"] == bs.REPLICATES and d["excludes_zero"] == (d["hi"] < 0 or d["lo"] > 0)
                assert d["reason"] is None
            else:
                assert d["lo"] is None and d["hi"] is None and d["excludes_zero"] is None and d["reason"]["en"] and d["reason"]["es"], vid


def test_the_bootstrap_is_reproducible_across_two_bakes(sample_bake) -> None:
    a, b = _fits(sample_bake, "a"), _fits(sample_bake, "b")
    for vid in a:
        assert a[vid]["fit"]["s4_bootstrap"] == b[vid]["fit"]["s4_bootstrap"]


def test_the_verdict_is_the_preregistered_rule_and_the_count_of_intervals_excluding_zero_is_stated(sample_bake) -> None:
    fits = _fits(sample_bake)
    holds, both = [], []
    for vid, doc in fits.items():
        pch = next(m for m in doc["model"] if m["id"] == "L3-pch")["details"].get("evaluation")
        blk = doc["fit"]["s4_bootstrap"]
        if pch is None:
            holds.append(None)
            both.append(None)
            assert blk["evaluated"] is False and blk["reason"]["en"]
            continue
        c = pch["criteria"]
        # the rule of S4_HYPOTHESIS: both of its two criteria, from the point numbers, never from an interval
        expect = None if None in (c["lower_integrated_brier"], c["smaller_decile_gap"]) else bool(c["lower_integrated_brier"] and c["smaller_decile_gap"])
        assert pch["holds_at_date"] is expect
        assert pch["integrated_brier"]["pch"] < pch["integrated_brier"]["cox"] if c["lower_integrated_brier"] else True
        assert "bootstrap" not in pch and set(pch) >= {"criteria", "holds_at_date", "hypothesis"}
        holds.append(pch["holds_at_date"])
        both.append(blk["both_exclude_zero"])
    overall = next(iter(fits.values()))["fit"]["s4_bootstrap"]["overall"]
    v = bt.s4_verdict(holds)
    assert overall["dates"] == len(holds) and overall["evaluable"] == v["evaluable"] and overall["holds_at"] == v["holds_at"]
    assert overall["verdict"] == v["verdict"]
    assert overall["holds_excluding_zero"] == sum(1 for h, b in zip(holds, both, strict=True) if h and b)
    assert all(d["fit"]["s4_bootstrap"]["overall"] == overall for d in fits.values())


def test_the_case_page_prints_each_interval_beside_its_difference_and_the_count(sample_bake) -> None:
    root, _ = sample_bake["a"]
    block = page.pch_block(root)
    assert "95% interval" in block and "excludes zero" in block.lower()
    assert "Brier" in block and "decile gap" in block.lower()
    fits = _fits(sample_bake)
    overall = next(iter(fits.values()))["fit"]["s4_bootstrap"]["overall"]
    assert f"{overall['holds_excluding_zero']} of the {overall['holds_at']} dates" in block
    assert f"{bs.REPLICATES:,} replicates" in block or f"{bs.REPLICATES} replicates" in block


def test_adversarial_too_few_defaults_or_an_unfitted_rung_give_a_null_interval_with_its_reason(tables, variant) -> None:
    run, follow, life, ev = _context(tables, variant)
    few = dataclasses.replace(follow, event=np.zeros_like(follow.event), cause=np.zeros_like(follow.cause))
    blk = s4.s4_bootstrap(run, few, ev, seed=1, replicates=5)
    assert blk["evaluated"] is False and f"{bs.MIN_EVENTS}" in blk["reason"]["en"] and blk["reason"]["es"]
    assert all(d["lo"] is None and d["hi"] is None and d["difference"] is None and d["reason"] for d in blk["differences"])
    none = s4.s4_bootstrap(run, follow, None, seed=1, replicates=5)
    assert none["evaluated"] is False and "PC-Hazard" in none["reason"]["en"] and none["accounts"] is None
    assert all(d["lo"] is None and d["reason"] for d in none["differences"])


def test_adversarial_a_count_that_disagrees_with_the_dates_is_found() -> None:
    def blk(excl, evaluated=True):
        return {"evaluated": evaluated, "both_exclude_zero": excl}

    holds = [True, True, False, None]
    blocks = [blk(True), blk(False), blk(True), blk(None, False)]
    ok = s4.overall(holds, blocks)
    assert ok == {"dates": 4, "evaluable": 3, "holds_at": 2, "holds_excluding_zero": 1, "verdict": "holds"}
    assert s4.overall_findings(ok, holds, blocks) == []
    bad = dict(ok, holds_excluding_zero=2)
    assert s4.overall_findings(bad, holds, blocks) != []
    assert s4.overall_findings(dict(ok, verdict="refuted"), holds, blocks) != []
    assert s4.overall_findings(ok, [True, True, False, True], blocks) != []


def test_the_s4_hypothesis_and_its_verdict_rule_are_unchanged() -> None:
    """The verdict is the pre-registered rule: the bootstrap adds a block beside it and touches neither (the hash pins the text)."""
    import hashlib
    import inspect

    text = json.dumps(bt.S4_HYPOTHESIS, sort_keys=True) + inspect.getsource(bt.s4_verdict)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == PREREGISTERED_SHA256


# the SHA-256 of ``S4_HYPOTHESIS`` (sorted JSON) followed by the source of ``s4_verdict`` as committed before this unit (1.01.000 M1)
PREREGISTERED_SHA256 = "63d33f7436bbcbd4d50e5a47f7bc82a026f3190850e286d5abc22e41242b6816"
