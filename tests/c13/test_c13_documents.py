"""CT-1306, CT-1307, CT-1310, CT-1311, CT-1312: the committed documents of C13 validate, pass the producer checks, are listed with
their hash, name their known deficiency, carry engine rows and say synthetic."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import c13_invariants as invariants
import numpy as np
import producer_checks as pc
from pipeline.cases.c13 import generator, params
from riskvalidation.market import frtb
from riskvalidation.validation import market as val

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import contract_schemas as cs  # noqa: E402

DERIVED = ROOT / "data" / "derived"
VARIANTS = params.IDS
MODELS = "models-generator.json"


def committed() -> list[Path]:
    return sorted((DERIVED / "C13").glob("*.json"))


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_every_committed_document_validates_passes_the_producer_checks_and_is_listed_with_its_hash() -> None:
    files = committed()
    assert [f.name for f in files] == sorted([MODELS, *(f"{v}.json" for v in VARIANTS)])
    manifest = load(DERIVED / "manifests" / "C13.json")
    assert cs.errors("common/case-manifest", manifest) == []
    listed = {a["path"]: a for a in manifest["artifacts"]}
    sums = dict(reversed(line.split("  ", 1)) for line in (DERIVED / "C13" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert set(listed) == {f"C13/{f.name}" for f in files} == set(sums)
    for f in files:
        doc = load(f)
        ref = cs.schema_for_document(f, doc)
        assert ref in ("c13/models", "c13/variant-deficiency"), (f.name, ref)
        assert cs.errors(ref, doc) == [], f.name
        found = pc.c13_models_violations(doc) if ref == "c13/models" else pc.c13_variant_violations(doc)
        assert found == [], (f.name, found)
        rel = f"C13/{f.name}"
        assert listed[rel]["bytes"] == f.stat().st_size, rel
        assert hashlib.sha256(f.read_bytes()).hexdigest() == sums[rel], rel
        assert doc["provenance"]["truth_status"] == "synthetic-known-truth" and listed[rel]["truth_status"] == "synthetic-known-truth"
    assert manifest["case_id"] == "C13" and manifest["sources"] == [] and manifest["default_variant"] in VARIANTS


def test_the_small_bake_validates_against_the_schemas_and_the_producer_checks(built) -> None:
    for vid, doc in built["variants"].items():
        ref = cs.schema_for_document(DERIVED / "C13" / f"{vid}.json", doc)
        assert ref == "c13/variant-deficiency" and cs.errors(ref, doc) == []
        assert pc.c13_variant_violations(doc) == [], vid
    ref = cs.schema_for_document(DERIVED / "C13" / MODELS, built["models"])
    assert ref == "c13/models" and cs.errors(ref, built["models"]) == [] and pc.c13_models_violations(built["models"]) == []


def test_every_variant_carries_its_known_deficiency_and_its_role(built) -> None:
    docs = [(f.name, load(f)) for f in committed() if f.name != MODELS] + list(built["variants"].items())
    assert len(docs) == 12
    for name, doc in docs:
        assert invariants.known_deficiency(doc) == [], name
        assert invariants.closure(doc) == [], name
        k = doc["outputs"]["known_deficiency"]
        want = params.deficiency(k["deficiency_id"])
        assert k["parameters"] == want["parameters"] and k["intended_to_fail"] == want["intended"], name
        assert doc["outputs"]["detection"]["role"] == ("size" if k["deficiency_id"] == "none" else "power")
    plans = {p["deficiency_id"]: p for p in built["models"]["fit"]["deficiencies"]}
    assert list(plans) == list(params.IDS) and all(plans[d]["parameters"] == params.deficiency(d)["parameters"] for d in plans)


def test_the_desk_backtest_rows_are_engine_rows_with_the_mar32_limits(built) -> None:
    docs = [load(f) for f in committed() if f.name != MODELS] + list(built["variants"].values())
    for doc in docs:
        assert invariants.desk_rows(doc) == [], doc["variant_id"]
        pla = [t for t in doc["tests"] if t["test_id"] == "market.pla_test"]
        assert len(pla) == 1 and pla[0]["light"] == doc["outputs"]["example"]["zone"] and pla[0]["n"] == 250
        for t in doc["tests"]:
            if t["test_id"] == "market.desk_backtest":
                alpha = float(t["segment"].split("=")[1])
                assert t["extras"]["aggregate"] == "median-across-replications" and t["extras"]["basis"] == "HPL"
                idx = t["extras"]["replication_index"]
                rep = generator.replicate(doc["variant_id"], idx)
                engine = val.desk_backtest(rep.loss, rep.var[alpha], alpha, model_id=t["model_id"], basis="HPL")
                assert (t["statistic"], t["metric"], t["light"], t["n_events"], t["inputs_hash"]) == (
                    engine.statistic, engine.metric, engine.light, engine.n_events, engine.inputs_hash), (doc["variant_id"], alpha)
                assert t["extras"]["replication_seed"] == rep.seed


def test_the_example_is_the_generator_output_for_its_seed_and_recomputes(built) -> None:
    docs = [load(f) for f in committed() if f.name != MODELS] + list(built["variants"].values())
    for doc in docs:
        ex = doc["outputs"]["example"]
        rep = generator.replicate(doc["variant_id"], ex["replication_index"])
        assert ex["seed"] == rep.seed == params.seed_of(doc["variant_id"], ex["replication_index"])
        assert np.allclose(ex["hpl"], rep.hpl, atol=1e-8, rtol=0) and np.allclose(ex["rtpl"], rep.rtpl, atol=1e-8, rtol=0)
        rho, ks = frtb.pla_spearman(np.array(ex["hpl"]), np.array(ex["rtpl"])), frtb.pla_ks(np.array(ex["hpl"]), np.array(ex["rtpl"]))
        assert abs(ex["spearman"] - rho) < 1e-6 and abs(ex["ks"] - ks) < 1e-6 and ex["zone"] == frtb.pla_zone(rho, ks)


def test_no_text_presents_the_generated_pnl_as_a_real_desk(built) -> None:
    docs = [built["models"], *built["variants"].values(), *(load(f) for f in committed())]
    for d in docs:
        assert invariants.synthetic(d) == []
    page = (ROOT / "docs" / "cases" / "C13.md").read_text(encoding="utf-8")
    assert "synthetic" in page.lower()
    assert not re.search(r"(these|the) (desks?|books?|portfolios?) (are|is|were|was) real", page, re.IGNORECASE)
    assert all("not the book of any real desk" in d["outputs"]["generator"]["notice"]["en"] for d in built["variants"].values())
