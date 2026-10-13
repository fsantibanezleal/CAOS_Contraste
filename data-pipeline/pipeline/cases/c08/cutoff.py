"""The cutoff rule of C08 (CT-904, CT-905): no look-ahead by default date.

A model for a cutoff is trained only on the defaults whose workout closed strictly before it. The SBA file records the
charge-off and nothing after it, so the charge-off date is the date the workout closes in this twin; the engine's
``closed_before`` applies the rule (a close on the cutoff date is not before it). A default charged off after the cutoff
is not in the training set, whatever the file says today.

The file has no default date earlier than the charge-off, so a workout open at the cutoff (defaulted before it, charged
off after it) cannot be told from a loan that was still performing. The nearest observable stand-in is the charge-offs
of the ``WORKOUT_WINDOW_MONTHS`` after the cutoff: they are counted as the open workouts excluded from the training set
(they are never in it) and stated as a proxy in the document.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from riskvalidation.lgd_ead.workout import closed_before

from .panel import Defaults

WORKOUT_WINDOW_MONTHS = 12


def training_mask(defaults: Defaults, cutoff: str) -> np.ndarray:
    """The defaults whose workout closed strictly before ``cutoff`` (an ISO date), by the engine's rule."""
    return np.asarray(closed_before(defaults.chargeoff_date, cutoff), dtype=bool)


def open_workout_mask(defaults: Defaults, cutoff: str, window_months: int = WORKOUT_WINDOW_MONTHS) -> np.ndarray:
    """The stand-in for the workouts open at the cutoff: charged off on or after it and within ``window_months`` of it."""
    end = (pd.Timestamp(cutoff) + pd.DateOffset(months=int(window_months))).to_datetime64().astype("datetime64[D]")
    after = ~training_mask(defaults, cutoff)
    return after & (defaults.chargeoff_date < end)


def cutoff_for(first_year: int) -> str:
    """The training cutoff of the cohort that starts in ``first_year``: the last day of the year before it."""
    return f"{first_year - 1}-12-31"
