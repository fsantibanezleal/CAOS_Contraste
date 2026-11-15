"""One rounding rule for every rate the report prints: half up on the decimal value of the stored number.

The binary float of 0.0785 times 100 is 7.8499999999999996, so ``f"{100 * x:.1f}"`` prints 7.8 where the papers print 7.9
(``Decimal(repr(x)) * 100`` quantized with ROUND_HALF_UP). Every ``pct`` of the table scripts calls ``percent`` so that a rate
reads the same in the report and in the manuscript of its method, and ``install`` gives the shared table writer
(``figkit.table``) the same rule for the fixed-digit cells of a table, so that a rate printed as a fraction in a table
(0.913) agrees with the same rate printed as a percentage in the text (91.3).
"""
from __future__ import annotations

import decimal
import math

_D = decimal


def percent(x: float, d: int = 1) -> str:
    """A share ``x`` (0 to 1) in percent with ``d`` decimals, rounded half up on ``repr(x)``."""
    q = _D.Decimal(1).scaleb(-d)
    return format((_D.Decimal(repr(float(x))) * 100).quantize(q, rounding=_D.ROUND_HALF_UP), "f")


def fixed(x: float, d: int) -> str:
    """``x`` with ``d`` decimals, rounded half up on ``repr(x)`` (a non-finite value is formatted as ``format`` does)."""
    if x != x or x in (float("inf"), float("-inf")):
        return f"{x:.{d}f}"
    q = _D.Decimal(1).scaleb(-d)
    return format(_D.Decimal(repr(float(x))).quantize(q, rounding=_D.ROUND_HALF_UP), "f")


def install(figkit) -> None:
    """Make ``figkit.fmt`` round the float cells of a table half up on their decimal value."""
    original = figkit.fmt

    def fmt(x, digits: int = 3):
        if isinstance(x, float) and not isinstance(x, bool) and x == x:
            return fixed(x, digits)
        return original(x, digits)

    figkit.fmt = fmt


_BS = chr(92)


def sci(x: float, d: int = 1) -> str:
    """A small number as a TeX mantissa times a power of ten (usable in text, in math and as a table cell), the mantissa rounded half up;
    programmer notation (1.5e-05) never reaches the text."""
    if x == 0:
        return _BS + "ensuremath{0}"
    e = math.floor(math.log10(abs(x)))
    m = fixed(x / 10 ** e, d)
    if abs(float(m)) >= 10:  # 9.96 rounds to 10.0: carry into the exponent
        e += 1
        m = fixed(x / 10 ** e, d)
    return _BS + "ensuremath{" + m + _BS + "times10^{" + str(e) + "}}"
