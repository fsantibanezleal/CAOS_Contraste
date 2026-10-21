"""CT-1710 to CT-1713: the committed documents of data/derived/C17."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
from c17_semantic import semantic_findings
from c17_support import DERIVED, DOCS, load
from pipeline.cases.c17 import replicate
from pipeline.core.schemas import validate_document
from riskvalidation.oprisk import sma

ALL = [f"C17/{d}.json" for d in DOCS] + ["C17/models-generator.json"]


def test_every_committed_document_validates_passes_the_semantic_gate_and_is_listed_with_its_hash():
    manifest = json.loads((DERIVED / "manifests" / "C17.json").read_text(encoding="utf-8"))
    listed = {a["path"]: a for a in manifest["artifacts"]}
    sums = dict(reversed(line.split("  ")) for line in (DERIVED / "C17" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert set(listed) == set(ALL) and manifest["case_id"] == "C17" and manifest["default_variant"] in DOCS
    for rel in ALL:
        raw = (DERIVED / rel).read_bytes()
        doc = json.loads(raw)
        validate_document(f"data/derived/{rel}", doc)
        assert semantic_findings(doc) == [], (rel, semantic_findings(doc))
        assert listed[rel]["bytes"] == len(raw)
        assert sums[rel] == hashlib.sha256(raw).hexdigest()
        assert doc["provenance"]["truth_status"] == "synthetic-known-truth"


def test_a_tail_index_of_one_or_more_states_no_mean_and_every_document_carries_its_truth():
    for d in DOCS:
        o = load(f"C17/{d}.json")["outputs"]
        t = o["truth"]
        assert t["label"] == "synthetic-known-truth" and t["annual_loss_quantile"]["value_eur"] > 0 and t["severity"]["law"] == "gpd"
        assert t["frequency"]["lambda_per_year"] > 0 and t["annual_loss_quantile"]["mc_check"]["agrees"] is True
        if o["tail_index"] >= 1.0:
            assert o["infinite_mean"] is True and t["annual_loss_mean"]["value_eur"] is None and t["annual_loss_mean"]["reason"]
            for c in o["cells"]:
                assert c["capital"]["sla_mean_corrected"]["summary"] is None and c["capital"]["sla_mean_corrected"]["reason"]
            assert "shortfall" not in json.dumps(o).lower()  # no expected shortfall anywhere
        else:
            assert o["infinite_mean"] is False and t["annual_loss_mean"]["value_eur"] > 0
            assert all(c["capital"]["sla_mean_corrected"]["summary"]["status"] == "UNVERIFIED" for c in o["cells"] if c["capital"]["sla_mean_corrected"]["summary"])
    m = load("C17/models-generator.json")["fit"]["variants"]
    assert [x["infinite_mean"] for x in m] == [False, False, False, True] and m[3]["true_mean_eur"] is None


def test_an_ilm_is_never_computed_on_fewer_than_five_years(variants_):
    for d in DOCS:
        o = load(f"C17/{d}.json")["outputs"]
        assert sorted({c["years"] for c in o["cells"]}) == [5, 10]
        assert all(c["sma"]["basis"] == "bic-times-ilm" for c in o["cells"])
    res = sma.sma_capital(1.4e9, np.full(3, 5e7))
    assert res.basis == "bic-only" and res.ilm is None and res.reason and res.discretion_applied == "transitional-bic-only"
    with pytest.raises(ValueError):
        sma.sma_capital(1.4e9, np.full(4, 5e7), minimum_years=3)
    v = variants_[0.8]
    with pytest.raises(ValueError):
        replicate.estimate(v, 3, 3, 20_000.0, 1.4e9, None, 20_000)


def test_no_text_presents_the_synthetic_bank_as_real():
    for rel in ALL:
        doc = load(rel)
        text = json.dumps(doc, ensure_ascii=False)
        assert "synthetic" in text.lower() and doc["provenance"]["truth_status"] == "synthetic-known-truth"
        if "outputs" in doc:
            o = doc["outputs"]
            assert o["bank"]["synthetic"] is True and "describes no real bank" in o["bank"]["notice"]["en"]
            assert o["calibration"]["targets"]["label"] == "derived-only" and "describe no real one" in o["calibration"]["targets"]["caveat"]["en"]
        else:
            assert doc["fit"]["calibration"]["label"] == "derived-only" and "no real bank" in doc["fit"]["generator"]["notice"]["en"]
