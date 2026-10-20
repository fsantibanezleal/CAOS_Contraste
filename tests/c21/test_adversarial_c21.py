"""The adversarial checks of C21 (docs/design/features/c21/validation.md): each plants a defect that the named gate must refuse."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import contract_schemas as cs
import pytest
from c21_support import (API_HEADER, C21, DERIVED, MODELS, SEED, VARIANTS, Paths, committed, listing_problems, load, make_year, planted_downloads,
                         planted_root, semantics, values, write_file)
from riskvalidation.fairness import metrics as rv_metrics

from pipeline.cases.c21 import bake, fetch, legal, page, reader
from pipeline.io import contract as c1

PAIR = "pair-2018-19"
SCHEMA = "c21/variant-year-pair"


def doc_copy() -> dict:
    return copy.deepcopy(committed("pair-2023-24"))


def schema_errors(doc: dict) -> list[str]:
    return cs.errors(SCHEMA, doc)


def attribute(doc: dict, field: str) -> dict:
    return next(a for a in doc["outputs"]["attributes"] if a["field"] == field)


def a_race_contrast(doc: dict, group: str = "Black or African American") -> dict:
    return next(c for c in attribute(doc, "derived_race")["contrasts"] if c["group"] == group)


# --- CT-2101 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_bad_column_state_or_year_is_refused(tmp_path: Path) -> None:
    rows = make_year(2019, 200)
    cut = API_HEADER.index("income")
    write_file(tmp_path / "a.csv", [r[:cut] + r[cut + 1:] for r in rows], API_HEADER[:cut] + API_HEADER[cut + 1:])
    with pytest.raises(reader.HmdaFormatError, match="required columns are absent"):
        reader.read_year(tmp_path / "a.csv", 2019)
    other = [list(r) for r in rows]
    other[3][1] = "DC"
    write_file(tmp_path / "b.csv", other)
    with pytest.raises(reader.HmdaFormatError, match="state_code"):
        reader.read_year(tmp_path / "b.csv", 2019)
    wrong = [list(r) for r in rows]
    wrong[5][0] = "2020"
    write_file(tmp_path / "c.csv", wrong)
    with pytest.raises(reader.HmdaFormatError, match="activity_year"):
        reader.read_year(tmp_path / "c.csv", 2019)


# --- CT-2102 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_withdrawn_row_never_enters_the_rates(tmp_path: Path) -> None:
    rows = [list(r) for r in make_year(2019, 600)]
    idx = next(i for i, r in enumerate(rows) if r[3] == "White" and r[6] == "1")
    before = reader.read_year(_write(tmp_path / "a.csv", rows), 2019)
    rows[idx][6] = "4"                                      # the approval becomes a withdrawn application
    after = reader.read_year(_write(tmp_path / "b.csv", rows), 2019)
    assert len(after.rows) == len(before.rows) - 1 and after.action_counts[4] == before.action_counts[4] + 1
    rb = rv_metrics.group_selection_rates(reader.to_sample(before).decision, reader.to_sample(before).attribute["derived_race"])["White"]
    ra = rv_metrics.group_selection_rates(reader.to_sample(after).decision, reader.to_sample(after).attribute["derived_race"])["White"]
    assert (ra.n, ra.favourable) == (rb.n - 1, rb.favourable - 1)       # the withdrawn row is in neither the count nor the approvals
    j = next(i for i, r in enumerate(rows) if r[6] == "3")
    assert {r["row"]: r["decision"] for r in after.rows}[j + 1] == 0    # a denial stays a denial


# --- CT-2103 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_decision_sample_without_the_decision_is_rejected_by_contract_1(tmp_path: Path) -> None:
    y = reader.read_year(_write(tmp_path / "a.csv", make_year(2019, 200)), 2019)
    recs = [{k: v for k, v in r.items() if k != "decision"} for r in reader.contract_records(y)]
    rep = c1.validate("scored_sample", recs, params={"outcome": "none"}, extra_fields=reader.CONTRACT_FIELDS)
    assert rep.counts()["accepted"] == 0 and rep.counts()["rejected"] == len(recs)
    assert rep.rejected[0]["violations"][0]["field"] == "decision"


# --- CT-2104 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_changed_raw_file_is_refused_by_its_provenance_record(tmp_path: Path) -> None:
    fetch.fetch(tmp_path, today="2026-10-19", years=(2018, 2019), download=planted_downloads(n=100), attempts=1, pause=0.0)
    assert len(fetch.load_provenance(tmp_path)) == 2
    f = tmp_path / "raw" / "hmda" / fetch.file_name(2019)
    data = bytearray(f.read_bytes())
    data[len(data) // 2] ^= 1
    f.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="differs from its provenance record"):
        fetch.load_provenance(tmp_path)


# --- CT-2105 -----------------------------------------------------------------------------------------------------------
def test_adversarial_an_unknown_category_is_refused_and_never_folded_into_a_group(tmp_path: Path) -> None:
    rows = [list(r) for r in make_year(2019, 200)]
    rows[7][API_HEADER.index("derived_race")] = "Whites"
    with pytest.raises(reader.HmdaFormatError, match="derived_race"):
        reader.read_year(_write(tmp_path / "a.csv", rows), 2019)
    rows = [list(r) for r in make_year(2019, 200)]
    rows[7][API_HEADER.index("loan_type")] = "9"
    with pytest.raises(reader.HmdaFormatError, match="loan_type"):
        reader.read_year(_write(tmp_path / "b.csv", rows), 2019)


# --- CT-2106 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_flag_decided_on_a_float_is_found_by_the_exact_check() -> None:
    sem = semantics()
    doc = doc_copy()
    a = attribute(doc, "derived_sex")
    a["groups"] = [{"group": "Male", "n": 100, "n_approved": 75, "n_denied": 25, "selection_rate": 0.75},
                   {"group": "Female", "n": 100, "n_approved": 60, "n_denied": 40, "selection_rate": 0.6}]
    a["four_fifths"]["highest_rate_group"] = "Male"
    ratio = 0.6 / 0.75
    assert ratio < 0.8                                             # the float is 0.7999999999999999: a float rule would flag it
    a["four_fifths"]["groups"] = [{"group": "Male", "ratio_to_highest": 1.0, "flag": False},
                                  {"group": "Female", "ratio_to_highest": ratio, "flag": ratio < 0.8}]
    found = sem.check_c21(doc)
    assert any("Female flag is True but the exact counts give False" in m for m in found), found


# --- CT-2107 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_z_statistic_from_elsewhere_is_found() -> None:
    doc = doc_copy()
    assert semantics().check_c21(doc) == []
    a_race_contrast(doc)["z_test"]["statistic"] += 0.01
    found = semantics().check_c21(doc)
    assert any("z-test" in m for m in found), found


# --- CT-2108 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_controlled_estimate_without_the_missing_credit_score_is_refused() -> None:
    doc = doc_copy()
    assert schema_errors(doc) == []
    a_race_contrast(doc)["controlled"]["estimate"]["missing_controls"] = []
    assert schema_errors(doc)
    doc = doc_copy()
    a_race_contrast(doc)["rate_spread"]["estimate"]["missing_controls"] = ["income"]
    assert schema_errors(doc)


# --- CT-2109 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_flipped_confirmation_sign_is_found() -> None:
    doc = doc_copy()
    conf = a_race_contrast(doc)["confirmation"]["estimate"]
    assert conf["same_sign"] is True
    conf["confirm_coefficient"] = -conf["confirm_coefficient"]
    found = semantics().check_c21(doc)
    assert any("same_sign" in m for m in found), found


# --- CT-2110 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_counterfactual_claim_or_standard_normalization_is_refused() -> None:
    doc = doc_copy()
    doc["outputs"]["situation_testing"]["counterfactual_test"]["run"] = True
    assert schema_errors(doc)
    doc = doc_copy()
    doc["outputs"]["situation_testing"]["distance_normalization"] = "standard"
    assert schema_errors(doc)
    doc = doc_copy()
    doc["outputs"]["situation_testing"]["comparator"] = "mutatis-mutandis"
    assert schema_errors(doc)


# --- CT-2111 -----------------------------------------------------------------------------------------------------------
def test_adversarial_an_outcome_conditioned_test_row_is_refused() -> None:
    doc = doc_copy()
    row = copy.deepcopy(doc["tests"][0])
    row["test_id"] = "fair.equalized_odds"
    doc["tests"].append(row)
    assert any("fair.equalized_odds" in e or "enum" in e for e in schema_errors(doc)) or schema_errors(doc)


# --- CT-2112 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_document_without_the_label_or_with_a_violation_finding_is_refused() -> None:
    doc = doc_copy()
    del doc["outputs"]["legal"]["label"]
    assert schema_errors(doc)
    doc = doc_copy()
    doc["outputs"]["legal"]["is_a_finding_of_violation"] = True
    assert schema_errors(doc)
    doc = doc_copy()
    doc["outputs"]["legal"]["procedures"]["quote"] = "Gross HMDA disparities are findings."
    assert schema_errors(doc)


# --- CT-2113 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_failed_year_writes_nothing_for_its_pairs(tmp_path: Path) -> None:
    root = planted_root(tmp_path / "raw", n=500, fail=(2020,))
    paths = Paths(tmp_path / "out")
    bake.bake_case(SEED, paths, root)
    written = sorted(p.name for p in (paths.root / "C21").glob("pair-*.json"))
    assert written == ["pair-2018-19.json", "pair-2021-22.json", "pair-2022-23.json", "pair-2023-24.json"]
    manifest = load(paths.manifests / "C21.json")
    assert [e["variant_id"] for e in manifest["artifacts"] if e["role"] == "variant"] == [w.removesuffix(".json") for w in written]


# --- CT-2114 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_document_changed_after_hashing_is_found(tmp_path: Path) -> None:
    folder = tmp_path / "C21"
    folder.mkdir()
    for f in C21.iterdir():
        (folder / f.name).write_bytes(f.read_bytes())
    manifest = load(DERIVED / "manifests" / "C21.json")
    assert listing_problems(folder, manifest) == []
    victim = folder / f"{VARIANTS[2]}.json"
    victim.write_bytes(victim.read_bytes().replace(b'"pair_id": "2020-21"', b'"pair_id": "2020-21" ', 1) if b'"pair_id": "2020-21"' in victim.read_bytes()
                       else victim.read_bytes() + b" ")
    assert listing_problems(folder, manifest)
    (folder / "SHA256SUMS.txt").write_text("", encoding="utf-8")
    assert len(listing_problems(folder, manifest)) > 1


# --- CT-2115 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_changed_input_row_changes_the_documents(tmp_path: Path) -> None:
    years = (2018, 2019)
    a = planted_root(tmp_path / "a", years=years, n=700)
    plain = planted_downloads(n=700)

    def altered(url: str) -> bytes:
        body = plain(url)
        if "years=2018" not in url:
            return body
        lines = body.decode("utf-8").split("\n")
        i = next(k for k, ln in enumerate(lines) if k and ln.split(",")[6] == "1")
        cells = lines[i].split(",")
        cells[6] = "3"                                           # one approval becomes a denial
        lines[i] = ",".join(cells)
        return "\n".join(lines).encode("utf-8")

    b = tmp_path / "b"
    fetch.fetch(b, today="2026-10-19", years=years, download=altered, attempts=1, pause=0.0)
    da = bake.build(SEED, a).variants[PAIR]
    db = bake.build(SEED, b).variants[PAIR]
    assert da != db and json.dumps(da, sort_keys=True) != json.dumps(db, sort_keys=True)
    assert da["outputs"]["attributes"] != db["outputs"]["attributes"]
    assert da == bake.build(SEED, a).variants[PAIR]              # and the same input still gives the same document


# --- CT-2116 -----------------------------------------------------------------------------------------------------------
def test_adversarial_an_edited_results_block_is_found() -> None:
    text = (C21.parents[2] / "docs" / "cases" / "C21.md").read_text(encoding="utf-8")
    want = page.results_block({v: committed(v) for v in VARIANTS}, committed(MODELS)).strip("\n")
    assert page.block_of(text) == want
    rows_fit = f"{committed(VARIANTS[0])['outputs']['scope']['rows_fit']:,}"
    assert f"| 2018-19 | {rows_fit} |" in want
    edited = text.replace(f"| 2018-19 | {rows_fit} |", "| 2018-19 | 0 |", 1)
    assert edited != text and page.block_of(edited) != want


# --- CT-2117 -----------------------------------------------------------------------------------------------------------
def test_adversarial_a_data_licence_sentence_is_refused() -> None:
    doc = doc_copy()
    doc["outputs"]["licence"]["data_licence"] = "CC0 1.0 Universal"
    assert schema_errors(doc)
    doc = doc_copy()
    doc["outputs"]["licence"]["status"] = "VERIFIED"
    assert schema_errors(doc)


def _write(path: Path, rows: list[list[str]]) -> Path:
    write_file(path, rows)
    return path


def test_adversarial_the_legal_constants_equal_the_contract_values() -> None:
    v = values()
    assert legal.GROUPS == {k: tuple(x) for k, x in v.GROUPS.items()} and legal.NON_GROUPS == {k: tuple(x) for k, x in v.NON_GROUPS.items()}
    assert legal.PLATFORM_TERMS == v.HMDA_PLATFORM_TERMS and legal.MODIFIED_STATEMENT == v.HMDA_MODIFIED
    assert legal.BASIS == v.LEGAL and legal.FHA_DISPARATE_IMPACT == v.FHA_DI and legal.FHA_DISPARATE_IMPACT_AGE == v.FHA_DI_AGE
    assert tuple(legal.CONTROLS) == tuple(v.CONTROL_FIELDS) and legal.ATTRIBUTES == tuple(v.ATTRIBUTE_FIELDS)
