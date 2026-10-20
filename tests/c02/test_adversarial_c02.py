"""Adversarial checks of C02 (validation.md): what was planted, and the gate that must refuse it."""
from __future__ import annotations

import copy
import hashlib
import shutil

import contract_schemas as cs
import numpy as np
import pytest
from c02_support import C02, DERIVED, MODELS, ROOT, SEED, ZIP_NAME, committed, listing_problems, load, make_zip, planted_root, semantics

from pipeline.cases.c02 import fits, page, prep, reader
from pipeline.cases.c02 import conventions as cv


def doc_errors(doc: dict, name: str = "h1") -> list[str]:
    return list(cs.errors(cs.schema_for_document(C02 / f"{name}.json", doc), doc))


def test_adversarial_an_out_of_time_claim_or_a_missing_exploratory_label_is_refused() -> None:
    doc = committed("h1")
    assert doc_errors(doc) == []
    a = copy.deepcopy(doc)
    a["outputs"]["split"]["out_of_time_claim"] = True
    assert doc_errors(a)
    for block, bad in (("transfer", "core"), ("term_structure", "final"), ("impact_detail", "measured")):
        b = copy.deepcopy(doc)
        b["outputs"][block]["label"] = bad
        assert doc_errors(b), block
        c = copy.deepcopy(doc)
        del c["outputs"][block]["label"]
        assert doc_errors(c), block


def test_adversarial_a_flipped_flag_or_an_inflated_count_is_found_by_the_semantic_checks() -> None:
    doc = committed("h1")
    sem = semantics()
    assert sem.check_c02(doc) == []
    a = copy.deepcopy(doc)
    r = a["outputs"]["rungs"][0]
    r["overfit"]["flag"] = not r["overfit"]["flag"]
    assert any("overfit flag" in m for m in sem.check_c02(a))
    b = copy.deepcopy(doc)
    b["outputs"]["counts"]["events"] = b["outputs"]["counts"]["rows"] + 1
    assert any("events above rows" in m for m in sem.check_c02(b))
    c = copy.deepcopy(doc)
    c["outputs"]["rungs"][1]["discrimination"]["auc_ci"]["lo"] = 0.999
    assert any("outside its interval" in m for m in sem.check_c02(c))
    d = copy.deepcopy(doc)
    d["outputs"]["challenger"][0]["auc_diff"] = d["outputs"]["challenger"][0]["auc_diff_ci"]["hi"] + 0.5
    assert any("challenger: the AUC difference is outside its interval" in m for m in sem.check_c02(d))


def test_adversarial_a_not_evaluated_row_with_a_number_is_refused() -> None:
    doc = copy.deepcopy(committed("h1"))
    row = next(r for r in doc["tests"] if r["light"] != "not_evaluated" and r["metric"] is not None or r["statistic"] is not None)
    row["light"] = "not_evaluated"
    assert doc_errors(doc)


def test_adversarial_a_changed_raw_byte_or_a_missing_file_stops_c02(tmp_path) -> None:
    root, man = planted_root(tmp_path / "raw")
    z = root / "raw" / "uci-polish" / ZIP_NAME
    z.write_bytes(z.read_bytes() + b"\x00")          # (the last byte of a zip is already 0x00: appending is a real change)
    with pytest.raises(reader.PolishSourceError):
        reader.ensure_zip(root, fetcher=lambda *a, **k: None, manifest=man)
    from pipeline.cases.c02 import bake

    with pytest.raises(reader.PolishSourceError):
        bake.build(SEED, tmp_path / "nothing-here", manifest=man, check_counts=False, fetcher=lambda *a, **k: None)
    assert not (tmp_path / "nothing-here" / "raw" / "uci-polish" / ZIP_NAME).exists()


def test_adversarial_a_transformation_fitted_on_the_holdout_is_visible_in_the_models_document(built) -> None:
    f = built.fits["h3"]
    on_train = prep.fit_preprocessor(f.X.iloc[f.sp.train])
    on_holdout = prep.fit_preprocessor(f.X.iloc[f.sp.holdout])
    assert on_train.medians != on_holdout.medians                                                    # the planted fit would differ
    rec = next(m for m in built.models["model"] if m["id"] == "h3-P0-constant")["details"]["preprocessing"]
    assert rec == on_train.record() and rec != on_holdout.record()


def test_adversarial_a_document_changed_after_hashing_or_an_edited_page_block_is_found(tmp_path) -> None:
    folder = tmp_path / "C02"
    shutil.copytree(C02, folder)
    manifest = load(DERIVED / "manifests" / "C02.json")
    assert listing_problems(folder, manifest) == []
    target = folder / "h2.json"
    target.write_bytes(target.read_bytes().replace(b"locked-stratified-holdout", b"locked-stratified-holdouT", 1))
    assert any("h2.json" in m for m in listing_problems(folder, manifest))
    text = (ROOT / "docs" / "cases" / "C02.md").read_text(encoding="utf-8")
    edited = text.replace(page.BEGIN, page.BEGIN + "\nan invented sentence", 1)
    docs = {v: committed(v) for v in ("h1", "h2", "h3", "h4", "h5", "pooled")}
    assert page.block_of(edited) != page.results_block(docs, committed(MODELS)).strip("\n")


def test_adversarial_an_engine_pin_the_sdd_does_not_name_or_a_branch_pin_is_refused() -> None:
    from engine_pin import engine_pin_findings

    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    old = req.replace("3767a3ddbfe88fbb26eef60c9c2b08815132e172", "2a21c0b85578357bc7eb13e9d8ffda9ab9b300fa")
    assert any("not the one the SDD technology row names" in m for m in engine_pin_findings(old, sdd))
    branch = req.replace("3767a3ddbfe88fbb26eef60c9c2b08815132e172", "task/0-08-000-batch3")
    assert any("neither a release tag nor a full 40-hex commit" in m for m in engine_pin_findings(branch, sdd))


def test_adversarial_a_finding_citing_a_row_of_no_document_is_refused() -> None:
    from pipeline.core.manifest import ContractViolation, build_artifact

    doc = committed("h1")
    bad = [{"id": "F-X", "severity": "S3", "status": "open", "evidence": ["ml.overfit@h1-nothing@portfolio"], "title": cv.t("x")}]
    from pipeline.core import lineage as lin

    lineage = lin.build("C02", sources=["uci-polish"], truth_status="real-outcomes", seed=SEED, code_version="x", manifest={"sources": {"uci-polish": {"files": [{"name": "a", "sha256": "0" * 64}]}}})
    with pytest.raises(ContractViolation):
        build_artifact(case_id="C02", variant_id="h1", model=doc["model"], outputs=doc["outputs"], tests=doc["tests"], impact=doc["impact"],
                       findings=bad, lineage=lineage, lane={"lane": "precompute", "reasons": []})


def test_adversarial_a_changed_pool_changes_the_split_and_a_decreasing_rate_stops_the_term_structure(tmp_path) -> None:
    root, man = planted_root(tmp_path / "raw", rows=(300,) * 5, shift=0.0)
    h = reader.read_horizons(root / "raw" / "uci-polish" / ZIP_NAME, check_counts=False)
    a = fits.build_fits(h, SEED, with_ladder=False)
    other = make_zip(tmp_path / "raw2" / "uci-polish" / ZIP_NAME, (300,) * 5, seed=SEED + 3, shift=0.0)
    b = fits.build_fits(reader.read_horizons(other, check_counts=False), SEED, with_ladder=False)
    assert not np.array_equal(a["pooled"].y, b["pooled"].y)
    assert hashlib.sha256(a["pooled"].y.tobytes()).hexdigest() != hashlib.sha256(b["pooled"].y.tobytes()).hexdigest() and man


def test_adversarial_a_horizon_read_from_the_file_name_mapping_is_found() -> None:
    """The old mapping (h{n} reads {n}year) disagrees with the dataset definition the documents must follow (decision G21)."""
    old = [(f"h{k}", k, f"{k}year.arff") for k in range(1, 6)]
    assert old != list(cv.HORIZONS)
    wrong = [m for _, years, m in old if m != f"{6 - years}year.arff"]
    assert wrong == ["1year.arff", "2year.arff", "4year.arff", "5year.arff"]                       # only h3 reads the same file either way
    assert cv.expected_counts(1) != cv.FILE_COUNTS[1]
