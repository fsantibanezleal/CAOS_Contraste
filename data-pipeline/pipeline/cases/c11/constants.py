"""The constants of C11 (decisions D1 to D4 of the U8 sizing): the six windows, the tail levels and the hyperparameter span.

Nothing here is computed; the producer checks of ``tests/contracts_u8/producer_checks.py`` hold the same dates and the
schemas bind them, so a change here that the contract does not follow fails the validation of every document.
"""
from __future__ import annotations

from dataclasses import dataclass

CASE_ID = "C11"
SEED = 42
LEVELS = (0.01, 0.025)
#: decision D1: every hyperparameter is fixed once on this span, which ends before the earliest test window
SPAN = ("1995-01-01", "2003-12-31")
#: the Basel traffic light is defined on 250 observations (MAR32.9); a shorter window carries it as not evaluated (D3)
BASEL_DAYS = 250
SIGNIFICANCE = 0.05
MCS_CONFIDENCE = 0.90
MCS_STATISTIC = "TR"
MCS_BOOTSTRAP = 1000
MCS_BLOCK = 10
Z2_DRAWS = 10_000
MC_DRAWS = 10_000


@dataclass(frozen=True)
class Window:
    window_id: str
    asset_class: str
    start: str
    end: str
    en: str
    es: str


#: decision D2, in the order of the models document: forecast days, inclusive
WINDOWS = (
    Window("equity-2007-09", "equity", "2007-07-02", "2009-06-30", "Equity 2007 to 2009: the financial crisis",
           "Renta variable 2007 a 2009: la crisis financiera"),
    Window("equity-2020", "equity", "2020-02-03", "2020-06-30", "Equity 2020: the pandemic crash",
           "Renta variable 2020: la caída de la pandemia"),
    Window("rates-2022", "rates", "2022-01-03", "2022-12-30", "Rates 2022: the hiking cycle",
           "Tasas 2022: el ciclo de alzas"),
    Window("fx-2008", "fx", "2008-07-01", "2009-06-30", "FX 2008: the euro against the dollar in the crisis",
           "Divisas 2008: el euro frente al dólar en la crisis"),
    Window("mixed-2023", "mixed", "2023-03-01", "2023-05-31", "Mixed 2023: the bank turmoil",
           "Mixta 2023: la turbulencia bancaria"),
    Window("calm-2004-06", "mixed", "2004-01-02", "2006-12-29", "Calm 2004 to 2006: the control window",
           "Calma 2004 a 2006: la ventana de control"),
)
WINDOW_BY_ID = {w.window_id: w for w in WINDOWS}

#: the mixed portfolio, the same composition in the mixed 2023 and the calm 2004-06 windows (decision D4)
MIXED_WEIGHTS = {"french-daily": 0.5, "treasury-par": 0.3, "h10-fx": 0.2}
PORTFOLIO_OF = {"equity": {"french-daily": 1.0}, "rates": {"treasury-par": 1.0}, "fx": {"h10-fx": 1.0},
                "mixed": MIXED_WEIGHTS}
