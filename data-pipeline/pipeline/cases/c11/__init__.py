"""C11, market VaR and ES back-testing across 2008, 2020, 2022 and 2023 on public daily series (unit U8-P1).

The case package (see ``docs/cases/C11.md`` and ``docs/design/features/c11/``): ``readers`` (Kenneth French, US Treasury and
the H.10, with their fetch), ``portfolio`` (the stated portfolio and returns of each window), ``forecast`` (the strictly
rolling one-step forecasts of the ten-rung ladder through ``riskvalidation.market``), ``hyper`` (the hyperparameters fixed on
1995 to 2003), ``documents`` (the window and models documents) and ``bake`` (the bake and the manifest) and ``_case`` (the case object discovery reads).
The heavy modules load when the case bakes, never at discovery.
"""
from __future__ import annotations

from ._case import CASE
from .constants import CASE_ID, LEVELS, SEED, SPAN, WINDOWS

__all__ = ["CASE", "CASE_ID", "LEVELS", "SEED", "SPAN", "WINDOWS"]
