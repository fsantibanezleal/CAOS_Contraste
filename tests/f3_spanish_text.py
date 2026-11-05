"""The U16-R2 text checks of the committed documents of C08 to C13 (one copy): a Spanish text carries no English number form and no
English light word, and the fields the Spanish views print are bilingual.

The review of the Spanish captures found titles such as "3.3 puntos", "13.9%" and "(amber)" inside Spanish sentences and plain English
strings interpolated into Spanish text. ``leaks`` finds them in a document without knowing which field holds them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
NUMBER = re.compile(r"(?<!QuantLib )(?<!ORE )(?<!Python )(?<![A-Za-z\d.,])\d+(?:[.,]\d+)+(?![A-Za-z])")  # not inside a paragraph reference (CRE32.36) or an equation number (5.7a)
ENGLISH_PERCENT = re.compile(r"\d%")
LIGHT_WORDS = re.compile(r"\((?:green|amber|red)\)|\b(?:green|amber)\b", re.IGNORECASE)  # "red" alone is the Spanish word for a network


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def bitexts(node: Any, path: str = "") -> Iterator[tuple[str, str, str]]:
    """Every ``{en, es}`` object of a document with its path."""
    if isinstance(node, dict):
        if set(node) == {"en", "es"} and isinstance(node["en"], str) and isinstance(node["es"], str):
            yield path, node["en"], node["es"]
            return
        for k, v in node.items():
            yield from bitexts(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from bitexts(v, f"{path}[{i}]")


def _plain(text: str) -> str:
    """The text without model orders such as GARCH(1,1), which are notation, not numbers, and without the identifiers of a
    citation (a DOI, an arXiv id, a URL), which stay as published in both languages."""
    text = re.sub(r"(?:doi:|arXiv[: ]|https?://)\S+", "", text)
    # citation locators, written the same in both languages: a circular's own number (Circular 2.346), the section of a module
    # (local_cl (2.1)), an equation after its authors (Anderson y Goodman 2.8)
    text = re.sub(r"\bCircular\s+(?:N[°º]\s*)?\d[\d.]*", "Circular", text)
    # the section of a regulation (B-1 section 2.1, sección 2.1 de B-1)
    text = re.sub(r"\b(?:section|sección)\s+\d+(?:\.\d+)+", "section", text)
    text = re.sub(r"\b([a-z_]+(?:\.[a-z_]+)+) \(\d+(?:\.\d+)+(?: [a-z])?\)", r"\1 ()", text)
    text = re.sub(r"\b([A-Z][a-z]+) \d+(?:\.\d+)+(?=\))", r"\1", text)
    return re.sub(r"\(\d+,\d+\)", "()", text)


def leaks(en: str, es: str) -> list[str]:
    en, es = _plain(en), _plain(es)
    """What an English form left in the Spanish text: a number token that is also in the English text (a decimal point or a
    thousands comma), a percent glued to its number, an English light word."""
    out = [t for t in NUMBER.findall(es) if t in NUMBER.findall(en) and ("." in t or "," in t) and t.count(".") < 2 and t.replace(",", ".") != t.replace(".", ",")]
    out += ENGLISH_PERCENT.findall(es)
    out += LIGHT_WORDS.findall(es)
    return out


def document_leaks(doc: Any, only: str | None = None) -> list[str]:
    found = []
    for path, en, es in bitexts(doc):
        if only and only not in path:
            continue
        # a test's reference keeps its citation as published (a locator such as "Annex 3.1" is a section number, not a
        # decimal); its Spanish is reviewed one reference at a time in REFERENCE_ES (pipeline/cases/reference_text.py)
        if path.endswith(".reference_text"):
            continue
        # a calibration target's source quotes its publication's locator and figures as published ("Comercial 163.602 de ...
        # MMUSD" in the CMF table), the same in both languages: a citation, not a number of the product
        if re.search(r"\.calibration_targets\[\d+\]\.source$", path):
            continue
        bad = leaks(en, es)
        if bad:
            found.append(f"{path}: {bad} in {es[:90]!r}")
    return found
