"""CT-1815: the reverse stress."""
from __future__ import annotations

import numpy as np
import pytest
from c18_support import requires_raw
from riskvalidation.stress import capital as rv_cap
from riskvalidation.stress import reverse as rv_rev

from pipeline.cases.c18 import params as P

pytestmark = requires_raw


def test_reverse_stress_reaches_the_stack_with_the_minimum_distance(built) -> None:
    o = built.variants[P.FILE_NAMES["reverse"]]["outputs"]
    fp = o["failure_point"]
    st = fp["stack"]
    assert st["basis"] == "chilean-legal-minimum-stack"
    assert st["total"] == pytest.approx(rv_cap.chilean_cet1_stack(st["c_ccyb"], st["c_dsib"], st["p2_cet1"]["value"]))
    fs = o["factor_space"]
    assert [f["id"] for f in fs["factors"]] == list(P.REGRESSORS) and fs["window"] == {"start": "1985-03-31", "end": "2019-12-31"}
    cov = np.array(fs["covariance"])
    assert np.allclose(np.diag(cov), [f["sd"] ** 2 for f in fs["factors"]])
    sol = o["solution"]
    x = np.array(sol["x_star"])
    assert sol["mahalanobis_distance"] == pytest.approx(float(np.sqrt(x @ np.linalg.solve(cov, x))))
    assert sol["loss_at_z_star_clp_m"] == pytest.approx(sol["loss_threshold_clp_m"], rel=1e-6)
    assert sol["loss_threshold_clp_m"] == pytest.approx((fp["cet1_ratio_start"] - st["total"]) * fp["rwa_clp_m"])
    assert len(o["starts"]) >= 3 and all(s["distance"] >= sol["mahalanobis_distance"] * (1 - 1e-6) for s in o["starts"] if s["converged"])
    assert o["loss_model"]["kind"] == "nonlinear" and sol["method"] == "scipy-optimize"
    test = built.variants[P.FILE_NAMES["reverse"]]["tests"][0]
    assert test["test_id"] == "stress.reverse_solution_check" and test["light"] == "green"
    # the closed form of the engine on a linear loss is the reference of the solver (derived identity)
    g = np.array([-60_000.0, 110_000.0])
    lin = rv_rev.reverse_stress_linear(g, cov, 1000.0)
    best, _ = rv_rev.reverse_stress(lambda v: float(g @ v), cov, 1000.0, [np.array([1.0, 1.0]), np.array([-1.0, 2.0]), np.array([0.5, 3.0])])
    assert best.distance == pytest.approx(lin.distance, rel=1e-5)


def test_reverse_stress_rests_on_the_ppnr_path_and_is_not_evaluated_when_the_baseline_fails(built) -> None:
    from pipeline.cases.c18 import reverse

    o = built.variants[P.FILE_NAMES["reverse"]]["outputs"]
    for lang in ("en", "es"):
        text = o["loss_model"]["description"][lang] + " " + o["failure_point"]["definition"][lang]
        assert "PPNR" in text and "excess" not in text.lower() and "exceso" not in text.lower()
    # the threshold is the headroom of CET1 over the stack at the jump-off, and the loss is net of the cumulative PPNR of the baseline
    fp, sol = o["failure_point"], o["solution"]
    assert sol["loss_threshold_clp_m"] == pytest.approx((fp["cet1_ratio_start"] - fp["stack"]["total"]) * fp["rwa_clp_m"])
    ppnr = sum(r["ppnr_clp_m"] for r in built.variants["baseline"]["outputs"]["headline_cet1"]["ppnr"]["rows"])
    assert ppnr > 0 and built.results["reverse"]["net_loss_at_zero"] < sol["loss_threshold_clp_m"]
    reverse.check_baseline(built.results["reverse"]["net_loss_at_zero"], sol["loss_threshold_clp_m"])          # evaluated: no error
    with pytest.raises(reverse.NotEvaluated, match="PPNR baseline"):
        reverse.check_baseline(sol["loss_threshold_clp_m"] * 1.01, sol["loss_threshold_clp_m"])
