"""The numeric expectations of a case, checked at bake time.

An expectation written only as prose can be wrong for months without anyone noticing (the template's epidemic
case promised one attack rate while its engine produced another, found 2026-10-04). Every case therefore states
its expected range for named results; the bake fails on a value outside its range, and the manifest carries the
ranges so the web can judge a live run against them too.
"""
from __future__ import annotations

import math
from collections.abc import Mapping


class ExpectationError(ValueError):
    """A baked result fell outside the range its case declares."""


def check(case_id: str, expect: Mapping[str, tuple[float, float]], values: Mapping[str, float]) -> dict[str, list[float]]:
    """Return the ranges as written to the manifest; raise ExpectationError naming every result out of range."""
    if not expect:
        raise ExpectationError(f"{case_id}: no expected range declared (every case states what a reader should see)")
    ranges: dict[str, list[float]] = {}
    bad: list[str] = []
    for name in sorted(expect):
        if name not in values:
            raise ExpectationError(f"{case_id}: unknown expected result {name!r} (known: {', '.join(sorted(values))})")
        lo, hi = expect[name]
        if lo > hi:
            raise ExpectationError(f"{case_id}: empty range for {name}: [{lo}, {hi}]")
        ranges[name] = [float(lo), float(hi)]
        v = float(values[name])
        if not math.isfinite(v) or not lo <= v <= hi:
            bad.append(f"{name}={v:.6g} outside [{lo}, {hi}]")
    if bad:
        raise ExpectationError(f"{case_id}: " + "; ".join(bad))
    return ranges
