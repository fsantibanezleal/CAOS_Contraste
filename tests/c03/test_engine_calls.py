"""CT-807: every validation row is the engine's and the product defines none of its functions."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from riskvalidation.core.policy import default_policy
from riskvalidation.core.registry import spec

from pipeline.cases.c03 import evaluate
from pipeline.core.manifest import TEST_RESULT_KEYS

from .helpers import COMMITTED, defined_functions, engine_function_names

PACKAGE = Path(__file__).resolve().parents[2] / "data-pipeline" / "pipeline" / "cases" / "c03"


def _rows(sample_bake) -> list[dict]:
    import json

    root, _ = sample_bake["a"]
    rows = []
    for p in sorted((root / "C03").glob("fy*.json")):
        rows += json.loads(p.read_text(encoding="utf-8"))["tests"]
    return rows


def test_the_battery_rows_are_engine_test_results(sample_bake):
    rows = _rows(sample_bake)
    assert rows
    ids = {r["test_id"] for r in rows}
    assert {"disc.auc_vs_initial", "disc.delong", "pd.jeffreys", "pd.binomial", "pd.binomial_vasicek", "pd.hosmer_lemeshow",
            "pd.spiegelhalter", "stability.psi"} <= ids
    assert not ids & {"disc.auc", "pd.brier", "pd.ece", "disc.ks"}, "a descriptive metric has no light: it is not a row"
    assert {r["policy_version"] for r in rows} == {default_policy().label}
    assert {r["light"] for r in rows} <= {"green", "amber", "red", "not_evaluated"}
    for r in rows:
        assert set(r) == set(TEST_RESULT_KEYS)
        spec(r["test_id"])  # a registered engine test, or the registry raises
        if r["light"] == "not_evaluated":
            assert r["statistic"] is None and r["p_value"] is None and r["metric"] is None and r["notes"]


def test_the_engine_numbers_are_the_engines():
    """The AUC and the Brier score the case reports equal the engine's on the same inputs (one call, no second formula)."""
    from riskvalidation.validation.calibration import pd_brier
    from riskvalidation.validation.discrimination import disc_auc

    rng = np.random.default_rng(3)
    risk = rng.uniform(0.02, 0.4, 600)
    y = (rng.uniform(size=600) < risk).astype(int)
    direct = disc_auc(risk, y).to_dict()
    assert evaluate.auc(risk, y)["auc"] == direct["metric"]
    assert evaluate.brier(risk, y) == pd_brier(y, risk).metric
    assert evaluate.auc(risk, np.zeros(600, dtype=int)) is None
    rows = evaluate.engine_rows("m", risk, y)
    assert {r["test_id"] for r in rows} >= {"pd.jeffreys", "pd.binomial", "pd.spiegelhalter"}


def test_the_product_defines_no_engine_function():
    names = engine_function_names()
    assert {"pd_binomial", "disc_auc", "stability_psi", "auc_with_variance"} <= names
    for path in sorted(PACKAGE.glob("*.py")):
        clash = defined_functions(path.read_text(encoding="utf-8")) & names
        assert not clash, f"{path.name} defines engine functions {sorted(clash)}"
    text = (PACKAGE / "evaluate.py").read_text(encoding="utf-8")
    assert "riskvalidation.validation" in text


def test_adversarial_an_engine_formula_copied_into_the_product_is_found():
    names = engine_function_names()
    copied = "def pd_binomial(n, d, pd):\n    from scipy import stats\n    return stats.binom.sf(d - 1, n, pd)\n"
    assert defined_functions(copied) & names == {"pd_binomial"}
    assert defined_functions("def vintage_rows(x):\n    return x\n") & names == set()
    assert COMMITTED.exists()
