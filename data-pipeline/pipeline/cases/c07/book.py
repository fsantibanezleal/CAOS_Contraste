"""The account book of Banco Andino (a synthetic bank) and the scenario state of its accounts.

One ``Book`` per seed: arrays over all accounts, every one an attribute the three regimes read. A scenario never edits the
book; ``state_at`` returns the state of the accounts under a scenario (days past due, default, B-1 category, watch list,
house price index) from the account's own fixed draws.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.provisions import term_structure as ts

from . import scenarios as sc
from . import sources as src

CLASSES = ("mortgage", "consumer", "commercial")
#: calibration classes by account: class, sub (product or assessment), tier (collateral or risk tier)
SEGMENTS: tuple[dict[str, Any], ...] = (
    {"id": "mortgage-ltv-le80", "klass": "mortgage", "sub": 0, "tier": 0, "b1": "residential-mortgage", "bde": "B.1.1",
     "label": {"en": "Residential mortgages, LTV up to 80%", "es": "Hipotecario vivienda, PVG hasta 80 %"},
     "bde_label": {"en": "Main residence, LTV up to 80%", "es": "Vivienda habitual, LTV hasta 80 %"},
     "eir": 0.08, "rho": 0.15},
    {"id": "mortgage-ltv-gt80", "klass": "mortgage", "sub": 0, "tier": 1, "b1": "residential-mortgage", "bde": "B.1.2",
     "label": {"en": "Residential mortgages, LTV above 80%", "es": "Hipotecario vivienda, PVG sobre 80 %"},
     "bde_label": {"en": "Main residence, LTV above 80%", "es": "Vivienda habitual, LTV sobre 80 %"},
     "eir": 0.08, "rho": 0.15},
    {"id": "consumer-instalment", "klass": "consumer", "sub": 0, "tier": None, "b1": "consumer", "bde": "B.2",
     "label": {"en": "Consumer instalment loans", "es": "Consumo en cuotas"},
     "bde_label": {"en": "Consumer credit", "es": "Crédito al consumo"}, "eir": 0.20, "rho": 0.10},
    {"id": "consumer-cards", "klass": "consumer", "sub": 1, "tier": None, "b1": "consumer", "bde": "B.2.1",
     "label": {"en": "Consumer cards and lines", "es": "Consumo tarjetas y líneas"},
     "bde_label": {"en": "Consumer credit, of which credit cards", "es": "Crédito al consumo, del cual tarjetas de crédito"},
     "eir": 0.30, "rho": 0.04},
    {"id": "commercial-group", "klass": "commercial", "sub": 0, "tier": None, "b1": "commercial-group", "bde": "A.2.2",
     "label": {"en": "Commercial, group assessment", "es": "Comercial, evaluación grupal"},
     "bde_label": {"en": "SMEs", "es": "Pymes"}, "eir": 0.12, "rho": 0.12},
    {"id": "commercial-individual", "klass": "commercial", "sub": 1, "tier": None, "b1": "commercial-individual", "bde": "A.2.1",
     "label": {"en": "Commercial, individual assessment", "es": "Comercial, evaluación individual"},
     "bde_label": {"en": "Large corporates", "es": "Grandes empresas"}, "eir": 0.08, "rho": 0.20},
)
SEG_IDS = tuple(s["id"] for s in SEGMENTS)


def seg_index(klass: str, sub: int, tier: int) -> int:
    if klass == "mortgage":
        return tier
    if klass == "consumer":
        return 2 + sub
    return 4 + sub


#: the case's structural assumptions (each labelled "assumption of the case" in the documents and the case page)
PARAMS: dict[str, Any] = {
    "generator_version": "banco-andino-synthetic/1.0.0",
    "total_exposure_clp": 6.0e12,
    "accounts": {"mortgage": 30000, "consumer-instalment": 60000, "consumer-cards": 55000,
                 "commercial-group": 25000, "commercial-individual": 1500},
    "sub_share": {"mortgage": [1.0], "consumer": [src.target("consumer product split: instalment loans"),
                                                  1.0 - src.target("consumer product split: instalment loans")],
                  "commercial": [0.40, 0.60]},
    "arrears_ratio": 1.2,          # exposure in 1 to 89 days past due as a multiple of the 90-day ratio
    "flow_factor": 0.5,            # annual default rate = flow_factor x the 90-day stock ratio
    "tier_pd_multiplier": 2.5,     # PD of the high tier over the low tier (before the level is normalised)
    "pd_dispersion": 0.6, "drift_dispersion": 0.45, "arrears_pd_multiplier": 1.8, "watch_pd_multiplier": 1.5,
    "ccf": 0.5,                    # credit conversion factor of the individual commercial undrawn amount
    "haircut": 0.20,               # realisable and adjusted collateral value = (1 - haircut) x appraisal
    "individual_category_weights": {"low": [0.10, 0.25, 0.35, 0.30], "high": [0.30, 0.20, 0.15, 0.15, 0.10, 0.10]},
    "individual_pd_over_pi": 0.8,  # internal PD of an individual debtor = 0.8 x the statutory PI of its category
    "guarantor_share": 0.10, "guarantor_cover": 0.5,
    "lgd_floor": 0.0, "mortgage_recovery_cap": 0.90,
    "consumer_recovery": {"consumer-instalment": 0.38, "consumer-cards": 0.22},
    "group_recovery_extra": [0.15, 0.35],
    "individual_recovery_extra": [0.0, 0.25],
    "recovery_months": [12, 24],
    "uf_value": src.UF_VALUE, "uf_date": src.UF_DATE,
    "median_exposure": {"mortgage-uf": 1400.0, "consumer-instalment": 4.0e6, "consumer-cards": 1.5e6,
                        "commercial-group": 3.0e7, "commercial-individual": 6.0e8},
    "exposure_sigma": {"mortgage": 0.6, "consumer-instalment": 0.7, "consumer-cards": 0.8, "commercial-group": 0.9,
                       "commercial-individual": 1.0},
}

STATE_CODES = ("performing", "arrears", "default")


@dataclass
class Book:
    """Arrays over the accounts. ``e`` is the exposure subject to provisions in CLP (loans, plus the converted undrawn
    amount for the individual commercial accounts)."""

    seed: int
    scale: float
    klass: np.ndarray            # int8 index into CLASSES
    sub: np.ndarray              # int8
    tier: np.ndarray             # int8
    seg: np.ndarray              # int8 index into SEGMENTS
    state: np.ndarray            # int8 0 performing, 1 arrears, 2 default (base state)
    e: np.ndarray
    drawn: np.ndarray
    undrawn: np.ndarray
    dpd: np.ndarray              # int64, base state
    forborne: np.ndarray
    watch: np.ndarray
    eir: np.ndarray
    rho: np.ndarray
    rem: np.ndarray              # int64 months
    amortising: np.ndarray
    pd_orig: np.ndarray          # annual TTC PD at origination
    pd_now: np.ndarray           # annual TTC PD now
    pvg: np.ndarray              # mortgage, nan elsewhere
    ptvg: np.ndarray             # group commercial, nan without guarantee
    coll_cover: np.ndarray       # collateral appraisal over exposure (appraisal of the individual and group accounts, 1/pvg for mortgages)
    has_mortgage: np.ndarray     # consumer
    arrears30: np.ndarray        # consumer
    cat: np.ndarray              # int8 0..9 for A1..B4, -1 for default and non-individual
    guarantor: np.ndarray        # bool: individual debtor with a guarantor of category A1
    recovery_x: np.ndarray       # extra recovery share beyond the collateral
    u_roll: np.ndarray
    u_real: np.ndarray
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(self.e.size)

    def mask(self, seg_id: str) -> np.ndarray:
        return self.seg == SEG_IDS.index(seg_id)

    def digest(self) -> str:
        """SHA-256 of the portfolio: the accounts and their draws (money to 0.01, the rest to 9 digits)."""
        h = hashlib.sha256()
        for name in ("klass", "sub", "tier", "seg", "state", "dpd", "forborne", "watch", "rem", "amortising", "has_mortgage",
                     "arrears30", "cat", "guarantor"):
            h.update(np.ascontiguousarray(getattr(self, name)).tobytes())
        for name in ("e", "drawn", "undrawn"):
            h.update(np.ascontiguousarray(np.round(getattr(self, name), 2)).tobytes())
        for name in ("eir", "rho", "pd_orig", "pd_now", "pvg", "ptvg", "coll_cover", "recovery_x", "u_roll", "u_real"):
            h.update(np.ascontiguousarray(np.round(getattr(self, name), 9)).tobytes())
        return h.hexdigest()


@dataclass(frozen=True)
class State:
    """The state of the accounts under one scenario."""

    scenario_id: str
    z_shift: float
    hpi: float
    dpd: np.ndarray
    default: np.ndarray
    cat: np.ndarray
    watch: np.ndarray


def dpd_bucket(dpd: int) -> str:
    """The days-past-due bucket names of the engine's B-1 tables."""
    if dpd <= 0:
        return "0"
    if dpd <= 29:
        return "1-29"
    if dpd <= 59:
        return "30-59"
    if dpd <= 89:
        return "60-89"
    return "default"


def state_at(book: Book, scenario: dict[str, Any]) -> State:
    """Account states under a scenario. An account moves to default when its own draw is below its extra default
    probability (the PIT PD at the variant's factor minus the PIT PD at current conditions, plus the scenario channel);
    when its draw is below ROLL_RATIO times that, it moves one arrears bucket (30 days). Individual debtors are
    downgraded two notches instead of rolling. Nested by construction: a harsher scenario moves a superset."""
    return _state(book, scenario)


def _state(book: Book, scenario: dict[str, Any]) -> State:
    z = float(scenario["z_shift"])
    pit_now = _pit(book, 0.0)
    pit_scen = _pit(book, z)
    extra = np.maximum(0.0, pit_scen - pit_now)
    names = np.array(CLASSES)[book.klass]
    for ch, p in scenario.get("channels", {}).items():
        if ch == "commercial-group":
            extra = extra + np.where(book.seg == SEG_IDS.index("commercial-group"), p, 0.0)
        else:
            extra = extra + np.where(names == ch, p, 0.0)
    performing_like = book.dpd < 90
    to_default = performing_like & (book.u_roll < extra)
    rolled = performing_like & ~to_default & (book.u_roll < extra * (1.0 + sc.ROLL_RATIO))
    individual = book.seg == SEG_IDS.index("commercial-individual")
    dpd = book.dpd.copy()
    r = rolled & ~individual
    dpd[r] = np.minimum(89, np.where(dpd[r] == 0, 15, dpd[r] + 30))
    dpd[to_default] = 91 + np.floor(book.u_real[to_default] * 200).astype(np.int64)
    cat = book.cat.copy()
    down = rolled & individual & (cat >= 0)
    cat[down] = np.minimum(9, cat[down] + 2)
    default = dpd >= 90
    cat[default & individual] = -1
    watch = book.watch | (individual & (cat >= 6)) | (rolled & ~individual & (dpd > 30))
    return State(scenario["id"], z, float(scenario["hpi"]), dpd, default, cat, watch)


def _pit(book: Book, z: float) -> np.ndarray:
    out = np.empty(book.n)
    for rho in np.unique(book.rho):
        m = book.rho == rho
        out[m] = ts.ttc_to_pit(np.clip(book.pd_now[m], 1e-6, 0.99), float(rho), np.full(int(m.sum()), z))
    return out
