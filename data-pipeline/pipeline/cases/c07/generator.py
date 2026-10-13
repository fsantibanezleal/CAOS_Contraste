"""The synthetic Banco Andino: a seeded generator calibrated to the CMF aggregates of ``sources.TARGETS``.

Design (docs/design/features/c07/design.md). The accounts are drawn once per seed (fixed uniform and normal draws). The
state of an account (performing, 1 to 89 days past due, default) is assigned by quota, so the 90-day ratio of each portfolio
is its target. Each portfolio has one *tier share* ``y`` (the share of high-LTV mortgages, of consumer debtors with
arrears in the system, of unguaranteed group commercial loans and high-category individual debtors): the exposure of every
(sub-portfolio, state, tier) class is then fixed so that the exposure-weighted B-1 provision index equals the CMF index.
The B-1 factor of each account is the engine's (``b1.provisions``); the product solves the one linear equation in ``y`` and
rescales exposures, it computes no B-1 number. Money is CLP; UF-indexed mortgages are converted at the SII value of
``sources.UF_DATE``.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.provisions import ecl as ecl_mod
from riskvalidation.provisions import local_cl as cl

from . import b1
from . import book as bk
from . import sources as src
from .book import PARAMS, SEG_IDS, Book

MIN_STATE = 2
PD_CLIP = (1e-4, 0.60)
TARGET = {
    "mix": {"mortgage": src.target("loan mix: mortgage"), "consumer": src.target("loan mix: consumer"),
            "commercial": src.target("loan mix: commercial")},
    "index": {"mortgage": src.target("provision index: mortgage"), "consumer": src.target("provision index: consumer"),
              "commercial": src.target("provision index: commercial")},
    "dr": {"mortgage": src.target("90-day delinquency: mortgage"), "consumer": src.target("90-day delinquency: consumer"),
           "commercial": src.target("90-day delinquency: commercial")},
}


class CalibrationError(ValueError):
    """A target the structural assumptions cannot reach."""


def _strat(n: int, rng: np.random.Generator) -> np.ndarray:
    return (rng.permutation(n) + rng.random(n)) / n


def _count(kind: str, scale: float) -> int:
    return max(40, int(round(PARAMS["accounts"][kind] * scale))) if kind != "commercial-individual" else max(30, int(round(PARAMS["accounts"][kind] * scale)))


_DRAWS = ("u_state", "u_tier", "u_dpd", "u_dpd2", "u_col", "u_pvg", "u_cat", "u_f", "u_w", "u_g", "u_coll", "u_rem", "u_x",
          "u_ud", "u_roll", "u_real")
_NORMALS = ("n_size", "n_pd", "n_drift")


def draws(seed: int, scale: float) -> dict[str, dict[str, np.ndarray]]:
    """Every random draw of the book, per block, in a fixed order (the same seed gives the same book)."""
    out: dict[str, dict[str, np.ndarray]] = {}
    for k, kind in enumerate(("mortgage", "consumer-instalment", "consumer-cards", "commercial-group", "commercial-individual")):
        n = _count(kind if kind != "mortgage" else "mortgage", scale)
        rng = np.random.default_rng([seed, 7, k])
        d = {name: _strat(n, rng) for name in _DRAWS}
        d.update({name: rng.standard_normal(n) for name in _NORMALS})
        d["n"] = n  # type: ignore[assignment]
        out[kind] = d
    return out


def _states(n: int, dr: float, arrears: bool, u: np.ndarray) -> np.ndarray:
    n_def = max(MIN_STATE, int(round(dr * n)))
    n_arr = max(MIN_STATE, int(round(PARAMS["arrears_ratio"] * dr * n))) if arrears else 0
    order = np.argsort(u, kind="stable")
    state = np.zeros(n, dtype=np.int8)
    state[order[:n_def]] = 2
    state[order[n_def:n_def + n_arr]] = 1
    return state


def _tiers(state: np.ndarray, y: float, u: np.ndarray) -> np.ndarray:
    tier = np.zeros(state.size, dtype=np.int8)
    for s in (0, 1, 2):
        idx = np.flatnonzero(state == s)
        if idx.size == 0:
            continue
        k = int(round(y * idx.size))
        if idx.size >= 2:
            k = min(max(k, 1), idx.size - 1)
        order = idx[np.argsort(u[idx], kind="stable")]
        tier[order[:k]] = 1
    return tier


def _dpd(state: np.ndarray, u1: np.ndarray, u2: np.ndarray, kind: str) -> np.ndarray:
    dpd = np.zeros(state.size, dtype=np.int64)
    arrears = state == 1
    if kind == "consumer":
        lo = np.where(u1 < 0.55, 8 + np.floor(u2 * 23), np.where(u1 < 0.85, 31 + np.floor(u2 * 30), 61 + np.floor(u2 * 29)))
        small = (state == 0) & (u2 > 0.8)
        dpd[small] = 1 + np.floor(u1[small] * 7).astype(np.int64)
    else:
        lo = np.where(u1 < 0.5, 1 + np.floor(u2 * 29), np.where(u1 < 0.8, 30 + np.floor(u2 * 30), 60 + np.floor(u2 * 30)))
    dpd[arrears] = np.minimum(89, lo[arrears]).astype(np.int64)
    d = state == 2
    dpd[d] = 91 + np.floor(-np.log1p(-np.minimum(u1[d], 0.999)) * 250).astype(np.int64)
    return dpd


def _cat_from(u: np.ndarray, tier: np.ndarray) -> np.ndarray:
    lo = np.cumsum(PARAMS["individual_category_weights"]["low"])
    hi = np.cumsum(PARAMS["individual_category_weights"]["high"])
    cat = np.where(tier == 0, np.searchsorted(lo, u * lo[-1]), 4 + np.searchsorted(hi, u * hi[-1]))
    return np.minimum(cat, 9).astype(np.int8)


def _assemble(d: dict[str, dict[str, np.ndarray]], y: dict[str, float], seed: int, scale: float) -> Book:
    P = PARAMS
    parts: list[dict[str, Any]] = []
    uf = P["uf_value"]
    for kind, dd in d.items():
        n = int(dd["n"])
        klass = {"mortgage": "mortgage", "consumer-instalment": "consumer", "consumer-cards": "consumer",
                 "commercial-group": "commercial", "commercial-individual": "commercial"}[kind]
        sub = {"mortgage": 0, "consumer-instalment": 0, "consumer-cards": 1, "commercial-group": 0, "commercial-individual": 1}[kind]
        yk = y[kind]
        state = _states(n, TARGET["dr"][klass], kind != "commercial-individual", dd["u_state"])
        tier = _tiers(state, yk, dd["u_tier"])
        dpd = _dpd(state, dd["u_dpd"], dd["u_dpd2"], "consumer" if klass == "consumer" else "other")
        nan = np.full(n, np.nan)
        zero_b = np.zeros(n, dtype=bool)
        a: dict[str, Any] = {"klass": np.full(n, bk.CLASSES.index(klass), np.int8), "sub": np.full(n, sub, np.int8),
                             "tier": tier, "state": state, "dpd": dpd,
                             "pvg": nan.copy(), "ptvg": nan.copy(), "coll_cover": np.zeros(n), "has_mortgage": zero_b.copy(),
                             "arrears30": zero_b.copy(), "cat": np.full(n, -1, np.int8), "guarantor": zero_b.copy()}
        sigma = P["exposure_sigma"]["mortgage" if kind == "mortgage" else kind]
        med = P["median_exposure"]["mortgage-uf" if kind == "mortgage" else kind]
        size = np.exp(np.log(med) + sigma * dd["n_size"])
        if kind == "mortgage":
            a["pvg"] = np.where(tier == 0, 0.25 + 0.55 * dd["u_pvg"], 0.82 + 0.20 * dd["u_pvg"])
            a["coll_cover"] = 1.0 / a["pvg"]
            a["drawn"], a["undrawn"] = size * uf, np.zeros(n)
            a["rem"] = (3 * (20 + np.floor(dd["u_rem"] * 80))).astype(np.int64)
            a["amortising"] = np.ones(n, dtype=bool)
        elif klass == "consumer":
            hi = tier == 1
            a["arrears30"] = hi
            a["has_mortgage"] = np.where(hi, dd["u_col"] < 0.4, dd["u_col"] < 0.5)
            a["drawn"], a["undrawn"] = size, np.zeros(n)
            if kind == "consumer-instalment":
                a["rem"] = (3 * (4 + np.floor(dd["u_rem"] * 16))).astype(np.int64)
                a["amortising"] = np.ones(n, dtype=bool)
            else:
                a["rem"] = np.full(n, 36, dtype=np.int64)
                a["amortising"] = zero_b.copy()
        elif kind == "commercial-group":
            a["ptvg"] = np.where(tier == 0, 0.3 + 0.9 * dd["u_pvg"], np.nan)
            a["coll_cover"] = np.where(tier == 0, 1.0 / np.where(tier == 0, a["ptvg"], 1.0), 0.0)
            a["drawn"], a["undrawn"] = size, np.zeros(n)
            a["rem"] = (3 * (4 + np.floor(dd["u_rem"] * 16))).astype(np.int64)
            a["amortising"] = np.ones(n, dtype=bool)
        else:
            cat = _cat_from(dd["u_cat"], tier)
            cat[state == 2] = -1
            a["cat"] = cat
            a["coll_cover"] = np.where(dd["u_coll"] < 0.6, 0.3 + 0.7 * dd["u_g"], 0.0)
            a["guarantor"] = dd["u_f"] < P["guarantor_share"]
            a["drawn"] = size
            a["undrawn"] = size * (0.1 + 0.5 * dd["u_ud"])
            a["rem"] = (3 * (4 + np.floor(dd["u_rem"] * 27))).astype(np.int64)
            a["amortising"] = np.ones(n, dtype=bool)
        e = ecl_mod.commitment_ead(a["drawn"], a["undrawn"], P["ccf"]) if kind == "commercial-individual" else a["drawn"].copy()
        a["e"] = np.asarray(e, dtype=float)
        a["forborne"] = (dd["u_f"] < np.where(state > 0, 0.06, 0.008)) if kind != "commercial-individual" else \
            (dd["u_f"] > 0.9) & (a["cat"] >= 6)
        a["watch"] = (dd["u_w"] < 0.02) & (state == 0) if kind != "commercial-individual" else (a["cat"] >= 6)
        seg = np.array([bk.seg_index(klass, sub, int(t) if klass == "mortgage" else 0) for t in tier], dtype=np.int8) \
            if klass == "mortgage" else np.full(n, bk.seg_index(klass, sub, 0), np.int8)
        a["seg"] = seg
        sg = [s for s in bk.SEGMENTS if s["id"] == (SEG_IDS[int(seg[0])])][0]
        a["eir"] = np.full(n, sg["eir"])
        a["rho"] = np.full(n, sg["rho"])
        if klass == "commercial" and sub == 1:
            pi = np.array([cl.b1_individual_category(c)[0] for c in b1.CAT_LABELS])
            pd0 = np.where(a["cat"] >= 0, pi[np.maximum(a["cat"], 0)] * P["individual_pd_over_pi"], 0.05)
        else:
            mult = np.where(tier == 1, P["tier_pd_multiplier"], 1.0) if klass != "mortgage" else np.where(tier == 1, P["tier_pd_multiplier"], 1.0)
            pd0 = mult * np.exp(P["pd_dispersion"] * dd["n_pd"] - 0.5 * P["pd_dispersion"] ** 2)
        a["pd_orig"] = pd0
        drift = np.exp(P["drift_dispersion"] * dd["n_drift"] - 0.5 * P["drift_dispersion"] ** 2)
        bump = np.where(state == 1, P["arrears_pd_multiplier"], 1.0) * np.where(a["watch"], P["watch_pd_multiplier"], 1.0)
        a["pd_now"] = pd0 * drift * bump
        a["recovery_x"] = dd["u_x"]
        a["u_roll"], a["u_real"] = dd["u_roll"], dd["u_real"]
        parts.append(a)
    cat = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    return Book(seed=seed, scale=scale, **{k: cat[k] for k in (
        "klass", "sub", "tier", "seg", "state", "e", "drawn", "undrawn", "dpd", "forborne", "watch", "eir", "rho", "rem",
        "amortising", "pd_orig", "pd_now", "pvg", "ptvg", "coll_cover", "has_mortgage", "arrears30", "cat", "guarantor",
        "recovery_x", "u_roll", "u_real")})


def _base_state(book: Book) -> bk.State:
    names = np.array(bk.CLASSES)
    del names
    return bk.State("base", 0.0, 0.0, book.dpd.copy(), book.dpd >= 90, book.cat.copy(), book.watch.copy())


def _class_weights(book: Book, pe: np.ndarray) -> tuple[dict[str, float], dict[tuple, float], dict[tuple, float]]:
    """Solve the tier share per class and return it with the target exposure of every class (state by tier) and the
    class average provision ratios."""
    P = PARAMS
    y: dict[str, float] = {}
    W: dict[tuple, float] = {}
    PE: dict[tuple, float] = {}
    e = book.e
    for kk, klass in enumerate(bk.CLASSES):
        dr, a_ratio = TARGET["dr"][klass], P["arrears_ratio"]
        subs = P["sub_share"][klass]
        a0 = a1 = 0.0
        for sub, share in enumerate(subs):
            members = (book.klass == kk) & (book.sub == sub)
            arrears_possible = not (klass == "commercial" and sub == 1)
            sh = {0: 1.0 - dr - (a_ratio * dr if arrears_possible else 0.0), 1: a_ratio * dr if arrears_possible else 0.0, 2: dr}
            for st in (0, 1, 2):
                for t in (0, 1):
                    m = members & (book.state == st) & (book.tier == t) if klass != "mortgage" else \
                        members & (book.state == st) & (book.tier == t)
                    PE[(klass, sub, st, t)] = float(np.sum(e[m] * pe[m]) / np.sum(e[m])) if np.any(m) else float("nan")
                if sh[st] > 0:
                    p0, p1 = PE[(klass, sub, st, 0)], PE[(klass, sub, st, 1)]
                    a0 += share * sh[st] * (p0 if np.isfinite(p0) else p1)
                    a1 += share * sh[st] * (p1 if np.isfinite(p1) else p0)
        yk = (TARGET["index"][klass] - a0) / (a1 - a0)
        if not 0.0 <= yk <= 1.0:
            raise CalibrationError(f"{klass}: the provision index {TARGET['index'][klass]:.4%} lies outside [{a0:.4%}, {a1:.4%}], the "
                                   "range the B-1 factors of the structural assumptions can reach")
        y[klass] = yk
        for sub, share in enumerate(subs):
            arrears_possible = not (klass == "commercial" and sub == 1)
            sh = {0: 1.0 - dr - (a_ratio * dr if arrears_possible else 0.0), 1: a_ratio * dr if arrears_possible else 0.0, 2: dr}
            for st in (0, 1, 2):
                for t in (0, 1):
                    W[(klass, sub, st, t)] = share * sh[st] * (yk if t == 1 else 1.0 - yk)
    return y, W, PE


def generate(seed: int, scale: float = 1.0) -> Book:
    """The calibrated book of a seed: assemble, solve the tier shares from the engine's B-1 factors, rescale exposures."""
    d = draws(seed, scale)
    yk = {k: 0.3 for k in d}
    ykl = {"mortgage": 0.3, "consumer": 0.3, "commercial": 0.3}
    book = None
    W: dict[tuple, float] = {}
    for _ in range(3):
        yk = {"mortgage": ykl["mortgage"], "consumer-instalment": ykl["consumer"], "consumer-cards": ykl["consumer"],
              "commercial-group": ykl["commercial"], "commercial-individual": ykl["commercial"]}
        book = _assemble(d, yk, seed, scale)
        res = b1.provisions(book, _base_state(book))
        pe = res.provision / book.e
        ykl, W, _pe = _class_weights(book, pe)
        ykl = {k: min(0.98, max(0.02, v)) for k, v in ykl.items()}
    assert book is not None
    P = PARAMS
    total = P["total_exposure_clp"] * scale
    for kk, klass in enumerate(bk.CLASSES):
        class_total = total * TARGET["mix"][klass]
        for sub in range(len(P["sub_share"][klass])):
            for st in (0, 1, 2):
                for t in (0, 1):
                    w = W[(klass, sub, st, t)]
                    m = (book.klass == kk) & (book.sub == sub) & (book.state == st) & (book.tier == t)
                    if w <= 0.0 or not np.any(m):
                        if np.any(m) and w <= 0.0:
                            raise CalibrationError(f"class {(klass, sub, st, t)} holds accounts but no exposure")
                        continue
                    f = w * class_total / float(np.sum(book.e[m]))
                    book.e[m] *= f
                    book.drawn[m] *= f
                    book.undrawn[m] *= f
    book.meta["tier_share"] = {k: float(v) for k, v in ykl.items()}
    _normalise_pd(book)
    return book


def _normalise_pd(book: Book) -> None:
    """Level of the annual PDs: the exposure-weighted mean PD of the performing accounts of each block is the flow factor
    times the 90-day ratio (the individual commercial PDs come from their category and are left as they are)."""
    ff = PARAMS["flow_factor"]
    for kk, klass in enumerate(bk.CLASSES):
        for sub in range(len(PARAMS["sub_share"][klass])):
            if klass == "commercial" and sub == 1:
                continue
            m = (book.klass == kk) & (book.sub == sub)
            live = m & (book.state < 2)
            target = ff * TARGET["dr"][klass]
            cur = float(np.sum(book.e[live] * book.pd_now[live]) / np.sum(book.e[live]))
            c = target / cur
            book.pd_orig[m] = np.clip(book.pd_orig[m] * c, *PD_CLIP)
            book.pd_now[m] = np.clip(book.pd_now[m] * c, *PD_CLIP)
    ind = book.seg == SEG_IDS.index("commercial-individual")
    book.pd_orig[ind] = np.clip(book.pd_orig[ind], *PD_CLIP)
    book.pd_now[ind] = np.clip(book.pd_now[ind], *PD_CLIP)
