"""The generated convergence verdict (unit U16-V; ADR-0075 section 4; decisions D16-2, D16-9, D16-11).

The gates of docs/design/features/release-1-0/ (CV-001 to CV-013). The script reads the requirement rows of both repositories
and the result files of the release run (pytest JUnit XML of each repository, the vitest JSON report) and writes
docs/design/features/release-1-0/verdict.md. These tests build small worlds in pytest's temporary folder (two repositories
with requirement files, result files written by hand, scripts that exit 0 or 1) and run the real script on them; the
repository is never written.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "convergence_verdict.py"
RELEASE = ROOT / "docs" / "design" / "features" / "release-1-0"


def _load():
    spec = importlib.util.spec_from_file_location("u16v_convergence_verdict", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


CV = _load()

# ---- the world -----------------------------------------------------------------------------------------------------------


def requirements(rows: list[tuple[str, str]]) -> str:
    """A requirements.md with one row per (id, gate cell)."""
    lines = ["# Requirements: a fixture", "", "Status: live", "", "| ID | Requirement | Gate |", "|---|---|---|"]
    lines += [f"| {rid} | THE fixture SHALL hold. | {gate} |" for rid, gate in rows]
    return "\n".join(lines) + "\n"


def write_repo(root: Path, features: dict[str, list[tuple[str, str]]]) -> Path:
    (root / "docs" / "design" / "features").mkdir(parents=True, exist_ok=True)
    for name, rows in features.items():
        folder = root / "docs" / "design" / "features" / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "requirements.md").write_text(requirements(rows), encoding="utf-8")
    return root


def junit(path: Path, cases: list[tuple], timestamp: str = "2026-10-20T10:00:00.000000") -> Path:
    """A pytest --junitxml file. A case is (classname, name, status[, message]), status passed, failed or skipped."""
    out = ['<?xml version="1.0" encoding="utf-8"?>', f'<testsuites><testsuite name="pytest" timestamp="{timestamp}">']
    for case in cases:
        classname, name, status = case[:3]
        message = case[3] if len(case) > 3 else ""
        out.append(f'<testcase classname="{classname}" name="{name}" time="0.001">')
        if status == "failed":
            out.append('<failure message="assert False">trace</failure>')
        elif status == "skipped":
            out.append(f'<skipped type="pytest.skip" message="{message}">skipped</skipped>')
        out.append("</testcase>")
    out.append("</testsuite></testsuites>")
    path.write_text("\n".join(out), encoding="utf-8")
    return path


def vitest(path: Path, files: dict[str, list[tuple[str, str]]], start_ms: int = 1_781_949_600_000) -> Path:
    """A vitest --reporter=json file: {absolute test file: [(title, status)]}."""
    results = []
    for name, tests in files.items():
        results.append({"name": name, "assertionResults": [
            {"title": title, "fullName": f"a suite {title}", "ancestorTitles": ["a suite"], "status": status} for title, status in tests]})
    path.write_text(json.dumps({"startTime": start_ms, "testResults": results}), encoding="utf-8")
    return path


class World:
    """Two repositories, three result files and the output path of one verdict run."""

    def __init__(self, tmp: Path, product: dict, engine: dict, product_cases=(), engine_cases=(), vitest_files=None):
        self.tmp = tmp
        self.product = write_repo(tmp / "product", product)
        self.engine = write_repo(tmp / "engine", engine)
        self.product_junit = junit(tmp / "product.xml", list(product_cases))
        self.engine_junit = junit(tmp / "engine.xml", list(engine_cases))
        self.vitest = vitest(tmp / "vitest.json", vitest_files or {})
        self.out = tmp / "out" / "verdict.md"

    def args(self, *extra: str) -> list[str]:
        return ["--product-repo", str(self.product), "--engine-repo", str(self.engine), "--product-junit", str(self.product_junit),
                "--engine-junit", str(self.engine_junit), "--vitest", str(self.vitest), "--out", str(self.out), *extra]

    def run(self, *extra: str) -> int:
        return CV.main(self.args(*extra))

    def text(self) -> str:
        return self.out.read_text(encoding="utf-8")


def sub(tmp: Path, name: str) -> Path:
    path = tmp / name
    path.mkdir()
    return path


def table_rows(text: str) -> list[tuple[str, str, str, str, str]]:
    """(repository, feature, id, result, detail) for every line of the requirements table of a verdict."""
    found = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 6 and cells[2] not in {"id", "---"} and not set(cells[0]) <= set("-: "):
            found.append((cells[0], cells[1], cells[2], cells[4], cells[5]))
    return found


def rows_of(text: str) -> dict[tuple[str, str], tuple[str, str]]:
    """(repository, id) -> (result, detail); an ID used by two features keeps the later row (see table_rows)."""
    return {(repo, rid): (result, detail) for repo, _feature, rid, result, detail in table_rows(text)}


def result_of(text: str, rid: str, repo: str = "contraste") -> str:
    return rows_of(text)[(repo, rid)][0]


def case(path: str, name: str, status: str = "passed", message: str = "") -> tuple:
    """A JUnit case for tests/x.py::name, written as pytest does (dotted classname)."""
    return (path.removesuffix(".py").replace("/", "."), name, status, message)


# ---- the four results ------------------------------------------------------------------------------------------------------


def test_a_passed_a_failed_a_skipped_and_an_absent_gate_are_each_listed_with_their_result(tmp_path):
    world = World(
        tmp_path,
        {"f1": [("CT-001", "`tests/test_a.py::test_ok`"), ("CT-002", "`tests/test_a.py::test_bad`"),
                ("CT-003", "`tests/test_a.py::test_skip`"), ("CT-004", "`tests/test_a.py::test_missing`")]},
        {},
        [case("tests/test_a.py", "test_ok"), case("tests/test_a.py", "test_bad", "failed"),
         case("tests/test_a.py", "test_skip", "skipped", "no network")],
    )
    assert world.run() == 1
    text = world.text()
    assert [result_of(text, f"CT-00{i}") for i in (1, 2, 3, 4)] == ["passed", "failed", "skipped", "absent"]
    assert "no network" in rows_of(text)[("contraste", "CT-003")][1]
    assert "NOT CONVERGED" in text


def test_every_requirement_row_of_both_repositories_is_listed_once(tmp_path):
    world = World(
        tmp_path,
        {"b": [("CT-002", "`tests/test_a.py::test_one`")], "a": [("CT-001", "`tests/test_a.py::test_one`")]},
        {"e1": [("RV-001", "`tests/test_e.py::test_one`")], "e2": [("RV-002", "`tests/test_e.py::test_one`")]},
        [case("tests/test_a.py", "test_one")],
        [case("tests/test_e.py", "test_one")],
    )
    assert world.run() == 0
    found = rows_of(world.text())
    assert sorted(found) == [("contraste", "CT-001"), ("contraste", "CT-002"), ("riskvalidation", "RV-001"), ("riskvalidation", "RV-002")]
    ids = [line.split("|")[3].strip() for line in world.text().splitlines() if re.match(r"\| (contraste|riskvalidation) \| \S+ \| [A-Z]{2}-", line)]
    assert ids == ["CT-001", "CT-002", "RV-001", "RV-002"]  # sorted by repository, feature and id
    assert "CONVERGED" in world.text() and "NOT CONVERGED" not in world.text()


def test_an_id_used_by_two_features_is_listed_in_both_and_named_in_its_own_section(tmp_path):
    gate = "`tests/test_a.py::test_one`"
    world = World(tmp_path, {}, {"u1": [("RV-001", gate)], "u2": [("RV-001", gate)], "u3": [("RV-002", gate)]}, [], [case("tests/test_a.py", "test_one")])
    assert world.run() == 0
    text = world.text()
    assert [r[:3] for r in table_rows(text)] == [("riskvalidation", "u1", "RV-001"), ("riskvalidation", "u2", "RV-001"), ("riskvalidation", "u3", "RV-002")]
    assert "- riskvalidation RV-001: u1, u2" in text and "RV-002: u3" not in text


# ---- several tests, parameters, classes -------------------------------------------------------------------------------------


def test_a_gate_that_names_several_tests_passes_only_if_all_of_them_pass(tmp_path):
    gate = "`tests/test_a.py::test_one` and `tests/test_a.py::test_two`"
    for second, expected in (("passed", "passed"), ("failed", "failed"), (None, "absent"), ("skipped", "skipped")):
        cases = [case("tests/test_a.py", "test_one")] + ([case("tests/test_a.py", "test_two", second)] if second else [])
        world = World(sub(tmp_path, second or "none"), {"f": [("CT-001", gate)]}, {}, cases)
        world.run()
        assert result_of(world.text(), "CT-001") == expected


def test_a_parametrized_test_counts_as_passed_only_if_every_parameter_passed(tmp_path):
    ok = World(sub(tmp_path, "ok"), {"f": [("CT-001", "`tests/test_a.py::test_p`")]}, {}, [case("tests/test_a.py", f"test_p[{i}]") for i in range(3)])
    ok.run()
    assert result_of(ok.text(), "CT-001") == "passed"
    cases = [case("tests/test_a.py", "test_p[0]"), case("tests/test_a.py", "test_p[1]", "failed"), case("tests/test_a.py", "test_p[2]")]
    bad = World(sub(tmp_path, "bad"), {"f": [("CT-001", "`tests/test_a.py::test_p`")]}, {}, cases)
    assert bad.run() == 1
    assert result_of(bad.text(), "CT-001") == "failed"
    one = World(sub(tmp_path, "one"), {"f": [("CT-001", "`tests/test_a.py::test_p[1]`")]}, {}, cases)
    one.run()
    assert result_of(one.text(), "CT-001") == "failed"  # a gate that names a parameter reads that parameter only
    zero = World(sub(tmp_path, "zero"), {"f": [("CT-001", "`tests/test_a.py::test_p[0]`")]}, {}, cases)
    zero.run()
    assert result_of(zero.text(), "CT-001") == "passed"


def test_a_method_of_a_test_class_and_a_whole_test_file_are_read_from_the_dotted_classname(tmp_path):
    cases = [("tests.sub.test_a.TestGroup", "test_method", "passed"), ("tests.sub.test_a", "test_plain", "passed"),
             ("tests.sub.test_b", "test_x", "passed"), ("tests.sub.test_b", "test_y", "failed")]
    rows = [("CT-001", "`tests/sub/test_a.py::test_method`"), ("CT-002", "`tests/sub/test_a.py::TestGroup::test_method`"),
            ("CT-003", "`tests/sub/test_a.py`"), ("CT-004", "`tests/sub/test_b.py`")]
    world = World(tmp_path, {"f": rows}, {}, cases)
    world.run()
    assert [result_of(world.text(), f"CT-00{i}") for i in (1, 2, 3, 4)] == ["passed", "passed", "passed", "failed"]


def test_a_vitest_gate_reads_the_title_in_the_named_file(tmp_path):
    files = {"D:/repo/frontend/src/engine/credit.test.ts": [("holds the parity", "passed"), ("holds the bounds", "failed"), ("later", "pending")],
             "D:/repo/frontend/src/other/credit.test.ts": [("holds the bounds", "passed")]}
    rows = [("CT-001", "`frontend/src/engine/credit.test.ts::holds the parity`"), ("CT-002", "`frontend/src/engine/credit.test.ts::holds the bounds`"),
            ("CT-003", "`frontend/src/engine/credit.test.ts::later`"), ("CT-004", "`frontend/src/engine/credit.test.ts::never written`")]
    world = World(tmp_path, {"f": rows}, {}, vitest_files=files)
    world.run()
    assert [result_of(world.text(), f"CT-00{i}") for i in (1, 2, 3, 4)] == ["passed", "failed", "skipped", "absent"]


# ---- scripts ------------------------------------------------------------------------------------------------------------------


def test_a_script_gate_is_run_by_the_verdict_and_its_exit_code_is_the_result(tmp_path):
    rows = [("CT-001", "`scripts/ok.py`"), ("CT-002", "`scripts/bad.py`"), ("CT-003", "`scripts/slow.py`")]
    world = World(tmp_path, {"f": rows}, {})
    scripts = world.product / "scripts"
    scripts.mkdir()
    (scripts / "ok.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    (scripts / "bad.py").write_text("import sys\nprint('broken')\nsys.exit(1)\n", encoding="utf-8")
    (scripts / "slow.py").write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    assert world.run("--script-timeout", "2") == 1
    found = rows_of(world.text())
    assert found[("contraste", "CT-001")][0] == "passed"
    assert found[("contraste", "CT-002")][0] == "failed" and "exit 1" in found[("contraste", "CT-002")][1]
    assert found[("contraste", "CT-003")][0] == "failed" and "timed out" in found[("contraste", "CT-003")][1]


def test_an_engine_script_gate_runs_in_the_engine_repository(tmp_path):
    world = World(tmp_path, {}, {"e": [("RV-001", "`scripts/only_engine.py`")]})
    (world.engine / "scripts").mkdir()
    (world.engine / "scripts" / "only_engine.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    assert world.run() == 0
    assert result_of(world.text(), "RV-001", "riskvalidation") == "passed"


def test_a_script_gate_that_is_missing_on_disk_is_absent(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`scripts/nowhere.py`")]}, {})
    assert world.run() == 1
    assert result_of(world.text(), "CT-001") == "absent"


# ---- the engine's file ----------------------------------------------------------------------------------------------------------


def test_an_engine_gate_is_looked_up_in_the_engines_file_never_the_products(tmp_path):
    node = "`tests/governance/test_x.py::test_same_node`"
    only_product = World(sub(tmp_path, "p"), {}, {"e": [("RV-001", node)]}, [case("tests/governance/test_x.py", "test_same_node")], [])
    assert only_product.run() == 1
    assert result_of(only_product.text(), "RV-001", "riskvalidation") == "absent"
    only_engine = World(sub(tmp_path, "e"), {}, {"e": [("RV-001", node)]}, [], [case("tests/governance/test_x.py", "test_same_node")])
    assert only_engine.run() == 0
    assert result_of(only_engine.text(), "RV-001", "riskvalidation") == "passed"
    product_row = World(sub(tmp_path, "pr"), {"f": [("CT-001", node)]}, {}, [], [case("tests/governance/test_x.py", "test_same_node")])
    assert product_row.run() == 1  # and a product gate is never read from the engine's file
    assert result_of(product_row.text(), "CT-001") == "absent"


# ---- skips ----------------------------------------------------------------------------------------------------------------------


def test_a_skipped_gate_never_counts_as_passed(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_s`"), ("CT-002", "`tests/test_a.py::test_ok`")]}, {},
                  [case("tests/test_a.py", "test_s", "skipped", "slow lane"), case("tests/test_a.py", "test_ok")])
    assert world.run() == 1
    text = world.text()
    assert result_of(text, "CT-001") == "skipped"
    counts = dict(re.findall(r"^\| (passed|failed|skipped|absent) \| (\d+) \|", text, re.M))
    assert counts == {"passed": "1", "failed": "0", "skipped": "1", "absent": "0"}


def test_a_skip_for_a_device_precondition_is_allowed_only_when_the_run_states_the_device(tmp_path):
    cases = [case("tests/test_a.py", "test_raw", "skipped", "requires_raw: the raw files are in the data root"), case("tests/test_a.py", "test_ok")]
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_raw`"), ("CT-002", "`tests/test_a.py::test_ok`")]}, {}, cases)
    assert world.run() == 1  # no device stated: a skip is not converged
    assert "NOT CONVERGED" in world.text()
    assert world.run("--device", "default device, data root present") == 0
    text = world.text()
    assert result_of(text, "CT-001") == "skipped" and "default device, data root present" in text and "NOT CONVERGED" not in text
    # a skip that is not a device precondition is never allowed, whatever device is stated
    cases[0] = case("tests/test_a.py", "test_raw", "skipped", "flaky on Tuesdays")
    other = World(sub(tmp_path, "o"), {"f": [("CT-001", "`tests/test_a.py::test_raw`")]}, {}, cases)
    assert other.run("--device", "default device") == 1


# ---- determinism, missing data, exit codes -----------------------------------------------------------------------------------------


def test_the_same_result_files_give_the_same_bytes_and_the_date_comes_from_them(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {"e": [("RV-001", "`tests/test_e.py::test_one`")]},
                  [case("tests/test_a.py", "test_one")], [case("tests/test_e.py", "test_one")])
    world.run()
    first = world.out.read_bytes()
    world.out.unlink()
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    done = subprocess.run([sys.executable, str(SCRIPT), *world.args()], cwd=elsewhere, capture_output=True, text=True, check=False)
    assert done.returncode == 0 and world.out.read_bytes() == first
    assert "2026-10-20" in first.decode("utf-8")  # the timestamp of the JUnit files
    junit(world.product_junit, [case("tests/test_a.py", "test_one")], timestamp="2026-11-02T08:00:00.000000")
    world.run()
    assert "2026-11-02" in world.text()  # the latest date of the result files, never the clock


def test_a_missing_result_file_exits_2_names_the_file_and_the_command_and_writes_no_verdict(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {})
    for attr, command in (("product_junit", "pytest"), ("engine_junit", "pytest"), ("vitest", "--reporter=json")):
        saved = getattr(world, attr)
        saved_text = saved.read_text(encoding="utf-8")
        saved.unlink()
        done = subprocess.run([sys.executable, str(SCRIPT), *world.args()], capture_output=True, text=True, check=False)
        assert done.returncode == 2, attr
        assert str(saved) in done.stderr and command in done.stderr and "--" in done.stderr
        assert not world.out.exists()
        saved.write_text(saved_text, encoding="utf-8")


def test_a_feature_folder_with_no_rows_is_reported_and_the_verdict_is_not_converged(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {}, [case("tests/test_a.py", "test_one")])
    empty = world.product / "docs" / "design" / "features" / "empty"
    empty.mkdir()
    (empty / "requirements.md").write_text("# Requirements: nothing yet\n\nStatus: live\n", encoding="utf-8")
    assert world.run() == 1
    text = world.text()
    assert "Features with no requirement rows" in text and "contraste: empty" in text and "NOT CONVERGED" in text


def test_the_sample_flag_marks_the_document_as_a_sample(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {}, [case("tests/test_a.py", "test_one")])
    world.run()
    assert "SAMPLE" not in world.text()
    world.run("--sample")
    assert "SAMPLE" in world.text().splitlines()[0]


# ---- the shared parser ------------------------------------------------------------------------------------------------------------


def test_the_requirement_rows_come_from_check_sdd_by_import_never_a_copy():
    source = SCRIPT.read_text(encoding="utf-8")
    assert re.search(r"^\s+import check_sdd", source, re.M) and "check_sdd.requirement_rows(" in source
    assert not re.search(r"^def (requirement_rows|strip_markup|strip_fences)", source, re.M)
    assert CV.check_sdd.requirement_rows.__module__ == "check_sdd"


# ---- adversarial: a verdict that says more than the run did ---------------------------------------------------------------------------


def test_adversarial_a_gate_whose_name_is_a_prefix_of_a_passed_test_is_absent_not_passed(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_ab`"), ("CT-002", "`tests/test_a.py::test_a`")]}, {},
                  [case("tests/test_a.py", "test_abc"), case("tests/test_a.py", "test_ab_other")])
    assert world.run() == 1
    assert [result_of(world.text(), "CT-001"), result_of(world.text(), "CT-002")] == ["absent", "absent"]


def test_adversarial_a_failed_test_planted_in_a_converged_run_flips_the_verdict(tmp_path):
    cases = [case("tests/test_a.py", "test_one"), case("tests/test_a.py", "test_two")]
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`"), ("CT-002", "`tests/test_a.py::test_two`")]}, {}, cases)
    assert world.run() == 0 and "NOT CONVERGED" not in world.text()
    junit(world.product_junit, [cases[0], case("tests/test_a.py", "test_two", "failed")])
    assert world.run() == 1 and result_of(world.text(), "CT-002") == "failed" and "NOT CONVERGED" in world.text()


def test_adversarial_a_test_file_of_the_same_name_in_another_folder_is_not_the_gate(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/c02/test_x.py::test_one`")]}, {}, [case("tests/c03/test_x.py", "test_one")])
    assert world.run() == 1
    assert result_of(world.text(), "CT-001") == "absent"


def test_adversarial_a_junit_with_no_testcases_makes_every_gate_absent(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {}, [])
    assert world.run() == 1 and result_of(world.text(), "CT-001") == "absent"


def test_adversarial_a_skip_with_a_made_up_device_reason_is_not_allowed_even_when_a_device_is_stated(tmp_path):
    cases = [case("tests/test_a.py", "test_s", "skipped", "the data root is somewhere else, trust me not")]
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_s`")]}, {}, cases)
    assert world.run("--device", "any device") == 0  # a reason that names the data root is a device precondition ...
    cases[0] = case("tests/test_a.py", "test_s", "skipped", "temporarily disabled")
    junit(world.product_junit, cases)
    assert world.run("--device", "any device") == 1  # ... one that does not is never allowed
    assert result_of(world.text(), "CT-001") == "skipped" and "NOT CONVERGED" in world.text()


def test_adversarial_a_script_that_prints_ok_and_exits_non_zero_is_failed(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`scripts/liar.py`")]}, {})
    (world.product / "scripts").mkdir()
    (world.product / "scripts" / "liar.py").write_text("import sys\nprint('OK, everything passed')\nsys.exit(3)\n", encoding="utf-8")
    assert world.run() == 1
    assert result_of(world.text(), "CT-001") == "failed" and "exit 3" in rows_of(world.text())[("contraste", "CT-001")][1]


def test_adversarial_a_passed_product_case_never_satisfies_an_engine_gate(tmp_path):
    node = "`tests/test_x.py::test_same`"
    world = World(tmp_path, {"f": [("CT-001", node)]}, {"e": [("RV-001", node)]}, [case("tests/test_x.py", "test_same")], [])
    assert world.run() == 1
    assert result_of(world.text(), "CT-001") == "passed" and result_of(world.text(), "RV-001", "riskvalidation") == "absent"


def test_adversarial_a_changed_result_file_changes_the_bytes_and_an_unchanged_one_does_not(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {}, [case("tests/test_a.py", "test_one")])
    world.run()
    first = world.out.read_bytes()
    world.run()
    assert world.out.read_bytes() == first
    junit(world.product_junit, [case("tests/test_a.py", "test_one", "failed")])
    world.run()
    assert world.out.read_bytes() != first


def test_adversarial_a_stale_verdict_is_left_alone_when_a_result_file_is_missing(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {}, [case("tests/test_a.py", "test_one")])
    world.out.parent.mkdir()
    world.out.write_text("an earlier verdict\n", encoding="utf-8")
    world.vitest.unlink()
    assert world.run() == 2
    assert world.out.read_text(encoding="utf-8") == "an earlier verdict\n"


def test_adversarial_a_folder_with_only_a_status_line_and_a_prose_id_is_not_a_converged_feature(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {}, [case("tests/test_a.py", "test_one")])
    folder = world.product / "docs" / "design" / "features" / "prose"
    folder.mkdir()
    (folder / "requirements.md").write_text("# Requirements\n\nStatus: live\n\n- CT-900 THE feature SHALL work.\n", encoding="utf-8")
    assert world.run() == 1
    assert "contraste: prose" in world.text() and ("contraste", "CT-900") not in rows_of(world.text())


def copy_findings(source: str) -> list[str]:
    """What the script must not contain: its own copy of the parser that scripts/check_sdd.py owns."""
    bad = [f"defines {name}" for name in ("requirement_rows", "strip_markup", "strip_fences", "gate_findings")
           if re.search(rf"^\s*def {name}\b", source, re.M)]
    if not re.search(r"^\s+import check_sdd\b", source, re.M):
        bad.append("does not import check_sdd")
    return bad


def test_adversarial_a_copied_parser_in_the_script_is_found():
    source = SCRIPT.read_text(encoding="utf-8")
    assert copy_findings(source) == []
    assert copy_findings(source + "\n\ndef requirement_rows(text):\n    return [], []\n") == ["defines requirement_rows"]
    assert copy_findings(source.replace("import check_sdd", "import json")) == ["does not import check_sdd"]


def skeleton_world(tmp_path: Path, status: str) -> World:
    world = World(tmp_path, {"f": [("CT-001", "`scripts/check_skeleton.py`")]}, {})
    (world.product / "scripts").mkdir()
    for name in ("check_skeleton.py", "check_contracts.py"):
        (world.product / "scripts" / name).write_text((ROOT / "scripts" / name).read_text(encoding="utf-8"), encoding="utf-8")
    catalog = world.product / "docs" / "contracts" / "catalog.md"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(f"# Catalog\n\n| id | provider | status |\n|---|---|---|\n| one | real:x | real |\n| two | fixture:y | {status} |\n", encoding="utf-8")
    return world


def test_adversarial_a_provider_left_on_a_boundary_fails_the_skeleton_gate_of_the_verdict(tmp_path):
    clean = skeleton_world(sub(tmp_path, "clean"), "real")
    assert clean.run() == 0 and result_of(clean.text(), "CT-001") == "passed"
    planted = skeleton_world(sub(tmp_path, "planted"), "fixture")
    assert planted.run() == 1
    assert result_of(planted.text(), "CT-001") == "failed" and "exit 2" in rows_of(planted.text())[("contraste", "CT-001")][1]


def verdict_findings(text: str) -> list[str]:
    """A generated verdict is self-consistent: the counts are the rows, and the verdict line follows from them."""
    found = [row[3] for row in table_rows(text)]
    counts = dict(re.findall(r"^\| (passed|failed|skipped|absent) \| (\d+) \|", text, re.M))
    bad = [f"{k}: counted {counts.get(k)}, listed {found.count(k)}" for k in ("passed", "failed", "skipped", "absent") if int(counts.get(k, -1)) != found.count(k)]
    converged = "Verdict: **CONVERGED**" in text
    if converged and any(r in {"failed", "absent"} for r in found):
        bad.append("converged with a failed or absent row")
    return bad


def test_the_committed_verdict_is_self_consistent_and_a_hand_edit_is_found():
    text = (RELEASE / "verdict.md").read_text(encoding="utf-8")
    assert verdict_findings(text) == []


def test_adversarial_a_verdict_edited_by_hand_is_found(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`tests/test_a.py::test_one`")]}, {}, [case("tests/test_a.py", "test_one", "failed")])
    world.run()
    text = world.text()
    assert verdict_findings(text) == []
    assert verdict_findings(text.replace("| failed |", "| passed |", 1))  # a row changed, the counts say otherwise
    assert verdict_findings(text.replace("Verdict: **NOT CONVERGED**", "Verdict: **CONVERGED**")) == ["converged with a failed or absent row"]


# ---- the release folder ---------------------------------------------------------------------------------------------------------------


def test_the_release_folder_states_the_requirements_the_format_and_the_sample_verdict():
    design = (RELEASE / "design.md").read_text(encoding="utf-8")
    for needed in ("--product-junit", "--engine-junit", "--vitest", "--device", "NOT CONVERGED", "exit 2"):
        assert needed in design, needed
    verdict = (RELEASE / "verdict.md").read_text(encoding="utf-8")
    assert verdict.splitlines()[0].startswith("# Convergence verdict") and "SAMPLE" in verdict.splitlines()[0]
    assert "Verdict: **NOT CONVERGED**" in verdict
    assert len(table_rows(verdict)) > 100 and "## Requirement IDs used by more than one feature" in verdict


def tasks_findings(features: Path) -> list[str]:
    """The feature folders whose tasks.md lacks the section Convergence verdict or the pointer at the release verdict."""
    bad = []
    for folder in sorted(p for p in features.iterdir() if p.is_dir()):
        path = folder / "tasks.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not re.search(r"^## Convergence verdict\s*$", text, re.M) or "release-1-0/verdict.md" not in text:
            bad.append(folder.name)
    return bad


def test_every_feature_task_list_points_at_the_release_verdict():
    features = ROOT / "docs" / "design" / "features"
    assert len([p for p in features.iterdir() if p.is_dir()]) >= 27 and (features / "release-1-0").is_dir()
    assert tasks_findings(features) == []


def test_adversarial_a_task_list_without_the_verdict_section_is_found(tmp_path):
    features = tmp_path / "features"
    good = "# Tasks\n\n## Convergence verdict\n\nSee ../release-1-0/verdict.md.\n"
    no_section = "# Tasks\n\nSee release-1-0/verdict.md.\n"
    no_pointer = "# Tasks\n\n## Convergence verdict\n\nConverged.\n"
    for name, text in (("good", good), ("no-section", no_section), ("no-pointer", no_pointer)):
        (features / name).mkdir(parents=True)
        (features / name / "tasks.md").write_text(text, encoding="utf-8")
    (features / "no-file").mkdir()
    assert tasks_findings(features) == ["no-file", "no-pointer", "no-section"]


def test_the_script_argument_table_names_only_scripts_that_exist():
    for script in CV.SCRIPT_ARGS:
        assert (ROOT / script).is_file(), script
    assert CV.SCRIPT_ARGS["scripts/check_skeleton.py"] == ["docs/contracts/catalog.md"]


@pytest.mark.parametrize("token", ["release 1.0", "convergence_verdict"])
def test_the_script_documents_its_usage(token):
    done = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, check=False)
    assert done.returncode == 0 and "--product-junit" in done.stdout
    assert token in (done.stdout + SCRIPT.read_text(encoding="utf-8"))


def test_the_gate_of_an_engine_row_is_plain_text_so_it_is_not_read_as_a_path_of_this_repository(tmp_path):
    gate = "`tests/test_x.py::test_one`"
    world = World(tmp_path, {"f": [("CT-001", gate)]}, {"e": [("RV-001", gate)]}, [case("tests/test_x.py", "test_one")], [case("tests/test_x.py", "test_one")])
    world.run()
    lines = {line.split("|")[3].strip(): line for line in world.text().splitlines() if line.startswith(("| contraste | f", "| riskvalidation | e"))}
    assert "`tests/test_x.py::test_one`" in lines["CT-001"] and "`" not in lines["RV-001"]


def test_the_output_of_a_failing_script_is_stable_between_runs_even_when_it_prints_a_port_or_a_path(tmp_path):
    world = World(tmp_path, {"f": [("CT-001", "`scripts/noisy.py`")]}, {})
    (world.product / "scripts").mkdir()
    noisy = [
        "import os, sys, time",
        "print('FAIL the page at http://127.0.0.1:%d/ in %s at %s' % (50000 + os.getpid() % 9000, os.path.abspath(sys.argv[0]), time.strftime('%H:%M:%S')))",
        "sys.exit(1)",
    ]
    (world.product / "scripts" / "noisy.py").write_text(chr(10).join(noisy) + chr(10), encoding="utf-8")
    world.run()
    first = world.out.read_bytes()
    time.sleep(1.1)
    world.run()
    assert world.out.read_bytes() == first and b"127.0.0.1:PORT" in first and b"<path>" in first
