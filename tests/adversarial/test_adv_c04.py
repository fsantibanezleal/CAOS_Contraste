"""Plants for C04 (CT-401 to CT-409, CT-414, CT-415): a defect planted in a copy of the fetcher, the reader or the committed
artifacts, the existing gate run on the copy, red on the plant and green on the clean copy. The web requirements of the
case (CT-410 to CT-413) are planted in test_adv_web.py."""
from __future__ import annotations

from pathlib import Path

from product_planting import edit, edit_json, refute

C04 = "tests/test_c04.py"
CEREP = "tests/test_cerep.py"
CEREP_SRC = "data-pipeline/pipeline/io/cerep.py"


def _edit(rel: str, fn):
    return lambda r: edit_json(r, rel, fn)


def test_ct401_requests_sent_without_the_pace_are_found_by_the_pacing_check(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{CEREP}::test_fetch_plan_paced_and_cached",
           lambda r: edit(r, CEREP_SRC, "if wait > 0:", "if False:"), "test_fetch_plan_paced_and_cached")


def test_ct401_a_file_already_present_is_refetched_when_the_cache_check_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{CEREP}::test_fetch_plan_paced_and_cached",
           lambda r: edit(r, CEREP_SRC, "if dest.exists() and not refresh:", "if False:"), "test_fetch_plan_paced_and_cached")


def test_ct402_a_label_that_is_not_on_the_agencys_scale_is_mapped_when_the_refusal_is_removed(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{CEREP}::test_reader_maps_every_agency",
           lambda r: edit(r, CEREP_SRC, "raise CerepError(f\"{cra}: the label {label!r} is not on the agency's scale\") from None", "return 0"),
           "test_reader_maps_every_agency")


def test_ct403_a_one_year_pd_that_is_not_defaulted_over_cohort_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        o = d["outputs"]
        for k, c in enumerate(o["cohorts"]):
            for g in range(7):
                if c["defaulted"] is not None and c["defaulted_cohort"][g] and o["pd"]["d2"][k][g]:
                    o["pd"]["d2"][k][g] *= 1.5
                    return
        raise AssertionError("no cohort and grade with a defaulted count to plant in")

    refute(base_copy, repo, f"{C04}::test_pd_definitions", _edit("data/derived/C04/sp.json", mutate), "test_pd_definitions")


def test_ct404_a_pooled_matrix_whose_row_does_not_sum_to_one_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["pooled"]["matrix"][0][0] += 0.1

    refute(base_copy, repo, f"{C04}::test_agency_statistics", _edit("data/derived/C04/sp.json", mutate), "test_agency_statistics")


def test_ct405_a_generator_family_not_drawn_from_the_em_generator_of_sp_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["generator"]["q"][0][0] *= 1.01

    refute(base_copy, repo, f"{C04}::test_generator_families", _edit("data/derived/C04/markov.json", mutate), "test_generator_families")


def test_ct406_a_published_cell_that_stops_agreeing_with_its_print_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        next(r for r in d["outputs"]["irw"]["rows"] if r["agrees"])["agrees"] = False

    refute(base_copy, repo, f"{C04}::test_published_answers", _edit("data/derived/C04/published.json", mutate), "test_published_answers")


def test_ct406_a_printed_matrix_entry_of_the_paper_in_the_artifact_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["engelmann"]["note"] = "the paper reprints 0.9276 as the first entry"

    refute(base_copy, repo, f"{C04}::test_published_answers", _edit("data/derived/C04/published.json", mutate), "test_published_answers")


def test_ct407_a_table_without_esmas_attribution_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["attribution"] = "Source: ESMA"

    refute(base_copy, repo, f"{C04}::test_attribution_and_definitions", _edit("data/derived/C04/sp.json", mutate),
           "test_attribution_and_definitions")


def test_ct407_a_pd_definition_missing_from_a_variant_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        del d["outputs"]["pd"]["d3"]

    refute(base_copy, repo, f"{C04}::test_attribution_and_definitions", _edit("data/derived/C04/fitch.json", mutate),
           "test_attribution_and_definitions")


def test_ct408_a_finding_evidenced_by_a_value_not_in_its_artifact_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["findings"][0]["evidence"] = ["pd.nothing@nowhere"]

    refute(base_copy, repo, f"{C04}::test_findings_and_ranges", _edit("data/derived/C04/sp.json", mutate), "test_findings_and_ranges")


def test_ct408_a_declared_range_dropped_from_the_manifest_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["expect"].popitem()

    refute(base_copy, repo, f"{C04}::test_findings_and_ranges", _edit("data/derived/manifests/C04.json", mutate),
           "test_findings_and_ranges")


def test_ct409_a_variant_with_the_wrong_truth_status_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["provenance"]["truth_status"] = "synthetic-known-truth"

    refute(base_copy, repo, f"{C04}::test_lineage_and_determinism", _edit("data/derived/C04/sp.json", mutate),
           "test_lineage_and_determinism")


def test_ct409_a_seed_that_depends_on_the_clock_is_found_by_the_determinism_check(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{C04}::test_lineage_and_determinism",
           lambda r: edit(r, "data-pipeline/pipeline/cases/c04_families.py",
                          'return int(np.random.SeedSequence([case_seed, zlib.crc32(key.encode("utf-8"))]).generate_state(1)[0])',
                          'return int(np.random.SeedSequence([case_seed, zlib.crc32(key.encode("utf-8")), __import__("time").time_ns()]).generate_state(1)[0])'),
           "test_lineage_and_determinism")


def test_ct414_a_case_page_with_a_pending_section_is_found(base_copy: Path, repo: Path) -> None:
    def plant(r: Path) -> None:
        page = r / "docs" / "cases" / "C04.md"
        page.write_bytes(page.read_bytes() + b"\nTODO: the lifetime section.\n")

    refute(base_copy, repo, f"{C04}::test_case_page", plant, "test_case_page")


def test_ct414_a_case_page_that_drops_a_source_is_found(base_copy: Path, repo: Path) -> None:
    refute(base_copy, repo, f"{C04}::test_case_page",
           lambda r: edit(r, "docs/cases/C04.md", "2401.08892", "0000.00000", count=100), "test_case_page")


def test_ct415_a_five_year_window_that_is_not_five_years_is_found(base_copy: Path, repo: Path) -> None:
    def mutate(d: dict) -> None:
        row = d["outputs"]["lifetime"][0]
        row["last"] = row["first"] + 3

    refute(base_copy, repo, f"{C04}::test_lifetime_check", _edit("data/derived/C04/sp.json", mutate), "test_lifetime_check")
