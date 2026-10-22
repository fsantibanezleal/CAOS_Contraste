"""Plants for the contracts feature (CT-001 to CT-014): each test plants the defect its requirement names in a throwaway
copy of the committed files, runs the real gate on the copy, and asserts the clean copy passes and the planted one fails
with the gate's own message."""
from __future__ import annotations

from pathlib import Path

from product_planting import ROOT, edit, edit_json, git_init, load_json, refute, script_gate

EM_DASH = chr(0x2014)
T = "tests/test_contract.py"


def test_ct001_a_pd_outside_its_open_range_is_accepted_when_the_bound_check_is_removed(base_copy: Path, repo: Path) -> None:
    out = refute(base_copy, repo, f"{T}::test_reject_out_of_range",
                 lambda r: edit(r, "data-pipeline/pipeline/io/contract.py",
                                "hi_bad = f.hi is not None and (value >= f.hi if f.hi_open else value > f.hi)", "hi_bad = False"))
    assert "test_reject_out_of_range" in out


def test_ct001_a_value_that_is_not_finite_is_coerced_when_the_parser_is_loosened(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{T}::test_numbers_are_parsed_strictly_never_coerced",
           lambda r: edit(r, "data-pipeline/pipeline/io/contract.py", 'return raw, "not finite"', "return 0.0, None"),
           "not finite")


def test_ct002_a_link_only_source_is_published_when_the_lineage_check_is_removed(base_copy: Path, repo: Path) -> None:
    out = refute(base_copy, repo, "tests/test_licence_lineage.py::test_refuses_link_only_source",
                 lambda r: edit(r, "data-pipeline/pipeline/core/lineage.py", "if inp.klass not in PUBLISHABLE:", "if False:"),
                 "DID NOT RAISE")
    assert "link-only" in out


def test_ct003_an_artifact_without_the_licence_classes_of_its_inputs_is_written(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_licence_lineage.py::test_export_writes_provenance",
           lambda r: edit(r, "data-pipeline/pipeline/core/lineage.py", '"licence_classes": self.classes(),', '"licence_classes": {},'),
           "licence_classes")


def test_ct003_an_unknown_truth_status_is_accepted_when_the_set_is_not_enforced(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_licence_lineage.py::test_export_writes_provenance",
           lambda r: edit(r, "data-pipeline/pipeline/core/lineage.py", "if truth_status not in TRUTH_STATUSES:", "if False:"),
           "DID NOT RAISE")


def test_ct004_a_family_contract_field_dropped_or_added_is_found_by_the_schema(repo: Path) -> None:
    """The contract documents are the pipeline's side of the mirror: a declaration with a field removed or an undeclared
    key added must stop validating against its schema, which is what the generated web types are built from."""
    import sys

    sys.path.insert(0, str(ROOT / "tests" / "contracts"))
    import contract_schemas as cs

    ref = cs.schema_for_document(ROOT / "data/derived/contract/scored_sample.json", load_json(ROOT, "data/derived/contract/scored_sample.json"))
    doc = load_json(repo, "data/derived/contract/scored_sample.json")
    assert cs.errors(ref, doc) == []  # the clean document is valid
    without = {k: v for k, v in doc.items() if k != "fields"}
    assert any("fields" in e for e in cs.errors(ref, without)), cs.errors(ref, without)
    assert any("invented" in e for e in cs.errors(ref, doc | {"invented": 1})), cs.errors(ref, doc | {"invented": 1})


def test_ct005_a_forbidden_licence_in_the_default_install_fails_the_licence_guard(repo: Path) -> None:
    # the clean copy is given the one entry the guard finds missing at this commit (jsonschema), so the plant is the
    # only difference between the passing and the failing run
    table = "data-pipeline/config/licences.json"
    edit_json(repo, table, lambda d: d["python"].setdefault(
        "jsonschema", {"licence": "MIT", "source": "package metadata, jsonschema 4.26.0", "verified": "2026-10-12"}))
    ok = script_gate(repo, "check_licences.py")
    assert ok.returncode == 0 and "OK" in ok.stdout, ok.stdout
    edit_json(repo, table, lambda d: d["python"]["numpy"].update(licence="AGPL-3.0-or-later"))
    r = script_gate(repo, "check_licences.py")
    assert r.returncode == 1 and "numpy" in r.stdout and "forbidden" in r.stdout, r.stdout
    edit_json(repo, table, lambda d: d["python"]["numpy"].update(licence="BSD-3-Clause"))
    edit_json(repo, table, lambda d: d["python"].pop("scipy"))
    r = script_gate(repo, "check_licences.py")
    assert r.returncode == 1 and "scipy has no verified licence" in r.stdout, r.stdout


def test_ct006_a_raw_file_of_a_derived_only_source_in_the_repository_fails_the_data_class_guard(repo: Path) -> None:
    git_init(repo)
    ok = script_gate(repo, "check_data_classes.py")
    assert ok.returncode == 0 and "OK" in ok.stdout, ok.stdout
    registry = load_json(repo, "data-pipeline/config/sources.json")
    derived = next(s["id"] for s in registry["sources"] if s["class"] == "derived-only")
    plant = repo / "data" / "raw" / derived / "rows.csv"
    plant.parent.mkdir(parents=True)
    plant.write_text("id,value\n1,2\n", encoding="utf-8")
    git_init(repo)
    r = script_gate(repo, "check_data_classes.py")
    assert r.returncode == 1 and derived in r.stdout and "rows.csv" in r.stdout, r.stdout


def test_ct007_an_em_dash_and_an_emoji_in_tracked_content_fail_the_content_guard(repo: Path) -> None:
    git_init(repo)
    ok = script_gate(repo, "check_content_standards.py")
    assert ok.returncode == 0 and "OK" in ok.stdout, ok.stdout
    (repo / "docs" / "planted.md").write_text(f"A sentence {EM_DASH} with a dash.\n", encoding="utf-8")
    git_init(repo)
    r = script_gate(repo, "check_content_standards.py")
    assert r.returncode == 1 and "planted.md:1" in r.stdout, r.stdout
    (repo / "docs" / "planted.md").write_text("A sentence with a " + chr(0x1F680) + ".\n", encoding="utf-8")
    git_init(repo)
    r = script_gate(repo, "check_content_standards.py")
    assert r.returncode == 1 and "planted.md:1" in r.stdout, r.stdout


def test_ct008_a_manifest_row_with_a_wrong_hash_is_written_when_the_digest_is_not_recorded(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_sources.py::test_fetch_writes_manifest_row",
           lambda r: edit(r, "data-pipeline/pipeline/io/fetch.py", '"sha256": sha, "bytes": size,', '"sha256": "0" * 64, "bytes": size,'),
           "sha256")


def test_ct009_a_source_with_an_unknown_class_is_loaded_when_the_class_is_not_checked(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        def mutate(d: dict) -> None:
            d["sources"][0]["class"] = "public"
        edit_json(r, "data-pipeline/config/sources.json", mutate)

    refute(base_copy, repo, "tests/test_sources.py::test_registry_classes_valid", plant, "RegistryError")


def test_ct009_a_case_reads_a_link_only_source_when_the_read_check_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_sources.py::test_registry_classes_valid",
           lambda r: edit(r, "data-pipeline/pipeline/io/sources.py",
                          'raise LicenceError(f"{case_id}: {sid} is {src.klass}; it may be linked, never read")', "pass"),
           "link-only")


def test_ct010_a_data_root_inside_the_repository_is_accepted_when_the_check_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_sources.py::test_data_root_outside_repository",
           lambda r: edit(r, "data-pipeline/pipeline/io/fetch.py", "if root == repo or repo in root.parents:", "if False:"),
           "DID NOT RAISE")


def test_ct011_a_changed_file_is_accepted_without_refresh_when_the_pin_is_not_compared(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_sources.py::test_hash_drift_fails",
           lambda r: edit(r, "data-pipeline/pipeline/io/fetch.py",
                          'if old is not None and old["sha256"] != sha and not refresh:', "if False:"),
           "DID NOT RAISE")


def test_ct012_a_changed_rounding_makes_the_examples_differ_from_the_committed_bytes(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_own_sample.py::test_examples_regenerate_identically",
           lambda r: edit(r, "data-pipeline/pipeline/io/examples.py", "rng.beta(a, b, N), 6)", "rng.beta(a, b, N), 5)"),
           "scored_sample_")


def test_ct012_a_committed_example_edited_by_hand_no_longer_regenerates(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        p = r / "data" / "examples" / "scored_sample_development.csv"
        p.write_bytes(p.read_bytes().replace(b"D00001,", b"D99999,", 1))

    refute(base_copy, repo, "tests/test_own_sample.py::test_examples_regenerate_identically", plant,
           "scored_sample_development.csv")


def test_ct013_a_shifted_sample_that_is_not_shifted_is_green_and_an_uncalibrated_one_is_red(base_copy: Path, repo: Path) -> None:
    dev = "data/examples/scored_sample_development.csv"
    cur = "data/examples/scored_sample_current.csv"
    # the current sample replaced by the development one: nothing is shifted, so the PSI cannot be red
    refute(base_copy, repo, "tests/test_own_sample.py::test_shifted_underestimated_sample_is_found",
           lambda r: (r / cur).write_bytes((r / dev).read_bytes().replace(b"D0", b"C0")), "stability.psi")

    # the development sample with every PD tripled: no longer calibrated by construction
    def triple(r: Path) -> None:
        lines = (r / dev).read_text(encoding="utf-8").splitlines()
        out = [lines[0]]
        for ln in lines[1:]:
            c = ln.split(",")
            c[3] = f"{min(0.999, float(c[3]) * 3):.6f}"
            out.append(",".join(c))
        (r / dev).write_bytes(("\n".join(out) + "\n").encode("utf-8"))

    refute(base_copy, repo, "tests/test_own_sample.py::test_calibrated_sample_passes_the_level_tests", triple, "red")


def test_ct014_a_record_outside_contract_one_reaches_the_battery_when_the_contract_is_bypassed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_own_sample.py::test_contract_rejects_before_the_battery",
           lambda r: edit(r, "data-pipeline/pipeline/own_sample.py",
                          'rows = [r for r in report.accepted if r.get("pd") is not None]',
                          'rows = [dict(r, pd=float(r["pd"]), target=int(r["target"])) for r in read_csv_rows(path)'
                          ' if r.get("pd") not in (None, "")]'),
           "pd must lie strictly between 0 and 1")


def test_ct014_a_report_is_written_inside_the_repository_when_the_location_check_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, "tests/test_own_sample.py::test_report_never_written_inside_the_repository",
           lambda r: edit(r, "data-pipeline/pipeline/own_sample.py", "if out == REPO or REPO in out.parents:", "if False:"),
           "DID NOT RAISE")
