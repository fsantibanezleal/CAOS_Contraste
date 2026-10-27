"""The reader text of the governance documents (U16-F10p, the third capture review R3 c23 B3 and B5).

A sentence the bake writes, or passes on from the engine, is read by a validator: it names no plan or decision code of the product's
sizing (``W15-13: ...``, ``(W15-5)``), and no engine key or developer text where words exist (``test_id@model``, ``risk_accepted``,
``dim_cube``). ``reader_text`` takes a bilingual text and returns it in those words; the numbers and the rest of the sentence are kept.
"""
from __future__ import annotations

import re

_CODE = r"W\d{2}-\d+"
#: a code that opens a sentence ("W15-13: the date ..."), a bracket of codes ("(W15-3, W15-4)"), a code after a semicolon or a comma
_LEADING = re.compile(rf"^\s*{_CODE}(?:\s*,\s*{_CODE})*\s*:\s*")
_BRACKET = re.compile(rf"\s*\((?:{_CODE})(?:\s*(?:,|;|and|y)\s*{_CODE})*\)")
_TRAILING = re.compile(rf"\s*[;,]\s*{_CODE}(?:\s*,\s*{_CODE})*(?=[;,.)]|$)")
_INLINE = re.compile(rf"\s*\b{_CODE}\b")

#: whole engine sentences in reader words (the engine's reason table, riskvalidation.governance.reasons, writes the left side)
_SENTENCES = {
    "en": [(re.compile(r"the evidence is not a test_id@model row \(it is a design:, contract:, rate: or bare test id\)"),
            "the finding cites a design limit, a contract check or a rate, not one test row of a model")],
    "es": [(re.compile(r"la evidencia no es una fila test_id@modelo \(es design:, contract:, rate: o un id de prueba sin modelo\)"),
            "el hallazgo cita un límite de diseño, una verificación de contrato o una tasa, no una fila de prueba de un modelo")],
}
#: engine keys in words
_KEYS = {
    "en": [(re.compile(r"\bwhen the bake runs\b"), "when the documents are generated"), (re.compile(r"\bthe bake\b"), "the generation step"),
           (re.compile(r"\brisk_accepted\b"), "risk accepted"), (re.compile(r"\bdim_cube\b"), "dynamic initial margin cube")],
    "es": [(re.compile(r"\bno risk_accepted\b"), "no aceptados como riesgo"), (re.compile(r"\brisk_accepted\b"), "riesgo aceptado"),
           (re.compile(r"\bdim_cube\b"), "cubo de margen inicial dinámico"),
           # the words, never a path or a key that holds them (`data-pipeline/`, `content_hash`)
           (re.compile(r"(?<![\w/-])del pipeline(?![\w/-])"), "de la cadena de cálculo"), (re.compile(r"(?<![\w/-])el pipeline(?![\w/-])"), "la cadena de cálculo"),
           (re.compile(r"(?<![\w/-])pipeline(?![\w/-])"), "cadena de cálculo"), (re.compile(r"(?<![\w/-])del hash(?![\w/-])"), "de la huella"),
           (re.compile(r"(?<![\w/-])el hash(?![\w/-])"), "la huella"), (re.compile(r"(?<![\w/-])hashes(?![\w/-])"), "huellas"),
           (re.compile(r"(?<![\w/-])hash(?![\w/-])"), "huella"),
           (re.compile(r"\bcuando corre el bake\b"), "cuando se generan los documentos"), (re.compile(r"\bel bake\b"), "la generación"),
           (re.compile(r"\bbake\b"), "generación")],
}


def _one(s: str, lang: str) -> str:
    for rx, words in _SENTENCES[lang]:
        s = rx.sub(words, s)
    lead = _LEADING.match(s)
    s = _LEADING.sub("", s)
    s = _BRACKET.sub("", s)
    s = _TRAILING.sub("", s)
    s = _INLINE.sub("", s)
    for rx, words in _KEYS[lang]:
        s = rx.sub(words, s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    if lead and s:
        s = s[0].upper() + s[1:]
    return s


def reader_text(t: dict[str, str]) -> dict[str, str]:
    """The bilingual text ``t`` in reader words, in both languages (the other keys of ``t`` are kept)."""
    out = dict(t)
    for lang in ("en", "es"):
        if isinstance(t.get(lang), str):
            out[lang] = _one(t[lang], lang)
    return out
