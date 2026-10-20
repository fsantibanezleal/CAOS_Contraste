"""The constants of the C18 bake: the windows, the loan-type map, the named parameters, the engine settings and the scenario ids.

Nothing here is a result: every satellite, marginal, aggregate, band row, capital path and reverse-stress scenario is returned by
``riskvalidation`` (ADR-0069). A named parameter is a value the sources do not give, written with its value, its basis and the label
``convention`` or ``case assumption`` (decision W6 of the U13 sizing approves these values).
"""
from __future__ import annotations

from typing import Any

CASE_ID = "C18"
FIT_ID = "banco-andino"
AS_OF = "2026-08-31"                      # the observation date: the CMF aggregates of August 2026 (C07, C15)
JUMP_OFF = "2025-12-31"                   # the last quarter of the Fed history: the scenarios start the quarter after (2026 Q1)
SEED = 18
N_DRAWS = 1_000_000
CHUNK = 100_000
LEVEL = 0.999
HORIZON_YEARS = 1
BOUNDS_N = 100_000
BOUNDS_EPSILON = 1e-3
EC_TOLERANCE = 0.01
N_PATHS_IRRBB = 1_000_000
CREDIT_NAMES = (400, 1600)                # the representative names of each C07 segment in the grouped copula, measured at both (the accounts number 171,500; decision Z15)
CREDIT_LGD_GAMMA = 0.0                    # a deterministic LGD per segment (C07 states one LGD per segment)

FIT_START = "1985-03-31"
FIT_END = "2019-12-31"
BACKCAST_START = "2020-03-31"
BACKCAST_END = "2025-12-31"
DESCRIPTIVE_2026 = ("2026-03-31", "2026-06-30")
AR_ORDER = 1
LAGS = (0, 1)
REGRESSORS = ("real_gdp_growth", "unemployment_rate")
HORIZON_QUARTERS = 12
REVERSION_QUARTERS = 12
GFC_START = "2008-03-31"
GFC_END = "2009-12-31"

#: Fed loan type -> (column of the Board's table, link, first quarter the Board publishes the series)
FED_TYPES: dict[str, tuple[str, str, str]] = {
    "commercial-industrial": ("CI", "probit", "1985-03-31"),
    "commercial-real-estate": ("RECI", "identity", "1991-03-31"),
    "residential": ("RERES", "identity", "1991-03-31"),
    "credit-cards": ("CONCC", "probit", "1985-03-31"),
    "other-consumer": ("CONOTH", "probit", "1985-03-31"),
}
CLASSES = ("commercial", "consumer", "mortgage")
#: Banco Andino class -> (Fed loan types, weights); the weights are the case's mapping (decision Q6), an adaptation
CLASS_MAP: dict[str, tuple[tuple[str, ...], tuple[float, ...]]] = {
    "commercial": (("commercial-industrial", "commercial-real-estate"), (0.6, 0.4)),
    "consumer": (("credit-cards", "other-consumer"), (0.5, 0.5)),
    "mortgage": (("residential",), (1.0,)),
}
#: the C07 segment -> the Banco Andino class of the loan mix
SEGMENT_CLASS = {"mortgage-ltv-le80": "mortgage", "mortgage-ltv-gt80": "mortgage", "consumer-instalment": "consumer",
                 "consumer-cards": "consumer", "commercial-group": "commercial", "commercial-individual": "commercial"}
#: the expected sign of a satellite coefficient, declared before the fit: a higher rate of growth lowers the loss rate, a higher
#: unemployment raises it at once; its lag enters as the offset of the first (a change), so no sign is claimed for it
EXPECTED_SIGN = {"intercept": "none", "ar_1": "positive", "real_gdp_growth_lag0": "negative", "real_gdp_growth_lag1": "negative",
                 "unemployment_rate_lag0": "positive", "unemployment_rate_lag1": "none"}

RISKS = ("credit", "market", "irrbb", "operational")
SCENARIOS = {"baseline": "baseline", "eba": "eba-2025-adverse", "fed": "fed-2026-severely-adverse", "ngfs": "ngfs-delayed-transition"}
FILE_NAMES = {"baseline": "baseline", "eba": "eba-2025-adverse", "fed": "fed-2026-severely-adverse", "ngfs": "ngfs-delayed-transition",
              "aggregation": "t-copula-baseline", "reverse": "reverse-stress"}
DEFAULT_VARIANT = "fed-2026-severely-adverse"
MODELS_REL = f"{CASE_ID}/models-{FIT_ID}.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
RAW_REL = f"{CASE_ID}/raw-sources.txt"

#: the C17 variant C18 reads (decision Y1)
C17_VARIANT = "xi-0-8"
CMF_ANCHOR_CET1 = 0.11
STACK = {"cet1_min": 0.045, "c_ccob": 0.025, "c_ccyb": 0.005, "c_dsib": 0.015}
P2_CAP = 0.04
#: the Banco Santander-Chile Form 20-F 2025 figures (dossier 03 l.1324-1328, Ch$ million), used as ratios only (derived-only, E5)
SANTANDER = {"rwa": 41_715_467.0, "credit": 29_551_588.0, "market": 7_143_966.0, "effective_equity": 7_047_321.0, "pillar2": 52_144.0}

NU_SET = (4.0, 8.0, 30.0)
CORR_ORDER = list(RISKS)
CORR_BASE = [[1.0, 0.5, 0.5, 0.2], [0.5, 1.0, 0.5, 0.2], [0.5, 0.5, 1.0, 0.2], [0.2, 0.2, 0.2, 1.0]]
CORR_STRESS = [[1.0, 0.8, 0.5, 0.2], [0.8, 1.0, 0.5, 0.2], [0.5, 0.5, 1.0, 0.2], [0.2, 0.2, 0.2, 1.0]]
C_P2 = 0.01
C_D = 0.01
REVERSE_P2_CET1 = 0.000625
PPNR_FEE = 0.25
PPNR_COST = 0.55
TRADING_DAYS = 250
SOURCE_LEVEL = 0.99
GX_BUDGET = 0.05
REVERSE_SEED = 1802

#: the as-of date of the BCCh EUR to CLP series
FX_SERIES = "F072.CLP.EUR.N.O.D"
FX_FIRST = "2026-08-01"
FX_LAST = "2026-08-31"

DERIVED = "data/derived"


def text(en: str, es: str | None = None) -> dict[str, str]:
    return {"en": en, "es": es if es is not None else en}


def quarter_end(year: int, quarter: int) -> str:
    return f"{year:04d}-{('03-31', '06-30', '09-30', '12-31')[quarter - 1]}"


def quarter_label_end(label: str) -> str:
    """``1985Q1`` or ``1985 Q1`` -> ``1985-03-31``."""
    year, q = label.replace(" ", "").split("Q")
    return quarter_end(int(year), int(q))


def next_quarters(last: str, n: int) -> list[str]:
    y, m = int(last[:4]), int(last[5:7])
    idx = y * 4 + m // 3 - 1
    out = []
    for k in range(1, n + 1):
        i = idx + k
        out.append(quarter_end(i // 4, i % 4 + 1))
    return out


def year_ends(n_years: int = 3) -> list[str]:
    start = int(JUMP_OFF[:4])
    return [f"{start + k}-12-31" for k in range(1, n_years + 1)]


def asdict(**kw: Any) -> dict[str, Any]:
    return dict(kw)
