"""The Banco Andino banking book of C15: a synthetic CLP and UF balance sheet calibrated to the CMF aggregates.

Reservation R3 of the U10 sizing: the C07 calibration (``cases/c07``) holds the credit book (loan mix, provisions) and no funding side,
no securities and no repricing profile, so the banking-book items IRRBB needs are added here and the extension is stated: the three
loan portfolios and the total exposure are C07's; securities, deposits, equity and loans to banks are the other figures of the same CMF
table (``targets.py``); the UF share of each portfolio, the repricing profile of each item, the deposit split and the NMD requests are
synthetic assumptions (``assumptions.py``), never CMF figures. Money is CLP million in the CLP leg and CLF (UF) million in the UR leg; the
UR leg is converted at the UF value of the valuation date.

The book is balanced by its borrowings: assets less liabilities equal the Tier 1 proxy (the equity of the CMF aggregate, scaled). The UF
share of the borrowings is solved so that the net UF position of a variant is its stated share of Tier 1. A seed perturbs the repricing
profile of every item (a log-normal factor, renormalised), so two seeds give two banks of the same size and the same totals.
The slotting into the 19 buckets and the NMD split are the engine's (``slot_cash_flows``, ``nmd_split``).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.irrbb import behavioural as rv_behavioural
from riskvalidation.irrbb import slotting as rv_slotting

from . import assumptions as asm
from . import targets

GRID = rv_slotting.bucket_grid()
MID = GRID.midpoints
Text = dict[str, str]


def t(en: str, es: str) -> Text:
    return {"en": en, "es": es}


class BookError(ValueError):
    """The stated parameters cannot make a balanced book (a negative borrowing, an item without a profile)."""


@dataclass(frozen=True)
class VariantSpec:
    id: str
    label: Text
    description: Text
    params: dict[str, float]
    cpi_surprise_pp: float | None = None
    offset_state: str = "on"


PARAM_UNITS = {"net_uf_share_tier1": "share of Tier 1", "ur_floating_share": "share of the UF commercial loans",
               "clp_long_asset_share": "share of the CLP fixed commercial loans and securities", "clp_bond_years_scale": "factor on the maturity"}
_BASE = {"net_uf_share_tier1": 0.30, "ur_floating_share": 0.0, "clp_long_asset_share": 0.0, "clp_bond_years_scale": 1.0}


def _spec(vid: str, en: str, es: str, d_en: str, d_es: str, cpi: float | None = None, offset: str = "on", **params: float) -> VariantSpec:
    return VariantSpec(vid, t(en, es), t(d_en, d_es), {**_BASE, **params}, cpi, offset)


SPECS: dict[str, VariantSpec] = {s.id: s for s in (
    _spec("long-uf", "Long UF", "UF largo",
          "A net long UF book: UF assets exceed UF funding by 30 percent of Tier 1, the difference funded in pesos.",
          "Libro con posición neta larga en UF: los activos en UF superan el fondeo en UF en 30 por ciento del Tier 1, financiado en pesos.",
          net_uf_share_tier1=0.30),
    _spec("short-uf", "Short UF", "UF corto",
          "A net short UF book: UF funding exceeds UF assets by 30 percent of Tier 1, so an indexation surprise is a loss.",
          "Libro con posición neta corta en UF: el fondeo en UF supera los activos en UF en 30 por ciento del Tier 1.",
          net_uf_share_tier1=-0.30),
    _spec("cpi-surprise", "CPI surprise +2.5 pp", "Sorpresa de IPC +2,5 pp",
          "The long UF book under a 2.5 percentage point inflation surprise on its net UF position.",
          "El libro largo en UF ante una sorpresa de inflación de 2,5 puntos porcentuales sobre su posición neta en UF.",
          cpi=2.5, net_uf_share_tier1=0.30),
    _spec("clp-steepener", "CLP steepener", "Empinamiento CLP",
          "A near-flat UF position and a CLP book with 35 percent of its fixed loans and securities moved to the long end, so the "
          "long-end rise of the steepener acts on it.",
          "Posicion en UF casi plana y libro en pesos con 35 por ciento de sus créditos fijos y valores en el tramo largo, de modo que el alza "
          "del tramo largo del empinamiento actua sobre el.",
          net_uf_share_tier1=0.05, clp_long_asset_share=0.35),
    _spec("offset-on-off", "CLP/CLF offset on and off", "Compensación CLP/CLF activada y desactivada",
          "A long UF book funded in long CLP bonds (twice the maturity), so the two legs move in opposite directions and the 50 percent "
          "offset can be read on and off.",
          "Libro largo en UF fondeado con bonos largos en pesos (el doble de plazo): los dos tramos se mueven en sentido contrario y la "
          "compensación de 50 por ciento se lee activada y desactivada.",
          offset="compared", net_uf_share_tier1=0.30, clp_bond_years_scale=2.0),
    _spec("floors-active", "Floors active", "Pisos activos",
          "A near-flat UF position with 70 percent of the UF commercial loans floating, the book most exposed to the UR post-shock floor.",
          "Posicion en UF casi plana con 70 por ciento de los créditos comerciales en UF a tasa variable: el libro mas expuesto al piso "
          "posterior al choque de la UR.",
          net_uf_share_tier1=0.05, ur_floating_share=0.70),
)}

#: repricing profiles (times in years and weights) of the items without a stated date: synthetic, see assumptions.item_profiles
PROFILES: dict[str, tuple[tuple[float, ...], tuple[float, ...]]] = {
    "overnight": ((0.0,), (1.0,)),
    "one_month": ((0.05,), (1.0,)),
    "reprice_3m": ((0.2,), (1.0,)),
    "com_fixed": ((0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0), (0.12, 0.18, 0.15, 0.15, 0.20, 0.12, 0.08)),
    "consumer": ((0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0), (0.10, 0.14, 0.20, 0.16, 0.16, 0.12, 0.08, 0.04)),
    "securities_clp": ((0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0), (0.08, 0.10, 0.15, 0.20, 0.20, 0.15, 0.12)),
    "securities_uf": ((1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 18.0), (0.06, 0.10, 0.18, 0.20, 0.16, 0.18, 0.12)),
    # residential mortgages: the prepayment-adjusted average life (about 8 years), not the contractual term of 20 to 25 years
    "mortgage_clp": ((1.0, 3.0, 5.0, 7.0, 10.0, 13.0, 17.0, 22.0), (0.10, 0.17, 0.20, 0.17, 0.14, 0.10, 0.07, 0.05)),
    "mortgage_uf": ((1.0, 3.0, 5.0, 7.0, 10.0, 13.0, 17.0, 22.0), (0.10, 0.17, 0.20, 0.17, 0.14, 0.10, 0.07, 0.05)),
    "com_uf": ((0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0), (0.08, 0.12, 0.18, 0.20, 0.20, 0.14, 0.08)),
    "td_clp": ((0.1, 0.25, 0.5, 0.75, 1.0), (0.25, 0.30, 0.25, 0.12, 0.08)),
    "td_uf": ((0.25, 0.5, 1.0, 1.5, 2.0, 3.0), (0.20, 0.25, 0.25, 0.12, 0.10, 0.08)),
    "bond_clp": ((1.0, 2.0, 3.0, 5.0, 7.0), (0.15, 0.20, 0.25, 0.25, 0.15)),
    "bond_uf": ((3.0, 5.0, 7.0, 10.0, 15.0), (0.15, 0.25, 0.25, 0.20, 0.15)),
    "long": ((8.0, 12.0, 16.0, 22.0), (0.20, 0.30, 0.30, 0.20)),
}
#: the maturities (years) of the rolling tranches of the stated replicating portfolio of each NMD category
TRANCHES = (1.0, 3.0, 5.0, 7.0, 10.0, 12.0)
#: the cap the profile times of a long-dated item may reach after a scale (still inside the 19 buckets)
MAX_YEARS = 40.0


@dataclass
class Item:
    item_id: str
    label: Text
    side: str                    # asset or liability
    category: str
    behavioural_class: str
    source: str
    amount: float                # in the currency of the leg, positive
    flows: np.ndarray            # (19,) signed notional repricing flows in the currency of the leg
    dyn: dict[str, Any]          # how the dynamic NII reads the item: kind and margin


@dataclass
class Leg:
    name: str                    # CLP or UR
    currency: str                # CLP or CLF
    items: list[Item] = field(default_factory=list)

    @property
    def assets_total(self) -> float:
        return float(sum(i.amount for i in self.items if i.side == "asset"))

    @property
    def liabilities_total(self) -> float:
        return float(sum(i.amount for i in self.items if i.side == "liability"))

    @property
    def net_position(self) -> float:
        return self.assets_total - self.liabilities_total


@dataclass
class Book:
    seed: int
    spec: VariantSpec
    uf_value: float
    legs: dict[str, Leg]
    segments: list[dict[str, Any]]
    tier1: float
    aggregates: dict[str, float]
    replicating: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def net_uf_position(self) -> float:
        """The net UF position in CLF million (assets positive)."""
        return self.legs["UR"].net_position

    def digest(self) -> str:
        h = hashlib.sha256()
        for name in ("CLP", "UR"):
            for i in self.legs[name].items:
                h.update(i.item_id.encode())
                h.update(np.ascontiguousarray(np.round(i.flows, 6)).tobytes())
                h.update(np.float64(round(i.amount, 6)).tobytes())
        return h.hexdigest()

    # ------------------------------------------------------------------------------------------------ document blocks

    def items_doc(self, leg: str) -> list[dict[str, Any]]:
        """The ``items`` of a leg as the c15-outputs schema has them (liabilities carry negative flows)."""
        return [{"item_id": i.item_id, "label": i.label, "side": i.side, "category": i.category, "behavioural_class": i.behavioural_class,
                 "source": i.source, "amount": float(i.amount), "cash_flows": flows_list(i.flows)} for i in self.legs[leg].items]

    def segments_doc(self) -> list[dict[str, Any]]:
        return [dict(s) for s in self.segments]

    def assumptions_doc(self) -> dict[str, dict[str, Any]]:
        segs = self.segments
        total = sum(s["balance"] for s in segs)
        reg = asm.REGISTRY

        def a(name: str, value: float) -> dict[str, Any]:
            r = reg[name]
            return {"value": float(value), "unit": r.unit, "source_kind": r.source_kind, "source": r.source}

        return {
            "nmd_core_share": {"value": sum(s["balance"] * s["core_share_used"] for s in segs) / total, "unit": "share",
                               "source_kind": "regulatory-cap",
                               "source": "balance-weighted average of the used values of nmd_segments (the SRP31 Table 4 caps applied to the "
                                         "synthetic requests)"},
            "nmd_core_maturity_years": {"value": sum(s["balance"] * s["core_maturity_used_years"] for s in segs) / total, "unit": "years",
                                        "source_kind": "regulatory-cap", "source": "balance-weighted average of the used values of nmd_segments"},
            "prepayment_cpr": a("prepayment_cpr", asm.PREPAYMENT_CPR),
            "term_deposit_redemption_rate": a("term_deposit_redemption_rate", asm.TERM_DEPOSIT_REDEMPTION_RATE),
            "deposit_beta": a("deposit_beta", asm.DEPOSIT_BETA)}

    def calibration_rows(self) -> list[dict[str, Any]]:
        """The calibration targets of the models document: target, achieved (from the items) and the source line of each."""
        uf = self.uf_value

        def clp(it: Item, leg: str) -> float:
            return it.amount * (uf if leg == "UR" else 1.0)

        items = [(n, i) for n, leg in self.legs.items() for i in leg.items]
        loans = sum(clp(i, n) for n, i in items if i.item_id.startswith(_LOAN_PREFIX))

        def share(prefixes: tuple[str, ...], base: float) -> float:
            return sum(clp(i, n) for n, i in items if i.item_id.startswith(prefixes)) / base

        total_assets = self.aggregates["total_assets"]
        achieved = {
            "loan mix: commercial": share(("CLP-COM", "UR-COM"), loans), "loan mix: consumer": share(("CLP-CON",), loans),
            "loan mix: mortgage": share(("CLP-MTG", "UR-MTG"), loans),
            "loans to banks over total assets": share(("CLP-IBK",), total_assets),
            "securities over total assets": share(("CLP-SEC", "UR-SEC"), total_assets),
            "deposits over total assets": share(("CLP-NMD", "CLP-TD", "UR-TD"), total_assets),
            "equity over total assets": self.tier1 / total_assets}
        out = []
        for r in targets.targets():
            out.append({"metric": r["metric"], "unit": r["unit"], "target": float(r["value"]), "achieved": float(achieved[r["metric"]]),
                        "source": targets.source_text(r), "as_of": r["as_of"]})
        return out


_LOAN_PREFIX = ("CLP-COM", "UR-COM", "CLP-CON", "CLP-MTG", "UR-MTG")


def flows_list(v: np.ndarray) -> list[dict[str, Any]]:
    """The non-zero buckets of a (19,) vector as document flow rows."""
    rows = [{"bucket": k + 1, "midpoint_years": float(MID[k]), "amount": float(v[k])} for k in range(19) if v[k] != 0.0]
    if not rows:
        raise BookError("an item without a flow")
    return rows


def _profile(key: str, rng: np.random.Generator, years_scale: float = 1.0, long_share: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """The jittered times and weights of a profile: a seeded log-normal factor per weight, renormalised; ``long_share`` of the weight is
    moved to the long profile and ``years_scale`` stretches the times."""
    times, weights = (np.array(x, dtype=float) for x in PROFILES[key])
    w = weights * np.exp(asm.JITTER * rng.standard_normal(weights.size))
    w = w / w.sum()
    if long_share > 0.0:
        lt, lw = (np.array(x, dtype=float) for x in PROFILES["long"])
        times = np.concatenate([times, lt])
        w = np.concatenate([(1.0 - long_share) * w, long_share * lw / lw.sum()])
    return np.minimum(times * years_scale, MAX_YEARS), w


def replicating_portfolio(maturity: float) -> dict[str, Any]:
    """The stated replicating portfolio of an NMD category: the two adjacent tranches whose weighted average maturity (the engine's
    ``weighted_average_maturity``, half the weighted tranche maturity) is the requested core maturity. Synthetic: the bank has no deposit-rate
    history to estimate it from, so there is no margin volatility."""
    target = 2.0 * maturity
    mats = np.array(TRANCHES)
    hi = int(np.searchsorted(mats, target, side="left"))
    hi = min(max(hi, 1), mats.size - 1)
    lo = hi - 1
    w = np.zeros(mats.size)
    w[hi] = (target - mats[lo]) / (mats[hi] - mats[lo])
    w[lo] = 1.0 - w[hi]
    wam = float(rv_behavioural.weighted_average_maturity(mats, w))
    if abs(wam - maturity) > 1e-9:
        raise BookError(f"the stated replicating portfolio gives {wam} years, not {maturity}")
    return {"maturities": [float(x) for x in mats], "weights": [float(x) for x in w], "weighted_average_maturity_years": wam}


def _slot(amount: float, sign: float, times: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return rv_slotting.slot_cash_flows(times, sign * amount * weights, GRID)


def build_book(seed: int, spec: VariantSpec, uf_value: float) -> Book:
    """The book of one variant at the UF value of the valuation date (CLP per UF)."""
    p = spec.params
    A = targets.amount("total_assets")
    com, con, mtg = targets.amount("commercial"), targets.amount("consumer"), targets.amount("mortgage")
    sec, ibk, dep, tier1 = targets.amount("securities"), targets.amount("interbank"), targets.amount("deposits"), targets.amount("equity")
    cash = asm.CASH_SHARE_OF_ASSETS * A
    uf = asm.UF_SHARE
    borrowings = cash + ibk + com + con + mtg + sec - dep - tier1
    td = dep * (1.0 - asm.NMD_SHARE_OF_DEPOSITS)
    nmd = dep * asm.NMD_SHARE_OF_DEPOSITS
    uf_assets = com * uf["commercial"] + mtg * uf["mortgage"] + sec * uf["securities"]
    uf_td = td * uf["time_deposits"]
    uf_bonds = uf_assets - uf_td - p["net_uf_share_tier1"] * tier1
    if not (0.0 < uf_bonds < borrowings):
        raise BookError(f"{spec.id}: the UF borrowings would be {uf_bonds:,.0f} of {borrowings:,.0f} CLP million: the stated shares cannot balance the book")
    clp_bonds = borrowings - uf_bonds
    n = 0
    legs = {"CLP": Leg("CLP", "CLP"), "UR": Leg("UR", "CLF")}

    def add(leg: str, item_id: str, en: str, es: str, side: str, category: str, bclass: str, source: str, clp_amount: float, profile: str,
            dyn: dict[str, Any], years_scale: float = 1.0, long_share: float = 0.0) -> None:
        nonlocal n
        if clp_amount <= 0.0:
            return
        rng = np.random.default_rng([seed, 15, n])
        n += 1
        amount = clp_amount / (uf_value if leg == "UR" else 1.0)
        times, weights = _profile(profile, rng, years_scale, long_share)
        sign = 1.0 if side == "asset" else -1.0
        legs[leg].items.append(Item(item_id, t(en, es), side, category, bclass, source, float(amount), _slot(amount, sign, times, weights), dyn))

    syn = "profile and currency split synthetic (assumptions.item_profiles, assumptions.currency_split)"
    cmf = "CMF, Informe del Desempeno del Sistema Bancario y Cooperativas, agosto 2026, Cuadro N 1 (Bancos)"
    lw = p["clp_long_asset_share"]
    fl = p["ur_floating_share"]
    # ---- assets, CLP
    add("CLP", "CLP-CASH", "CLP cash and Central Bank deposits", "Caja y depósitos en el Banco Central en pesos", "asset", "cash", "none",
        f"synthetic: {asm.CASH_SHARE_OF_ASSETS:.0%} of total assets (assumption); overnight", cash, "overnight", {"kind": "floating", "margin": "cash"})
    add("CLP", "CLP-IBK", "CLP loans to banks", "Adeudado por bancos en pesos", "asset", "loans-floating", "none",
        f"{cmf}: Adeudado por Bancos; {syn}", ibk, "one_month", {"kind": "floating", "margin": "interbank"})
    com_clp = com * (1.0 - uf["commercial"])
    add("CLP", "CLP-COM-F", "CLP commercial loans, floating", "Créditos comerciales en pesos, tasa variable", "asset", "loans-floating", "none",
        f"{cmf}: Comercial, scaled with the C07 book; {syn}; floating share {asm.COMMERCIAL_FLOATING_SHARE:.0%} synthetic",
        com_clp * asm.COMMERCIAL_FLOATING_SHARE, "reprice_3m", {"kind": "floating", "margin": "commercial_floating"})
    add("CLP", "CLP-COM-X", "CLP commercial loans, fixed", "Créditos comerciales en pesos, tasa fija", "asset", "loans-fixed", "none",
        f"{cmf}: Comercial, scaled with the C07 book; {syn}", com_clp * (1.0 - asm.COMMERCIAL_FLOATING_SHARE), "com_fixed",
        {"kind": "fixed", "margin": "commercial_fixed"}, long_share=lw)
    add("CLP", "CLP-CON", "CLP consumer loans", "Créditos de consumo en pesos", "asset", "loans-fixed", "none",
        f"{cmf}: Consumo, scaled with the C07 book; {syn}", con, "consumer", {"kind": "fixed", "margin": "consumer"})
    add("CLP", "CLP-MTG", "CLP residential mortgages", "Créditos hipotecarios en pesos", "asset", "loans-fixed", "prepayable-loan",
        f"{cmf}: Vivienda, scaled with the C07 book; {syn}", mtg * (1.0 - uf["mortgage"]), "mortgage_clp", {"kind": "fixed", "margin": "mortgage"})
    add("CLP", "CLP-SEC", "CLP debt securities", "Instrumentos de deuda en pesos", "asset", "securities", "none",
        f"{cmf}: Instrumentos financieros de deuda; {syn}", sec * (1.0 - uf["securities"]), "securities_clp",
        {"kind": "fixed", "margin": "securities"}, long_share=lw)
    # ---- assets, UR
    com_uf = com * uf["commercial"]
    add("UR", "UR-COM-F", "UF commercial loans, floating", "Créditos comerciales en UF, tasa variable", "asset", "loans-uf", "none",
        f"{cmf}: Comercial, scaled with the C07 book; {syn}; floating share is a variant parameter", com_uf * fl, "reprice_3m",
        {"kind": "floating", "margin": "commercial_floating"})
    add("UR", "UR-COM", "UF commercial loans", "Créditos comerciales en UF", "asset", "loans-uf", "none",
        f"{cmf}: Comercial, scaled with the C07 book; {syn}", com_uf * (1.0 - fl), "com_uf", {"kind": "fixed", "margin": "commercial_fixed"})
    add("UR", "UR-MTG", "UF residential mortgages", "Créditos hipotecarios en UF", "asset", "loans-uf", "prepayable-loan",
        f"{cmf}: Vivienda, scaled with the C07 book; {syn}", mtg * uf["mortgage"], "mortgage_uf", {"kind": "fixed", "margin": "mortgage"})
    add("UR", "UR-SEC", "UF debt securities", "Instrumentos de deuda en UF", "asset", "securities", "none",
        f"{cmf}: Instrumentos financieros de deuda; {syn}", sec * uf["securities"], "securities_uf", {"kind": "fixed", "margin": "securities"})
    # ---- liabilities, CLP: the non-maturity deposits are split and slotted by the engine below
    segments: list[dict[str, Any]] = []
    for cat, share in asm.NMD_SEGMENT_SHARE.items():
        balance = nmd * share
        req = asm.REQUESTS[cat]
        s = rv_slotting.nmd_split(balance, cat, req.share, req.maturity, enforce_caps=True, grid=GRID)
        code = {"retail-operational": "RO", "retail-non-operational": "RN", "wholesale": "W"}[cat]
        legs["CLP"].items.append(Item(
            f"CLP-NMD-{code}", t(f"CLP non-maturity deposits, {cat}", f"Depósitos a la vista en pesos, {cat}"), "liability", "deposits-nmd",
            asm.CATEGORY_CLASS[cat], f"{cmf}: Depósitos totales, split synthetic (assumptions.deposit_split); core share and maturity requested "
            "synthetic, capped by SRP31 Table 4", float(balance), -np.asarray(s.flows, dtype=float), {"kind": "nmd", "margin": None}))
        segments.append({"category": cat, "balance": float(balance), "requested_core_share": float(s.requested_core_share),
                         "core_share_cap": float(s.core_share_cap), "core_share_used": float(s.core_share_used),
                         "requested_core_maturity_years": float(s.requested_core_maturity_years),
                         "core_maturity_cap_years": float(s.core_maturity_cap_years), "core_maturity_used_years": float(s.core_maturity_used_years),
                         "cap_applied": bool(s.cap_applied), "source_kind": "synthetic-stated",
                         "source": "request stated by Contraste (synthetic); the used value is min(request, SRP31 Table 4 cap)"})
    add("CLP", "CLP-TD", "CLP term deposits", "Depósitos a plazo en pesos", "liability", "deposits-time", "term-deposit",
        f"{cmf}: Depósitos totales, split synthetic (assumptions.deposit_split); {syn}", td * (1.0 - uf["time_deposits"]), "td_clp",
        {"kind": "time", "margin": "time_deposit"})
    add("CLP", "CLP-BND", "CLP bonds and other borrowings", "Bonos y otros financiamientos en pesos", "liability", "borrowings", "none",
        f"synthetic: the balancing item of the book (assets less deposits less Tier 1 proxy), {syn}", clp_bonds, "bond_clp",
        {"kind": "fixed", "margin": "bond"}, years_scale=p["clp_bond_years_scale"])
    # ---- liabilities, UR
    add("UR", "UR-TD", "UF term deposits", "Depósitos a plazo en UF", "liability", "deposits-time", "term-deposit",
        f"{cmf}: Depósitos totales, split synthetic (assumptions.deposit_split); {syn}", uf_td, "td_uf", {"kind": "time", "margin": "time_deposit"})
    add("UR", "UR-BND", "UF bonds", "Bonos en UF", "liability", "borrowings", "none",
        f"synthetic: the UF borrowings solved so that the net UF position is the variant's share of Tier 1, {syn}", uf_bonds, "bond_uf",
        {"kind": "fixed", "margin": "bond"})
    agg = {"total_assets": A, "cash": cash, "loans": com + con + mtg, "securities": sec, "deposits": dep, "borrowings": borrowings}
    replicating = {cat: replicating_portfolio(asm.REQUESTS[cat].maturity) for cat in asm.REQUESTS}
    return Book(seed, spec, uf_value, legs, segments, float(tier1), agg, replicating)
