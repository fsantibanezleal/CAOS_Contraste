"""U16-F10d (fix round 4, R3 c13): the C12 producer texts a reader sees name the horizons, the initial-margin bound and ORE's
output in words (no horizon code, JSON key, ORE file name or internal decision id), carry the estimator in both languages,
and write the Spanish without the English words of the 2026-10-27 ruling (proxy, hazard, backtest)."""
from __future__ import annotations

import re

from pipeline.cases.c12 import backtest, bake, calibration, models, variant

RULED = re.compile(r"\b(proxy|proxies|hazard|backtest\w*|back-test\w*)\b", re.IGNORECASE)
HORIZON_CODE = re.compile(r"\b(10bd|20bd|1m|3m|6m|12m)\b")


def test_bl1_the_pit_note_names_the_horizon_in_words() -> None:
    """BL1: "W^2 is above the simulated 5 percent critical value the book at the 10bd horizon" printed the horizon id."""
    engine = "W^2 is above the simulated 5 percent critical value"
    for h, words in (("10bd", "10 business days"), ("20bd", "20 business days"), ("1m", "1 month"), ("3m", "3 months"),
                     ("6m", "6 months"), ("12m", "12 months")):
        for tag in ("book", "risk factor"):
            note = backtest.pit_note(engine, tag, h)
            assert not HORIZON_CODE.search(note), note
            assert note == f"{engine} for the {tag} at the horizon of {words}", note
    # a row the engine wrote no note for keeps only the measure and the horizon
    assert backtest.pit_note("", "book", "1m") == "for the book at the horizon of 1 month"


def test_bl2_the_initial_margin_limit_states_the_bound_in_words() -> None:
    """BL2: ``ee_vm_only``, `dim` and "decision B2" in the with-im read-out (the repeated "a regression proxy, not SIMM" is
    the view's, which now leaves the sentence to this limit)."""
    for lang in ("en", "es"):
        t = variant.IM_LIMIT[lang]
        for raw in ("ee_vm_only", "`dim`", "decision B2", "decisión B2", "B2"):
            assert raw not in t, (lang, raw)
        assert t.count("SIMM") == 1, (lang, t)
    assert variant.IM_LIMIT["en"].startswith("A regression proxy, never SIMM.")
    assert variant.IM_LIMIT["es"].startswith("Una aproximación por regresión, nunca SIMM.")
    assert "between the EE with variation margin only less the mean DIM (floored at 0) and the EE with variation margin only" in variant.IM_LIMIT["en"]
    assert "entre la EE con solo margen de variación menos el DIM medio (con piso en 0) y la EE con solo margen de variación" in variant.IM_LIMIT["es"]


def test_bl3_the_dim_finding_names_orees_margin_not_its_file() -> None:
    """BL3: "1 red row on the mean initial margin against ORE's dim_cube"."""
    en, es = variant.WHAT["ccr.ore_dim_agreement"]
    assert "dim_cube" not in en and "dim_cube" not in es
    assert en == "the mean initial margin against ORE's dynamic initial margin"
    assert es == "el margen inicial medio frente al margen inicial dinámico de ORE"
    title = variant.findings_of([{"test_id": "ccr.ore_dim_agreement", "model_id": "hw1f-exposure", "segment": None, "light": "red"}])[0]["title"]
    assert "dim_cube" not in title["en"] and "dim_cube" not in title["es"]


def test_bl4_the_fit_carries_the_estimator_in_both_languages() -> None:
    """BL4: the Spanish Context printed the English estimator sentence (``fit.estimator`` was English only)."""
    est = models.fit_block([])["estimator"]
    assert est == calibration.ESTIMATOR_TEXT
    assert est["en"] == calibration.ESTIMATOR  # the English sentence is unchanged; every calibration record keeps it
    assert est["es"] == "AR(1) exacto por MCO sobre la tasa cero más corta del Tesoro (Brigo et al., arXiv 0812.4210, ecuaciones 55 a 57)"


def test_the_spanish_texts_have_no_ruled_english_word() -> None:
    """The 2026-10-27 ruling: proxy, hazard and backtest are translated in Spanish text."""
    texts = [variant.IM_LIMIT["es"], variant.not_applicable_ore()["reason"]["es"], *(t["es"] for t in models.LIMITS)]
    texts += [es for _, _, _, es in bake.TITLES.values()]
    texts += [es for _, es in variant.WHAT.values()]
    for t in texts:
        assert not RULED.search(t), t
