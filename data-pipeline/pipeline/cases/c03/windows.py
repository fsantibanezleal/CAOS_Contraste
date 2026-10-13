"""The test cohorts of C03 and the training window of each (CT-803; decision D1 of the U6 sizing).

A model trained on approvals up to a fiscal year L has seen the 5-year outcome of every loan of the window only when the
5-year mark of L (30 September of L + 5) has passed. D1: a cohort starting in fiscal year F trains only on fiscal years
whose mark falls before the first approval date of the cohort (1 October of F - 1), that is on L <= F - 6, with the cutoff on
30 September of F - 1. The FY2006-07 and FY2008-10 cohorts therefore train before the crisis; "trained through the crisis"
holds for FY2011-14 and later, whose windows hold charge-offs dated in the recession.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import panel

FIRST_FY = 1991
#: the NBER recession of the 2008 crisis (December 2007 to June 2009), the period a window must hold outcomes of to be
#: "trained through the crisis"
CRISIS_START, CRISIS_END = "2007-12-01", "2009-06-30"


@dataclass(frozen=True)
class Cohort:
    """A test cohort of approval fiscal years (SDD section 5: FY2006-07, 2008-10, 2011-14, 2015-17, 2018-20)."""

    id: str
    first_fy: int
    last_fy: int

    @property
    def fiscal_years(self) -> tuple[int, ...]:
        return tuple(range(self.first_fy, self.last_fy + 1))

    @property
    def name(self) -> str:
        return f"FY{self.first_fy}-{str(self.last_fy)[2:]}"


@dataclass(frozen=True)
class Window:
    """A training window: approval fiscal years ``first_fy`` to ``last_fy``, outcomes read up to ``cutoff`` (an ISO date)."""

    first_fy: int
    last_fy: int
    cutoff: str


COHORTS = tuple(Cohort(f"fy{a}-{str(b)[2:]}", a, b) for a, b in ((2006, 2007), (2008, 2010), (2011, 2014), (2015, 2017), (2018, 2020)))


def training_window(cohort: Cohort) -> Window:
    return Window(FIRST_FY, cohort.first_fy - 6, f"{cohort.first_fy - 1}-09-30")


def check_window(cohort: Cohort, window: Window) -> None:
    """Refuse a window that is not strictly out of time for the cohort."""
    if window.last_fy > cohort.first_fy - 6:
        raise ValueError(f"{cohort.id}: the window ends in FY{window.last_fy}, whose 5-year mark ({five_year_mark(window.last_fy)}) "
                         f"is not before the first approval of {cohort.name} (FY{cohort.first_fy - 6} is the last allowed)")
    if window.cutoff > f"{cohort.first_fy - 1}-09-30":
        raise ValueError(f"{cohort.id}: the cutoff {window.cutoff} is after 30 September of FY{cohort.first_fy - 1}")
    last_approval = np.array([f"{window.last_fy}-09-30"], dtype="datetime64[D]")
    if panel.horizon_end(last_approval)[0] > np.datetime64(window.cutoff):
        raise ValueError(f"{cohort.id}: a loan of FY{window.last_fy} has not reached its 5-year mark by the cutoff {window.cutoff}")


def five_year_mark(fy: int) -> str:
    """The 5-year mark of a vintage: 60 months after its last approval (30 September of the fiscal year)."""
    return f"{fy + 5}-09-30"


def mark_observed(fy: int, observed_at: str) -> bool:
    return five_year_mark(fy) <= str(observed_at)


def crisis_events(loans: panel.Loans, window: Window) -> int:
    """Charge-offs within 60 months of approval, dated in the recession, among the loans of the window (the outcomes a model
    trained on the window has seen of the crisis)."""
    cutoff = np.datetime64(window.cutoff)
    sel = np.flatnonzero((loans.fy >= window.first_fy) & (loans.fy <= window.last_fy))
    ln = loans.take(sel)
    y = panel.label(ln, cutoff)
    in_crisis = (ln.exit_date >= np.datetime64(CRISIS_START)) & (ln.exit_date <= np.datetime64(CRISIS_END))
    return int(((y == 1) & in_crisis).sum())
