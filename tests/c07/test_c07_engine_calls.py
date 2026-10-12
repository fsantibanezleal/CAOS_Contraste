"""CT-704: the pinned engine reproduces the goldens of docs/contracts/engine/provisions-api.md (the consumer test of the
contract), and the C07 regime numbers come from it."""
from __future__ import annotations

import math
import pathlib
import re

import numpy as np
import pytest
from riskvalidation.provisions import ecl
from riskvalidation.provisions import local_cl as cl
from riskvalidation.provisions import local_es as es
from riskvalidation.provisions import overlays as ov
from riskvalidation.provisions import term_structure as ts

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_the_pin_is_riskvalidation_0_5_0() -> None:
    from importlib.metadata import version

    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    tag = re.search(r"CAOS_RiskValidation@v(\d+)\.(\d+)\.(\d+)", req)
    assert tag is not None
    assert version("riskvalidation") == ".".join(str(int(g)) for g in tag.groups())     # tag v0.05.000 is release 0.5.0


def test_the_pinned_engine_reproduces_the_contract_goldens() -> None:
    # B-1 individual categories and provisions
    assert cl.b1_individual_category("A1") == (0.0004, 0.9, 0.00036)
    assert cl.b1_individual_category("A4") == (0.02, 0.875, 0.0175)
    assert cl.b1_individual_category("B4") == (0.45, 0.975, 0.43875)
    assert cl.b1_individual_provision(1000, 0, "A4") == pytest.approx(17.5)
    assert cl.b1_individual_provision(1000, 400, "A4", "A1") == pytest.approx(10.644)
    assert cl.b1_default_provision(1000, 700) == (0.30, "C3", 250.0)
    assert cl.b1_default_provision(1000, 970)[1] == "C1" and cl.b1_default_provision(1000, 200)[1] == "C5"
    assert cl.b1_default_provision(1000, 190)[1] == "C6"
    # group standard methods
    assert cl.b1_mortgage_pe(0.75, "0") == pytest.approx((0.019158, 0.021955, 0.000421))
    assert cl.b1_mortgage_pe(0.95, "default") == pytest.approx((1.0, 0.302436, 0.302436))
    assert cl.b1_leasing_pe(0.45, "0", True) == pytest.approx((0.0079, 0.0005, 3.95e-6))
    assert cl.b1_student_loan_pe("CAE", "0") == pytest.approx((0.052, 0.709, 0.036868))
    assert cl.b1_student_loan_pe("CAE", "not-due") == pytest.approx((0.416, 0.503, 0.209248))
    assert cl.b1_commercial_pe("0", None) == pytest.approx((0.0491, 0.569, 0.0279379))
    assert cl.b1_commercial_pe("0", 0.5) == pytest.approx((0.0186, 0.05, 0.00093))
    assert cl.b1_consumer_pe(3, True, False, "instalment") == pytest.approx((0.033, 0.477, 0.015741))
    assert cl.b1_consumer_pe(70, False, True, "cards-lines-other") == pytest.approx((0.869, 0.603, 0.524007))
    assert cl.b1_group_provision(1000, 0.02, 0.5, 0.0004) == pytest.approx(10.2)
    m = cl.b1_minimum_normal_check(25e9, 100e6)
    assert (m.minimum_amount, m.binding, m.top_up) == (125e6, True, 25e6)
    assert not cl.b1_minimum_normal_check(25e9, 150e6).binding
    assert cl.b1_group_max_rule(100, 90, False) == (100, "max") and cl.b1_group_max_rule(100, 90, True) == (90, "internal")
    assert cl.b1_group_max_rule(100, None, False) == (100, "standard")
    assert cl.b1_additional_provisions(60e6, 0, 120e6) == 60e6
    with pytest.raises(ValueError):
        cl.b1_additional_provisions(130e6, 0, 120e6)
    # Annex 9
    assert es.annex9_uncovered_amount(100, [30, 20]) == 50 and es.annex9_uncovered_amount(100, [120]) == 0
    assert es.annex9_normal_coverage("B.1.1", "normal") == 0.007
    assert es.annex9_normal_coverage("B.1.1", "normal-special-watch") == 0.18
    assert es.annex9_normal_coverage("A.1.1", "normal") == 0.019
    assert es.annex9_normal_coverage("B.2", "normal-special-watch") == 0.202
    assert es.annex9_normal_coverage("B.2.1", "normal") == 0.010
    assert es.annex9_doubtful_coverage("B.1.1", 150) == 0.45 and es.annex9_doubtful_coverage("B.1.1", 670) == 1.0
    assert es.annex9_doubtful_coverage("B.2", 243) == 0.65 and es.annex9_doubtful_coverage("A.2.3", 122) == 0.35
    with pytest.raises(ValueError):
        es.annex9_doubtful_coverage("B.1.1", 90)
    # ECL
    z = np.array([1.0, 0.0, -2.0])
    pit = ts.ttc_to_pit(np.array(0.02), 0.12, z)
    assert pit == pytest.approx([0.005255059, 0.014287387, 0.073424082], abs=1e-8)
    w = np.array([0.25, 0.5, 0.25])
    assert ts.weighted_pit_pd(0.02, 0.12, z, w) == pytest.approx(0.026813479, abs=1e-8)
    assert ecl.probability_weighted_ecl(0.4 * pit, w) == pytest.approx(0.010725392, abs=1e-8)
    assert ecl.non_linearity_index(0.026813479, 0.017997448) == pytest.approx(0.4898489, abs=1e-6)
    q = np.array([[0.01, 0.01]])
    assert ecl.ecl_scenario(q, 0.4, 100000.0, np.zeros(1), np.array([6, 12]), 12)[0] == pytest.approx(800.0)
    assert ecl.ecl_scenario(q, 0.4, 100000.0, np.zeros(1), np.array([6, 12]), 6)[0] == pytest.approx(400.0)
    s3 = ecl.stage3_ecl(np.array([50000.0]), np.array([[30000.0]]), np.array([[12.0]]), np.array([0.08]))[0]
    assert s3 == pytest.approx(22222.2222, abs=1e-4)
    o = ov.Overlay("O", "r", "r", "expert", "pd", None, "stage1", 5.0, "none", "2026-08-31", "CLP")
    a = ecl.portfolio_allowance(np.array([1, 2, 3]), np.array([10.0, 20, 30]), np.array([15.0, 40, 45]), np.array([0.0, 0, 25]),
                                overlays=[o])
    assert a.by_stage == {"stage1": 10.0, "stage2": 40.0, "stage3": 25.0, "poci": 0.0} and a.model_total == 75 and a.total == 80
    assert math.isclose(ov.overlay_share(5, 80), 0.0625)


def test_every_regime_number_of_the_bake_is_an_engine_function() -> None:
    """The bake modules call the engine functions and carry no B-1, Annex 9 or ECL table of their own."""
    pkg = ROOT / "data-pipeline" / "pipeline" / "cases" / "c07"
    text = "\n".join(p.read_text(encoding="utf-8") for p in pkg.glob("*.py") if p.name not in ("sources.py", "scenarios.py"))
    for fn in ("b1_mortgage_pe", "b1_consumer_pe", "b1_commercial_pe", "b1_group_provision", "b1_individual_provision",
               "b1_default_provision", "b1_minimum_normal_check", "annex9_coverage", "ecl_scenario", "stage3_ecl",
               "allocate_stages", "portfolio_allowance", "probability_weighted_ecl", "allowance_rollforward"):
        assert re.search(rf"\b{fn}\(", text), fn
    for table in ("_MORTGAGE_PI", "_POINT_144", "_POINT_140", "_CONSUMER_PI", "_COMMERCIAL_PI"):
        assert table not in text, f"the product reads the engine table {table}"
