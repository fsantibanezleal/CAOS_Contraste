"""Adversarial checks of C13 (docs/design/features/c13/validation.md): each plants a defect in a copy of the baked documents or
inputs and asserts the clean copy passes and the planted copy fails."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import c13_invariants as invariants
import numpy as np
import producer_checks as pc
import pytest
from pipeline.cases.c13 import CASE, bake, generator, measure, page
from pipeline.pipeline import PipelinePaths
from riskvalidation.market import frtb
from riskvalidation.validation import market as val

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import contract_schemas as cs  # noqa: E402

TOLERANCE = 0.03


def pearson(did: str, n: int = 150) -> float:
    reps = [generator.replicate(did, i) for i in range(n)]
    return float(np.corrcoef(np.concatenate([r.hpl for r in reps]), np.concatenate([r.rtpl for r in reps]))[0, 1])


def test_adversarial_a_generator_with_another_deficiency_is_not_recovered() -> None:
    got = pearson("none")
    assert abs(got - generator.known_pearson("none")) < TOLERANCE                      # within the tolerance of its own truth
    assert abs(got - generator.known_pearson("missing-basis")) > 5 * TOLERANCE         # and far from another variant's


def test_adversarial_a_short_or_non_finite_window_is_refused() -> None:
    rep = generator.replicate("none", 0)
    assert invariants.window_violations(rep.hpl, rep.rtpl, rep.var) == []
    assert invariants.window_violations(rep.hpl[:249], rep.rtpl, rep.var) != []
    nan = rep.rtpl.copy()
    nan[10] = np.nan
    assert invariants.window_violations(rep.hpl, nan, rep.var) != []
    inf = {a: v.copy() for a, v in rep.var.items()}
    inf[0.01][3] = np.inf
    assert invariants.window_violations(rep.hpl, rep.rtpl, inf) != []
    with pytest.raises(ValueError):
        frtb.pla_spearman(rep.hpl[:249], rep.rtpl[:249])                                # the engine refuses it too (MAR32.20)
    with pytest.raises(ValueError):
        frtb.pla_ks(rep.hpl, nan)


def test_adversarial_replications_sharing_a_seed_are_found() -> None:
    clean = bake.plan(13, 0.05)
    assert invariants.independent(clean) == []
    dup = copy.deepcopy(clean)
    dup["variants"][2]["seeds"][1] = dup["variants"][2]["seeds"][0]
    assert invariants.independent(dup) != []
    overlap = copy.deepcopy(clean)
    overlap["variants"][1]["seeds"] = [s + 5 for s in overlap["variants"][0]["seeds"]]
    overlap["variants"][1]["seed_base"] = overlap["variants"][0]["seed_base"] + 5
    assert invariants.independent(overlap) != []


def test_adversarial_a_different_seed_gives_different_bytes(built) -> None:
    other = bake.build(14, 0.05)
    a, b = json.dumps(built["variants"]["missing-basis"], sort_keys=True), json.dumps(other["variants"]["missing-basis"], sort_keys=True)
    assert a != b and built["variants"]["none"]["outputs"]["example"]["seed"] != other["variants"]["none"]["outputs"]["example"]["seed"]


def test_adversarial_a_number_not_from_the_engine_is_found(built, monkeypatch: pytest.MonkeyPatch) -> None:
    n = built["plan"]["n_replications"]
    clean = measure.measure("missing-basis", 13, n)
    assert clean.zone_counts("spearman") == built["variants"]["missing-basis"]["outputs"]["pla"]["zones"]["spearman"]
    monkeypatch.setattr(frtb, "pla_spearman", lambda hpl, rtpl: 0.5)                    # a number not from the engine
    planted = measure.measure("missing-basis", 13, n)
    assert planted.zone_counts("spearman") != built["variants"]["missing-basis"]["outputs"]["pla"]["zones"]["spearman"]
    assert planted.zone_counts("spearman") == {"green": 0, "amber": 0, "red": n}


def test_adversarial_a_document_failing_its_schema_its_producer_checks_or_its_hash_is_found(built, tmp_path: Path) -> None:
    doc = built["variants"]["missing-basis"]
    ref = cs.schema_for_document(ROOT / "data" / "derived" / "C13" / "missing-basis.json", doc)
    assert cs.errors(ref, doc) == [] and pc.c13_variant_violations(doc) == []
    no_block = copy.deepcopy(doc)
    del no_block["outputs"]["pla"]
    assert cs.errors(ref, no_block) != []
    wrong = copy.deepcopy(doc)
    wrong["outputs"]["pla"]["zones"]["overall"]["red"] += 1
    assert pc.c13_variant_violations(wrong) != []
    paths = PipelinePaths.from_output(tmp_path)
    CASE.bake(13, paths, None, 0.02)
    sums = dict(reversed(line.split("  ", 1)) for line in (tmp_path / "C13" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    f = tmp_path / "C13" / "missing-basis.json"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == sums["C13/missing-basis.json"]
    f.write_bytes(f.read_bytes().replace(b"synthetic", b"syntheti_"))
    assert hashlib.sha256(f.read_bytes()).hexdigest() != sums["C13/missing-basis.json"]


def test_adversarial_a_document_without_its_known_deficiency_is_found(built) -> None:
    doc = built["variants"]["omitted-factor"]
    assert invariants.known_deficiency(doc) == []
    other = copy.deepcopy(doc)
    other["outputs"]["known_deficiency"] = copy.deepcopy(built["variants"]["missing-basis"]["outputs"]["known_deficiency"])
    assert invariants.known_deficiency(other) != []
    assert pc.c13_variant_violations(other) != []
    swapped = copy.deepcopy(doc)
    swapped["outputs"]["detection"]["role"] = "size"
    assert invariants.known_deficiency(swapped) != []


def test_adversarial_a_no_deficiency_variant_that_is_not_green_is_found(built) -> None:
    assert invariants.size(built["variants"]["none"], 0.10) == []
    assert invariants.size(built["variants"]["time-misalignment"], 0.10) != []         # a planted variant presented as the size run
    noisy = copy.deepcopy(built["variants"]["none"])
    noisy["outputs"]["detection"]["share_amber_or_red"] = 0.4
    assert invariants.size(noisy, 0.10) != []


def test_adversarial_a_catch_rate_that_does_not_recompute_is_found(built) -> None:
    doc = built["variants"]["stale-volatility"]
    assert invariants.closure(doc) == []
    raised = copy.deepcopy(doc)
    raised["outputs"]["pla"]["zones"]["overall"]["red"] += 1
    raised["outputs"]["pla"]["zones"]["overall"]["green"] -= 1                          # closes on the replications but not on the detection
    assert invariants.closure(raised) != [] or pc.c13_variant_violations(raised) != []
    fresh = measure.measure("stale-volatility", 13, built["plan"]["n_replications"])
    edited = copy.deepcopy(doc)
    z = edited["outputs"]["pla"]["zones"]["ks"]
    z["amber"], z["green"] = z["amber"] + 1, z["green"] - 1                             # closes everywhere, differs from a fresh count
    assert invariants.closure(edited) == [] and edited["outputs"]["pla"]["zones"]["ks"] != fresh.zone_counts("ks")


def test_adversarial_a_desk_row_with_the_wrong_limit_is_found(built) -> None:
    doc = built["variants"]["wrong-correlation"]
    assert invariants.desk_rows(doc) == []
    bad = copy.deepcopy(doc)
    bad["outputs"]["desk_backtest"][1]["limit_exceptions"] = 30
    assert invariants.desk_rows(bad) != []
    assert cs.errors("c13/variant-deficiency", bad) != []                               # the schema binds alpha 0.01 to 12 too
    row = next(t for t in doc["tests"] if t["test_id"] == "market.desk_backtest")
    alpha = float(row["segment"].split("=")[1])
    rep = generator.replicate("wrong-correlation", row["extras"]["replication_index"])
    assert val.desk_backtest(rep.loss, rep.var[alpha], alpha, model_id=row["model_id"]).statistic == row["statistic"]
    other = generator.replicate("wrong-correlation", row["extras"]["replication_index"] + 1)
    different = val.desk_backtest(other.loss, other.var[alpha], alpha, model_id=row["model_id"])
    assert different.inputs_hash != row["inputs_hash"]                                   # a row that is no replication's row is found


def test_adversarial_an_example_that_is_not_the_seeds_output_is_found(built) -> None:
    doc = built["variants"]["missing-basis"]
    ex = doc["outputs"]["example"]
    rep = generator.replicate("missing-basis", ex["replication_index"])
    assert np.allclose(ex["hpl"], rep.hpl, atol=1e-8, rtol=0)
    other = generator.replicate("missing-basis", ex["replication_index"] + 1)
    assert not np.allclose(ex["hpl"], other.hpl, atol=1e-8, rtol=0)                      # another seed's series is found
    edited = copy.deepcopy(doc)
    edited["outputs"]["example"]["zone"] = "green" if ex["zone"] != "green" else "red"
    assert pc.c13_variant_violations(edited) != []                                       # the zone contradicts MAR32.42


def test_adversarial_a_notice_that_drops_the_word_synthetic_is_found(built) -> None:
    doc = built["variants"]["none"]
    assert invariants.synthetic(doc) == []
    quiet = copy.deepcopy(doc)
    quiet["outputs"]["generator"]["notice"] = {"en": "Generated desk P&L with a planted deficiency.", "es": "P&L de mesa generado."}
    assert invariants.synthetic(quiet) != []
    real = copy.deepcopy(doc)
    real["provenance"]["truth_status"] = "real-outcomes"
    assert invariants.synthetic(real) != []


def test_adversarial_a_page_block_that_differs_from_the_documents_is_found(tmp_path: Path) -> None:
    CASE.bake(13, PipelinePaths.from_output(tmp_path), None, 0.02)
    clean = page.results_block(tmp_path)
    f = tmp_path / "C13" / "omitted-factor.json"
    doc = json.loads(f.read_text(encoding="utf-8"))
    doc["outputs"]["detection"]["share_amber_or_red"] = 0.123
    f.write_text(json.dumps(doc), encoding="utf-8")
    assert page.results_block(tmp_path) != clean
    assert page.claim_findings("These are the books of a real bank desk.") != []
    assert page.claim_findings("Synthetic desk P&L; these desks are not real.") == []
