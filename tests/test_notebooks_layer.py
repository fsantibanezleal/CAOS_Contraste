"""The notebooks layer and the README by areas (unit U17-A; CAOS_MANAGE conventions/product-notebooks.md).

The gates of docs/design/features/notebooks/ (NB-001 to NB-019) and docs/design/features/repository/ (RP-001 to RP-005).
The checks themselves are the template's scripts, adopted byte for byte (scripts/check_notebooks.py,
scripts/run_notebooks.py, scripts/check_readme_areas.py); these tests run them on the repository and, for every
requirement, plant a defect in a copy of the committed set and expect the real check to name it. The copy lives in
pytest's temporary folder; the repository is never written.

BS claims: the SDD lists eight claims (BS-1 to BS-8). The adopted check requires a level 4 notebook in each language for
every claim, and those notebooks come with their topic units (U17-B onwards), so until they land the check reports each
claim as covered by no level 4 notebook. ``PENDING_CLAIMS`` names exactly those claims; a topic unit's integrator removes
a claim from it when its level 4 notebook is committed, and the test then holds the claim to the check.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
LANGS = ("en", "es")
TOPIC_01 = "01-getting-started"
PENDING_CLAIMS = frozenset(f"BS-{k}" for k in range(1, 9))
ENGINE_PIN = "0.8.0"  # the PyPI pin of the notebooks; the engine release tag is the same number, zero-padded (X.XX.XXX)
ENGINE_TAG = "v%d.%02d.%03d" % tuple(int(part) for part in ENGINE_PIN.split("."))
ENGINE_RELEASE = f"https://github.com/fsantibanezleal/CAOS_RiskValidation/releases/tag/{ENGINE_TAG}"

# sha256 of the three adopted scripts at the template release 0.10 (git show of scripts/<name> at its tag)
ADOPTED = {
    "check_notebooks.py": "827f67ebd495ea643ef814c0d33378e46f6ed232937f2bb192daf2458c13fc50",
    "run_notebooks.py": "f5caebdefbe98ce23e733198c7c8157c9683f76f0340a6dc613f90b27c6f6123",
    "check_readme_areas.py": "1eb76a810d13aeebf12809a69490e8e1cac4cdf6f51516e0568e9d2c717e96e2",
}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"u17a_{name}", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NOTEBOOKS = _load("check_notebooks")
AREAS = _load("check_readme_areas")


# ---- helpers -------------------------------------------------------------------------------------------------------


def uncovered(finding: str) -> bool:
    """A finding that only says a pending claim has no level 4 notebook yet."""
    return any(f"beyond: the SDD claim {c} is covered by no level 4 notebook" in finding for c in PENDING_CLAIMS)


def findings_of(root: Path) -> list[str]:
    return [f for f in NOTEBOOKS.findings_of(root) if not uncovered(f)]


def kind(findings: list[str], word: str) -> list[str]:
    return [f for f in findings if f": {word}:" in f]


def read_nb(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_nb(path: Path, nb: dict) -> None:
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def notebooks(root: Path, lang: str = "en") -> list[Path]:
    return sorted((root / "notebooks" / lang).glob("*/*.ipynb"))


def copy_set(dest: Path) -> Path:
    """A copy of what the static checks read: the notebooks, the SDD, the README, the workflows, the data the notebooks
    declare and the pipeline's engine modules."""
    shutil.copytree(ROOT / "notebooks", dest / "notebooks")
    shutil.copytree(ROOT / ".github", dest / ".github")
    (dest / "docs" / "design").mkdir(parents=True)
    shutil.copy(ROOT / "docs" / "design" / "SDD.md", dest / "docs" / "design" / "SDD.md")
    shutil.copy(ROOT / "README.md", dest / "README.md")
    for path in sorted((ROOT / "data-pipeline").glob("**/model/*.py")):
        target = dest / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, target)
    for path in notebooks(dest, "en"):
        for data in read_nb(path)["metadata"]["caos"]["data"]:
            target = dest / data
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / data, target)
    return dest


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    copy = copy_set(tmp_path / "copy")
    assert findings_of(copy) == [], "the control copy must pass before anything is planted"
    return copy


def code_cells(nb: dict) -> list[dict]:
    return [c for c in nb["cells"] if c["cell_type"] == "code"]


def markdown_cells(nb: dict) -> list[dict]:
    return [c for c in nb["cells"] if c["cell_type"] == "markdown"]


def edit_both(root: Path, name: str, mutate) -> None:
    """Apply one change to a notebook in both trees (a change the mirror must not see)."""
    for lang in LANGS:
        for path in (root / "notebooks" / lang).glob(f"*/{name}"):
            nb = read_nb(path)
            mutate(nb)
            write_nb(path, nb)


def claim_blocks(sdd: str) -> dict[str, str]:
    """The text of each claim of the SDD section 'Beyond the state of the art', keyed by its identifier."""
    lines = sdd.splitlines()
    start = next(i for i, ln in enumerate(lines) if re.match(r"^##\s+Beyond the state of the art\s*$", ln))
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^##\s+(?!#)", lines[i])), len(lines))
    blocks: dict[str, list[str]] = {}
    current = None
    for ln in lines[start + 1:end]:
        m = re.match(r"^- \*\*(BS-\d+)\*\*", ln)
        if m:
            current = m[1]
            blocks[current] = [ln]
        elif current and (ln.startswith(" ") or not ln.strip()):
            blocks[current].append(ln)
        elif ln.startswith("#"):
            current = None
    return {k: "\n".join(v) for k, v in blocks.items()}


def evidence_gaps(sdd: str) -> list[str]:
    """Claims without a committed evidence path, and evidence paths that do not exist (relative to the repository)."""
    out = []
    for claim, text in claim_blocks(sdd).items():
        paths = [p for p in re.findall(r"`([^`\s]+/[^`\s]*)`", text) if not p.startswith("http")]
        if not paths:
            out.append(f"{claim}: names no committed evidence path")
        out += [f"{claim}: {p} does not exist" for p in paths if not (ROOT / p).exists()]
    return out


FORBIDDEN = re.compile(r"CONTRASTE_DATA|CONTRASTE_MODELS|\.write_text\(|\.write_bytes\(|open\([^)]*['\"][wa]b?['\"]|to_json\(|json\.dump\(")


def touches_the_data_root_or_writes(source: str) -> bool:
    """A code cell that needs the data root (a notebook reads committed files only) or writes a file."""
    return bool(FORBIDDEN.search(source))


def recomputes_without_the_baked_version(source: str) -> bool:
    """A notebook that reads the test rows of a committed artifact (a file of data/derived) and never prints the engine version
    that baked them."""
    return '["tests"]' in source and "derived" in source and "riskvalidation_version" not in source


def run_checker(script: str, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), str(root)], capture_output=True, text=True, check=False)


# ---- NB gates: the committed set --------------------------------------------------------------------------------------


def test_the_notebooks_layout_is_complete():
    found = findings_of(ROOT)
    assert kind(found, "layout") == []
    for name in ("README.md", "requirements.txt", "en/README.md", "es/README.md"):
        assert (ROOT / "notebooks" / name).read_text(encoding="utf-8").strip(), name


def test_the_two_trees_mirror_each_other():
    en = {p.relative_to(ROOT / "notebooks" / "en").as_posix() for p in (ROOT / "notebooks" / "en").rglob("*")}
    es = {p.relative_to(ROOT / "notebooks" / "es").as_posix() for p in (ROOT / "notebooks" / "es").rglob("*")}
    assert en == es and kind(findings_of(ROOT), "mirror") == []


def test_topics_and_notebooks_are_numbered_without_gaps():
    assert kind(findings_of(ROOT), "numbering") == []


def test_levels_never_decrease_and_every_topic_has_levels_one_and_two():
    levels = [read_nb(p)["metadata"]["caos"]["level"] for p in notebooks(ROOT)]
    assert levels == sorted(levels) and {1, 2} <= set(levels)
    assert kind(findings_of(ROOT), "levels") == []


def test_every_index_row_gives_its_reason_and_lists_every_notebook():
    assert kind(findings_of(ROOT), "index") == [] and kind(findings_of(ROOT), "levels") == []
    for lang, marker in (("en", "No level 3:"), ("es", "Sin nivel 3:")):
        index = (ROOT / "notebooks" / lang / "README.md").read_text(encoding="utf-8")
        row = next(ln for ln in index.splitlines() if TOPIC_01 in ln and marker in ln)
        assert len(row.split(marker, 1)[1].split()) >= 4
        for path in notebooks(ROOT, lang):
            assert path.name in index


def test_every_sdd_claim_is_covered_by_a_level_four_notebook_or_is_pending():
    claims, problem = NOTEBOOKS.sdd_claims(ROOT)
    assert problem is None and claims == {f"BS-{k}" for k in range(1, 9)}
    for lang in LANGS:
        covered = set()
        for path in notebooks(ROOT, lang):
            caos = read_nb(path)["metadata"]["caos"]
            if caos["level"] == 4:
                covered |= set(caos["beyond"])
        assert claims - covered == PENDING_CLAIMS & claims, f"{lang}: a claim is neither covered nor pending"
    assert [f for f in NOTEBOOKS.findings_of(ROOT) if "beyond" in f and not uncovered(f)] == []


def test_every_sdd_claim_names_its_committed_evidence():
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    assert sorted(claim_blocks(sdd)) == [f"BS-{k}" for k in range(1, 9)]
    assert evidence_gaps(sdd) == []


def test_every_notebook_has_the_anatomy_of_its_level():
    found = findings_of(ROOT)
    assert kind(found, "anatomy") == []
    for lang in LANGS:
        for path in notebooks(ROOT, lang):
            nb = read_nb(path)
            assert nb["cells"][0]["cell_type"] == "markdown"
            sections = [ln for c in markdown_cells(nb) for ln in "".join(c["source"]).splitlines() if ln.startswith("## ")]
            assert len(sections) == 7, (path.name, sections)


def test_the_metadata_agrees_with_the_tree_the_pins_and_the_repository():
    assert kind(findings_of(ROOT), "metadata") == []
    pins = NOTEBOOKS.read_pins(ROOT)
    assert f"riskvalidation=={ENGINE_PIN}" in pins
    for lang in LANGS:
        for path in notebooks(ROOT, lang):
            caos = read_nb(path)["metadata"]["caos"]
            assert caos["language"] == lang and caos["topic"] == path.parent.name
            assert set(caos["packages"]) <= pins and all((ROOT / d).is_file() for d in caos["data"])


def test_the_committed_outputs_are_clean_and_in_order():
    found = findings_of(ROOT)
    for word in ("execution", "output", "path", "secret", "size"):
        assert kind(found, word) == [], word
    for path in notebooks(ROOT) + notebooks(ROOT, "es"):
        counts = [c["execution_count"] for c in code_cells(read_nb(path))]
        assert counts == list(range(1, len(counts) + 1)), path.name


def test_a_spanish_notebook_has_the_cells_the_english_one_has():
    assert kind(findings_of(ROOT), "mirror") == []
    for en in notebooks(ROOT):
        es = ROOT / "notebooks" / "es" / en.parent.name / en.name
        a, b = read_nb(en), read_nb(es)
        assert [c["cell_type"] for c in a["cells"]] == [c["cell_type"] for c in b["cells"]]
        a_out = [json.dumps(c["outputs"], sort_keys=True) for c in code_cells(a) if all(o["output_type"] == "stream" for o in c["outputs"])]
        b_out = [json.dumps(c["outputs"], sort_keys=True) for c in code_cells(b) if all(o["output_type"] == "stream" for o in c["outputs"])]
        assert a_out == b_out, f"{en.name}: the printed outputs of the two trees differ"


def test_a_notebook_never_installs_and_never_needs_the_data_root_or_writes_the_repository():
    assert kind(findings_of(ROOT), "anatomy") == []
    for lang in LANGS:
        for path in notebooks(ROOT, lang):
            nb = read_nb(path)
            for cell in code_cells(nb):
                assert not touches_the_data_root_or_writes("".join(cell["source"])), path.name
            text = "\n".join("".join(c["source"]) for c in markdown_cells(nb))
            assert "pip install -r notebooks/requirements.txt" in text


def test_every_code_cell_is_explained_and_commented():
    for lang in LANGS:
        for path in notebooks(ROOT, lang):
            previous = None
            for cell in read_nb(path)["cells"]:
                if cell["cell_type"] == "code":
                    assert previous == "markdown", f"{path.name}: a code cell with no explanation before it"
                    assert any(ln.lstrip().startswith("#") for ln in cell["source"]), f"{path.name}: a code cell with no comment"
                previous = cell["cell_type"]


def test_every_source_a_notebook_cites_is_listed_in_the_sdd_and_in_its_references():
    assert kind(findings_of(ROOT), "sources") == []
    for lang in LANGS:
        for path in notebooks(ROOT, lang):
            caos = read_nb(path)["metadata"]["caos"]
            assert caos["sources"] and all(s.startswith("https://") for s in caos["sources"])


def test_the_notebook_pins_are_exact_and_the_sdd_technology_table_holds_them():
    assert kind(findings_of(ROOT), "pins") == []
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    rows = {}
    for line in sdd.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 3:
            rows[cells[1]] = cells[2]
    # riskvalidation is pinned by commit in the pipeline's requirements until the release tag replaces it (SDD row);
    # the notebooks pin the release, 0.8.0, and the two pins become one at the release that carries the set
    for line in NOTEBOOKS.requirement_lines(ROOT):
        name, version = line.split("==")
        if name == "riskvalidation":
            assert name in rows
        else:
            assert rows.get(name) == version, f"{name} {version} is not a row of the SDD technology table"


def test_the_ci_runs_the_static_checks_and_never_the_notebooks():
    assert kind(findings_of(ROOT), "ci") == []
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python scripts/check_notebooks.py" in ci and "python scripts/check_readme_areas.py" in ci
    assert all("run_notebooks" not in p.read_text(encoding="utf-8") for p in (ROOT / ".github" / "workflows").glob("*.y*ml"))


def test_the_adopted_scripts_are_the_template_scripts_byte_for_byte():
    for name, digest in ADOPTED.items():
        data = (SCRIPTS / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest, f"{name} differs from the template release 0.10"


@pytest.mark.skipif(not (ROOT / ".venv-notebooks").exists(), reason="the notebook environment .venv-notebooks is a local release gate (ADR-0074)")
def test_every_notebook_runs_top_to_bottom_in_a_fresh_kernel():
    done = subprocess.run([sys.executable, str(SCRIPTS / "run_notebooks.py"), "--check"], capture_output=True, text=True, check=False,
                          cwd=ROOT, timeout=3000)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    assert "nothing written" in done.stdout


def test_a_notebook_that_reads_test_rows_prints_the_engine_version_that_baked_them():
    for lang in LANGS:
        for path in notebooks(ROOT, lang):
            source = "\n".join("".join(c["source"]) for c in code_cells(read_nb(path)))
            assert not recomputes_without_the_baked_version(source), path.name


def test_topic_one_has_its_four_notebooks_in_both_languages():
    plan = [1, 1, 1, 2]
    for lang in LANGS:
        found = notebooks(ROOT, lang)
        got = [p for p in found if p.parent.name == TOPIC_01]
        assert [read_nb(p)["metadata"]["caos"]["level"] for p in got] == plan
        assert [p.name[:2] for p in got] == ["01", "02", "03", "04"]


# ---- NB adversarial: a defect planted in a copy of the committed set --------------------------------------------------


def test_adversarial_a_missing_spanish_index_is_found(repo):
    (repo / "notebooks" / "es" / "README.md").unlink()
    assert any("notebooks/es/README.md" in f and "layout" in f for f in findings_of(repo))


def test_adversarial_a_spanish_notebook_deleted_breaks_the_mirror(repo):
    victim = notebooks(repo, "es")[-1]
    victim.unlink()
    assert any("absent from the es tree" in f and victim.name in f for f in findings_of(repo))


def test_adversarial_a_numbering_gap_in_both_trees_is_found(repo):
    for lang in LANGS:
        folder = repo / "notebooks" / lang / TOPIC_01
        first = sorted(folder.glob("*.ipynb"))[1]
        first.rename(folder / ("05" + first.name[2:]))
    assert kind(findings_of(repo), "numbering")


def test_adversarial_a_level_that_decreases_and_a_missing_level_two_are_found(repo):
    def raise_first(nb):
        nb["metadata"]["caos"]["level"] = 3

    edit_both(repo, notebooks(repo)[0].name, raise_first)
    assert any("levels" in f for f in findings_of(repo))


def test_adversarial_a_missing_reason_and_an_unlisted_notebook_are_found(repo):
    index = repo / "notebooks" / "en" / "README.md"
    text = index.read_text(encoding="utf-8")
    index.write_text(text.replace("No level 3:", "Level 3 is not needed:"), encoding="utf-8")
    es_index = repo / "notebooks" / "es" / "README.md"
    es_text = es_index.read_text(encoding="utf-8")
    victim = notebooks(repo)[0].name
    es_index.write_text(es_text.replace(victim, "removed.ipynb"), encoding="utf-8")
    found = findings_of(repo)
    assert any("gives no reason" in f for f in found) and any(victim in f and "not listed" in f for f in found)


def test_adversarial_a_claim_with_no_level_four_notebook_and_a_notebook_claiming_an_unlisted_one_are_found(repo):
    sdd = repo / "docs" / "design" / "SDD.md"
    sdd.write_text(sdd.read_text(encoding="utf-8") + "\n\n## Planted\n\nnothing\n", encoding="utf-8")
    edit_both(repo, notebooks(repo)[0].name, lambda nb: nb["metadata"]["caos"].update({"level": 4, "beyond": ["BS-99"]}))
    found = NOTEBOOKS.findings_of(repo)
    assert any("BS-99" in f and "not a claim" in f for f in found)
    assert any("covered by no level 4 notebook" in f for f in found)


def test_adversarial_a_claim_without_committed_evidence_is_found():
    planted = "## Beyond the state of the art\n\n- **BS-1** A claim with no path.\n  Beyond: nothing.\n- **BS-2** A claim with a missing path.\n  Evidence: `data/derived/none/missing.json`.\n\n## Next\n"
    gaps = evidence_gaps(planted)
    assert "BS-1: names no committed evidence path" in gaps and "BS-2: data/derived/none/missing.json does not exist" in gaps


def test_adversarial_a_renamed_section_and_a_title_cell_turned_into_code_are_found(repo):
    def rename(nb):
        for c in markdown_cells(nb):
            c["source"] = [s.replace("## Results", "## Findings").replace("## Resultados", "## Hallazgos") for s in c["source"]]
        nb["cells"][0]["cell_type"] = "code"
        nb["cells"][0]["outputs"], nb["cells"][0]["execution_count"] = [], None

    edit_both(repo, notebooks(repo)[0].name, rename)
    found = kind(findings_of(repo), "anatomy")
    assert any("Findings" in f or "Hallazgos" in f for f in found) and any("first cell" in f for f in found)


def test_adversarial_a_code_cell_stripped_of_its_comment_and_its_explanation_is_found(repo):
    def strip(nb):
        cell = code_cells(nb)[1]
        cell["source"] = [ln for ln in cell["source"] if not ln.lstrip().startswith("#")]
        index = nb["cells"].index(cell)
        del nb["cells"][index - 1]

    edit_both(repo, notebooks(repo)[1].name, strip)
    found = kind(findings_of(repo), "anatomy")
    assert any("no comment" in f for f in found) and any("not preceded by a markdown cell" in f for f in found)


def test_adversarial_a_package_data_path_and_widget_metadata_that_disagree_are_found(repo):
    def plant(nb):
        nb["metadata"]["caos"]["packages"] = ["riskvalidation==9.9.9"]
        nb["metadata"]["caos"]["data"] = ["data/derived/none/missing.json"]
        nb["metadata"]["widgets"] = {"state": {}}
        code_cells(nb)[0]["metadata"] = {"execution": {"iopub": "x"}}

    edit_both(repo, notebooks(repo)[0].name, plant)
    found = kind(findings_of(repo), "metadata")
    assert any("9.9.9" in f for f in found) and any("missing.json" in f for f in found)
    assert any("widgets" in f for f in found) and any("cell 2 metadata" in f or "cell" in f for f in found)


def test_adversarial_an_error_a_stderr_stream_a_machine_path_and_a_token_are_found(repo):
    def plant(nb):
        cell = code_cells(nb)[0]
        cell["execution_count"] = 9
        cell["outputs"] = [
            {"output_type": "error", "ename": "ValueError", "evalue": "x", "traceback": ["Traceback (most recent call last)"]},
            {"output_type": "stream", "name": "stderr", "text": ["warning\n"]},
            {"output_type": "stream", "name": "stdout", "text": ["C:\\\\Users\\\\someone\\\\file.csv\n"]},
        ]
        markdown_cells(nb)[1]["source"].append("\ntoken: ghp_" + "a" * 30)

    edit_both(repo, notebooks(repo)[0].name, plant)
    found = findings_of(repo)
    assert kind(found, "output") and kind(found, "execution") and kind(found, "path") and kind(found, "secret")


def test_adversarial_an_image_above_the_limit_is_found(repo):
    def plant(nb):
        code_cells(nb)[0]["outputs"] = [{"output_type": "display_data", "metadata": {}, "data": {"image/png": "A" * 600_000}}]

    edit_both(repo, notebooks(repo)[0].name, plant)
    assert any("an image" in f and "limit" in f for f in kind(findings_of(repo), "size"))


def test_adversarial_a_cell_deleted_from_the_spanish_counterpart_is_found(repo):
    path = notebooks(repo, "es")[0]
    nb = read_nb(path)
    nb["cells"].pop()
    write_nb(path, nb)
    assert any("not a full counterpart" in f for f in kind(findings_of(repo), "mirror"))


def test_adversarial_a_notebook_that_runs_pip_is_found(repo):
    def plant(nb):
        code_cells(nb)[0]["source"].append("\n%pip install riskvalidation")

    edit_both(repo, notebooks(repo)[0].name, plant)
    assert any("runs pip" in f for f in kind(findings_of(repo), "anatomy"))


def test_adversarial_a_notebook_that_reads_the_data_root_or_writes_the_repository_is_seen_by_the_gate():
    for planted in ('os.environ["CONTRASTE_DATA"]', 'Path("x").write_text("y")', 'open("x", "w")', "json.dump(a, f)", "frame.to_json(path)"):
        assert touches_the_data_root_or_writes(planted), planted
    assert not touches_the_data_root_or_writes('json.loads(Path("x").read_text())')


def test_adversarial_a_source_the_sdd_does_not_list_and_a_reference_that_is_missing_are_found(repo):
    def plant(nb):
        nb["metadata"]["caos"]["sources"].append("https://doi.org/10.1000/never-listed")

    edit_both(repo, notebooks(repo)[0].name, plant)
    found = kind(findings_of(repo), "sources")
    assert any("never-listed" in f and "SDD" in f for f in found) and any("never-listed" in f and "References" in f for f in found)


def test_adversarial_an_unpinned_notebook_requirement_is_found(repo):
    path = repo / "notebooks" / "requirements.txt"
    path.write_text(path.read_text(encoding="utf-8") + "pandas>=2\n", encoding="utf-8")
    assert any("pandas>=2" in f for f in kind(findings_of(repo), "pins"))


def test_adversarial_a_ci_that_runs_the_notebooks_and_one_that_drops_the_static_step_are_found(repo):
    workflows = repo / ".github" / "workflows"
    (workflows / "notebooks.yml").write_text("name: x\njobs:\n  a:\n    steps:\n      - run: python scripts/run_notebooks.py\n", encoding="utf-8")
    ci = workflows / "ci.yml"
    ci.write_text(ci.read_text(encoding="utf-8").replace("python scripts/check_notebooks.py", "python scripts/other.py"), encoding="utf-8")
    found = kind(findings_of(repo), "ci")
    assert any("never CI" in f for f in found) and any("check_notebooks.py" in f for f in found)


def test_adversarial_a_changed_adopted_script_is_not_the_template_script(tmp_path):
    changed = (SCRIPTS / "check_notebooks.py").read_bytes().replace(b"MAX_NOTEBOOK_BYTES = 3_000_000", b"MAX_NOTEBOOK_BYTES = 9_000_000")
    assert changed != (SCRIPTS / "check_notebooks.py").read_bytes()
    assert hashlib.sha256(changed.replace(b"\r\n", b"\n")).hexdigest() != ADOPTED["check_notebooks.py"]


@pytest.mark.skipif(not (ROOT / ".venv-notebooks").exists(), reason="the notebook environment .venv-notebooks is a local release gate (ADR-0074)")
def test_adversarial_a_hand_edited_output_fails_the_release_gate(repo):
    # local-only: the execution gate needs the notebook environment, which CI does not install
    (repo / "scripts").mkdir()
    shutil.copy(SCRIPTS / "run_notebooks.py", repo / "scripts" / "run_notebooks.py")
    shutil.copytree(ROOT / "data-pipeline", repo / "data-pipeline", dirs_exist_ok=True)
    shutil.copy(ROOT / "VERSION", repo / "VERSION")
    if sys.platform == "win32":
        link = subprocess.run(["cmd", "/c", "mklink", "/J", str(repo / ".venv-notebooks"), str(ROOT / ".venv-notebooks")],
                              capture_output=True, text=True, check=False)
        if link.returncode != 0:
            pytest.skip("a directory junction to the notebook environment could not be made")
    else:
        (repo / ".venv-notebooks").symlink_to(ROOT / ".venv-notebooks", target_is_directory=True)
    target = notebooks(repo)[0]
    nb = read_nb(target)
    cell = next(c for c in code_cells(nb) if any(o["output_type"] == "stream" for o in c["outputs"]))
    next(o for o in cell["outputs"] if o["output_type"] == "stream")["text"] = ["edited by hand\n"]
    write_nb(target, nb)
    done = subprocess.run([sys.executable, str(repo / "scripts" / "run_notebooks.py"), "--check", "--only", str(target)],
                          capture_output=True, text=True, check=False, timeout=900)
    assert done.returncode == 1 and "stale" in done.stdout, done.stdout[-1500:]


def test_adversarial_a_notebook_that_recomputes_without_the_baked_version_is_seen_by_the_gate():
    planted = 'DERIVED = ROOT / "data" / "derived"\nrows = holdout["tests"]\nprint(rows[0])'
    assert recomputes_without_the_baked_version(planted)
    assert not recomputes_without_the_baked_version(planted + '\nprint(holdout["provenance"]["riskvalidation_version"])')


def test_adversarial_topic_one_with_a_dropped_notebook_loses_its_plan(repo):
    for lang in LANGS:
        (repo / "notebooks" / lang / TOPIC_01 / sorted(p.name for p in (repo / "notebooks" / lang / TOPIC_01).glob("*.ipynb"))[-1]).unlink()
    got = [read_nb(p)["metadata"]["caos"]["level"] for p in notebooks(repo)]
    assert got != [1, 1, 1, 2]


# ---- RP gates: the README by areas -------------------------------------------------------------------------------------


def test_the_readme_has_the_areas_section_with_a_row_for_every_area():
    assert AREAS.findings_of(ROOT) == []
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert re.search(r"^## Areas\s*$", text, re.M)
    section = text.split("## Areas", 1)[1]
    for area, _folders in AREAS.AREAS:
        assert re.search(rf"^\| {re.escape(area)} \|", section, re.M), area


def test_every_area_row_states_active_or_dormant_with_a_reason():
    section = (ROOT / "README.md").read_text(encoding="utf-8").split("## Areas", 1)[1].split("\n## ", 1)[0]
    rows = [ln for ln in section.splitlines() if ln.startswith("| ") and not ln.startswith("| Area") and not ln.startswith("|---")]
    assert len(rows) == len(AREAS.AREAS)
    for row in rows:
        status = [c.strip() for c in row.strip("|").split("|")][2].lower()
        assert status.startswith(("active", "dormant")), row
        if status.startswith("dormant"):
            assert len(status.split(":", 1)[1].split()) >= 3


def test_every_folder_and_document_an_area_row_links_exists():
    section = (ROOT / "README.md").read_text(encoding="utf-8").split("## Areas", 1)[1].split("\n## ", 1)[0]
    links = [t.split("#")[0] for t in re.findall(r"\]\(([^)\s]+)\)", section) if not re.match(r"^[a-z]+:", t)]
    assert links and all((ROOT / t).exists() for t in links)


def test_the_packages_row_links_the_engine_release():
    section = (ROOT / "README.md").read_text(encoding="utf-8").split("## Areas", 1)[1].split("\n## ", 1)[0]
    row = next(ln for ln in section.splitlines() if ln.startswith("| Packages"))
    assert ENGINE_RELEASE in row and "riskvalidation" in row
    assert "not yet published on PyPI" in row


def test_the_areas_section_follows_the_purpose_and_the_live_urls():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    before = text.split("## Areas", 1)[0]
    assert "https://contraste.fasl-work.com" in before and AREAS.preamble_findings(before.splitlines()) == []


# ---- RP adversarial -----------------------------------------------------------------------------------------------------


def readme_copy(tmp_path: Path) -> Path:
    root = tmp_path / "readme"
    root.mkdir()
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    (root / "README.md").write_text(text, encoding="utf-8")
    for link in re.findall(r"\]\(([^)\s]+)\)", text.split("## Areas", 1)[1].split("\n## ", 1)[0]):
        if re.match(r"^[a-z]+:", link):
            continue
        target = root / link.split("#")[0]
        if link.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x", encoding="utf-8")
    return root


def test_adversarial_a_readme_without_areas_and_a_dropped_area_row_are_found(tmp_path):
    root = readme_copy(tmp_path)
    assert run_checker("check_readme_areas.py", root).returncode == 0
    path = root / "README.md"
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace("## Areas", "## What is in it"), encoding="utf-8")
    assert run_checker("check_readme_areas.py", root).returncode == 1
    path.write_text("\n".join(ln for ln in original.splitlines() if not ln.startswith("| Notebooks")) + "\n", encoding="utf-8")
    done = run_checker("check_readme_areas.py", root)
    assert done.returncode == 1 and "Notebooks" in done.stdout


def test_adversarial_a_row_with_no_status_and_a_dormant_row_with_no_reason_are_found(tmp_path):
    root = readme_copy(tmp_path)
    path = root / "README.md"
    original = path.read_text(encoding="utf-8")
    broken = re.sub(r"(\| Data \|[^|]*\|)[^|]*\|", r"\1 someday |", original, count=1)
    path.write_text(broken, encoding="utf-8")
    assert "Data" in run_checker("check_readme_areas.py", root).stdout
    path.write_text(re.sub(r"dormant: [^|]*\|", "dormant: no |", original, count=1), encoding="utf-8")
    assert "dormant" in run_checker("check_readme_areas.py", root).stdout


def test_adversarial_a_folder_link_that_does_not_exist_is_found(tmp_path):
    root = readme_copy(tmp_path)
    shutil.rmtree(root / "deploy")
    done = run_checker("check_readme_areas.py", root)
    assert done.returncode == 1 and "deploy/" in done.stdout


def test_adversarial_a_packages_row_without_the_release_link_is_found(tmp_path):
    root = readme_copy(tmp_path)
    path = root / "README.md"
    path.write_text(path.read_text(encoding="utf-8").replace(ENGINE_RELEASE, "https://example.org/x"), encoding="utf-8")
    done = run_checker("check_readme_areas.py", root)
    assert done.returncode == 1 and "Packages" in done.stdout


def test_adversarial_the_areas_section_moved_above_the_purpose_is_found(tmp_path):
    root = readme_copy(tmp_path)
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    head, rest = text.split("## Areas", 1)
    area_block = "## Areas" + rest.split("\n## ", 1)[0]
    others = "## " + rest.split("\n## ", 1)[1] if "\n## " in rest else ""
    path.write_text("# Contraste\n\n" + area_block + "\n\n" + head.split("# Contraste", 1)[1] + "\n" + others, encoding="utf-8")
    done = run_checker("check_readme_areas.py", root)
    assert done.returncode == 1 and "purpose" in done.stdout
