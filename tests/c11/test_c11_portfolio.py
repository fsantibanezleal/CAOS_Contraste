"""CT-603: the six windows, their dates (D2), the portfolios (D4) and the returns of a book."""
from __future__ import annotations

import numpy as np

from pipeline.cases.c11 import constants as K
from pipeline.cases.c11 import portfolio as pf
from producer_checks import D1_SPAN, D2_DATES, WINDOWS, window_violations


def test_the_six_windows_are_the_contract_dates():
    assert [w.window_id for w in K.WINDOWS] == WINDOWS
    for w in K.WINDOWS:
        assert (w.start, w.end) == D2_DATES[w.window_id]
    assert K.SPAN == D1_SPAN


def test_the_hyperparameter_span_ends_before_the_earliest_window():
    assert K.SPAN[1] < min(w.start for w in K.WINDOWS) and K.SPAN == ("1995-01-01", "2003-12-31")


def test_portfolios_follow_decision_d4():
    assert K.PORTFOLIO_OF["mixed"] == K.MIXED_WEIGHTS and abs(sum(K.MIXED_WEIGHTS.values()) - 1.0) < 1e-12
    calm = next(w for w in K.WINDOWS if w.window_id == "calm-2004-06")
    mixed = next(w for w in K.WINDOWS if w.window_id == "mixed-2023")
    assert calm.asset_class == mixed.asset_class == "mixed"
    assert set(K.PORTFOLIO_OF["equity"]) == {"french-daily"} and set(K.PORTFOLIO_OF["rates"]) == {"treasury-par"}


def test_duration_of_a_par_bond_matches_a_numerical_derivative():
    def price(y: float) -> float:       # a 10-year bond with semiannual coupons at the par yield 5 percent
        return sum(0.025 / (1 + y / 2) ** (k + 1) for k in range(20)) + 1.0 / (1 + y / 2) ** 20

    h = 1e-5
    numeric = -(price(0.05 + h) - price(0.05 - h)) / (2 * h) / price(0.05)
    assert abs(float(pf.modified_duration_par(np.array([0.05]))[0]) - numeric) < 1e-4
    assert abs(float(pf.modified_duration_par(np.array([0.0]))[0]) - 10.0) < 1e-9


def test_portfolio_return_is_the_weighted_sum_of_components(series):
    p = pf.build("mixed-2023", series)
    assert p.derived_only and set(p.weights) == {"french-daily", "treasury-par", "h10-fx"}
    k = int(np.flatnonzero(p.dates >= np.datetime64("2023-03-01"))[0])
    d, prev = p.dates[k], p.dates[k - 1]
    fr, ty, eu = (series[i] for i in ("french-daily", "treasury-par", "h10-fx"))
    lev = np.cumprod(1.0 + fr.values)
    r_eq = lev[np.searchsorted(fr.dates, d)] / lev[np.searchsorted(fr.dates, prev)] - 1.0
    y1, y0 = ty.values[np.searchsorted(ty.dates, d)], ty.values[np.searchsorted(ty.dates, prev)]
    r_rt = -float(pf.modified_duration_par(np.array([y0]))[0]) * (y1 - y0)
    r_fx = eu.values[np.searchsorted(eu.dates, d)] / eu.values[np.searchsorted(eu.dates, prev)] - 1.0
    assert abs(p.returns[k] - (0.5 * r_eq + 0.3 * r_rt + 0.2 * r_fx)) < 1e-12
    single = pf.build("rates-2022", series)
    assert not single.derived_only and set(single.weights) == {"treasury-par"}


def test_adversarial_a_changed_window_date_is_refused():
    w = {"window_id": "rates-2022", "start_date": "2022-01-03", "end_date": "2022-12-30"}
    assert window_violations(w) == []
    w["start_date"] = "2022-01-04"
    assert window_violations(w) != []
