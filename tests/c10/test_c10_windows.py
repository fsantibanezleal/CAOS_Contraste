"""CT-1103: the fit window is 1985-2006, the evaluation window 2007-2012, and no evaluation year enters the fit."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from pipeline.cases.c10 import documents as docs
from pipeline.cases.c10 import fed
from pipeline.cases.c10 import params as P


def test_the_fit_is_the_same_when_the_evaluation_years_change(table, built) -> None:
    assert (P.FIT["first_year"], P.FIT["last_year"], P.EVALUATION["first_year"], P.EVALUATION["last_year"]) == (1985, 2006, 2007, 2012)
    assert P.FIT["n_years"] == 22 and P.EVALUATION["n_years"] == 6
    shifted = {c: tuple(v if int(q[:4]) < 2007 else 7.5 for q, v in zip(table.quarters, vals, strict=True)) for c, vals in table.series.items()}
    other = dataclasses.replace(table, series=shifted)
    for lt in ("credit-cards", "commercial-industrial"):
        a = fed.annual_rates(table, lt, 1985, 2012)
        b = fed.annual_rates(other, lt, 1985, 2012)
        ra, rb = docs.fit_window_rates(a), docs.fit_window_rates(b)
        assert ra.size == 22 and np.array_equal(ra, rb, equal_nan=True)
        fa, fb = docs.fit_series(ra, 7, 100), docs.fit_series(rb, 7, 100)
        assert (fa.ml.pd, fa.ml.rho, fa.moments.rho, fa.ml_ci, fa.moments_ci) == (fb.ml.pd, fb.ml.rho, fb.moments.rho, fb.ml_ci, fb.moments_ci)
        assert [r.rate for r in a if r.year >= 2007] != [r.rate for r in b if r.year >= 2007]
    # in the documents: the years of the fit window are labelled fit, the others evaluation, and the count is the fit years with a rate
    for vid, doc in built["variants"].items():
        if vid.startswith("grid"):
            continue
        o = doc["outputs"]
        assert o["windows"]["fit"]["last_year"] < o["windows"]["evaluation"]["first_year"]
        assert {r["year"] for r in o["annual_rates"] if r["window"] == "fit"} == set(range(1985, 2007))
        assert o["fit"]["n_years_used"] == sum(1 for r in o["annual_rates"] if r["window"] == "fit" and r["loss_rate"] is not None)


def test_a_fit_input_with_an_evaluation_year_is_refused() -> None:
    docs.check_fit_input(range(1985, 2007))
    with pytest.raises(ValueError, match="evaluation"):
        docs.check_fit_input(range(1985, 2008))
