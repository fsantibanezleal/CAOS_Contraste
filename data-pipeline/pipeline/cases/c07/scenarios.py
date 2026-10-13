"""The six scenario variants of C07 and the weighting scenarios of the IFRS 9 regime (CT-711).

Scenario conditioning only: the loans of Banco Andino are fixed per seed; a variant moves the systematic factor (the
variant's ``z_shift``, added to every weighting scenario), moves a fixed uniform draw of each account into arrears or
default (the account's own draw, so a harsher variant moves a superset of the accounts a milder one moves), and moves
the collateral values with the house price index. Every magnitude carries its basis: a source or the explicit label
"assumption of the case" (``ASSUMPTION``). The Federal Reserve severely adverse scenario of the 2026 cycle is named as
a reference only (unemployment peaks at 10.0 per cent in its published CSV, dossier 08 D.1); no Chilean official
scenario path was readable (the BCCh site answered with a bot-protection page, dossier 08 D.5, UNVERIFIED).
"""
from __future__ import annotations

from typing import Any

ASSUMPTION = "assumption of the case"
FED_REF = ("reference: Federal Reserve 2026 severely adverse scenario, unemployment peak 10.0 per cent "
           "(dossier 08 D.1, checked); not a Chilean path")

#: the weighting scenarios of the IFRS 9 regime (dossier 02 B.4 worked example: factors 1, 0 and -2, weights 25, 50, 25 per
#: cent): z_offset is the offset around current conditions; the variant adds its z_shift
WEIGHTING: tuple[dict[str, Any], ...] = (
    {"id": "upside", "label": {"en": "Upside", "es": "Favorable"}, "weight": 0.25, "z_offset": 1.0},
    {"id": "central", "label": {"en": "Central", "es": "Central"}, "weight": 0.50, "z_offset": 0.0},
    {"id": "downside", "label": {"en": "Downside", "es": "Adverso"}, "weight": 0.25, "z_offset": -2.0},
)
WEIGHTING_BASIS = "dossier 02 B.4 (worked example of the non-linearity of the weighted ECL)"

#: ``shocks`` are the document's drivers; ``channels`` are the extra default probabilities per calibration class
#: (probability that a performing account of the class is moved to default, the account's own draw decides);
#: ``hpi`` is the house price change applied to real-estate collateral values
SCENARIOS: tuple[dict[str, Any], ...] = (
    {"id": "base", "z_shift": 0.0, "hpi": 0.0, "channels": {}, "shocks": [],
     "label": {"en": "Base", "es": "Base"},
     "description": {"en": "Base scenario: no shock; the portfolio at its reporting-date state.",
                     "es": "Escenario base: sin shock; la cartera en su estado a la fecha de reporte."}},
    {"id": "recession", "z_shift": -1.0, "hpi": -0.05, "channels": {},
     "shocks": [("gdp-growth", "percentage points", -3.0), ("unemployment", "percentage points", 4.0),
                ("house-prices", "percent", -5.0)],
     "label": {"en": "Recession", "es": "Recesión"},
     "description": {"en": "Recession: GDP growth 3 points below base, unemployment 4 points above, house prices 5 per cent down; "
                           "the systematic factor shifts by -1.0 standard deviations. All magnitudes: assumption of the case; "
                           + FED_REF + ".",
                     "es": "Recesión: crecimiento del PIB 3 puntos bajo el base, desempleo 4 puntos sobre, precios de viviendas 5 % a la baja; "
                           "el factor sistemático se desplaza -1,0 desviaciones estándar. Todas las magnitudes: supuesto del caso; "
                           "referencia: escenario severamente adverso 2026 de la Reserva Federal, desempleo máximo 10,0 % (dossier 08 D.1); no es una trayectoria chilena."}},
    {"id": "consumer-arrears-shock", "z_shift": -0.3, "hpi": 0.0, "channels": {"consumer": 0.03},
     "shocks": [("consumer-arrears", "percentage points", 3.0)],
     "label": {"en": "Consumer arrears shock", "es": "Shock de mora de consumo"},
     "description": {"en": "Consumer arrears shock: 3 per cent of the consumer accounts move to 90 days or more past due, the systematic "
                           "factor shifts by -0.3. Magnitudes: assumption of the case.",
                     "es": "Shock de mora de consumo: el 3 % de las cuentas de consumo pasa a mora de 90 días o más, el factor "
                           "sistemático se desplaza -0,3. Magnitudes: supuesto del caso."}},
    {"id": "house-price-fall", "z_shift": -0.4, "hpi": -0.15, "channels": {},
     "shocks": [("house-prices", "percent", -15.0)],
     "label": {"en": "House price fall", "es": "Caída del precio de viviendas"},
     "description": {"en": "House prices 15 per cent down: real-estate collateral values fall, which moves recoveries and the Annex 9 "
                           "uncovered amount; the B-1 group matrices use the appraisal at origination and do not move; the systematic "
                           "factor shifts by -0.4. Magnitudes: assumption of the case (the Fed 2026 severely adverse path is about "
                           "-30 per cent, UNVERIFIED in dossier 08 D.1).",
                     "es": "Precios de viviendas 15 % a la baja: caen los valores de las garantías inmobiliarias, lo que mueve las "
                           "recuperaciones y el monto no cubierto del Anejo 9; las matrices grupales de B-1 usan la tasación de origen y no "
                           "se mueven; el factor sistemático se desplaza -0,4. Magnitudes: supuesto del caso."}},
    {"id": "uf-inflation-spike", "z_shift": -0.3, "hpi": 0.0, "channels": {"mortgage": 0.010, "commercial-group": 0.005},
     "shocks": [("uf-inflation", "percentage points", 4.0)],
     "label": {"en": "UF inflation spike", "es": "Alza de inflación UF"},
     "description": {"en": "UF inflation 4 points above base: UF-indexed instalments rise faster than income; 1.0 per cent of the mortgage and "
                           "0.5 per cent of the group commercial accounts move to default (0.25 and 0.125 points per point of inflation), the "
                           "systematic factor shifts by -0.3. Magnitudes: assumption of the case.",
                     "es": "Inflación UF 4 puntos sobre el base: las cuotas indexadas a la UF suben más que el ingreso; el 1,0 % de las cuentas "
                           "hipotecarias y el 0,5 % de las comerciales grupales pasa a incumplimiento (0,25 y 0,125 puntos por punto de inflación), "
                           "el factor sistemático se desplaza -0,3. Magnitudes: supuesto del caso."}},
    {"id": "combined-severe", "z_shift": -2.0, "hpi": -0.25, "channels": {},
     "shocks": [("gdp-growth", "percentage points", -5.0), ("unemployment", "percentage points", 6.0),
                ("house-prices", "percent", -25.0)],
     "label": {"en": "Combined severe", "es": "Severo combinado"},
     "description": {"en": "Combined severe: GDP growth 5 points below base, unemployment 6 points above, house prices 25 per cent down; the "
                           "systematic factor shifts by -2.0. All magnitudes: assumption of the case; " + FED_REF + ".",
                     "es": "Severo combinado: crecimiento del PIB 5 puntos bajo el base, desempleo 6 puntos sobre, precios de viviendas 25 % a la baja; "
                           "el factor sistemático se desplaza -2,0. Todas las magnitudes: supuesto del caso; referencia: escenario severamente "
                           "adverso 2026 de la Reserva Federal (dossier 08 D.1); no es una trayectoria chilena."}},
)

SCENARIO_IDS = tuple(s["id"] for s in SCENARIOS)
#: what the engine's roll rate means: extra accounts that move one arrears bucket per extra default
ROLL_RATIO = 3.0


class ScenarioError(ValueError):
    """A scenario magnitude without its basis."""


def basis(scenario: dict[str, Any]) -> str:
    """The basis stated in the scenario's description (a source or the assumption label)."""
    return scenario["description"]["en"]


def validate_scenarios(scenarios: tuple[dict[str, Any], ...] = SCENARIOS) -> None:
    """Every scenario with a shock names its basis, and the ids are the six of the SDD (CT-711)."""
    if tuple(s["id"] for s in scenarios) != SCENARIO_IDS:
        raise ScenarioError(f"the variants are {SCENARIO_IDS}")
    for s in scenarios:
        if s["shocks"] and ASSUMPTION not in basis(s) and "source:" not in basis(s):
            raise ScenarioError(f"scenario {s['id']}: its magnitudes carry neither a source nor the label {ASSUMPTION!r}")
        for driver, unit, value in s["shocks"]:
            if not driver or not unit or not isinstance(value, (int, float)):
                raise ScenarioError(f"scenario {s['id']}: malformed shock {driver!r}")


def scenario(sid: str) -> dict[str, Any]:
    return next(s for s in SCENARIOS if s["id"] == sid)
