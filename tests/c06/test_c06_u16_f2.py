"""U16-F2 (the R2 fix round, C06): Spanish finding titles with Spanish light words and numbers; the reasons the views print are bilingual."""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = sorted(glob.glob(str(ROOT / "data" / "derived" / "C06" / "rd-*.json")))
ENGLISH_LIGHT = re.compile(r"\((red|amber|green)\)|\b(red|amber|green)\b")
ENGLISH_NUMBER = re.compile(r"\d,\d{3}\b|\b\d+\.\d+\b")


def _bitext(x: object) -> bool:
    return isinstance(x, dict) and set(x) == {"en", "es"} and all(isinstance(v, str) and v for v in x.values())


def test_there_are_six_reporting_dates() -> None:
    assert len(DOCS) == 6


def test_spanish_finding_titles_have_spanish_light_words_and_numbers() -> None:
    """PR-C06 (b03 B2): '(red)', 'amber (métrica 2)', '19.4 puntos', '49,856 cuentas' in Spanish titles."""
    seen = 0
    for path in DOCS:
        for f in json.loads(Path(path).read_text(encoding="utf-8"))["findings"]:
            es = f["title"]["es"]
            seen += 1
            assert not ENGLISH_LIGHT.search(es), (path, f["id"], es)
            assert not ENGLISH_NUMBER.search(es), (path, f["id"], es)
    assert seen > 30


def test_the_spanish_titles_carry_the_numbers_of_the_english_ones() -> None:
    """Numbers unchanged: '19.4 points' reads '19,4 puntos'; '49,856 accounts' reads '49.856 cuentas'."""
    for path in DOCS:
        for f in json.loads(Path(path).read_text(encoding="utf-8"))["findings"]:
            if f["id"] == "F-SHORT-LIFE":
                n = re.match(r"([\d,]+) accounts", f["title"]["en"]).group(1)
                assert f["title"]["es"].startswith(n.replace(",", ".") + " cuentas"), (path, f["title"])
            if f["id"] == "F-LIFETIME-GAP":
                n = re.search(r"by up to ([\d.]+) points", f["title"]["en"]).group(1)
                assert f"hasta {n.replace('.', ',')} puntos" in f["title"]["es"], (path, f["title"])


def test_the_reasons_the_views_print_are_bilingual() -> None:
    """V06-1 / PR-C06: rung_comparison[*].reason and data_status.freddie_mac_reason were English-only strings."""
    for path in DOCS:
        o = json.loads(Path(path).read_text(encoding="utf-8"))["outputs"]
        assert _bitext(o["data_status"]["freddie_mac_reason"]), path
        reasons = [r["reason"] for r in o["rung_comparison"] if r["reason"] is not None]
        assert reasons and all(_bitext(r) and r["es"] != r["en"] for r in reasons), path
