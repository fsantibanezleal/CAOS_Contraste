"""The adversarial gates of validation.md: each plants a defect and requires the check to refuse it."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import c14_docs as d
import contract_schemas as cs
import pytest
import semantics
from c14_support import SEED, SMALL_PATHS, data_root, requires_raw

from pipeline.cases.c14 import assumptions
from pipeline.io import fdic
from pipeline.io import treasury

DATA = Path(__file__).resolve().parent / "data"


def doc(vid: str = "vd-2021-q4") -> dict:
    return copy.deepcopy(d.variant(vid))


def test_adversarial_a_later_report_is_never_returned_and_a_missing_date_is_refused() -> None:
    rs = fdic.read_financials(DATA / "sample-financials.json", 24735)
    assert "2022-03-31" not in [r.report_date for r in fdic.up_to(rs, "2021-12-31")]
    with pytest.raises(ValueError):
        fdic.report_at(rs, "2022-01-31")
    with pytest.raises(ValueError):
        fdic.realised_nii(rs, "2022-12-31", "2022-01-01", "2022-12-31")


def test_adversarial_a_later_curve_day_is_not_read_and_a_deleted_tenor_is_listed(tmp_path: Path) -> None:
    shutil.copytree(DATA / "treasury-sample", tmp_path / "t")
    f = tmp_path / "t" / "daily-treasury-par-2021.csv"
    f.write_text(f.read_text(encoding="utf-8") + "01/03/2022,9.99,9.99,9.99,9.99,9.99,9.99,9.99,9.99,9.99,9.99,9.99,9.99\n", encoding="utf-8")
    g = tmp_path / "t" / "daily-treasury-par-2022.csv"
    g.write_text(g.read_text(encoding="utf-8").replace("12/30/2022,4.12,4.41,4.42,4.69", "12/30/2022,4.12,4.41,,4.69"), encoding="utf-8")
    curves = treasury.read_par(tmp_path / "t")
    assert max(treasury.curve_as_of(curves, "2021-12-31").par.values()) < 0.05
    assert 0.25 in treasury.curve_as_of(curves, "2022-12-30").missing_tenors()


@requires_raw
def test_adversarial_a_changed_raw_file_is_refused_by_its_provenance_record(tmp_path: Path) -> None:
    from pipeline.cases.c14 import fetch

    root = tmp_path / "root"
    shutil.copytree(data_root() / "raw" / fetch.FDIC_DIR, root / "raw" / fetch.FDIC_DIR)
    shutil.copytree(data_root() / "raw" / fetch.TREASURY_DIR, root / "raw" / fetch.TREASURY_DIR)
    victim = root / "raw" / fetch.TREASURY_DIR / "daily-treasury-par-2021.csv"
    victim.write_bytes(victim.read_bytes().replace(b"0.06", b"0.07", 1))
    with pytest.raises(ValueError, match="differs from its provenance record"):
        fetch.load_provenance(root)


def test_adversarial_an_item_whose_flows_miss_its_amount_is_refused() -> None:
    x = doc()
    x["outputs"]["balance_sheet"]["items"][0]["cash_flows"]["behavioural"][0]["amount"] += 1000.0
    assert any("flows do not sum to its amount" in m for m in semantics.check_document(x))


def test_adversarial_an_assumption_without_its_source_is_refused() -> None:
    reg = dict(assumptions.REGISTRY)
    reg["prepayment_cpr"] = assumptions.Assumption(0.08, "per year", "fitted", "")
    reg["hw1f_a"] = assumptions.Assumption(0.1, "per year", "fitted", "a fit that nobody ran")
    found = assumptions.check_registry(reg)
    assert any("prepayment_cpr" in m for m in found) and any("hw1f_a" in m for m in found)


def test_adversarial_a_share_above_its_cap_without_cap_applied_is_refused() -> None:
    x = doc()
    seg = next(s for s in x["outputs"]["nmd_segments"] if s["cap_applied"])
    seg["cap_applied"] = False
    assert cs.errors(cs.schema_for_document(d.C14 / "x.json", x), x), "the schema refuses it"
    assert semantics.check_document(x), "the semantic check refuses it"


def test_adversarial_an_eve_computed_elsewhere_is_found_by_the_engine_call_check() -> None:
    import test_c14_engine_calls as ec

    x = doc()
    assert ec.engine_findings(x["outputs"]) == []
    x["outputs"]["scenarios"][0]["shocks"][0]["delta_eve"] += 1.0
    assert ec.engine_findings(x["outputs"]), "the engine-call check names it"
    assert semantics.check_document(x), "the semantic recomputation names it too"


def test_adversarial_a_document_changed_after_hashing_is_found(tmp_path: Path) -> None:
    sums = (d.C14 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    first = sums[0].split("  ", 1)
    copy_of = tmp_path / "x.json"
    copy_of.write_bytes((d.DERIVED / first[1]).read_bytes() + b" ")
    assert hashlib.sha256(copy_of.read_bytes()).hexdigest() != first[0]


def test_adversarial_a_scenario_without_its_twin_is_refused() -> None:
    x = doc()
    x["outputs"]["scenarios"] = [s for s in x["outputs"]["scenarios"] if s["nmd_assumption"] == "behavioural"]
    assert cs.errors(cs.schema_for_document(d.C14 / "x.json", x), x)


def test_adversarial_a_monte_carlo_error_not_from_the_engine_is_found() -> None:
    import test_c14_engine_calls as ec

    x = doc()
    x["outputs"]["ear_evar"]["levels"][0]["ear_se"] *= 1.5
    assert ec.engine_findings(x["outputs"]), "the engine-call check recomputes the error from the paths"
    assert semantics.check_document(x) == [], "the semantic check cannot: it only bounds the error below |ear|"


def test_adversarial_an_out_of_sample_row_that_does_not_use_the_projection_is_refused() -> None:
    x = doc()
    o = x["outputs"]["out_of_sample"]
    o["projected_delta_nii"] = o["realised_delta_nii"]
    o["relative_error"] = 0.0
    assert any("projected_delta_nii" in m for m in semantics.check_document(x))


def test_adversarial_a_call_report_after_the_valuation_date_is_refused() -> None:
    x = doc()
    x["outputs"]["data"]["call_reports"].append({"report_date": "2022-03-31", "source": "planted", "fields": ["ASSET"]})
    assert any("after the valuation date" in m for m in semantics.dating_violations(x))
    assert semantics.check_document(x)


@requires_raw
def test_adversarial_another_seed_changes_the_simulated_blocks() -> None:
    from pipeline.cases.c14 import bake

    a = bake.build(SEED, data_root(), n_paths=SMALL_PATHS, only=("vd-2022-q4",))
    b = bake.build(SEED + 1, data_root(), n_paths=SMALL_PATHS, only=("vd-2022-q4",))
    ea, eb = a.variants["vd-2022-q4"]["outputs"]["ear_evar"], b.variants["vd-2022-q4"]["outputs"]["ear_evar"]
    assert ea["levels"] != eb["levels"]
    assert a.variants["vd-2022-q4"]["outputs"]["scenarios"] == b.variants["vd-2022-q4"]["outputs"]["scenarios"]


def test_adversarial_an_edited_results_block_is_found() -> None:
    from pipeline.cases.c14 import page

    text = (d.ROOT / "docs" / "cases" / "C14.md").read_text(encoding="utf-8")
    block = text.split(page.BEGIN, 1)[1].split(page.END, 1)[0]
    digit = next(c for c in block if c.isdigit())
    edited = block.replace(digit, str((int(digit) + 1) % 10), 1)
    want = page.results_block({v: d.variant(v) for v in d.VARIANTS}, d.models())
    assert edited.strip("\n") != want.strip("\n")
    assert json is not None
