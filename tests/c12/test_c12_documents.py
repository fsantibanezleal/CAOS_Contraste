"""CT-1204, CT-1208 to CT-1210, CT-1212 to CT-1217: the committed C12 documents."""
from __future__ import annotations

from pathlib import Path

import c12_docs as d
import contract_schemas as cs
import numpy as np
import semantics
from scipy.stats import norm

from pipeline.cases.c12 import bake, book, ore


def test_every_committed_document_validates_passes_the_checks_and_is_listed_with_its_hash() -> None:
    files = list(d.C12.iterdir())
    names = sorted([*(f"{v}.json" for v in d.VARIANTS), f"{d.MODELS}.json", "raw-sources.txt", "SHA256SUMS.txt"])
    assert sorted(f.name for f in files) == names
    manifest = d.load(d.DERIVED / "manifests" / "C12.json")
    assert cs.errors("common/case-manifest", manifest) == []
    docs = [f for f in files if f.suffix == ".json"]
    listed = {a["path"]: a for a in manifest["artifacts"]}
    sums = dict(reversed(line.split("  ", 1)) for line in (d.C12 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert set(listed) == {f"C12/{f.name}" for f in docs} and set(sums) == set(listed) | {"C12/raw-sources.txt"}
    for f in docs:
        doc = d.load(f)
        assert d.problems(doc, f) == [], f.name
        assert doc["provenance"]["truth_status"] == "synthetic-calibrated" and doc["case_id"] == "C12"
        assert listed[f"C12/{f.name}"]["bytes"] == f.stat().st_size and sums[f"C12/{f.name}"] == d.sha(f)
    assert sums["C12/raw-sources.txt"] == d.sha(d.C12 / "raw-sources.txt")
    variants = {v: d.variant(v) for v in d.VARIANTS}
    assert semantics.check_c12_variants({"documents": list(variants.values())}) == []
    assert [a["variant_id"] for a in manifest["artifacts"] if a["role"] == "variant"] == list(d.VARIANTS)
    assert semantics.check_c12_models(d.models()) == []


def test_every_named_parameter_is_a_labelled_convention_and_the_six_variants_share_them() -> None:
    docs = {v: d.variant(v)["outputs"] for v in d.VARIANTS}
    first = docs["netting-set"]["named_parameters"]
    assert len(first) == 33 and all(p["label"] == "convention" and p["unit"] for p in first.values())
    for v, o in docs.items():
        assert o["named_parameters"] == first, v
        assert o["named_parameters"]["time_grid_years"]["value"] == o["exposure"]["time_grid_years"]
        assert all(t["label"] == "convention" for t in o["book"]["trades"])
    assert first["wwr_b_grid"]["value"] == [-2.0, 0.0, 1.0, 2.0, 4.0] and first["counterparty_spread"]["value"] == 0.0125
    assert len(docs["single-swap"]["book"]["trades"]) == 1 and len(docs["netting-set"]["book"]["trades"]) == 4


def test_the_initial_margin_variant_is_a_labelled_regression_proxy_in_calendar_days() -> None:
    o = d.variant("with-im")["outputs"]
    im = o["initial_margin"]
    assert im["labelled"] == "regression proxy, not SIMM" and im["simm_used"] is False and "SIMM" in im["limit"]["en"]
    assert abs(im["alpha"] - norm.ppf(im["quantile"])) < 1e-9
    assert im["horizon_calendar_days"] == im["mpor_calendar_days"] == 14 and o["collateral"]["csa"]["mpor_business_days"] == 10
    assert all(e <= b + 1e-9 for e, b in zip(o["exposure"]["ee"]["values"], im["ee_vm_only"]["values"], strict=True))
    assert all(max(b - m, 0.0) - 1e-3 <= e for e, b, m in zip(o["exposure"]["ee"]["values"], im["ee_vm_only"]["values"], im["dim"]["values"], strict=True))
    for v in ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "wrong-way-risk"):
        assert d.variant(v)["outputs"]["initial_margin"] is None


def test_the_nica_of_each_variant_follows_the_cre52_17_definition() -> None:
    text = (d.ROOT / "docs" / "cases" / "C12.md").read_text(encoding="utf-8")
    assert "NICA represents any collateral (segregated or unsegregated) posted by the counterparty less the unsegregated collateral " \
           "posted by the bank" in text and "CRE52.17" in text and "https://www.bis.org/basel_framework/chapter/CRE/52.htm" in text
    for v in d.VARIANTS:
        sa = d.variant(v)["outputs"]["sa_ccr"]
        assert (sa["nica"]["amount"] > 0) == (v == "with-im"), v
    im = d.variant("with-im")["outputs"]["sa_ccr"]
    assert im["rc"]["amount"] >= im["th"]["amount"] + im["mta"]["amount"] - im["nica"]["amount"] - 1e-9


def test_the_wrong_way_sweep_has_b_zero_equal_to_the_independent_cva_and_no_ore_row() -> None:
    o = d.variant("wrong-way-risk")["outputs"]
    w = o["wrong_way_risk"]
    assert [p["b"] for p in w["sweep"]] == [-2.0, 0.0, 1.0, 2.0, 4.0]
    zero = next(p for p in w["sweep"] if p["b"] == 0)
    assert zero["independent"] and zero["cva"]["amount"] == w["independent_cva"]["amount"] == o["cva_dva"]["cva"]["amount"]
    assert w["largest_b_w"] == 4.0 * w["w_max_usd_million"] and all(p["a_calibration_max_error"] <= 1e-10 for p in w["sweep"])
    assert [p["cva"]["amount"] for p in w["sweep"] if p["b"] >= 0] == sorted(p["cva"]["amount"] for p in w["sweep"] if p["b"] >= 0)
    assert o["ore_reconciliation"]["status"] == "not-applicable" and o["ore_reconciliation"]["reason"]["en"]
    for v in d.VARIANTS[:5]:
        assert d.variant(v)["outputs"]["ore_reconciliation"]["status"] == "reconciled", v
        assert d.variant(v)["outputs"]["wrong_way_risk"] is None


def test_the_stress_window_contains_a_rise_of_the_hqm_spread() -> None:
    for v in d.VARIANTS:
        st = d.variant(v)["outputs"]["regulatory_comparison"]["stressed"]
        assert (st["window_start"], st["window_end"]) == ("2007-01-01", "2009-12-31") and st["label"] == "convention"
        assert st["spread_rose"] and st["hqm_spread_peak"] > st["hqm_spread_start"] >= 0 and st["effective_epe"]["amount"] > 0


def test_the_backtest_has_six_horizons_simulated_critical_values_and_secondary_exceedance_rows() -> None:
    doc = d.variant("netting-set")
    bt = doc["outputs"]["backtest"]
    assert bt["window_start"] == "2000-01" and bt["pit_rule"] == "(i + 1) / (N + 2)" and len(bt["dates"]) >= 300
    n_paths = bt["paths_per_date"]
    for blk in (bt["book_horizons"], bt["risk_factor"]["horizons"]):
        assert [h["horizon"] for h in blk] == ["10bd", "20bd", "1m", "3m", "6m", "12m"]
        for h in blk:
            assert h["n"] == len(bt["dates"]) and h["critical_iid"] == {"p05": 2.492, "p01": 3.88}
            assert h["critical_simulated"]["p01"] >= h["critical_simulated"]["p05"] > 0 and 0 < h["effective_sample_size"] <= h["n"]
            assert abs(h["w2"] - semantics.anderson_darling_w2(h["pits"])) < 1e-6 * max(1.0, h["w2"])
            assert all(abs((p * (n_paths + 2)) - round(p * (n_paths + 2))) < 1e-6 for p in h["pits"])
            assert [e["quantile"] for e in h["exceedances"]] == [0.9, 0.95, 0.99]
    assert [w["window"] for w in bt["sub_windows"]] == ["before-2008", "2008-2019", "from-2020"]
    assert bt["sub_windows"][0]["end"] <= "2007-12-31" and bt["sub_windows"][2]["start"] >= "2020-01-01"
    rows = [t for t in doc["tests"] if t["test_id"] == "ccr.pfe_exceedance_backtest"]
    assert len(rows) == 18 and all(t["extras"]["row_role"] == "secondary" and "secondary" in t["notes"] for t in rows)
    pit = [t for t in doc["tests"] if t["test_id"] == "ccr.pit_exposure_backtest"]
    assert len(pit) == 12 and all(t["light"] in {"green", "amber", "red"} and t["extras"]["iid_critical_values"] for t in pit)


def test_the_calibration_sensitivity_moves_a_and_sigma_by_one_standard_error() -> None:
    for v in d.VARIANTS:
        o = d.variant(v)["outputs"]
        cal = o["calibration_used"]
        cs_ = {s["case"]: s for s in o["calibration_sensitivity"]}
        assert set(cs_) == {"base", "a-plus-1se", "a-minus-1se", "sigma-plus-1se", "sigma-minus-1se"}
        assert np.isclose(cs_["a-minus-1se"]["a"], cal["a"] - cal["a_se"]) and np.isclose(cs_["sigma-plus-1se"]["sigma"], cal["sigma"] + cal["sigma_se"])
        assert cs_["base"]["ee"] == o["exposure"]["ee"] and cs_["base"]["pfe"] == o["exposure"]["pfe"]
        assert all(s["pfe_peak"]["amount"] == max(s["pfe"]["values"]) for s in cs_.values())


def test_the_ore_rows_state_version_platform_timing_and_flags_that_follow_the_numbers(tmp_path: Path) -> None:
    for v in d.VARIANTS[:5]:
        r = d.variant(v)["outputs"]["ore_reconciliation"]
        assert r["ore_version"] == "1.8.17.0" and "native (no WSL)" in r["platform"] and r["run_seconds"] > 0
        flags = [a["within_two_se"] for a in r["agreement"]] + [r["eepe_agreement"]["within_two_se"], r["cva_agreement"]["within_two_se"]]
        flags += [a["within_two_se"] for a in (r["dim_agreement"] or [])]
        assert r["all_within_two_se"] == all(flags)
        for a in r["agreement"]:
            assert a["within_two_se"] == (abs(a["difference"]) <= 2 * a["combined_se"] + 1e-12)
        rows = [t for t in d.variant(v)["tests"] if t["test_id"] == "ccr.reconcile_ee_profile"]
        assert rows and rows[0]["light"] in {"green", "red"}
        assert (rows[0]["light"] == "green") == all(a["within_two_se"] for a in r["agreement"])
    # the committed ORE inputs are the inputs the bake regenerates from the document
    for v in d.VARIANTS[:5]:
        o = d.variant(v)["outputs"]
        cal, npm = o["calibration_used"], o["named_parameters"]
        tenors = np.array([p["tenor_years"] for p in o["curve"]["points"]])
        zeros = np.array([p["zero_rate"] for p in o["curve"]["points"]])
        trades = [book.Trade(t["trade_id"], t["notional"]["amount"], t["maturity_years"], t["side"], t["fixed_rate"]) for t in o["book"]["trades"]]
        mp = o["collateral"]["csa"]["mpor_business_days"] if o["collateral"] else None
        spec = ore.Spec(v, ore.asof_for(int(o["curve"]["curve_date"][5:7])), tenors, zeros, cal["a"], cal["sigma"], trades, mp,
                        o["initial_margin"] is not None, np.array(o["exposure"]["time_grid_years"]), bake.ORE_SAMPLES, npm["seed"]["value"])
        committed = ore.INPUT_DIR / v
        for name in ore.write_inputs(spec, tmp_path / v):
            assert (committed / name).read_bytes() == (tmp_path / v / name).read_bytes(), (v, name)


def test_the_quantlib_rows_are_green_in_every_variant() -> None:
    for v in d.VARIANTS:
        rows = [t for t in d.variant(v)["tests"] if t["test_id"].startswith("ccr.quantlib_")]
        assert sorted(t["test_id"] for t in rows) == ["ccr.quantlib_bond_call", "ccr.quantlib_bond_put", "ccr.quantlib_swaption_payer",
                                                    "ccr.quantlib_swaption_receiver"], v
        assert all(t["light"] == "green" and t["statistic"] <= 1e-6 for t in rows), v
