"""CT-1616 to CT-1620: the documents the bake writes (producer test of ``c16-outputs``, ``c16-outputs-reverse`` and ``c16-models``),
as committed under ``data/derived/C16``. No test bakes the real data (ADR-0074); the bake runs where the device data root holds
the raw files."""
from __future__ import annotations

import json
import re

import pytest

from .helpers import (C16, MANIFEST, ROOT, MODELS, REVERSE, VARIANTS, VD, committed, committed_documents, problems, semantics, sha)


def _scenarios():
    return {v: committed(v) for v in VARIANTS}


def engine_pin() -> str:
    """The commit the product pins the engine by (data-pipeline/requirements.txt): the documents name the engine as ``<version>+<its first seven>``."""
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    return re.search(r"^riskvalidation\S* @ git\+\S+@([0-9a-f]{40})\s*$", req, re.M).group(1)


def test_every_committed_document_validates_and_is_listed_with_its_hash():
    docs = committed_documents()
    assert len(docs) == 7
    for name, doc in docs.items():
        found = problems(doc, name)
        assert found == [], (name, found[:5])
        assert doc["case_id"] == "C16"
    allv = list(docs.values())
    assert semantics.check_conventions_agree(allv) == [] and semantics.check_cross_document(allv) == []
    for v, doc in _scenarios().items():
        bank = doc["outputs"]["bank"]
        assert (bank["aggregates"], bank["behaviour"], bank["deposits"], bank["cert"]) == ("real", "synthetic", "synthetic", 24735)
        assert "does not represent the bank" in bank["notice"]["en"] and doc["outputs"]["valuation_date"] == VD
        assert doc["variant_id"] == v and doc["provenance"]["truth_status"] == "synthetic-calibrated"
        assert doc["provenance"]["inputs"] and doc["provenance"]["riskvalidation_version"]
    # the manifest lists each document with its size, and the checksum file holds each digest
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {a["path"]: a for a in manifest["artifacts"]}
    assert set(entries) == {f"C16/{n}.json" for n in docs}
    sums = {line.split("  ")[1]: line.split("  ")[0] for line in (C16 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()}
    for rel, entry in entries.items():
        assert entry["bytes"] == (C16.parent / rel).stat().st_size and sums[rel] == sha(C16.parent / rel)
        assert (entry["role"], entry["lane"]) in {("variant", "precompute"), ("models", "precompute")}
    assert sums["C16/raw-sources.txt"] == sha(C16 / "raw-sources.txt")
    raw = json.loads((C16 / "raw-sources.txt").read_text(encoding="utf-8"))
    for sid in ("fdic-bankfind", "fed-h8", "treasury-par-curve"):
        for f in raw["sources"][sid]["files"]:
            assert f["url"].startswith("https://") and f["bytes"] > 0 and len(f["sha256"]) == 64 and f["retrieved"]
    assert manifest["default_variant"] in {a["variant_id"] for a in manifest["artifacts"]} and manifest["engine"]["riskvalidation"].endswith(engine_pin()[:7])


def test_no_value_is_dated_after_its_valuation_date():
    for v, doc in _scenarios().items():
        o = doc["outputs"]
        assert o["data"]["read_up_to_valuation_date"] is True and o["data"]["data_cutoff"] <= o["valuation_date"]
        assert all(r["report_date"] <= o["valuation_date"] for r in o["data"]["call_reports"]), v
        for t in o["time_block"]:
            assert t["report_date"] <= t["as_of"] < o["valuation_date"], (v, t["as_of"])
        # the dates of the ladder start after the valuation date: they are the horizon, not data
        if o["path"] is not None:
            assert o["path"]["ladder"]["dates"][0] > o["valuation_date"]
    # a call report dated after the valuation date added to the inputs changes nothing
    from pipeline.cases.c16 import bake
    from pipeline.io.fdic import Report

    from .helpers import sample_inputs

    base = sample_inputs()
    later = sample_inputs()
    last = later.reports[-1]
    late = dict(last.values)
    late.update({"REPDTE": "20230331", "DEP": 1.0, "DEPUNA": 1.0, "DEPINS": 1.0, "SCHF": 1.0, "SCPLEDGE": 1.0})
    later.reports = [*later.reports, Report("2023-03-31", late)]
    a = bake.build(42, base, n_draws=50, only=("list-adverse", "lcr-standard"))
    b = bake.build(42, later, n_draws=50, only=("list-adverse", "lcr-standard"))
    assert json.dumps(a.variants, sort_keys=True) == json.dumps(b.variants, sort_keys=True)
    for doc in b.variants.values():
        assert max(r["report_date"] for r in doc["outputs"]["data"]["call_reports"]) == "2022-12-31"


def test_the_scoring_states_both_denominators_and_the_svb_anchor():
    from riskvalidation.liquidity import runoff

    for v, doc in _scenarios().items():
        o = doc["outputs"]
        sc, conv, dep = o["scoring"], o["conventions"], o["balance_sheet"]["deposits"]
        board, call = sc["denominators"]
        assert (board["id"], call["id"]) == ("board-stated-share", "call-report-dep")
        assert board["realised_share"] == 0.85 and call["denominator_amount"] == dep["dep"] and call["realised_amount"] == 140_000_000
        assert call["realised_share"] == pytest.approx(140_000_000 / dep["dep"], rel=1e-9) and call["realised_share"] < board["realised_share"]
        for d in (board, call):
            assert d["ratio"] == pytest.approx(d["modelled_share"] / d["realised_share"], rel=1e-9)
            assert d["shortfall"] == pytest.approx(d["realised_share"] - d["modelled_share"], abs=1e-9)
            want = ("green" if d["ratio"] >= conv["scoring_ratio_green"]["value"] else
                    "amber" if d["ratio"] >= conv["scoring_ratio_amber"]["value"] else "red")
            assert d["light"] == want and d["compared_at"] == ("model-horizon" if v == "lcr-standard" else "event-horizon")
            assert d["source"]
        a = sc["svb_anchor"]
        assert a["forecast_claim"] is False and a["outflow_share"] == 0.85 and a["days"] == 2
        assert a["implied_daily_rate"] == pytest.approx(0.612702, abs=5e-7) and "anchor" in a["label"]["en"].lower()
        rows = {r["row_id"]: r for r in sc["table_a1_scoring"]}
        assert set(rows) == {r.row_id for r in runoff.TABLE_A1}
        for r in rows.values():
            assert (r["modelled_share"] is None) == (r["reason"] is not None)
            if r["modelled_share"] is not None:
                assert r["error"] == pytest.approx(r["observed_share"] - r["modelled_share"], abs=1e-9)
        assert sc["event"]["event_date"] == "2023-03-10" and "Federal Reserve" in sc["event"]["source"]
    # the LCR has one 30-day aggregate: no outflow at the 2-day horizon, the comparison at the model's own horizon
    lcr = committed("lcr-standard")["outputs"]["scoring"]["modelled_outflow"]
    assert lcr["at_event_horizon"] is None and lcr["at_event_horizon_reason"]["en"] and lcr["at_model_horizon"]["horizon_days"] == 30
    fast = committed("fast-run")["outputs"]["scoring"]
    assert {r["role"] for r in fast["table_a1_scoring"]} == {"calibration", "scored"}
    assert {r["role"] for r in committed("list-adverse")["outputs"]["scoring"]["table_a1_scoring"]} == {"reference"}


def test_every_scenario_document_carries_the_time_block_and_its_labels():
    from pipeline.cases.c16 import balance

    from .helpers import sample_reports

    reports = {r.report_date: r for r in sample_reports()}
    for v, doc in _scenarios().items():
        o = doc["outputs"]
        assert [t["as_of"] for t in o["time_block"]] == ["2021-12-31", "2022-06-30"], v
        for t in o["time_block"]:
            assert t["deposits"] == balance.deposits_block(reports[t["report_date"]])
            assert t["htm_unrealised_loss"] < 0 and t["cbc_fair_value_basis"] < t["cbc_amortised_basis"]
            if v == "lcr-standard":
                assert t["survival"] is None and t["lcr_ratio"] > 0
            else:
                assert t["survival"]["horizon_days"] == o["variant"]["horizon_days"] and t["lcr_ratio"] is None
        # the htm loss grew over the block: the loss of 2022-12-31 is larger than those of the two earlier dates
        loss = o["htm"]["reported"]["htm_unrealised"] if o["htm"] else None
        if loss is not None:
            assert loss < o["time_block"][1]["htm_unrealised_loss"] < o["time_block"][0]["htm_unrealised_loss"] < 0
        for name, c in o["conventions"].items():
            assert c["status"] == "convention" or name in ("variant_scenarios",) or c.get("status") == "convention", name
        assert o["conventions"]["day_calendar"]["kind"] == "us-business-days"
        rec = o["aggregate_record"]
        assert (rec is None) == (o["aggregate_record_reason"] is not None), v
        if rec is not None:
            assert {s["series_id"] for s in rec["series"]} >= {"h8-deposits-large-domestic", "h8-deposits-small-domestic"}
            for s in rec["series"]:
                assert [p["date"] for p in s["points"]] == sorted(p["date"] for p in s["points"]) and "billions" in s["unit"]
                assert "seasonally adjusted" in s["unit"]
        assert any(a["assumption_id"] == "deposit-mapping" for a in o["balance_sheet"]["assumptions"])
        assert all(a["behaviour"] == "synthetic" for a in o["balance_sheet"]["assumptions"])
        assert doc["impact"]["survival_days"]["label"]["en"] and doc["impact"]["lcr"]["label"]["en"]


def test_the_models_document_repeats_the_engine_tables():
    from riskvalidation.liquidity import runoff

    fit = committed(MODELS)["fit"]
    adverse, extreme = runoff.LIST_PARAMETERS["adverse"], runoff.LIST_PARAMETERS["extreme"]
    for row in fit["list_parameters"]["open_maturity_daily"]:
        assert row["adverse"] == adverse["open_maturity"][row["item"]] and row["extreme"] == extreme["open_maturity"][row["item"]]
    rename = {"derivatives-payable": "derivatives", "derivatives-receivable": "derivatives", "paper-own-portfolio": "own-paper",
              "other-cash-inflows": "other-inflows"}   # the contract's item names where the engine's keys differ
    for row in fit["list_parameters"]["contractual_outflows"]:
        key = rename.get(row["item"], row["item"])
        assert row["baseline"] == runoff.LIST_PARAMETERS["baseline"]["contractual_outflow"][key]
        assert row["adverse"] == adverse["contractual_outflow"][key] and row["extreme"] == extreme["contractual_outflow"][key]
    for row in fit["list_parameters"]["contractual_inflows"]:
        key = rename.get(row["item"], row["item"])
        assert row["adverse"] == adverse["contractual_inflow"][key] and row["extreme"] == extreme["contractual_inflow"][key]
    for row in fit["list_parameters"]["committed_drawdown"]:
        assert row["adverse"] == adverse["drawdown"][row["item"]] and row["extreme"] == extreme["drawdown"][row["item"]]
    rows = {r.row_id: r for r in runoff.TABLE_A1}
    assert {r["row_id"] for r in fit["table_a1"]["rows"]} == set(rows)
    for r in fit["table_a1"]["rows"]:
        assert (r["bank"], r["year"], r["outflow_share"], r["days"]) == (rows[r["row_id"]].bank, rows[r["row_id"]].year, rows[r["row_id"]].outflow_share, rows[r["row_id"]].days)
    assert fit["calibration"]["statement"]["en"] and fit["calibration"]["anchor"]["forecast_claim"] is False
    gen = fit["generator"]
    assert gen["config"]["truth_status"] == "synthetic-known-truth" and gen["config"]["seed"] == 42
    v = gen["verification"]
    assert v["n_draws"] == 20_000 and v["within_error"] is True and v["max_abs_error"] <= 3.0 * v["mc_standard_error"]
    by = {s["segment"]: s for s in gen["config"]["segments"]}
    assert sum(s["share_of_deposits"] for s in by.values()) == pytest.approx(1.0, abs=1e-9)
    for t in gen["truth"]:
        assert t["true_outflow_rate"] == pytest.approx(semantics.generator_truth(by[t["segment"]], t["horizon_days"]), abs=5e-7)
    assert {s["source_id"] for s in fit["sources"]} >= {"fdic-bankfind", "fed-h8", "fed-svb-review", "bcbs-d555-table-a1", "ecb-list-2019"}
    assert all("not legal advice" in s["statement"]["en"] for s in fit["sources"])
    assert (C16 / f"{REVERSE}.json").exists()
