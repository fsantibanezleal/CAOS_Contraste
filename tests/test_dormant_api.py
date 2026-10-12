"""The dormant app/ serves the committed contract-2 documents as they are and nothing outside data/derived. The
service layer is stdlib only, so the first group runs without the API lane; the route tests need fastapi and httpx
and skip without them. A document that is absent is a declared state (503 with the state and the reason, never an
empty body), an unknown case is a 404."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import content  # noqa: E402

DERIVED = ROOT / "data" / "derived"


def test_serves_the_index_every_built_manifest_and_every_artifact_it_names():
    index = content.load_index()
    assert len(index["cases"]) == 22
    served = 0
    for entry in index["cases"]:
        m = content.load_manifest(entry["case_id"])
        if m is None:
            assert not (DERIVED / entry["manifest_path"]).exists(), entry["case_id"]  # a planned case
            continue
        assert m["case_id"] == entry["case_id"]
        paths = content.artifact_paths(m)
        assert paths, f"{entry['case_id']}: the manifest names no artifact"
        for rel in paths:
            assert content.load_artifact(rel) is not None, rel
        served += 1
    assert served == 4


def test_reads_both_forms_of_a_manifest():
    assert content.artifact_paths({"artifact": {"path": "A/trace.json"}}) == ["A/trace.json"]
    assert content.artifact_paths({"artifacts": [{"path": "B/v1.json"}, {"path": "B/v2.json"}]}) == ["B/v1.json", "B/v2.json"]
    assert content.artifact_paths({}) == []


def test_nothing_outside_the_derived_root():
    assert content.load_artifact("../../VERSION") is None
    assert content.load_artifact("manifests/../../../pyproject.toml") is None
    assert content.load_artifact("../../package.json") is None
    assert content.load_manifest("../index") is None
    assert content.load_manifest("..\\index") is None


pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402


def client(monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> TestClient:
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture()
def real(monkeypatch) -> TestClient:
    return client(monkeypatch, DERIVED)


def test_readiness_is_served_with_the_api_row_available(real):
    r = real.get("/api/readiness")
    assert r.status_code == 200
    doc = r.json()
    api = next(e for e in doc["contracts"] if e["id"] == "api")
    assert (api["state"], api["provenance"], api["reason"]) == ("available", "real", None)
    cm = next(e for e in doc["contracts"] if e["id"] == "case-manifest")
    assert cm["state"] == "partial" and len(cm["missing"]) == 18


def test_a_planned_case_answers_503_with_the_declared_state_never_an_empty_body(real):
    r = real.get("/api/cases/C02/manifest")
    assert r.status_code == 503
    body = r.json()
    assert body["detail"]["state"] == "partial"
    reason = body["detail"]["reason"]
    assert set(reason) == {"en", "es"} and "C02" in reason["en"] and "planned" in reason["en"]
    assert real.get("/api/cases/C02/manifest").content  # never an empty body


def test_a_built_case_is_served(real):
    r = real.get("/api/cases/C22/manifest")
    assert r.status_code == 200 and r.json()["case_id"] == "C22"
    first = r.json()["artifacts"][0]["path"]
    assert real.get(f"/api/artifacts/{first}").status_code == 200


def test_an_unknown_case_is_404(real):
    r = real.get("/api/cases/C99/manifest")
    assert r.status_code == 404 and r.json() == {"detail": "unknown case"}
    for bad in ("..%5Cindex", ".hidden", "..", "%2e%2e", "index"):
        assert real.get(f"/api/cases/{bad}/manifest").status_code == 404, bad


def test_the_index_lists_22_cases(real):
    assert len(real.get("/api/cases").json()["cases"]) == 22


def test_a_built_case_whose_manifest_vanished_is_503_partial(monkeypatch, tmp_path):
    root = tmp_path / "derived"
    shutil.copytree(DERIVED, root)
    (root / "manifests" / "C04.json").unlink()
    c = client(monkeypatch, root)
    r = c.get("/api/cases/C04/manifest")
    assert r.status_code == 503 and r.json()["detail"]["state"] in ("partial", "missing")


def test_503_when_documents_are_absent(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path)
    for path in ("/api/cases", "/api/cases/C01/manifest", "/api/readiness"):
        r = c.get(path)
        assert r.status_code == 503, path
        d = r.json()["detail"]
        assert d["state"] == "missing" and set(d["reason"]) == {"en", "es"}, path


def test_only_indexed_documents_are_served(real):
    for rel in ("readiness.json", "manifests/index.json", "manifests/C22.json", "C99/x.json"):
        assert real.get(f"/api/artifacts/{rel}").status_code == 404, rel


def test_get_only(real):
    for method in ("post", "put", "patch", "delete"):
        assert getattr(real, method)("/api/cases").status_code == 405, method
