"""U16-P1b (BL-086): every case producer states what it reads in the `depends_on` list of its manifest, and the governance graph is built from those lists.

Four checks: every committed manifest carries a valid list; each list is what its producer's source reads (the documents of other cases it names, the
modules of other cases it imports; the scan below is the test's own, apart from the helper's); the governance edges the lists give are the edges of
0.15.000 (the document and code edges E01 to E15 of the U15 addendum), and `edges.json` keeps only the related links.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "data-pipeline" / "pipeline" / "cases"
MANIFESTS = ROOT / "data" / "derived" / "manifests"
EDGES_JSON = ROOT / "data-pipeline" / "pipeline" / "governance" / "edges.json"
BUILT = sorted(p.stem for p in MANIFESTS.glob("C[0-9][0-9].json"))

#: the case-level edges of 0.15.000 (inventory.json before this unit): (upstream, downstream, kind). The same set before and after (U16-P1b invariant).
EDGES_0_15_000 = {
    ("C01", "C02", "code"), ("C01", "C03", "code"), ("C01", "C04", "code"), ("C01", "C05", "code"), ("C01", "C20", "code"), ("C01", "C22", "code"),
    ("C05", "C04", "code"), ("C06", "C03", "code"), ("C06", "C08", "code"), ("C07", "C15", "code"), ("C07", "C18", "document"),
    ("C10", "C18", "code"), ("C11", "C18", "document"), ("C15", "C18", "document"), ("C17", "C18", "document"),
}
DOC_REF = re.compile(r"^(C\d\d)/[A-Za-z0-9._-]+\.json$|^manifests/(C\d\d)\.json$")


def producer_files(case_id: str) -> list[Path]:
    n = case_id[1:]
    pkg = CASES_DIR / f"c{n}"
    files = sorted(pkg.rglob("*.py")) if pkg.is_dir() else []
    return files + sorted(CASES_DIR.glob(f"c{n}_*.py"))


def scan_imports(case_id: str) -> set[str]:
    """Modules of other cases the producer's files import (the test's own resolution of relative imports)."""
    out: set[str] = set()
    for f in producer_files(case_id):
        package = list(f.relative_to(CASES_DIR.parent.parent).with_suffix("").parts)[:-1]      # pipeline, cases, c18
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                base = package[: len(package) - (node.level - 1)] if node.level else []
                out |= _other(base + (node.module.split(".") if node.module else []), [a.name for a in node.names], case_id)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    out |= _other(a.name.split("."), [], case_id)
    return out


def _other(mod: list[str], names: list[str], case_id: str) -> set[str]:
    if mod[:2] != ["pipeline", "cases"]:
        return set()
    found = set()
    for n in names or [None]:
        full = mod + ([n] if n else [])
        # a name is a module when a file of that name exists, else the name is a member of the module before it
        probe = ROOT / "data-pipeline" / Path(*full)
        target = full if probe.with_suffix(".py").is_file() or probe.is_dir() else full[:-1]
        if len(target) < 3:
            continue
        m = re.match(r"c(\d\d)", target[2])
        if m and f"C{m.group(1)}" != case_id:
            found.add(".".join(target))
    return found


def scan_documents(case_id: str) -> set[str]:
    """Document paths of other cases named by a string literal of the producer's files."""
    out: set[str] = set()
    for f in producer_files(case_id):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        table = [n for n in tree.body if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", "") == "DEPENDS_REASONS"]
        skip = {id(c) for t in table for c in ast.walk(t)}          # the reasons table names what is read; it is not a read
        for node in ast.walk(tree):
            if id(node) not in skip and isinstance(node, ast.Constant) and isinstance(node.value, str):
                m = DOC_REF.match(node.value)
                if m and (m.group(1) or m.group(2)) != case_id:
                    out.add(node.value)
    return out


def manifest(case_id: str) -> dict:
    return json.loads((MANIFESTS / f"{case_id}.json").read_text(encoding="utf-8"))


def test_there_are_built_cases():
    assert len(BUILT) == 21


@pytest.mark.parametrize("case_id", BUILT)
def test_every_committed_manifest_has_a_valid_depends_on(case_id):
    from pipeline.core.schemas import validate_document

    man = manifest(case_id)
    assert "depends_on" in man, f"{case_id}: the manifest states no depends_on"
    validate_document(f"data/derived/manifests/{case_id}.json", man)
    dep = man["depends_on"]
    assert dep == sorted(dep, key=lambda d: (d["kind"], d["ref"])), "sorted by kind then ref"
    assert len({(d["kind"], d["ref"]) for d in dep}) == len(dep)
    for d in dep:
        assert set(d) == {"kind", "ref", "reason"} and d["kind"] in ("document", "code")
        assert d["reason"]["en"].strip() and d["reason"]["es"].strip()


def drift(case_id: str, dep: list[dict]) -> dict[str, set[str]]:
    """What a list states that the producer does not read (`stated`) and what the producer reads that the list omits (`omitted`)."""
    read = scan_imports(case_id) | scan_documents(case_id)
    listed = {d["ref"] for d in dep}
    assert all((d["kind"] == "code") == d["ref"].startswith("pipeline.") for d in dep), "the kind follows the reference"
    return {"stated": listed - read, "omitted": read - listed}


@pytest.mark.parametrize("case_id", BUILT)
def test_each_list_is_what_its_producer_reads(case_id):
    assert drift(case_id, manifest(case_id)["depends_on"]) == {"stated": set(), "omitted": set()}


def test_adversarial_a_list_that_differs_from_its_source_is_found():
    """A list written by hand drifts: a document dropped, a module invented, a read of C01 that the producer never makes."""
    dep = manifest("C18")["depends_on"]
    reason = {"en": "x", "es": "y"}
    assert drift("C18", [d for d in dep if d["ref"] != "C11/mixed-2023.json"])["omitted"] == {"C11/mixed-2023.json"}
    assert drift("C18", [*dep, {"kind": "code", "ref": "pipeline.cases.c05_ldp_calibration", "reason": reason}])["stated"] == {"pipeline.cases.c05_ldp_calibration"}
    assert drift("C01", [{"kind": "code", "ref": "pipeline.cases.c10.fed", "reason": reason}])["stated"] == {"pipeline.cases.c10.fed"}
    assert drift("C20", [])["omitted"] == {"pipeline.cases.c01_features", "pipeline.cases.c01_ladder"}


@pytest.mark.parametrize("case_id", BUILT)
def test_every_producer_builds_its_manifest_with_the_list_its_case_derives(case_id):
    """One call of build_case_manifest per case, and its depends_on is `CASE.depends_on()` (or `self.depends_on()` inside the case class), never a literal."""
    calls = []
    for f in producer_files(case_id):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "build_case_manifest":
                calls.append({k.arg: ast.unparse(k.value) for k in node.keywords})
    assert len(calls) == 1, f"{case_id}: {len(calls)} calls of build_case_manifest"
    assert calls[0]["depends_on"] in ("CASE.depends_on()", "self.depends_on()")


def test_the_scan_sees_the_known_producers():
    """The scan itself is not blind: C18 reads seven documents (six before the literal read of C15/long-uf.json) and imports one module of C10; C01 reads nothing of another case."""
    assert scan_imports("C18") == {"pipeline.cases.c10.fed"}
    assert len(scan_documents("C18")) == 7
    assert scan_imports("C01") == set() and scan_documents("C01") == set()
    assert scan_imports("C20") == {"pipeline.cases.c01_features", "pipeline.cases.c01_ladder"}


def test_the_governance_edges_built_from_the_lists_are_the_edges_of_0_15_000():
    from pipeline.governance import edge_table

    mans = {c: manifest(c) for c in BUILT}
    got = {(e["upstream_case"], e["downstream_case"], e["kind"]) for e in edge_table.dependency_edges(mans)}
    assert got == EDGES_0_15_000, f"appear: {sorted(got - EDGES_0_15_000)}; disappear: {sorted(EDGES_0_15_000 - got)}"


def test_adversarial_a_dropped_or_invented_dependency_changes_the_edge_set():
    """The comparison with the 0.15.000 set names the edge that disappears or appears."""
    from pipeline.governance import edge_table

    mans = {c: manifest(c) for c in BUILT}
    dropped = {**mans, "C18": {**mans["C18"], "depends_on": [d for d in mans["C18"]["depends_on"] if not d["ref"].startswith("C11/")]}}
    got = {(e["upstream_case"], e["downstream_case"], e["kind"]) for e in edge_table.dependency_edges(dropped)}
    assert EDGES_0_15_000 - got == {("C11", "C18", "document")}
    invented = {**mans, "C01": {**mans["C01"], "depends_on": [{"kind": "code", "ref": "pipeline.cases.c05_ldp_calibration", "reason": {"en": "x", "es": "y"}}]}}
    got = {(e["upstream_case"], e["downstream_case"], e["kind"]) for e in edge_table.dependency_edges(invented)}
    assert got - EDGES_0_15_000 == {("C05", "C01", "code")}


def test_edges_json_keeps_only_the_related_links():
    table = json.loads(EDGES_JSON.read_text(encoding="utf-8"))
    assert set(table) == {"schema", "description", "tag", "related"}
    assert table["related"]


def test_the_baked_inventory_has_the_same_case_edges():
    from pipeline.governance import bake

    inv = bake.build().inventory
    got = {(e["upstream"].split("/")[0], e["downstream"].split("/")[0], e["kind"]) for e in inv["edges"]}
    assert got == EDGES_0_15_000
    assert len(inv["edges"]) == 21


def test_adversarial_a_manifest_without_depends_on_fails_the_schema_and_stops_the_bake(tmp_path):
    import shutil

    from pipeline.core.schemas import SchemaViolation, validate_document
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    man = manifest("C07")
    del man["depends_on"]
    with pytest.raises(SchemaViolation):
        validate_document("data/derived/manifests/C07.json", man)
    for rel in ("data/derived", "CHANGELOG.md", "data-pipeline/pipeline/governance/inputs.json", "data-pipeline/pipeline/governance/edges.json"):
        src, out = ROOT / rel, tmp_path / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, out, ignore=shutil.ignore_patterns("governance", "regulatory"))
        else:
            shutil.copyfile(src, out)
    (tmp_path / "data/derived/manifests/C07.json").write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(BakeError, match=r"C07.*depends_on"):
        bake.build(tmp_path)


def test_adversarial_the_helper_refuses_a_list_that_differs_from_the_source():
    from pipeline.core.manifest import ContractViolation, derive_depends_on

    assert derive_depends_on("C01", {}) == []
    with pytest.raises(ContractViolation, match="no reason"):
        derive_depends_on("C20", {})
    with pytest.raises(ContractViolation, match="not read"):
        derive_depends_on("C01", {"pipeline.cases.c10.fed": {"en": "x", "es": "y"}})


def _sandbox(tmp_path: Path, case_id: str):
    import shutil

    from pipeline.pipeline import PipelinePaths

    man = manifest(case_id)
    (tmp_path / "manifests").mkdir()
    for art in man["artifacts"]:
        (tmp_path / art["path"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "data" / "derived" / art["path"], tmp_path / art["path"])
    return man, PipelinePaths(root=tmp_path, manifests=tmp_path / "manifests", models=tmp_path / "models")


def test_the_manifests_only_step_restates_the_list_and_touches_nothing_else(tmp_path):
    from pipeline.pipeline import write_manifests_only

    man, paths = _sandbox(tmp_path, "C15")
    old = {k: v for k, v in man.items() if k != "depends_on"}
    (paths.manifests / "C15.json").write_text(json.dumps(old, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    assert write_manifests_only(paths, ["C15"]) == ["C15"]
    again = (paths.manifests / "C15.json").read_bytes()
    assert again == (MANIFESTS / "C15.json").read_bytes(), "byte-identical to the committed manifest"
    assert write_manifests_only(paths, ["C15"]) == ["C15"] and (paths.manifests / "C15.json").read_bytes() == again, "idempotent"


def test_adversarial_the_manifests_only_step_refuses_a_manifest_that_no_longer_describes_its_documents(tmp_path):
    from pipeline.pipeline import write_manifests_only

    man, paths = _sandbox(tmp_path, "C15")
    (paths.manifests / "C15.json").write_text(json.dumps(man, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    victim = tmp_path / man["artifacts"][0]["path"]
    victim.write_bytes(victim.read_bytes() + b" ")
    with pytest.raises(FileNotFoundError, match="size differs"):
        write_manifests_only(paths, ["C15"])


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# U16-P1b fix round (review M1): a cross-case read the derivation cannot name is refused, a run-time built path included
# ---------------------------------------------------------------------------------------------------------------------------------------------------
_CASE_ID = re.compile(r"^C\d\d$")
_CASE_PREFIX = re.compile(r"^(C\d\d)/")


def scan_unnamed(source: str, case_id: str) -> list[str]:
    """The test's own flag rule (written here, not imported from the helper): a string equal to another case id, or a string part of a literal or an
    f-string that starts with another case id and a slash without being a whole document reference. Walks `Constant` nodes, which includes the parts of an f-string."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and not DOC_REF.match(node.value):
            v = node.value
            other = v if _CASE_ID.match(v) else (m.group(1) if (m := _CASE_PREFIX.match(v)) else None)
            if other and other != case_id:
                out.append(v)
    return out


PLANTED_ARGS = [
    ('def f(derived):\n    return derived / "C14" / "svb-2021-2022.json"\n', "C14"),
    ("def f(derived, name):\n    return derived / f\"C15/{name}.json\"\n", "C15/"),
    ('def f(load, name):\n    return load("C15/" + name + ".json")\n', "C15/"),
]


@pytest.mark.parametrize("source,literal", PLANTED_ARGS)
def test_adversarial_a_cross_case_read_built_at_run_time_is_flagged_by_the_test_scan_and_refused_by_the_derivation(source, literal):
    """The D1.5 mutant of the review: the source is built here and scanned; no producer is edited."""
    from pipeline.core.manifest import ContractViolation, scan_source

    assert literal in scan_unnamed(source, "C16")
    docs, unnamed = scan_source("C16", "c16/planted.py", source)
    assert docs == set() and literal in unnamed
    with pytest.raises(ContractViolation, match=rf"c16/planted\.py.*{re.escape(literal)}"):
        from pipeline.core.manifest import refuse_unnamed

        refuse_unnamed("C16", [("c16/planted.py", u) for u in unnamed], {})


def test_a_flagged_occurrence_that_is_a_label_is_accepted_only_through_the_refusal_table():
    from pipeline.core import manifest as m

    src = 'MSG = "C17/models-generator.json has no variant x"\n'
    _, unnamed = m.scan_source("C18", "c18/anchors.py", src)
    assert unnamed == ["C17/models-generator.json has no variant x"]
    assert m.refuse_unnamed("C18", [("c18/anchors.py", "C17/models-generator.json has no variant ")], {}) is None
    with pytest.raises(m.ContractViolation, match="c18/other.py"):
        m.refuse_unnamed("C18", [("c18/other.py", "C17/models-generator.json has no variant ")], {})


def test_the_refusal_table_is_what_the_independent_scan_finds_in_the_producers():
    """Every flagged occurrence of the 21 producers is in the table with a reason, and every table entry occurs in its module (none is a stale entry)."""
    from pipeline.core.manifest import NOT_READS

    found = {}
    for case_id in BUILT:
        for f in producer_files(case_id):
            tree_src = f.read_text(encoding="utf-8")
            for lit in scan_unnamed(tree_src, case_id):
                found[(f.relative_to(CASES_DIR).as_posix(), lit)] = case_id
    # the DEPENDS_REASONS keys are whole refs (not flagged); a flagged literal outside the table is a read the derivation cannot name
    assert set(found) == set(NOT_READS), f"scan only: {sorted(set(found) - set(NOT_READS))}; table only: {sorted(set(NOT_READS) - set(found))}"
    for (module, literal), reason in NOT_READS.items():
        assert (CASES_DIR / module).is_file() and literal in (CASES_DIR / module).read_text(encoding="utf-8")
        assert reason["en"].strip() and reason["es"].strip()


def test_c18_names_the_concrete_c15_document_it_reads_and_it_is_the_default_variant_of_c15():
    refs = {d["ref"] for d in manifest("C18")["depends_on"]}
    assert "C15/long-uf.json" in refs
    assert manifest("C15")["default_variant"] == "long-uf", "C15 changed its default variant: C18 reads C15/long-uf.json and must be changed with it"


def test_adversarial_c18_stops_when_the_default_variant_of_c15_is_no_longer_the_one_it_reads(tmp_path):
    import shutil

    from pipeline.cases.c18 import anchors

    for rel in ("C07", "C11", "C15", "C17", "manifests"):
        shutil.copytree(ROOT / "data" / "derived" / rel, tmp_path / rel, ignore=shutil.ignore_patterns("index.json"))
    man = json.loads((tmp_path / "manifests" / "C15.json").read_text(encoding="utf-8"))
    man["default_variant"] = [a["variant_id"] for a in man["artifacts"] if a["role"] == "variant" and a["variant_id"] != "long-uf"][0]
    (tmp_path / "manifests" / "C15.json").write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(anchors.MissingDocument, match="long-uf"):
        anchors.load_anchors(tmp_path)


def test_adversarial_manifests_only_on_an_unknown_or_unbuilt_case_exits_non_zero_naming_it(tmp_path):
    import subprocess
    import sys

    for case in ("C19", "C99"):
        r = subprocess.run([sys.executable, str(ROOT / "data-pipeline" / "run.py"), case, "--manifests-only", "--output", str(tmp_path)],
                           capture_output=True, text=True, cwd=ROOT / "data-pipeline", timeout=120)
        assert r.returncode != 0, r.stdout
        assert case in r.stderr + r.stdout
