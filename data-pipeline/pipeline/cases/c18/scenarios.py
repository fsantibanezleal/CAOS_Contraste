"""The four scenarios as published and transposed onto the Banco Andino jump-off, through ``riskvalidation.stress.paths``.

Every path is a published path (Fed 2026 baseline and severely adverse, the EBA/ESRB 2025 adverse, the NGFS Phase 5 Delayed transition)
whose **shape** (its change from its own jump-off) is put on the last observed value of the same series (the United States history at
2025 Q4), the periods aligned by their distance from the jump-off. The satellites are fitted on United States charge-off rates, so the
transposition onto Banco Andino is a labelled adaptation (``us-calibrated-adaptation``). The engine does the arithmetic
(``transpose_path``, ``annual_to_quarterly``, ``level_from_deviation``, ``check_vintage``); this module reads the sources and builds the
document block.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.stress import paths as rv_paths

from . import eba as eba_reader
from . import fetch
from . import ngfs as ngfs_reader
from . import params as P
from .fed import FedInputs

T = P.text
RULE = "shape-onto-last-observed-then-revert-to-baseline"
LABEL = "transposed-onto-banco-andino-jump-off"
ADAPTATION = T("The path is a United States path transposed onto the last observed value of the United States history; the satellites are fitted "
               "on United States charge-off rates and applied to Banco Andino: a US-calibrated adaptation.")
UNIT_NAMES = {"real_gdp_growth": "percent, annualised", "unemployment_rate": "percent", "prime_rate": "percent", "treasury_10y": "percent"}


@dataclass(frozen=True)
class Scenario:
    key: str                              # baseline | eba | fed | ngfs
    scenario_id: str
    block: dict[str, Any]                 # the document's outputs.scenario
    transposed: dict[str, np.ndarray]     # regressor -> 12 quarterly values
    missing_reason: str | None = None


def _pts(dates: list[str], values: Any) -> list[dict[str, Any]]:
    return [{"date": d, "value": float(v)} for d, v in zip(dates, values, strict=True)]


def _target(fed: FedInputs, regressor: str) -> float:
    return float(fed.hist(regressor).loc[P.JUMP_OFF])


def _quarters() -> list[str]:
    return P.next_quarters(P.JUMP_OFF, P.HORIZON_QUARTERS)


def fed_scenario(key: str, fed: FedInputs) -> Scenario:
    """The baseline or the severely adverse Federal Reserve 2026 path: 13 quarters, the first 12 transposed."""
    sev = key == "fed"
    df = fed.scenarios["severely-adverse" if sev else "baseline"]
    dates13 = list(df["quarter_end"])
    qs = _quarters()
    paths, transposed = [], {}
    for regressor, variable in (("unemployment_rate", "Unemployment rate"), ("real_gdp_growth", "Real GDP growth"), ("prime_rate", "Prime rate")):
        levels = df[regressor].to_numpy(dtype=float)
        jump = _target(fed, regressor)
        tr = rv_paths.transpose_path(levels, jump, jump, P.HORIZON_QUARTERS)      # the Fed path starts on the last actual: target = its jump-off
        transposed[regressor] = tr
        pts = _pts(dates13, levels)
        paths.append({
            "variable": variable, "unit": UNIT_NAMES[regressor], "maps_to_regressor": regressor, "frequency": "quarterly",
            "vintage_date": "2026-02-04", "level_rule": {"kind": "level", "baseline": None}, "source": pts, "levels": [dict(p) for p in pts],
            "transposition": {"label": LABEL, "rule": RULE, "source_jump_off": {"date": P.JUMP_OFF, "value": jump},
                              "target": {"date": P.JUMP_OFF, "value": jump}, "reversion": "none-within-horizon"},
            "transposed": _pts(qs, tr)})
    name = "2026_Final_Supervisory_Severely_Adverse_Domestic.csv" if sev else "2026_Final_Supervisory_Baseline_Domestic.csv"
    block = {
        "scenario_id": P.SCENARIOS[key],
        "title": T("Federal Reserve 2026 severely adverse", "Severamente adverso de la Reserva Federal 2026") if sev
        else T("Baseline (Federal Reserve 2026)", "Base (Reserva Federal 2026)"),
        "provider": "fed", "source_document": name, "source_url": "https://www.federalreserve.gov/supervisionreg/files/" + name,
        "vintage_date": "2026-02-04", "adaptation_label": "us-calibrated-adaptation", "adaptation_statement": ADAPTATION, "paths": paths,
        "policy_shock_window": None}
    return Scenario(key, P.SCENARIOS[key], block, transposed)


def eba_scenario(fed: FedInputs, workbook: dict[str, eba_reader.EbaPath]) -> Scenario:
    """The EBA/ESRB 2025 adverse path of the United States: three annual values from year-end 2024, joined to year-end levels."""
    qs = _quarters()
    dates = [f"{y}-12-31" for y in eba_reader.YEARS]
    paths, transposed = [], {}
    for regressor in ("real_gdp_growth", "unemployment_rate", "treasury_10y"):
        p = workbook[regressor]
        levels = np.array(p.adverse)
        quarterly = rv_paths.annual_to_quarterly(levels, p.jump_off_value)
        target = _target(fed, regressor)
        tr = rv_paths.transpose_path(quarterly, p.jump_off_value, target, P.HORIZON_QUARTERS)
        transposed[regressor] = tr
        paths.append({
            "variable": p.variable, "unit": p.unit, "maps_to_regressor": regressor, "frequency": "annual", "vintage_date": fetch.EBA_VINTAGE,
            "level_rule": {"kind": "level", "baseline": None}, "source": _pts(dates, levels), "levels": _pts(dates, levels),
            "transposition": {"label": LABEL, "rule": RULE, "source_jump_off": {"date": "2024-12-31", "value": p.jump_off_value},
                              "target": {"date": P.JUMP_OFF, "value": target}, "reversion": "none-within-horizon"},
            "transposed": _pts(qs, tr)})
    block = {
        "scenario_id": P.SCENARIOS["eba"], "title": T("EBA and ESRB 2025 adverse scenario", "Escenario adverso EBA y ESRB 2025"),
        "provider": "eba-esrb",
        "source_document": "2025 EU-wide stress test - Macro financial scenario (updated 26 February 2025), United States rows",
        "source_url": fetch.EBA_URL, "vintage_date": fetch.EBA_VINTAGE, "adaptation_label": "us-calibrated-adaptation",
        "adaptation_statement": T("The adverse annual values of the United States for 2025 to 2027, read as year-end levels joined linearly from year-end 2024 "
                                  "(the workbook says annual averages; the year-end reading is UNVERIFIED), transposed onto the last observed value of the "
                                  "United States history; the satellites are US-calibrated."),
        "paths": paths, "policy_shock_window": None}
    return Scenario("eba", P.SCENARIOS["eba"], block, transposed)


def ngfs_scenario(fed: FedInputs, variables: list[ngfs_reader.NgfsVariable]) -> Scenario:
    """The NGFS Phase 5 Delayed transition: the baseline plus the deviation of the three years of the policy shock (2031 to 2033)."""
    qs = _quarters()
    years = list(ngfs_reader.SHOCK_YEARS)
    dates = [f"{y}-12-31" for y in years]
    paths, transposed = [], {}
    for v in variables:
        base = np.array([v.baseline[y] for y in years])
        dev = np.array([v.deviation[y] for y in years])
        levels = rv_paths.level_from_deviation(base, dev, v.kind)
        jump_level = float(rv_paths.level_from_deviation(np.array([v.baseline[ngfs_reader.JUMP_YEAR]]), np.array([v.deviation[ngfs_reader.JUMP_YEAR]]), v.kind)[0])
        target = _target(fed, v.regressor)
        if v.kind == "percent":
            # a level path of a growth regressor: each year's four quarters carry that year's growth in percent
            growth, prev = [], jump_level
            for lv in levels:
                growth.append((float(lv) / prev - 1.0) * 100.0)
                prev = float(lv)
            tr = np.repeat(np.array(growth), 4)
            rule = {"kind": "baseline-times-percent-deviation", "baseline": _pts(dates, base)}
        else:
            tr = rv_paths.transpose_path(rv_paths.annual_to_quarterly(levels, jump_level), jump_level, target, P.HORIZON_QUARTERS)
            rule = {"kind": "baseline-plus-deviation", "baseline": _pts(dates, base)}
        transposed[v.regressor] = tr
        paths.append({
            "variable": v.scenario_name, "unit": v.scenario_unit, "maps_to_regressor": v.regressor, "frequency": "annual",
            "vintage_date": ngfs_vintage(), "level_rule": rule, "source": _pts(dates, dev), "levels": _pts(dates, levels),
            "transposition": {"label": LABEL, "rule": RULE, "source_jump_off": {"date": f"{ngfs_reader.JUMP_YEAR}-12-31", "value": jump_level},
                              "target": {"date": P.JUMP_OFF, "value": target}, "reversion": "none-within-horizon"},
            "transposed": _pts(qs, tr)})
    order = [v[0] for v in ngfs_reader.VARIABLES]
    paths.sort(key=lambda p: order.index(p["variable"]))
    block = {
        "scenario_id": P.SCENARIOS["ngfs"], "title": T("NGFS Phase 5 delayed transition (disorderly)", "Transición tardía NGFS fase 5 (desordenada)"),
        "provider": "ngfs",
        "source_document": "NGFS Phase V, NiGEM NGFS v1.24.2 runs, read through the IIASA Scenario Explorer (IXSE_NGFS_PHASE_5)",
        "source_url": fetch.NGFS_UI, "vintage_date": ngfs_vintage(), "adaptation_label": "us-calibrated-adaptation",
        "adaptation_statement": T("The United States NiGEM deviations of the three years in which the policy shock acts, added to the Baseline run and transposed "
                                  "onto the last observed value; the satellites are US-calibrated."),
        "paths": paths,
        "policy_shock_window": {"start_year": years[0], "end_year": years[-1],
                                "label": T("The policy shock acts in 2031 to 2033: zero deviation through 2030 and the first deviation in 2031 (F8 of the "
                                           "research addendum). NGFS is the only Phase 5 scenario NGFS itself classes as disorderly.")}}
    return Scenario("ngfs", P.SCENARIOS["ngfs"], block, transposed)


def ngfs_vintage() -> str:
    return fetch.NGFS_VINTAGE


def check_vintages(block: dict[str, Any], observation_date: str = P.AS_OF) -> None:
    """No scenario vintage postdates the observation date (SDD l.169), through the engine's check."""
    rv_paths.check_vintage(block["vintage_date"], observation_date)
    for p in block["paths"]:
        rv_paths.check_vintage(p["vintage_date"], observation_date)
