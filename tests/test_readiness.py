"""Catalog row readiness 1.0.0 (producer side): core/readiness.py computes every row's declared state from the
catalog and the repository. Each case is reached through the real ``compute`` on a sandbox copy of the inputs; each
document is checked against the schema and each reason against the Missing-data table (parsed here, never copied;
the table is the catalog's plus the rows of ``docs/contracts/rows/CF-B.md`` until the integrator merges them)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))

from contract_schemas import errors  # noqa: E402
from pipeline import registry  # noqa: E402
from pipeline.core import readiness  # noqa: E402

CATALOG = ROOT / "docs" / "contracts" / "catalog.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "CF-B.md"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
OLDER = VERSION.rsplit(".", 1)[0] + ".999"
PLANNED = sorted(c.id for c in registry.planned_cases())
BUILT = [c.id for c in registry.built_cases()]


def _section(text: str, name: str) -> list[list[str]]:
    text = text.replace("\r\n", "\n")
    if f"## {name}\n" not in text:
        return []
    body = text.split(f"## {name}\n", 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in body.splitlines() if ln.startswith("|")]
    return rows[2:]


def merged_catalog() -> str:
    """catalog.md with the rows of the CF-B fragment appended to its Contracts table."""
    text = CATALOG.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not ROWS.is_file():
        return text
    extra = ["| " + " | ".join(r) + " |" for r in _section(ROWS.read_text(encoding="utf-8"), "Contracts")]
    head, rest = text.split("## Contracts\n", 1)
    table, tail = rest.split("\n\n", 1)
    return head + "## Contracts\n" + table + "\n" + "\n".join(extra) + "\n\n" + tail


def template(condition: str) -> tuple[str, str]:
    cells_all = _section(CATALOG.read_text(encoding="utf-8"), "Missing-data states")
    if ROWS.is_file():
        cells_all += _section(ROWS.read_text(encoding="utf-8"), "Missing-data states")
    for cells in cells_all:
        if len(cells) == 6 and condition in cells[1]:
            return cells[4].replace("{{", "{").replace("}}", "}"), cells[5].replace("{{", "{").replace("}}", "}")
    raise AssertionError(f"no Missing-data row mentions {condition!r}")


def fill(tpl: tuple[str, str], **vals) -> dict[str, str]:
    out = []
    for t in tpl:
        for k, v in vals.items():
            t = t.replace("{" + k + "}", str(v))
        out.append(t)
    return {"en": out[0], "es": out[1]}


@pytest.fixture()
def repo(tmp_path) -> Path:
    """A sandbox repository: VERSION, the merged catalog, the planned registry, the cases folder names and the
    committed derived tree."""
    r = tmp_path / "repo"
    (r / "docs" / "contracts").mkdir(parents=True)
    (r / "VERSION").write_text(VERSION + "\n", encoding="utf-8")
    (r / "docs" / "contracts" / "catalog.md").write_text(merged_catalog(), encoding="utf-8")
    (r / "data-pipeline" / "config").mkdir(parents=True)
    shutil.copy(registry.PLANNED_PATH, r / "data-pipeline" / "config" / "planned_cases.json")
    shutil.copytree(ROOT / "data-pipeline" / "pipeline" / "cases", r / "data-pipeline" / "pipeline" / "cases",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data" / "derived", r / "data" / "derived")
    (r / "models").mkdir()
    return r


def compute(r: Path) -> dict:
    return readiness.compute(repo_root=r, derived_root=r / "data" / "derived", models_dir=r / "models")


def row(doc: dict, rid: str) -> dict:
    return next(e for e in doc["contracts"] if e["id"] == rid)


def test_the_computed_document_validates_and_is_deterministic(repo):
    a, b = compute(repo), compute(repo)
    assert errors("common/readiness", a) == []
    assert json.dumps(a) == json.dumps(b)
    ids = [e["id"] for e in a["contracts"]]
    assert "readiness" not in ids and "c01-pd-rung" in ids and ids.index("case-index") < ids.index("case-manifest")


def test_committed_readiness_is_current():
    path = ROOT / "data" / "derived" / "readiness.json"
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert errors("common/readiness", committed) == []
    fresh = readiness.compute(repo_root=ROOT, derived_root=ROOT / "data" / "derived", models_dir=ROOT / "models",
                              catalog_path=CATALOG)
    assert fresh == committed
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_readiness.py")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_16_planned_cases_are_a_partial_case_manifest_with_sorted_paths(repo):
    e = row(compute(repo), "case-manifest")
    assert (e["state"], e["provenance"]) == ("partial", "real")
    assert e["missing"] == [f"manifests/{c}.json" for c in PLANNED] and len(PLANNED) == 16
    assert e["reason"] == fill(template("planned and not built"), n=16, total=22, ids=", ".join(PLANNED))
    assert "C02, C03, C08" in e["reason"]["en"]


def test_a_planned_case_is_declared_absent_only(repo):
    doc = compute(repo)
    for e in doc["contracts"]:
        for m in e["missing"]:
            assert not any(m.startswith(f"{c}/") for c in PLANNED)  # never an artifact of a planned case
    derived = repo / "data" / "derived"
    for c in PLANNED:
        assert not (derived / c).exists() and not (derived / "manifests" / f"{c}.json").exists()


def test_a_built_case_with_its_manifest_removed_is_partial_with_its_path(repo):
    (repo / "data" / "derived" / "manifests" / "C04.json").unlink()
    e = row(compute(repo), "case-manifest")
    assert e["state"] == "partial"
    assert e["missing"] == sorted(["manifests/C04.json"] + [f"manifests/{c}.json" for c in PLANNED])
    assert e["reason"] == fill(template("a manifest the index lists is absent"), n=17, total=22)


def test_an_absent_artifact_is_partial_for_its_case_rows(repo):
    (repo / "data" / "derived" / "C05" / "sp-2010.json").unlink()
    doc = compute(repo)
    assert row(doc, "c05-sp")["state"] == "partial" and row(doc, "c05-sp")["missing"] == ["C05/sp-2010.json"]
    assert row(doc, "c04-agency")["state"] == "available"
    assert row(doc, "c05-models-sp")["state"] == "available"


def test_no_index_is_missing(repo):
    (repo / "data" / "derived" / "manifests" / "index.json").unlink()
    doc = compute(repo)
    for rid in ("case-index", "case-manifest", "c01-variant", "c01-pd-rung"):
        e = row(doc, rid)
        assert (e["state"], e["provenance"], e["reason"]) == ("missing", None, fill(template("is absent")))


def test_an_older_engine_is_stale(repo):
    p = repo / "data" / "derived" / "manifests" / "index.json"
    idx = json.loads(p.read_text(encoding="utf-8"))
    idx["engine_version"] = OLDER
    p.write_text(json.dumps(idx), encoding="utf-8")
    e = row(compute(repo), "case-index")
    assert e["state"] == "stale"
    assert e["reason"] == fill(template("differs from `VERSION`"), engine_version=OLDER, version=VERSION)


def test_the_slot_is_available_when_every_rung_is_fitted(repo):
    e = row(compute(repo), "c01-pd-rung")
    assert (e["state"], e["provenance"], e["reason"], e["missing"]) == ("available", "real", None, [])


def test_a_rung_missing_from_the_models_artifact_is_training_on_the_baseline(repo):
    p = repo / "data" / "derived" / "C01" / "models-german.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["model"] = [m for m in doc["model"] if m["id"] != "P3-ebm"]
    p.write_text(json.dumps(doc), encoding="utf-8")
    e = row(compute(repo), "c01-pd-rung")
    assert (e["state"], e["provenance"], e["missing"]) == ("training", "baseline", [])
    assert e["reason"] == fill(template("fitted rung"), rungs="P3-ebm", artifacts="C01/models-german.json")


def test_the_api_row_is_missing_while_dormant(repo):
    e = row(compute(repo), "api")
    assert (e["state"], e["provenance"]) == ("missing", None)
    assert e["reason"] == fill(template("always, in the static document"))


def test_a_stale_catalog_is_detected_by_the_checker(repo):
    cat = repo / "docs" / "contracts" / "catalog.md"
    doc = compute(repo)
    (repo / "data" / "derived" / "readiness.json").write_text(
        json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    cat.write_text(cat.read_text(encoding="utf-8") + "\nEdited.\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_readiness.py"), str(repo)],
                          capture_output=True, text=True)
    assert proc.returncode == 1 and "catalog_sha256" in proc.stdout


def test_status_vocabulary_is_enforced(repo):
    cat = repo / "docs" / "contracts" / "catalog.md"
    cat.write_text(re.sub(r"\| real \|\n", "| Real |\n", cat.read_text(encoding="utf-8"), count=1), encoding="utf-8")
    with pytest.raises(ValueError, match="status"):
        compute(repo)


def test_built_ids_by_filename_match_the_discovery():
    assert readiness.built_ids(ROOT / "data-pipeline" / "pipeline" / "cases") == BUILT


def test_the_required_rungs_are_the_ladder_core():
    from pipeline.cases import c01_ladder

    assert set(readiness.C01_RUNGS) <= set(c01_ladder.SHORT_TITLES)
    assert readiness.C01_RUNGS[0] == "P0-constant"


def test_the_check_script_needs_no_numerical_engine():
    script = ROOT / "scripts" / "check_readiness.py"
    code = ("import sys, runpy; sys.modules['numpy'] = None; sys.modules['pandas'] = None; "
            f"sys.argv = ['check_readiness.py']; runpy.run_path(r'{script}', run_name='__main__')")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "readiness: current" in proc.stdout, proc.stdout + proc.stderr


def _write_readiness(r: Path) -> None:
    readiness.write(r / "data" / "derived", compute(r))


def _check_artifacts(r: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "check_artifacts.py"), str(r)],
                          capture_output=True, text=True)


def test_check_artifacts_accepts_an_absent_manifest_only_when_the_current_readiness_declares_it(repo):
    _write_readiness(repo)
    ok = _check_artifacts(repo)
    assert ok.returncode == 0 and "16 declared absent" in ok.stdout, ok.stdout
    (repo / "data" / "derived" / "manifests" / "C22.json").unlink()
    stale = _check_artifacts(repo)  # the readiness was not recomputed: it does not list C22
    assert stale.returncode == 1 and "manifests" in stale.stdout and "C22.json" in stale.stdout
    _write_readiness(repo)
    declared = _check_artifacts(repo)
    assert declared.returncode == 0 and "17 declared absent" in declared.stdout, declared.stdout


def test_check_artifacts_still_fails_on_any_other_absent_file(repo):
    _write_readiness(repo)
    (repo / "data" / "derived" / "C22" / "null.json").unlink()
    _write_readiness(repo)  # even a current readiness (it says partial for the artifact) does not excuse an artifact
    proc = _check_artifacts(repo)
    assert proc.returncode == 1 and "missing artifact" in proc.stdout
    (repo / "data" / "derived" / "readiness.json").unlink()
    assert _check_artifacts(repo).returncode == 1
