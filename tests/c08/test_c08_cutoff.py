"""CT-904 and CT-905: no look-ahead by default date, and the open workouts at the cutoff."""
from __future__ import annotations

import numpy as np
from c08_helpers import lookahead_findings, open_workout_findings

from pipeline.cases.c08 import cutoff as C
from pipeline.cases.c08 import panel
from pipeline.cases.c08.ladder import fit_ladder

CUTOFF = "2008-12-31"


def _perturbed(d: panel.Defaults, cutoff: str) -> panel.Defaults:
    """Every default charged off on or after the cutoff gets another outcome, another size and another term."""
    late = ~C.training_mask(d, cutoff)
    rng = np.random.default_rng(11)
    amount = np.where(late, d.chargeoff_amount * rng.uniform(0.2, 3.0, d.n), d.chargeoff_amount)
    gross = np.where(late, d.gross_approval * rng.uniform(0.5, 2.0, d.n), d.gross_approval)
    term = np.where(late, np.maximum(d.term // 2, 6), d.term)
    share = np.where(late, rng.uniform(0.2, 1.0, d.n), d.guaranteed_share)
    return panel.Defaults(chargeoff_date=d.chargeoff_date, approval_date=d.approval_date, year=d.year, gross_approval=gross,
                          chargeoff_amount=amount, term=term, revolver=d.revolver, sector=d.sector, guaranteed_share=share,
                          seasoning_share=d.seasoning_share, rate=d.rate)


def test_a_model_for_a_cutoff_ignores_every_default_after_it(tables):
    d = tables["defaults"]
    e = _perturbed(d, CUTOFF)
    assert not np.array_equal(d.chargeoff_amount, e.chargeoff_amount)
    a, b = d.take(C.training_mask(d, CUTOFF)), e.take(C.training_mask(e, CUTOFF))
    assert a.n == b.n > 500
    assert lookahead_findings(a.chargeoff_date, CUTOFF) == []
    la = fit_ladder(a.design(), a.y, CUTOFF, 7)
    lb = fit_ladder(b.design(), b.y, CUTOFF, 7)
    assert (la.n_fitted, la.n_out_of_range) == (lb.n_fitted, lb.n_out_of_range)
    probe = d.take(np.arange(d.n) % 7 == 0).design()
    n_eval = 0
    for rid, ra in la.rungs.items():
        rb = lb.rungs[rid]
        assert ra.evaluated == rb.evaluated and ra.reason == rb.reason
        if ra.evaluated:
            n_eval += 1
            assert np.array_equal(la.predict(ra, probe), lb.predict(rb, probe)), f"{rid} saw a default after the cutoff"
            if ra.fit is not None:
                assert np.array_equal(ra.fit.coefficients, rb.fit.coefficients)
    assert n_eval >= 4


def test_adversarial_a_default_after_the_cutoff_in_training_is_found(tables):
    d = tables["defaults"]
    train = d.take(C.training_mask(d, CUTOFF))
    assert lookahead_findings(train.chargeoff_date, CUTOFF) == []
    after = d.take(~C.training_mask(d, CUTOFF))
    planted = np.concatenate([train.chargeoff_date, after.chargeoff_date[:3]])
    assert lookahead_findings(planted, CUTOFF) == [f"3 training defaults charged off on or after {CUTOFF}"]
    on_cutoff = np.array([np.datetime64(CUTOFF)])
    assert lookahead_findings(on_cutoff, CUTOFF), "a close on the cutoff date is not before it"


def test_open_workouts_at_the_cutoff_are_excluded_and_counted(tables, docs):
    d = tables["defaults"]
    train = C.training_mask(d, CUTOFF)
    open_ = C.open_workout_mask(d, CUTOFF)
    assert open_.sum() > 0 and not (open_ & train).any(), "an open workout is never in the training set"
    dates = d.chargeoff_date[open_]
    assert dates.min() >= np.datetime64(CUTOFF) and dates.max() < np.datetime64("2009-12-31") + 1
    assert C.WORKOUT_WINDOW_MONTHS == 12 and C.cutoff_for(2009) == CUTOFF
    t = docs["variants"]["dc-2009-10"]["outputs"]["training"]
    assert t["cutoff_date"] == CUTOFF and t["n_defaults"] == int(train.sum()) and t["n_open_workouts_excluded"] == int(open_.sum())
    assert "12 months" in t["closure_rule"]["en"]
    assert docs["models"]["models-dc-2009-10"]["fit"]["training"] == t
    for vid, doc in docs["variants"].items():
        lo = doc["outputs"]["cohort"]["first_year"]
        cut = f"{lo - 1}-12-31"
        assert doc["outputs"]["training"]["cutoff_date"] == cut
        assert doc["outputs"]["training"]["n_open_workouts_excluded"] == int(C.open_workout_mask(d, cut).sum()), vid


def test_adversarial_an_open_workout_kept_in_training_is_found(tables):
    d = tables["defaults"]
    train = d.take(C.training_mask(d, CUTOFF))
    assert open_workout_findings(train.chargeoff_date, CUTOFF) == []
    open_dates = d.chargeoff_date[C.open_workout_mask(d, CUTOFF)]
    planted = np.concatenate([train.chargeoff_date, open_dates[:2]])
    assert open_workout_findings(planted, CUTOFF) == ["2 open workouts of the window kept in the training set"]
