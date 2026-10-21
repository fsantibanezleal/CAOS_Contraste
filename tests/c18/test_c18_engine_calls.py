"""CT-1820: the package computes no statistic the engine provides (ADR-0069)."""
from __future__ import annotations

import ast
from pathlib import Path

from c18_support import ROOT

PACKAGE = ROOT / "data-pipeline" / "pipeline" / "cases" / "c18"
#: the numerical estimators of the engine that a bake must never restate
FORBIDDEN_CALLS = {"quantile", "percentile", "nanquantile", "nanpercentile", "var", "std", "corrcoef", "lstsq", "cholesky", "eigvalsh", "polyfit"}
#: the modules that hold numbers of the documents and so must call the engine
ENGINE_MODULES = {"satellites": "riskvalidation.stress", "marginals": "riskvalidation.portfolio", "aggregation": "riskvalidation.aggregation",
                  "capital": "riskvalidation.stress", "reverse": "riskvalidation.stress", "scenarios": "riskvalidation.stress"}


def _calls(path: Path) -> list[tuple[str, int]]:
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            out.append((name, node.lineno))
    return out


def test_no_statistic_of_the_engine_is_computed_in_the_package() -> None:
    for path in sorted(PACKAGE.glob("*.py")):
        bad = [(n, ln) for n, ln in _calls(path) if n in FORBIDDEN_CALLS]
        assert not bad, f"{path.name} restates an estimator the engine provides: {bad}"
    for mod, prefix in ENGINE_MODULES.items():
        text = (PACKAGE / f"{mod}.py").read_text(encoding="utf-8")
        assert f"from {prefix}" in text, f"{mod}.py does not import {prefix}"
    # the numbers of the documents come from named engine functions
    expected = {"marginals.py": ["measures_from_sample", "expected_loss", "simulate_gaussian", "quantile_from_pmf", "es_for_severity", "hw1f_scenarios"],
                "aggregation.py": ["dependence_band", "es_contributions", "glasserman_xu_worst_case", "barrieu_scandolo", "euler_additivity"],
                "capital.py": ["internal_capital_target", "annex3_summary", "ppnr_row", "cet1_path_loss_only", "p2g_proxy"],
                "satellites.py": ["fit_satellite", "project_scenario", "satellite_backcast"], "reverse.py": ["reverse_stress", "plausibility", "chilean_cet1_stack"],
                "scenarios.py": ["transpose_path", "annual_to_quarterly", "level_from_deviation", "check_vintage"]}
    for name, funcs in expected.items():
        called = {n for n, _ in _calls(PACKAGE / name)}
        assert set(funcs) <= called, (name, set(funcs) - called)
