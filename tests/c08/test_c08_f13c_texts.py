"""U16-F13c (R5 batch c11, C08): every model of the ladder carries one name, the one every C08 view prints, in both languages, so a
finding that names a model by its short title never shows English body text in a Spanish view (B1: "L4 Hurdle") nor a second name
for the same model (n1: "L1 OLS" beside "Linear regression"). Tested on the producer's tables and record function."""
from __future__ import annotations

from types import SimpleNamespace

from pipeline.cases.c08 import build as bd
from pipeline.cases.c08 import models

#: the words of `frontend/src/workbench/c08/selection.ts` KIND_TEXT, which every C08 view prints for a model
VIEW_NAMES = {
    "L1-ols": ("Linear regression", "Regresión lineal"),
    "L2-fractional-logit": ("Fractional logit", "Logit fraccional"),
    "L3-beta": ("Beta regression", "Regresión beta"),
    "L4-hurdle": ("Two-stage hurdle", "Modelo en dos etapas"),
    "L5-gradient-boosted": ("Gradient boosting", "Árboles potenciados por gradiente"),
    "L6-tobit": ("Tobit", "Tobit"),
}


def test_every_short_title_is_the_name_the_views_print():
    assert set(bd.RUNG_TEXT) == set(VIEW_NAMES)
    for rid, (en, es) in VIEW_NAMES.items():
        assert bd.RUNG_TEXT[rid][1] == (en, es), rid


def test_no_spanish_short_title_repeats_an_english_word():
    for rid, (_title, (en, es)) in bd.RUNG_TEXT.items():
        assert "Hurdle" not in es and "hurdle" not in es, rid
        assert "OLS" not in es and "Boosted" not in es, rid


def test_the_model_records_carry_the_view_names():
    """The record function writes the short title from RUNG_TEXT: the generic findings and the names module read it there."""
    rungs = {rid: SimpleNamespace(rung_id=rid, kind=kind, evaluated=False, fit=None, reason="not fitted", library="riskvalidation",
                                  library_version="0") for rid, kind in models.RUNGS}
    scaler = SimpleNamespace(mean=[0.0] * len(models.CONTINUOUS), std=[1.0] * len(models.CONTINUOUS))
    res = SimpleNamespace(ladder=SimpleNamespace(rungs=rungs, n_fitted=10, n_out_of_range=0, scaler=scaler, beta_by_epsilon={}))
    recs = {r["id"]: r for r in models.model_records(res)}
    for rid, (en, es) in VIEW_NAMES.items():
        assert recs[rid]["short_title"] == {"en": en, "es": es}, rid
