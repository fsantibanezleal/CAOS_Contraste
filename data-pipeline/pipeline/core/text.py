"""Numbers and light names inside the producers' bilingual texts, written as the web shell writes them.

The shell formats a number with ``Intl.NumberFormat`` in ``en-US`` and ``es-CL`` (``@fasl-work/caos-app-shell`` ``formatNumber``):
a thousands comma and a decimal point in English, a thousands dot and a decimal comma in Spanish (``es-CL`` groups from four
digits, ``1.120``), and a percent joined to its number by a no-break space. A finding title or a note a producer writes is read
beside the shell's own numbers, so it uses these functions instead of Python's format specifiers, which write the English form
in both languages (the U16-R2 capture review: "3.3 puntos", "1,120 nombres", "(amber)" in Spanish sentences).
"""
from __future__ import annotations

import math

NBSP = " "

#: the light words of a test row in each language (the frontend's light names)
LIGHT: dict[str, dict[str, str]] = {
    "green": {"en": "green", "es": "verde"},
    "amber": {"en": "amber", "es": "ámbar"},
    "red": {"en": "red", "es": "rojo"},
    "not_evaluated": {"en": "not evaluated", "es": "no evaluada"},
    "error": {"en": "error", "es": "error"},
}


def number(x: float | int, decimals: int = 0, *, lang: str, grouping: bool = True) -> str:
    """``x`` with ``decimals`` fixed decimals in the language's form; ``grouping=False`` for a calendar year or an id."""
    if lang not in ("en", "es"):
        raise ValueError(f"lang is 'en' or 'es', not {lang!r}")
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"a finite number is required, not {x!r}")
    if decimals < 0:
        raise ValueError("decimals must be 0 or more")
    text = f"{float(x):,.{decimals}f}" if grouping else f"{float(x):.{decimals}f}"
    if text.startswith("-") and float(text.replace(",", "")) == 0:
        text = text[1:]  # no negative zero
    if lang == "en":
        return text
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def percent(share: float, decimals: int = 1, *, lang: str) -> str:
    """A share (0.139) as a percent with its sign ("13.9 %", "13,9 %"), the shell's no-break space before the sign."""
    return f"{number(100.0 * share, decimals, lang=lang)}{NBSP}%"


def bi_number(x: float | int, decimals: int = 0, *, grouping: bool = True) -> dict[str, str]:
    """``number`` in both languages."""
    return {lang: number(x, decimals, lang=lang, grouping=grouping) for lang in ("en", "es")}


def bi_percent(share: float, decimals: int = 1) -> dict[str, str]:
    """``percent`` in both languages."""
    return {lang: percent(share, decimals, lang=lang) for lang in ("en", "es")}


def light(name: str, lang: str) -> str:
    """The light word of a test row in the language; an unknown light raises."""
    try:
        return LIGHT[name][lang]
    except KeyError as exc:
        raise ValueError(f"unknown light {name!r} or language {lang!r}") from exc


__all__ = ["LIGHT", "NBSP", "bi_number", "bi_percent", "light", "number", "percent"]
