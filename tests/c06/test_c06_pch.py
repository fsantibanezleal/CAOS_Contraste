"""S-4 (method tiers plan, section 3): the L3 PC-Hazard rung of C06, a discrete-time neural survival model (Kvamme and Borgan 2019).

The acceptance criterion: calibration at 12, 24 and 36 months against Aalen-Johansen per decile, the c-index and the integrated
Brier score beside Cox, at the six reporting dates. These tests state the method on known truth (a piecewise-constant hazard the
network must recover, an Aalen-Johansen estimator checked by hand), the discipline (seeded, on what is known at the date) and the
documents the rung writes (models and variant).
"""
from __future__ import annotations

import dataclasses
import hashlib
import re

import numpy as np
import pytest

from pipeline.cases.c06 import ladder, macro, neural, panel
from pipeline.cases.c06 import backtest as bt


# ---------------------------------------------------------------------------------------------------------------------
# the interval statistics: the sufficient statistics of a piecewise-constant hazard


def test_interval_statistics_are_the_exact_events_and_exposure_of_each_interval() -> None:
    """Three loans of one stratum, width 3 months, 4 intervals: a default at 4.5 months, a loan observed to 7 months, a default
    at 1.0 month. Stratum 1 holds one loan observed to 12.5 months (past the 4 intervals: the last one is open)."""
    stratum = np.array([0, 0, 0, 1])
    time = np.array([4.5, 7.0, 1.0, 12.5])
    event = np.array([True, False, True, False])
    ev, ex = neural.interval_statistics(stratum, time, event, n_strata=2, n_intervals=4, width=3.0)
    assert ev.shape == ex.shape == (2, 4)
    assert ev[0].tolist() == [1.0, 1.0, 0.0, 0.0]
    # interval 0: 3 (loan a) + 3 (loan b) + 1.0 (loan c, which defaults in it); interval 1: 1.5 (a, defaults) + 3 (b); interval 2: 1.0 (b)
    assert ex[0].tolist() == [7.0, 4.5, 1.0, 0.0]
    assert ev[1].tolist() == [0.0, 0.0, 0.0, 0.0]
    # the open last interval takes all the exposure past its start: 3 + 3 + 3 + (12.5 - 9)
    assert ex[1].tolist() == [3.0, 3.0, 3.0, 3.5]


def test_total_exposure_is_total_observed_time() -> None:
    rng = np.random.default_rng(1)
    time = rng.uniform(0.5, 200.0, 5000)
    event = rng.random(5000) < 0.2
    stratum = rng.integers(0, 7, 5000)
    ev, ex = neural.interval_statistics(stratum, time, event, n_strata=7, n_intervals=60, width=3.0)
    assert ex.sum() == pytest.approx(time.sum(), rel=1e-12)
    assert ev.sum() == event.sum()


# ---------------------------------------------------------------------------------------------------------------------
# the conditional cumulative PD of a piecewise-constant hazard


def test_conditional_cumulative_pd_is_the_exact_piecewise_integral() -> None:
    rates = np.array([[0.01, 0.02]])    # per month, 3-month intervals, the second one open
    s = np.array([0, 0, 0])
    age = np.array([0.0, 2.0, 0.0])
    horizon = np.array([[6.0], [3.0], [12.0]])
    got = neural.conditional_cumulative_pd(rates, s, age, horizon[:, 0][:, None], width=3.0)
    h = [0.03 + 0.03 * 2, (0.03 + 2 * 0.02) - 0.02, 0.03 + 0.02 * 9]
    assert got[:, 0] == pytest.approx(1.0 - np.exp(-np.array(h)))


def test_the_curve_is_monotone_in_the_horizon_and_a_probability() -> None:
    rng = np.random.default_rng(3)
    rates = rng.uniform(1e-4, 0.02, (5, 60))
    s = rng.integers(0, 5, 200)
    age = rng.uniform(0, 170, 200)
    hz = np.array([6.0, 12.0, 18.0, 24.0, 30.0, 36.0])
    f = neural.conditional_cumulative_pd(rates, s, age, np.broadcast_to(hz, (200, 6)), width=3.0)
    assert ((f > 0) & (f < 1)).all() and (np.diff(f, axis=1) > 0).all()


# ---------------------------------------------------------------------------------------------------------------------
# the network recovers a known hazard


def _poisson_stats(rates: np.ndarray, exposure: np.ndarray, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).poisson(rates * exposure).astype(float)


def test_the_network_recovers_a_known_piecewise_constant_hazard() -> None:
    """Two strata whose hazards differ by a factor that changes with age (non-proportional): the network, which has no
    proportional-hazards constraint, must recover both curves from Poisson counts."""
    m = 10
    age = np.arange(m)
    truth = np.vstack([0.004 + 0.002 * np.sin(age / 3.0) ** 2, 0.012 * np.exp(-age / 8.0) + 0.002])
    exposure = np.full((2, m), 4.0e5)
    x = np.eye(2)
    fit = neural.fit_network(x, _poisson_stats(truth, exposure, 11), exposure, val_events=_poisson_stats(truth, exposure, 12),
                             val_exposure=exposure, seed=7)
    assert fit.rates.shape == (2, m)
    assert np.abs(fit.rates / truth - 1.0).max() < 0.08
    assert fit.best_epoch >= 1 and fit.n_parameters > 0
    assert re.fullmatch(r"[0-9a-f]{64}", fit.weights_sha256)


def test_the_fit_is_seeded() -> None:
    m = 6
    truth = np.full((3, m), 0.005) * np.array([[1.0], [2.0], [3.0]])
    exposure = np.full((3, m), 1.0e5)
    ev, vev = _poisson_stats(truth, exposure, 1), _poisson_stats(truth, exposure, 2)
    a = neural.fit_network(np.eye(3), ev, exposure, val_events=vev, val_exposure=exposure, seed=5)
    b = neural.fit_network(np.eye(3), ev, exposure, val_events=vev, val_exposure=exposure, seed=5)
    c = neural.fit_network(np.eye(3), ev, exposure, val_events=vev, val_exposure=exposure, seed=6)
    assert a.weights_sha256 == b.weights_sha256 and np.array_equal(a.rates, b.rates)
    assert a.weights_sha256 != c.weights_sha256


def test_early_stopping_reads_the_validation_loss_not_the_training_one() -> None:
    """A tiny training set the network can memorise: the best epoch is the one of the lowest validation loss, before the end."""
    rng = np.random.default_rng(0)
    m = 8
    truth = np.full((4, m), 0.01)
    exposure = np.full((4, m), 300.0)
    ev = rng.poisson(truth * exposure).astype(float)
    vev = rng.poisson(truth * exposure).astype(float)
    fit = neural.fit_network(np.eye(4), ev, exposure, val_events=vev, val_exposure=exposure, seed=3, max_epochs=600, patience=25)
    assert fit.best_epoch < fit.epochs
    assert fit.val_nll <= fit.val_nll_curve.max()
    assert fit.val_nll == pytest.approx(fit.val_nll_curve.min())


# ---------------------------------------------------------------------------------------------------------------------
# Aalen-Johansen, the observed side of the calibration


def test_aalen_johansen_matches_the_hand_computation() -> None:
    time = np.array([1.0, 2.0, 3.0, 4.0])
    cause = np.array([1, 2, 0, 1])
    got = neural.aalen_johansen(time, cause, np.array([0.5, 1.0, 2.0, 3.0, 4.0]), target=1)
    assert got == pytest.approx([0.0, 0.25, 0.25, 0.25, 0.75])
    other = neural.aalen_johansen(time, cause, np.array([2.0, 4.0]), target=2)
    assert other == pytest.approx([0.25, 0.25])


def test_aalen_johansen_without_a_competing_cause_is_kaplan_meier() -> None:
    from statsmodels.duration.survfunc import SurvfuncRight

    rng = np.random.default_rng(4)
    time = rng.exponential(30.0, 3000)
    cens = rng.exponential(60.0, 3000)
    t = np.minimum(time, cens)
    cause = (time <= cens).astype(int)
    hz = np.array([6.0, 12.0, 24.0, 36.0])
    sf = SurvfuncRight(t, cause)
    times, surv = np.asarray(sf.surv_times), np.asarray(sf.surv_prob)
    km = np.array([1.0 - surv[np.searchsorted(times, h, side="right") - 1] for h in hz])
    assert neural.aalen_johansen(t, cause, hz, target=1) == pytest.approx(km, abs=1e-12)


def test_the_incidences_and_the_survival_add_up_to_one() -> None:
    rng = np.random.default_rng(8)
    t = rng.exponential(20.0, 4000)
    cause = rng.choice([0, 1, 2], 4000, p=[0.3, 0.3, 0.4])
    hz = np.array([5.0, 20.0, 50.0])
    s = 1.0 - neural.aalen_johansen(t, cause, hz, target=1) - neural.aalen_johansen(t, cause, hz, target=2)
    assert (s > 0).all() and (np.diff(s) < 0).all()


# ---------------------------------------------------------------------------------------------------------------------
# the rung on the loans: what is known at the reporting date, nothing after


def _fit(tables, date: str, loans=None):
    loans = tables["loans"] if loans is None else loans
    r = np.datetime64(date)
    obs = panel.observe(loans, r)
    return obs, neural.fit_pch(loans, obs, reporting_date=r)


def test_the_rung_fits_on_the_sample_and_says_what_it_stands_on(tables) -> None:
    obs, pch = _fit(tables, "2010-12-31")
    assert pch.status.evaluated and pch.status.n_loans == int(obs.selected.sum()) and pch.status.n_events == int(obs.event.sum())
    assert pch.rates.shape == (panel.N_STRATA, neural.N_INTERVALS) and (pch.rates > 0).all()
    assert pch.n_train_loans + pch.n_val_loans == pch.status.n_loans and pch.n_val_loans > 0
    age = np.array([0.0, 12.0, 36.0])
    c = pch.cumulative(np.array([0, 1, 2]), age, np.array([12.0, 36.0]))
    assert ((c > 0) & (c < 1)).all() and (np.diff(c, axis=1) > 0).all()


def test_the_fit_reads_nothing_after_the_reporting_date(tables) -> None:
    """Every default after the date turned into a payment and every exit date moved: the fit at the date is identical."""
    loans = tables["loans"]
    r = np.datetime64("2010-12-31")
    after = loans.exit_date > r
    future = dataclasses.replace(loans, exit_kind=np.where(after, panel.EXIT_PAID, loans.exit_kind),
                                 exit_date=np.where(after, r + np.timedelta64(3000, "D"), loans.exit_date))
    _, a = _fit(tables, "2010-12-31")
    _, b = _fit(tables, "2010-12-31", future)
    assert a.weights_sha256 == b.weights_sha256 and np.array_equal(a.rates, b.rates)


def test_a_thin_vintage_is_not_fitted_and_says_why(tables) -> None:
    obs, pch = _fit(tables, "1991-06-30")
    n = int(obs.selected.sum())
    assert not pch.status.evaluated and pch.status.n_loans == n
    assert f"{n} loans" in pch.status.reason and "L3-pch" in pch.status.reason
    assert pch.rates.size == 0 and pch.weights_sha256 is None


def test_the_ladder_carries_the_fourth_rung(tables) -> None:
    r = np.datetime64("2010-12-31")
    obs = panel.observe(tables["loans"], r)
    lad = ladder.fit_ladder(tables["loans"], obs, macro.history_known(tables["fed"], r))
    assert lad.pch.status.evaluated


# ---------------------------------------------------------------------------------------------------------------------
# the follow-up and the documents


def test_the_follow_up_names_the_cause_of_each_exit(variant, tables) -> None:
    follow = bt.follow_up(tables["loans"], variant.run)
    assert set(np.unique(follow.cause).tolist()) <= {0, 1, 2}
    assert ((follow.cause == 1) == follow.event).all()
    assert (follow.cause == 2).sum() > 0 and (follow.cause == 0).sum() > 0


def test_the_models_document_carries_the_rung_with_its_weights_hash(variant) -> None:
    rungs = {m["id"]: m for m in variant.document["model"]}
    assert set(rungs) == {"L0-km", "L1-dth", "L2-cox", "L3-pch"}
    rec = {m["id"]: m for m in variant.models["model"]}["L3-pch"]
    assert rec["engine"] == "torch" and rec["rung"] == "piecewise-constant-hazard-network"
    assert re.fullmatch(r"[0-9a-f]{64}", rec["checkpoint_sha256"])
    assert rec["short_title"] == {"en": "L3 PC-Hazard", "es": "L3 PC-Hazard"}
    assert rec["details"]["evaluated"] is True and rec["details"]["seed"] > 0
    lad = {r["rung_id"]: r for r in variant.models["fit"]["ladder"]}
    assert lad["L3-pch"]["kind"] == "piecewise-constant-hazard-network" and lad["L3-pch"]["baseline"]["months"]


def test_the_rung_comparison_has_the_new_rung_beside_cox(variant) -> None:
    cmp = {r["rung_id"]: r for r in variant.document["outputs"]["rung_comparison"]}
    assert list(cmp) == ["L0-km", "L1-dth", "L2-cox", "L3-pch"]
    for rung in ("L2-cox", "L3-pch"):
        assert 0.5 < cmp[rung]["c_index"] < 1.0 and 0.0 < cmp[rung]["integrated_brier"] < 0.25
    assert any(t["model_id"] == "L3-pch" and t["test_id"] == "ifrs9.lifetime_pd_backtest" for t in variant.document["tests"])


def test_the_evaluation_is_calibration_by_decile_against_aalen_johansen(variant) -> None:
    rec = {m["id"]: m for m in variant.models["model"]}
    for rung in ("L2-cox", "L3-pch"):
        rows = rec[rung]["details"]["decile_calibration"]
        assert {r["months"] for r in rows} == {12, 24, 36} and {r["decile"] for r in rows} == set(range(1, 11))
        assert len(rows) == 30
        ok = [r for r in rows if r["reason"] is None]
        assert ok, rung
        for r in ok:
            assert 0 < r["predicted_cumulative_pd"] < 1
            assert 0 <= r["observed_kaplan_meier"] <= 1 and 0 <= r["observed_aalen_johansen"] <= 1
            # the incidence with a competing cause never exceeds the cause-specific Kaplan-Meier cumulative incidence
            assert r["observed_aalen_johansen"] <= r["observed_kaplan_meier"] + 1e-9
            assert r["gap_aalen_johansen"] == pytest.approx(r["predicted_cumulative_pd"] - r["observed_aalen_johansen"])
    ev = rec["L3-pch"]["details"]["evaluation"]
    assert ev["comparator"] == "L2-cox"
    for key in ("lower_integrated_brier", "smaller_decile_gap", "higher_c_index"):
        assert ev["criteria"][key] in (True, False, None)
    assert ev["mean_abs_decile_gap_aalen_johansen"]["months"] and set(ev["mean_abs_decile_gap_aalen_johansen"]) >= {"pch", "cox", "months"}
    assert ev["hypothesis"]["en"] and ev["hypothesis"]["es"]


def test_the_documents_name_the_method_in_both_languages(variant) -> None:
    rec = {m["id"]: m for m in variant.models["model"]}["L3-pch"]
    assert "PC-Hazard" in rec["title"]["en"] and "PC-Hazard" in rec["title"]["es"]
    assert rec["title"]["en"] != rec["title"]["es"]
    h = rec["details"]["evaluation"]["hypothesis"]
    assert h["en"] != h["es"] and "Cox" in h["en"] and "Cox" in h["es"]


def test_the_checkpoint_hash_is_of_the_trained_weights(tables) -> None:
    _, pch = _fit(tables, "2010-12-31")
    assert pch.weights_sha256 != hashlib.sha256(b"").hexdigest()


# ---------------------------------------------------------------------------------------------------------------------
# the verdict: reported whatever the result


def test_the_verdict_counts_only_the_evaluable_dates_and_a_tie_is_a_refutation() -> None:
    assert bt.s4_verdict([True, True, False, None])["verdict"] == "holds"
    assert bt.s4_verdict([True, False, None, None]) == {"dates": 4, "evaluable": 2, "holds_at": 1, "verdict": "refuted"}
    assert bt.s4_verdict([False, False, False, False, False, False])["verdict"] == "refuted"
    assert bt.s4_verdict([None, None])["verdict"] is None


def test_the_case_page_carries_the_committed_s4_result() -> None:
    """The S-4 block of docs/cases/C06.md is generated from the committed models documents, the verdict included."""
    from pathlib import Path

    from pipeline.cases.c06 import page

    root = Path(__file__).resolve().parents[2]
    text = (root / "docs" / "cases" / "C06.md").read_text(encoding="utf-8")
    assert text.count(page.PCH_START) == 1 and text.count(page.PCH_END) == 1
    block = text.split(page.PCH_START, 1)[1].split(page.PCH_END, 1)[0].strip("\n")
    assert block == page.pch_block(root / "data" / "derived").strip("\n"), "regenerate it: python data-pipeline/pipeline/cases/c06/page.py"
    assert "**Verdict.**" in block and "evaluable reporting dates" in block


def test_the_committed_documents_hold_the_rung_at_every_reporting_date() -> None:
    """Six dates, each with the PC-Hazard record, its weights hash and its decile cells (the hypothesis is judged on these)."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "data" / "derived" / "C06"
    docs = sorted(root.glob("models-rd-*.json"))
    assert len(docs) == 6
    hashes = set()
    for p in docs:
        rec = next(m for m in json.loads(p.read_text(encoding="utf-8"))["model"] if m["id"] == "L3-pch")
        assert rec["details"]["evaluated"] is True and len(rec["details"]["decile_calibration"]) == 30, p.name
        assert rec["details"]["evaluation"]["follow_up_months"] > 0
        hashes.add(rec["checkpoint_sha256"])
    assert len(hashes) == 6, "six dates, six different trained networks"
