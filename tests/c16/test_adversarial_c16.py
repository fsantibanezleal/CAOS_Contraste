"""The adversarial checks of C16 (docs/design/features/c16/validation.md): each test plants one defect and asserts that the gate it
names refuses it. The plants are made on the documents of the committed samples, so they run wherever the suite runs."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from .helpers import (DATA, ROOT, built_sample, engine_findings, listing_findings, mutated, problems, sample_inputs, sample_report,
                      sample_reports, semantics)


def _doc(name: str):
    b = built_sample(True)
    return mutated({**b.variants, "reverse-stress": b.reverse, "models": b.models}[name])


def _refuses(doc, fragment: str, name: str = "x") -> None:
    found = problems(doc, name)
    assert any(fragment in f for f in found), f"{fragment!r} not found in {found[:5]}"


def test_adversarial_a_later_report_is_never_returned_and_a_missing_date_is_refused(tmp_path):
    from pipeline.io import fdic

    d = json.loads((DATA / "financials-sample.json").read_text(encoding="utf-8"))
    late = json.loads(json.dumps(d["data"][-1]))
    late["data"]["REPDTE"] = "20230331"
    late["data"]["DEP"] = 1
    d["data"].append(late)
    (tmp_path / "f.json").write_text(json.dumps(d), encoding="utf-8")
    reports = fdic.read_financials(tmp_path / "f.json", 24735)
    assert reports[-1].report_date == "2023-03-31"
    assert all(r.report_date <= "2022-12-31" for r in fdic.up_to(reports, "2022-12-31"))
    assert fdic.report_at(reports, "2022-12-31").get("DEP") > 1
    with pytest.raises(ValueError):
        fdic.report_at(reports, "2022-12-30")


def test_adversarial_a_page_of_another_table_or_adjustment_is_refused():
    from pipeline.cases.c16 import h8

    text = (DATA / "h8-sample-20230317.html").read_text(encoding="utf-8")
    with pytest.raises(h8.H8Error, match="title"):
        h8.weekly_series(h8.parse_release(text.replace("Large Domestically Chartered", "Small Domestically Chartered"), "2023-03-17"), 6, "Deposits")
    with pytest.raises(h8.H8Error, match="seasonally adjusted"):
        h8.weekly_series(h8.parse_release(text.replace("Seasonally adjusted, billions", "Not seasonally adjusted, billions", 1), "2023-03-17"), 6, "Deposits")
    with pytest.raises(h8.H8Error, match="billions"):
        h8.weekly_series(h8.parse_release(text.replace("billions of dollars", "millions of dollars", 1), "2023-03-17"), 6, "Deposits")


def test_adversarial_a_changed_raw_file_or_a_lost_sidecar_is_refused(tmp_path):
    from pipeline.cases.c16 import fetch

    def fake(url: str, timeout: float = 90.0) -> bytes:
        return json.dumps({"data": [], "url": url}).encode() if "fdic" in url else b"<html></html>"

    (tmp_path / "raw" / fetch.TREASURY_DIR).mkdir(parents=True)
    t = tmp_path / "raw" / fetch.TREASURY_DIR / "daily-treasury-par-2022.csv"
    t.write_text("Date\n", encoding="utf-8")
    (tmp_path / "raw" / fetch.TREASURY_DIR / "provenance.json").write_text(json.dumps([fetch.describe(t, "https://example.test", "2026-10-19")]))
    fetch.fetch(tmp_path, today="2026-10-19", download=fake, releases=("20230317",))
    side = tmp_path / "raw" / fetch.FDIC_DIR / fetch.PROVENANCE
    rows = json.loads(side.read_text(encoding="utf-8"))
    rows[0]["sha256"] = "0" * 64
    side.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="differs from its provenance record"):
        fetch.load_provenance(tmp_path)
    side.unlink()
    with pytest.raises(FileNotFoundError, match="not fetched"):
        fetch.load_provenance(tmp_path)


def test_adversarial_an_uninsured_share_on_the_wrong_denominator_is_refused():
    doc = _doc("list-adverse")
    d = doc["outputs"]["balance_sheet"]["deposits"]
    d["uninsured_share_of_depdom"] = d["uninsured_share_of_dep"]
    _refuses(doc, "uninsured_share_of_depdom is not DEPUNA over DEPDOM")
    doc = _doc("list-adverse")
    doc["outputs"]["balance_sheet"]["deposits"]["denominators"]["insured_uninsured"] = "DEP"
    assert schema_refuses(doc)


def schema_refuses(doc) -> bool:
    from .helpers import schema_errors

    return bool(schema_errors(doc))


def test_adversarial_a_mapping_band_ratio_not_recomputed_from_the_central_row_is_refused():
    doc = _doc("lcr-standard")
    doc["outputs"]["lcr"]["mapping_sensitivity"][1]["ratio"] = 99.0
    _refuses(doc, "the ratio is not HQLA over net outflows")
    doc = _doc("lcr-standard")
    doc["outputs"]["lcr"]["mapping_sensitivity"] = [r for r in doc["outputs"]["lcr"]["mapping_sensitivity"] if r["lcr_category"] != "operational"]
    assert problems(doc)


def test_adversarial_a_pledged_class_that_keeps_its_securities_in_the_cbc_is_refused():
    doc = _doc("list-adverse")
    cls = next(c for c in doc["outputs"]["cbc"]["classes"] if c["class_id"] == "treasury")
    cls["encumbered"] = 0.0
    _refuses(doc, "liquidity_value is not (value used - encumbered)")
    doc = _doc("htm-losses")
    cls = next(c for c in doc["outputs"]["cbc"]["classes"] if c["class_id"] == "treasury")
    cls["fair_value"] = cls["carrying_value"]
    _refuses(doc, "the fair value is not the carrying value with the reported HTM loss")


def test_adversarial_an_item_with_a_number_and_a_reason_is_refused():
    doc = _doc("list-adverse")
    item = next(i for i in doc["outputs"]["balance_sheet"]["items"] if i["item_id"] == "other-assets")
    item["reported_amount"] = 5.0
    assert schema_refuses(doc) and any("reported_amount and reason_missing disagree" in f for f in semantics.check_document(doc))


def test_adversarial_a_ladder_number_computed_elsewhere_is_found_by_the_engine_call_check():
    doc = _doc("list-adverse")
    assert engine_findings(doc) == []
    doc["outputs"]["path"]["ladder"]["segments"][1]["outflows"][3] += 1000.0
    assert any("outflows are not the engine's" in f for f in engine_findings(doc))
    doc = _doc("list-adverse")
    doc["outputs"]["path"]["ladder"]["nlp"][10] += 1.0
    assert any("the NLP is not the engine's" in f for f in engine_findings(doc))
    _refuses(doc, "breaks NLP = CBC - cumulative net outflow")


def test_adversarial_the_product_holds_no_liquidity_formula():
    src = ROOT / "data-pipeline" / "pipeline" / "cases" / "c16"
    banned = re.compile(r"cumprod|brentq|\(1(\.0)? - [A-Za-z_]+\) \*\*|1(\.0)? - \(1(\.0)? - |np\.min\(.*nlp|\.argmax\(.*nlp")
    assert {p.name for p in src.glob("*.py")} >= {"bake.py", "variant.py", "balance.py", "h8.py", "fetch.py"}
    hits = [f"{p.name}:{n}: {line.strip()}" for p in sorted(src.glob("*.py")) for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if banned.search(line) and not line.lstrip().startswith("#")]
    assert hits == []


def test_adversarial_a_calibration_that_takes_a_2023_row_is_refused():
    from riskvalidation.liquidity import runoff, scenarios

    from pipeline.cases.c16 import models

    svb = next(r for r in runoff.TABLE_A1 if r.row_id == "svb-2023")
    with pytest.raises(ValueError, match="2023"):
        scenarios.fast_run_scenario([svb], scored=True)
    with pytest.raises(ValueError, match="2023"):
        models.calibration([r for r in runoff.TABLE_A1 if r.year < 2023] + [svb], "maximum-implied-daily-rate")
    doc = _doc("models")
    doc["fit"]["calibration"]["fitted_daily_rate"]["value"] = 0.612702
    _refuses(doc, "the fitted daily rate is not the maximum-implied-daily-rate")


def test_adversarial_a_survival_day_beyond_the_horizon_or_with_a_positive_nlp_is_refused():
    doc = _doc("list-adverse")
    doc["outputs"]["path"]["survival"] = {"kind": "day", "day": 400, "horizon_days": 125}
    _refuses(doc, "survival is not the first day on which the NLP turns negative")
    doc = _doc("list-adverse")
    nlp = doc["outputs"]["path"]["ladder"]["nlp"]
    if min(nlp) >= 0:
        doc["outputs"]["path"]["survival"] = {"kind": "day", "day": 5, "horizon_days": 125}
    else:
        doc["outputs"]["path"]["survival"] = {"kind": "survives-horizon", "day": None, "horizon_days": 125}
    _refuses(doc, "survival is")


def test_adversarial_an_lcr_presented_as_the_reported_one_is_refused():
    doc = _doc("lcr-standard")
    doc["outputs"]["lcr"]["reported_or_regulatory"] = True
    assert schema_refuses(doc)
    doc = _doc("lcr-standard")
    doc["outputs"]["lcr"]["label"] = "reported-lcr"
    assert schema_refuses(doc)
    doc = _doc("lcr-standard")
    doc["outputs"]["lcr"]["ratio"] *= 1.5
    _refuses(doc, "LCR ratio is not HQLA over net outflows")


def test_adversarial_an_empty_stock_is_never_a_zero_share():
    from riskvalidation.regulatory import lcr_nsfr

    from pipeline.cases.c16 import variant

    block = variant.hqla_block(0.0, 0.0, 0.0)
    assert block["l2_share"] is None and block["l2b_share"] is None and block["l2_share"] != 0.0
    with pytest.raises(ValueError):
        lcr_nsfr.lcr_ratio(block["hqla"], 0.0)    # an LCR over no net outflow is refused by the engine, never infinite or zero


def test_adversarial_a_solved_multiplier_that_does_not_reach_the_target_is_refused():
    doc = _doc("reverse-stress")
    b = next(x for x in doc["outputs"]["bases"] if x["solved"]["status"] == "solved")
    target = doc["outputs"]["target"]["days"]
    b["solved"]["survival_at_multiplier"] = target + 1
    b["solved"]["round_trip_error"] = 1
    _refuses(doc, "the survival at the solved multiplier is above the target")
    doc = _doc("reverse-stress")
    b = next(x for x in doc["outputs"]["bases"] if x["solved"]["status"] == "solved")
    b["solved"]["multiplier"] = b["max_multiplier"]
    _refuses(doc, "the solved multiplier is above the first curve point at the target")


def test_adversarial_an_htm_cbc_without_the_loss_is_refused():
    doc = _doc("htm-losses")
    doc["outputs"]["htm"]["cbc_with_loss"] = doc["outputs"]["htm"]["cbc_without_loss"]
    doc["outputs"]["htm"]["cbc_removed"] = 0.0
    _refuses(doc, "htm cbc_with_loss is not the CBC of the fair-value basis")
    doc = _doc("htm-losses")
    doc["outputs"]["htm"]["revaluation"]["difference"] += 1.0
    _refuses(doc, "the revaluation difference is not model minus reported")


def test_adversarial_a_document_changed_after_hashing_is_found(tmp_path):
    from pipeline.cases.c16 import bake

    bake.write_documents(tmp_path, built_sample(True))
    assert listing_findings(tmp_path) == []
    victim = tmp_path / "C16" / "list-adverse.json"
    victim.write_bytes(victim.read_bytes().replace(b"synthetic", b"syntheti_", 1))
    assert any("list-adverse.json" in f for f in listing_findings(tmp_path))


def test_adversarial_a_call_report_after_the_valuation_date_is_refused():
    doc = _doc("list-adverse")
    doc["outputs"]["data"]["call_reports"].append({"report_date": "2023-03-31", "source": "x", "fields": ["DEP"]})
    _refuses(doc, "a call report is dated after the valuation date")
    doc = _doc("list-adverse")
    doc["outputs"]["time_block"][0]["report_date"] = "2023-03-31"
    _refuses(doc, "report date or as_of after the valuation date")


def test_adversarial_a_score_with_the_wrong_denominator_or_light_is_refused():
    doc = _doc("fast-run")
    den = doc["outputs"]["scoring"]["denominators"][1]
    den["light"] = "green" if den["light"] != "green" else "red"
    _refuses(doc, "the light breaks the scoring_ratio conventions")
    doc = _doc("fast-run")
    doc["outputs"]["scoring"]["denominators"][1]["denominator_amount"] = doc["outputs"]["balance_sheet"]["deposits"]["depdom"]
    _refuses(doc, "the call-report denominator is not DEP")
    doc = _doc("fast-run")
    doc["outputs"]["scoring"]["svb_anchor"]["forecast_claim"] = True
    assert schema_refuses(doc)


def test_adversarial_a_time_block_after_the_valuation_date_or_without_its_survival_is_refused():
    doc = _doc("list-adverse")
    doc["outputs"]["time_block"][1]["survival"] = None
    _refuses(doc, "survival and the daily path disagree")
    doc = _doc("list-adverse")
    doc["outputs"]["aggregate_record"] = None
    doc["outputs"]["aggregate_record_reason"] = None
    from pipeline.cases.c16 import bake

    assert any("aggregate record" in f for f in bake.extra_findings(doc))
    doc = _doc("list-adverse")
    doc["outputs"]["time_block"] = doc["outputs"]["time_block"][:1]
    assert any("time block" in f for f in bake.extra_findings(doc))


def test_adversarial_a_generator_truth_that_is_not_its_recursion_is_refused():
    doc = _doc("models")
    doc["fit"]["generator"]["truth"][0]["true_outflow_rate"] /= 2
    _refuses(doc, "is not the transfer recursion of its configuration")
    doc = _doc("models")
    doc["fit"]["generator"]["verification"]["within_error"] = not doc["fit"]["generator"]["verification"]["within_error"]
    _refuses(doc, "within_error does not follow max_abs_error")


def test_adversarial_another_seed_changes_the_generator_block_so_the_determinism_test_is_not_vacuous():
    from pipeline.cases.c16 import bake

    a = bake.build(42, sample_inputs(), n_draws=150, only=("fast-run",))
    b = bake.build(43, sample_inputs(), n_draws=150, only=("fast-run",))
    assert a.models["fit"]["generator"]["verification"] != b.models["fit"]["generator"]["verification"]


def test_adversarial_an_edited_results_block_is_found():
    from pipeline.cases.c16 import page

    from .helpers import committed_documents

    docs = list(committed_documents().values())
    text = (ROOT / "docs" / "cases" / "C16.md").read_text(encoding="utf-8")
    assert page.findings(text, *docs) == []
    assert page.findings(text.replace("survives", "survived", 1), *docs) != []


def test_adversarial_a_rebake_that_differs_by_one_byte_is_found(tmp_path):
    from pipeline.cases.c16 import bake

    a, b = tmp_path / "a", tmp_path / "b"
    bake.write_documents(a, built_sample(True))
    shutil.copytree(a, b)
    assert bake.differences(a, b) == []
    f = b / "C16" / "fast-run.json"
    f.write_bytes(f.read_bytes() + b" ")
    assert bake.differences(a, b) == ["C16/fast-run.json"]
    assert np.isfinite(0.0) and Path(__file__).exists() and sample_report() and sample_reports()
