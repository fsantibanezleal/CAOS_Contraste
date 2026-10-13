"""CT-804: a model for a test cohort sees nothing after the cutoff of its window (no look-ahead)."""
from __future__ import annotations

import dataclasses

import numpy as np

from pipeline.cases.c03 import fit, panel, windows

SEED = 42


def _perturbed(loans: panel.Loans, cutoff: np.datetime64) -> panel.Loans:
    """Every approval and every outcome after the cutoff changed: the loans approved later get other attributes and an
    outcome of the opposite kind, and the exits dated after the cutoff of a loan approved before it turn into other exits."""
    rng = np.random.default_rng(7)
    later = loans.approval > cutoff
    after = ~np.isnat(loans.exit_date) & (loans.exit_date > cutoff)
    kind = loans.exit_kind.copy()
    date = loans.exit_date.copy()
    kind[later] = np.where(kind[later] == panel.EXIT_DEFAULT, panel.EXIT_PAID, panel.EXIT_DEFAULT)
    flip = after & ~later
    kind[flip] = np.where(kind[flip] == panel.EXIT_DEFAULT, panel.EXIT_PAID, panel.EXIT_DEFAULT)
    date[flip] = date[flip] + rng.integers(1, 400, size=int(flip.sum())).astype("timedelta64[D]")
    return dataclasses.replace(
        loans, exit_kind=kind, exit_date=date, amount=np.where(later, loans.amount * 7.0, loans.amount),
        term=np.where(later, 12, loans.term), guarantee_share=np.where(later, 0.05, loans.guarantee_share),
        revolver=np.where(later, ~loans.revolver, loans.revolver))


def test_a_model_for_a_cohort_ignores_everything_after_its_cutoff(tables, cohort_2008, fit_2008):
    loans = tables["loans"]
    window = windows.training_window(cohort_2008)
    cutoff = np.datetime64(window.cutoff)
    other = _perturbed(loans, cutoff)
    assert (other.exit_kind != loans.exit_kind).sum() > 100, "the perturbation really changes outcomes after the cutoff"
    idx0, y0 = fit.training_data(loans, window)
    idx1, y1 = fit.training_data(other, window)
    assert np.array_equal(idx0, idx1) and np.array_equal(y0, y1), "the training labels do not move"
    assert (y0 >= 0).all(), "every loan of the window has a known outcome at the cutoff"
    again = fit.fit_window(other, window, SEED)
    assert again.monotone == fit_2008.monotone
    probe = panel.features(loans, np.arange(0, loans.n, 7))
    assert set(again.rungs) == set(fit_2008.rungs)
    for rid, rung in fit_2008.rungs.items():
        assert np.array_equal(rung.raw_pd(probe), again.rungs[rid].raw_pd(probe)), f"{rid} changed with data after the cutoff"
        assert np.array_equal(rung.pd(probe), again.rungs[rid].pd(probe))


def test_adversarial_a_leaky_window_changes_the_fitted_model(tables, cohort_2008):
    loans = tables["loans"]
    clean = windows.training_window(cohort_2008)
    leaky = windows.Window(clean.first_fy, clean.last_fy + 1, clean.cutoff)
    thin = {"min_events": 10**9}  # the constant rung alone: the comparison does not need the whole ladder
    a = fit.fit_window(loans, clean, SEED, **thin)
    b = fit.fit_window(loans, leaky, SEED, **thin)
    c = fit.fit_window(loans, clean, SEED, **thin)
    probe = panel.features(loans, np.arange(0, loans.n, 7))
    assert np.array_equal(a.rungs["P0-constant"].raw_pd(probe), c.rungs["P0-constant"].raw_pd(probe)), "the same window gives the same model"
    assert not np.array_equal(a.rungs["P0-constant"].raw_pd(probe), b.rungs["P0-constant"].raw_pd(probe))
    assert (a.n_loans, a.n_events) != (b.n_loans, b.n_events)
    idx_clean, _ = fit.training_data(loans, clean)
    idx_leaky, y_leaky = fit.training_data(loans, leaky)
    assert len(idx_leaky) > len(idx_clean), "the leaky window reads the vintage whose mark has not closed"
    assert (y_leaky == 1).sum() > (fit.training_data(loans, clean)[1] == 1).sum()


def test_adversarial_a_charge_off_after_the_cutoff_is_not_an_event_at_it(tables, cohort_2008):
    loans = tables["loans"]
    window = windows.training_window(cohort_2008)
    cutoff = np.datetime64(window.cutoff)
    y_at_cutoff = panel.label(loans, cutoff)
    y_later = panel.label(loans, np.datetime64("2026-06-30"))
    inside = loans.fy <= window.last_fy
    assert (y_at_cutoff[inside] == y_later[inside]).all(), "a window loan is fully observed at the cutoff"
    late = loans.fy > window.last_fy
    assert (y_at_cutoff[late] != y_later[late]).any(), "a later loan is not: it is censored or an event not yet seen"
    assert (y_at_cutoff[late & (loans.approval > cutoff)] == -1).all()
