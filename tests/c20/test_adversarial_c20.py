"""The adversarial checks of docs/design/features/c20/validation.md: what was planted, and the gate that must refuse it."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest
from c20_support import C20, DATA, MANIFEST, MODELS, PROHIBITED, ROOT, SEED, Paths, committed, listing_problems, load, semantics, sha
from engine_pin import engine_pin_findings
from test_c20_documents import FAIR_IDS, FORBIDDEN, group_problems, problems
from test_c20_readers import polish_zip
from test_c20_shocks import frame_of_sample, widened

from pipeline.cases.c20 import bake, data, fed, fetch, sgcd, shocks, v_shift
from pipeline.io import polish
from pipeline.core.manifest import ContractViolation, build_artifact


def doc(name: str) -> dict:
    return copy.deepcopy(committed(name))


def refused(d: dict, name: str = "sgcd-seen") -> list[str]:
    return problems(d, C20 / f"{name}.json")


def test_adversarial_a_bad_sgcd_record_is_refused(tmp_path: Path) -> None:
    lines = (DATA / "sgcd-sample.jsonl").read_text(encoding="utf-8").splitlines()
    base = json.loads(lines[0])

    def write(rec_lines: list[str]) -> Path:
        p = tmp_path / "x.jsonl"
        p.write_text("\n".join(rec_lines) + "\n", encoding="utf-8")
        return p

    def mutate(fn) -> Path:
        r = copy.deepcopy(base)
        fn(r)
        return write([json.dumps(r)])

    for fn, why in ((lambda r: r["metadata"].update(batch="X9"), "batch"), (lambda r: r.update(label=2), "label"),
                    (lambda r: r["value"]["json_view"].update(duration=None), "null"),
                    (lambda r: r["value"]["json_view"].pop("job"), "key"), (lambda r: r.update(version="SGCD-v9"), "version"),
                    (lambda r: r["metadata"].update(shock_semantic="F9"), "shock")):
        with pytest.raises(sgcd.SgcdFormatError):
            sgcd.read_records(mutate(fn))
    with pytest.raises(sgcd.SgcdFormatError, match="repeated"):
        sgcd.read_records(write([lines[0], lines[0]]))
    with pytest.raises(sgcd.SgcdFormatError):
        sgcd.read_records(write([]))
    meta = json.loads((DATA / "sgcd-metadata.json").read_text(encoding="utf-8"))
    meta["seed"] = 7
    (tmp_path / "m.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(sgcd.SgcdFormatError):
        sgcd.read_metadata(tmp_path / "m.json")


def test_adversarial_a_sgcd_document_without_the_prohibited_use_sentence_or_another_with_it_is_refused() -> None:
    d = doc("sgcd-seen")
    assert refused(d) == []
    d["outputs"]["sgcd_notice"] = None
    assert refused(d)
    d = doc("sgcd-seen")
    d["outputs"]["sgcd_notice"]["quote"] = PROHIBITED.replace("must not", "may")
    assert refused(d)
    e = doc("seed-sweep")
    e["outputs"]["sgcd_notice"] = committed("sgcd-seen")["outputs"]["sgcd_notice"]
    assert refused(e, "seed-sweep")
    m = doc(MODELS)
    m["fit"]["sgcd"]["notice"]["quote"] = "an invented sentence"
    assert refused(m, MODELS)


def test_adversarial_a_family_forced_on_every_record_still_obeys_its_conventions() -> None:
    X, ds = frame_of_sample()
    modal = shocks.modal_codes(X)
    full = widened(ds.metadata, 1.0)
    f1 = shocks.apply("F1", X, full, "seen", modal=modal)
    assert {c for c in X.columns if not f1.X[c].equals(X[c])} <= set(shocks.F1_COLUMNS)          # F1 never drops a field F1 does not drop
    assert shocks.apply("F3", X, full, "seen", modal=modal).n_changed == 0                          # cosmetic never reaches the structured view
    with pytest.raises(KeyError):
        shocks.apply("F9", X, full, "seen", modal=modal)
    with pytest.raises(KeyError):
        shocks.probability(ds.metadata, "F4", "seen")                                                # F4 is held out of the seen group
    assert shocks.apply("F4", X, ds.metadata, "held-out", modal=modal).X.equals(shocks.apply("F4", X, ds.metadata, "held-out", modal=modal).X)


def test_adversarial_a_seen_document_that_carries_a_held_out_batch_or_shock_is_refused_by_the_group_check() -> None:
    d = doc("sgcd-seen")
    assert group_problems(d) == []
    d["outputs"]["shipped"]["rows"][1]["batches"] = ["T4", "T5", "T6"]
    assert any("batches" in p for p in group_problems(d))
    d = doc("sgcd-seen")
    d["outputs"]["applied"]["rows"][1]["shock_id"] = "F4"
    assert any("F4" in p for p in group_problems(d))
    h = doc("sgcd-held-out")
    h["outputs"]["shipped"]["rows"][1]["shock_id"] = "F1"
    assert any("F1" in p for p in group_problems(h))
    # the structured-view counts and the drift maxima are the producer checks of the contract
    d = doc("sgcd-seen")
    d["outputs"]["shipped"]["rows"][1]["n_reaching_structured_view"] = d["outputs"]["shipped"]["rows"][1]["n_records"] + 1
    assert any("more records reach the view" in m for m in semantics().check_c20(d))


def test_adversarial_a_german_frame_that_lets_a_test_record_into_the_fit_rows_is_refused(root) -> None:
    sg = root / "raw" / fetch.SGCD_ID
    ds = sgcd.read_dataset(sg / "SGCDataset.jsonl", sg / "SGCDataset_metadata.json")
    frame = data.load_sgcd(root, SEED, ds)
    data.assert_locked(frame)
    leaked = data.Frame(**{**frame.__dict__, "train": np.concatenate([frame.train, frame.hold[:3]])})
    with pytest.raises(data.LockedHoldoutError, match="overlap"):
        data.assert_locked(leaked)
    stage = frame.X["stage"].to_numpy()
    wrong = data.Frame(**{**frame.__dict__, "hold": np.flatnonzero(stage == "adaptation")[:50], "train": np.flatnonzero(stage == "setup"),
                          "cal": np.flatnonzero(stage == "test")[:20]})
    with pytest.raises(data.LockedHoldoutError):
        data.assert_locked(wrong)


def test_adversarial_a_bad_fed_file_is_refused(tmp_path: Path) -> None:
    good = (DATA / "fed-sample.csv").read_text(encoding="utf-8").splitlines()

    def write(lines: list[str]) -> Path:
        p = tmp_path / "f.csv"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return p

    with pytest.raises(fed.FedFormatError, match="header"):
        fed.read_portfolio(write(["loan_id,x", *good[1:]]), "t", expected_rows=None)
    with pytest.raises(fed.FedFormatError, match="rating"):
        fed.read_portfolio(write([good[0], good[1].replace(",BB,", ",XYZ,")]), "t", expected_rows=None)
    with pytest.raises(fed.FedFormatError, match="loans"):
        fed.read_portfolio(write(good), "t", expected_rows=200)
    with pytest.raises(fed.FedFormatError, match="not a number"):
        fed.read_portfolio(write([good[0], good[1].replace("618000", "abc")]), "t", expected_rows=None)
    with pytest.raises(fed.FedFormatError, match="loan_id"):
        fed.read_portfolio(write([good[0], good[1], good[1]]), "t", expected_rows=None)


def test_adversarial_a_real_drift_block_that_names_a_model_or_a_fourth_portfolio_is_refused() -> None:
    d = doc("fed-shift")
    assert refused(d, "fed-shift") == []
    d["outputs"]["real_drift"]["model"] = "P4-lightgbm-polish"
    assert refused(d, "fed-shift")
    d = doc("fed-shift")
    d["outputs"]["real_drift"]["portfolios"].append("median-risk")
    assert refused(d, "fed-shift")
    d = doc("fed-shift")
    d["outputs"]["real_drift"]["pairs"][0]["variables"][0]["ks"] = 1.5
    assert refused(d, "fed-shift")


def test_adversarial_a_shift_that_would_touch_a_training_row_is_refused(root) -> None:
    frame = data.load_polish(root, SEED, 1200)
    data.assert_evaluation_only(frame, frame.hold)
    with pytest.raises(data.LockedHoldoutError, match="training or calibration"):
        data.assert_evaluation_only(frame, frame.train[:4])
    with pytest.raises(data.LockedHoldoutError):
        data.assert_evaluation_only(frame, np.concatenate([frame.hold[:3], frame.cal[:1]]))
    d = doc("fed-shift")
    d["outputs"]["synthetic_shift"]["reference_portfolio"] = "median-risk"
    assert refused(d, "fed-shift")


def test_adversarial_a_cbpe_row_labelled_measured_or_a_coverage_that_misses_its_target_is_refused() -> None:
    d = doc("fed-shift")
    d["outputs"]["synthetic_shift"]["label_free"]["cbpe"]["label"] = "measured"
    assert refused(d, "fed-shift")
    from riskvalidation.ml.cbpe import CbpeAuc

    with pytest.raises(ValueError, match="estimate"):
        CbpeAuc(0.7, "measured", ("a", "b", "c", "d"))
    d = doc("fed-shift")
    d["outputs"]["synthetic_shift"]["label_free"]["conformal"]["target_coverage"] = 0.85
    assert any("target coverage" in m for m in semantics().check_c20(d))
    d = doc("fed-shift")
    d["outputs"]["synthetic_shift"]["label_free"]["conformal"]["coverage"] = 0.99
    assert any("windows do not average" in m for m in semantics().check_c20(d))
    d = doc("fed-shift")
    d["outputs"]["synthetic_shift"]["label_free"]["cbpe"]["assumptions"].pop()
    assert refused(d, "fed-shift")


def test_adversarial_a_seed_sweep_with_the_wrong_seed_count_or_a_mean_outside_its_range_is_found() -> None:
    d = doc("seed-sweep")
    d["outputs"]["rows"][0]["n_seeds"] = 19
    assert any("n_seeds" in m for m in semantics().check_c20(d))
    d = doc("seed-sweep")
    d["outputs"]["rows"][0]["auc"]["mean"] = d["outputs"]["rows"][0]["auc"]["max"] + 0.01
    assert any("minimum and maximum" in m for m in semantics().check_c20(d))
    d = doc("seed-sweep")
    d["outputs"]["rows"][0]["n_seeds"] = 1
    assert refused(d, "seed-sweep")


def test_adversarial_a_reason_code_overlap_with_99_refits_or_top_five_reasons_is_found() -> None:
    d = doc("seed-sweep")
    d["outputs"]["rows"][0]["reason_code_overlap"]["n_refits"] = 99
    assert any("n_refits" in m for m in semantics().check_c20(d))
    d = doc("seed-sweep")
    d["outputs"]["rows"][0]["reason_code_overlap"]["top_k"] = 5
    assert refused(d, "seed-sweep")


def test_adversarial_an_ale_curve_that_goes_backwards_or_a_correlation_without_its_reason_is_found() -> None:
    d = doc("seed-sweep")
    e = d["outputs"]["explainer_agreement"][0]
    e["top_features"][0]["ale"]["edges"] = list(reversed(e["top_features"][0]["ale"]["edges"]))
    assert any("ALE edges do not increase" in m for m in semantics().check_c20(d))
    d = doc("seed-sweep")
    d["outputs"]["explainer_agreement"][0]["rank_correlation"] = None
    assert any("rank_correlation and its reason disagree" in m for m in semantics().check_c20(d))
    d = doc("seed-sweep")
    d["outputs"]["explainer_agreement"][0]["top_features"][0]["ale"]["effect"].append(0.0)
    assert any("one effect per bin" in m for m in semantics().check_c20(d))


def test_adversarial_a_finding_flag_that_disagrees_with_the_tolerance_or_a_preset_off_the_grid_is_found() -> None:
    d = doc("perturbation-grid")
    preset = next(r for r in d["outputs"]["rows"] if r["eps"] == 0.1)
    preset["finding"] = not preset["finding"]
    assert any("finding at eps" in m for m in semantics().check_c20(d))
    d = doc("perturbation-grid")
    d["outputs"]["preset_eps"] = 0.3
    assert any("preset scale is not on the grid" in m for m in semantics().check_c20(d))


def test_adversarial_a_cutoff_that_is_not_the_named_share_or_a_flip_share_above_one_is_refused() -> None:
    d = doc("perturbation-grid")
    d["outputs"]["impact_detail"]["cutoff"]["reject_share"] = 0.3
    assert any("cut-off reject share" in m for m in semantics().check_c20(d))
    d = doc("perturbation-grid")
    d["outputs"]["impact_detail"]["rows"][0]["flip_share"] = 1.2
    assert refused(d, "perturbation-grid")
    d = doc("perturbation-grid")
    d["outputs"]["impact_detail"]["cutoff"]["rule"] = "reject-by-hand"
    assert refused(d, "perturbation-grid")


def test_adversarial_a_leak_that_is_suspect_but_not_caught_or_a_screen_with_no_feature_is_found() -> None:
    d = doc("leakage-planted")
    d["outputs"]["caught"] = False
    assert any("caught disagrees" in m for m in semantics().check_c20(d))
    d = doc("leakage-planted")
    d["outputs"]["screen"]["single_feature_auc"]["suspect"] = False
    assert any("suspect disagrees" in m for m in semantics().check_c20(d))
    d = doc("leakage-planted")
    del d["outputs"]["screen"]["entity_overlap"]
    assert refused(d, "leakage-planted")


def test_adversarial_a_battery_on_another_model_with_eleven_rows_or_a_four_fifths_row_is_refused() -> None:
    d = doc("seed-sweep")
    d["outputs"]["fairness_battery"]["model"] = "uci-german"
    assert refused(d, "seed-sweep")
    d = doc("seed-sweep")
    d["outputs"]["fairness_battery"]["rows"].pop()
    assert refused(d, "seed-sweep")
    d = doc("seed-sweep")
    d["outputs"]["fairness_battery"]["rows"][0]["test_id"] = "fair.adverse_impact"
    assert refused(d, "seed-sweep")
    s = doc("sgcd-seen")
    s["outputs"]["fairness_battery"] = committed("seed-sweep")["outputs"]["fairness_battery"]      # a German-based model carries no battery
    assert refused(s)
    t = doc("seed-sweep")
    t["outputs"]["fairness_battery"] = None                                                            # and a Taiwan model always does
    assert refused(t, "seed-sweep")
    t = doc("seed-sweep")
    t["tests"].append({**t["tests"][0], "test_id": "fair.adverse_impact"})
    assert {r["test_id"] for r in t["tests"]} & set(FORBIDDEN)                                         # the producer test above names it
    assert set(FAIR_IDS) <= {r["test_id"] for r in committed("seed-sweep")["tests"]}


def test_adversarial_a_document_changed_after_hashing_or_a_missing_listing_is_found(tmp_path: Path) -> None:
    folder = tmp_path / "C20"
    folder.mkdir()
    for p in C20.iterdir():
        (folder / p.name).write_bytes(p.read_bytes())
    manifest = load(MANIFEST)
    assert listing_problems(folder, manifest) == []
    (folder / "sgcd-seen.json").write_bytes((folder / "sgcd-seen.json").read_bytes() + b" ")
    assert listing_problems(folder, manifest)
    (folder / "sgcd-seen.json").write_bytes((C20 / "sgcd-seen.json").read_bytes())
    (folder / "SHA256SUMS.txt").write_text("\n".join(line for line in (C20 / "SHA256SUMS.txt").read_text().splitlines() if "fed-shift" not in line) + "\n")
    assert any("fed-shift" in p for p in listing_problems(folder, manifest))
    bad = copy.deepcopy(committed("sgcd-seen"))
    bad["outputs"]["parameters"][1]["value"] = 0.03
    assert any("perturbation_tolerance" in m for m in semantics().check_c20(bad))


def test_adversarial_a_different_seed_changes_the_documents_so_the_determinism_test_is_not_vacuous(root, tmp_path: Path) -> None:
    a, b = Paths(tmp_path / "a"), Paths(tmp_path / "b")
    bake.bake_case(42, a, root, only=("leakage-planted",), max_rows=1200)
    bake.bake_case(43, b, root, only=("leakage-planted",), max_rows=1200)
    assert (a.root / "C20" / "leakage-planted.json").read_bytes() != (b.root / "C20" / "leakage-planted.json").read_bytes()


def test_adversarial_an_edited_results_block_is_found() -> None:
    from test_c20_case_page import PAGE, generated

    from pipeline.cases.c20 import page

    text = PAGE.read_text(encoding="utf-8")
    edited = text.replace("| P4-lightgbm |", "| P4-lightgbm-edited |", 1) if "| P4-lightgbm |" in text else text.replace("0.", "9.", 1)
    assert edited != text and page.block_of(edited) != generated()


def test_adversarial_a_changed_raw_file_or_a_source_that_is_absent_is_refused(tmp_path: Path) -> None:
    fetch.fetch(tmp_path, today="2026-10-19", download=lambda u: b"x" * 10, attempts=1, pause=0.0)
    path = tmp_path / "raw" / fetch.SGCD_ID / "SGCDataset.jsonl"
    path.write_bytes(b"y" * 10)
    with pytest.raises(ValueError, match="differs from its provenance record"):
        fetch.load_provenance(tmp_path, fetch.SGCD_ID)
    path.unlink()
    with pytest.raises(FileNotFoundError, match="absent"):
        fetch.load_provenance(tmp_path, fetch.SGCD_ID)
    (tmp_path / "raw" / fetch.FED_ID / fetch.PROVENANCE[fetch.FED_ID]).unlink()
    assert {m["source"] for m in fetch.missing_for(tmp_path)} == {fetch.FED_ID}
    assert fetch.missing_for(tmp_path)[0]["variants"] == ["fed-shift"]


def test_adversarial_an_engine_pin_the_sdd_does_not_name_or_a_branch_pin_is_refused() -> None:
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    assert engine_pin_findings(req, sdd) == []
    old = req.replace("3767a3ddbfe88fbb26eef60c9c2b08815132e172", "2a21c0b85578357bc7eb13e9d8ffda9ab9b300fa")
    assert any("not the one the SDD technology row names" in f for f in engine_pin_findings(old, sdd))
    branch = req.replace("@3767a3ddbfe88fbb26eef60c9c2b08815132e172", "@task/0-08-000-batch3")
    assert any("neither a release tag nor a full 40-hex commit" in f for f in engine_pin_findings(branch, sdd))


def test_adversarial_an_approved_parameter_changed_in_a_document_is_found() -> None:
    for name, key, bad in (("sgcd-held-out", 0, [0.05, 0.1]), ("seed-sweep", 2, 25), ("leakage-planted", 8, 0.25)):
        d = doc(name)
        d["outputs"]["parameters"][key]["value"] = bad
        assert any("not the approved value" in m for m in semantics().check_c20(d)), (name, key)
    d = doc("seed-sweep")
    d["outputs"]["parameters"][0]["label"] = "regulatory"
    assert refused(d, "seed-sweep")
    d = doc("seed-sweep")
    d["outputs"]["parameters"].pop()
    assert refused(d, "seed-sweep")


def test_adversarial_a_finding_that_cites_a_row_of_no_document_or_has_no_evidence_is_refused() -> None:
    d = doc("perturbation-grid")
    model, tests, outputs = d["model"], d["tests"], d["outputs"]
    from pipeline.cases.c20.conv import t

    lineage = None
    from pipeline.core import lineage as lin

    lineage = lin.build("C20", sources=["uci-taiwan"], truth_status="real-outcomes", seed=1, code_version="x",
                        manifest={"sources": {"uci-taiwan": {"files": [{"name": "a", "sha256": "0" * 64}]}}})
    base = {"case_id": "C20", "variant_id": "x", "model": model, "outputs": outputs, "tests": tests, "impact": d["impact"],
            "lineage": lineage, "lane": d["lane"]}
    build_artifact(**base, findings=[])
    for ev in (["ml.robustness@nobody"], []):
        with pytest.raises(ContractViolation):
            build_artifact(**base, findings=[{"id": "f", "severity": "S3", "status": "open", "evidence": ev, "title": t("a", "b")}])


def test_adversarial_a_ladder_on_a_dataset_the_case_does_not_use_or_a_family_off_the_enum_is_refused() -> None:
    d = doc(MODELS)
    d["fit"]["ladder"][0]["dataset"] = "uci-australian"
    assert refused(d, MODELS)
    d = doc(MODELS)
    d["fit"]["datasets"][0]["id"] = "hmda"
    assert refused(d, MODELS)
    d = doc(MODELS)
    d["fit"]["sgcd"]["commit"] = "deadbeef"
    assert refused(d, MODELS)


def test_adversarial_a_polish_file_with_a_class_outside_the_two_values_or_foreign_attributes_is_refused(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        data.read_polish(polish_zip(tmp_path / "a.zip", [(["1.0"] * 64, "2")]))
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(data.POLISH_MEMBER, "@relation x\n@attribute a numeric\n@attribute class {0,1}\n@data\n1,0\n")
    p = tmp_path / "b.zip"
    p.write_bytes(buf.getvalue())
    with pytest.raises(polish.PolishFormatError, match="Attr1 to Attr64"):
        data.read_polish(p)
    assert sha(p) != sha(polish_zip(tmp_path / "c.zip", [(["1.0"] * 64, "0")]))
    assert v_shift.PAIRS and Paths(tmp_path).root.exists()
