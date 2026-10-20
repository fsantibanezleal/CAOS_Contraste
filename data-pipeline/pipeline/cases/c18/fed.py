"""The Federal Reserve inputs of C18: the history and the two 2026 supervisory scenarios (agency columns only) and the Board's
net charge-off rates (signed, as the Board prints them).

``io/sba.py`` reads three columns of these files; C18 needs the 10-year Treasury yield as well (the EBA long-term rate maps onto it), so
the columns are read here by name from the same files, without changing the shared reader (reservation R3 of the U13 sizing). The
third-party index levels of the historic table (equity, house price, commercial real estate price, volatility, BBB yield) are never
read (decision Q7). A missing file stops the bake and names the URL it comes from. The charge-off table is the reader of C10
(``cases/c10/fed.py``), unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ...io import sba
from ..c10 import fed as chargeoff
from . import params as P

COLUMNS = {"Real GDP growth": "real_gdp_growth", "Unemployment rate": "unemployment_rate", "Prime rate": "prime_rate",
           "10-year Treasury yield": "treasury_10y"}
SCENARIO_FILES = {"baseline": sba.FED_BASELINE, "severely-adverse": sba.FED_SEVERE}


def _read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=lambda c: c in ("Scenario Name", "Date", *COLUMNS))
    missing = [c for c in ("Scenario Name", "Date", *COLUMNS) if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: the layout changed, missing columns {missing}")
    df = df.rename(columns=COLUMNS)
    df["quarter_end"] = [P.quarter_label_end(s) for s in df["Date"]]
    return df[["Scenario Name", "quarter_end", *COLUMNS.values()]].rename(columns={"Scenario Name": "scenario"}).reset_index(drop=True)


@dataclass(frozen=True)
class FedInputs:
    history: pd.DataFrame
    scenarios: dict[str, pd.DataFrame]
    files: tuple[str, ...]

    def hist(self, column: str) -> pd.Series:
        return self.history.set_index("quarter_end")[column]


def read_inputs(data_root: str | Path) -> FedInputs:
    """The history (1976 Q1 to the last actual) and the 13 quarters of each scenario, by quarter end."""
    folder = Path(data_root) / "raw" / sba.FED_FOLDER
    paths = {name: sba._need(folder / name, sba.FED_URLS[name]) for name in sba.FED_FILES}
    history = _read(paths[sba.FED_HISTORY])
    scen = {k: _read(paths[v]) for k, v in SCENARIO_FILES.items()}
    for k, df in scen.items():
        if len(df) != 13:
            raise ValueError(f"the Federal Reserve {k} table holds {len(df)} quarters, not 13 (dossier 08 D.1)")
    if history["quarter_end"].iloc[-1] != P.JUMP_OFF:
        raise ValueError(f"the Federal Reserve history ends {history['quarter_end'].iloc[-1]}, not at the jump-off {P.JUMP_OFF}")
    if scen["baseline"]["quarter_end"].iloc[0] != P.next_quarters(P.JUMP_OFF, 1)[0]:
        raise ValueError("the Federal Reserve scenarios do not start the quarter after the history")
    return FedInputs(history, scen, sba.FED_FILES)


@dataclass(frozen=True)
class Rates:
    """The charge-off rates of the five loan types as decimals, aligned on ``quarters`` (NaN where the Board has none: never filled)."""

    quarters: tuple[str, ...]
    rates: dict[str, np.ndarray]
    updated: str | None
    non_positive: dict[str, int]

    def window(self, loan_type: str, start: str, end: str) -> np.ndarray:
        i, j = self.quarters.index(start), self.quarters.index(end)
        return self.rates[loan_type][i:j + 1]


def read_chargeoffs(data_root: str | Path) -> Rates:
    """The Board's net charge-off rates, signed: a quarter of net recoveries stays negative or zero, none is floored or dropped (W1)."""
    path = Path(data_root) / "raw" / "fed-chargeoff" / "chgallsa.htm"
    if not path.exists():
        raise sba.SourceUnavailable(f"{path.name} is not in {path.parent}; fetch it from {chargeoff.URL}")
    table = chargeoff.read_table(path)
    qs = tuple(P.quarter_label_end(q) for q in table.quarters)
    rates = {}
    for ltype, (col, _link, _first) in P.FED_TYPES.items():
        rates[ltype] = np.array([np.nan if v is None else v / 100.0 for v in table.series[col]], dtype=float)
    return Rates(qs, rates, table.updated, {})


def aligned(history: pd.DataFrame, rates: Rates) -> tuple[list[str], np.ndarray]:
    """The quarters both the rates and the history cover (1985 Q1 to the last actual) and the regressor matrix of the satellites."""
    hq = history.set_index("quarter_end")
    qs = [q for q in rates.quarters if q in hq.index]
    x = np.column_stack([hq.loc[qs, name].to_numpy(dtype=float) for name in P.REGRESSORS])
    return qs, x
