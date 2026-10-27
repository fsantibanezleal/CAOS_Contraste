"""The net interest income of the PPNR row, following the rate path of each variant (decisions Q10 and Z11 of the U13 sizing).

The base is the C15 twelve-month net interest margin of Banco Andino. For each year of the horizon the engine's ``irrbb.eve_nii.delta_nii`` (loss
positive, on C15's book and curve) gives the change of that margin when the curve is shifted in parallel by the variant's transposed rate change from
the jump-off, with C15's floors (0 for the pesos leg, -2 percent for the UR leg, applied by ``shocks.apply_floor``). The rate is the
variant's short rate where it carries one (the Fed prime rate, the NGFS policy rate, which the paths map to ``prime_rate``) and its 10-year rate
otherwise (the EBA long-term rate). An EVE change is not a profit-and-loss item of the banking book: it stays out of the capital path.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from riskvalidation.irrbb import eve_nii, shocks

from . import params as P
from .anchors import Anchors

FLOORS = {"CLP": 0.0, "UR": -0.02}
KEY = {"CLP": "clp", "UR": "ur"}
RATE_NAMES = {"prime_rate": "the short rate (prime rate / policy rate)", "treasury_10y": "the 10-year rate"}


@dataclass(frozen=True)
class RatePath:
    regressor: str                 # prime_rate or treasury_10y
    variable: str                  # the variant's own name for it
    shifts_bp: tuple[float, float, float]


def rate_of(transposed: dict[str, np.ndarray], paths: list[dict]) -> tuple[str, str]:
    """The short rate if the variant carries one, otherwise its 10-year rate; with the variable's name in the variant."""
    for reg in ("prime_rate", "treasury_10y"):
        for p in paths:
            if p["maps_to_regressor"] == reg:
                return reg, p["variable"]
    raise ValueError("the variant carries neither a short rate nor a 10-year rate: the PPNR row has no rate path to follow")


def yearly_shifts_bp(transposed: dict[str, np.ndarray], reg: str, jump_off_value: float) -> tuple[float, float, float]:
    """The mean change from the jump-off of the four quarters of each year, in basis points."""
    path = np.asarray(transposed[reg], dtype=float)
    return tuple(float(np.mean(path[4 * y: 4 * y + 4]) - jump_off_value) * 100.0 for y in range(3))   # type: ignore[return-value]


def nii_by_year(anchors: Anchors, shifts_bp: tuple[float, float, float]) -> list[float]:
    """The twelve-month NII of each year: the C15 margin less the engine's delta NII of the shift (the sum of the two currency legs)."""
    o, models = anchors.c15, anchors.c15_models
    uf = o["ur_currency"]["uf_value"]
    mid = np.array([b["midpoint_years"] for b in models["buckets"]])
    conv = {"CLP": 1.0, "UR": uf}
    base_nii = float(o["thresholds"]["net_interest_and_indexation_margin_12m"])
    out = []
    for bp in shifts_bp:
        delta = 0.0
        for leg in o["legs"]:
            n = leg["leg"]
            r0 = np.array(o["curves"][KEY[n]]["zero_rates_at_midpoints"])
            flows = np.zeros(19)
            for it in leg["items"]:
                for cf in it["cash_flows"]:
                    flows[cf["bucket"] - 1] += cf["amount"] * conv[n]
            shocked = shocks.apply_floor(r0, np.full(19, bp), FLOORS[n])
            delta += float(eve_nii.delta_nii(flows, r0, shocked, mid))
        out.append(base_nii - delta)
    return out


#: the Spanish of the rate a variant's NII follows (U16-R3 c19 B3: "(Prime rate)" in the Spanish view; the product names it tasa preferencial)
RATE_NAME_ES = {"Prime rate": "tasa preferencial", "10-year Treasury rate": "tasa del Tesoro a 10 años", "Long-term interest rate": "tasa de interés de largo plazo",
                "Long term interest rate": "tasa de interés de largo plazo",
                "Central bank Intervention rate (policy interest rate)": "tasa de intervención del banco central, la tasa de política monetaria"}
#: the English name of the same rates, as the product writes them in a sentence (U16-R4 c23 B1: the NGFS sentence printed the source variable
#: with its unit and aggregation suffix, "Central bank Intervention rate (policy interest rate) ; %(combined)")
RATE_NAME_EN = {"Prime rate": "prime rate", "10-year Treasury rate": "10-year Treasury rate", "Long-term interest rate": "long-term interest rate",
                "Long term interest rate": "long-term interest rate",
                "Central bank Intervention rate (policy interest rate)": "central bank intervention rate, the policy rate"}


def rate_name_es(name: str) -> str:
    """The Spanish name of a rate variable of a scenario (the NGFS suffix " ; %(combined)" dropped); an unknown name stops the bake."""
    base = name.split(" ;")[0].strip()
    if base not in RATE_NAME_ES:
        raise ValueError(f"no Spanish name for the rate variable {name!r}: add it to nii.RATE_NAME_ES")
    return RATE_NAME_ES[base]


def rate_name_en(name: str) -> str:
    """The English name of a rate variable of a scenario in a sentence (the NGFS suffix " ; %(combined)" dropped); an unknown name stops the bake."""
    base = name.split(" ;")[0].strip()
    if base not in RATE_NAME_EN:
        raise ValueError(f"no English name for the rate variable {name!r}: add it to nii.RATE_NAME_EN")
    return RATE_NAME_EN[base]


def rate_statement(name: str, regressor: str) -> dict[str, str]:
    """The sentence of the rate the NII follows, naming the rate as the product does, never the source's variable string (U16-R4 c23 B1)."""
    kind = "short rate" if regressor == "prime_rate" else "10-year rate"
    return P.text(f"The NII of each year follows the variant's {kind} (the {rate_name_en(name)}): the C15 twelve-month margin less the engine's delta NII on "
                  "C15's book and curve, shifted in parallel by the mean change of that rate in the year from the jump-off, with C15's floors.",
                  f"El NII de cada año sigue la tasa de {'corto plazo' if regressor == 'prime_rate' else 'diez años'} de la variante (la {rate_name_es(name)}): "
                  "el margen de doce meses de C15 menos el delta NII del motor sobre el libro y la curva de C15, desplazada en paralelo por el cambio medio de esa tasa "
                  "en el año desde el punto de partida, con los pisos de C15.")
