"""Contract 2, the case manifest and the index, and the expected ranges every case declares."""
from __future__ import annotations

import pytest

from pipeline.core import expect
from pipeline.core import manifest as m

T = {"en": "Retail cards PD", "es": "PD de tarjetas"}
VARIANT = {"role": "variant", "variant_id": "holdout", "title": {"en": "Holdout", "es": "Muestra reservada"},
           "short_title": {"en": "Holdout", "es": "Reservada"},
           "regime": {"en": "As observed", "es": "Tal como se observa"}, "truth_status": "real-outcomes",
           "path": "C01/holdout.json", "bytes": 1234, "lane": "precompute", "gate": {"lane": "precompute"},
           "models_ref": "C01/models-taiwan.json"}
MODELS = {"role": "models", "variant_id": "models-taiwan", "title": {"en": "Models", "es": "Modelos"},
          "short_title": {"en": "Models", "es": "Modelos"},
          "regime": {"en": "Fitted on the training slice", "es": "Ajustados en el tramo de entrenamiento"},
          "truth_status": "real-outcomes", "path": "C01/models-taiwan.json", "bytes": 99, "lane": "precompute",
          "gate": {"lane": "precompute"}}


def _manifest(**over):
    kw = dict(case_id="C01", title=T, category={"en": "Credit scoring", "es": "Scoring de crédito"},
              question={"en": "Does the challenger beat the champion?", "es": "¿Supera el retador al campeón?"},
              sources=["uci-taiwan"], seed=42, variants=[MODELS, VARIANT], default_variant="holdout",
              contract={"family": "scored_sample", "counts": {"input": 1}}, expect={"auc": (0.70, 0.80)},
              riskvalidation_version="0.1.0", source_details={"uci-taiwan": {"name": "x", "publisher": "y", "landing": "https://x", "licence": "CC BY 4.0", "class": "mirror-allowed", "attribution": "z"}}) | over
    return m.build_case_manifest(**kw)


def test_manifest_shape_and_checks():
    man = _manifest()
    assert man["schema"] == m.MANIFEST_SCHEMA and man["artifacts"][1]["path"] == "C01/holdout.json"
    assert man["expect"] == {"auc": [0.70, 0.80]}
    with pytest.raises(m.ContractViolation, match="default variant"):
        _manifest(default_variant="drift")
    with pytest.raises(m.ContractViolation, match="lane and the gate verdict disagree"):
        _manifest(variants=[MODELS, VARIANT | {"gate": {"lane": "live"}}])
    with pytest.raises(m.ContractViolation, match="variant ids repeat"):
        _manifest(variants=[MODELS, VARIANT, VARIANT])
    with pytest.raises(m.ContractViolation, match="models_ref names no models artifact"):
        _manifest(variants=[VARIANT])
    with pytest.raises(m.ContractViolation, match="has a role"):
        _manifest(variants=[MODELS, VARIANT | {"role": "extra"}])
    with pytest.raises(m.ContractViolation, match="both non-empty"):
        _manifest(question={"en": "only English"})
    with pytest.raises(m.ContractViolation, match="no expected range"):
        _manifest(expect={})


def test_index_names_a_baked_default_case():
    entries = [{"case_id": "C01", "title": T, "category": T, "manifest_path": "manifests/C01.json"}]
    idx = m.build_index(entries, "C01")
    assert idx["schema"] == m.INDEX_SCHEMA and idx["n_cases"] == 1 and idx["default_case"] == "C01"
    with pytest.raises(m.ContractViolation, match="default case"):
        m.build_index(entries, "C02")


def test_a_value_outside_its_range_is_named():
    assert expect.check("C01", {"auc": (0.7, 0.8)}, {"auc": 0.75, "ks": 0.4}) == {"auc": [0.7, 0.8]}
    with pytest.raises(expect.ExpectationError, match=r"auc=0\.65 outside \[0\.7, 0\.8\]"):
        expect.check("C01", {"auc": (0.7, 0.8)}, {"auc": 0.65})
    with pytest.raises(expect.ExpectationError, match="unknown expected result"):
        expect.check("C01", {"gini": (0.4, 0.6)}, {"auc": 0.75})
    with pytest.raises(expect.ExpectationError, match="outside"):
        expect.check("C01", {"auc": (0.7, 0.8)}, {"auc": float("nan")})
