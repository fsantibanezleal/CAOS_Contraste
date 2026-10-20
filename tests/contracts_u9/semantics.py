"""The cross-field checks of the C12 and regulatory-calculators documents, as importable functions (as U10's semantics.py).

JSON Schema cannot hold these: they recompute numbers and compare dates. The C12 bake calls ``check_c12`` on every document it
writes (and ``check_c12_variants`` on the six together), the regulatory parity bake calls ``check_regulatory`` (a non-empty list is
a refusal to publish); the producer tests run them over every committed document. The formulas are written from dossier 01 (E.1,
E.2, D.2, D.3, C), the addendum (R1, R2, R5, R7, R9), dossier 05 C.1 and C.2 and the BIS CRE99 page (CRE99.20 to CRE99.97).

Each function returns a list of messages, empty when the document conforms. A checker never raises on a schema-invalid document:
it returns one message naming the failure (the bake may run the schema first, but the checker is safe alone).
"""
from __future__ import annotations

import datetime as dt
import math
from statistics import NormalDist
from typing import Callable

REL = 1e-6
PHI = NormalDist().cdf
PHI_INV = NormalDist().inv_cdf


def close(a: float, b: float, rel: float = REL, abs_: float = 1e-9) -> bool:
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


def guarded(fn: Callable[[dict], list[str]]) -> Callable[[dict], list[str]]:
    """A checker returns a message, never an exception, on a document it cannot read (the schema refuses it first)."""
    def run(doc: dict) -> list[str]:
        try:
            return fn(doc)
        except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError, AttributeError, StopIteration) as e:
            return [f"{fn.__name__}: the document cannot be read ({type(e).__name__}: {e}); validate it against its schema first"]
    run.__name__ = fn.__name__
    run.__doc__ = fn.__doc__
    return run


# ------------------------------------------------------------------------------------------------ tables, typed here once

GIRR_TENORS = [0.25, 0.5, 1, 2, 3, 5, 10, 15, 20, 30]  # MAR21.8, MAR21.42 Table 1
GIRR_RW = [0.017, 0.017, 0.016, 0.013, 0.012, 0.011, 0.011, 0.011, 0.011, 0.011]  # MAR21.42 Table 1
#: MAR21.46 Table 2, percent, rows and columns in the order of GIRR_TENORS (addendum R7)
GIRR_CORR = [
    [100.0, 97.0, 91.4, 81.1, 71.9, 56.6, 40.0, 40.0, 40.0, 40.0],
    [97.0, 100.0, 97.0, 91.4, 86.1, 76.3, 56.6, 41.9, 40.0, 40.0],
    [91.4, 97.0, 100.0, 97.0, 94.2, 88.7, 76.3, 65.7, 56.6, 41.9],
    [81.1, 91.4, 97.0, 100.0, 98.5, 95.6, 88.7, 82.3, 76.3, 65.7],
    [71.9, 86.1, 94.2, 98.5, 100.0, 98.0, 93.2, 88.7, 84.4, 76.3],
    [56.6, 76.3, 88.7, 95.6, 98.0, 100.0, 97.0, 94.2, 91.4, 86.1],
    [40.0, 56.6, 76.3, 88.7, 93.2, 97.0, 100.0, 98.5, 97.0, 94.2],
    [40.0, 41.9, 65.7, 82.3, 88.7, 94.2, 98.5, 100.0, 99.0, 97.0],
    [40.0, 40.0, 56.6, 76.3, 84.4, 91.4, 97.0, 99.0, 100.0, 98.5],
    [40.0, 40.0, 41.9, 65.7, 76.3, 86.1, 94.2, 97.0, 98.5, 100.0],
]
SQRT2 = math.sqrt(2.0)
#: MAR50.16 Table 1 (dossier 01 E.1): sector -> (investment grade, high yield or not rated), decimals
BA_CVA_RW = {
    "sovereigns-central-banks-mdbs": (0.005, 0.02), "local-government-public": (0.01, 0.04), "financials": (0.05, 0.12),
    "basic-materials-energy-industrials": (0.03, 0.07), "consumer-transport-administrative": (0.03, 0.085),
    "technology-telecoms": (0.02, 0.055), "health-care-utilities-professional": (0.015, 0.05), "other": (0.05, 0.12),
}
#: CRE52.72 Table 2 (dossier 01 E.2): key -> (supervisory factor, correlation or None, option volatility)
CRE52_72 = {
    "interest-rate": (0.005, None, 0.5), "fx": (0.04, None, 0.15),
    "credit-single-name-AAA": (0.0038, 0.5, 1.0), "credit-single-name-AA": (0.0038, 0.5, 1.0),
    "credit-single-name-A": (0.0042, 0.5, 1.0), "credit-single-name-BBB": (0.0054, 0.5, 1.0),
    "credit-single-name-BB": (0.0106, 0.5, 1.0), "credit-single-name-B": (0.016, 0.5, 1.0),
    "credit-single-name-CCC": (0.06, 0.5, 1.0), "credit-index-IG": (0.0038, 0.8, 0.8), "credit-index-SG": (0.0106, 0.8, 0.8),
    "equity-single-name": (0.32, 0.5, 1.2), "equity-index": (0.20, 0.8, 0.75),
    "commodity-electricity": (0.40, 0.4, 1.5), "commodity-oil-gas-metals-agricultural-other": (0.18, 0.4, 0.7),
}
#: MAR33.4 Table 1 and the rows of MAR33.12 Table 2 that dossier 01 D.3 transcribes (the row "commodity volatility 60 or 120"
#: is ambiguous in the dossier and is not transcribed), liquidity horizons in days
MAR33_4 = {"j1": 10, "j2": 20, "j3": 40, "j4": 60, "j5": 120}
MAR33_12 = {
    "interest-rate-specified-currencies": 10, "interest-rate-other": 20, "interest-rate-volatility": 60,
    "credit-spread-sovereign-investment-grade": 20, "credit-spread-sovereign-high-yield": 40,
    "credit-spread-corporate-investment-grade": 40, "credit-spread-corporate-high-yield": 60, "credit-spread-volatility": 120,
    "equity-large-cap": 10, "equity-small-cap": 20, "equity-large-cap-volatility": 20, "equity-small-cap-volatility": 60,
    "fx-specified-pairs": 10, "fx-other-pairs": 20, "fx-volatility": 40, "commodity-energy-and-carbon": 20,
    "commodity-precious-and-non-ferrous-metals": 20, "commodity-other": 60,
}
#: RBC90.1 Table 1 (dossier 01 C.1): year -> floor factor
PHASE_IN = {2023: 0.50, 2024: 0.55, 2025: 0.60, 2026: 0.65, 2027: 0.70, 2028: 0.725}
#: the chapters of the regulatory document and the in-force date of the version each is read at (dossier 01 C, C.1, D, E)
IN_FORCE = {"CRE20": "2023-01-01", "CRE52": "2023-01-01", "CRE53": "2023-01-01", "CRE99": "2023-01-01", "MAR21": "2023-01-01",
            "MAR33": "2023-01-01", "MAR50": "2023-01-01", "RBC20": "2023-01-01", "RBC90": "2023-01-01"}


# CRE20 (dossier 01 C): the lookup the grid of the document is checked against, keyed as the engine's `standardised.lookup`
_RATINGS = ["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to B-", "below B-", "unrated"]
_CORP = ["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to BB-", "below BB-", "unrated"]
_LTV_RES = [(0.5, 0.2, 0.3), (0.6, 0.25, 0.35), (0.8, 0.3, 0.45), (0.9, 0.4, 0.6), (1.0, 0.5, 0.75), (math.inf, 0.7, 1.05)]
CCF = {"direct-credit-substitute": 1.0, "repo": 1.0, "securities-lending": 1.0, "forward-purchase": 1.0, "nif-ruf": 0.5,
       "transaction-related-contingent": 0.5, "commitment": 0.4, "trade-letter-of-credit": 0.2, "unconditionally-cancellable": 0.1}


def cre20_lookup(exposure_class: str, key: str, short_term: bool = False, cash_flow_dependent: bool = False,
                 counterparty_weight: float | None = None) -> float:
    """The CRE20 risk weight (a decimal) of one cell; raises ValueError for a key outside the table."""
    if exposure_class == "sovereign":
        return dict(zip(_RATINGS, [0.0, 0.2, 0.5, 1.0, 1.5, 1.0]))[key]
    if exposure_class == "eca":
        return {0: 0.0, 1: 0.0, 2: 0.2, 3: 0.5, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.5}[int(key)]
    if exposure_class == "bank-ecra":
        w = dict(zip(_RATINGS[:5], [0.2, 0.2, 0.2, 0.5, 1.5] if short_term else [0.2, 0.3, 0.5, 1.0, 1.5]))
        return w[key]
    if exposure_class == "bank-scra":
        return {"A": (0.4, 0.2), "B": (0.75, 0.5), "C": (1.5, 1.5)}[key][1 if short_term else 0]
    if exposure_class == "corporate":
        w = dict(zip(_CORP, [0.2, 0.5, 0.75, 1.0, 1.5, 1.0]))
        w.update({"investment-grade-unrated": 0.65, "sme-unrated": 0.85, "regulatory-retail-sme": 0.75})
        return w[key]
    if exposure_class == "retail":
        return {"regulatory": 0.75, "transactor": 0.45, "other": 1.0}[key]
    if exposure_class == "equity":
        return {"equity": 2.5, "speculative-unlisted": 4.0, "legislated-programme": 1.0, "subordinated-debt": 1.5}[key]
    if exposure_class == "residential-re":
        ltv = float(key)
        return next(cf if cash_flow_dependent else nc for edge, nc, cf in _LTV_RES if ltv <= edge)
    if exposure_class == "commercial-re":
        ltv = float(key)
        if cash_flow_dependent:
            return 0.7 if ltv <= 0.6 else (0.9 if ltv <= 0.8 else 1.1)
        if counterparty_weight is None:
            raise ValueError("commercial real estate that is not cash-flow dependent needs the counterparty weight")
        return min(0.6, counterparty_weight) if ltv <= 0.6 else counterparty_weight
    if exposure_class == "defaulted":
        return {"provision-below-20pct": 1.5, "provision-at-least-20pct": 1.0, "residential-non-cash-flow-dependent": 1.0}[key]
    if exposure_class == "ccf":
        return CCF[key]
    if exposure_class == "currency-mismatch":
        return {"multiplier": 1.5, "cap": 1.5}[key]
    raise ValueError(f"unknown exposure class {exposure_class!r}")


# ------------------------------------------------------------------------------------------------ formulas


def supervisory_duration(start: float, end: float) -> float:
    """CRE52.34 (dossier 01 E.2)."""
    return (math.exp(-0.05 * start) - math.exp(-0.05 * end)) / 0.05


def maturity_factor(maturity_years: float, mpor_business_days: int | None) -> float:
    """CRE52.48 unmargined and CRE52.52 margined (dossier 01 E.2): 250 business days to the year."""
    if mpor_business_days is None:
        return math.sqrt(min(maturity_years, 1.0) / 1.0)
    return 1.5 * math.sqrt(mpor_business_days / 250.0)


def ir_bucket(end_years: float) -> str:
    """CRE52.57: B1 under one year, B2 one to five years, B3 over five."""
    return "B1" if end_years < 1 else ("B2" if end_years <= 5 else "B3")


def ir_effective_notional(d1: float, d2: float, d3: float, offset: bool = True) -> float:
    """CRE52.57 offset and no-offset formulas (dossier 01 E.2)."""
    if not offset:
        return abs(d1) + abs(d2) + abs(d3)
    return math.sqrt(d1 * d1 + d2 * d2 + d3 * d3 + 1.4 * d1 * d2 + 1.4 * d2 * d3 + 0.6 * d1 * d3)


def entity_aggregate(addons: list[float], rhos: list[float]) -> float:
    """CRE52.61, CRE52.66, CRE52.70 with a correlation per entity: sqrt((sum rho A)^2 + sum (1 - rho^2) A^2)."""
    if len(addons) != len(rhos):
        raise ValueError("one correlation per entity")
    return math.sqrt(sum(r * a for a, r in zip(addons, rhos)) ** 2 + sum((1 - r * r) * a * a for a, r in zip(addons, rhos)))


def multiplier(v_minus_c: float, addon: float) -> float:
    """CRE52.23: floor 5 percent."""
    if addon <= 0:
        return 1.0
    return min(1.0, 0.05 + 0.95 * math.exp(v_minus_c / (2 * 0.95 * addon)))


def rc_unmargined(v: float, c: float) -> float:
    return max(v - c, 0.0)


def rc_margined(v: float, c: float, th: float, mta: float, nica: float) -> float:
    return max(v - c, th + mta - nica, 0.0)


def option_delta(option_type: str, price: float, strike: float, vol: float, expiry: float) -> float:
    """CRE52.38 to CRE52.41: bought call Phi(d1), sold call -Phi(d1), bought put -Phi(-d1), sold put Phi(-d1)."""
    d1 = (math.log(price / strike) + 0.5 * vol * vol * expiry) / (vol * math.sqrt(expiry))
    return {"bought-call": PHI(d1), "sold-call": -PHI(d1), "bought-put": -PHI(-d1), "sold-put": PHI(-d1)}[option_type]


LINEAR_DELTA = {"pay-fixed-receive-floating": 1.0, "pay-floating-receive-fixed": -1.0, "protection-buyer": 1.0,
                "protection-seller": -1.0, "long": 1.0, "short": -1.0}


def ba_cva_df(m: float) -> float:
    return (1 - math.exp(-0.05 * m)) / (0.05 * m)


def scva(rw: float, ead: float, m: float, df: float) -> float:
    """MAR50.15 with alpha 1.4, one netting set per counterparty."""
    return rw * m * ead * df / 1.4


def k_reduced(scvas: list[float], rho: float = 0.5) -> float:
    return math.sqrt((rho * sum(scvas)) ** 2 + (1 - rho * rho) * sum(x * x for x in scvas))


def scenario_rho(rho: float, scenario: str) -> float:
    """MAR21.6: medium prescribed, high min(1.25 rho, 1), low max(2 rho - 1, 0.75 rho)."""
    if scenario == "medium":
        return rho
    if scenario == "high":
        return min(1.25 * rho, 1.0)
    return max(2 * rho - 1.0, 0.75 * rho)


def sbm_bucket(ws: list[float], corr: list[list[float]], scenario: str) -> float:
    """MAR21.4 within-bucket aggregation, K_b = sqrt(max(0, sum WS^2 + sum_{k != l} rho WS WS))."""
    total = 0.0
    for k, a in enumerate(ws):
        for l, b in enumerate(ws):
            total += a * a if k == l else scenario_rho(corr[k][l], scenario) * a * b
    return math.sqrt(max(0.0, total))


def sbm_cross(k_b: list[float], s_b: list[float], gamma: float, scenario: str) -> tuple[float, bool]:
    """MAR21.4 cross-bucket aggregation with the MAR21.4(5)(b) fallback: returns (charge, fallback used)."""
    g = scenario_rho(gamma, scenario)

    def radicand(s: list[float]) -> float:
        return sum(k * k for k in k_b) + sum(g * s[b] * s[c] for b in range(len(k_b)) for c in range(len(k_b)) if b != c)

    rad = radicand(s_b)
    if rad >= 0:
        return math.sqrt(rad), False
    alt = [max(min(s, k), -k) for s, k in zip(s_b, k_b)]
    return math.sqrt(max(radicand(alt), 0.0)), True


def liquidity_cascade(es_t: float, es_by_j: list[float], lhs: list[float], t: float = 10.0) -> float:
    """MAR33.4: sqrt(ES_T(P)^2 + sum_{j >= 2} (ES_T(P, j) sqrt((LH_j - LH_{j-1}) / T))^2); lhs[0] is LH_1."""
    total = es_t ** 2
    for j, es in enumerate(es_by_j, start=2):
        total += (es * math.sqrt((lhs[j - 1] - lhs[j - 2]) / t)) ** 2
    return math.sqrt(total)


def anderson_darling_w2(pits: list[float]) -> float:
    """R5: W^2 = -n - sum (2k - 1) / n [ln F(x_k) + ln(1 - F(x_{n+1-k}))] on the sorted PITs."""
    x = sorted(pits)
    n = len(x)
    return -n - sum((2 * k - 1) / n * (math.log(x[k - 1]) + math.log(1 - x[n - k])) for k in range(1, n + 1))


def effective_ee(ee: list[float]) -> list[float]:
    """CRE53.12 equation 2 (the running maximum of EE)."""
    out, run = [], 0.0
    for v in ee:
        run = max(run, v)
        out.append(run)
    return out


def eepe(grid: list[float], eff: list[float]) -> float:
    """CRE53.13 equation 3: weighted by the time steps over the first year or to maturity."""
    total, prev = 0.0, 0.0
    for t, v in zip(grid, eff):
        if t > 1.0 + 1e-12:
            break
        total += v * (t - prev)
        prev = t
    return total / prev if prev else 0.0


def cva_from(buckets: list[dict], epe_discounted: list[float], lgd: float) -> float:
    return sum(b["pd_counterparty"] * lgd * e for b, e in zip(buckets, epe_discounted))


# ------------------------------------------------------------------------------------------------ the C12 checker


def _sa_ccr_from_book(o: dict, msgs: list[str]) -> None:
    sa = o["sa_ccr"]
    trades = o["book"]["trades"]
    margined = sa["margined"]
    if sorted(t["trade_id"] for t in sa["trades"]) != sorted(t["trade_id"] for t in trades):
        msgs.append("sa_ccr trades are not the book's trades")
    csa = (o["collateral"] or {}).get("csa")
    want_mpor = csa["mpor_business_days"] if csa else None
    if sa["mpor_business_days"] != want_mpor:
        msgs.append(f"sa_ccr: the MPoR {sa['mpor_business_days']} is not the CSA's {want_mpor} (null when uncollateralised)")
    if margined != (csa is not None) or margined != (sa["mpor_business_days"] is not None):
        msgs.append("sa_ccr: margined iff the variant has a CSA and an MPoR is stated")
    if sa["mpor_business_days"] is not None and sa["mpor_business_days"] < 10:
        msgs.append("sa_ccr: the MPoR is below the CRE52.50 floor of 10 business days")
    sets: dict[str, list[float]] = {}
    for t in sa["trades"]:
        bt = next((x for x in trades if x["trade_id"] == t["trade_id"]), None)
        if bt is None:
            continue
        if not close(t["end_years"], bt["maturity_years"]) or not close(t["start_years"], bt["start_years"]):
            msgs.append(f"{t['trade_id']}: end_years or start_years differs from the book")
        if not close(t["notional"]["amount"], bt["notional"]["amount"]):
            msgs.append(f"{t['trade_id']}: the notional differs from the book")
        sd = supervisory_duration(t["start_years"], t["end_years"])
        if not close(t["supervisory_duration"], sd):
            msgs.append(f"{t['trade_id']}: supervisory duration")
        if not close(t["adjusted_notional"]["amount"], bt["notional"]["amount"] * sd):
            msgs.append(f"{t['trade_id']}: adjusted notional")
        if t["delta"] != (1 if bt["side"] == "payer" else -1):
            msgs.append(f"{t['trade_id']}: supervisory delta of a {bt['side']} swap")
        if not close(t["maturity_factor"], maturity_factor(t["end_years"], sa["mpor_business_days"])):
            msgs.append(f"{t['trade_id']}: maturity factor")
        if t["bucket"] != ir_bucket(t["end_years"]):
            msgs.append(f"{t['trade_id']}: maturity bucket")
        if not close(t["effective_notional"], t["adjusted_notional"]["amount"] * t["delta"] * t["maturity_factor"]):
            msgs.append(f"{t['trade_id']}: effective notional")
        sets.setdefault(t["hedging_set"], [0.0, 0.0, 0.0])["B1 B2 B3".split().index(t["bucket"])] += t["effective_notional"]
    if sorted(sets) != sorted(h["hedging_set"] for h in sa["hedging_sets"]):
        msgs.append("sa_ccr: the hedging sets of the trades are not the hedging_sets of the block")
    addon_ir = 0.0
    for hs in sa["hedging_sets"]:
        d = sets.get(hs["hedging_set"], [0.0] * 3)
        if not all(close(a, b) for a, b in zip(d, (hs["d_b1"], hs["d_b2"], hs["d_b3"]))):
            msgs.append(f"{hs['hedging_set']}: bucket effective notionals")
        if not close(hs["effective_notional"], ir_effective_notional(*d, offset=hs["offset"])):
            msgs.append(f"{hs['hedging_set']}: hedging-set effective notional")
        if not close(hs["addon"], 0.005 * hs["effective_notional"]):
            msgs.append(f"{hs['hedging_set']}: add-on is not 0.5 percent of the effective notional")
        addon_ir += hs["addon"]
    ac = sa["addon_by_class"]
    if not close(ac["interest_rate"], addon_ir):
        msgs.append("sa_ccr: interest rate add-on is not the sum of the hedging sets")
    if not close(sa["addon_aggregate"]["amount"], sum(ac.values())):
        msgs.append("sa_ccr: aggregate add-on is not the sum of the five classes")
    v, c = sa["v"]["amount"], sa["c"]["amount"]
    rc = rc_margined(v, c, sa["th"]["amount"], sa["mta"]["amount"], sa["nica"]["amount"]) if margined else rc_unmargined(v, c)
    if not close(sa["rc"]["amount"], rc):
        msgs.append("sa_ccr: RC")
    if not close(sa["multiplier"], multiplier(v - c, sa["addon_aggregate"]["amount"])):
        msgs.append("sa_ccr: multiplier")
    if not close(sa["pfe"]["amount"], sa["multiplier"] * sa["addon_aggregate"]["amount"]):
        msgs.append("sa_ccr: PFE")
    if not close(sa["ead"]["amount"], 1.4 * (sa["rc"]["amount"] + sa["pfe"]["amount"])):
        msgs.append("sa_ccr: EAD")


def _exposure_and_collateral(o: dict, msgs: list[str], grid: list[float]) -> None:
    ex = o["exposure"]
    for name in ("ee", "ee_discounted", "ene", "ene_discounted", "pfe", "effective_ee"):
        if any(v < 0 for v in ex[name]["values"]):
            msgs.append(f"exposure.{name}: a negative value")
    col = o["collateral"]
    if col is not None:
        unc, bal = col["uncollateralised_ee"]["values"], col["collateral_balance"]["values"]
        for k, (e, u, b) in enumerate(zip(ex["ee"]["values"], unc, bal)):
            posted = max(-b, 0.0)
            if e > u + posted + 1e-9:
                msgs.append(f"collateralised EE above the uncollateralised EE plus the collateral posted at point {k}")
        if len(col["uncollateralised_ee"]["values"]) != len(grid):
            msgs.append("collateral: one uncollateralised EE per grid point")
    im = o["initial_margin"]
    if im is not None:
        if any(v < 0 for v in im["dim"]["values"]):
            msgs.append("initial margin: a negative DIM")
        if not close(im["alpha"], PHI_INV(im["quantile"])):
            msgs.append(f"initial margin: alpha {im['alpha']} is not the normal quantile {PHI_INV(im['quantile']):.6f} of {im['quantile']}")
        bd = col["csa"]["mpor_business_days"] if col else None
        if bd is not None and im["mpor_calendar_days"] != round(1.4 * bd):
            msgs.append(f"initial margin: the MPoR is stated in calendar days ({round(1.4 * bd)} for {bd} business days)")
        if any(e > b + 1e-9 for e, b in zip(ex["ee"]["values"], im["ee_vm_only"]["values"])):
            msgs.append("initial margin: the EE with IM is above the VM-only EE")
        for k, (e, b, d) in enumerate(zip(ex["ee"]["values"], im["ee_vm_only"]["values"], im["dim"]["values"])):
            # DIM reduces the exposure path by path (U9 decision B2, ORE): E[max(X - DIM, 0)] is at least max(E[X] - E[DIM], 0)
            # (Jensen) and at most the VM-only EE, so the profile-level identity of earlier versions is an inequality
            if e < max(b - d, 0.0) - 1e-3:
                msgs.append(f"initial margin: the EE is below max(VM-only EE - DIM, 0) at point {k}")
                break


def _girr(o: dict, msgs: list[str]) -> None:
    g = o["girr"]
    if [s["scenario"] for s in g["scenarios"]] != ["low", "medium", "high"]:
        msgs.append("girr: scenarios must be low, medium, high in order")
        return
    s = g["sensitivities"]
    ws = [x * w / SQRT2 for x, w in zip(s, GIRR_RW)]
    if not all(close(a, b, abs_=1e-6) for a, b in zip(ws, g["weighted_sensitivities"])):
        msgs.append("girr: the weighted sensitivities are not RW x s / sqrt(2) with s the change for 1 bp divided by 0.0001 (MAR21.19)")
    corr = [[x / 100 for x in row] for row in GIRR_CORR]
    ks = {name: sbm_bucket(g["weighted_sensitivities"], corr, name) for name in ("low", "medium", "high")}
    for sc in g["scenarios"]:
        if not close(sc["k_b"], ks[sc["scenario"]]):
            msgs.append(f"girr: the bucket charge of the {sc['scenario']} scenario is not the MAR21.4 aggregation of the weighted sensitivities")
    if not close(g["delta_charge"]["amount"], max(sc["k_b"] for sc in g["scenarios"])):
        msgs.append("girr: the charge is not the maximum over the three scenarios")
    if not close(g["delta_charge_undivided"]["amount"], SQRT2 * g["delta_charge"]["amount"]):
        msgs.append("girr: the undivided charge is not sqrt(2) times the divided charge")


def _ore(o: dict, msgs: list[str], grid: list[float]) -> None:
    ore = o["ore_reconciliation"]
    n = len(grid)
    variant = o["variant"]
    if (ore["status"] == "reconciled") == (variant == "wrong-way-risk"):
        msgs.append("ore: every variant but the wrong-way one is reconciled; the wrong-way one is not-applicable (S2)")
    if ore["status"] != "reconciled":
        return
    flags = []
    for a in ore["agreement"]:
        flags.append(a["within_two_se"])
        if a["within_two_se"] != (abs(a["difference"]) <= 2 * a["combined_se"]):
            msgs.append("ore: within_two_se disagrees with the difference")
    if len(ore["agreement"]) != n or len(ore["ore_ee"]["values"]) != n or len(ore["ore_ee_discounted"]["values"]) != n:
        msgs.append("ore: one agreement and one ORE value per grid point")
        return
    for k, a in enumerate(ore["agreement"]):
        if not close(a["difference"], ore["ore_ee"]["values"][k] - o["exposure"]["ee"]["values"][k], abs_=1e-3):
            msgs.append("ore: the EE agreement difference is not ORE minus the Python EE")
            break
    if any(v < 0 for v in ore["ore_ee"]["values"]):
        msgs.append("ore: a negative ORE EE")
    ore_eepe = eepe(grid, effective_ee(ore["ore_ee"]["values"]))
    if not close(ore["ore_eepe"]["amount"], ore_eepe):
        msgs.append("ore_eepe is not the EEPE recomputed from the ORE EE")
    cva = o["cva_dva"]
    ore_cva = cva_from(cva["buckets"], ore["ore_ee_discounted"]["values"], cva["lgd"])
    if not close(ore["ore_cva"]["amount"], ore_cva):
        msgs.append("ore_cva is not the CVA recomputed from the ORE discounted EE")
    for name, py, orev in (("eepe_agreement", o["exposure"]["eepe"]["amount"], ore["ore_eepe"]["amount"]),
                           ("cva_agreement", cva["cva"]["amount"], ore["ore_cva"]["amount"])):
        a = ore[name]
        flags.append(a["within_two_se"])
        if not (close(a["python"], py) and close(a["ore"], orev) and close(a["difference"], orev - py, abs_=1e-6)):
            msgs.append(f"ore: {name} does not state the Python value, the ORE value and their difference")
        if a["within_two_se"] != (abs(a["difference"]) <= 2 * a["combined_se"]):
            msgs.append(f"ore: {name} within_two_se disagrees with the difference")
    if (o["initial_margin"] is None) != (ore["ore_dim"] is None) or (ore["ore_dim"] is None) != (ore["dim_agreement"] is None):
        msgs.append("ore: ore_dim and dim_agreement belong to the initial-margin variant only (B2)")
    elif ore["dim_agreement"] is not None:
        dim = o["initial_margin"]["dim"]["values"]
        if len(ore["dim_agreement"]) != n or len(ore["ore_dim"]["values"]) != n:
            msgs.append("ore: one DIM agreement per grid point")
        else:
            for k, a in enumerate(ore["dim_agreement"]):
                flags.append(a["within_two_se"])
                if not close(a["difference"], ore["ore_dim"]["values"][k] - dim[k], abs_=1e-3):
                    msgs.append("ore_dim: the agreement difference is not ORE minus the Python DIM")
                    break
                if a["within_two_se"] != (abs(a["difference"]) <= 2 * a["combined_se"]):
                    msgs.append("ore: a DIM within_two_se disagrees with the difference")
    if ore["all_within_two_se"] != all(flags):
        msgs.append("ore: all_within_two_se is not the conjunction of every agreement")


@guarded
def check_c12(doc: dict) -> list[str]:
    msgs: list[str] = []
    o = doc["outputs"]
    grid = o["exposure"]["time_grid_years"]
    n = len(grid)
    if grid != sorted(set(grid)):
        msgs.append("time grid not strictly increasing")
    if o["named_parameters"]["time_grid_years"]["value"] != grid:
        msgs.append("the time grid is not the named parameter time_grid_years")
    for name in ("ee", "ee_discounted", "ene", "ene_discounted", "pfe", "effective_ee"):
        pr = o["exposure"][name]
        if len(pr["values"]) != n or len(pr["mc_se"]) != n:
            msgs.append(f"exposure.{name}: values and mc_se must have one entry per grid point")
    _exposure_and_collateral(o, msgs, grid)
    ee = o["exposure"]["ee"]["values"]
    eff = o["exposure"]["effective_ee"]["values"]
    if any(b < a - 1e-9 for a, b in zip(eff, eff[1:])):
        msgs.append("effective EE is not non-decreasing")
    if any(e + 1e-9 < v for e, v in zip(eff, ee)):
        msgs.append("effective EE below EE")
    epe_v = o["exposure"]["eepe"]["amount"]
    if epe_v > max(ee) + 1e-9:
        msgs.append("EEPE above the maximum of EE")
    if not close(epe_v, eepe(grid, eff)):
        msgs.append("EEPE is not the time-weighted average of the effective EE over the first year")
    nb = o["netting_benefit"]
    for k in range(n):
        s = sum(t["ee"]["values"][k] for t in nb["per_trade_ee"])
        if not close(s, nb["sum_of_single_trade_ee"]["values"][k]):
            msgs.append(f"netting_benefit: sum of single-trade EE differs at point {k}")
        if nb["netted_ee"]["values"][k] > s + 1e-9:
            msgs.append(f"netting_benefit: netted EE above the sum of single-trade EE at point {k}")
        if not close(nb["benefit"]["values"][k], s - nb["netted_ee"]["values"][k]):
            msgs.append(f"netting_benefit: benefit is not sum minus netted at point {k}")
    if len(nb["per_trade_ee"]) != len(o["book"]["trades"]):
        msgs.append("netting_benefit has not one profile per trade")
    if o["exposure"]["basis"] == "uncollateralised" and not all(close(a, b) for a, b in zip(ee, nb["netted_ee"]["values"])):
        msgs.append("an uncollateralised EE must equal the netted EE")
    cva = o["cva_dva"]
    pairs = list(zip([0.0] + grid[:-1], grid))
    if [(b["t_start"], b["t_end"]) for b in cva["buckets"]] != pairs:
        msgs.append("cva buckets are not the grid intervals")
    tc = td = 0.0
    for b in cva["buckets"]:
        tc += b["cva_term"]
        td += b["dva_term"]
        if not close(b["cva_term"], b["pd_counterparty"] * cva["lgd"] * b["epe_discounted"]):
            msgs.append("cva term is not PD x LGD x discounted EPE")
        if not close(b["dva_term"], b["pd_bank"] * cva["bank_lgd"] * b["ene_discounted"]):
            msgs.append("dva term is not PD x LGD x discounted ENE")
        if b["t_end"] in grid and not close(b["epe_discounted"], o["exposure"]["ee_discounted"]["values"][grid.index(b["t_end"])]):
            msgs.append("cva bucket EPE is not the discounted EE at the bucket end")
    if not close(tc, cva["cva"]["amount"]):
        msgs.append("CVA is not the sum of its terms")
    if not close(td, cva["dva"]["amount"]):
        msgs.append("DVA is not the sum of its terms")
    if not close(cva["bcva"]["amount"], cva["cva"]["amount"] - cva["dva"]["amount"]):
        msgs.append("BCVA is not CVA minus DVA")
    if all(s["spread"] == 0 for s in cva["buckets"]) and cva["cva"]["amount"] != 0:
        msgs.append("CVA with a zero spread at every bucket must be zero")
    w = o["wrong_way_risk"]
    if w is not None:
        zero = [p for p in w["sweep"] if p["b"] == 0]
        if len(zero) != 1 or not zero[0]["independent"] or any(p["independent"] for p in w["sweep"] if p["b"] != 0):
            msgs.append("wrong-way sweep: the independent point is b = 0 only and exactly once")
        elif zero[0]["cva"]["amount"] != w["independent_cva"]["amount"] or w["independent_cva"]["amount"] != cva["cva"]["amount"]:
            msgs.append("wrong-way risk with b = 0 must equal the independent CVA exactly")
        if [p["b"] for p in w["sweep"]] != w["b_grid"]:
            msgs.append("wrong-way sweep is not the b grid in order")
        if w["b_grid"] != o["named_parameters"]["wwr_b_grid"]["value"]:
            msgs.append("wrong-way b grid is not the named parameter wwr_b_grid")
        if not close(w["largest_b_w"], max(abs(b) for b in w["b_grid"]) * w["w_max_usd_million"]):
            msgs.append("wrong-way: largest_b_w is not the largest |b| times w_max_usd_million")
    _sa_ccr_from_book(o, msgs)
    ba = o["ba_cva"]
    sc = []
    sa = o["sa_ccr"]
    for cp in ba["counterparties"]:
        if not close(cp["discount_factor"], ba_cva_df(cp["m_years"])):
            msgs.append("ba_cva: discount factor")
        rw = BA_CVA_RW[cp["sector"]][0 if cp["rating_class"] == "investment-grade" else 1]
        if cp["risk_weight"] != rw:
            msgs.append(f"ba_cva: the risk weight {cp['risk_weight']} is not MAR50.16 Table 1's {rw} for {cp['sector']}")
        if not close(cp["ead"]["amount"], sa["ead"]["amount"]):
            msgs.append("ba_cva: the EAD is not the SA-CCR EAD of the netting set")
        if not close(cp["scva"], scva(cp["risk_weight"], cp["ead"]["amount"], cp["m_years"], cp["discount_factor"])):
            msgs.append("ba_cva: SCVA")
        sc.append(cp["scva"])
    if not close(ba["k_reduced"], k_reduced(sc)):
        msgs.append("ba_cva: K_reduced")
    if not close(ba["capital"]["amount"], 0.65 * ba["k_reduced"]):
        msgs.append("ba_cva: capital")
    np_ = o["named_parameters"]
    if np_["ba_cva_sector"]["value"] != ba["counterparties"][0]["sector"]:
        msgs.append("ba_cva: the sector is not the named parameter ba_cva_sector")
    rg = o["regulatory_comparison"]
    if not close(rg["alpha_times_eepe"]["amount"], 1.4 * epe_v):
        msgs.append("regulatory: alpha times EEPE")
    if rg["sa_ccr_ead"]["amount"] != sa["ead"]["amount"]:
        msgs.append("regulatory: the SA-CCR EAD differs from the sa_ccr block")
    if not close(rg["sa_ccr_over_alpha_eepe"], sa["ead"]["amount"] / rg["alpha_times_eepe"]["amount"]):
        msgs.append("regulatory: ratio")
    if rg["stressed"]["spread_rose"] != (rg["stressed"]["hqm_spread_peak"] > rg["stressed"]["hqm_spread_start"]):
        msgs.append("regulatory: spread_rose disagrees with the spreads")
    if rg["stressed"]["window_start"] >= rg["stressed"]["window_end"]:
        msgs.append("regulatory: the stress window is not ordered")
    _girr(o, msgs)
    bt = o["backtest"]
    for blk in [bt["book_horizons"], bt["risk_factor"]["horizons"]]:
        for h in blk:
            if h["n"] != len(h["pits"]):
                msgs.append(f"backtest {h['horizon']}: n is not the number of PITs")
            if any(not 0 < p < 1 for p in h["pits"]):
                msgs.append(f"backtest {h['horizon']}: a PIT outside (0, 1)")
                continue
            if not close(h["w2"], anderson_darling_w2(h["pits"])):
                msgs.append(f"backtest {h['horizon']}: W^2 does not recompute from the PITs")
            if h["reject_at_5pct"] != (h["w2"] > h["critical_simulated"]["p05"]):
                msgs.append(f"backtest {h['horizon']}: the decision disagrees with the simulated critical value")
            for e in h["exceedances"]:
                if not close(e["expected"], h["n"] * (1 - e["quantile"])):
                    msgs.append(f"backtest {h['horizon']}: expected exceedances")
    if bt["paths_per_date"] != np_["backtest_paths_per_date"]["value"]:
        msgs.append("backtest: paths_per_date is not the named parameter backtest_paths_per_date")
    cal = o["calibration_used"]
    if not (cal["sample_start"] < cal["sample_end"] < cal["backtest_date"]):
        msgs.append("calibration: the sample window must end before the backtest date (look-ahead)")
    if cal["backtest_date"] != o["curve"]["curve_date"]:
        msgs.append("calibration: backtest_date is not the curve date")
    msgs += _window_msgs(cal)
    cv = o["curve"]
    present = [p["tenor_years"] for p in cv["points"]]
    if present != cv["tenors_present"] or set(present) & set(cv["tenors_absent"]):
        msgs.append("curve: tenors_present must be the points' tenors and disjoint from tenors_absent")
    cs = {s["case"]: s for s in o["calibration_sensitivity"]}
    if sorted(cs) != sorted(["base", "a-plus-1se", "a-minus-1se", "sigma-plus-1se", "sigma-minus-1se"]):
        msgs.append("sensitivity: the five cases")
    elif not (close(cs["a-plus-1se"]["a"], cal["a"] + cal["a_se"]) and close(cs["sigma-minus-1se"]["sigma"], cal["sigma"] - cal["sigma_se"])):
        msgs.append("sensitivity: a and sigma are not moved by one standard error")
    for s in o["calibration_sensitivity"]:
        if len(s["ee"]["values"]) != n or len(s["pfe"]["values"]) != n:
            msgs.append(f"sensitivity {s['case']}: one EE and one PFE value per grid point")
            continue
        if any(v < 0 for v in s["ee"]["values"] + s["pfe"]["values"]):
            msgs.append(f"sensitivity {s['case']}: a negative EE or PFE")
        if not close(s["pfe_peak"]["amount"], max(s["pfe"]["values"])):
            msgs.append(f"sensitivity {s['case']}: pfe_peak is not the maximum of the PFE profile")
        if not close(s["eepe"]["amount"], eepe(grid, effective_ee(s["ee"]["values"]))):
            msgs.append(f"sensitivity {s['case']}: eepe is not recomputed from its EE profile")
    if "base" in cs and not (all(close(a, b) for a, b in zip(cs["base"]["ee"]["values"], ee))
                             and all(close(a, b) for a, b in zip(cs["base"]["pfe"]["values"], o["exposure"]["pfe"]["values"]))):
        msgs.append("sensitivity: the base case is not the document's EE and PFE")
    _ore(o, msgs, grid)
    for t in doc["tests"]:
        if not t["test_id"].startswith("ccr."):
            msgs.append("tests: a C12 test id starts with ccr.")
    return msgs


def _window_msgs(cal: dict) -> list[str]:
    msgs = []
    yrs = (dt.date.fromisoformat(cal["sample_end"]) - dt.date.fromisoformat(cal["sample_start"])).days / 365.25
    if yrs + 0.01 < cal["history_years"] or cal["history_years"] < 3:
        msgs.append("calibration: the sample window spans less than history_years, or history_years is under three years (CRE53.51)")
    if cal["n_obs"] < 12 * cal["history_years"]:
        msgs.append("calibration: n_obs is below one observation per month of history")
    return msgs


@guarded
def check_c12_variants(doc: dict) -> list[str]:
    """The six variant documents together: one time grid, one curve, one calibration, one book and one parameter set (W1 draws
    the variants on one axis). ``doc`` is ``{"documents": [...]}``."""
    docs = doc["documents"]
    msgs: list[str] = []
    if len(docs) < 2:
        return msgs
    first = docs[0]["outputs"]
    for d in docs[1:]:
        o = d["outputs"]
        if o["exposure"]["time_grid_years"] != first["exposure"]["time_grid_years"]:
            msgs.append(f"{d['variant_id']}: the time grid differs from {docs[0]['variant_id']}")
        if o["named_parameters"] != first["named_parameters"]:
            msgs.append(f"{d['variant_id']}: the named parameters differ")
        if o["curve"] != first["curve"] or o["calibration_used"] != first["calibration_used"]:
            msgs.append(f"{d['variant_id']}: the curve or the calibration differs")
        if o["book"]["trades"][0] != first["book"]["trades"][0]:
            msgs.append(f"{d['variant_id']}: the first trade differs")
    return msgs


@guarded
def check_c12_models(doc: dict) -> list[str]:
    msgs: list[str] = []
    cals = doc["fit"]["calibrations"]
    dates = [c["backtest_date"] for c in cals]
    if dates != sorted(set(dates)):
        msgs.append("calibration dates are not unique and increasing")
    for c in cals:
        if not (c["sample_start"] < c["sample_end"] < c["backtest_date"]):
            msgs.append(f"{c['backtest_date']}: the sample window ends on or after the backtest date (look-ahead)")
        msgs += [f"{c['backtest_date']}: {m}" for m in _window_msgs(c)]
    girr = doc["fit"]["girr_parameters"]
    corr, ten = girr["correlation_percent"], girr["tenors_years"]
    for k in range(10):
        for l in range(10):
            want = 100.0 if k == l else max(100 * math.exp(-0.03 * abs(ten[k] - ten[l]) / min(ten[k], ten[l])), 40.0)
            if abs(corr[k][l] - want) > 0.051 or corr[k][l] != corr[l][k]:
                msgs.append(f"girr correlation ({ten[k]}, {ten[l]}) differs from MAR21.46 Table 2")
    return msgs


# ------------------------------------------------------------------------------------------ the regulatory checker


def _terms(trade: dict) -> dict:
    return {v["name"]: v["value"] for v in trade["terms"]}


def sa_ccr_from_trades(trades: list[dict], c: float, mpor: int | None, th: float = 0.0, mta: float = 0.0, nica: float = 0.0) -> dict:
    """The CRE99 path from the trade inputs, intermediates unrounded (CRE99.20 to CRE99.97). ``trades`` are the document's trades."""
    margined = mpor is not None
    v = 0.0
    ir: dict[str, list[float]] = {}
    credit: dict[str, list[float]] = {}  # entity -> [effective notional, sf, rho]
    com: dict[str, dict[str, list[float]]] = {}
    out: dict[str, float] = {}
    for tr in trades:
        t = _terms(tr)
        v += t["market_value"]
        ac = t["asset_class"]
        if ac in ("interest-rate", "credit"):
            sd = max(supervisory_duration(t["start_years"], t["end_years"]), 10 / 250)
            adjusted = t["notional"] * sd
            maturity = t["end_years"]
        else:
            adjusted = t["adjusted_notional"]
            maturity = t["maturity_years"]
        mf = maturity_factor(maturity, mpor)
        if t.get("option_type", "none") != "none":
            delta = option_delta(t["option_type"], t["option_price"], t["option_strike"], t["option_volatility"], t["option_expiry_years"])
            out["swaption_delta"] = delta
        else:
            delta = LINEAR_DELTA[t["position"]]
        en = adjusted * delta * mf
        out["maturity_factor"] = mf
        if ac == "interest-rate":
            ir.setdefault(t["currency"], [0.0, 0.0, 0.0])["B1 B2 B3".split().index(ir_bucket(t["end_years"]))] += en
        elif ac == "credit":
            key = "credit-index-" + t["rating"] if t["reference_kind"] == "index" else "credit-single-name-" + t["rating"]
            sf, rho, _ = CRE52_72[key]
            e = credit.setdefault(t["entity"], [0.0, sf, rho])
            e[0] += en
        else:
            key = "commodity-electricity" if t["commodity_type"] == "electricity" else "commodity-oil-gas-metals-agricultural-other"
            sf, rho, _ = CRE52_72[key]
            com.setdefault(t["hedging_set"], {}).setdefault(t["commodity_type"], [0.0, sf, rho])[0] += en
    addon = 0.0
    if ir:
        a_ir = 0.0
        for ccy, d in ir.items():
            en = ir_effective_notional(*d)
            out[f"en_{ccy.lower()}"] = en
            out[f"addon_{ccy.lower()}"] = 0.005 * en
            a_ir += 0.005 * en
        out["addon_ir"] = a_ir
        addon += a_ir
    if credit:
        adds = [e[0] * e[1] for e in credit.values()]
        rhos = [e[2] for e in credit.values()]
        out["term_1"] = sum(r * a for a, r in zip(adds, rhos)) ** 2
        out["term_2"] = sum((1 - r * r) * a * a for a, r in zip(adds, rhos))
        out["addon_credit"] = entity_aggregate(adds, rhos)
        addon += out["addon_credit"]
    if com:
        a_c = 0.0
        for hs, types in com.items():
            adds = [e[0] * e[1] for e in types.values()]
            a = entity_aggregate(adds, [e[2] for e in types.values()])
            out[f"addon_{hs}"] = a
            a_c += a
        out["addon_commodity"] = a_c
        addon += a_c
    rc = rc_margined(v, c, th, mta, nica) if margined else rc_unmargined(v, c)
    mult = multiplier(v - c, addon)
    out.update({"v": v, "rc": rc, "addon_aggregate": addon, "multiplier": mult, "pfe": mult * addon, "ead": 1.4 * (rc + mult * addon)})
    return out


def _round_to(x: float, rounding: str) -> float:
    if rounding == "nearest integer":
        return float(math.floor(x + 0.5))
    if rounding.endswith("decimal places"):
        d = int(rounding.split()[0])
        return math.floor(x * 10 ** d + 0.5) / 10 ** d
    if rounding == "none":
        return x
    raise ValueError(f"unknown rounding {rounding!r}")


def _chapter(paragraph: str) -> str:
    i = 0
    while i < len(paragraph) and paragraph[i].isalpha():
        i += 1
    j = i
    while j < len(paragraph) and paragraph[j].isdigit():
        j += 1
    return paragraph[:j]


def _matrix(flat: list[float], n: int) -> list[list[float]]:
    return [flat[i * n:(i + 1) * n] for i in range(n)]


def _check_sa_ccr_entry(k: str, e: dict, msgs: list[str]) -> None:
    ins = {v["name"]: v["value"] for v in e["inputs"]}
    outs = {v["name"]: v["value"] for v in e["outputs"]}
    if not e["trades"]:
        msgs.append(f"{k}: an SA-CCR example carries its trades (CRE99.20 to CRE99.97)")
        return
    for tr in e["trades"]:
        t = _terms(tr)
        if t["asset_class"] == "commodity" and t["adjusted_notional"] != t["notional"]:
            msgs.append(f"{k}: {tr['trade_id']}: the adjusted notional is not the notional (the CRE99.64 simplification)")
    got = sa_ccr_from_trades(e["trades"], ins["c"], ins.get("mpor_business_days"), ins.get("th", 0.0), ins.get("mta", 0.0), ins.get("nica", 0.0))
    if "mpor_business_days" in ins and ins["mpor_business_days"] != 9 + ins["margin_frequency_business_days"]:
        msgs.append(f"{k}: the MPoR is 9 business days plus the re-margining period (CRE52.50)")
    if not close(ins["v"], got["v"]):
        msgs.append(f"{k}: V is not the sum of the market values of the trades")
    for name, value in outs.items():
        if name not in got:
            msgs.append(f"{k}: the output {name} is not an SA-CCR quantity the document can recompute")
        elif not close(value, got[name], rel=1e-9, abs_=1e-9):
            msgs.append(f"{k}: {name} recomputes from the trades to {got[name]!r}, the document says {value!r}")
    for need in ("rc", "addon_aggregate", "multiplier", "ead"):
        if need not in outs:
            msgs.append(f"{k}: the output {need} is missing")
    pub = {p["name"]: p for p in e["published"]}
    if "ead" not in pub:
        msgs.append(f"{k}: the published EAD is missing")
        return
    for name, p in pub.items():
        if name not in got:
            msgs.append(f"{k}: the published value {name} is not an SA-CCR quantity")
            continue
        if _round_to(got[name], p["rounding"]) != p["value"]:
            msgs.append(f"{k}: {name} recomputes to {got[name]!r}, which rounds to {_round_to(got[name], p['rounding'])}, published {p['value']}")
    # the path from the printed intermediates keeps the one-unit tolerance (the printed values are rounded)
    if all(n in pub for n in ("rc", "multiplier", "addon_aggregate")):
        path = 1.4 * (pub["rc"]["value"] + pub["multiplier"]["value"] * pub["addon_aggregate"]["value"])
        if abs(path - pub["ead"]["value"]) > 1.0:
            msgs.append(f"{k}: the printed intermediates give an EAD of {path:.3f}, published {pub['ead']['value']}")


@guarded
def check_regulatory(doc: dict) -> list[str]:
    msgs: list[str] = []
    ex = {e["id"]: e for e in doc["official_examples"]}
    iv = {e["id"]: e for e in doc["invariant_cases"]}

    def val(e: dict, group: str, name: str):
        return next(v["value"] for v in e[group] if v["name"] == name)

    for e in doc["official_examples"] + doc["invariant_cases"]:
        want = IN_FORCE.get(_chapter(e["paragraph"]))
        if want is None or e["in_force_date"] != want:
            msgs.append(f"{e['id']}: in-force date {e['in_force_date']} is not {want} for {_chapter(e['paragraph'])}")
        for v in e["inputs"] + e["outputs"] + e["published"]:
            if _chapter(v["paragraph"]) not in IN_FORCE:
                msgs.append(f"{e['id']}: {v['name']} cites a chapter outside the document ({v['paragraph']})")
        for tr in e["trades"]:
            if not tr["paragraph"].startswith("CRE99."):
                msgs.append(f"{e['id']}: trade {tr['trade_id']} does not cite its CRE99 paragraph")

    for i in range(1, 6):
        k = f"cre99-netting-set-{i}"
        if k not in ex:
            msgs.append(f"missing official example {k}")
        else:
            _check_sa_ccr_entry(k, ex[k], msgs)
    if all(f"cre99-netting-set-{i}" in ex for i in (1, 2, 4)):
        o1, o2, o4 = (ex[f"cre99-netting-set-{i}"] for i in (1, 2, 4))
        if not close(val(o4, "outputs", "addon_ir"), val(o1, "outputs", "addon_ir")) or \
                not close(val(o4, "outputs", "addon_credit"), val(o2, "outputs", "addon_credit")):
            msgs.append("cre99-netting-set-4: the add-ons are not those of netting sets 1 and 2")
    if all(f"cre99-netting-set-{i}" in ex for i in (1, 3, 5)):
        s1, s3 = ex["cre99-netting-set-1"], ex["cre99-netting-set-3"]
        if len(ex["cre99-netting-set-5"]["trades"]) != len(s1["trades"]) + len(s3["trades"]):
            msgs.append("cre99-netting-set-5: its trades are not those of netting sets 1 and 3")

    f = ex.get("rbc20-13-output-floor")
    if f:
        want = max(val(f, "inputs", "rwa_nominated"), val(f, "inputs", "floor_factor") * val(f, "inputs", "rwa_sa_only"))
        if not close(val(f, "outputs", "rwa_floored"), want):
            msgs.append("output floor: not max(nominated, f x SA)")
    c = ex.get("rbc20-13-output-floor-capped")
    if c:
        pre = val(c, "inputs", "rwa_nominated")
        want = min(max(pre, val(c, "inputs", "floor_factor") * val(c, "inputs", "rwa_sa_only")), pre * (1 + val(c, "inputs", "cap_share")))
        if not close(val(c, "outputs", "rwa_floored"), want):
            msgs.append("output floor with the RBC90.2 cap")
    for e in doc["official_examples"]:
        for p in e["published"]:
            if e["calculator"] == "output-floor" and not close(p["value"], val(e, "outputs", p["name"])):
                msgs.append(f"{e['id']}: the published {p['name']} differs from the output")

    _check_invariants(iv, msgs)

    ph = {r["year"]: r["factor"] for r in doc["output_floor_phase_in"]}
    if ph != PHASE_IN:
        msgs.append("output_floor_phase_in is not RBC90.1 Table 1 (2023 to 2028)")
    for r in doc["output_floor_phase_in"]:
        if r["effective_from"] != f"{r['year']}-01-01":
            msgs.append(f"output_floor_phase_in {r['year']}: effective_from is not the first of January")
        if r["in_force_date"] != IN_FORCE["RBC90"] or _chapter(r["paragraph"]) != "RBC90":
            msgs.append(f"output_floor_phase_in {r['year']}: paragraph or in-force date")
    _check_tables(doc["parameter_tables"], msgs)

    for g in doc["cre20_grid"]:
        try:
            want = cre20_lookup(g["exposure_class"], g["key"], g["short_term"], g["cash_flow_dependent"], g["counterparty_weight"])
        except (KeyError, ValueError):
            msgs.append(f"cre20 grid: {g['exposure_class']} / {g['key']} is not a cell of the table")
            continue
        if g["risk_weight"] != want:
            msgs.append(f"cre20 grid: {g['exposure_class']} / {g['key']} is {g['risk_weight']}, the table gives {want}")
        if g["in_force_date"] != IN_FORCE.get(_chapter(g["paragraph"])):
            msgs.append(f"cre20 grid: {g['exposure_class']} / {g['key']} in-force date")
    return msgs


def _check_tables(tables: list[dict], msgs: list[str]) -> None:
    want = {
        "cre52-72-table-2": {(k, name): v for k, row in CRE52_72.items() for name, v in zip(("supervisory_factor", "correlation", "option_volatility"), row) if v is not None},
        "mar50-16-table-1": {(k, name): v for k, row in BA_CVA_RW.items() for name, v in zip(("risk_weight_investment_grade", "risk_weight_high_yield_or_not_rated"), row)},
        "mar33-12-table-2": {(k, "liquidity_horizon_days"): v for k, v in MAR33_12.items()},
        "mar33-4-table-1": {(k, "liquidity_horizon_days"): v for k, v in MAR33_4.items()},
    }
    chapters = {"cre52-72-table-2": "CRE52", "mar50-16-table-1": "MAR50", "mar33-12-table-2": "MAR33", "mar33-4-table-1": "MAR33"}
    seen = {t["id"] for t in tables}
    for tid in want:
        if tid not in seen:
            msgs.append(f"parameter table {tid} is missing")
    for t in tables:
        if t["id"] not in want:
            msgs.append(f"parameter table {t['id']} is not one the document may carry")
            continue
        got = {(r["key"], r["parameter"]): r["value"] for r in t["rows"]}
        if got != want[t["id"]] or len(got) != len(t["rows"]):
            msgs.append(f"parameter table {t['id']} differs from the transcribed table")
        if _chapter(t["paragraph"]) != chapters[t["id"]] or t["in_force_date"] != IN_FORCE[chapters[t["id"]]]:
            msgs.append(f"parameter table {t['id']}: paragraph or in-force date")


def _check_invariants(iv: dict, msgs: list[str]) -> None:
    def vals(e: dict, group: str) -> dict:
        return {v["name"]: v["value"] for v in e[group]}

    for e in iv.values():
        if e["holds"] is not True:
            msgs.append(f"{e['id']}: an invariant case must hold")
    b = iv.get("ba-cva-rho-one")
    if b:
        i, o = vals(b, "inputs"), vals(b, "outputs")
        s = [v for k, v in i.items() if k.startswith("scva")]
        if not close(o["k_reduced"], k_reduced(s, i["rho"])) or not close(o["k_reduced"], sum(s)):
            msgs.append("BA-CVA with rho = 1 must give the sum of SCVA")
    h = iv.get("ba-cva-hedges-floor")
    if h:
        i, o = vals(h, "inputs"), vals(h, "outputs")
        if not close(o["k_full"], i["beta"] * i["k_reduced"] + (1 - i["beta"]) * i["k_hedged"]) or o["k_full"] < i["beta"] * i["k_reduced"]:
            msgs.append("BA-CVA K_full is not beta K_reduced + (1 - beta) K_hedged, or is below beta K_reduced")
    s = iv.get("sbm-low-and-high-scenarios")
    if s:
        i, o = vals(s, "inputs"), vals(s, "outputs")
        for name, sc in (("rho_low", "low"), ("rho_medium", "medium"), ("rho_high", "high")):
            if not close(o[name], scenario_rho(i["rho"], sc)):
                msgs.append(f"SBM {name} is not the MAR21.6 transform of rho")
    for case in ("sbm-bucket-and-cross-bucket-aggregation", "sbm-cross-bucket-fallback"):
        e = iv.get(case)
        if not e:
            msgs.append(f"missing invariant case {case}")
            continue
        i, o = vals(e, "inputs"), vals(e, "outputs")
        ws = [i[k] for k in sorted(i) if k.startswith("ws_")]
        rhos = [_matrix(i[f"rho_{b + 1}"], len(w)) for b, w in enumerate(ws)]
        charges = {}
        for sc in ("low", "medium", "high"):
            kb = [sbm_bucket(w, r, sc) for w, r in zip(ws, rhos)]
            cross, fb = sbm_cross(kb, [sum(w) for w in ws], i["gamma"], sc)
            charges[sc] = cross
            for b, k in enumerate(kb):
                if not close(o[f"k_b{b + 1}_{sc}"], k):
                    msgs.append(f"{case}: bucket {b + 1} charge under {sc}")
            if not close(o[f"cross_bucket_{sc}"], cross) or o[f"fallback_{sc}"] != float(fb):
                msgs.append(f"{case}: cross-bucket charge or fallback flag under {sc}")
        if not close(o["sbm_charge"], max(charges.values())):
            msgs.append(f"{case}: the charge is not the maximum over the three scenarios")
    if "sbm-cross-bucket-fallback" in iv:
        o = vals(iv["sbm-cross-bucket-fallback"], "outputs")
        if not (o["fallback_medium"] == 1.0 and o["fallback_low"] == 0.0):
            msgs.append("sbm-cross-bucket-fallback must exercise the fallback and the plain path")
    for case in ("cascade-all-lh-ten", "cascade-two-horizons"):
        e = iv.get(case)
        if not e:
            msgs.append(f"missing invariant case {case}")
            continue
        i, o = vals(e, "inputs"), vals(e, "outputs")
        n = len([k for k in i if k.startswith("lh_")])
        lhs = [i[f"lh_{j}"] for j in range(1, n + 1)]
        es_j = [i[f"es_t_p_{j}"] for j in range(2, n + 1)]
        want = liquidity_cascade(i["es_t_p"], es_j, lhs, i["t"])
        if not close(o["es"], want):
            msgs.append(f"{case}: the cascade is {want!r}, the document says {o['es']!r}")
    c = iv.get("cascade-all-lh-ten")
    if c and not close(vals(c, "outputs")["es"], vals(c, "inputs")["es_t_p"]):
        msgs.append("cascade with every LH equal to 10 must return ES_T(P)")
