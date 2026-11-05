"""U16-I (engine-governance-api 1.1.0): the Spanish of every engine reason comes from ``riskvalidation.governance.reasons.bilingual`` and the
accented text of the engine; the 0.15.000 stopgap (``pipeline/governance/spanish.py``) is gone."""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[2] / "data-pipeline" / "pipeline" / "governance"


def test_the_stopgap_module_is_gone_and_nothing_imports_it():
    assert importlib.util.find_spec("pipeline.governance.spanish") is None
    assert not (PIPELINE / "spanish.py").exists()
    for path in PIPELINE.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bspanish\b\s*(\.|,|$)|import spanish|from \.spanish", text, flags=re.M), path.name


def test_the_scope_rationales_are_the_engine_bilingual_pair(baked):
    from riskvalidation.governance.reasons import bilingual

    n = 0
    for entry in baked.inventory["entries"]:
        for prof in entry["scope"]["profiles"]:
            assert prof["rationale"] == bilingual(prof["rationale"]["en"]), (entry["key"], prof["profile"])
            n += 1
    assert n >= 12


def test_the_anchor_and_share_reasons_are_the_engine_bilingual_pair_in_reader_words(baked):
    """The engine's bilingual pair, read through pipeline.governance.reader (U16-F10p, R3 c23 B3: no `test_id@model` developer text)."""
    import re

    from pipeline.governance.reader import reader_text

    seen = 0
    for row in baked.findings["rows"]:
        for field in ("anchor_reason", "rwea_share_reason"):
            if row[field] is not None:
                assert row[field] == reader_text(row[field]), (row["key"], field)
                assert row[field]["es"] != row[field]["en"], (row["key"], field)
                assert not re.search(r"test_id@|risk_accepted|dim_cube|spec\(", row[field]["en"] + row[field]["es"]), (row["key"], field)
                seen += 1
    assert seen > 0


def test_an_excluded_variant_states_the_engine_spanish_of_its_reason(baked):
    from riskvalidation.governance.reasons import bilingual

    prefix = "no fit can be assigned to the variant: "
    seen = 0
    for ex in baked.inventory["excluded"]:
        en = ex["reason"]["en"]
        if not en.startswith(prefix):
            continue
        why = en[len(prefix):].rsplit("; its ", 1)[0]
        assert ex["reason"]["es"].startswith("no se puede asignar un ajuste a la variante: " + bilingual(why)["es"] + ";"), ex
        seen += 1
    assert seen > 0


def test_the_engine_reasons_the_bake_reads_all_have_a_code():
    """Every reason sentence the bake can meet is in the engine table: an unknown sentence stops the bake (ValueError), never an English text on the Spanish side."""
    import pytest
    from riskvalidation.governance.reasons import bilingual

    with pytest.raises(ValueError):
        bilingual("a sentence the engine table does not hold")


def test_a_model_id_inside_a_spanish_text_is_never_accented(baked):
    """The 0.15.000 stopgap turned the id `hmda-logistic-decision` of the C21 report into `hmda-logistic-decisión`; the engine's text keeps an identifier verbatim."""
    seen = 0
    for rep in baked.reports.values():
        text = json.dumps(rep, ensure_ascii=False)
        assert "hmda-logistic-decisión" not in text
        seen += text.count("hmda-logistic-decision")
    assert seen > 0
