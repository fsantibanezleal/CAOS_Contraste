"""Constants and helpers shared by the C15 tests (a uniquely named module: several units ship a ``conftest`` of their own)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SAMPLES = HERE / "samples"
for _p in (HERE, ROOT / "tests" / "contracts", ROOT / "tests" / "contracts_u10"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
SEED = 42
VARIANT_IDS = ("long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active")
SHOCKS = ("parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down")


def _find_data_root() -> Path | None:
    cand = os.environ.get("CONTRASTE_DATA")            # the device data root by role; never a drive written here
    if cand and (Path(cand) / "raw" / "bcch-f022" / "provenance.json").exists():
        return Path(cand)
    return None


# resolved once, at import: the suite's sandbox fixture (tests/conftest.py) removes CONTRASTE_DATA from every test's environment
_DATA_ROOT = _find_data_root()


def data_root() -> Path | None:
    return _DATA_ROOT


requires_raw = pytest.mark.skipif(data_root() is None, reason="the raw BCCh files are not in the device data root")


def make_series(code: str, values: dict[str, float | None], title_es: str = "Tasa de interés mercado secundario, bonos a 5 años"):
    """A parsed BDE series from ``{ISO date: percent or None}`` (None is an ``ND`` observation), through the real parser."""
    import json

    from pipeline.io import bcch

    obs = []
    for day, v in values.items():
        y, m, d = day.split("-")
        obs.append({"indexDateString": f"{d}-{m}-{y}", "value": "NaN" if v is None else repr(float(v)), "statusCode": "ND" if v is None else "OK"})
    body = {"Codigo": 0, "Descripcion": "Success", "Series": {"descripEsp": title_es, "descripIng": f"English title of {code}", "seriesId": code, "Obs": obs}}
    return bcch.parse_series(json.dumps(body, ensure_ascii=False).encode("latin-1"))


def make_info(code: str, first: str = "2002-09-12", last: str = "2026-10-14", title_es: str = "Tasa de interés mercado secundario"):
    from pipeline.io import bcch

    return bcch.SeriesInfo(code, "DAILY", title_es, f"English title of {code}", first, last)


CLP_CODES = {2: "F022.BCLP.TIS.AN02.NO.Z.D", 5: "F022.BCLP.TIS.AN05.NO.Z.D", 10: "F022.BCLP.TIS.AN10.NO.Z.D"}
UF_CODES = {2: "F022.BUF.TIS.AN02.UF.Z.D", 5: "F022.BUF.TIS.AN05.UF.Z.D", 10: "F022.BUF.TIS.AN10.UF.Z.D", 30: "F022.BUF.TIS.AN30.UF.Z.D"}
STALE = {"F022.BCLP.TIS.AN01.NO.Z.D": "2025-12-24", "F022.BUF.TIS.AN01.UF.Z.D": "2025-12-26", "F022.BUF.TIS.AN20.UF.Z.D": "2026-08-18"}


def world(extra_clp_tenor: bool = False):
    """A small BDE world of September 2026: ``(series by code, infos)``. The valuation date of the rule is 2026-09-02: AN30 UF has no value
    on the 3rd, CLP AN10 none on the 4th, and the stale series of the BCCh (1 year CLP and UF, 20 years UF) have no value in the month."""
    days = ("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07")
    clp = {2: (4.9, 4.9, 4.9, 4.9, 4.9), 5: (5.4, 5.4, 5.4, 5.5, 5.5), 10: (5.7, 5.7, 5.7, None, None)}
    uf = {2: (1.8, 1.8, 1.8, 1.8, 1.8), 5: (2.2, 2.2, 2.2, 2.3, 2.3), 10: (2.5, 2.5, 2.5, 2.6, 2.6), 30: (2.8, 2.8, None, 2.9, None)}
    series, infos = {}, []
    for tenor, code in CLP_CODES.items():
        series[code] = make_series(code, dict(zip(days, clp[tenor])))
        infos.append(make_info(code))
    for tenor, code in UF_CODES.items():
        series[code] = make_series(code, dict(zip(days, uf[tenor])))
        infos.append(make_info(code))
    if extra_clp_tenor:
        code = "F022.BCLP.TIS.AN07.NO.Z.D"
        series[code] = make_series(code, dict(zip(days, (5.55, 5.55, 5.55, 5.6, 5.6))))
        infos.append(make_info(code))
    for code, last in STALE.items():
        infos.append(make_info(code, last=last))
        series[code] = make_series(code, {d: None for d in days})
    series["F022.TPM.TIN.D001.NO.Z.D"] = make_series("F022.TPM.TIN.D001.NO.Z.D", {d: 4.5 for d in days}, "Tasa de política monetaria (TPM)")
    series["F073.UFF.PRE.Z.D"] = make_series("F073.UFF.PRE.Z.D", {d: 40870.0 + k for k, d in enumerate(days)}, "Unidad de fomento (UF)")
    infos.append(make_info("F022.TPM.TIN.D001.NO.Z.D"))
    infos.append(make_info("F073.UFF.PRE.Z.D"))
    return series, infos
