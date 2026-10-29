"""S-3 of the method tiers plan (tier sota): the robust severity estimators with the mean-adjusted single loss approximation, run on C17.

Acceptance criterion (plan section 3): on the generators of known truth, the capital's bias and spread of the robust estimators are
reported beside the MLE splice. The hypothesis is written in ``params.S3_HYPOTHESIS`` before the bake; the committed documents state
the measured result whether it holds or not.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from c17_support import DOCS, load
from pipeline.cases.c17 import params as P
from pipeline.cases.c17 import replicate
from pipeline.cases.c17.generator import draw_history
from riskvalidation.oprisk import distributions as dist
from riskvalidation.oprisk import robust

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "data-pipeline" / "pipeline" / "cases" / "c17"
NEW = ("sla_mean_adjusted", "sla_cvm", "sla_obre", "sla_cvm_lognormal")
NEW_IDS = ("sla-mean-adjusted", "sla-cvm", "sla-obre", "sla-cvm-lognormal")
YEARS, THRESHOLD, SEED = 5, 10_000.0, 11


def _estimate(v):
    return replicate.estimate(v, SEED, YEARS, THRESHOLD, 1.4e9, None, 20_000)


def test_the_ladder_names_the_four_new_rungs_after_the_existing_six():
    assert replicate.RUNGS[:6] == ("lda_lognormal", "lda_lognormal_truncated", "lda_splice", "sla", "sla_mean_corrected", "scenario")
    assert replicate.RUNGS[6:] == NEW
    assert tuple(r["rung_id"] for r in P.LADDER)[6:] == NEW_IDS
    assert all(r["status"] == "SECONDARY_SOURCE" for r in P.LADDER[6:])


def test_each_new_rung_is_the_engines_fit_through_the_engines_mean_adjusted_sla(variants_):
    v = variants_[0.6]
    out = _estimate(v)
    rec = draw_history(v, SEED, YEARS).recorded(THRESHOLD)
    lam = dist.fit_frequency(rec.counts).params[0]
    gpd_mle = dist.fit_severity("gpd", rec.amounts, THRESHOLD, truncated=True)
    for key, fit in (("sla_mean_adjusted", gpd_mle), ("sla_cvm", robust.fit_severity_cvm("gpd", rec.amounts, THRESHOLD)),
                     ("sla_obre", robust.fit_severity_obre("gpd", rec.amounts, THRESHOLD, 0.95))):
        par = (fit.params[0], fit.params[1], THRESHOLD)
        want = robust.sla_var_mean_adjusted(lam, "gpd", par, P.LEVEL).var
        assert np.isfinite(out[key]) and out[key] == want, key
    ln = robust.fit_severity_cvm("lognormal", rec.amounts, THRESHOLD)
    lam_full = dist.rescale_frequency(lam, "lognormal", ln.params, THRESHOLD)
    assert out["sla_cvm_lognormal"] == robust.sla_var_mean_adjusted(lam_full, "lognormal", ln.params, P.LEVEL).var


def test_the_new_rungs_are_computed_not_read_and_a_refused_fit_is_nan_with_its_reason(variants_, monkeypatch):
    v = variants_[0.6]
    base = _estimate(v)
    monkeypatch.setattr(robust, "sla_var_mean_adjusted", lambda *a, **k: type("R", (), {"var": 777.0})())
    out = _estimate(v)
    assert all(out[k] == 777.0 for k in NEW) and base["sla_cvm"] != 777.0
    monkeypatch.undo()

    def refuse(*a, **k):
        raise ValueError("planted refusal")

    monkeypatch.setattr(robust, "fit_severity_obre", refuse)
    out = _estimate(v)
    assert np.isnan(out["sla_obre"]) and "planted refusal" in out["errors"]["sla_obre"]
    assert out["sla_cvm"] == base["sla_cvm"] and out["lda_lognormal_truncated"] == base["lda_lognormal_truncated"]  # the other rungs are untouched


def test_the_estimation_uses_only_the_recorded_history_and_is_deterministic(variants_):
    v = variants_[0.8]
    a, b = _estimate(v), _estimate(v)
    assert all(a[k] == b[k] for k in NEW)
    other = replicate.estimate(v, SEED + 1, YEARS, THRESHOLD, 1.4e9, None, 20_000)
    assert all(a[k] != other[k] for k in NEW)  # another seed, another history, another capital


def test_a_fitted_tail_index_of_one_or_more_leaves_no_mean_adjusted_capital_and_says_why(variants_):
    # at the infinite-mean truth most fits have xi_hat >= 1: the mean-adjusted form does not exist there
    v = variants_[1.1]
    out = [replicate.estimate(v, s, 5, 10_000.0, 1.4e9, None, 20_000) for s in range(40, 52)]
    undefined = [o for o in out if np.isnan(o["sla_mean_adjusted"])]
    assert undefined and all("infinite mean" in o["errors"]["sla_mean_adjusted"] for o in undefined)


def test_the_product_holds_no_robust_formula():
    for f in PKG.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        for pat in (r"1\s*/\s*\(12\s*\*", r"\(2\s*\*\s*i\s*-\s*1\)", r"min\(1\.0,\s*c\s*/"):
            assert not re.search(pat, text), f"{f.name} holds a formula of the engine: {pat}"


def test_the_hypothesis_is_written_before_the_run_with_its_thresholds():
    h = P.S3_HYPOTHESIS
    assert 0.0 < h["refuted_below_share"] < h["holds_at_share"] <= 1.0
    assert h["rungs"] == ["sla-cvm", "sla-obre"] and h["against"] == "lda-splice"
    assert {"en", "es"} <= set(h["statement"])


def test_the_committed_documents_carry_the_new_rungs_in_every_cell_and_the_finding_with_its_verdict():
    for d in DOCS:
        o = load(f"C17/{d}.json")["outputs"]
        for c in o["cells"]:
            for key in NEW:
                slot = c["capital"][key]
                assert (slot["summary"] is None) != (slot["reason"] is None)
                if slot["summary"] is not None:
                    assert slot["summary"]["status"] == "SECONDARY_SOURCE" and slot["summary"]["n_defined"] >= 4
        doc = load(f"C17/{d}.json")
        f5 = [f for f in doc["findings"] if f["id"] == "F-5"]
        assert len(f5) == 1 and re.search(r"holds|refuted|inconclusive", f5[0]["title"]["en"])
        tests = {(t["model_id"], t["segment"]) for t in doc["tests"] if t["test_id"] == "oprisk.capital_stability"}
        assert all((mid, c["id"]) in tests for mid in NEW_IDS[:3] for c in o["cells"] if c["capital"][mid.replace("-", "_")]["summary"])
    ladder = load("C17/models-generator.json")["fit"]["ladder"]
    assert [r["rung_id"] for r in ladder][6:] == list(NEW_IDS)


def test_the_models_document_lists_the_rungs_with_the_engine_and_the_secondary_source_label():
    models = load("C17/models-generator.json")
    ids = [m["id"] for m in models["model"]]
    assert all(i in ids for i in NEW_IDS)
    assert json.dumps(models).count("SECONDARY_SOURCE") >= 4
