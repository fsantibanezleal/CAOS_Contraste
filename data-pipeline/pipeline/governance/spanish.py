"""The Spanish of the governance documents.

The engine writes its Spanish texts without accents and without the eñe ("as the product's documents write it" in the first draft of the contract), and
returns some reasons in English only (the contract: ``scope_test``, ``assign_variant``, ``anchor_from_test_row``, ``rwea_share_of_anchor``). The product's
documents carry their accents (ADR-0017), so the bake does two things here and nothing else:

* ``restore`` puts the accents and the eñe back on the words of the engine's Spanish vocabulary (a table of whole words, plus a few phrases for the words
  an accent separates from another word: ``esta`` the verb and ``esta`` the demonstrative). A text that is already accented is returned unchanged.
* ``translate`` gives the Spanish of an English-only reason of the engine from a table of its sentences; a sentence the table does not hold stops the
  bake, because a Spanish text is never invented or left in English.

No number or decision is changed by either: they are cosmetic and the engine's English text stays the source of record.
"""
from __future__ import annotations

import re
from typing import Any

from .readers import BakeError

#: whole words (lower case, unaccented) to their accented form; matching is case-insensitive and keeps the case of the first letter
WORDS = {
    "descripcion": "descripción", "implementacion": "implementación", "verificacion": "verificación", "analisis": "análisis", "estres": "estrés",
    "opinion": "opinión", "recomendacion": "recomendación", "ningun": "ningún", "algun": "algún", "critico": "crítico", "maximo": "máximo",
    "convencion": "convención", "proporcion": "proporción", "bateria": "batería", "seccion": "sección", "limite": "límite", "limites": "límites",
    "operacion": "operación", "diseno": "diseño", "disenos": "diseños", "peldano": "peldaño", "peldanos": "peldaños", "evaluacion": "evaluación",
    "calificacion": "calificación", "version": "versión", "versiones": "versiones", "codigo": "código", "replicacion": "replicación",
    "declaracion": "declaración", "politica": "política", "direccion": "dirección", "catalogo": "catálogo", "remediacion": "remediación",
    "sintetico": "sintético", "sintetica": "sintética", "leido": "leído", "leidos": "leídos", "validacion": "validación", "linea": "línea",
    "ejecucion": "ejecución", "excepcion": "excepción", "rubrica": "rúbrica", "estadistico": "estadístico", "estadistica": "estadística",
    "economico": "económico", "economica": "económica", "teoria": "teoría", "metodo": "método", "metodologia": "metodología", "metrica": "métrica",
    "numero": "número", "pequeno": "pequeño", "unico": "único", "ultimo": "último", "ultima": "última",
    "tambien": "también", "despues": "después", "agentico": "agéntico", "agentica": "agéntica", "cuantitativo": "cuantitativo", "ejecutivo": "ejecutivo",
    "periodo": "período", "indice": "índice", "union": "unión", "calculo": "cálculo", "dia": "día", "dias": "días",
    "clasificacion": "clasificación", "aplicacion": "aplicación", "informacion": "información", "relacion": "relación", "decision": "decisión",
    "revision": "revisión", "supervision": "supervisión", "exposicion": "exposición", "generacion": "generación", "produccion": "producción",
    "reproducibilidad": "reproducibilidad", "monitorizacion": "monitorización", "calibracion": "calibración", "estimacion": "estimación",
    "dependencia": "dependencia", "explicacion": "explicación", "perdida": "pérdida", "capitalizacion": "capitalización",
}
WORDS = {k: v for k, v in WORDS.items() if k != v}

#: phrases where an unaccented word is a verb: "esta" before a participle or an adjective of state, "estan" as a verb
PHRASES = [
    (re.compile(r"\b(no )?(esta)( (?:(?:establecid|registrad|determinad|declarad|definid|listad|incluid|asignad|calculad|encontrad|nombrad)[oa]s?|presente|vigente|disponible|vac[ií]a|vac[ií]o|cerrad[oa]))", re.I), None),
    (re.compile(r"\b(no lo )(estan)\b", re.I), None),
    (re.compile(r"\b(estan)( (?:(?:establecid|registrad|determinad|declarad|definid|listad|incluid|asignad|calculad|encontrad|nombrad)[oa]s?|presentes|vigentes|disponibles|abiertos|cerrados))", re.I), None),
]
#: an identifier (``.decision``, ``spec(...)``, ``a_version``, a path) is never a word of the prose
_WORD = re.compile(r"(?<![\w.@/])(" + "|".join(sorted(WORDS, key=len, reverse=True)) + r")(?![\w(@/])", re.I)


def _case(src: str, dst: str) -> str:
    if src.isupper() and len(src) > 1:
        return dst.upper()
    if src[:1].isupper():
        return dst[:1].upper() + dst[1:]
    return dst


def restore(text: str) -> str:
    """The text with the accents and the eñe of the engine's vocabulary put back (an accented text is unchanged)."""

    def verb(m: re.Match) -> str:
        parts = list(m.groups())
        out = ""
        for p in parts:
            if p is None:
                continue
            if p.lower() == "esta":
                p = _case(p, "está")
            elif p.lower() == "estan":
                p = _case(p, "están")
            out += p
        return out

    for rx, _ in PHRASES:
        text = rx.sub(verb, text)
    return _WORD.sub(lambda m: _case(m.group(0), WORDS[m.group(0).lower()]), text)


def restore_document(node: Any, verbatim: frozenset[str] = frozenset()) -> Any:
    """Every ``{"en", "es"}`` object of a document gets its Spanish restored, in place; returns the node. A text in ``verbatim`` (copied from a case document)
    is left exactly as the case wrote it."""
    if isinstance(node, dict):
        if set(node) == {"en", "es"} and isinstance(node["es"], str):
            if node["es"] not in verbatim:
                node["es"] = restore(node["es"])
        else:
            for v in node.values():
                restore_document(v, verbatim)
    elif isinstance(node, list):
        for v in node:
            restore_document(v, verbatim)
    return node


#: the English-only reasons of the engine and their Spanish (exact sentences; the placeholders are filled by ``translate``)
SENTENCES = {
    "In scope: it applies statistical or economic theory, its output is an estimate and it is not generative or agentic (SR 26-2).":
        "En alcance: aplica teoría estadística o económica, su resultado es una estimación y no es generativo ni agéntico (SR 26-2).",
    "Out of scope: it is a generative or agentic AI model (SR 26-2).":
        "Fuera de alcance: es un modelo de inteligencia artificial generativo o agéntico (SR 26-2).",
    "Out of scope: it applies no statistical or economic theory (SR 26-2).":
        "Fuera de alcance: no aplica teoría estadística ni económica (SR 26-2).",
    "Out of scope: it applies no statistical or economic theory and it is a deterministic rule set (SR 26-2).":
        "Fuera de alcance: no aplica teoría estadística ni económica y es un conjunto de reglas deterministas (SR 26-2).",
    "Out of scope: its output is not an estimate (SR 26-2).": "Fuera de alcance: su resultado no es una estimación (SR 26-2).",
    "In scope: it applies a quantitative method (SS1/23 Principle 1.1).": "En alcance: aplica un método cuantitativo (SS1/23 Principio 1.1).",
    "Out of scope: it applies no statistical, economic, financial or mathematical theory (SS1/23 Principle 1.1).":
        "Fuera de alcance: no aplica teoría estadística, económica, financiera ni matemática (SS1/23 Principio 1.1).",
    "In scope: it applies theory and its output is an estimate (OSFI E-23).": "En alcance: aplica teoría y su resultado es una estimación (OSFI E-23).",
    "Out of scope: it applies no statistical, economic, financial or mathematical theory (OSFI E-23).":
        "Fuera de alcance: no aplica teoría estadística, económica, financiera ni matemática (OSFI E-23).",
    "Out of scope: its output is not an estimate (OSFI E-23).": "Fuera de alcance: su resultado no es una estimación (OSFI E-23).",
    "In scope: it applies theory and its output is an estimate (ECB).": "En alcance: aplica teoría y su resultado es una estimación (BCE).",
    "Out of scope: it applies no statistical, economic, financial or mathematical theory (ECB).":
        "Fuera de alcance: no aplica teoría estadística, económica, financiera ni matemática (BCE).",
    "Out of scope: its output is not an estimate (ECB).": "Fuera de alcance: su resultado no es una estimación (BCE).",
    "the evidence is not a test_id@model row (it is a design:, contract:, rate: or bare test id), so no statistic is read":
        "la evidencia no es una fila test_id@modelo (es design:, contract:, rate: o un id de prueba sin modelo), por lo que no se lee estadístico",
    "the cited test row holds no statistic or metric (or no row matches), so the anchor is null":
        "la fila de prueba citada no tiene estadístico ni métrica (o ninguna fila coincide), por lo que el ancla es nula",
    "the anchor is not stated as a share of RWEA or as an RWEA amount, so no RWEA level applies":
        "el ancla no se expresa como proporción de RWEA ni como monto de RWEA, por lo que no aplica nivel RWEA",
    "the case has no fit to assign the variant to": "el caso no tiene un ajuste al que asignar la variante",
    "the variant's provenance names no source, so no fit can be determined":
        "la procedencia de la variante no nombra fuente alguna, por lo que no se puede determinar el ajuste",
}
_PATTERNS = [
    (re.compile(r"no fit holds all of the variant's sources \((?P<s>.*)\)"), "ningún ajuste contiene todas las fuentes de la variante ({s})"),
    (re.compile(r"(?P<n>\d+) fits hold all of the variant's sources \((?P<s>.*?)\): (?P<f>.*)"),
     "{n} ajustes contienen todas las fuentes de la variante ({s}): {f}"),
]


def translate(english: str) -> str:
    """The Spanish of an English-only reason of the engine; an unknown sentence stops the bake."""
    if english in SENTENCES:
        return SENTENCES[english]
    for rx, template in _PATTERNS:
        m = rx.fullmatch(english)
        if m:
            return template.format(**m.groupdict())
    raise BakeError(f"no Spanish text is held for the engine reason {english!r}: add its sentence to pipeline/governance/spanish.py")
