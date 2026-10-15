"""The parameters of C10, committed with their sources (CT-1103, CT-1105, CT-1108, CT-1111).

Everything here is an input of the case: the windows of the contract, the five loan types and their IRB classes, the pinned
Federal Reserve page, the shape of the illustrative portfolios and the simulator grid. No number here is a result; a
result is computed by ``riskvalidation`` in ``documents`` and ``bake``.
"""
from __future__ import annotations

from typing import Any

CASE_ID = "C10"
GENERATOR = "contraste.c10.vasicek-lhp-simulator"

#: the contract's windows (c10-outputs, ``windows``): the fit window ends before the evaluation window begins
FIT = {"first_year": 1985, "last_year": 2006, "n_years": 22}
EVALUATION = {"first_year": 2007, "last_year": 2012, "n_years": 6}
QUARTERS_EXPECTED = 4 * (EVALUATION["last_year"] - FIT["first_year"] + 1)
LEVELS = (0.99, 0.999)
BACKTEST_LEVELS = (0.95, 0.99, 0.999)
QUANTILE_LEVELS = (0.5, 0.9, 0.95, 0.99, 0.999)
CURRENCY = "USD"

#: the loan types of the case (SDD section 5): the Board's column, the nearest IRB class of the Basel framework and its
#: paragraph. The IRB class is the closest regulatory class to the Board's loan type, not a claim that the Board's series
#: is that class (the Board's commercial real estate series is not the HVCRE class, which is a stricter subset).
LOAN_TYPES: tuple[dict[str, Any], ...] = (
    {"id": "commercial-industrial", "label": {"en": "Commercial and industrial", "es": "Comerciales e industriales"},
     "irb_asset_class": "corporate", "irb_reference": "CRE31.5"},
    {"id": "commercial-real-estate", "label": {"en": "Commercial real estate", "es": "Inmobiliario comercial"},
     "irb_asset_class": "hvcre", "irb_reference": "CRE31.11"},
    {"id": "residential", "label": {"en": "Residential real estate", "es": "Crédito hipotecario residencial"},
     "irb_asset_class": "residential_mortgage", "irb_reference": "CRE31.14"},
    {"id": "credit-cards", "label": {"en": "Credit cards", "es": "Tarjetas de crédito"},
     "irb_asset_class": "qrre", "irb_reference": "CRE31.15"},
    {"id": "other-consumer", "label": {"en": "Other consumer", "es": "Otro consumo"},
     "irb_asset_class": "other_retail", "irb_reference": "CRE31.16"},
)
IRB_REGIME = "basel3"
IRB_MATURITY = 2.5   # years, the supervisory default of a non-retail class; retail classes carry none

#: the page the case reads, pinned. The saved page carries a per-request script token, so two fetches differ in their bytes:
#: the page is identified by its bytes (this fetch) and, over the years the case uses, by the digest of its numbers.
RAW = {
    "source": "fed-chargeoff",
    "table": "chgallsa",
    "url": "https://www.federalreserve.gov/releases/chargeoff/chgallsa.htm",
    "name": "chgallsa.htm",
    "retrieved": "2026-10-13",
    "files_as_of": "2026-08-25",
    "bytes": 131057,
    "sha256": "eee388f9681023ccc130542af90966abef657217c1a151bfb0c51d9e8588fa11",
    "window_sha256": "af9d1e59aed95c88857b6521b9b4a8407c5d006bb9633f8dc293a03320ea4f16",
    "folder": "fed-chargeoff",
}

# --- the illustrative portfolio (constructed per loan type; never a bank's) -----------------------------------------
TOTAL_EAD = 100_000_000.0
LGD = 0.45                 # one expected LGD for every name: the case isolates correlation, concentration and tail
LGD_GAMMA = 0.25           # V[LGD] = gamma E[LGD] (1 - E[LGD]), Gordy and Lutkebohmert (2013) eq. 16, a typical value
XI = 0.25                  # the precision of the Gamma systematic factor of the granularity adjustment (the paper's value)
LOSS_UNIT = 1_000.0        # CreditRisk+ loss unit: LGD x EAD of every group is a whole number of units
NU = 5.0                   # degrees of freedom of the Student-t copula (rung C3)
SECTOR_CORRELATION = 0.5   # correlation between the two sector factors of the multi-factor rung
#: group id, label, share of the groups' PD relative to the portfolio's fitted PD, and the sector of the multi-factor rung
GROUP_STYLE: tuple[dict[str, Any], ...] = (
    {"id": "g-large", "label": {"en": "Large names", "es": "Nombres grandes"}, "pd_multiple": 0.5, "sector": "core"},
    {"id": "g-mid", "label": {"en": "Mid-size names", "es": "Nombres medianos"}, "pd_multiple": 1.0, "sector": "core"},
    {"id": "g-small", "label": {"en": "Small names", "es": "Nombres pequeños"}, "pd_multiple": 1.5, "sector": "periphery"},
)
#: per loan type: (names, exposure of each) of the three groups; every group has a whole number of loss units
PORTFOLIO_SHAPE: dict[str, tuple[tuple[int, float], ...]] = {
    "commercial-industrial": ((20, 2_000_000.0), (100, 400_000.0), (1000, 20_000.0)),
    "commercial-real-estate": ((10, 4_000_000.0), (40, 1_000_000.0), (500, 40_000.0)),
    "residential": ((50, 400_000.0), (200, 200_000.0), (2000, 20_000.0)),
    "credit-cards": ((100, 100_000.0), (400, 100_000.0), (2500, 20_000.0)),
    "other-consumer": ((100, 200_000.0), (500, 80_000.0), (2000, 20_000.0)),
}

# --- the Monte Carlo ladder (full size; ``scale`` shrinks it for the tests) -----------------------------------------------
FULL_SCENARIOS = 1_000_000
FULL_IS_SCENARIOS = 100_000
FULL_CRP_SAMPLE = 400_000
LHP_LIKE_NAMES = 5_000     # identical names of the Monte Carlo convergence check against the LHP anchor
FULL_CONVERGENCE_SCENARIOS = 200_000
CHUNK_BYTES = 150_000_000  # one chunk of the copula holds at most this many bytes of float64 (the engine keeps a few copies alive)
EULER_TOLERANCES = {"var": 0.01, "es": 1e-6}
FULL_BOOTSTRAP = 500
SIM_SEED = 7001
SEEDS = {"sim": SIM_SEED, "c2-gaussian-1f": 4001, "c2-gaussian-mf": 4002, "c3-student-t": 4003, "c6-is-gaussian": 4004, "convergence": 4005,
         "crp": 4006, "bootstrap": 4007}

# --- the simulator (known correlation) --------------------------------------------------------------------------------
KNOWN_PD = 0.02
RHO_GRID = tuple(round(0.02 * k, 2) for k in range(1, 13))
SERIES_LENGTHS = (22, 40)
NULL_RHO = 0.12
ALPHA = 0.05
FULL_REPLICATIONS = 400     # the moments interval is a 100-draw bootstrap per replication (about 2 s): 1,000 would take hours
SIM_BOOTSTRAP = 100        # the engine's minimum, for the method-of-moments test of each replication
