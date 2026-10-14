"""CT-1406, CT-1408 to CT-1412: the committed C14 documents."""
from __future__ import annotations

import copy

import c14_docs as d
import contract_schemas as cs
import pytest
import semantics
from conftest import data_root, requires_raw


def test_every_committed_document_validates_passes_the_semantic_checks_and_is_listed_with_its_hash() -> None:
    files = list(d.C14.iterdir())
    names = sorted([*(f"{v}.json" for v in d.VARIANTS), f"{d.MODELS}.json", "raw-sources.txt", "SHA256SUMS.txt"])
    assert sorted(f.name for f in files) == names
    manifest = d.load(d.DERIVED / "manifests" / "C14.json")
    assert cs.errors("common/case-manifest", manifest) == []
    docs = [f for f in files if f.suffix == ".json"]
    listed = {a["path"]: a for a in manifest["artifacts"]}
    sums = dict(reversed(line.split("  ", 1)) for line in (d.C14 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert set(listed) == {f"C14/{f.name}" for f in docs} and set(sums) == set(listed) | {"C14/raw-sources.txt"}
    for f in docs:
        doc = d.load(f)
        assert d.problems(doc, f) == [], f.name
        assert doc["provenance"]["truth_status"] == "synthetic-calibrated"
        assert listed[f"C14/{f.name}"]["bytes"] == f.stat().st_size
        assert sums[f"C14/{f.name}"] == d.sha(f)
        out = doc["outputs"] if "outputs" in doc else doc["fit"]
        assert out["bank"]["aggregates"] == "real" and out["bank"]["behaviour"] == "synthetic" and out["bank"]["cert"] == 24735
    assert sums["C14/raw-sources.txt"] == d.sha(d.C14 / "raw-sources.txt")


def test_nmd_requests_above_the_cap_are_cut_and_flagged_and_slotted_at_the_used_values() -> None:
    caps = {"retail-transactional": (0.9, 5.0), "retail-non-transactional": (0.7, 4.5), "wholesale": (0.5, 4.0)}
    for vid in d.VARIANTS:
        out = d.variant(vid)["outputs"]
        assert out["nmd_segments"]
        for s in out["nmd_segments"]:
            cs_, cm = caps[s["category"]]
            assert (s["core_share_cap"], s["core_maturity_cap_years"]) == (cs_, cm)
            assert s["core_share_used"] == min(s["requested_core_share"], cs_) and s["core_maturity_used_years"] == min(s["requested_core_maturity_years"], cm)
            assert s["cap_applied"] == (s["requested_core_share"] > cs_ or s["requested_core_maturity_years"] > cm)
            assert s["source_kind"] == "synthetic-stated" and "synthetic" in s["source"].lower()
        assert any(s["cap_applied"] for s in out["nmd_segments"]), "the stated requests stand above the caps"
        rep = semantics.Report()
        semantics.check_nmd_segments(out, out["balance_sheet"]["items"], rep, "c14")
        assert list(rep) == []
        by_cat = {s["category"]: s["balance"] for s in out["nmd_segments"]}
        items = [i for i in out["balance_sheet"]["items"] if i["behavioural_class"].startswith("nmd-")]
        for cat, bal in by_cat.items():
            assert bal == pytest.approx(sum(i["amount"] for i in items if i["behavioural_class"] == f"nmd-{cat}"))


def test_every_valuation_date_carries_six_shocks_in_four_scenarios_with_their_twins() -> None:
    for vid in d.VARIANTS:
        out = d.variant(vid)["outputs"]
        sc = out["scenarios"]
        assert [(s["calibration"], s["nmd_assumption"]) for s in sc] == [("2024", "behavioural"), ("2024", "contractual"),
                                                                        ("2016", "behavioural"), ("2016", "contractual")]
        for s in sc:
            assert [x["shock"] for x in s["shocks"]] == list(d.SHOCKS)
            assert s["eve_risk_measure"] == max([0.0, *(x["delta_eve"] for x in s["shocks"])])
            assert s["outlier"]["tier1"] > 0 and s["outlier"]["threshold_share_tier1"] == 0.15
            assert [x["delta_nii"] is not None for x in s["shocks"]] == [True, True, False, False, False, False]
        assert len(out["behavioural_comparison"]) == 12
        assert {a["nmd_assumption"] for a in out["ladder"]} == {"behavioural", "contractual"}
        assert out["sign_convention"]["delta_eve"] == "positive-is-loss" and out["currency"] == "USD"


def test_ear_evar_levels_carry_the_engine_monte_carlo_errors() -> None:
    for vid in d.VARIANTS:
        ee = d.variant(vid)["outputs"]["ear_evar"]
        assert ee["method"] == "hw1f" and ee["n_paths"] >= 10000 and ee["seed"] == 42 and ee["n_batches"] == 20
        assert ee["mc_error_method"] == "batch-means"
        assert [lv["level"] for lv in ee["levels"]] == [0.95, 0.99]
        for lv in ee["levels"]:
            assert lv["ear_se"] > 0 and lv["evar_se"] > 0 and lv["ear_se"] < abs(lv["ear"]) and lv["evar_se"] < abs(lv["evar"])


def test_the_out_of_sample_row_compares_2021_q4_with_the_realised_2022_nii() -> None:
    first = d.variant("vd-2021-q4")["outputs"]
    oos = first["out_of_sample"]
    assert oos["applicable"] and oos["projection_date"] == "2021-12-31"
    assert (oos["realised_period_start"], oos["realised_period_end"]) == ("2022-01-01", "2022-12-31")
    assert oos["projected_delta_nii"] == first["dynamic_nii"]["scenarios"][1]["delta_vs_base"]
    # the realised change is the 2021 net interest income less the 2022 one (loss-positive), from the two year-end reports
    assert oos["realised_delta_nii"] == pytest.approx(3226000.0 - 4584000.0)
    assert oos["relative_error"] == pytest.approx(abs(oos["projected_delta_nii"] - oos["realised_delta_nii"]) / abs(oos["realised_delta_nii"]))
    for vid in ("vd-2022-q2", "vd-2022-q4"):
        o = d.variant(vid)["outputs"]["out_of_sample"]
        assert not o["applicable"] and o["reason"]["en"] and o["reason"]["es"] and o["realised_delta_nii"] is None
    rows = {t["test_id"]: t for t in d.variant("vd-2021-q4")["tests"]}
    assert rows["irrbb.nii_out_of_sample"]["light"] in ("green", "amber", "red")
    rows = {t["test_id"]: t for t in d.variant("vd-2022-q4")["tests"]}
    assert rows["irrbb.nii_out_of_sample"]["light"] == "not_evaluated"


def test_no_value_is_dated_after_its_valuation_date_and_later_data_changes_nothing() -> None:
    for vid in d.VARIANTS:
        doc = d.variant(vid)
        out = doc["outputs"]
        v = out["valuation_date"]
        assert semantics.dating_violations(doc) == []
        assert max(r["report_date"] for r in out["data"]["call_reports"]) == out["data"]["data_cutoff"] <= v
        assert out["curve"]["date"] == v and out["balance_sheet"]["as_of"] == v
    m = d.models()["fit"]
    for nm in m["nmd_models"]:
        assert all(w["window_end"] <= nm["valuation_date"] for w in nm["stability"])


@requires_raw
def test_a_variant_does_not_change_when_every_later_report_is_removed(built) -> None:
    from conftest import SEED
    from pipeline.cases.c14 import bake

    cut = bake.build(SEED, data_root(), n_paths=2000, drop_after="2021-12-31", only=("vd-2021-q4",))
    a, b = copy.deepcopy(built.variants["vd-2021-q4"]), cut.variants["vd-2021-q4"]
    for doc in (a, b):
        doc["outputs"].pop("out_of_sample")
        doc["tests"] = [t for t in doc["tests"] if t["test_id"] != "irrbb.nii_out_of_sample"]
        doc["findings"] = [f for f in doc["findings"] if "irrbb.nii_out_of_sample" not in f["evidence"]]
        doc["provenance"].pop("inputs")
    assert a == b
