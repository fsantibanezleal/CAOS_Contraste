"""CT-1806 and CT-1807: the satellites, fitted on 1985 to 2019 and back-cast out of time."""
from __future__ import annotations

import numpy as np
import pytest
from c18_support import data_root, requires_raw

from pipeline.cases.c18 import fed
from pipeline.cases.c18 import params as P
from pipeline.cases.c18 import satellites as sat

pytestmark = requires_raw


@pytest.fixture(scope="module")
def sats():
    f = fed.read_inputs(data_root())
    return sat.fit_all(fed.read_chargeoffs(data_root()), f)


def test_satellite_windows_end_in_2019_and_the_links_follow_the_signs(sats) -> None:
    assert P.FIT_END == "2019-12-31"
    for lt, s in sats.items():
        assert s.fit.window_end == "2019-12-31"
        want_link, first = P.FED_TYPES[lt][1], P.FED_TYPES[lt][2]
        assert (s.fit.link, s.fit.window_start) == (want_link, first)
        if want_link == "probit":
            assert s.non_positive == 0
    assert sats["residential"].fit.link == sats["commercial-real-estate"].fit.link == "identity"
    assert (sats["residential"].non_positive, sats["commercial-real-estate"].non_positive) == (6, 13)
    r = sat.record(sats["residential"])
    assert r["sample_window"] == {"start": "1991-03-31", "end": "2019-12-31"} and r["n_obs"] == 115 and r["link"] == "identity"
    assert sat.record(sats["credit-cards"])["n_obs"] == 139
    # the independent reference of the SDD oracles (item 5): the same design solved by numpy.linalg.lstsq
    s = sats["commercial-industrial"]
    qs = list(s.quarters)
    i0, i1 = qs.index("1985-03-31"), qs.index("2019-12-31")
    from scipy.special import ndtri

    g = ndtri(s.rates[i0:i1 + 1])
    x = s.x[i0:i1 + 1]
    rows = np.arange(1, g.size)
    design = np.column_stack([np.ones(rows.size), g[rows - 1], x[rows, 0], x[rows - 1, 0], x[rows, 1], x[rows - 1, 1]])
    beta = np.linalg.lstsq(design, g[rows], rcond=None)[0]
    assert np.allclose(beta, s.fit.estimates, atol=1e-9)


def test_backcast_is_out_of_time_and_2026_is_descriptive(sats) -> None:
    rates = fed.read_chargeoffs(data_root())
    for lt, s in sats.items():
        b = sat.backcast(s)
        qs = [q["quarter_end"] for q in b["quarters"]]
        assert qs[0] == "2020-03-31" and qs[-1] == "2025-12-31" and len(qs) == 24
        assert b["fit_window"]["end"] == "2019-12-31"
        assert b["_test"].test_id == "stress.satellite_backcast" and b["_test"].segment == lt
        real = [q["realised"] for q in b["quarters"]]
        assert real == [float(rates.rates[lt][rates.quarters.index(q)]) for q in qs]                 # the Board's rates, signed, unfilled
        assert b["metrics"]["peak_timing_error_quarters"] == qs.index(b["metrics"]["peak_predicted_quarter"]) - qs.index(b["metrics"]["peak_realised_quarter"])
    d = sat.descriptive_2026(rates)
    assert [r["quarter_end"] for r in d] == ["2026-03-31", "2026-06-30"]
    assert all(r["label"] == "rate-only-descriptive" and r["forecast_claim"] is False for r in d)
    assert d[0]["realised_rates"][0]["fed_loan_type"] == "commercial-industrial"
