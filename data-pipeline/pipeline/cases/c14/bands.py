"""Maturity bands of the call report spread over the 19 buckets of SRP31.96 Table 3.

The report gives a balance by band of remaining maturity or next repricing ("3 months or less", "3 to 12 months", ...), not by
the 19 buckets. Each band is spread uniformly in time: the share of a bucket is the length of its overlap with the band over the
length of the band (a stated synthetic slotting assumption, ``assumptions.REGISTRY['band_spread']``). The bucket edges are the
engine's (``riskvalidation.irrbb.slotting.bucket_grid``); a band that is open above carries an upper edge stated in
``assumptions.OPEN_EDGES``.
"""
from __future__ import annotations

import numpy as np
from riskvalidation.irrbb import slotting as rv_slotting

from .assumptions import OPEN_EDGES

#: the closed bands of the report, years
BANDS: dict[str, tuple[float, float]] = {
    "3m_or_less": (0.0, 0.25), "3_12m": (0.25, 1.0), "1_3y": (1.0, 3.0), "3_5y": (3.0, 5.0), "5_15y": (5.0, 15.0),
    "over_15y": (15.0, OPEN_EDGES["over_15y"]),
    "up_to_1y": (0.0, 1.0), "over_5y_borrowing": (5.0, OPEN_EDGES["over_5y_borrowing"]),
    "mbs_average_life_3y_or_less": (0.0, 3.0), "mbs_average_life_over_3y": (3.0, OPEN_EDGES["mbs_average_life_over_3y"]),
    "over_3y_time_deposit": (3.0, OPEN_EDGES["over_3y_time_deposit"]),
}


def slot_band(lo: float, hi: float) -> np.ndarray:
    """(19,) weights summing to one: the overlap of ``(lo, hi]`` with each bucket over the length of the band."""
    if not hi > lo >= 0.0:
        raise ValueError(f"a band needs 0 <= lo < hi, got ({lo}, {hi})")
    g = rv_slotting.bucket_grid()
    upper = np.where(np.isinf(g.upper), hi, g.upper)
    overlap = np.clip(np.minimum(hi, upper) - np.maximum(lo, g.lower), 0.0, None)
    return overlap / (hi - lo)


def _cum(x: float, lo: float, hi: float) -> float:
    """``integral over T in (lo, hi) of min(x, T) / T dT``: the principal repaid by time ``x`` summed over the remaining maturities."""
    if x <= 0.0:
        return 0.0
    if x >= hi:
        return hi - lo
    if x <= lo:
        return x * np.log(hi / lo)
    return (x - lo) + x * np.log(hi / x)


def slot_amortising(lo: float, hi: float) -> np.ndarray:
    """(19,) weights summing to one for a balance that amortises linearly to zero over its remaining maturity T, T uniform in ``(lo, hi]``.

    The principal repaid in a bucket is ``integral of (overlap of the bucket with (0, T]) / T`` over T, in closed form (the
    synthetic amortisation assumption ``assumptions.REGISTRY['amortisation']``): a mortgage pool slotted by its contractual maturity
    repays over its life, so its notional repricing cash flows are spread to the maturity and not placed at it."""
    if not hi > lo >= 0.0:
        raise ValueError(f"a band needs 0 <= lo < hi, got ({lo}, {hi})")
    g = rv_slotting.bucket_grid()
    upper = np.where(np.isinf(g.upper), hi, g.upper)
    cum = np.array([_cum(x, lo, hi) for x in np.append(g.lower, upper[-1])])
    cum[-1] = hi - lo                                       # the last bucket runs to the top of the band
    return np.diff(cum) / (hi - lo)


def spread(parts: list[tuple[float, str]], amortising: bool = False) -> np.ndarray:
    """(19,) amounts: each ``(amount, band name)`` spread over the buckets (at the maturity, or amortising) and summed."""
    out = np.zeros(19)
    for amount, band in parts:
        out += amount * (slot_amortising if amortising else slot_band)(*BANDS[band])
    return out
