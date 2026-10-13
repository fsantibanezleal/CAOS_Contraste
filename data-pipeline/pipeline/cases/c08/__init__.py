"""C08, LGD and downturn LGD on the SBA 7(a) charge-off twin (unit U6-P2).

The case package (see ``docs/cases/C08.md`` and ``docs/design/features/c08/``): ``panel`` (cleaning with counted exclusions,
the LGD proxy, the default cohorts), ``cutoff`` (no look-ahead by default date), ``ladder`` (the six LGD rungs through the
engine and catboost), ``downturn`` (the downturn period and the cohort-based add-on), ``variant`` (one test cohort),
``build`` and ``models`` (the documents) and ``page`` (the case page's results).
The heavy modules load when the case bakes, never at discovery.
"""
from __future__ import annotations

from ._case import CASE, CASE_ID, C08

__all__ = ["CASE", "CASE_ID", "C08"]
