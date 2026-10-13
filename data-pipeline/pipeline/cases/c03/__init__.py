"""C03, SME PD by vintage through 2008, on the SBA 7(a) loans (unit U6-P1).

The case package (see ``docs/cases/C03.md`` and ``docs/design/features/c03/``): ``panel`` (cleaning, the origination inputs and
the 5-year target as known at an observation date), ``windows`` (the five test cohorts and the strict out-of-time training window
of each, decision D1), ``fit`` (the existing C01 rungs fitted on a window), ``evaluate`` (the engine's validation rows),
``variant`` and ``models`` (the documents) and ``page`` (the result table of the case page). The heavy modules load when the case
bakes, never at discovery.
"""
from __future__ import annotations

from ._case import CASE, CASE_ID, COHORTS, C03

__all__ = ["CASE", "CASE_ID", "COHORTS", "C03"]
