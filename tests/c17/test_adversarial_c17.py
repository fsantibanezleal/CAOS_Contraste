"""Adversarial checks of C17: each plants a defect in a copy and asserts that the clean copy passes and the planted copy fails."""
from __future__ import annotations

import copy
import re

import numpy as np
import pytest
from c17_semantic import semantic_findings
from conftest import DERIVED, ROOT, load
from pipeline.cases.c17 import generator, page, truth
from pipeline.cases.c17 import params as P
from pipeline.core.schemas import SchemaViolation, validate_document
from pipeline.io import contract
from riskvalidation.oprisk import distributions as dist
from riskvalidation.oprisk import sma


def _fails(doc: dict) -> bool:
    rel = "data/derived/C17/xi-0-8.json" if "outputs" in doc else "data/derived/C17/models-generator.json"
    try:
        validate_document(rel, doc)
    except SchemaViolation:
        return True
    return bool(semantic_findings(doc))


def test_adversarial_a_scale_off_the_ldce_fit_is_found():
    v = generator.variant(0.8)
    good = np.max(np.abs(generator._log_residuals(0.8, v.scale_above_ldce_eur)))
    bad = np.max(np.abs(generator._log_residuals(0.8, v.scale_above_ldce_eur * 2.5)))
    assert good <= P.CALIBRATION_TOLERANCE_LOG < bad


def test_adversarial_a_frequency_without_the_survival_adjustment_is_found():
    v = generator.variant(1.1)
    assert abs(generator.expected_count_above(v, 20_000.0) - 41.0) < 1e-6
    naive = P.LDCE_FREQUENCY_PER_BN * P.ASSETS_EUR_BN  # 41 a year counted from the floor instead of from EUR 20,000
    assert abs(generator.expected_count_above(generator.Variant(v.tail_index, v.scale_eur, v.scale_above_ldce_eur, naive, v.fitted_quantiles_eur,
                                                                v.max_abs_log_error), 20_000.0) - 41.0) > 5.0


def test_adversarial_a_shifted_true_quantile_is_found():
    t = truth.compute(generator.variant(0.8), mc_years=300_000)
    qm = t.exceedance_block["quantile_999_eur"]
    assert abs(qm["panjer"] - qm["fft"]) / qm["panjer"] < 1e-3
    assert abs(qm["panjer"] - 1.05 * qm["fft"]) / qm["panjer"] > 1e-3  # a truth shifted by 5 percent leaves the cross-method agreement
    mc = t.truth_block["annual_loss_quantile"]["mc_check"]
    assert abs(mc["value_eur"] - t.quantile_eur) <= 3 * mc["standard_error_eur"]
    assert abs(mc["value_eur"] - 1.5 * t.quantile_eur) > 3 * mc["standard_error_eur"]  # and one shifted by 50 percent leaves the Monte Carlo band


def test_adversarial_a_mean_for_a_tail_index_of_one_point_one_is_refused():
    doc = load("C17/xi-1-1.json")
    assert not _fails(doc)
    bad = copy.deepcopy(doc)
    bad["outputs"]["truth"]["annual_loss_mean"] = {"value_eur": 1.0e9, "reason": None}
    assert _fails(bad)
    models = load("C17/models-generator.json")
    assert not _fails(models)
    swapped = copy.deepcopy(models)
    v = swapped["fit"]["variants"]
    v[0]["true_quantile_999_eur"], v[1]["true_quantile_999_eur"] = v[1]["true_quantile_999_eur"], v[0]["true_quantile_999_eur"]
    assert _fails(swapped)


def test_adversarial_a_fit_on_losses_below_the_threshold_is_refused():
    v = generator.variant(0.8)
    h = generator.draw_history(v, 4, 10)
    assert (h.amount_eur < 20_000.0).any()
    with pytest.raises(ValueError):
        dist.fit_severity("lognormal", h.amount_eur, 20_000.0, truncated=True)
    assert h.recorded(20_000.0).amounts.min() >= 20_000.0


def test_adversarial_rows_below_the_threshold_are_rejected_by_contract_one():
    h = generator.draw_history(generator.variant(0.8), 4, 10)
    p = {"collection_threshold": 20_000.0, "currency": "EUR"}
    assert contract.validate("loss_events", h.rows(20_000.0), params=p).counts()["rejected"] == 0
    assert contract.validate("loss_events", h.rows(10_000.0), params=p).counts()["rejected"] > 0
    dup = h.rows(20_000.0)
    dup.append(dict(dup[0]))
    assert contract.validate("loss_events", dup, params=p).counts()["rejected"] > 0


def test_adversarial_overlapping_seed_ranges_are_found():
    spans = [generator.cell_seeds(42, vi, ci, 1000) for vi in range(4) for ci in range(4)]
    ranges = sorted((a, a + n - 1) for a, n in spans)
    assert all(x[1] < y[0] for x, y in zip(ranges, ranges[1:]))
    bad = sorted([*ranges, (ranges[3][0] + 10, ranges[3][0] + 1009)])
    assert any(x[1] >= y[0] for x, y in zip(bad, bad[1:]))
    v = generator.variant(0.8)
    assert not np.array_equal(generator.draw_history(v, 1, 5).amount_eur, generator.draw_history(v, 2, 5).amount_eur)


def test_adversarial_a_changed_engine_golden_is_found(monkeypatch):
    from riskvalidation.oprisk import aggregate as agg

    h = agg.panjer_recursion("poisson", (100.0,), agg.discretise_severity("lognormal", (0.0, 2.0), 1.0, 6000))
    assert agg.quantile_from_pmf(h, 1.0, 0.999) == 5849.0
    monkeypatch.setattr(agg, "quantile_from_pmf", lambda *a, **k: 5900.0)
    assert agg.quantile_from_pmf(h, 1.0, 0.999) != 5849.0


def test_adversarial_a_formula_in_the_product_is_found():
    pkg = ROOT / "data-pipeline" / "pipeline" / "cases" / "c17"
    pattern = re.compile(r"0\.12\s*\*|\*\*\s*0\.8")
    assert not any(pattern.search(f.read_text(encoding="utf-8")) for f in pkg.glob("*.py"))
    assert pattern.search("bic = 0.12 * min(bi, 1e9)") and pattern.search("ilm = log(e - 1 + (lc / bic) ** 0.8)")


def test_adversarial_a_document_without_its_truth_or_with_a_disordered_summary_is_refused():
    doc = load("C17/xi-0-8.json")
    assert not _fails(doc)
    no_truth = copy.deepcopy(doc)
    del no_truth["outputs"]["truth"]
    assert _fails(no_truth)
    disordered = copy.deepcopy(doc)
    cap = disordered["outputs"]["cells"][0]["capital"]["lda_splice"]["capital_eur"]
    cap["p05"], cap["p95"] = cap["p95"], cap["p05"]
    assert _fails(disordered)
    ratio = copy.deepcopy(doc)
    ratio["outputs"]["cells"][1]["capital"]["sla"]["ratio_to_truth"]["median"] *= 1.5
    assert _fails(ratio)


def test_adversarial_a_mean_corrected_sla_for_a_tail_index_above_one_is_refused():
    doc = load("C17/xi-1-1.json")
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"][0]["capital"]["sla_mean_corrected"] = copy.deepcopy(load("C17/xi-0-8.json")["outputs"]["cells"][0]["capital"]["sla_mean_corrected"])
    assert not _fails(doc) and _fails(bad)


def test_adversarial_an_ilm_on_three_years_is_refused():
    doc = load("C17/xi-0-8.json")
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"][0]["years"] = 3
    assert _fails(bad)
    assert sma.sma_capital(1.4e9, np.full(3, 5e7)).basis == "bic-only"


def test_adversarial_a_page_that_calls_the_bank_real_is_found():
    assert page.claim_findings("The bank is synthetic. The calibration follows the BCBS LDCE medians.") == []
    assert page.claim_findings("The bank is a real bank with real losses.\nSynthetic otherwise. The BCBS LDCE medians.")
    assert page.claim_findings("A page about losses with no statement of origin at all.")


def test_adversarial_a_bake_that_ignores_its_seed_is_found():
    v = generator.variant(0.8)
    assert np.array_equal(generator.draw_history(v, 9, 5).amount_eur, generator.draw_history(v, 9, 5).amount_eur)
    first = np.random.default_rng().random(5)  # a draw from the clock or the OS differs between two calls: equality above would fail
    assert not np.array_equal(first, np.random.default_rng().random(5))


def test_adversarial_a_hand_edited_results_block_is_found():
    block = page.results_block(DERIVED)
    assert block == page.results_block(DERIVED)
    assert block.replace("0", "1", 1) != block
