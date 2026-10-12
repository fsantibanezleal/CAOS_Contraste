"""C06, lifetime PD, IFRS 9 staging and ECL on the SBA 7(a) twin and the Federal Reserve scenarios (unit U5-P1).

The case package (see ``docs/cases/C06.md`` and ``docs/design/features/c06/``): ``readers`` (SBA, Federal Reserve and the
Freddie Mac slot), ``panel`` (cleaning, the book and the observation at a date), ``macro`` (history as known, scenario
paths, reduced form), ``ladder`` (the three lifetime PD rungs), ``run`` (term structures, staging and ECL through the
engine), ``rollforward``, ``backtest``, ``build`` and ``models`` (the documents) and ``variant`` (one reporting date).
The heavy modules load when the case bakes, never at discovery.
"""
from __future__ import annotations

from typing import Any

from ._case import CASE, CASE_ID, REPORTING_DATES, C06

__all__ = ["CASE", "CASE_ID", "REPORTING_DATES", "C06", "Any"]
