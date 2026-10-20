"""CT-2119 (decision G17): the engine pin is the shared rule of tests/engine_pin.py, and the product alters no engine row."""
from __future__ import annotations

import importlib.metadata as md
import inspect

from c21_support import ROOT, VARIANTS, committed
from engine_pin import ENGINE_PIN, engine_pin_findings
from riskvalidation.validation import fairness as rv_tests

from pipeline.cases.c21 import bake, legal, reader
from pipeline.cases.c21 import estimates as est

PIN = "2a21c0b85578357bc7eb13e9d8ffda9ab9b300fa"
NULL_ALPHA_TESTS = ("fair.conditional_disparity", "fair.rate_spread_disparity", "fair.situation_testing")


def test_the_engine_is_pinned_at_the_engine_1_2_0_commit_that_the_sdd_names() -> None:
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    assert len(ENGINE_PIN.findall(req)) == 1 and engine_pin_findings(req, sdd) == []   # a tag, or a full commit that the SDD row names
    assert ENGINE_PIN.search(req).group("ref") == PIN
    assert bake.engine_version().endswith(f"+{PIN[:7]}") and md.version("riskvalidation")
    for name in VARIANTS:
        assert committed(name)["provenance"]["riskvalidation_version"].endswith(f"+{PIN[:7]}")


def test_the_product_alters_no_engine_row_and_the_committed_rows_carry_the_engines_null_alphas(built) -> None:
    source = inspect.getsource(est)
    assert not hasattr(est, "NO_ALPHA_TESTS") and "NO_ALPHA_TESTS" not in source
    assert "alpha_amber=" not in source and "alpha_red=" not in source               # _segment replaces the segment and the notes only
    for docs in ([built.variants[n] for n in built.order], [committed(n) for n in VARIANTS]):
        for doc in docs:
            for row in doc["tests"]:
                if row["test_id"] in NULL_ALPHA_TESTS:
                    assert row["alpha_amber"] is None and row["alpha_red"] is None and row["extras"]["thresholds"], row["test_id"]


def test_the_engine_rows_of_the_three_tests_carry_null_alphas_before_the_product_touches_them(root) -> None:
    s = reader.to_sample(reader.read_year(root / "raw" / "hmda" / "hmda-de-2018.csv", 2018))
    d = est.build_design(s)
    logit = est.fit_contrast(s, d, "derived_race", "Black or African American", "White", "logistic")
    ols = est.fit_contrast(s, d, "derived_race", "Black or African American", "White", "linear")
    rows = [rv_tests.conditional_disparity(est.MODEL_LOGIT, logit.effect, legal.CONTROLS, legal.MISSING_CONTROLS),
            rv_tests.rate_spread_disparity(est.MODEL_OLS, ols.effect, legal.CONTROLS, legal.MISSING_CONTROLS)]
    block, sit = est.situation_result(s, d, 5)
    raw = [r.test_id for r in rows] + [sit.test_id]
    assert raw == list(NULL_ALPHA_TESTS) and block["n_complainants"] > 0
    for row in (*rows, sit):
        assert row.alpha_amber is None and row.alpha_red is None, row.test_id
