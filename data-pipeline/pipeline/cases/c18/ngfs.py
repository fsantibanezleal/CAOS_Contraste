"""The NGFS Phase 5 reader: the reader of the saved runs of a standard-library client of the IIASA Manager API (no ``pyam``).

The API (application ``IXSE_NGFS_PHASE_5``, see ``fetch.py``) issues an anonymous token and serves a run's whole time series in long
form (``/runs/{id}/ts``: runId, model, scenario, region, variable, unit, year, value). Scenario runs hold **deviations** from the
Baseline run, so a level is the baseline plus the deviation (rates, unemployment) or the baseline times the percent difference (GDP),
which is ``riskvalidation.stress.paths.level_from_deviation`` (addendum F8). NGFS is derived-only (decision E6): the documents carry
the four United States variables of the three years of the policy shock and fitted parameters, never an extract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fetch

#: the four NiGEM variables of the record (F8): (scenario variable, its unit, baseline variable, its unit, kind, regressor)
VARIABLES = (
    ("Unemployment rate ; %(combined)", "Abs. difference", "Unemployment rate ; %", "%", "plus", "unemployment_rate"),
    ("Central bank Intervention rate (policy interest rate) ; %(combined)", "Abs. difference",
     "Central bank Intervention rate (policy interest rate) ; %", "%", "plus", "prime_rate"),
    ("Long term interest rate ; %(combined)", "Abs. difference", "Long term interest rate ; %", "%", "plus", "treasury_10y"),
    ("Gross Domestic Product (GDP)(combined)", "% difference,  2017 PPP ; US$ Bn", "Gross Domestic Product (GDP)", "2017 PPP ; US$ Bn", "percent",
     "real_gdp_growth"),
)
SHOCK_YEARS = (2031, 2032, 2033)       # the policy shock acts in 2031 to 2033 (F8): zero deviation through 2030, the first deviation in 2031
JUMP_YEAR = 2030


class NgfsReaderError(ValueError):
    """The saved run is not the long-form answer the reader knows."""


@dataclass(frozen=True)
class NgfsVariable:
    scenario_name: str
    scenario_unit: str
    baseline_name: str
    baseline_unit: str
    kind: str                       # "plus" or "percent"
    regressor: str
    deviation: dict[int, float]     # year -> deviation (2030 to 2033)
    baseline: dict[int, float]      # year -> baseline level (2030 to 2033)


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"{path.name} is not in {path.parent}; fetch it from {fetch.NGFS_BASE} (application IXSE_NGFS_PHASE_5, "
                                f"anonymous token at {fetch.IIASA_TOKEN_URL})")
    rows = json.loads(path.read_bytes())
    if not isinstance(rows, list) or not rows or not {"runId", "region", "variable", "unit", "year", "value"} <= set(rows[0]):
        raise NgfsReaderError(f"{path.name}: not a long-form IIASA run answer")
    return rows


def _series(rows: list[dict[str, Any]], run: int, region: str, name: str, unit: str, years: tuple[int, ...]) -> dict[int, float]:
    hit = {r["year"]: float(r["value"]) for r in rows if r["runId"] == run and r["region"] == region and r["variable"] == name
           and r["unit"] == unit and r["year"] in years}
    missing = [y for y in years if y not in hit]
    if missing:
        raise NgfsReaderError(f"run {run}, {region}, {name!r} ({unit}): no value for {missing}")
    return hit


def read_runs(data_root: str | Path) -> tuple[list[NgfsVariable], dict[str, Any]]:
    """The four variables of the Delayed transition (deviations) and the Baseline (levels) for 2030 to 2033, and the run facts."""
    folder = Path(data_root) / "raw" / fetch.NGFS_DIR
    base_rows = _load(folder / fetch.ngfs_name(fetch.NGFS_RUNS["baseline"]))
    scen_rows = _load(folder / fetch.ngfs_name(fetch.NGFS_RUNS["delayed-transition"]))
    years = (JUMP_YEAR, *SHOCK_YEARS)
    out = []
    for sname, sunit, bname, bunit, kind, regressor in VARIABLES:
        dev = _series(scen_rows, fetch.NGFS_RUNS["delayed-transition"], fetch.NGFS_REGION, sname, sunit, years)
        base = _series(base_rows, fetch.NGFS_RUNS["baseline"], fetch.NGFS_REGION, bname, bunit, years)
        out.append(NgfsVariable(sname, sunit, bname, bunit, kind, regressor, dev, base))
    facts = {"model": scen_rows[0]["model"], "scenario": scen_rows[0]["scenario"], "baseline_scenario": base_rows[0]["scenario"],
             "version": scen_rows[0]["version"], "region": fetch.NGFS_REGION}
    if facts["scenario"] != "Delayed transition":
        raise NgfsReaderError(f"run {fetch.NGFS_RUNS['delayed-transition']} is {facts['scenario']!r}, not the Delayed transition")
    return out, facts
