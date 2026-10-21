"""The EUR to CLP rate of the as-of date from the Banco Central de Chile (series F072.CLP.EUR.N.O.D, the observed rate of the euro)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...io import bcch
from . import fetch
from . import params as P


@dataclass(frozen=True)
class FxRate:
    series_id: str
    title: str
    observation_date: str
    value: float


def read_rate(data_root: str | Path, as_of: str = P.AS_OF) -> FxRate:
    """The last observation of the series on or before ``as_of`` (a day without a value is skipped, never filled)."""
    folder = Path(data_root) / "raw" / fetch.FX_DIR
    path = folder / bcch.file_name(P.FX_SERIES, P.FX_FIRST, P.FX_LAST)
    if not path.exists():
        raise FileNotFoundError(f"{path.name} is not in {folder}; fetch the series {P.FX_SERIES} with "
                                f"`python -m pipeline.cases.c18.fetch --fx` ({bcch.LANDING})")
    s = bcch.parse_series(path.read_bytes())
    values = s.values(up_to=as_of)
    if not values:
        raise ValueError(f"{s.series_id}: no value on or before {as_of}")
    date = max(values)
    return FxRate(s.series_id, s.title_en or s.title_es, date, float(values[date]))
