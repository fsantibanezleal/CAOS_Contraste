"""U16-F2 (the R2 fix round, C07): bilingual reasons and sources, Spanish finding titles with Spanish light words and numbers."""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C07 = ROOT / "data" / "derived" / "C07"
VARIANTS = sorted(p for p in glob.glob(str(C07 / "*.json")) if "models-" not in Path(p).name)
ENGLISH_LIGHT = re.compile(r"\((red|amber|green)\)")
ENGLISH_NUMBER = re.compile(r"\d,\d{3}\b|\b\d+\.\d+\b")


def _bitext(x: object) -> bool:
    return isinstance(x, dict) and set(x) == {"en", "es"} and all(isinstance(v, str) and v for v in x.values())


def test_the_group_max_rule_reason_is_a_bilingual_text() -> None:
    """PR-C07-1 (b04 B1): an English 30-word sentence repeated in the Spanish Interno column."""
    assert VARIANTS
    for path in VARIANTS:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))["outputs"]["b1_detail"]["group_max_rule"]
        for r in rows:
            assert r["internal"] is None and _bitext(r["internal_reason"]), path
            assert "no tiene método interno" in r["internal_reason"]["es"], path


def test_spanish_finding_titles_have_spanish_light_words_and_numbers() -> None:
    """PR-C07-2 (b04 B4, M1): '(amber)', '3.0 veces', 'complemento 0.0 millones CLP'."""
    for path in VARIANTS:
        for f in json.loads(Path(path).read_text(encoding="utf-8"))["findings"]:
            es = f["title"]["es"]
            assert not ENGLISH_LIGHT.search(es), (path, f["id"], es)
            assert not ENGLISH_NUMBER.search(es), (path, f["id"], es)


def test_the_b1_table_sources_are_bilingual() -> None:
    """V07-1 (b04 B2): the table caption printed an English plain string."""
    fit = json.loads((C07 / "models-banco-andino.json").read_text(encoding="utf-8"))["fit"]
    assert len(fit["b1_tables"]) == 4
    for t in fit["b1_tables"]:
        assert _bitext(t["source"]) and "Capítulo B-1" in t["source"]["es"], t["table_id"]
