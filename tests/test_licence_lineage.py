"""Licence lineage and provenance: CT-002 and CT-003, through the contract-2 builder every export uses."""
from __future__ import annotations

import pytest

from pipeline.core import lineage as lin
from pipeline.core import manifest as m
from pipeline.io import sources as s

MAN = {"schema": "contraste.licence-manifest/v1", "sources": {
    "uci-taiwan": {"files": [{"name": "default+of+credit+card+clients.zip", "sha256": "a" * 64}]},
    "fannie-mae-sflp": {"files": [{"name": "x.zip", "sha256": "b" * 64}]},
}}


def _test_row(test_id="pd.jeffreys", light="green"):
    return {k: None for k in m.TEST_RESULT_KEYS} | {
        "test_id": test_id, "h0": "PD is correctly calibrated", "reference": "ECB (2019) 2.5.3.1",
        "policy_version": "2026.10.0", "light": light, "p_value": 0.4, "alternative": "", "inputs_hash": "",
        "notes": "", "extras": {}}


MODEL = [{"id": "scorecard", "family": "pd-scoring", "rung": 1, "title": {"en": "Scorecard", "es": "Scorecard"},
          "short_title": {"en": "P1 Scorecard", "es": "P1 Scorecard"},
          "engine": "optbinning", "engine_version": "0.21.0", "licence": "Apache-2.0", "checkpoint_sha256": "c" * 64,
          "calibration": None, "parameters": {"pdo": {"value": 20, "unit": "points"}}}]
IMPACT = {"rwa": {"value": 1.5e6, "unit": "NTD", "label": {"en": "RWA", "es": "APR"}}}
FINDING = [{"id": "F1", "severity": "S3", "status": "open", "evidence": ["pd.jeffreys"],
            "title": {"en": "Calibration drift", "es": "Deriva de calibración"}}]
LANE = {"lane": "precompute", "reasons": ["GBM scores are replayed"]}


def _lineage(sources, truth="real-outcomes"):
    return lin.build("C01", sources=sources, truth_status=truth, seed=42, code_version="test-build",
                     riskvalidation_version="0.1.0", manifest=MAN)


def _artifact(lineage):
    return m.build_artifact(case_id="C01", variant_id="holdout", model=MODEL, outputs={"roc": {"fpr": [0, 1]}},
                            tests=[_test_row()], impact=IMPACT, findings=FINDING, lineage=lineage, lane=LANE)


def test_refuses_link_only_source():
    with pytest.raises(s.LicenceError, match="fannie-mae-sflp is link-only"):
        _artifact(_lineage(["uci-taiwan", "fannie-mae-sflp"]))
    with pytest.raises(s.LicenceError, match="not in the licence manifest"):
        _artifact(_lineage(["uci-german"]))  # readable, but never fetched: no hashes to vouch for it
    with pytest.raises(s.LicenceError, match="unknown source"):
        _lineage(["nowhere"])


def test_export_writes_provenance():
    art = _artifact(_lineage(["uci-taiwan"]))
    prov = art["provenance"]
    assert prov["truth_status"] == "real-outcomes"
    assert prov["licence_classes"] == {"uci-taiwan": "mirror-allowed"}
    assert prov["inputs"][0]["files"][0]["sha256"] == "a" * 64
    assert prov["seed"] == 42 and prov["riskvalidation_version"] == "0.1.0"
    assert set(art) == {"schema", "case_id", "variant_id", "model", "outputs", "tests", "impact", "findings",
                        "provenance", "lane"}
    with pytest.raises(ValueError, match="truth status"):
        _lineage(["uci-taiwan"], truth="real")


def test_findings_cite_tests_by_model_and_segment_or_a_stated_limit():
    row = _test_row() | {"model_id": "P1", "segment": "holdout"}
    finding = FINDING[0] | {"evidence": ["pd.jeffreys@P1", "pd.jeffreys@P1@holdout", "design:single-snapshot",
                                         "contract:C01-PAY-CODE"]}
    art = m.build_artifact(case_id="C01", variant_id="holdout", model=MODEL, outputs={}, tests=[row], impact=IMPACT,
                           findings=[finding], lineage=_lineage(["uci-taiwan"]), lane=LANE)
    assert art["findings"][0]["evidence"][0] == "pd.jeffreys@P1"


def test_rate_evidence_names_a_simulation():
    """CT-305: a finding may cite a measured rate of the artifact (rate:<key> of outputs.simulations), never one that
    is not there."""
    outputs = {"simulations": [{"key": "pd.hosmer_lemeshow@fitted", "rates": {}}]}
    kw = dict(case_id="C01", variant_id="holdout", model=MODEL, outputs=outputs, tests=[_test_row()], impact=IMPACT,
              lineage=_lineage(["uci-taiwan"]), lane=LANE)
    art = m.build_artifact(findings=[FINDING[0] | {"evidence": ["rate:pd.hosmer_lemeshow@fitted"]}], **kw)
    assert art["findings"][0]["evidence"] == ["rate:pd.hosmer_lemeshow@fitted"]
    with pytest.raises(m.ContractViolation, match="cites rates not in this artifact"):
        m.build_artifact(findings=[FINDING[0] | {"evidence": ["rate:pd.spiegelhalter@null"]}], **kw)
    with pytest.raises(m.ContractViolation, match="cites rates not in this artifact"):
        m.build_artifact(**(kw | {"outputs": {}}), findings=[FINDING[0] | {"evidence": ["rate:pd.hosmer_lemeshow@fitted"]}])


def test_models_artifact_carries_its_fit_and_provenance():
    doc = m.build_models_artifact(case_id="C01", fit_id="taiwan", model=MODEL, fit={"n_train": 16800},
                                  lineage=_lineage(["uci-taiwan"]), lane=LANE)
    assert doc["schema"] == m.MODELS_SCHEMA and doc["fit"] == {"n_train": 16800}
    assert doc["provenance"]["licence_classes"] == {"uci-taiwan": "mirror-allowed"}
    with pytest.raises(s.LicenceError):
        m.build_models_artifact(case_id="C01", fit_id="x", model=MODEL, fit={},
                                lineage=_lineage(["fannie-mae-sflp"]), lane=LANE)


def test_generated_inputs_need_no_source():
    gen = lin.build("C22", sources=(), truth_status="synthetic-known-truth", seed=1, code_version="test-build",
                    generators=("vasicek-portfolio",), manifest=MAN)
    lin.assert_publishable(gen)
    assert gen.provenance()["generators"] == ["vasicek-portfolio"]
    with pytest.raises(ValueError, match="at least one source or generator"):
        lin.build("C22", sources=(), truth_status="synthetic-known-truth", seed=1, code_version="x", manifest=MAN)


@pytest.mark.parametrize("bad,match", [
    ({"tests": [{"test_id": "x"}]}, "is not a TestResult"),
    ({"tests": [_test_row(light="blue")]}, "light 'blue'"),
    ({"findings": [FINDING[0] | {"severity": "S5"}]}, "S1 to S4"),
    ({"findings": [FINDING[0] | {"evidence": ["pd.binomial"]}]}, "cites tests not in this artifact"),
    ({"findings": [FINDING[0] | {"evidence": ["pd.jeffreys@P9"]}]}, "cites tests not in this artifact"),
    ({"model": []}, "at least one model"),
    ({"impact": {"rwa": {"value": float("nan"), "unit": "x", "label": {"en": "a", "es": "b"}}}}, "not finite"),
    ({"lane": {"lane": "replay"}}, "lane 'replay'"),
])
def test_contract_two_refuses_a_malformed_artifact(bad, match):
    kw = dict(case_id="C01", variant_id="holdout", model=MODEL, outputs={}, tests=[_test_row()], impact=IMPACT,
              findings=FINDING, lineage=_lineage(["uci-taiwan"]), lane=LANE) | bad
    with pytest.raises(m.ContractViolation, match=match):
        m.build_artifact(**kw)
