"""CT-1104: every number of a C10 document is returned by riskvalidation; the pinned engine reproduces the golden values of the
engine contract (docs/contracts/engine/portfolio-api.md), and the product defines none of the engine's functions."""
from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest
from riskvalidation.engines import vasicek
from riskvalidation.portfolio import asrf_fit, euler, granularity
from riskvalidation.portfolio import portfolio as pf
from riskvalidation.validation import portfolio as val

PACKAGE = Path(__file__).resolve().parents[2] / "data-pipeline" / "pipeline" / "cases" / "c10"
ENGINE_NAMES = {"lhp_quantile", "lhp_cdf", "lhp_pdf", "conditional_pd", "implied_factor", "var_from_sample", "es_from_sample",
                "measures_from_sample", "lhp_measures", "expected_loss", "hhi", "effective_names", "gamma_quantile", "delta",
                "granularity_adjustment", "fit_ml", "fit_moments", "profile_likelihood", "profile_interval", "bootstrap_interval",
                "tail_backtest", "mc_convergence", "euler_additivity", "crp_recursion_vs_mc", "correlation_size_power"}
FORBIDDEN_IMPORTS = {"ndtr", "ndtri", "norm", "multivariate_normal", "NormalDist"}


def test_the_pinned_engine_reproduces_the_contract_goldens() -> None:
    assert vasicek.lhp_quantile(0.999, 0.02, 0.15) == pytest.approx(0.176329, abs=5e-7)
    assert vasicek.lhp_quantile(0.99, 0.02, 0.15) == pytest.approx(0.105587, abs=5e-7)
    m99, m999 = pf.lhp_measures(1.0, 1.0, 0.02, 0.15, (0.99, 0.999))
    assert (m99.var, m99.es, m999.var, m999.es, m999.el, m999.ec) == pytest.approx((0.105587, 0.135971, 0.176329, 0.209404, 0.02, 0.156329), abs=5e-6)
    assert pf.lhp_measures(1.0, 0.45, 0.02, 0.15, (0.999,))[0].ec == pytest.approx(0.070348, abs=5e-7)
    assert granularity.delta(0.25, 0.999) == pytest.approx(4.8336, abs=5e-5) and abs(granularity.delta(0.25, 0.999) - 4.83) < 0.005
    assert granularity.gamma_quantile(0.25, 0.999) == pytest.approx(17.505777, abs=5e-6)
    assert asrf_fit.fit_moments(np.array([0.01, 0.02, 0.03])).rho == pytest.approx(0.026880, abs=5e-7)
    assert asrf_fit.log_likelihood(np.array([0.01, 0.02, 0.05]), 0.02, 0.15) == pytest.approx(7.694105, abs=5e-7)
    rc = euler.asrf_var_contributions(np.array([60.0, 40.0]), np.array([0.01, 0.05]), np.array([0.45, 0.45]), 0.15, 0.999)
    assert rc == pytest.approx([2.977148, 5.643106], abs=5e-6)
    assert euler.hhi(np.array([50.0, 30.0, 20.0])) == pytest.approx(0.38)
    assert euler.effective_names(np.array([50.0, 30.0, 20.0])) == pytest.approx(2.631579, abs=5e-7)
    bt = val.tail_backtest(np.array([0.0045, 0.0085, 0.0160, 0.0120, 0.0080, 0.0050]), 0.003, 0.06, model_id="m")
    assert (bt.statistic, bt.p_value, bt.metric) == pytest.approx((1.0, 0.058520, 0.06), abs=5e-7) and bt.light == "green"
    assert val.mc_convergence(0.1030, 0.0010, 0.1000).p_value == pytest.approx(0.0027, abs=5e-7)
    res = val.correlation_size_power(np.array([True] * 52 + [False] * 948), 0.12, 0.12)
    assert (res.statistic, res.p_value) == pytest.approx((0.290191, 0.771671), abs=5e-7)


def test_the_product_defines_and_imports_none_of_the_engines_numerics() -> None:
    """No function of the engine is re-implemented here, and no normal-law numerics are imported to compute a capital or a test."""
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        assert not defined & ENGINE_NAMES, (path.name, defined & ENGINE_NAMES)
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith(("scipy", "statistics"))
                    for a in n.names}
        assert not imported & FORBIDDEN_IMPORTS, (path.name, imported & FORBIDDEN_IMPORTS)
