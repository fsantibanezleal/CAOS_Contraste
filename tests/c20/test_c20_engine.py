"""CT-2021, CT-2022: the engine pin and the rule that the product alters no engine row; the named parameters."""
from __future__ import annotations

import importlib.metadata as md

from c20_support import ROOT, VARIANTS, committed, semantics, values
from engine_pin import engine_pin_findings, pinned_ref

from pipeline.cases.c20 import bake, conv, ops

RELEASE = "0.8.1"


def test_the_engine_is_pinned_at_the_batch_3_release_tag_that_the_sdd_names() -> None:
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    assert len([ln for ln in req.splitlines() if ln.startswith("riskvalidation")]) == 1 and engine_pin_findings(req, sdd) == []   # the PyPI release the SDD row names
    assert pinned_ref(req) == RELEASE
    assert bake.engine_version() == RELEASE == md.version("riskvalidation")
    for name in VARIANTS:
        assert committed(name)["provenance"]["riskvalidation_version"] == RELEASE


def test_the_product_alters_no_engine_row_it_names_the_segment_and_the_model_only() -> None:
    import numpy as np
    from riskvalidation.validation import ml as mlv
    from riskvalidation.validation.stability import stability_psi

    raw = stability_psi([10.0, 20.0, 30.0], [12.0, 18.0, 30.0])
    named = ops.row(raw, model_id="m", segment="s")
    plain = raw.to_dict()
    assert named["model_id"] == "m" and named["segment"] == "s"
    for k in plain:
        if k not in ("model_id", "segment"):
            assert named[k] == plain[k], k          # the statistic, the light, the alphas and the hash are the engine's
    est = mlv.cbpe_estimate("m", __import__("riskvalidation.ml.cbpe", fromlist=["cbpe_auc"]).cbpe_auc(np.linspace(0.05, 0.9, 50)))
    assert ops.row(est)["light"] == "not_evaluated"
    for name in VARIANTS:                          # the committed rows carry the engine's lights and lines, never one the product wrote
        for r in committed(name)["tests"]:
            assert set(r) >= {"test_id", "light", "alpha_amber", "alpha_red", "inputs_hash", "extras"}
            assert r["light"] in ("green", "amber", "red", "not_evaluated", "error") and r["reference"] and r["h0"]


def test_the_named_parameters_are_the_approved_values_and_the_semantics_agree() -> None:
    sem, v = semantics(), values()
    assert {n: val for n, val, _, _ in conv.PARAMETERS} == sem.APPROVED_PARAMS
    bases = {n: (val, unit, basis) for n, (val, unit, basis) in v.NAMED.items()}
    for n, val, unit, basis in conv.PARAMETERS:
        assert bases[n] == (val, unit, basis), n
    assert [p["name"] for p in conv.parameters_block()] == list(v.C20_NAMES) and all(p["label"] == "convention" for p in conv.parameters_block())
    assert conv.PRESET_EPS in conv.PERTURBATION_GRID and conv.N_SEEDS == 20 and conv.N_BOOTSTRAP_REFITS == 100 and conv.TOP_K == 4
    for name in VARIANTS:
        assert {p["name"]: p["value"] for p in committed(name)["outputs"]["parameters"]} == sem.APPROVED_PARAMS
