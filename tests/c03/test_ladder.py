"""CT-806: the rungs of the C03 ladder are the existing ones of C01, fitted on each training window."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from pipeline.cases.c03 import fit, panel, windows

RUNGS = {"P0-constant", "P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm"}


def test_the_ladder_fits_the_existing_rungs_and_names_their_kinds(tables, fit_2008):
    assert set(fit_2008.rungs) == RUNGS
    assert fit.RUNG_KINDS == {"P0-constant": "constant", "P1-scorecard": "woe-scorecard", "P2a-l1": "penalised-logit",
                              "P2b-pltr": "pltr", "P3-ebm": "ebm", "P4-lightgbm": "monotone-gbm"}
    probe = panel.features(tables["loans"], np.arange(0, tables["loans"].n, 5))
    for rid, rung in fit_2008.rungs.items():
        p = rung.pd(probe)
        assert len(p) == len(probe) and (p > 0).all() and (p < 1).all(), f"{rid}: a PD is open (0, 1)"
    assert fit_2008.not_evaluated == {"P5-tabpfn": fit.TABPFN_REASON}
    assert "not installed" in fit.TABPFN_REASON and "requirements-tabpfn.txt" in fit.TABPFN_REASON
    assert fit_2008.n_events > 0 and fit_2008.n_loans > fit_2008.n_events


def test_the_monotone_directions_are_declared_from_the_training_window_only(tables, fit_2008, cohort_2008):
    loans = tables["loans"]
    idx, y = fit.training_data(loans, windows.training_window(cohort_2008))
    x = panel.features(loans, idx)
    declared = fit.declared_directions(x, y)
    assert declared == fit_2008.monotone and set(declared) == set(panel.FEATURES)
    assert declared["sector"] == 0, "a categorical input has no direction"
    assert all(v in (-1, 0, 1) for v in declared.values())
    # a rule that reads only the window: the same inputs with the labels reversed flip every declared sign
    flipped = fit.declared_directions(x, 1 - y)
    assert all(flipped[k] == -declared[k] for k in declared)


def test_a_thin_window_is_reported_with_its_counts_and_not_fitted(tables, cohort_2008):
    window = windows.training_window(cohort_2008)
    thin = fit.fit_window(tables["loans"], window, 42, min_events=1_000_000)
    assert set(thin.rungs) == {"P0-constant"}
    for rid in RUNGS - {"P0-constant"}:
        reason = thin.not_evaluated[rid]
        assert str(thin.n_events) in reason and str(thin.n_loans - thin.n_events) in reason and "not fitted" in reason
    assert "P5-tabpfn" in thin.not_evaluated


def test_adversarial_a_window_without_events_is_refused(tables, cohort_2008):
    loans = tables["loans"]
    quiet = dataclasses.replace(loans, exit_kind=np.where(loans.exit_kind == panel.EXIT_DEFAULT, panel.EXIT_PAID, loans.exit_kind))
    with pytest.raises(ValueError, match="0 events"):
        fit.fit_window(quiet, windows.training_window(cohort_2008), 42)
