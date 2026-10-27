"""U16-F10b (fix round 4, the R3 capture review of C02, batch c03): the producer's texts a Spanish view prints are Spanish and
carry no raw id, tested on the producer's functions and on the planted bake in memory (the committed documents are re-baked by the
integrator, never here).

- B2: the named parameter's unit and basis are bilingual texts (the Spanish table printed "0,05 AUC points" and an English basis).
- B3: the ladder's engine is a bilingual text ("own on optbinning" in the Spanish Context).
- B4: the pooled event names the files, not the variant ids ("h1 to h5").
- m3: no plan decision id in a reader text ("decision V6", "(decision Q9)", "(decisión G22)").
- m2: the Spanish texts of the case say "tarjeta de puntuación", not "scorecard"; "bake" and "and" are not Spanish words.
"""
from __future__ import annotations

import re
from types import SimpleNamespace

import numpy as np
import pytest
from c02_support import ROOT  # noqa: F401  (puts the pipeline and the contract test folders on the path)

import contract_schemas as cs
from pipeline.cases.c02 import blocks, models
from pipeline.cases.c02 import conventions as cv

DECISION_ID = re.compile(r"\b(?:decision|decisión)\s+[A-Z]\d+\b|\((?:decision|decisión)\s+[A-Z]\d+\)")
VARIANT_ID = re.compile(r"\bh[1-5]\b")


def _bitext(x: object) -> bool:
    return isinstance(x, dict) and set(x) == {"en", "es"} and all(isinstance(v, str) and v for v in x.values())


def test_b2_the_named_parameter_unit_and_basis_are_bilingual_and_name_no_decision() -> None:
    (p,) = cv.parameters()
    assert _bitext(p["unit"]) and _bitext(p["basis"]), p
    assert p["unit"] == {"en": "AUC points", "es": "puntos de AUC"}
    assert "Train minus test AUC gap" in p["basis"]["en"]                     # the English wording keeps its sense
    assert "AUC" in p["basis"]["es"] and "Train minus" not in p["basis"]["es"] and " gap " not in p["basis"]["es"]
    assert "entre 1,5 y 3" in p["basis"]["es"]                                # Spanish numbers
    for text in p["basis"].values():
        assert not DECISION_ID.search(text), text
        assert "V6" not in text, text


def test_b3_the_ladder_engine_is_bilingual_and_the_library_names_stay() -> None:
    assert models.engine_text("own") == {"en": "own", "es": "propio"}
    assert models.engine_text("own on optbinning") == {"en": "own on optbinning", "es": "propio sobre optbinning"}
    assert models.engine_text("scikit-learn trees and LogisticRegression, own rule extraction")["es"] == (
        "árboles y regresión logística de scikit-learn, extracción de reglas propia")
    for name in ("optbinning + statsmodels Logit", "scikit-learn LogisticRegression", "InterpretML ExplainableBoostingClassifier", "LightGBM", "XGBoost"):
        assert models.engine_text(name) == {"en": name, "es": name}
    with pytest.raises(KeyError):
        models.engine_text("a new engine nobody named")


def test_b3_fit_document_writes_the_bilingual_engine() -> None:
    rung = SimpleNamespace(title={"en": "Single variable", "es": "Una variable"}, engine="own on optbinning")
    fit = SimpleNamespace(rungs={"P0-single": rung}, horizon_id="h1", years=1, file="5year", y=np.array([0, 1, 0]))
    doc = models.fit_document({"h1": fit}, {"protocol": "planted"})
    assert doc["ladder"][0]["engine"] == {"en": "own on optbinning", "es": "propio sobre optbinning"}
    assert _bitext(doc["parameters"][0]["basis"])


def test_b4_the_pooled_event_names_the_files_not_the_variant_ids() -> None:
    for lang, text in cv.POOLED_EVENT.items():
        assert not VARIANT_ID.search(text), (lang, text)
    assert "1-year to 5-year files" in cv.POOLED_EVENT["en"]
    assert "archivos de 1 a 5 años" in cv.POOLED_EVENT["es"]


def test_m3_no_reader_text_names_a_plan_decision() -> None:
    texts = [cv.TERM_STRUCTURE_REASON, cv.IMPACT_REASON, cv.MAPPING_NOTE, cv.OBSERVATION_DATE_NOTE, cv.TRANSFER_REASON]
    _, reason = blocks.term_structure({k: 100 for k in range(1, 6)}, {1: 9, 2: 8, 3: 7, 4: 6, 5: 5})
    texts.append(reason)
    for t in texts:
        for lang, text in t.items():
            assert not DECISION_ID.search(text), (lang, text)
    # the mapping note names the horizons, not the variant ids
    for text in cv.MAPPING_NOTE.values():
        assert not VARIANT_ID.search(text), text


def test_m2_the_spanish_texts_use_spanish_words() -> None:
    for t in (cv.MAPPING_NOTE, cv.PAPER_READING):
        es = t["es"]
        assert "scorecard" not in es.lower() and " bake " not in es and " and " not in es, es
    assert "tarjeta de puntuación" in cv.MAPPING_NOTE["es"]


def test_the_producer_documents_validate_against_the_bumped_schemas(built) -> None:
    """The produced side of c02-outputs 3.0.0 and c02-models 2.0.0: the planted bake's documents, in memory, validate."""
    docs, fit = built.variants, built.models
    for vid, doc in docs.items():
        assert cs.errors("c02/variant-horizon", doc) == [], vid
        (p,) = doc["outputs"]["parameters"]
        assert _bitext(p["unit"]) and _bitext(p["basis"]), vid
    assert cs.errors("c02/models", fit) == []
    assert all(_bitext(r["engine"]) for r in fit["fit"]["ladder"])
    assert docs["pooled"]["outputs"]["counts"]["event_definition"] == cv.POOLED_EVENT


def test_the_schemas_still_accept_a_committed_string_and_refuse_a_number() -> None:
    """Until the integrator re-bakes, a committed document carries the string form; anything else is refused."""
    doc = cs.load_json(cs.DERIVED / "C02" / "h1.json")
    assert cs.errors("c02/variant-horizon", doc) == []
    doc["outputs"]["parameters"][0]["unit"] = 5
    assert cs.errors("c02/variant-horizon", doc) != []
    fit = cs.load_json(cs.DERIVED / "C02" / "models-polish-horizons.json")
    fit["fit"]["ladder"][0]["engine"] = {"en": "own"}
    assert cs.errors("c02/models", fit) != []
