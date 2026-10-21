"""CT-1825: the Spanish of a C18 document writes its decimals with a comma and is Spanish (the release gate, G11).

The shell gate fails a Spanish page that writes a decimal with a point. The documents' own Spanish sentences are built in the
producer, so the producer writes them the Spanish way (``P.es``); a text born in English alone (the Spanish field repeating the
English one) is a missing translation, and the mitigation reason is one that was."""
from __future__ import annotations

import re
from typing import Any, Iterator

from c18_support import requires_raw

from pipeline.cases.c18 import params as P

pytestmark = requires_raw

DECIMAL = re.compile(r"(?<![\w.,/:@#])(\d+)\.(\d+)(?:[eE][-+]?\d+)?(?![\w/@]|\.\d)")
THOUSANDS = re.compile(r"[1-9]\d{0,2}(\.\d{3})+")
# a row of a regulation's annex ("fila 10.2"): a reference kept as the source writes it, which the view marks translate="no"
ROW_REFERENCE = re.compile(r"\b(?:fila|row) \d+\.\d+")


def _spanish_texts(node: Any, path: str = "") -> Iterator[tuple[str, dict[str, str]]]:
    if isinstance(node, dict):
        if set(node) == {"en", "es"} and isinstance(node["es"], str):
            yield path, node
        for k, v in node.items():
            yield from _spanish_texts(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _spanish_texts(v, f"{path}[{i}]")


def decimal_points(text: str) -> list[str]:
    """The decimals of a text written with a point, as the gate reads them (a Spanish thousands group passes)."""
    out = []
    text = ROW_REFERENCE.sub("", text)
    for m in DECIMAL.finditer(text):
        token = re.match(r"\d+(?:\.\d+)+", text[m.start():]).group(0)  # type: ignore[union-attr]
        if not THOUSANDS.fullmatch(token):
            out.append(m.group(0))
    return out


def test_es_writes_the_spanish_separators() -> None:
    assert P.es(0.1234, ".2%") == "12,34%"
    assert P.es(658046.4, ",.0f") == "658.046"
    assert P.es(-0.5, "+.2f") == "-0,50"
    assert P.es_num("1,234.5") == "1.234,5"


def test_no_spanish_sentence_of_a_variant_writes_a_decimal_point(built) -> None:
    bad = []
    for vid, doc in built.variants.items():
        for path, t in _spanish_texts(doc):
            if decimal_points(t["es"]):
                bad.append((vid, path, decimal_points(t["es"])))
    assert not bad, bad[:5]


def test_the_mitigation_reason_is_spanish_and_keeps_its_row_reference(built) -> None:
    seen = 0
    for doc in built.variants.values():
        mit = doc["outputs"].get("capital_plan", {}).get("mitigation")
        if not mit:
            continue
        seen += 1
        assert mit["reason"]["es"] != mit["reason"]["en"]
        assert "No se supone ninguna acción de mitigación" in mit["reason"]["es"]
        assert "fila 10.2 del Anexo 3" in mit["reason"]["es"] and "row 10.2 of the Annex 3" in mit["reason"]["en"]
    assert seen


def test_the_named_parameters_state_their_basis_in_both_languages(built) -> None:
    for doc in built.variants.values():
        for name, p in doc.get("fit", {}).get("named_parameters", {}).items():
            if isinstance(p, dict) and isinstance(p.get("basis"), dict) and re.search(r"\d\.\d", p["basis"]["en"]):
                assert p["basis"]["es"] != p["basis"]["en"], name


def test_a_baked_variant_chip_fits_the_rail_in_spanish(tmp_path) -> None:
    """A sandbox bake (nothing of the committed data is written): the short title of every variant is one chip line, 24 characters at most."""
    from types import SimpleNamespace

    from c18_support import SEED, SMALL_DRAWS, SMALL_PATHS, data_root
    from pipeline.cases.c18 import bake

    (tmp_path / "manifests").mkdir()
    manifest = bake.bake_case(SEED, SimpleNamespace(root=tmp_path / "derived", manifests=tmp_path / "manifests"), data_root(), n_draws=SMALL_DRAWS, n_paths=SMALL_PATHS)
    shorts = {a["variant_id"]: a["short_title"] for a in manifest["artifacts"] if a["role"] == "variant"}
    assert shorts[P.SCENARIOS["fed"]] == {"en": "Fed 2026 severely adverse", "es": "Fed 2026 severo"}
    assert all(len(t["es"]) <= 24 for t in shorts.values()), shorts
