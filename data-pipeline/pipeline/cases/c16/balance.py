"""The call-report mapping of C16: the FDIC items of one report mapped to the balance sheet, the deposit segments, the securities by
type, the LCR balances and the contractual ladder, every assumption stated as synthetic behaviour on real aggregates.

The product reads and maps; it computes no liquidity quantity. A mapping here is an assignment of a reported item to a category or a
spreading of a reported band over days, never a run-off, a haircut, a ratio or a survival period: those are ``riskvalidation`` calls
in ``variant``. A field the report lacks is a derived amount with its reason or a refusal naming it, never a number from elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...io.fdic import MissingField, Report
from .assumptions import txt

SECURITY_TYPES = ("treasury", "mortgage-backed", "other-agency", "municipal", "other-debt")
#: the FDIC fields that carry each securities class at its carrying value (addendum L3.2)
CLASS_FIELDS = {"cash-and-balances": ("CHBAL",), "treasury": ("SCUST",), "mortgage-backed": ("SCMTGBK",), "other-agency": ("SCASPNSUM",),
                "municipal": ("SCMUNI",), "other-debt": ("SCDOMO", "SCFORD")}
CLASS_LABELS = {
    "cash-and-balances": txt("Cash and balances due", "Efectivo y saldos"), "treasury": txt("Treasury securities", "Valores del Tesoro"),
    "mortgage-backed": txt("Mortgage-backed securities", "Valores respaldados por hipotecas"),
    "other-agency": txt("Other agency securities", "Otros valores de agencias"),
    "municipal": txt("Municipal securities", "Valores municipales"), "other-debt": txt("Other debt securities", "Otros valores de deuda")}
#: the HQLA level each class takes in the Basel formula (a convention, stated as an assumption of the document): Treasuries and
#: reserves are Level 1, agency and agency mortgage-backed securities Level 2A (the Level 1 part, GNMA, is not split by the report),
#: municipal and other debt securities are not HQLA under the Basel text
HQLA_LEVEL = {"cash-and-balances": "level_1", "treasury": "level_1", "mortgage-backed": "level_2a", "other-agency": "level_2a",
              "municipal": None, "other-debt": None}
#: the maturity bands of the report in days (lower, upper), the upper edge None when open
BAND_DAYS = {"3m_or_less": (0, 90), "3_12m": (90, 365), "1_3y": (365, 1095), "3_5y": (1095, 1825), "5_15y": (1825, 5475), "over_15y": (5475, None)}
#: the midpoint in years a band takes for the revaluation of the HTM book (the open band 'over 15 years' is taken at 20, a convention)
BAND_MIDPOINT_YEARS = {"3m_or_less": 0.125, "3_12m": 0.625, "1_3y": 2.0, "3_5y": 4.0, "5_15y": 10.0, "over_15y": 20.0}
FHLB_30D_SHARE = 30.0 / 365.0      # of the advances of one year or less, spread uniformly over the year (a convention)
LOAN_30D_SHARE = 30.0 / 90.0       # of the loans of three months or less, spread uniformly over the three months (a convention)


def opt(r: Report, name: str) -> float | None:
    v = r.values.get(name)
    return None if v is None else float(v)


def foreign_deposits(r: Report) -> tuple[float, float | None, bool]:
    """DEPFOR as reported, or DEP minus DEPDOM when the report lacks it: ``(amount, reported, derived)``."""
    rep = opt(r, "DEPFOR")
    if rep is not None:
        return rep, rep, False
    return r.get("DEP") - r.get("DEPDOM"), None, True


def deposits_block(r: Report) -> dict[str, Any]:
    """The deposit fields with both denominators stated: DEPUNA and DEPINS cover the domestic offices (matching denominator DEPDOM),
    DEP includes the foreign offices (A5); DEPSMAMT and DEPLGAMT are on the 250,000 USD threshold."""
    dep, depdom, depuna, depins = r.get("DEP"), r.get("DEPDOM"), r.get("DEPUNA"), r.get("DEPINS")
    return {"dep": dep, "depdom": depdom, "depuna": depuna, "depins": depins, "depsmamt": r.get("DEPSMAMT"), "deplgamt": r.get("DEPLGAMT"),
            "denominators": {"insured_uninsured": "DEPDOM", "total": "DEP"},
            "uninsured_share_of_dep": depuna / dep, "uninsured_share_of_depdom": depuna / depdom,
            "size_threshold": {"value": 250000, "unit": "USD",
                               "source": "FDIC BankFind definitions (addendum L3.1): the 250,000 USD threshold applies at 2022-12-31"}}


def deposit_segments(r: Report) -> list[dict[str, Any]]:
    """The three segments the ladder runs under the central mapping: insured deposits as other retail, uninsured deposits as
    non-operational non-financial corporates, foreign-office deposits as non-operational other financial customers."""
    fo, _, _ = foreign_deposits(r)
    return [
        {"segment": "retail-insured", "list_class": "other-retail", "opening": r.get("DEPINS"), "field": "DEPINS"},
        {"segment": "non-operational-corporate", "list_class": "non-operational-non-financial-corporates", "opening": r.get("DEPUNA"),
         "field": "DEPUNA"},
        {"segment": "financial", "list_class": "non-operational-other-financial", "opening": fo, "field": "DEPFOR"}]


def fair_value_factor(r: Report) -> float:
    """The held-to-maturity loss applied to the whole securities book, pro rata: (SCHF + SCAF) over (SCHA + SCAF). A stated
    assumption (A3): the FDIC reports the loss for the totals, never by type."""
    return (r.get("SCHF") + r.get("SCAF")) / (r.get("SCHA") + r.get("SCAF"))


@dataclass(frozen=True)
class SecurityClass:
    class_id: str
    label: dict[str, str]
    source_fields: tuple[str, ...]
    carrying: float
    fair_value: float | None
    encumbered: float


def securities_classes(r: Report) -> list[SecurityClass]:
    """Cash and the securities by type at the carrying values the FDIC reports; the pledged securities (SCPLEDGE) are encumbered pro
    rata across the types and leave the CBC; the fair value is the carrying value with the whole-book loss factor (A3)."""
    share = r.get("SCPLEDGE") / r.get("SC")
    factor = fair_value_factor(r)
    out = []
    for cid, fields in CLASS_FIELDS.items():
        carrying = r.sum(*fields)
        sec = cid in SECURITY_TYPES
        out.append(SecurityClass(cid, CLASS_LABELS[cid], fields, carrying, carrying * factor if sec else None, carrying * share if sec else 0.0))
    return out


def _item(iid: str, en: str, es: str, side: str, cat: str, field: str, reported: float | None, reason: dict | None, assumption: str,
          amount: float, lc: str | None = None, rd: int | None = None, ins: bool | None = None, fv: float | None = None) -> dict[str, Any]:
    return {"item_id": iid, "label": txt(en, es), "side": side, "category": cat, "source_field": field, "reported_amount": reported,
            "reason_missing": reason, "assumption": assumption, "amount": float(amount), "liquidity_class": lc, "residual_days": rd,
            "insured": ins, "fair_value": fv}


def balance_sheet(r: Report) -> dict[str, Any]:
    """The balance sheet at the report date with its source items and its assumptions. The items reconcile to the reported total
    assets on both sides; an item the report does not carry has a reason and no reported amount."""
    asset = r.get("ASSET")
    cash, scha, schf, scaf, net_loans = r.get("CHBAL"), r.get("SCHA"), r.get("SCHF"), r.get("SCAF"), r.get("LNLSNET")
    depins, depuna, eq = r.get("DEPINS"), r.get("DEPUNA"), r.get("EQ")
    frepo, frepp, fhlb = opt(r, "FREPO"), opt(r, "FREPP"), opt(r, "OTHBFHLB")
    fo, fo_reported, fo_derived = foreign_deposits(r)
    other_assets = asset - (cash + (frepo or 0.0) + scha + scaf + net_loans)
    other_liab = asset - (depins + depuna + fo) - (frepp or 0.0) - (fhlb or 0.0) - eq
    if other_assets < 0 or other_liab < 0:
        raise ValueError(f"{r.report_date}: the reported items exceed the total ({other_assets=}, {other_liab=})")
    zero = "not reported by the FDIC for this date: taken as zero, an assumption (the residual item absorbs the difference)"

    def missing(what: str) -> dict:
        return txt(f"{what} is not in the FDIC financials for this report: taken as zero.", f"{what} no esta en los estados FDIC de este reporte: se toma como cero.")

    items = [
        _item("cash", "Cash and balances due from depository institutions", "Efectivo y saldos en instituciones", "asset", "cash", "CHBAL",
              cash, None, "Reported by the FDIC financials, taken as reserves at nominal value (Level 1).", cash, "level_1", 0, None, cash),
        _item("reverse-repo", "Federal funds sold and reverse repurchase agreements", "Fondos federales vendidos y repos inversos", "asset",
              "reverse-repo", "FREPO", frepo, None if frepo is not None else missing("FREPO"),
              "Reported; an asset (addendum L3.1); assumed overnight, synthetic behaviour." if frepo is not None else zero,
              frepo or 0.0, "non_hqla", 1, None, frepo or 0.0),
        _item("securities-htm", "Securities held to maturity (amortised cost)", "Valores mantenidos al vencimiento (costo amortizado)", "asset",
              "securities-htm", "SCHA", scha, None, "Reported at amortised cost; fair value from SCHF.", scha, None, None, None, schf),
        _item("securities-afs", "Securities available for sale (fair value)", "Valores disponibles para la venta (valor razonable)", "asset",
              "securities-afs", "SCAF", scaf, None, "Reported at fair value.", scaf, None, None, None, scaf),
        _item("loans", "Net loans and leases", "Prestamos y arrendamientos netos", "asset", "loans", "LNLSNET", net_loans, None,
              "Reported; not counted in the CBC.", net_loans, "non_hqla", None, None, None),
        _item("other-assets", "Other assets", "Otros activos", "asset", "other-assets", "ASSET", None,
              txt("No single FDIC item: derived as ASSET minus the items above.",
                  "No hay una partida FDIC unica: derivada como ASSET menos las partidas anteriores."),
              "Total assets less the listed asset items, synthetic aggregation.", other_assets, "non_hqla", None, None, None),
        _item("deposits-insured", "Estimated insured deposits (domestic offices)", "Depositos asegurados estimados (oficinas domesticas)",
              "liability", "deposits-insured", "DEPINS", depins, None, "Reported; mapped to other retail sight deposits.", depins, None, 0, True, None),
        _item("deposits-uninsured", "Estimated uninsured deposits (domestic offices)", "Depositos no asegurados estimados (oficinas domesticas)",
              "liability", "deposits-uninsured", "DEPUNA", depuna, None, "Reported estimate; mapped to non-operational non-financial corporates.",
              depuna, None, 0, False, None),
        _item("deposits-foreign", "Foreign-office deposits", "Depositos en oficinas extranjeras", "liability", "deposits-foreign-office", "DEPFOR",
              fo_reported, txt("DEPFOR is not in the FDIC financials for this report: derived as DEP minus DEPDOM.",
                               "DEPFOR no esta en los estados FDIC de este reporte: derivado como DEP menos DEPDOM.") if fo_derived else None,
              "Foreign-office deposits mapped to non-operational other financial customers, synthetic behaviour.", fo, None, 0, None, None),
        _item("repo-borrowings", "Federal funds purchased and repurchase agreements", "Fondos federales comprados y repos", "liability",
              "repo-borrowings", "FREPP", frepp, None if frepp is not None else missing("FREPP"),
              "Reported; a liability (addendum L3.1)." if frepp is not None else zero, frepp or 0.0, None, 1, None, None),
        _item("fhlb", "FHLB advances", "Anticipos FHLB", "liability", "fhlb-advances", "OTHBFHLB", fhlb, None if fhlb is not None else missing("OTHBFHLB"),
              "Reported; its maturity bands feed the ladder." if fhlb is not None else zero, fhlb or 0.0, None, None, None, None),
        _item("other-liabilities", "Other liabilities", "Otros pasivos", "liability", "other-liabilities", "LIAB", None,
              txt("No single FDIC item: derived as ASSET minus the deposit items, repos, FHLB advances and equity.",
                  "Derivada como ASSET menos las partidas de depositos, repos, anticipos FHLB y patrimonio."),
              "Residual liabilities, synthetic aggregation.", other_liab, None, None, None, None),
        _item("equity", "Total equity capital", "Capital patrimonial total", "liability", "equity", "EQ", eq, None, "Reported.", eq, None, None, None, None),
    ]

    def a(aid: str, applies: str, en: str, es: str) -> dict:
        return {"assumption_id": aid, "behaviour": "synthetic", "applies_to": applies, "statement": txt(en, es)}

    return {
        "as_of": r.report_date, "items": items, "total_assets": asset, "deposits": deposits_block(r),
        "assumptions": [
            a("deposit-mapping", "deposits", "Deposits are mapped to LiST classes by the named mapping table of the conventions: insured to other retail, "
              "uninsured to non-operational non-financial corporates, foreign offices to non-operational other financial.",
              "Los depositos se mapean a clases LiST por la tabla de mapeo nombrada de las convenciones."),
            a("pledged-pro-rata", "securities", "Pledged securities (SCPLEDGE) are encumbered pro rata across the securities types and leave the CBC.",
              "Los valores pignorados (SCPLEDGE) se gravan a prorrata entre los tipos y salen del CBC."),
            a("no-committed-lines", "off-balance-sheet", "The FDIC financials read give no undrawn commitments: no drawdown and no collateral call is "
              "modelled (a scenario input of zero, labelled).",
              "Los estados FDIC leidos no dan compromisos no girados: no se modela giro ni llamada de colateral."),
            a("no-contractual-deposits", "deposits", "Every deposit runs on the open-maturity rate of its class: the term deposits (NTRTIME) are not run on the "
              "contractual roll-off of the LiST note, because the report gives no residual maturity of the uninsured balance.",
              "Todo deposito corre a la tasa de vencimiento abierto de su clase; los depositos a plazo no corren con el roll-off contractual."),
            a("lcr-hqla-levels", "lcr", "HQLA levels: reserves and Treasuries Level 1; agency and agency mortgage-backed securities Level 2A (the Level 1 part, "
              "GNMA, is not split by the report); municipal and other debt securities not HQLA. Securities enter at fair value (the whole-book loss), "
              "unencumbered.",
              "Niveles HQLA: reservas y bonos del Tesoro nivel 1; agencias y MBS de agencias nivel 2A; municipales y otra deuda no HQLA."),
            a("lcr-flows", "lcr", "Reverse repos are secured lending maturing in 30 days at 100 percent; loans of three months or less mature uniformly "
              "(a third of them in 30 days) at the 50 percent rate of retail and non-financial wholesale inflows (repricing is read as maturity: an "
              "upper bound); FHLB advances of one year or less mature uniformly (30 over 365 of them in 30 days) as other secured funding at 100 percent.",
              "Los repos inversos vencen a 30 dias al 100 por ciento; los prestamos a tres meses o menos vencen uniformemente."),
        ],
    }


def spread(amount: float, lo: int, hi: int | None, edges: list[int]) -> list[float]:
    """The amount of a band ``(lo, hi]`` days spread uniformly over the contractual buckets ``(0, e1], (e1, e2], ... (e_n, inf)``; an
    open band lies in the last bucket (the slotting assumption of the contractual ladder)."""
    upper = [*edges, None]
    lower = [0, *edges]
    out = []
    for lo_b, hi_b in zip(lower, upper):
        if hi is None:
            out.append(amount if lo >= lower[-1] else 0.0)
            continue
        top = hi if hi_b is None else min(hi, hi_b)
        out.append(amount * max(0.0, top - max(lo, lo_b)) / (hi - lo))
    return out


def contractual_flows(r: Report, edges: list[int]) -> tuple[list[float], list[float]]:
    """The contractual inflows and outflows by bucket from the reported maturity bands (each band spread uniformly over the days it
    covers; non-maturity deposits and overnight items in the first bucket). Items without a contractual maturity (equity, other
    liabilities and assets) are left out."""
    n = len(edges) + 1
    inn, out = [0.0] * n, [0.0] * n

    def add(into: list[float], parts: list[float]) -> None:
        for k, v in enumerate(parts):
            into[k] += v

    add(inn, spread(r.get("CHBAL") + (opt(r, "FREPO") or 0.0), 0, 1, edges))
    for prefix in ("SCNM", "SCPT"):
        for band, suffix in (("3m_or_less", "3LES"), ("3_12m", "3T12"), ("1_3y", "1T3"), ("3_5y", "3T5"), ("5_15y", "5T15"), ("over_15y", "OV15")):
            lo, hi = BAND_DAYS[band]
            add(inn, spread(r.get(prefix + suffix), lo, hi, edges))
    add(inn, spread(r.get("SCO3YLES"), 0, 1095, edges))
    add(inn, spread(r.get("SCOOV3Y"), 1095, None, edges))
    for prefix in ("LNRS", "LNOT"):
        for band, suffix in (("3m_or_less", "3LES"), ("3_12m", "3T12"), ("1_3y", "1T3"), ("3_5y", "3T5"), ("5_15y", "5T15"), ("over_15y", "OV15")):
            lo, hi = BAND_DAYS[band]
            add(inn, spread(r.get(prefix + suffix), lo, hi, edges))
    ntr = r.get("NTRTIME")
    add(out, spread(r.get("DEP") - ntr, 0, 1, edges))
    for fields, lo, hi in ((("CD3LES", "CD3LESS"), 0, 90), (("CD3T12", "CD3T12S"), 90, 365), (("CD1T3", "CD1T3S"), 365, 1095),
                           (("CDOV3", "CDOV3S"), 1095, None)):
        add(out, spread(r.sum(*fields), lo, hi, edges))
    add(out, spread(opt(r, "FREPP") or 0.0, 0, 1, edges))
    for name, lo, hi in (("OTHBFH1L", 0, 365), ("OTBFH1T3", 365, 1095), ("OTBFH3T5", 1095, 1825), ("OTBFHOV5", 1825, None),
                         ("OTBOT1L", 0, 365), ("OTBOT1T3", 365, 1095), ("OTBOT3T5", 1095, 1825), ("OTBOTOV5", 1825, None)):
        add(out, spread(opt(r, name) or 0.0, lo, hi, edges))
    return inn, out


def lcr_balances(r: Report, factor: float) -> dict[str, Any]:
    """The balances the Basel LCR formula takes, under the central mapping, from one report: the HQLA at their level (securities at
    fair value less the encumbered part, before the Basel haircuts), the outflow and inflow balances by category key of the engine's
    tables (``riskvalidation.regulatory.lcr_nsfr``), with the amounts they stand on."""
    sec = {c.class_id: c for c in securities_classes(r)}
    levels: dict[str, float] = {"level_1": 0.0, "level_2a": 0.0, "level_2b": 0.0}
    held: dict[str, float] = {}
    for cid, lvl in HQLA_LEVEL.items():
        c = sec[cid]
        used = c.carrying if c.fair_value is None else c.fair_value
        v = used - c.encumbered
        held[cid] = v
        if lvl is not None:
            levels[lvl] += v
    fo, _, _ = foreign_deposits(r)
    fhlb30 = (opt(r, "OTHBFH1L") or 0.0) * FHLB_30D_SHARE
    loans30 = (r.get("LNRS3LES") + r.get("LNOT3LES")) * LOAN_30D_SHARE
    outflows = {"retail_less_stable": r.get("DEPINS"), "non_financial_corporate": r.get("DEPUNA"), "other_legal_entity": fo,
                "secured_other": (opt(r, "FREPP") or 0.0) + fhlb30}
    inflows = {"secured_lending_other": opt(r, "FREPO") or 0.0, "retail_and_nonfinancial_wholesale": loans30}
    return {"levels": levels, "held": held, "outflows": outflows, "inflows": inflows, "uninsured": r.get("DEPUNA"),
            "foreign": fo, "factor": factor}


def maturity_profile(r: Report) -> list[tuple[float, float]]:
    """The securities maturity profile of the report as ``(midpoint years, amount)`` rows: the non-mortgage and pass-through bands
    and the other mortgage securities (average life of three years or less, over three years); the amounts are the report's."""
    rows: list[tuple[float, float]] = []
    for prefix in ("SCNM", "SCPT"):
        for band, suffix in (("3m_or_less", "3LES"), ("3_12m", "3T12"), ("1_3y", "1T3"), ("3_5y", "3T5"), ("5_15y", "5T15"), ("over_15y", "OV15")):
            rows.append((BAND_MIDPOINT_YEARS[band], r.get(prefix + suffix)))
    rows.append((1.5, r.get("SCO3YLES")))
    rows.append((7.0, r.get("SCOOV3Y")))
    return rows


__all__ = ["MissingField", "SecurityClass", "balance_sheet", "contractual_flows", "deposit_segments", "deposits_block", "fair_value_factor",
           "foreign_deposits", "lcr_balances", "maturity_profile", "securities_classes", "spread"]
