"""CMF CNCB Chapter B-1 on the book: every provision comes from ``riskvalidation.provisions.local_cl``.

The product picks the engine function that applies to an account (its B-1 portfolio and days-past-due bucket) and sums;
it never carries a factor, a table cell or a threshold of B-1 (ADR-0069). The recoverable amount of a defaulted individual
debtor and the collateral at realisable value are the case's inputs (``recovery`` and ``PARAMS['haircut']``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.provisions import local_cl as cl

from . import book as bk
from .book import Book, State

CAT_LABELS = ("A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4")
INDIVIDUAL_ID = bk.SEG_IDS.index("commercial-individual")
GROUP_ID = bk.SEG_IDS.index("commercial-group")
CARDS_ID = bk.SEG_IDS.index("consumer-cards")
CONSUMER_IDS = (bk.SEG_IDS.index("consumer-instalment"), CARDS_ID)
MORTGAGE_IDS = (0, 1)


def recovery(book: Book, hpi: float) -> np.ndarray:
    """The recovered share of the exposure of an account that defaults (collateral at realisable value plus the
    case's extra recovery), under a house price index change; the one source of the B-1 recoverable amount, the Stage 3
    recoveries and the LGD of the performing accounts."""
    p = bk.PARAMS
    keep = 1.0 - p["haircut"]
    r = np.empty(book.n)
    for sid in MORTGAGE_IDS:
        m = book.seg == sid
        r[m] = np.minimum(p["mortgage_recovery_cap"], keep * book.coll_cover[m] * (1.0 + hpi))
    for sid in CONSUMER_IDS:
        m = book.seg == sid
        r[m] = np.clip(p["consumer_recovery"][bk.SEG_IDS[sid]] + (book.recovery_x[m] - 0.5) * 0.2, 0.05, 0.6)
    m = book.seg == GROUP_ID
    r[m] = np.clip(keep * np.nan_to_num(book.coll_cover[m]) + book.recovery_x[m], 0.0, 0.95)
    m = book.seg == INDIVIDUAL_ID
    r[m] = np.clip(keep * book.coll_cover[m] * (1.0 + hpi) + book.recovery_x[m], 0.0, 0.97)
    return r


@dataclass
class B1Result:
    provision: np.ndarray            # (A,) statutory provision per account, before the minimum
    category: np.ndarray             # (A,) object: B-1 default category C1..C6 for defaulted individual debtors, else ''
    normal_mask: np.ndarray          # individually assessed normal portfolio (A1 to A6)
    individual_normal_substandard: float
    individual_default: float


def provisions(book: Book, state: State) -> B1Result:
    """The B-1 provision of every account under a state, through the engine."""
    prov = np.zeros(book.n)
    cats = np.full(book.n, "", dtype=object)
    r = recovery(book, state.hpi)
    keep = 1.0 - bk.PARAMS["haircut"]
    for i in range(book.n):
        sid = int(book.seg[i])
        d = int(state.dpd[i])
        e = float(book.e[i])
        if sid in MORTGAGE_IDS:
            pe = cl.b1_mortgage_pe(float(book.pvg[i]), bk.dpd_bucket(d))[2]
            prov[i] = cl.b1_group_provision(e, pe)
        elif sid in CONSUMER_IDS:
            product = "instalment" if sid == CONSUMER_IDS[0] else "cards-lines-other"
            pe = cl.b1_consumer_pe(d, bool(book.has_mortgage[i]), bool(book.arrears30[i]), product)[2]
            prov[i] = cl.b1_group_provision(e, pe)
        elif sid == GROUP_ID:
            ptvg = None if np.isnan(book.ptvg[i]) else float(book.ptvg[i])
            pe = cl.b1_commercial_pe(bk.dpd_bucket(d), ptvg)[2]
            prov[i] = cl.b1_group_provision(e, pe)
        elif state.default[i]:
            _tpe, category, p = cl.b1_default_provision(e, float(min(e, r[i] * e)))
            prov[i] = p
            cats[i] = category
        else:
            eap = max(0.0, e * (1.0 - keep * float(book.coll_cover[i]) * (1.0 + state.hpi)))
            ea = bk.PARAMS["guarantor_cover"] * eap if book.guarantor[i] else 0.0
            prov[i] = cl.b1_individual_provision(eap, ea, CAT_LABELS[int(state.cat[i])], "A1" if ea > 0 else None)
    ind = book.seg == INDIVIDUAL_ID
    normal = ind & ~state.default & (state.cat >= 0) & (state.cat <= 5)
    sub = ind & ~state.default & (state.cat >= 6)
    return B1Result(prov, cats, normal, float(prov[sub].sum()) + float(prov[normal].sum()),
                    float(prov[ind & state.default].sum()))


def minimum_check(book: Book, state: State, res: B1Result) -> Any:
    """The 0.50 per cent minimum on the individually assessed normal portfolio (A1 to A6) only."""
    return cl.b1_minimum_normal_check(float(book.e[res.normal_mask].sum()), float(res.provision[res.normal_mask].sum()))
