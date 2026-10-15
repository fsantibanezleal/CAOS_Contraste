"""The call report slotted into balance-sheet items with notional repricing cash flows in the 19 buckets.

The product reads the report items and spreads their bands (``bands``); the non-maturity deposits go through the engine's
``nmd_split`` with the SRP31 Table 4 caps. Assets carry positive flows and liabilities negative ones. Each item carries two
flow vectors: ``behavioural`` (the NMD core slotted at the used maturity, prepayable loans with the base CPR) and
``contractual`` (every NMD overnight, no prepayment). Equity is not an item: the EVE is that of assets less liabilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.irrbb import slotting as rv_slotting

from . import assumptions as asm
from .bands import spread
from .fdic import Report

CATEGORIES = (
    "cash", "securities-htm", "securities-afs", "loans-fixed", "loans-floating", "other-assets", "deposits-transactional",
    "deposits-non-transactional", "deposits-time", "borrowings", "other-liabilities",
)
Text = dict[str, str]


def t(en: str, es: str) -> Text:
    return {"en": en, "es": es}


@dataclass
class Item:
    item_id: str
    label: Text
    side: str
    category: str
    behavioural_class: str
    repricing_type: str
    source_field: str
    reported_amount: float | None
    reason_missing: Text | None
    slotting_assumption: str
    amount: float
    behavioural: np.ndarray
    contractual: np.ndarray


def overnight(x: float) -> np.ndarray:
    v = np.zeros(19)
    v[0] = x
    return v


def prepaid_profile(flows: np.ndarray, cpr: float) -> np.ndarray:
    """Expected cash flows when a fixed-rate loan slotted at its repricing bucket may prepay at ``cpr`` a year.

    A loan slotted in bucket k reaches the bucket with survival ``(1 - cpr) ** lower_k``; the mass that prepays earlier falls in the
    buckets it passes (``S(lower_j) - S(upper_j)`` in bucket j < k), the rest in k. The total is preserved (SRP31.121 leaves the
    slotting of the prepayment to the caller)."""
    g = rv_slotting.bucket_grid()
    lower = g.lower
    upper = np.where(np.isinf(g.upper), 1e9, g.upper)
    surv = lambda x: (1.0 - cpr) ** x                                                                   # noqa: E731
    out = np.zeros(19)
    for k in np.flatnonzero(flows):
        passed = surv(lower[:k]) - surv(upper[:k])
        out[:k] += flows[k] * passed
        out[k] += flows[k] * surv(lower[k])
    return out


def retail_share(r: Report) -> float:
    small_time = r.sum("CD3LESS", "CD3T12S", "CD1T3S", "CDOV3S")
    return (r.get("DEPSMAMT") - small_time) / (r.get("DEP") - r.get("NTRTIME"))


def build_items(r: Report, requests: dict[str, asm.Request] = asm.REQUESTS, cpr: float = asm.PREPAYMENT_CPR) -> list[Item]:
    """The balance-sheet items of one call report, in the order A1..A8, L1..L9."""
    items: list[Item] = []
    sc = r.get("SC")
    htm_amount, afs_amount = sc - r.get("SCAF"), r.get("SCAF")
    nonmort = [(r.get("SCNM3LES"), "3m_or_less"), (r.get("SCNM3T12"), "3_12m"), (r.get("SCNM1T3"), "1_3y"), (r.get("SCNM3T5"), "3_5y"),
               (r.get("SCNM5T15"), "5_15y"), (r.get("SCNMOV15"), "over_15y")]
    mort = [(r.get("SCPT3LES"), "3m_or_less"), (r.get("SCPT3T12"), "3_12m"), (r.get("SCPT1T3"), "1_3y"), (r.get("SCPT3T5"), "3_5y"),
            (r.get("SCPT5T15"), "5_15y"), (r.get("SCPTOV15"), "over_15y"),
            (r.get("SCO3YLES"), "mbs_average_life_3y_or_less"), (r.get("SCOOV3Y"), "mbs_average_life_over_3y")]
    debt = sum(a for a, _ in nonmort) + sum(a for a, _ in mort)
    # contractual: bullets at their maturity, mortgage pools amortising; behavioural: the mortgage pools also prepay at the base CPR
    sec_con = (spread(nonmort) + spread(mort, amortising=True)) / debt                    # per unit of debt securities
    sec_beh = (spread(nonmort) + prepaid_profile(spread(mort, amortising=True), cpr)) / debt
    no_flow = "uniform spread of the report bands over the buckets they overlap"
    sec_assumption = ("non-mortgage debt at its maturity band, mortgage-backed securities amortising linearly over their remaining "
                      f"maturity band; behavioural flows prepay the mortgage-backed part at the base CPR of {cpr:g} a year")

    def add(**kw: Any) -> None:
        amount = kw["amount"]
        sign = 1.0 if kw["side"] == "asset" else -1.0
        beh = kw.pop("behavioural", None)
        con = kw.pop("contractual", None)
        if beh is None:
            beh = con
        if con is None:
            con = beh
        for v in (beh, con):
            if not np.isclose(v.sum(), sign * amount, rtol=1e-12, atol=1e-6):
                raise ValueError(f"{kw['item_id']}: the flows sum to {v.sum()}, not {sign * amount}")
        items.append(Item(behavioural=beh, contractual=con, **kw))

    plug_a = t("Derived as total assets less the itemised assets; not a call-report line.",
               "Derivado como activos totales menos los activos detallados; no es una linea del reporte.")
    plug_l = t("Derived as total liabilities less the itemised liabilities; not a call-report line.",
               "Derivado como pasivos totales menos los pasivos detallados; no es una linea del reporte.")
    split = t("The call report has no customer-type split: the item is the reported deposits times the retail share (accounts of "
              "250 000 USD or less), a synthetic mapping.",
              "El reporte no separa depositos por tipo de cliente: la partida es el deposito informado por la proporcion minorista "
              "(cuentas de hasta 250 000 USD), un mapeo sintetico.")
    # ---- assets
    add(item_id="A1", label=t("Cash and balances due from depository institutions", "Efectivo y saldos en instituciones depositarias"),
        side="asset", category="cash", behavioural_class="none", repricing_type="floating", source_field="CHBAL",
        reported_amount=r.get("CHBAL"), reason_missing=None, slotting_assumption="overnight bucket", amount=r.get("CHBAL"),
        contractual=overnight(r.get("CHBAL")))
    add(item_id="A2", label=t("Federal funds sold and reverse repurchase agreements", "Fondos federales vendidos y pactos de retroventa"),
        side="asset", category="cash", behavioural_class="none", repricing_type="floating", source_field="FREPO",
        reported_amount=r.get("FREPO"), reason_missing=None, slotting_assumption="overnight bucket", amount=r.get("FREPO"),
        contractual=overnight(r.get("FREPO")))
    sec_bands = "bands SCNM*, SCPT*, SCO3YLES, SCOOV3Y"
    add(item_id="A3", label=t("Securities held to maturity", "Valores mantenidos al vencimiento"), side="asset",
        category="securities-htm", behavioural_class="none", repricing_type="fixed", source_field=f"SC - SCAF; {sec_bands}",
        reported_amount=htm_amount, reason_missing=None, slotting_assumption=f"{sec_assumption}; split pro rata to the held-to-maturity share",
        amount=htm_amount, contractual=htm_amount * sec_con, behavioural=htm_amount * sec_beh)
    add(item_id="A4", label=t("Securities available for sale", "Valores disponibles para la venta"), side="asset",
        category="securities-afs", behavioural_class="none", repricing_type="fixed", source_field=f"SCAF; {sec_bands}",
        reported_amount=afs_amount, reason_missing=None, slotting_assumption=f"{sec_assumption}; split pro rata to the available-for-sale share",
        amount=afs_amount, contractual=afs_amount * sec_con, behavioural=afs_amount * sec_beh)
    floating = r.sum("LNOT3LES", "LNRS3LES")
    add(item_id="A5", label=t("Loans repricing within three months", "Prestamos con reprecio dentro de tres meses"), side="asset",
        category="loans-floating", behavioural_class="none", repricing_type="floating", source_field="LNOT3LES + LNRS3LES",
        reported_amount=floating, reason_missing=None, slotting_assumption=no_flow, amount=floating,
        contractual=spread([(floating, "3m_or_less")]))
    com = [(r.get("LNOT3T12"), "3_12m"), (r.get("LNOT1T3"), "1_3y"), (r.get("LNOT3T5"), "3_5y"), (r.get("LNOT5T15"), "5_15y"),
           (r.get("LNOTOV15"), "over_15y")]
    add(item_id="A6", label=t("Fixed-rate commercial and other loans", "Prestamos comerciales y otros de tasa fija"), side="asset",
        category="loans-fixed", behavioural_class="none", repricing_type="fixed",
        source_field="LNOT3T12 + LNOT1T3 + LNOT3T5 + LNOT5T15 + LNOTOV15", reported_amount=sum(a for a, _ in com), reason_missing=None,
        slotting_assumption=no_flow, amount=sum(a for a, _ in com), contractual=spread(com))
    res = [(r.get("LNRS3T12"), "3_12m"), (r.get("LNRS1T3"), "1_3y"), (r.get("LNRS3T5"), "3_5y"), (r.get("LNRS5T15"), "5_15y"),
           (r.get("LNRSOV15"), "over_15y")]
    res_c = spread(res, amortising=True)
    add(item_id="A7", label=t("Closed-end residential loans (prepayable)", "Prestamos residenciales a plazo (prepagables)"), side="asset",
        category="loans-fixed", behavioural_class="prepayable-loan", repricing_type="fixed",
        source_field="LNRS3T12 + LNRS1T3 + LNRS3T5 + LNRS5T15 + LNRSOV15", reported_amount=sum(a for a, _ in res), reason_missing=None,
        slotting_assumption=f"amortising linearly over the remaining maturity band; behavioural flows prepay at the base CPR of {cpr:g} a year",
        amount=sum(a for a, _ in res), contractual=res_c, behavioural=prepaid_profile(res_c, cpr))
    others = r.get("ASSET") - sum(i.amount for i in items)
    add(item_id="A8", label=t("Other assets, net of the allowance, and loans without a repricing band",
                              "Otros activos, netos de provision, y prestamos sin banda de reprecio"),
        side="asset", category="other-assets", behavioural_class="none", repricing_type="fixed", source_field="ASSET less the items above",
        reported_amount=None, reason_missing=plug_a, slotting_assumption="not interest-sensitive: overnight bucket at par",
        amount=others, contractual=overnight(others))
    # ---- liabilities
    r_share = retail_share(r)
    nib = r.sum("DEPNIDOM", "DEPNIFOR")
    ib = r.sum("DEPIDOM", "DEPIFOR") - r.get("NTRTIME")

    def nmd(item_id: str, label: Text, cat_class: str, category: str, amount: float, source: str) -> None:
        cat = cat_class.removeprefix("nmd-")
        req = requests[cat]
        sl = rv_slotting.nmd_split(amount, cat, req.share, req.maturity, enforce_caps=True)
        add(item_id=item_id, label=label, side="liability", category=category, behavioural_class=cat_class,
            repricing_type="non-maturity", source_field=source, reported_amount=None, reason_missing=split,
            slotting_assumption="behavioural: non-core overnight, core around the used maturity (nmd_split, SRP31 Table 4 caps); "
                                "contractual: overnight",
            amount=amount, behavioural=-sl.flows, contractual=overnight(-amount))

    nmd("L1", t("Noninterest-bearing deposits, retail", "Depositos sin interes, minoristas"), "nmd-retail-transactional",
        "deposits-transactional", nib * r_share, "(DEPNIDOM + DEPNIFOR) x retail share")
    nmd("L2", t("Noninterest-bearing deposits, wholesale", "Depositos sin interes, mayoristas"), "nmd-wholesale",
        "deposits-transactional", nib * (1 - r_share), "(DEPNIDOM + DEPNIFOR) x (1 - retail share)")
    nmd("L3", t("Interest-bearing non-maturity deposits, retail", "Depositos a la vista con interes, minoristas"),
        "nmd-retail-non-transactional", "deposits-non-transactional", ib * r_share, "(DEPIDOM + DEPIFOR - NTRTIME) x retail share")
    nmd("L4", t("Interest-bearing non-maturity deposits, wholesale", "Depositos a la vista con interes, mayoristas"), "nmd-wholesale",
        "deposits-non-transactional", ib * (1 - r_share), "(DEPIDOM + DEPIFOR - NTRTIME) x (1 - retail share)")
    td = [(r.sum("CD3LES", "CD3LESS"), "3m_or_less"), (r.sum("CD3T12", "CD3T12S"), "3_12m"), (r.sum("CD1T3", "CD1T3S"), "1_3y"),
          (r.sum("CDOV3", "CDOV3S"), "over_3y_time_deposit")]
    td_flows = -spread(td)
    add(item_id="L5", label=t("Time deposits", "Depositos a plazo"), side="liability", category="deposits-time",
        behavioural_class="term-deposit", repricing_type="fixed", source_field="NTRTIME (bands CD3LES, CD3T12, CD1T3, CDOV3 and the small-deposit ones)",
        reported_amount=r.get("NTRTIME"), reason_missing=None, slotting_assumption=no_flow, amount=r.get("NTRTIME"), contractual=td_flows)
    fh = [(r.get("OTHBFH1L"), "up_to_1y"), (r.get("OTBFH1T3"), "1_3y"), (r.get("OTBFH3T5"), "3_5y"), (r.get("OTBFHOV5"), "over_5y_borrowing")]
    add(item_id="L6", label=t("Federal Home Loan Bank advances", "Anticipos del Federal Home Loan Bank"), side="liability",
        category="borrowings", behavioural_class="none", repricing_type="fixed", source_field="OTHBFHLB (bands OTHBFH1L, OTBFH*)",
        reported_amount=r.get("OTHBFHLB"), reason_missing=None, slotting_assumption=no_flow, amount=r.get("OTHBFHLB"), contractual=-spread(fh))
    ob = [(r.get("OTBOT1L"), "up_to_1y"), (r.get("OTBOT1T3"), "1_3y"), (r.get("OTBOT3T5"), "3_5y"), (r.get("OTBOTOV5"), "over_5y_borrowing")]
    other_b = r.get("OTHBRF") - r.get("OTHBFHLB")
    if not np.isclose(sum(a for a, _ in ob), other_b, atol=1e-6) or not np.isclose(sum(a for a, _ in fh), r.get("OTHBFHLB"), atol=1e-6):
        raise ValueError(f"{r.report_date}: the borrowing bands do not add up to the reported borrowings")
    add(item_id="L7", label=t("Other borrowed money", "Otras obligaciones por prestamos"), side="liability", category="borrowings",
        behavioural_class="none", repricing_type="fixed", source_field="OTHBRF - OTHBFHLB (bands OTBOT*)", reported_amount=other_b,
        reason_missing=None, slotting_assumption=no_flow, amount=other_b, contractual=-spread(ob))
    add(item_id="L8", label=t("Federal funds purchased and repurchase agreements", "Fondos federales comprados y pactos de retrocompra"),
        side="liability", category="borrowings", behavioural_class="none", repricing_type="floating", source_field="FREPP",
        reported_amount=r.get("FREPP"), reason_missing=None, slotting_assumption="overnight bucket", amount=r.get("FREPP"),
        contractual=overnight(-r.get("FREPP")))
    other_l = r.get("LIAB") - sum(i.amount for i in items if i.side == "liability")
    add(item_id="L9", label=t("Other liabilities", "Otros pasivos"), side="liability", category="other-liabilities", behavioural_class="none",
        repricing_type="fixed", source_field="LIAB less the items above", reported_amount=None, reason_missing=plug_l,
        slotting_assumption="not interest-sensitive: overnight bucket at par", amount=other_l, contractual=overnight(-other_l))
    return items


def nmd_segments(items: list[Item], requests: dict[str, asm.Request] = asm.REQUESTS) -> list[dict[str, Any]]:
    """The ``nmd_segments`` of a document: per category the balance, the request, the cap, the used value and ``cap_applied``
    (every field from ``nmd_split``)."""
    out = []
    for cat in ("retail-transactional", "retail-non-transactional", "wholesale"):
        bal = sum(i.amount for i in items if i.behavioural_class == f"nmd-{cat}")
        if bal <= 0:
            continue
        req = requests[cat]
        sl = rv_slotting.nmd_split(bal, cat, req.share, req.maturity, enforce_caps=True)
        out.append({
            "category": cat, "balance": bal, "requested_core_share": sl.requested_core_share, "core_share_cap": sl.core_share_cap,
            "core_share_used": sl.core_share_used, "requested_core_maturity_years": sl.requested_core_maturity_years,
            "core_maturity_cap_years": sl.core_maturity_cap_years, "core_maturity_used_years": sl.core_maturity_used_years,
            "cap_applied": bool(sl.cap_applied), "source_kind": "synthetic-stated",
            "source": "Request stated by Contraste (synthetic); the call report carries no behavioural assumption. Used value: the "
                      "SRP31 Table 4 cap when the request exceeds it."})
    return out
