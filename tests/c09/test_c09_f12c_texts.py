"""U16-F12c (R4 batch c11 m2, C09): a finding that prints an estimate and the known CCF prints their difference with one more decimal,
so the printed difference agrees with the printed pair (level 4 read "0.752 against the known 0.754, 0.001 below"). Tested on the
producer's function over the committed outputs of every level, never by re-baking."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.cases.c09 import documents

ROOT = Path(__file__).resolve().parents[2]
LEVELS = range(6)


def _outputs(n):
    return json.loads((ROOT / "data" / "derived" / "C09" / f"level-{n}.json").read_text(encoding="utf-8"))["outputs"]


def _num(s, lang):
    return float(s.replace(".", "").replace(",", ".")) if lang == "es" else float(s.replace(",", ""))


def _consistent(a, b, d, decimals_pair):
    """The printed difference d lies inside the range the printed pair a, b allows (each rounded at decimals_pair)."""
    half = 0.5 * 10 ** -decimals_pair
    return abs(a - b) - 2 * half - 1e-12 <= d <= abs(a - b) + 2 * half + 1e-12


@pytest.mark.parametrize("n", LEVELS)
@pytest.mark.parametrize("lang", ["en", "es"])
def test_the_fixed_horizon_finding_prints_a_difference_its_pair_allows(n, lang):
    f = next(x for x in documents.findings(_outputs(n), 0.1) if x["id"] == "F-FIXED")["title"][lang]
    pat = (r"is ([\d.]+) against the known ([\d.]+), ([\d.]+) (?:below|above)" if lang == "en"
           else r"es ([\d,]+) frente al conocido ([\d,]+), ([\d,]+) por (?:debajo|encima)")
    m = re.search(pat, f)
    assert m, f
    a, b, d = (_num(x, lang) for x in m.groups())
    assert len(m.group(3).split("." if lang == "en" else ",")[1]) == 4, f
    assert _consistent(a, b, d, 3), f


@pytest.mark.parametrize("n", LEVELS)
@pytest.mark.parametrize("lang", ["en", "es"])
def test_the_treatment_finding_names_the_known_value_and_a_difference_its_pair_allows(n, lang):
    out = _outputs(n)
    f = next(x for x in documents.findings(out, 0.1) if x["id"] == "F-TREATMENT")["title"][lang]
    pat = (r"to ([\d.]+) \(([+-][\d.]+) against the known ([\d.]+)\)" if lang == "en"
           else r"a ([\d,]+) \(([+-][\d,]+) frente al conocido ([\d,]+)\)")
    m = re.search(pat, f)
    assert m, f
    a, d, b = _num(m.group(1), lang), _num(m.group(2), lang), _num(m.group(3), lang)
    assert _consistent(a, b, abs(d), 3), f
