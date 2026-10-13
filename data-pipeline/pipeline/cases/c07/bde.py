"""Banco de Espana Circular 4/2017 Annex 9 (alternative solutions) on the book, through ``riskvalidation.provisions.local_es``.

The category of an account follows the facts Annex 9 uses (days past due, forbearance, watch list), never a model PD: more
than 90 days past due is doubtful, 31 to 90 days past due, forborne or on the watch list is normal under special watch,
anything else is normal. The coverage is the engine's ``annex9_coverage`` on the amount not covered by guarantees, the
guarantees adjusted by the case's collateral haircut (the Annex 9 haircut table is not transcribed in the engine, dossier 03
K.3, so the case states 20 per cent, assumption of the case).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from riskvalidation.provisions import local_es as es

from . import book as bk
from .book import PARAMS, Book, State

CATEGORIES = ("normal", "normal-special-watch", "doubtful", "written-off")


def category(book: Book, state: State) -> np.ndarray:
    cat = np.full(book.n, "normal", dtype=object)
    special = state.watch | book.forborne | ((state.dpd > 30) & (state.dpd < 90))
    cat[special] = "normal-special-watch"
    cat[state.dpd >= 90] = "doubtful"
    return cat


def adjusted_guarantee(book: Book, state: State) -> np.ndarray:
    """Adjusted value of the effective guarantees (appraisal times one minus the haircut, real estate moved by the house
    price index; the group commercial guarantees are not revalued)."""
    keep = 1.0 - PARAMS["haircut"]
    hpi_applies = np.isin(book.seg, [0, 1, bk.SEG_IDS.index("commercial-individual")])
    value = book.e * book.coll_cover * np.where(hpi_applies, 1.0 + state.hpi, 1.0)
    return keep * value


@dataclass
class BdeResult:
    provision: np.ndarray
    category: np.ndarray


def coverage(book: Book, state: State) -> BdeResult:
    cats = category(book, state)
    adj = adjusted_guarantee(book, state)
    prov = np.zeros(book.n)
    codes = [s["bde"] for s in bk.SEGMENTS]
    for i in range(book.n):
        c = cats[i]
        prov[i] = es.annex9_coverage(codes[int(book.seg[i])], str(c), float(book.e[i]), [float(adj[i])],
                                     int(state.dpd[i]) if c == "doubtful" else None)
    return BdeResult(prov, cats)
