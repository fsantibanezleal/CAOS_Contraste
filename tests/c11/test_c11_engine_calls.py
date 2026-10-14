"""CT-1106, CT-1107: every number is the pinned engine; the product defines none of its functions; fits are deterministic."""
from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
from pathlib import Path

import numpy as np
from riskvalidation.market import caviar, evt, garch, gas_fz, historical, parametric, scoring
from riskvalidation.validation import market as rv_val

from pipeline.cases.c11 import forecast as fc

PKG = Path(__file__).resolve().parents[2] / "data-pipeline" / "pipeline" / "cases" / "c11"


def _y(n: int = 1100, seed: int = 3) -> np.ndarray:
    import sim

    return sim.shocks(n, seed, 0.01)


def test_the_engine_goldens_reproduce_through_the_pin():
    """The consumer test of engine-market-api: values that hold by formula, through the installed engine."""
    v, e = parametric.delta_normal_var_es(0.0, 0.01, 0.01)
    assert abs(v - (-0.0232634787)) < 5e-10 and abs(e - (-0.0266521424)) < 5e-9
    assert abs(float(scoring.tick_loss(np.array([-0.03]), np.array([-0.02]), 0.01)[0]) - 0.99 * 0.01) < 1e-15
    k = rv_val.kupiec_pof(np.zeros(250, dtype=int), 0.01, "m")
    assert k.light.value in ("green", "amber", "red") and abs(k.statistic - 5.0251679) < 1e-6   # zero exceedances in 250 days
    z2 = rv_val.acerbi_szekely(np.array([0, 0, 0, 0, 0.05]), np.full(5, 0.02), np.full(5, 0.03), 0.025, lambda r: np.zeros(5), "g", "Z2", 20, 0)
    assert abs(z2.statistic - (-12.333333)) < 5e-7                                             # the golden of the contract


def test_every_forecast_is_an_engine_call(tiny):
    y = _y()
    idx = np.array([1000])
    w = y[500:1000]
    r = fc.run_model(fc.SPEC_BY_ID["hs-250"], y, idx, tiny)
    assert (r.var[0.01][0], r.es[0.01][0]) == historical.historical_var_es(y[750:1000], 0.01, 250)
    r = fc.run_model(fc.SPEC_BY_ID["awhs"], y, idx, tiny)
    assert (r.var[0.025][0], r.es[0.025][0]) == historical.age_weighted_var_es(y[750:1000], 0.025, tiny.age_weight_lambda, 250)
    r = fc.run_model(fc.SPEC_BY_ID["ewma"], y, idx, tiny)
    assert (r.var[0.01][0], r.es[0.01][0]) == parametric.ewma_var_es(w, tiny.ewma_lambda, 0.01, float(w.var()))
    r = fc.run_model(fc.SPEC_BY_ID["garch-t"], y, idx, tiny)
    fit = garch.fit_garch(w, "garch", "student-t", "constant")
    flt = garch.garch_filter(fit, w)
    q, eq = garch.innovation_var_es(fit, 0.01)
    assert abs(r.var[0.01][0] - (flt.mu_next + flt.sigma_next * q)) < 1e-15 and abs(r.es[0.01][0] - (flt.mu_next + flt.sigma_next * eq)) < 1e-15
    r = fc.run_model(fc.SPEC_BY_ID["evt-mf"], y, idx, tiny)
    ev = evt.conditional_evt_forecast(w, 0.01, tiny.evt_threshold_fraction, "garch")
    assert r.var[0.01][0] == ev.var and (np.isnan(r.es[0.01][0]) if ev.es is None else r.es[0.01][0] == ev.es)
    r = fc.run_model(fc.SPEC_BY_ID["fhs"], y, idx, tiny)
    fit = garch.fit_garch(w, "garch", "normal", "constant")
    flt = garch.garch_filter(fit, w)
    assert (r.var[0.01][0], r.es[0.01][0]) == historical.filtered_hs_var_es(flt.std_residuals, flt.mu_next, flt.sigma_next, 0.01)


def test_adversarial_the_fits_are_deterministic_for_a_seed_and_change_with_it(tiny):
    y = _y()[:600]
    a = caviar.fit_caviar(y, 0.025, "sav", 3, 42)
    b = caviar.fit_caviar(y, 0.025, "sav", 3, 42)
    assert np.array_equal(a.params, b.params) and a.tick_loss == b.tick_loss
    g1 = gas_fz.fit_gas_fz(y, 0.025, "one-factor", 2, 42)
    g2 = gas_fz.fit_gas_fz(y, 0.025, "one-factor", 2, 42)
    assert np.array_equal(g1.params, g2.params)
    r1 = fc.run_model(fc.SPEC_BY_ID["caviar-sav"], _y(), np.array([1000, 1001]), tiny, (0.025,))
    r2 = fc.run_model(fc.SPEC_BY_ID["caviar-sav"], _y(), np.array([1000, 1001]), tiny, (0.025,))
    assert np.array_equal(r1.var[0.025], r2.var[0.025])
    y, idx = _y(), np.array([1000])
    import dataclasses
    assert fc.fingerprint(y, idx, tiny, fc.SPEC_BY_ID["caviar-sav"], "e") != fc.fingerprint(y, idx, dataclasses.replace(tiny, seed=7), fc.SPEC_BY_ID["caviar-sav"], "e")


def _engine_function_names() -> set[str]:
    names = set()
    for base in ("riskvalidation.market", "riskvalidation.validation"):
        pkg = importlib.import_module(base)
        for m in pkgutil.iter_modules(pkg.__path__):
            mod = importlib.import_module(f"{base}.{m.name}")
            for n, f in inspect.getmembers(mod, inspect.isfunction):
                if f.__module__ == mod.__name__ and not n.startswith("_"):
                    names.add(n)
    return names


def defined_and_imported(source: str) -> tuple[set[str], set[str]]:
    tree = ast.parse(source)
    defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            mods.add(n.module.split(".")[0])
    return defs, mods


def test_adversarial_the_product_defines_no_engine_function():
    engine = _engine_function_names()
    assert {"fz0_loss", "kupiec_pof", "historical_var_es", "model_confidence_set", "fit_caviar"} <= engine
    for path in sorted(PKG.glob("*.py")):
        defs, mods = defined_and_imported(path.read_text(encoding="utf-8"))
        assert not (defs & engine), f"{path.name} defines an engine function: {sorted(defs & engine)}"
        assert not ({"arch", "statsmodels", "sklearn"} & mods), f"{path.name} imports an estimation library directly"
    # the scan can fail: a planted definition and a planted import are found
    defs, mods = defined_and_imported("import arch\nfrom scipy import stats\ndef fz0_loss(y, v, e, a):\n    return 0\n")
    assert "fz0_loss" in (defs & engine) and "arch" in mods
