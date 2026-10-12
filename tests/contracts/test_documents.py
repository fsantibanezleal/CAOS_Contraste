"""Producer-side tests of the document contracts (docs/contracts/catalog.md): every committed document of
data/derived and the three registries validates against exactly one schema file chosen by discovery
(contract_schemas.schema_for_document), and a schema is strict both ways: a removed key or an unknown key fails.
The consumer side is frontend/src/lib/contract.test.ts, which reads the same documents."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

import contract_schemas as cs

DOCS = cs.committed_documents()


def rel(path: Path) -> str:
    return path.relative_to(cs.ROOT).as_posix()


def ids(paths: list[Path]) -> list[str]:
    return [rel(p) for p in paths]


def schema_of(path: Path) -> tuple[Any, str]:
    doc = cs.load_json(path)
    return doc, cs.schema_for_document(path, doc)


def under(path: Path, folder: str) -> bool:
    return path.relative_to(cs.DERIVED).parts[0] == folder if cs.DERIVED in path.parents else False


def variants() -> list[Path]:
    return [p for p in DOCS if cs.DERIVED in p.parents and cs.load_json(p).get("schema") == "contraste.case/v1"]


def models() -> list[Path]:
    return [p for p in DOCS if cs.DERIVED in p.parents and cs.load_json(p).get("schema") == "contraste.models/v1"]


def test_there_are_documents_to_cover() -> None:
    assert len(DOCS) >= 54, len(DOCS)  # 51 under data/derived (3 manifests excluded of .gitkeep) + 3 registries
    assert variants() and models()


@pytest.mark.parametrize("path", DOCS, ids=ids(DOCS))
def test_every_document_matches_exactly_one_schema_and_validates(path: Path) -> None:
    doc, ref = schema_of(path)
    assert cs.errors(ref, doc) == [], f"{rel(path)} against {ref}"


def test_discovery_covers_every_schema_file_that_a_document_selects() -> None:
    chosen = {schema_of(p)[1] for p in DOCS}
    selectable = {c.ref for c in cs.candidates()}
    exempt = cs.exempt_from_documents(cs.catalog_rows(), cs.fixture_documents())
    assert cs.unused_schemas(chosen, selectable, exempt) == []


def test_a_schema_without_a_document_and_without_an_exempting_row_is_reported() -> None:
    rows = [{"schema file": "docs/contracts/schemas/c06/variant.schema.json", "status": "real"}]
    assert cs.unused_schemas({"c01/variant"}, {"c01/variant", "c06/variant"}, cs.exempt_from_documents(rows, [])) == ["c06/variant"]


def test_an_active_row_exempts_its_schema() -> None:
    rows = [{"schema file": "docs/contracts/schemas/c06/variant.schema.json", "status": "active"}]
    assert cs.unused_schemas(set(), {"c06/variant"}, cs.exempt_from_documents(rows, [])) == []


def test_a_fixture_document_exempts_its_schema() -> None:
    fixtures = cs.fixture_documents()
    assert fixtures, "docs/contracts/fixtures holds no document"
    assert "common/readiness" in cs.exempt_from_documents([], fixtures)


def test_the_unused_test_names_no_schema_by_hand() -> None:
    src = Path(__file__).read_text(encoding="utf-8")
    start = src.index("def test_discovery_covers_every_schema_file")
    assert "common/readiness" not in src[start:src.index("def test_a_schema_without_a_document")]


def test_exactly_one_default_variant_schema_per_case() -> None:
    assert all(len(v) == 1 for v in cs.default_variants().values())
    assert cs.default_variants().get("C01") == ["c01/variant"]
    assert cs.default_violations() == []


def _real() -> tuple[cs.Candidate, ...]:
    return cs.candidates()


def _kindless(ref: str, case: str | None) -> cs.Candidate:
    consts: dict[str, Any] = {"schema": "contraste.case/v1"}
    if case:
        consts["case_id"] = case
    return cs.Candidate.from_parts(ref, consts)


def test_a_second_default_variant_schema_for_one_case_fails_the_selector() -> None:
    cands = (*_real(), _kindless("c01/variant-twin", "C01"))
    path = cs.DERIVED / "C01" / "holdout.json"
    with pytest.raises(cs.SelectionError, match="more than one variant schema omits"):
        cs.schema_for_document(path, cs.load_json(path), cands)


def test_a_default_variant_schema_for_another_case_is_accepted() -> None:
    cands = (*_real(), _kindless("c06/variant", "C06"))
    for path in DOCS:
        doc = cs.load_json(path)
        assert cs.schema_for_document(path, doc, cands) == cs.schema_for_document(path, doc), rel(path)
    path = cs.DERIVED / "C06" / "base.json"
    assert cs.schema_for_document(path, {"schema": "contraste.case/v1", "case_id": "C06", "outputs": {}}, cands) == "c06/variant"


def test_every_case_schema_declares_the_case_id_of_its_folder() -> None:
    assert cs.case_folder_violations() == []


def test_a_case_schema_without_case_id_is_reported() -> None:
    plant = cs.Candidate.from_parts("c06/variant-agency", {"schema": "contraste.case/v1", "outputs.kind": "agency"})
    wrong = cs.Candidate.from_parts("c06/models", {"schema": "contraste.models/v1", "case_id": "C04"})
    found = cs.case_folder_violations((*_real(), plant, wrong))
    assert len(found) == 2 and found[0].startswith("c06/variant-agency") and found[1].startswith("c06/models")


def test_a_document_matched_by_nothing_fails_the_selector() -> None:
    path = cs.DERIVED / "C99" / "unknown.json"
    with pytest.raises(cs.SelectionError, match="matches no schema"):
        cs.schema_for_document(path, {"schema": "contraste.case/v1", "case_id": "C99", "outputs": {"kind": "nothing"}})


def test_a_document_matched_by_two_schemas_equally_fails_the_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    twin = cs.Candidate(cs.SCHEMAS / "c04" / "variant-published.schema.json")
    twin.ref = "c04/variant-published-twin"
    real = cs.candidates()
    monkeypatch.setattr(cs, "candidates", lambda: (*real, twin))
    path = cs.DERIVED / "C04" / "published.json"
    with pytest.raises(cs.SelectionError, match="equally"):
        cs.schema_for_document(path, cs.load_json(path))


def test_index_validates() -> None:
    index = cs.load_json(cs.DERIVED / "manifests" / "index.json")
    assert cs.errors("common/case-index", index) == []
    ids_ = [c["case_id"] for c in index["cases"]]
    assert index["n_cases"] == len(ids_) and index["default_case"] in ids_
    for entry in index["cases"]:
        assert (cs.DERIVED / entry["manifest_path"]).is_file(), entry["manifest_path"]
    for f in index["files"]:
        assert (cs.DERIVED / f).is_file(), f


def test_manifests_validate() -> None:
    index = cs.load_json(cs.DERIVED / "manifests" / "index.json")
    for entry in index["cases"]:
        m = cs.load_json(cs.DERIVED / entry["manifest_path"])
        assert cs.errors("common/case-manifest", m) == [], entry["case_id"]
        assert m["case_id"] == entry["case_id"]
        for a in m["artifacts"]:
            path = cs.DERIVED / a["path"]
            assert path.is_file(), a["path"]
            assert path.stat().st_size == a["bytes"], f"{a['path']}: bytes"
            assert (a["role"] == "variant") == ("models_ref" in a), a["path"]


@pytest.mark.parametrize("path", variants(), ids=ids(variants()))
def test_every_variant_matches_the_envelope(path: Path) -> None:
    doc = cs.load_json(path)
    assert cs.errors("common/variant-envelope", doc) == [], rel(path)
    assert doc["variant_id"] == path.stem


@pytest.mark.parametrize("path", variants(), ids=ids(variants()))
def test_variants_validate(path: Path) -> None:
    doc, ref = schema_of(path)
    assert ref.split("/")[0] != "common" and ref.split("/")[1].startswith("variant"), ref
    assert cs.errors(ref, doc) == [], rel(path)


@pytest.mark.parametrize("path", models(), ids=ids(models()))
def test_models_validate(path: Path) -> None:
    doc, ref = schema_of(path)
    assert ref.split("/")[1].startswith("models"), ref
    assert cs.errors("common/models-envelope", doc) == [], rel(path)
    assert cs.errors(ref, doc) == [], rel(path)


def test_every_test_row_validates() -> None:
    n = 0
    for path in variants():
        for i, row in enumerate(cs.load_json(path)["tests"]):
            assert cs.errors("common/test-result", row) == [], f"{rel(path)} tests[{i}]"
            n += 1
    assert n > 100, n


def test_contract_declarations_validate() -> None:
    folder = cs.DERIVED / "contract"
    index = cs.load_json(folder / "index.json")
    assert cs.errors("common/contract-index", index) == []
    assert len(index["families"]) == 8
    for fam in index["families"]:
        doc = cs.load_json(folder / fam["path"])
        assert cs.errors("common/contract-family", doc) == [], fam["family"]
        assert doc["family"] == fam["family"]


def test_registries_validate() -> None:
    sources = cs.load_json(cs.ROOT / "data-pipeline" / "config" / "sources.json")
    assert cs.errors("common/source-registry", sources) == []
    licences = cs.load_json(cs.ROOT / "data-pipeline" / "config" / "licences.json")
    assert cs.errors("common/licences", licences) == []
    manifest = cs.load_json(cs.ROOT / "data" / "sources" / "manifest.json")
    assert cs.errors("common/licence-manifest", manifest) == []


def test_examples_validate() -> None:
    examples = sorted((cs.CONTRACTS / "examples").glob("*.json"))
    assert examples
    for path in examples:
        ref = path.name.removesuffix(".json").replace(".", "/", 1)  # common.test-result.json -> common/test-result
        assert cs.errors(ref, cs.load_json(path)) == [], f"{path.name} against {ref}"


# --- strictness both ways (plant tests on in-memory copies) -----------------------------------------------------------

D = cs.DERIVED
# (document, path of a fixed-key object inside it, a key it must have): maps are skipped on purpose, a map entry
# may legitimately be absent. Every one is a place the producer always writes.
PLANTS = [
    (D / "manifests" / "index.json", (), "default_case"),
    (D / "manifests" / "index.json", ("cases", 0), "manifest_path"),
    (D / "manifests" / "C04.json", (), "seed"),
    (D / "manifests" / "C04.json", ("engine",), "pipeline"),
    (D / "manifests" / "C04.json", ("artifacts", 0, "gate"), "lane"),
    (D / "contract" / "loan_panel.json", ("fields", 0), "unit"),
    (D / "C04" / "published.json", (), "provenance"),
    (D / "C04" / "published.json", ("outputs",), "irw"),
    (D / "C04" / "published.json", ("outputs", "sr190"), "n"),
    (D / "C05" / "ldp-published.json", ("tests", 0), "p_value"),
    (D / "C04" / "published.json", ("provenance",), "seed"),
    (D / "C05" / "models-sp2009.json", ("fit",), "estimation_year"),
    (D / "C05" / "models-sp2009.json", ("model", 0), "details"),
    (D / "C05" / "models-sp2009.json", ("lane",), "reasons"),
    (D / "C04" / "thin.json", ("outputs",), "ladder"),
    (D / "C04" / "thin.json", ("outputs", "rungs", 0), "level"),
]
PLANT_IDS = [f"{rel(p)}:{'/'.join(map(str, t)) or '$'}" for p, t, _ in PLANTS]


def _at(doc: Any, trail: tuple) -> Any:
    for k in trail:
        doc = doc[k]
    return doc


@pytest.mark.parametrize(("path", "trail", "key"), PLANTS, ids=PLANT_IDS)
def test_plant_a_removed_key_fails(path: Path, trail: tuple, key: str) -> None:
    doc, ref = schema_of(path)
    assert cs.errors(ref, doc) == []
    mutated = copy.deepcopy(doc)
    del _at(mutated, trail)[key]
    assert cs.errors(ref, mutated), f"removing {key} under {trail} still validates against {ref}"


@pytest.mark.parametrize(("path", "trail", "key"), PLANTS, ids=PLANT_IDS)
def test_plant_an_unknown_key_fails(path: Path, trail: tuple, key: str) -> None:
    doc, ref = schema_of(path)
    mutated = copy.deepcopy(doc)
    _at(mutated, trail)["planted_unknown_key"] = 1
    assert cs.errors(ref, mutated), f"an unknown key under {trail} still validates against {ref}"

def test_a_wrong_type_and_a_wrong_enum_fail() -> None:
    doc = cs.load_json(cs.DERIVED / "manifests" / "C04.json")
    bad_type = copy.deepcopy(doc)
    bad_type["seed"] = "7"
    assert cs.errors("common/case-manifest", bad_type)
    bad_enum = copy.deepcopy(doc)
    bad_enum["artifacts"][0]["truth_status"] = "invented"
    assert cs.errors("common/case-manifest", bad_enum)
    bad_light = cs.load_json(cs.DERIVED / "C05" / "ldp-published.json")
    bad_light["tests"][0]["light"] = "blue"
    assert cs.errors("c05/variant-ldp", bad_light)


def test_the_schema_files_use_lf_and_two_space_json() -> None:
    for f in cs.schema_files():
        raw = f.read_bytes()
        assert b"\r" not in raw, f"{f}: CRLF"
        assert raw.endswith(b"\n"), f"{f}: no final newline"
        json.loads(raw)


# --- the PD range: open (0, 1) at estimate sites, closed at the one engine-input grid ---------------------------------


@pytest.mark.parametrize("bad", [0.0, 1.0])
def test_a_pd_of_exactly_0_or_1_is_refused_at_an_estimate_site(bad: float) -> None:
    path = cs.DERIVED / "C01" / "holdout.json"
    doc = cs.load_json(path)
    rung = next(iter(doc["outputs"]["rungs"].values()))
    rung["reliability"][0]["pd"] = bad
    assert cs.errors("c01/variant", doc), f"PD {bad} accepted at c01 reliability"


def test_a_pd_of_0_is_accepted_at_the_c04_capital_parity_grid() -> None:
    doc = cs.load_json(cs.DERIVED / "C04" / "models-transitions.json")
    assert doc["fit"]["parity"]["capital"][0]["pd"] == 0.0
    assert cs.errors("c04/models", doc) == []
    doc["fit"]["parity"]["capital"][0]["pd"] = 1.5
    assert cs.errors("c04/models", doc)
