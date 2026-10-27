"""U16-F10d (fix round 4, R3 c15): the C14 producer texts a Spanish reader sees are bilingual at the source (the call-report
provenance, the shock-shape reference, the slotting assumption of every item), no engine function name prints in a slotting cell,
the wholesale deposit lines state their own derivation, and the breach finding says the threshold was exceeded."""
from __future__ import annotations

import inspect

from c14_sample import report

from pipeline.cases.c14 import assumptions, bake, models, slotting, variant

FD = {"url": "https://api.fdic.gov/banks/financials?filters=CERT%3A24735&limit=100", "name": "financials-cert24735-20121231-20221231.json",
      "sha256": "03b036abc5ff" + "0" * 52, "retrieved": "2026-10-14"}


def test_b2_the_call_report_source_is_bilingual() -> None:
    """B2: "(file ..., sha256 ..., retrieved 2026-10-14)" printed English words in the Spanish Context."""
    src = bake.report_source(FD)
    assert src["en"] == f"{FD['url']} (file {FD['name']}, sha256 03b036abc5ff, retrieved 2026-10-14)"
    assert src["es"] == f"{FD['url']} (archivo {FD['name']}, sha256 03b036abc5ff, obtenido el 2026-10-14)"
    for word in ("file ", "retrieved"):
        assert word not in src["es"]


def test_b3_the_shock_shape_reference_is_bilingual() -> None:
    """B3: "SRP31.91 to SRP31.92" in the Spanish Shock shapes view."""
    assert models.SHOCK_SHAPE["reference"] == {"en": "SRP31.91 to SRP31.92", "es": "SRP31.91 a SRP31.92"}


def test_b4_n1_every_slotting_assumption_is_bilingual_names_no_engine_function_and_the_wholesale_lines_their_own_share() -> None:
    """B4: ``nmd_split`` in the slotting cells; n1: the wholesale lines said "the reported deposits times the retail share"."""
    items = slotting.build_items(report(), assumptions.REQUESTS)
    for i in items:
        assert isinstance(i.slotting_assumption, dict) and set(i.slotting_assumption) == {"en", "es"}, i.item_id
        for lang in ("en", "es"):
            assert i.slotting_assumption[lang] and "nmd_split" not in i.slotting_assumption[lang], (i.item_id, lang)
            assert " x " not in i.slotting_assumption[lang] or lang == "en", (i.item_id, lang)
    by = {i.item_id: i for i in items}
    for k in ("L1", "L2", "L3", "L4"):
        assert "the engine's NMD split" in by[k].slotting_assumption["en"]
        assert "la división NMD del motor" in by[k].slotting_assumption["es"]
    for k in ("L1", "L3"):
        assert "times the retail share" in by[k].reason_missing["en"] and "por la proporción minorista" in by[k].reason_missing["es"]
    for k in ("L2", "L4"):
        assert "times the retail share" not in by[k].reason_missing["en"]
        assert "times one minus the retail share" in by[k].reason_missing["en"]
        assert "por uno menos la proporción minorista" in by[k].reason_missing["es"]
    assert by["A1"].slotting_assumption == {"en": "overnight bucket", "es": "tramo a la vista"}
    assert by["A7"].slotting_assumption["es"].endswith("al CPR base de 0,08 al año"), by["A7"].slotting_assumption["es"]


def test_m4_the_breach_finding_says_the_threshold_was_exceeded() -> None:
    """m4: "en que se superó la prueba" reads as passing the test."""
    src = inspect.getsource(variant._findings)
    assert "se superó la prueba" not in src
    assert "en que se excedió el umbral de la prueba de valores " in src and "atípicos estandarizada" in src
