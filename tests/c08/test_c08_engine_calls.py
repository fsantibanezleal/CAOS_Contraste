"""CT-908 and CT-909: the engine contract's golden values through the pinned `riskvalidation`, and no LGD logic in the product.

The goldens are transcribed from `docs/contracts/engine/lgd-ead-api.md` (engine-lgd-ead-api 1.0.0), which takes them from
dossier 04 F.1 to F.4 and dossier 01 A.5. A drift of the pin from the released engine fails here."""
from __future__ import annotations

import importlib.metadata as md
from pathlib import Path

import numpy as np
import pytest
from c08_helpers import ENGINE_FUNCTIONS, engine_logic_findings
from riskvalidation.lgd_ead import downturn as D
from riskvalidation.lgd_ead import floors as F
from riskvalidation.lgd_ead import lgd_models as M
from riskvalidation.lgd_ead import workout as W
from riskvalidation.validation import lgd_ead as V
from engine_pin import engine_pin_findings, released_version

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "data-pipeline" / "pipeline" / "cases" / "c08"
FLOORS = {("corporate", "unsecured"): 0.25, ("corporate", "financial"): 0.0, ("corporate", "receivables"): 0.10,
          ("corporate", "real-estate"): 0.10, ("corporate", "other-physical"): 0.15, ("retail", "mortgage"): 0.05,
          ("retail", "qrre"): 0.50, ("retail", "unsecured"): 0.30, ("retail", "financial"): 0.0, ("retail", "receivables"): 0.10,
          ("retail", "real-estate"): 0.10, ("retail", "other-physical"): 0.15}


def floor_golden_findings(table=FLOORS) -> list[str]:
    return [f"{p} {c}: {F.lgd_floor(p, c)} is not {v}" for (p, c), v in table.items() if abs(F.lgd_floor(p, c) - v) > 1e-12]


def test_the_pin_is_the_released_engine():
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    assert engine_pin_findings(req, sdd) == []  # a release tag, or during a batch the commit the SDD names (tests/engine_pin.py)
    rel = released_version(req)
    if rel is not None:  # the tag v0.06.000 is the release 0.6.0 of the package
        assert rel >= (0, 6, 0)          # lgd_ead arrived in 0.6.0; a later release keeps it
        assert md.version("riskvalidation") == ".".join(map(str, rel))


def test_the_engine_golden_values_reproduce_through_the_pin():
    assert abs(W.eba_discount_rate(0.0325) - 0.0825) < 1e-12
    ead, t = np.array([100.0]), np.array([[1.0, 2.0]])
    zero = np.zeros((1, 2))
    lgd = W.workout_lgd(ead, t, np.array([[40.0, 30.0]]), np.array([[10.0, 0.0]]), zero, 0.10)
    assert abs(float(lgd[0]) - 0.479339) < 5e-7
    assert abs(float(W.workout_lgd(ead, t, np.array([[5.0, 0.0]]), np.array([[20.0, 0.0]]), zero, 0.10)[0]) - 1.136364) < 5e-7
    assert abs(float(W.workout_lgd(ead, t, np.array([[120.0, 0.0]]), zero, zero, 0.10)[0]) + 0.090909) < 5e-7
    assert W.range_flag(np.array([-0.090909, 0.0, 0.5, 1.0, 1.136364])).tolist() == ["below-zero", "in-range", "in-range", "in-range", "above-one"]
    r = W.resolve_incomplete(np.array([0.2, 0.6, 0.9]), np.array([True, True, False]), "excluded")
    assert r.lgd.tolist() == [0.2, 0.6] and r.n_excluded == 1
    r = W.resolve_incomplete(np.array([0.2, 0.6, 0.9]), np.array([True, True, False]), "projected", np.array([np.nan, np.nan, 0.7]))
    assert r.lgd.tolist() == [0.2, 0.6, 0.7] and r.n_projected == 1
    cd = np.array(["2008-06-30", "2008-12-31", "2009-03-31", "NaT"], dtype="datetime64[D]")
    assert W.closed_before(cd, "2008-12-31").tolist() == [True, False, False, False]
    dist = W.lgd_distribution(np.array([-0.05, 0, 0, 0.25, 0.5, 1, 1, 1.2]), np.array([0.0, 0.5, 1.0]))
    assert (dist.counts.tolist(), dist.n, dist.n_below_zero, dist.n_above_one, dist.mass_zero, dist.mass_one) == ([3, 3], 8, 1, 1, 2, 2)


def test_the_lgd_rung_goldens_reproduce_through_the_pin():
    assert M.endpoint_transform(np.array([0.0, 0.5, 1.0]), 0.001).tolist() == [0.001, 0.5, 0.999]
    ols = M.fit_ols(np.array([[1.0, 0.0], [1.0, 1.0]]), np.array([0.0, 1.0]))
    assert np.allclose(ols.coefficients, [0.0, 1.0], atol=1e-12) and float(M.predict_lgd(ols, np.array([[1.0, 2.0]]))[0]) == 1.0
    x = np.array([[1.0, 0], [1, 0], [1, 1], [1, 1]])
    fl = M.fit_fractional_logit(x, np.array([0.0, 0.5, 0.5, 1.0]))
    assert np.allclose(fl.coefficients, [-1.098612, 2.197225], atol=5e-7)
    assert np.allclose(M.predict_lgd(fl, np.array([[1.0, 0], [1.0, 1]])), [0.25, 0.75], atol=1e-6)
    hu = M.fit_hurdle(np.ones((4, 1)), np.array([0.0, 0.4, 0.4, 0.4]), min_positive=3)
    assert abs(float(M.predict_lgd(hu, np.ones((1, 1)))[0]) - 0.3) < 1e-9
    to = M.fit_tobit(np.array([[1.0, 0], [1, 1], [1, 2]]), np.array([0.2, 0.3, 0.6]))
    assert np.allclose(to.coefficients, [0.166667, 0.2], atol=1e-6) and abs(to.extras["sigma"] - 0.0471405) < 1e-6
    assert abs(float(M.cure_decomposition(np.array([0.3]), np.array([0.05]), np.array([0.6]))[0]) - 0.435) < 1e-12
    b1, b2 = (M.fit_beta(x, np.array([0.0, 0.5, 0.5, 1.0]), e) for e in (0.01, 0.0001))
    assert b1.extras["epsilon"] == 0.01 and b2.extras["epsilon"] == 0.0001


def test_the_downturn_floor_and_validation_goldens_reproduce_through_the_pin():
    years = np.arange(2006, 2012)
    assert D.identify_downturn(years, np.array([4.6, 4.6, 5.8, 9.3, 9.6, 8.9]), 7.0).tolist() == [False, False, False, True, True, True]
    res = D.downturn_add_on(np.array([0.30, 0.60, 0.40]), np.array([100.0, 50.0, 50.0]), np.array([False, True, False]))
    assert (abs(res.long_run - 0.40) < 1e-12, abs(res.downturn - 0.60) < 1e-12, abs(res.add_on - 0.20) < 1e-12) == (True, True, True)
    assert D.coverage_shortfall(0.55, 0.60) == (False, pytest.approx(0.05)) and D.coverage_shortfall(0.70, 0.68) == (True, 0.0)
    assert floor_golden_findings() == []
    bite = F.apply_lgd_floor(np.array([0.20, 0.30, 0.60]), 0.25)
    assert bite.applied.tolist() == [0.25, 0.30, 0.60] and bite.binding.tolist() == [True, False, False]
    assert abs(bite.share_binding - 1 / 3) < 1e-12 and abs(bite.mean_before - 0.366667) < 5e-7
    assert abs(bite.mean_after - 0.383333) < 5e-7 and abs(bite.uplift - 0.016667) < 5e-7
    cal = V.lgd_calibration_by_segment(np.array([0.4, 0.5, 0.6]), np.array([0.3, 0.3, 0.3]))
    assert abs(cal.statistic - 3.464102) < 5e-7 and abs(cal.p_value - 0.074180) < 5e-7 and abs(cal.metric - 0.2) < 1e-12
    assert cal.light.value == "green"
    over = V.lgd_calibration_over_time(np.array([0.4, 0.5, 0.6, 0.4, 0.5, 0.6]), np.array([0.3, 0.3, 0.3, 0.5, 0.5, 0.5]),
                                       np.array([1, 1, 1, 2, 2, 2]))
    assert abs(over.statistic - 3.464102) < 5e-7 and abs(over.p_value - 0.148360) < 5e-7 and abs(over.metric - 0.2) < 1e-12
    disc = V.lgd_discrimination(np.array([0.1, 0.4, 0.6, 0.9]), np.array([0.2, 0.3, 0.7, 0.8]))
    assert disc.statistic == pytest.approx(1.0) and disc.light.value == "green"
    assert V.lgd_discrimination(np.array([0.1, 0.4, 0.6, 0.9]), np.array([0.8, 0.7, 0.3, 0.2])).light.value == "red"
    cov = V.downturn_coverage(0.55, np.array([0.5, 0.6, 0.7]))
    assert abs(cov.statistic - 0.866025) < 5e-7 and abs(cov.p_value - 0.238884) < 5e-7 and abs(cov.metric - 0.05) < 1e-12


def test_adversarial_a_drifted_golden_value_is_found():
    assert floor_golden_findings() == []
    drifted = {**FLOORS, ("corporate", "unsecured"): 0.30}
    assert floor_golden_findings(drifted) == ["corporate unsecured: 0.25 is not 0.3"]


def test_the_product_defines_no_engine_function():
    sources = {p.name: p.read_text(encoding="utf-8") for p in PACKAGE.glob("*.py")}
    assert sources and engine_logic_findings(sources) == []
    used = {"closed_before", "range_flag", "lgd_distribution", "fit_ols", "fit_fractional_logit", "fit_beta", "fit_hurdle",
            "fit_tobit", "predict_lgd", "identify_downturn", "downturn_add_on", "coverage_shortfall", "lgd_floor", "apply_lgd_floor",
            "lgd_calibration_by_segment", "lgd_calibration_over_time", "lgd_discrimination", "downturn_coverage"}
    assert used <= ENGINE_FUNCTIONS
    text = "\n".join(sources.values())
    for fn in used:
        assert fn in text, f"{fn} is not called by the C08 package"
    assert "from riskvalidation" in text


def test_adversarial_an_engine_formula_copied_into_the_product_is_found():
    planted = {"downturn.py": "from riskvalidation.lgd_ead import downturn\n\ndef downturn_add_on(lgd, w, mask):\n"
                              "    return (lgd[mask] * w[mask]).sum() / w[mask].sum() - (lgd * w).sum() / w.sum()\n"}
    assert engine_logic_findings(planted) == ["downturn.py: defines downturn_add_on, an engine function"]
    assert engine_logic_findings({"x.py": "def apply_lgd_floor(l, f):\n    return l\n"}) == [
        "x.py: defines apply_lgd_floor, an engine function", "no import from riskvalidation"]
