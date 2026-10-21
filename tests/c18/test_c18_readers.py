"""CT-1801 to CT-1805: the readers of C18 (Federal Reserve, charge-offs, EBA workbook, NGFS runs, BCCh EUR to CLP)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from c18_support import data_root, requires_raw

from pipeline.cases.c18 import eba, fed, fetch, fx, ngfs
from pipeline.cases.c18 import params as P
from pipeline.io import bcch, sba


@requires_raw
def test_fed_inputs_are_the_agency_columns_and_a_missing_file_names_its_url(tmp_path: Path) -> None:
    f = fed.read_inputs(data_root())
    assert set(f.history.columns) == {"scenario", "quarter_end", "real_gdp_growth", "unemployment_rate", "prime_rate", "treasury_10y"}
    for df in f.scenarios.values():
        assert set(df.columns) == set(f.history.columns)
        assert len(df) == 13
    assert f.history["quarter_end"].iloc[-1] == P.JUMP_OFF
    assert f.scenarios["baseline"]["quarter_end"].iloc[0] == "2026-03-31"
    assert not any("Index" in c or "BBB" in c or "Volatility" in c for c in f.history.columns)
    with pytest.raises(sba.SourceUnavailable) as exc:
        fed.read_inputs(tmp_path)
    assert "federalreserve.gov" in str(exc.value)


@requires_raw
def test_chargeoff_rates_are_signed_and_the_real_estate_series_start_in_1991() -> None:
    r = fed.read_chargeoffs(data_root())
    assert r.quarters[0] == "1985-03-31"
    for lt in ("commercial-real-estate", "residential"):
        i = r.quarters.index("1991-03-31")
        assert np.all(np.isnan(r.rates[lt][:i])) and np.all(np.isfinite(r.rates[lt][i:]))     # missing 1985 to 1990, never filled
        assert np.sum(r.window(lt, "1991-03-31", P.FIT_END) <= 0.0) > 0                       # net recoveries stay as printed
    assert np.sum(r.window("residential", "1991-03-31", P.FIT_END) <= 0.0) == 6
    assert np.sum(r.window("commercial-real-estate", "1991-03-31", P.FIT_END) <= 0.0) == 13
    for lt in ("commercial-industrial", "credit-cards", "other-consumer"):
        assert np.all(r.window(lt, P.FIT_START, P.FIT_END) > 0.0)


def _workbook(path: Path, years_ok: bool = True) -> Path:
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    specs = {"GDP": ("Real GDP", [None, None, None, "Historical growth (%)"], [None, None, None, 2024, 2025, 2026, 2027, 2025, 2026, 2027]),
             "Unemployment": ("Unemployment rate", [None] * 4, [None, None, None, 2024, 2025, 2026, 2027, 2025, 2026, 2027]),
             "Long-term rates": ("Long-term interest rates", [None] * 4, [None, None, None, 2024, 2024, 2025, 2026, 2027, 2025, 2026, 2027])}
    for sheet, (title, head, years) in specs.items():
        ws = wb.create_sheet(sheet)
        ws.append([])
        ws.append([None, title])
        ws.append([])
        ws.append(head)
        ws.append(years if years_ok else [None, None, None, 2023, 2025])
        ws.append([None, "Belgium", "BE", *([1.0] * (len(years) - 3))])
        ws.append([None, "United States", "US", *[float(k) for k in range(1, len(years) - 2)]])
    wb.save(path)
    return path


def test_eba_reader_reads_the_us_rows_and_refuses_an_unknown_layout(tmp_path: Path) -> None:
    p = eba.read_workbook(_workbook(tmp_path / "w.xlsx"))
    assert set(p) == {"real_gdp_growth", "unemployment_rate", "treasury_10y"}
    g = p["real_gdp_growth"]
    assert (g.jump_off_year, g.jump_off_value, g.baseline, g.adverse) == (2024, 1.0, (2.0, 3.0, 4.0), (5.0, 6.0, 7.0))
    r = p["treasury_10y"]
    assert (r.jump_off_value, r.baseline, r.adverse) == (2.0, (3.0, 4.0, 5.0), (6.0, 7.0, 8.0))      # the December 2024 starting point
    with pytest.raises(eba.EbaReaderError):
        eba.read_workbook(_workbook(tmp_path / "bad.xlsx", years_ok=False))
    with pytest.raises(FileNotFoundError) as exc:
        eba.read_workbook(tmp_path / "absent.xlsx")
    assert "eba.europa.eu" in str(exc.value)


@requires_raw
def test_eba_reader_reads_the_real_workbook_when_it_is_in_the_data_root() -> None:
    path = Path(data_root()) / "raw" / fetch.EBA_DIR / fetch.EBA_NAME
    if not path.exists():
        pytest.skip("the EBA workbook is not in the device data root")
    g = eba.read_workbook(path)["real_gdp_growth"]
    assert g.adverse[0] < g.baseline[0] and len(g.adverse) == 3


def _runs(folder: Path, shock: float = 0.1) -> None:
    folder.mkdir(parents=True)
    rows = []
    for name, unit_dev, bname, unit_base, kind, _reg in ngfs.VARIABLES:
        for y in (2030, 2031, 2032, 2033):
            base = 1000.0 if kind == "percent" else 4.0
            rows.append({"runId": 137, "model": "m", "scenario": "Baseline", "version": 2, "region": fetch.NGFS_REGION, "variable": bname, "unit": unit_base,
                         "year": y, "value": base + (y - 2030)})
            rows.append({"runId": 140, "model": "m", "scenario": "Delayed transition", "version": 2, "region": fetch.NGFS_REGION, "variable": name, "unit": unit_dev,
                         "year": y, "value": 0.0 if y == 2030 else shock * (y - 2030)})
    (folder / fetch.ngfs_name(137)).write_text(json.dumps([r for r in rows if r["runId"] == 137]))
    (folder / fetch.ngfs_name(140)).write_text(json.dumps([r for r in rows if r["runId"] == 140]))


@requires_raw
def test_ngfs_levels_are_the_baseline_plus_the_deviation_over_the_shock_window(tmp_path: Path) -> None:
    from pipeline.cases.c18 import scenarios

    _runs(tmp_path / "raw" / fetch.NGFS_DIR)
    variables, facts = ngfs.read_runs(tmp_path)
    assert facts["scenario"] == "Delayed transition" and facts["region"].endswith("United States")
    assert [v.scenario_name for v in variables] == [n for n, *_ in ngfs.VARIABLES]
    sc = scenarios.ngfs_scenario(fed.read_inputs(data_root()), variables)
    blk = sc.block
    assert (blk["policy_shock_window"]["start_year"], blk["policy_shock_window"]["end_year"]) == (2031, 2033)
    for p in blk["paths"]:
        assert [q["date"] for q in p["source"]] == ["2031-12-31", "2032-12-31", "2033-12-31"]
        kind, base = p["level_rule"]["kind"], p["level_rule"]["baseline"]
        for s, lv, b in zip(p["source"], p["levels"], base, strict=True):
            want = b["value"] + s["value"] if kind == "baseline-plus-deviation" else b["value"] * (1 + s["value"] / 100.0)
            assert lv["value"] == pytest.approx(want)
    with pytest.raises(FileNotFoundError) as exc:
        ngfs.read_runs(tmp_path / "empty")
    assert "IXSE_NGFS_PHASE_5" in str(exc.value)


def _bcch_answer(rows: list[tuple[str, str, str]]) -> bytes:
    obs = [{"indexDateString": d, "value": v, "statusCode": s} for d, v, s in rows]
    return json.dumps({"Codigo": 0, "Descripcion": "ok", "Series": {"seriesId": P.FX_SERIES, "descripEsp": "Tipo de cambio nominal euro",
                                                                    "descripIng": "Euro nominal exchange rate", "Obs": obs}}).encode("latin-1")


def test_the_eur_clp_rate_records_its_series_and_the_asset_scaling_uses_it(tmp_path: Path) -> None:
    folder = tmp_path / "raw" / fetch.FX_DIR
    folder.mkdir(parents=True)
    (folder / bcch.file_name(P.FX_SERIES, P.FX_FIRST, P.FX_LAST)).write_bytes(
        _bcch_answer([("28-08-2026", "1070.5", "OK"), ("30-08-2026", "NaN", "ND"), ("31-08-2026", "1076.06", "OK"), ("01-09-2026", "1099.0", "OK")]))
    rate = fx.read_rate(tmp_path)
    assert (rate.series_id, rate.observation_date, rate.value) == (P.FX_SERIES, "2026-08-31", 1076.06)
    assert fx.read_rate(tmp_path, "2026-08-30").value == 1070.5                 # the day without a value is skipped, never filled
    from pipeline.cases.c18 import anchors as anc
    from pipeline.cases.c18 import marginals

    a = anc.load_anchors()
    op = marginals.operational(a, rate.value, n_points=1 << 16)
    want = a.total_assets_clp_m / (a.c17_generator["assets_eur_bn"] * 1000.0 * rate.value)
    assert op.extras["asset_scaling"] == pytest.approx(want) and op.extras["fx_rate"] == rate.value
