"""C04's live parity points (CT-410, CT-411; contract section 4): what ``c04_parity.parity`` writes for the browser
ports to be held to, checked against direct engine calls and against Schuermann and Hanson's printed Table 5."""
from __future__ import annotations

import json

import numpy as np
import pytest

from pipeline.cases import c04_parity as par
from pipeline.cases.c05_ldp_calibration import IRB_ASSUMPTIONS, _irb_rw
from riskvalidation.transitions import intervals as iv
from riskvalidation.transitions import ttc

ORIGINATION = [0.0, 0.1, 0.3, 0.3, 0.2, 0.1, 0.0]


def _toy(default_scale: float = 1.0) -> np.ndarray:
    """Seven grades and default: most mass on the diagonal, one notch each way, a default probability rising with the
    grade (times ``default_scale``), rows summing to one."""
    p = np.zeros((8, 8))
    pd = default_scale * np.array([0.0001, 0.0003, 0.001, 0.003, 0.012, 0.05, 0.25])
    for i in range(7):
        up, down = (0.04 if i > 0 else 0.0), (0.06 if i < 6 else 0.0)
        p[i, i - 1] = up if i > 0 else 0.0
        if i < 6:
            p[i, i + 1] = down
        p[i, 7] = pd[i]
        p[i, i] = 1.0 - p[i].sum()
    p[7, 7] = 1.0
    return p


@pytest.fixture(scope="module")
def out() -> dict:
    return par.parity({"STPGB": _toy(), "FITGB": _toy(1.5)}, ORIGINATION)


def test_keys_and_plain_json(out):
    assert set(out) == {"projection", "intervals", "capital"}
    assert json.loads(json.dumps(out)) == out
    for row in out["projection"]:
        assert set(row) == {"agency", "matrix", "origination", "w0", "years", "default_rate", "portfolio_last", "ttc",
                            "ttc_default_rate"}
    for row in out["intervals"]:
        assert set(row) == {"defaults", "n", "rho", "level", "wald", "agresti_coull", "jeffreys", "n_effective"}
    for row in out["capital"]:
        assert set(row) == {"pd", "lgd", "maturity", "regime", "asset_class", "risk_weight"}


def test_projection_rows_are_the_engine(out):
    """Three starts per agency in the agencies' order (all in the best grade, the origination mix, uniform), each the
    engine's projection over 20 years and its TTC portfolio."""
    rows = out["projection"]
    assert [r["agency"] for r in rows] == ["STPGB"] * 3 + ["FITGB"] * 3
    o = ORIGINATION + [0.0]
    starts = [[1.0] + [0.0] * 7, o, [1 / 7] * 7 + [0.0]]
    for k, r in enumerate(rows):
        assert r["w0"] == pytest.approx(starts[k % 3], abs=0) and r["origination"] == o and r["years"] == par.YEARS
        t = np.asarray(r["matrix"])
        want = ttc.project(t, r["w0"], o, par.YEARS)
        assert r["default_rate"] == want["default_rate"].tolist() and len(r["default_rate"]) == par.YEARS
        assert r["portfolio_last"] == want["portfolio"][-1].tolist()
        assert sum(r["portfolio_last"]) == pytest.approx(1.0, abs=1e-12)
        assert r["ttc"] == want["ttc"]["portfolio"].tolist() and sum(r["ttc"]) == pytest.approx(1.0, abs=1e-12)
        # the TTC portfolio's default rate is its default column under the matrix, and the propagation leaves it
        assert r["ttc_default_rate"] == pytest.approx(float(np.asarray(r["ttc"]) @ t[:, -1]), rel=1e-12)
        fixed = ttc.ttc_portfolio(t, o)["portfolio"]
        assert np.allclose(fixed, r["ttc"], atol=1e-12)
    # the two agencies' matrices differ, and so do their TTC default rates
    assert rows[0]["ttc_default_rate"] < rows[3]["ttc_default_rate"]


def test_projection_refusals():
    """A scale without a default category (Moody's transition page) is refused, naming the agency; so is a matrix of
    the wrong shape, an origination of the wrong length, and an empty set of agencies."""
    moodys = _toy()
    moodys[:7, 6] += moodys[:7, 7]
    moodys[:7, 7] = 0.0
    with pytest.raises(ValueError, match="MDYGB: no grade reaches default"):
        par.parity({"MDYGB": moodys}, ORIGINATION)
    with pytest.raises(ValueError, match="not seven grades and default"):
        par.parity({"STPGB": _toy()[:7, :7]}, ORIGINATION)
    with pytest.raises(ValueError, match="not 7 grades"):
        par.parity({"STPGB": _toy()}, ORIGINATION[:5])
    with pytest.raises(ValueError, match="at least one"):
        par.parity({}, ORIGINATION)


def test_intervals_grid_and_table5(out):
    """The grid at 95% (every count within its size, four correlations), the web's other levels, CEREP's pooled
    sizes; Schuermann and Hanson's Table 5 (BB 2002, 15 defaults of 531) at its printed digits in basis points."""
    rows = out["intervals"]
    grid = sum(1 for n in par.INTERVAL_N for d in par.INTERVAL_DEFAULTS if d <= n) * len(par.INTERVAL_RHO)
    other = len(par.LEVELS_OTHER) * len(par.INTERVAL_OTHER) * len(par.INTERVAL_OTHER_RHO)
    pooled = len(par.LEVELS_POOLED) * len(par.INTERVAL_POOLED) * len(par.INTERVAL_POOLED_RHO)
    assert len(rows) == grid + other + pooled
    assert {r["level"] for r in rows} == {0.90, 0.95, 0.99}
    printed = {0.0: ((141.56, 423.41), (168.03, 464.71), 531.0), 0.01: ((0.00, 636.20), (38.25, 938.00), 84.3),
               0.02: ((0.00, 762.45), (0.00, 1332.56), 45.8)}
    for rho, (wald, ac, n_eff) in printed.items():
        r = next(x for x in rows if (x["defaults"], x["n"], x["rho"], x["level"]) == (15, 531, rho, 0.95))
        assert [round(1e4 * b, 2) for b in r["wald"]] == list(wald)
        assert [round(1e4 * b, 2) for b in r["agresti_coull"]] == list(ac)
        assert round(r["n_effective"], 1) == n_eff
    for r in rows:
        assert 0.0 <= r["wald"][0] <= r["wald"][1] <= 1.0 and 0.0 <= r["jeffreys"][0] <= r["jeffreys"][1] <= 1.0
        if r["defaults"] == 0:
            assert r["jeffreys"][0] == 0.0
        j = iv.pd_jeffreys(r["defaults"], r["n"], level=r["level"])
        assert r["jeffreys"] == [j["lower"], j["upper"]]
        w = iv.pd_wald(r["defaults"], r["n"], level=r["level"], rho=r["rho"])
        a = iv.pd_agresti_coull(r["defaults"], r["n"], level=r["level"], rho=r["rho"])
        assert r["wald"] == [w["lower"], w["upper"]] and r["agresti_coull"] == [a["lower"], a["upper"]]
        assert r["n_effective"] == w["n_effective"]


def test_capital_rows_share_c05_convention(out):
    """One IRB convention for the impact, the parity and the live capital (C05's); a PD of 0 takes the floor."""
    rows = out["capital"]
    assert [r["pd"] for r in rows] == list(par.CAPITAL_PD)
    for r in rows:
        assert (r["regime"], r["asset_class"], r["lgd"], r["maturity"]) == (
            IRB_ASSUMPTIONS["regime"], IRB_ASSUMPTIONS["asset_class"], IRB_ASSUMPTIONS["lgd"], IRB_ASSUMPTIONS["maturity"])
        assert r["risk_weight"] == float(_irb_rw(r["pd"]))
    at = {r["pd"]: r["risk_weight"] for r in rows}
    assert at[0.0] == at[0.0003] == at[0.0005] < at[0.001] < at[0.02]


def test_the_export_keeps_the_parity_exact(out):
    """The bake writes ``parity`` at full precision (an exact key): rounded to nine significant digits, the 1e-9
    comparison of the ports would measure the rounding."""
    from pipeline.cases import c04_transitions as c04
    from pipeline.stages.export import compact

    doc = {"fit": {"parity": out}}
    assert "parity" in c04.EXACT and compact(doc, exact=c04.EXACT) == doc
    assert compact(doc, exact=frozenset()) != doc


def test_plain_json_guard():
    with pytest.raises(TypeError, match="not plain JSON"):
        par._check_json({"x": [np.float64(0.5)]}, "parity")
    with pytest.raises(ValueError, match="not a finite number"):
        par._check_json({"x": float("nan")}, "parity")
