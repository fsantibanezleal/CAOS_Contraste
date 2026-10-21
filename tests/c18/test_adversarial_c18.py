"""Adversarial checks of C18: what is planted, and the gate that must refuse it (docs/design/features/c18/validation.md)."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from c18_support import C18, ROOT, SEED, SMALL_DRAWS, SMALL_PATHS, data_root, requires_raw, semantics
from riskvalidation.stress import satellites as rv_sat
from riskvalidation.validation import aggregation as rv_va
from riskvalidation.validation import stress as rv_vs

from pipeline.cases.c18 import bake, eba, fed, fetch, fx, ngfs, page
from pipeline.cases.c18 import params as P
from pipeline.core.schemas import SchemaViolation, validate_document
from pipeline.io import bcch, sba

FED_V = "fed-2026-severely-adverse"


def doc(name: str) -> dict:
    return copy.deepcopy(json.loads((C18 / f"{name}.json").read_text(encoding="utf-8")))


def models() -> dict:
    return doc("models-banco-andino")


def docset() -> dict[str, dict]:
    keys = {"baseline": "baseline", "eba": "eba-2025-adverse", "fed": FED_V, "ngfs": "ngfs-delayed-transition", "aggregation": "t-copula-baseline",
            "reverse": "reverse-stress"}
    return {"models": models(), **{k: doc(v) for k, v in keys.items()}}


# ------------------------------------------------------------------------------------------------ the readers


@requires_raw
def test_adversarial_a_history_that_does_not_end_at_the_jump_off_is_refused(tmp_path: Path) -> None:
    folder = tmp_path / "raw" / sba.FED_FOLDER
    folder.mkdir(parents=True)
    for name in sba.FED_FILES:
        shutil.copy(Path(data_root()) / "raw" / sba.FED_FOLDER / name, folder / name)
    h = folder / sba.FED_HISTORY
    lines = h.read_text(encoding="utf-8").splitlines()
    h.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")                      # the last actual quarter removed
    with pytest.raises(ValueError, match="jump-off"):
        fed.read_inputs(tmp_path)


def test_adversarial_a_probit_fit_on_net_recoveries_is_refused_and_never_floored() -> None:
    rates = np.array([-0.0003, 0.0001, 0.0002, 0.0004, 0.0005, 0.0006, 0.0007, 0.0008])
    qs = [f"{2000 + k // 4}-{('03-31', '06-30', '09-30', '12-31')[k % 4]}" for k in range(8)]
    with pytest.raises(ValueError, match="identity link"):
        rv_sat.fit_satellite(rates, np.arange(8.0).reshape(-1, 1), ["real_gdp_growth"], [0], 0, "probit", qs, qs[0], qs[-1])
    ok = rv_sat.fit_satellite(rates, np.arange(8.0).reshape(-1, 1), ["real_gdp_growth"], [0], 0, "identity", qs, qs[0], qs[-1])
    assert ok.link == "identity" and ok.n_obs == 8


def test_adversarial_an_eba_workbook_without_the_us_row_is_refused(tmp_path: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet, title in (("GDP", "Real GDP"), ("Unemployment", "Unemployment rate"), ("Long-term rates", "Long-term interest rates")):
        ws = wb.create_sheet(sheet)
        ws.append([])
        ws.append([None, title])
        ws.append([])
        ws.append([])
        ws.append([None, None, None, 2024, 2025, 2026, 2027, 2025, 2026, 2027])
        ws.append([None, "Belgium", "BE", *([1.0] * 7)])
    wb.save(tmp_path / "w.xlsx")
    with pytest.raises(eba.EbaReaderError, match="US"):
        eba.read_workbook(tmp_path / "w.xlsx")


def test_adversarial_an_ngfs_variable_with_the_wrong_unit_is_not_read(tmp_path: Path) -> None:
    folder = tmp_path / "raw" / fetch.NGFS_DIR
    folder.mkdir(parents=True)
    rows = [{"runId": 137, "model": "m", "scenario": "Baseline", "version": 2, "region": fetch.NGFS_REGION, "variable": "Unemployment rate ; %", "unit": "%",
             "year": 2030, "value": 4.0}]
    (folder / fetch.ngfs_name(137)).write_text(json.dumps(rows))
    (folder / fetch.ngfs_name(140)).write_text(json.dumps([dict(rows[0], runId=140, scenario="Delayed transition", variable="Unemployment rate ; %(combined)",
                                                                  unit="Abs. difference ")]))
    with pytest.raises(ngfs.NgfsReaderError, match="no value"):
        ngfs.read_runs(tmp_path)


def test_adversarial_an_eur_series_with_no_value_before_the_as_of_date_is_refused(tmp_path: Path) -> None:
    folder = tmp_path / "raw" / fetch.FX_DIR
    folder.mkdir(parents=True)
    body = json.dumps({"Codigo": 0, "Series": {"seriesId": P.FX_SERIES, "descripEsp": "x", "descripIng": "x",
                                               "Obs": [{"indexDateString": "01-09-2026", "value": "1100.0", "statusCode": "OK"}]}}).encode("latin-1")
    (folder / bcch.file_name(P.FX_SERIES, P.FX_FIRST, P.FX_LAST)).write_bytes(body)
    with pytest.raises(ValueError, match="no value on or before"):
        fx.read_rate(tmp_path)


# ------------------------------------------------------------------------------------------------ the documents


def test_adversarial_a_fit_window_that_reaches_2020_is_refused_by_the_schema() -> None:
    m = models()
    m["fit"]["satellites"][0]["sample_window"]["end"] = "2020-03-31"
    with pytest.raises(SchemaViolation):
        validate_document("data/derived/C18/models-banco-andino.json", m)
    m = models()
    m["fit"]["satellites"][2]["sample_window"]["start"] = "1985-03-31"           # a real estate window started before the Board's series
    assert any("first quarter the Board publishes" in x for x in semantics().violations(m))


def test_adversarial_a_backcast_that_overlaps_its_fit_is_an_error_row() -> None:
    qs = ["2020-03-31", "2020-06-30", "2020-09-30"]
    t = rv_vs.satellite_backcast(np.array([0.01, 0.02, 0.01]), np.array([0.01, 0.02, 0.01]), qs, "2020-06-30")
    assert t.light == "error"


def test_adversarial_a_path_vintage_after_the_as_of_date_is_refused() -> None:
    d = doc("baseline")
    d["outputs"]["scenario"]["vintage_date"] = "2026-09-15"
    assert any("postdates the observation date" in x for x in semantics().violations(d))


def test_adversarial_an_ec_that_is_not_var_less_el_and_a_marginal_at_99_are_found() -> None:
    d = doc("baseline")
    d["outputs"]["aggregation"]["marginals"][0]["ec_clp_m"] *= 1.1
    assert any("is not var - el" in x for x in semantics().violations(d))
    t = rv_va.horizon_confidence_consistency([1, 1, 1, 1], [0.999, 0.99, 0.999, 0.999])
    assert t.light == "red" and t.statistic == 1


def test_adversarial_a_changed_market_scaling_is_found() -> None:
    m = models()
    m["fit"]["named_parameters"]["market_horizon_scaling"]["horizon_factor"]["value"] = 1.0
    assert any("horizon factor" in x for x in semantics().violations(m))


def test_adversarial_a_headline_that_is_not_the_simple_sum_is_found() -> None:
    d = doc(FED_V)
    d["outputs"]["aggregation"]["headline"]["capital_clp_m"] = next(r for r in d["outputs"]["aggregation"]["band"] if r["method"] == "gaussian-copula")["capital_clp_m"]
    assert any("is not the simple sum" in x for x in semantics().violations(d))


def test_adversarial_an_euler_contribution_moved_and_a_non_psd_matrix_are_found() -> None:
    d = doc("t-copula-baseline")
    d["outputs"]["aggregation"]["euler"]["allocation"][0]["contribution_clp_m"] *= 1.2
    assert any("Euler contributions add up" in x or "euler" in x.lower() for x in semantics().violations(d))
    d = doc("t-copula-baseline")
    d["outputs"]["aggregation"]["correlation"]["matrix"][0][1] = d["outputs"]["aggregation"]["correlation"]["matrix"][1][0] = 0.99
    d["outputs"]["aggregation"]["correlation"]["matrix"][0][2] = d["outputs"]["aggregation"]["correlation"]["matrix"][2][0] = -0.99
    d["outputs"]["aggregation"]["correlation"]["matrix"][1][2] = d["outputs"]["aggregation"]["correlation"]["matrix"][2][1] = 0.99
    assert any("not positive semi-definite" in x for x in semantics().violations(d))


def test_adversarial_a_c_p2_below_the_requirement_and_a_cet1_with_revenue_are_found() -> None:
    d = doc(FED_V)
    d["outputs"]["headline_cet1"]["rows"][0]["cet1_clp_m"] += 50_000.0
    assert any("loss-only depletion" in x for x in semantics().violations(d))
    m = models()
    m["fit"]["named_parameters"]["c_p2"]["value"] = 0.0001
    assert any("c_P2 is below" in x for x in semantics().violations(m))


def test_adversarial_annex3_row_7_2_taken_from_c_p2_is_found() -> None:
    docs = docset()
    for r in docs["fed"]["outputs"]["annex3"]["rows"]:
        if r["row_id"] == "7.2":
            r["a"]["value"] = docs["fed"]["outputs"]["internal_capital_target"]["c_p2"]["value"]
    found = semantics().cross_violations(docs) + semantics().violations(docs["fed"])
    assert any("7.2" in x or "row 7" in x for x in found)


def test_adversarial_a_reverse_solution_that_misses_the_threshold_is_found() -> None:
    d = doc("reverse-stress")
    d["outputs"]["solution"]["loss_at_z_star_clp_m"] *= 1.01
    assert any("tolerance" in x or "relative_gap" in x for x in semantics().violations(d))
    d = doc("reverse-stress")
    d["outputs"]["starts"][0]["distance"] = d["outputs"]["solution"]["mahalanobis_distance"] * 0.5
    assert any("closer point" in x for x in semantics().violations(d))


def test_adversarial_a_document_changed_after_hashing_is_found(tmp_path: Path) -> None:
    sums = dict(line.split("  ")[::-1] for line in (C18 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    p = tmp_path / "baseline.json"
    p.write_bytes((C18 / "baseline.json").read_bytes() + b" ")
    assert hashlib.sha256(p.read_bytes()).hexdigest() != sums["C18/baseline.json"]
    d = doc("baseline")
    d["outputs"]["bank"]["synthetic"] = False
    with pytest.raises(SchemaViolation):
        validate_document("data/derived/C18/baseline.json", d)


# ------------------------------------------------------------------------------------------------ the bake


@requires_raw
def test_adversarial_a_changed_fed_byte_stops_the_whole_case(tmp_path: Path) -> None:
    for f in (fetch.FED_HIST_DIR, fetch.CHARGEOFF_DIR, fetch.FX_DIR):
        shutil.copytree(Path(data_root()) / "raw" / f, tmp_path / "raw" / f)
    victim = tmp_path / "raw" / fetch.FED_HIST_DIR / sba.FED_BASELINE
    victim.write_bytes(victim.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="differs from its provenance record"):
        bake.build(SEED, tmp_path, n_draws=SMALL_DRAWS, n_paths=SMALL_PATHS)


def test_adversarial_the_bcch_provenance_never_records_the_account(tmp_path: Path) -> None:
    body = json.dumps({"Codigo": 0, "Series": {"seriesId": P.FX_SERIES, "descripEsp": "x", "descripIng": "x", "Obs": []}}).encode("latin-1")
    rows = fetch.fetch_fx(tmp_path, "someuser", "somesecret", "2026-10-19", transport=lambda url: body)
    side = (tmp_path / "raw" / fetch.FX_DIR / fetch.PROVENANCE).read_text(encoding="utf-8")
    assert "someuser" not in side and "somesecret" not in side and "pass=" not in rows[0]["url"]


@requires_raw
def test_adversarial_another_seed_changes_the_simulated_blocks(built) -> None:
    other = bake.build(SEED + 1, data_root(), n_draws=SMALL_DRAWS, n_paths=SMALL_PATHS)
    a = built.variants["t-copula-baseline"]["outputs"]["aggregation"]["band"]
    b = other.variants["t-copula-baseline"]["outputs"]["aggregation"]["band"]
    assert a != b


def test_adversarial_a_quantile_restated_in_the_package_is_found(tmp_path: Path) -> None:
    import test_c18_engine_calls as ec

    src = tmp_path / "planted.py"
    src.write_text("import numpy as np\n\ndef f(x):\n    return np.quantile(x, 0.999)\n", encoding="utf-8")
    assert [(n, ln) for n, ln in ec._calls(src) if n in ec.FORBIDDEN_CALLS] == [("quantile", 4)]


def test_adversarial_an_edited_results_block_is_found() -> None:
    text = (ROOT / "docs" / "cases" / "C18.md").read_text(encoding="utf-8")
    got = text.split(page.BEGIN, 1)[1].split(page.END, 1)[0].strip("\n")
    variants = {v: json.loads((C18 / f"{v}.json").read_text(encoding="utf-8")) for v in ("baseline", "eba-2025-adverse", FED_V, "ngfs-delayed-transition",
                                                                                         "t-copula-baseline", "reverse-stress")}
    want = page.results_block(variants, models()).strip("\n")
    assert got == want
    first = next(tok for tok in want.split() if tok.replace(",", "").isdigit())
    assert got.replace(first, str(int(first.replace(",", "")) + 1), 1) != want


def test_adversarial_a_reverse_stress_in_excess_of_the_baseline_text_and_a_failing_ppnr_baseline_are_refused() -> None:
    from pipeline.cases.c18 import reverse

    d = doc("reverse-stress")
    text = d["outputs"]["loss_model"]["description"]["en"]
    assert "PPNR" in text and "excess" not in text.lower()
    with pytest.raises(reverse.NotEvaluated):
        reverse.check_baseline(150_000.0, 145_000.0)


def test_adversarial_a_constant_nii_in_the_ppnr_row_is_found() -> None:
    from test_c18_nii import _expected_nii

    from pipeline.cases.c18 import anchors as anc

    class C:
        anchors = anc.load_anchors()

    d = doc(FED_V)
    want, _ = _expected_nii(C, d)
    rows = d["outputs"]["headline_cet1"]["ppnr"]["rows"]
    assert [r["nii_clp_m"] for r in rows] == pytest.approx(want)
    constant = C.anchors.c15["thresholds"]["net_interest_and_indexation_margin_12m"]
    assert any(abs(r["nii_clp_m"] - constant) > 1.0 for r in rows)                      # a constant margin would differ from the rate path
    rows[0]["nii_clp_m"] = constant
    assert [r["nii_clp_m"] for r in rows] != pytest.approx(want)


def test_adversarial_a_headline_without_the_backcast_statement_is_found() -> None:
    d = doc(FED_V)
    head = next(f for f in d["findings"] if f["id"] == "headline-simple-sum")
    assert "fail their own" in head["title"]["en"] and "UNVERIFIED" in d["outputs"]["capital_start"]["basis"]["en"]
    head["title"]["en"] = head["title"]["en"].split(" The stressed")[0]
    d["outputs"]["capital_start"]["basis"]["en"] = d["outputs"]["capital_start"]["basis"]["en"].replace("UNVERIFIED", "")
    assert "fail their own" not in head["title"]["en"] and "UNVERIFIED" not in d["outputs"]["capital_start"]["basis"]["en"]


def test_adversarial_the_granularity_rule_picks_the_larger_count_beyond_two_standard_errors() -> None:
    from pipeline.cases.c18 import marginals

    lo = {"names": 400, "seed": 1, "var": 100.0, "es": 130.0, "var_se": 1.0, "es_se": 1.0}
    hi = dict(lo, names=1600, var=103.1, es=130.5)
    g = marginals.granularity_choice(lo, hi)
    assert g["exceeds_two_se"] and g["names_used"] == 1600
    near = marginals.granularity_choice(lo, dict(hi, var=101.0, es=130.5))
    assert not near["exceeds_two_se"] and near["names_used"] == 400
